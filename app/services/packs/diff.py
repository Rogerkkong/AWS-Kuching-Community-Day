"""Compare an installed pack with its replacement and create notifications for affected officers."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

STATUS_MS = {"IN_FORCE": "Berkuat kuasa", "AMENDED": "Dipinda", "CANCELLED": "Dibatalkan", "ONE_OFF": "Sekali sahaja",
             "UNKNOWN": "Belum disahkan", "RECORD": "Rekod"}
STATUS_EN = {"IN_FORCE": "In force", "AMENDED": "Amended", "CANCELLED": "Cancelled", "ONE_OFF": "One-off",
             "UNKNOWN": "Unverified", "RECORD": "Record"}


def snapshot(path: Path | None) -> dict:
    if path is None:
        return {"docs": {}, "relations": {}, "summaries": {}}
    conn = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        docs = {r["id"]: dict(r) for r in conn.execute(
            "SELECT id, circular_no, title, status, status_reason, cluster, classification_level, doc_type FROM documents")}
        rels = {r["id"]: dict(r) for r in conn.execute("SELECT * FROM relations")}
        sums = {(r["old_doc_id"], r["new_doc_id"]): dict(r) for r in conn.execute(
            "SELECT id, old_doc_id, new_doc_id, summary_ms, summary_en FROM change_summaries")}
    finally:
        conn.close()
    return {"docs": docs, "relations": rels, "summaries": sums}


def compare(old_path: Path | None, new_path: Path) -> dict:
    old, new = snapshot(old_path), snapshot(new_path)
    added = [d for i, d in new["docs"].items() if i not in old["docs"]]
    status_changes = []
    for i, d in new["docs"].items():
        before = old["docs"].get(i)
        if before and before["status"] != d["status"]:
            status_changes.append({"document_id": i, "circular_no": d["circular_no"], "title": d["title"],
                                   "cluster": d["cluster"], "old_status": before["status"], "new_status": d["status"],
                                   "status_reason": d["status_reason"]})
    rels_added = [r for i, r in new["relations"].items() if i not in old["relations"]]
    new_sums = [s for k, s in new["summaries"].items() if k not in old["summaries"]]
    return {"added": added, "status_changes": status_changes, "relations_added": rels_added,
            "change_summaries": new_sums, "removed": [d for i, d in old["docs"].items() if i not in new["docs"]]}


def _replacement(changes: dict, doc_id: int) -> int | None:
    for r in changes["relations_added"]:
        if r["target_doc_id"] == doc_id and r["relation_type"] in ("CANCELS", "SUPERSEDES", "AMENDS"):
            return r["source_doc_id"]
    return None


def _summary_for(changes: dict, old_id: int, new_id: int | None) -> dict | None:
    return next((s for s in changes["change_summaries"] if s["old_doc_id"] == old_id and s["new_doc_id"] == new_id), None)


def create_notifications(conn: sqlite3.Connection, changes: dict, tier: int, version: int, recent_days: int = 30) -> int:
    """Notify officers cleared for the tier who follow the cluster or circular, or who recently searched
    for a circular whose status changed."""
    conn.row_factory = sqlite3.Row
    users = [dict(u) for u in conn.execute("SELECT * FROM users WHERE role = 'OFFICER' AND clearance_level >= ?", (tier,))]
    since = (datetime.now() - timedelta(days=recent_days)).isoformat(timespec="seconds")
    now = datetime.now().isoformat(timespec="seconds")
    made = 0

    for u in users:
        subs = [dict(s) for s in conn.execute("SELECT cluster, circular_no FROM subscriptions WHERE user_id = ?", (u["id"],))]
        clusters = {s["cluster"] for s in subs if s["cluster"]}
        numbers = {s["circular_no"] for s in subs if s["circular_no"]}
        recent = [dict(r) for r in conn.execute(
            "SELECT query, retrieved_ids FROM query_logs WHERE user_id = ? AND created_at >= ?", (u["id"], since))]

        def searched(doc: dict) -> bool:
            for r in recent:
                if doc["circular_no"].lower() in (r["query"] or "").lower():
                    return True
                try:
                    ids = json.loads(r["retrieved_ids"] or "[]")
                except ValueError:
                    ids = []
                # retrieved_ids holds [{"doc": document_id, "chunk": chunk_id}, ...]
                if doc["document_id"] in {x.get("doc") for x in ids if isinstance(x, dict)}:
                    return True
            return False

        items = []
        for ch in changes["status_changes"]:
            if ch["cluster"] in clusters or ch["circular_no"] in numbers or searched(ch):
                new_id = _replacement(changes, ch["document_id"])
                summ = _summary_for(changes, ch["document_id"], new_id)
                ms = (f"{ch['circular_no']}: {STATUS_MS.get(ch['old_status'])} -> {STATUS_MS.get(ch['new_status'])} "
                      f"({ch['status_reason']}).")
                en = (f"{ch['circular_no']}: {STATUS_EN.get(ch['old_status'])} -> {STATUS_EN.get(ch['new_status'])} "
                      f"({ch['status_reason']}).")
                if summ:
                    ms, en = f"{ms} {summ['summary_ms']}", f"{en} {summ['summary_en']}"
                items.append((ch["circular_no"], "STATUS_CHANGE", ms, en, ch["document_id"], new_id))
        for d in changes["added"]:
            targets = [r for r in changes["relations_added"] if r["source_doc_id"] == d["id"]]
            if d["cluster"] in clusters or d["circular_no"] in numbers:
                items.append((d["circular_no"], "NEW_DOCUMENT", f"Dokumen baharu: {d['circular_no']} - {d['title']}.",
                              f"New document: {d['circular_no']} - {d['title']}.", d["id"],
                              targets[0]["target_doc_id"] if targets else None))
        for no, kind, ms, en, doc_id, related in items:
            conn.execute("""INSERT INTO notifications (user_id, circular_no, change_type, summary_ms, summary_en,
                            pack_version, read, created_at, document_id, related_doc_id, tier)
                            VALUES (?,?,?,?,?,?,0,?,?,?,?)""",
                         (u["id"], no, kind, ms, en, version, now, doc_id, related, tier))
            made += 1
    conn.commit()
    return made
