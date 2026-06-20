from sqlalchemy import Column, String, Integer, Float, Boolean, ForeignKey, JSON, DateTime, Text
from sqlalchemy.orm import relationship
from db.database import Base   
import uuid
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime

class Product(Base):
    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sku = Column(String, unique=True, index=True, nullable=False)
    manufacturer = Column(String)
    brand = Column(String)
    family = Column(String)
    
    # Classification
    category_product_family = Column(String) # e.g. downlight, panel
    category_mounting_type = Column(String) # e.g. recessed, surface
    
    # Photometric
    lumens = Column(Float)
    cct = Column(Integer)
    cri = Column(Integer)
    beam_angle = Column(Float, nullable=True)
    
    # Electrical
    voltage_range = Column(String) # e.g. 120-277V
    dimming_protocol = Column(String)
    thd = Column(Float, nullable=True)
    power_factor = Column(Float, nullable=True)
    efficacy = Column(Float, nullable=True) # lm/W
    
    # Mechanical
    cutout_in = Column(Float, nullable=True)
    ip_rating = Column(Integer) # e.g. 20, 65
    finish = Column(String, nullable=True)
    trim = Column(String, nullable=True)
    
    # Compliance & Controls
    certifications = Column(JSON, default=list) # e.g. ["UL", "DLC", "JA8"]
    controls_protocols = Column(JSON, default=list)
    
    # Commercial & Lifecycle
    lifecycle_status = Column(String, default="active") # active, superseded, discontinued
    tier = Column(Integer, default=2) # 1, 2, 3
    margin = Column(Float, default=0.20)
    supplier_stock = Column(Integer, default=100)
    lead_time_days = Column(Integer, default=7)


class Project(Base):
    __tablename__ = "projects"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    status = Column(String, default="draft")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    lines = relationship("ProjectLine", back_populates="project", cascade="all, delete-orphan")


class ProjectLine(Base):
    __tablename__ = "project_lines"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    mark = Column(String)
    quantity = Column(Integer, default=1)
    description = Column(Text)
    specified_sku = Column(String, nullable=True)
    
    # PRO (Project Requirement Object) fields mapped flatly or as JSON. Using JSON for flexibility in MVP.
    pro_json = Column(JSON, default=dict)
    
    status = Column(String, default="pending") # pending, matched, no_match, escalated, finalized
    confidence_overall = Column(String, default="extracted")
    fields_requiring_review = Column(JSON, default=list)
    thread_id = Column(String, nullable=True)
    
    project = relationship("Project", back_populates="lines")
    traces = relationship("DecisionTrace", back_populates="line", cascade="all, delete-orphan")


class DecisionTrace(Base):
    __tablename__ = "decision_traces"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    line_id = Column(UUID(as_uuid=True), ForeignKey("project_lines.id"), nullable=False)
    candidate_sku = Column(String, nullable=True)
    step = Column(String) # hard_filter, soft_scoring, overlay, compliance
    rule = Column(String, nullable=True)
    message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    line = relationship("ProjectLine", back_populates="traces")
