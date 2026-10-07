"""Installed packs, update checks, verified installs (update source or file picker) and rollback."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Request, UploadFile
from pydantic import BaseModel

from app import db
from app.config import TIERS
from app.services.packs import install

router = APIRouter(prefix="/api/packs", tags=["packs"])


def _source(st, override: str | None) -> str:
    if override:
        return override
    with st.app_db() as conn:
        return db.get_setting(conn, "update_source", str(st.settings.dist_packs_dir))


@router.get("")
def list_packs(request: Request) -> dict:
    st = request.app.state.pn
    packs = install.installed_packs(st)
    for p in packs:
        p["tier_name"] = TIERS[p["tier"]].upper()
        p["size_bytes"] = Path(p["file_path"]).stat().st_size
        p["embedding_ok"] = p["embedding_model"] == st.settings.embedding_model_id
    return {"installed": packs, "update_source": _source(st, None), "device_clearance": install.device_clearance(st),
            "embedding_model": st.settings.embedding_model_id}


class SourceBody(BaseModel):
    source: str | None = None


@router.post("/check")
def check(request: Request, body: SourceBody | None = None) -> dict:
    st = request.app.state.pn
    source = _source(st, body.source if body else None)
    try:
        return install.check_updates(st, source)
    except Exception as exc:  # noqa: BLE001 - offline or folder missing is a normal state
        return {"source": source, "updates": [], "installed": install.installed_packs(st), "error": str(exc)}


@router.post("/install")
def install_updates(request: Request, body: SourceBody | None = None) -> dict:
    st = request.app.state.pn
    source = _source(st, body.source if body else None)
    try:
        return install.install_updates(st, source)
    except Exception as exc:  # noqa: BLE001
        return {"results": [], "error": str(exc)}


@router.post("/install-file")
async def install_file(request: Request, pack: UploadFile = File(...), signature: UploadFile = File(...)) -> dict:
    """USB case: the pack file plus its .sig.json sidecar written by the Publisher."""
    st = request.app.state.pn
    try:
        entry = json.loads((await signature.read()).decode("utf-8"))
    except ValueError:
        return {"ok": False, "error_code": "signature", "message": "Signature file is not valid JSON"}
    st.settings.packs_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=st.settings.packs_dir, suffix=".upload", delete=False) as tmp:
        while chunk := await pack.read(1 << 20):
            tmp.write(chunk)
        tmp_path = Path(tmp.name)
    try:
        return install.install_local_file(st, tmp_path, entry)
    finally:
        tmp_path.unlink(missing_ok=True)


class RollbackBody(BaseModel):
    tier: int


@router.post("/rollback")
def rollback(body: RollbackBody, request: Request) -> dict:
    return install.rollback(request.app.state.pn, body.tier)
