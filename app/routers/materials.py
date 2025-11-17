"""
Materials API Endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import logging
from uuid import UUID

from app.database import get_db
from app.db_models import Material as MaterialModel
from app.models.schemas import MaterialCreate, MaterialResponse, MaterialUpdate

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/", response_model=List[MaterialResponse])
async def list_materials(
    category: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """List materials with optional category filtering"""
    try:
        stmt = select(MaterialModel)
        if category:
            stmt = stmt.where(MaterialModel.category == category)
        stmt = stmt.offset(skip).limit(limit).order_by(MaterialModel.created_at.desc())
        result = await db.execute(stmt)
        materials = result.scalars().all()
        return materials
    except Exception as e:
        logger.error(f"Error listing materials: {e}")
        raise HTTPException(status_code=500, detail="Error listing materials")

@router.post("/", response_model=MaterialResponse, status_code=201)
async def create_material(material: MaterialCreate, db: AsyncSession = Depends(get_db)):
    """Create new material"""
    try:
        db_material = MaterialModel(
            name=material.name,
            category=material.category,
            unit=material.unit,
            datanorm_id=material.datanorm_id
        )
        db.add(db_material)
        await db.commit()
        await db.refresh(db_material)
        logger.info(f"Created material: {db_material.id}")
        return db_material
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating material: {e}")
        raise HTTPException(status_code=500, detail="Error creating material")

@router.get("/{material_id}", response_model=MaterialResponse)
async def get_material(material_id: str, db: AsyncSession = Depends(get_db)):
    """Get specific material"""
    try:
        stmt = select(MaterialModel).where(MaterialModel.id == UUID(material_id))
        result = await db.execute(stmt)
        material = result.scalar_one_or_none()
        if not material:
            raise HTTPException(status_code=404, detail="Material not found")
        return material
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid material ID format")
    except Exception as e:
        logger.error(f"Error getting material: {e}")
        raise HTTPException(status_code=500, detail="Error getting material")

@router.put("/{material_id}", response_model=MaterialResponse)
async def update_material(
    material_id: str,
    update_data: MaterialUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update material"""
    try:
        stmt = select(MaterialModel).where(MaterialModel.id == UUID(material_id))
        result = await db.execute(stmt)
        material = result.scalar_one_or_none()

        if not material:
            raise HTTPException(status_code=404, detail="Material not found")

        if update_data.name:
            material.name = update_data.name
        if update_data.category:
            material.category = update_data.category
        if update_data.unit:
            material.unit = update_data.unit
        if update_data.datanorm_id:
            material.datanorm_id = update_data.datanorm_id

        await db.commit()
        await db.refresh(material)
        logger.info(f"Updated material: {material.id}")
        return material
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid material ID format")
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating material: {e}")
        raise HTTPException(status_code=500, detail="Error updating material")

@router.delete("/{material_id}", status_code=204)
async def delete_material(material_id: str, db: AsyncSession = Depends(get_db)):
    """Delete material"""
    try:
        stmt = select(MaterialModel).where(MaterialModel.id == UUID(material_id))
        result = await db.execute(stmt)
        material = result.scalar_one_or_none()

        if not material:
            raise HTTPException(status_code=404, detail="Material not found")

        await db.delete(material)
        await db.commit()
        logger.info(f"Deleted material: {material.id}")
        return None
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid material ID format")
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting material: {e}")
        raise HTTPException(status_code=500, detail="Error deleting material")
