"""
Projects API Endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import logging
from uuid import UUID
from datetime import date

from app.database import get_db
from app.db_models import Project as ProjectModel
from app.models.schemas import ProjectCreate, ProjectResponse, ProjectUpdate

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/", response_model=List[ProjectResponse])
async def list_projects(skip: int = 0, limit: int = 50, db: AsyncSession = Depends(get_db)):
    """List all projects with pagination"""
    try:
        stmt = select(ProjectModel).offset(skip).limit(limit).order_by(ProjectModel.created_at.desc())
        result = await db.execute(stmt)
        projects = result.scalars().all()
        return projects
    except Exception as e:
        logger.error(f"Error listing projects: {e}")
        raise HTTPException(status_code=500, detail="Error listing projects")

@router.post("/", response_model=ProjectResponse, status_code=201)
async def create_project(project: ProjectCreate, db: AsyncSession = Depends(get_db)):
    """Create new project with automatic embedding generation"""
    try:
        # Parse project_date if provided
        project_date = date.today()
        if hasattr(project, 'project_date') and project.project_date:
            if isinstance(project.project_date, str):
                project_date = date.fromisoformat(project.project_date)
            else:
                project_date = project.project_date

        db_project = ProjectModel(
            name=project.name,
            description=project.description or "",
            project_type=project.project_type,
            region=project.region,
            total_area_sqm=project.total_area_sqm,
            wood_type=project.wood_type,
            complexity=project.complexity or 1,
            final_price=project.final_price or 0,
            project_date=project_date
        )
        db.add(db_project)
        await db.commit()
        await db.refresh(db_project)

        # Queue embedding generation as background task
        try:
            from app.tasks.embedding_tasks import generate_project_embedding
            metadata = {
                "name": db_project.name,
                "description": db_project.description,
                "project_type": db_project.project_type,
                "region": db_project.region,
                "final_price": float(db_project.final_price) if db_project.final_price else 0.0
            }

            embedding_text = db_project.description or db_project.name
            task = generate_project_embedding.delay(
                str(db_project.id),
                embedding_text,
                metadata
            )
            logger.info(f"Queued embedding generation for project {db_project.id} (task: {task.id})")
        except Exception as e:
            logger.warning(f"Failed to queue embedding task for {db_project.id}: {e}")
            # Don't fail the project creation if task queueing fails

        logger.info(f"Created project: {db_project.id}")
        return db_project
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating project: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    """Get specific project"""
    try:
        stmt = select(ProjectModel).where(ProjectModel.id == UUID(project_id))
        result = await db.execute(stmt)
        project = result.scalar_one_or_none()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return project
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID format")
    except Exception as e:
        logger.error(f"Error getting project: {e}")
        raise HTTPException(status_code=500, detail="Error getting project")

@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: str, update_data: ProjectUpdate, db: AsyncSession = Depends(get_db)):
    """Update project and regenerate embedding if description changed"""
    try:
        stmt = select(ProjectModel).where(ProjectModel.id == UUID(project_id))
        result = await db.execute(stmt)
        project = result.scalar_one_or_none()

        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Check if finalized
        if project.is_finalized:
            raise HTTPException(status_code=403, detail="Cannot update finalized project")

        # Track if description changed
        description_changed = False

        # Update fields
        if update_data.name:
            project.name = update_data.name
        if update_data.description:
            project.description = update_data.description
            description_changed = True
        if update_data.final_price:
            project.final_price = update_data.final_price

        await db.commit()
        await db.refresh(project)

        # Regenerate embedding if description changed
        if description_changed:
            try:
                from app.tasks.embedding_tasks import regenerate_project_embedding
                metadata = {
                    "name": project.name,
                    "description": project.description,
                    "project_type": project.project_type,
                    "region": project.region,
                    "final_price": float(project.final_price) if project.final_price else 0.0
                }

                embedding_text = project.description or project.name
                task = regenerate_project_embedding.delay(
                    str(project.id),
                    embedding_text,
                    metadata
                )
                logger.info(f"Queued embedding regeneration for project {project.id} (task: {task.id})")
            except Exception as e:
                logger.warning(f"Failed to queue embedding regeneration for {project.id}: {e}")
                # Don't fail the update if task queueing fails

        logger.info(f"Updated project: {project.id}")
        return project
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID format")
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating project: {e}")
        raise HTTPException(status_code=500, detail="Error updating project")

@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: str, db: AsyncSession = Depends(get_db)):
    """Delete project and remove from vector index"""
    try:
        stmt = select(ProjectModel).where(ProjectModel.id == UUID(project_id))
        result = await db.execute(stmt)
        project = result.scalar_one_or_none()

        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        await db.delete(project)
        await db.commit()

        # Queue vector deletion as background task
        try:
            from app.tasks.embedding_tasks import delete_project_embedding
            task = delete_project_embedding.delay(str(project.id))
            logger.info(f"Queued embedding deletion for project {project.id} (task: {task.id})")
        except Exception as e:
            logger.warning(f"Failed to queue embedding deletion for {project.id}: {e}")
            # Don't fail the deletion if task queueing fails

        logger.info(f"Deleted project: {project.id}")
        return None
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID format")
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting project: {e}")
        raise HTTPException(status_code=500, detail="Error deleting project")
