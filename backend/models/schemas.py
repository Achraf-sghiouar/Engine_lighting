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

class ValueTolerance(BaseModel):
    value: float
    tolerance_pct: float = 10.0

class MechanicalPRO(BaseModel):
    mounting_type: Optional[str] = None
    cutout_in: Optional[ValueTolerance] = None
    ip_rating_min: Optional[str] = None
    ik_rating_min: Optional[str] = None

class ElectricalPRO(BaseModel):
    voltage: Optional[str] = None
    dimming_protocol: Optional[str] = None
    wattage: Optional[float] = None

class PhotometricPRO(BaseModel):
    lumens_min: Optional[ValueTolerance] = None
    cct: Optional[ValueTolerance] = None
    cri_min: Optional[int] = None
    beam_angle_deg: Optional[float] = None

class CompliancePRO(BaseModel):
    ce_required: Optional[bool] = None
    enec_required: Optional[bool] = None
    ul_etl: Optional[bool] = None
    dlc: Optional[bool] = None
    title_24_ja8: Optional[bool] = None

class CommercialPRO(BaseModel):
    preferred_tiers: Optional[List[str]] = None
    allow_value_tier: Optional[bool] = None
    required_install_date: Optional[str] = None
    strategy: Optional[str] = None
    quantity: Optional[int] = 1

class PRO(BaseModel):
    pro_id: Optional[str] = None
    category: Optional[str] = None
    mechanical: MechanicalPRO = Field(default_factory=MechanicalPRO)
    electrical: ElectricalPRO = Field(default_factory=ElectricalPRO)
    dimming_protocol: Optional[str] = None
    photometric: PhotometricPRO = Field(default_factory=PhotometricPRO)
    compliance: CompliancePRO = Field(default_factory=CompliancePRO)
    commercial: CommercialPRO = Field(default_factory=CommercialPRO)
    confidence: str = "extracted"
    tenant_id: str = "default_tenant"

class ExtractedItem(BaseModel):
    Rep: str
    Designation: str
    Marque_Model_Ref: Optional[str] = None
    Dimensions: Optional[str] = None
    Flux_Lm: Optional[str] = None
    P_W: Optional[str] = None
    CCT_K: Optional[str] = None
    LifeSpan_H: Optional[str] = None
    IP: Optional[str] = None
    IK: Optional[str] = None
    Quantite: Optional[str] = None
    Unite: Optional[str] = None
    Texte_Source: str
