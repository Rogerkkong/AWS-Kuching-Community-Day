"""SQLite helpers and schemas for publisher.db, knowledge packs and app.db."""
from __future__ import annotations

import sqlite3
import struct
from pathlib import Path
from typing import Iterable, Sequence

import sqlite_vec

MIN_SQLITE = (3, 34, 0)


def check_sqlite_version() -> None:
    if sqlite3.sqlite_version_info < MIN_SQLITE:
        raise RuntimeError(f"SQLite {sqlite3.sqlite_version} is too old; need >= 3.34 (trigram tokenizer).")


def _load_vec(conn: sqlite3.Connection) -> None:
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)


def connect(path: Path | str, *, vec: bool = False, readonly: bool = False) -> sqlite3.Connection:
    check_sqlite_version()
    if readonly:
        uri = Path(path).resolve().as_uri() + "?mode=ro"
        conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
    else:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    if vec:
        _load_vec(conn)
    return conn


def serialize_f32(vector: Sequence[float]) -> bytes:
    return struct.pack(f"{len(vector)}f", *vector)


def deserialize_f32(blob: bytes) -> list[float]:
    return list(struct.unpack(f"{len(blob) // 4}f", blob))


def rows(cur: Iterable[sqlite3.Row]) -> list[dict]:
    return [dict(r) for r in cur]


# --------------------------------------------------------------------------------------------------
# Shared document tables (publisher.db and packs use the same columns so rows copy 1:1)
# --------------------------------------------------------------------------------------------------
DOC_COLUMNS = [
    "id", "circular_no", "series", "title", "issuer", "doc_type", "jurisdiction", "cluster",
    "issue_date", "effective_date", "expiry_date", "one_off", "classification_level", "language",
    "applicability", "source_url", "file_path", "status", "status_reason", "owner_verified", "updated_at",
]
CHUNK_COLUMNS = ["id", "document_id", "chunk_index", "clause_ref", "breadcrumb", "page_start",
                 "page_end", "text", "ocr"]
RELATION_COLUMNS = ["id", "source_doc_id", "target_doc_id", "target_ref_text", "relation_type", "scope",
                    "effective_date", "evidence_text", "evidence_page", "confidence", "verified"]
SUMMARY_COLUMNS = ["id", "old_doc_id", "new_doc_id", "diff_json", "summary_ms", "summary_en"]

DOCS_SQL = """
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY,
    circular_no TEXT NOT NULL,
    series TEXT DEFAULT 'OTHER',
    title TEXT,
    issuer TEXT,
    doc_type TEXT DEFAULT 'circular',
    jurisdiction TEXT DEFAULT 'UNKNOWN',
    cluster TEXT,
    issue_date TEXT,
    effective_date TEXT,
    expiry_date TEXT,
    one_off INTEGER DEFAULT 0,
    classification_level INTEGER NOT NULL DEFAULT 0,
    language TEXT,
    applicability TEXT,
    source_url TEXT,
    file_path TEXT,
    status TEXT DEFAULT 'UNKNOWN',
    status_reason TEXT,
    owner_verified INTEGER DEFAULT 0,
    updated_at TEXT
);
CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    clause_ref TEXT,
    breadcrumb TEXT,
    page_start INTEGER,
    page_end INTEGER,
    text TEXT NOT NULL,
    ocr INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(document_id);
CREATE TABLE IF NOT EXISTS relations (
    id INTEGER PRIMARY KEY,
    source_doc_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    target_doc_id INTEGER REFERENCES documents(id) ON DELETE SET NULL,
    target_ref_text TEXT,
    relation_type TEXT NOT NULL,
    scope TEXT,
    effective_date TEXT,
    evidence_text TEXT,
    evidence_page INTEGER,
    confidence REAL,
    verified INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS change_summaries (
    id INTEGER PRIMARY KEY,
    old_doc_id INTEGER NOT NULL,
    new_doc_id INTEGER NOT NULL,
    diff_json TEXT,
    summary_ms TEXT,
    summary_en TEXT
);
"""

PUBLISHER_SQL = DOCS_SQL + """
CREATE UNIQUE INDEX IF NOT EXISTS idx_docs_no ON documents(circular_no);
CREATE TABLE IF NOT EXISTS chunk_vectors (
    chunk_id INTEGER PRIMARY KEY REFERENCES chunks(id) ON DELETE CASCADE,
    embedding BLOB NOT NULL
);
CREATE TABLE IF NOT EXISTS usage_reports (
    id INTEGER PRIMARY KEY,
    imported_at TEXT,
    payload_json TEXT
);
CREATE TABLE IF NOT EXISTS ingestion_log (
    id INTEGER PRIMARY KEY,
    created_at TEXT DEFAULT (datetime('now')),
    file_name TEXT,
    level TEXT,
    message TEXT
);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
"""

PACK_SQL = DOCS_SQL + """
CREATE TABLE IF NOT EXISTS manifest (
    pack_id TEXT, tier INTEGER, version INTEGER, created_at TEXT, embedding_model TEXT,
    embedding_dim INTEGER, document_count INTEGER, previous_version INTEGER
);
CREATE TABLE IF NOT EXISTS files (document_id INTEGER PRIMARY KEY, pdf BLOB);
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    text, content='chunks', content_rowid='id', tokenize='unicode61 remove_diacritics 2'
);
CREATE VIRTUAL TABLE IF NOT EXISTS docs_trgm USING fts5(circular_no, title, tokenize='trigram');
"""

APP_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY, name TEXT, role TEXT, clearance_level INTEGER, jurisdiction TEXT,
    grade TEXT, scheme TEXT
);
CREATE TABLE IF NOT EXISTS installed_packs (
    tier INTEGER PRIMARY KEY, version INTEGER, file_path TEXT, sha256 TEXT, embedding_model TEXT,
    installed_at TEXT, previous_file_path TEXT, previous_version INTEGER
);
CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY, user_id INTEGER, cluster TEXT, circular_no TEXT
);
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY, user_id INTEGER, circular_no TEXT, change_type TEXT, summary_ms TEXT,
    summary_en TEXT, pack_version INTEGER, read INTEGER DEFAULT 0, created_at TEXT,
    document_id INTEGER, related_doc_id INTEGER, tier INTEGER
);
CREATE TABLE IF NOT EXISTS query_logs (
    id INTEGER PRIMARY KEY, user_id INTEGER, query TEXT, rewritten_json TEXT, retrieved_ids TEXT,
    excluded_ids TEXT, answerable INTEGER, top_score REAL, confidence TEXT, latency_ms INTEGER,
    feedback TEXT, created_at TEXT, topic TEXT, cluster TEXT, sources_ms INTEGER
);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
"""

DEMO_USERS = [
    # id, name, role, clearance, jurisdiction, grade, scheme
    (1, "Aina binti Ahmad", "OFFICER", 0, "FEDERAL", "N41", "Pegawai Tadbir (Perkhidmatan Persekutuan)"),
    (2, "Jason anak Ling", "OFFICER", 0, "SARAWAK", "N41", "Pegawai Tadbir Negeri Sarawak"),
    (3, "Aminah binti Yusof", "OFFICER", 1, "FEDERAL", "M41", "Pegawai Tadbir dan Diplomatik"),
    (4, "Faizal bin Hassan", "PUBLISHER", 1, "FEDERAL", "N48", "Pentadbir Pengetahuan (Ibu Pejabat)"),
]
DEMO_SUBSCRIPTIONS = [
    (1, "cuti", None), (1, "elaun", None),
    (2, "cuti", None), (2, "elaun", None),
    (3, "cuti", None), (3, "elaun", None), (3, "keselamatan", None),
]


def init_publisher_db(path: Path) -> sqlite3.Connection:
    conn = connect(path)
    conn.executescript(PUBLISHER_SQL)
    conn.commit()
    return conn


def init_app_db(path: Path) -> sqlite3.Connection:
    conn = connect(path)
    conn.executescript(APP_SQL)
    if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        conn.executemany("INSERT INTO users VALUES (?,?,?,?,?,?,?)", DEMO_USERS)
        conn.executemany("INSERT INTO subscriptions (user_id, cluster, circular_no) VALUES (?,?,?)",
                         DEMO_SUBSCRIPTIONS)
        conn.execute("INSERT OR REPLACE INTO settings VALUES ('current_user_id', '1')")
        conn.execute("INSERT OR REPLACE INTO settings VALUES ('ui_language', 'ms')")
    conn.commit()
    return conn


def get_setting(conn: sqlite3.Connection, key: str, default: str | None = None) -> str | None:
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row[0] if row else default


def set_setting(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
