"""
models.py
---------
SQLAlchemy ORM table definitions.
Three tables: users, otps, screening_results.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Boolean, DateTime,
    Float, Text, ForeignKey, Integer,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    otps = relationship("OTP", back_populates="user", cascade="all, delete-orphan")
    screening_results = relationship(
        "ScreeningResult",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<User email={self.email} verified={self.is_verified}>"


class OTP(Base):
    __tablename__ = "otps"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # We store the HASH of the OTP, never plaintext
    hashed_otp = Column(String(255), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="otps")

    def __repr__(self):
        return f"<OTP user_id={self.user_id} used={self.is_used}>"


class ScreeningResult(Base):
    __tablename__ = "screening_results"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_id = Column(String(36), nullable=False, index=True)  # groups a batch run
    candidate_name = Column(String(255), nullable=True)
    filename = Column(String(255), nullable=False)
    score = Column(Float, nullable=False)
    recommendation = Column(String(50), nullable=False)  # Strong Fit / Moderate / Not Fit
    strengths = Column(Text, nullable=True)   # JSON array stored as text
    gaps = Column(Text, nullable=True)        # JSON array stored as text
    resume_text = Column(Text, nullable=True)
    job_description = Column(Text, nullable=True)
    rank = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="screening_results")

    def __repr__(self):
        return f"<ScreeningResult {self.candidate_name} score={self.score}>"