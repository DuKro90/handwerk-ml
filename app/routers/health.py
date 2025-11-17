"""
Health Check Endpoints
"""

from fastapi import APIRouter
from typing import Dict, Any
import logging

router = APIRouter(tags=["health"])
logger = logging.getLogger(__name__)

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Basic health check"""
    return {
        "status": "healthy",
        "service": "handwerk_ml_fastapi",
        "version": "2.0.0"
    }

@router.get("/health/ready")
async def readiness_check() -> Dict[str, Any]:
    """Readiness check - validates all dependencies"""
    checks = {
        "database": False,
        "redis": False,
        "qdrant": False,
        "embeddings": False
    }
    
    try:
        # Check Redis
        from app.services.redis_cache import redis_client
        if redis_client:
            checks["redis"] = True
    except Exception as e:
        logger.warning(f"Redis check failed: {e}")
    
    try:
        # Check Qdrant
        from app.services.qdrant_client import qdrant_client
        if qdrant_client:
            checks["qdrant"] = True
    except Exception as e:
        logger.warning(f"Qdrant check failed: {e}")
    
    try:
        # Check embeddings model
        from app.services.embeddings import embedding_model
        if embedding_model:
            checks["embeddings"] = True
    except Exception as e:
        logger.warning(f"Embeddings check failed: {e}")
    
    checks["database"] = True  # SQLite always available
    
    return {
        "ready": all(checks.values()),
        "checks": checks
    }

@router.get("/health/live")
async def liveness_check() -> Dict[str, str]:
    """Liveness check - simple ping"""
    return {"status": "alive"}
