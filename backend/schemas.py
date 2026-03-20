"""
schemas.py
----------
Pydantic request/response models (data validation + serialization).
Completely separate from SQLAlchemy ORM models.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


# ── Auth schemas ──────────────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class OTPVerifyRequest(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=6, max_length=6)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: UUID
    email: str
    is_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Resume / Screening schemas ────────────────────────────────────────────────

class ParsedResume(BaseModel):
    """Structured output from Groq LLM resume parser."""
    name: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    experience: List[str] = Field(default_factory=list)
    projects: List[str] = Field(default_factory=list)
    education: List[str] = Field(default_factory=list)


class CandidateResult(BaseModel):
    """Score + analysis for a single candidate."""
    filename: str
    candidate_name: Optional[str]
    score: float = Field(ge=0, le=100)
    skill_match_score: float
    semantic_score: float
    strengths: List[str]
    gaps: List[str]
    recommendation: str
    rank: Optional[int] = None


class ScreeningResponse(BaseModel):
    """Response for a full screening batch."""
    session_id: str
    total_candidates: int
    results: List[CandidateResult]


class ScreeningResultDB(BaseModel):
    """For returning saved results from DB."""
    id: UUID
    session_id: str
    candidate_name: Optional[str]
    filename: str
    score: float
    recommendation: str
    strengths: Optional[str]
    gaps: Optional[str]
    rank: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Generic responses ─────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str


class ErrorResponse(BaseModel):
    detail: str