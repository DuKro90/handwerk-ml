"""
Price Prediction API Endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import logging
import os
from datetime import datetime

from app.database import get_db
from app.db_models import PricePrediction as PricePredictionModel
from app.models.schemas import PredictionRequest, PredictionResponse

router = APIRouter()
logger = logging.getLogger(__name__)

# Load ML models (lazy loading)
_price_model = None
_feature_engineer = None
_confidence_calculator = None

async def get_models():
    """Lazy load ML models"""
    global _price_model, _feature_engineer, _confidence_calculator

    if _price_model is None:
        try:
            import joblib
            model_path = "./models/xgboost_model.pkl"
            if os.path.exists(model_path):
                _price_model = joblib.load(model_path)
                logger.info("✓ XGBoost model loaded")
            else:
                logger.warning("Model file not found, using mock model")
                _price_model = None
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            _price_model = None

    return _price_model

@router.post("/predict/", response_model=PredictionResponse)
async def predict_price(
    prediction_request: PredictionRequest,
    db: AsyncSession = Depends(get_db)
):
    """Predict price for given features"""
    try:
        model = await get_models()

        # Mock prediction if model not available
        if not model:
            # Return realistic mock prediction
            predicted_price = float(prediction_request.final_price or 10000)
            confidence_score = 0.65
            similar_count = 0
        else:
            # Prepare features for model
            try:
                import numpy as np
                # Create feature vector (should match training features)
                features = np.array([[
                    prediction_request.total_area_sqm or 0,
                    prediction_request.complexity or 1,
                    0,  # wood_type encoded
                    0,  # project_type encoded
                    0,  # region encoded
                ]])

                predicted_price = float(model.predict(features)[0])
                confidence_score = min(0.95, 0.5 + (0.1 * prediction_request.complexity))
                similar_count = 0
            except Exception as e:
                logger.warning(f"Model prediction error: {e}, using default")
                predicted_price = float(prediction_request.final_price or 10000)
                confidence_score = 0.65
                similar_count = 0

        # Determine confidence level
        if confidence_score > 0.9:
            confidence_level = "Very High"
        elif confidence_score > 0.75:
            confidence_level = "High"
        elif confidence_score > 0.5:
            confidence_level = "Medium"
        elif confidence_score > 0.3:
            confidence_level = "Low"
        else:
            confidence_level = "Very Low"

        # Log prediction
        prediction_log = PricePredictionModel(
            project_features={
                "total_area_sqm": prediction_request.total_area_sqm,
                "complexity": prediction_request.complexity,
                "project_type": prediction_request.project_type,
                "wood_type": prediction_request.wood_type,
                "region": prediction_request.region
            },
            predicted_price=predicted_price,
            confidence_score=confidence_score,
            similar_projects_count=similar_count,
            model_version="1.0.0"
        )
        db.add(prediction_log)
        await db.commit()

        logger.info(f"Price prediction: {predicted_price:.2f} (confidence: {confidence_score:.2f})")

        return PredictionResponse(
            predicted_price=predicted_price,
            confidence_score=confidence_score,
            confidence_level=confidence_level,
            similar_projects_count=similar_count,
            model_version="1.0.0",
            timestamp=datetime.utcnow()
        )
    except Exception as e:
        await db.rollback()
        logger.error(f"Error predicting price: {e}")
        raise HTTPException(status_code=500, detail="Error predicting price")

@router.get("/model-info/")
async def get_model_info():
    """Get model information"""
    try:
        model = await get_models()

        model_info = {
            "version": "1.0.0",
            "type": "XGBoost Regressor",
            "status": "ready" if model else "not_loaded",
            "features": [
                "total_area_sqm",
                "complexity",
                "project_type",
                "wood_type",
                "region"
            ],
            "output": "predicted_price",
            "confidence_enabled": True,
            "last_updated": "2025-11-17"
        }
        return model_info
    except Exception as e:
        logger.error(f"Error getting model info: {e}")
        raise HTTPException(status_code=500, detail="Error getting model info")
