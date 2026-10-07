"""FEATURE B - "what changed" between two versions. STUB created by Foundation.

Contract (keep this signature):
    what_changed(store, user, old_id, new_id) -> {
        "aligned": [{"clause_old", "clause_new", "type", "old_text", "new_text", "diff_html"}],
        "summary_ms", "summary_en", "effective_date", "who_is_affected", "mode"}

type is ADDED | REMOVED | CHANGED | SAME. Cache in runtime/change_cache.json.
Access: both documents must be visible to the user (access.get_doc), else empty.
"""

from __future__ import annotations

from . import access


def what_changed(store, user, old_id: str, new_id: str) -> dict:
    """Stub: returns an empty comparison (Feature B implements clause alignment + summaries)."""
    old, new = access.get_doc(store, user, old_id), access.get_doc(store, user, new_id)
    empty = {
        "aligned": [],
        "summary_ms": "",
        "summary_en": "",
        "effective_date": None,
        "who_is_affected": "Tidak dinyatakan / Not stated",
        "mode": "offline",
    }
    if old is None or new is None:
        return empty
    empty["effective_date"] = new.effective_date
    return empty
