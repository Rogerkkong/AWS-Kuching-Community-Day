"""Reference regex normalisation, glossary expansion, tokenizer, language detection."""

import pytest

from mixup.textutil import detect_language, expand_query, find_refs, normalize_circular_no, series_for, tokenize


@pytest.mark.parametrize(
    "text, expected",
    [
        ("PP Bil. 3/2024", "PP 3/2024"),
        ("Surat Pekeliling Perkhidmatan Bilangan 5 Tahun 2018", "SPP 5/2018"),
        ("SPP 1/2023", "SPP 1/2023"),
        ("spp bil 1/2023", "SPP 1/2023"),
        ("Pekeliling Perkhidmatan Bil. 4 Tahun 2024", "PP 4/2024"),
        ("Pekeliling Perkhidmatan Bilangan 03 Tahun 2024", "PP 3/2024"),
        ("Pekeliling Am Negeri Bil. 2/2024", "PAN 2/2024"),
        ("Surat Edaran Bilangan 1 Tahun 2021", "SE 1/2021"),
        ("Pekeliling Perbendaharaan Bil. 2/2020", "PB 2/2020"),
        ("Garis Panduan Bil. 1/2022", "GP 1/2022"),
        ("GUIDELINE NO. 2 OF 2025 (GARIS PANDUAN BIL. 2/2025)", "GP 2/2025"),
    ],
)
def test_reference_normalisation(text, expected):
    assert normalize_circular_no(text) == expected


def test_no_reference_without_prefix():
    assert normalize_circular_no("Minit Bil. 3/2025 sahaja") is None


def test_find_multiple_refs_in_cancellation_sentence():
    sentence = (
        "Surat Pekeliling Perkhidmatan Bilangan 1 Tahun 2023 dan Surat Pekeliling Perkhidmatan "
        "Bilangan 2 Tahun 2025 adalah dibatalkan."
    )
    assert [r["circular_no"] for r in find_refs(sentence)] == ["SPP 1/2023", "SPP 2/2025"]


def test_series_for():
    assert series_for("SPP 1/2023") == "SPP"
    assert series_for("PAN 2/2024") == "STATE"
    assert series_for("GP 1/2022") == "OTHER"


def test_tokenize_keeps_numbers_and_money():
    toks = tokenize("Kadar RM0.70 sekilometer dalam SPP 1/2023 perenggan 4.2")
    assert "rm0.70" in toks and "1/2023" in toks and "4.2" in toks
    assert "dalam" not in toks  # Malay stop-word removed


def test_glossary_expansion_both_directions():
    expanded = expand_query("travel claim deadline")
    for term in ("perjalanan", "tuntutan", "tempoh"):
        assert term in expanded
    assert "claim" in expand_query("tuntutan perjalanan")


def test_detect_language():
    assert detect_language("Berapa lama tempoh tuntutan perjalanan?") == "ms"
    assert detect_language("What is the travel claim deadline?") == "en"
    assert detect_language("Boleh saya claim travel allowance kalau outstation?") == "mixed"
