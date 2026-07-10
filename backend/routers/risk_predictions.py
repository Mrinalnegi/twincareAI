"""Risk prediction API endpoints."""

import os
import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from schemas.risk_prediction import (
    RiskPredictionResponse,
    RiskPredictionListResponse,
    RiskPredictionRequest,
    ShapValues,
    FeatureImportance,
)
from config import settings
from services.prediction_service import get_user_predictions, get_prediction_by_id
from utils.security import get_current_user_id
from ai.heart_model import predict_risk
from ai.shap_explainer import compute_shap_values

router = APIRouter(prefix="/risk-predictions", tags=["Risk Predictions"])

# Internal feature flag to gate the direct prediction endpoint
ENABLE_DIRECT_PREDICTION_ENDPOINT = os.getenv("ENABLE_DIRECT_PREDICTION_ENDPOINT", "true").lower() == "true"


@router.get("", response_model=RiskPredictionListResponse)
def list_predictions(
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Get all risk predictions for the current user."""
    predictions = get_user_predictions(db, user_id)
    return RiskPredictionListResponse(
        predictions=[_format_prediction(p) for p in predictions]
    )


@router.get("/{prediction_id}", response_model=RiskPredictionResponse)
def get_prediction(
    prediction_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Get a specific risk prediction with SHAP explainability data."""
    prediction = get_prediction_by_id(db, prediction_id, user_id)
    return _format_prediction(prediction)


@router.post("/direct", response_model=RiskPredictionResponse)
def predict_risk_direct(
    data: RiskPredictionRequest,
    user_id: UUID = Depends(get_current_user_id),
):
    """
    Direct risk prediction endpoint (internal/testing only).
    
    Accepts 15 raw feature values directly and returns v3 prediction with SHAP.
    """
    if not ENABLE_DIRECT_PREDICTION_ENDPOINT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Direct prediction endpoint is disabled."
        )

    patient_dict = data.model_dump()
    try:
        result = predict_risk(patient_dict)
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )

    # Compute SHAP values in probability space
    explanation = compute_shap_values(patient_dict, result)

    # Construct transient mock prediction record for response formatting
    class TransientPrediction:
        def __init__(self):
            self.id = uuid.uuid4()
            self.disease_type = "heart_disease"
            self.probability = result["risk_probability"]
            self.confidence = 0.95
            self.risk_level = result["risk_band"]
            self.threshold_used = result["threshold_used"]
            self.risk_band = result["risk_band"]
            self.shap_values = explanation["shap_values"]
            self.feature_importance = explanation["feature_importance"]
            self.shap_explanation = explanation
            from datetime import datetime, timezone
            self.predicted_at = datetime.now(timezone.utc)

    return _format_prediction(TransientPrediction())


def _format_prediction(prediction) -> RiskPredictionResponse:
    """Format a prediction model into the response schema."""
    shap = None
    if prediction.shap_values:
        shap = ShapValues(
            features=prediction.shap_values.get("features", []),
            values=prediction.shap_values.get("values", []),
            base_value=prediction.shap_values.get("base_value", 0),
        )

    feature_imp = None
    if prediction.feature_importance:
        feature_imp = [
            FeatureImportance(
                feature=fi.get("feature", ""),
                importance=fi.get("importance", 0),
                direction=fi.get("direction", "unknown"),
            )
            for fi in prediction.feature_importance
        ]

    # Handle threshold_used and risk_band safety fallbacks
    threshold = getattr(prediction, "threshold_used", 0.4)
    band = getattr(prediction, "risk_band", prediction.risk_level)

    return RiskPredictionResponse(
        id=prediction.id,
        disease_type=prediction.disease_type,
        probability=prediction.probability,
        confidence=prediction.confidence,
        risk_level=prediction.risk_level,
        
        # New v3 fields
        risk_probability=prediction.probability,
        risk_band=band,
        flagged=(prediction.probability > threshold),
        threshold_used=threshold,
        shap_explanation=getattr(prediction, "shap_explanation", None),
        
        # Legacy fields
        shap_values=shap,
        feature_importance=feature_imp,
        
        predicted_at=prediction.predicted_at,
        disclaimer=settings.DISCLAIMER,
    )
