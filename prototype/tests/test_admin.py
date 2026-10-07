"""Feature C: live upload, verification queue, status recompute, permissions, idempotency."""

from __future__ import annotations

from pathlib import Path

import pytest

from mixup import admin, alerts
from mixup.llm import LLMError
from mixup.store import Store

ROOT = Path(__file__).resolve().parent.parent
OLD_CHAIN = {"SPP-1-2023", "SPP-2-2025"}


def _demo_bytes(store) -> tuple[str, bytes]:
    path = store.data_dir / "upload_demo" / "SPP-1-2026.md"
    return path.name, path.read_bytes()


def _analyze(store, user=None):
    name, data = _demo_bytes(store)
    return admin.analyze_upload(store, name, data, user)


def _commit(store, user=None) -> str:
    return admin.commit_upload(store, _analyze(store, user), user)


def _approve_all(store, user=None) -> list[dict]:
    results = []
    for rel in admin.pending_relations(store, user):
        results.append(admin.verify_relation(store, rel.relation_id, True, None, user))
    return results


# ----------------------------------------------------------------------------
# Analysis
# ----------------------------------------------------------------------------


def test_analyze_demo_offline_yields_cancels_candidates(store, users):
    analysis = _analyze(store, users["ADMIN"])
    doc = analysis["doc"]
    assert doc.doc_id == "SPP-1-2026" and doc.circular_no == "SPP 1/2026"
    assert doc.effective_date.isoformat() == "2026-10-01"
    assert doc.jurisdiction == "FEDERAL" and doc.cluster == "travel-claims" and doc.classification_level == 0
    assert [s["step"] for s in analysis["steps"]] == ["parse", "metadata", "relations"]
    assert all(s["ok"] for s in analysis["steps"])
    assert analysis["relation_mode"] == "regex" and analysis["metadata_mode"] == "regex"

    cands = {r.target_doc_id: r for r in analysis["candidates"]}
    assert set(cands) == OLD_CHAIN
    for rel in cands.values():
        assert rel.relation_type == "CANCELS"
        assert not rel.verified and not rel.rejected and rel.origin == "extracted"
        assert "dibatalkan" in rel.evidence_text and "Bilangan 1 Tahun 2023" in rel.evidence_text
        assert rel.evidence_page == analysis["pages"]  # the PEMBATALAN section is the last page
        assert rel.source_doc_id == "SPP-1-2026"


def test_analyze_saves_nothing(store):
    _analyze(store)
    assert "SPP-1-2026" not in store.docs
    assert store.pending_relations() == []
    assert not (store.runtime_dir / "uploads").exists()


def test_unsupported_and_empty_files_are_logged(store, users):
    with pytest.raises(ValueError):
        admin.analyze_upload(store, "notes.xlsx", b"abc", users["ADMIN"])
    with pytest.raises(ValueError):
        admin.analyze_upload(store, "empty.md", b"", users["ADMIN"])
    with pytest.raises(ValueError):
        admin.analyze_upload(store, "broken.pdf", b"%PDF-1.4 not really a pdf", users["ADMIN"])
    events = [r["event"] for r in admin.ingest_log(store, users["ADMIN"])]
    assert events.count("error") == 3


def test_scanned_page_flagged_for_ocr(store):
    text = "SURAT PEKELILING PERKHIDMATAN BILANGAN 9 TAHUN 2026\nRujukan: SPP 9/2026\n" + "x " * 40 + "\f\f"
    analysis = admin.analyze_upload(store, "scan.txt", text.encode("utf-8"))
    assert any("OCR" in w for w in analysis["warnings"])


# ----------------------------------------------------------------------------
# Commit and verification
# ----------------------------------------------------------------------------


def test_commit_keeps_statuses_until_approval(store, users):
    doc_id = _commit(store, users["ADMIN"])
    assert doc_id == "SPP-1-2026"
    assert store.docs[doc_id].status == "IN_FORCE" and store.docs[doc_id].origin == "upload"
    assert store.docs["SPP-1-2023"].status == "AMENDED"
    assert store.docs["SPP-2-2025"].status == "IN_FORCE"
    pending = admin.pending_relations(store, users["ADMIN"])
    assert {r.target_doc_id for r in pending} == OLD_CHAIN
    assert (store.runtime_dir / "relations_pending.csv").read_text(encoding="utf-8").count("SPP-1-2026") == 2
    assert "SPP-1-2026" in (store.runtime_dir / "metadata_uploads.csv").read_text(encoding="utf-8")
    assert (store.runtime_dir / "uploads" / "SPP-1-2026" / "SPP-1-2026.md").exists()


def test_approval_cancels_old_chain_and_search_returns_new(store, users):
    _commit(store, users["ADMIN"])
    results = _approve_all(store, users["ADMIN"])
    for doc_id in OLD_CHAIN:
        assert store.docs[doc_id].status == "CANCELLED"
        assert store.docs[doc_id].status_reason == "Dibatalkan oleh SPP 1/2026"
    assert store.docs["SPP-1-2026"].status == "IN_FORCE"
    changed = {c["doc_id"]: c for r in results for c in r["status_changes"]}
    assert set(changed) == OLD_CHAIN
    assert changed["SPP-1-2023"]["old_status"] == "AMENDED" and changed["SPP-1-2023"]["new_status"] == "CANCELLED"
    assert admin.pending_relations(store) == []

    for query in ("tempoh tuntutan perjalanan", "travel claim deadline", "kadar elaun perbatuan"):
        hits = store.search(users["FED-T0"], query, k=5)
        assert hits and hits[0].doc.doc_id == "SPP-1-2026", query
        assert not {h.doc.doc_id for h in hits} & OLD_CHAIN, query

    # the bell lights up for an officer following the travel-claims cluster
    assert alerts.notifications(store, users["FED-T0"])
    assert [r["event"] for r in admin.ingest_log(store)][:2] == ["approve", "approve"]


def test_reject_does_not_change_status(store, users):
    _commit(store, users["ADMIN"])
    rel = next(r for r in admin.pending_relations(store) if r.target_doc_id == "SPP-2-2025")
    result = admin.verify_relation(store, rel.relation_id, False, None, users["ADMIN"])
    assert result["status_changes"] == [] and result["notifications"] == []
    assert store.get_relation(rel.relation_id).rejected
    assert store.docs["SPP-2-2025"].status == "IN_FORCE"
    assert len(admin.pending_relations(store)) == 1


def test_edit_then_approve(store, users):
    _commit(store, users["ADMIN"])
    rel = next(r for r in admin.pending_relations(store) if r.target_doc_id == "SPP-2-2025")
    with pytest.raises(ValueError):
        admin.verify_relation(store, rel.relation_id, True, {"relation_type": "DESTROYS"}, users["ADMIN"])
    with pytest.raises(ValueError):
        admin.verify_relation(store, rel.relation_id, True, {"target_doc_id": "NOPE"}, users["ADMIN"])
    with pytest.raises(KeyError):
        admin.verify_relation(store, "X-missing", True, None, users["ADMIN"])
    admin.verify_relation(store, rel.relation_id, True, {"relation_type": "AMENDS", "scope": "clauses: 4.2"}, users["ADMIN"])
    assert store.docs["SPP-2-2025"].status == "AMENDED"
    assert store.docs["SPP-2-2025"].status_reason == "Dipinda oleh SPP 1/2026"
    assert store.get_relation(rel.relation_id).scope == "clauses: 4.2"


def test_reset_restores_original_state(store, users, settings):
    _commit(store, users["ADMIN"])
    _approve_all(store, users["ADMIN"])
    store.reset_runtime()
    assert "SPP-1-2026" not in store.docs
    assert store.docs["SPP-1-2023"].status == "AMENDED"
    assert store.docs["SPP-2-2025"].status == "IN_FORCE"
    assert admin.pending_relations(store) == [] and admin.ingest_log(store) == []
    assert "SPP-1-2026" not in Store(settings).docs  # nothing left on disk either


def test_decisions_persist_across_restart(store, users, settings):
    _commit(store, users["ADMIN"])
    _approve_all(store, users["ADMIN"])
    reloaded = Store(settings)
    assert reloaded.docs["SPP-1-2023"].status_reason == "Dibatalkan oleh SPP 1/2026"
    assert admin.pending_relations(reloaded) == []


def test_reupload_is_idempotent(store, users):
    _commit(store, users["ADMIN"])
    ids = sorted(r.relation_id for r in admin.pending_relations(store))
    first, second = admin.pending_relations(store)
    admin.verify_relation(store, first.relation_id, True, None, users["ADMIN"])
    admin.verify_relation(store, second.relation_id, False, None, users["ADMIN"])
    n_docs, n_rels = len(store.docs), len(store.relations)

    analysis = _analyze(store, users["ADMIN"])
    assert analysis["replaces_upload"]
    assert _commit(store, users["ADMIN"]) == "SPP-1-2026"
    assert len(store.docs) == n_docs and len(store.relations) == n_rels
    assert sorted(r.relation_id for r in store.relations if r.source_doc_id == "SPP-1-2026") == ids
    assert store.get_relation(first.relation_id).verified
    assert store.get_relation(second.relation_id).rejected
    assert admin.pending_relations(store) == []
    assert len([c for c in store.chunks if c.doc_id == "SPP-1-2026"]) == len(store.chunks_by_doc["SPP-1-2026"])


def test_uploading_a_base_circular_uses_metadata_csv_and_changes_nothing(store, users):
    path = store.data_dir / "documents" / "SPP-1-2023.md"
    analysis = admin.analyze_upload(store, path.name, path.read_bytes(), users["ADMIN"])
    assert analysis["duplicate_of"] == "SPP-1-2023"
    assert analysis["meta_sources"]["title"] == "metadata.csv"
    assert analysis["doc"].title == store.docs["SPP-1-2023"].title
    n_docs = len(store.docs)
    assert admin.commit_upload(store, analysis, users["ADMIN"]) == "SPP-1-2023"
    assert len(store.docs) == n_docs and store.docs["SPP-1-2023"].origin == "base"


def test_apply_metadata_edits(store):
    analysis = _analyze(store)
    admin.apply_metadata_edits(store, analysis, {"title": "Tajuk Baharu", "expiry_date": None, "classification_level": 1})
    doc = analysis["doc"]
    assert doc.title == "Tajuk Baharu" and doc.classification_level == 1 and doc.doc_id == "SPP-1-2026"
    assert analysis["meta_sources"]["title"] == "manual"
    admin.apply_metadata_edits(store, analysis, {"circular_no": "SPP Bil. 7/2026", "effective_date": None})
    doc = analysis["doc"]
    assert doc.circular_no == "SPP 7/2026" and doc.doc_id == "SPP-7-2026" and doc.effective_date is None
    assert {r.source_doc_id for r in analysis["candidates"]} == {"SPP-7-2026"}
    assert {r.target_doc_id for r in analysis["candidates"]} == OLD_CHAIN
    assert admin.commit_upload(store, analysis) == "SPP-7-2026"
    assert store.docs["SPP-7-2026"].status == "UNKNOWN"  # no effective date -> Belum disahkan


# ----------------------------------------------------------------------------
# Permissions and access control
# ----------------------------------------------------------------------------


def test_non_admin_cannot_commit_or_verify(store, users):
    assert admin.can_admin(users["ADMIN"]) and admin.can_admin(users["OWNER"])
    assert not admin.can_admin(users["FED-T0"]) and not admin.can_admin(users["FED-T1"]) and not admin.can_admin(None)
    with pytest.raises(PermissionError):
        admin.commit_upload(store, _analyze(store, users["FED-T0"]), users["FED-T0"])
    assert "SPP-1-2026" not in store.docs

    _commit(store, users["ADMIN"])
    rel = admin.pending_relations(store)[0]
    for officer in ("FED-T0", "SWK-T0", "FED-T1"):
        with pytest.raises(PermissionError):
            admin.verify_relation(store, rel.relation_id, True, None, users[officer])
        with pytest.raises(PermissionError):
            admin.approve_all(store, "SPP-1-2026", users[officer])
    assert not store.get_relation(rel.relation_id).verified
    assert store.docs[rel.target_doc_id].status in ("AMENDED", "IN_FORCE")

    admin.verify_relation(store, rel.relation_id, True, None, users["OWNER"])  # policy owner may verify
    assert store.docs[rel.target_doc_id].status == "CANCELLED"


SULIT_DOC = """SINTETIK - CONTOH SAHAJA / SYNTHETIC - SAMPLE ONLY

# ARAHAN KESELAMATAN DALAMAN

Rujukan: SE 9/2026
Klasifikasi: SULIT
Tarikh kuat kuasa: 1 Oktober 2026

## PEMBATALAN

1. Surat Edaran Bilangan 1 Tahun 2021 adalah dibatalkan berkuat kuasa serta-merta bagi tujuan ujian.

SINTETIK - CONTOH SAHAJA / SYNTHETIC - SAMPLE ONLY
"""


def test_queue_and_log_respect_clearance(store, users):
    analysis = admin.analyze_upload(store, "se-9-2026.md", SULIT_DOC.encode("utf-8"), users["ADMIN"])
    assert analysis["doc"].classification_level == 2
    assert {r.target_doc_id for r in analysis["candidates"]} == {"SE-1-2021"}
    doc_id = admin.commit_upload(store, analysis, users["ADMIN"])

    assert [r.source_doc_id for r in admin.pending_relations(store, users["ADMIN"])] == [doc_id]
    assert admin.pending_relations(store, users["OWNER"]) == []  # clearance 1 cannot see a Sulit source
    owner_log = " ".join(str(r) for r in admin.ingest_log(store, users["OWNER"]))
    assert "SE 9/2026" not in owner_log and doc_id not in owner_log
    rel = admin.pending_relations(store)[0]
    with pytest.raises(PermissionError):
        admin.verify_relation(store, rel.relation_id, True, None, users["OWNER"])
    hits = store.search(users["FED-T0"], "arahan keselamatan dalaman SE 9/2026", k=10, statuses=None)
    assert doc_id not in {h.doc.doc_id for h in hits}
    assert doc_id in {h.doc.doc_id for h in store.search(users["ADMIN"], "arahan keselamatan dalaman SE 9/2026", k=10, statuses=None)}


# ----------------------------------------------------------------------------
# LLM paths (FakeLLM) and fallback
# ----------------------------------------------------------------------------


def test_llm_fills_gaps_but_regex_and_csv_win(store, fake_llm):
    meta = {"circular_no": "SPP 99/2026", "series": "SPP", "title": "Model title", "issuer": None, "issue_date": None,
            "effective_date": None, "jurisdiction": "SARAWAK", "applicability": None, "one_off": False, "language": "ms"}
    rels = {"relations": [{"ref_text": "Surat Pekeliling Perkhidmatan Bilangan 1 Tahun 2023", "relation": "SUPERSEDES",
                           "scope": "whole", "effective_date": "2026-10-01", "evidence": "...", "page": 7, "confidence": 0.95}]}
    store.llm = fake_llm([meta, rels])
    analysis = _analyze(store)
    doc = analysis["doc"]
    assert doc.circular_no == "SPP 1/2026" and doc.title.startswith("Tuntutan")  # regex values kept
    assert doc.jurisdiction == "FEDERAL"
    assert len(store.llm.calls) == 2 and "TEXT:" in store.llm.calls[0]["prompt"]
    cands = {r.target_doc_id: r for r in analysis["candidates"]}
    assert cands["SPP-1-2023"].relation_type == "SUPERSEDES" and cands["SPP-1-2023"].confidence == 0.95
    assert cands["SPP-2-2025"].relation_type == "CANCELS"
    assert analysis["relation_mode"] == "llm"
    assert not any(r.verified for r in analysis["candidates"])


def test_llm_error_falls_back_to_regex(store, fake_llm):
    store.llm = fake_llm(error=LLMError("Cannot reach Ollama", "network"))
    analysis = _analyze(store)
    assert {r.relation_type for r in analysis["candidates"]} == {"CANCELS"}
    assert analysis["relation_mode"] == "regex"
    assert any("Ollama" in w for w in analysis["warnings"])


# ----------------------------------------------------------------------------
# UI smoke test (Streamlit AppTest)
# ----------------------------------------------------------------------------


def _admin_page(root: str, runtime: str, user_id: str) -> None:
    import sys

    sys.path.insert(0, root)
    import streamlit as st

    from mixup.config import load_settings
    from mixup.store import Store
    from ui import admin_tab, common

    if "test_store" not in st.session_state:
        env = {"MIXUP_TODAY": "2026-10-07", "LLM_PROVIDER": "offline", "MIXUP_RUNTIME_DIR": runtime}
        st.session_state["test_store"] = Store(load_settings(env, use_dotenv=False))
    store = st.session_state["test_store"]
    admin_tab.render(common.UIContext(store=store, user=store.users[user_id], lang="ms"))


def _button(at, key):
    return next(b for b in at.button if b.key == key)


def test_admin_tab_end_to_end(tmp_path):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_function(_admin_page, args=(str(ROOT), str(tmp_path / "rt"), "ADMIN"), default_timeout=30)
    at.run()
    assert not at.exception
    _button(at, "admin_demo").click().run()
    assert not at.exception
    assert "admin_analysis" in at.session_state
    _button(at, "admin_commit").click().run()
    assert not at.exception
    store = at.session_state["test_store"]
    assert "SPP-1-2026" in store.docs and store.docs["SPP-1-2023"].status == "AMENDED"
    _button(at, "admin_all_SPP-1-2026").click().run()
    assert not at.exception
    assert store.docs["SPP-1-2023"].status == "CANCELLED"
    assert any("Dibatalkan oleh SPP 1/2026" in s.value for s in at.success)
    _button(at, "admin_reset").click().run()
    assert not at.exception
    assert "SPP-1-2026" not in store.docs


def test_admin_tab_hidden_for_officers(tmp_path):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_function(_admin_page, args=(str(ROOT), str(tmp_path / "rt"), "FED-T0"), default_timeout=30)
    at.run()
    assert not at.exception
    assert at.info and "Admin" in at.info[0].value
    assert not [b for b in at.button if b.key == "admin_demo"]
