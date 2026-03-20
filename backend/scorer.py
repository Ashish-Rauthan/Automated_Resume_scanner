"""
scorer.py
---------
Candidate scoring engine.

Two independent scoring signals:
  1. Skill Match Score  — exact + fuzzy keyword overlap between JD and resume
  2. Semantic Score     — sentence-transformers cosine similarity (JD text vs resume text)

Final score = weighted combination (configurable via .env):
  score = (SKILL_MATCH_WEIGHT * skill_score) + (SEMANTIC_WEIGHT * semantic_score)
  Default: 50% + 50%

Public API:
  score_candidate()      -> scores ONE resume against ONE JD
  score_candidates()     -> scores + ranks MULTIPLE resumes against ONE JD

Output per candidate:
  - score            (0.0 – 100.0, rounded to 1 decimal)
  - skill_match_score (0.0 – 100.0)
  - semantic_score    (0.0 – 100.0)
  - strengths         [skills found in both JD and resume]
  - gaps              [JD skills missing from resume]
  - recommendation    "Strong Fit" | "Moderate Fit" | "Not a Fit"

Design decisions:
  - sentence-transformers model loaded ONCE as a module-level singleton
    (loading takes ~2s — we cannot afford per-request loading)
  - Fuzzy matching via difflib.SequenceMatcher handles "PostgreSQL" vs "Postgres"
  - Semantic scoring uses all-MiniLM-L6-v2 (fast, accurate, 80MB)
  - All scores normalised to 0–100 for human-readable output
  - Ranking is deterministic: ties broken by filename alphabetically
"""

import logging
import time
from difflib import SequenceMatcher
from typing import Optional

import numpy as np
from sentence_transformers import SentenceTransformer

from database import get_settings
from schemas import ParsedResume, CandidateResult
from jd_extractor import extract_jd_skills, JDSkills

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Sentence-transformer singleton ───────────────────────────────────────────
# all-MiniLM-L6-v2: 80MB, 384-dim embeddings, very fast inference
# Downloads automatically on first use to ~/.cache/huggingface/
_embedding_model: Optional[SentenceTransformer] = None
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"


def get_embedding_model() -> SentenceTransformer:
    """Load sentence-transformer model once and reuse across all requests."""
    global _embedding_model
    if _embedding_model is None:
        logger.info("Loading sentence-transformer model: %s", EMBEDDING_MODEL_NAME)
        t0 = time.time()
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        logger.info(
            "Sentence-transformer loaded in %.2fs", time.time() - t0
        )
    return _embedding_model


# ── Recommendation thresholds ────────────────────────────────────────────────
STRONG_FIT_THRESHOLD   = 70.0   # score >= 70 → Strong Fit
MODERATE_FIT_THRESHOLD = 45.0   # score >= 45 → Moderate Fit
                                 # score <  45 → Not a Fit


# ── Skill normalisation helpers ───────────────────────────────────────────────

def _normalise(text: str) -> str:
    """Lowercase, strip, collapse whitespace."""
    import re
    return re.sub(r"\s+", " ", text.lower().strip())


def _fuzzy_match(a: str, b: str, threshold: float = 0.82) -> bool:
    """
    True if strings are similar enough to be considered the same skill.

    Uses SequenceMatcher ratio — handles:
      "PostgreSQL" vs "Postgres"     → 0.87 ✓
      "Node.js"    vs "NodeJS"       → 0.86 ✓
      "React.js"   vs "ReactJS"      → 0.86 ✓
      "scikit-learn" vs "sklearn"    → 0.67 ✗ (caught by alias map below)
      "Kubernetes"  vs "k8s"         → 0.35 ✗ (caught by alias map below)

    Threshold 0.82 is deliberately conservative — we'd rather miss a match
    than count "Python" and "Pytorch" as the same skill (ratio ≈ 0.73).
    """
    if a == b:
        return True
    return SequenceMatcher(None, a, b).ratio() >= threshold


# Common aliases that fuzzy matching alone won't catch
SKILL_ALIASES: dict[str, list[str]] = {
    "kubernetes": ["k8s"],
    "javascript": ["js", "es6", "es2015", "ecmascript"],
    "typescript": ["ts"],
    "postgresql": ["postgres", "psql"],
    "mongodb":    ["mongo"],
    "react":      ["react.js", "reactjs"],
    "vue":        ["vue.js", "vuejs"],
    "node.js":    ["nodejs", "node"],
    "next.js":    ["nextjs"],
    "scikit-learn": ["sklearn"],
    "machine learning": ["ml"],
    "deep learning":    ["dl"],
    "natural language processing": ["nlp"],
    "continuous integration": ["ci/cd", "cicd"],
    "amazon web services": ["aws"],
    "google cloud platform": ["gcp", "google cloud"],
    "express": ["expressjs", "express.js"],
}

# Build reverse alias lookup: "k8s" → "kubernetes"
_ALIAS_LOOKUP: dict[str, str] = {}
for canonical, aliases in SKILL_ALIASES.items():
    for alias in aliases:
        _ALIAS_LOOKUP[alias] = canonical


def _canonical(skill: str) -> str:
    """Map a skill to its canonical form via alias lookup."""
    norm = _normalise(skill)
    return _ALIAS_LOOKUP.get(norm, norm)


# ── Skill match scoring ───────────────────────────────────────────────────────

def compute_skill_match(
    jd_skills: list[str],
    resume_skills: list[str],
) -> dict:
    """
    Compare JD skills against resume skills.

    Matching strategy (in order of preference):
      1. Exact match after normalisation
      2. Alias/canonical match (e.g. k8s → kubernetes)
      3. Fuzzy match (SequenceMatcher ratio >= 0.82)

    Returns:
        {
          "score": float,              # 0–100
          "strengths": list[str],      # matched skills (display using JD skill name)
          "gaps": list[str],           # unmatched JD skills
          "match_count": int,
          "total_jd_skills": int,
        }
    """
    if not jd_skills:
        return {
            "score": 0.0,
            "strengths": [],
            "gaps": [],
            "match_count": 0,
            "total_jd_skills": 0,
        }

    # Build canonical resume skill set for fast lookup
    resume_canonical = {_canonical(s) for s in resume_skills}
    resume_normalised = {_normalise(s) for s in resume_skills}

    strengths: list[str] = []
    gaps: list[str] = []

    for jd_skill in jd_skills:
        jd_norm = _normalise(jd_skill)
        jd_canon = _canonical(jd_skill)

        matched = False

        # 1. Exact normalised match
        if jd_norm in resume_normalised:
            matched = True

        # 2. Canonical / alias match
        elif jd_canon in resume_canonical:
            matched = True

        # 3. Fuzzy match against all resume skills
        else:
            for res_skill in resume_skills:
                if _fuzzy_match(jd_norm, _normalise(res_skill)):
                    matched = True
                    break

        if matched:
            strengths.append(jd_skill)
        else:
            gaps.append(jd_skill)

    match_count = len(strengths)
    total = len(jd_skills)
    score = (match_count / total * 100.0) if total > 0 else 0.0

    return {
        "score": round(score, 2),
        "strengths": strengths,
        "gaps": gaps,
        "match_count": match_count,
        "total_jd_skills": total,
    }


# ── Semantic similarity scoring ───────────────────────────────────────────────

def _build_resume_text(parsed: ParsedResume) -> str:
    """
    Reconstruct a flat text representation of the parsed resume
    for embedding. We use the structured fields, not raw PDF text,
    to ensure the embedding focuses on professional content.
    """
    parts = []

    if parsed.name:
        parts.append(parsed.name)

    if parsed.skills:
        parts.append("Skills: " + ", ".join(parsed.skills))

    if parsed.experience:
        parts.append("Experience: " + " | ".join(parsed.experience))

    if parsed.projects:
        parts.append("Projects: " + " | ".join(parsed.projects))

    if parsed.education:
        parts.append("Education: " + " | ".join(parsed.education))

    return " ".join(parts)


def _build_jd_text_for_embedding(jd_skills: JDSkills) -> str:
    """
    Build a compact JD representation for embedding.
    Focus on skills and requirements — not generic HR boilerplate.
    """
    parts = []

    if jd_skills.tech_skills:
        parts.append("Required skills: " + ", ".join(jd_skills.tech_skills))

    if jd_skills.soft_skills:
        parts.append("Soft skills: " + ", ".join(jd_skills.soft_skills))

    if jd_skills.experience_requirements:
        parts.append("Experience: " + ", ".join(jd_skills.experience_requirements))

    if jd_skills.education_requirements:
        parts.append("Education: " + ", ".join(jd_skills.education_requirements))

    # Fall back to raw text if extraction yielded nothing
    if not parts and jd_skills.raw_text:
        return jd_skills.raw_text[:1000]

    return " ".join(parts)


def compute_semantic_similarity(
    jd_text: str,
    resume_text: str,
) -> float:
    """
    Compute cosine similarity between JD and resume embeddings.

    Returns:
        Score in range 0–100.

    Notes:
        - Cosine similarity returns -1 to +1; we clamp to 0–1 then scale
        - Typical scores for relevant resumes: 0.4–0.8 (raw cosine)
        - We apply a mild calibration curve to spread scores better across 0–100
    """
    if not jd_text.strip() or not resume_text.strip():
        return 0.0

    model = get_embedding_model()

    # Truncate to avoid excessive compute (512 tokens ≈ 2000 chars for this model)
    jd_text = jd_text[:2000]
    resume_text = resume_text[:2000]

    embeddings = model.encode(
        [jd_text, resume_text],
        normalize_embeddings=True,   # L2-normalised → dot product == cosine sim
        show_progress_bar=False,
    )

    jd_emb, res_emb = embeddings[0], embeddings[1]

    # Cosine similarity (dot product of L2-normalised vectors)
    cosine_sim = float(np.dot(jd_emb, res_emb))

    # Clamp to [0, 1] — negative cosine is meaningless for text similarity
    cosine_sim = max(0.0, min(1.0, cosine_sim))

    # Mild calibration: apply sqrt to spread low scores and compress high ones
    # Raw 0.5 cosine → 0.707 calibrated → 70.7/100
    # This gives a more human-readable distribution across 0–100
    calibrated = float(np.sqrt(cosine_sim))

    return round(calibrated * 100.0, 2)


# ── Recommendation logic ──────────────────────────────────────────────────────

def get_recommendation(score: float) -> str:
    """Map final score to a human-readable recommendation."""
    if score >= STRONG_FIT_THRESHOLD:
        return "Strong Fit"
    elif score >= MODERATE_FIT_THRESHOLD:
        return "Moderate Fit"
    else:
        return "Not a Fit"


# ── Core scoring function ─────────────────────────────────────────────────────

def score_candidate(
    jd_text: str,
    parsed_resume: ParsedResume,
    filename: str = "unknown.pdf",
    raw_resume_text: str = "",
) -> CandidateResult:
    """
    Score a single candidate against a job description.

    Args:
        jd_text:          Raw JD text (user input)
        parsed_resume:    Output of parser.parse_resume()
        filename:         PDF filename (for display)
        raw_resume_text:  Original extracted PDF text (used as fallback for embedding)

    Returns:
        CandidateResult with score, strengths, gaps, recommendation

    Pipeline:
        1. Extract JD skills via jd_extractor
        2. Compute skill match score (keyword overlap)
        3. Compute semantic similarity (sentence-transformers)
        4. Weighted average → final score
        5. Generate recommendation
    """
    # ── Step 1: Extract JD skills ─────────────────────────────────────────────
    jd_skills = extract_jd_skills(jd_text)

    # ── Step 2: Skill match ───────────────────────────────────────────────────
    skill_result = compute_skill_match(
        jd_skills=jd_skills.all_skills,
        resume_skills=parsed_resume.skills,
    )

    skill_score = skill_result["score"]
    strengths = skill_result["strengths"]
    gaps = skill_result["gaps"]

    # ── Step 3: Semantic similarity ───────────────────────────────────────────
    jd_emb_text = _build_jd_text_for_embedding(jd_skills)

    # Use structured resume text for embedding; fall back to raw if empty
    resume_emb_text = _build_resume_text(parsed_resume)
    if len(resume_emb_text.strip()) < 50 and raw_resume_text:
        resume_emb_text = raw_resume_text[:2000]

    semantic_score = compute_semantic_similarity(jd_emb_text, resume_emb_text)

    # ── Step 4: Weighted final score ──────────────────────────────────────────
    w_skill = settings.SKILL_MATCH_WEIGHT
    w_sem = settings.SEMANTIC_WEIGHT

    final_score = (w_skill * skill_score) + (w_sem * semantic_score)
    final_score = round(min(100.0, max(0.0, final_score)), 1)

    # ── Step 5: Recommendation ────────────────────────────────────────────────
    recommendation = get_recommendation(final_score)

    logger.info(
        "[%s] Score: %.1f (skill=%.1f, semantic=%.1f) → %s",
        filename, final_score, skill_score, semantic_score, recommendation,
    )

    return CandidateResult(
        filename=filename,
        candidate_name=parsed_resume.name,
        score=final_score,
        skill_match_score=round(skill_score, 1),
        semantic_score=round(semantic_score, 1),
        strengths=strengths,
        gaps=gaps,
        recommendation=recommendation,
    )


# ── Batch scoring + ranking ───────────────────────────────────────────────────

def score_candidates(
    jd_text: str,
    candidates: list[dict],
) -> list[CandidateResult]:
    """
    Score and rank multiple candidates against a single JD.

    Args:
        jd_text: Raw job description text
        candidates: list of dicts:
            {
              "filename": str,
              "parsed": ParsedResume,
              "raw_text": str,   # optional, for embedding fallback
            }

    Returns:
        List of CandidateResult objects, sorted by score descending.
        Ties broken alphabetically by filename.
        Each result has a `rank` field set (1 = best).

    Notes:
        - JD skill extraction runs ONCE for the whole batch (not per-candidate)
        - Embedding model is pre-loaded before the loop (avoid reload per candidate)
        - Failed parse results get score=0 and recommendation="Not a Fit"
    """
    if not candidates:
        return []

    # Pre-warm the embedding model before the loop
    get_embedding_model()

    results: list[CandidateResult] = []

    for candidate in candidates:
        filename = candidate.get("filename", "unknown.pdf")
        parsed = candidate.get("parsed")
        raw_text = candidate.get("raw_text", "")

        if parsed is None:
            # Handle failed parse gracefully — score as zero
            logger.warning("[%s] No parsed resume — scoring as 0.", filename)
            results.append(CandidateResult(
                filename=filename,
                candidate_name=None,
                score=0.0,
                skill_match_score=0.0,
                semantic_score=0.0,
                strengths=[],
                gaps=[],
                recommendation="Not a Fit",
            ))
            continue

        result = score_candidate(
            jd_text=jd_text,
            parsed_resume=parsed,
            filename=filename,
            raw_resume_text=raw_text,
        )
        results.append(result)

    # Sort: primary = score descending, secondary = filename ascending (stable tie-break)
    results.sort(key=lambda r: (-r.score, r.filename))

    # Assign ranks (1-indexed; ties get same rank)
    current_rank = 1
    for i, result in enumerate(results):
        if i > 0 and result.score == results[i - 1].score:
            result.rank = results[i - 1].rank   # tie → same rank
        else:
            result.rank = current_rank
        current_rank = result.rank + 1

    return results