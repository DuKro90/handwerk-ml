"""
Request/Response Schemas
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum

# ============================================
# Project Models
# ============================================

class ProjectType(str, Enum):
    """Project type enumeration"""
    TREPPENBAU = "Treppenbau"
    MÖBEL = "Möbel"
    KÜCHENEINRICHTUNG = "Kücheneinrichtung"
    SPEZIALBAU = "Spezialbau"
    DACHSTUHL = "Dachstuhl"
    POLSTEREI = "Polsterei"

class WoodType(str, Enum):
    """Wood type enumeration"""
    EICHE = "Eiche"
    NUSSBAUM = "Nussbaum"
    KIEFER = "Kiefer"
    ESCHE = "Esche"
    FICHTE = "Fichte"
    BUCHE = "Buche"

class ProjectBase(BaseModel):
    """Base project data"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    project_type: ProjectType
    region: Optional[str] = None
    total_area_sqm: Optional[float] = Field(None, ge=0)
    wood_type: Optional[WoodType] = None
    complexity: Optional[int] = Field(None, ge=1, le=5)
    final_price: Optional[float] = Field(None, ge=0)

class ProjectCreate(ProjectBase):
    """Create project request"""
    pass

class ProjectUpdate(BaseModel):
    """Update project request"""
    name: Optional[str] = None
    description: Optional[str] = None
    final_price: Optional[float] = None

class ProjectResponse(ProjectBase):
    """Project response"""
    id: str
    created_at: datetime
    project_date: str
    is_finalized: bool = False
    finalized_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# ============================================
# Material Models
# ============================================

class MaterialBase(BaseModel):
    """Base material data"""
    name: str = Field(..., min_length=1, max_length=255)
    category: str = Field(..., min_length=1, max_length=100)
    unit: str = Field(..., min_length=1, max_length=20)
    datanorm_id: Optional[str] = None

class MaterialCreate(MaterialBase):
    """Create material request"""
    pass

class MaterialUpdate(BaseModel):
    """Update material request"""
    name: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None
    datanorm_id: Optional[str] = None

class MaterialResponse(MaterialBase):
    """Material response"""
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ============================================
# Settings Models
# ============================================

class SettingsBase(BaseModel):
    """Base settings data"""
    labor_rate_per_hour: float = 50.00
    material_markup_percentage: float = 30.0
    overhead_percentage: float = 15.0
    profit_margin_percentage: float = 25.0
    polster_fabric_base_price: float = 25.00
    polster_labor_rate: float = 65.00

class SettingsUpdate(BaseModel):
    """Update settings request"""
    labor_rate_per_hour: Optional[float] = None
    material_markup_percentage: Optional[float] = None
    overhead_percentage: Optional[float] = None
    profit_margin_percentage: Optional[float] = None
    polster_fabric_base_price: Optional[float] = None
    polster_labor_rate: Optional[float] = None

class SettingsResponse(SettingsBase):
    """Settings response"""
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ============================================
# Prediction Models
# ============================================

class PredictionRequest(BaseModel):
    """Price prediction request"""
    project_id: Optional[str] = None
    description: Optional[str] = None
    total_area_sqm: float = Field(..., ge=0)
    complexity: int = Field(..., ge=1, le=5)
    project_type: ProjectType
    wood_type: WoodType
    region: Optional[str] = None

class PredictionResponse(BaseModel):
    """Price prediction response"""
    predicted_price: float
    confidence_score: float = Field(..., ge=0, le=1)
    confidence_level: str  # "Very High", "High", "Medium", "Low", "Very Low"
    similar_projects_count: int
    model_version: str
    timestamp: datetime

# ============================================
# Document Models
# ============================================

class DocumentResponse(BaseModel):
    """Document response"""
    id: str
    filename: str
    file_type: str
    page_count: Optional[int] = None
    created_at: datetime
    processing_status: str  # pending, processing, completed, failed
    extracted_text_preview: Optional[str] = None

# ============================================
# Similarity Search Models
# ============================================

class SimilarProject(BaseModel):
    """Similar project result"""
    id: str
    name: str
    project_type: str
    similarity_score: float = Field(..., ge=0, le=1)
    final_price: Optional[float] = None

class SimilaritySearchResponse(BaseModel):
    """Similarity search response"""
    query: str
    results: List[SimilarProject]
    total_count: int
    search_time_ms: float

# ============================================
# Health Check Models
# ============================================

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    service: str
    version: str

class ReadinessResponse(BaseModel):
    """Readiness check response"""
    ready: bool
    checks: dict
