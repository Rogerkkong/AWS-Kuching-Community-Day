"""Status engine: every branch of guide 7.3, plus the corpus ground truth."""

from datetime import date

import pytest

from mixup.models import AMENDS, CANCELS, REFERENCES, SUPERSEDES, Document, Relation
from mixup.status import compute_status, recompute_all

TODAY = date(2026, 10, 7)


def doc(doc_id, **kw):
    return Document(doc_id=doc_id, circular_no=kw.pop("circular_no", doc_id.replace("-", " ", 1).replace("-", "/")), **kw)


def rel(source, target, rtype, verified=True, **kw):
    return Relation(relation_id=f"{source}>{target}", source_doc_id=source, target_doc_id=target,
                    relation_type=rtype, verified=verified, **kw)


@pytest.fixture
def docs():
    return {
        "OLD": doc("OLD", circular_no="PP 1/2020", effective_date=date(2020, 1, 1)),
        "NEW": doc("NEW", circular_no="PP 2/2024", effective_date=date(2024, 1, 1)),
        "FUT": doc("FUT", circular_no="PP 9/2027", effective_date=date(2027, 1, 1)),
        "AM1": doc("AM1", circular_no="SPP 1/2025", effective_date=date(2025, 1, 1)),
        "AM2": doc("AM2", circular_no="SPP 2/2025", effective_date=date(2025, 6, 1)),
    }


def test_cancelled_by_verified_cancels(docs):
    status, reason = compute_status(docs["OLD"], [rel("NEW", "OLD", CANCELS)], docs, TODAY)
    assert (status, reason) == ("CANCELLED", "Dibatalkan oleh PP 2/2024")


def test_cancelled_by_verified_supersedes(docs):
    status, reason = compute_status(docs["OLD"], [rel("NEW", "OLD", SUPERSEDES)], docs, TODAY)
    assert status == "CANCELLED" and reason == "Dibatalkan oleh PP 2/2024"


def test_future_cancellation_not_yet_effective(docs):
    # relation date missing -> source effective date (2027) -> not yet effective
    status, _ = compute_status(docs["OLD"], [rel("FUT", "OLD", CANCELS)], docs, TODAY)
    assert status == "IN_FORCE"


def test_relation_date_wins_over_source_date(docs):
    r = rel("FUT", "OLD", CANCELS, effective_date=date(2026, 1, 1))
    assert compute_status(docs["OLD"], [r], docs, TODAY)[0] == "CANCELLED"


def test_unverified_and_rejected_relations_ignored(docs):
    rels = [rel("NEW", "OLD", CANCELS, verified=False), rel("AM1", "OLD", CANCELS, rejected=True)]
    assert compute_status(docs["OLD"], rels, docs, TODAY)[0] == "IN_FORCE"


def test_one_off():
    d = Document(doc_id="SE", one_off=True, effective_date=date(2021, 1, 1), expiry_date=date(2021, 6, 1))
    assert compute_status(d, [], {"SE": d}, TODAY) == ("ONE_OFF", "Arahan sekali sahaja")


def test_expired():
    d = Document(doc_id="X", effective_date=date(2020, 1, 1), expiry_date=date(2026, 10, 7))
    assert compute_status(d, [], {"X": d}, TODAY) == ("CANCELLED", "Tamat tempoh")


def test_not_expired_yet():
    d = Document(doc_id="X", effective_date=date(2020, 1, 1), expiry_date=date(2026, 10, 8))
    assert compute_status(d, [], {"X": d}, TODAY)[0] == "IN_FORCE"


def test_amended_lists_all_amenders(docs):
    rels = [rel("AM1", "OLD", AMENDS), rel("AM2", "OLD", AMENDS), rel("NEW", "OLD", REFERENCES)]
    assert compute_status(docs["OLD"], rels, docs, TODAY) == ("AMENDED", "Dipinda oleh SPP 1/2025, SPP 2/2025")


def test_cancellation_beats_amendment(docs):
    rels = [rel("AM1", "OLD", AMENDS), rel("NEW", "OLD", CANCELS)]
    assert compute_status(docs["OLD"], rels, docs, TODAY)[0] == "CANCELLED"


def test_in_force_and_unknown():
    a = Document(doc_id="A", effective_date=date(2026, 10, 7))
    b = Document(doc_id="B")
    c = Document(doc_id="C", effective_date=date(2026, 10, 8))
    docs = {"A": a, "B": b, "C": c}
    assert compute_status(a, [], docs, TODAY) == ("IN_FORCE", "")
    assert compute_status(b, [], docs, TODAY) == ("UNKNOWN", "Status belum disahkan")
    assert compute_status(c, [], docs, TODAY)[0] == "UNKNOWN"


def test_recompute_all_reports_changes(docs):
    changes = recompute_all(docs, [rel("NEW", "OLD", CANCELS)], TODAY)
    assert changes["OLD"][1] == "CANCELLED"
    assert docs["FUT"].status == "UNKNOWN"


def test_corpus_ground_truth(store):
    expected = {
        "SPP-3-2019": ("CANCELLED", "Dibatalkan oleh SPP 1/2023"),
        "SPP-1-2023": ("AMENDED", "Dipinda oleh SPP 2/2025"),
        "SPP-2-2025": ("IN_FORCE", ""),
        "PP-2-2018": ("CANCELLED", "Dibatalkan oleh PP 3/2024"),
        "PP-3-2024": ("IN_FORCE", ""),
        "PP-4-2024": ("IN_FORCE", ""),
        "PAN-2-2024": ("IN_FORCE", ""),
        "SE-1-2021": ("ONE_OFF", "Arahan sekali sahaja"),
        "GP-1-2025": ("IN_FORCE", ""),
        "GP-1-2022": ("CANCELLED", "Dibatalkan oleh GP 2/2025"),
        "GP-2-2025": ("IN_FORCE", ""),
    }
    for doc_id, want in expected.items():
        d = store.docs[doc_id]
        assert (d.status, d.status_reason) == want, doc_id


def test_mixup_today_controls_status(tmp_path):
    from conftest import make_settings
    from mixup.store import Store

    s = Store(make_settings(tmp_path, MIXUP_TODAY="2020-01-01"))
    assert s.docs["SPP-3-2019"].status == "IN_FORCE"  # SPP 1/2023 not effective yet in 2020
    assert s.docs["SPP-2-2025"].status == "UNKNOWN"  # not yet effective
