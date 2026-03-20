"""
models.py
---------
SQLAlchemy ORM — four tables:
  users, otps, screening_projects, screening_results

New: ScreeningProject
  - A named "sheet" that groups one or more screening runs
  - One project has many ScreeningResults (via project_id FK)
  - Users see their project list on the dashboard home page
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

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email           = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_verified     = Column(Boolean, default=False, nullable=False)
    is_active       = Column(Boolean, default=True,  nullable=False)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    otps              = relationship("OTP",              back_populates="user", cascade="all, delete-orphan")
    screening_results = relationship("ScreeningResult",  back_populates="user", cascade="all, delete-orphan")
    projects          = relationship("ScreeningProject", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.email}>"


class OTP(Base):
    __tablename__ = "otps"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    hashed_otp = Column(String(255), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_used    = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="otps")


class ScreeningProject(Base):
    """
    A named screening sheet created by the user.
    Groups one or more screening sessions under a human-readable title
    (e.g. "Q3 Backend Hiring", "ML Engineer Round 2").
    """
    __tablename__ = "screening_projects"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id     = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title       = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user    = relationship("User",            back_populates="projects")
    results = relationship("ScreeningResult", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ScreeningProject '{self.title}'>"


class ScreeningResult(Base):
    __tablename__ = "screening_results"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id         = Column(UUID(as_uuid=True), ForeignKey("users.id",              ondelete="CASCADE"), nullable=False, index=True)
    project_id      = Column(UUID(as_uuid=True), ForeignKey("screening_projects.id", ondelete="CASCADE"), nullable=True,  index=True)
    session_id      = Column(String(36),  nullable=False, index=True)
    candidate_name  = Column(String(255), nullable=True)
    filename        = Column(String(255), nullable=False)
    score           = Column(Float,       nullable=False)
    recommendation  = Column(String(50),  nullable=False)
    strengths       = Column(Text,        nullable=True)
    gaps            = Column(Text,        nullable=True)
    resume_text     = Column(Text,        nullable=True)
    job_description = Column(Text,        nullable=True)
    rank            = Column(Integer,     nullable=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    user    = relationship("User",             back_populates="screening_results")
    project = relationship("ScreeningProject", back_populates="results")

    def __repr__(self):
        return f"<ScreeningResult {self.candidate_name} score={self.score}>"