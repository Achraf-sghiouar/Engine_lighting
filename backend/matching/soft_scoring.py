def score_candidat(demande: dict, produit: dict) -> float:
    """Score 0-100 : plus c'est haut, meilleur est le match."""
    score = 0.0
    poids_total = 0.0

    # DIMENSION 1 — Proximité du flux (poids 30)
    if demande.get("lumens") and produit.get("lumens"):
        ecart = abs(produit["lumens"] - demande["lumens"]) / demande["lumens"]
        score += 30 * max(0, 1 - ecart)
        poids_total += 30

    # DIMENSION 2 — Proximité puissance (poids 20) — moins = mieux
    if demande.get("wattage") and produit.get("wattage"):
        ecart = abs(produit["wattage"] - demande["wattage"]) / demande["wattage"]
        score += 20 * max(0, 1 - ecart)
        poids_total += 20

    # DIMENSION 3 — Efficacité (poids 15) — bonus si le produit est plus efficace
    if produit.get("lumens") and produit.get("wattage") and produit["wattage"] > 0:
        eff = produit["lumens"] / produit["wattage"]
        score += 15 * min(1, eff / 150)  # 150 lm/W = excellent
        poids_total += 15

    # DIMENSION 4 — Match CCT exact (poids 10)
    if demande.get("cct_k") and produit.get("cct_k"):
        score += 10 * max(0, 1 - abs(produit["cct_k"] - demande["cct_k"]) / 1000)
        poids_total += 10

    # DIMENSION 5 — Match CRI (poids 10)
    if demande.get("cri") and produit.get("cri"):
        score += 10 * min(1, produit["cri"] / max(demande["cri"], 80))
        poids_total += 10

    # DIMENSION 6 — Marge IP (poids 8) — bonus si plus étanche
    if demande.get("ip") and produit.get("ip") and demande["ip"] > 0:
        score += 8 * min(1, produit["ip"] / demande["ip"])
        poids_total += 8

    # DIMENSION 7 — Complétude des specs (poids 7) — produit bien documenté = confiance
    champs = ["lumens", "wattage", "cct_k", "cri", "ip", "ik", "beam_angle"]
    remplis = sum(1 for c in champs if produit.get(c) is not None)
    score += 7 * (remplis / len(champs))
    poids_total += 7

    return round(score / poids_total * 100, 1) if poids_total > 0 else 0.0
