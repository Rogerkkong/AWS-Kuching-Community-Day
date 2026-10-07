"""Status engine. Recompute after every ingestion or verification.

0. minutes/report -> RECORD ("Rekod bertarikh <issue_date>"); records are never cancelled.
1. verified CANCELS/SUPERSEDES targeting the doc, effective (relation date, else source effective_date,
   else source issue_date) on or before today -> CANCELLED ("Dibatalkan oleh <source>").
2. one_off -> ONE_OFF.
3. expiry_date on or before today -> CANCELLED ("Tamat tempoh").
4. verified AMENDS targeting it -> AMENDED ("Dipinda oleh <list>").
5. effective_date on or before today -> IN_FORCE.
6. else UNKNOWN.
"""
from __future__ import annotations

import sqlite3
from datetime import date, datetime

from app.config import RECORD_DOC_TYPES, today
from app.services.ingest.chunker import malay_date


def _d(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def compute_status(doc: dict, incoming: list[dict], on: date | None = None) -> tuple[str, str]:
    """doc: documents row. incoming: verified relations targeting doc, each with source_no,
    source_effective_date, source_issue_date. Returns (status, reason)."""
    on = on or today()
    if doc.get("doc_type") in RECORD_DOC_TYPES:
        return "RECORD", f"Rekod bertarikh {malay_date(doc.get('issue_date'))}"

    cancels = []
    for rel in incoming:
        if rel["relation_type"] not in ("CANCELS", "SUPERSEDES"):
            continue
        when = _d(rel.get("effective_date")) or _d(rel.get("source_effective_date")) or _d(rel.get("source_issue_date"))
        if when is not None and when <= on:
            cancels.append((when, rel["source_no"]))
    if cancels:
        cancels.sort()
        return "CANCELLED", f"Dibatalkan oleh {cancels[-1][1]}"
    if doc.get("one_off"):
        return "ONE_OFF", "Sekali sahaja"
    expiry = _d(doc.get("expiry_date"))
    if expiry is not None and expiry <= on:
        return "CANCELLED", "Tamat tempoh"
    amenders = []
    for rel in incoming:
        if rel["relation_type"] != "AMENDS":
            continue
        when = _d(rel.get("effective_date")) or _d(rel.get("source_effective_date")) or _d(rel.get("source_issue_date"))
        if when is None or when <= on:
            amenders.append(rel["source_no"])
    if amenders:
        return "AMENDED", "Dipinda oleh " + ", ".join(dict.fromkeys(amenders))
    eff = _d(doc.get("effective_date"))
    if eff is not None and eff <= on:
        return "IN_FORCE", "Berkuat kuasa"
    if eff is not None:
        return "UNKNOWN", f"Belum berkuat kuasa (mulai {malay_date(doc.get('effective_date'))})"
    return "UNKNOWN", "Belum disahkan"


def recompute_all(conn: sqlite3.Connection, on: date | None = None) -> dict[int, tuple[str, str]]:
    conn.row_factory = sqlite3.Row
    docs = [dict(r) for r in conn.execute("SELECT * FROM documents")]
    rels = [dict(r) for r in conn.execute(
        """SELECT r.*, s.circular_no AS source_no, s.effective_date AS source_effective_date,
                  s.issue_date AS source_issue_date
           FROM relations r JOIN documents s ON s.id = r.source_doc_id
           WHERE r.verified = 1 AND r.target_doc_id IS NOT NULL""")]
    by_target: dict[int, list[dict]] = {}
    for r in rels:
        by_target.setdefault(r["target_doc_id"], []).append(r)
    result = {}
    stamp = datetime.now().isoformat(timespec="seconds")
    for doc in docs:
        status, reason = compute_status(doc, by_target.get(doc["id"], []), on)
        result[doc["id"]] = (status, reason)
        if (status, reason) != (doc["status"], doc["status_reason"]):
            conn.execute("UPDATE documents SET status = ?, status_reason = ?, updated_at = ? WHERE id = ?",
                         (status, reason, stamp, doc["id"]))
    conn.commit()
    return result
