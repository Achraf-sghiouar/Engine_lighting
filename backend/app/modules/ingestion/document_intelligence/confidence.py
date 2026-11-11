"""
Module de calcul du Score de Confiance et de Validation Physique.
Fait office de filtre (Confidence Gate) pour décider si l'extraction du SLM est fiable
ou si elle doit être escaladée vers le modèle Teacher (Groq).
"""

from typing import Dict, Any, List, Tuple
import logging

logger = logging.getLogger(__name__)

FAMILLES_VALIDES = {
    "downlight", "spot", "panel", "linear", "projecteur", "applique",
    "suspension", "ruban", "borne", "hublot", "plafonnier", "secours",
    "baes", "bapi", "lampadaire", "autre"
}

class ConfidenceEvaluator:
    """Évalue la qualité et la cohérence physique d'une extraction."""

    @classmethod
    def evaluate(cls, pro_dict: Dict[str, Any], raw_text: str = "") -> Tuple[float, bool, List[str]]:
        """
        Retourne :
        - score (float de 0.0 à 1.0)
        - is_confident (bool, True si >= 0.70)
        - issues (liste de motifs d'alerte ou d'ambiguïté)
        """
        if not pro_dict or not isinstance(pro_dict, dict):
            return 0.0, False, ["Extraction JSON vide ou invalide"]

        score = 1.0
        issues: List[str] = []

        # 1. Validation de la famille
        family = str(pro_dict.get("product_family") or "").lower().strip()
        if not family or family == "none" or family == "null":
            score -= 0.35
            issues.append("Famille de luminaire manquante")
        elif family not in FAMILLES_VALIDES and not any(f in family for f in FAMILLES_VALIDES):
            score -= 0.15
            issues.append(f"Famille atypique ou incertaine: '{family}'")

        # 2. Vérification des specs électriques et photométriques
        elec = pro_dict.get("electrical", {}) if isinstance(pro_dict.get("electrical"), dict) else {}
        photo = pro_dict.get("photometric", {}) if isinstance(pro_dict.get("photometric"), dict) else {}
        mech = pro_dict.get("mechanical", {}) if isinstance(pro_dict.get("mechanical"), dict) else {}

        wattage = elec.get("wattage")
        lumens = photo.get("delivered_lumens") or photo.get("lumens_min")
        if isinstance(lumens, dict):
            lumens = lumens.get("value")

        cct = photo.get("cct_k") or photo.get("cct")
        if isinstance(cct, dict):
            cct = cct.get("value")

        cri = photo.get("cri_min")

        # Présence du minimum vital pour la Phase 2
        if wattage is None and lumens is None:
            score -= 0.40
            issues.append("Ni puissance (Watts) ni flux (Lumens) détectés")

        # 3. Cohérence physique du ratio lm/W (Efficacité lumineuse)
        if wattage and lumens:
            try:
                w_f = float(wattage)
                l_f = float(lumens)
                if w_f > 0:
                    eff = l_f / w_f
                    # Norme LED moderne typique : 40 à 220 lm/W (hors secours)
                    if family != "secours" and family != "baes":
                        if eff < 25:
                            score -= 0.35
                            issues.append(f"Efficacité lumineuse anormalement faible ({eff:.1f} lm/W)")
                        elif eff > 250:
                            score -= 0.35
                            issues.append(f"Efficacité lumineuse anormalement élevée ({eff:.1f} lm/W)")
            except (ValueError, TypeError):
                pass

        # 4. Cohérence CCT
        if cct is not None:
            try:
                cct_val = int(cct)
                if cct_val < 1800 or cct_val > 10000:
                    score -= 0.20
                    issues.append(f"CCT hors plage standard ({cct_val}K)")
            except (ValueError, TypeError):
                score -= 0.10
                issues.append("Format CCT invalide")

        # 5. Cohérence CRI
        if cri is not None:
            try:
                cri_val = int(cri)
                if cri_val < 50 or cri_val > 100:
                    score -= 0.15
                    issues.append(f"CRI hors plage réaliste ({cri_val})")
            except (ValueError, TypeError):
                score -= 0.10
                issues.append("Format CRI invalide")

        # 6. Risque d'hallucination de Quantité (ex: SDCM pris pour Qté)
        qty = pro_dict.get("quantity")
        if qty is not None and raw_text:
            raw_lower = raw_text.lower()
            if qty in (2, 3, 4) and f"{qty} sdcm" in raw_lower and "quantité" not in raw_lower and f"{qty} un" not in raw_lower:
                score -= 0.20
                issues.append(f"Suspicion de confusion entre {qty} SDCM et quantité")

        # Score borné entre 0.0 et 1.0
        final_score = max(0.0, min(1.0, round(score, 2)))
        has_major_anomaly = any("anormalement" in iss for iss in issues)
        is_confident = (final_score >= 0.70) and (wattage is not None or lumens is not None) and not has_major_anomaly

        return final_score, is_confident, issues
