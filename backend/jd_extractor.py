"""
jd_extractor.py
---------------
Job Description skill extraction using Groq LLM.

Why LLM instead of rule-based?
  - Handles ANY job domain (tech, finance, healthcare, marketing, etc.)
  - Extracts implicit skills ("build scalable APIs" -> FastAPI, REST, Python)
  - Understands context — doesn't confuse "Python" (language) with generic words
  - No need to maintain a 300-entry master skills list

Architecture:
  extract_jd_skills()   -> main public function, returns JDSkills
  get_jd_skill_set()    -> convenience wrapper returning a normalised set
  _call_groq_jd()       -> raw Groq API call with retry
  _extract_json()       -> JSON extraction + sanitisation (same as parser.py)

Error handling:
  - LLM failure -> returns empty JDSkills (scoring returns 0 skill match)
  - Never raises — always returns something usable
"""

import json
import re
import time
import logging
from dataclasses import dataclass, field
from typing import Optional

from groq import Groq, RateLimitError, APIConnectionError, APIStatusError

from database import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Groq client singleton ─────────────────────────────────────────────────────
_groq_client: Optional[Groq] = None


def _get_groq_client() -> Groq:
    global _groq_client
    if _groq_client is None:
        _groq_client = Groq(api_key=settings.GROQ_API_KEY)
    return _groq_client


# ── Output dataclass ──────────────────────────────────────────────────────────

@dataclass
class JDSkills:
    raw_text: str = ""
    tech_skills: list = field(default_factory=list)
    soft_skills: list = field(default_factory=list)
    all_skills: list = field(default_factory=list)
    experience_requirements: list = field(default_factory=list)
    education_requirements: list = field(default_factory=list)
    keywords: list = field(default_factory=list)


# ── Prompt ────────────────────────────────────────────────────────────────────

def _build_jd_prompt(jd_text: str) -> str:
    return f"""You are an expert job description analyser. Extract structured requirements from the job description below.

STRICT RULES:
1. Return ONLY a valid JSON object — no explanation, no markdown, no code fences.
2. Extract REAL skills/tools/technologies only — not generic words like "experience", "team", "role".
3. tech_skills: programming languages, frameworks, libraries, databases, cloud platforms, DevOps tools, methodologies, protocols, APIs. Each as a SHORT string (e.g. "Python", "FastAPI", "AWS S3", "CI/CD", "REST APIs").
4. soft_skills: communication, leadership, teamwork, problem-solving, mentoring, etc.
5. experience_requirements: strings like "3+ years of Python", "2+ years backend development".
6. education_requirements: strings like "Bachelor's in Computer Science", "B.Tech or equivalent".
7. keywords: ALL meaningful domain terms that describe the role for semantic matching (broader than tech_skills — include things like "microservices", "API design", "cloud infrastructure", "data pipelines").
8. Use [] for any empty field — never null.
9. Deduplicate: never repeat the same item.
10. Be EXHAUSTIVE for tech_skills — extract every single technology mentioned anywhere in the JD.
11. NEVER extract section headings, generic phrases, or boilerplate like "Basic Qualifications", "Key Responsibilities", "Preferred Qualifications", "Bachelor's degree", "Developer", "Problem Solving", "Information Technology", "Adept", "Verifying", "Troubleshooting". Only concrete skills/tools.

Return EXACTLY this JSON structure:
{{
  "tech_skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "AWS", "REST APIs"],
  "soft_skills": ["Communication", "Problem-solving", "Teamwork"],
  "experience_requirements": ["4+ years of Python", "2+ years with REST APIs"],
  "education_requirements": ["Bachelor's in Computer Science or equivalent"],
  "keywords": ["backend", "microservices", "API design", "cloud infrastructure", "distributed systems"]
}}

JOB DESCRIPTION:
---
{jd_text[:4000]}
---

Return ONLY the JSON now:"""


# ── JSON extraction ───────────────────────────────────────────────────────────

def _strip_fences(text: str) -> str:
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    return match.group(1).strip() if match else text.strip()


def _find_json_object(text: str) -> Optional[str]:
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_string = False
    escape_next = False
    for i, char in enumerate(text[start:], start=start):
        if escape_next:
            escape_next = False
            continue
        if char == "\\" and in_string:
            escape_next = True
            continue
        if char == '"' and not escape_next:
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start: i + 1]
    return None


def _extract_json(raw: str) -> Optional[dict]:
    if not raw or not raw.strip():
        return None
    for candidate in [raw.strip(), _strip_fences(raw)]:
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
    for candidate in [raw.strip(), _strip_fences(raw)]:
        json_str = _find_json_object(candidate)
        if json_str:
            try:
                parsed = json.loads(json_str)
                if isinstance(parsed, dict):
                    logger.info("JD JSON extracted via brace matching.")
                    return parsed
            except json.JSONDecodeError:
                pass
    logger.error("JD JSON extraction failed. Raw (first 300): %s", raw[:300])
    return None


def _sanitize_list(value, min_len: int = 1, max_words: int = 8) -> list:
    """Clean and deduplicate a list field from LLM output."""
    if isinstance(value, str):
        value = [item.strip() for item in re.split(r"[,\n]+", value)]
    if not isinstance(value, list):
        return []
    cleaned = []
    seen = set()
    for item in value:
        if not isinstance(item, str):
            item = str(item)
        item = item.strip().lstrip("*-—•")
        item = item.strip()
        if len(item) < min_len:
            continue
        # Truncate overly long entries
        words = item.split()
        if len(words) > max_words:
            item = " ".join(words[:max_words])
        norm = item.lower().strip()
        if norm not in seen:
            seen.add(norm)
            cleaned.append(item)
    return cleaned


# ── Groq API call ─────────────────────────────────────────────────────────────

def _call_groq_jd(prompt: str) -> Optional[str]:
    """Call Groq with retry on rate limit. Returns raw string or None."""
    client = _get_groq_client()
    max_retries = 3
    base_delay = 2.0

    for attempt in range(1, max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=1024,
                stream=False,
            )
            content = response.choices[0].message.content
            logger.info(
                "JD Groq call succeeded (attempt %d, tokens: %d)",
                attempt,
                response.usage.total_tokens if response.usage else 0,
            )
            return content

        except RateLimitError:
            wait = base_delay * (2 ** (attempt - 1))
            logger.warning("JD Groq rate limit (attempt %d/%d), waiting %.1fs", attempt, max_retries, wait)
            if attempt < max_retries:
                time.sleep(wait)
            else:
                return None
        except (APIConnectionError, APIStatusError) as e:
            logger.error("JD Groq API error: %s", e)
            return None
        except Exception as e:
            logger.exception("JD Groq unexpected error (attempt %d)", attempt)
            if attempt < max_retries:
                time.sleep(base_delay)
            else:
                return None

    return None


# ── Public API ────────────────────────────────────────────────────────────────

def extract_jd_skills(jd_text: str) -> JDSkills:
    """
    Extract skills and requirements from a Job Description using Groq LLM.

    Args:
        jd_text: Raw JD text (plain text, any industry/domain)

    Returns:
        JDSkills dataclass — always returns a valid object even on LLM failure.
        On failure, all lists are empty (scorer returns 0 for skill match component).
    """
    if not jd_text or not jd_text.strip():
        logger.warning("Empty JD text provided to extract_jd_skills().")
        return JDSkills()

    prompt = _build_jd_prompt(jd_text)
    raw_response = _call_groq_jd(prompt)

    if raw_response is None:
        logger.error("JD LLM call failed — returning empty JDSkills.")
        return JDSkills(raw_text=jd_text)

    parsed = _extract_json(raw_response)

    if parsed is None:
        logger.error("JD JSON parse failed — returning empty JDSkills.")
        return JDSkills(raw_text=jd_text)

    tech_skills = _sanitize_list(parsed.get("tech_skills", []),              min_len=1, max_words=5)
    soft_skills = _sanitize_list(parsed.get("soft_skills", []),              min_len=2, max_words=5)
    exp_reqs    = _sanitize_list(parsed.get("experience_requirements", []),  min_len=3, max_words=10)
    edu_reqs    = _sanitize_list(parsed.get("education_requirements", []),   min_len=3, max_words=10)
    keywords    = _sanitize_list(parsed.get("keywords", []),                 min_len=2, max_words=6)

    # all_skills = tech + soft, deduplicated
    seen = set()
    all_skills = []
    for skill in tech_skills + soft_skills:
        norm = skill.lower().strip()
        if norm not in seen:
            seen.add(norm)
            all_skills.append(skill)

    result = JDSkills(
        raw_text=jd_text,
        tech_skills=tech_skills,
        soft_skills=soft_skills,
        all_skills=all_skills,
        experience_requirements=exp_reqs,
        education_requirements=edu_reqs,
        keywords=keywords,
    )

    logger.info(
        "JD LLM extraction: %d tech, %d soft, %d exp_req, %d edu_req, %d keywords",
        len(tech_skills), len(soft_skills),
        len(exp_reqs), len(edu_reqs), len(keywords),
    )
    return result


def get_jd_skill_set(jd_text: str) -> set:
    """
    Convenience wrapper — returns normalised set of all JD skills.
    Used by scorer.py for O(1) membership testing.
    """
    jd_skills = extract_jd_skills(jd_text)
    return {s.lower().strip() for s in jd_skills.all_skills}