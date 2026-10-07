"""Relation candidates (regex), relations.csv ground truth and LLM classification."""

from mixup.ingest import extract_metadata, parse_file
from mixup.llm import LLMError
from mixup.relations import classify_with_llm, extract_candidates, load_relations_csv
from mixup.store import make_document


def test_ground_truth_relations_are_verified(store):
    rels = load_relations_csv(store.data_dir / "relations.csv")
    assert len(rels) >= 9 and all(r.verified for r in rels)
    chain = {(r.source_doc_id, r.target_doc_id, r.relation_type) for r in rels}
    assert ("SPP-1-2023", "SPP-3-2019", "CANCELS") in chain
    assert ("SPP-2-2025", "SPP-1-2023", "AMENDS") in chain
    assert ("GP-2-2025", "GP-1-2022", "SUPERSEDES") in chain


def _upload_doc(store):
    pages = parse_file(store.data_dir / "upload_demo" / "SPP-1-2026.md", "SPP-1-2026")
    return make_document("SPP-1-2026", extract_metadata(pages)), pages


def test_upload_demo_candidates_cancel_both(store):
    doc, pages = _upload_doc(store)
    cands = extract_candidates(doc, pages, store.circular_map())
    by_target = {c.target_doc_id: c for c in cands}
    assert set(by_target) == {"SPP-1-2023", "SPP-2-2025"}
    for c in cands:
        assert c.relation_type == "CANCELS" and not c.verified and c.origin == "extracted"
        assert c.evidence_page == 7 and "dibatalkan" in c.evidence_text


def test_amends_with_clause_scope(store):
    doc = store.docs["SPP-2-2025"]
    cands = extract_candidates(doc, store.pages["SPP-2-2025"], store.circular_map())
    amend = [c for c in cands if c.relation_type == "AMENDS"]
    assert amend and amend[0].target_doc_id == "SPP-1-2023" and amend[0].scope == "clauses: 4.2"


def test_supersedes_and_references(store):
    cands = extract_candidates(store.docs["PP-3-2024"], store.pages["PP-3-2024"], store.circular_map())
    assert [(c.target_doc_id, c.relation_type) for c in cands] == [("PP-2-2018", "SUPERSEDES")]
    refs = extract_candidates(store.docs["SOP-AUDIT-2025"], store.pages["SOP-AUDIT-2025"], store.circular_map())
    assert [(c.target_doc_id, c.relation_type) for c in refs] == [("SPP-1-2023", "REFERENCES")]


def test_llm_classification_overrides_regex(store, fake_llm):
    doc, pages = _upload_doc(store)
    cands = extract_candidates(doc, pages, store.circular_map())
    reply = {"relations": [{"ref_text": cands[0].target_ref_text, "relation": "SUPERSEDES", "scope": "whole",
                            "effective_date": "2026-10-01", "evidence": "x", "page": 7, "confidence": 0.9}]}
    llm = fake_llm([reply])
    out, warning = classify_with_llm(llm, doc, cands)
    assert warning is None and out[0].relation_type == "SUPERSEDES" and out[0].confidence == 0.9
    assert "CANDIDATES" in llm.calls[0]["prompt"]


def test_llm_failure_keeps_regex(store, fake_llm):
    doc, pages = _upload_doc(store)
    cands = extract_candidates(doc, pages, store.circular_map())
    out, warning = classify_with_llm(fake_llm(error=LLMError("down", "network")), doc, cands)
    assert warning and all(c.relation_type == "CANCELS" for c in out)
