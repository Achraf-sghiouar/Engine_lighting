import asyncio
from db.database import AsyncSessionLocal
from matching.pipeline import charger_tous_les_produits, matcher_luminaire
from matching.overlay import apply_overlay
from models.schemas import PRO

async def main():
    async with AsyncSessionLocal() as db:
        produits = await charger_tous_les_produits(db)
        print(f"Chargé {len(produits)} produits de la BDD.")
        
    demande = {
        "product_family": "panel",
        "photometric": {"delivered_lumens": 3685, "cct_k": 3000, "cri_min": 80},
        "electrical": {"wattage": 26},
        "mechanical": {"ip_rating_min": None},
        "commercial": {"quantity": 10}
    }
    
    print("\n--- Matching ---")
    candidats = matcher_luminaire(demande, produits)
    print(f"Trouvé {len(candidats)} candidats valides.")
    
    # Simulate pro object
    pro_obj = PRO(**demande)
    
    # Overlay
    final = await apply_overlay(candidats, pro_obj)
    
    for c in final[:5]:
        p = c["product"]
        print(f"Score: {c['final_score']:.1f}% (Tech: {c['tech_score']:.1f}%) | {p.brand} {p.family} | {p.lumens}lm / {c['product'].efficacy}lm/W / {p.ip_rating}IP | IK: {p.ik_rating} | Tiers: {p.tier}")

if __name__ == "__main__":
    asyncio.run(main())
