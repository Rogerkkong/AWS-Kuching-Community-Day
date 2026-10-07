"""A TERBUKA session never opens the TERHAD pack and never receives TERHAD content from search, the
excluded list, documents, lineage, diff or page images (rule 3)."""
import sqlite3

from conftest import H, ask, switch

SECRET = "Bilik Fail Terhad Aras 3"  # appears only in the synthetic TERHAD guideline
TERHAD_NO = "GP 1/2026"


def terhad_doc_id(env) -> int:
    conn = sqlite3.connect(env.settings.publisher_db)
    try:
        return conn.execute("SELECT id FROM documents WHERE circular_no = ?", (TERHAD_NO,)).fetchone()[0]
    finally:
        conn.close()


def test_terbuka_session_never_opens_terhad_pack(officer, monkeypatch):
    from app import db

    opened = []
    real = db.connect

    def spy(path, **kw):
        opened.append(str(path))
        return real(path, **kw)

    monkeypatch.setattr(db, "connect", spy)
    switch(officer, 1)  # Aina, TERBUKA
    ask(officer, "Di manakah fail Terhad disimpan?")
    officer.get("/api/documents", headers=H)
    assert any("pack-terbuka" in p for p in opened)
    assert not any("pack-terhad" in p for p in opened)


def test_terbuka_search_and_answer_never_contain_terhad(officer):
    switch(officer, 1)
    for q in ("Di manakah fail Terhad disimpan?", "pengendalian fail terhad bilik kabinet berkunci", "GP 1/2026"):
        for event, data in ask(officer, q, include_historical=True):
            data = {k: v for k, v in data.items() if k != "rewritten"}  # echo of the user's own query
            text = str(data)
            assert SECRET not in text, (event, q)
            assert TERHAD_NO not in text, (event, q)


def test_terhad_officer_sees_terhad_content(officer):
    switch(officer, 3)  # Aminah, TERHAD
    events = ask(officer, "Di manakah fail Terhad disimpan?")
    sources = events[0][1]["sources"]
    assert any(s["circular_no"] == TERHAD_NO for s in sources)
    assert SECRET in events[-1][1]["answer"]


def test_terbuka_documents_lineage_diff_and_pages_hide_terhad(officer, env):
    switch(officer, 1)
    tid = terhad_doc_id(env)
    docs = officer.get("/api/documents", headers=H).json()["documents"]
    assert all(d["classification_level"] == 0 for d in docs)
    assert TERHAD_NO not in str(docs)
    assert officer.get(f"/api/documents/{tid}", headers=H).status_code == 404
    assert officer.get(f"/api/documents/{tid}/lineage", headers=H).status_code == 404
    assert officer.get(f"/api/documents/{tid}/pages/1.png", headers=H).status_code == 404
    assert officer.get(f"/api/diff?old={tid}&new={tid}", headers=H).status_code == 404
    # The TERHAD officer can open the same page image.
    switch(officer, 3)
    r = officer.get(f"/api/documents/{tid}/pages/1.png", headers=H)
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"


def test_excluded_list_respects_clearance(officer):
    switch(officer, 1)
    events = ask(officer, "Berapa hari cuti rehat yang boleh dibawa ke hadapan?")
    excluded = events[0][1]["excluded"]
    assert [e["circular_no"] for e in excluded] == ["PP 3/2018"]
    assert all(TERHAD_NO not in str(e) for e in excluded)


def test_sql_filter_applies_inside_packs_too(env, tmp_path):
    """Even if a TERHAD row were inside an opened pack, the clearance predicate drops it."""
    from app.services.retrieval.filters import fetch_documents, PackHandle
    from app import db

    terhad_pack = next(env.settings.dist_packs_dir.glob("pack-terhad-v1.sqlite"))
    conn = db.connect(terhad_pack, vec=True, readonly=True)
    try:
        handle = PackHandle(1, 1, terhad_pack, conn, "fake-hash-1024")
        assert fetch_documents([handle], clearance=0) == []
        assert len(fetch_documents([handle], clearance=1)) == 1
    finally:
        conn.close()
