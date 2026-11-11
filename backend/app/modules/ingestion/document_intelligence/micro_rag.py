"""
Micro-RAG & Dictionnaire Sémantique Typé pour l'Ingestion Documentaire Éclairage.
Garantit une recherche déterministe ultra-rapide (<1ms) sans surcoût mémoire ni base vectorielle lourde.
"""

import re
from typing import Dict, List, Optional, Tuple, Any

# 1. GLOSSAIRE TECHNIQUE TYPÉ
GLOSSARY: Dict[str, str] = {
    "sati": "SATI: Système Automatique de Test Intégré pour blocs de secours.",
    "baes": "BAES: Bloc Autonome d'Éclairage de Sécurité (famille 'secours').",
    "baeh": "BAEH: Bloc Autonome d'Éclairage pour Habitation (famille 'secours').",
    "bapi": "BAPI: Bloc Autonome Portatif d'Intervention (famille 'secours', montage 'portable').",
    "dali": "DALI/DALI-2: Protocole de gradation numérique (dimming_protocol: 'DALI' ou 'DALI-2').",
    "dmx": "DMX/DMX512: Protocole de gestion scénique/dynamique (dimming_protocol: 'DMX').",
    "ugr": "UGR: Taux d'éblouissement d'inconfort (Unified Glare Rating).",
    "sdcm": "SDCM/MacAdam: Tolérance chromatique. ATTENTION: Ne PAS extraire comme une quantité !",
    "cld": "CLD: Alimentation électronique intégrée (Courant Ligne Direct).",
    "ra": "Ra/IRC/CRI: Indice de rendu des couleurs (ex: 80 Ra -> cri_min=80).",
    "irc": "IRC/CRI: Indice de rendu des couleurs (ex: IRC 90 -> cri_min=90).",
    "cri": "CRI/IRC: Indice de rendu des couleurs (ex: CRI80 -> cri_min=80).",
    "ik": "IK: Indice de résistance aux chocs mécaniques (ex: IK08 -> ik_rating_min='08').",
    "ip": "IP: Indice d'étanchéité eau/poussière (ex: IP65 -> ip_rating_min='65').",
    "rgbw": "RGBW: Température de couleur dynamique RGB + Blanc (cct_k peut être null si non fixe).",
    "trimless": "Trimless: Montage encastré sans collerette apparente (mounting_type: 'recessed').",
    "saillie": "En saillie: Montage direct en surface (mounting_type: 'surface').",
    "suspendu": "Suspendu: Montage par câbles ou tiges (mounting_type: 'suspended').",
    "rail": "Sur rail: Montage sur rail triphasé ou magnétique (mounting_type: 'track').",
}

# 2. RÉPERTOIRE DE MARQUES CONNUES ET PARTENAIRES
KNOWN_BRANDS: List[str] = [
    "leds c4", "disano", "neko", "lavov", "nexia", "avolux", "onok", "klus", "klús",
    "werdell", "werdell lighting", "forlight", "lanzini", "philips", "schréder", "schreder",
    "thorn", "mazda", "iguzzini", "prilux", "bega", "artemide", "targetti", "sammode",
    "lighttek", "puk", "altaïr", "altair", "legrand", "eaton", "saft", "ines", "ingelex", "ingelec",
    "formrack", "kramer", "novastar", "zenith", "prolights", "unilumin"
]

# 3. EXPRESSIONS RÉGULIÈRES DÉTERMINISTES
RE_WATT = re.compile(r'(?i)\b(?:puissance(?:\s+raccord[eé]e|\s+absorb[eé]e)?\s*[:=~]?\s*)?(\d+(?:[.,]\d+)?)\s*(?:w\b|watts?\b)(?!\s*/\s*m\b)', re.IGNORECASE)
RE_WATT_PER_M = re.compile(r'(?i)(\d+(?:[.,]\d+)?)\s*w\s*/\s*m\b', re.IGNORECASE)
RE_LUMENS = re.compile(r'(?i)\b(?:flux(?:\s+lumineux)?(?:\s+sortant|\s+minimal|\s+r[eé]el)?\s*[:=~]?\s*)?(\d+(?:[\s.,]\d+)?)\s*(?:lm\b|lumens?\b)(?!\s*/\s*m\b)', re.IGNORECASE)
RE_LUMENS_PER_M = re.compile(r'(?i)(\d+(?:[\s.,]\d+)?)\s*(?:lm|lumens?)\s*/\s*m\b', re.IGNORECASE)
RE_CCT = re.compile(r'(?i)\b(?:cct|temp[eé]rature(?:\s+de)?\s+couleur)?\s*[:=~]?\s*(\d{4})\s*k\b', re.IGNORECASE)
RE_CRI = re.compile(r'(?i)\b(?:irc|cri|ra)\s*[:=~]?\s*(?:>|≥)?\s*(\d{2})\b|(\d{2})\s*ra\b', re.IGNORECASE)
RE_IP = re.compile(r'(?i)\bip\s*([0-9]{2})\b', re.IGNORECASE)
RE_IK = re.compile(r'(?i)\b(?:ik|k)\s*([0-9]{2})\b', re.IGNORECASE)
RE_BEAM = re.compile(r'(?i)\b(?:angle(?:\s+de\s+faisceau|\s+optique|\s+de\s+diffusion)?|ouverture)\s*[:=~]?\s*(?:spot|flood|medium)?\s*(\d+(?:[.,]\d+)?)\s*º?', re.IGNORECASE)
RE_QTY = re.compile(r'(?i)\b(?:quantit[eé]\s*[:=]\s*|qt[eé]\s*[:=]\s*)(\d+)\b|\b(\d+)\s*(?:unit[eé]s?|pi[eè]ces?|pcs)\b', re.IGNORECASE)

class MicroRAG:
    """Service Micro-RAG ultra-léger et déterministe pour guider l'extraction."""

    @classmethod
    def get_context(cls, text: str) -> str:
        """
        Analyse le texte brut et génère un micro-contexte technique compact (<150 tokens)
        contenant uniquement les règles et définitions pertinentes pour ce luminaire.
        """
        text_lower = text.lower()
        active_rules: List[str] = []

        # 1. Vérification des termes du glossaire
        for term, explanation in GLOSSARY.items():
            pattern = rf'\b{re.escape(term)}\b'
            if re.search(pattern, text_lower):
                active_rules.append(explanation)
                if len(active_rules) >= 4:
                    break

        # 2. Détection des marques référencées dans le texte
        detected_brands = []
        for brand in KNOWN_BRANDS:
            if brand in text_lower:
                detected_brands.append(brand.upper())
        if detected_brands:
            active_rules.append(f"Marques potentielles détectées: {', '.join(detected_brands[:3])} (extraire Marque + Référence complète).")

        if not active_rules:
            return ""

        return "CONTEXTE MÉTIER ÉCLAIRAGE:\n" + "\n".join(f"- {r}" for r in active_rules)

    @classmethod
    def extract_deterministic_hints(cls, text: str) -> Dict[str, Any]:
        """
        Extrait instantanément les métriques évidentes par expressions régulières
        pour servir de point de comparaison ou de secours au SLM.
        """
        hints: Dict[str, Any] = {}

        # Puissance
        wm = RE_WATT.search(text)
        if wm:
            try:
                val = wm.group(1).replace(',', '.').replace(' ', '')
                hints["wattage"] = float(val)
            except Exception:
                pass

        # Flux lumineux
        lm = RE_LUMENS.search(text)
        if lm:
            try:
                val = lm.group(1).replace(',', '.').replace(' ', '')
                hints["delivered_lumens"] = int(float(val))
            except Exception:
                pass

        # CCT
        cct = RE_CCT.search(text)
        if cct:
            try:
                hints["cct_k"] = int(cct.group(1))
            except Exception:
                pass

        # CRI / IRC
        cri = RE_CRI.search(text)
        if cri:
            try:
                val = cri.group(1) or cri.group(2)
                hints["cri_min"] = int(val)
            except Exception:
                pass

        # IP
        ip = RE_IP.search(text)
        if ip:
            hints["ip_rating_min"] = str(int(ip.group(1)))

        # IK
        ik = RE_IK.search(text)
        if ik:
            hints["ik_rating_min"] = f"{int(ik.group(1)):02d}"

        # Quantité
        qty = RE_QTY.search(text)
        if qty:
            try:
                val = qty.group(1) or qty.group(2)
                hints["quantity"] = int(val)
            except Exception:
                pass

        return hints
