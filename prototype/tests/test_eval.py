"""Feature D: golden set, evaluation harness (baseline vs navigator) and analytics access rules."""

from __future__ import annotations

import csv

from mixup import analytics, ask, evaluate
from mixup import logging as qlog
from mixup.models import AskResponse, Citation


def test_golden_set_shape_and_references(store):
    rows = evaluate.load_golden(evaluate.GOLDEN_PATH)
    assert 24 <= len(rows) <= 50
    assert len({r["id"] for r in rows}) == len(rows)
    types = [r["type"] for r in rows]
    assert types.count("trap_cancelled") >= 8
    assert types.count("jurisdiction") >= 4
    assert types.count("unanswerable") >= 4
    assert types.count("access") >= 3
    langs = [r["language"] for r in rows]
    assert langs.count("ms") / len(rows) >= 0.4
    assert langs.count("en") / len(rows) >= 0.2
    assert langs.count("mixed") / len(rows) >= 0.15
    # every doc_id, clause and profile exists in the corpus
    assert evaluate.validate_golden(store, rows) == []
    for r in rows:
        if r["type"] in ("unanswerable", "access"):
            assert r["should_refuse"]
        if r["type"] == "access":
            assert all(store.docs[d].classification_level > store.users[r["user_profile"]].clearance_level for d, _ in r["must_not"])


def test_parsers():
    assert evaluate.parse_must_not("SPP-3-2019; SPP-1-2023@4.2") == [("SPP-3-2019", ""), ("SPP-1-2023", "4.2")]
    assert evaluate.parse_keywords("refusal") == []
    assert evaluate.parse_keywords("60 hari;7 days|7 hari") == [["60 hari"], ["7 days", "7 hari"]]
    assert evaluate.keywords_found("Jawapan: **7 Hari** [S1]", [["7 days", "7 hari"]])
    assert evaluate.clause_matches("4.1", "4") and evaluate.clause_matches("4.1", "4.1")
    assert not evaluate.clause_matches("4.10", "4.1") and not evaluate.clause_matches("3.1", "4")


def test_run_offline_navigator_beats_baseline(store):
    result = evaluate.run(store, evaluate.GOLDEN_PATH)
    base, nav = result["baseline"], result["navigator"]
    n = len(evaluate.load_golden())
    assert base["n"] == nav["n"] == n
    assert len(result["rows"]) == 2 * n
    for key in ("recall_at_5", "mrr", "citation_accuracy", "cancelled_citation_rate", "refusal_accuracy",
                "access_leaks", "latency_p50_ms", "latency_p95_ms"):
        assert key in nav and key in base
    assert nav["cancelled_citation_rate"] < base["cancelled_citation_rate"]
    assert nav["access_leaks"] == 0
    assert base["access_leaks"] == 0  # the clearance filter sits below both systems
    assert nav["correct_current"] > base["correct_current"]
    assert nav["jurisdiction_accuracy"] >= base["jurisdiction_accuracy"]
    assert result["meta"]["llm_provider"] == "offline"
    assert result["meta"]["problems"] == []


def test_run_is_isolated_from_demo_query_log(store):
    evaluate.run(store, evaluate.GOLDEN_PATH)
    assert qlog.read_logs(store) == []


def test_leak_checker_flags_restricted_content(store):
    checker = evaluate.LeakChecker(store)
    officer, admin = store.users["FED-T0"], store.users["ADMIN"]
    leaky = AskResponse(answer="Pusat data sandaran terletak di Tapak B dengan nama kod KENYALANG-2.", answerable=True)
    assert checker.check(officer, leaky)
    assert checker.check(admin, leaky) == []
    cited = AskResponse(
        answer="ok [S1]", answerable=True,
        citations=[Citation("S1", "SOP-AUDIT-2025", "SOP 1/2025", "t", "3.1", 3, "IN_FORCE", "", "FEDERAL", "")],
    )
    assert any("SOP-AUDIT-2025" in x for x in checker.check(officer, cited))
    assert checker.check(store.users["FED-T1"], cited) == []
    # shared boilerplate (watermark, referenced circular names) is not a leak
    clean = AskResponse(answer="SINTETIK - CONTOH SAHAJA / SYNTHETIC - SAMPLE ONLY. Surat Pekeliling Perkhidmatan Bilangan 1 Tahun 2023.")
    assert checker.check(officer, clean) == []


def test_stale_citation_counts_only_when_presented_as_current(store):
    row = next(r for r in evaluate.load_golden() if r["id"] == "G11")  # one-off WFH instruction trap
    checker = evaluate.LeakChecker(store)
    user = store.users[row["user_profile"]]
    cit = Citation("S2", "SE-1-2021", "SE 1/2021", "t", "3.1", 3, "ONE_OFF", "", "FEDERAL", "")
    labelled = AskResponse(answer="x [S2]", answerable=True, citations=[cit],
                           extra={"context": [{"label": "S2", "doc_id": "SE-1-2021", "role": "historical"}]})
    scored = evaluate.evaluate_answer(row, "navigator", labelled, user, checker, 1.0)
    assert scored["stale_as_current"] == "" and scored["stale_labelled"]
    scored = evaluate.evaluate_answer(row, "baseline", labelled, user, checker, 1.0)
    assert scored["stale_as_current"] and not scored["correct_current"]


def test_write_and_load_results(store, tmp_path):
    result = evaluate.run(store, evaluate.GOLDEN_PATH)
    paths = evaluate.write_results(result, tmp_path)
    assert {p.name for p in paths.values()} == {"summary.md", "results.csv", "results.json"}
    summary = paths["summary"].read_text(encoding="utf-8")
    assert "| Cancelled-citation rate |" in summary and "## Method" in summary and "synthetic" in summary.lower()
    with paths["csv"].open(encoding="utf-8", newline="") as fh:
        csv_rows = list(csv.DictReader(fh))
    assert len(csv_rows) == len(result["rows"]) and csv_rows[0]["id"] == "G01"
    cached = evaluate.load_cached(tmp_path)
    assert cached["navigator"]["access_leaks"] == 0
    assert "Cancelled-citation rate" in evaluate.text_table(cached)


# ----------------------------------------------------------------------------
# Analytics
# ----------------------------------------------------------------------------


def _seed_queries(store):
    users = store.users
    ask.ask(store, users["FED-T0"], "Berapakah tempoh untuk mengemukakan tuntutan elaun perjalanan?")
    ask.ask(store, users["FED-T0"], "Berapakah tempoh untuk mengemukakan tuntutan elaun perjalanan?")
    ask.ask(store, users["FED-T0"], "What is the work-from-home policy for private contractors?")
    ask.ask(store, users["SWK-T0"], "Berapa hari cuti penjagaan anak yang saya layak?")
    secret = ask.ask(store, users["ADMIN"], "Apakah nama kod pusat data sandaran KENYALANG-2?")
    ask.ask(store, users["FED-T0"], "Berapakah tempoh tuntutan perjalanan?", mode="baseline")
    return secret


def test_analytics_officer_sees_only_own_questions(store):
    _seed_queries(store)
    data = analytics.summary(store, store.users["FED-T0"])
    assert data["scope"] == "own"
    assert data["total_queries"] == 3  # baseline run is not counted
    assert data["baseline_queries"] == 1
    assert data["unanswered"] >= 1
    assert all("user_id" not in q for q in data["unanswered_questions"])
    assert data["top_questions"][0]["count"] == 2
    excluded = {e["doc_id"]: e for e in data["most_excluded"]}
    assert "SPP-3-2019" in excluded and excluded["SPP-3-2019"]["count"] == 2
    assert "Dibatalkan" in excluded["SPP-3-2019"]["status_reason"]
    other = analytics.summary(store, store.users["SWK-T0"])
    assert other["total_queries"] == 1


def test_analytics_respects_clearance_for_policy_owner(store):
    secret = _seed_queries(store)
    owner = analytics.summary(store, store.users["OWNER"])  # clearance 1: must not see the Sulit question
    assert owner["scope"] == "all"
    texts = repr(owner)
    assert "KENYALANG" not in texts and "PKP-1-2025" not in texts and "PKP 1/2025" not in texts
    assert owner["total_queries"] == 4
    assert owner["hidden_rows"] == 1
    admin = analytics.summary(store, store.users["ADMIN"])
    assert admin["total_queries"] == 5
    assert any(q["question"].startswith("Apakah nama kod") for q in admin["top_questions"])
    assert secret.query_log_id


def test_analytics_feedback_counts(store):
    resp = ask.ask(store, store.users["FED-T0"], "Berapa hari seminggu pegawai boleh bekerja dari rumah?")
    qlog.add_feedback(store, resp.query_log_id, 1, user_id="FED-T0")
    qlog.add_feedback(store, resp.query_log_id, -1, "kurang jelas", user_id="FED-T0")
    qlog.add_feedback(store, resp.query_log_id, 0, "GP 1/2025 sudah dipinda?", kind="wrong_status", user_id="FED-T0")
    data = analytics.summary(store, store.users["FED-T0"])
    assert data["feedback"] == {"up": 1, "down": 1, "wrong_status": 1}
    assert data["wrong_status_reports"][0]["comment"] == "GP 1/2025 sudah dipinda?"
    assert data["feedback_comments"][0]["comment"] == "kurang jelas"


def test_analytics_empty_log(store):
    data = analytics.summary(store, store.users["FED-T0"])
    assert data["total_queries"] == 0 and data["unanswered_rate"] == 0.0 and data["most_excluded"] == []
