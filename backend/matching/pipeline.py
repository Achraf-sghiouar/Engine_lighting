from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models.domain import Product
from matching.canonical import cpc_to_canonical, product_to_canonical
from matching.hard_filter import passe_hard_filter
from matching.soft_scoring import score_candidat

# Cache global pour éviter de recharger 6000 produits à chaque luminaire
_PRODUCTS_CACHE = None

async def charger_tous_les_produits(db: AsyncSession) -> List[Product]:
    global _PRODUCTS_CACHE
    if _PRODUCTS_CACHE is None:
        result = await db.execute(select(Product))
        _PRODUCTS_CACHE = result.scalars().all()
    return _PRODUCTS_CACHE

def matcher_luminaire(demande_pro_json: dict, tous_les_produits: List[Product]) -> List[Dict[str, Any]]:
    """Pour un luminaire CPC, retourne les meilleurs produits substituables."""
    demande = cpc_to_canonical(demande_pro_json)

    candidats = []
    for produit_raw in tous_les_produits:
        produit = product_to_canonical(produit_raw)
        
        # 1. Hard filter
        passe, raison = passe_hard_filter(demande, produit)
        if not passe:
            continue
            
        # 2. Soft scoring
        score = score_candidat(demande, produit)
        candidats.append({
            "product": produit_raw,
            "tech_score": score,
            "score": score,
        })

    # 3. Classer par score décroissant
    candidats.sort(key=lambda x: x["score"], reverse=True)
    return candidats[:5]  # top 5 substituts
