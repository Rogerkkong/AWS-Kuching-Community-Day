"""Text helpers: tokenizing, BM/EN stop-words, language detection, glossary
expansion and circular-number recognition / normalisation.

No English stemming is applied to Malay words (guide NFR-06); only a light,
symmetric plural strip ("claims" -> "claim") that is applied to documents and
queries alike.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

# Tokens: money "rm0.70", numbers like "3/2019" or "4.2", then plain words.
_TOKEN_RE = re.compile(r"rm\d+(?:\.\d+)?|\d+(?:[./]\d+)+|[a-z0-9À-ɏ]+(?:-[a-z0-9]+)*")

STOPWORDS_EN = set(
    """
    a an the and or but if then else of to in on at by for with from into onto about as is are was were be been being
    this that these those it its they them their there here we our you your i me my he she his her
    do does did done can could should would will shall may might must not no yes so such than too very
    what which who whom whose when where why how all any each both few more most other some own same
    up down out over under again further once only also just per via am get got still now
    """.split()
)

STOPWORDS_MS = set(
    """
    yang dan atau untuk dengan adalah ialah ini itu di ke dari daripada pada dalam oleh akan telah sudah sedang
    tidak bukan juga sahaja saja lagi masih bagi kepada terhadap antara serta jika kalau apabila bila maka
    ia mereka kami kita saya anda beliau dia nya pun lah kah tah sebagai secara iaitu
    apa siapa mana bagaimana kenapa mengapa berapa boleh perlu hendaklah mesti harus dapat
    se semua setiap sesuatu tersebut berikut seperti hingga sehingga mulai sejak selepas sebelum semasa
    atas bawah luar ada nak kena dah ka macam sekarang terkini
    """.split()
)

STOPWORDS = STOPWORDS_EN | STOPWORDS_MS

# Words that hint at each language (used by detect_language).
_MS_MARKERS = set(
    """
    yang dan untuk dengan adalah ialah ini itu tidak boleh berapa apa bagaimana bila siapa mana kepada dalam
    pada akan oleh telah saya kami kita perlu hendaklah atau jika bagi mesti sahaja ke di dari daripada
    berkenaan mengenai tentang hari tarikh tuntutan perjalanan pekeliling elaun garis panduan kelulusan
    mesyuarat minit keputusan tindakan seminggu minggu bekerja rumah pegawai ketua jabatan kerajaan negeri
    dasar borang resit perbatuan berkuat kuasa ada masih baru baharu lama terkini sekarang cuti rehat anak
    penjagaan tempoh kadar macam nak kena kalau dah sudah lah masa awam perkhidmatan
    """.split()
)
_EN_MARKERS = set(
    """
    the is are what how when who which of to for with and or can should must i my we our this that in on by
    be does do many much days day claim claims travel allowance deadline approval meeting minutes decision
    policy guideline circular work home hybrid cloud data latest current new old rule rules leave annual
    still allowed allow submit within week office rate mileage child care officer officers state federal
    """.split()
)

# Built-in fallback glossary (EN, MS) used when data/glossary.json is missing.
_FALLBACK_GLOSSARY: list[tuple[str, str]] = [
    ("claim", "tuntutan"),
    ("allowance", "elaun"),
    ("travel", "perjalanan"),
    ("mileage", "perbatuan"),
    ("leave", "cuti"),
    ("annual leave", "cuti rehat"),
    ("circular", "pekeliling"),
    ("guideline", "garis panduan"),
    ("work from home", "bekerja dari rumah"),
    ("approval", "kelulusan"),
    ("effective date", "tarikh kuat kuasa"),
    ("cancelled", "dibatalkan"),
    ("amended", "dipinda"),
    ("deadline", "tempoh"),
]


# ----------------------------------------------------------------------------
# Tokenizing and language
# ----------------------------------------------------------------------------


def _stem(token: str) -> str:
    """Light plural strip: 'claims' -> 'claim'. Applied to docs and queries alike."""
    if len(token) > 3 and token.endswith("s") and not token.endswith(("ss", "us", "is")) and not token[0].isdigit():
        return token[:-1]
    return token


def tokenize(text: str, remove_stopwords: bool = True) -> list[str]:
    """Lowercase tokens; keeps '3/2019', '4.2' and 'rm0.70' intact."""
    out = []
    for tok in _TOKEN_RE.findall((text or "").lower()):
        if remove_stopwords and tok in STOPWORDS:
            continue
        out.append(_stem(tok))
    return out


def normalize(text: str) -> str:
    """Lowercase and collapse punctuation/spaces (for phrase matching)."""
    text = (text or "").lower()
    text = re.sub(r"[^\w/.\-]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def detect_language(text: str) -> str:
    """Guess 'ms' (Bahasa Melayu), 'en' (English) or 'mixed'."""
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


# ----------------------------------------------------------------------------
# Glossary (BM <-> EN)
# ----------------------------------------------------------------------------


@lru_cache(maxsize=8)
def _load_glossary_cached(path: str, mtime: float) -> tuple[tuple[str, str], ...]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    pairs = []
    for item in data:
        if isinstance(item, dict) and item.get("en") and item.get("ms"):
            pairs.append((str(item["en"]).lower().strip(), str(item["ms"]).lower().strip()))
        elif isinstance(item, (list, tuple)) and len(item) == 2:
            pairs.append((str(item[0]).lower().strip(), str(item[1]).lower().strip()))
    return tuple(pairs)


def load_glossary(path: str | Path | None = None) -> list[tuple[str, str]]:
    """Read glossary.json ([{"ms": ..., "en": ...}]) into (en, ms) pairs."""
    if path is None:
        path = Path(__file__).resolve().parent.parent / "data" / "glossary.json"
    path = Path(path)
    try:
        return list(_load_glossary_cached(str(path), path.stat().st_mtime))
    except (OSError, ValueError):
        return list(_FALLBACK_GLOSSARY)


def _phrase_in(phrase: str, text: str) -> bool:
    pattern = r"(?<![\w-])" + re.escape(phrase) + r"(?:s|es)?(?![\w-])"
    return re.search(pattern, text) is not None


def glossary_terms(query: str, glossary: list[tuple[str, str]] | None = None) -> list[str]:
    """Translations (both directions) of glossary phrases found in the query."""
    if glossary is None:
        glossary = load_glossary()
    q = normalize(query)
    extra: list[str] = []
    for en, ms in glossary:
        if _phrase_in(en, q) and not _phrase_in(ms, q):
            extra.append(ms)
        elif _phrase_in(ms, q) and not _phrase_in(en, q):
            extra.append(en)
    seen: set[str] = set()
    return [t for t in extra if not (t in seen or seen.add(t))]


def expand_query(query: str, glossary: list[tuple[str, str]] | None = None) -> str:
    """'travel claim deadline' -> 'travel claim deadline perjalanan tuntutan tempoh ...'."""
    extra = glossary_terms(query, glossary)
    return (query + " " + " ".join(extra)).strip() if extra else query


# ----------------------------------------------------------------------------
# Circular numbers
# ----------------------------------------------------------------------------

# Extends the guide's REF regex: the "Bil." part is optional ("SPP 1/2023"),
# and state / treasury / guideline / circular-letter prefixes are recognised.
REF_RE = re.compile(
    r"""(?ix)
    (?P<prefix>
        surat \s+ pekeliling \s+ perkhidmatan
      | pekeliling \s+ perkhidmatan
      | pekeliling \s+ perbendaharaan
      | pekeliling \s+ am (?: \s+ negeri )?
      | surat \s+ edaran
      | garis \s+ panduan
      | \b (?: spp | pp | se | pb | pan | gp | sop | pkp ) \b
    )
    \s* (?: bilangan | bil \.? | no \.? | number )? \s*
    (?P<num> \d{1,3} )
    \s* (?: tahun | / | of ) \s*
    (?P<year> (?:19|20) \d{2} ) \b
    """
)

_PREFIX_CODES = {
    "surat pekeliling perkhidmatan": "SPP",
    "pekeliling perkhidmatan": "PP",
    "pekeliling perbendaharaan": "PB",
    "pekeliling am negeri": "PAN",
    "pekeliling am": "PAN",
    "surat edaran": "SE",
    "garis panduan": "GP",
}

# Code -> series value used in metadata.csv
SERIES_BY_CODE = {
    "PP": "PP",
    "SPP": "SPP",
    "SE": "SE",
    "PB": "PEKELILING_PERBENDAHARAAN",
    "PAN": "STATE",
}


def _code(prefix: str) -> str:
    key = re.sub(r"\s+", " ", prefix.strip().lower())
    return _PREFIX_CODES.get(key, key.upper())


def find_refs(text: str) -> list[dict]:
    """All circular references in text: [{"circular_no", "raw", "start", "end"}]."""
    out = []
    for m in REF_RE.finditer(text or ""):
        out.append(
            {
                "circular_no": f"{_code(m.group('prefix'))} {int(m.group('num'))}/{m.group('year')}",
                "raw": m.group(0).strip(),
                "start": m.start(),
                "end": m.end(),
            }
        )
    return out


def normalize_circular_no(text: str) -> str | None:
    """'PP Bil. 3/2024' -> 'PP 3/2024'; 'Surat Pekeliling Perkhidmatan Bilangan 5 Tahun 2018' -> 'SPP 5/2018'."""
    refs = find_refs(text)
    return refs[0]["circular_no"] if refs else None


def series_for(circular_no: str) -> str:
    """'SPP 1/2023' -> 'SPP'; unknown codes -> 'OTHER'."""
    code = (circular_no or "").split(" ")[0].upper()
    return SERIES_BY_CODE.get(code, "OTHER")


# ----------------------------------------------------------------------------
# Misc
# ----------------------------------------------------------------------------


def split_sentences(text: str) -> list[str]:
    """Split into sentences/lines without breaking 'Bil. 3/2019' or '4.2'."""
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z(\"'])|\n+", text or "")
    return [p.strip() for p in parts if p and p.strip()]


def snippet(text: str, max_chars: int = 240) -> str:
    """Shorten text for display, cutting at a word boundary."""
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0] + " ..."
