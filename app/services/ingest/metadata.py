"""Document metadata: regex first, then the METADATA prompt for missing fields, then data/metadata.csv
overrides (manual values always win)."""
from __future__ import annotations

import csv
import re
from datetime import date
from pathlib import Path

from app.services.generation import prompts
from app.services.ingest.parse import Page

MALAY_MONTHS = {
    "januari": 1, "februari": 2, "mac": 3, "april": 4, "mei": 5, "jun": 6, "julai": 7, "ogos": 8,
    "september": 9, "oktober": 10, "november": 11, "disember": 12,
    # English fallbacks
    "january": 1, "february": 2, "march": 3, "may": 5, "june": 6, "july": 7, "august": 8,
    "october": 10, "december": 12,
}
DATE_RE = re.compile(r"\b(\d{1,2})\s+(" + "|".join(MALAY_MONTHS) + r")\s+((?:19|20)\d{2})\b", re.I)

SERIES_PATTERNS = [
    # (regex, series, prefix, jurisdiction)
    (re.compile(r"SURAT\s+PEKELILING\s+PERKHIDMATAN\s+BILANGAN\s+(\d{1,3})\s+TAHUN\s+((?:19|20)\d{2})", re.I), "SPP", "SPP", "FEDERAL"),
    (re.compile(r"PEKELILING\s+PERKHIDMATAN\s+BILANGAN\s+(\d{1,3})\s+TAHUN\s+((?:19|20)\d{2})", re.I), "PP", "PP", "FEDERAL"),
    (re.compile(r"PEKELILING\s+PERBENDAHARAAN\s+(?:BILANGAN\s+)?(?:[A-Z]{2}\s*)?(\d{1,3})(?:\.\d+)?\s*(?:TAHUN|/)\s*((?:19|20)\d{2})", re.I), "PEKELILING_PERBENDAHARAAN", "PB", "FEDERAL"),
    (re.compile(r"SURAT\s+EDARAN\s+(?:BILANGAN|BIL\.?)\s*(\d{1,3})\s*(?:TAHUN|/)\s*((?:19|20)\d{2})", re.I), "SE", "SE", "FEDERAL"),
    (re.compile(r"PEKELILING\s+AM\s+SARAWAK\s+BILANGAN\s+(\d{1,3})\s+TAHUN\s+((?:19|20)\d{2})", re.I), "STATE", "PAS", "SARAWAK"),
    (re.compile(r"GARIS\s+PANDUAN\s+BILANGAN\s+(\d{1,3})\s+TAHUN\s+((?:19|20)\d{2})", re.I), "OTHER", "GP", None),
]
SOP_RE = re.compile(r"\b(SOP[-\s][A-Z0-9]+(?:[-\s][A-Z0-9]+)*\s*\d{0,3}/(?:19|20)\d{2})\b")
MINUTES_RE = re.compile(r"MINIT\s+MESYUARAT\s+(.+?)\s+BIL\.?\s*(\d{1,3})\s*/\s*((?:19|20)\d{2})", re.I)
LABEL_DATE_RE = re.compile(r"^\s*Tarikh\s*:\s*(.+)$", re.I | re.M)
EFFECTIVE_RE = re.compile(r"berkuat\s+kuasa\s+mulai\s+(\d{1,2}\s+\w+\s+(?:19|20)\d{2})", re.I)
ONE_OFF_RE = re.compile(r"\b(sekali\s+sahaja|one[-\s]off)\b", re.I)
HEADING_WORDS = {"TUJUAN", "LATAR BELAKANG", "PEMAKAIAN", "KEHADIRAN", "TERHAD", "SULIT"}

FIELDS = ["circular_no", "series", "title", "issuer", "doc_type", "jurisdiction", "cluster", "issue_date",
          "effective_date", "expiry_date", "one_off", "classification_level", "language", "applicability",
          "source_url"]


def parse_malay_date(text: str | None) -> str | None:
    if not text:
        return None
    m = DATE_RE.search(text)
    if not m:
        return None
    try:
        return date(int(m.group(3)), MALAY_MONTHS[m.group(2).lower()], int(m.group(1))).isoformat()
    except ValueError:
        return None


SMALL_WORDS = {"dan", "atau", "di", "ke", "dari", "bagi", "untuk", "melalui", "yang", "dalam", "of", "and", "the"}


def title_case(text: str) -> str:
    words = text.lower().split()
    out = []
    for i, w in enumerate(words):
        if i and w in SMALL_WORDS:
            out.append(w)
        elif w in {"hrmis", "sop", "gcr"}:
            out.append(w.upper())
        elif w.startswith("(") and len(w) > 1:
            out.append("(" + w[1:].capitalize())
        else:
            out.append(w[:1].upper() + w[1:])
    return " ".join(out)


def _initials(name: str) -> str:
    return "".join(w[0] for w in re.findall(r"[A-Za-z]+", name) if w.lower() not in SMALL_WORDS).upper()


def regex_metadata(pages: list[Page]) -> dict:
    head = "\n".join(p.text for p in pages[:2])
    full = "\n".join(p.text for p in pages)
    lines = [ln.strip() for ln in head.split("\n") if ln.strip()]
    meta: dict = {}
    upper_head = head.upper()

    # Document type
    if "MINIT MESYUARAT" in upper_head:
        meta["doc_type"] = "minutes"
    elif re.search(r"PROSEDUR\s+OPERASI\s+STANDARD|\bSOP\b", upper_head):
        meta["doc_type"] = "sop"
    elif "GARIS PANDUAN" in upper_head:
        meta["doc_type"] = "guideline"
    elif re.search(r"^\s*LAPORAN\b", upper_head, re.M):
        meta["doc_type"] = "report"
    elif re.search(r"^\s*DASAR\b", upper_head, re.M):
        meta["doc_type"] = "policy"
    else:
        meta["doc_type"] = "circular"

    number_line_idx = None
    # The reference number sits in the header block; body text may cite other circulars.
    header_block = "\n".join(lines[:10])
    for regex, series, prefix, jur in SERIES_PATTERNS:
        m = regex.search(header_block)
        if m:
            meta["circular_no"] = f"{prefix} {int(m.group(1))}/{m.group(2)}"
            meta["series"] = series
            if jur:
                meta["jurisdiction"] = jur
            number_line_idx = next((i for i, ln in enumerate(lines) if regex.search(ln)), None)
            break
    if "circular_no" not in meta:
        m = MINUTES_RE.search(header_block)
        if m:
            meta["circular_no"] = f"MM{_initials(m.group(1))} {int(m.group(2))}/{m.group(3)}"
            meta["series"] = "OTHER"
            meta["title"] = title_case(f"Minit Mesyuarat {m.group(1)} Bil. {int(m.group(2))}/{m.group(3)}")
            meta["issuer"] = title_case(f"Mesyuarat {m.group(1)}")
        else:
            m = SOP_RE.search(header_block)
            if m:
                meta["circular_no"] = re.sub(r"\s+", " ", m.group(1)).strip()
                meta["series"] = "OTHER"
                number_line_idx = next((i for i, ln in enumerate(lines) if m.group(1) in ln), None)

    # Title: first upper-case line after the number line that is not a heading or classification.
    if "title" not in meta and number_line_idx is not None:
        for ln in lines[number_line_idx + 1:number_line_idx + 4]:
            clean = ln.strip()
            if clean.isupper() and clean not in HEADING_WORDS and not re.match(r"^\d+\.", clean):
                meta["title"] = title_case(clean)
                break

    # Issuer: first line of the page when it is upper case and not the number line.
    if "issuer" not in meta and lines:
        first = lines[0]
        if first.isupper() and (number_line_idx is None or number_line_idx > 0):
            meta["issuer"] = title_case(first)

    # Jurisdiction
    if "jurisdiction" not in meta:
        if "SARAWAK" in upper_head.split("\n", 3)[0] or "NEGERI SARAWAK" in upper_head[:300]:
            meta["jurisdiction"] = "SARAWAK"
        elif re.search(r"PERKHIDMATAN AWAM MALAYSIA|KEMENTERIAN|PERSEKUTUAN", upper_head):
            meta["jurisdiction"] = "FEDERAL"

    # Dates
    label = LABEL_DATE_RE.search(head)
    if label:
        meta["issue_date"] = parse_malay_date(label.group(1))
    eff = EFFECTIVE_RE.search(full)
    if eff:
        meta["effective_date"] = parse_malay_date(eff.group(1))
    elif meta.get("doc_type") in ("sop", "guideline", "policy") and meta.get("issue_date"):
        meta["effective_date"] = meta["issue_date"]

    if ONE_OFF_RE.search(full):
        meta["one_off"] = 1
    if re.search(r"^\s*TERHAD\s*$", head, re.M):
        meta["classification_level"] = 1
    if re.search(r"^\s*SULIT\s*$", head, re.M):
        meta["classification_level"] = 2

    # Applicability: text following the PEMAKAIAN heading.
    pm = re.search(r"PEMAKAIAN\s*\n(.+?)(?:\n\d+\.\s+[A-Z ]{4,}\n|\Z)", full, re.S)
    if pm:
        meta["applicability"] = re.sub(r"\s+", " ", re.sub(r"^\d+(\.\d+)*\s*", "", pm.group(1).strip()))[:400]
    meta["language"] = "ms"
    return {k: v for k, v in meta.items() if v not in (None, "")}


def llm_metadata(pages: list[Page], client) -> dict:
    """Ask the METADATA prompt for fields the regex could not find. Errors return {}."""
    from app.services.inference.client import parse_json_loose

    text = "\n".join(p.text for p in pages[:2])[:6000]
    try:
        reply = client.chat([{"role": "user", "content": prompts.METADATA.format(text=text)}],
                            json_mode=True, max_tokens=400, timeout=180)
        data = parse_json_loose(reply)
    except Exception:  # noqa: BLE001
        return {}
    if not isinstance(data, dict):
        return {}
    allowed_types = {"circular", "policy", "sop", "guideline", "report", "minutes"}
    out = {}
    for key in ("doc_type", "circular_no", "series", "title", "issuer", "issue_date", "effective_date",
                "jurisdiction", "applicability", "language"):
        value = data.get(key)
        if isinstance(value, str) and value.strip() and value.strip().lower() != "null":
            out[key] = value.strip()
    if out.get("doc_type") not in allowed_types:
        out.pop("doc_type", None)
    for key in ("issue_date", "effective_date"):
        if key in out and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", out[key]):
            out.pop(key)
    if data.get("one_off") is True:
        out["one_off"] = 1
    return out


def load_overrides(csv_path: Path) -> dict[str, dict]:
    """data/metadata.csv keyed by file name; blank cells mean "no override"."""
    if not csv_path.exists():
        return {}
    out: dict[str, dict] = {}
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            name = (row.pop("file", "") or "").strip()
            if not name:
                continue
            clean = {}
            for k, v in row.items():
                if k in FIELDS and v is not None and v.strip() != "":
                    v = v.strip()
                    clean[k] = int(v) if k in ("classification_level", "one_off") else v
            out[name] = clean
    return out


def extract_metadata(pages: list[Page], file_name: str, client=None, overrides: dict | None = None,
                     use_llm: bool = True) -> tuple[dict, list[str]]:
    """Returns (metadata, notes). Precedence: regex < LLM (missing fields only) < metadata.csv."""
    notes: list[str] = []
    meta = regex_metadata(pages)
    missing = [k for k in ("circular_no", "title", "issue_date", "jurisdiction") if not meta.get(k)]
    if missing and use_llm and client is not None:
        llm = llm_metadata(pages, client)
        for k, v in llm.items():
            if not meta.get(k):
                meta[k] = v
                notes.append(f"LLM filled {k}")
    manual = (overrides or {}).get(file_name, {})
    if manual:
        meta.update(manual)
        notes.append(f"metadata.csv overrides: {', '.join(sorted(manual))}")
    meta.setdefault("series", "OTHER")
    meta.setdefault("jurisdiction", "UNKNOWN")
    meta.setdefault("classification_level", 0)
    meta.setdefault("one_off", 0)
    meta.setdefault("doc_type", "circular")
    if not meta.get("circular_no"):
        meta["circular_no"] = Path(file_name).stem
        notes.append("No reference number found; using the file name")
    if not meta.get("title"):
        meta["title"] = meta["circular_no"]
    return meta, notes
