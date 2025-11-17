"""
HandwerkML FastAPI Application
High-performance ML system for German woodworking price estimation
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest

from app.config import settings, validate_security_on_startup
from app.routers import projects, materials, settings as settings_router, predictions, documents, similarity, health, celery_tasks

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================
# PROMETHEUS METRICS
# ============================================
REQUEST_COUNT = Counter(
    'handwerk_ml_request_total',
    'Total requests',
    labelnames=['method', 'endpoint', 'status']
)

REQUEST_DURATION = Histogram(
    'handwerk_ml_request_duration_seconds',
    'Request latency (seconds)',
    labelnames=['method', 'endpoint'],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0)
)

REQUEST_ERRORS = Counter(
    'handwerk_ml_request_errors_total',
    'Total request errors',
    labelnames=['method', 'endpoint', 'error_type']
)

ACTIVE_REQUESTS = Counter(
    'handwerk_ml_active_requests',
    'Active requests',
    labelnames=['method', 'endpoint']
)

# ============================================
# LIFESPAN MANAGEMENT
# ============================================
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application startup and shutdown events"""
    logger.info("🚀 HandwerkML FastAPI starting...")

    # Startup
    try:
        # Validate security settings
        validate_security_on_startup()
        logger.info("✓ Security validation passed")

        # Initialize Qdrant connection
        from app.services.qdrant_client import init_qdrant
        await init_qdrant()
        logger.info("✓ Qdrant connected")
        
        # Initialize Redis connection
        from app.services.redis_cache import init_redis
        await init_redis()
        logger.info("✓ Redis connected")
        
        logger.info("✓ All services initialized")
    except Exception as e:
        logger.error(f"✗ Startup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("🛑 HandwerkML FastAPI shutting down...")
    try:
        from app.services.redis_cache import close_redis
        await close_redis()
        logger.info("✓ Redis closed")
    except Exception as e:
        logger.error(f"⚠ Shutdown error: {e}")

# ============================================
# FASTAPI INITIALIZATION
# ============================================
app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION,
    lifespan=lifespan
)

# ============================================
# MIDDLEWARE
# ============================================
# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# Metrics middleware
@app.middleware("http")
async def add_metrics(request: Request, call_next):
    """Collect Prometheus metrics for all requests"""
    endpoint = f"{request.method} {request.url.path}"
    
    ACTIVE_REQUESTS.labels(
        method=request.method,
        endpoint=request.url.path
    ).inc()
    
    import time
    start_time = time.time()
    
    try:
        response = await call_next(request)
        duration = time.time() - start_time
        
        REQUEST_DURATION.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(duration)
        
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()
        
        logger.debug(f"{endpoint} - {response.status_code} ({duration:.3f}s)")
        return response
        
    except Exception as e:
        duration = time.time() - start_time
        REQUEST_ERRORS.labels(
            method=request.method,
            endpoint=request.url.path,
            error_type=type(e).__name__
        ).inc()
        
        logger.error(f"{endpoint} - Error: {e} ({duration:.3f}s)")
        
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )
    finally:
        ACTIVE_REQUESTS.labels(
            method=request.method,
            endpoint=request.url.path
        ).dec()

# ============================================
# ROUTES
# ============================================
# Health check
app.include_router(health.router)

# API routes
app.include_router(projects.router, prefix="/api/v1/projects", tags=["projects"])
app.include_router(materials.router, prefix="/api/v1/materials", tags=["materials"])
app.include_router(settings_router.router, prefix="/api/v1/settings", tags=["settings"])
app.include_router(predictions.router, prefix="/api/v1/predictions", tags=["predictions"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["documents"])
app.include_router(similarity.router, prefix="/api/v1/similarity", tags=["similarity"])
app.include_router(celery_tasks.router, prefix="/api/v1/tasks", tags=["tasks"])

# ============================================
# METRICS ENDPOINT
# ============================================
@app.get("/metrics", include_in_schema=False)
async def metrics():
    """Prometheus metrics endpoint"""
    return generate_latest()

# ============================================
# ROOT ENDPOINT
# ============================================
@app.get("/")
async def root():
    """API information"""
    return {
        "application": settings.API_TITLE,
        "version": settings.API_VERSION,
        "description": settings.API_DESCRIPTION,
        "docs": "/docs",
        "health": "/health",
        "metrics": "/metrics"
    }

# ============================================
# ERROR HANDLERS
# ============================================
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle validation errors"""
    logger.warning(f"Validation error: {exc}")
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )  # ✓ Fixed: now correctly uses settings from app.config
