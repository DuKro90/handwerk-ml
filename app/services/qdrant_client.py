"""
Qdrant Vector Database Client
"""

import logging
from typing import Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

logger = logging.getLogger(__name__)

qdrant_client: Optional[QdrantClient] = None

async def init_qdrant():
    """Initialize Qdrant connection"""
    global qdrant_client
    
    from app.config import settings
    
    try:
        qdrant_client = QdrantClient(url=settings.QDRANT_URL)
        
        # Create collection if not exists
        try:
            qdrant_client.get_collection(settings.QDRANT_COLLECTION_NAME)
            logger.info(f"✓ Collection '{settings.QDRANT_COLLECTION_NAME}' exists")
        except Exception:
            logger.info(f"Creating collection '{settings.QDRANT_COLLECTION_NAME}'...")
            qdrant_client.create_collection(
                collection_name=settings.QDRANT_COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=settings.QDRANT_VECTOR_SIZE,
                    distance=Distance.COSINE
                ),
                optimizers_config={
                    "memmap_threshold": 20000,
                    "indexing_threshold": 20000,
                    "flush_interval_sec": 60,
                    "deleted_threshold": 0.2
                }
            )
            logger.info(f"✓ Collection '{settings.QDRANT_COLLECTION_NAME}' created")
            
        logger.info("✓ Qdrant initialized successfully")
        
    except Exception as e:
        logger.error(f"✗ Qdrant initialization failed: {e}")
        raise

async def close_qdrant():
    """Close Qdrant connection"""
    global qdrant_client
    if qdrant_client:
        try:
            # Qdrant client doesn't need explicit close
            logger.info("✓ Qdrant connection closed")
        except Exception as e:
            logger.error(f"Error closing Qdrant: {e}")
