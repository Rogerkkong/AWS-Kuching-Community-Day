"""FEATURE B - MixUp Map: Graphviz DOT of document relationships.

STUB created by Foundation (already draws a basic graph). Feature B improves it.
"""

from __future__ import annotations

from .context import AppContext

STATUS_COLORS = {"in_force": "#2e7d32", "superseded": "#c62828", "record": "#1565c0"}
EDGE_STYLES = {
    "supersedes": 'color="#c62828", penwidth=2, label="supersedes"',
    "references": 'color="#757575", style=dashed, label="references"',
    "conflicts": 'color="#ef6c00", penwidth=2, style=bold, label="conflicts", dir=both',
    "discussed_in": 'color="#1565c0", style=dotted, label="discussed in"',
}


def _q(text: str) -> str:
    return '"' + str(text).replace("\\", "\\\\").replace('"', '\\"') + '"'


def build_dot(ctx: AppContext, highlight: str | None = None) -> str:
    """Return a DOT string for st.graphviz_chart."""
    lines = ["digraph MixUp {", "  rankdir=LR;", '  node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=10];']
    for doc in ctx.docs.values():
        color = STATUS_COLORS.get(doc.status, "#616161")
        pen = 3 if doc.doc_id == highlight else 1
        label = f"{doc.short_label}\\n{doc.title[:40]}"
        lines.append(f'  {_q(doc.doc_id)} [label={_q(label)}, fillcolor="white", color="{color}", penwidth={pen}];')
    for src, dst, rel in ctx.versions.edges:
        lines.append(f"  {_q(src)} -> {_q(dst)} [{EDGE_STYLES.get(rel, '')}, fontsize=8];")
    lines.append("}")
    return "\n".join(lines)
