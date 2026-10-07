"""FEATURE C - admin: live upload, verification queue. STUB created by Foundation.

Contract (keep these signatures):
    analyze_upload(store, filename, data: bytes) -> {"doc": Document (proposed), "candidates": [Relation],
                                                      "pages": int, "warnings": [], "page_list": [Page]}
    commit_upload(store, analysis) -> doc_id
    pending_relations(store) -> list[Relation]
    verify_relation(store, relation_id, approve: bool, edits: dict | None) -> dict  (recomputes statuses + alerts)

The stub already works end to end with regex-only extraction.
"""

from __future__ import annotations

from pathlib import Path

from . import alerts
from .ingest import extract_metadata, parse_bytes
from .relations import extract_candidates
from .store import make_document


def analyze_upload(store, filename: str, data: bytes) -> dict:
    """Parse + regex metadata + relation candidates (nothing is saved yet)."""
    warnings: list[str] = []
    pages = parse_bytes(filename, data, Path(filename).stem)
    meta = extract_metadata(pages, filename)
    doc_id = store.unique_doc_id(meta.get("circular_no") or Path(filename).stem)
    doc = make_document(doc_id, meta)
    for p in pages:
        p.doc_id = doc_id
    ocr = [p.page_no for p in pages if p.needs_ocr]
    if ocr:
        warnings.append(f"Pages needing OCR (not available offline): {ocr}")
    candidates = extract_candidates(doc, pages, store.circular_map())
    return {"doc": doc, "candidates": candidates, "pages": len(pages), "warnings": warnings, "page_list": pages,
            "filename": filename, "data": data}


def commit_upload(store, analysis: dict) -> str:
    """Save the document and queue its (unverified) relation candidates."""
    doc = analysis["doc"]
    doc_id = store.add_document(doc, analysis["page_list"], analysis.get("data"), analysis.get("filename"))
    for rel in analysis["candidates"]:
        rel.source_doc_id = doc_id
    store.add_relations(analysis["candidates"])
    store.recompute()
    return doc_id


def pending_relations(store) -> list:
    return store.pending_relations()


def verify_relation(store, relation_id: str, approve: bool, edits: dict | None = None) -> dict:
    """Approve (verified=True) or reject a candidate, then recompute statuses and alerts."""
    changes = dict(edits or {})
    changes.update({"verified": True, "rejected": False} if approve else {"verified": False, "rejected": True})
    rel = store.update_relation(relation_id, **changes)
    status_changes = store.recompute()
    notes = alerts.on_new_relations(store, [rel]) if (rel is not None and approve) else []
    return {"relation": rel, "status_changes": status_changes, "notifications": notes}
