"""Shared fixtures: a Publisher workspace built from the synthetic corpus with the deterministic fake
backend, signed v1 packs, and helpers to start fresh Officer apps against them. No model or network."""
from __future__ import annotations

import dataclasses
import json
import os
import shutil
import warnings
from pathlib import Path

import pytest

warnings.filterwarnings("ignore", category=DeprecationWarning)

ROOT = Path(__file__).resolve().parent.parent
TOKEN = "test-token"
H = {"X-Session-Token": TOKEN}

os.environ["INFERENCE_BACKEND"] = "fake"
os.environ["PN_TODAY"] = "2026-10-07"


@dataclasses.dataclass
class Env:
    settings: object
    root: Path

    def with_(self, **kw):
        return dataclasses.replace(self.settings, **kw)


def _base_env(root: Path):
    from app import db
    from app.config import reset_settings
    from app.services.inference.client import get_client, set_client
    from app.services.ingest.pipeline import ingest_paths
    from app.services.packs.build import build_packs
    from app.services.packs.sign import generate_keypair

    os.environ.update({
        "PN_DATA_DIR": str(root / "officer"), "PN_WORKSPACE": str(root / "ws"), "PN_DIST_PACKS": str(root / "dist"),
        "PN_PUBLIC_KEY": str(root / "keys" / "publisher_public.pem"),
    })
    settings = reset_settings()
    set_client(None)
    generate_keypair(settings.private_key_path, settings.public_key_path, overwrite=True)
    conn = db.init_publisher_db(settings.publisher_db)
    ingest_paths(conn, sorted((ROOT / "data" / "raw").glob("*.pdf")), get_client(), settings)
    conn.close()
    build_packs(settings, 1, log=lambda *_: None)
    return settings


@pytest.fixture(scope="session")
def env(tmp_path_factory) -> Env:
    root = tmp_path_factory.mktemp("pn")
    return Env(_base_env(root), root)


@pytest.fixture(scope="session")
def env_v2(env: Env, tmp_path_factory) -> Env:
    """Copy of the workspace where the held-back PP 3/2026 is uploaded, verified and published as v2."""
    from app import db
    from app.services.inference.client import get_client
    from app.services.ingest.pipeline import ingest_paths, refresh_validity
    from app.services.packs.build import build_packs

    root = tmp_path_factory.mktemp("pn2")
    shutil.copytree(env.settings.workspace_dir, root / "ws")
    shutil.copytree(env.settings.dist_packs_dir, root / "dist")
    s = env.with_(workspace_dir=root / "ws", dist_packs_dir=root / "dist")
    conn = db.init_publisher_db(s.publisher_db)
    ingest_paths(conn, [ROOT / "data" / "incoming" / "PP-3-2026.pdf"], get_client(), s)
    rel = conn.execute("""SELECT r.id FROM relations r JOIN documents d ON d.id = r.source_doc_id
                          WHERE d.circular_no = 'PP 3/2026' AND r.target_ref_text = 'PP 1/2025'""").fetchone()
    conn.execute("UPDATE relations SET verified = 1 WHERE id = ?", (rel[0],))
    conn.commit()
    refresh_validity(conn, get_client(), s, load_ground_truth=False)
    conn.close()
    build_packs(s, 2, log=lambda *_: None)
    return Env(s, root)


def make_officer(settings, tmp: Path, install: bool = True, mode: str = "officer"):
    """Fresh Officer app (own app.db and pack folder) using `settings` for the update source."""
    from fastapi.testclient import TestClient

    from app.main import create_app

    s = dataclasses.replace(settings, data_dir=tmp)
    app = create_app(mode, TOKEN, s)
    client = TestClient(app, base_url="http://127.0.0.1")
    if install:
        r = client.post("/api/packs/install", headers=H, json={}).json()
        assert all(x["ok"] for x in r["results"]), r
    return client


@pytest.fixture
def officer(env: Env, tmp_path):
    return make_officer(env.settings, tmp_path / "officer")


def switch(client, user_id: int) -> None:
    assert client.post("/api/users/switch", headers=H, json={"user_id": user_id}).status_code == 200


def ask(client, query: str, include_historical: bool = False) -> list[tuple[str, dict]]:
    with client.stream("POST", "/api/ask", headers=H, json={"query": query, "include_historical": include_historical}) as r:
        assert r.status_code == 200
        body = "".join(r.iter_text())
    events = []
    for block in body.strip().split("\n\n"):
        lines = block.split("\n")
        events.append((lines[0][len("event: "):], json.loads(lines[1][len("data: "):])))
    return events
