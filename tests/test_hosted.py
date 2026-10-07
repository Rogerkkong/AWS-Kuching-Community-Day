"""Hosted demo (Vercel): works without the sqlite-vec extension and without a session token."""
import dataclasses

from fastapi.testclient import TestClient

from conftest import ask, switch


def test_search_works_without_sqlite_vec(env, tmp_path, monkeypatch):
    from app import db
    from app.main import create_app
    from app.services.packs.build import build_packs

    monkeypatch.setattr(db, "_VEC_OK", False)  # as on a runtime that forbids SQLite extensions
    s = dataclasses.replace(env.settings, dist_packs_dir=tmp_path / "dist", data_dir=tmp_path / "officer")
    build_packs(s, 1, log=lambda *_: None)
    conn = db.connect(s.dist_packs_dir / "pack-terbuka-v1.sqlite")
    assert conn.execute("SELECT COUNT(*) FROM chunk_vectors").fetchone()[0] > 0
    assert conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE name = 'vec_chunks'").fetchone()[0] == 0
    conn.close()

    client = TestClient(create_app("officer", "t", s), base_url="http://127.0.0.1")
    H = {"X-Session-Token": "t"}
    assert all(r["ok"] for r in client.post("/api/packs/install", headers=H, json={}).json()["results"])
    with client.stream("POST", "/api/ask", headers=H, json={"query": "Berapa hari cuti rehat yang boleh dibawa ke hadapan?"}) as r:
        body = "".join(r.iter_text())
    assert '"circular_no": "PP 2/2024"' in body and "event: final" in body


def test_public_demo_mode_needs_no_token(env, tmp_path):
    from app.main import create_app

    s = dataclasses.replace(env.settings, data_dir=tmp_path / "web", public_demo=True)
    client = TestClient(create_app("web", "ignored", s), base_url="https://mixup-navigator.vercel.app")
    assert client.get("/api/config").status_code == 200
    assert client.get("/health").json()["mode"] == "web"
