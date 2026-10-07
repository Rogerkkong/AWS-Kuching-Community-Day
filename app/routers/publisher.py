"""Publisher-mode endpoints: upload + ingestion, relation verification, metadata editing, pack build,
usage-report import and the analytics dashboard. Mounted only with --mode publisher."""
from __future__ import annotations

import json
import re
from contextlib import contextmanager
from datetime import datetime
from typing import Iterator, Literal

from fastapi import APIRouter, File, Request, UploadFile
from pydantic import BaseModel

from app import db
from app.services.analytics.export import validate_report
from app.services.analytics.gaps import dashboard
from app.services.inference.client import get_client
from app.services.ingest import pipeline
from app.services.packs.build import build_packs, latest_versions, read_manifest

router = APIRouter(prefix="/api/publisher", tags=["publisher"])

EDITABLE = {"circular_no", "series", "title", "issuer", "doc_type", "jurisdiction", "cluster", "issue_date",
            "effective_date", "expiry_date", "one_off", "classification_level", "language", "applicability",
            "source_url"}


@contextmanager
def pub_db(st) -> Iterator:
    conn = db.init_publisher_db(st.settings.publisher_db)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


@router.get("/documents")
def documents(request: Request) -> dict:
    st = request.app.state.pn
    with pub_db(st) as conn:
        docs = db.rows(conn.execute(
            """SELECT d.*, (SELECT COUNT(*) FROM chunks c WHERE c.document_id = d.id) AS chunk_count,
                      (SELECT COUNT(*) FROM chunk_vectors v JOIN chunks c ON c.id = v.chunk_id WHERE c.document_id = d.id) AS vector_count,
                      (SELECT MAX(ocr) FROM chunks c WHERE c.document_id = d.id) AS has_ocr
               FROM documents d ORDER BY d.issue_date DESC"""))
    return {"documents": docs}


@router.get("/log")
def ingestion_log(request: Request, limit: int = 100) -> dict:
    st = request.app.state.pn
    with pub_db(st) as conn:
        return {"log": db.rows(conn.execute("SELECT * FROM ingestion_log ORDER BY id DESC LIMIT ?", (limit,)))}


@router.post("/upload")
async def upload(request: Request, files: list[UploadFile] = File(...)) -> dict:
    st = request.app.state.pn
    st.settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    saved = []
    for f in files:
        name = re.sub(r"[^\w.\-]+", "_", f.filename or "upload.pdf")
        dest = st.settings.uploads_dir / name
        dest.write_bytes(await f.read())
        saved.append(dest)
    with pub_db(st) as conn:
        log = pipeline.ingest_paths(conn, saved, get_client(), st.settings)
    return {"log": log.entries, "files": [p.name for p in saved]}


@router.get("/relations")
def relations(request: Request, verified: str | None = None) -> dict:
    st = request.app.state.pn
    where = "1=1"
    if verified in ("false", "0"):
        where = "r.verified = 0"
    elif verified in ("true", "1"):
        where = "r.verified = 1"
    with pub_db(st) as conn:
        rows = db.rows(conn.execute(
            f"""SELECT r.*, s.circular_no AS source_no, s.title AS source_title, s.jurisdiction AS source_jurisdiction,
                       s.file_path AS source_file, t.circular_no AS target_no, t.title AS target_title, t.status AS target_status
                FROM relations r JOIN documents s ON s.id = r.source_doc_id LEFT JOIN documents t ON t.id = r.target_doc_id
                WHERE {where} ORDER BY r.verified, r.id DESC"""))
    effect = {"CANCELS": "CANCELLED", "SUPERSEDES": "CANCELLED", "AMENDS": "AMENDED", "REFERENCES": None}
    for r in rows:
        r["effect"] = effect.get(r["relation_type"])
    return {"relations": rows}


class VerifyBody(BaseModel):
    action: Literal["approve", "reject", "edit", "reset"]
    relation_type: Literal["CANCELS", "SUPERSEDES", "AMENDS", "REFERENCES"] | None = None
    target_ref_text: str | None = None
    scope: str | None = None
    effective_date: str | None = None


@router.post("/relations/{rel_id}/verify")
def verify_relation(rel_id: int, body: VerifyBody, request: Request) -> dict:
    st = request.app.state.pn
    with pub_db(st) as conn:
        if conn.execute("SELECT 1 FROM relations WHERE id = ?", (rel_id,)).fetchone() is None:
            raise LookupError("Relation not found")
        if body.action == "edit":
            sets, params = [], []
            for key in ("relation_type", "target_ref_text", "scope", "effective_date"):
                value = getattr(body, key)
                if value is not None:
                    sets.append(f"{key} = ?")
                    params.append(value or None)
            if sets:
                conn.execute(f"UPDATE relations SET {', '.join(sets)} WHERE id = ?", (*params, rel_id))
                conn.execute("UPDATE relations SET target_doc_id = (SELECT id FROM documents WHERE circular_no = relations.target_ref_text) WHERE id = ?", (rel_id,))
        elif body.action == "approve":
            conn.execute("UPDATE relations SET verified = 1 WHERE id = ?", (rel_id,))
        elif body.action == "reject":
            conn.execute("UPDATE relations SET verified = -1 WHERE id = ?", (rel_id,))
        else:
            conn.execute("UPDATE relations SET verified = 0 WHERE id = ?", (rel_id,))
        conn.commit()
        pipeline.refresh_validity(conn, get_client(), st.settings, load_ground_truth=False)
        rel = dict(conn.execute("SELECT * FROM relations WHERE id = ?", (rel_id,)).fetchone())
        target = conn.execute("SELECT circular_no, status, status_reason FROM documents WHERE id = ?",
                              (rel["target_doc_id"],)).fetchone() if rel["target_doc_id"] else None
    return {"relation": rel, "target": dict(target) if target else None}


@router.patch("/documents/{doc_id}")
async def edit_document(doc_id: int, request: Request) -> dict:
    st = request.app.state.pn
    body = await request.json()
    changes = {k: v for k, v in body.items() if k in EDITABLE}
    with pub_db(st) as conn:
        if conn.execute("SELECT 1 FROM documents WHERE id = ?", (doc_id,)).fetchone() is None:
            raise LookupError("Document not found")
        if changes:
            sets = ", ".join(f"{k} = ?" for k in changes)
            conn.execute(f"UPDATE documents SET {sets}, owner_verified = 1, updated_at = ? WHERE id = ?",
                         (*changes.values(), datetime.now().isoformat(timespec="seconds"), doc_id))
            conn.commit()
            pipeline.refresh_validity(conn, get_client(), st.settings, load_ground_truth=False)
        doc = dict(conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone())
    return {"document": doc}


@router.get("/packs")
def packs(request: Request) -> dict:
    st = request.app.state.pn
    manifest = read_manifest(st.settings.dist_packs_dir)
    latest = latest_versions(manifest)
    with pub_db(st) as conn:
        tiers = db.rows(conn.execute(
            """SELECT classification_level AS tier, COUNT(*) AS documents,
                      SUM(CASE WHEN status IN ('CANCELLED') THEN 1 ELSE 0 END) AS cancelled
               FROM documents GROUP BY classification_level"""))
        verified = conn.execute("SELECT COUNT(*) FROM relations WHERE verified = 1").fetchone()[0]
        pending = conn.execute("SELECT COUNT(*) FROM relations WHERE verified = 0").fetchone()[0]
        summaries = conn.execute("SELECT COUNT(*) FROM change_summaries").fetchone()[0]
    return {"manifest": manifest, "next_version": (max(latest.values()) + 1) if latest else 1, "tiers": tiers,
            "verified_relations": verified, "pending_relations": pending, "change_summaries": summaries,
            "embedding_model": st.settings.embedding_model_id, "private_key_present": st.settings.private_key_path.exists(),
            "dist_packs_dir": str(st.settings.dist_packs_dir)}


class BuildBody(BaseModel):
    version: int


@router.post("/build-packs")
def build(body: BuildBody, request: Request) -> dict:
    st = request.app.state.pn
    lines: list[str] = []
    entries = build_packs(st.settings, body.version, log=lines.append)
    return {"packs": entries, "log": lines}


@router.post("/import-report")
async def import_report(request: Request, file: UploadFile = File(...)) -> dict:
    st = request.app.state.pn
    try:
        payload = validate_report(json.loads((await file.read()).decode("utf-8")))
    except ValueError as exc:
        return {"ok": False, "message": str(exc)}
    with pub_db(st) as conn:
        conn.execute("INSERT INTO usage_reports (imported_at, payload_json) VALUES (?, ?)",
                     (datetime.now().isoformat(timespec="seconds"), json.dumps(payload, ensure_ascii=False)))
    return {"ok": True, "queries": len(payload["queries"])}


@router.get("/analytics")
def analytics(request: Request) -> dict:
    st = request.app.state.pn
    with pub_db(st) as conn:
        return dashboard(conn)
