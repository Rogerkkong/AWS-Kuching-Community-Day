"""Pack verification (checksum, signature, embedding model) and atomic install with rollback."""
import json
import shutil

import pytest

from conftest import H, ask, make_officer, switch


def manifest(settings) -> dict:
    return json.loads((settings.dist_packs_dir / "manifest.json").read_text())


def test_manifest_lists_signed_packs_with_embedding_model(env):
    packs = manifest(env.settings)["packs"]
    assert {(p["tier"], p["version"]) for p in packs} >= {(0, 1), (1, 1)}
    for p in packs:
        assert len(p["sha256"]) == 64 and p["signature"] and p["embedding_model"] == "fake-hash-1024"


def test_pack_contents(env):
    from app import db

    pack = env.settings.dist_packs_dir / "pack-terbuka-v1.sqlite"
    conn = db.connect(pack, vec=True, readonly=True)
    try:
        m = dict(conn.execute("SELECT * FROM manifest").fetchone())
        assert m["tier"] == 0 and m["version"] == 1 and m["embedding_dim"] == 1024
        n_chunks = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        assert conn.execute("SELECT COUNT(*) FROM vec_chunks").fetchone()[0] == n_chunks
        assert conn.execute("SELECT COUNT(*) FROM chunks_fts WHERE chunks_fts MATCH '\"cuti\"'").fetchone()[0] > 0
        assert conn.execute("SELECT circular_no FROM docs_trgm WHERE circular_no MATCH '\"PP 3/2018\"'").fetchone()[0] == "PP 3/2018"
        assert conn.execute("SELECT COUNT(*) FROM files WHERE pdf IS NOT NULL").fetchone()[0] == m["document_count"]
        assert conn.execute("SELECT COUNT(*) FROM documents WHERE classification_level <> 0").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM relations WHERE verified <> 1").fetchone()[0] == 0
    finally:
        conn.close()


def _tampered_source(env, tmp_path, mutate):
    src = tmp_path / "source"
    shutil.copytree(env.settings.dist_packs_dir, src)
    mutate(src)
    return env.with_(dist_packs_dir=src)


def _bump_v2(src, edit_entry=None, edit_bytes=None):
    m = json.loads((src / "manifest.json").read_text())
    entry = next(p for p in m["packs"] if p["tier"] == 0 and p["version"] == 1)
    v2 = dict(entry, version=2, file="pack-terbuka-v2.sqlite")
    data = (src / entry["file"]).read_bytes()
    if edit_bytes:
        data = edit_bytes(data)
    (src / v2["file"]).write_bytes(data)
    if edit_entry:
        edit_entry(v2)
    m["packs"].append(v2)
    (src / "manifest.json").write_text(json.dumps(m))


@pytest.mark.parametrize("case,code", [
    ("tampered_bytes", "checksum"),
    ("bad_signature", "signature"),
])
def test_rejected_pack_keeps_previous_version(env, tmp_path, case, code):
    client = make_officer(env.settings, tmp_path / "officer")
    if case == "tampered_bytes":
        src = _tampered_source(env, tmp_path, lambda s: _bump_v2(s, edit_bytes=lambda b: b[:-10] + b"X" * 10))
    else:
        def resign(entry):
            entry["signature"] = entry["signature"][:-4] + ("AAAA" if not entry["signature"].endswith("AAAA") else "BBBB")
        src = _tampered_source(env, tmp_path, lambda s: _bump_v2(s, edit_entry=resign))
    client.post("/api/settings", headers=H, json={"update_source": str(src.dist_packs_dir)})
    r = client.post("/api/packs/install", headers=H, json={}).json()
    result = r["results"][0]
    assert result["ok"] is False and result["error_code"] == code
    installed = {p["tier"]: p["version"] for p in client.get("/api/packs", headers=H).json()["installed"]}
    assert installed[0] == 1  # previous version still active
    switch(client, 1)
    assert ask(client, "Berapa hari cuti rehat yang boleh dibawa ke hadapan?")[0][1]["sources"]  # still searchable


def test_signature_from_other_key_is_rejected(env, tmp_path):
    from app.services.packs.sign import generate_keypair, sign_digest

    other_priv, other_pub = tmp_path / "k" / "priv.pem", tmp_path / "k" / "pub.pem"
    generate_keypair(other_priv, other_pub)

    def resign(entry):
        entry["signature"] = sign_digest(other_priv, entry["sha256"])
    src = _tampered_source(env, tmp_path, lambda s: _bump_v2(s, edit_entry=resign))
    client = make_officer(src, tmp_path / "officer", install=False)
    r = client.post("/api/packs/install", headers=H, json={}).json()
    assert [x["error_code"] for x in r["results"] if not x["ok"]] == ["signature"]
    assert {p["tier"] for p in client.get("/api/packs", headers=H).json()["installed"]} == {1}


def test_embedding_model_mismatch_is_detected(env, tmp_path):
    from app.services.packs.verify import PackVerificationError, verify_pack

    entry = next(p for p in manifest(env.settings)["packs"] if p["tier"] == 0)
    with pytest.raises(PackVerificationError) as exc:
        verify_pack(env.settings.dist_packs_dir / entry["file"], entry, env.settings.public_key_path, "bge-m3")
    assert exc.value.code == "embedding_model"


def test_officer_refuses_to_search_pack_with_other_embedding_model(env, tmp_path):
    """An installed pack whose model differs from the app's (e.g. backend changed) is not searched."""
    client = make_officer(env.settings, tmp_path / "officer")
    client.app.state.pn.settings.embed_model = "bge-m3"
    client.app.state.pn.settings.inference_backend = "ollama"  # embedding_model_id -> "bge-m3"
    try:
        from app.services.generation.answer import retrieve
        from app.services.inference.fake_backend import FakeBackend

        st = client.app.state.pn
        r = retrieve(st, st.current_user(), "cuti rehat", client=FakeBackend(st.settings))
        assert r.selected == []
        assert any(w["code"] == "embedding_model_mismatch" for w in r.warnings)
    finally:
        client.app.state.pn.settings.inference_backend = "fake"


def test_install_from_file_with_sidecar(env, tmp_path):
    client = make_officer(env.settings, tmp_path / "officer", install=False)
    pack = env.settings.dist_packs_dir / "pack-terbuka-v1.sqlite"
    sig = env.settings.dist_packs_dir / "pack-terbuka-v1.sqlite.sig.json"
    r = client.post("/api/packs/install-file", headers=H,
                    files={"pack": ("p.sqlite", pack.read_bytes()), "signature": ("s.json", sig.read_bytes())}).json()
    assert r["ok"] is True
    bad = json.loads(sig.read_text())
    bad["sha256"] = "0" * 64
    bad["version"] = 1
    client2 = make_officer(env.settings, tmp_path / "officer2", install=False)
    r2 = client2.post("/api/packs/install-file", headers=H,
                      files={"pack": ("p.sqlite", pack.read_bytes()), "signature": ("s.json", json.dumps(bad).encode())}).json()
    assert r2["ok"] is False and r2["error_code"] == "checksum"
    assert client2.get("/api/packs", headers=H).json()["installed"] == []
