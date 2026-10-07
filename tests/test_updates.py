"""Pack v2 (new circular PP 3/2026 supersedes PP 1/2025): check, verify, install, diff -> notifications."""
from conftest import H, ask, make_officer, switch


def test_update_flow_and_notifications(env, env_v2, tmp_path):
    client = make_officer(env.settings, tmp_path / "officer")  # v1 installed from the original source
    switch(client, 1)
    # Aina searched for the travel-allowance circular before the update.
    ask(client, "Berapa kadar elaun makan perjalanan dalam negeri dalam PP 1/2025?")

    client.post("/api/settings", headers=H, json={"update_source": str(env_v2.settings.dist_packs_dir)})
    check = client.post("/api/packs/check", headers=H, json={}).json()
    assert [(u["tier"], u["version"]) for u in check["updates"]] == [(0, 2), (1, 2)]  # every tier is rebuilt per version

    r = client.post("/api/packs/install", headers=H, json={}).json()
    terbuka = next(x for x in r["results"] if x["tier"] == 0)
    assert terbuka["ok"] and terbuka["previous_version"] == 1
    changes = terbuka["changes"]
    assert [d["circular_no"] for d in changes["added"]] == ["PP 3/2026"]
    assert [(c["circular_no"], c["old_status"], c["new_status"]) for c in changes["status_changes"]] == [
        ("PP 1/2025", "IN_FORCE", "CANCELLED")]
    assert len(changes["change_summaries"]) == 1

    alerts = client.get("/api/alerts", headers=H).json()
    kinds = sorted((n["circular_no"], n["change_type"]) for n in alerts["notifications"])
    assert kinds == [("PP 1/2025", "STATUS_CHANGE"), ("PP 3/2026", "NEW_DOCUMENT")]
    status_note = next(n for n in alerts["notifications"] if n["change_type"] == "STATUS_CHANGE")
    assert "Dibatalkan oleh PP 3/2026" in status_note["summary_ms"]
    assert alerts["unread"] == 2

    # What-changed view for the pair named in the notification.
    diff = client.get(f"/api/diff?old={status_note['document_id']}&new={status_note['related_doc_id']}", headers=H).json()
    assert diff["new"]["circular_no"] == "PP 3/2026" and diff["clauses"]
    assert any("RM75" in c["new_text"] for c in diff["clauses"])

    # The new rule is answered, and the cancelled one is excluded.
    events = ask(client, "Berapa kadar elaun makan bagi perjalanan dalam negeri?")
    assert events[0][1]["sources"][0]["circular_no"] == "PP 3/2026"
    assert "PP 1/2025" in [e["circular_no"] for e in events[0][1]["excluded"]]

    # A second check finds nothing new; rollback restores v1.
    assert client.post("/api/packs/check", headers=H, json={}).json()["updates"] == []
    assert client.post("/api/packs/rollback", headers=H, json={"tier": 0}).json() == {"ok": True, "version": 1}


def test_unsubscribed_user_without_searches_gets_no_notifications(env, env_v2, tmp_path):
    client = make_officer(env.settings, tmp_path / "officer")
    st = client.app.state.pn
    with st.app_db() as conn:
        conn.execute("DELETE FROM subscriptions")
    client.post("/api/settings", headers=H, json={"update_source": str(env_v2.settings.dist_packs_dir)})
    client.post("/api/packs/install", headers=H, json={})
    switch(client, 2)
    assert client.get("/api/alerts", headers=H).json()["notifications"] == []
