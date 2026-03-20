"""
main.py — AI Resume Screener API (with Projects feature)

Projects routes:
  POST   /projects                  create a new project
  GET    /projects                  list all user projects
  GET    /projects/{id}             get project detail + sessions
  PATCH  /projects/{id}             rename / update description
  DELETE /projects/{id}             delete project + all its results

Screening routes (scoped to a project):
  POST /projects/{id}/screen        run screening inside a project
  GET  /projects/{id}/sessions      list sessions in a project
  GET  /screen/export/{session_id}  download CSV for a session

Auth routes:   POST /auth/signup|verify-otp|login|resend-otp   GET /auth/me
System routes: GET /health   POST /test/extract|parse (dev)
"""

import uuid
import json as _json
import logging
from typing import List, Optional

from fastapi import (
    FastAPI, UploadFile, File, Form,
    HTTPException, Depends, status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database import engine, Base, get_settings, get_db
from models import User
from utils import extract_text_from_bytes, validate_pdf_file
from parser import parse_resume
from scorer import score_candidates
from csv_exporter import results_to_csv_bytes, build_csv_filename
from crud import (
    get_user_by_email, create_user, update_user_verified,
    save_screening_results, get_results_by_session,
    get_sessions_by_user, delete_session_results,
    create_project, get_projects_by_user, get_project_by_id,
    update_project, delete_project,
    get_sessions_by_project, get_results_by_project,
)
from auth import (
    hash_password, verify_password, create_access_token,
    create_otp_record, verify_and_consume_otp, generate_otp,
    get_current_user, get_verified_user,
)
from email_service import send_otp_email
from middleware import RateLimitMiddleware, RequestLoggingMiddleware
from startup import run_startup_checks
from schemas import (
    SignupRequest, OTPVerifyRequest, LoginRequest,
    TokenResponse, UserResponse, MessageResponse,
    ScreeningResponse, CandidateResult,
    ProjectCreate, ProjectUpdate, ProjectResponse, SessionSummary,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)

settings = get_settings()
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered resume screening with named project sheets",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    run_startup_checks(fail_fast=False)


# ── System ────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
def health_check():
    return {"status": "ok", "app": settings.APP_NAME}

@app.get("/", tags=["System"])
def root():
    return {"message": "AI Resume Screener API v2", "docs": "/docs"}


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.post("/auth/signup", response_model=MessageResponse, tags=["Auth"])
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    existing = get_user_by_email(db, payload.email)
    if existing:
        if existing.is_verified:
            raise HTTPException(status_code=409, detail="An account with this email already exists.")
        otp = generate_otp()
        create_otp_record(db, existing.id, otp)
        sent, err = send_otp_email(payload.email, otp)
        if not sent:
            raise HTTPException(status_code=500, detail=f"Failed to send OTP: {err}")
        return MessageResponse(message="Account exists but is unverified. A new OTP has been sent.")

    user = create_user(db, email=payload.email, hashed_password=hash_password(payload.password))
    otp = generate_otp()
    create_otp_record(db, user.id, otp)
    sent, err = send_otp_email(payload.email, otp)
    if not sent:
        return MessageResponse(message=f"Account created but OTP email failed ({err}). Use /auth/resend-otp.")
    return MessageResponse(message=f"Account created. A 6-digit code was sent to {payload.email}.")


@app.post("/auth/verify-otp", response_model=MessageResponse, tags=["Auth"])
def verify_otp(payload: OTPVerifyRequest, db: Session = Depends(get_db)):
    user = get_user_by_email(db, payload.email)
    if not user:
        raise HTTPException(status_code=404, detail="No account found with this email.")
    if user.is_verified:
        return MessageResponse(message="Already verified. You can log in.")
    valid, reason = verify_and_consume_otp(db, user.id, payload.otp)
    if not valid:
        raise HTTPException(status_code=400, detail=reason)
    update_user_verified(db, user.id)
    return MessageResponse(message="Email verified. You can now log in.")


@app.post("/auth/resend-otp", response_model=MessageResponse, tags=["Auth"])
def resend_otp(email: str = Form(...), db: Session = Depends(get_db)):
    user = get_user_by_email(db, email)
    if not user or user.is_verified:
        return MessageResponse(message="If an account exists and is unverified, a new OTP has been sent.")
    otp = generate_otp()
    create_otp_record(db, user.id, otp)
    send_otp_email(email, otp)
    return MessageResponse(message="New verification code sent.")


@app.post("/auth/login", response_model=TokenResponse, tags=["Auth"])
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = get_user_by_email(db, payload.email)
    dummy = "$2b$12$dummyhashfortimingattackprevention000000000000000000000"
    stored = user.hashed_password if user else dummy
    ok = verify_password(payload.password, stored)
    if not user or not ok:
        raise HTTPException(status_code=401, detail="Incorrect email or password.",
                            headers={"WWW-Authenticate": "Bearer"})
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated.")
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Email not verified. Please verify before logging in.")
    return TokenResponse(access_token=create_access_token(str(user.id)))


@app.get("/auth/me", response_model=UserResponse, tags=["Auth"])
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


# ── Projects ──────────────────────────────────────────────────────────────────

@app.post("/projects", tags=["Projects"])
def create_new_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_verified_user),
):
    """Create a new named screening project (sheet)."""
    project = create_project(db, current_user.id, payload.title, payload.description or "")
    return {
        "id": str(project.id),
        "title": project.title,
        "description": project.description or "",
        "created_at": project.created_at,
        "updated_at": project.updated_at,
        "candidate_count": 0,
        "top_score": None,
        "last_run": None,
    }


@app.get("/projects", tags=["Projects"])
def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_verified_user),
):
    """List all projects for the current user with aggregate stats."""
    return {"projects": get_projects_by_user(db, current_user.id)}


@app.get("/projects/{project_id}", tags=["Projects"])
def get_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_verified_user),
):
    """Get project details + list of screening sessions inside it."""
    try:
        pid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid project ID.")
    project = get_project_by_id(db, pid, current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    sessions = get_sessions_by_project(db, pid, current_user.id)
    return {
        "id":          str(project.id),
        "title":       project.title,
        "description": project.description or "",
        "created_at":  project.created_at,
        "updated_at":  project.updated_at,
        "sessions":    sessions,
    }


@app.patch("/projects/{project_id}", tags=["Projects"])
def rename_project(
    project_id: str,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_verified_user),
):
    try:
        pid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid project ID.")
    project = update_project(db, pid, current_user.id, payload.title, payload.description or "")
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    return {"id": str(project.id), "title": project.title, "description": project.description or ""}


@app.delete("/projects/{project_id}", response_model=MessageResponse, tags=["Projects"])
def remove_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_verified_user),
):
    try:
        pid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid project ID.")
    ok = delete_project(db, pid, current_user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="Project not found.")
    return MessageResponse(message="Project and all its results have been deleted.")


# ── Screening inside a project ────────────────────────────────────────────────

@app.post("/projects/{project_id}/screen", tags=["Screening"], response_model=ScreeningResponse)
async def screen_resumes_in_project(
    project_id: str,
    job_description: str = Form(...),
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_verified_user),
):
    """
    Run a screening session inside a project.
    Pipeline: validate → extract → parse (Groq) → score → rank → save → return.
    """
    try:
        pid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid project ID.")

    project = get_project_by_id(db, pid, current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    if len(job_description.strip()) < 50:
        raise HTTPException(status_code=422, detail="Job description too short (min 50 chars).")

    session_id = str(uuid.uuid4())
    candidates = []
    pipeline_errors = []

    for upload in files:
        file_bytes = await upload.read()
        val_err = validate_pdf_file(upload.filename, file_bytes)
        if val_err:
            pipeline_errors.append({"filename": upload.filename, "error": val_err})
            continue
        text, extract_err = extract_text_from_bytes(file_bytes, upload.filename)
        if extract_err:
            pipeline_errors.append({"filename": upload.filename, "error": extract_err})
            continue
        parsed, parse_err = parse_resume(text, upload.filename)
        if parse_err:
            pipeline_errors.append({"filename": upload.filename, "warning": parse_err})
        candidates.append({"filename": upload.filename, "parsed": parsed, "raw_text": text})

    if not candidates:
        raise HTTPException(status_code=400,
                            detail=f"No valid resumes processed. Details: {pipeline_errors}")

    results: list = score_candidates(job_description, candidates)

    try:
        save_screening_results(
            db=db,
            user_id=current_user.id,
            session_id=session_id,
            results=results,
            job_description=job_description,
            project_id=pid,
        )
    except Exception as e:
        pipeline_errors.append({"db_save_warning": str(e)})

    return ScreeningResponse(
        session_id=session_id,
        total_candidates=len(results),
        results=results,
    )


@app.get("/projects/{project_id}/sessions", tags=["Screening"])
def list_project_sessions(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_verified_user),
):
    """List all screening sessions inside a project."""
    try:
        pid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid project ID.")
    project = get_project_by_id(db, pid, current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    return {"sessions": get_sessions_by_project(db, pid, current_user.id)}


# ── CSV export ────────────────────────────────────────────────────────────────

@app.get("/screen/export/{session_id}", tags=["Screening"])
def export_session_csv(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_verified_user),
):
    db_results = get_results_by_session(db, session_id, current_user.id)
    if not db_results:
        raise HTTPException(status_code=404, detail="Session not found.")

    candidate_results = []
    jd_preview = ""
    for row in db_results:
        strengths = _json.loads(row.strengths) if row.strengths else []
        gaps      = _json.loads(row.gaps)      if row.gaps      else []
        candidate_results.append(CandidateResult(
            filename=row.filename, candidate_name=row.candidate_name,
            score=row.score, skill_match_score=0.0, semantic_score=0.0,
            strengths=strengths, gaps=gaps,
            recommendation=row.recommendation, rank=row.rank,
        ))
        if not jd_preview and row.job_description:
            jd_preview = row.job_description

    csv_bytes = results_to_csv_bytes(candidate_results, session_id, jd_preview)
    filename  = build_csv_filename(session_id)
    return StreamingResponse(
        content=iter([csv_bytes]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"',
                 "Content-Length": str(len(csv_bytes))},
    )


# ── Legacy screen endpoint (no project) ──────────────────────────────────────

@app.post("/screen", tags=["Screening"], response_model=ScreeningResponse)
async def screen_resumes(
    job_description: str = Form(...),
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_verified_user),
):
    """Screen resumes without a project (creates orphan results)."""
    if len(job_description.strip()) < 50:
        raise HTTPException(status_code=422, detail="Job description too short (min 50 chars).")
    session_id = str(uuid.uuid4())
    candidates, pipeline_errors = [], []
    for upload in files:
        file_bytes = await upload.read()
        val_err = validate_pdf_file(upload.filename, file_bytes)
        if val_err:
            pipeline_errors.append({"filename": upload.filename, "error": val_err}); continue
        text, err = extract_text_from_bytes(file_bytes, upload.filename)
        if err:
            pipeline_errors.append({"filename": upload.filename, "error": err}); continue
        parsed, warn = parse_resume(text, upload.filename)
        if warn:
            pipeline_errors.append({"filename": upload.filename, "warning": warn})
        candidates.append({"filename": upload.filename, "parsed": parsed, "raw_text": text})
    if not candidates:
        raise HTTPException(status_code=400, detail=f"No valid resumes processed. {pipeline_errors}")
    results = score_candidates(job_description, candidates)
    try:
        save_screening_results(db=db, user_id=current_user.id, session_id=session_id,
                               results=results, job_description=job_description)
    except Exception as e:
        pass
    return ScreeningResponse(session_id=session_id, total_candidates=len(results), results=results)


@app.get("/screen/history", tags=["Screening"])
def get_screening_history(limit: int = 10, offset: int = 0,
                          db: Session = Depends(get_db),
                          current_user: User = Depends(get_verified_user)):
    return {"sessions": get_sessions_by_user(db, current_user.id, limit, offset)}


@app.delete("/screen/{session_id}", response_model=MessageResponse, tags=["Screening"])
def delete_session(session_id: str, db: Session = Depends(get_db),
                   current_user: User = Depends(get_verified_user)):
    deleted = delete_session_results(db, session_id, current_user.id)
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Session not found.")
    return MessageResponse(message=f"Deleted {deleted} results.")


# ── Dev/test endpoints ────────────────────────────────────────────────────────

@app.post("/test/extract", tags=["Testing"])
async def test_pdf_extraction(files: List[UploadFile] = File(...)):
    results = []
    for upload in files:
        file_bytes = await upload.read()
        err = validate_pdf_file(upload.filename, file_bytes)
        if err:
            results.append({"filename": upload.filename, "success": False, "error": err}); continue
        text, error = extract_text_from_bytes(file_bytes, upload.filename)
        results.append({"filename": upload.filename, "success": error is None,
                        "error": error, "char_count": len(text), "preview": text[:500] if text else None})
    return {"total_files": len(files), "results": results}


@app.post("/test/parse", tags=["Testing"])
async def test_llm_parse(files: List[UploadFile] = File(...)):
    results = []
    for upload in files:
        file_bytes = await upload.read()
        err = validate_pdf_file(upload.filename, file_bytes)
        if err:
            results.append({"filename": upload.filename, "success": False, "error": err, "parsed": None}); continue
        text, extract_err = extract_text_from_bytes(file_bytes, upload.filename)
        if extract_err:
            results.append({"filename": upload.filename, "success": False, "error": extract_err, "parsed": None}); continue
        parsed, parse_err = parse_resume(text, upload.filename)
        results.append({"filename": upload.filename, "success": parse_err is None, "error": parse_err,
                        "parsed": {"name": parsed.name, "skills": parsed.skills,
                                   "experience": parsed.experience, "projects": parsed.projects,
                                   "education": parsed.education}})
    return {"total_files": len(files), "results": results}


# ── Session results (used by ProjectDetail frontend) ─────────────────────────

@app.get("/session/{session_id}/results", tags=["Screening"])
def get_session_results(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_verified_user),
):
    """Return scored results for a session as CandidateResult-shaped dicts."""
    db_results = get_results_by_session(db, session_id, current_user.id)
    if not db_results:
        return {"results": []}

    results = []
    for row in db_results:
        strengths = _json.loads(row.strengths) if row.strengths else []
        gaps      = _json.loads(row.gaps)      if row.gaps      else []
        results.append({
            "filename":          row.filename,
            "candidate_name":    row.candidate_name,
            "score":             row.score,
            "skill_match_score": 0.0,
            "semantic_score":    0.0,
            "strengths":         strengths,
            "gaps":              gaps,
            "recommendation":    row.recommendation,
            "rank":              row.rank,
        })
    return {"results": results}