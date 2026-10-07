from pathlib import Path

from app.services.ingest.metadata import parse_malay_date, regex_metadata
from app.services.ingest.parse import parse_pdf

ROOT = Path(__file__).resolve().parent.parent


def test_malay_dates():
    assert parse_malay_date("Tarikh: 12 Mac 2026") == "2026-03-12"
    assert parse_malay_date("berkuat kuasa mulai 1 Ogos 2024") == "2024-08-01"
    assert parse_malay_date("tiada tarikh") is None


def test_metadata_regex_on_synthetic_pdfs():
    m = regex_metadata(parse_pdf(ROOT / "data" / "raw" / "PP-3-2018.pdf"))
    assert m["circular_no"] == "PP 3/2018"  # not the SPP 5/2011 cited in its body
    assert m["issue_date"] == "2018-03-15" and m["effective_date"] == "2018-04-01"
    assert m["jurisdiction"] == "FEDERAL" and m["doc_type"] == "circular"
    sw = regex_metadata(parse_pdf(ROOT / "data" / "raw" / "PAS-4-2023.pdf"))
    assert sw["circular_no"] == "PAS 4/2023" and sw["jurisdiction"] == "SARAWAK"
    mm = regex_metadata(parse_pdf(ROOT / "data" / "raw" / "MMPJ-2-2026.pdf"))
    assert mm["doc_type"] == "minutes" and mm["issue_date"] == "2026-03-12"
    gp = regex_metadata(parse_pdf(ROOT / "data" / "raw" / "GP-1-2026-TERHAD.pdf"))
    assert gp["classification_level"] == 1


def test_watermark_removed_from_text_but_present_on_pages():
    import pymupdf

    pages = parse_pdf(ROOT / "data" / "raw" / "PP-2-2024.pdf")
    assert all("SINTETIK" not in p.text for p in pages)
    with pymupdf.open(ROOT / "data" / "raw" / "PP-2-2024.pdf") as d:
        assert all("SINTETIK - CONTOH SAHAJA" in page.get_text() for page in d)


def test_prompts_are_present_verbatim():
    from app.services.generation import prompts

    assert prompts.ANSWER_SYSTEM.startswith("You are Pekeliling Navigator, an offline assistant")
    assert '"ANSWERABLE: YES" or "ANSWERABLE: NO"' in prompts.ANSWER_SYSTEM
    assert "Do not answer the question." in prompts.QUERY_REWRITE
    assert prompts.METADATA.format(text="x").endswith("TEXT:\nx")
    assert "Return only a JSON list." in prompts.RELATION
    assert "never invent numbers, dates or groups of people" in prompts.CHANGE_SUMMARY


def test_glossary_expansion_and_long_form_refs(env):
    from app.services.retrieval.rewrite import rewrite

    user = {"jurisdiction": "FEDERAL", "grade": "N41", "scheme": "x"}
    rq = rewrite("How many days of annual leave can I carry forward?", user, None, env.settings, use_llm=False)
    assert "cuti rehat" in rq.expansions and "bawa ke hadapan" in rq.expansions
    rq2 = rewrite("Adakah PP 3/2018 masih terpakai?", user, None, env.settings, use_llm=False)
    assert rq2.circular_refs == ["PP 3/2018"]
    assert "Pekeliling Perkhidmatan Bilangan 3 Tahun 2018" in rq2.expansions
    assert rq2.wants_history is False
    assert rewrite("Apakah peraturan lama sebelum ini?", user, None, env.settings, use_llm=False).wants_history is True
