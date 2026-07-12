"""Patient intake validation schemas."""

from uuid import UUID
from pydantic import BaseModel, Field


class PatientIntakeBase(BaseModel):
    """Base schema for patient intake clinical history."""
    education: int | None = Field(None, ge=1, le=4, description="Education level (1-4)")
    current_smoker: bool | None = Field(None, description="Is currently a smoker")
    cigs_per_day: int | None = Field(None, ge=0, description="Average cigarettes per day")
    bp_meds: bool | None = Field(None, description="Is currently on blood pressure medication")
    prevalent_stroke: bool | None = Field(None, description="Has history of stroke")
    prevalent_hyp: bool | None = Field(None, description="Has history of hypertension")
    diabetes: bool | None = Field(None, description="Has diabetes")
    doctors_prescription: str | None = Field(None, description="Current doctors prescription notes")


class PatientIntakeCreate(PatientIntakeBase):
    """Request body for creating/updating patient intake clinical history."""
    pass


class PatientIntakeResponse(PatientIntakeBase):
    """Response body returning patient intake clinical history."""
    user_id: UUID

    model_config = {"from_attributes": True}
