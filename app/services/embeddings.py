"""
Embeddings Service with Qdrant Integration
Supports multiple embedding models (384D, 768D)
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
import numpy as np

logger = logging.getLogger(__name__)

embedding_model = None
embedding_model_768d = None  # For migration to 768D embeddings

async def init_embeddings():
    """Initialize embedding model"""
    global embedding_model

    from app.config import settings

    try:
        from sentence_transformers import SentenceTransformer

        logger.info(f"Loading embeddings model: {settings.EMBEDDING_MODEL}")
        embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
        logger.info("✓ Embeddings model loaded")

    except Exception as e:
        logger.error(f"✗ Failed to load embeddings model: {e}")
        raise

async def embed_text(text: str) -> List[float]:
    """Generate embedding for text"""
    if not embedding_model:
        await init_embeddings()

    if not text or not text.strip():
        return [0.0] * 384  # Default embedding dimension

    try:
        embedding = embedding_model.encode(text)
        return embedding.tolist()
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        return [0.0] * 384

async def embed_texts_batch(texts: List[str]) -> List[List[float]]:
    """Generate embeddings for multiple texts"""
    if not embedding_model:
        await init_embeddings()

    try:
        embeddings = embedding_model.encode(texts, show_progress_bar=False)
        return [emb.tolist() for emb in embeddings]
    except Exception as e:
        logger.error(f"Batch embedding generation failed: {e}")
        return [[0.0] * 384 for _ in texts]

# ============================================
# 768D EMBEDDINGS (German-Optimized Upgrade)
# ============================================

async def init_embeddings_768d():
    """Initialize 768D German-optimized embedding model"""
    global embedding_model_768d

    from app.config import settings

    try:
        from sentence_transformers import SentenceTransformer

        logger.info(f"Loading 768D embeddings model: {settings.EMBEDDING_MODEL_NEXT}")
        embedding_model_768d = SentenceTransformer(settings.EMBEDDING_MODEL_NEXT)
        logger.info("✓ 768D embeddings model loaded (German-optimized)")

    except Exception as e:
        logger.error(f"✗ Failed to load 768D embeddings model: {e}")
        raise

async def embed_text_768d(text: str) -> List[float]:
    """Generate 768D embedding for text"""
    if not embedding_model_768d:
        await init_embeddings_768d()

    if not text or not text.strip():
        return [0.0] * 768

    try:
        embedding = embedding_model_768d.encode(text)
        return embedding.tolist()
    except Exception as e:
        logger.error(f"768D embedding generation failed: {e}")
        return [0.0] * 768

async def embed_texts_batch_768d(texts: List[str]) -> List[List[float]]:
    """Generate 768D embeddings for multiple texts"""
    if not embedding_model_768d:
        await init_embeddings_768d()

    try:
        embeddings = embedding_model_768d.encode(texts, show_progress_bar=False)
        return [emb.tolist() for emb in embeddings]
    except Exception as e:
        logger.error(f"Batch 768D embedding generation failed: {e}")
        return [[0.0] * 768 for _ in texts]

async def compare_embedding_models(text: str) -> Dict[str, Any]:
    """Compare embeddings from 384D and 768D models"""
    try:
        embedding_384d = await embed_text(text)
        embedding_768d = await embed_text_768d(text)

        # Calculate similarity between same embeddings from different models
        similarity = float(np.dot(
            np.array(embedding_384d) / np.linalg.norm(embedding_384d),
            np.array(embedding_768d) / np.linalg.norm(embedding_768d)
        ))

        return {
            "text": text[:100],  # First 100 chars
            "embedding_384d_size": len(embedding_384d),
            "embedding_768d_size": len(embedding_768d),
            "model_similarity": similarity,
            "model_difference": 1.0 - similarity
        }

    except Exception as e:
        logger.error(f"Error comparing models: {e}")
        return {}

# ============================================
# QDRANT VECTOR STORAGE OPERATIONS
# ============================================

async def upsert_vector(
    project_id: str,
    embedding: List[float],
    metadata: Dict[str, Any]
) -> bool:
    """Upsert vector to Qdrant collection"""
    try:
        from app.services.qdrant_client import qdrant_client
        from app.config import settings
        from qdrant_client.models import PointStruct

        if not qdrant_client:
            logger.warning("Qdrant client not initialized")
            return False

        # Convert project_id to integer hash for Qdrant point ID
        point_id = int(UUID(project_id).int % (2**31))

        point = PointStruct(
            id=point_id,
            vector=embedding,
            payload={
                "project_id": project_id,
                "name": metadata.get("name", ""),
                "description": metadata.get("description", ""),
                "project_type": metadata.get("project_type", ""),
                "region": metadata.get("region", ""),
                "final_price": metadata.get("final_price", 0.0)
            }
        )

        qdrant_client.upsert(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            points=[point]
        )

        logger.debug(f"Upserted vector for project {project_id}")
        return True

    except Exception as e:
        logger.error(f"Error upserting vector: {e}")
        return False

async def search_similar(
    embedding: List[float],
    top_k: int = 5,
    threshold: float = 0.3
) -> List[Dict[str, Any]]:
    """Search for similar vectors in Qdrant"""
    try:
        from app.services.qdrant_client import qdrant_client
        from app.config import settings

        if not qdrant_client:
            logger.warning("Qdrant client not initialized")
            return []

        results = qdrant_client.search(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            query_vector=embedding,
            limit=top_k,
            score_threshold=threshold
        )

        similar_projects = []
        for hit in results:
            payload = hit.payload
            similar_projects.append({
                "id": payload.get("project_id"),
                "name": payload.get("name"),
                "project_type": payload.get("project_type"),
                "similarity_score": hit.score,
                "final_price": payload.get("final_price")
            })

        logger.debug(f"Search found {len(similar_projects)} similar projects")
        return similar_projects

    except Exception as e:
        logger.error(f"Error searching similar vectors: {e}")
        return []

async def delete_vector(project_id: str) -> bool:
    """Delete vector from Qdrant"""
    try:
        from app.services.qdrant_client import qdrant_client
        from app.config import settings

        if not qdrant_client:
            logger.warning("Qdrant client not initialized")
            return False

        point_id = int(UUID(project_id).int % (2**31))

        qdrant_client.delete(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            points_selector=[point_id]
        )

        logger.debug(f"Deleted vector for project {project_id}")
        return True

    except Exception as e:
        logger.error(f"Error deleting vector: {e}")
        return False

async def get_collection_stats() -> Dict[str, Any]:
    """Get Qdrant collection statistics"""
    try:
        from app.services.qdrant_client import qdrant_client
        from app.config import settings

        if not qdrant_client:
            return {}

        collection = qdrant_client.get_collection(settings.QDRANT_COLLECTION_NAME)

        return {
            "points_count": collection.points_count,
            "vectors_count": collection.vectors_count,
            "indexed_vectors_count": collection.indexed_vectors_count
        }

    except Exception as e:
        logger.error(f"Error getting collection stats: {e}")
        return {}

# ============================================
# 768D COLLECTION MANAGEMENT
# ============================================

async def search_similar_768d(
    embedding: List[float],
    top_k: int = 5,
    threshold: float = 0.3,
    collection_name: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Search for similar vectors in 768D collection"""
    try:
        from app.services.qdrant_client import qdrant_client
        from app.config import settings

        if not qdrant_client:
            logger.warning("Qdrant client not initialized")
            return []

        if not collection_name:
            collection_name = settings.QDRANT_COLLECTION_NEXT

        results = qdrant_client.search(
            collection_name=collection_name,
            query_vector=embedding,
            limit=top_k,
            score_threshold=threshold
        )

        similar_projects = []
        for hit in results:
            payload = hit.payload
            similar_projects.append({
                "id": payload.get("project_id"),
                "name": payload.get("name"),
                "project_type": payload.get("project_type"),
                "similarity_score": hit.score,
                "final_price": payload.get("final_price")
            })

        logger.debug(f"768D search found {len(similar_projects)} similar projects")
        return similar_projects

    except Exception as e:
        logger.error(f"Error searching 768D vectors: {e}")
        return []

async def get_collection_stats_768d() -> Dict[str, Any]:
    """Get 768D collection statistics"""
    try:
        from app.services.qdrant_client import qdrant_client
        from app.config import settings

        if not qdrant_client:
            return {}

        collection = qdrant_client.get_collection(settings.QDRANT_COLLECTION_NEXT)

        return {
            "points_count": collection.points_count,
            "vectors_count": collection.vectors_count,
            "indexed_vectors_count": collection.indexed_vectors_count,
            "dimension": 768
        }

    except Exception as e:
        logger.error(f"Error getting 768D collection stats: {e}")
        return {}

async def upsert_vector_768d(
    project_id: str,
    embedding: List[float],
    metadata: Dict[str, Any],
    collection_name: Optional[str] = None
) -> bool:
    """Upsert 768D vector to Qdrant collection"""
    try:
        from app.services.qdrant_client import qdrant_client
        from app.config import settings
        from qdrant_client.models import PointStruct

        if not qdrant_client:
            logger.warning("Qdrant client not initialized")
            return False

        if not collection_name:
            collection_name = settings.QDRANT_COLLECTION_NEXT

        # Convert project_id to integer hash for Qdrant point ID
        point_id = int(UUID(project_id).int % (2**31))

        point = PointStruct(
            id=point_id,
            vector=embedding,
            payload={
                "project_id": project_id,
                "name": metadata.get("name", ""),
                "description": metadata.get("description", ""),
                "project_type": metadata.get("project_type", ""),
                "region": metadata.get("region", ""),
                "final_price": metadata.get("final_price", 0.0)
            }
        )

        qdrant_client.upsert(
            collection_name=collection_name,
            points=[point]
        )

        logger.debug(f"Upserted 768D vector for project {project_id}")
        return True

    except Exception as e:
        logger.error(f"Error upserting 768D vector: {e}")
        return False
