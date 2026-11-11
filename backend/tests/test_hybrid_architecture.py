import pytest
import asyncio
from unittest.mock import AsyncMock, patch

from app.modules.ingestion.document_intelligence.micro_rag import MicroRAG
from app.modules.ingestion.document_intelligence.confidence import ConfidenceEvaluator
from app.modules.ingestion.document_intelligence.hybrid_engine import HybridDocumentEngine, HybridExtractionResult

def test_micro_rag_glossary():
    text = "Luminaire avec driver DALI-2 et taux d'inconfort UGR<19 pour bloc BAES avec test SATI."
    context = MicroRAG.get_context(text)
    assert "DALI" in context or "DALI-2" in context
    assert "SATI" in context or "BAES" in context
    assert "UGR" in context

def test_micro_rag_deterministic_hints():
    text = """
    PRIX N° 138 : Luminaire type panel LED 600*600 (P02)
    Puissance raccordée : 26 W
    Flux lumineux minimal : 3685 Lm
    Température de couleur : 4000K
    IRC : 80 Ra
    Résistance contre les chocs mécaniques : IK08
    Indice de protection : IP65
    Quantité : 45 pièces
    """
    hints = MicroRAG.extract_deterministic_hints(text)
    assert hints.get("wattage") == 26.0
    assert hints.get("delivered_lumens") == 3685
    assert hints.get("cct_k") == 4000
    assert hints.get("cri_min") == 80
    assert hints.get("ip_rating_min") == "65"
    assert hints.get("ik_rating_min") == "08"
    assert hints.get("quantity") == 45

def test_confidence_evaluator_valid():
    good_pro = {
        "product_family": "downlight",
        "electrical": {"wattage": 20.0},
        "photometric": {"delivered_lumens": 2200, "cct_k": 3000, "cri_min": 85},
        "mechanical": {"ip_rating_min": "44"}
    }
    score, is_confident, issues = ConfidenceEvaluator.evaluate(good_pro)
    assert is_confident is True
    assert score >= 0.70
    assert len(issues) == 0

def test_confidence_evaluator_abnormal_efficiency():
    bad_pro = {
        "product_family": "projecteur",
        "electrical": {"wattage": 500.0},
        "photometric": {"delivered_lumens": 50, "cct_k": 4000},  # 0.1 lm/W -> absurde !
    }
    score, is_confident, issues = ConfidenceEvaluator.evaluate(bad_pro)
    assert is_confident is False
    assert any("anormalement faible" in issue for issue in issues)

@pytest.mark.asyncio
async def test_hybrid_engine_slm_autonomous():
    mock_client = AsyncMock()
    mock_client.call_slm.return_value = {
        "product_family": "downlight",
        "electrical": {"wattage": 15.0},
        "photometric": {"delivered_lumens": 1500, "cct_k": 3000, "cri_min": 80},
        "mechanical": {"ip_rating_min": "20"}
    }

    engine = HybridDocumentEngine(llm_client=mock_client)
    res = await engine.extract_item("Downlight LED 15W 1500 lumens 3000K", mark="D01")

    assert res.engine_used == "slm"
    assert res.confidence_score >= 0.70
    assert res.pro_json["electrical"]["wattage"] == 15.0
    mock_client.call_teacher_groq.assert_not_called()

@pytest.mark.asyncio
async def test_hybrid_engine_escalates_on_ambiguity():
    mock_client = AsyncMock()
    # Le SLM échoue à extraire lumens et watts
    mock_client.call_slm.return_value = {
        "product_family": "inconnu",
        "electrical": {},
        "photometric": {}
    }
    # Le Teacher Groq intervient et fournit la bonne réponse
    mock_client.call_reflection_teacher.return_value = ({
        "product_family": "spot",
        "electrical": {"wattage": 10.0},
        "photometric": {"delivered_lumens": 900, "cct_k": 3000},
        "mechanical": {"ip_rating_min": "65"}
    }, "Correction des watts et lumens omis par le SLM")

    engine = HybridDocumentEngine(llm_client=mock_client)
    res = await engine.extract_item("Spot encastré étanche 10W 900lm IP65", mark="S01")

    assert res.engine_used == "groq_escalated"
    assert res.reflection_data is not None
    assert res.reflection_data["teacher_rationale"] == "Correction des watts et lumens omis par le SLM"
