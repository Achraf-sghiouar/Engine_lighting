import pdfplumber
import logging
import json
import re
import os
import asyncio
import redis.asyncio as redis
from typing import List, Tuple
from models.schemas import RawLineItem, ExtractedField, SourceRef, PRO
from app.modules.ingestion.document_intelligence.llm_client import OllamaClient
from app.modules.ingestion.document_intelligence.prompts import (
    SYSTEM_PROMPT_EXTRACTION, USER_PROMPT_TEMPLATE,
    SYSTEM_PROMPT_EXTRACTION_MULTI, USER_PROMPT_TEMPLATE_MULTI
)
from app.modules.ingestion.document_intelligence.normalizer import to_tolerance
from app.modules.ingestion.document_intelligence.vocab import is_valid_luminaire_spec
import pytesseract
from pdf2image import convert_from_path

logger = logging.getLogger(__name__)
ollama_client = OllamaClient()

_PRIX_RE = re.compile(r"Prix\s*n[°ºo]\s*(\d+)", re.IGNORECASE)

def _build_pro_from_dict(pro_dict: dict) -> PRO:
    """Helper to convert the LLM dictionary into a validated PRO object with tolerances."""
    
    def _unwrap_dict(val):
        if isinstance(val, list):
            return val[0] if val and isinstance(val[0], dict) else {}
        return val if isinstance(val, dict) else {}
        
    photo = _unwrap_dict(pro_dict.get("photometric", {}))
    mech = _unwrap_dict(pro_dict.get("mechanical", {}))
    elec = _unwrap_dict(pro_dict.get("electrical", {}))
    comp = _unwrap_dict(pro_dict.get("compliance", {}))

    if photo.get("cct_k") is not None:
        photo["cct"] = to_tolerance(photo["cct_k"], 150)
        photo.pop("cct_k", None)
    if photo.get("delivered_lumens") is not None:
        photo["lumens_min"] = to_tolerance(photo["delivered_lumens"], 10)
        photo.pop("delivered_lumens", None)
    if mech.get("cutout_in") is not None:
        mech["cutout_in"] = to_tolerance(mech["cutout_in"], 10)
        
    clean_dict = {
        "category": pro_dict.get("product_family"),
        "mechanical": mech,
        "electrical": elec,
        "photometric": photo,
        "compliance": comp,
        "dimming_protocol": elec.get("dimming_protocol")
    }
    
    try:
        return PRO(**clean_dict)
    except Exception as e:
        logger.warning(f"PRO Validation failed during extraction: {e}")
        return PRO()

from app.modules.ingestion.document_intelligence.prompts import EXTRACTION_PROMPT

async def _process_llm_item(item_data: dict, page_num: int, source_text: str = "") -> RawLineItem | None:
    if not isinstance(item_data, dict):
        return None
    mark_str = str(item_data.get("mark", ""))
    if not mark_str or mark_str.lower() in ("null", "none"):
        return None
        
    desc_str = str(item_data.get("description", ""))
    
    # Pass B: Structuration stricte via le moteur Hybride (SLM + Micro-RAG + Confidence Gate + Groq)
    from app.modules.ingestion.document_intelligence.hybrid_engine import HybridDocumentEngine
    hybrid_engine = HybridDocumentEngine(ollama_client)
    
    engine_used = "slm"
    confidence_score = 0.8
    reflection_data = None
    
    if desc_str or source_text:
        text_to_analyze = source_text if (len(desc_str) < 50 and len(source_text) > 50) else (desc_str or source_text)
        try:
            h_res = await hybrid_engine.extract_item(text_to_analyze, mark=mark_str)
            structured_data = h_res.pro_json
            engine_used = h_res.engine_used
            confidence_score = h_res.confidence_score
            reflection_data = h_res.reflection_data
        except Exception as e:
            logger.warning(f"Hybrid engine failed in extractor_advanced: {e}")
            structured_data = {}
    else:
        structured_data = {}
        
    if "quantity" in structured_data and structured_data["quantity"] is not None:
        qty_val = structured_data["quantity"]
    else:
        qty_val = item_data.get("quantity")
        
    try:
        qty = int(qty_val) if qty_val else 1
    except:
        qty = 1
    
        
    # MERGE Pass A (item_data["pro"]) and Pass B (structured_data) to prevent data loss
    pass_a_pro = item_data.get("pro", {})
    if not isinstance(pass_a_pro, dict):
        pass_a_pro = {}
        
    pro_raw = {}
    # Helper to merge deeply
    for cat in ["photometric", "mechanical", "electrical", "compliance"]:
        pro_raw[cat] = {}
        a_cat = pass_a_pro.get(cat, {}) if isinstance(pass_a_pro.get(cat), dict) else {}
        b_cat = structured_data.get(cat, {}) if isinstance(structured_data.get(cat), dict) else {}
        keys = set(a_cat.keys()).union(set(b_cat.keys()))
        for k in keys:
            # Prefer Pass B, fallback to Pass A if Pass B missed it (e.g., table header context)
            val_b = b_cat.get(k)
            val_a = a_cat.get(k)
            pro_raw[cat][k] = val_b if val_b is not None else val_a
            
    # Top level keys
    pro_raw["product_family"] = structured_data.get("product_family") or pass_a_pro.get("product_family")
    pro_raw["reference_brands"] = structured_data.get("reference_brands") or pass_a_pro.get("reference_brands")
    if structured_data.get("_extraction_failed"):
        pro_raw["_extraction_failed"] = True
    
    pro_obj = _build_pro_from_dict(pro_raw)
    
    line_item = RawLineItem(
        mark=ExtractedField(value=mark_str, source_ref=SourceRef(page=page_num, cell="LLM")),
        quantity=ExtractedField(value=str(qty), source_ref=SourceRef(page=page_num, cell="LLM")),
        description=ExtractedField(value=desc_str, source_ref=SourceRef(page=page_num, cell="LLM")),
        raw_data={
            "source": "llm",
            "page": page_num,
            "engine_used": engine_used,
            "confidence_score": confidence_score,
            "reflection_data": reflection_data
        }
    )
    pro_dict = pro_obj.model_dump(exclude_unset=True)
    if desc_str:
        pro_dict["_raw_source_text"] = desc_str
    # Conserver si l'extraction a planté (utile pour la vue debug)
    if structured_data.get("_extraction_failed"):
        pro_dict["_extraction_failed"] = True
        
    line_item.raw_data["pro"] = pro_dict
    return line_item

def _page_index(pages: List[str], offset: int) -> int:
    current = 0
    for i, p in enumerate(pages):
        current += len(p) + 1  # +1 for newline
        if offset < current:
            return i + 1
    return len(pages)

async def extract_advanced_pdf(file_path: str, project_id: str = None) -> List[RawLineItem]:
    all_lines = []
    pages = []
    try:
        pages_text = []
        pages_to_ocr = []
        with pdfplumber.open(file_path) as pdf:
            pdf_pages = pdf.pages
            if len(pdf_pages) > 15:
                raise ValueError(
                    f"Document trop long pour le mode BOQ ({len(pdf_pages)} pages). "
                    "Utilisez le mode 'AO Public / CPC'."
                )
                
            for i, page in enumerate(pdf_pages):
                text = page.extract_text() or ""
                pages_text.append(text)
                
                if len(text.split()) < 30:
                    from app.modules.ingestion.document_intelligence.vocab import is_luminaire, has_technical_specs
                    quick_check = is_luminaire(text) or has_technical_specs(text) or len(text.split()) < 5
                    
                    if quick_check:
                        pages_to_ocr.append(i)
                    else:
                        logger.info(f"Page {i+1}: skip OCR (texte natif pauvre et non pertinent)")
                        
        if pages_to_ocr:
            logger.info(f"Exécution de l'OCR en parallèle sur {len(pages_to_ocr)} pages...")
            
            def do_ocr(page_idx):
                try:
                    images = convert_from_path(
                        file_path, 
                        first_page=page_idx + 1, 
                        last_page=page_idx + 1,
                        dpi=150
                    )
                    if images:
                        extracted = pytesseract.image_to_string(images[0], lang='fra+eng')
                        logger.info(f"Page {page_idx+1}: OCR réussi, {len(extracted.split())} mots extraits")
                        return page_idx, extracted
                except Exception as e:
                    logger.error(f"Page {page_idx+1}: échec OCR — {e}")
                return page_idx, ""

            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                ocr_tasks = [loop.run_in_executor(pool, do_ocr, idx) for idx in pages_to_ocr]
                ocr_results = await asyncio.gather(*ocr_tasks)
                
                for idx, text in ocr_results:
                    if text:
                        pages_text[idx] = text

        pages = pages_text

    except Exception as e:
        logger.error(f"Error reading document: {e}")
        return []

    full_text = "\n".join(pages)
    matches = list(_PRIX_RE.finditer(full_text))
    tasks = []
    
    if matches:
        logger.info(f"Using PROSE segmentation mode, found {len(matches)} 'Prix n°' blocks.")
        for idx, m in enumerate(matches):
            start = m.start()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(full_text)
            chunk = full_text[start:end]
            if not is_valid_luminaire_spec(chunk): continue
                
            page_num = _page_index(pages, start)
            async def process_prose(p_text=chunk[:16000], p_num=page_num, s_text=chunk):
                res = await ollama_client.extract_json_async(text=USER_PROMPT_TEMPLATE.format(text=p_text), system_prompt=SYSTEM_PROMPT_EXTRACTION)
                if res and isinstance(res, dict): return await _process_llm_item(res, p_num, source_text=s_text)
                return None
            tasks.append(process_prose())
    else:
        logger.info("Using TABLE segmentation mode, passing full pages to LLM.")
        for i, text in enumerate(pages):
            if not is_valid_luminaire_spec(text) or len(text.strip()) < 50: continue
            page_num = i + 1
            async def process_table(p_text=text[:16000], p_num=page_num, s_text=text):
                results = []
                res = await ollama_client.extract_json_async(text=USER_PROMPT_TEMPLATE_MULTI.format(text=p_text), system_prompt=SYSTEM_PROMPT_EXTRACTION_MULTI)
                if res and isinstance(res, dict):
                    for v in res.values():
                        if isinstance(v, list):
                            res = v
                            break
                if res and isinstance(res, list):
                    for item in res:
                        processed = await _process_llm_item(item, p_num, source_text=s_text)
                        if processed: results.append(processed)
                elif res and isinstance(res, dict):
                    processed = await _process_llm_item(res, p_num, source_text=s_text)
                    if processed: results.append(processed)
                return results
            tasks.append(process_table())
            
    if not tasks:
        logger.warning("No luminaire-like text found.")
        return []

    r = None
    if project_id:
        try:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            r = redis.from_url(redis_url)
            await r.set(f"progress:{project_id}:total", len(tasks))
            await r.set(f"progress:{project_id}:completed", 0)
            await r.set(f"debug:{project_id}:total_pages", len(pages))
            await r.set(f"debug:{project_id}:processed_tasks", len(tasks))
        except Exception as e:
            logger.error(f"Redis progress setup failed: {e}")

    logger.info(f"Executing {len(tasks)} LLM tasks with concurrency limit 2...")
    sem = asyncio.Semaphore(2)
    
    from db.database import AsyncSessionLocal
    from models.domain import Project
    
    async def sem_task(t, task_idx):
        async with sem:
            res = await t
            # Update DB progress
            if project_id:
                try:
                    async with AsyncSessionLocal() as db:
                        project = await db.get(Project, project_id)
                        if project:
                            project.total_items = len(tasks)
                            project.processed_items = task_idx + 1
                            await db.commit()
                except Exception as e:
                    logger.error(f"Error updating DB progress: {e}")
                    
            if r and project_id:
                try: await r.incr(f"progress:{project_id}:completed")
                except: pass
            return res
            
    results_nested = await asyncio.gather(*(sem_task(t, i) for i, t in enumerate(tasks)), return_exceptions=True)
    for res in results_nested:
        if isinstance(res, Exception): logger.error(f"Task failed: {res}")
        elif res:
            if isinstance(res, list): all_lines.extend(res)
            else: all_lines.append(res)
                
    seen_marks = set()
    unique = []
    for line in all_lines:
        m = line.mark.value
        if m in seen_marks: continue
        seen_marks.add(m)
        unique.append(line)
        
    return unique
