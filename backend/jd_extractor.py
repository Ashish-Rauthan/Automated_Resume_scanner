"""
jd_extractor.py
---------------
Job Description keyword + skill extraction using spaCy + rule-based patterns.

No LLM used here — this must be:
  - Fast (< 100ms per JD)
  - Deterministic (same input -> same output always)
  - Free (no API calls)
  - Offline-capable

Architecture:
  extract_jd_skills()       -> main public function, returns JDSkills
  _normalise()              -> lowercase + strip for comparison
  _rule_based_extract()     -> regex + keyword-list matching
  _spacy_extract()          -> NLP noun-chunk + entity extraction
  _deduplicate()            -> case-insensitive dedup + sort
  _extract_experience_requirements() -> "3+ years Python" patterns
  _extract_education_requirements()  -> degree requirement patterns
"""

import re
import logging
from typing import Optional
from dataclasses import dataclass, field

import spacy
from spacy.language import Language

logger = logging.getLogger(__name__)

# ── Lazy spaCy model loader ───────────────────────────────────────────────────

_nlp: Optional[Language] = None


def _get_nlp() -> Language:
    global _nlp
    if _nlp is None:
        try:
            _nlp = spacy.load("en_core_web_sm")
            logger.info("spaCy model loaded: en_core_web_sm")
        except OSError:
            logger.error(
                "spaCy model not found. Run: python -m spacy download en_core_web_sm"
            )
            raise
    return _nlp


# ── Master skill lists ────────────────────────────────────────────────────────

TECH_SKILLS_MASTER = {
    # Languages
    "python", "java", "javascript", "typescript", "c", "c++", "c#", "go",
    "golang", "rust", "ruby", "php", "swift", "kotlin", "scala", "r",
    "matlab", "perl", "bash", "shell", "powershell", "lua", "haskell",
    "elixir", "erlang", "clojure", "groovy", "dart", "objective-c",

    # Web frontend
    "react", "react.js", "reactjs", "vue", "vue.js", "vuejs", "angular",
    "angularjs", "next.js", "nextjs", "nuxt", "svelte", "html", "css",
    "sass", "scss", "less", "tailwind", "tailwindcss", "bootstrap",
    "jquery", "webpack", "vite", "babel", "redux", "zustand", "graphql",
    "apollo", "axios", "jest", "cypress", "playwright", "storybook",

    # Web backend
    "fastapi", "django", "flask", "express", "expressjs", "node.js",
    "nodejs", "spring", "spring boot", "springboot", "rails", "laravel",
    "asp.net", "fastify", "hapi", "koa", "gin", "fiber", "echo",
    "nestjs", "strapi", "prisma", "sqlalchemy", "hibernate",

    # Databases
    "postgresql", "postgres", "mysql", "sqlite", "mariadb", "oracle",
    "mongodb", "mongoose", "redis", "elasticsearch", "cassandra",
    "dynamodb", "firestore", "supabase", "planetscale", "cockroachdb",
    "neo4j", "influxdb", "timescaledb", "clickhouse", "snowflake",
    "bigquery", "redshift",

    # Cloud & DevOps
    "aws", "amazon web services", "ec2", "s3", "lambda", "rds",
    "cloudfront", "route53", "iam", "ecs", "eks", "fargate",
    "azure", "gcp", "google cloud", "firebase",
    "docker", "kubernetes", "k8s", "helm", "terraform", "ansible",
    "puppet", "chef", "vagrant", "packer",
    "ci/cd", "cicd", "jenkins", "github actions", "gitlab ci",
    "circleci", "travis ci", "argocd", "spinnaker",
    "nginx", "apache", "caddy", "traefik",
    "linux", "ubuntu", "debian", "centos", "rhel",

    # Data & ML
    "machine learning", "deep learning", "artificial intelligence",
    "natural language processing", "nlp", "computer vision",
    "tensorflow", "pytorch", "keras", "scikit-learn", "sklearn",
    "pandas", "numpy", "scipy", "matplotlib", "seaborn", "plotly",
    "hugging face", "transformers", "langchain", "openai",
    "llm", "large language model", "rag", "vector database",
    "spark", "pyspark", "hadoop", "airflow", "dbt", "kafka",
    "mlflow", "kubeflow", "sagemaker", "vertex ai",
    "tableau", "power bi", "looker", "metabase",

    # APIs & protocols
    "rest", "restful", "grpc", "soap", "websocket",
    "oauth", "oauth2", "jwt", "openapi", "swagger",
    "rabbitmq", "celery", "sqs",

    # Testing
    "unit testing", "integration testing", "e2e testing",
    "tdd", "test driven development", "bdd",
    "pytest", "unittest", "mocha", "chai", "selenium", "postman",

    # Version control & tools
    "git", "github", "gitlab", "bitbucket",
    "jira", "confluence", "notion", "figma",

    # Architecture & patterns
    "microservices", "serverless", "event-driven",
    "domain driven design", "ddd", "cqrs", "event sourcing",
    "solid", "design patterns", "clean architecture",
    "system design", "distributed systems",

    # Methodologies
    "agile", "scrum", "kanban", "lean", "devops", "devsecops",

    # Security
    "cybersecurity", "penetration testing", "owasp",
    "encryption", "authentication", "authorization",

    # Mobile
    "android", "ios", "react native", "flutter", "xamarin",
}

SOFT_SKILLS_MASTER = {
    "communication", "leadership", "teamwork", "problem solving",
    "problem-solving", "critical thinking", "time management",
    "project management", "stakeholder management", "presentation",
    "negotiation", "collaboration", "mentoring", "coaching",
    "analytical", "attention to detail", "self-motivated",
    "adaptability", "creativity", "innovation",
}

EXPERIENCE_PATTERN = re.compile(
    r"(\d+)\+?\s*(?:to\s*\d+)?\s*years?\s*(?:of\s*)?(?:experience\s*(?:in|with)?\s*)?"
    r"([a-zA-Z][a-zA-Z0-9\s\./\+#-]{1,40})",
    re.IGNORECASE,
)

DEGREE_PATTERN = re.compile(
    r"\b(bachelor['\s]*s?|master['\s]*s?|ph\.?d|b\.?tech|m\.?tech|b\.?e|m\.?e|"
    r"b\.?sc|m\.?sc|mba|associate)\b.*?(?:in|of)?\s*([a-zA-Z\s]{3,50})?",
    re.IGNORECASE,
)

ACRONYM_FIXES = {
    "aws": "AWS", "gcp": "GCP", "api": "API", "apis": "APIs",
    "rest": "REST", "sql": "SQL", "html": "HTML", "css": "CSS",
    "ci/cd": "CI/CD", "cicd": "CI/CD", "llm": "LLM", "nlp": "NLP",
    "tdd": "TDD", "bdd": "BDD", "ddd": "DDD", "cqrs": "CQRS",
    "jwt": "JWT", "oauth": "OAuth", "oauth2": "OAuth2",
    "iot": "IoT", "k8s": "Kubernetes", "c++": "C++", "c#": "C#",
    "git": "Git", "ios": "iOS", "php": "PHP", "sass": "SASS",
    "scss": "SCSS", "go": "Go", "rust": "Rust", "r": "R",
    "sqs": "SQS", "ec2": "EC2", "s3": "S3", "rds": "RDS",
    "iam": "IAM", "ecs": "ECS", "eks": "EKS",
}

GENERIC_BLOCKLIST = {
    "experience", "team", "work", "year", "knowledge", "ability",
    "skill", "requirement", "candidate", "role", "position", "job",
    "company", "opportunity", "benefit", "salary", "resume",
    "application", "employer", "employee", "staff", "support",
    "service", "business", "management", "responsibility",
    "understanding", "familiarity", "proficiency", "background",
    "environment", "solution", "project", "product", "system",
    "development", "implementation", "integration", "design",
    "testing", "deployment", "maintain", "build", "create",
}


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


# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


def _deduplicate(items: list) -> list:
    seen: dict = {}
    for item in items:
        key = _normalise(item)
        if key not in seen:
            seen[key] = item
    return sorted(seen.values(), key=lambda x: x.lower())


def _clean_skill(skill: str) -> str:
    skill = skill.strip(" .,;:()[]{}'\"-*+/\\")
    skill = re.sub(r"\s+", " ", skill)
    return skill


# ── Extraction strategies ─────────────────────────────────────────────────────

def _rule_based_extract(text: str) -> tuple:
    normalised = _normalise(text)
    tech_found = []
    soft_found = []

    for skill in TECH_SKILLS_MASTER:
        pattern = r"\b" + re.escape(skill) + r"\b"
        if re.search(pattern, normalised, re.IGNORECASE):
            display = ACRONYM_FIXES.get(skill.lower(), skill)
            if display == skill:
                # Apply title case only to non-acronym multi-word skills
                display = skill.title() if " " in skill else skill
            tech_found.append(display)

    for skill in SOFT_SKILLS_MASTER:
        pattern = r"\b" + re.escape(skill) + r"\b"
        if re.search(pattern, normalised, re.IGNORECASE):
            soft_found.append(skill.title())

    return tech_found, soft_found


def _spacy_extract(text: str) -> list:
    nlp = _get_nlp()
    doc = nlp(text[:5000])
    candidates = []

    for ent in doc.ents:
        if ent.label_ in {"PRODUCT", "ORG", "WORK_OF_ART"}:
            cleaned = _clean_skill(ent.text)
            if 2 <= len(cleaned) <= 50 and not cleaned.isdigit():
                candidates.append(cleaned)

    for chunk in doc.noun_chunks:
        if chunk.root.is_stop:
            continue
        tokens = [t for t in chunk if not t.is_stop and not t.is_punct]
        if not tokens or len(tokens) > 4:
            continue
        text_chunk = " ".join(t.text for t in tokens)
        cleaned = _clean_skill(text_chunk)
        if 2 <= len(cleaned) <= 50 and not cleaned.isdigit():
            candidates.append(cleaned)

    return candidates


def _extract_experience_requirements(text: str) -> list:
    matches = EXPERIENCE_PATTERN.findall(text)
    results = []
    for years, skill in matches:
        skill = _clean_skill(skill)
        if skill and len(skill) > 2:
            results.append(f"{years}+ years of {skill.strip()}")
    return _deduplicate(results)


def _extract_education_requirements(text: str) -> list:
    matches = DEGREE_PATTERN.findall(text)
    results = []
    for degree, field_study in matches:
        degree = _clean_skill(degree)
        field_study = _clean_skill(field_study)
        if degree:
            entry = degree.title()
            if field_study and len(field_study) > 2:
                entry += f" in {field_study.title()}"
            results.append(entry)
    return _deduplicate(results)[:5]


def _extract_all_keywords(text: str) -> list:
    nlp = _get_nlp()
    doc = nlp(text[:5000])
    keywords = []
    for token in doc:
        if (
            not token.is_stop
            and not token.is_punct
            and not token.is_space
            and token.pos_ in {"NOUN", "PROPN", "ADJ"}
            and len(token.text) > 2
            and not token.text.isdigit()
        ):
            keywords.append(token.lemma_.lower())
    return _deduplicate(keywords)


# ── Public API ────────────────────────────────────────────────────────────────

def extract_jd_skills(jd_text: str) -> JDSkills:
    """
    Extract all skills, requirements, and keywords from a Job Description.

    Args:
        jd_text: Raw JD text (plain text)

    Returns:
        JDSkills dataclass with categorised skills and keywords.

    Pipeline:
        1. Rule-based matching against TECH_SKILLS_MASTER + SOFT_SKILLS_MASTER
        2. spaCy NLP noun-chunk + entity extraction for unlisted terms
        3. Filter + merge both sets
        4. Extract experience + education requirements
        5. Build broad keyword list for semantic matching
    """
    if not jd_text or not jd_text.strip():
        logger.warning("Empty JD text provided.")
        return JDSkills()

    jd_result = JDSkills(raw_text=jd_text)

    # Strategy 1: Rule-based master list
    tech_skills, soft_skills = _rule_based_extract(jd_text)

    # Strategy 2: spaCy NLP candidates
    spacy_candidates = _spacy_extract(jd_text)

    normalised_tech = {_normalise(s) for s in tech_skills}
    spacy_tech = []
    for candidate in spacy_candidates:
        norm = _normalise(candidate)
        if norm in normalised_tech:
            continue
        if norm in GENERIC_BLOCKLIST:
            continue
        if len(norm.split()) == 1 and len(norm) < 4:
            continue
        # Only include proper nouns or tech-looking terms
        if candidate[0].isupper() or re.search(r"\d", candidate):
            spacy_tech.append(candidate)

    all_tech = _deduplicate(tech_skills + spacy_tech)
    all_soft = _deduplicate(soft_skills)
    all_skills = _deduplicate(all_tech + all_soft)

    jd_result.tech_skills = all_tech
    jd_result.soft_skills = all_soft
    jd_result.all_skills = all_skills
    jd_result.experience_requirements = _extract_experience_requirements(jd_text)
    jd_result.education_requirements = _extract_education_requirements(jd_text)
    jd_result.keywords = _extract_all_keywords(jd_text)

    logger.info(
        "JD extraction: %d tech, %d soft, %d keywords",
        len(all_tech), len(all_soft), len(jd_result.keywords),
    )
    return jd_result


def get_jd_skill_set(jd_text: str) -> set:
    """
    Convenience wrapper — returns normalised set of all JD skills.
    Used by scorer.py for O(1) membership testing.
    """
    jd_skills = extract_jd_skills(jd_text)
    return {_normalise(s) for s in jd_skills.all_skills}