import re

LUMINAIRE_TERMS = [
    "luminaire", "réglette", "reglette", "downlight", "spot", "applique", "projecteur",
    "hublot", "encastré", "encastre", "borne", "ruban", "bandeau", "baes", "dalle",
    "panel", "panneau", "suspension", "lampadaire", "plafonnier", "lustrerie", "wallwasher",
    "lampe", "led", "éclairage", "eclairage",  # ← ajout termes génériques
]

ACCESSORY_TERMS = ["driver", "alimentation", "piquet", "louver", "accessoire", "déport", "deport"]

ADMIN_TERMS = [
    "bordereau", "titulaire", "marché", "obligations", "pénalités", "pénalite",
    "délais", "delais", "fourniture et pose", "mât octo", "câble", "cable",
    "cahier", "prescriptions", "juridique", "maître d'ouvrage", "sous-traitant",
]


def is_luminaire(text: str) -> bool:
    t = text.lower()
    return any(term in t for term in LUMINAIRE_TERMS)


def has_technical_specs(text: str) -> bool:
    """Détecte les unités techniques de façon tolérante."""
    pattern = r'\d+\s*(lm|lumen|w|watt|k|kelvin|ip\d+|cri|ma|°)\b'
    return bool(re.search(pattern, text, re.IGNORECASE))


def has_photometric_specs(text: str) -> bool:
    """Détecte les unités purement lumineuses (lumens, température, rendu des couleurs)."""
    pattern = r'\d+\s*(lm|lumen|k|kelvin|cri|°)\b'
    return bool(re.search(pattern, text, re.IGNORECASE))


def is_administrative(text: str) -> bool:
    """Détecte une forte densité de vocabulaire juridique."""
    t = text.lower()
    matches = sum(1 for term in ADMIN_TERMS if term in t)
    return matches >= 3  # ← seuil relevé : 3+ mots juridiques


def is_valid_luminaire_spec(text: str) -> bool:
    """Combined smart filter - Uses OR instead of AND for robustness against fragmented text"""
    has_luminaire = is_luminaire(text)
    has_specs = has_technical_specs(text)
    is_admin = is_administrative(text)
    
    has_accessory_terms = any(term in text.lower() for term in ACCESSORY_TERMS)
    has_photo = has_photometric_specs(text)
    
    is_driver_only = has_accessory_terms and not has_photo

    # Passe si (luminaire OU specs) et pas administratif ni driver/accessoire seul
    return (has_luminaire or has_specs) and not is_admin and not is_driver_only