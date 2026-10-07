"""Query log (audit trail, FR-18) and feedback (FR-17).

Append-only JSONL files in runtime/ (cleared by "Reset demo"):
    query_log.jsonl   one row per ask() call (navigator and baseline)
    feedback.jsonl    thumbs up/down and "report wrong status", keyed by query_log_id

Imported as `from mixup import logging as qlog` (never shadow the standard library).

    log_id = log_query(store, user, {"query": ..., "answerable": ..., ...})
    rows = read_logs(store)                        # raw rows: callers filter by access!
    rows = read_logs(store, with_feedback=True)    # each row gets "feedback": [...]
    add_feedback(store, log_id, rating=1, comment="")             # thumbs up (+1) / down (-1)
    add_feedback(store, log_id, 0, "SPP 1/2023 is cancelled", kind="wrong_status")

Row fields written by ask.ask(): query_log_id, created_at, user_id, role, jurisdiction,
clearance_level, query, language, mode, include_historical, historical, rewritten, wants_history,
retrieved (chunk ids), retrieved_docs, cited, cited_docs, excluded (doc ids), answerable, answer,
top_score, confidence, primary_status, primary_doc, cluster, topic, jurisdiction_conflict,
latency_ms, llm_mode, warnings.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

QUERY_LOG = "query_log.jsonl"
FEEDBACK_LOG = "feedback.jsonl"
FEEDBACK_KINDS = ("thumbs", "wrong_status", "comment")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_log_id() -> str:
    """A fresh query_log_id ('Q-' + 10 hex characters)."""
    return "Q-" + uuid.uuid4().hex[:10]


def log_query(store, user, record: dict) -> str:
    """Append one query record; returns its query_log_id."""
    log_id = new_log_id()
    row = {
        "query_log_id": log_id,
        "created_at": _now(),
        "user_id": getattr(user, "user_id", None),
        "role": getattr(user, "role", None),
        "jurisdiction": getattr(user, "jurisdiction", None),
        "clearance_level": getattr(user, "clearance_level", 0),
    }
    row.update({k: v for k, v in (record or {}).items() if k != "query_log_id"})
    store.append_jsonl(QUERY_LOG, row)
    return log_id


def read_feedback(store) -> list[dict]:
    """All feedback rows (oldest first)."""
    return store.read_jsonl(FEEDBACK_LOG)


def read_logs(store, with_feedback: bool = False) -> list[dict]:
    """All query log rows (oldest first). with_feedback=True attaches row["feedback"] = [...]."""
    rows = store.read_jsonl(QUERY_LOG)
    if with_feedback:
        by_id: dict[str, list[dict]] = {}
        for fb in read_feedback(store):
            by_id.setdefault(fb.get("query_log_id"), []).append(fb)
        for row in rows:
            row["feedback"] = by_id.get(row.get("query_log_id"), [])
    return rows


def get_log(store, query_log_id: str) -> dict | None:
    """One query log row (with its feedback), or None."""
    return next((r for r in read_logs(store, with_feedback=True) if r.get("query_log_id") == query_log_id), None)


def add_feedback(store, query_log_id: str, rating: int, comment: str = "", kind: str = "thumbs", user_id: str | None = None) -> dict:
    """Thumbs up (+1) / down (-1), or kind="wrong_status" for 'report wrong status' (FR-17)."""
    row = {
        "query_log_id": query_log_id,
        "rating": int(rating),
        "comment": (comment or "")[:1000],
        "kind": kind if kind in FEEDBACK_KINDS else "comment",
        "user_id": user_id,
        "created_at": _now(),
    }
    store.append_jsonl(FEEDBACK_LOG, row)
    return row


def feedback(store, query_log_id: str, rating: int, comment: str = "", **kwargs) -> dict:
    """Alias of add_feedback (the name used in the task spec)."""
    return add_feedback(store, query_log_id, rating, comment, **kwargs)
