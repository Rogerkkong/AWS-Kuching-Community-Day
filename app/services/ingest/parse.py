"""PDF text extraction per page (PyMuPDF), with OCR fallback for pages without a text layer."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pymupdf

from app.services.ingest import ocr

MIN_TEXT_CHARS = 30
WATERMARK_RE = re.compile(r"^\s*SINTETIK\s*[-–]\s*CONTOH SAHAJA.*$", re.I | re.M)


@dataclass
class Page:
    number: int  # 1-based
    text: str
    ocr: bool = False


def clean_text(text: str) -> str:
    text = WATERMARK_RE.sub("", text)
    text = text.replace("­", "").replace("\r", "")
    lines = [ln.rstrip() for ln in text.split("\n")]
    return "\n".join(ln for ln in lines if ln.strip())


def parse_pdf(path: Path, log=None) -> list[Page]:
    pages: list[Page] = []
    with pymupdf.open(path) as doc:
        for page in doc:
            raw = page.get_text("text")
            text = clean_text(raw)
            used_ocr = False
            if len(text.strip()) < MIN_TEXT_CHARS:
                ocr_text = ocr.ocr_page(page)
                if ocr_text is not None:
                    text, used_ocr = clean_text(ocr_text), True
                elif log:
                    log("warning", f"Page {page.number + 1} has no text layer and OCR is unavailable "
                                   f"({ocr.unavailable_reason()}).")
            pages.append(Page(page.number + 1, text, used_ocr))
    return pages
