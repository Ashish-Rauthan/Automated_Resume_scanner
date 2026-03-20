"""
csv_exporter.py
---------------
CSV export utilities for screening results.

Generates a clean, spreadsheet-friendly CSV from ranked CandidateResult objects.
Uses Python's built-in csv module — no pandas dependency for this simple case.

Public API:
    results_to_csv_string()   -> returns CSV as a string (for testing)
    results_to_csv_bytes()    -> returns CSV as bytes (for StreamingResponse)
    build_csv_filename()      -> generates a timestamped filename
"""

import csv
import io
import json
import logging
from datetime import datetime, timezone
from typing import Union

from schemas import CandidateResult

logger = logging.getLogger(__name__)

# ── Column definitions ────────────────────────────────────────────────────────
# Order and headers exactly as they will appear in the exported file

CSV_COLUMNS = [
    ("rank",               "Rank"),
    ("candidate_name",     "Candidate Name"),
    ("filename",           "Resume File"),
    ("score",              "Overall Score (0-100)"),
    ("skill_match_score",  "Skill Match Score"),
    ("semantic_score",     "Semantic Score"),
    ("recommendation",     "Recommendation"),
    ("strengths",          "Matched Skills"),
    ("gaps",               "Missing Skills"),
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _format_list_field(value: Union[list, str, None]) -> str:
    """
    Convert a list field to a pipe-separated string for CSV.

    Handles three input types:
    - list  → "Python | FastAPI | Docker"
    - str   → may be JSON-encoded list (from DB) or plain string
    - None  → ""

    Using pipe (|) instead of comma prevents CSV column misalignment
    when the list is embedded in a comma-delimited file.
    """
    if value is None:
        return ""

    if isinstance(value, list):
        return " | ".join(str(item) for item in value if item)

    if isinstance(value, str):
        # Try to decode JSON-encoded list (from DB storage)
        try:
            decoded = json.loads(value)
            if isinstance(decoded, list):
                return " | ".join(str(item) for item in decoded if item)
        except (json.JSONDecodeError, TypeError):
            pass
        return value

    return str(value)


def _format_score(score: Union[float, int, None]) -> str:
    """Format score to 1 decimal place."""
    if score is None:
        return "N/A"
    try:
        return f"{float(score):.1f}"
    except (ValueError, TypeError):
        return str(score)


def _format_name(name: Union[str, None], filename: str) -> str:
    """Use filename stem as fallback when candidate name is not detected."""
    if name and name.strip():
        return name.strip()
    # Strip extension and underscores/dashes for readability
    stem = filename.replace(".pdf", "").replace("_", " ").replace("-", " ")
    return stem.title()


# ── Core export function ──────────────────────────────────────────────────────

def results_to_csv_string(
    results: list[CandidateResult],
    session_id: str = "",
    job_description_preview: str = "",
) -> str:
    """
    Convert a list of CandidateResult objects to a CSV string.

    Args:
        results:                    Ranked list from score_candidates()
        session_id:                 Optional session ID for the header
        job_description_preview:    First 100 chars of JD (added as metadata row)

    Returns:
        UTF-8 CSV string with:
        - Metadata header (2 rows): export timestamp + session info
        - Column header row
        - One data row per candidate
        - Summary footer row

    Design notes:
        - BOM (\\ufeff) prepended for Excel compatibility
        - All list fields pipe-separated to avoid column misalignment
        - Empty string for missing values (never "None" or "null")
    """
    output = io.StringIO()

    # Use excel dialect but with utf-8-sig for Excel BOM handling
    writer = csv.writer(output, dialect="excel", quoting=csv.QUOTE_ALL)

    # ── Metadata rows ─────────────────────────────────────────────────────────
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    writer.writerow(["AI Resume Screening Report"])
    writer.writerow(["Exported at", now])

    if session_id:
        writer.writerow(["Session ID", session_id])

    if job_description_preview:
        preview = job_description_preview[:100].replace("\n", " ").strip()
        writer.writerow(["Job Description", preview + ("..." if len(job_description_preview) > 100 else "")])

    writer.writerow([])  # blank separator row

    # ── Column headers ────────────────────────────────────────────────────────
    headers = [col[1] for col in CSV_COLUMNS]
    writer.writerow(headers)

    # ── Data rows ─────────────────────────────────────────────────────────────
    if not results:
        writer.writerow(["No results to display"] + [""] * (len(headers) - 1))
    else:
        for result in results:
            row = []
            for field_name, _ in CSV_COLUMNS:
                if field_name == "rank":
                    row.append(result.rank if result.rank is not None else "")

                elif field_name == "candidate_name":
                    row.append(_format_name(result.candidate_name, result.filename))

                elif field_name == "filename":
                    row.append(result.filename)

                elif field_name == "score":
                    row.append(_format_score(result.score))

                elif field_name == "skill_match_score":
                    row.append(_format_score(result.skill_match_score))

                elif field_name == "semantic_score":
                    row.append(_format_score(result.semantic_score))

                elif field_name == "recommendation":
                    row.append(result.recommendation or "")

                elif field_name == "strengths":
                    row.append(_format_list_field(result.strengths))

                elif field_name == "gaps":
                    row.append(_format_list_field(result.gaps))

                else:
                    row.append("")

            writer.writerow(row)

    # ── Summary footer ────────────────────────────────────────────────────────
    writer.writerow([])
    if results:
        strong   = sum(1 for r in results if r.recommendation == "Strong Fit")
        moderate = sum(1 for r in results if r.recommendation == "Moderate Fit")
        not_fit  = sum(1 for r in results if r.recommendation == "Not a Fit")
        avg_score = sum(r.score for r in results) / len(results)

        writer.writerow(["Summary"])
        writer.writerow(["Total Candidates", len(results)])
        writer.writerow(["Strong Fit",        strong])
        writer.writerow(["Moderate Fit",       moderate])
        writer.writerow(["Not a Fit",          not_fit])
        writer.writerow(["Average Score",      _format_score(avg_score)])

        if results:
            top = results[0]
            writer.writerow([
                "Top Candidate",
                _format_name(top.candidate_name, top.filename),
                f"Score: {_format_score(top.score)}",
                top.recommendation,
            ])

    return output.getvalue()


def results_to_csv_bytes(
    results: list[CandidateResult],
    session_id: str = "",
    job_description_preview: str = "",
) -> bytes:
    """
    Returns CSV as UTF-8 bytes with BOM for Excel compatibility.
    Used directly in FastAPI StreamingResponse.
    """
    csv_string = results_to_csv_string(results, session_id, job_description_preview)
    # \\ufeff = UTF-8 BOM — makes Excel open the file with correct encoding
    return ("\ufeff" + csv_string).encode("utf-8")


def build_csv_filename(session_id: str = "") -> str:
    """
    Build a timestamped CSV filename.
    Example: resume_screening_2024-01-15_143022.csv
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    if session_id:
        short_id = session_id[:8]
        return f"resume_screening_{timestamp}_{short_id}.csv"
    return f"resume_screening_{timestamp}.csv"