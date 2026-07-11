"""
heart_model.py — inference module for TwinCare's CVD risk model.

Loads the v3 LightGBM model (trained on Framingham, real features only,
class-weighted, honestly cross-validated).
"""

from pathlib import Path
import joblib
import numpy as np
import logging

logger = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).parent
MODEL_PATH = MODEL_DIR / "heart_disease_model_v3_lgb.joblib"
SCALER_PATH = MODEL_DIR / "scaler_v3.joblib"

# Order matters — must exactly match training order
FEATURE_NAMES = [
    "age", "sex", "education", "currentSmoker", "cigsPerDay",
    "BPMeds", "prevalentStroke", "prevalentHyp", "diabetes",
    "total_cholesterol", "systolic_bp", "diastolic_bp", "bmi",
    "heart_rate", "fasting_glucose", "pulse_pressure", "map",
]

DECISION_THRESHOLD = 0.15  # Optimized screening threshold. At training baseline 0.40: AUC 0.664, precision 22.1%, recall 64.9%, F1 0.330

# Calibrated risk bands aligned with clinical guidelines (e.g. ACC/AHA CHD risk categories)
RISK_BANDS = [
    (0.0, 0.05, "low"),
    (0.05, 0.15, "moderate"),
    (0.15, 1.01, "elevated"),
]

_model = None
_scaler = None


def _load():
    """Load LightGBM model + scaler."""
    global _model, _scaler
    if _model is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(f"Model file not found at {MODEL_PATH}")
        if not SCALER_PATH.exists():
            raise FileNotFoundError(f"Scaler file not found at {SCALER_PATH}")
        _model = joblib.load(MODEL_PATH)
        _scaler = joblib.load(SCALER_PATH)
    return _model, _scaler


def load_model():
    """Compatibility wrapper around _load() so main.py startup check doesn't break."""
    try:
        model, _ = _load()
        return model
    except Exception as e:
        logger.error(f"Failed to load model in startup wrapper: {e}")
        return None


def _risk_band(prob: float) -> str:
    for lo, hi, label in RISK_BANDS:
        if lo <= prob < hi:
            return label
    return "elevated"


def build_feature_vector(patient: dict) -> np.ndarray:
    """
    Build 17-feature input vector from 15 raw features.
    
    Accepts keys in either snake_case or camelCase:
      age, sex (1=male/0=female), education (1-4), current_smoker/currentSmoker, 
      cigs_per_day/cigsPerDay, bp_meds/BPMeds, prevalent_stroke/prevalentStroke, 
      prevalent_hyp/prevalentHyp, diabetes, total_cholesterol, systolic_bp, 
      diastolic_bp, bmi, heart_rate, fasting_glucose
    """
    raw_keys_map = {
        "age": "age",
        "sex": "sex",
        "education": "education",
        "currentSmoker": "currentSmoker",
        "current_smoker": "currentSmoker",
        "cigsPerDay": "cigsPerDay",
        "cigs_per_day": "cigsPerDay",
        "BPMeds": "BPMeds",
        "bp_meds": "BPMeds",
        "prevalentStroke": "prevalentStroke",
        "prevalent_stroke": "prevalentStroke",
        "prevalentHyp": "prevalentHyp",
        "prevalent_hyp": "prevalentHyp",
        "diabetes": "diabetes",
        "total_cholesterol": "total_cholesterol",
        "systolic_bp": "systolic_bp",
        "diastolic_bp": "diastolic_bp",
        "bmi": "bmi",
        "heart_rate": "heart_rate",
        "fasting_glucose": "fasting_glucose",
    }

    # Map input keys to model-expected keys
    values = {}
    for input_k, input_v in patient.items():
        if input_k in raw_keys_map:
            values[raw_keys_map[input_k]] = input_v

    required_raw = [
        "age", "sex", "education", "currentSmoker", "cigsPerDay",
        "BPMeds", "prevalentStroke", "prevalentHyp", "diabetes",
        "total_cholesterol", "systolic_bp", "diastolic_bp", "bmi",
        "heart_rate", "fasting_glucose",
    ]

    # Explicitly check for missing or None values
    missing = [k for k in required_raw if k not in values or values[k] is None]
    if missing:
        raise ValueError(f"Missing required clinical history: {missing}")

    # Explicitly cast boolean fields to integer (0 or 1)
    bool_fields = ["currentSmoker", "BPMeds", "prevalentStroke", "prevalentHyp", "diabetes"]
    for field in bool_fields:
        values[field] = int(bool(values[field]))

    # Compute clinical derived features
    values["pulse_pressure"] = float(values["systolic_bp"]) - float(values["diastolic_bp"])
    values["map"] = float(values["diastolic_bp"]) + (float(values["systolic_bp"]) - float(values["diastolic_bp"])) / 3.0

    # Ensure all raw values are float/int
    for name in FEATURE_NAMES:
        values[name] = float(values[name])

    return np.array([[values[name] for name in FEATURE_NAMES]], dtype=np.float32)


def predict_risk(patient: dict) -> dict:
    """
    Predict heart disease risk.
    
    Returns:
      {
        "risk_probability": float,        # 0-1
        "risk_band": str,                 # "low" | "moderate" | "elevated"
        "flagged": bool,                  # probability > DECISION_THRESHOLD
        "threshold_used": float,
      }
    """
    model, scaler = _load()
    X = build_feature_vector(patient)
    X_scaled = scaler.transform(X)
    prob = float(model.predict_proba(X_scaled)[0, 1])

    return {
        "risk_probability": round(prob, 4),
        "risk_band": _risk_band(prob),
        "flagged": prob > DECISION_THRESHOLD,
        "threshold_used": DECISION_THRESHOLD,
    }
