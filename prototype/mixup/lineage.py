"""FEATURE B - lineage: the "family tree" of a rule (guide 7.7, FR-10).

    get_lineage(store, user, doc_id) -> {"nodes": [...], "edges": [...]}
    to_dot(lineage, lang="ms") -> str      Graphviz DOT for st.graphviz_chart
    change_pairs(lineage) -> [(old_id, new_id, relation_type, effective_date)]   newest first

Walk: version-chain relations (CANCELS, SUPERSEDES, AMENDS) are followed in both
directions, transitively. REFERENCES are added one hop from the chain (shown, not
followed), so the graph stays focused on one rule. Verified relations are solid edges;
pending (unverified) chain candidates are dashed and marked "belum disahkan".

Node: {"doc_id", "circular_no", "title", "status", "status_reason", "issue_date",
       "effective_date", "jurisdiction", "doc_type", "cluster", "is_root", "hidden": False}
Hidden node (above the user's clearance; never reveals number, title or dates):
       {"doc_id": "hidden-1", "hidden": True, "label": "1 dokumen terhad disembunyikan", "label_en": ...}
External node (cited circular not in the library): {"doc_id": "ext-1", "external": True, "label": "PP 5/2018"}
Edge: {"relation_id", "source", "target", "type", "evidence", "page", "scope", "verified",
       "effective_date", "confidence"}   source --type--> target (e.g. SPP 1/2023 CANCELS SPP 3/2019)
"""

from __future__ import annotations

from datetime import date

from . import access
from .models import AMENDS, CANCELS, REFERENCES, STATUS_LABELS, SUPERSEDES

CHAIN_TYPES = (CANCELS, SUPERSEDES, AMENDS)

# Edge wording, read as "<source> <verb> <target>".
EDGE_LABELS = {
    CANCELS: ("membatalkan", "cancels"),
    SUPERSEDES: ("menggantikan", "supersedes"),
    AMENDS: ("meminda", "amends"),
    REFERENCES: ("merujuk", "references"),
}
# Graphviz fill / border colours by status (text label is always shown too).
DOT_COLOURS = {
    "IN_FORCE": ("#d8f0dd", "#2e7d32"),
    "AMENDED": ("#ffe9c2", "#b26a00"),
    "CANCELLED": ("#f9d6d5", "#c62828"),
    "ONE_OFF": ("#e4e4e4", "#616161"),
    "UNKNOWN": ("#e4e4e4", "#616161"),
}
HIDDEN_COLOURS = ("#eeeeee", "#9e9e9e")


def _date_key(doc) -> date:
    return doc.issue_date or doc.effective_date or date.max


def _relations(store, include_pending: bool) -> list:
    """Verified relations, plus pending chain candidates when include_pending."""
    rels = list(store.verified_relations())
    if include_pending:
        rels += [r for r in store.pending_relations() if r.relation_type in CHAIN_TYPES]
    return rels


def _component(store, doc_id: str, rels: list) -> set[str]:
    """Documents connected to doc_id through version-chain relations (both directions)."""
    chain = [r for r in rels if r.relation_type in CHAIN_TYPES and r.target_doc_id]
    seen, queue = {doc_id}, [doc_id]
    while queue:
        current = queue.pop()
        for r in chain:
            if current not in (r.source_doc_id, r.target_doc_id):
                continue
            for other in (r.source_doc_id, r.target_doc_id):
                if other not in seen and other in store.docs:
                    seen.add(other)
                    queue.append(other)
    return seen


def get_lineage(store, user, doc_id: str, include_pending: bool = True) -> dict:
    """Lineage of doc_id for this user: nodes ordered by date, edges with evidence.

    Returns {"nodes": [], "edges": []} when the document is missing or hidden from the user.
    """
    if access.get_doc(store, user, doc_id) is None:
        return {"nodes": [], "edges": []}
    rels = _relations(store, include_pending)
    members = _component(store, doc_id, rels)

    # Edges: chain relations inside the component, references one hop out, external targets.
    edges, external = [], {}
    for r in rels:
        src_in, tgt_in = r.source_doc_id in members, r.target_doc_id in members
        if not r.target_doc_id:
            if src_in and r.relation_type in CHAIN_TYPES and r.target_ref_text:
                external.setdefault(r.target_ref_text, f"ext-{len(external) + 1}")
                edges.append(r)
            continue
        if r.source_doc_id not in store.docs or r.target_doc_id not in store.docs:
            continue
        if r.relation_type in CHAIN_TYPES and src_in and tgt_in:
            edges.append(r)
        elif r.relation_type == REFERENCES and (src_in or tgt_in):
            edges.append(r)
    edges = list({r.relation_id: r for r in edges}.values())
    node_ids = set(members) | {r.source_doc_id for r in edges if r.source_doc_id in store.docs} | {
        r.target_doc_id for r in edges if r.target_doc_id in store.docs
    }

    nodes, hidden_ids = [], {}
    visible = [d for d in node_ids if access.can_see(user, store.docs[d])]
    for did in sorted(visible, key=lambda d: (_date_key(store.docs[d]), store.docs[d].label)):
        doc = store.docs[did]
        nodes.append(
            {
                "doc_id": did,
                "circular_no": doc.label,
                "title": doc.title,
                "status": doc.status,
                "status_reason": safe_reason(store, user, doc.status_reason),
                "issue_date": doc.issue_date,
                "effective_date": doc.effective_date,
                "jurisdiction": doc.jurisdiction,
                "doc_type": doc.doc_type,
                "cluster": doc.cluster,
                "is_root": did == doc_id,
                "hidden": False,
            }
        )
    # Restricted nodes go last (their dates would hint at them) and reveal nothing.
    for did in sorted(d for d in node_ids if d not in visible):
        hidden_ids[did] = f"hidden-{len(hidden_ids) + 1}"
        nodes.append(
            {
                "doc_id": hidden_ids[did],
                "hidden": True,
                "label": access.hidden_placeholder(1, "ms"),
                "label_en": access.hidden_placeholder(1, "en"),
            }
        )
    for ref_text, ext_id in external.items():
        nodes.append({"doc_id": ext_id, "external": True, "hidden": False, "label": ref_text,
                      "circular_no": ref_text, "title": "", "status": "UNKNOWN",
                      "status_reason": "Tiada dalam perpustakaan / Not in the library"})

    out_edges = []
    def order(r):  # edges touching hidden nodes go last, like the nodes themselves
        hidden = r.source_doc_id in hidden_ids or r.target_doc_id in hidden_ids
        return (hidden, r.effective_date or date.max, r.relation_id)

    for r in sorted(edges, key=order):
        touches_hidden = r.source_doc_id in hidden_ids or r.target_doc_id in hidden_ids
        if r.source_doc_id in hidden_ids and not r.target_doc_id:
            continue
        out_edges.append(
            {
                "relation_id": "" if touches_hidden else r.relation_id,
                "source": hidden_ids.get(r.source_doc_id, r.source_doc_id),
                "target": hidden_ids.get(r.target_doc_id, r.target_doc_id) or external.get(r.target_ref_text, ""),
                "type": r.relation_type,
                "evidence": "" if touches_hidden else r.evidence_text,
                "page": None if touches_hidden else r.evidence_page,
                "scope": "" if touches_hidden else r.scope,
                "verified": bool(r.verified),
                "effective_date": None if touches_hidden else r.effective_date,
                "confidence": r.confidence,
            }
        )
    return {"nodes": nodes, "edges": out_edges}


def safe_reason(store, user, reason: str) -> str:
    """status_reason with the number of any document the user may not see masked
    (e.g. 'Dibatalkan oleh PKP 1/2025' -> 'Dibatalkan oleh dokumen terhad')."""
    reason = reason or ""
    for doc in store.docs.values():
        if doc.circular_no and doc.circular_no in reason and not access.can_see(user, doc):
            reason = reason.replace(doc.circular_no, "dokumen terhad")
    return reason


def change_pairs(lineage: dict) -> list[tuple[str, str, str, date | None]]:
    """(old_id, new_id, relation_type, effective_date) for every visible chain edge, newest first."""
    ok = {n["doc_id"] for n in lineage.get("nodes", []) if not n.get("hidden") and not n.get("external")}
    pairs = [
        (e["target"], e["source"], e["type"], e.get("effective_date"))
        for e in lineage.get("edges", [])
        if e["type"] in CHAIN_TYPES and e["source"] in ok and e["target"] in ok
    ]
    return sorted(pairs, key=lambda p: (p[3] or date.min), reverse=True)


def edge_label(relation_type: str, lang: str = "ms") -> str:
    """'membatalkan' / 'cancels'."""
    pair = EDGE_LABELS.get(relation_type, (relation_type.lower(), relation_type.lower()))
    return pair[1] if lang == "en" else pair[0]


def scope_label(scope: str, lang: str = "ms") -> str:
    """'clauses: 4.2' -> 'perenggan 4.2' / 'clause 4.2'; 'whole' -> ''."""
    scope = (scope or "").strip()
    if not scope or scope == "whole":
        return ""
    if scope.lower().startswith("clauses:"):
        refs = scope.split(":", 1)[1].strip()
        return f"clause {refs}" if lang == "en" else f"perenggan {refs}"
    return scope


def _esc(text) -> str:
    """Escape a value for a double-quoted DOT string."""
    return str(text or "").replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def _wrap(text: str, width: int = 28, max_lines: int = 3) -> list[str]:
    words, lines, line = (text or "").split(), [], ""
    for w in words:
        if line and len(line) + 1 + len(w) > width:
            lines.append(line)
            line = w
        else:
            line = f"{line} {w}".strip()
    if line:
        lines.append(line)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1][: width - 3] + "..."
    return lines


def to_dot(lineage: dict, lang: str = "ms") -> str:
    """Graphviz DOT text (rankdir=LR, older rules on the left).

    Nodes are coloured AND labelled by status (green Berkuat kuasa, amber Dipinda,
    red Dibatalkan, grey Belum disahkan / Sekali sahaja). Edges read "new verb old".
    """
    en = lang == "en"
    lines = [
        "digraph lineage {",
        "  rankdir=LR;",
        '  graph [bgcolor="transparent", nodesep=0.4, ranksep=0.6];',
        '  node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=11, penwidth=1.5];',
        '  edge [fontname="Helvetica", fontsize=10];',
    ]
    for n in lineage.get("nodes", []):
        nid = _esc(n["doc_id"])
        if n.get("hidden"):
            fill, border = HIDDEN_COLOURS
            label = _esc(n.get("label_en") if en else n.get("label"))
            lines.append(f'  "{nid}" [label="{label}", fillcolor="{fill}", color="{border}", style="rounded,filled,dashed"];')
            continue
        if n.get("external"):
            text = "Tiada dalam perpustakaan" if not en else "Not in the library"
            lines.append(f'  "{nid}" [label="{_esc(n["label"])}\\n({text})", fillcolor="#ffffff", color="#9e9e9e", style="rounded,dashed"];')
            continue
        ms, en_label, _ = STATUS_LABELS.get(n.get("status"), (n.get("status"), n.get("status"), "gray"))
        fill, border = DOT_COLOURS.get(n.get("status"), DOT_COLOURS["UNKNOWN"])
        title = "\\n".join(_esc(t) for t in _wrap(n.get("title", "")))
        when = n.get("effective_date") or n.get("issue_date")
        status_text = _esc(en_label if en else ms)
        label = f"{_esc(n['circular_no'])}\\n{title}\\n[{status_text}]"
        if when:
            label += f"\\n{when.isoformat() if hasattr(when, 'isoformat') else _esc(when)}"
        width = 3.0 if n.get("is_root") else 1.5
        lines.append(f'  "{nid}" [label="{label}", fillcolor="{fill}", color="{border}", penwidth={width}];')
    for e in lineage.get("edges", []):
        if not e.get("target"):
            continue
        parts = [edge_label(e["type"], lang)]
        style = "solid"
        if not e.get("verified"):
            parts[0] += " (unverified)" if en else " (belum disahkan)"
            style = "dashed"
        if e["type"] == REFERENCES:
            style, colour = "dotted", "#757575"
        else:
            colour = {CANCELS: "#c62828", SUPERSEDES: "#c62828", AMENDS: "#b26a00"}.get(e["type"], "#424242")
        if e.get("scope") and e["scope"] != "whole":
            parts.append(scope_label(e["scope"], lang))
        label = "\\n".join(_esc(p) for p in parts)
        # Drawn old -> new (so time flows left to right) with the arrowhead on the old node.
        lines.append(
            f'  "{_esc(e["target"])}" -> "{_esc(e["source"])}" [dir=back, label="{label}", '
            f'style={style}, color="{colour}", fontcolor="{colour}"];'
        )
    lines.append("}")
    return "\n".join(lines)
