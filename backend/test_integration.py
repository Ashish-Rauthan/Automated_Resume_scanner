"""
test_integration.py
-------------------
End-to-end integration tests using FastAPI TestClient.
Tests the full HTTP layer: routing, auth, validation, error handling.

Run with:  python test_integration.py
Requirements: all dependencies installed, .env present.

Note: Uses an in-memory SQLite DB for isolation — does NOT touch your
Supabase DB. Replace DATABASE_URL in the test fixture to use Postgres
if you want full fidelity.
"""

import io
import json
import sys
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

# ── Patch DB URL to SQLite before importing app ───────────────
import os
os.environ.setdefault("DATABASE_URL",    "sqlite:///./test_integration.db")
os.environ.setdefault("SECRET_KEY",      "test-secret-key-32-chars-minimum!!!")
os.environ.setdefault("GROQ_API_KEY",    "test-groq-key")
os.environ.setdefault("RESEND_API_KEY",  "test-resend-key")
os.environ.setdefault("EMAIL_FROM",      "test@example.com")
os.environ.setdefault("ALGORITHM",       "HS256")

from main import app  # noqa: E402
from database import engine, Base  # noqa: E402

# Create tables in test DB
Base.metadata.create_all(bind=engine)

client = TestClient(app, raise_server_exceptions=False)

# ── Helpers ───────────────────────────────────────────────────

def make_pdf_bytes(text: str = "Python FastAPI developer with Docker experience") -> bytes:
    """Minimal valid PDF with embedded text."""
    content = (
        f"%PDF-1.4\n"
        f"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        f"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        f"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Contents 4 0 R/Parent 2 0 R>>endobj\n"
        f"4 0 obj<</Length {len(text)+20}>>\nstream\nBT /F1 12 Tf 72 720 Td ({text}) Tj ET\nendstream endobj\n"
        f"xref\n0 5\ntrailer<</Size 5/Root 1 0 R>>\n%%EOF"
    )
    return content.encode()


def register_and_login(email: str, password: str = "TestPass1") -> str:
    """Register a user, bypass OTP verification, and return JWT."""
    from crud import get_user_by_email, update_user_verified
    from database import SessionLocal
    from auth import hash_password
    from models import User
    import uuid

    db = SessionLocal()
    try:
        # Create user directly (bypasses email)
        existing = get_user_by_email(db, email)
        if not existing:
            user = User(
                id=uuid.uuid4(),
                email=email,
                hashed_password=hash_password(password),
                is_verified=True,
                is_active=True,
            )
            db.add(user)
            db.commit()
        else:
            update_user_verified(db, existing.id)
    finally:
        db.close()

    resp = client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed: {resp.json()}"
    return resp.json()["access_token"]


# ── System tests ──────────────────────────────────────────────

def test_health():
    print("\n── test_health")
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    print("PASS")


def test_root():
    print("\n── test_root")
    r = client.get("/")
    assert r.status_code == 200
    assert "docs" in r.json()["message"] or "API" in r.json()["message"]
    print("PASS")


# ── Auth tests ────────────────────────────────────────────────

def test_signup_success():
    print("\n── test_signup (success)")
    with patch("main.send_otp_email", return_value=(True, None)):
        r = client.post("/auth/signup", json={
            "email": "signup_test@example.com",
            "password": "TestPass1",
        })
    assert r.status_code == 200, r.json()
    assert "verification" in r.json()["message"].lower() or "created" in r.json()["message"].lower()
    print("PASS")


def test_signup_weak_password():
    print("\n── test_signup (weak password)")
    r = client.post("/auth/signup", json={
        "email": "weak@example.com",
        "password": "short",
    })
    assert r.status_code == 422
    print("PASS")


def test_signup_invalid_email():
    print("\n── test_signup (invalid email)")
    r = client.post("/auth/signup", json={
        "email": "not-an-email",
        "password": "TestPass1",
    })
    assert r.status_code == 422
    print("PASS")


def test_login_success():
    print("\n── test_login (success)")
    token = register_and_login("login_test@example.com")
    assert token and len(token) > 20
    print(f"  Token: {token[:30]}…")
    print("PASS")


def test_login_wrong_password():
    print("\n── test_login (wrong password)")
    register_and_login("wrongpw@example.com")
    r = client.post("/auth/login", json={
        "email": "wrongpw@example.com",
        "password": "WrongPass1",
    })
    assert r.status_code == 401
    assert "Incorrect" in r.json()["detail"]
    print("PASS")


def test_login_nonexistent_user():
    print("\n── test_login (nonexistent user)")
    r = client.post("/auth/login", json={
        "email": "nobody@example.com",
        "password": "TestPass1",
    })
    assert r.status_code == 401
    print("PASS")


def test_get_me_authenticated():
    print("\n── test_get_me (authenticated)")
    token = register_and_login("me_test@example.com")
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert data["email"] == "me_test@example.com"
    assert data["is_verified"] is True
    print(f"  User: {data['email']}")
    print("PASS")


def test_get_me_unauthenticated():
    print("\n── test_get_me (unauthenticated)")
    r = client.get("/auth/me")
    assert r.status_code == 403  # HTTPBearer returns 403 when no credentials
    print("PASS")


def test_get_me_bad_token():
    print("\n── test_get_me (invalid token)")
    r = client.get("/auth/me", headers={"Authorization": "Bearer totally.invalid.token"})
    assert r.status_code in (401, 403)
    print("PASS")


# ── Screening tests ───────────────────────────────────────────

SAMPLE_JD = """
Senior Python Backend Engineer — 4+ years required.
Must have: Python, FastAPI, PostgreSQL, Docker, AWS, REST API, Git.
Nice to have: Redis, Kubernetes, Kafka.
Strong communication skills. Agile/Scrum environment.
B.Tech Computer Science or equivalent required.
"""

def test_screen_unauthenticated():
    print("\n── test_screen (unauthenticated)")
    r = client.post("/screen", data={"job_description": SAMPLE_JD})
    assert r.status_code in (401, 403)
    print("PASS")


def test_screen_short_jd():
    print("\n── test_screen (JD too short)")
    token = register_and_login("shortjd@example.com")
    pdf   = make_pdf_bytes()
    r = client.post(
        "/screen",
        data={"job_description": "Too short"},
        files=[("files", ("resume.pdf", pdf, "application/pdf"))],
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422
    print("PASS")


def test_screen_no_files():
    print("\n── test_screen (no files)")
    token = register_and_login("nofiles@example.com")
    r = client.post(
        "/screen",
        data={"job_description": SAMPLE_JD},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422
    print("PASS")


def test_screen_non_pdf():
    print("\n── test_screen (non-PDF file)")
    token = register_and_login("nonpdf@example.com")
    r = client.post(
        "/screen",
        data={"job_description": SAMPLE_JD},
        files=[("files", ("resume.docx", b"not a pdf", "application/octet-stream"))],
        headers={"Authorization": f"Bearer {token}"},
    )
    # Either 400 (all files rejected) or 422
    assert r.status_code in (400, 422)
    print("PASS")


def test_screen_full_pipeline_mocked():
    print("\n── test_screen (full pipeline, mocked LLM + embeddings)")
    token = register_and_login("fullpipeline@example.com")
    pdf   = make_pdf_bytes("Python FastAPI PostgreSQL Docker AWS senior engineer")

    mock_parsed = MagicMock()
    mock_parsed.name     = "Test Candidate"
    mock_parsed.skills   = ["Python", "FastAPI", "PostgreSQL", "Docker", "AWS"]
    mock_parsed.experience = ["Senior Engineer at TechCorp (2020-2024)"]
    mock_parsed.projects  = ["API Platform: FastAPI + PostgreSQL"]
    mock_parsed.education = ["B.Tech CS"]

    with patch("main.parse_resume",        return_value=(mock_parsed, None)), \
         patch("scorer.compute_semantic_similarity", return_value=75.0):

        r = client.post(
            "/screen",
            data={"job_description": SAMPLE_JD},
            files=[("files", ("alice.pdf", pdf, "application/pdf"))],
            headers={"Authorization": f"Bearer {token}"},
        )

    assert r.status_code == 200, r.json()
    data = r.json()
    assert "session_id" in data
    assert data["total_candidates"] == 1
    assert len(data["results"]) == 1
    result = data["results"][0]
    assert result["rank"] == 1
    assert result["score"] > 0
    assert "recommendation" in result
    assert isinstance(result["strengths"], list)
    assert isinstance(result["gaps"], list)
    print(f"  Score: {result['score']}, Rec: {result['recommendation']}")
    print("PASS")


def test_screen_multi_resume_ranking():
    print("\n── test_screen (multi-resume ranking)")
    token = register_and_login("multiresume@example.com")

    strong_pdf = make_pdf_bytes("Python FastAPI PostgreSQL Docker AWS Kubernetes Redis Git CI/CD microservices")
    weak_pdf   = make_pdf_bytes("Photoshop Illustrator Canva graphic design")

    strong_parsed = MagicMock()
    strong_parsed.name = "Alice Strong"
    strong_parsed.skills = ["Python", "FastAPI", "PostgreSQL", "Docker", "AWS", "Redis"]
    strong_parsed.experience = strong_parsed.projects = strong_parsed.education = []

    weak_parsed = MagicMock()
    weak_parsed.name = "Bob Weak"
    weak_parsed.skills = ["Photoshop", "Illustrator"]
    weak_parsed.experience = weak_parsed.projects = weak_parsed.education = []

    call_count = [0]
    def side_effect_parse(text, filename):
        call_count[0] += 1
        if "strong" in filename:
            return (strong_parsed, None)
        return (weak_parsed, None)

    def side_effect_semantic(jd, resume):
        if "Alice" in resume or "Python" in resume:
            return 85.0
        return 10.0

    with patch("main.parse_resume", side_effect=side_effect_parse), \
         patch("scorer.compute_semantic_similarity", side_effect=side_effect_semantic):

        r = client.post(
            "/screen",
            data={"job_description": SAMPLE_JD},
            files=[
                ("files", ("strong_alice.pdf", strong_pdf, "application/pdf")),
                ("files", ("weak_bob.pdf",     weak_pdf,   "application/pdf")),
            ],
            headers={"Authorization": f"Bearer {token}"},
        )

    assert r.status_code == 200, r.json()
    results = r.json()["results"]
    assert len(results) == 2
    assert results[0]["score"] > results[1]["score"], "Should be sorted by score desc"
    assert results[0]["rank"] == 1
    assert results[1]["rank"] == 2
    print(f"  #1 {results[0]['filename']}: {results[0]['score']}")
    print(f"  #2 {results[1]['filename']}: {results[1]['score']}")
    print("PASS")


def test_export_not_found():
    print("\n── test_export (session not found)")
    token = register_and_login("exporttest@example.com")
    r = client.get(
        "/screen/export/nonexistent-session-id",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404
    print("PASS")


def test_history_empty():
    print("\n── test_history (empty for new user)")
    token = register_and_login("historytest@example.com")
    r = client.get(
        "/screen/history",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert isinstance(r.json()["sessions"], list)
    print("PASS")


# ── Cleanup ────────────────────────────────────────────────────

def cleanup():
    """Remove test SQLite DB after all tests."""
    import os
    try:
        os.remove("test_integration.db")
        print("\nTest DB cleaned up.")
    except FileNotFoundError:
        pass


if __name__ == "__main__":
    passed = 0
    failed = 0

    tests = [
        test_health, test_root,
        test_signup_success, test_signup_weak_password, test_signup_invalid_email,
        test_login_success, test_login_wrong_password, test_login_nonexistent_user,
        test_get_me_authenticated, test_get_me_unauthenticated, test_get_me_bad_token,
        test_screen_unauthenticated, test_screen_short_jd, test_screen_no_files,
        test_screen_non_pdf, test_screen_full_pipeline_mocked,
        test_screen_multi_resume_ranking,
        test_export_not_found, test_history_empty,
    ]

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"FAIL: {test.__name__}: {e}")

    cleanup()

    print(f"\n{'='*50}")
    print(f"Integration tests: {passed} passed, {failed} failed")
    if failed:
        sys.exit(1)