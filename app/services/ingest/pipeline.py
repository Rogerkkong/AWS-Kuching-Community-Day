"""Publisher ingestion pipeline: parse -> metadata -> chunks -> embeddings -> relation candidates,
then validity refresh (ground-truth relations, statuses, change summaries)."""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from app.config import Settings
from app.db import DOC_COLUMNS
from app.services.ingest import changes, chunker, embed, metadata, relations
from app.services.ingest.parse import parse_pdf
from app.services.validity import status


class IngestLog:
    def __init__(self, conn: sqlite3.Connection, echo: bool = False):
        self.conn, self.echo, self.file = conn, echo, ""
        self.entries: list[dict] = []

    def __call__(self, level: str, message: str) -> None:
        self.entries.append({"file": self.file, "level": level, "message": message})
        self.conn.execute("INSERT INTO ingestion_log (file_name, level, message) VALUES (?,?,?)",
                          (self.file, level, message))
        if self.echo:
            print(f"[{level}] {self.file}: {message}")


def _rel_path(path: Path, settings: Settings) -> str:
    try:
        return path.resolve().relative_to(settings.repo_root).as_posix()
    except ValueError:
        return str(path.resolve())


def ingest_file(conn: sqlite3.Connection, path: Path, client, settings: Settings, log: IngestLog,
                overrides: dict | None = None, use_llm: bool = True) -> int | None:
    log.file = path.name
    if path.suffix.lower() != ".pdf":
        log("error", "Only PDF files are supported in this prototype.")
        return None
    try:
        pages = parse_pdf(path, log)
    except Exception as exc:  # noqa: BLE001
        log("error", f"Could not read PDF: {exc}")
        return None
    if not any(p.text.strip() for p in pages):
        log("error", "No text found on any page (OCR unavailable or failed).")
        return None
    ocr_pages = [p.number for p in pages if p.ocr]
    if ocr_pages:
        log("info", f"OCR used on pages {ocr_pages}")

    meta, notes = metadata.extract_metadata(pages, path.name, client=client, overrides=overrides, use_llm=use_llm)
    for n in notes:
        log("info", n)
    row = {c: meta.get(c) for c in DOC_COLUMNS if c not in ("id", "status", "status_reason", "owner_verified", "updated_at")}
    row["file_path"] = _rel_path(path, settings)
    row["updated_at"] = datetime.now().isoformat(timespec="seconds")

    existing = conn.execute("SELECT id FROM documents WHERE circular_no = ?", (meta["circular_no"],)).fetchone()
    if existing:
        doc_id = existing[0]
        sets = ", ".join(f"{k} = ?" for k in row)
        conn.execute(f"UPDATE documents SET {sets} WHERE id = ?", (*row.values(), doc_id))
        conn.execute("DELETE FROM chunks WHERE document_id = ?", (doc_id,))
        conn.execute("DELETE FROM relations WHERE source_doc_id = ? AND verified = 0", (doc_id,))
        conn.execute("DELETE FROM change_summaries WHERE old_doc_id = ? OR new_doc_id = ?", (doc_id, doc_id))
        log("info", f"Re-ingested existing document {meta['circular_no']}")
    else:
        cols = ", ".join(row)
        cur = conn.execute(f"INSERT INTO documents ({cols}, status) VALUES ({', '.join('?' * len(row))}, 'UNKNOWN')",
                           tuple(row.values()))
        doc_id = cur.lastrowid

    chunks = chunker.chunk_document(pages, meta)
    conn.executemany(
        """INSERT INTO chunks (document_id, chunk_index, clause_ref, breadcrumb, page_start, page_end, text, ocr)
           VALUES (?,?,?,?,?,?,?,?)""",
        [(doc_id, c.chunk_index, c.clause_ref, c.breadcrumb, c.page_start, c.page_end, c.text, int(c.ocr)) for c in chunks])
    chunk_ids = [r[0] for r in conn.execute("SELECT id FROM chunks WHERE document_id = ?", (doc_id,))]
    try:
        n = embed.embed_chunks(conn, client, chunk_ids)
        log("info", f"{meta['circular_no']} ({meta['doc_type']}): {len(chunks)} chunks, {n} embeddings")
    except Exception as exc:  # noqa: BLE001
        log("error", f"Embedding failed ({exc}); document stored without vectors")

    if meta.get("doc_type") not in ("minutes", "report"):
        cands = relations.find_candidates(pages, meta["circular_no"])
        if cands:
            classified = relations.classify(cands, meta, client if use_llm else None)
            added = relations.store_extracted(conn, doc_id, classified)
            log("info", f"{added} relation candidate(s) queued for verification")
    conn.commit()
    return doc_id


def refresh_validity(conn: sqlite3.Connection, client, settings: Settings, log: IngestLog | None = None,
                     load_ground_truth: bool = True) -> None:
    relations.resolve_targets(conn)
    if load_ground_truth:
        n = relations.load_ground_truth(conn, settings.ground_truth_dir / "relations.csv")
        if log and n:
            log.file = "relations.csv"
            log("info", f"{n} verified relation(s) loaded from data/relations.csv")
    # Drop summaries whose relation is no longer verified.
    conn.execute("""DELETE FROM change_summaries WHERE NOT EXISTS (
                      SELECT 1 FROM relations r WHERE r.verified = 1 AND r.relation_type IN ('SUPERSEDES','AMENDS')
                      AND r.source_doc_id = change_summaries.new_doc_id AND r.target_doc_id = change_summaries.old_doc_id)""")
    status.recompute_all(conn)
    made = changes.build_change_summaries(conn, client)
    if log and made:
        log.file = "change_summaries"
        log("info", f"{made} change summary(ies) generated")
    conn.commit()


def ingest_paths(conn: sqlite3.Connection, paths: list[Path], client, settings: Settings, echo: bool = False,
                 use_llm: bool = True) -> IngestLog:
    log = IngestLog(conn, echo)
    overrides = metadata.load_overrides(settings.ground_truth_dir / "metadata.csv")
    for p in paths:
        ingest_file(conn, p, client, settings, log, overrides, use_llm)
    refresh_validity(conn, client, settings, log)
    return log
