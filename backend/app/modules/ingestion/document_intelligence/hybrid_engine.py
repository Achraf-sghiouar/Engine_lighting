"""
Orchestrateur Hybride Spécialisé pour l'Éclairage.
Met en œuvre la cascade : Déterministe -> Micro-RAG -> SLM Local -> Confidence Gate -> Escalade Groq Teacher -> Buffer d'Apprentissage.
"""

import logging
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass, field

from app.modules.ingestion.document_intelligence.micro_rag import MicroRAG
from app.modules.ingestion.document_intelligence.confidence import ConfidenceEvaluator
from app.modules.ingestion.document_intelligence.llm_client import LLMClient
from app.modules.ingestion.document_intelligence.prompts import EXTRACTION_PROMPT

logger = logging.getLogger(__name__)

@dataclass
class HybridExtractionResult:
    pro_json: Dict[str, Any]
    engine_used: str  # "deterministic" | "slm" | "groq_escalated" | "slm_with_hints"
    confidence_score: float
    issues: List[str] = field(default_factory=list)
    reflection_data: Optional[Dict[str, Any]] = None


class HybridDocumentEngine:
    """Moteur central d'extraction orchestrant SLM, RAG et Teacher."""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm_client = llm_client or LLMClient()

    async def extract_item(
        self,
        raw_text: str,
        mark: str = "",
        fallback_quantity: Optional[int] = None
    ) -> HybridExtractionResult:
        """
        Exécute l'extraction d'un bloc de spécifications luminaire.
        """
        clean_text = raw_text.strip()
        if not clean_text:
            return HybridExtractionResult(
                pro_json={},
                engine_used="empty",
                confidence_score=0.0,
                issues=["Texte brut vide"]
            )

        # ÉTAPE 1 : Indices déterministes et Micro-RAG
        deterministic_hints = MicroRAG.extract_deterministic_hints(clean_text)
        micro_context = MicroRAG.get_context(clean_text)

        # Construction du prompt contextualisé pour le SLM
        user_prompt = clean_text
        if micro_context:
            user_prompt = f"{micro_context}\n\nSPÉCIFICATION À EXTRAIRE :\n{clean_text}"

        # ÉTAPE 2 : Inférence avec le SLM Local (Qwen 2.5 3B)
        logger.info(f"[{mark}] Inférence SLM locale (Qwen 2.5:3b)...")
        slm_draft = await self.llm_client.call_slm(EXTRACTION_PROMPT, user_prompt)

        # ÉTAPE 3 : Confidence Gate (Évaluation de la sortie SLM)
        score, is_confident, issues = ConfidenceEvaluator.evaluate(slm_draft or {}, clean_text)
        logger.info(f"[{mark}] Évaluation SLM : Score={score:.2f}, Confident={is_confident}, Alertes={issues}")

        # ÉTAPE 4 : Décision de Routage (Cascade / Escalade Teacher)
        if is_confident and slm_draft:
            # Succès SLM autonome (80% des cas)
            final_pro = self._merge_deterministic_safeguards(slm_draft, deterministic_hints, fallback_quantity)
            return HybridExtractionResult(
                pro_json=final_pro,
                engine_used="slm",
                confidence_score=score,
                issues=issues
            )

        # Cas ambigu ou échec SLM -> Escalade vers Groq (Teacher)
        logger.warning(f"[{mark}] Escalade déclenchée vers Groq Teacher (Score {score:.2f}) : {issues}")
        
        teacher_pro = None
        reflection_rationale = ""
        if slm_draft:
            # Reflection-Tuning : on demande au Teacher de corriger l'ébauche du SLM
            teacher_pro, reflection_rationale = await self.llm_client.call_reflection_teacher(
                clean_text, slm_draft, issues, EXTRACTION_PROMPT
            )
        else:
            # Appel standard Teacher si le SLM n'a produit aucun JSON
            teacher_pro = await self.llm_client.call_teacher_groq(EXTRACTION_PROMPT, user_prompt)

        if teacher_pro and isinstance(teacher_pro, dict):
            final_pro = self._merge_deterministic_safeguards(teacher_pro, deterministic_hints, fallback_quantity)
            t_score, _, t_issues = ConfidenceEvaluator.evaluate(final_pro, clean_text)
            
            reflection_entry = {
                "mark": mark,
                "raw_text": clean_text,
                "slm_draft": slm_draft,
                "teacher_correction": final_pro,
                "detected_issues": issues,
                "teacher_rationale": reflection_rationale,
                "micro_context": micro_context
            }

            return HybridExtractionResult(
                pro_json=final_pro,
                engine_used="groq_escalated",
                confidence_score=max(t_score, 0.85),
                issues=t_issues,
                reflection_data=reflection_entry
            )

        # Si Groq n'est pas disponible ou a échoué : Sauvetage hybride SLM + Regex
        logger.info(f"[{mark}] Secours déterministe appliqué sur l'ébauche SLM.")
        rescue_pro = self._merge_deterministic_safeguards(slm_draft or {}, deterministic_hints, fallback_quantity)
        r_score, _, r_issues = ConfidenceEvaluator.evaluate(rescue_pro, clean_text)
        
        return HybridExtractionResult(
            pro_json=rescue_pro,
            engine_used="slm_with_hints",
            confidence_score=r_score,
            issues=r_issues + ["Échec de l'escalade Teacher - Secours déterministe appliqué"]
        )

    def _merge_deterministic_safeguards(
        self,
        extracted: Dict[str, Any],
        hints: Dict[str, Any],
        fallback_quantity: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Complète les omissions évidentes du modèle par les détections déterministes.
        """
        pro = dict(extracted)
        photo = pro.setdefault("photometric", {})
        elec = pro.setdefault("electrical", {})
        mech = pro.setdefault("mechanical", {})

        # Compléter les watts s'ils étaient manquants
        if elec.get("wattage") is None and hints.get("wattage") is not None:
            elec["wattage"] = hints["wattage"]

        # Compléter le flux s'il était manquant
        if photo.get("delivered_lumens") is None and hints.get("delivered_lumens") is not None:
            photo["delivered_lumens"] = hints["delivered_lumens"]

        # Compléter CCT
        if photo.get("cct_k") is None and hints.get("cct_k") is not None:
            photo["cct_k"] = hints["cct_k"]

        # Compléter CRI
        if photo.get("cri_min") is None and hints.get("cri_min") is not None:
            photo["cri_min"] = hints["cri_min"]

        # Compléter IP
        if mech.get("ip_rating_min") is None and hints.get("ip_rating_min") is not None:
            mech["ip_rating_min"] = hints["ip_rating_min"]

        # Compléter IK
        if mech.get("ik_rating_min") is None and hints.get("ik_rating_min") is not None:
            mech["ik_rating_min"] = hints["ik_rating_min"]

        # Quantité : priorité à la valeur connue (BPU/tableau), sinon hint, sinon modèle
        if fallback_quantity is not None:
            pro["quantity"] = fallback_quantity
        elif pro.get("quantity") is None and hints.get("quantity") is not None:
            pro["quantity"] = hints["quantity"]

        return pro
