import re
import unicodedata
from typing import Any, Dict, List


def _clean_page_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).replace("\x00", "")
    text = text.replace("\u00ad", "")
    return re.sub(r"\s+", " ", text).strip()


def _extract_with_pymupdf(filepath: str) -> List[Dict[str, Any]]:
    import fitz

    pages: List[Dict[str, Any]] = []
    with fitz.open(filepath) as document:
        for page_index, page in enumerate(document):
            text = _clean_page_text(page.get_text("text", sort=True))
            if text:
                pages.append({"page_number": page_index + 1, "text": text})
    return pages


def _extract_with_pypdf(filepath: str) -> List[Dict[str, Any]]:
    from pypdf import PdfReader

    reader = PdfReader(filepath)
    pages: List[Dict[str, Any]] = []

    for page_index, page in enumerate(reader.pages):
        text = _clean_page_text(page.extract_text() or "")
        if text:
            pages.append({"page_number": page_index + 1, "text": text})

    return pages


def extract_text_from_pdf(filepath: str) -> List[Dict[str, Any]]:
    """
    Extract text page by page. PyMuPDF is preferred because it usually preserves
    page ordering better; pypdf remains a local fallback for existing installs.
    """
    try:
        return _extract_with_pymupdf(filepath)
    except ImportError:
        return _extract_with_pypdf(filepath)
