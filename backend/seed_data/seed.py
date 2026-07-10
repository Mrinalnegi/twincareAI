"""
Seed script — populates the database with demo data for presentations.

Run: python seed_data/seed.py

Creates a demo user with pre-populated patient intake, biomarkers,
digital twin state, and v3 risk prediction so the dashboard immediately shows data.
"""

import sys
import os
from datetime import date, datetime, timezone
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import SessionLocal, create_tables
from models.user import User
from models.report import Report
from models.biomarker import Biomarker
from models.digital_twin import DigitalTwinState
from models.risk_prediction import RiskPrediction
from models.chat_message import ChatMessage
from models.patient_intake import PatientIntake
from utils.security import hash_password


def seed_database():
    """Create demo data."""
    create_tables()
    db = SessionLocal()

    try:
        # Check if demo user exists
        existing = db.query(User).filter(User.email == "demo@twincare.ai").first()
        if existing:
            print("Demo user already exists. Skipping seed.")
            return

        # Create demo user
        user = User(
            email="demo@twincare.ai",
            password_hash=hash_password("demo123"),
            full_name="Alex Johnson",
            date_of_birth=date(1985, 6, 15),
            gender="male",
        )
        db.add(user)
        db.flush()
        print(f"✅ Demo user created: demo@twincare.ai / demo123")

        # Create patient intake clinical history for demo user
        intake = PatientIntake(
            user_id=user.id,
            education=2,
            current_smoker=True,
            cigs_per_day=10,
            bp_meds=False,
            prevalent_stroke=False,
            prevalent_hyp=True,
            diabetes=False,
        )
        db.add(intake)
        db.flush()
        print(f"✅ Patient intake clinical history created for demo user")

        # Create a demo report (simulating an already-processed upload)
        report = Report(
            user_id=user.id,
            file_path="seed_data/sample_reports/demo_blood_report.pdf",
            file_type="pdf",
            original_filename="blood_report_2024.pdf",
            status="extracted",
            raw_text={
                "pages": "COMPLETE BLOOD COUNT AND METABOLIC PANEL\n"
                         "Patient: Alex Johnson  DOB: 06/15/1985  Sex: Male\n\n"
                         "LIPID PANEL:\n"
                         "Total Cholesterol: 242 mg/dL (Ref: 125-200) HIGH\n"
                         "LDL Cholesterol: 158 mg/dL (Ref: 0-100) HIGH\n"
                         "HDL Cholesterol: 42 mg/dL (Ref: 40-100) LOW\n"
                         "Triglycerides: 185 mg/dL (Ref: 0-150) HIGH\n"
                         "VLDL Cholesterol: 37 mg/dL (Ref: 2-30) HIGH\n\n"
                         "BLOOD SUGAR:\n"
                         "Fasting Glucose: 112 mg/dL (Ref: 70-100) HIGH\n"
                         "HbA1c: 5.9% (Ref: 4.0-5.7) HIGH\n\n"
                         "VITALS:\n"
                         "Blood Pressure: 145/90 mmHg HIGH\n"
                         "BMI: 28.5 kg/m2 OVERWEIGHT\n"
                         "Heart Rate: 78 bpm NORMAL\n\n"
                         "COMPLETE BLOOD COUNT:\n"
                         "Hemoglobin: 14.8 g/dL (Ref: 12.0-17.5) NORMAL\n"
                         "RBC Count: 5.2 million/µL (Ref: 4.0-6.0) NORMAL\n"
                         "WBC Count: 7200 /µL (Ref: 4000-11000) NORMAL\n"
                         "Platelet Count: 245000 /µL (Ref: 150000-400000) NORMAL\n\n"
                         "LIVER FUNCTION:\n"
                         "SGOT (AST): 32 U/L (Ref: 0-40) NORMAL\n"
                         "SGPT (ALT): 38 U/L (Ref: 0-40) NORMAL\n"
                         "Total Bilirubin: 0.9 mg/dL (Ref: 0.1-1.2) NORMAL\n"
                         "Albumin: 4.2 g/dL (Ref: 3.5-5.5) NORMAL\n\n"
                         "KIDNEY FUNCTION:\n"
                         "Creatinine: 1.0 mg/dL (Ref: 0.6-1.2) NORMAL\n"
                         "Blood Urea Nitrogen: 16 mg/dL (Ref: 7-20) NORMAL\n"
                         "Uric Acid: 6.8 mg/dL (Ref: 3.4-7.0) NORMAL\n\n"
                         "THYROID:\n"
                         "TSH: 2.8 mIU/L (Ref: 0.4-4.0) NORMAL\n\n"
                         "VITAMINS:\n"
                         "Vitamin D: 22 ng/mL (Ref: 30-100) LOW\n"
                         "Vitamin B12: 380 pg/mL (Ref: 200-900) NORMAL",
                "char_count": 1350,
            },
            processed_at=datetime.now(timezone.utc),
        )
        db.add(report)
        db.flush()
        print(f"✅ Demo report created")

        # Create biomarkers
        biomarker_data = [
            ("Total Cholesterol", 242.0, "mg/dL", "125-200 mg/dL", "high"),
            ("LDL Cholesterol", 158.0, "mg/dL", "0-100 mg/dL", "high"),
            ("HDL Cholesterol", 42.0, "mg/dL", "40-100 mg/dL", "normal"),
            ("Triglycerides", 185.0, "mg/dL", "0-150 mg/dL", "high"),
            ("VLDL Cholesterol", 37.0, "mg/dL", "2-30 mg/dL", "high"),
            ("Fasting Glucose", 112.0, "mg/dL", "70-100 mg/dL", "high"),
            ("HbA1c", 5.9, "%", "4.0-5.7 %", "high"),
            ("Systolic BP", 145.0, "mmHg", "90-120 mmHg", "high"),
            ("Diastolic BP", 90.0, "mmHg", "60-80 mmHg", "high"),
            ("BMI", 28.5, "kg/m2", "18.5-24.9 kg/m2", "high"),
            ("Heart Rate", 78.0, "bpm", "60-100 bpm", "normal"),
            ("Hemoglobin", 14.8, "g/dL", "12.0-17.5 g/dL", "normal"),
            ("RBC Count", 5.2, "million/µL", "4.0-6.0 million/µL", "normal"),
            ("WBC Count", 7200.0, "/µL", "4000-11000 /µL", "normal"),
            ("Platelet Count", 245000.0, "/µL", "150000-400000 /µL", "normal"),
            ("SGOT (AST)", 32.0, "U/L", "0-40 U/L", "normal"),
            ("SGPT (ALT)", 38.0, "U/L", "0-40 U/L", "normal"),
            ("Total Bilirubin", 0.9, "mg/dL", "0.1-1.2 mg/dL", "normal"),
            ("Albumin", 4.2, "g/dL", "3.5-5.5 g/dL", "normal"),
            ("Creatinine", 1.0, "mg/dL", "0.6-1.2 mg/dL", "normal"),
            ("Blood Urea Nitrogen", 16.0, "mg/dL", "7-20 mg/dL", "normal"),
            ("Uric Acid", 6.8, "mg/dL", "3.4-7.0 mg/dL", "normal"),
            ("TSH", 2.8, "mIU/L", "0.4-4.0 mIU/L", "normal"),
            ("Vitamin D", 22.0, "ng/mL", "30-100 ng/mL", "low"),
            ("Vitamin B12", 380.0, "pg/mL", "200-900 pg/mL", "normal"),
        ]

        for name, value, unit, ref_range, status in biomarker_data:
            bio = Biomarker(
                report_id=report.id,
                user_id=user.id,
                name=name,
                value=value,
                unit=unit,
                reference_range=ref_range,
                status=status,
            )
            db.add(bio)
        print(f"✅ {len(biomarker_data)} biomarkers created")

        # Create Digital Twin state
        twin = DigitalTwinState(
            user_id=user.id,
            current_biomarkers={
                "total_cholesterol": {"value": 242.0, "unit": "mg/dL", "status": "high", "display_name": "Total Cholesterol", "recorded_at": datetime.now(timezone.utc).isoformat()},
                "ldl_cholesterol": {"value": 158.0, "unit": "mg/dL", "status": "high", "display_name": "LDL Cholesterol", "recorded_at": datetime.now(timezone.utc).isoformat()},
                "hdl_cholesterol": {"value": 42.0, "unit": "mg/dL", "status": "normal", "display_name": "HDL Cholesterol", "recorded_at": datetime.now(timezone.utc).isoformat()},
                "triglycerides": {"value": 185.0, "unit": "mg/dL", "status": "high", "display_name": "Triglycerides", "recorded_at": datetime.now(timezone.utc).isoformat()},
                "fasting_glucose": {"value": 112.0, "unit": "mg/dL", "status": "high", "display_name": "Fasting Glucose", "recorded_at": datetime.now(timezone.utc).isoformat()},
                "systolic_bp": {"value": 145.0, "unit": "mmHg", "status": "high", "display_name": "Systolic BP", "recorded_at": datetime.now(timezone.utc).isoformat()},
                "diastolic_bp": {"value": 90.0, "unit": "mmHg", "status": "high", "display_name": "Diastolic BP", "recorded_at": datetime.now(timezone.utc).isoformat()},
                "bmi": {"value": 28.5, "unit": "kg/m2", "status": "high", "display_name": "BMI", "recorded_at": datetime.now(timezone.utc).isoformat()},
                "heart_rate": {"value": 78.0, "unit": "bpm", "status": "normal", "display_name": "Heart Rate", "recorded_at": datetime.now(timezone.utc).isoformat()},
                "hba1c": {"value": 5.9, "unit": "%", "status": "high", "display_name": "HbA1c", "recorded_at": datetime.now(timezone.utc).isoformat()},
                "hemoglobin": {"value": 14.8, "unit": "g/dL", "status": "normal", "display_name": "Hemoglobin", "recorded_at": datetime.now(timezone.utc).isoformat()},
                "sgot_ast": {"value": 32.0, "unit": "U/L", "status": "normal", "display_name": "SGOT (AST)", "recorded_at": datetime.now(timezone.utc).isoformat()},
                "sgpt_alt": {"value": 38.0, "unit": "U/L", "status": "normal", "display_name": "SGPT (ALT)", "recorded_at": datetime.now(timezone.utc).isoformat()},
                "creatinine": {"value": 1.0, "unit": "mg/dL", "status": "normal", "display_name": "Creatinine", "recorded_at": datetime.now(timezone.utc).isoformat()},
                "tsh": {"value": 2.8, "unit": "mIU/L", "status": "normal", "display_name": "TSH", "recorded_at": datetime.now(timezone.utc).isoformat()},
                "vitamin_d": {"value": 22.0, "unit": "ng/mL", "status": "low", "display_name": "Vitamin D", "recorded_at": datetime.now(timezone.utc).isoformat()},
            },
            health_score=72.5,
            organ_scores={
                "heart": 0.52,
                "liver": 1.0,
                "kidney": 1.0,
                "blood": 1.0,
                "metabolic": 0.6,
                "thyroid": 1.0,
            },
        )
        db.add(twin)
        print(f"✅ Digital Twin state created (health_score=72.5)")

        # Create v3 risk prediction structure
        shap_explanation = {
            "shap_values": {
                "features": ["Systolic BP", "Total Cholesterol", "Fasting Glucose", "Age", "Cigarettes Per Day", "Diastolic BP", "BMI", "Heart Rate", "Prior Hypertension"],
                "values": [0.08, 0.06, 0.04, 0.03, 0.02, 0.01, 0.005, 0.003, 0.002],
                "base_value": 0.15
            },
            "feature_importance": [
                {"feature": "Systolic BP", "importance": 0.08, "direction": "increases_risk", "actual_value": 145.0, "source": "actual"},
                {"feature": "Total Cholesterol", "importance": 0.06, "direction": "increases_risk", "actual_value": 242.0, "source": "actual"},
                {"feature": "Fasting Glucose", "importance": 0.04, "direction": "increases_risk", "actual_value": 112.0, "source": "actual"},
                {"feature": "Age", "importance": 0.03, "direction": "increases_risk", "actual_value": 41.0, "source": "actual"},
                {"feature": "Cigarettes Per Day", "importance": 0.02, "direction": "increases_risk", "actual_value": 10.0, "source": "actual"},
                {"feature": "Diastolic BP", "importance": 0.01, "direction": "increases_risk", "actual_value": 90.0, "source": "actual"},
            ]
        }

        prediction = RiskPrediction(
            user_id=user.id,
            report_id=report.id,
            disease_type="heart_disease",
            probability=0.34,
            confidence=0.95,
            risk_level="moderate",
            threshold_used=0.4,
            risk_band="moderate",
            shap_values=shap_explanation["shap_values"],
            feature_importance=shap_explanation["feature_importance"],
            shap_explanation=shap_explanation,
        )
        db.add(prediction)
        print(f"✅ Heart disease risk prediction created (34% moderate risk, threshold=0.4)")

        # Create demo chat messages
        chat_messages = [
            ChatMessage(
                user_id=user.id,
                role="user",
                content="What does my cholesterol level mean?",
            ),
            ChatMessage(
                user_id=user.id,
                role="assistant",
                content=(
                    "Based on your latest blood report, your Total Cholesterol is 242 mg/dL, "
                    "which is above the desirable range of 125-200 mg/dL. Your LDL ('bad') "
                    "cholesterol is 158 mg/dL (optimal is below 100 mg/dL), and your HDL "
                    "('good') cholesterol is 42 mg/dL, which is on the lower end.\n\n"
                    "High LDL and total cholesterol levels can contribute to plaque buildup "
                    "in your arteries, which may increase your risk of heart disease over time. "
                    "The good news is that lifestyle changes — such as a heart-healthy diet, "
                    "regular exercise, and maintaining a healthy weight — can significantly "
                    "improve your cholesterol levels.\n\n"
                    "⚠️ This is not a medical diagnosis. Always consult a qualified healthcare "
                    "professional for medical advice."
                ),
                context_used={
                    "references": [
                        "biomarker:total_cholesterol",
                        "biomarker:ldl_cholesterol",
                        "biomarker:hdl_cholesterol",
                    ]
                },
            ),
        ]

        for msg in chat_messages:
            db.add(msg)
        print(f"✅ Demo chat history created")

        db.commit()
        print("\n🎉 Database seeded successfully!")
        print("   Login: demo@twincare.ai / demo123")

    except Exception as e:
        db.rollback()
        print(f"❌ Seed failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
