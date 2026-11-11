from fastapi import FastAPI, UploadFile, File, Depends, BackgroundTasks, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
import shutil
import os
import uuid
import logging
from fastapi.responses import JSONResponse
from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from db.database import get_db
from models.domain import Project, ProjectLine
from ingestion.extractors.excel import extract_from_excel
from ingestion.pro_builder import build_pro
from workflow.router import router as workflow_router


app = FastAPI(title="LAE v4 Substitution Engine")

cors_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:3001"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.middleware("http")
async def add_correlation_id_and_log(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    request.state.correlation_id = correlation_id
    logger.info(f"[{correlation_id}] {request.method} {request.url.path}")
    try:
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response
    except Exception as e:
        logger.error(f"[{correlation_id}] Unhandled exception: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal Server Error", "correlation_id": correlation_id, "detail": str(e)}
        )

app.include_router(workflow_router)

@app.on_event("startup")
async def startup_event():
    from db.seed import init_db
    try:
        await init_db()
    except Exception as e:
        print("Database initialization failed or already initialized:", e)

@app.get("/")
def read_root():
    return {"status": "ok"}

# ========== Fonction pour exécuter le workflow en arrière-plan ==========
async def run_workflow(app_graph, state_input, config, line_id: str, project_id: str):
    logger.info(f"🚀 Starting workflow for line {line_id}")
    try:
        async for event in app_graph.astream(state_input, config):
            logger.info(f"📦 Workflow event for line {line_id}: {event}")
        logger.info(f"✅ Workflow completed for line {line_id}")
    except Exception as e:
        logger.error(f"❌ Workflow failed for line {line_id}: {e}", exc_info=True)
        from db.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(ProjectLine).where(ProjectLine.id == line_id))
            line = result.scalar_one_or_none()
            if line:
                line.status = "error"
                await db.commit()

# Vocabulaire FIXE des familles
FAMILLES = {
    "lampadaire": [
        "éclairage public", "eclairage public", "fonctionnel", "voirie",
        "candélabre", "candelabre", "mât", "mat ", "routier", "urbain",
        "circulaire led", "tête de mât", "tete de mat", "public",
        "extérieur"
    ],
    "secours": ["bloc autonome", "baes", "baeh", "bapi", "balisage", "sécurité", "secours", "antipanique", "evacuation"],
    "panel": ["panel", "dalle"],
    "downlight": ["downlight", "spot encastr"],
    "spot": ["spot", "projecteur sur rail"],
    "projecteur": ["projecteur", "floodlight", "gradins"],
    "linear": ["linéaire", "lineaire", "réglette", "reglette", "profil", "bandeau", "ruban", "tube", "flexible"],
    "suspension": ["suspension", "suspendu"],
    "applique": ["applique", "murale"],
    "plafonnier": ["plafonnier", "hublot"],
}

def _normaliser_famille(pf_llm: str, pro: dict) -> str:
    titre = str(pro.get("_titre_source", "")).lower()
    for famille, mots in FAMILLES.items():
        if any(m in titre for m in mots):
            return famille
    return str(pf_llm or pro.get("product_family") or "autre")

ACCESSOIRES_NON_LUMINAIRE = [
    'driver', 'drivers', 'alimentation', 'ballast', 'transformateur',
    'télécommande', 'centrale', 'profilé seul', 'accessoire'
]

def a_des_specs_reelles(pro: dict, titre: str = "") -> bool:
    t = titre.lower()
    
    photo = pro.get("photometric", {})
    elec = pro.get("electrical", {})
    mech = pro.get("mechanical", {})
    
    has_flux = bool(photo.get("lumens_min") or photo.get("delivered_lumens"))
    has_cct = bool(photo.get("cct") or photo.get("cct_k"))
    
    import re
    is_ps_drv = bool(re.search(r'\b(?:ps|drv|driver)\d*\b', t, re.IGNORECASE))
    
    # Si c'est un accessoire (ex: driver, alimentation), on EXIGE une spécification de lumière
    if any(a in t for a in ACCESSOIRES_NON_LUMINAIRE) or is_ps_drv:
        if not (has_flux or has_cct):
            return False
            
    # Pour un luminaire normal, la présence d'au moins UNE spec suffit (même juste les Watts ou l'IP)
    has_specs = any([
        has_flux,
        has_cct,
        elec.get("wattage"),
        mech.get("ip_rating_min"),
        photo.get("cri_min")
    ])
    
    if has_specs:
        return True
        
    # Si la ligne n'a AUCUNE spec (souvent dû à un mauvais OCR sur un BOQ),
    # on l'accepte QUAND MÊME si sa description est courte (ce n'est donc pas un méga-bloc juridique).
    if len(t) < 500:
        return True
        
    return False

def normaliser_pro_json(pro: dict) -> dict:
    import re
    
    pro.pop("dimming_protocol", None)
    if "category" in pro:
        pro["product_family"] = pro.pop("category")
        
    photo = pro.get("photometric", {})
    if photo.get("cct") and isinstance(photo["cct"], dict):
        if photo["cct"].get("tolerance_pct", 0) > 50:
            photo["cct"]["tolerance_pct"] = 10
    pro["photometric"] = photo
    
    mech = pro.get("mechanical", {})

    ip_raw = str(mech.get("ip_rating_min") or "").strip()
    ip_match = re.search(r'ip\s*(\d{2})', ip_raw, re.IGNORECASE)
    if ip_raw.isdigit():
        mech["ip_rating_min"] = int(ip_raw)
    elif ip_match:
        mech["ip_rating_min"] = int(ip_match.group(1))
    else:
        mech["ip_rating_min"] = None

    ik_raw = str(mech.get("ik_rating_min") or "")
    ik_match = re.search(r'ik\s*(\d{2})', ik_raw, re.IGNORECASE)
    if ik_match:
        mech["ik_rating_min"] = int(ik_match.group(1))
    else:
        mech["ik_rating_min"] = None

    cutout = mech.get("cutout_in")
    if cutout and isinstance(cutout, (int, float)) and cutout > 50:
        mech["cutout_in"] = None

    pro["mechanical"] = mech

    pf = str(pro.get("product_family") or "").lower()
    pro["product_family"] = _normaliser_famille(pf, pro)

    elec = pro.get("electrical", {})
    dim = str(elec.get("dimming_protocol") or "")
    elec["dimming_protocol"] = re.sub(r'\s*-\s*', '-', dim).strip() or None
    pro["electrical"] = elec

    return pro

async def process_upload_bg(file_path: str, project_id: str, filename_lower: str, pipeline_type: str = "BOQ"):
    from db.database import AsyncSessionLocal
    
    try:
        if pipeline_type == "CPC":
            from app.modules.ingestion.document_intelligence.omni_extractor import OmniDocumentExtractor
            from app.modules.ingestion.document_intelligence.llm_client import LLMClient
            from app.modules.ingestion.document_intelligence.prompts import EXTRACTION_PROMPT
            from models.schemas import RawLineItem, ExtractedField
            import asyncio
            
            extractor = OmniDocumentExtractor()
            llm_client = LLMClient()
            try:
                logger.info(f"CPC: démarrage OmniDocumentExtractor pour {filename_lower}")
                if filename_lower.endswith(".pdf"):
                    extracted_items = await asyncio.to_thread(extractor.process_pdf, file_path)
                elif filename_lower.endswith((".docx", ".doc")):
                    extracted_items = await asyncio.to_thread(extractor.process_word, file_path)
                elif filename_lower.endswith((".xlsx", ".xls")):
                    extracted_items = await asyncio.to_thread(extractor.process_excel, file_path)
                else:
                    extracted_items = []
                logger.info(f"CPC: {len(extracted_items)} items extraits")
            except ValueError as ve:
                logger.warning(f"CPC rejeté: {ve}")
                async with AsyncSessionLocal() as db:
                    project = await db.get(Project, project_id)
                    if project:
                        project.status = "error"
                        await db.commit()
                return
            except Exception as e:
                logger.error(f"CPC pipeline crash: {e}", exc_info=True)
                extracted_items = []
            
            if not extracted_items and hasattr(extractor, 'last_full_text') and extractor.last_full_text:
                logger.warning("CPC regex a trouvé 0 luminaire, fallback LLM sur le texte complet")
                from models.schemas import ExtractedItem
                extracted_items = [ExtractedItem(
                    Rep="Fallback",
                    Designation="Extraction Complète",
                    Texte_Source=extractor.last_full_text[:50000]
                )]
            
            raw_lines = []
            sem = asyncio.Semaphore(1)
            
            from datetime import datetime
            async with AsyncSessionLocal() as db:
                project = await db.get(Project, project_id)
                if project:
                    project.total_items = len(extracted_items)
                    project.processed_items = 0
                    project.started_at = datetime.utcnow()
                    project.status = "processing"
                    await db.commit()

            from app.modules.ingestion.document_intelligence.hybrid_engine import HybridDocumentEngine
            hybrid_engine = HybridDocumentEngine(llm_client)

            for idx, e_item in enumerate(extracted_items):
                if len(e_item.Texte_Source) > 6000:
                    logger.warning(f"Bloc {e_item.Rep} anormalement long ({len(e_item.Texte_Source)} car) — probable fusion juridique, rejeté")
                    continue
                    
                qte_num = None
                try:
                    if e_item.Quantite:
                        qte_num = int(float(str(e_item.Quantite).replace(',', '.')))
                except Exception:
                    pass

                async with sem:
                    raw_text_block = e_item.Texte_Source[:4000]
                    try:
                        h_res = await hybrid_engine.extract_item(
                            raw_text=raw_text_block,
                            mark=e_item.Rep or f"Item {idx+1}",
                            fallback_quantity=qte_num
                        )
                        pro_dict = h_res.pro_json
                        engine_used = h_res.engine_used
                        confidence_score = h_res.confidence_score
                        reflection_data = h_res.reflection_data
                    except Exception as e:
                        logger.warning(f"Failed hybrid extraction for item {idx}: {e}")
                        pro_dict = {}
                        engine_used = "error"
                        confidence_score = 0.0
                        reflection_data = None
                    
                    # Pause courte pour SLM local, un peu plus longue si Groq
                    pause_time = 3 if engine_used == "groq_escalated" else 0.5
                    await asyncio.sleep(pause_time)
                
                if not pro_dict:
                    pro_dict = {}
                pro_dict["_raw_source_text"] = e_item.Texte_Source
                pro_dict["_titre_source"] = e_item.Designation
                
                pro_dict = normaliser_pro_json(pro_dict)
                
                full_cpc_title = f"{e_item.Rep or ''} {e_item.Designation or ''}"
                if not a_des_specs_reelles(pro_dict, full_cpc_title):
                    logger.warning(f"Bloc {e_item.Rep} rejeté : aucune spec réelle (juridique ou vide)")
                    continue
                
                raw_lines.append(RawLineItem(
                    id=str(idx),
                    mark=ExtractedField(value=e_item.Rep),
                    description=ExtractedField(value=e_item.Texte_Source),
                    quantity=ExtractedField(value=str(pro_dict.get("quantity") or e_item.Quantite or "1")),
                    raw_data={
                        "pro": pro_dict,
                        "source": "cpc",
                        "engine_used": engine_used,
                        "confidence_score": confidence_score,
                        "reflection_data": reflection_data
                    }
                ))
                
                async with AsyncSessionLocal() as db:
                    project = await db.get(Project, project_id)
                    if project:
                        project.processed_items = idx + 1
                        await db.commit()
        else:
            if filename_lower.endswith(".pdf"):
                from app.modules.ingestion.document_intelligence.extractor_advanced import extract_advanced_pdf
                raw_lines = await extract_advanced_pdf(file_path, project_id)
            elif filename_lower.endswith((".docx", ".doc")):
                from ingestion.extractors.excel import extract_from_word
                import asyncio
                raw_lines = await asyncio.to_thread(extract_from_word, file_path)
            else:
                from ingestion.extractors.excel import extract_from_excel
                import asyncio
                raw_lines = await asyncio.to_thread(extract_from_excel, file_path)
        
        valid_lines = []
        for item in raw_lines:
            mark = item.mark.value if item.mark else ""
            desc = item.description.value if item.description else ""
            if mark and desc and not mark.lower() in ("code", "codeluminaire", "fabricant", "modèle"):
                valid_lines.append(item)
            else:
                logger.warning(f"Ligne ignorée : mark='{mark}', desc='{desc}'")
        
        async with AsyncSessionLocal() as db:
            project = await db.get(Project, project_id)
            if not project:
                return
                
            if not valid_lines:
                project.status = "error"
                await db.commit()
                return

            new_valid_lines = []
            for item in valid_lines:
                if "pro" in item.raw_data:
                    pro_json = item.raw_data["pro"]
                else:
                    pro_obj = build_pro(item)
                    pro_json = pro_obj.model_dump()
                
                pro_json = normaliser_pro_json(pro_json)
                
                full_title = f"{item.mark.value if item.mark else ''} {item.description.value if item.description else ''}"
                if not a_des_specs_reelles(pro_json, full_title):
                    logger.warning(f"Ligne {item.mark.value if item.mark else 'inconnue'} rejetée: pas de specs valides | Titre: {full_title} | Specs extraites: {pro_json}")
                    continue
                
                item.raw_data["pro"] = pro_json
                new_valid_lines.append(item)
                
            if not new_valid_lines:
                project.status = "error"
                await db.commit()
                return
                
            for item in new_valid_lines:
                pro_json = item.raw_data["pro"]
                    
                thread_id = str(uuid.uuid4())
                qty_str = item.quantity.value if item.quantity else "1"
                try:
                    qty = int(qty_str)
                    if qty < 0 or qty > 9999:
                        qty = 1
                except ValueError:
                    qty = 1
                
                line = ProjectLine(
                    project_id=project.id,
                    mark=item.mark.value if item.mark else None,
                    quantity=qty,
                    description=item.description.value if item.description else None,
                    specified_sku=item.specified_sku.value if item.specified_sku else None,
                    pro_json=pro_json,
                    thread_id=thread_id,
                    status="draft"
                )
                db.add(line)
            
            project.status = "draft" # Done processing upload
            await db.commit()
    except Exception as e:
        logger.error(f"Error in background upload processing: {e}", exc_info=True)
        async with AsyncSessionLocal() as db:
            project = await db.get(Project, project_id)
            if project:
                project.status = "error"
                await db.commit()

# ========== Endpoint d'upload ==========
@app.post("/uploads")
async def upload_file(
    file: UploadFile = File(...),
    pipeline_type: str = Form("BOQ"),
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks = None
):
    os.makedirs("/tmp/uploads", exist_ok=True)
    file_path = f"/tmp/uploads/{file.filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    filename_lower = file.filename.lower() if file.filename else ""
    
    if filename_lower.endswith(".pdf") and pipeline_type == "BOQ":
        import pdfplumber
        try:
            with pdfplumber.open(file_path) as pdf:
                if len(pdf.pages) > 15:
                    return JSONResponse(
                        status_code=400,
                        content={"error": f"Document trop long pour le mode BOQ ({len(pdf.pages)} pages). Utilisez le mode 'AO Public / CPC'."}
                    )
        except Exception as e:
            pass
            
    project = Project(name=file.filename, status="processing")
    db.add(project)
    await db.flush()
    project_id = str(project.id)
    await db.commit()
    
    if background_tasks:
        background_tasks.add_task(process_upload_bg, file_path, project_id, filename_lower, pipeline_type)
        
    return {"project_id": project_id, "status": "processing"}

# ========== Endpoints de récupération ==========
from pydantic import BaseModel
from typing import List, Dict, Any
from models.domain import ExtractionFeedback

@app.get("/uploads/{project_id}/progress")
async def get_progress(project_id: str, db: AsyncSession = Depends(get_db)):
    from datetime import datetime
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    total = project.total_items or 1
    done = project.processed_items or 0
    
    eta_seconds = None
    if done > 0 and project.started_at:
        elapsed = (datetime.utcnow() - project.started_at).total_seconds()
        rate = elapsed / done
        remaining = total - done
        eta_seconds = int(rate * remaining)
        
    return {
        "status": project.status,
        "total": total,
        "processed": done,
        "percent": round(done / total * 100),
        "eta_seconds": eta_seconds,
    }

@app.get("/uploads/{project_id}/preview")
async def preview_upload(project_id: str, db: AsyncSession = Depends(get_db)):
    query = select(Project).where(Project.id == project_id).options(selectinload(Project.lines))
    result = await db.execute(query)
    project = result.scalar_one_or_none()
    if not project:
        return JSONResponse(status_code=404, content={"error": "Not found"})
        
    progress_data = {"completed": 0, "total": 0}
    if project.status == "processing":
        try:
            import redis.asyncio as redis
            import os
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            r = redis.from_url(redis_url)
            total = await r.get(f"progress:{project_id}:total")
            completed = await r.get(f"progress:{project_id}:completed")
            if total:
                progress_data["total"] = int(total)
            if completed:
                progress_data["completed"] = int(completed)
        except Exception as e:
            pass
            
    return {
        "id": str(project.id),
        "name": project.name,
        "status": project.status,
        "progress": progress_data,
        "lines": [
            {
                "id": str(line.id),
                "mark": line.mark,
                "quantity": line.quantity,
                "description": line.description,
                "specified_sku": line.specified_sku,
                "pro": line.pro_json,
                "confidence": line.confidence_overall
            } for line in project.lines
        ]
    }

@app.get("/debug/project/{project_id}/extraction")
async def debug_extraction(project_id: str, db: AsyncSession = Depends(get_db)):
    """Retourne le PRO JSON brut de chaque ligne pour debug."""
    result = await db.execute(
        select(ProjectLine)
        .options(selectinload(ProjectLine.project))
        .where(ProjectLine.project_id == project_id)
    )
    lines = result.scalars().all()
    
    pages_in_pdf = 0
    pages_processed = 0
    try:
        import redis.asyncio as redis
        import os
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        r = redis.from_url(redis_url)
        tp = await r.get(f"debug:{project_id}:total_pages")
        pp = await r.get(f"debug:{project_id}:processed_tasks")
        if tp: pages_in_pdf = int(tp)
        if pp: pages_processed = int(pp)
    except Exception:
        pass
    
    return {
        "project_id": project_id,
        "total_lines": len(lines),
        "pages_in_pdf": pages_in_pdf,
        "pages_processed": pages_processed,
        "lines": [
            {
                "mark": line.mark,
                "description": line.description,
                "pro_json": line.pro_json,
                "extraction_failed": line.pro_json.get("_extraction_failed", False) if line.pro_json else True,
                "confidence": line.pro_json.get("confidence") if line.pro_json else None,
            }
            for line in lines
        ]
    }
from typing import List, Dict, Any, Optional

from models.schemas import PRO

class ConfirmLineRequest(BaseModel):
    id: str
    mark: Optional[str] = None
    quantity: int = 1
    description: Optional[str] = None
    specified_sku: Optional[str] = None
    pro: Optional[PRO] = None

class ConfirmUploadRequest(BaseModel):
    lines: List[ConfirmLineRequest]

@app.post("/uploads/{project_id}/confirm")
async def confirm_and_match(
    project_id: str, 
    req: ConfirmUploadRequest, 
    background_tasks: BackgroundTasks, 
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Project).options(selectinload(Project.lines)).where(Project.id == project_id)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if not project:
        return JSONResponse(status_code=404, content={"error": "Not found"})
        
    project.status = "processing"
    
    from workflow.graph import app_graph
    
    for corr in req.lines:
        line = next((l for l in project.lines if str(l.id) == corr.id), None)
        if not line:
            continue
            
        original_pro = line.pro_json or {}
        
        if corr.mark and line.mark != corr.mark:
            db.add(ExtractionFeedback(line_id=line.id, field_name="mark", original_value=line.mark, corrected_value=corr.mark, confidence=line.confidence_overall, actor="user"))
            line.mark = corr.mark
        if corr.specified_sku and line.specified_sku != corr.specified_sku:
            db.add(ExtractionFeedback(line_id=line.id, field_name="specified_sku", original_value=line.specified_sku, corrected_value=corr.specified_sku, confidence=line.confidence_overall, actor="user"))
            line.specified_sku = corr.specified_sku
        if corr.quantity and line.quantity != corr.quantity:
            line.quantity = corr.quantity
        if corr.description and line.description != corr.description:
            line.description = corr.description
            
        if corr.pro:
            corr_pro_dict = corr.pro.model_dump(exclude_unset=True)
            for key, value in corr_pro_dict.items():
                orig_val = original_pro.get(key)
                if orig_val != value:
                    db.add(ExtractionFeedback(line_id=line.id, field_name=f"pro.{key}", original_value=str(orig_val), corrected_value=str(value), confidence=line.confidence_overall, actor="user"))
                    
            line.pro_json = corr.pro.model_dump()
            
        # Start workflow
        thread_id = str(uuid.uuid4())
        line.thread_id = thread_id
        line.status = "processing"
        
        config = {"configurable": {"thread_id": thread_id}}
        state_input = {
            "project_id": str(project.id),
            "line_id": str(line.id),
            "pro": line.pro_json,
            "status": "processing"
        }
        background_tasks.add_task(run_workflow, app_graph, state_input, config, line.id, project.id)
                
    await db.commit()
    return {"status": "workflows_started"}

@app.get("/projects/{project_id}")
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    query = select(Project).where(Project.id == project_id).options(selectinload(Project.lines))
    result = await db.execute(query)
    project = result.scalar_one_or_none()
    if not project:
        return JSONResponse(status_code=404, content={"error": "Not found"})
    return {
        "id": str(project.id),
        "name": project.name,
        "status": project.status,
        "lines": [
            {
                "id": str(line.id),
                "mark": line.mark,
                "quantity": line.quantity,
                "description": line.description,
                "status": line.status,
                "thread_id": line.thread_id
            } for line in project.lines
        ]
    }

@app.get("/lines/{line_id}")
async def get_line(line_id: str, db: AsyncSession = Depends(get_db)):
    query = select(ProjectLine).where(ProjectLine.id == line_id)
    result = await db.execute(query)
    line = result.scalar_one_or_none()
    if not line:
        return JSONResponse(status_code=404, content={"error": "Not found"})
    
    from workflow.graph import app_graph
    config = {"configurable": {"thread_id": line.thread_id}}
    try:
        state = await app_graph.aget_state(config)
    except Exception as e:
        logger.error(f"Error getting state for line {line_id}: {e}")
        state = None
    
    candidates = []
    if state and state.values and "final_candidates" in state.values:
        for c in state.values["final_candidates"]:
            prod = c.get("product")
            if prod:
                candidates.append({
                    "sku": prod.sku,
                    "brand": prod.brand,
                    "lumens": prod.lumens,
                    "cct": prod.cct,
                    "tier": prod.tier,
                    "margin": c.get("margin", prod.margin),
                    "final_score": c.get("final_score", 0),
                    "risk_flags": c.get("risk_flags", [])
                })
    
    return {
        "id": str(line.id),
        "mark": line.mark,
        "description": line.description,
        "specified_sku": line.specified_sku,
        "pro": line.pro_json,
        "thread_id": line.thread_id,
        "candidates": candidates
    }

@app.post("/tuning/export-dataset")
async def export_tuning_dataset(db: AsyncSession = Depends(get_db)):
    """Exporte les corrections validées et les réflexions Teacher au format JSONL SFT."""
    from app.modules.tuning.dataset_exporter import DatasetExporter
    res = await DatasetExporter.export_sft_dataset(db)
    return res