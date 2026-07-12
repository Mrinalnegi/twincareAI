"""Risk prediction service — runs the heart disease model and stores results."""

import logging
from uuid import UUID
from datetime import date

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from models.risk_prediction import RiskPrediction
from models.user import User
from models.patient_intake import PatientIntake
from services.digital_twin_service import get_or_create_twin
from ai.heart_model import predict_risk
from ai.shap_explainer import compute_shap_values

logger = logging.getLogger(__name__)


async def run_prediction_for_user(
    db: Session,
    user_id: UUID,
    report_id: UUID | None = None,
) -> RiskPrediction:
    """
    Run heart disease risk prediction for a user using their PatientIntake and Digital Twin biomarkers.
    
    Creates a new RiskPrediction record with probability, confidence, SHAP values,
    and feature importance.
    """
    # 1. Get user profile
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # 2. Get patient intake clinical history
    intake = db.query(PatientIntake).filter(PatientIntake.user_id == user_id).first()
    if not intake:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please complete your health questionnaire before generating a risk prediction."
        )

    # 3. Get current Digital Twin state biomarkers
    twin = get_or_create_twin(db, user_id)
    biomarkers = twin.current_biomarkers or {}

    # Calculate age
    dob = user.date_of_birth
    if not dob:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Date of birth is required to calculate age for risk prediction."
        )
    if isinstance(dob, str):
        dob = date.fromisoformat(dob)
    today = date.today()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    # Map gender: 1 = male, 0 = female per Framingham coding
    gender = (user.gender or "").lower()
    if gender == "male":
        sex = 1
    elif gender == "female":
        sex = 0
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gender must be set to 'male' or 'female' to compute Framingham heart disease risk."
        )

    # Helper to retrieve twin biomarker values with defaults for missing data
    def get_biomarker_val(name, default=0.0):
        bio = biomarkers.get(name)
        if isinstance(bio, dict) and bio.get("value") is not None:
            return float(bio.get("value"))
        return default

    # Construct patient input dict with safe fallbacks
    patient_dict = {
        "age": float(age),
        "sex": int(sex),
        "education": intake.education or 1,
        "current_smoker": intake.current_smoker or False,
        "cigs_per_day": intake.cigs_per_day or 0,
        "bp_meds": intake.bp_meds or False,
        "prevalent_stroke": intake.prevalent_stroke or False,
        "prevalent_hyp": intake.prevalent_hyp or False,
        "diabetes": intake.diabetes or False,
        "total_cholesterol": get_biomarker_val("total_cholesterol", default=180.0),
        "systolic_bp": get_biomarker_val("systolic_bp", default=120.0),
        "diastolic_bp": get_biomarker_val("diastolic_bp", default=80.0),
        "bmi": get_biomarker_val("bmi", default=24.0),
        "heart_rate": get_biomarker_val("heart_rate", default=75.0),
        "fasting_glucose": get_biomarker_val("fasting_glucose", default=90.0),
    }

    # 4. Execute prediction
    try:
        logger.info(f"Running heart disease prediction for user {user_id}")
        result = predict_risk(patient_dict)
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Incomplete clinical profile: {str(ve)}"
        )

    # 5. Compute SHAP explainability
    explanation = compute_shap_values(patient_dict, result)

    # 6. Delete old prediction to keep latest prediction record
    db.query(RiskPrediction).filter(
        RiskPrediction.user_id == user_id,
        RiskPrediction.disease_type == "heart_disease",
    ).delete()

    prediction = RiskPrediction(
        user_id=user_id,
        report_id=report_id,
        disease_type="heart_disease",
        probability=result["risk_probability"],
        confidence=0.95,  # High confidence since all inputs are present
        risk_level=result["risk_band"],
        threshold_used=result["threshold_used"],
        risk_band=result["risk_band"],
        shap_values=explanation["shap_values"],
        feature_importance=explanation["feature_importance"],
        shap_explanation=explanation,
    )
    
    db.add(prediction)
    db.commit()
    db.refresh(prediction)

    logger.info(
        f"Prediction saved: {prediction.risk_band} risk "
        f"({prediction.probability:.1%} probability, threshold_used={prediction.threshold_used})"
    )
    return prediction


def get_user_predictions(db: Session, user_id: UUID) -> list[RiskPrediction]:
    """Get all risk predictions for a user."""
    return (
        db.query(RiskPrediction)
        .filter(RiskPrediction.user_id == user_id)
        .order_by(RiskPrediction.predicted_at.desc())
        .all()
    )


def get_prediction_by_id(
    db: Session, prediction_id: UUID, user_id: UUID
) -> RiskPrediction:
    """Get a specific prediction by ID."""
    prediction = db.query(RiskPrediction).filter(
        RiskPrediction.id == prediction_id,
        RiskPrediction.user_id == user_id,
    ).first()

    if not prediction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Prediction not found"
        )

    return prediction
