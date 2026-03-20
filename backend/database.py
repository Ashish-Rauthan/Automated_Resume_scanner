"""
database.py
-----------
SQLAlchemy engine setup and session factory.
All modules import `get_db` for dependency injection.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """
    Reads all config from environment variables / .env file.
    Pydantic validates types automatically.
    """
    APP_NAME: str = "AI Resume Screener"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    DATABASE_URL: str

    GROQ_API_KEY: str
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    RESEND_API_KEY: str
    EMAIL_FROM: str

    OTP_EXPIRE_MINUTES: int = 5

    SKILL_MATCH_WEIGHT: float = 0.50
    SEMANTIC_WEIGHT: float = 0.50
    PROJECT_WEIGHT: float = 0.30

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Cached settings — loaded once, reused everywhere."""
    return Settings()


settings = get_settings()

# ── Engine ────────────────────────────────────────────────────────────────────
# pool_pre_ping=True: validates connections before use (handles dropped DB conns)
# pool_size / max_overflow: tune for your expected concurrency
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=False,  # Set True during development to log SQL queries
)

# ── Session factory ───────────────────────────────────────────────────────────
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# ── Base class for all ORM models ─────────────────────────────────────────────
Base = declarative_base()


# ── FastAPI dependency ────────────────────────────────────────────────────────
def get_db():
    """
    Yields a DB session and guarantees cleanup even on exceptions.
    Usage in route:  db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()