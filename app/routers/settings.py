"""
Settings API Endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from app.database import get_db
from app.db_models import Settings as SettingsModel
from app.models.schemas import SettingsResponse, SettingsUpdate

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/current/", response_model=SettingsResponse)
async def get_current_settings(db: AsyncSession = Depends(get_db)):
    """Get current active settings"""
    try:
        stmt = select(SettingsModel).limit(1)
        result = await db.execute(stmt)
        settings = result.scalar_one_or_none()
        
        # Create default settings if none exist
        if not settings:
            settings = SettingsModel()
            db.add(settings)
            await db.commit()
            await db.refresh(settings)
            logger.info("Created default settings")
        
        return settings
    except Exception as e:
        logger.error(f"Error getting settings: {e}")
        raise HTTPException(status_code=500, detail="Error getting settings")

@router.put("/current/", response_model=SettingsResponse)
async def update_current_settings(
    update_data: SettingsUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update current active settings"""
    try:
        stmt = select(SettingsModel).limit(1)
        result = await db.execute(stmt)
        settings = result.scalar_one_or_none()
        
        # Create default settings if none exist
        if not settings:
            settings = SettingsModel()
            db.add(settings)
            await db.commit()
            await db.refresh(settings)
        
        # Update fields
        if update_data.labor_rate_per_hour is not None:
            settings.labor_rate_per_hour = update_data.labor_rate_per_hour
        if update_data.material_markup_percentage is not None:
            settings.material_markup_percentage = update_data.material_markup_percentage
        if update_data.overhead_percentage is not None:
            settings.overhead_percentage = update_data.overhead_percentage
        if update_data.profit_margin_percentage is not None:
            settings.profit_margin_percentage = update_data.profit_margin_percentage
        if update_data.polster_fabric_base_price is not None:
            settings.polster_fabric_base_price = update_data.polster_fabric_base_price
        if update_data.polster_labor_rate is not None:
            settings.polster_labor_rate = update_data.polster_labor_rate
        
        await db.commit()
        await db.refresh(settings)
        logger.info("Updated settings")
        return settings
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating settings: {e}")
        raise HTTPException(status_code=500, detail="Error updating settings")
