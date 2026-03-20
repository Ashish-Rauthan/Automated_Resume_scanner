"""
jd_extractor.py — UNIVERSAL VERSION (works for every department)
"""

import re
import logging
from typing import Optional
from dataclasses import dataclass, field

import spacy
from spacy.language import Language

logger = logging.getLogger(__name__)

_nlp: Optional[Language] = None

def _get_nlp() -> Language:
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_web_sm")
    return _nlp

# ── Master lists (tech + soft — spaCy catches everything else) ───────────────
TECH_SKILLS_MASTER = {
    "python", "java", "javascript", "c", "c++", "c#", "go", "rust", "php", "sql",
    "aws", "azure", "gcp", "docker", "kubernetes", "react", "node.js", "mongodb",
    "postgresql", "mysql", "rest", "api", "agile", "scrum", "devops",
}

SOFT_SKILLS_MASTER = {
    "communication", "teamwork", "problem solving", "leadership", "analytical",
    "adaptability", "creativity", "time management",
}

# ── Universal generic blocklist (never treat these as skills) ────────────────
GENERIC_BLOCKLIST = {
    "experience", "team", "work", "year", "knowledge", "ability", "skill",
    "requirement", "candidate", "role", "position", "job", "company",
    "opportunity", "benefit", "salary", "application", "employer", "employee",
    "responsibility", "understanding", "familiarity", "proficiency", "background",
    "environment", "solution", "project", "product", "system", "development",
    "implementation", "integration", "design", "testing", "deployment",
    "maintain", "build", "create", "advanced knowledge", "bachelor", "degree",
    "master", "phd", "qualifications", "responsibilities", "requirements",
    "key responsibilities", "basic qualifications", "preferred qualifications",
    "developer", "information technology", "verifying", "troubleshooting",
}

# ── Remove common section headers (works on any JD) ─────────────────────────
def _remove_section_headers(text: str) -> str:
    """Strip lines that look like headings (ALL CAPS, ends with :, short titles)."""
    lines = text.splitlines()
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Skip obvious headings
        if (stripped.isupper() or
            stripped.endswith(':') or
            len(stripped.split()) <= 5 and stripped[0].isupper()):
            continue
        cleaned.append(line)
    return "\n".join(cleaned)

# ── Dataclass (unchanged) ────────────────────────────────────────────────────
@dataclass
class JDSkills:
    raw_text: str = ""
    tech_skills: list = field(default_factory=list)
    soft_skills: list = field(default_factory=list)
    all_skills: list = field(default_factory=list)
    experience_requirements: list = field(default_factory=list)
    education_requirements: list = field(default_factory=list)
    keywords: list = field(default_factory=list)

# ── Helpers ──────────────────────────────────────────────────────────────────
def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())

def _deduplicate(items: list) -> list:
    seen = {}
    for item in items:
        key = _normalise(item)
        if key not in seen and key not in GENERIC_BLOCKLIST and len(key.split()) <= 4:
            seen[key] = item
    return sorted(seen.values(), key=str.lower)

# ── Extraction strategies ────────────────────────────────────────────────────
def _rule_based_extract(text: str) -> tuple:
    norm = _normalise(text)
    tech = [s.title() if " " in s else s for s in TECH_SKILLS_MASTER if re.search(r"\b" + re.escape(s) + r"\b", norm, re.IGNORECASE)]
    soft = [s.title() for s in SOFT_SKILLS_MASTER if re.search(r"\b" + re.escape(s) + r"\b", norm, re.IGNORECASE)]
    return tech, soft

def _spacy_extract(text: str) -> list:
    doc = _get_nlp()(text[:5000])
    candidates = []
    for chunk in doc.noun_chunks:
        if chunk.root.is_stop:
            continue
        txt = " ".join(t.text for t in chunk if not t.is_stop and not t.is_punct).strip()
        if 1 <= len(txt.split()) <= 4 and _normalise(txt) not in GENERIC_BLOCKLIST and not txt[0].isdigit():
            candidates.append(txt)
    return candidates

def _extract_experience_requirements(text: str) -> list:
    pattern = re.compile(r"(\d+)\+?\s*(?:to\s*\d+)?\s*years?\s*(?:of\s*)?(?:experience\s*(?:in|with)?\s*)?([a-zA-Z][a-zA-Z0-9\s\./\+#-]{1,40})", re.IGNORECASE)
    matches = pattern.findall(text)
    results = [f"{years}+ years of {skill.strip()}" for years, skill in matches if skill.strip()]
    return _deduplicate(results)

def _extract_education_requirements(text: str) -> list:
    pattern = re.compile(r"\b(bachelor['\s]*s?|master['\s]*s?|ph\.?d|b\.?tech|m\.?tech|b\.?e|m\.?e|b\.?sc|m\.?sc|mba)\b.*?(?:in|of)?\s*([a-zA-Z\s]{3,50})?", re.IGNORECASE)
    matches = pattern.findall(text)
    results = []
    for degree, field in matches:
        entry = degree.title()
        if field.strip():
            entry += f" in {field.strip().title()}"
        results.append(entry)
    return _deduplicate(results)[:5]

# ── Public API ───────────────────────────────────────────────────────────────
def extract_jd_skills(jd_text: str) -> JDSkills:
    if not jd_text or not jd_text.strip():
        return JDSkills()

    # Step 1: Remove section headers (this fixes ALL your garbage)
    clean_text = _remove_section_headers(jd_text)

    jd_result = JDSkills(raw_text=jd_text)

    tech, soft = _rule_based_extract(clean_text)
    spacy_cands = _spacy_extract(clean_text)

    all_tech = _deduplicate(tech + spacy_cands)
    all_soft = _deduplicate(soft)

    jd_result.tech_skills = all_tech
    jd_result.soft_skills = all_soft
    jd_result.all_skills = _deduplicate(all_tech + all_soft)

    jd_result.experience_requirements = _extract_experience_requirements(clean_text)
    jd_result.education_requirements = _extract_education_requirements(clean_text)
    jd_result.keywords = []  # you can re-add _extract_all_keywords if you use it

    logger.info(f"✅ Universal JD extraction: {len(jd_result.all_skills)} clean skills")
    return jd_result