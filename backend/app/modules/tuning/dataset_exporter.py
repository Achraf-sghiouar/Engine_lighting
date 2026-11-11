"""
Générateur de Dataset pour Fine-Tuning et Reflection-Tuning du SLM Local.
Collecte les retours d'exploitation (feedback utilisateur et arbitrages du Teacher Groq)
pour produire des paires d'entraînement haute fidélité au format JSONL standard.
"""

import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.domain import ProjectLine, ExtractionFeedback
from app.modules.ingestion.document_intelligence.prompts import EXTRACTION_PROMPT

logger = logging.getLogger(__name__)

DEFAULT_DATASET_DIR = os.getenv("TRAINING_DATASET_DIR", "/app/data/training")

class DatasetExporter:
    """Exporte les corrections et réflexions pour le ré-entraînement du SLM."""

    @classmethod
    async def export_sft_dataset(
        cls,
        db: AsyncSession,
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Génère un fichier JSONL contenant les exemples corrigés par les experts humains
        et par le Teacher Groq.
        """
        if not output_path:
            os.makedirs(DEFAULT_DATASET_DIR, exist_ok=True)
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(DEFAULT_DATASET_DIR, f"sft_lighting_dataset_{timestamp}.jsonl")
        else:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

        samples: List[Dict[str, Any]] = []

        # 1. Collecter les lignes ayant fait l'objet d'un feedback utilisateur
        feedback_stmt = select(ExtractionFeedback.line_id).distinct()
        feedback_result = await db.execute(feedback_stmt)
        corrected_line_ids = set(feedback_result.scalars().all())

        if corrected_line_ids:
            lines_stmt = select(ProjectLine).where(ProjectLine.id.in_(corrected_line_ids))
            lines_res = await db.execute(lines_stmt)
            lines = lines_res.scalars().all()

            for line in lines:
                raw_text = line.description or ""
                if not raw_text or len(raw_text.strip()) < 20:
                    continue

                pro_json = line.pro_json or {}
                if not pro_json:
                    continue

                # Format conversationnel d'entraînement
                sample = {
                    "messages": [
                        {"role": "system", "content": EXTRACTION_PROMPT},
                        {"role": "user", "content": raw_text.strip()},
                        {"role": "assistant", "content": json.dumps(pro_json, ensure_ascii=False)}
                    ],
                    "metadata": {
                        "source": "human_feedback_verified",
                        "mark": line.mark,
                        "line_id": str(line.id),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
                samples.append(sample)

        # 2. Collecter les cas d'escalade Groq (Teacher) enregistrés dans raw_data
        all_lines_stmt = select(ProjectLine).where(ProjectLine.raw_data.isnot(None))
        all_lines_res = await db.execute(all_lines_stmt)
        all_lines = all_lines_res.scalars().all()

        for line in all_lines:
            raw_data = line.raw_data or {}
            reflection = raw_data.get("reflection_data")
            if reflection and isinstance(reflection, dict):
                teacher_correction = reflection.get("teacher_correction")
                raw_text = reflection.get("raw_text")
                if raw_text and teacher_correction:
                    sample = {
                        "messages": [
                            {"role": "system", "content": EXTRACTION_PROMPT},
                            {"role": "user", "content": raw_text.strip()},
                            {"role": "assistant", "content": json.dumps(teacher_correction, ensure_ascii=False)}
                        ],
                        "metadata": {
                            "source": "teacher_reflection",
                            "mark": line.mark,
                            "teacher_rationale": reflection.get("teacher_rationale", ""),
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    }
                    samples.append(sample)

        # 3. Écriture dans le fichier JSONL
        written_count = 0
        with open(output_path, "w", encoding="utf-8") as f:
            for s in samples:
                f.write(json.dumps(s, ensure_ascii=False) + "\n")
                written_count += 1

        logger.info(f"Dataset exporté avec succès : {written_count} échantillons dans '{output_path}'.")
        return {
            "total_samples": written_count,
            "output_path": output_path,
            "status": "success"
        }
