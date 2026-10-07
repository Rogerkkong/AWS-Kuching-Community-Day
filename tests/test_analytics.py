import json

from conftest import H, ask, switch


def test_export_is_anonymised_and_hour_rounded(officer):
    switch(officer, 1)
    ask(officer, "Berapa hari cuti rehat yang boleh dibawa ke hadapan?")
    ask(officer, "What is the work-from-home policy for private contractors?")
    r = officer.post("/api/analytics/export", headers=H).json()
    text = json.dumps(r["report"], ensure_ascii=False)
    for name in ("Aina", "Jason", "Aminah", "user_id"):
        assert name not in text
    assert r["report"]["query_count"] == 2
    for q in r["report"]["queries"]:
        assert q["hour"].endswith(":00")
    assert any(q["excluded_circulars"] == ["PP 3/2018"] for q in r["report"]["queries"])


def test_publisher_import_and_dashboard(officer, env, tmp_path):
    import dataclasses

    from fastapi.testclient import TestClient

    from app.main import create_app

    ask(officer, "Berapa hari cuti rehat yang boleh dibawa ke hadapan?")
    ask(officer, "What is the work-from-home policy for private contractors?")
    report = officer.post("/api/analytics/export", headers=H).json()["report"]

    s = dataclasses.replace(env.settings, data_dir=tmp_path / "pub", workspace_dir=tmp_path / "pubws")
    pub = TestClient(create_app("publisher", "test-token", s), base_url="http://127.0.0.1")
    r = pub.post("/api/publisher/import-report", headers=H, files={"file": ("r.json", json.dumps(report).encode())}).json()
    assert r == {"ok": True, "queries": 2}
    dash = pub.get("/api/publisher/analytics", headers=H).json()
    assert dash["reports"] == 1 and dash["queries"] == 2 and dash["unanswered_rate"] == 0.5
    assert dash["top_unanswered"][0]["query"].startswith("What is the work-from-home")
    assert dash["excluded_circulars"][0]["circular_no"] == "PP 3/2018"
    bad = pub.post("/api/publisher/import-report", headers=H, files={"file": ("x.json", b'{"hello": 1}')}).json()
    assert bad["ok"] is False


def test_publisher_routes_absent_in_officer_mode(officer):
    assert officer.get("/api/publisher/documents", headers=H).status_code == 404
