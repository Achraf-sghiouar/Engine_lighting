from typing import List, Tuple
from models.domain import Product
from models.schemas import PRO
from datetime import datetime

def voltage_covers(product_range: str, pro_voltage: str) -> bool:
    if not pro_voltage:
        return True
    if not product_range:
        return False
    # Simplified check for MVP
    pr_lower = product_range.lower()
    pv_lower = pro_voltage.lower()
    if pv_lower in pr_lower:
        return True
    if "120-277" in pr_lower and (pv_lower == "120v" or pv_lower == "277v" or "mvolt" in pv_lower):
        return True
    return False

def ip_rank(ip: int) -> int:
    return ip if ip else 0

def apply_hard_filters(candidates: List[Product], pro: PRO) -> Tuple[List[Product], List[dict]]:
    """
    Applies the 11 hard constraint rules.
    Returns (filtered_candidates, decision_traces)
    """
    filtered = []
    traces = []
    
    for c in candidates:
        rejection_reason = None
        
        # 1. Discontinued
        if c.lifecycle_status == "discontinued":
            rejection_reason = "Product is discontinued"
            
        # 2. Category
        elif pro.category and c.category_product_family and pro.category.lower() not in c.category_product_family.lower():
            rejection_reason = f"Category mismatch: {c.category_product_family} != {pro.category}"
            
        # 3. Mounting
        elif "mounting_type" in pro.mechanical and c.category_mounting_type and pro.mechanical["mounting_type"].lower() not in c.category_mounting_type.lower():
            rejection_reason = f"Mounting mismatch: {c.category_mounting_type} != {pro.mechanical['mounting_type']}"
            
        # 4. Voltage
        elif "voltage" in pro.electrical and not voltage_covers(c.voltage_range, pro.electrical["voltage"]):
            rejection_reason = f"Voltage not covered: {c.voltage_range} != {pro.electrical['voltage']}"
            
        # 5. Certifications
        elif pro.compliance:
            for cert, req in pro.compliance.items():
                if req and cert not in (c.certifications or []):
                    rejection_reason = f"Missing required certification: {cert}"
                    break
                    
        # 6. IP Rating
        elif "ip_rating_min" in pro.mechanical and ip_rank(c.ip_rating) < ip_rank(pro.mechanical["ip_rating_min"]):
            rejection_reason = f"Insufficient IP rating: {c.ip_rating} < {pro.mechanical['ip_rating_min']}"
            
        # 7. Cutout Tolerance
        elif "cutout_in" in pro.mechanical and c.cutout_in is not None:
            if abs(c.cutout_in - pro.mechanical["cutout_in"]["value"]) > 0.25:
                rejection_reason = f"Cutout out of tolerance: {c.cutout_in} != {pro.mechanical['cutout_in']['value']}"
                
        # 8. Dimming
        elif pro.dimming_protocol and c.dimming_protocol and pro.dimming_protocol.lower() not in c.dimming_protocol.lower():
             rejection_reason = f"Dimming mismatch: {c.dimming_protocol} != {pro.dimming_protocol}"
             
        # 9. Lead Time
        elif "required_install_date" in pro.commercial:
            install_date = datetime.fromisoformat(pro.commercial["required_install_date"].replace("Z", "+00:00")).date()
            days_until = (install_date - datetime.today().date()).days
            if c.lead_time_days > days_until:
                rejection_reason = f"Lead time {c.lead_time_days} exceeds limit {days_until}"
                
        # 10. Tier Policy
        elif "preferred_tiers" in pro.commercial and c.tier not in pro.commercial["preferred_tiers"]:
             rejection_reason = f"Tier {c.tier} not allowed"
             
        # 11. Stock
        elif pro.commercial.get("strategy") == "in_stock_only" and c.supplier_stock <= 0:
             rejection_reason = "Out of stock"
             
             
        if rejection_reason:
            traces.append({
                "candidate_sku": c.sku,
                "step": "hard_filter",
                "message": rejection_reason
            })
        else:
            filtered.append(c)
            
    return filtered, traces
