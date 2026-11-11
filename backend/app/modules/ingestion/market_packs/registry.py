from typing import Dict, Optional
from .base import MarketPack
from .morocco import MOROCCO_PACK

# Registre central des Market Packs disponibles
REGISTRY: Dict[str, MarketPack] = {
    "MA": MOROCCO_PACK,
}

DEFAULT_PACK = MOROCCO_PACK


def get_market_pack(code: Optional[str] = None) -> MarketPack:
    """Retourne le Market Pack correspondant au code ou le pack par défaut."""
    if not code:
        return DEFAULT_PACK
    return REGISTRY.get(code.upper(), DEFAULT_PACK)


def detect_market_pack(document_text: str) -> MarketPack:
    """
    Détection heuristique du pack de marché le plus adapté à partir du contenu d'un document.
    """
    text_lower = document_text.lower()
    
    # Heuristique Maroc (termes CCAG-T, CPS, Dirham, NM)
    if any(k in text_lower for k in ["ccag-t", "royaume du maroc", "dirhams", "cps", "lustrerie"]):
        return MOROCCO_PACK
        
    return DEFAULT_PACK
