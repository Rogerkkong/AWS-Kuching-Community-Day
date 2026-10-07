"""Change summaries for SUPERSEDES / AMENDS pairs (Publisher only; Officer only displays them).

Clauses are aligned by clause_ref, otherwise by embedding similarity >= 0.80 (AMENDS relations with a
clause scope align the amended clause with the clause holding the evidence sentence). The aligned
diff goes to the CHANGE_SUMMARY prompt.
"""
from __future__ import annotations

import difflib
import json
import re
import sqlite3

from app.services.generation import prompts

CLAUSE_LINE_RE = re.compile(r"^(\d{1,2}(?:\.\d{1,2})*)\.?\s+(.+)$")
SIM_THRESHOLD = 0.80


def clauses_of(conn: sqlite3.Connection, doc_id: int) -> dict[str, str]:
    """clause number -> text, from the chunk text lines (headings are folded into their clause)."""
    out: dict[str, str] = {}
    for row in conn.execute("SELECT text FROM chunks WHERE document_id = ? ORDER BY chunk_index", (doc_id,)):
        heading_num = None
        for line in row[0].split("\n"):
            m = CLAUSE_LINE_RE.match(line.strip())
            if not m:
                if heading_num and heading_num not in out:
                    out[heading_num] = line.strip()
                elif heading_num:
                    out[heading_num] += " " + line.strip()
                continue
            num, text = m.group(1), m.group(2).strip()
            if text.isupper():  # section heading line, e.g. "4. MEMBAWA KE HADAPAN CUTI REHAT"
                heading_num = num
                continue
            out[num] = text
            heading_num = None
    return out


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def align(old: dict[str, str], new: dict[str, str], client=None, scope_pairs: list[tuple[str, str]] | None = None) -> list[dict]:
    pairs: list[tuple[str | None, str | None]] = []
    used_old, used_new = set(), set()
    for o, n in scope_pairs or []:
        if o in old and n in new:
            pairs.append((o, n))
            used_old.add(o)
            used_new.add(n)
    for ref in new:
        if ref in old and ref not in used_old and ref not in used_new:
            if difflib.SequenceMatcher(None, old[ref], new[ref]).ratio() >= 0.4:
                pairs.append((ref, ref))
                used_old.add(ref)
                used_new.add(ref)
    rest_old = [r for r in old if r not in used_old]
    rest_new = [r for r in new if r not in used_new]
    if rest_old and rest_new and client is not None:
        try:
            vo = client.embed([old[r] for r in rest_old])
            vn = client.embed([new[r] for r in rest_new])
            candidates = sorted(((_dot(a, b), i, j) for i, a in enumerate(vo) for j, b in enumerate(vn)), reverse=True)
            for score, i, j in candidates:
                if score < SIM_THRESHOLD:
                    break
                if rest_old[i] in used_old or rest_new[j] in used_new:
                    continue
                pairs.append((rest_old[i], rest_new[j]))
                used_old.add(rest_old[i])
                used_new.add(rest_new[j])
        except Exception:  # noqa: BLE001 - alignment degrades to ADDED/REMOVED
            pass
    pairs += [(r, None) for r in old if r not in used_old]
    pairs += [(None, r) for r in new if r not in used_new]

    diff = []
    for o, n in pairs:
        old_text, new_text = old.get(o, "") if o else "", new.get(n, "") if n else ""
        if o and n and old_text == new_text:
            continue
        kind = "CHANGED" if o and n else ("REMOVED" if o else "ADDED")
        diff.append({"clause_old": o, "clause_new": n, "type": kind, "old_text": old_text, "new_text": new_text,
                     "inline": _inline(old_text, new_text) if kind == "CHANGED" else None})
    key = lambda d: [int(x) for x in (d["clause_new"] or d["clause_old"]).split(".")]  # noqa: E731
    return sorted(diff, key=key)


def _inline(old: str, new: str) -> list[list[str]]:
    """Word-level diff ops for the side-by-side view: [op, text] with op in = - +."""
    a, b = old.split(), new.split()
    ops: list[list[str]] = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b).get_opcodes():
        if tag == "equal":
            ops.append(["=", " ".join(a[i1:i2])])
        else:
            if i2 > i1:
                ops.append(["-", " ".join(a[i1:i2])])
            if j2 > j1:
                ops.append(["+", " ".join(b[j1:j2])])
    return ops


def _scope_pairs(rel: dict, new_clauses: dict[str, str]) -> list[tuple[str, str]]:
    scope = rel.get("scope") or ""
    targets = re.findall(r"\d{1,2}(?:\.\d{1,2})+", scope)
    evidence = (rel.get("evidence_text") or "")[:60]
    holder = next((ref for ref, text in new_clauses.items() if evidence and evidence[:40] in text), None)
    if holder is None:
        holder = next((ref for ref, text in new_clauses.items()
                       if any(t in text for t in targets) and ("dipinda" in text or "pindaan" in text)), None)
    return [(t, holder) for t in targets] if holder else []


def build_change_summaries(conn: sqlite3.Connection, client) -> int:
    from app.services.inference.client import parse_json_loose

    conn.row_factory = sqlite3.Row
    rels = [dict(r) for r in conn.execute(
        """SELECT r.*, s.circular_no AS new_no, s.title AS new_title, t.circular_no AS old_no, t.title AS old_title
           FROM relations r JOIN documents s ON s.id = r.source_doc_id JOIN documents t ON t.id = r.target_doc_id
           WHERE r.verified = 1 AND r.relation_type IN ('SUPERSEDES', 'AMENDS')""")]
    made = 0
    for rel in rels:
        old_id, new_id = rel["target_doc_id"], rel["source_doc_id"]
        if conn.execute("SELECT 1 FROM change_summaries WHERE old_doc_id=? AND new_doc_id=?", (old_id, new_id)).fetchone():
            continue
        old_c, new_c = clauses_of(conn, old_id), clauses_of(conn, new_id)
        scope_pairs = _scope_pairs(rel, new_c) if rel["relation_type"] == "AMENDS" else []
        diff = align(old_c, new_c, client, scope_pairs)
        if rel["relation_type"] == "AMENDS" and scope_pairs:
            # An amending circular only changes the scoped clauses; the rest of the old text still applies.
            diff = [d for d in diff if (d["clause_old"], d["clause_new"]) in scope_pairs]
        prompt_diff = [{k: d[k] for k in ("clause_old", "clause_new", "type", "old_text", "new_text")} for d in diff]
        summary = {}
        try:
            reply = client.chat([{"role": "user", "content": prompts.CHANGE_SUMMARY.format(
                old_circular_no=rel["old_no"], old_title=rel["old_title"], new_circular_no=rel["new_no"],
                new_title=rel["new_title"], diff_json=json.dumps(prompt_diff, ensure_ascii=False))}],
                json_mode=True, max_tokens=900, timeout=300)
            summary = parse_json_loose(reply)
            if not isinstance(summary, dict):
                summary = {}
        except Exception:  # noqa: BLE001
            summary = {}
        changed = ", ".join((d["clause_new"] or d["clause_old"]) for d in diff) or "-"
        summary_ms = summary.get("summary_ms") or f"{rel['new_no']} mengubah perenggan {changed} berbanding {rel['old_no']}."
        summary_en = summary.get("summary_en") or f"{rel['new_no']} changes paragraphs {changed} compared with {rel['old_no']}."
        payload = {"relation_type": rel["relation_type"], "clauses": diff,
                   "changes": summary.get("changes") or [], "who_is_affected": summary.get("who_is_affected"),
                   "effective_date": summary.get("effective_date")}
        conn.execute("INSERT INTO change_summaries (old_doc_id, new_doc_id, diff_json, summary_ms, summary_en) VALUES (?,?,?,?,?)",
                     (old_id, new_id, json.dumps(payload, ensure_ascii=False), summary_ms, summary_en))
        made += 1
    conn.commit()
    return made
