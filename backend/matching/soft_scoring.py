from typing import List, Dict, Any
from models.domain import Product
from models.schemas import PRO

def calculate_photometric(c: Product, pro: PRO) -> float:
    scores = []
    # Lumens
    if "lumens_min" in pro.photometric and c.lumens:
        req_lumens = pro.photometric["lumens_min"]
        delta_pct = abs(c.lumens - req_lumens) / req_lumens * 100
        tolerance_pct = 10.0
        score = max(0, 100 - max(0, delta_pct - tolerance_pct) * 10)
        scores.append(score)
        
    # CCT
    if "cct" in pro.photometric and c.cct:
        req_cct = pro.photometric["cct"]
        delta_k = abs(c.cct - req_cct)
        tolerance_k = 150
        score = max(0, 100 - max(0, delta_k - tolerance_k) * 0.5)
        scores.append(score)
        
    # CRI
    if "cri_min" in pro.photometric and c.cri:
        req_cri = pro.photometric["cri_min"]
        if c.cri >= req_cri:
            score = min(100, 100 + (c.cri - req_cri) * 0.5)
        else:
            score = max(0, 50 - (req_cri - c.cri) * 5)
        scores.append(score)
        
    return sum(scores) / len(scores) if scores else 100.0


def calculate_mechanical(c: Product, pro: PRO) -> float:
    return 100.0 # simplified for MVP


def calculate_electrical(c: Product, pro: PRO) -> float:
    return 100.0 # simplified for MVP


def calculate_controls(c: Product, pro: PRO) -> float:
    if not pro.dimming_protocol: return 100.0
    if c.dimming_protocol and pro.dimming_protocol.lower() in c.dimming_protocol.lower():
        return 100.0
    return 25.0


def calculate_compliance(c: Product, pro: PRO) -> float:
    if not pro.compliance: return 100.0
    for cert, req in pro.compliance.items():
        if req and cert not in (c.certifications or []):
            return 0.0
    return 100.0


def calculate_lifecycle(c: Product) -> float:
    if c.lifecycle_status == "active": return 100.0
    if c.lifecycle_status == "superseded": return 55.0
    return 0.0


def score_candidates(candidates: List[Product], pro: PRO) -> List[Dict[str, Any]]:
    scored = []
    for c in candidates:
        photo = calculate_photometric(c, pro)
        mech = calculate_mechanical(c, pro)
        elec = calculate_electrical(c, pro)
        ctrl = calculate_controls(c, pro)
        comp = calculate_compliance(c, pro)
        life = calculate_lifecycle(c)
        esth = 100.0 # bonus later
        
        tech_score = min(100, (
            photo * 0.30 +
            mech * 0.20 +
            elec * 0.15 +
            ctrl * 0.15 +
            comp * 0.10 +
            life * 0.05 +
            esth * 0.05
        ))
        
        scored.append({
            "product": c,
            "tech_score": tech_score,
            "breakdown": {
                "photometric": photo,
                "mechanical": mech,
                "electrical": elec,
                "controls": ctrl,
                "compliance": comp,
                "lifecycle": life
            }
        })
    
    # Sort by tech score
    scored.sort(key=lambda x: x["tech_score"], reverse=True)
    return scored
