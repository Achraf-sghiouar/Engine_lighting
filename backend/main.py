from fastapi import FastAPI, UploadFile, File, Depends, BackgroundTasks
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup basic logging
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
    """Exécute le workflow LangGraph en arrière-plan et met à jour le statut."""
    try:
        async for event in app_graph.astream(state_input, config):
            # On peut traiter les événements intermédiaires si besoin
            pass
        logger.info(f"Workflow completed for line {line_id}")
    except Exception as e:
        logger.error(f"Workflow failed for line {line_id}: {e}")
        # Mettre à jour le statut de la ligne en cas d'échec
        from db.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(ProjectLine).where(ProjectLine.id == line_id))
            line = result.scalar_one_or_none()
            if line:
                line.status = "error"
                await db.commit()

# ========== Endpoint d'upload ==========
@app.post("/uploads")
async def upload_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks = None
):
    os.makedirs("/tmp/uploads", exist_ok=True)
    file_path = f"/tmp/uploads/{file.filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    filename_lower = file.filename.lower() if file.filename else ""
    
    # Extraction selon le type de fichier
    if filename_lower.endswith(".pdf"):
        from ingestion.extractors.pdf import extract_from_pdf
        raw_lines = extract_from_pdf(file_path)
    else:
        raw_lines = extract_from_excel(file_path)
    
    # Vérifier que des lignes ont été extraites
    if not raw_lines:
        return JSONResponse(
            status_code=400,
            content={"error": "No lines could be extracted from the file. Please check the format."}
        )
    
    # Créer le projet
    project = Project(name=file.filename, status="processing")
    db.add(project)
    await db.flush()
    
    from workflow.graph import app_graph
    
    # Traiter chaque ligne
    for item in raw_lines:
        pro = build_pro(item)
        thread_id = str(uuid.uuid4())
        
        line = ProjectLine(
            project_id=project.id,
            mark=item.mark.value if item.mark else None,
            quantity=item.quantity.value if item.quantity else 1,
            description=item.description.value if item.description else None,
            specified_sku=item.specified_sku.value if item.specified_sku else None,
            pro_json=pro.model_dump(),
            thread_id=thread_id,
            status="processing"
        )
        db.add(line)
        await db.flush()
        
        # Lancer le workflow en arrière-plan
        config = {"configurable": {"thread_id": thread_id}}
        state_input = {
            "project_id": str(project.id),
            "line_id": str(line.id),
            "pro": pro.model_dump(),
            "status": "processing"
        }
        background_tasks.add_task(run_workflow, app_graph, state_input, config, line.id, project.id)
            
    await db.commit()
    return {"project_id": project.id, "lines_extracted": len(raw_lines)}

# ========== Endpoint pour récupérer les détails d'un projet ==========
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

# ========== Endpoint pour récupérer les détails d'une ligne ==========
@app.get("/lines/{line_id}")
async def get_line(line_id: str, db: AsyncSession = Depends(get_db)):
    query = select(ProjectLine).where(ProjectLine.id == line_id)
    result = await db.execute(query)
    line = result.scalar_one_or_none()
    if not line:
        return JSONResponse(status_code=404, content={"error": "Not found"})
        
    # Récupérer les candidats depuis l'état du workflow LangGraph
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