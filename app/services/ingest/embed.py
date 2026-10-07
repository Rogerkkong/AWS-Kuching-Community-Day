"""Embeddings for chunks (Publisher). Vectors are L2-normalised float32 blobs in chunk_vectors."""
from __future__ import annotations

import sqlite3

from app.db import serialize_f32


def embedding_text(chunk: dict, title: str | None = None) -> str:
    """What gets embedded: the breadcrumb gives short clauses their document/heading context."""
    head = chunk.get("breadcrumb") or ""
    if title:
        head = f"{title} | {head}"
    return f"{head}\n{chunk['text']}"


def embed_chunks(conn: sqlite3.Connection, client, chunk_ids: list[int] | None = None, batch: int = 16) -> int:
    sql = """SELECT c.id, c.text, c.breadcrumb, d.title FROM chunks c JOIN documents d ON d.id = c.document_id
             WHERE c.id NOT IN (SELECT chunk_id FROM chunk_vectors)"""
    params: tuple = ()
    if chunk_ids:
        sql += f" AND c.id IN ({','.join('?' * len(chunk_ids))})"
        params = tuple(chunk_ids)
    pending = [dict(r) for r in conn.execute(sql, params)]
    for i in range(0, len(pending), batch):
        part = pending[i:i + batch]
        vectors = client.embed([embedding_text(c, c["title"]) for c in part])
        conn.executemany("INSERT OR REPLACE INTO chunk_vectors (chunk_id, embedding) VALUES (?, ?)",
                         [(c["id"], serialize_f32(v)) for c, v in zip(part, vectors)])
    conn.commit()
    return len(pending)
