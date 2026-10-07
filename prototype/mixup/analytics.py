"""FEATURE D - analytics dashboard data (FR-16). STUB created by Foundation.

Contract (keep this signature):
    summary(store, user) -> dict
Must only count / show queries and documents the user may see (access helpers).
"""

from __future__ import annotations

from . import logging as qlog


def summary(store, user) -> dict:
    """Stub: basic counts from the query log."""
    rows = qlog.read_logs(store)
    return {
        "total_queries": len(rows),
        "unanswered": sum(1 for r in rows if not r.get("answerable")),
    }
