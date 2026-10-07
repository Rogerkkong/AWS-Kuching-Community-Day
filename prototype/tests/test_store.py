"""Store: live ingestion, verification -> status change, persistence and Reset demo."""

from mixup import admin
from mixup.store import Store


def _upload(store):
    path = store.data_dir / "upload_demo" / "SPP-1-2026.md"
    analysis = admin.analyze_upload(store, path.name, path.read_bytes())
    return admin.commit_upload(store, analysis)


def test_upload_is_searchable_but_unverified(store, users):
    doc_id = _upload(store)
    assert doc_id == "SPP-1-2026"
    doc = store.docs[doc_id]
    assert doc.circular_no == "SPP 1/2026" and doc.origin == "upload" and doc.status == "IN_FORCE"
    # candidates are queued, statuses unchanged until verified
    pending = store.pending_relations()
    assert {r.target_doc_id for r in pending} == {"SPP-1-2023", "SPP-2-2025"}
    assert store.docs["SPP-1-2023"].status == "AMENDED"
    hits = store.search(users["FED-T0"], "tempoh tuntutan perjalanan 90 hari", k=3)
    assert hits[0].doc.doc_id == "SPP-1-2026"


def test_verification_cancels_old_chain(store):
    _upload(store)
    for rel in list(store.pending_relations()):
        admin.verify_relation(store, rel.relation_id, approve=True)
    assert store.docs["SPP-1-2023"].status == "CANCELLED"
    assert store.docs["SPP-1-2023"].status_reason == "Dibatalkan oleh SPP 1/2026"
    assert store.docs["SPP-2-2025"].status == "CANCELLED"
    assert store.docs["SPP-1-2026"].status == "IN_FORCE"


def test_rejected_relation_does_not_change_status(store):
    _upload(store)
    rel = store.pending_relations()[0]
    admin.verify_relation(store, rel.relation_id, approve=False)
    assert store.get_relation(rel.relation_id).rejected
    assert store.docs[rel.target_doc_id].status in ("AMENDED", "IN_FORCE")


def test_runtime_persists_and_reset_clears(store, settings):
    _upload(store)
    first = store.pending_relations()[0]
    admin.verify_relation(store, first.relation_id, approve=True)
    store.append_jsonl("query_log.jsonl", {"q": 1})

    reloaded = Store(settings)
    assert "SPP-1-2026" in reloaded.docs
    assert reloaded.get_relation(first.relation_id).verified
    assert reloaded.read_jsonl("query_log.jsonl") == [{"q": 1}]

    reloaded.reset_runtime()
    assert "SPP-1-2026" not in reloaded.docs
    assert reloaded.pending_relations() == []
    assert reloaded.read_jsonl("query_log.jsonl") == []
    assert reloaded.docs["SPP-1-2023"].status == "AMENDED"


def test_doc_by_circular_and_users(store):
    assert store.doc_by_circular("Surat Pekeliling Perkhidmatan Bilangan 1 Tahun 2023").doc_id == "SPP-1-2023"
    assert store.doc_by_circular("Pekeliling Am Negeri Bil. 2/2024").doc_id == "PAN-2-2024"
    assert list(store.users) == ["FED-T0", "SWK-T0", "FED-T1", "OWNER", "ADMIN"]
    assert store.users["SWK-T0"].jurisdiction == "SARAWAK" and store.users["ADMIN"].clearance_level == 2
    assert store.load_errors == []
    assert len(store.glossary) >= 50
