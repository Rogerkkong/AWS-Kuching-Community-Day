"""Feature A - Ask (hero flow): validity filter, excluded list, citations, jurisdiction, refusal, log."""

import pytest

from mixup import ask
from mixup import logging as qlog
from mixup.llm import LLMError
from mixup.models import CANCELLED, IN_FORCE
from mixup.prompts import REFUSAL_MS

TRAP = "Berapakah kadar elaun perbatuan untuk tuntutan perjalanan?"
DEADLINE = "Berapa lama tempoh untuk mengemukakan tuntutan perjalanan?"
CHILDCARE = "How many days of childcare leave can I take?"
MIXED = "Boleh saya claim mileage kalau guna kereta sendiri?"
UNANSWERABLE = "What is the work-from-home policy for private contractors?"

RESTRICTED_DOCS = {"SOP-AUDIT-2025", "PKP-1-2025"}
RESTRICTED_MARKERS = ["RM3,000", "Unit Integriti", "KENYALANG", "Tapak B", "SOP 1/2025", "PKP 1/2025"]
REWRITE_JSON = {
    "queries_ms": ["kadar elaun perbatuan"], "queries_en": ["mileage rate"], "circular_refs": [],
    "jurisdiction_hint": None, "topic": "elaun perbatuan", "wants_history": False,
}


def cited_docs(resp):
    return [c.doc_id for c in resp.citations]


# --- validity filter + excluded list ------------------------------------------


@pytest.mark.parametrize("question", [TRAP, DEADLINE, MIXED])
def test_trap_never_cites_cancelled_and_lists_it_as_excluded(store, users, question):
    resp = ask.ask(store, users["FED-T0"], question)
    assert resp.answerable
    assert "SPP-3-2019" not in cited_docs(resp)
    assert all(c.status != CANCELLED for c in resp.citations)
    assert "RM0.55" not in resp.answer and "30 hari" not in resp.answer
    excluded = {e["doc_id"]: e for e in resp.excluded}
    assert "SPP-3-2019" in excluded
    assert excluded["SPP-3-2019"]["status_reason"] == "Dibatalkan oleh SPP 1/2023"
    assert ask.excluded_line(resp.excluded).startswith("Dikecualikan: SPP 3/2019, dibatalkan oleh SPP 1/2023")


def test_baseline_cites_the_cancelled_circular(store, users):
    resp = ask.ask(store, users["FED-T0"], TRAP, mode="baseline")
    assert resp.mode == "baseline" and resp.answerable
    assert "SPP-3-2019" in cited_docs(resp)
    assert "RM0.55" in resp.answer
    assert resp.excluded == []  # a typical chatbot does not know what it should have excluded


def test_mileage_answer_comes_from_the_amending_circular(store, users):
    resp = ask.ask(store, users["FED-T0"], TRAP)
    assert cited_docs(resp)[0] == "SPP-2-2025"
    assert resp.primary_status == IN_FORCE
    assert "RM0.80" in resp.answer and "RM0.70" not in resp.answer
    assert resp.confidence == "HIGH"
    # the amended clause SPP 1/2023 para 4.2 was swapped for the amending clause, and the answer says so
    assert any(r["doc_id"] == "SPP-1-2023" and r["clause_ref"] == "4.2" for r in resp.extra["amended_clauses"])
    assert "SPP 1/2023" in resp.answer and "dipinda oleh SPP 2/2025" in resp.answer


def test_deadline_answer_uses_unamended_clause_of_amended_circular(store, users):
    resp = ask.ask(store, users["FED-T0"], DEADLINE)
    first = resp.citations[0]
    assert (first.doc_id, first.clause_ref, first.page) == ("SPP-1-2023", "4.1", 5)
    assert "60 hari" in resp.answer
    assert resp.primary_status == "AMENDED"


def test_english_question_is_answered_from_malay_circular(store, users):
    resp = ask.ask(store, users["FED-T0"], "How long do I have to submit a travel claim?")
    assert resp.language == "en"
    assert cited_docs(resp)[0] == "SPP-1-2023" and "60 days" in resp.answer


def test_historical_mode_labels_cancelled_and_keeps_current_rule_first(store, users):
    resp = ask.ask(store, users["FED-T0"], TRAP, include_historical=True)
    assert resp.citations[0].doc_id == "SPP-2-2025"
    hist = [c for c in resp.citations if c.doc_id == "SPP-3-2019"]
    assert hist and hist[0].status == CANCELLED
    assert "Sejarah" in resp.answer and resp.excluded == []
    assert resp.answer.index("RM0.80") < resp.answer.index("RM0.55")


def test_naming_a_cancelled_circular_turns_on_history(store, users):
    resp = ask.ask(store, users["FED-T0"], "Apakah kadar perbatuan dalam SPP 3/2019?")
    assert resp.extra["historical"] is True
    assert "SPP-3-2019" in cited_docs(resp)
    assert resp.citations[0].doc_id != "SPP-3-2019"  # the current rule still comes first


def test_one_off_instruction_is_excluded_by_default(store, users):
    resp = ask.ask(store, users["FED-T0"], "Berapa hari seminggu boleh bekerja dari rumah?")
    assert cited_docs(resp)[0] == "GP-1-2025" and "2 hari seminggu" in resp.answer
    assert "SE-1-2021" not in cited_docs(resp)
    assert any(e["doc_id"] == "SE-1-2021" and e["status"] == "ONE_OFF" for e in resp.excluded)


@pytest.mark.parametrize(
    "question,expected",
    [
        ("Berapa lama tempoh untuk mengemukakan tuntutan perjalanan?", False),
        ("Berapakah kadar elaun perbatuan?", False),
        ("Apakah kadar lama elaun perbatuan?", True),
        ("Apakah peraturan sebelum ini?", True),
        ("What was the previous mileage rate?", True),
        ("Which circular was cancelled?", True),
    ],
)
def test_wants_history_detection(question, expected):
    assert ask.detect_wants_history(question) is expected


# --- jurisdiction ---------------------------------------------------------------


def test_sarawak_user_gets_state_rule_first_with_comparison(store, users):
    resp = ask.ask(store, users["SWK-T0"], CHILDCARE)
    assert resp.answerable and resp.jurisdiction_conflict
    assert cited_docs(resp)[0] == "PAN-2-2024"
    assert resp.comparison["home"]["doc_id"] == "PAN-2-2024"
    assert resp.comparison["other"]["doc_id"] == "PP-4-2024"
    assert resp.comparison["differs"] is True
    assert resp.answer.index("10 days") < resp.answer.index("7 days")


def test_federal_user_gets_federal_rule_first(store, users):
    resp = ask.ask(store, users["FED-T0"], CHILDCARE)
    assert cited_docs(resp)[0] == "PP-4-2024" and resp.jurisdiction_conflict
    assert resp.comparison["other"]["doc_id"] == "PAN-2-2024"
    assert resp.answer.index("7 days") < resp.answer.index("10 days")


def test_baseline_has_no_jurisdiction_logic(store, users):
    resp = ask.ask(store, users["SWK-T0"], CHILDCARE, mode="baseline")
    assert not resp.jurisdiction_conflict and resp.comparison is None


def test_federal_only_topic_warns_sarawak_user(store, users):
    resp = ask.ask(store, users["SWK-T0"], TRAP)
    assert cited_docs(resp)[0] == "SPP-2-2025"
    assert not resp.jurisdiction_conflict
    assert "Persekutuan" in resp.extra["jurisdiction_note"]
    assert resp.confidence != "HIGH"


# --- access control ------------------------------------------------------------


@pytest.mark.parametrize(
    "question",
    [
        "Apakah had nilai tuntutan yang dipilih untuk audit dalaman?",
        "Di manakah lokasi pusat data sandaran?",
        "SOP 1/2025 audit dalaman",
        "PKP 1/2025 KENYALANG-2 pusat data",
    ],
)
def test_clearance_zero_never_gets_restricted_content(store, users, question):
    for user_id in ("FED-T0", "SWK-T0"):
        for mode in ("navigator", "baseline"):
            for historical in (False, True):
                resp = ask.ask(store, users[user_id], question, include_historical=historical, mode=mode)
                doc_derived = {k: v for k, v in resp.extra.items() if k != "rewrite"}  # "rewrite" echoes the user's own words
                blob = " ".join(
                    [resp.answer, str(resp.citations), str(resp.excluded), str(resp.comparison), str(doc_derived),
                     " ".join(h.chunk.text for h in resp.retrieved)]
                )
                for marker in RESTRICTED_MARKERS:
                    assert marker not in blob, (question, user_id, mode, marker)
                assert not RESTRICTED_DOCS & set(cited_docs(resp))
                assert not RESTRICTED_DOCS & {e["doc_id"] for e in resp.excluded}


def test_cleared_users_do_get_restricted_answers(store, users):
    resp = ask.ask(store, users["FED-T1"], "Apakah had nilai tuntutan yang dipilih untuk audit dalaman?")
    assert cited_docs(resp)[0] == "SOP-AUDIT-2025" and "RM3,000" in resp.answer
    resp = ask.ask(store, users["ADMIN"], "Di manakah lokasi pusat data sandaran?")
    assert cited_docs(resp)[0] == "PKP-1-2025" and "KENYALANG-2" in resp.answer


# --- refusal + citation validator --------------------------------------------------


@pytest.mark.parametrize("question", [UNANSWERABLE, "What is the dress code for Fridays?", "Berapa elaun makan harian semasa kursus?", ""])
def test_unanswerable_question_is_refused(store, users, question):
    resp = ask.ask(store, users["FED-T0"], question)
    assert not resp.answerable
    assert REFUSAL_MS in resp.answer and "Unit Sumber Manusia" in resp.answer
    assert resp.citations == [] and resp.confidence == "LOW"
    assert resp.query_log_id


def test_validate_citations_drops_unknown_labels():
    text, used, dropped = ask.validate_citations("Rule A [S1][S9]. Rule B [S2, S7]. Rule C [s3].", {"S1", "S2", "S3"})
    assert text == "Rule A [S1]. Rule B [S2]. Rule C [S3]."
    assert used == ["S1", "S2", "S3"] and dropped == ["S9", "S7"]


def test_invented_citation_from_llm_is_dropped(store, users, fake_llm):
    llm = fake_llm([REWRITE_JSON, {
        "answerable": True, "language": "ms", "citations": ["S1", "S9"], "jurisdiction_note": "",
        "answer": "Kadar elaun perbatuan ialah RM0.80 sekilometer [S1]. Kadar lama ialah RM9.99 [S9].",
    }])
    store.llm = llm
    resp = ask.ask(store, users["FED-T0"], TRAP)
    assert resp.answerable and resp.llm_mode == "fake"
    assert "[S9]" not in resp.answer and "[S1]" in resp.answer
    assert [c.label for c in resp.citations] == ["S1"]
    assert any("S9" in w for w in resp.warnings)
    # the answer prompt carried status headers and no cancelled passage (validity filter before the LLM)
    prompt = llm.calls[1]["prompt"]
    assert "[S1] SPP 2/2025" in prompt and "IN_FORCE" in prompt and "RM0.55" not in prompt


def test_llm_answer_with_only_invalid_citations_is_refused(store, users, fake_llm):
    store.llm = fake_llm([REWRITE_JSON, {
        "answerable": True, "language": "ms", "citations": ["S9"], "jurisdiction_note": "",
        "answer": "Kadar ialah RM9.99 sekilometer [S9].",
    }])
    resp = ask.ask(store, users["FED-T0"], TRAP)
    assert not resp.answerable and REFUSAL_MS in resp.answer and resp.citations == []


def test_llm_says_unanswerable(store, users, fake_llm):
    store.llm = fake_llm([REWRITE_JSON, {"answerable": False, "language": "ms", "citations": [], "jurisdiction_note": "", "answer": ""}])
    resp = ask.ask(store, users["FED-T0"], TRAP)
    assert not resp.answerable and REFUSAL_MS in resp.answer
    assert any(e["doc_id"] == "SPP-3-2019" for e in resp.excluded)  # still explains what was excluded


def test_llm_failure_falls_back_to_offline(store, users, fake_llm):
    store.llm = fake_llm(error=LLMError("Model not running; using the offline result.", "network"))
    resp = ask.ask(store, users["FED-T0"], TRAP)
    assert resp.answerable and resp.llm_mode == "offline" and "RM0.80" in resp.answer
    assert any("Model not running" in w for w in resp.warnings)


def test_baseline_llm_prompt_has_no_status_headers(store, users, fake_llm):
    llm = fake_llm([REWRITE_JSON, {"answerable": True, "language": "ms", "citations": ["S1"], "jurisdiction_note": "",
                                   "answer": "RM0.80 [S1]"}])
    store.llm = llm
    ask.ask(store, users["FED-T0"], TRAP, mode="baseline")
    assert llm.calls[1]["system"] == ask.BASELINE_SYSTEM
    assert "CANCELLED" not in llm.calls[1]["prompt"] and "IN_FORCE" not in llm.calls[1]["prompt"]


# --- query log + feedback -------------------------------------------------------------


def test_every_answer_is_logged_with_feedback(store, users):
    ids = []
    for question in (TRAP, CHILDCARE, UNANSWERABLE):
        for mode in ("navigator", "baseline"):
            resp = ask.ask(store, users["SWK-T0"], question, mode=mode)
            assert resp.query_log_id.startswith("Q-")
            ids.append(resp.query_log_id)
    rows = {r["query_log_id"]: r for r in qlog.read_logs(store)}
    assert set(ids) <= set(rows)
    row = rows[ids[0]]
    assert row["user_id"] == "SWK-T0" and row["query"] == TRAP and row["mode"] == "navigator"
    assert row["answerable"] is True and "SPP-3-2019" in row["excluded"] and row["cited_docs"][0] == "SPP-2-2025"
    for key in ("language", "rewritten", "retrieved", "top_score", "confidence", "latency_ms", "llm_mode"):
        assert key in row
    qlog.add_feedback(store, ids[0], -1, "salah", user_id="SWK-T0")
    qlog.feedback(store, ids[0], 0, "SPP 1/2023 sudah dibatalkan", kind="wrong_status")
    logged = qlog.get_log(store, ids[0])
    assert [f["kind"] for f in logged["feedback"]] == ["thumbs", "wrong_status"]


def test_change_pair_and_source_passage(store, users):
    t0 = users["FED-T0"]
    assert ask.change_pair(store, t0, "SPP-2-2025") == ("SPP-1-2023", "SPP-2-2025")
    assert ask.change_pair(store, t0, "SPP-3-2019") == ("SPP-3-2019", "SPP-1-2023")
    assert ask.change_pair(store, t0, "SOP-AUDIT-2025") is None
    resp = ask.ask(store, t0, TRAP)
    assert "RM0.80 sekilometer" in ask.source_passage(store, t0, resp.citations[0])
