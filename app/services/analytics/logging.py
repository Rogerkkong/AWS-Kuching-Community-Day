"""Local query log (app.db only; nothing leaves the PC unless the user exports a report)."""
from __future__ import annotations

import json
from datetime import datetime


def log_query(state, user: dict, question: str, retrieval, answerable: bool, confidence: str,
              latency_ms: int, sources_ms: int) -> int:
    top = retrieval.selected[0].chunk if retrieval.selected else None
    with state.app_db() as conn:
        cur = conn.execute(
            """INSERT INTO query_logs (user_id, query, rewritten_json, retrieved_ids, excluded_ids, answerable, top_score,
               confidence, latency_ms, feedback, created_at, topic, cluster, sources_ms)
               VALUES (?,?,?,?,?,?,?,?,?,NULL,?,?,?,?)""",
            (user["id"], question, retrieval.rq.to_json(),
             json.dumps([{"doc": c.doc_id, "chunk": c.chunk_id, "no": c.chunk["circular_no"]} for c in retrieval.selected]),
             json.dumps([{"doc": e["document_id"], "no": e["circular_no"]} for e in retrieval.excluded]),
             int(answerable), retrieval.top_score, confidence, latency_ms,
             datetime.now().isoformat(timespec="seconds"), retrieval.rq.topic, top["cluster"] if top else None, sources_ms))
        return cur.lastrowid


def record_feedback(state, query_log_id: int, rating: str, comment: str | None) -> bool:
    with state.app_db() as conn:
        cur = conn.execute("UPDATE query_logs SET feedback = ? WHERE id = ?",
                           (json.dumps({"rating": rating, "comment": (comment or "")[:500]}), query_log_id))
        return cur.rowcount > 0
