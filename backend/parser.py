"""
parser.py
---------
Resume parsing via Groq LLM (llama-3.3-70b-versatile).

Architecture:
  parse_resume()          → main public function, returns ParsedResume
  _call_groq()            → raw API call, returns response string
  _extract_json_from_response() → finds + validates JSON from LLM output
  _build_prompt()         → constructs the structured extraction prompt
  _sanitize_parsed()      → cleans/normalises the parsed dict

Error handling strategy:
  - LLM may return markdown fences (```json ... ```) → strip them
  - LLM may hallucinate extra keys → whitelist-filter
  - LLM may return partial JSON → attempt repair, then fallback
  - Network/API errors → return empty ParsedResume with error logged
  - Never raise — always return something usable
"""

import json
import re
import logging
import time
from typing import Optional, Any

from groq import Groq
from groq import APIConnectionError, APIStatusError, RateLimitError

from database import get_settings
from schemas import ParsedResume

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Groq client (module-level singleton) ──────────────────────────────────────
_groq_client: Optional[Groq] = None


def get_groq_client() -> Groq:
    """Lazy singleton — instantiated once, reused across requests."""
    global _groq_client
    if _groq_client is None:
        _groq_client = Groq(api_key=settings.GROQ_API_KEY)
    return _groq_client


# ── Prompt engineering ────────────────────────────────────────────────────────

def _build_prompt(resume_text: str) -> str:
    """
    Build the system + user prompt for resume parsing.

    Key prompt engineering decisions:
    1. Explicit JSON schema in the prompt (not just "return JSON")
    2. All fields specified with types and examples
    3. "ONLY return the JSON object" — prevents preamble/postamble
    4. Null-safe instructions — tell model to use [] not null
    5. Name extraction heuristic — first line is usually the candidate name
    """
    return f"""You are an expert resume parser. Your only job is to extract structured information from resume text and return it as a valid JSON object.

STRICT RULES:
1. Return ONLY a valid JSON object. No explanation, no markdown, no extra text.
2. Do not wrap in ```json``` code blocks.
3. Every array field must be a JSON array (use [] if empty, never null).
4. Extract actual content — do not summarize or paraphrase skills/technologies.
5. For the "name" field, extract the candidate's full name (usually the first line or heading).

Return this exact JSON structure:
{{
  "name": "Full Name of candidate or null if not found",
  "skills": ["skill1", "skill2", "skill3"],
  "experience": [
    "Job Title at Company Name (Year - Year): key responsibility or achievement",
    "Job Title at Company Name (Year - Year): key responsibility or achievement"
  ],
  "projects": [
    "Project Name: brief description including technologies used",
    "Project Name: brief description including technologies used"
  ],
  "education": [
    "Degree, Major - Institution Name (Year)",
    "Certification Name - Issuing Body (Year)"
  ]
}}

EXTRACTION GUIDELINES:
- skills: Extract ALL technical skills, programming languages, frameworks, tools, databases, cloud platforms, methodologies. Each skill as a short string (e.g. "Python", "React", "AWS S3", "Agile").
- experience: Each job as ONE string. Include title, company, dates, and 1-2 key achievements.
- projects: Each project as ONE string. Include name, tech stack, and purpose.
- education: Each degree/certification as ONE string.
- name: Look for a prominent name at the top of the resume. Return null if unclear.

RESUME TEXT:
---
{resume_text[:6000]}
---

Return ONLY the JSON object now:"""


# ── JSON extraction + repair ──────────────────────────────────────────────────

def _strip_markdown_fences(text: str) -> str:
    """
    Remove ```json ... ``` or ``` ... ``` code fences that LLMs often add
    despite being instructed not to.
    """
    # Match ```json ... ``` or ``` ... ```
    fence_pattern = re.compile(
        r"```(?:json)?\s*([\s\S]*?)\s*```",
        re.IGNORECASE,
    )
    match = fence_pattern.search(text)
    if match:
        return match.group(1).strip()
    return text.strip()


def _find_json_object(text: str) -> Optional[str]:
    """
    Find the first complete JSON object in text using brace counting.
    Handles cases where the LLM adds text before or after the JSON.
    """
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
                return text[start : i + 1]

    return None


def _repair_json(broken: str) -> Optional[str]:
    """
    Attempt light repair on truncated/malformed JSON.

    Common LLM failures we handle:
    1. Truncated mid-array → close the array and object
    2. Trailing comma before } or ] → remove
    3. Single quotes instead of double quotes → replace
    """
    if not broken:
        return None

    # Replace single quotes used as string delimiters (naive but effective for simple cases)
    # Only replace when not inside a double-quoted string
    repaired = broken

    # Remove trailing commas before ] or }
    repaired = re.sub(r",\s*([}\]])", r"\1", repaired)

    # Try to close open structures if truncated
    open_braces = repaired.count("{") - repaired.count("}")
    open_brackets = repaired.count("[") - repaired.count("]")

    if open_braces > 0 or open_brackets > 0:
        # Close innermost open string if any
        if repaired.count('"') % 2 != 0:
            repaired += '"'
        repaired += "]" * max(0, open_brackets)
        repaired += "}" * max(0, open_braces)

    try:
        json.loads(repaired)
        logger.info("JSON repair succeeded.")
        return repaired
    except json.JSONDecodeError:
        return None


def _extract_json_from_response(raw_response: str) -> Optional[dict]:
    """
    Multi-strategy JSON extraction:
    Strategy 1: Direct parse (ideal case — model returned clean JSON)
    Strategy 2: Strip markdown fences, then parse
    Strategy 3: Find JSON object by brace matching
    Strategy 4: Repair truncated JSON
    Strategy 5: Give up, return None (caller handles fallback)
    """
    if not raw_response or not raw_response.strip():
        logger.error("LLM returned empty response.")
        return None

    candidates = [
        raw_response.strip(),
        _strip_markdown_fences(raw_response),
    ]

    # Strategy 1 + 2: Direct parse
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    # Strategy 3: Find JSON object by brace matching
    for candidate in candidates:
        json_str = _find_json_object(candidate)
        if json_str:
            try:
                parsed = json.loads(json_str)
                if isinstance(parsed, dict):
                    logger.info("JSON extracted via brace matching.")
                    return parsed
            except json.JSONDecodeError:
                # Try repair on this extracted substring
                repaired = _repair_json(json_str)
                if repaired:
                    try:
                        parsed = json.loads(repaired)
                        if isinstance(parsed, dict):
                            return parsed
                    except json.JSONDecodeError:
                        pass

    logger.error(
        "All JSON extraction strategies failed. Raw response (first 500 chars): %s",
        raw_response[:500],
    )
    return None


# ── Output sanitisation ───────────────────────────────────────────────────────

def _sanitize_parsed(data: dict) -> dict:
    """
    Whitelist filter + type coercion on LLM output.

    Goals:
    - Remove any hallucinated keys (only keep our 5 fields)
    - Ensure every list field is actually a list
    - Ensure every list item is a non-empty string
    - Ensure name is str or None
    - Deduplicate skills (LLM sometimes repeats)
    - Normalise skill capitalisation lightly
    """
    ALLOWED_FIELDS = {"name", "skills", "experience", "projects", "education"}
    LIST_FIELDS = {"skills", "experience", "projects", "education"}

    result = {}

    # name
    name = data.get("name")
    result["name"] = str(name).strip() if name and str(name).strip().lower() != "null" else None

    # list fields
    for field in LIST_FIELDS:
        raw_value = data.get(field, [])

        # Handle case where LLM returns a string instead of a list
        if isinstance(raw_value, str):
            # Try to split on commas or newlines
            raw_value = [item.strip() for item in re.split(r"[,\n]+", raw_value)]

        if not isinstance(raw_value, list):
            raw_value = []

        # Filter + clean each item
        cleaned_items = []
        for item in raw_value:
            if not isinstance(item, str):
                item = str(item)
            item = item.strip()
            # Remove empty, very short, or obviously junk entries
            if len(item) < 2:
                continue
            # Remove bullet characters that sometimes leak through
            item = item.lstrip("•-–—*·▪▸►✓✔ ")
            if item:
                cleaned_items.append(item)

        # Deduplicate skills (case-insensitive)
        if field == "skills":
            seen = set()
            deduped = []
            for skill in cleaned_items:
                normalised = skill.lower().strip()
                if normalised not in seen:
                    seen.add(normalised)
                    deduped.append(skill)
            result[field] = deduped
        else:
            result[field] = cleaned_items

    return result


# ── Groq API call ─────────────────────────────────────────────────────────────

def _call_groq(prompt: str, filename: str = "unknown") -> Optional[str]:
    """
    Make the Groq API call with retry on rate limit.

    Returns:
        Raw string from the model, or None on failure.
    """
    client = get_groq_client()
    max_retries = 3
    base_delay = 2.0  # seconds

    for attempt in range(1, max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                temperature=0.0,        # Deterministic — we want consistent JSON
                max_tokens=2048,        # Enough for a full structured resume
                top_p=1,
                stream=False,
            )
            content = response.choices[0].message.content
            logger.info(
                "[%s] Groq call succeeded on attempt %d. Tokens used: %d",
                filename, attempt,
                response.usage.total_tokens if response.usage else 0,
            )
            return content

        except RateLimitError as e:
            wait = base_delay * (2 ** (attempt - 1))
            logger.warning(
                "[%s] Groq rate limit hit (attempt %d/%d). Waiting %.1fs: %s",
                filename, attempt, max_retries, wait, e,
            )
            if attempt < max_retries:
                time.sleep(wait)
            else:
                logger.error("[%s] Groq rate limit: all retries exhausted.", filename)
                return None

        except APIConnectionError as e:
            logger.error("[%s] Groq connection error: %s", filename, e)
            return None

        except APIStatusError as e:
            logger.error(
                "[%s] Groq API error (status %d): %s",
                filename, e.status_code, e.message,
            )
            return None

        except Exception as e:
            logger.exception("[%s] Unexpected Groq error on attempt %d", filename, attempt)
            if attempt < max_retries:
                time.sleep(base_delay)
            else:
                return None

    return None


# ── Public API ────────────────────────────────────────────────────────────────

def parse_resume(
    resume_text: str,
    filename: str = "unknown.pdf",
) -> tuple[ParsedResume, Optional[str]]:
    """
    Parse a resume text into structured data using Groq LLM.

    Args:
        resume_text: Clean text extracted from PDF (via utils.py)
        filename:    Original filename (for logging only)

    Returns:
        (ParsedResume, error_message)
        - On success: (populated ParsedResume, None)
        - On partial success: (partially populated ParsedResume, warning message)
        - On full failure: (empty ParsedResume, error message)

    The caller should always use the ParsedResume even on error —
    it will contain whatever could be extracted (or empty lists).
    """
    if not resume_text or not resume_text.strip():
        return ParsedResume(), "Empty resume text provided."

    # Truncate very long resumes to avoid token limits
    # 6000 chars ≈ ~1500 tokens, well within context window
    if len(resume_text) > 8000:
        logger.warning(
            "[%s] Resume text truncated from %d to 8000 chars.",
            filename, len(resume_text),
        )
        resume_text = resume_text[:8000]

    prompt = _build_prompt(resume_text)
    raw_response = _call_groq(prompt, filename)

    if raw_response is None:
        return (
            ParsedResume(),
            f"[{filename}] LLM API call failed. Check logs for details.",
        )

    parsed_dict = _extract_json_from_response(raw_response)

    if parsed_dict is None:
        return (
            ParsedResume(),
            f"[{filename}] LLM returned unparseable output. "
            f"Raw (first 300 chars): {raw_response[:300]}",
        )

    sanitized = _sanitize_parsed(parsed_dict)

    # Validate via Pydantic
    try:
        result = ParsedResume(**sanitized)
    except Exception as validation_err:
        logger.error("[%s] Pydantic validation failed: %s", filename, validation_err)
        # Still return what we have — better than nothing
        result = ParsedResume(
            name=sanitized.get("name"),
            skills=sanitized.get("skills", []),
            experience=sanitized.get("experience", []),
            projects=sanitized.get("projects", []),
            education=sanitized.get("education", []),
        )

    # Warn if suspiciously empty
    total_items = (
        len(result.skills)
        + len(result.experience)
        + len(result.projects)
        + len(result.education)
    )
    if total_items == 0:
        return (
            result,
            f"[{filename}] LLM parse succeeded but all fields are empty. "
            "Resume text may be too short or unstructured.",
        )

    logger.info(
        "[%s] Parsed: name=%r, skills=%d, exp=%d, proj=%d, edu=%d",
        filename,
        result.name,
        len(result.skills),
        len(result.experience),
        len(result.projects),
        len(result.education),
    )
    return result, None


# ── Batch parsing ─────────────────────────────────────────────────────────────

def parse_resumes_batch(
    resume_texts: list[dict],
) -> list[dict]:
    """
    Parse multiple resumes sequentially.

    Args:
        resume_texts: list of {"filename": str, "text": str}

    Returns:
        list of {
            "filename": str,
            "parsed": ParsedResume,
            "success": bool,
            "error": str | None,
        }
    """
    results = []
    for item in resume_texts:
        filename = item.get("filename", "unknown.pdf")
        text = item.get("text", "")

        parsed, error = parse_resume(text, filename)
        results.append({
            "filename": filename,
            "parsed": parsed,
            "success": error is None,
            "error": error,
        })

    return results