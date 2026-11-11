import re

def to_tolerance(value: float, default_pct: float = 10.0) -> dict:
    if value is None: return None
    return {"value": float(value), "tolerance_pct": float(default_pct)}

def normalize_cct(value):
    if not value:
        return None
    val = None
    if isinstance(value, (int, float)):
        val = int(value)
    else:
        match = re.search(r"(\d+)\s*[Kk]", str(value))
        if match:
            val = int(match.group(1))
        elif "warm white" in str(value).lower():
            val = 2700
    if val:
        return {"value": val, "tolerance_pct": 150} # For CCT, tolerance is 150K
    return None

def normalize_ip(value):
    if not value:
        return None
    match = re.search(r"IP(\d{2})", str(value), re.IGNORECASE)
    return f"IP{match.group(1)}" if match else None

def normalize_voltage(value):
    if not value: return None
    val_lower = str(value).lower()
    if "mvolt" in val_lower or "120/277" in val_lower or "120-277" in val_lower:
        return "120-277V"
    if "347" in val_lower:
        return "347V"
    if "120" in val_lower:
        return "120V"
    return str(value)

def normalize_dimming(value):
    if not value: return None
    val_lower = str(value).lower()
    if "0-10" in val_lower:
        return "0-10V"
    if "dali" in val_lower:
        return "DALI"
    if "phase" in val_lower or "triac" in val_lower:
        return "Phase"
    return str(value)
