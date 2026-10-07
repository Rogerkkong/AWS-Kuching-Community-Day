"""FEATURE B - lineage (amendment / cancellation history). STUB created by Foundation.

Contract (keep these signatures):
    get_lineage(store, user, doc_id) -> {"nodes": [...], "edges": [...]}
    to_dot(lineage) -> str   (Graphviz DOT for st.graphviz_chart)

Node: {"doc_id", "circular_no", "title", "status", "status_reason", "issue_date",
       "effective_date", "jurisdiction", "hidden": False}
Hidden placeholder node (restricted, never reveals title/number):
      {"doc_id": "hidden-1", "hidden": True, "label": "1 dokumen terhad disembunyikan"}
Edge: {"source", "target", "type", "evidence", "page", "scope"}

This stub walks verified relations in both directions and hides restricted nodes.
"""

from __future__ import annotations

from . import access


def get_lineage(store, user, doc_id: str) -> dict:
    """Connected component of doc_id over verified relations, ordered by date."""
    if access.get_doc(store, user, doc_id) is None:
        return {"nodes": [], "edges": []}
    seen, queue, edges = {doc_id}, [doc_id], []
    rels = store.verified_relations()
    while queue:
        current = queue.pop()
        for r in rels:
            if current in (r.source_doc_id, r.target_doc_id) and r.target_doc_id:
                edges.append(r)
                for other in (r.source_doc_id, r.target_doc_id):
                    if other not in seen and other in store.docs:
                        seen.add(other)
                        queue.append(other)
    nodes, hidden_ids = [], {}
    for did in sorted(seen, key=lambda d: (store.docs[d].issue_date or store.docs[d].effective_date or store.today)):
        doc = store.docs[did]
        if access.can_see(user, doc):
            nodes.append(
                {
                    "doc_id": did, "circular_no": doc.label, "title": doc.title, "status": doc.status,
                    "status_reason": doc.status_reason, "issue_date": doc.issue_date, "effective_date": doc.effective_date,
                    "jurisdiction": doc.jurisdiction, "hidden": False,
                }
            )
        else:
            hidden_ids[did] = f"hidden-{len(hidden_ids) + 1}"
            nodes.append({"doc_id": hidden_ids[did], "hidden": True, "label": access.hidden_placeholder(1)})
    unique = {r.relation_id: r for r in edges}.values()
    out_edges = [
        {
            "source": hidden_ids.get(r.source_doc_id, r.source_doc_id),
            "target": hidden_ids.get(r.target_doc_id, r.target_doc_id),
            "type": r.relation_type,
            "evidence": "" if (r.source_doc_id in hidden_ids or r.target_doc_id in hidden_ids) else r.evidence_text,
            "page": r.evidence_page,
            "scope": r.scope,
        }
        for r in unique
    ]
    return {"nodes": nodes, "edges": out_edges}


def to_dot(lineage: dict) -> str:
    """Graphviz DOT text for the lineage graph."""
    lines = ["digraph lineage {", "  rankdir=LR;", '  node [shape=box, style="rounded"];']
    for n in lineage.get("nodes", []):
        label = n["label"] if n.get("hidden") else f"{n['circular_no']}\\n{n['status']}"
        lines.append(f'  "{n["doc_id"]}" [label="{label}"];')
    for e in lineage.get("edges", []):
        lines.append(f'  "{e["source"]}" -> "{e["target"]}" [label="{e["type"]}"];')
    lines.append("}")
    return "\n".join(lines)
