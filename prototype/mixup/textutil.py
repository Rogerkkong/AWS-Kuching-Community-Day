"""Small text helpers: tokenizing, stopwords, language detection, BM<->EN glossary."""

from __future__ import annotations

import re

# Tokens: "rm0.70" money, "3/2021" document numbers, then plain words/numbers.
_TOKEN_RE = re.compile(r"rm\d+(?:\.\d+)?|\d+(?:[./]\d+)+|[a-z0-9À-ɏ]+")

STOPWORDS_EN = set(
    """
    a an the and or but if then else of to in on at by for with from into onto about as is are was were be been being
    this that these those it its they them their there here we our you your i me my he she his her
    do does did done can could should would will shall may might must not no yes so such than too very
    what which who whom whose when where why how all any each both few more most other some own same
    up down out over under again further once only also just per via
    """.split()
)

STOPWORDS_MS = set(
    """
    yang dan atau untuk dengan adalah ialah ini itu di ke dari daripada pada dalam oleh akan telah sudah sedang
    tidak bukan juga sahaja saja lagi masih bagi kepada terhadap antara serta jika kalau apabila bila maka
    ia mereka kami kita saya anda beliau dia nya pun lah kah tah sebagai secara iaitu iaitu-nya
    apa siapa mana bagaimana kenapa mengapa berapa boleh perlu hendaklah mesti harus dapat
    se semua setiap sesuatu tersebut berikut seperti hingga sehingga mulai sejak selepas sebelum semasa
    atas bawah luar """.split()
)

STOPWORDS = STOPWORDS_EN | STOPWORDS_MS

# Function words that are a strong hint of each language (used by detect_language).
_MS_MARKERS = set(
    """
    yang dan untuk dengan adalah ialah ini itu tidak boleh berapa apa bagaimana bila siapa mana kepada dalam
    pada akan oleh telah saya kami kita perlu hendaklah atau jika bagi mesti sahaja ke di dari daripada
    berkenaan mengenai tentang hari tarikh tuntutan perjalanan pekeliling elaun garis panduan kelulusan
    mesyuarat minit keputusan tindakan seminggu minggu bekerja rumah pegawai ketua jabatan kerajaan negeri
    perkongsian dasar borang resit perbatuan berkuat kuasa kuat kuasa ada masih baru lama terkini sekarang
    macam mana nak kena kalau dah sudah ka ke lah
    """.split()
)
_EN_MARKERS = set(
    """
    the is are what how when who which of to for with and or can should must i my we our this that in on by
    be does do many much days day claim claims travel allowance deadline approval meeting minutes decision
    action policy guideline circular work home hybrid cloud data sharing latest current new old rule rules
    still allowed allow allowances submit within week office
    """.split()
)

# Bilingual glossary: (English, Bahasa Malaysia). Phrases are matched on word boundaries.
GLOSSARY: list[tuple[str, str]] = [
    ("claim", "tuntutan"),
    ("travel", "perjalanan"),
    ("allowance", "elaun"),
    ("circular", "pekeliling"),
    ("guideline", "garis panduan"),
    ("work from home", "bekerja dari rumah"),
    ("wfh", "bekerja dari rumah"),
    ("hybrid", "hibrid"),
    ("cloud", "awan"),
    ("cloud computing", "pengkomputeran awan"),
    ("data sharing", "perkongsian data"),
    ("meeting", "mesyuarat"),
    ("minutes", "minit"),
    ("approval", "kelulusan"),
    ("approve", "meluluskan"),
    ("deadline", "tarikh akhir"),
    ("days", "hari"),
    ("day", "hari"),
    ("working days", "hari bekerja"),
    ("mileage", "perbatuan"),
    ("receipt", "resit"),
    ("policy", "dasar"),
    ("procedure", "prosedur"),
    ("form", "borang"),
    ("rate", "kadar"),
    ("head of department", "ketua jabatan"),
    ("head of unit", "ketua unit"),
    ("officer", "pegawai"),
    ("staff", "kakitangan"),
    ("civil servant", "penjawat awam"),
    ("week", "minggu"),
    ("per week", "seminggu"),
    ("month", "bulan"),
    ("year", "tahun"),
    ("application", "permohonan"),
    ("apply", "memohon"),
    ("effective date", "tarikh berkuat kuasa"),
    ("in force", "berkuat kuasa"),
    ("cancel", "membatalkan"),
    ("replace", "menggantikan"),
    ("decision", "keputusan"),
    ("action", "tindakan"),
    ("attendance", "kehadiran"),
    ("agency", "agensi"),
    ("department", "jabatan"),
    ("government", "kerajaan"),
    ("state", "negeri"),
    ("confidential", "sulit"),
    ("secret", "rahsia"),
    ("internal", "terhad"),
    ("public", "terbuka"),
    ("report", "laporan"),
    ("annual", "tahunan"),
    ("digitalisation", "pendigitalan"),
    ("digitalization", "pendigitalan"),
    ("system", "sistem"),
    ("training", "latihan"),
    ("payment", "bayaran"),
    ("reimbursement", "bayaran balik"),
    ("remote", "jarak jauh"),
    ("office", "pejabat"),
    ("personal data", "data peribadi"),
    ("anonymisation", "penganoniman"),
    ("anonymise", "menganonimkan"),
    ("security", "keselamatan"),
    ("committee", "jawatankuasa"),
    ("chairman", "pengerusi"),
    ("secretariat", "urus setia"),
    ("due date", "tarikh siap"),
    ("requirement", "keperluan"),
    ("submit", "mengemukakan"),
    ("submission", "penyerahan"),
    ("vehicle", "kenderaan"),
    ("lodging", "penginapan"),
    ("on-premise", "premis sendiri"),
    ("data centre", "pusat data"),
    ("data center", "pusat data"),
    ("classification", "pengelasan"),
    ("agreement", "perjanjian"),
    ("review", "kaji semula"),
    ("supervisor", "penyelia"),
    ("core hours", "waktu teras"),
    ("electronic claim", "e-tuntutan"),
    ("e-claim", "e-tuntutan"),
    ("submit", "dikemukakan"),
    ("approve", "diluluskan"),
    ("approved", "diluluskan"),
    ("period", "tempoh"),
    ("deadline", "tempoh"),
    ("how long", "tempoh"),
    ("per km", "sekilometer"),
    ("kilometre", "sekilometer"),
    ("store", "disimpan"),
    ("stored", "disimpan"),
    ("cancelled", "dibatalkan"),
    ("replaced", "digantikan"),
    ("latest", "terkini"),
    ("new", "baharu"),
    ("rule", "peraturan"),
    ("paper form", "borang kertas"),
    ("digital receipt", "resit digital"),
    ("original receipt", "resit asal"),
    ("meal", "makan"),
    ("how many", "berapa"),
    ("when", "bila"),
    ("who", "siapa"),
]


def _stem(token: str) -> str:
    """Very light English plural stripping: 'claims' -> 'claim', 'days' -> 'day'."""
    if len(token) > 3 and token.endswith("s") and not token.endswith(("ss", "us", "is")) and not token[0].isdigit():
        return token[:-1]
    return token


def tokenize(text: str, remove_stopwords: bool = True) -> list[str]:
    """Lowercase, strip punctuation, keep numbers like '3/2021' and 'rm0.70'."""
    tokens = _TOKEN_RE.findall((text or "").lower())
    out = []
    for tok in tokens:
        if remove_stopwords and tok in STOPWORDS:
            continue
        out.append(_stem(tok))
    return out


def normalize(text: str) -> str:
    """Lowercase and collapse spaces/punctuation (for phrase matching)."""
    text = (text or "").lower()
    text = re.sub(r"[^\w/.\-]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def detect_language(text: str) -> str:
    """Guess "ms" (Bahasa Malaysia), "en" (English) or "mixed"."""
    words = re.findall(r"[a-z]+", (text or "").lower())
    ms = sum(1 for w in words if w in _MS_MARKERS)
    en = sum(1 for w in words if w in _EN_MARKERS)
    if ms + en == 0:
        return "en"
    if ms and en:
        ratio = ms / (ms + en)
        if ratio >= 0.75 and en <= 1:
            return "ms"
        if ratio <= 0.25 and ms <= 1:
            return "en"
        return "mixed"
    return "ms" if ms else "en"


def _phrase_in(phrase: str, text: str) -> bool:
    pattern = r"(?<![\w-])" + re.escape(phrase) + r"(?:s|es)?(?![\w-])"
    return re.search(pattern, text) is not None


def glossary_terms(query: str) -> list[str]:
    """Translations (both directions) of glossary phrases found in the query."""
    q = normalize(query)
    extra: list[str] = []
    for en, ms in GLOSSARY:
        if _phrase_in(en, q) and not _phrase_in(ms, q):
            extra.append(ms)
        elif _phrase_in(ms, q) and not _phrase_in(en, q):
            extra.append(en)
    # keep order, drop duplicates
    seen: set[str] = set()
    return [t for t in extra if not (t in seen or seen.add(t))]


def expand_query(query: str) -> str:
    """Add BM/EN translations so an English question finds Malay documents and vice versa.

    expand_query("travel claim deadline") -> "travel claim deadline perjalanan tuntutan tarikh akhir"
    """
    extra = glossary_terms(query)
    return (query + " " + " ".join(extra)).strip() if extra else query


def split_sentences(text: str) -> list[str]:
    """Split into sentences/lines without breaking 'Bil. 3/2021' or 'No. 5/2025'."""
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z(\"'])|\n+", text or "")
    return [p.strip() for p in parts if p and p.strip()]


def snippet(text: str, max_chars: int = 240) -> str:
    """Shorten text for display, cutting at a word boundary."""
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars].rsplit(" ", 1)[0]
    return cut + " ..."
