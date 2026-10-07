from app.services.ingest.parse import Page
from app.services.ingest.relations import find_candidates, find_refs, refs_in_query


def test_reference_regex_examples():
    assert find_refs("Rujuk PP Bil. 3/2024 untuk butiran.")[0][0] == "PP 3/2024"
    assert find_refs("Surat Pekeliling Perkhidmatan Bilangan 5 Tahun 2018 adalah dibatalkan.")[0][0] == "SPP 5/2018"
    assert find_refs("Pekeliling Perkhidmatan Bilangan 3 Tahun 2018 adalah dibatalkan")[0][0] == "PP 3/2018"
    assert find_refs("Pekeliling Perbendaharaan Bil. 1/2020")[0][0] == "PB 1/2020"
    assert find_refs("Pekeliling Am Sarawak Bilangan 6 Tahun 2016 dibatalkan")[0][0] == "PAS 6/2016"


def test_query_refs_without_bil():
    assert refs_in_query("Adakah PP 3/2018 masih terpakai?") == ["PP 3/2018"]
    assert refs_in_query("spp 5/2011 dan PAS 4/2023") == ["SPP 5/2011", "PAS 4/2023"]


def test_candidates_need_trigger_words_and_skip_self():
    pages = [Page(1, "PEKELILING PERKHIDMATAN BILANGAN 2 TAHUN 2024\n"
                     "Rujuk Pekeliling Perkhidmatan Bilangan 7 Tahun 2021 untuk tatacara.\n"
                     "Pekeliling Perkhidmatan Bilangan 3 Tahun 2018 adalah dibatalkan dan digantikan dengan Pekeliling ini.")]
    cands = find_candidates(pages, "PP 2/2024")
    assert [c["ref_text"] for c in cands] == ["PP 3/2018"]
    assert cands[0]["page"] == 1 and "dibatalkan" in cands[0]["sentence"]


def test_extracted_relations_are_unverified_until_approved(env):
    from app import db

    conn = db.connect(env.settings.publisher_db)
    rows = {(r["target_ref_text"], r["relation_type"]): r["verified"] for r in conn.execute("SELECT * FROM relations")}
    conn.close()
    assert rows[("PP 3/2018", "SUPERSEDES")] == 1  # merged with data/relations.csv ground truth
    assert rows[("PP 2/2024", "AMENDS")] == 1
    assert rows[("SPP 5/2011", "CANCELS")] == 0  # extracted only: waits in the verification queue
