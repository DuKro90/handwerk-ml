"""
Semantic Similarity Search Endpoints (Qdrant-Powered)
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import logging
import time

from app.database import get_db
from app.models.schemas import SimilarProject, SimilaritySearchResponse
from app.services.embeddings import embed_text, search_similar, embed_texts_batch

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/find-similar", response_model=SimilaritySearchResponse)
async def find_similar(
    query: str,
    top_k: int = 5,
    threshold: float = 0.3,
    db: AsyncSession = Depends(get_db)
):
    """
    Find similar projects based on semantic search using Qdrant.

    Uses vector similarity search with HNSW indexing for O(log n) performance.
    Expected latency: 20-30ms for typical collections.
    """
    try:
        start_time = time.time()

        # Generate embedding for query
        query_embedding = await embed_text(query)

        # Search Qdrant for similar vectors
        qdrant_results = await search_similar(
            embedding=query_embedding,
            top_k=top_k,
            threshold=threshold
        )

        # Convert Qdrant results to response model
        results = [
            SimilarProject(
                id=hit["id"],
                name=hit["name"],
                project_type=hit["project_type"],
                similarity_score=hit["similarity_score"],
                final_price=hit.get("final_price")
            )
            for hit in qdrant_results
        ]

        search_time_ms = (time.time() - start_time) * 1000

        logger.info(f"Qdrant search: '{query}' found {len(results)} results in {search_time_ms:.1f}ms")

        return SimilaritySearchResponse(
            query=query,
            results=results,
            total_count=len(results),
            search_time_ms=search_time_ms
        )

    except Exception as e:
        logger.error(f"Error finding similar projects: {e}")
        raise HTTPException(status_code=500, detail="Error finding similar projects")

@router.post("/batch-similar")
async def batch_similar_projects(
    queries: List[str],
    top_k: int = 3,
    threshold: float = 0.3,
    db: AsyncSession = Depends(get_db)
):
    """
    Find similar projects for multiple queries in parallel.

    Batch processing is optimized for throughput.
    """
    try:
        start_time = time.time()

        # Generate embeddings in batch for efficiency
        embeddings = await embed_texts_batch(queries)

        results = []
        for query, embedding in zip(queries, embeddings):
            qdrant_results = await search_similar(
                embedding=embedding,
                top_k=top_k,
                threshold=threshold
            )

            similar_projects = [
                SimilarProject(
                    id=hit["id"],
                    name=hit["name"],
                    project_type=hit["project_type"],
                    similarity_score=hit["similarity_score"],
                    final_price=hit.get("final_price")
                )
                for hit in qdrant_results
            ]

            results.append(SimilaritySearchResponse(
                query=query,
                results=similar_projects,
                total_count=len(similar_projects),
                search_time_ms=0  # Individual timing not tracked in batch
            ))

        batch_time_ms = (time.time() - start_time) * 1000

        logger.info(f"Batch search: {len(queries)} queries completed in {batch_time_ms:.1f}ms")

        return {
            "total_queries": len(queries),
            "results": results,
            "batch_time_ms": batch_time_ms
        }

    except Exception as e:
        logger.error(f"Error in batch similarity search: {e}")
        raise HTTPException(status_code=500, detail="Error in batch similarity search")

@router.get("/stats")
async def get_search_stats():
    """Get Qdrant collection statistics for monitoring"""
    try:
        from app.services.embeddings import get_collection_stats

        stats = await get_collection_stats()

        return {
            "vector_index": "Qdrant HNSW",
            "status": "active" if stats else "unavailable",
            **stats
        }

    except Exception as e:
        logger.error(f"Error getting search stats: {e}")
        raise HTTPException(status_code=500, detail="Error getting search stats")
