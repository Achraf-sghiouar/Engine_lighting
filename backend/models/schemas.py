from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class SourceRef(BaseModel):
    page: Optional[int] = None
    cell: Optional[str] = None
    bbox: Optional[list] = None

class ExtractedField(BaseModel):
    value: Any
    confidence: str = "extracted" # extracted, inferred, missing
    source_ref: Optional[SourceRef] = None

class RawLineItem(BaseModel):
    mark: Optional[ExtractedField] = None
    quantity: Optional[ExtractedField] = None
    description: Optional[ExtractedField] = None
    specified_sku: Optional[ExtractedField] = None
    raw_data: Dict[str, Any] = Field(default_factory=dict)

# PRO (Project Requirement Object)
class PRO(BaseModel):
    category: Optional[str] = None
    mechanical: Dict[str, Any] = Field(default_factory=dict) # e.g. {"mounting_type": "recessed", "cutout_in": {"value": 6.75}, "ip_rating_min": 20}
    electrical: Dict[str, Any] = Field(default_factory=dict) # e.g. {"voltage": "120-277V"}
    dimming_protocol: Optional[str] = None
    photometric: Dict[str, Any] = Field(default_factory=dict) # e.g. {"lumens_min": 1000, "cct": 3000, "cri_min": 80}
    compliance: Dict[str, bool] = Field(default_factory=dict) # e.g. {"UL": True, "DLC": True}
    commercial: Dict[str, Any] = Field(default_factory=dict) # e.g. {"required_install_date": "2026-07-01", "preferred_tiers": [1, 2]}
