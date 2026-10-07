"""Opt-in anonymised usage report: no user names or ids, timestamps rounded down to the hour."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

REPORT_VERSION = 1


def _hour(ts: str | None) -> str | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts).replace(minute=0, second=0, microsecond=0).isoformat(timespec="minutes")
    except ValueError:
        return None


def build_report(conn) -> dict:
    items = []
    for r in conn.execute("SELECT query, topic, cluster, answerable, confidence, excluded_ids, feedback, created_at "
                          "FROM query_logs ORDER BY id"):
        try:
            excluded = [e.get("no") for e in json.loads(r["excluded_ids"] or "[]") if isinstance(e, dict)]
        except ValueError:
            excluded = []
        try:
            rating = (json.loads(r["feedback"]) or {}).get("rating") if r["feedback"] else None
        except ValueError:
            rating = None
        items.append({"query": r["query"], "topic": r["topic"], "cluster": r["cluster"],
                      "answerable": bool(r["answerable"]), "confidence": r["confidence"],
                      "excluded_circulars": excluded, "feedback": rating, "hour": _hour(r["created_at"])})
    return {"report_version": REPORT_VERSION, "kind": "pekeliling-navigator-usage",
            "generated_hour": _hour(datetime.now().isoformat()), "query_count": len(items), "queries": items}


def export_report(conn, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    report = build_report(conn)
    path = out_dir / f"usage-report-{datetime.now():%Y%m%d-%H00}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def validate_report(payload: dict) -> dict:
    if payload.get("kind") != "pekeliling-navigator-usage" or not isinstance(payload.get("queries"), list):
        raise ValueError("Not a Pekeliling Navigator usage report")
    allowed = {"query", "topic", "cluster", "answerable", "confidence", "excluded_circulars", "feedback", "hour"}
    payload["queries"] = [{k: v for k, v in q.items() if k in allowed} for q in payload["queries"] if isinstance(q, dict)]
    return payload
