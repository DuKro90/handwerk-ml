"""
Migration Script: Upgrade to 768D German-Optimized Embeddings

This script:
1. Creates new 768D Qdrant collection
2. Generates 768D embeddings for all projects
3. Migrates vectors from 384D to 768D collection
4. Validates migration success
5. Allows safe cutover from 384D to 768D
"""

import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime
import time

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.db_models import Project as ProjectModel
from app.services.embeddings import (
    embed_texts_batch_768d,
    upsert_vector_768d,
    get_collection_stats_768d,
    compare_embedding_models
)
from app.services.qdrant_client import qdrant_client
from app.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def create_768d_collection():
    """Create 768D collection in Qdrant if it doesn't exist"""
    from qdrant_client.models import Distance, VectorParams

    try:
        # Check if collection exists
        qdrant_client.get_collection(settings.QDRANT_COLLECTION_NEXT)
        logger.info(f"✓ Collection '{settings.QDRANT_COLLECTION_NEXT}' already exists")
        return True

    except Exception:
        logger.info(f"Creating 768D collection '{settings.QDRANT_COLLECTION_NEXT}'...")

        try:
            qdrant_client.create_collection(
                collection_name=settings.QDRANT_COLLECTION_NEXT,
                vectors_config=VectorParams(
                    size=768,  # 768D for German-optimized model
                    distance=Distance.COSINE
                ),
                optimizers_config={
                    "memmap_threshold": 20000,
                    "indexing_threshold": 20000,
                    "flush_interval_sec": 60,
                    "deleted_threshold": 0.2
                }
            )
            logger.info(f"✓ Collection '{settings.QDRANT_COLLECTION_NEXT}' created successfully")
            return True

        except Exception as e:
            logger.error(f"✗ Failed to create collection: {e}")
            raise

async def get_all_projects():
    """Fetch all projects from database"""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        stmt = select(ProjectModel)
        result = await session.execute(stmt)
        projects = result.scalars().all()

    await engine.dispose()
    return projects

async def migrate_embeddings_to_768d():
    """Migrate embeddings from 384D to 768D"""

    start_time = datetime.now()
    logger.info("=" * 80)
    logger.info("EMBEDDINGS MIGRATION: 384D → 768D (German-Optimized)")
    logger.info("=" * 80)

    try:
        # Step 1: Create 768D collection
        logger.info("\n[Step 1] Creating 768D collection in Qdrant...")
        await create_768d_collection()

        # Step 2: Get all projects
        logger.info("\n[Step 2] Fetching projects from database...")
        projects = await get_all_projects()
        total_projects = len(projects)
        logger.info(f"Found {total_projects} projects to migrate")

        if total_projects == 0:
            logger.warning("No projects found. Migration skipped.")
            return

        # Step 3: Migrate embeddings in batches
        logger.info("\n[Step 3] Generating 768D embeddings and migrating vectors...")
        batch_size = 10
        successful = 0
        failed = 0
        errors = []

        for batch_start in range(0, total_projects, batch_size):
            batch_end = min(batch_start + batch_size, total_projects)
            batch = projects[batch_start:batch_end]
            batch_num = (batch_start // batch_size) + 1
            total_batches = (total_projects + batch_size - 1) // batch_size

            logger.info(
                f"\nProcessing batch {batch_num}/{total_batches} "
                f"({batch_start+1}-{batch_end}/{total_projects})..."
            )

            # Extract descriptions for embedding
            descriptions = [p.description or p.name for p in batch]

            # Generate 768D embeddings
            logger.info(f"  Generating 768D embeddings for {len(batch)} projects...")
            embeddings_768d = await embed_texts_batch_768d(descriptions)

            # Upsert vectors to 768D collection
            for project, embedding in zip(batch, embeddings_768d):
                try:
                    metadata = {
                        "name": project.name,
                        "description": project.description or "",
                        "project_type": project.project_type or "",
                        "region": project.region or "",
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
                        errors.append(f"Failed to upsert {project.id}")

                except Exception as e:
                    failed += 1
                    errors.append(f"Error for {project.id}: {str(e)}")

            logger.info(
                f"  Batch {batch_num} complete: "
                f"{successful + failed - sum(1 for _ in errors[-len([x for x in range(batch_start, batch_end)])])}/{len(batch)} successful"
            )

        # Step 4: Validate migration
        logger.info("\n[Step 4] Validating migration...")
        stats_768d = await get_collection_stats_768d()

        if stats_768d and stats_768d.get("points_count", 0) > 0:
            logger.info(f"✓ 768D collection stats:")
            logger.info(f"  Points: {stats_768d.get('points_count')}")
            logger.info(f"  Vectors: {stats_768d.get('vectors_count')}")
            logger.info(f"  Indexed: {stats_768d.get('indexed_vectors_count')}")
        else:
            logger.warning("⚠ 768D collection appears empty")

        # Step 5: Model comparison (sample)
        logger.info("\n[Step 5] Comparing model quality (sample)...")
        if projects and len(projects) >= 5:
            sample_texts = [
                projects[0].description or projects[0].name,
                projects[1].description or projects[1].name,
                projects[2].description or projects[2].name,
            ]

            comparison_results = []
            for text in sample_texts:
                result = await compare_embedding_models(text)
                comparison_results.append(result)
                logger.info(
                    f"  Sample: '{text[:50]}...' → "
                    f"Model difference: {result.get('model_difference', 0):.4f}"
                )

        # Step 6: Summary
        elapsed = (datetime.now() - start_time).total_seconds()

        logger.info("\n" + "=" * 80)
        logger.info("MIGRATION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total projects: {total_projects}")
        logger.info(f"Successfully migrated: {successful}")
        logger.info(f"Failed: {failed}")
        logger.info(f"Total time: {elapsed:.2f}s")
        logger.info(f"Average time per project: {elapsed/total_projects:.3f}s")

        if errors:
            logger.info(f"\nErrors ({len(errors)}):")
            for error in errors[:10]:  # Show first 10 errors
                logger.info(f"  - {error}")
            if len(errors) > 10:
                logger.info(f"  ... and {len(errors) - 10} more errors")

        logger.info("\n" + "=" * 80)
        logger.info("NEXT STEPS")
        logger.info("=" * 80)
        logger.info("1. Test the 768D collection with similarity searches")
        logger.info("2. Validate search quality improvements")
        logger.info("3. Update config to point to 768D collection")
        logger.info("4. Gradually switch traffic to 768D (canary deployment)")
        logger.info("5. Archive 384D collection after validation")
        logger.info("=" * 80 + "\n")

        return successful, failed, errors

    except Exception as e:
        logger.error(f"Migration failed with error: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(migrate_embeddings_to_768d())
