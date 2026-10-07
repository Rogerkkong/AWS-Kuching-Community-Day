"""FEATURE B - "What changed?" between an old and a new version of a document.

STUB created by Foundation. Feature B replaces the body of what_changed().
"""

from __future__ import annotations

from .context import AppContext


def what_changed(ctx: AppContext, old_id: str, new_id: str) -> dict:
    """Return {"summary", "changes": [{"topic","before","after"}], "effective_date", "mode"}."""
    old = ctx.get_doc(old_id)
    new = ctx.get_doc(new_id)
    if old is None or new is None:
        return {"summary": "Document not found.", "changes": [], "effective_date": "", "mode": "offline"}
    return {
        "summary": f"{new.short_label} replaces {old.short_label}. (Stub: detailed comparison not implemented yet.)",
        "changes": [],
        "effective_date": new.date_issued,
        "mode": "offline",
    }
