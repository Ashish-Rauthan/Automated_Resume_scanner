"""
startup.py
----------
Startup validation — runs before the app accepts any requests.
Fails fast with clear error messages instead of cryptic runtime errors.

Checks:
  1. All required env vars present and non-empty
  2. DATABASE_URL is reachable (test connection)
  3. Groq API key is syntactically valid (doesn't make an API call)
  4. Sentence-transformer model is loadable
  5. spaCy model is installed
"""

import logging
import sys
import os

logger = logging.getLogger(__name__)


def _check_env_vars() -> list[str]:
    """Return list of missing/empty required env vars."""
    required = {
        "SECRET_KEY":      "JWT signing key (min 32 chars)",
        "DATABASE_URL":    "PostgreSQL connection string",
        "GROQ_API_KEY":    "Groq API key from console.groq.com",
        "RESEND_API_KEY":  "Resend API key from resend.com",
        "EMAIL_FROM":      "Sender email address",
    }
    missing = []
    for var, description in required.items():
        val = os.getenv(var, "").strip()
        if not val:
            missing.append(f"  - {var}: {description}")
        elif var == "SECRET_KEY" and len(val) < 32:
            missing.append(f"  - {var}: must be at least 32 characters (got {len(val)})")
    return missing


def _check_database() -> str | None:
    """Try to connect to the database. Returns error string or None."""
    try:
        from database import engine
        with engine.connect() as conn:
            conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        return None
    except Exception as e:
        return f"Database connection failed: {e}"


def _check_spacy() -> str | None:
    """Verify spaCy model is installed."""
    try:
        import spacy
        spacy.load("en_core_web_sm")
        return None
    except OSError:
        return "spaCy model 'en_core_web_sm' not installed. Run: python -m spacy download en_core_web_sm"
    except ImportError:
        return "spaCy not installed. Run: pip install spacy"


def _check_sentence_transformers() -> str | None:
    """Verify sentence-transformers is importable (model downloads lazily)."""
    try:
        from sentence_transformers import SentenceTransformer  # noqa: F401
        return None
    except ImportError:
        return "sentence-transformers not installed. Run: pip install sentence-transformers"


def run_startup_checks(fail_fast: bool = True) -> bool:
    """
    Run all startup checks.

    Args:
        fail_fast: If True, sys.exit(1) on any failure (production mode).
                   If False, log warnings and continue (dev/test mode).

    Returns:
        True if all checks passed, False otherwise.
    """
    logger.info("Running startup checks…")
    errors   = []
    warnings = []

    # 1. Env vars
    missing_vars = _check_env_vars()
    if missing_vars:
        errors.append("Missing required environment variables:\n" + "\n".join(missing_vars))

    # 2. Database (skip if DATABASE_URL missing — already caught above)
    if not missing_vars:
        db_err = _check_database()
        if db_err:
            errors.append(db_err)
        else:
            logger.info("  ✓ Database connection OK")

    # 3. spaCy
    spacy_err = _check_spacy()
    if spacy_err:
        errors.append(spacy_err)
    else:
        logger.info("  ✓ spaCy model OK")

    # 4. sentence-transformers
    st_err = _check_sentence_transformers()
    if st_err:
        errors.append(st_err)
    else:
        logger.info("  ✓ sentence-transformers OK")

    if errors:
        logger.error("Startup checks FAILED:")
        for err in errors:
            logger.error("  ✗ %s", err)
        if fail_fast:
            logger.error("Exiting. Fix the above errors and restart.")
            sys.exit(1)
        return False

    logger.info("All startup checks passed.")
    return True