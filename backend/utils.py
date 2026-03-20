"""
utils.py
--------
PDF text extraction utilities using pdfplumber.

Design decisions:
- extract_text_from_pdf()  → single file, returns clean string
- extract_text_from_bytes() → works with FastAPI UploadFile bytes (no temp files)
- clean_text()             → normalises whitespace, removes junk characters
- All functions return (text, error) tuples — never raise, always report
"""

import io
import re
import logging
from typing import Tuple, Optional

import pdfplumber

logger = logging.getLogger(__name__)


# ── Text cleaning ─────────────────────────────────────────────────────────────

def clean_text(raw: str) -> str:
    """
    Normalise extracted PDF text.

    Steps:
    1. Replace common PDF ligatures (ﬁ → fi, etc.)
    2. Strip non-printable / control characters
    3. Collapse multiple spaces into one
    4. Collapse 3+ consecutive newlines into two (preserve paragraphs)
    5. Strip leading/trailing whitespace per line
    6. Final strip of the whole string
    """
    if not raw:
        return ""

    # 1. Fix common PDF ligatures
    ligature_map = {
        "\ufb01": "fi",   # ﬁ
        "\ufb02": "fl",   # ﬂ
        "\ufb00": "ff",   # ﬀ
        "\ufb03": "ffi",  # ﬃ
        "\ufb04": "ffl",  # ﬄ
        "\u2022": "-",    # bullet •
        "\u2013": "-",    # en-dash
        "\u2014": "-",    # em-dash
        "\u2019": "'",    # right single quotation
        "\u201c": '"',    # left double quotation
        "\u201d": '"',    # right double quotation
    }
    for ligature, replacement in ligature_map.items():
        raw = raw.replace(ligature, replacement)

    # 2. Remove non-printable / control characters (keep newlines + tabs)
    raw = re.sub(r"[^\x09\x0A\x0D\x20-\x7E\u00A0-\uFFFF]", " ", raw)

    # 3. Strip per-line and collapse internal spaces
    lines = []
    for line in raw.splitlines():
        line = line.strip()
        line = re.sub(r" {2,}", " ", line)
        lines.append(line)

    # 4. Collapse 3+ consecutive blank lines into 2
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# ── Core extraction ───────────────────────────────────────────────────────────

def extract_text_from_bytes(
    file_bytes: bytes,
    filename: str = "unknown.pdf",
) -> Tuple[str, Optional[str]]:
    """
    Extract and clean text from PDF bytes.

    Args:
        file_bytes: Raw PDF bytes from UploadFile.read()
        filename:   Original filename (for logging only)

    Returns:
        (text, error_message)
        - On success: (non-empty string, None)
        - On failure: ("", descriptive error string)

    Strategy:
        1. Try pdfplumber page-by-page text extraction
        2. For each page, also attempt table extraction and append as plain text
        3. If a page yields nothing, log a warning (common for scanned pages)
        4. If the entire document yields nothing, return an error
    """
    if not file_bytes:
        return "", f"[{filename}] Empty file — no bytes received."

    try:
        pdf_stream = io.BytesIO(file_bytes)
        full_text_parts: list[str] = []

        with pdfplumber.open(pdf_stream) as pdf:
            total_pages = len(pdf.pages)

            if total_pages == 0:
                return "", f"[{filename}] PDF has 0 pages."

            for page_num, page in enumerate(pdf.pages, start=1):
                page_text = ""

                # -- Primary: extract text layer --
                try:
                    raw = page.extract_text(
                        x_tolerance=3,       # horizontal tolerance for word grouping
                        y_tolerance=3,       # vertical tolerance for line grouping
                        layout=True,         # preserve spatial layout
                        x_density=7.25,      # characters per point (affects column detection)
                        y_density=13,        # lines per point
                    )
                    if raw:
                        page_text += raw
                except Exception as page_err:
                    logger.warning(
                        "[%s] Page %d text extraction failed: %s",
                        filename, page_num, page_err,
                    )

                # -- Secondary: extract any tables and append as TSV-style text --
                try:
                    tables = page.extract_tables()
                    for table in tables:
                        for row in table:
                            # Filter None cells, join with tab
                            clean_row = "\t".join(
                                cell.strip() if cell else ""
                                for cell in row
                            )
                            if clean_row.strip():
                                page_text += "\n" + clean_row
                except Exception as table_err:
                    logger.debug(
                        "[%s] Page %d table extraction failed: %s",
                        filename, page_num, table_err,
                    )

                if page_text.strip():
                    full_text_parts.append(page_text)
                else:
                    logger.warning(
                        "[%s] Page %d yielded no text (possibly scanned image).",
                        filename, page_num,
                    )

        if not full_text_parts:
            return (
                "",
                f"[{filename}] No text could be extracted from any of the "
                f"{total_pages} page(s). The PDF may contain only scanned "
                "images. Please use a text-based PDF.",
            )

        raw_combined = "\n\n".join(full_text_parts)
        cleaned = clean_text(raw_combined)

        if len(cleaned) < 50:
            return (
                "",
                f"[{filename}] Extracted text is too short ({len(cleaned)} chars). "
                "The PDF may be scanned or corrupted.",
            )

        logger.info(
            "[%s] Extracted %d chars from %d/%d pages.",
            filename, len(cleaned), len(full_text_parts), total_pages,
        )
        return cleaned, None

    except pdfplumber.exceptions.PDFSyntaxError as e:
        return "", f"[{filename}] Invalid or corrupted PDF: {e}"
    except Exception as e:
        logger.exception("[%s] Unexpected extraction error", filename)
        return "", f"[{filename}] Extraction failed: {str(e)}"


# ── Batch helper ──────────────────────────────────────────────────────────────

def extract_texts_from_uploads(
    files: list[tuple[str, bytes]],
) -> list[dict]:
    """
    Process multiple PDF uploads in one call.

    Args:
        files: list of (filename, bytes) tuples

    Returns:
        list of dicts:
        {
            "filename": str,
            "text": str,           # empty string on failure
            "success": bool,
            "error": str | None,
            "char_count": int,
        }
    """
    results = []

    for filename, file_bytes in files:
        text, error = extract_text_from_bytes(file_bytes, filename)
        results.append({
            "filename": filename,
            "text": text,
            "success": error is None,
            "error": error,
            "char_count": len(text),
        })

    return results


# ── Validation helper ─────────────────────────────────────────────────────────

def validate_pdf_file(
    filename: str,
    file_bytes: bytes,
    max_size_mb: float = 5.0,
) -> Optional[str]:
    """
    Validate a PDF upload before processing.

    Returns:
        None  → file is valid
        str   → human-readable error message
    """
    # 1. Extension check
    if not filename.lower().endswith(".pdf"):
        return f"'{filename}' is not a PDF file. Only .pdf files are accepted."

    # 2. Size check
    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > max_size_mb:
        return (
            f"'{filename}' is {size_mb:.1f} MB, which exceeds the "
            f"{max_size_mb} MB limit."
        )

    # 3. Magic bytes check (PDF files start with %PDF)
    if not file_bytes.startswith(b"%PDF"):
        return (
            f"'{filename}' does not appear to be a valid PDF "
            "(missing PDF header)."
        )

    return None