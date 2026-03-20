"""
test_parser.py
--------------
Tests for parser.py — both unit tests (no API call)
and an integration test (real Groq API call).

Run unit tests only:
    python test_parser.py

Run with real API call:
    python test_parser.py --integration
"""

import sys
import json
from unittest.mock import patch, MagicMock

# ── Unit tests (no API calls) ─────────────────────────────────────────────────

from parser import (
    _strip_markdown_fences,
    _find_json_object,
    _repair_json,
    _extract_json_from_response,
    _sanitize_parsed,
)


def test_strip_markdown_fences():
    print("\n── test_strip_markdown_fences ───────────────────")

    # With ```json fence
    raw = '```json\n{"name": "Alice"}\n```'
    result = _strip_markdown_fences(raw)
    assert result == '{"name": "Alice"}', f"Got: {result}"

    # With plain ``` fence
    raw2 = '```\n{"name": "Bob"}\n```'
    assert _strip_markdown_fences(raw2) == '{"name": "Bob"}'

    # No fence — should return original
    raw3 = '{"name": "Carol"}'
    assert _strip_markdown_fences(raw3) == '{"name": "Carol"}'

    print("PASS")


def test_find_json_object():
    print("\n── test_find_json_object ────────────────────────")

    # JSON preceded by text
    text = 'Here is the JSON: {"name": "Alice", "skills": ["Python"]}'
    result = _find_json_object(text)
    assert result == '{"name": "Alice", "skills": ["Python"]}', f"Got: {result}"

    # Nested JSON
    text2 = '{"outer": {"inner": "value"}}'
    result2 = _find_json_object(text2)
    assert result2 == '{"outer": {"inner": "value"}}', f"Got: {result2}"

    # No JSON
    assert _find_json_object("no json here") is None

    print("PASS")


def test_repair_json():
    print("\n── test_repair_json ─────────────────────────────")

    # Trailing comma
    broken = '{"skills": ["Python", "React",]}'
    repaired = _repair_json(broken)
    assert repaired is not None
    parsed = json.loads(repaired)
    assert parsed["skills"] == ["Python", "React"]

    # Truncated — missing closing brackets
    broken2 = '{"skills": ["Python", "React"'
    repaired2 = _repair_json(broken2)
    assert repaired2 is not None
    parsed2 = json.loads(repaired2)
    assert "skills" in parsed2

    print("PASS")


def test_extract_json_from_response():
    print("\n── test_extract_json_from_response ──────────────")

    # Case 1: Clean JSON
    clean = '{"name": "Alice", "skills": ["Python"]}'
    result = _extract_json_from_response(clean)
    assert result == {"name": "Alice", "skills": ["Python"]}

    # Case 2: Fenced JSON
    fenced = '```json\n{"name": "Bob", "skills": []}\n```'
    result2 = _extract_json_from_response(fenced)
    assert result2["name"] == "Bob"

    # Case 3: JSON buried in text
    buried = 'Here is my response:\n{"name": "Carol", "skills": ["Go"]}\nEnd.'
    result3 = _extract_json_from_response(buried)
    assert result3["name"] == "Carol"

    # Case 4: Completely invalid
    assert _extract_json_from_response("This is not JSON at all.") is None

    # Case 5: Empty
    assert _extract_json_from_response("") is None

    print("PASS")


def test_sanitize_parsed():
    print("\n── test_sanitize_parsed ─────────────────────────")

    raw = {
        "name": "Alice Johnson",
        "skills": ["Python", "python", "  React  ", "•Django", "", "A"],
        "experience": ["Engineer at Acme (2020-2023): built APIs"],
        "projects": ["ResumeAI: AI tool using Python and FastAPI"],
        "education": ["B.Tech Computer Science - IIT Delhi (2020)"],
        "hallucinated_field": "should be removed",  # extra key
    }

    result = _sanitize_parsed(raw)

    assert "hallucinated_field" not in result, "Hallucinated key not removed"
    assert result["name"] == "Alice Johnson"
    # "python" deduped with "Python"
    skill_lower = [s.lower() for s in result["skills"]]
    assert skill_lower.count("python") == 1, "Duplicate skill not removed"
    # "A" is too short (len < 2)
    assert "A" not in result["skills"], "Short skill not removed"
    # "React" should be stripped of whitespace
    assert "React" in result["skills"]
    # "•Django" should have bullet removed
    assert "Django" in result["skills"]

    print("PASS")


def test_parse_resume_with_mock():
    """Test parse_resume() end-to-end with a mocked Groq API call."""
    print("\n── test_parse_resume_with_mock ──────────────────")
    from parser import parse_resume

    mock_json = json.dumps({
        "name": "Jane Doe",
        "skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
        "experience": [
            "Backend Engineer at TechCorp (2021-2024): Built REST APIs serving 1M req/day"
        ],
        "projects": [
            "AI Resume Screener: Full-stack app using FastAPI, React, and Groq LLM"
        ],
        "education": ["B.Sc Computer Science - Delhi University (2021)"],
    })

    with patch("parser._call_groq", return_value=mock_json):
        parsed, error = parse_resume("some resume text", "test_resume.pdf")

    assert error is None, f"Unexpected error: {error}"
    assert parsed.name == "Jane Doe"
    assert "Python" in parsed.skills
    assert len(parsed.experience) == 1
    assert len(parsed.projects) == 1
    assert len(parsed.education) == 1
    print(f"  name={parsed.name}")
    print(f"  skills={parsed.skills}")
    print("PASS")


def test_parse_resume_bad_llm_output():
    """Test graceful handling when LLM returns garbage."""
    print("\n── test_parse_resume_bad_llm_output ────────────")
    from parser import parse_resume

    with patch("parser._call_groq", return_value="I cannot parse this resume."):
        parsed, error = parse_resume("some text", "bad_resume.pdf")

    assert error is not None, "Expected an error message"
    assert isinstance(parsed.skills, list), "Should still return a ParsedResume"
    print(f"  Error correctly returned: {error[:80]}...")
    print("PASS")


# ── Integration test (real API) ───────────────────────────────────────────────

SAMPLE_RESUME = """
John Smith
john.smith@email.com | github.com/johnsmith | linkedin.com/in/johnsmith

SKILLS
Python, FastAPI, Django, React, TypeScript, PostgreSQL, Redis, Docker, 
Kubernetes, AWS (EC2, S3, Lambda), Git, CI/CD, Agile/Scrum

EXPERIENCE
Senior Software Engineer — Acme Technologies (Jan 2022 – Present)
- Designed and built microservices handling 500K daily requests using FastAPI + PostgreSQL
- Reduced API latency by 40% through Redis caching and query optimisation
- Led a team of 4 engineers, conducted code reviews, mentored junior devs

Software Engineer — StartupXYZ (Jun 2019 – Dec 2021)
- Built full-stack web app using React + Django REST Framework
- Integrated Stripe payment gateway processing $2M/month
- Implemented CI/CD pipeline using GitHub Actions + Docker

PROJECTS
AI Resume Screener: Built an LLM-powered resume ranking system using FastAPI, 
Groq API (Llama 3), sentence-transformers, and React. Deployed on AWS.

Portfolio Website: Personal site built with Next.js, TypeScript, Tailwind CSS.

EDUCATION
B.Tech in Computer Science — Indian Institute of Technology Delhi (2019)
AWS Certified Solutions Architect — Amazon Web Services (2022)
"""


def run_integration_test():
    print("\n── INTEGRATION TEST (real Groq API call) ────────")
    print("  Calling Groq API... (this takes 2-5 seconds)")
    from parser import parse_resume

    parsed, error = parse_resume(SAMPLE_RESUME, "john_smith_resume.pdf")

    if error:
        print(f"  ERROR: {error}")
    else:
        print(f"  name:       {parsed.name}")
        print(f"  skills:     {parsed.skills[:5]}{'...' if len(parsed.skills) > 5 else ''}")
        print(f"  experience: {len(parsed.experience)} entries")
        print(f"  projects:   {len(parsed.projects)} entries")
        print(f"  education:  {parsed.education}")
        print("  PASS")


if __name__ == "__main__":
    # Always run unit tests
    test_strip_markdown_fences()
    test_find_json_object()
    test_repair_json()
    test_extract_json_from_response()
    test_sanitize_parsed()
    test_parse_resume_with_mock()
    test_parse_resume_bad_llm_output()

    # Only run integration test if --integration flag is passed
    if "--integration" in sys.argv:
        run_integration_test()
    else:
        print("\n  (Tip: run with --integration to make a real Groq API call)")

    print("\nAll unit tests passed.")