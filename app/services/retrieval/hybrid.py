"""Hybrid retrieval over every allowed pack: sqlite-vec vectors + FTS5 keywords + trigram circular-number
match, fused with Reciprocal Rank Fusion (k = 60). Also builds the "excluded: cancelled" list and applies
jurisdiction preference."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field

from app.db import serialize_f32
from app.services.retrieval.filters import ALL_STATUSES, PackHandle, status_clause
from app.services.retrieval.rewrite import RewrittenQuery

CHUNK_SELECT = """SELECT c.id AS chunk_id, c.document_id, c.chunk_index, c.clause_ref, c.breadcrumb, c.page_start,
       c.page_end, c.text, c.ocr, d.circular_no, d.title, d.doc_type, d.jurisdiction, d.cluster, d.issue_date,
       d.effective_date, d.status, d.status_reason, d.classification_level, d.applicability
FROM chunks c JOIN documents d ON d.id = c.document_id"""


@dataclass
class Candidate:
    chunk: dict
    tier: int
    rrf: float = 0.0
    ranks: dict = field(default_factory=dict)
    score: float = 0.0  # reranker score
    role: str = "primary"  # primary | comparison

    @property
    def chunk_id(self) -> int:
        return self.chunk["chunk_id"]

    @property
    def doc_id(self) -> int:
        return self.chunk["document_id"]


def _filtered_chunks(h: PackHandle, ids: list[int], statuses: tuple[str, ...], clearance: int) -> dict[int, dict]:
    if not ids:
        return {}
    clause, params = status_clause(statuses)
    rows = h.conn.execute(
        f"{CHUNK_SELECT} WHERE c.id IN ({','.join('?' * len(ids))}) AND {clause} AND d.classification_level <= ?",
        [*ids, *params, clearance]).fetchall()
    return {r["chunk_id"]: dict(r) for r in rows}


def vector_list(h: PackHandle, qvec: list[float] | None, statuses, clearance, k: int, keep: int) -> list[dict]:
    if qvec is None:
        return []
    from app.db import vec_available

    if vec_available():
        hits = h.conn.execute("SELECT rowid, distance FROM vec_chunks WHERE embedding MATCH ? AND k = ? ORDER BY distance",
                              (serialize_f32(qvec), k)).fetchall()
    else:
        hits = _brute_force(h, qvec, k)
    rows = _filtered_chunks(h, [r[0] for r in hits], statuses, clearance)
    out = []
    for rowid, dist in hits:
        if rowid in rows:
            out.append({**rows[rowid], "_vec_distance": dist})
        if len(out) >= keep:
            break
    return out


def _brute_force(h: PackHandle, qvec: list[float], k: int) -> list[tuple[int, float]]:
    """Exact search without sqlite-vec: L2 distance over the pack's plain chunk_vectors table."""
    from app.db import deserialize_f32

    scored = []
    for chunk_id, blob in h.conn.execute("SELECT chunk_id, embedding FROM chunk_vectors"):
        vec = deserialize_f32(blob)
        scored.append((chunk_id, sum((a - b) ** 2 for a, b in zip(qvec, vec)) ** 0.5))
    return sorted(scored, key=lambda x: x[1])[:k]


def keyword_list(h: PackHandle, fts_query: str, statuses, clearance, keep: int) -> list[dict]:
    if not fts_query:
        return []
    try:
        hits = h.conn.execute("SELECT rowid, bm25(chunks_fts) AS s FROM chunks_fts WHERE chunks_fts MATCH ? "
                              "ORDER BY s LIMIT 100", (fts_query,)).fetchall()
    except sqlite3.OperationalError:
        return []
    rows = _filtered_chunks(h, [r[0] for r in hits], statuses, clearance)
    return [rows[r[0]] for r in hits if r[0] in rows][:keep]


def trigram_list(h: PackHandle, refs: list[str], statuses, clearance, keep: int) -> list[dict]:
    doc_ids: list[int] = []
    for ref in refs:
        phrase = '"' + ref.replace('"', "") + '"'
        try:
            doc_ids += [r[0] for r in h.conn.execute("SELECT rowid FROM docs_trgm WHERE circular_no MATCH ?", (phrase,))]
        except sqlite3.OperationalError:
            continue
    if not doc_ids:
        return []
    clause, params = status_clause(statuses)
    rows = h.conn.execute(
        f"{CHUNK_SELECT} WHERE d.id IN ({','.join('?' * len(doc_ids))}) AND {clause} AND d.classification_level <= ? "
        "ORDER BY c.chunk_index DESC", [*doc_ids, *params, clearance]).fetchall()
    # Later chunks first: PEMBATALAN / PINDAAN clauses usually carry the answer for "is X still valid?".
    return [dict(r) for r in rows][:keep]


def search(handles: list[PackHandle], rq: RewrittenQuery, qvec: list[float] | None, statuses: tuple[str, ...],
           clearance: int, settings) -> list[Candidate]:
    fused: dict[int, Candidate] = {}
    fts = rq.fts_query()
    for h in handles:
        lists = {
            "vector": vector_list(h, qvec, statuses, clearance, settings.vector_k, settings.per_list_limit),
            "keyword": keyword_list(h, fts, statuses, clearance, settings.per_list_limit),
            "trigram": trigram_list(h, rq.circular_refs, statuses, clearance, settings.per_list_limit),
        }
        for name, items in lists.items():
            for rank, item in enumerate(items, start=1):
                cand = fused.get(item["chunk_id"])
                if cand is None:
                    item.pop("_vec_distance", None)
                    cand = fused[item["chunk_id"]] = Candidate(item, h.tier)
                cand.rrf += 1.0 / (settings.rrf_k + rank)
                cand.ranks[name] = rank
    return sorted(fused.values(), key=lambda c: c.rrf, reverse=True)


def excluded_candidates(handles: list[PackHandle], rq: RewrittenQuery, qvec, clearance: int, settings,
                        shown_statuses: tuple[str, ...]) -> list[Candidate]:
    """Best chunk of each CANCELLED document that would have ranked in the top N without the status filter."""
    everything = search(handles, rq, qvec, ALL_STATUSES, clearance, settings)[: settings.excluded_top_n]
    out, seen = [], set()
    for c in everything:
        ch = c.chunk
        if ch["status"] == "CANCELLED" and ch["status"] not in shown_statuses and ch["document_id"] not in seen:
            seen.add(ch["document_id"])
            out.append(c)
    return out


def excluded_payload(c: Candidate) -> dict:
    ch = c.chunk
    return {"document_id": ch["document_id"], "circular_no": ch["circular_no"], "title": ch["title"],
            "status": ch["status"], "status_reason": ch["status_reason"], "clause_ref": ch["clause_ref"],
            "issue_date": ch["issue_date"], "page": ch["page_start"], "text": ch["text"], "score": round(c.score, 4)}


def inject_amendments(handles: list[PackHandle], selected: list[Candidate], statuses: tuple[str, ...],
                      clearance: int, n: int) -> list[Candidate]:
    """When a selected passage comes from an AMENDED document, make sure the amending clause is in the
    context too (it may not share the question's words), replacing the weakest passage if needed."""
    have = {c.chunk_id for c in selected}
    added: dict[int, list[Candidate]] = {}  # amended chunk id -> amending passages
    for c in list(selected):
        if c.chunk["status"] != "AMENDED":
            continue
        for h in handles:
            rels = h.conn.execute("SELECT source_doc_id, scope, evidence_text FROM relations WHERE target_doc_id = ? "
                                  "AND relation_type = 'AMENDS' AND verified = 1", (c.doc_id,)).fetchall()
            for source_id, scope, evidence in rels:
                if not _scope_touches(scope, c.chunk.get("clause_ref")):
                    continue  # e.g. PP 5/2025 amends 6.1 only; a passage on 4.1 stays as it is
                clause, params = status_clause(statuses)
                rows = h.conn.execute(f"{CHUNK_SELECT} WHERE d.id = ? AND {clause} AND d.classification_level <= ? "
                                      "ORDER BY c.chunk_index", [source_id, *params, clearance]).fetchall()
                key = (evidence or "")[:40]
                best = next((dict(r) for r in rows if key and key in r["text"].replace("\n", " ")), None)
                best = best or next((dict(r) for r in rows if "dipinda" in r["text"].lower()), None)
                if best is None:
                    continue
                existing = next((x for x in selected if x.chunk_id == best["chunk_id"]), None)
                if existing is None and best["chunk_id"] in have:
                    continue
                have.add(best["chunk_id"])
                added.setdefault(c.chunk_id, []).append(existing or Candidate(best, h.tier, score=c.score, role=c.role))
    if not added:
        return selected
    placed = {a.chunk_id for group in added.values() for a in group}
    base = [c for c in selected if c.chunk_id not in placed]
    n_new = sum(1 for group in added.values() for a in group if a not in selected)
    keep = base[: max(1, n - len(placed))] if n_new else base  # new amendments replace the weakest passages
    out: list[Candidate] = []
    for c in keep:
        out.append(c)
        out += added.get(c.chunk_id, [])  # each amendment right after the passage it amends
    return out[:n]


def _clause_key(ref: str) -> list[int]:
    return [int(p) for p in ref.split(".")]


def _scope_touches(scope: str | None, clause_ref: str | None) -> bool:
    """True when an AMENDS scope ("whole" or "clauses: 6.1, 6.2") overlaps a chunk's clause_ref ("6.1-6.2")."""
    import re

    targets = re.findall(r"\d{1,2}(?:\.\d{1,2})*", scope or "")
    if not targets or not clause_ref:
        return True
    m = re.fullmatch(r"(\d+(?:\.\d+)*)(?:-(\d+(?:\.\d+)*))?", clause_ref)
    if not m:
        return True
    lo, hi = _clause_key(m.group(1)), _clause_key(m.group(2) or m.group(1))
    return any(lo <= _clause_key(t) <= hi or _clause_key(t)[: len(lo)] == lo for t in targets)


PREFERRED = {"FEDERAL": {"FEDERAL", "FEDERAL_SARAWAK"}, "SARAWAK": {"SARAWAK", "FEDERAL_SARAWAK"}}


def apply_jurisdiction(ranked: list[Candidate], user: dict, rq: RewrittenQuery, n: int,
                       strong: float, ratio: float = 0.75) -> tuple[list[Candidate], bool]:
    """Prefer the user's jurisdiction (or the question's explicit hint). If strong passages from both
    jurisdictions remain, flag a conflict and keep the best of each."""
    target = rq.jurisdiction_hint or user.get("jurisdiction") or "FEDERAL"
    pref = PREFERRED.get(target, {target})
    other_j = "FEDERAL" if target == "SARAWAK" else "SARAWAK"

    def is_other(c: Candidate) -> bool:
        return c.chunk["jurisdiction"] in PREFERRED[other_j] - pref

    mine = [c for c in ranked if not is_other(c)]
    other = [c for c in ranked if is_other(c)]
    for c in other:
        c.role = "comparison"
    strong_mine = [c for c in mine if c.score >= strong and c.chunk["doc_type"] not in ("minutes", "report")]
    strong_other = [c for c in other if c.score >= strong and c.chunk["doc_type"] not in ("minutes", "report")]
    top = max((c.score for c in ranked), default=0.0)
    conflict = bool(strong_mine and strong_other and strong_other[0].score >= ratio * top
                    and strong_mine[0].score >= ratio * top)
    if conflict:
        keep_other = min(2, len(strong_other))
        selected = mine[: n - keep_other] + strong_other[:keep_other]
    else:
        # Preferred jurisdiction first; other-jurisdiction passages only fill remaining slots.
        selected = (mine + other)[:n] if len(mine) < n else mine[:n]
    return selected, conflict
