"""Tesseract OCR (msa+eng) for scanned pages. Publisher only; degrades gracefully when not installed."""
from __future__ import annotations

import io
import os
import shutil
from functools import lru_cache
from pathlib import Path

import pymupdf

WINDOWS_DEFAULT = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")


@lru_cache(maxsize=1)
def _tesseract() -> str | None:
    found = os.environ.get("TESSERACT_CMD") or shutil.which("tesseract")
    if found:
        return found
    if WINDOWS_DEFAULT.exists():
        return str(WINDOWS_DEFAULT)
    return None


def unavailable_reason() -> str:
    try:
        import pytesseract  # noqa: F401
    except ImportError:
        return "pytesseract not installed"
    if _tesseract() is None:
        return "Tesseract binary not found (install Tesseract 5 with Malay + English data)"
    return "unknown"


def ocr_page(page: pymupdf.Page, dpi: int = 300) -> str | None:
    cmd = _tesseract()
    if cmd is None:
        return None
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        return None
    pytesseract.pytesseract.tesseract_cmd = cmd
    pix = page.get_pixmap(dpi=dpi)
    image = Image.open(io.BytesIO(pix.tobytes("png")))
    langs = pytesseract.get_languages(config="")
    lang = "+".join(l for l in ("msa", "eng") if l in langs) or "eng"
    return pytesseract.image_to_string(image, lang=lang)
