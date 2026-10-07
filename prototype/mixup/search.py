"""Keyword search (BM25) with bilingual query expansion and optional Titan embeddings.

BM25 is a classic ranking formula: a chunk scores higher when it contains rare
query words, several times, and is not too long. We implement it ourselves (no
extra dependencies) and add:
  * query expansion BM<->EN (textutil.expand_query)
  * a small boost when query words hit the document's title/number/tags
  * optional hybrid scoring with Amazon Titan Text Embeddings V2 (MIXUP_EMBEDDINGS=on)
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Iterable

from .config import Settings
from .models import STATUS_SUPERSEDED, Chunk, DocMeta, SearchHit
from .textutil import expand_query, tokenize

K1 = 1.5
B = 0.75


class BedrockEmbedder:
    """Amazon Titan Text Embeddings V2 via boto3 (an AWS model, not Claude).

    Embeddings are cached on disk by text hash, so each chunk is embedded once.
    """

    def __init__(self, settings: Settings, client=None):
        import boto3

        self.model_id = settings.embed_model
        if client is None:
            session = boto3.Session(profile_name=settings.aws_profile) if settings.aws_profile else boto3.Session()
            client = session.client("bedrock-runtime", region_name=settings.aws_region)
        self._client = client
        self._cache_file = Path(settings.cache_dir) / "embeddings" / f"{self.model_id.replace(':', '_')}.json"
        try:
            self._cache: dict[str, list[float]] = json.loads(self._cache_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self._cache = {}
        self._dirty = False

    def embed(self, text: str) -> list[float]:
        key = hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]
        if key not in self._cache:
            resp = self._client.invoke_model(
                modelId=self.model_id,
                body=json.dumps({"inputText": text[:8000], "dimensions": 512, "normalize": True}),
            )
            self._cache[key] = json.loads(resp["body"].read())["embedding"]
            self._dirty = True
        return self._cache[key]

    def save(self) -> None:
        if not self._dirty:
            return
        try:
            self._cache_file.parent.mkdir(parents=True, exist_ok=True)
            self._cache_file.write_text(json.dumps(self._cache), encoding="utf-8")
            self._dirty = False
        except OSError:
            pass


def make_embedder(settings: Settings):
    """Return a BedrockEmbedder when MIXUP_EMBEDDINGS=on and not offline, else None."""
    if not settings.embeddings or settings.offline:
        return None
    try:
        return BedrockEmbedder(settings)
    except Exception:
        return None


class Index:
    """In-memory search index over chunks.

    docs is the shared {doc_id: DocMeta} dict (status changes are seen immediately).
    embedder is optional: any object with .embed(text) -> list[float].
    """

    def __init__(self, chunks: Iterable[Chunk], docs: dict[str, DocMeta], embedder=None):
        self.docs = docs
        self.embedder = embedder
        self.embed_error: str | None = None
        self.chunks: list[Chunk] = []
        self._tfs: list[Counter] = []
        self._lens: list[int] = []
        self._df: Counter = Counter()
        self._avgdl = 1.0
        self._vectors: list = []  # numpy arrays when embeddings are on
        self.add_chunks(chunks)

    # -- building ---------------------------------------------------------------

    def _field_text(self, chunk: Chunk) -> str:
        doc = self.docs.get(chunk.doc_id)
        title = doc.title if doc else ""
        return f"{title}\n{chunk.heading}\n{chunk.text}"

    def _meta_tokens(self, doc: DocMeta | None) -> set[str]:
        if doc is None:
            return set()
        return set(tokenize(f"{doc.title} {doc.number} {doc.doc_id} {' '.join(doc.tags)}"))

    def add_chunks(self, chunks: Iterable[Chunk]) -> None:
        """Add chunks (e.g. from an uploaded document) and refresh statistics."""
        new = list(chunks)
        for chunk in new:
            tf = Counter(tokenize(self._field_text(chunk)))
            self.chunks.append(chunk)
            self._tfs.append(tf)
            self._lens.append(sum(tf.values()))
            self._df.update(tf.keys())
        self._avgdl = (sum(self._lens) / len(self._lens)) if self._lens else 1.0
        if self.embedder is not None and new:
            self._embed_chunks(new)

    def _embed_chunks(self, chunks: list[Chunk]) -> None:
        try:
            import numpy as np

            for chunk in chunks:
                self._vectors.append(np.asarray(self.embedder.embed(self._field_text(chunk)), dtype=float))
            if hasattr(self.embedder, "save"):
                self.embedder.save()
        except Exception as exc:  # embeddings are a bonus; BM25 keeps working
            self.embed_error = f"Embeddings disabled: {type(exc).__name__}"
            self.embedder = None
            self._vectors = []

    # -- scoring ----------------------------------------------------------------

    def _bm25(self, i: int, q_tokens: list[str]) -> float:
        tf = self._tfs[i]
        n = len(self.chunks)
        dl = self._lens[i] or 1
        score = 0.0
        for tok in q_tokens:
            f = tf.get(tok, 0)
            if not f:
                continue
            df = self._df.get(tok, 0)
            idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
            score += idf * (f * (K1 + 1)) / (f + K1 * (1 - B + B * dl / self._avgdl))
        return score

    def search(
        self,
        queries: str | list[str],
        k: int = 8,
        include_superseded: bool = True,
        doc_ids: Iterable[str] | None = None,
        doc_types: Iterable[str] | None = None,
        expand: bool = True,
    ) -> list[SearchHit]:
        """Return the top-k chunks for one query (or the best score over several queries).

        include_superseded=False hides superseded documents.
        doc_ids / doc_types restrict the search to some documents.
        expand=True adds BM<->EN glossary translations to each query.
        """
        if isinstance(queries, str):
            queries = [queries]
        allowed_ids = set(doc_ids) if doc_ids is not None else None
        allowed_types = set(doc_types) if doc_types is not None else None

        candidates = []
        for i, chunk in enumerate(self.chunks):
            doc = self.docs.get(chunk.doc_id)
            if doc is None:
                continue
            if not include_superseded and doc.status == STATUS_SUPERSEDED:
                continue
            if allowed_ids is not None and doc.doc_id not in allowed_ids:
                continue
            if allowed_types is not None and doc.doc_type not in allowed_types:
                continue
            candidates.append(i)
        if not candidates:
            return []

        best: dict[int, float] = {}
        for query in queries:
            q_text = expand_query(query) if expand else query
            q_tokens = list(dict.fromkeys(tokenize(q_text)))  # unique, keep order
            if not q_tokens:
                continue
            q_set = set(q_tokens)
            raw = {}
            meta_cache: dict[str, set[str]] = {}
            for i in candidates:
                s = self._bm25(i, q_tokens)
                if s <= 0:
                    continue
                doc_id = self.chunks[i].doc_id
                if doc_id not in meta_cache:
                    meta_cache[doc_id] = self._meta_tokens(self.docs.get(doc_id))
                meta = meta_cache[doc_id]
                overlap = len(q_set & meta) / len(q_set)
                raw[i] = s * (1 + 0.3 * overlap)
            scores = self._hybrid(query, raw, candidates)
            for i, s in scores.items():
                if s > best.get(i, 0.0):
                    best[i] = s

        ranked = sorted(best.items(), key=lambda kv: kv[1], reverse=True)[:k]
        return [SearchHit(chunk=self.chunks[i], score=round(s, 4), doc=self.docs[self.chunks[i].doc_id]) for i, s in ranked]

    def _hybrid(self, query: str, bm25: dict[int, float], candidates: list[int]) -> dict[int, float]:
        """Blend BM25 with cosine similarity when embeddings are available."""
        if self.embedder is None or len(self._vectors) != len(self.chunks):
            return bm25
        try:
            import numpy as np

            q = np.asarray(self.embedder.embed(query), dtype=float)
            top = max(bm25.values()) if bm25 else 1.0
            out = {}
            for i in candidates:
                v = self._vectors[i]
                cos = float(np.dot(q, v) / ((np.linalg.norm(q) * np.linalg.norm(v)) or 1.0))
                out[i] = 0.5 * (bm25.get(i, 0.0) / top) + 0.5 * max(cos, 0.0)
            return {i: s for i, s in out.items() if s > 0.05}
        except Exception as exc:
            self.embed_error = f"Embeddings disabled: {type(exc).__name__}"
            self.embedder = None
            return bm25

