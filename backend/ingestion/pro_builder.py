import re
from models.schemas import RawLineItem, PRO, ValueTolerance
from app.modules.ingestion.document_intelligence.normalizer import to_tolerance

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
        pro.photometric.cct = to_tolerance(int(cct_match.group(1)), 150)
        
    # 2. Normalizing Voltage
    if "120-277" in combined_text or "mvolt" in combined_text:
        pro.electrical.voltage = "120-277V"
    elif "120v" in combined_text:
        pro.electrical.voltage = "120V"
    elif "277v" in combined_text:
        pro.electrical.voltage = "277V"
        
    # 3. Normalizing Dimming
    if "0-10" in combined_text or "0/10" in combined_text:
        pro.electrical.dimming_protocol = "0-10V"
        
    # 4. Extract Wattage
    watt_match = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:w|watts?)\b', combined_text)
    if watt_match:
        pro.electrical.wattage = float(watt_match.group(1).replace(',', '.'))
        
    # 5. Extract Lumens
    lumen_match = re.search(r'(\d+(?:[.,\s]\d+)?)\s*(?:lm|lumens?)\b', combined_text)
    if lumen_match:
        val = float(lumen_match.group(1).replace(' ', '').replace(',', ''))
        pro.photometric.lumens_min = to_tolerance(val, 10.0)

    # 6. Extract IP and IK
    ip_match = re.search(r'ip\s*(\d{2})', combined_text)
    if ip_match:
        pro.mechanical.ip_rating_min = f"IP{ip_match.group(1)}"
        
    ik_match = re.search(r'ik\s*(\d{2})', combined_text)
    if ik_match:
        pro.mechanical.ik_rating_min = f"IK{ik_match.group(1)}"

    # 7. Extract CRI
    cri_match = re.search(r'(?:cri|ra|irc)\s*(?:>|=)?\s*(\d{2})', combined_text)
    if cri_match:
        pro.photometric.cri_min = int(cri_match.group(1))
        
    # 8. Normalizing Cutout
    cutout_match = re.search(r'([\d\.]+)\s*(in|inch|")', combined_text)
    if cutout_match:
        pro.mechanical.cutout_in = to_tolerance(float(cutout_match.group(1)), 0.25)
        
    # 9. Normalizing Compliance
    if "ul" in combined_text:
        pro.compliance.ul_etl = True
    if "dlc" in combined_text:
        pro.compliance.dlc = True
    if "ja8" in combined_text:
        pro.compliance.title_24_ja8 = True
    if "ce " in combined_text or "ce," in combined_text:
        pro.compliance.ce_required = True
        
    # Basic Category heuristic
    if "downlight" in combined_text or "recessed" in combined_text:
        pro.category = "downlight"
        pro.mechanical.mounting_type = "recessed"
    elif "panel" in combined_text or "troffer" in combined_text:
        pro.category = "panel"
    elif "highbay" in combined_text or "high bay" in combined_text:
        pro.category = "highbay"
        
    return pro
