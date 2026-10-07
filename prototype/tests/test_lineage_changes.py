"""Feature B: lineage, what changed, alerts (guide 7.7, FR-10 / FR-12 / FR-13)."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from conftest import FakeLLM
from mixup import alerts, changes, lineage
from mixup.ingest import extract_metadata, parse_bytes
from mixup.models import AMENDS, CANCELS, REFERENCES, SUPERSEDES, Relation
from mixup.store import Store, make_document

ROOT = Path(__file__).resolve().parent.parent
RESTRICTED_MARKERS = ["RM3,000", "Unit Integriti", "KENYALANG", "SOP 1/2025", "PKP 1/2025", "SOP-AUDIT-2025",
                      "PKP-1-2025", "Prosedur Dalaman Audit", "Pelan Kesinambungan"]


def _edges(lin):
    return {(e["source"], e["type"], e["target"]) for e in lin["edges"]}


def _upload_spp_1_2026(store) -> str:
    """Ingest the live-demo circular without the admin module (store primitives only)."""
    data = (ROOT / "data" / "upload_demo" / "SPP-1-2026.md").read_bytes()
    pages = parse_bytes("SPP-1-2026.md", data, "SPP-1-2026")
    doc = make_document("SPP-1-2026", extract_metadata(pages, "SPP-1-2026.md"), {"cluster": "travel-claims"})
    return store.add_document(doc, pages, data, "SPP-1-2026.md")


def _cancel(source, target, rid, verified=True):
    return Relation(relation_id=rid, source_doc_id=source, target_doc_id=target, relation_type=CANCELS,
                    effective_date=date(2026, 10, 1), evidence_text="... adalah dibatalkan.", evidence_page=7,
                    verified=verified, origin="manual")


# ---------------------------------------------------------------------------- lineage


def test_lineage_travel_chain(store, users):
    lin = lineage.get_lineage(store, users["FED-T0"], "SPP-3-2019")
    ids = [n["doc_id"] for n in lin["nodes"] if not n.get("hidden")]
    assert {"SPP-3-2019", "SPP-1-2023", "SPP-2-2025"} <= set(ids)
    chain = [d for d in ids if d.startswith("SPP")]
    assert chain == ["SPP-3-2019", "SPP-1-2023", "SPP-2-2025"]  # ordered by date
    edges = _edges(lin)
    assert ("SPP-1-2023", CANCELS, "SPP-3-2019") in edges
    assert ("SPP-2-2025", AMENDS, "SPP-1-2023") in edges
    amend = next(e for e in lin["edges"] if e["type"] == AMENDS)
    assert amend["scope"] == "clauses: 4.2" and amend["verified"] and amend["page"] == 5
    root = next(n for n in lin["nodes"] if n["doc_id"] == "SPP-3-2019")
    assert root["is_root"] and root["status"] == "CANCELLED" and "SPP 1/2023" in root["status_reason"]
    # The same family is returned from any member.
    assert _edges(lineage.get_lineage(store, users["FED-T0"], "SPP-2-2025")) == edges


def test_lineage_other_chains(store, users):
    t0 = users["FED-T0"]
    assert ("PP-3-2024", SUPERSEDES, "PP-2-2018") in _edges(lineage.get_lineage(store, t0, "PP-2-2018"))
    assert ("GP-2-2025", SUPERSEDES, "GP-1-2022") in _edges(lineage.get_lineage(store, t0, "GP-1-2022"))
    pan = lineage.get_lineage(store, users["SWK-T0"], "PAN-2-2024")
    assert ("PAN-2-2024", REFERENCES, "PP-4-2024") in _edges(pan)


def test_lineage_hides_restricted_nodes_for_clearance_0(store, users):
    lin = lineage.get_lineage(store, users["FED-T0"], "SPP-1-2023")
    hidden = [n for n in lin["nodes"] if n.get("hidden")]
    assert len(hidden) == 1 and hidden[0]["label"] == "1 dokumen terhad disembunyikan"
    edge = next(e for e in lin["edges"] if e["source"] == hidden[0]["doc_id"])
    assert edge["evidence"] == "" and edge["relation_id"] == ""
    text = str(lin) + lineage.to_dot(lin) + lineage.to_dot(lin, "en")
    for marker in RESTRICTED_MARKERS:
        assert marker not in text
    # Terhad clearance sees the SOP, but the Sulit plan stays hidden from it.
    t1 = lineage.get_lineage(store, users["FED-T1"], "SPP-1-2023")
    assert "SOP-AUDIT-2025" in [n["doc_id"] for n in t1["nodes"]]
    gp = lineage.get_lineage(store, users["FED-T1"], "GP-2-2025")
    assert "PKP-1-2025" not in str(gp) and any(n.get("hidden") for n in gp["nodes"])
    assert "PKP-1-2025" in str(lineage.get_lineage(store, users["ADMIN"], "GP-2-2025"))


def test_change_pairs_latest_first(store, users):
    pairs = lineage.change_pairs(lineage.get_lineage(store, users["FED-T0"], "SPP-3-2019"))
    assert [(p[0], p[1], p[2]) for p in pairs] == [
        ("SPP-1-2023", "SPP-2-2025", AMENDS),
        ("SPP-3-2019", "SPP-1-2023", CANCELS),
    ]


def test_to_dot_labels_colours_and_escaping(store, users):
    dot = lineage.to_dot(lineage.get_lineage(store, users["FED-T0"], "SPP-3-2019"))
    assert dot.startswith("digraph") and "rankdir=LR" in dot
    for text in ("membatalkan", "meminda", "Dibatalkan", "Dipinda", "Berkuat kuasa", "#c62828", "#2e7d32"):
        assert text in dot
    dot_en = lineage.to_dot(lineage.get_lineage(store, users["FED-T0"], "SPP-3-2019"), "en")
    assert "cancels" in dot_en and "Cancelled" in dot_en and "perenggan" not in dot_en
    tricky = {
        "nodes": [
            {"doc_id": 'A"1', "circular_no": 'PP "1"/2020', "title": 'Tajuk "petik" \\ x', "status": "UNKNOWN",
             "hidden": False},
            {"doc_id": "B", "circular_no": "PP 2/2021", "title": "B", "status": "ONE_OFF", "hidden": False},
        ],
        "edges": [{"source": "B", "target": 'A"1', "type": SUPERSEDES, "verified": True, "scope": "whole"}],
    }
    dot = lineage.to_dot(tricky)
    assert '\\"petik\\"' in dot and '"A\\"1"' in dot and "menggantikan" in dot
    assert "Belum disahkan" in dot and "Sekali sahaja" in dot


def test_pending_relation_shown_dashed(store, users):
    doc_id = _upload_spp_1_2026(store)
    store.add_relations([_cancel(doc_id, "SPP-1-2023", "T-PEND", verified=False)])
    store.recompute()
    lin = lineage.get_lineage(store, users["FED-T0"], "SPP-3-2019")
    edge = next(e for e in lin["edges"] if e["source"] == doc_id)
    assert edge["verified"] is False and edge["type"] == CANCELS
    assert "belum disahkan" in lineage.to_dot(lin)
    assert store.docs["SPP-1-2023"].status == "AMENDED"  # unverified edges never change a status


# ---------------------------------------------------------------------------- what changed


def _row(result, clause_old):
    return next(r for r in result["aligned"] if r["clause_old"] == clause_old)


def test_what_changed_cancellation_detects_days_and_rate(store, users):
    result = changes.what_changed(store, users["FED-T0"], "SPP-3-2019", "SPP-1-2023")
    r41, r42 = _row(result, "4.1"), _row(result, "4.2")
    assert r41["type"] == "CHANGED" and r41["clause_new"] == "4.1"
    assert ("30 hari", "60 hari") in [(q["old"]["ms"], q["new"]["ms"]) for q in r41["quantities"]]
    assert ("RM0.55", "RM0.70") in [(q["old"]["ms"][:6], q["new"]["ms"][:6]) for q in r42["quantities"]]
    assert "pn-del" in r41["diff_html"] and "30" in r41["old_html"] and "60" in r41["new_html"]
    assert {"2.1", "4.5", "6"} <= {r["clause_new"] for r in result["aligned"] if r["type"] == "ADDED"}
    assert "Tempoh tuntutan berubah daripada 30 hari kepada 60 hari" in result["summary_ms"]
    assert "RM0.55 sekilometer kepada RM0.70 sekilometer" in result["summary_ms"]
    assert "from 30 days to 60 days" in result["summary_en"] and "RM0.70 per km" in result["summary_en"]
    assert result["effective_date"] == "2023-03-01" and "1 Mac 2023" in result["summary_ms"]
    assert "Persekutuan" in result["who_is_affected"]
    assert result["mode"] == "offline" and result["relation_type"] == CANCELS


def test_what_changed_amendment_only_para_4_2(store, users):
    result = changes.what_changed(store, users["FED-T0"], "SPP-1-2023", "SPP-2-2025")
    changed = [r for r in result["aligned"] if r["type"] != "SAME"]
    assert [r["clause_old"] for r in changed] == ["4.2"]
    row = changed[0]
    assert "RM0.70" in row["old_text"] and "RM0.80" in row["new_text"]
    assert [(q["old"]["ms"], q["new"]["ms"]) for q in row["quantities"]] == [("RM0.70 sekilometer", "RM0.80 sekilometer")]
    assert "perenggan 4.2" in result["summary_ms"] and "RM0.70 sekilometer kepada RM0.80 sekilometer" in result["summary_ms"]
    assert "clause 4.2 of SPP 1/2023 only" in result["summary_en"]
    assert _row(result, "4.1")["type"] == "SAME"  # the 60-day rule stays in force
    assert result["effective_date"] == "2025-07-01"


@pytest.mark.parametrize("old_id,new_id,expected", [
    ("PP-2-2018", "PP-3-2024", ("15 hari", "20 hari")),
    ("GP-1-2022", "GP-2-2025", ("30 hari bekerja", "14 hari bekerja")),
])
def test_what_changed_every_chain(store, users, old_id, new_id, expected):
    result = changes.what_changed(store, users["FED-T0"], old_id, new_id)
    assert result["aligned"] and result["counts"]["CHANGED"] >= 1
    pairs = [(h["old"], h["new"]) for h in result["highlights"]]
    assert expected in pairs
    assert result["summary_ms"] and result["summary_en"]


def test_what_changed_respects_access(store, users):
    t0 = users["FED-T0"]
    for old_id, new_id in (("SPP-1-2023", "SOP-AUDIT-2025"), ("PKP-1-2025", "GP-2-2025")):
        result = changes.what_changed(store, t0, old_id, new_id)
        assert result["aligned"] == [] and result["summary_ms"] == "" and result["warnings"]
        for marker in RESTRICTED_MARKERS:
            assert marker not in json.dumps(result, default=str)
    assert changes.what_changed(store, users["FED-T1"], "SPP-1-2023", "SOP-AUDIT-2025")["aligned"]


def test_what_changed_is_cached(store, users):
    first = changes.what_changed(store, users["FED-T0"], "SPP-3-2019", "SPP-1-2023")
    cache = store.read_json(changes.CACHE, {})
    assert len(cache) == 1 and next(iter(cache)).startswith("SPP-3-2019|SPP-1-2023|offline|")
    second = changes.what_changed(store, users["FED-T0"], "SPP-3-2019", "SPP-1-2023")
    assert second["summary_ms"] == first["summary_ms"] and len(second["aligned"]) == len(first["aligned"])


def test_diff_html_is_escaped():
    inline, old_html, new_html = changes.word_diff("<b>lama</b> 30 hari", "<script>x</script> 60 hari")
    assert "<script>" not in inline + old_html + new_html and "&lt;script&gt;" in new_html
    assert "<del" in inline and "<ins" in inline


def test_quantities_ignore_circular_years():
    q = changes.quantities("Surat Pekeliling Bilangan 1 Tahun 2023: tempoh 30 hari, RM0.80 sekilometer, 5%.")
    assert [(x["kind"], x["ms"]) for x in q] == [("duration", "30 hari"), ("amount", "RM0.80 sekilometer"),
                                                 ("percent", "5%")]


def test_llm_summary_used_and_numbers_checked(settings, users):
    good = {"summary_ms": "Perenggan 4.1: tempoh tuntutan kini 60 hari, bukan 30 hari.",
            "summary_en": "Clause 4.1: the claim period is now 60 days instead of 30.",
            "effective_date": "2023-03-01", "who_is_affected": "Pegawai Persekutuan", "changes": []}
    store = Store(settings, llm=FakeLLM([good]))
    result = changes.what_changed(store, users["FED-T0"], "SPP-3-2019", "SPP-1-2023")
    assert result["mode"] == "fake" and result["summary_ms"] == good["summary_ms"]
    assert "CHANGED" in store.llm.calls[0]["prompt"] and "SPP 3/2019" in store.llm.calls[0]["prompt"]

    invented = dict(good, summary_en="Clause 4.1: the claim period is now 75 days.")
    store = Store(settings, llm=FakeLLM([invented]))
    result = changes.what_changed(store, users["FED-T0"], "SPP-3-2019", "SPP-1-2023", use_cache=False)
    assert result["mode"] == "offline" and result["warnings"]
    assert "60 hari" in result["summary_ms"]

    store = Store(settings, llm=FakeLLM(error=RuntimeError("down")))
    result = changes.what_changed(store, users["FED-T0"], "SPP-3-2019", "SPP-1-2023", use_cache=False)
    assert result["mode"] == "offline" and result["warnings"] and "30 hari" in result["summary_ms"]


# ---------------------------------------------------------------------------- alerts


def test_subscriptions_seed_and_toggle(store, users):
    seeded = alerts.subscriptions(store)
    followers = {s["user_id"] for s in seeded if s["cluster"] == "travel-claims"}
    assert {"FED-T0", "SWK-T0"} <= followers and "ADMIN" not in followers
    alerts.subscribe(store, "ADMIN", doc_id="GP-2-2025")
    alerts.subscribe(store, "ADMIN", doc_id="GP-2-2025")
    assert alerts.is_following(store, "ADMIN", doc_id="GP-2-2025")
    assert len(alerts.subscriptions(store, "ADMIN")) == 1
    assert alerts.unsubscribe(store, "ADMIN", doc_id="GP-2-2025")
    assert not alerts.is_following(store, "ADMIN", doc_id="GP-2-2025")


def test_new_cancel_relation_notifies_followers(store, users):
    doc_id = _upload_spp_1_2026(store)
    pending = _cancel(doc_id, "SPP-1-2023", "T-1", verified=False)
    store.add_relations([pending])
    assert alerts.on_new_relations(store, [pending]) == []  # unverified: no alert yet

    store.update_relation("T-1", verified=True)
    store.recompute()
    assert store.docs["SPP-1-2023"].status == "CANCELLED"
    created = alerts.on_new_relations(store, [store.get_relation("T-1")])
    assert {n["user_id"] for n in created} >= {"FED-T0", "SWK-T0"}
    assert "ADMIN" not in {n["user_id"] for n in created}

    notes = alerts.notifications(store, users["FED-T0"])
    assert len(notes) == 1 and not notes[0]["read"]
    note = notes[0]
    assert note["doc_id"] == "SPP-1-2023" and note["new_doc_id"] == doc_id
    assert note["title"] == "SPP 1/2023 dibatalkan oleh SPP 1/2026"
    assert "60 hari kepada 90 hari" in note["summary_ms"] and "RM0.85" in note["summary_en"]
    assert alerts.notifications(store, users["ADMIN"]) == []

    # Idempotent per (user, relation); read state persists.
    assert alerts.on_new_relations(store, [store.get_relation("T-1")]) == []
    alerts.mark_all_read(store, users["FED-T0"])
    assert alerts.unread_count(store, users["FED-T0"]) == 0
    assert alerts.unread_count(store, users["SWK-T0"]) == 1


def test_document_followers_and_access(store, users):
    """A follower who may not see the new document gets nothing (access is enforced in code)."""
    alerts.subscribe(store, "FED-T0", doc_id="GP-2-2025")
    alerts.subscribe(store, "ADMIN", doc_id="GP-2-2025")
    rel = _cancel("PKP-1-2025", "GP-2-2025", "T-SULIT")  # a Sulit document cancels an open one
    store.add_relations([rel])
    store.recompute()
    created = alerts.on_new_relations(store, [rel])
    assert [n["user_id"] for n in created] == ["ADMIN"]
    for marker in RESTRICTED_MARKERS:
        assert marker not in json.dumps(alerts.notifications(store, users["FED-T0"]))


def test_references_do_not_notify(store):
    rel = Relation(relation_id="T-REF", source_doc_id="MINIT-3-2025", target_doc_id="SPP-1-2023",
                   relation_type=REFERENCES, verified=True)
    assert alerts.on_new_relations(store, [rel]) == []


def test_status_reason_masks_hidden_canceller(store, users):
    rel = _cancel("PKP-1-2025", "GP-2-2025", "T-SULIT-2")
    store.add_relations([rel])
    store.recompute()
    node = next(n for n in lineage.get_lineage(store, users["FED-T0"], "GP-2-2025")["nodes"]
                if n["doc_id"] == "GP-2-2025")
    assert node["status"] == "CANCELLED" and "PKP" not in node["status_reason"]
    assert "terhad" in node["status_reason"]


# ---------------------------------------------------------------------------- UI smoke test


def _tab_script(runtime_dir: str, user_id: str, lang: str):
    """Runs inside Streamlit's AppTest: draw only the lineage tab."""
    import streamlit as st

    from mixup.config import load_settings
    from mixup.store import Store
    from ui import common, lineage_tab

    if "test_store" not in st.session_state:
        st.session_state["test_store"] = Store(load_settings(
            {"MIXUP_TODAY": "2026-10-07", "LLM_PROVIDER": "offline", "MIXUP_RUNTIME_DIR": runtime_dir},
            use_dotenv=False))
    store = st.session_state["test_store"]
    lineage_tab.render(common.UIContext(store=store, user=store.users[user_id], lang=lang))


@pytest.mark.parametrize("user_id,lang", [("FED-T0", "ms"), ("SWK-T0", "en"), ("ADMIN", "ms")])
def test_lineage_tab_renders(tmp_path, user_id, lang):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_function(_tab_script, args=(str(tmp_path / "rt"), user_id, lang), default_timeout=60)
    at.run()
    assert not at.exception
    pair = next(s for s in at.selectbox if s.key == "lineage_pair_SPP-3-2019")
    pair.set_value("SPP-3-2019|SPP-1-2023").run()
    assert not at.exception
    shown = " ".join(m.value for m in list(at.markdown) + list(at.caption))
    assert ("30 hari" in shown and "60 hari" in shown) or ("30 days" in shown and "60 days" in shown)
    if user_id != "ADMIN":
        for marker in RESTRICTED_MARKERS:
            assert marker not in shown
