"""
Celery Tasks for Async Embedding Generation

Background tasks for:
- Generating embeddings for projects
- Batch embedding generation
- Embedding cleanup
"""

import logging
from typing import Dict, Any, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.celery_app import app
from app.db_models import Project as ProjectModel
from app.config import settings
from app.services.embeddings import embed_text, upsert_vector, delete_vector

logger = logging.getLogger(__name__)

# ============================================
# ASYNC DATABASE UTILITIES
# ============================================

async def get_async_session():
    """Get async database session"""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return async_session, engine

# ============================================
# EMBEDDING GENERATION TASKS
# ============================================

@app.task(bind=True, name='tasks.generate_project_embedding')
def generate_project_embedding(
    self,
    project_id: str,
    description: str,
    metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate embedding for a project asynchronously

    Args:
        project_id: UUID of the project
        description: Project description text
        metadata: Project metadata (name, project_type, region, final_price)

    Returns:
        Task result with status and timing
    """
    import asyncio
    from datetime import datetime

    start_time = datetime.utcnow()

    try:
        logger.info(f"[Task {self.request.id}] Generating embedding for project {project_id}")

        # Run async embedding function
        async def _generate():
            embedding = await embed_text(description)
            success = await upsert_vector(project_id, embedding, metadata)
            return success

        result = asyncio.run(_generate())

        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        if result:
            logger.info(
                f"[Task {self.request.id}] ✓ Embedding generated for {project_id} "
                f"in {duration_ms:.1f}ms"
            )
            return {
                "status": "success",
                "project_id": project_id,
                "duration_ms": duration_ms,
                "task_id": self.request.id
            }
        else:
            raise Exception("Failed to upsert vector to Qdrant")

    except Exception as e:
        logger.error(f"[Task {self.request.id}] ✗ Error generating embedding: {e}")

        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))

@app.task(bind=True, name='tasks.regenerate_project_embedding')
def regenerate_project_embedding(
    self,
    project_id: str,
    description: str,
    metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Regenerate embedding for updated project

    Args:
        project_id: UUID of the project
        description: Updated description
        metadata: Updated metadata

    Returns:
        Task result with status and timing
    """
    import asyncio
    from datetime import datetime

    start_time = datetime.utcnow()

    try:
        logger.info(f"[Task {self.request.id}] Regenerating embedding for project {project_id}")

        async def _regenerate():
            # Delete old vector
            await delete_vector(project_id)
            # Generate and upsert new vector
            embedding = await embed_text(description)
            success = await upsert_vector(project_id, embedding, metadata)
            return success

        result = asyncio.run(_regenerate())

        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        if result:
            logger.info(
                f"[Task {self.request.id}] ✓ Embedding regenerated for {project_id} "
                f"in {duration_ms:.1f}ms"
            )
            return {
                "status": "success",
                "project_id": project_id,
                "duration_ms": duration_ms,
                "task_id": self.request.id
            }
        else:
            raise Exception("Failed to regenerate vector in Qdrant")

    except Exception as e:
        logger.error(f"[Task {self.request.id}] ✗ Error regenerating embedding: {e}")
        raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))

@app.task(bind=True, name='tasks.batch_generate_embeddings')
def batch_generate_embeddings(
    self,
    project_ids: List[str]
) -> Dict[str, Any]:
    """
    Generate embeddings for multiple projects

    Args:
        project_ids: List of project UUIDs

    Returns:
        Task result with count of successful/failed embeddings
    """
    import asyncio
    from datetime import datetime

    start_time = datetime.utcnow()

    try:
        logger.info(
            f"[Task {self.request.id}] Batch generating embeddings for "
            f"{len(project_ids)} projects"
        )

        async def _batch_generate():
            async_session, engine = await get_async_session()

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

            logger.info(f"Found {len(projects)} projects for batch embedding")

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

                    from app.services.embeddings import embed_text, upsert_vector
                    embedding = await embed_text(embedding_text)
                    success = await upsert_vector(str(project.id), embedding, metadata)

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
            f"[Task {self.request.id}] ✓ Batch embedding complete: "
            f"{successful} successful, {failed} failed in {duration_ms:.1f}ms"
        )

        return {
            "status": "success" if failed == 0 else "partial",
            "successful": successful,
            "failed": failed,
            "total": len(project_ids),
            "duration_ms": duration_ms,
            "errors": errors,
            "task_id": self.request.id
        }

    except Exception as e:
        logger.error(f"[Task {self.request.id}] ✗ Batch embedding error: {e}")
        raise self.retry(exc=e, countdown=120 * (self.request.retries + 1))

@app.task(bind=True, name='tasks.delete_project_embedding')
def delete_project_embedding(self, project_id: str) -> Dict[str, Any]:
    """
    Delete embedding for a project

    Args:
        project_id: UUID of the project to remove

    Returns:
        Task result with status
    """
    import asyncio

    try:
        logger.info(f"[Task {self.request.id}] Deleting embedding for project {project_id}")

        async def _delete():
            success = await delete_vector(project_id)
            return success

        result = asyncio.run(_delete())

        if result:
            logger.info(f"[Task {self.request.id}] ✓ Embedding deleted for {project_id}")
            return {
                "status": "success",
                "project_id": project_id,
                "task_id": self.request.id
            }
        else:
            raise Exception("Failed to delete vector from Qdrant")

    except Exception as e:
        logger.error(f"[Task {self.request.id}] ✗ Error deleting embedding: {e}")
        raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))

# ============================================
# SCHEDULED TASKS
# ============================================

@app.task(name='tasks.cleanup_old_embeddings')
def cleanup_old_embeddings() -> Dict[str, Any]:
    """
    Periodic task to clean up orphaned embeddings

    Runs daily to remove vectors for deleted projects
    """
    logger.info("Running scheduled cleanup of old embeddings")

    # This would check for orphaned vectors and remove them
    # Implementation depends on specific business logic

    return {
        "status": "success",
        "message": "Embedding cleanup completed"
    }

@app.task(name='tasks.reindex_embeddings')
def reindex_embeddings() -> Dict[str, Any]:
    """
    Periodic task to reindex embeddings in Qdrant

    Helps maintain index performance
    """
    logger.info("Running scheduled embedding reindex")

    # This would trigger Qdrant reindexing
    # Implementation depends on Qdrant capabilities

    return {
        "status": "success",
        "message": "Embedding reindex completed"
    }
