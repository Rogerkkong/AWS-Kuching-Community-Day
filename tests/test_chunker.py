from app.services.ingest.chunker import chunk_document
from app.services.ingest.parse import Page

CIRCULAR = Page(1, """JABATAN PERKHIDMATAN AWAM MALAYSIA
PEKELILING PERKHIDMATAN BILANGAN 2 TAHUN 2024
CUTI REHAT
1. TUJUAN
Pekeliling ini bertujuan menetapkan peraturan cuti rehat.
4. MEMBAWA KE HADAPAN CUTI REHAT
4.1 Cuti rehat yang tidak dihabiskan boleh dibawa ke tahun
berikutnya tidak melebihi lima belas (15) hari.
4.2 Permohonan hendaklah diluluskan oleh Ketua Jabatan:
(a) melalui HRMIS; dan
(b) sebelum 31 Disember.""")
PAGE2 = Page(2, """4.3 Cuti yang melebihi had adalah luput.
9. PEMBATALAN
Pekeliling Perkhidmatan Bilangan 3 Tahun 2018 adalah dibatalkan.""")

MINUTES = Page(1, """MINIT MESYUARAT PENGURUSAN JABATAN BIL. 2/2026
Tarikh: 12 Mac 2026
KEHADIRAN
Ketua Setiausaha (Pengerusi).
PERKARA 2: PERANCANGAN CUTI REHAT AKHIR TAHUN
Unit Sumber Manusia melaporkan baki cuti yang tinggi.
KEPUTUSAN:
Mesyuarat memutuskan jadual cuti dihantar sebelum 30 September 2026.
TINDAKAN:
Semua Ketua Bahagian.""")


def test_numbered_paragraphs_clause_refs_and_pages():
    chunks = chunk_document([CIRCULAR, PAGE2], {"circular_no": "PP 2/2024", "doc_type": "circular"})
    assert [c.clause_ref for c in chunks] == ["1", "4.1-4.3", "9"]
    section4 = chunks[1]
    assert section4.page_start == 1 and section4.page_end == 2
    assert section4.breadcrumb == "PP 2/2024 > Membawa Ke Hadapan Cuti Rehat > 4.1-4.3"
    # wrapped lines are joined; (a)/(b) items stay inside clause 4.2
    assert "dibawa ke tahun berikutnya tidak melebihi lima belas (15) hari." in section4.text
    assert "(a) melalui HRMIS" in section4.text and section4.text.startswith("4. MEMBAWA KE HADAPAN")
    assert chunks[2].text.endswith("adalah dibatalkan.")


def test_minutes_split_on_perkara_keputusan_tindakan_with_date():
    chunks = chunk_document([MINUTES], {"circular_no": "MMPJ 2/2026", "doc_type": "minutes", "issue_date": "2026-03-12"})
    assert [c.clause_ref for c in chunks] == ["Kehadiran", "Perkara 2", "Perkara 2 - Keputusan", "Perkara 2 - Tindakan"]
    assert all("12 Mac 2026" in c.breadcrumb for c in chunks)
    decision = chunks[2]
    assert decision.text.startswith("PERKARA 2: PERANCANGAN CUTI REHAT AKHIR TAHUN - KEPUTUSAN:")
    assert "30 September 2026" in decision.text
    assert chunks[3].breadcrumb.endswith("> Tindakan")


def test_chunks_never_exceed_max_words():
    long = Page(1, "1. TUJUAN\n" + "\n".join(f"1.{i} " + "perkataan " * 120 for i in range(1, 8)))
    chunks = chunk_document([long], {"circular_no": "X 1/2020", "doc_type": "circular"})
    assert len(chunks) > 1
    assert all(len(c.text.split()) <= 510 for c in chunks)
