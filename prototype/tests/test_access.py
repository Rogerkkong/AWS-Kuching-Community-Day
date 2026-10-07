"""Access control (release blocker): a clearance-0 user never receives Terhad/Sulit content."""

import pytest

from mixup import access, alerts, ask, lineage
from mixup.models import CANCELLED

RESTRICTED_MARKERS = ["RM3,000", "Unit Integriti", "KENYALANG", "Tapak B", "SOP 1/2025", "PKP 1/2025",
                      "Prosedur Dalaman Audit", "Pelan Kesinambungan"]
QUERIES = [
    "Apakah had nilai tuntutan yang dipilih untuk audit dalaman?",
    "audit dalaman tuntutan perjalanan RM3,000",
    "Di manakah lokasi pusat data sandaran?",
    "backup data centre recovery time",
    "SOP 1/2025",
    "PKP 1/2025 KENYALANG-2",
    "tempoh tuntutan perjalanan",
]


def test_visible_docs_by_clearance(store, users):
    t0 = access.visible_docs(store, users["FED-T0"])
    assert "SOP-AUDIT-2025" not in t0 and "PKP-1-2025" not in t0
    t1 = access.visible_docs(store, users["FED-T1"])
    assert "SOP-AUDIT-2025" in t1 and "PKP-1-2025" not in t1
    assert "PKP-1-2025" in access.visible_docs(store, users["ADMIN"])
    assert "SOP-AUDIT-2025" not in access.visible_docs(store, None)  # missing user = clearance 0


@pytest.mark.parametrize("query", QUERIES)
@pytest.mark.parametrize("statuses", ["default", None])
def test_search_never_leaks(store, users, query, statuses):
    kwargs = {} if statuses == "default" else {"statuses": None}
    for user in users.values():
        for hit in store.search(user, query, k=20, **kwargs):
            assert hit.doc.classification_level <= user.clearance_level


def test_higher_clearance_does_find_restricted(store, users):
    hits = store.search(users["FED-T1"], "audit dalaman tuntutan RM3,000", k=3)
    assert hits[0].doc.doc_id == "SOP-AUDIT-2025"
    hits = store.search(users["ADMIN"], "pusat data sandaran KENYALANG", k=3)
    assert hits[0].doc.doc_id == "PKP-1-2025"


def test_single_document_paths_fail_closed(store, users):
    t0 = users["FED-T0"]
    for doc_id in ("SOP-AUDIT-2025", "PKP-1-2025"):
        assert access.get_doc(store, t0, doc_id) is None
        assert access.get_pages(store, t0, doc_id) == []
        assert access.get_chunks(store, t0, doc_id) == []
    assert access.get_pages(store, users["ADMIN"], "PKP-1-2025")


def test_filter_helpers(store, users):
    t0 = users["FED-T0"]
    hits = store.search(users["ADMIN"], "audit dalaman pusat data sandaran", k=20, statuses=None)
    assert any(h.doc.classification_level > 0 for h in hits)
    assert all(h.doc.classification_level == 0 for h in access.filter_chunks(store, t0, hits))
    rows = [{"doc_id": "SOP-AUDIT-2025"}, {"doc_id": "SPP-1-2023"}, {"doc_id": "NOPE"}]
    assert access.filter_docs(store, t0, rows) == [{"doc_id": "SPP-1-2023"}]
    rels = access.filter_relations(store, t0, store.verified_relations())
    assert all("SOP-AUDIT-2025" not in (r.source_doc_id, r.target_doc_id) for r in rels)


def test_excluded_list_search_never_leaks(store, users):
    """The excluded list re-runs search without the status filter: still clearance-filtered."""
    t0 = users["FED-T0"]
    hits = store.search(t0, "audit tuntutan perjalanan", k=20, statuses=None)
    cancelled = [h for h in hits if h.doc.status == CANCELLED]
    assert all(h.doc.classification_level == 0 for h in cancelled)


def test_lineage_hides_restricted_nodes(store, users):
    result = lineage.get_lineage(store, users["FED-T0"], "SPP-1-2023")
    text = str(result)
    assert "disembunyikan" in text
    for marker in RESTRICTED_MARKERS + ["SOP-AUDIT-2025"]:
        assert marker not in text
    assert lineage.get_lineage(store, users["FED-T0"], "SOP-AUDIT-2025")["nodes"] == []


@pytest.mark.parametrize("query", QUERIES[:4])
def test_ask_never_leaks(store, users, query):
    t0 = users["FED-T0"]
    for mode in ("navigator", "baseline"):
        for historical in (False, True):
            resp = ask.ask(store, t0, query, include_historical=historical, mode=mode)
            blob = " ".join([resp.answer, str(resp.citations), str(resp.excluded), str(resp.comparison),
                             " ".join(h.chunk.text for h in resp.retrieved)])
            for marker in RESTRICTED_MARKERS:
                assert marker not in blob, (query, mode, marker)
            assert all(c.doc_id not in ("SOP-AUDIT-2025", "PKP-1-2025") for c in resp.citations)


def test_notifications_are_access_filtered(store, users):
    store.write_json(alerts.NOTIFICATIONS, [
        {"id": "n1", "user_id": "FED-T0", "doc_id": "SOP-AUDIT-2025", "title": "x", "created_at": "1", "read": False},
        {"id": "n2", "user_id": "FED-T0", "doc_id": "SPP-1-2023", "title": "y", "created_at": "2", "read": False},
    ])
    ids = [n["id"] for n in alerts.notifications(store, users["FED-T0"])]
    assert ids == ["n2"]
