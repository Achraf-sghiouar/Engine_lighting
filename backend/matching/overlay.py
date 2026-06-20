import json
from typing import List, Dict, Any
from models.schemas import PRO
from db.cache import redis_client

async def apply_overlay(scored_candidates: List[Dict[str, Any]], pro: PRO) -> List[Dict[str, Any]]:
    # Batch fetch from Redis for all candidates
    skus = [item["product"].sku for item in scored_candidates]
    if skus:
        redis_keys = [f"product_erp:{sku}" for sku in skus]
        erp_data_raw = await redis_client.mget(redis_keys)
    else:
        erp_data_raw = []

    erp_map = {}
    for sku, raw in zip(skus, erp_data_raw):
        if raw:
            erp_map[sku] = json.loads(raw)
        else:
            # Fallback if not in cache
            erp_map[sku] = {"stock": 0, "margin": 0.20}

    for item in scored_candidates:
        c = item["product"]
        tech_score = item["tech_score"]
        erp_info = erp_map.get(c.sku, {})
        
        c_margin = erp_info.get("margin", c.margin)
        c_stock = erp_info.get("stock", c.supplier_stock)
        
        # 1. Tier Multiplier
        tier_multi = 1.0
        preferred_tiers = pro.commercial.get("preferred_tiers", [2])
        if preferred_tiers and c.tier not in preferred_tiers:
             diff = abs(c.tier - preferred_tiers[0])
             if diff == 1: tier_multi = 0.92
             elif diff >= 2: tier_multi = 0.80
             
        # 2. Margin Multiplier
        target_margin = pro.commercial.get("target_margin", 0.20)
        margin_multi = 1.0
        if c_margin > target_margin + 0.05: margin_multi = 1.05
        elif c_margin < target_margin - 0.05: margin_multi = 0.90
        
        # Stock penalty
        stock_penalty = 0
        req_qty = pro.commercial.get("quantity", 1)
        if c_stock < req_qty:
            stock_penalty = (1 - (max(0, c_stock) / req_qty)) * 8
            
        final_score = max(0, tech_score * (tier_multi * margin_multi) - stock_penalty)
        item["final_score"] = final_score
        
        # Risk flags
        risk_flags = []
        if c_stock < req_qty:
             risk_flags.append(f"Partial stock ({c_stock}/{req_qty})")
        if c_margin < target_margin:
             risk_flags.append("Below target margin")
             
        item["risk_flags"] = risk_flags
        
    scored_candidates.sort(key=lambda x: x["final_score"], reverse=True)
    return scored_candidates
