from datetime import date

from app.services.validity.status import compute_status

TODAY = date(2026, 10, 7)


def doc(**kw):
    base = {"doc_type": "circular", "one_off": 0, "expiry_date": None, "effective_date": "2024-01-01", "issue_date": "2023-12-01"}
    return {**base, **kw}


def rel(kind, src="PP 9/2025", eff=None, src_eff="2025-01-01", src_issue="2024-12-01"):
    return {"relation_type": kind, "source_no": src, "effective_date": eff, "source_effective_date": src_eff,
            "source_issue_date": src_issue}


def test_record_for_minutes_and_reports_even_if_targeted():
    assert compute_status(doc(doc_type="minutes", issue_date="2026-03-12"), [rel("CANCELS")], TODAY) == ("RECORD", "Rekod bertarikh 12 Mac 2026")
    assert compute_status(doc(doc_type="report", issue_date="2025-01-05"), [], TODAY)[0] == "RECORD"


def test_cancelled_by_verified_cancel_or_supersede():
    assert compute_status(doc(), [rel("CANCELS")], TODAY) == ("CANCELLED", "Dibatalkan oleh PP 9/2025")
    assert compute_status(doc(), [rel("SUPERSEDES", src="PP 2/2024")], TODAY) == ("CANCELLED", "Dibatalkan oleh PP 2/2024")


def test_cancellation_date_precedence_and_future_dates():
    assert compute_status(doc(), [rel("CANCELS", eff="2027-01-01")], TODAY)[0] == "IN_FORCE"  # relation date first
    assert compute_status(doc(), [rel("CANCELS", src_eff="2027-01-01")], TODAY)[0] == "IN_FORCE"  # then source effective
    assert compute_status(doc(), [rel("CANCELS", src_eff=None, src_issue="2025-05-01")], TODAY)[0] == "CANCELLED"  # then issue


def test_one_off_expiry_amended_in_force_unknown():
    assert compute_status(doc(one_off=1), [], TODAY)[0] == "ONE_OFF"
    assert compute_status(doc(expiry_date="2026-01-01"), [], TODAY) == ("CANCELLED", "Tamat tempoh")
    assert compute_status(doc(), [rel("AMENDS", src="PP 5/2025"), rel("AMENDS", src="PP 6/2025")], TODAY) == (
        "AMENDED", "Dipinda oleh PP 5/2025, PP 6/2025")
    assert compute_status(doc(), [rel("REFERENCES")], TODAY)[0] == "IN_FORCE"
    assert compute_status(doc(effective_date=None), [], TODAY)[0] == "UNKNOWN"
    assert compute_status(doc(effective_date="2027-01-01"), [], TODAY)[0] == "UNKNOWN"


def test_rule_order_cancel_before_one_off():
    assert compute_status(doc(one_off=1), [rel("CANCELS"), rel("AMENDS")], TODAY)[0] == "CANCELLED"


def test_synthetic_corpus_statuses(env):
    from app import db

    conn = db.connect(env.settings.publisher_db)
    got = {r["circular_no"]: (r["status"], r["status_reason"]) for r in conn.execute("SELECT * FROM documents")}
    conn.close()
    assert got["PP 3/2018"] == ("CANCELLED", "Dibatalkan oleh PP 2/2024")
    assert got["PP 2/2024"] == ("AMENDED", "Dipinda oleh PP 5/2025")
    assert got["PP 5/2025"][0] == "IN_FORCE"
    assert got["PAS 4/2023"][0] == "IN_FORCE"
    assert got["MMPJ 2/2026"] == ("RECORD", "Rekod bertarikh 12 Mac 2026")
    assert got["MJKK 1/2026"][0] == "RECORD"
    assert got["GP 1/2026"][0] == "IN_FORCE"
