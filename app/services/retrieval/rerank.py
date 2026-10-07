"""Reranking of the top fused candidates.

Order of preference (RERANKER=auto):
1. the backend's own reranker (llama-server /v1/rerank, or the fake backend's overlap score);
2. sentence-transformers CrossEncoder BAAI/bge-reranker-v2-m3 if installed and cached locally;
3. cosine similarity between the query embedding and the passage vectors stored in the pack.
"""
from __future__ import annotations

import threading

from app.db import deserialize_f32
from app.services.retrieval.filters import PackHandle
from app.services.retrieval.hybrid import Candidate

_ce = {"model": None, "tried": False}
_ce_lock = threading.Lock()


def _cross_encoder(settings):
    with _ce_lock:
        if not _ce["tried"]:
            _ce["tried"] = True
            try:
                from sentence_transformers import CrossEncoder  # optional dependency

                _ce["model"] = CrossEncoder(settings.rerank_model, max_length=512, local_files_only=True)
            except Exception:  # noqa: BLE001 - not installed or not cached (offline)
                _ce["model"] = None
        return _ce["model"]


def trim(text: str, words: int) -> str:
    parts = text.split()
    return text if len(parts) <= words else " ".join(parts[:words]) + " ..."


def passage_text(c: Candidate) -> str:
    return f"{c.chunk['circular_no']} {c.chunk['title']} | {c.chunk.get('breadcrumb') or ''}\n{c.chunk['text']}"


def rerank(query: str, candidates: list[Candidate], client, settings, handles: list[PackHandle],
           qvec: list[float] | None) -> tuple[list[Candidate], str]:
    pool = candidates[: settings.rerank_candidates]
    if not pool:
        return [], "none"
    kind = settings.reranker
    scores = None
    if kind in ("auto", "backend"):
        try:
            scores = client.rerank(query, [passage_text(c) for c in pool])
        except Exception:  # noqa: BLE001
            scores = None
        if scores is not None:
            kind = "fake" if getattr(client, "name", "") == "fake" else "crossencoder"
    if scores is None and kind in ("auto", "crossencoder"):
        model = _cross_encoder(settings)
        if model is not None:
            import math

            raw = model.predict([(query, passage_text(c)) for c in pool])
            scores = [1 / (1 + math.exp(-float(s))) if not 0 <= float(s) <= 1 else float(s) for s in raw]
            kind = "crossencoder"
    if scores is None and kind in ("auto", "embedding", "crossencoder") and qvec is not None:
        by_tier = {h.tier: h for h in handles}
        scores = []
        for c in pool:
            conn = by_tier[c.tier].conn
            try:
                row = conn.execute("SELECT embedding FROM chunk_vectors WHERE chunk_id = ?", (c.chunk_id,)).fetchone()
            except Exception:  # noqa: BLE001 - packs built before chunk_vectors existed
                row = conn.execute("SELECT embedding FROM vec_chunks WHERE rowid = ?", (c.chunk_id,)).fetchone()
            vec = deserialize_f32(row[0]) if row else None
            scores.append(sum(a * b for a, b in zip(qvec, vec)) if vec else 0.0)
        kind = "embedding"
    if scores is None:
        scores = [c.rrf for c in pool]
        kind = "none"
    for c, s in zip(pool, scores):
        c.score = float(s)
    pool.sort(key=lambda c: (c.score, c.rrf), reverse=True)
    for c in pool:
        c.chunk["text"] = trim(c.chunk["text"], settings.passage_words)
    return pool, kind


def confidence(top: float | None, kind: str, settings) -> str:
    if top is None:
        return "LOW"
    t = settings.confidence_thresholds.get(kind, settings.confidence_thresholds["none"])
    if top >= t["high"]:
        return "HIGH"
    if top >= t["medium"]:
        return "MEDIUM"
    return "LOW"
