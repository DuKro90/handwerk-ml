"""
FastAPI Configuration
"""

from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """Application settings from environment variables"""

    # API
    API_TITLE: str = "HandwerkML API"
    API_DESCRIPTION: str = "High-performance ML system for German woodworking price estimation"
    API_VERSION: str = "2.0.0"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # Security (⚠️  Must be set in environment for production)
    SECRET_KEY: str = "dev-secret-key-minimum-32-characters-required-for-production-use"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 24
    REQUIRE_HTTPS: bool = False  # Set to True in production
    CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:3001"]
    
    # Database
    DATABASE_URL: str = "sqlite:///./db.sqlite3"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PASSWORD: Optional[str] = None
    
    # Qdrant
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_COLLECTION_NAME: str = "projects"
    QDRANT_VECTOR_SIZE: int = 768
    QDRANT_DISTANCE_METRIC: str = "Cosine"
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    # ML
    MODEL_PATH: str = "./models/xgboost_model.pkl"

    # Embedding Model Configuration
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"  # Current: 384D
    EMBEDDING_MODEL_NEXT: str = "T-Systems-onsite/cross-en-de-roberta-sentence-transformers"  # Upgrade: 768D
    EMBEDDING_DIMENSION: int = 384
    EMBEDDING_DIMENSION_NEXT: int = 768

    # Collection versioning
    QDRANT_COLLECTION_CURRENT: str = "projects_384d"  # Current collection
    QDRANT_COLLECTION_NEXT: str = "projects_768d"    # Upgrade target
    EMBEDDING_CACHE_TTL: int = 86400  # 24 hours
    
    # Document Processing
    MAX_UPLOAD_SIZE: int = 52428800  # 50MB
    SUPPORTED_FILE_TYPES: str = "pdf,docx,doc,jpg,jpeg,png,txt"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()

# Validate security settings on startup
def validate_security_on_startup():
    """Validate security configuration"""
    import logging
    logger = logging.getLogger(__name__)

    # Check SECRET_KEY length
    if len(settings.SECRET_KEY) < 32:
        logger.warning(
            f"⚠️  WARNING: SECRET_KEY is too short ({len(settings.SECRET_KEY)} chars). "
            "Minimum 32 characters required. Using development key."
        )

    # Check for development defaults
    if "dev-secret-key" in settings.SECRET_KEY.lower() and settings.ENVIRONMENT == "production":
        logger.error(
            "🛑 ERROR: Using development SECRET_KEY in production! "
            "Set SECRET_KEY environment variable to a secure random value."
        )
        raise ValueError("SECRET_KEY not properly configured for production")

    # Check HTTPS in production
    if settings.ENVIRONMENT == "production" and not settings.REQUIRE_HTTPS:
        logger.warning("⚠️  WARNING: HTTPS not enforced in production. Set REQUIRE_HTTPS=true")

    # Check database for production
    if settings.ENVIRONMENT == "production" and "sqlite" in settings.DATABASE_URL.lower():
        logger.warning("⚠️  WARNING: Using SQLite in production. Use PostgreSQL for better concurrency.")

    logger.info(f"✓ Security validation passed (Environment: {settings.ENVIRONMENT})")
