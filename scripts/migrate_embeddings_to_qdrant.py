"""
Migration Script: Move embeddings from SQLite to Qdrant

This script:
1. Reads all projects from SQLite database
2. Generates embeddings for project descriptions
3. Upserts vectors to Qdrant with project metadata
4. Logs progress and timing
"""

import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.db_models import Project as ProjectModel
from app.services.embeddings import embed_texts_batch, upsert_vector
from app.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def migrate_embeddings_to_qdrant():
    """Migrate all project embeddings to Qdrant"""

    start_time = datetime.now()
    logger.info("=" * 60)
    logger.info("Starting embeddings migration to Qdrant")
    logger.info("=" * 60)

    try:
        # Initialize database connection
        engine = create_async_engine(
            settings.DATABASE_URL,
            echo=False,
            pool_pre_ping=True
        )

        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )

        # Get all projects
        async with async_session() as session:
            stmt = select(ProjectModel)
            result = await session.execute(stmt)
            projects = result.scalars().all()

        total_projects = len(projects)
        logger.info(f"Found {total_projects} projects to migrate")

        if total_projects == 0:
            logger.warning("No projects found. Migration skipped.")
            return

        # Process in batches
        batch_size = 10
        successful = 0
        failed = 0

        for batch_start in range(0, total_projects, batch_size):
            batch_end = min(batch_start + batch_size, total_projects)
            batch = projects[batch_start:batch_end]

            logger.info(f"\nProcessing batch {batch_start//batch_size + 1} "
                       f"({batch_start+1}-{batch_end}/{total_projects})...")

            # Extract descriptions for embedding
            descriptions = [
                p.description or p.name
                for p in batch
            ]

            # Generate embeddings in batch
            logger.info(f"  Generating embeddings for {len(batch)} projects...")
            embeddings = await embed_texts_batch(descriptions)

            # Upsert each vector to Qdrant
            for project, embedding in zip(batch, embeddings):
                try:
                    metadata = {
                        "name": project.name,
                        "description": project.description or "",
                        "project_type": project.project_type or "",
                        "region": project.region or "",
                        "final_price": float(project.final_price) if project.final_price else 0.0
                    }

                    success = await upsert_vector(
                        str(project.id),
                        embedding,
                        metadata
                    )

                    if success:
                        successful += 1
                    else:
                        failed += 1
                        logger.warning(f"    Failed to upsert: {project.name}")

                except Exception as e:
                    failed += 1
                    logger.error(f"    Error upserting {project.name}: {e}")

            logger.info(f"  Batch complete: {successful + len([x for x in range(batch_start, batch_end)])} successful")

        # Close engine
        await engine.dispose()

        # Print summary
        elapsed = (datetime.now() - start_time).total_seconds()

        logger.info("\n" + "=" * 60)
        logger.info("Migration Complete!")
        logger.info("=" * 60)
        logger.info(f"Total projects: {total_projects}")
        logger.info(f"Successfully migrated: {successful}")
        logger.info(f"Failed: {failed}")
        logger.info(f"Total time: {elapsed:.2f}s")
        logger.info(f"Average time per project: {elapsed/total_projects:.3f}s")
        logger.info("=" * 60)

        return successful, failed

    except Exception as e:
        logger.error(f"Migration failed with error: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(migrate_embeddings_to_qdrant())
