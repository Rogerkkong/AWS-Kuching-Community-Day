"""Amendment / cancellation history (lineage) across the packs the user may open."""
from __future__ import annotations

import json

from app import db
from app.services.retrieval.filters import PackHandle

LINEAGE_TYPES = ("CANCELS", "SUPERSEDES", "AMENDS")


def _all(handles: list[PackHandle], clearance: int) -> tuple[dict[int, dict], dict[int, dict], dict[tuple, dict]]:
    docs, rels, sums = {}, {}, {}
    for h in handles:
        for d in db.rows(h.conn.execute(
                "SELECT id, circular_no, title, doc_type, jurisdiction, issue_date, effective_date, status, status_reason, "
                "classification_level FROM documents WHERE classification_level <= ?", (clearance,))):
            docs[d["id"]] = d
        for r in db.rows(h.conn.execute("SELECT * FROM relations")):
            rels[r["id"]] = r
        for s in db.rows(h.conn.execute("SELECT * FROM change_summaries")):
            sums[(s["old_doc_id"], s["new_doc_id"])] = s
    # Drop anything touching a document this user cannot see.
    rels = {i: r for i, r in rels.items() if r["source_doc_id"] in docs and (r["target_doc_id"] in docs)}
    sums = {k: s for k, s in sums.items() if k[0] in docs and k[1] in docs}
    return docs, rels, sums


def lineage(handles: list[PackHandle], clearance: int, doc_id: int) -> dict:
    docs, rels, sums = _all(handles, clearance)
    if doc_id not in docs:
        raise LookupError("Document not found")
    edges = [r for r in rels.values() if r["relation_type"] in LINEAGE_TYPES]
    component, frontier = {doc_id}, [doc_id]
    while frontier:
        cur = frontier.pop()
        for e in edges:
            for a, b in ((e["source_doc_id"], e["target_doc_id"]), (e["target_doc_id"], e["source_doc_id"])):
                if a == cur and b not in component:
                    component.add(b)
                    frontier.append(b)
    nodes = sorted((docs[i] for i in component), key=lambda d: (d.get("issue_date") or "", d["id"]))
    links = []
    for e in edges:
        if e["source_doc_id"] in component and e["target_doc_id"] in component:
            s = sums.get((e["target_doc_id"], e["source_doc_id"]))
            links.append({"source_doc_id": e["source_doc_id"], "target_doc_id": e["target_doc_id"],
                          "relation_type": e["relation_type"], "scope": e["scope"], "evidence_text": e["evidence_text"],
                          "evidence_page": e["evidence_page"], "effective_date": e["effective_date"],
                          "summary_ms": s["summary_ms"] if s else None, "summary_en": s["summary_en"] if s else None,
                          "has_diff": bool(s)})
    # Mentions of circulars not in any pack (e.g. an old circular cancelled long ago).
    return {"document_id": doc_id, "nodes": nodes, "links": links}


def change_view(handles: list[PackHandle], clearance: int, old_id: int, new_id: int) -> dict:
    docs, _, sums = _all(handles, clearance)
    if old_id not in docs or new_id not in docs:
        raise LookupError("Document not found")
    s = sums.get((old_id, new_id))
    if s is None:
        raise LookupError("No change summary for this pair")
    payload = json.loads(s["diff_json"] or "{}")
    return {"old": docs[old_id], "new": docs[new_id], "summary_ms": s["summary_ms"], "summary_en": s["summary_en"],
            "relation_type": payload.get("relation_type"), "clauses": payload.get("clauses", []),
            "changes": payload.get("changes", []), "who_is_affected": payload.get("who_is_affected"),
            "effective_date": payload.get("effective_date")}
