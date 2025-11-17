"""
SQLAlchemy ORM Models - Maps to Django models via SQLite
"""

import uuid
from datetime import datetime, date
from sqlalchemy import Column, String, Integer, Float, DateTime, Date, Boolean, JSON, ForeignKey, Index, UniqueConstraint, DECIMAL
from sqlalchemy.dialects.sqlite import UUID
from sqlalchemy.orm import relationship
from app.database import Base

# ============================================
# PROJECT MODEL
# ============================================
class Project(Base):
    __tablename__ = "calculator_project"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(String(10000), nullable=True)
    project_type = Column(String(100), nullable=False)
    region = Column(String(50), nullable=True)
    total_area_sqm = Column(DECIMAL(10, 2), nullable=True)
    wood_type = Column(String(50), nullable=True)
    complexity = Column(Integer, nullable=False)
    final_price = Column(DECIMAL(10, 2), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    project_date = Column(Date, nullable=False)
    description_embedding = Column(JSON, nullable=True)
    is_finalized = Column(Boolean, default=False)
    finalized_at = Column(DateTime, nullable=True)
    
    # Relationships
    materials = relationship("ProjectMaterial", back_populates="project", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_wood_type_project_type', 'wood_type', 'project_type'),
        Index('idx_project_date', 'project_date'),
        Index('idx_is_finalized', 'is_finalized'),
    )

# ============================================
# MATERIAL MODEL
# ============================================
class Material(Base):
    __tablename__ = "calculator_material"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)
    unit = Column(String(20), nullable=False)
    datanorm_id = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    prices = relationship("MaterialPrice", back_populates="material", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_category', 'category'),
        Index('idx_datanorm_id', 'datanorm_id'),
    )

# ============================================
# MATERIAL PRICE MODEL
# ============================================
class MaterialPrice(Base):
    __tablename__ = "calculator_materialprice"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    material_id = Column(UUID(as_uuid=True), ForeignKey('calculator_material.id'), nullable=False)
    price = Column(DECIMAL(10, 2), nullable=False)
    region = Column(String(50), nullable=False)
    valid_from = Column(Date, nullable=False)
    valid_to = Column(Date, nullable=True)
    recorded_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    material = relationship("Material", back_populates="prices")
    
    __table_args__ = (
        Index('idx_material_recorded', 'material_id', 'recorded_at'),
        Index('idx_valid_dates', 'valid_from', 'valid_to'),
    )

# ============================================
# PROJECT MATERIAL MODEL
# ============================================
class ProjectMaterial(Base):
    __tablename__ = "calculator_projectmaterial"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey('calculator_project.id'), nullable=False)
    material_id = Column(UUID(as_uuid=True), ForeignKey('calculator_material.id'), nullable=False)
    quantity = Column(DECIMAL(10, 2), nullable=False)
    unit_price = Column(DECIMAL(10, 2), nullable=False)
    total_cost = Column(DECIMAL(10, 2), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="materials")
    material = relationship("Material")
    
    __table_args__ = (
        UniqueConstraint('project_id', 'material_id', name='uq_project_material'),
    )

# ============================================
# PRICE PREDICTION MODEL
# ============================================
class PricePrediction(Base):
    __tablename__ = "calculator_priceprediction"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime, default=datetime.utcnow)
    project_features = Column(JSON, nullable=False)
    predicted_price = Column(DECIMAL(10, 2), nullable=False)
    confidence_score = Column(Float, nullable=False)
    similar_projects_count = Column(Integer, nullable=False)
    model_version = Column(String(50), nullable=False)
    actual_price = Column(DECIMAL(10, 2), nullable=True)
    was_accepted = Column(Boolean, nullable=True)
    user_modified_price = Column(DECIMAL(10, 2), nullable=True)
    prediction_error = Column(Float, nullable=True)
    
    __table_args__ = (
        Index('idx_timestamp', 'timestamp'),
        Index('idx_model_version', 'model_version'),
    )

# ============================================
# SETTINGS MODEL
# ============================================
class Settings(Base):
    __tablename__ = "calculator_settings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    labor_rate_per_hour = Column(DECIMAL(6, 2), default=50.00)
    material_markup_percentage = Column(Float, default=30.0)
    overhead_percentage = Column(Float, default=15.0)
    profit_margin_percentage = Column(Float, default=25.0)
    polster_fabric_base_price = Column(DECIMAL(6, 2), default=25.00)
    polster_labor_rate = Column(DECIMAL(6, 2), default=65.00)
    foam_types = Column(JSON, nullable=True)
    seam_extras = Column(JSON, nullable=True)
    antirutsch_price = Column(DECIMAL(6, 2), nullable=True)
    zipper_price = Column(DECIMAL(6, 2), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# ============================================
# DOCUMENT MODEL
# ============================================
class Document(Base):
    __tablename__ = "calculator_document"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(20), nullable=False)
    file_path = Column(String(500), nullable=False)
    text_content = Column(String(50000), nullable=True)
    embedding = Column(JSON, nullable=True)
    page_count = Column(Integer, nullable=True)
    extracted_features = Column(JSON, nullable=True)
    similar_projects = Column(JSON, nullable=True)
    searchable_text = Column(String(10000), nullable=True)
    status = Column(String(20), default='pending')  # pending, processing, completed, failed
    project_id = Column(UUID(as_uuid=True), ForeignKey('calculator_project.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_processed = Column(DateTime, nullable=True)
    
    __table_args__ = (
        Index('idx_file_type', 'file_type'),
        Index('idx_status', 'status'),
        Index('idx_project_id', 'project_id'),
        Index('idx_created_at', 'created_at'),
    )
