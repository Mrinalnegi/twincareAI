"""Risk prediction model for disease risk assessments."""

import uuid
from datetime import datetime

from sqlalchemy import String, Float, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class RiskPrediction(Base):
    __tablename__ = "risk_predictions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    report_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("reports.id", ondelete="SET NULL"), nullable=True
    )
    disease_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # heart_disease, diabetes, etc.
    probability: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    risk_level: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # low, moderate, high, very_high
    threshold_used: Mapped[float] = mapped_column(Float, nullable=False, default=0.4)
    risk_band: Mapped[str] = mapped_column(String(20), nullable=False, default="low")
    # SHAP values: {features: [...], values: [...], base_value: float}
    shap_values: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Feature importance: [{feature, importance, direction}, ...]
    feature_importance: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    shap_explanation: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    predicted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    user = relationship("User", back_populates="risk_predictions")
    report = relationship("Report", back_populates="risk_predictions")
