from models.domain import Product

def _get_val(obj, key):
    if not obj:
        return None
    val = obj.get(key)
    if isinstance(val, dict):
        return val.get("value")
    return val

def cpc_to_canonical(pro_json: dict) -> dict:
    """Convertit un luminaire CPC en format canonique."""
    if not pro_json:
        pro_json = {}
        
    photo = pro_json.get("photometric", {})
    elec = pro_json.get("electrical", {})
    mech = pro_json.get("mechanical", {})
    
    # Gestion des valeurs tolérées (SpecValue) ou directes
    lumens = _get_val(photo, "delivered_lumens") or _get_val(photo, "lumens_min")
    wattage = _get_val(elec, "wattage")
    cct_k = _get_val(photo, "cct_k") or _get_val(photo, "cct")
    cri = _get_val(photo, "cri_min")
    ip = _get_val(mech, "ip_rating_min")
    if ip and isinstance(ip, str):
        ip = ip.upper().replace("IP", "").strip()
        
    ik = _get_val(mech, "ik_rating_min")
    if ik and isinstance(ik, str):
        ik = ik.upper().replace("IK", "").strip()
        
    beam_angle = _get_val(photo, "beam_angle_deg")
    
    return {
        "family": pro_json.get("product_family") or pro_json.get("category"),
        "lumens": float(lumens) if lumens is not None else None,
        "wattage": float(wattage) if wattage is not None else None,
        "cct_k": int(cct_k) if cct_k is not None else None,
        "cri": int(cri) if cri is not None else None,
        "ip": int(ip) if ip is not None else None,
        "ik": int(ik) if ik is not None else None,
        "beam_angle": float(beam_angle) if beam_angle is not None else None,
    }

def product_to_canonical(product: Product) -> dict:
    """Convertit un produit scrapé (SQLAlchemy) en format canonique."""
    # Wattage can be derived from lumens / efficacy if it's not stored directly
    wattage = None
    if product.lumens and product.efficacy:
        wattage = product.lumens / product.efficacy

    return {
        "family": product.category_product_family or product.family,
        "lumens": product.lumens,
        "wattage": wattage,
        "cct_k": product.cct,
        "cri": product.cri,
        "ip": product.ip_rating,
        "ik": product.ik_rating,
        "beam_angle": product.beam_angle,
    }
