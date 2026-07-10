"""Patient intake API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models.patient_intake import PatientIntake
from schemas.patient_intake import PatientIntakeCreate, PatientIntakeResponse
from utils.security import get_current_user_id

router = APIRouter(prefix="/patient-intake", tags=["Patient Intake"])


@router.get("", response_model=PatientIntakeResponse)
def get_intake(
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Retrieve the current user's clinical intake questionnaire."""
    intake = db.query(PatientIntake).filter(PatientIntake.user_id == user_id).first()
    if not intake:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient intake questionnaire has not been completed yet."
        )
    return intake


@router.post("", response_model=PatientIntakeResponse)
def create_or_update_intake(
    data: PatientIntakeCreate,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Create or update the current user's clinical intake questionnaire."""
    intake = db.query(PatientIntake).filter(PatientIntake.user_id == user_id).first()
    
    if intake:
        # Update existing intake record
        for field, val in data.model_dump(exclude_unset=True).items():
            setattr(intake, field, val)
    else:
        # Create new intake record
        intake = PatientIntake(
            user_id=user_id,
            **data.model_dump()
        )
        db.add(intake)
        
    db.commit()
    db.refresh(intake)
    return intake
