"""Access control and validity filters (rules 3 and 4).

Clearance decides which installed packs are opened at all; inside each pack every query that returns
documents or chunks also carries `classification_level <= :clearance`.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from app import db
from app.config import DEFAULT_STATUSES, HISTORICAL_STATUSES, TIERS

ALL_STATUSES = DEFAULT_STATUSES + HISTORICAL_STATUSES


@dataclass
class PackHandle:
    tier: int
    version: int
    path: Path
    conn: sqlite3.Connection
    embedding_model: str


def allowed_tiers(clearance: int) -> list[int]:
    return [t for t in sorted(TIERS) if t <= clearance]


def allowed_statuses(include_historical: bool = False, wants_history: bool = False) -> tuple[str, ...]:
    return ALL_STATUSES if (include_historical or wants_history) else DEFAULT_STATUSES


def status_clause(statuses: tuple[str, ...], alias: str = "d") -> tuple[str, list]:
    return f"{alias}.status IN ({','.join('?' * len(statuses))})", list(statuses)


@contextmanager
def open_packs(state, user: dict) -> Iterator[tuple[list[PackHandle], list[dict]]]:
    """Open only the packs the user's clearance allows, read-only, with sqlite-vec loaded.
    Yields (handles, warnings); packs with a different embedding model are refused (rule 8)."""
    from app.services.packs.install import installed_packs

    clearance = int(user["clearance_level"])
    handles: list[PackHandle] = []
    warnings: list[dict] = []
    with state.lock:
        try:
            for row in installed_packs(state):
                if row["tier"] not in allowed_tiers(clearance):
                    continue  # never opened for this user
                conn = db.connect(row["file_path"], vec=True, readonly=True)
                manifest = dict(conn.execute("SELECT * FROM manifest LIMIT 1").fetchone())
                if manifest["embedding_model"] != state.settings.embedding_model_id:
                    conn.close()
                    warnings.append({"code": "embedding_model_mismatch", "tier": row["tier"],
                                     "message": f"Pek {TIERS[row['tier']].upper()} v{row['version']} dibina dengan model "
                                                f"'{manifest['embedding_model']}', tetapi aplikasi ini menggunakan "
                                                f"'{state.settings.embedding_model_id}'. Pek ini tidak dicari. / "
                                                f"This pack was built with a different embedding model and is not searched."})
                    continue
                handles.append(PackHandle(row["tier"], row["version"], Path(row["file_path"]), conn,
                                          manifest["embedding_model"]))
            yield handles, warnings
        finally:
            for h in handles:
                h.conn.close()


def fetch_documents(handles: list[PackHandle], clearance: int, where: str = "1=1", params: list | None = None) -> list[dict]:
    out = []
    for h in handles:
        out += db.rows(h.conn.execute(
            f"SELECT d.*, {h.tier} AS pack_tier FROM documents d WHERE d.classification_level <= ? AND ({where})",
            [clearance, *(params or [])]))
    return out


def fetch_document(handles: list[PackHandle], clearance: int, doc_id: int) -> tuple[dict, PackHandle] | None:
    for h in handles:
        row = h.conn.execute("SELECT d.* FROM documents d WHERE d.id = ? AND d.classification_level <= ?",
                             (doc_id, clearance)).fetchone()
        if row:
            return dict(row), h
    return None
