"""
shap_explainer.py — SHAP explainability for TwinCare's CVD risk model.

Computes exact per-feature SHAP contributions in probability space
using PermutationExplainer on the calibrated model's probability predictions.
"""

import logging
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import shap

logger = logging.getLogger(__name__)

# Cache explainer globally to avoid reloading on every request
_explainer = None

DISPLAY_NAMES = {
    "age": "Age",
    "sex": "Sex",
    "education": "Education",
    "currentSmoker": "Current Smoker",
    "cigsPerDay": "Cigarettes Per Day",
    "BPMeds": "BP Medication",
    "prevalentStroke": "Prior Stroke",
    "prevalentHyp": "Prior Hypertension",
    "diabetes": "Diabetes",
    "total_cholesterol": "Total Cholesterol",
    "systolic_bp": "Systolic BP",
    "diastolic_bp": "Diastolic BP",
    "bmi": "BMI",
    "heart_rate": "Heart Rate",
    "fasting_glucose": "Fasting Glucose",
    "pulse_pressure": "Pulse Pressure",
    "map": "Mean Arterial Pressure",
}


def _load_explainer():
    """Load the shap.Explainer cached instance."""
    global _explainer
    if _explainer is None:
        from ai.heart_model import _load, FEATURE_NAMES
        model, _ = _load()
        bg_path = Path(__file__).parent / "background_sample.joblib"
        if not bg_path.exists():
            raise FileNotFoundError(f"Background sample file not found at {bg_path}")
        background_sample = joblib.load(bg_path)
        
        # Blackbox prediction function returning calibrated positive class probability.
        # Wrap inputs in a pandas DataFrame to avoid scikit-learn feature name warnings.
        def predict_prob_pos(x):
            df = pd.DataFrame(x, columns=FEATURE_NAMES)
            return model.predict_proba(df)[:, 1]
            
        _explainer = shap.Explainer(
            predict_prob_pos,
            background_sample
        )
    return _explainer


def compute_shap_values(patient_dict: dict, prediction_result: dict) -> dict:
    """
    Compute exact SHAP values in probability space for a user prediction.
    
    Returns:
        dict with:
            - "shap_values": {"features": [...], "values": [...], "base_value": float}
            - "feature_importance": [{"feature": str, "importance": float, "direction": str, "actual_value": float, "source": str}]
    """
    from ai.heart_model import build_feature_vector, _load, FEATURE_NAMES

    # Load model, scaler, and explainer
    _, scaler = _load()
    explainer = _load_explainer()

    # Reconstruct patient vector (17 features)
    X = build_feature_vector(patient_dict)
    X_scaled = scaler.transform(X)

    # Compute probability space SHAP values
    explanation = explainer(X_scaled)

    # Extract positive class SHAP values and base value
    shap_values_pos = explanation.values[0]
    base_value = float(explanation.base_values[0])

    shap_values_list = [float(v) for v in shap_values_pos]
    features_display = [DISPLAY_NAMES.get(name, name) for name in FEATURE_NAMES]

    # SHAP output dictionary
    shap_output = {
        "features": features_display,
        "values": [round(v, 4) for v in shap_values_list],
        "base_value": round(base_value, 4),
    }

    # Extract raw feature values for the feature importance list
    raw_feature_values = X[0]

    # Map to structured feature importance list
    feature_importance = []
    for name, val, shap_val in zip(FEATURE_NAMES, raw_feature_values, shap_values_list):
        direction = "increases_risk" if shap_val > 0 else "decreases_risk"
        feature_importance.append({
            "feature": DISPLAY_NAMES.get(name, name),
            "importance": round(abs(shap_val), 4),
            "direction": direction,
            "actual_value": round(float(val), 2),
            "source": "actual",
        })

    # Sort feature importance list by absolute impact descending
    feature_importance.sort(key=lambda x: x["importance"], reverse=True)

    return {
        "shap_values": shap_output,
        "feature_importance": feature_importance,
    }
