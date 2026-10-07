"""FEATURE C - Smart Upload: extract metadata, detect supersession, commit.

STUB created by Foundation (works offline with simple rules). Feature C improves it.
"""

from __future__ import annotations

from pathlib import Path

from .context import AppContext
from .ingest import pages_to_text, read_document_bytes
from .models import DocMeta
from .textutil import detect_language, snippet
from .versions import detect_references, detect_supersession


def analyze(ctx: AppContext, filename: str, data: bytes) -> dict:
    """Read the file and propose metadata. Nothing is saved until commit()."""
    doc_id = Path(filename).stem.upper()
    pages = read_document_bytes(filename, data, doc_id)
    text = pages_to_text(pages)
    title = pages[0].heading.split(" > ")[0] if pages and pages[0].heading else Path(filename).stem
    supersedes = [{"doc_id": d, "evidence": e} for d, e in detect_supersession(text, ctx.docs)]
    references = [{"doc_id": d, "evidence": e} for d, e in detect_references(text, ctx.docs)]
    meta = DocMeta(
        doc_id=doc_id,
        title=title,
        doc_type="other",
        language=detect_language(text),
        supersedes=[s["doc_id"] for s in supersedes],
        summary=snippet(text, 200),
    )
    return {
        "meta": meta,
        "supersedes": supersedes,
        "references": references,
        "pages": len(pages),
        "preview": snippet(text, 600),
        "mode": "offline",
    }


def commit(ctx: AppContext, analysis: dict, data: bytes, filename: str) -> str:
    """Save the document and update library, map and answers. Returns the doc_id."""
    meta: DocMeta = analysis["meta"]
    stored = ctx.add_document(meta, data, filename)
    return stored.doc_id
