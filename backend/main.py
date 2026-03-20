"""
main.py
-------
FastAPI application — all 10 backend steps complete.

Auth routes:
  POST /auth/signup         register + trigger OTP email
  POST /auth/verify-otp     verify OTP → activate account
  POST /auth/login          email+password → JWT
  POST /auth/resend-otp     resend OTP to same email
  GET  /auth/me             get current user info

Screening routes (JWT protected):
  POST /screen              full AI pipeline → ranked results
  GET  /screen/export/{id}  download CSV
  GET  /screen/history      list past sessions
  DELETE /screen/{session}  delete a session

System routes:
  GET  /health
  POST /test/extract        (dev only)
  POST /test/parse          (dev only)
"""

import uuid
import json as _json
import logging
from typing import List

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
    description="AI-powered resume screening and candidate ranking API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Middleware (order matters: outermost runs first) ───────────────────────────
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
    """Run validation checks when the server starts."""
    run_startup_checks(fail_fast=False)  # set True in production


# ── System ─────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
def health_check():
    return {"status": "ok", "app": settings.APP_NAME}

@app.get("/", tags=["System"])
def root():
    return {"message": "AI Resume Screener API", "docs": "/docs"}


# ── Auth: Signup ───────────────────────────────────────────────────────────────

@app.post("/auth/signup", response_model=MessageResponse, tags=["Auth"])
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    """
    Register a new account.
    1. Validate email uniqueness
    2. Hash password
    3. Create unverified user
    4. Generate + store OTP
    5. Send OTP email
    """
    existing = get_user_by_email(db, payload.email)
    if existing:
        if existing.is_verified:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists.",
            )
        # Unverified — allow re-signup by sending a new OTP
        otp = generate_otp()
        create_otp_record(db, existing.id, otp)
        sent, err = send_otp_email(payload.email, otp)
        if not sent:
            raise HTTPException(status_code=500, detail=f"Failed to send OTP: {err}")
        return MessageResponse(message="Account exists but is unverified. A new OTP has been sent.")

    hashed_pw = hash_password(payload.password)
    user = create_user(db, email=payload.email, hashed_password=hashed_pw)

    otp = generate_otp()
    create_otp_record(db, user.id, otp)
    sent, err = send_otp_email(payload.email, otp)
    if not sent:
        # User created but email failed — still allow retry via resend-otp
        return MessageResponse(
            message=f"Account created but OTP email failed ({err}). "
                    "Use /auth/resend-otp to try again."
        )

    return MessageResponse(
        message=f"Account created. A 6-digit verification code has been sent to {payload.email}."
    )


# ── Auth: Verify OTP ───────────────────────────────────────────────────────────

@app.post("/auth/verify-otp", response_model=MessageResponse, tags=["Auth"])
def verify_otp(payload: OTPVerifyRequest, db: Session = Depends(get_db)):
    """
    Verify OTP → activate account.
    After this call succeeds the user can log in.
    """
    user = get_user_by_email(db, payload.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found with this email.",
        )
    if user.is_verified:
        return MessageResponse(message="Account is already verified. You can log in.")

    valid, reason = verify_and_consume_otp(db, user.id, payload.otp)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=reason,
        )

    update_user_verified(db, user.id)
    return MessageResponse(message="Email verified successfully. You can now log in.")


# ── Auth: Resend OTP ───────────────────────────────────────────────────────────

@app.post("/auth/resend-otp", response_model=MessageResponse, tags=["Auth"])
def resend_otp(email: str = Form(...), db: Session = Depends(get_db)):
    """Resend a fresh OTP to the given email (rate-limited by OTP expiry)."""
    user = get_user_by_email(db, email)
    if not user:
        # Return generic message to avoid email enumeration
        return MessageResponse(message="If an account exists, a new OTP has been sent.")
    if user.is_verified:
        return MessageResponse(message="Account is already verified.")

    otp = generate_otp()
    create_otp_record(db, user.id, otp)
    send_otp_email(email, otp)
    return MessageResponse(message="A new verification code has been sent.")


# ── Auth: Login ────────────────────────────────────────────────────────────────

@app.post("/auth/login", response_model=TokenResponse, tags=["Auth"])
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate with email + password.
    Returns a JWT access token valid for ACCESS_TOKEN_EXPIRE_MINUTES.
    """
    user = get_user_by_email(db, payload.email)

    # Use constant-time comparison to prevent timing attacks
    # Always call verify_password even if user is None (uses dummy hash)
    dummy_hash = "$2b$12$dummyhashfortimingattackprevention000000000000000000000"
    stored_hash = user.hashed_password if user else dummy_hash
    password_ok = verify_password(payload.password, stored_hash)

    if not user or not password_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated.",
        )
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please verify your email before logging in.",
        )

    token = create_access_token(subject=str(user.id))
    return TokenResponse(access_token=token, token_type="bearer")


# ── Auth: Current user ─────────────────────────────────────────────────────────

@app.get("/auth/me", response_model=UserResponse, tags=["Auth"])
def get_me(current_user: User = Depends(get_current_user)):
    """Return the authenticated user's profile."""
    return current_user


# ── Screening: Full pipeline ───────────────────────────────────────────────────

@app.post("/screen", tags=["Screening"], response_model=ScreeningResponse)
async def screen_resumes(
    job_description: str = Form(...),
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_verified_user),
):
    """
    Full AI screening pipeline (JWT protected, email verification required):
      1. Validate + extract text from each PDF
      2. Parse with Groq LLM → structured JSON
      3. Score + rank all candidates
      4. Persist results to DB
      5. Return ranked results
    """
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
        raise HTTPException(
            status_code=400,
            detail=f"No valid resumes could be processed. Details: {pipeline_errors}",
        )

    results: list[CandidateResult] = score_candidates(job_description, candidates)

    try:
        save_screening_results(
            db=db,
            user_id=current_user.id,
            session_id=session_id,
            results=results,
            job_description=job_description,
        )
    except Exception as e:
        pipeline_errors.append({"db_save_warning": str(e)})

    return ScreeningResponse(
        session_id=session_id,
        total_candidates=len(results),
        results=results,
    )


# ── Screening: CSV Export ──────────────────────────────────────────────────────

@app.get("/screen/export/{session_id}", tags=["Screening"])
def export_session_csv(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_verified_user),
):
    """Download ranked results as an Excel-compatible CSV."""
    db_results = get_results_by_session(db, session_id, current_user.id)
    if not db_results:
        raise HTTPException(status_code=404, detail="Session not found.")

    candidate_results = []
    jd_preview = ""
    for row in db_results:
        strengths = _json.loads(row.strengths) if row.strengths else []
        gaps      = _json.loads(row.gaps)      if row.gaps      else []
        candidate_results.append(CandidateResult(
            filename=row.filename,
            candidate_name=row.candidate_name,
            score=row.score,
            skill_match_score=0.0,
            semantic_score=0.0,
            strengths=strengths,
            gaps=gaps,
            recommendation=row.recommendation,
            rank=row.rank,
        ))
        if not jd_preview and row.job_description:
            jd_preview = row.job_description

    csv_bytes = results_to_csv_bytes(candidate_results, session_id, jd_preview)
    filename  = build_csv_filename(session_id)

    return StreamingResponse(
        content=iter([csv_bytes]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(csv_bytes)),
        },
    )


# ── Screening: History ─────────────────────────────────────────────────────────

@app.get("/screen/history", tags=["Screening"])
def get_screening_history(
    limit: int = 10,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_verified_user),
):
    sessions = get_sessions_by_user(db, current_user.id, limit, offset)
    return {"sessions": sessions, "total": len(sessions)}


# ── Screening: Delete session ──────────────────────────────────────────────────

@app.delete("/screen/{session_id}", tags=["Screening"], response_model=MessageResponse)
def delete_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_verified_user),
):
    deleted = delete_session_results(db, session_id, current_user.id)
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Session not found.")
    return MessageResponse(message=f"Deleted {deleted} results for session {session_id}.")


# ── Dev / test endpoints ───────────────────────────────────────────────────────

@app.post("/test/extract", tags=["Testing"])
async def test_pdf_extraction(files: List[UploadFile] = File(...)):
    results = []
    for upload in files:
        file_bytes = await upload.read()
        err = validate_pdf_file(upload.filename, file_bytes)
        if err:
            results.append({"filename": upload.filename, "success": False, "error": err})
            continue
        text, error = extract_text_from_bytes(file_bytes, upload.filename)
        results.append({
            "filename": upload.filename, "success": error is None,
            "error": error, "char_count": len(text), "preview": text[:500] if text else None,
        })
    return {"total_files": len(files), "results": results}


@app.post("/test/parse", tags=["Testing"])
async def test_llm_parse(files: List[UploadFile] = File(...)):
    results = []
    for upload in files:
        file_bytes = await upload.read()
        err = validate_pdf_file(upload.filename, file_bytes)
        if err:
            results.append({"filename": upload.filename, "success": False, "error": err, "parsed": None})
            continue
        text, extract_err = extract_text_from_bytes(file_bytes, upload.filename)
        if extract_err:
            results.append({"filename": upload.filename, "success": False, "error": extract_err, "parsed": None})
            continue
        parsed, parse_err = parse_resume(text, upload.filename)
        results.append({
            "filename": upload.filename, "success": parse_err is None,
            "error": parse_err,
            "parsed": {
                "name": parsed.name, "skills": parsed.skills,
                "experience": parsed.experience, "projects": parsed.projects,
                "education": parsed.education,
            },
        })
    return {"total_files": len(files), "results": results}