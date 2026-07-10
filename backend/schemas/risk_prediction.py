"""Risk prediction schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from config import settings


class ShapValues(BaseModel):
    """SHAP explainability data for waterfall chart."""
    features: list[str]
    values: list[float]
    base_value: float


class FeatureImportance(BaseModel):
    """Single feature's importance in the prediction."""
    feature: str
    importance: float
    direction: str  # increases_risk / decreases_risk


class RiskPredictionRequest(BaseModel):
    """Request model for direct risk prediction endpoint validation."""
    age: float = Field(..., gt=0, lt=120, description="Age in years")
    sex: int = Field(..., ge=0, le=1, description="Gender (1=Male, 0=Female)")
    education: int = Field(..., ge=1, le=4, description="Education level (1=Some high school, 2=High school grad, 3=Some college, 4=College grad)")
    currentSmoker: int = Field(..., ge=0, le=1, description="Currently smoker status (0=No, 1=Yes)")
    cigsPerDay: float = Field(..., ge=0, description="Average cigarettes smoked per day")
    BPMeds: int = Field(..., ge=0, le=1, description="On blood pressure meds status (0=No, 1=Yes)")
    prevalentStroke: int = Field(..., ge=0, le=1, description="Prior stroke history status (0=No, 1=Yes)")
    prevalentHyp: int = Field(..., ge=0, le=1, description="Prior hypertension diagnosis status (0=No, 1=Yes)")
    diabetes: int = Field(..., ge=0, le=1, description="Diabetes diagnosis status (0=No, 1=Yes)")
    total_cholesterol: float = Field(..., ge=80, le=600, description="Total cholesterol (mg/dL)")
    systolic_bp: float = Field(..., ge=70, le=250, description="Systolic blood pressure (mmHg)")
    diastolic_bp: float = Field(..., ge=40, le=150, description="Diastolic blood pressure (mmHg)")
    bmi: float = Field(..., ge=10, le=60, description="Body Mass Index (BMI)")
    heart_rate: float = Field(..., ge=30, le=200, description="Heart rate (beats per minute)")
    fasting_glucose: float = Field(..., ge=40, le=500, description="Fasting blood glucose (mg/dL)")


class RiskPredictionResponse(BaseModel):
    """Single risk prediction response."""
    id: UUID
    disease_type: str
    probability: float
    confidence: float
    risk_level: str
    
    # New v3 fields
    risk_probability: float
    risk_band: str
    flagged: bool
    threshold_used: float
    shap_explanation: dict | None = None
    
    # Legacy fields (kept for backward compatibility)
    shap_values: ShapValues | None = None
    feature_importance: list[FeatureImportance] | None = None
    
    predicted_at: datetime
    disclaimer: str = settings.DISCLAIMER

    model_config = {"from_attributes": True}


class RiskPredictionListResponse(BaseModel):
    """List of risk predictions."""
    predictions: list[RiskPredictionResponse]
