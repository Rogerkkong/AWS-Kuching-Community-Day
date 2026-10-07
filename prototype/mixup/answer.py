"""FEATURE A - Ask MixUp: bilingual Q&A grounded in the documents.

STUB created by Foundation. Feature A replaces the body of ask() but must keep
the signature and return an Answer (see mixup/models.py).
"""

from __future__ import annotations

from .context import AppContext
from .models import Answer, Citation
from .textutil import detect_language, snippet

NOT_FOUND = {
    "ms": "Maaf, jawapan tidak ditemui dalam dokumen yang ada.",
    "en": "Sorry, the answer is not in the available documents.",
    "mixed": "Sorry, the answer is not in the available documents. / Maaf, jawapan tidak ditemui dalam dokumen.",
}


def ask(ctx: AppContext, question: str, history: list | None = None) -> Answer:
    """Answer a question from the documents (stub: shows the top passages)."""
    lang = detect_language(question)
    hits = ctx.index.search(question, k=5)
    if not hits:
        return Answer(text=NOT_FOUND[lang], language=lang, confidence="none", mode="offline")
    citations = []
    for i, hit in enumerate(hits[:3], start=1):
        citations.append(
            Citation(
                label=f"S{i}",
                doc_id=hit.doc.doc_id,
                title=hit.doc.title,
                number=hit.doc.number,
                page_no=hit.chunk.page_no,
                heading=hit.chunk.heading,
                snippet=snippet(hit.chunk.text),
                status=hit.doc.status,
            )
        )
    lines = [f"[{c.label}] {c.snippet}" for c in citations]
    return Answer(
        text="Most relevant passages (stub):\n\n" + "\n\n".join(lines),
        citations=citations,
        language=lang,
        confidence="low",
        mode="offline",
        hits=hits,
    )
