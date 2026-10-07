"""Lexical retrieval for FAST MODE: BM25 + BM/EN glossary expansion + exact
circular-number boost, with the validity, clearance and jurisdiction filters
applied in code (replaces pgvector + full-text search from the guide).

    hits = search(store, user, "tempoh tuntutan perjalanan")              # in-force only
    hits = search(store, user, q, statuses=None)                            # every status (baseline / excluded list)
    hits = search(store, user, q, prefer_jurisdiction="SARAWAK")            # boost the user's jurisdiction
    hits = search(store, user, q, jurisdictions={"FEDERAL"})                # hard filter

The clearance filter is ALWAYS applied (access.visible_doc_ids).
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Iterable

from . import access
from .models import DEFAULT_STATUSES, Chunk, Citation, Document, Hit, User, jurisdiction_matches
from .textutil import _phrase_in, detect_language, find_refs, load_glossary, normalize, snippet, tokenize

K1 = 1.5
B = 0.75
EXPANSION_WEIGHT = 0.6  # glossary translations count less than the user's own words (same language)
CIRCULAR_BOOST = 2.0  # x score when the query names the document's circular number
JURISDICTION_BOOST = 1.3  # x score for the user's preferred jurisdiction
RECORD_PRIOR = 0.85  # minutes / reports rank a little below rules


class BM25Index:
    """In-memory BM25 over chunks. Index text = title + circular no + breadcrumb + text."""

    def __init__(self) -> None:
        self.chunks: list[Chunk] = []
        self.tfs: list[Counter] = []
        self.lens: list[int] = []
        self.df: Counter = Counter()
        self.avgdl = 1.0

    @staticmethod
    def index_text(chunk: Chunk, doc: Document | None) -> str:
        title = f"{doc.title} {doc.circular_no}" if doc else ""
        return f"{title}\n{chunk.breadcrumb}\n{chunk.text}"

    def add(self, chunks: Iterable[Chunk], docs: dict[str, Document]) -> None:
        """Add chunks and refresh statistics."""
        for chunk in chunks:
            tf = Counter(tokenize(self.index_text(chunk, docs.get(chunk.doc_id))))
            self.chunks.append(chunk)
            self.tfs.append(tf)
            self.lens.append(sum(tf.values()))
            self.df.update(tf.keys())
        self.avgdl = (sum(self.lens) / len(self.lens)) if self.lens else 1.0

    def remove_doc(self, doc_id: str) -> None:
        """Drop every chunk of one document (used when an upload is replaced)."""
        keep = [i for i, c in enumerate(self.chunks) if c.doc_id != doc_id]
        if len(keep) == len(self.chunks):
            return
        self.chunks = [self.chunks[i] for i in keep]
        self.tfs = [self.tfs[i] for i in keep]
        self.lens = [self.lens[i] for i in keep]
        self.df = Counter()
        for tf in self.tfs:
            self.df.update(tf.keys())
        self.avgdl = (sum(self.lens) / len(self.lens)) if self.lens else 1.0

    def bm25(self, i: int, weights: dict[str, float]) -> float:
        """BM25 score of chunk i for weighted query tokens."""
        tf = self.tfs[i]
        n = len(self.chunks)
        dl = self.lens[i] or 1
        score = 0.0
        for tok, weight in weights.items():
            f = tf.get(tok, 0)
            if not f:
                continue
            df = self.df.get(tok, 0)
            idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
            score += weight * idf * (f * (K1 + 1)) / (f + K1 * (1 - B + B * dl / self.avgdl))
        return score


def build_index(chunks: Iterable[Chunk], docs: dict[str, Document]) -> BM25Index:
    index = BM25Index()
    index.add(chunks, docs)
    return index


def query_terms(query: str, glossary=None) -> tuple[dict[str, float], dict[str, set[str]]]:
    """Weighted tokens for a query, and for each user token the set of tokens that
    count as 'found' (itself + glossary translations), used for coverage.

    glossary=None loads data/glossary.json; glossary=[] disables expansion.
    """
    if glossary is None:
        glossary = load_glossary()
    q = normalize(query)
    user_tokens = list(dict.fromkeys(tokenize(query)))
    weights = {tok: 1.0 for tok in user_tokens}
    equivalents = {tok: {tok} for tok in user_tokens}
    for en, ms in glossary:
        for src, dst in ((en, ms), (ms, en)):
            if _phrase_in(src, q) and not _phrase_in(dst, q):
                dst_tokens = tokenize(dst)
                for tok in dst_tokens:
                    weights.setdefault(tok, EXPANSION_WEIGHT)
                for stok in tokenize(src):
                    if stok in equivalents:
                        equivalents[stok].update(dst_tokens)
    return weights, equivalents


def search(
    store,
    user: User | None,
    query: str,
    *,
    k: int = 10,
    statuses: Iterable[str] | None = DEFAULT_STATUSES,
    jurisdictions: Iterable[str] | None = None,
    prefer_jurisdiction: str | None = None,
    cluster: str | None = None,
    doc_types: Iterable[str] | None = None,
    doc_ids: Iterable[str] | None = None,
    expand: bool = True,
    extra_queries: Iterable[str] = (),
    max_per_doc: int | None = None,
) -> list[Hit]:
    """Top-k Hits for a query.

    statuses: allowed document statuses (None = all, e.g. baseline or excluded list).
    jurisdictions: hard filter; prefer_jurisdiction: soft boost ("FEDERAL"/"SARAWAK").
    extra_queries: rewritten queries (e.g. from QUERY_REWRITE); best score per chunk wins.
    """
    index: BM25Index = store.index
    allowed_docs = access.visible_docs(store, user)  # clearance filter: always on
    statuses = set(statuses) if statuses is not None else None
    jurisdictions = set(jurisdictions) if jurisdictions is not None else None
    doc_types = set(doc_types) if doc_types is not None else None
    doc_ids = set(doc_ids) if doc_ids is not None else None

    candidates = []
    for i, chunk in enumerate(index.chunks):
        doc = allowed_docs.get(chunk.doc_id)
        if doc is None:
            continue
        if statuses is not None and doc.status not in statuses:
            continue
        if jurisdictions is not None and doc.jurisdiction not in jurisdictions:
            continue
        if cluster and doc.cluster != cluster:
            continue
        if doc_types is not None and doc.doc_type not in doc_types:
            continue
        if doc_ids is not None and doc.doc_id not in doc_ids:
            continue
        candidates.append(i)
    if not candidates:
        return []

    glossary = getattr(store, "glossary", None)
    queries = [q for q in [query, *extra_queries] if q and q.strip()]
    refs = {r["circular_no"] for q in queries for r in find_refs(q)}
    _, equivalents = query_terms(query, glossary if expand else [])

    best: dict[int, float] = {}
    for q in queries:
        weights, _ = query_terms(q, glossary if expand else [])
        if not weights:
            continue
        cross = {t: 1.0 for t in weights}  # translations count fully for the other language
        q_lang = detect_language(q)
        for i in candidates:
            doc = allowed_docs[index.chunks[i].doc_id]
            is_cross = q_lang in ("ms", "en") and doc.language in ("ms", "en") and doc.language != q_lang
            s = index.bm25(i, cross if is_cross else weights)
            if doc.circular_no and doc.circular_no in refs:
                s = s * CIRCULAR_BOOST + 1.0  # exact circular-number match
            if s <= 0:
                continue
            if prefer_jurisdiction and jurisdiction_matches(doc.jurisdiction, prefer_jurisdiction):
                s *= JURISDICTION_BOOST
            if doc.doc_type in ("minutes", "report"):
                s *= RECORD_PRIOR
            if s > best.get(i, 0.0):
                best[i] = s

    ranked = sorted(best.items(), key=lambda kv: kv[1], reverse=True)
    hits: list[Hit] = []
    per_doc: Counter = Counter()
    for i, score in ranked:
        chunk = index.chunks[i]
        if max_per_doc and per_doc[chunk.doc_id] >= max_per_doc:
            continue
        per_doc[chunk.doc_id] += 1
        tf = index.tfs[i]
        found = [t for t, eq in equivalents.items() if any(e in tf for e in eq)]
        coverage = len(found) / len(equivalents) if equivalents else 0.0
        hits.append(
            Hit(
                chunk=chunk,
                doc=allowed_docs[chunk.doc_id],
                score=round(score, 4),
                rank=len(hits) + 1,
                coverage=round(coverage, 3),
                matched=found,
            )
        )
        if len(hits) >= k:
            break
    return hits


def top_docs(hits: list[Hit], n: int = 5) -> list[str]:
    """Distinct doc_ids in rank order (for Recall@5 / MRR)."""
    return list(dict.fromkeys(h.doc.doc_id for h in hits))[:n]


def citation_from_hit(label: str, hit: Hit, max_chars: int = 300) -> Citation:
    """Build the Citation shown under an answer for passage [label] (e.g. 'S1')."""
    return Citation(
        label=label,
        doc_id=hit.doc.doc_id,
        circular_no=hit.doc.label,
        title=hit.doc.title,
        clause_ref=hit.chunk.clause_ref,
        page=hit.chunk.page_start,
        status=hit.doc.status,
        status_reason=hit.doc.status_reason,
        jurisdiction=hit.doc.jurisdiction,
        snippet=snippet(hit.chunk.text, max_chars),
        chunk_id=hit.chunk.chunk_id,
    )
