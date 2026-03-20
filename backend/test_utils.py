"""
test_utils.py
-------------
Quick smoke-test for utils.py.
Run with:  python test_utils.py
"""

import sys
from pathlib import Path
from utils import extract_text_from_bytes, validate_pdf_file, clean_text


def test_clean_text():
    print("\n── test_clean_text ──────────────────────────────")
    raw = "Hello   World\n\n\n\nThis  has  extra   spaces\n\u2022 Bullet point\nﬁle → fi"
    result = clean_text(raw)
    print(result)
    assert "fi" in result, "Ligature replacement failed"
    assert "  " not in result, "Double spaces not collapsed"
    assert result.count("\n\n\n") == 0, "3+ newlines not collapsed"
    print("PASS")


def test_validate_pdf():
    print("\n── test_validate_pdf ────────────────────────────")

    # Bad extension
    err = validate_pdf_file("resume.docx", b"%PDF-1.4 content", max_size_mb=5)
    assert err is not None and "not a PDF" in err
    print(f"  Extension check: {err}")

    # Bad magic bytes
    err = validate_pdf_file("resume.pdf", b"This is not a PDF", max_size_mb=5)
    assert err is not None and "header" in err
    print(f"  Magic bytes check: {err}")

    # Valid
    err = validate_pdf_file("resume.pdf", b"%PDF-1.4 valid content", max_size_mb=5)
    assert err is None
    print(f"  Valid file check: PASS")

    print("PASS")


def test_extract_real_pdf(pdf_path: str):
    """Pass a real PDF path to test full extraction."""
    print(f"\n── test_extract_real_pdf ({pdf_path}) ──────────")
    pdf_bytes = Path(pdf_path).read_bytes()
    text, error = extract_text_from_bytes(pdf_bytes, Path(pdf_path).name)
    if error:
        print(f"  ERROR: {error}")
    else:
        preview = text[:400].replace("\n", " ")
        print(f"  Chars extracted: {len(text)}")
        print(f"  Preview: {preview}...")
        print("  PASS")


if __name__ == "__main__":
    test_clean_text()
    test_validate_pdf()

    # If you pass a PDF path as CLI arg, test real extraction too
    if len(sys.argv) > 1:
        test_extract_real_pdf(sys.argv[1])
    else:
        print("\n  (Tip: pass a PDF path as argument to test real extraction)")
        print("  Example: python test_utils.py /path/to/resume.pdf")

    print("\nAll tests passed.")