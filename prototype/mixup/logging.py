"""FEATURE D - query log (audit trail, FR-18). STUB created by Foundation; Feature D may extend.

Append-only JSONL at runtime/query_log.jsonl. Imported as `from mixup import logging as qlog`
(never shadow the standard library inside other modules).

    log_id = log_query(store, user, {"query": ..., "answerable": ..., ...})
    rows = read_logs(store)                       # raw rows (callers filter by access!)
    add_feedback(store, log_id, rating=1, comment="")
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

QUERY_LOG = "query_log.jsonl"
FEEDBACK_LOG = "feedback.jsonl"


def log_query(store, user, record: dict) -> str:
    """Append one query record; returns its query_log_id."""
    log_id = "Q-" + uuid.uuid4().hex[:10]
    row = {
        "query_log_id": log_id,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "user_id": getattr(user, "user_id", None),
        "role": getattr(user, "role", None),
        "jurisdiction": getattr(user, "jurisdiction", None),
        "clearance_level": getattr(user, "clearance_level", 0),
    }
    row.update(record or {})
    store.append_jsonl(QUERY_LOG, row)
    return log_id


def read_logs(store) -> list[dict]:
    """All query log rows (oldest first)."""
    return store.read_jsonl(QUERY_LOG)


def add_feedback(store, query_log_id: str, rating: int, comment: str = "") -> None:
    """Thumbs up (+1) / down (-1) or 'report wrong status' (FR-17)."""
    store.append_jsonl(
        FEEDBACK_LOG,
        {
            "query_log_id": query_log_id,
            "rating": rating,
            "comment": comment,
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        },
    )
