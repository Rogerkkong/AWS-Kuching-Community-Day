"""BM25 search: bilingual queries, validity filter, jurisdiction filter/boost, circular-number boost."""

from mixup.search import top_docs

TRAVEL_CHAIN = {"SPP-3-2019", "SPP-1-2023", "SPP-2-2025"}


def test_bm_query_returns_travel_chain(store, users):
    hits = store.search(users["FED-T0"], "tempoh tuntutan perjalanan", k=5)
    assert hits[0].doc.doc_id == "SPP-1-2023" and hits[0].chunk.clause_ref == "4.1"
    assert set(top_docs(hits)) <= TRAVEL_CHAIN
    assert "SPP-3-2019" not in top_docs(hits)  # cancelled: excluded by default


def test_en_query_returns_travel_chain(store, users):
    hits = store.search(users["FED-T0"], "travel claim deadline", k=5)
    assert hits[0].doc.doc_id == "SPP-1-2023" and "60 hari" in hits[0].chunk.text
    assert set(top_docs(hits)) <= TRAVEL_CHAIN
    assert hits[0].coverage == 1.0


def test_historical_search_includes_cancelled(store, users):
    hits = store.search(users["FED-T0"], "tempoh tuntutan perjalanan", k=5, statuses=None)
    assert "SPP-3-2019" in top_docs(hits)
    assert set(top_docs(hits)) <= TRAVEL_CHAIN


def test_one_off_excluded_by_default(store, users):
    default = top_docs(store.search(users["FED-T0"], "bekerja dari rumah berapa hari seminggu", k=10), 10)
    historical = top_docs(store.search(users["FED-T0"], "bekerja dari rumah berapa hari seminggu", k=10, statuses=None), 10)
    assert default[0] == "GP-1-2025" and "SE-1-2021" not in default
    assert "SE-1-2021" in historical


def test_jurisdiction_hard_filter(store, users):
    hits = store.search(users["SWK-T0"], "cuti penjagaan anak", k=10, jurisdictions={"SARAWAK"})
    assert hits and {h.doc.doc_id for h in hits} == {"PAN-2-2024"}
    hits = store.search(users["FED-T0"], "cuti penjagaan anak", k=10, jurisdictions={"FEDERAL"})
    assert "PAN-2-2024" not in {h.doc.doc_id for h in hits}


def test_jurisdiction_preference_boost(store, users):
    swk = store.search(users["SWK-T0"], "berapa hari cuti penjagaan anak", k=5, prefer_jurisdiction="SARAWAK")
    fed = store.search(users["FED-T0"], "berapa hari cuti penjagaan anak", k=5, prefer_jurisdiction="FEDERAL")
    assert swk[0].doc.doc_id == "PAN-2-2024"
    assert fed[0].doc.doc_id == "PP-4-2024"
    assert {"PAN-2-2024", "PP-4-2024"} <= set(top_docs(swk))  # the other rule is still available


def test_federal_sarawak_doc_is_home_for_both(store, users):
    hits = store.search(users["SWK-T0"], "bawa ke hadapan cuti rehat", k=3, prefer_jurisdiction="SARAWAK")
    assert hits[0].doc.doc_id == "PP-3-2024" and hits[0].doc.jurisdiction == "FEDERAL_SARAWAK"


def test_circular_number_boost(store, users):
    hits = store.search(users["FED-T0"], "Apakah kandungan Surat Pekeliling Perkhidmatan Bil. 2/2025?", k=3)
    assert hits[0].doc.doc_id == "SPP-2-2025"


def test_english_corpus_and_cluster_filter(store, users):
    hits = store.search(users["FED-T0"], "Can Terhad information be stored in the cloud?", k=5, cluster="ict-data")
    assert hits[0].doc.doc_id == "GP-2-2025" and hits[0].chunk.clause_ref == "3.2"
    assert all(h.doc.cluster == "ict-data" for h in hits)


def test_unrelated_query_has_low_coverage(store, users):
    hits = store.search(users["FED-T0"], "private contractor insurance premium", k=3)
    assert not hits or hits[0].coverage < 0.5
