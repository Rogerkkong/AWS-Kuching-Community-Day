"""Knowledge-pack builder (Publisher). One read-only SQLite file per clearance tier."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app import db
from app.config import TIERS, Settings
from app.services.packs.sign import sha256_file, sign_digest


def read_manifest(dist: Path) -> dict:
    path = dist / "manifest.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"publisher": "Pekeliling Navigator Publisher", "packs": []}


def latest_versions(manifest: dict) -> dict[int, int]:
    out: dict[int, int] = {}
    for p in manifest.get("packs", []):
        out[p["tier"]] = max(out.get(p["tier"], 0), int(p["version"]))
    return out


def _levels(pub: sqlite3.Connection) -> dict[int, int]:
    return {r[0]: r[1] for r in pub.execute("SELECT id, classification_level FROM documents")}


def build_tier(pub: sqlite3.Connection, settings: Settings, tier: int, version: int, previous: int | None,
               out_path: Path) -> dict:
    levels = _levels(pub)
    docs = db.rows(pub.execute("SELECT * FROM documents WHERE classification_level = ? ORDER BY id", (tier,)))
    doc_ids = [d["id"] for d in docs]
    if out_path.exists():
        out_path.unlink()
    tmp = out_path.with_suffix(".building")
    if tmp.exists():
        tmp.unlink()
    pack = db.connect(tmp, vec=True)
    pack.executescript(db.PACK_SQL)
    pack.execute(f"CREATE VIRTUAL TABLE vec_chunks USING vec0(embedding float[{settings.embed_dim}])")

    # Status reasons must not reveal higher-tier documents to this tier.
    hidden_sources = {r[0]: r[1] for r in pub.execute(
        """SELECT r.target_doc_id, s.circular_no FROM relations r JOIN documents s ON s.id = r.source_doc_id
           WHERE r.verified = 1 AND s.classification_level > ?""", (tier,))}
    for d in docs:
        if d["id"] in hidden_sources and d.get("status_reason") and hidden_sources[d["id"]] in d["status_reason"]:
            d["status_reason"] = d["status_reason"].replace(hidden_sources[d["id"]], "dokumen bertaraf keselamatan lebih tinggi")
    _insert(pack, "documents", db.DOC_COLUMNS, docs)

    chunks = []
    if doc_ids:
        q = ",".join("?" * len(doc_ids))
        chunks = db.rows(pub.execute(f"SELECT * FROM chunks WHERE document_id IN ({q}) ORDER BY id", doc_ids))
        _insert(pack, "chunks", db.CHUNK_COLUMNS, chunks)
        vecs = pub.execute(f"""SELECT v.chunk_id, v.embedding FROM chunk_vectors v JOIN chunks c ON c.id = v.chunk_id
                               WHERE c.document_id IN ({q})""", doc_ids).fetchall()
        for chunk_id, blob in vecs:
            if len(blob) != settings.embed_dim * 4:
                raise ValueError(f"Chunk {chunk_id} vector has {len(blob) // 4} dims, expected {settings.embed_dim}")
            pack.execute("INSERT INTO vec_chunks (rowid, embedding) VALUES (?, ?)", (chunk_id, blob))
        missing = len(chunks) - len(vecs)
        if missing:
            raise ValueError(f"{missing} chunk(s) in tier {tier} have no embedding; re-run ingestion")

    def visible(*ids) -> bool:
        lv = [levels.get(i) for i in ids if i is not None]
        return all(v is not None and v <= tier for v in lv) and any(v == tier for v in lv)

    rels = [r for r in db.rows(pub.execute("SELECT * FROM relations WHERE verified = 1"))
            if visible(r["source_doc_id"], r["target_doc_id"])]
    _insert(pack, "relations", db.RELATION_COLUMNS, rels)
    sums = [s for s in db.rows(pub.execute("SELECT * FROM change_summaries"))
            if visible(s["old_doc_id"], s["new_doc_id"])]
    _insert(pack, "change_summaries", db.SUMMARY_COLUMNS, sums)

    for d in docs:
        pdf = None
        if d.get("file_path"):
            p = Path(d["file_path"])
            p = p if p.is_absolute() else settings.repo_root / p
            if p.exists():
                pdf = p.read_bytes()
        pack.execute("INSERT INTO files (document_id, pdf) VALUES (?, ?)", (d["id"], pdf))

    pack.execute("INSERT INTO chunks_fts (rowid, text) SELECT id, text FROM chunks")
    pack.execute("INSERT INTO docs_trgm (rowid, circular_no, title) SELECT id, circular_no, title FROM documents")
    created = datetime.now(timezone.utc).isoformat(timespec="seconds")
    pack.execute("INSERT INTO manifest VALUES (?,?,?,?,?,?,?,?)",
                 (f"pn-{TIERS[tier]}-v{version}", tier, version, created, settings.embedding_model_id,
                  settings.embed_dim, len(docs), previous))
    pack.commit()
    pack.execute("VACUUM")
    pack.close()
    tmp.replace(out_path)
    return {"tier": tier, "version": version, "created_at": created, "documents": len(docs),
            "chunks": len(chunks), "relations": len(rels), "change_summaries": len(sums)}


def _insert(conn: sqlite3.Connection, table: str, columns: list[str], items: list[dict]) -> None:
    if not items:
        return
    conn.executemany(f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join('?' * len(columns))})",
                     [tuple(i.get(c) for c in columns) for i in items])


def build_packs(settings: Settings, version: int, tiers: list[int] | None = None, force: bool = False,
                log=print) -> list[dict]:
    if not settings.private_key_path.exists():
        raise FileNotFoundError("Publisher private key not found; run scripts/make_keys.py first")
    dist = settings.dist_packs_dir
    dist.mkdir(parents=True, exist_ok=True)
    manifest = read_manifest(dist)
    latest = latest_versions(manifest)
    pub = db.connect(settings.publisher_db, vec=True)
    try:
        present = sorted({r[0] for r in pub.execute("SELECT DISTINCT classification_level FROM documents")})
        tiers = tiers if tiers is not None else present
        entries = []
        for tier in tiers:
            if tier not in TIERS:
                continue
            prev = latest.get(tier)
            if prev is not None and version <= prev and not force:
                raise ValueError(f"Version {version} must be greater than the latest {TIERS[tier]} pack (v{prev})")
            name = f"pack-{TIERS[tier]}-v{version}.sqlite"
            out = dist / name
            stats = build_tier(pub, settings, tier, version, prev, out)
            digest = sha256_file(out)
            signature = sign_digest(settings.private_key_path, digest)
            entry = {"tier": tier, "tier_name": TIERS[tier].upper(), "version": version, "file": name,
                     "sha256": digest, "signature": signature, "embedding_model": settings.embedding_model_id,
                     "embedding_dim": settings.embed_dim, "created_at": stats["created_at"],
                     "size_bytes": out.stat().st_size, "previous_version": prev,
                     "documents": stats["documents"]}
            (dist / f"{name}.sig.json").write_text(json.dumps(entry, indent=2), encoding="utf-8")
            manifest["packs"] = [p for p in manifest["packs"] if not (p["tier"] == tier and p["version"] == version)]
            manifest["packs"].append(entry)
            entries.append({**entry, **stats})
            log(f"Built {name}: {stats['documents']} documents, {stats['chunks']} chunks, "
                f"{stats['relations']} relations, sha256 {digest[:12]}...")
        manifest["packs"].sort(key=lambda p: (p["tier"], p["version"]))
        manifest["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        (dist / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return entries
    finally:
        pub.close()
