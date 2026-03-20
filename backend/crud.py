"""
crud.py
-------
Database CRUD operations for all entities.
"""

import json
import logging
import uuid
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from models import ScreeningResult, ScreeningProject, User
from schemas import CandidateResult

logger = logging.getLogger(__name__)


# ── Projects ──────────────────────────────────────────────────────────────────

def create_project(db: Session, user_id: UUID, title: str, description: str = "") -> ScreeningProject:
    project = ScreeningProject(
        id=uuid.uuid4(),
        user_id=user_id,
        title=title.strip(),
        description=description.strip() if description else None,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    logger.info("Created project '%s' for user %s", title, user_id)
    return project


def get_projects_by_user(db: Session, user_id: UUID) -> list:
    """
    List all projects for a user, newest first.
    Includes aggregate stats per project (candidate count, top score, last run).
    """
    projects = (
        db.query(ScreeningProject)
        .filter(ScreeningProject.user_id == user_id)
        .order_by(desc(ScreeningProject.updated_at))
        .all()
    )

    result = []
    for p in projects:
        stats = (
            db.query(
                func.count(ScreeningResult.id).label("candidate_count"),
                func.max(ScreeningResult.score).label("top_score"),
                func.max(ScreeningResult.created_at).label("last_run"),
            )
            .filter(ScreeningResult.project_id == p.id)
            .first()
        )
        result.append({
            "id":              str(p.id),
            "title":           p.title,
            "description":     p.description or "",
            "created_at":      p.created_at,
            "updated_at":      p.updated_at,
            "candidate_count": stats.candidate_count or 0,
            "top_score":       round(stats.top_score, 1) if stats.top_score else None,
            "last_run":        stats.last_run,
        })
    return result


def get_project_by_id(db: Session, project_id: UUID, user_id: UUID) -> Optional[ScreeningProject]:
    return (
        db.query(ScreeningProject)
        .filter(ScreeningProject.id == project_id, ScreeningProject.user_id == user_id)
        .first()
    )


def update_project(db: Session, project_id: UUID, user_id: UUID, title: str, description: str = "") -> Optional[ScreeningProject]:
    project = get_project_by_id(db, project_id, user_id)
    if not project:
        return None
    project.title = title.strip()
    project.description = description.strip() if description else None
    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, project_id: UUID, user_id: UUID) -> bool:
    project = get_project_by_id(db, project_id, user_id)
    if not project:
        return False
    db.delete(project)
    db.commit()
    logger.info("Deleted project %s", project_id)
    return True


# ── Screening Results ─────────────────────────────────────────────────────────

def save_screening_results(
    db: Session,
    user_id: UUID,
    session_id: str,
    results: list,
    job_description: str,
    project_id: Optional[UUID] = None,
) -> list:
    orm_objects = []
    for result in results:
        db_result = ScreeningResult(
            id=uuid.uuid4(),
            user_id=user_id,
            project_id=project_id,
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
        # Bump project updated_at so it floats to top of list
        if project_id:
            proj = db.query(ScreeningProject).filter(ScreeningProject.id == project_id).first()
            if proj:
                from datetime import datetime, timezone
                proj.updated_at = datetime.now(timezone.utc)
                db.commit()
        logger.info("Saved %d results for session %s (project=%s)", len(orm_objects), session_id, project_id)
    except Exception as e:
        db.rollback()
        logger.error("Failed to save screening results: %s", e)
        raise

    return orm_objects


def get_results_by_project(db: Session, project_id: UUID, user_id: UUID) -> list:
    """All results for a project, grouped by session (most recent session first)."""
    return (
        db.query(ScreeningResult)
        .filter(ScreeningResult.project_id == project_id, ScreeningResult.user_id == user_id)
        .order_by(desc(ScreeningResult.created_at), ScreeningResult.rank.asc())
        .all()
    )


def get_sessions_by_project(db: Session, project_id: UUID, user_id: UUID) -> list:
    """
    List distinct screening sessions within a project, newest first.
    Returns summary dicts with session_id, candidate_count, top_score, created_at, jd_preview.
    """
    rows = (
        db.query(
            ScreeningResult.session_id,
            func.count(ScreeningResult.id).label("candidate_count"),
            func.max(ScreeningResult.created_at).label("created_at"),
            func.max(ScreeningResult.score).label("top_score"),
        )
        .filter(ScreeningResult.project_id == project_id, ScreeningResult.user_id == user_id)
        .group_by(ScreeningResult.session_id)
        .order_by(desc("created_at"))
        .all()
    )

    result = []
    for row in rows:
        # Grab JD preview from first result in this session
        sample = (
            db.query(ScreeningResult.job_description)
            .filter(ScreeningResult.session_id == row.session_id)
            .first()
        )
        jd_preview = ""
        if sample and sample.job_description:
            jd_preview = sample.job_description[:120].replace("\n", " ").strip()

        result.append({
            "session_id":      row.session_id,
            "candidate_count": row.candidate_count,
            "created_at":      row.created_at,
            "top_score":       round(row.top_score, 1) if row.top_score else None,
            "jd_preview":      jd_preview,
        })
    return result


def get_results_by_session(db: Session, session_id: str, user_id: UUID) -> list:
    return (
        db.query(ScreeningResult)
        .filter(ScreeningResult.session_id == session_id, ScreeningResult.user_id == user_id)
        .order_by(ScreeningResult.rank.asc())
        .all()
    )


def get_sessions_by_user(db: Session, user_id: UUID, limit: int = 20, offset: int = 0) -> list:
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
        .offset(offset).limit(limit).all()
    )
    return [
        {"session_id": r.session_id, "candidate_count": r.candidate_count,
         "created_at": r.created_at, "top_score": r.top_score}
        for r in rows
    ]


def delete_session_results(db: Session, session_id: str, user_id: UUID) -> int:
    deleted = (
        db.query(ScreeningResult)
        .filter(ScreeningResult.session_id == session_id, ScreeningResult.user_id == user_id)
        .delete(synchronize_session=False)
    )
    db.commit()
    logger.info("Deleted %d results for session %s", deleted, session_id)
    return deleted


# ── User helpers ──────────────────────────────────────────────────────────────

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: UUID) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def create_user(db: Session, email: str, hashed_password: str) -> User:
    user = User(id=uuid.uuid4(), email=email, hashed_password=hashed_password,
                is_verified=False, is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("Created user: %s", email)
    return user


def update_user_verified(db: Session, user_id: UUID) -> Optional[User]:
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.is_verified = True
        db.commit()
        db.refresh(user)
    return user