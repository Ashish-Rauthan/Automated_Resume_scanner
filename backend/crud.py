"""
crud.py
-------
Database CRUD operations.
All DB logic lives here — routes stay thin, models stay clean.

Functions:
    save_screening_results()    -> persist a batch of ranked results
    get_results_by_session()    -> fetch all results for a session
    get_sessions_by_user()      -> list all sessions for a user
    get_result_by_id()          -> fetch one result by PK
    delete_session_results()    -> delete all results in a session

Design:
    - Every function takes a `db: Session` parameter (injected via Depends)
    - No commits inside individual helpers — caller decides when to commit
      (exception: save_screening_results commits its own batch for atomicity)
    - All functions return ORM objects or None — never raise on missing data
"""

import json
import logging
import uuid
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import desc

from models import ScreeningResult, User
from schemas import CandidateResult

logger = logging.getLogger(__name__)


# ── Screening Results ─────────────────────────────────────────────────────────

def save_screening_results(
    db: Session,
    user_id: UUID,
    session_id: str,
    results: list[CandidateResult],
    job_description: str,
) -> list[ScreeningResult]:
    """
    Persist a full ranked batch of screening results atomically.

    Args:
        db:              SQLAlchemy session
        user_id:         Authenticated user UUID
        session_id:      Batch identifier (same for all results in one run)
        results:         Ranked list from score_candidates()
        job_description: Original JD text (stored for auditability)

    Returns:
        List of persisted ScreeningResult ORM objects.

    Notes:
        - Stores strengths and gaps as JSON strings (TEXT column)
        - Truncates JD to 5000 chars to keep row size manageable
        - Commits as a single transaction — all or nothing
    """
    orm_objects: list[ScreeningResult] = []

    for result in results:
        db_result = ScreeningResult(
            id=uuid.uuid4(),
            user_id=user_id,
            session_id=session_id,
            candidate_name=result.candidate_name,
            filename=result.filename,
            score=result.score,
            recommendation=result.recommendation,
            strengths=json.dumps(result.strengths),
            gaps=json.dumps(result.gaps),
            rank=result.rank,
            job_description=job_description[:5000],
        )
        db.add(db_result)
        orm_objects.append(db_result)

    try:
        db.commit()
        for obj in orm_objects:
            db.refresh(obj)
        logger.info(
            "Saved %d screening results for session %s",
            len(orm_objects), session_id,
        )
    except Exception as e:
        db.rollback()
        logger.error("Failed to save screening results: %s", e)
        raise

    return orm_objects


def get_results_by_session(
    db: Session,
    session_id: str,
    user_id: UUID,
) -> list[ScreeningResult]:
    """
    Fetch all results for a specific screening session.
    Scoped to the requesting user (users cannot see each other's results).
    """
    return (
        db.query(ScreeningResult)
        .filter(
            ScreeningResult.session_id == session_id,
            ScreeningResult.user_id == user_id,
        )
        .order_by(ScreeningResult.rank.asc())
        .all()
    )


def get_sessions_by_user(
    db: Session,
    user_id: UUID,
    limit: int = 20,
    offset: int = 0,
) -> list[dict]:
    """
    List distinct screening sessions for a user (most recent first).
    Returns summary dicts, not full result rows.
    """
    from sqlalchemy import func

    rows = (
        db.query(
            ScreeningResult.session_id,
            func.count(ScreeningResult.id).label("candidate_count"),
            func.max(ScreeningResult.created_at).label("created_at"),
            func.max(ScreeningResult.score).label("top_score"),
        )
        .filter(ScreeningResult.user_id == user_id)
        .group_by(ScreeningResult.session_id)
        .order_by(desc("created_at"))
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [
        {
            "session_id":      row.session_id,
            "candidate_count": row.candidate_count,
            "created_at":      row.created_at,
            "top_score":       row.top_score,
        }
        for row in rows
    ]


def get_result_by_id(
    db: Session,
    result_id: UUID,
    user_id: UUID,
) -> Optional[ScreeningResult]:
    """Fetch a single result by PK, scoped to the user."""
    return (
        db.query(ScreeningResult)
        .filter(
            ScreeningResult.id == result_id,
            ScreeningResult.user_id == user_id,
        )
        .first()
    )


def delete_session_results(
    db: Session,
    session_id: str,
    user_id: UUID,
) -> int:
    """
    Delete all results for a session. Returns count of deleted rows.
    """
    deleted = (
        db.query(ScreeningResult)
        .filter(
            ScreeningResult.session_id == session_id,
            ScreeningResult.user_id == user_id,
        )
        .delete(synchronize_session=False)
    )
    db.commit()
    logger.info("Deleted %d results for session %s", deleted, session_id)
    return deleted


# ── User helpers (used by auth.py in next step) ───────────────────────────────

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: UUID) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def create_user(
    db: Session,
    email: str,
    hashed_password: str,
) -> User:
    """Create a new unverified user."""
    user = User(
        id=uuid.uuid4(),
        email=email,
        hashed_password=hashed_password,
        is_verified=False,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("Created user: %s", email)
    return user


def update_user_verified(db: Session, user_id: UUID) -> Optional[User]:
    """Mark a user as email-verified."""
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.is_verified = True
        db.commit()
        db.refresh(user)
        logger.info("User verified: %s", user.email)
    return user