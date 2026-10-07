"""FEATURE D - analytics dashboard data (FR-16), from the append-only query log.

    data = summary(store, user)

Who sees what (enforced here, never in the UI):
  OFFICER        only their own questions
  POLICY_OWNER   every question asked at or below their own clearance
  ADMIN          same rule (an admin with clearance 2 sees everything)
In both cases a log row is also hidden if it touches any document (retrieved, cited, excluded)
the viewer may not open (access.can_see), so restricted content never shows up in analytics.

Only navigator questions count towards the dashboard; "compare with a typical chatbot"
(baseline) runs are counted separately in baseline_queries.
"""

from __future__ import annotations

import re
from collections import Counter

import numpy as np

from . import access
from . import logging as qlog

PRIVILEGED_ROLES = ("POLICY_OWNER", "ADMIN")
LOW_CONFIDENCE = "LOW"
TOP_N = 10


def scope_of(user) -> str:
    """'all' for policy owners and admins, 'own' for officers."""
    return "all" if getattr(user, "role", "OFFICER") in PRIVILEGED_ROLES else "own"


def _row_doc_ids(row: dict) -> set[str]:
    """Every document a log row touches (retrieved chunks, cited, excluded, primary)."""
    ids = set(row.get("retrieved_docs") or []) | set(row.get("cited_docs") or []) | set(row.get("excluded") or [])
    ids |= {str(c).split("#", 1)[0] for c in row.get("retrieved") or []}
    ids |= {c.get("doc_id") for c in row.get("cited") or [] if isinstance(c, dict)}
    if row.get("primary_doc"):
        ids.add(row["primary_doc"])
    return {i for i in ids if i}


def row_visible(store, user, row: dict) -> bool:
    """May this viewer see this log row? (scope rule + document clearance rule)."""
    if row.get("user_id") != getattr(user, "user_id", None):
        if scope_of(user) != "all":
            return False
        if int(row.get("clearance_level") or 0) > access.clearance(user):
            return False
    visible = access.visible_doc_ids(store, user)
    return _row_doc_ids(row) <= visible


def visible_rows(store, user, mode: str | None = "navigator") -> tuple[list[dict], int]:
    """(log rows the viewer may see, number hidden for clearance). mode=None keeps every mode."""
    rows, hidden = [], 0
    for row in qlog.read_logs(store, with_feedback=True):
        if mode and (row.get("mode") or "navigator") != mode:
            continue
        if row_visible(store, user, row):
            rows.append(row)
        elif scope_of(user) == "all" or row.get("user_id") == getattr(user, "user_id", None):
            hidden += 1
    return rows, hidden


def normalize_question(text: str) -> str:
    """Lower case, single spaces, no trailing punctuation (for 'top questions')."""
    return re.sub(r"\s+", " ", (text or "").strip().lower()).rstrip("?.!")


def _cluster(store, row: dict) -> str:
    if row.get("cluster"):
        return row["cluster"]
    for doc_id in row.get("retrieved_docs") or []:
        doc = store.docs.get(doc_id)
        if doc and doc.cluster:
            return doc.cluster
    return "unknown"


def _brief(row: dict, show_user: bool) -> dict:
    item = {
        "question": row.get("query", ""),
        "created_at": row.get("created_at", ""),
        "language": row.get("language", ""),
        "confidence": row.get("confidence", ""),
        "cluster": row.get("cluster") or "",
        "query_log_id": row.get("query_log_id", ""),
    }
    if show_user:
        item["user_id"] = row.get("user_id", "")
    return item


def _rate(part: int, whole: int) -> float:
    return round(part / whole, 3) if whole else 0.0


def summary(store, user) -> dict:
    """Dashboard data for this viewer. See the module docstring for the access rules."""
    rows, hidden = visible_rows(store, user)
    all_modes, _ = visible_rows(store, user, mode=None)
    show_user = scope_of(user) == "all"
    total = len(rows)
    answered = [r for r in rows if r.get("answerable")]
    unanswered = [r for r in rows if not r.get("answerable")]
    low_conf = [r for r in answered if (r.get("confidence") or "").upper() == LOW_CONFIDENCE]

    clusters: dict[str, dict] = {}
    for r in rows:
        c = clusters.setdefault(_cluster(store, r), {"total": 0, "unanswered": 0, "low_confidence": 0})
        c["total"] += 1
        c["unanswered"] += 0 if r.get("answerable") else 1
        c["low_confidence"] += 1 if r in low_conf else 0
    by_cluster = [
        {"cluster": k, **v, "unanswered_rate": _rate(v["unanswered"], v["total"])}
        for k, v in sorted(clusters.items(), key=lambda kv: (-kv[1]["total"], kv[0]))
    ]

    questions: Counter = Counter()
    first_text: dict[str, str] = {}
    answered_q: Counter = Counter()
    for r in rows:
        key = normalize_question(r.get("query", ""))
        if not key:
            continue
        questions[key] += 1
        first_text.setdefault(key, r.get("query", "").strip())
        answered_q[key] += 1 if r.get("answerable") else 0
    top_questions = [
        {"question": first_text[k], "count": n, "answered": answered_q[k]} for k, n in questions.most_common(TOP_N)
    ]
    topics = Counter((r.get("topic") or _cluster(store, r)) for r in rows)
    top_topics = [{"topic": t, "count": n} for t, n in topics.most_common(TOP_N)]

    excluded: Counter = Counter()
    for r in rows:
        excluded.update(set(r.get("excluded") or []))
    most_excluded = []
    for doc_id, n in excluded.most_common(TOP_N):
        doc = access.get_doc(store, user, doc_id)
        if doc is None:  # defence in depth: never name a document the viewer may not open
            continue
        most_excluded.append(
            {"doc_id": doc_id, "circular_no": doc.label, "title": doc.title, "status": doc.status,
             "status_reason": doc.status_reason, "count": n}
        )

    up = down = wrong = 0
    reports, comments = [], []
    for r in all_modes:
        for fb in r.get("feedback") or []:
            kind = fb.get("kind", "thumbs")
            if kind == "wrong_status":
                wrong += 1
                reports.append({"question": r.get("query", ""), "comment": fb.get("comment", ""),
                                "created_at": fb.get("created_at", ""), "cited_docs": r.get("cited_docs") or []})
            elif int(fb.get("rating") or 0) > 0:
                up += 1
            elif int(fb.get("rating") or 0) < 0:
                down += 1
            if kind != "wrong_status" and fb.get("comment"):
                comments.append({"question": r.get("query", ""), "comment": fb["comment"],
                                 "rating": int(fb.get("rating") or 0)})

    latencies = [float(r.get("latency_ms") or 0) for r in rows]
    newest = lambda items: sorted(items, key=lambda r: r.get("created_at", ""), reverse=True)  # noqa: E731
    return {
        "scope": scope_of(user),
        "viewer": getattr(user, "user_id", None),
        "total_queries": total,
        "answered": len(answered),
        "unanswered": len(unanswered),
        "unanswered_rate": _rate(len(unanswered), total),
        "low_confidence": len(low_conf),
        "low_confidence_rate": _rate(len(low_conf), len(answered)),
        "excluded_answers": sum(1 for r in rows if r.get("excluded")),
        "jurisdiction_conflicts": sum(1 for r in rows if r.get("jurisdiction_conflict")),
        "baseline_queries": sum(1 for r in all_modes if r.get("mode") == "baseline"),
        "hidden_rows": hidden,
        "latency_p50_ms": round(float(np.percentile(latencies, 50)), 1) if latencies else 0.0,
        "latency_p95_ms": round(float(np.percentile(latencies, 95)), 1) if latencies else 0.0,
        "by_language": dict(Counter(r.get("language") or "?" for r in rows)),
        "by_confidence": dict(Counter((r.get("confidence") or "?") for r in answered)),
        "by_cluster": by_cluster,
        "top_questions": top_questions,
        "top_topics": top_topics,
        "most_excluded": most_excluded,
        "unanswered_questions": [_brief(r, show_user) for r in newest(unanswered)[:TOP_N]],
        "low_confidence_questions": [_brief(r, show_user) for r in newest(low_conf)[:TOP_N]],
        "feedback": {"up": up, "down": down, "wrong_status": wrong},
        "wrong_status_reports": newest(reports)[:TOP_N],
        "feedback_comments": comments[-TOP_N:],
    }
