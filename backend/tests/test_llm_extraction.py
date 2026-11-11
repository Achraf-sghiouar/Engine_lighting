import pytest
from models.schemas import PRO, ValueTolerance
from pydantic import ValidationError

def test_pro_schema_validation_example_1():
    # Example 1: Projecteur architectural
    raw_data = {
        "category": "panel", # fixed from projecteur_sportif
        "photometric": {
            "delivered_lumens": 6000,
            "cct_k": 3000,
            "cri_min": 80,
            "beam_angle_deg": None
        },
        "mechanical": {
            "mounting_type": "yoke", # fixed from surface
            "cutout_in": None,
            "ip_rating_min": "IP66",
            "ik_rating_min": "IK08"
        },
        "electrical": {
            "voltage": "230V",
            "dimming_protocol": "DALI",
            "wattage": None
        },
        "compliance": {
            "ce_required": True,
            "enec_required": True,
            "ul_etl": False
        },
        "commercial": {
            "preferred_tiers": ["tier_1", "tier_2"],
            "allow_value_tier": False
        }
    }
    
    # Should parse without error
    pro = PRO(**raw_data)
    assert pro.mechanical.mounting_type == "yoke"
    assert pro.mechanical.ip_rating_min == "IP66"
    assert pro.compliance.ce_required is True

def test_pro_schema_validation_example_2():
    # Example 2: BOQ with ValueTolerance
    raw_data = {
        "category": "downlight",
        "photometric": {
            "lumens_min": {"value": 851, "tolerance_pct": 10},
            "cct": {"value": 3000, "tolerance_pct": 150},
            "cri_min": 92
        },
        "mechanical": {
            "mounting_type": "recessed",
            "ip_rating_min": "IP20"
        },
        "electrical": {
            "voltage": "120-277V",
            "dimming_protocol": "0-10V"
        }
    }
    
    pro = PRO(**raw_data)
    assert pro.photometric.lumens_min.value == 851
    assert pro.photometric.cct.tolerance_pct == 150
    assert pro.electrical.voltage == "120-277V"

def test_pro_schema_invalid_tolerance():
    raw_data = {
        "photometric": {
            "lumens_min": "851" # Should fail, expects ValueTolerance object or dict
        }
    }
    with pytest.raises(ValidationError):
        PRO(**raw_data)
