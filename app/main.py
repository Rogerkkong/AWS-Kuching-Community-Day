"""FastAPI application factory. Serves the API (token-protected) and the built React UI."""
from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import sqlite_vec
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app import db
from app.config import Settings, get_settings
from app.security import SessionTokenMiddleware
from app.services.inference.client import get_client, warm_state

SETUP_HTML = """<!doctype html><html><head><meta charset="utf-8"><title>MixUp Navigator</title></head>
<body style="font-family:system-ui;background:#F6F4F0;color:#1A1D21;padding:48px;max-width:720px">
<h1>MixUp Navigator</h1><p>The interface has not been built yet. Run:</p>
<pre style="background:#fff;padding:12px;border:1px solid #ddd">cd ui &amp;&amp; npm install &amp;&amp; npm run build</pre>
<p>Antara muka belum dibina. Jalankan arahan di atas, kemudian buka semula aplikasi.</p></body></html>"""


class AppState:
    """Process-wide state shared by routers (one officer/publisher session per process)."""

    def __init__(self, settings: Settings, mode: str, token: str):
        self.settings = settings
        self.mode = mode
        self.token = token
        self.lock = threading.RLock()  # serialises pack install vs. pack reads
        settings.ensure_dirs()
        db.check_sqlite_version()
        conn = db.init_app_db(settings.app_db)
        conn.close()

    @contextmanager
    def app_db(self) -> Iterator[sqlite3.Connection]:
        conn = db.connect(self.settings.app_db)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def current_user(self) -> dict:
        with self.app_db() as conn:
            uid = db.get_setting(conn, "current_user_id", "1")
            row = conn.execute("SELECT * FROM users WHERE id = ?", (int(uid),)).fetchone()
            if row is None:
                row = conn.execute("SELECT * FROM users ORDER BY id LIMIT 1").fetchone()
            return dict(row)


def create_app(mode: str = "officer", token: str = "dev-token", settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(title="MixUp Navigator local API", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.pn = AppState(settings, mode, token)

    from app.routers import alerts, analytics, ask, documents, packs, publisher, users
    for module in (users, packs, documents, ask, alerts, analytics):
        app.include_router(module.router)
    if mode in ("publisher", "web"):
        app.include_router(publisher.router)

    @app.get("/health")
    def health(request: Request) -> dict:
        st: AppState = request.app.state.pn
        try:
            inference = get_client().health()
        except Exception as exc:  # noqa: BLE001
            inference = {"backend": st.settings.inference_backend, "reachable": False, "detail": str(exc)}
        from app.services.packs.install import installed_packs
        packs_info = installed_packs(st) if mode != "publisher" else []
        return {
            "status": "ok",
            "mode": st.mode,
            "inference": inference,
            "model": warm_state(),
            "embedding_model": st.settings.embedding_model_id,
            "packs_installed": len(packs_info),
            "sqlite_version": sqlite3.sqlite_version,
            "sqlite_vec": sqlite_vec.__version__ if hasattr(sqlite_vec, "__version__") else "loaded",
        }

    @app.get("/api/config")
    def config(request: Request) -> dict:
        st: AppState = request.app.state.pn
        with st.app_db() as conn:
            lang = db.get_setting(conn, "ui_language", "ms")
            source = db.get_setting(conn, "update_source", str(st.settings.dist_packs_dir))
        # "web" mode serves both views on one site; the current account's role picks the view.
        view = st.mode
        if st.mode == "web":
            view = "publisher" if st.current_user()["role"] == "PUBLISHER" else "officer"
        return {"mode": view, "server_mode": st.mode, "ui_language": lang, "update_source": source,
                "backend": st.settings.inference_backend, "llm_model": st.settings.llm_model,
                "embedding_model": st.settings.embedding_model_id}

    @app.post("/api/settings")
    async def update_settings(request: Request) -> dict:
        st: AppState = request.app.state.pn
        body = await request.json()
        allowed = {"ui_language", "update_source"}
        with st.app_db() as conn:
            for key, value in body.items():
                if key in allowed and isinstance(value, str):
                    db.set_setting(conn, key, value)
        return {"ok": True}

    @app.exception_handler(PermissionError)
    async def forbidden(_: Request, exc: PermissionError) -> JSONResponse:
        return JSONResponse({"detail": str(exc) or "Forbidden"}, status_code=403)

    @app.exception_handler(ValueError)
    async def bad_request(_: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse({"detail": str(exc)}, status_code=400)

    @app.exception_handler(FileNotFoundError)
    async def missing_file(_: Request, exc: FileNotFoundError) -> JSONResponse:
        return JSONResponse({"detail": str(exc)}, status_code=400)

    @app.exception_handler(LookupError)
    async def not_found(_: Request, exc: LookupError) -> JSONResponse:
        return JSONResponse({"detail": str(exc) or "Not found"}, status_code=404)

    _mount_ui(app, settings.ui_dist)
    app.add_middleware(SessionTokenMiddleware, token=token)
    return app


def _mount_ui(app: FastAPI, dist: Path) -> None:
    index = dist / "index.html"
    if (dist / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path.startswith(("api/", "health")):
            return JSONResponse({"detail": "Not found"}, status_code=404)
        candidate = (dist / path).resolve()
        if path and candidate.is_file() and dist.resolve() in candidate.parents:
            return FileResponse(candidate)
        if index.exists():
            return FileResponse(index, headers={"Cache-Control": "no-store"})
        return HTMLResponse(SETUP_HTML)
