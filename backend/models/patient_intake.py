"""Patient intake database model — stores clinical questionnaire history."""

import uuid
from datetime import datetime

from sqlalchemy import String, Integer, Boolean, ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class PatientIntake(Base):
    __tablename__ = "patient_intake"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    
    # 7 Intake Fields
    education: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_smoker: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    cigs_per_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bp_meds: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    prevalent_stroke: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    prevalent_hyp: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    diabetes: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user = relationship("User", back_populates="patient_intake")
