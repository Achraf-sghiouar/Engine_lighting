import re
from models.schemas import RawLineItem, PRO
 
def build_pro(raw_item: RawLineItem) -> PRO:
    pro = PRO()
    desc = ""
    if raw_item.description and raw_item.description.value:
        desc = raw_item.description.value.lower()
        
    sku = ""
    if raw_item.specified_sku and raw_item.specified_sku.value:
        sku = raw_item.specified_sku.value.lower()
        
    combined_text = f"{desc} {sku}"
    
    # 1. Normalizing CCT
    cct_match = re.search(r'(2700|3000|3500|4000|5000)k?', combined_text)
    if cct_match:
        pro.photometric["cct"] = int(cct_match.group(1))
        
    # 2. Normalizing Voltage
    if "120-277" in combined_text or "mvolt" in combined_text:
        pro.electrical["voltage"] = "120-277V"
    elif "120v" in combined_text:
        pro.electrical["voltage"] = "120V"
    elif "277v" in combined_text:
        pro.electrical["voltage"] = "277V"
        
    # 3. Normalizing Dimming
    if "0-10" in combined_text or "0/10" in combined_text:
        pro.dimming_protocol = "0-10V"
        
    # 4. Normalizing Cutout
    cutout_match = re.search(r'([\d\.]+)\s*(in|inch|")', combined_text)
    if cutout_match:
        pro.mechanical["cutout_in"] = {"value": float(cutout_match.group(1))}
        
    # 5. Normalizing Compliance
    if "ul" in combined_text:
        pro.compliance["UL"] = True
    if "dlc" in combined_text:
        pro.compliance["DLC"] = True
    if "ja8" in combined_text:
        pro.compliance["JA8"] = True
        
    # Basic Category heuristic
    if "downlight" in combined_text or "recessed" in combined_text:
        pro.category = "downlight"
        pro.mechanical["mounting_type"] = "recessed"
    elif "panel" in combined_text or "troffer" in combined_text:
        pro.category = "panel"
    elif "highbay" in combined_text or "high bay" in combined_text:
        pro.category = "highbay"
        
    return pro
