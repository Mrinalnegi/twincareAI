"""User model for authentication and profile data."""

import uuid
from datetime import datetime

from sqlalchemy import String, Date, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    date_of_birth: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    reports = relationship("Report", back_populates="user", cascade="all, delete-orphan")
    digital_twin = relationship(
        "DigitalTwinState", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    patient_intake = relationship(
        "PatientIntake", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    risk_predictions = relationship(
        "RiskPrediction", back_populates="user", cascade="all, delete-orphan"
    )
    chat_messages = relationship(
        "ChatMessage", back_populates="user", cascade="all, delete-orphan"
    )
