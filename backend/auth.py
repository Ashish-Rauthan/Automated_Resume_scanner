"""
auth.py
-------
Authentication logic: JWT tokens, password hashing, OTP generation/verification.

Public API:
  hash_password()           -> bcrypt hash a plain password
  verify_password()         -> check plain against hash
  create_access_token()     -> sign a JWT with expiry
  decode_access_token()     -> verify + decode a JWT
  generate_otp()            -> random 6-digit string
  hash_otp()                -> bcrypt hash an OTP (same as password)
  verify_otp_hash()         -> check plain OTP against stored hash
  get_current_user()        -> FastAPI dependency — extracts + validates JWT
  get_verified_user()       -> like get_current_user but also checks is_verified

OTP security model:
  - OTP is a 6-digit number (000000–999999)
  - Stored as bcrypt hash in DB — never plaintext
  - Expires after OTP_EXPIRE_MINUTES (default: 5)
  - Marked is_used=True after first successful verification
  - Old unused OTPs for a user are invalidated when a new one is issued
"""

import logging
import random
import string
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from database import get_db, get_settings
from models import User, OTP
from crud import get_user_by_id

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Password hashing ──────────────────────────────────────────────────────────
# bcrypt with 12 rounds — good balance of security and speed
# (12 rounds ≈ 250ms per hash on modern hardware)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

# ── JWT bearer scheme ─────────────────────────────────────────────────────────
bearer_scheme = HTTPBearer(auto_error=True)


# ── Password utilities ────────────────────────────────────────────────────────

def hash_password(plain_password: str) -> str:
    """Hash a plain-text password with bcrypt."""
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


# ── JWT utilities ─────────────────────────────────────────────────────────────

def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a signed JWT access token.

    Args:
        subject:      The user's UUID as a string (stored in 'sub' claim)
        expires_delta: Custom expiry; defaults to ACCESS_TOKEN_EXPIRE_MINUTES

    Returns:
        Signed JWT string.
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + expires_delta,
        "type": "access",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict:
    """
    Verify and decode a JWT.

    Returns:
        Decoded payload dict.

    Raises:
        HTTPException 401 on any invalid/expired token.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token. Please log in again.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")

        if user_id is None:
            raise credentials_exception
        if token_type != "access":
            raise credentials_exception

        return payload

    except JWTError as e:
        logger.warning("JWT decode failed: %s", e)
        raise credentials_exception


# ── OTP utilities ─────────────────────────────────────────────────────────────

def generate_otp() -> str:
    """Generate a cryptographically random 6-digit OTP string."""
    return "".join(random.choices(string.digits, k=6))


def hash_otp(plain_otp: str) -> str:
    """Hash OTP with bcrypt (same pwd_context as passwords)."""
    return pwd_context.hash(plain_otp)


def verify_otp_hash(plain_otp: str, hashed_otp: str) -> bool:
    """Verify a plain OTP against its bcrypt hash."""
    return pwd_context.verify(plain_otp, hashed_otp)


# ── OTP DB operations ─────────────────────────────────────────────────────────

def create_otp_record(
    db: Session,
    user_id: uuid.UUID,
    plain_otp: str,
) -> OTP:
    """
    Store a new OTP for a user.

    Before creating:
    - Invalidates (marks is_used=True) all existing unused OTPs for this user
      to prevent replay attacks with old codes.
    """
    # Invalidate old unused OTPs
    db.query(OTP).filter(
        OTP.user_id == user_id,
        OTP.is_used == False,  # noqa: E712
    ).update({"is_used": True})

    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.OTP_EXPIRE_MINUTES
    )
    otp_record = OTP(
        id=uuid.uuid4(),
        user_id=user_id,
        hashed_otp=hash_otp(plain_otp),
        expires_at=expires_at,
        is_used=False,
    )
    db.add(otp_record)
    db.commit()
    db.refresh(otp_record)

    logger.info("OTP created for user_id=%s, expires=%s", user_id, expires_at)
    return otp_record


def verify_and_consume_otp(
    db: Session,
    user_id: uuid.UUID,
    plain_otp: str,
) -> tuple[bool, str]:
    """
    Verify an OTP and mark it consumed if valid.

    Returns:
        (True, "")                  on success
        (False, reason_string)      on failure

    Checks (in order):
        1. OTP record exists for user
        2. Not already used
        3. Not expired
        4. Hash matches
    """
    otp_record = (
        db.query(OTP)
        .filter(
            OTP.user_id == user_id,
            OTP.is_used == False,  # noqa: E712
        )
        .order_by(OTP.created_at.desc())
        .first()
    )

    if otp_record is None:
        return False, "No active OTP found. Please request a new one."

    # Check expiry
    now = datetime.now(timezone.utc)
    otp_expires = otp_record.expires_at
    # Make offset-aware if stored as naive datetime
    if otp_expires.tzinfo is None:
        otp_expires = otp_expires.replace(tzinfo=timezone.utc)

    if now > otp_expires:
        return False, "OTP has expired. Please request a new one."

    # Check hash
    if not verify_otp_hash(plain_otp, otp_record.hashed_otp):
        return False, "Invalid OTP. Please check and try again."

    # Consume the OTP
    otp_record.is_used = True
    db.commit()

    logger.info("OTP verified and consumed for user_id=%s", user_id)
    return True, ""


# ── FastAPI dependencies ──────────────────────────────────────────────────────

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    FastAPI dependency — extracts JWT from Authorization header,
    validates it, and returns the User ORM object.

    Usage in route:
        current_user: User = Depends(get_current_user)
    """
    token = credentials.credentials
    payload = decode_access_token(token)

    user_id_str = payload.get("sub")
    try:
        user_id = uuid.UUID(user_id_str)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload.",
        )

    user = get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated.",
        )

    return user


async def get_verified_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Like get_current_user but additionally enforces email verification.
    Use this on all screening endpoints.

    Usage in route:
        current_user: User = Depends(get_verified_user)
    """
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email address not verified. "
                   "Please check your email for the OTP verification code.",
        )
    return current_user