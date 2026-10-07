"""Vercel entrypoint: hosted public demo of the website with the synthetic documents.

Vercel only allows writing to /tmp, so on a cold start this module creates a throw-away publisher key
pair, ingests data/raw (fake backend), builds and signs pack v1 and installs it, all under /tmp/pn.
Nothing secret is stored in the repository. State lives in /tmp, so it resets when Vercel starts a new
instance. PN_PUBLIC_DEMO=1 turns off the session token and Host check: synthetic documents only.
"""
from __future__ import annotations

import os
from pathlib import Path

BASE = Path(os.environ.get("PN_HOSTED_ROOT", "/tmp/pn"))
os.environ.setdefault("INFERENCE_BACKEND", "fake")
os.environ.setdefault("PN_PUBLIC_DEMO", "1")
os.environ.setdefault("PN_DATA_DIR", str(BASE / "officer"))
os.environ.setdefault("PN_WORKSPACE", str(BASE / "ws"))
os.environ.setdefault("PN_DIST_PACKS", str(BASE / "dist"))
os.environ.setdefault("PN_PUBLIC_KEY", str(BASE / "keys" / "publisher_public.pem"))

from app import db  # noqa: E402
from app.config import reset_settings  # noqa: E402
from app.main import create_app  # noqa: E402
from app.services.inference.client import get_client, set_client  # noqa: E402
from app.services.ingest.pipeline import ingest_paths  # noqa: E402
from app.services.packs.build import build_packs  # noqa: E402
from app.services.packs.install import install_updates  # noqa: E402
from app.services.packs.sign import generate_keypair  # noqa: E402

settings = reset_settings()
set_client(None)


def _prepare() -> None:
    if (settings.dist_packs_dir / "manifest.json").exists():
        return
    generate_keypair(settings.private_key_path, settings.public_key_path, overwrite=True)
    conn = db.init_publisher_db(settings.publisher_db)
    try:
        ingest_paths(conn, sorted(settings.raw_dir.glob("*.pdf")), get_client(), settings)
    finally:
        conn.close()
    build_packs(settings, 1, log=lambda *_: None)


_prepare()
app = create_app("web", token="hosted-demo", settings=settings)
if not (settings.packs_dir / "pack-terbuka.sqlite").exists():
    install_updates(app.state.pn, str(settings.dist_packs_dir))
