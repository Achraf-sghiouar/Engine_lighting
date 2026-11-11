def familles_compatibles(f1, f2):
    """Certaines familles sont interchangeables."""
    if not f1 or not f2:
        return True
        
    f1, f2 = f1.lower(), f2.lower()
    
    groupes = [
        {"downlight", "spot", "recessed"},
        {"panel", "dalle"},
        {"linear", "reglette", "profil"},
        {"lampadaire", "exterieur", "projecteur", "outdoor"},
        {"applique", "wall"},
        {"suspension", "suspended"},
        {"highbay", "high-bay"}
    ]
    for g in groupes:
        if f1 in g and f2 in g:
            return True
            
    # Fuzzy match simple
    if f1 in f2 or f2 in f1:
        return True
        
    return f1 == f2

def passe_hard_filter(demande: dict, produit: dict) -> tuple[bool, str]:
    """True si le produit est un candidat POSSIBLE. Retourne (bool, raison_rejet_ou_none)."""

    # RÈGLE 1 — Famille compatible
    if demande.get("family") and produit.get("family"):
        if not familles_compatibles(demande["family"], produit["family"]):
            return False, f"Famille incompatible: {demande['family']} vs {produit['family']}"

    # RÈGLE 2 — IP suffisant
    if demande.get("ip") is not None:
        if produit.get("ip") is None or produit["ip"] < demande["ip"]:
            return False, f"IP insuffisant: {produit.get('ip')} < {demande['ip']}"

    # RÈGLE 3 — IK suffisant
    if demande.get("ik") is not None:
        if produit.get("ik") is None or produit["ik"] < demande["ik"]:
            return False, f"IK insuffisant: {produit.get('ik')} < {demande['ik']}"

    # RÈGLE 4 — Flux dans une plage acceptable (±30%)
    if demande.get("lumens") and produit.get("lumens"):
        ratio = produit["lumens"] / demande["lumens"]
        if ratio < 0.7 or ratio > 1.3:
            return False, f"Flux incompatible: {produit['lumens']}lm vs {demande['lumens']}lm (ratio {ratio:.2f})"

    # RÈGLE 5 — CCT compatible (±700K)
    if demande.get("cct_k") and produit.get("cct_k"):
        if abs(produit["cct_k"] - demande["cct_k"]) > 700:
            return False, f"CCT incompatible: {produit['cct_k']}K vs {demande['cct_k']}K"

    # RÈGLE 6 — CRI suffisant (tolérance -5 points)
    if demande.get("cri") and produit.get("cri"):
        if produit["cri"] < demande["cri"] - 5:
            return False, f"CRI insuffisant: {produit['cri']} < {demande['cri']}"

    # RÈGLE 7 — Puissance raisonnable (pas > 1.5x)
    if demande.get("wattage") and produit.get("wattage"):
        ratio = produit["wattage"] / demande["wattage"]
        if ratio > 1.5:
            return False, f"Puissance trop élevée: {produit['wattage']}W vs {demande['wattage']}W (ratio {ratio:.2f})"

    return True, None
