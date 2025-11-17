"""
Celery Tasks for 768D Embedding Generation

Background tasks for migrating to German-optimized 768D embeddings
"""

import logging
from typing import Dict, Any, List
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.celery_app import app
from app.db_models import Project as ProjectModel
from app.config import settings
from app.services.embeddings import embed_text_768d, upsert_vector_768d, embed_texts_batch_768d

logger = logging.getLogger(__name__)

# ============================================
# 768D EMBEDDING GENERATION TASKS
# ============================================

@app.task(bind=True, name='tasks.generate_768d_embedding')
def generate_768d_embedding(
    self,
    project_id: str,
    description: str,
    metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate 768D German-optimized embedding for a project

    Args:
        project_id: UUID of the project
        description: Project description text
        metadata: Project metadata

    Returns:
        Task result with status and timing
    """
    import asyncio

    start_time = datetime.utcnow()

    try:
        logger.info(f"[Task {self.request.id}] Generating 768D embedding for project {project_id}")

        async def _generate():
            embedding = await embed_text_768d(description)
            success = await upsert_vector_768d(project_id, embedding, metadata)
            return success

        result = asyncio.run(_generate())

        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        if result:
            logger.info(
                f"[Task {self.request.id}] ✓ 768D embedding generated for {project_id} "
                f"in {duration_ms:.1f}ms"
            )
            return {
                "status": "success",
                "project_id": project_id,
                "dimension": 768,
                "duration_ms": duration_ms,
                "task_id": self.request.id
            }
        else:
            raise Exception("Failed to upsert 768D vector to Qdrant")

    except Exception as e:
        logger.error(f"[Task {self.request.id}] ✗ Error generating 768D embedding: {e}")
        raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))

@app.task(bind=True, name='tasks.batch_generate_768d_embeddings')
def batch_generate_768d_embeddings(
    self,
    project_ids: List[str]
) -> Dict[str, Any]:
    """
    Generate 768D embeddings for multiple projects

    Args:
        project_ids: List of project UUIDs

    Returns:
        Task result with count of successful/failed embeddings
    """
    import asyncio

    start_time = datetime.utcnow()

    try:
        logger.info(
            f"[Task {self.request.id}] Batch generating 768D embeddings for "
            f"{len(project_ids)} projects"
        )

        async def _batch_generate():
            async_session, engine = get_async_session()

            successful = 0
            failed = 0
            errors = []

            async with async_session() as session:
                # Fetch all projects
                stmt = select(ProjectModel).where(ProjectModel.id.in_([
                    __import__('uuid').UUID(pid) for pid in project_ids
                ]))
                result = await session.execute(stmt)
                projects = result.scalars().all()

            logger.info(f"Found {len(projects)} projects for 768D batch embedding")

            for project in projects:
                try:
                    embedding_text = project.description or project.name
                    metadata = {
                        "name": project.name,
                        "description": project.description,
                        "project_type": project.project_type,
                        "region": project.region,
                        "final_price": float(project.final_price) if project.final_price else 0.0
                    }

                    embedding = await embed_text_768d(embedding_text)
                    success = await upsert_vector_768d(str(project.id), embedding, metadata)

                    if success:
                        successful += 1
                    else:
                        failed += 1
                        errors.append(f"Failed to upsert {project.id}")

                except Exception as e:
                    failed += 1
                    errors.append(f"Error for {project.id}: {str(e)}")

            await engine.dispose()
            return successful, failed, errors

        successful, failed, errors = asyncio.run(_batch_generate())

        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        logger.info(
            f"[Task {self.request.id}] ✓ Batch 768D embedding complete: "
            f"{successful} successful, {failed} failed in {duration_ms:.1f}ms"
        )

        return {
            "status": "success" if failed == 0 else "partial",
            "successful": successful,
            "failed": failed,
            "total": len(project_ids),
            "dimension": 768,
            "duration_ms": duration_ms,
            "errors": errors,
            "task_id": self.request.id
        }

    except Exception as e:
        logger.error(f"[Task {self.request.id}] ✗ Batch 768D embedding error: {e}")
        raise self.retry(exc=e, countdown=120 * (self.request.retries + 1))

@app.task(name='tasks.full_migration_to_768d')
def full_migration_to_768d() -> Dict[str, Any]:
    """
    Full migration task for all projects to 768D embeddings

    Runs as a scheduled task or triggered manually
    """
    import asyncio

    logger.info("Starting full migration to 768D embeddings")

    try:
        async def _migrate_all():
            async_session, engine = get_async_session()

            # Fetch all projects
            async with async_session() as session:
                stmt = select(ProjectModel)
                result = await session.execute(stmt)
                projects = result.scalars().all()

            total = len(projects)
            successful = 0
            failed = 0

            logger.info(f"Migrating {total} projects to 768D")

            # Process in large batches for efficiency
            batch_size = 100
            for batch_start in range(0, total, batch_size):
                batch_end = min(batch_start + batch_size, total)
                batch = projects[batch_start:batch_end]

                descriptions = [p.description or p.name for p in batch]
                embeddings = await embed_texts_batch_768d(descriptions)

                for project, embedding in zip(batch, embeddings):
                    try:
                        metadata = {
                            "name": project.name,
                            "description": project.description,
                            "project_type": project.project_type,
                            "region": project.region,
                            "final_price": float(project.final_price) if project.final_price else 0.0
                        }

                        success = await upsert_vector_768d(
                            str(project.id),
                            embedding,
                            metadata
                        )

                        if success:
                            successful += 1
                        else:
                            failed += 1

                    except Exception as e:
                        logger.warning(f"Failed to migrate {project.id}: {e}")
                        failed += 1

                logger.info(f"Batch progress: {batch_end}/{total} projects processed")

            await engine.dispose()
            return successful, failed

        successful, failed = asyncio.run(_migrate_all())

        return {
            "status": "success" if failed == 0 else "partial",
            "total": successful + failed,
            "successful": successful,
            "failed": failed,
            "dimension": 768,
            "message": f"Migration complete: {successful} successful, {failed} failed"
        }

    except Exception as e:
        logger.error(f"Full migration error: {e}")
        return {
            "status": "failed",
            "error": str(e)
        }

# ============================================
# UTILITY FUNCTIONS
# ============================================

def get_async_session():
    """Get async database session (synchronous wrapper for creating async engine/session)"""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return async_session, engine

@app.task(name='tasks.compare_embedding_models')
def compare_embedding_models_task() -> Dict[str, Any]:
    """
    Compare 384D and 768D embedding models

    Provides metrics on model differences for quality validation
    """
    import asyncio

    logger.info("Comparing 384D and 768D embedding models")

    try:
        async def _compare():
            from app.services.embeddings import compare_embedding_models
            async_session, engine = get_async_session()

            # Get sample projects
            async with async_session() as session:
                stmt = select(ProjectModel).limit(10)
                result = await session.execute(stmt)
                projects = result.scalars().all()

            await engine.dispose()

            similarities = []
            differences = []

            for project in projects:
                text = project.description or project.name
                comparison = await compare_embedding_models(text)

                if comparison:
                    similarities.append(comparison.get("model_similarity", 0))
                    differences.append(comparison.get("model_difference", 0))

            if similarities:
                avg_similarity = sum(similarities) / len(similarities)
                avg_difference = sum(differences) / len(differences)

                return {
                    "samples_tested": len(similarities),
                    "average_model_similarity": avg_similarity,
                    "average_model_difference": avg_difference,
                    "interpretation": (
                        "Models are very similar" if avg_similarity > 0.95
                        else "Models show moderate differences" if avg_similarity > 0.85
                        else "Models show significant differences"
                    )
                }

            return {"error": "No projects to compare"}

        result = asyncio.run(_compare())
        logger.info(f"Model comparison result: {result}")
        return result

    except Exception as e:
        logger.error(f"Model comparison error: {e}")
        return {"error": str(e)}
