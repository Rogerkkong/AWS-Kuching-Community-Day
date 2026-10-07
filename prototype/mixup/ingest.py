"""Ingestion: parse files into pages, clause-aware chunking, regex metadata.

Files:
  .pdf   one Page per PDF page (pypdf); pages with < 30 characters are flagged
         "needs OCR" (OCR itself is out of scope offline)
  .md    one Page per '##' section (or per form-feed page if the file has \\f)
  .txt   one Page per upper-case heading section (or per \\f page)
  .docx  one Page per heading section (python-docx)

Chunking follows the circular structure (guide 7.2): headings such as TUJUAN,
LATAR BELAKANG, PEMAKAIAN, TARIKH KUAT KUASA, PEMBATALAN, and numbered
paragraphs 1., 2.1, (a). Each chunk keeps clause_ref, a breadcrumb like
"SPP 1/2023 > PEMAKAIAN > 3" and page_start / page_end.
"""

from __future__ import annotations

import io
import re
from datetime import date
from pathlib import Path

from .models import Chunk, Document, Page
from .textutil import detect_language, find_refs, series_for

SUPPORTED_EXTENSIONS = (".pdf", ".md", ".markdown", ".txt", ".docx")
OCR_MIN_CHARS = 30
WATERMARK = "SINTETIK - CONTOH SAHAJA / SYNTHETIC - SAMPLE ONLY"

# Guide 7.2 patterns (plus English equivalents for the English guidelines).
HEADING_RE = re.compile(
    r"^(TUJUAN|LATAR BELAKANG|PEMAKAIAN|TARIKH (?:BERKUAT|KUAT) KUASA|PEMBATALAN|PINDAAN|LAMPIRAN\s*\w*"
    r"|PURPOSE|BACKGROUND|SCOPE|APPLICABILITY|EFFECTIVE DATE|SUPERSESSION|CANCELLATION)\b"
)
PARA_RE = re.compile(r"^(\d{1,2})\.\s+")  # 1. 2.
SUBPARA_RE = re.compile(r"^(\d{1,2}(?:\.\d{1,2})+)\.?\s+")  # 2.1  3.2.1
ITEM_RE = re.compile(r"^\((\w{1,3})\)\s+")  # (a) (i) (iv)
_MD_HEADING = re.compile(r"^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
_CLASSIFICATION_WORDS = {"TERBUKA", "TERHAD", "SULIT", "RAHSIA", "RAHSIA BESAR"}
MIN_CHUNK_WORDS = 8
MAX_CHUNK_WORDS = 500

MONTHS = {
    "januari": 1, "january": 1, "jan": 1,
    "februari": 2, "february": 2, "feb": 2,
    "mac": 3, "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "mei": 5, "may": 5,
    "jun": 6, "june": 6,
    "julai": 7, "july": 7, "jul": 7,
    "ogos": 8, "august": 8, "aug": 8, "ogo": 8,
    "september": 9, "sep": 9, "sept": 9,
    "oktober": 10, "october": 10, "okt": 10, "oct": 10,
    "november": 11, "nov": 11,
    "disember": 12, "december": 12, "dis": 12, "dec": 12,
}
_DATE_TEXT_RE = re.compile(r"(\d{1,2})(?:hb)?\s+([A-Za-z]{3,9})\s+((?:19|20)\d{2})")
_DATE_ISO_RE = re.compile(r"((?:19|20)\d{2})-(\d{2})-(\d{2})")


# ----------------------------------------------------------------------------
# Parsing files into pages
# ----------------------------------------------------------------------------


def _clean_heading(text: str) -> str:
    """'## 3. PEMAKAIAN' -> 'PEMAKAIAN'; strips markdown emphasis."""
    text = text.replace("**", "").replace("__", "").strip()
    return re.sub(r"^\d+(?:\.\d+)*\.?\s+", "", text).strip()


def heading_of(line: str) -> str | None:
    """Return the section name if the line is a section heading, else None.

    '# Title' lines (level 1) are titles, not sections.
    """
    m = _MD_HEADING.match(line)
    if m:
        return _clean_heading(m.group(2)) if len(m.group(1)) >= 2 else None
    stripped = line.strip().replace("**", "")
    if not stripped or len(stripped) > 60 or stripped.endswith((".", ",", ";", ":")):
        return None
    if HEADING_RE.match(stripped):
        return stripped
    words = stripped.split()
    if (
        stripped.isupper()
        and not any(ch.isdigit() for ch in stripped)
        and 1 <= len(words) <= 6
        and stripped not in _CLASSIFICATION_WORDS
        and "SINTETIK" not in stripped
    ):
        return stripped
    return None


def _pages_from_sections(doc_id: str, lines: list[str], is_heading) -> list[Page]:
    """Start a new page at every section heading (text before it is page 1)."""
    pages: list[list[str]] = [[]]
    headings = [""]
    for line in lines:
        name = is_heading(line)
        if name is not None and any(x.strip() for x in pages[-1]):
            pages.append([])
            headings.append(name)
        elif name is not None:
            headings[-1] = headings[-1] or name
        pages[-1].append(line)
    out = []
    for heading, body in zip(headings, pages):
        text = "\n".join(body).strip()
        if text:
            out.append(Page(doc_id=doc_id, page_no=len(out) + 1, text=text, heading=heading))
    return out


def _pages_from_text(doc_id: str, text: str) -> list[Page]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if "\f" in text:
        pages = []
        for i, part in enumerate(text.split("\f"), start=1):
            body = part.strip()
            pages.append(Page(doc_id=doc_id, page_no=i, text=body, needs_ocr=len(body) < OCR_MIN_CHARS))
        return pages
    return _pages_from_sections(doc_id, text.split("\n"), heading_of)


def _pages_from_pdf(doc_id: str, data: bytes) -> list[Page]:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    pages = []
    for i, pdf_page in enumerate(reader.pages, start=1):
        try:
            body = (pdf_page.extract_text() or "").strip()
        except Exception:  # a broken page should not kill the whole upload
            body = ""
        pages.append(Page(doc_id=doc_id, page_no=i, text=body, needs_ocr=len(body) < OCR_MIN_CHARS))
    return pages


def _pages_from_docx(doc_id: str, data: bytes) -> list[Page]:
    import docx  # python-docx

    document = docx.Document(io.BytesIO(data))
    lines: list[str] = []
    for para in document.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        style = ((para.style.name if para.style is not None else "") or "").lower()
        if style.startswith("heading") and not style.endswith(" 1"):
            text = "## " + text  # make Word headings look like markdown sections
        elif style.startswith("title") or style == "heading 1":
            text = "# " + text
        lines.append(text)
    for table in document.tables:  # tables are common in circulars
        for row in table.rows:
            lines.append(" | ".join(cell.text.strip() for cell in row.cells))
    return _pages_from_sections(doc_id, lines, heading_of)


def parse_bytes(filename: str, data: bytes, doc_id: str | None = None) -> list[Page]:
    """Parse an uploaded file's bytes into Pages. Raises ValueError for unsupported types."""
    ext = Path(filename).suffix.lower()
    doc_id = doc_id or Path(filename).stem
    if ext == ".pdf":
        return _pages_from_pdf(doc_id, data)
    if ext == ".docx":
        return _pages_from_docx(doc_id, data)
    if ext in (".md", ".markdown", ".txt"):
        return _pages_from_text(doc_id, data.decode("utf-8", errors="replace"))
    raise ValueError(f"Unsupported file type '{ext}'. Use PDF, DOCX, MD or TXT.")


def parse_file(path: str | Path, doc_id: str | None = None) -> list[Page]:
    """Parse a file on disk into Pages."""
    path = Path(path)
    return parse_bytes(path.name, path.read_bytes(), doc_id or path.stem)


def full_text(pages: list[Page]) -> str:
    """All page text joined (for regexes and prompts)."""
    return "\n\n".join(p.text for p in pages)


# ----------------------------------------------------------------------------
# Clause-aware chunking
# ----------------------------------------------------------------------------


def _is_noise(line: str) -> bool:
    s = line.strip()
    is_watermark = "SINTETIK" in s.upper() and "CONTOH" in s.upper()
    return not s or is_watermark or re.fullmatch(r"[-=*_]{3,}", s) is not None


def _clean_line(line: str) -> str:
    m = _MD_HEADING.match(line)
    if m:  # '# TITLE' -> 'TITLE'
        line = m.group(2)
    return line.replace("**", "").rstrip()


def _new_unit(section: str, clause: str, page: int) -> dict:
    return {"section": section, "clause": clause, "page_start": page, "page_end": page, "lines": []}


def _units(pages: list[Page]) -> list[dict]:
    """Walk the lines and cut a unit at every heading or (sub)paragraph number."""
    units: list[dict] = []
    section = ""
    current = _new_unit("", "", pages[0].page_no if pages else 1)
    for page in pages:
        for raw in page.text.split("\n"):
            if _is_noise(raw):
                continue
            name = heading_of(raw)
            if name is not None:
                if current["lines"]:
                    units.append(current)
                section = name
                current = _new_unit(section, "", page.page_no)
                continue
            line = _clean_line(raw).strip()
            sub = SUBPARA_RE.match(line)
            para = PARA_RE.match(line) if not sub else None
            if sub or para:
                if current["lines"]:
                    units.append(current)
                current = _new_unit(section, (sub or para).group(1), page.page_no)
            current["lines"].append(line)
            current["page_end"] = page.page_no
    if current["lines"]:
        units.append(current)
    return units


def _split_long(text: str, max_words: int) -> list[str]:
    """Split an over-long clause on sentence boundaries."""
    words = text.split()
    if len(words) <= max_words:
        return [text]
    parts, buf = [], []
    for sentence in re.split(r"(?<=[.;:])\s+", text):
        if buf and len(" ".join(buf + [sentence]).split()) > max_words:
            parts.append(" ".join(buf))
            buf = []
        buf.append(sentence)
    if buf:
        parts.append(" ".join(buf))
    return parts


def breadcrumb(label: str, section: str, clause_ref: str) -> str:
    """'SPP 1/2023' + 'PEMAKAIAN' + '3' -> 'SPP 1/2023 > PEMAKAIAN > 3'."""
    parts = [label, section]
    if clause_ref and clause_ref != section:
        parts.append(clause_ref)
    return " > ".join(p for p in parts if p)


def chunk_document(doc: Document, pages: list[Page]) -> list[Chunk]:
    """Clause-aware chunks for one document (never crosses documents)."""
    units = _units(pages)
    # Merge very short units (e.g. a lead-in "4. Peraturan berikut:") into the next one.
    merged: list[dict] = []
    carry: dict | None = None
    for unit in units:
        if carry is not None:
            if carry["section"] == unit["section"]:
                unit["lines"] = carry["lines"] + unit["lines"]
                unit["page_start"] = carry["page_start"]
            else:
                merged.append(carry)
            carry = None
        words = sum(len(x.split()) for x in unit["lines"])
        if words < MIN_CHUNK_WORDS and unit is not units[-1] and unit["clause"]:
            carry = unit
            continue
        merged.append(unit)
    if carry is not None:
        merged.append(carry)

    chunks: list[Chunk] = []
    for unit in merged:
        clause = unit["clause"] or unit["section"] or "Tajuk"
        text = "\n".join(unit["lines"]).strip()
        for piece in _split_long(text, MAX_CHUNK_WORDS):
            idx = len(chunks)
            chunks.append(
                Chunk(
                    chunk_id=f"{doc.doc_id}#{idx}",
                    doc_id=doc.doc_id,
                    chunk_index=idx,
                    clause_ref=clause,
                    breadcrumb=breadcrumb(doc.label, unit["section"], clause),
                    section=unit["section"],
                    page_start=unit["page_start"],
                    page_end=unit["page_end"],
                    text=piece,
                )
            )
    return chunks


# ----------------------------------------------------------------------------
# Regex metadata (guide FR-02: regex first; metadata.csv values always win)
# ----------------------------------------------------------------------------


def parse_any_date(text: str) -> date | None:
    """First date in text: '1 Mac 2023', '15 February 2025', '2023-03-01'."""
    if not text:
        return None
    candidates = []
    for m in _DATE_TEXT_RE.finditer(text):
        month = MONTHS.get(m.group(2).lower())
        if month:
            try:
                candidates.append((m.start(), date(int(m.group(3)), month, int(m.group(1)))))
            except ValueError:
                pass
    for m in _DATE_ISO_RE.finditer(text):
        try:
            candidates.append((m.start(), date(int(m.group(1)), int(m.group(2)), int(m.group(3)))))
        except ValueError:
            pass
    return min(candidates)[1] if candidates else None


def _field(text: str, labels: list[str]) -> str:
    """Value of the first 'Label: value' line among labels (case-insensitive)."""
    for label in labels:
        m = re.search(rf"(?im)^\s*{label}\s*:\s*(.+)$", text)
        if m:
            return m.group(1).strip()
    return ""


def section_text(pages: list[Page], names: tuple[str, ...]) -> str:
    """Text of the first section whose heading starts with one of names."""
    lines, inside = [], False
    for page in pages:
        for raw in page.text.split("\n"):
            name = heading_of(raw)
            if name is not None:
                if inside:
                    return "\n".join(lines).strip()
                inside = name.upper().startswith(names)
                continue
            if inside and not _is_noise(raw):
                lines.append(_clean_line(raw).strip())
    return "\n".join(lines).strip()


def detect_doc_language(text: str) -> str:
    """Document-level language: 'ms', 'en' or 'mixed' (ratio of marker words)."""
    words = re.findall(r"[a-z]+", (text or "").lower())
    from .textutil import _EN_MARKERS, _MS_MARKERS  # small private word lists

    ms = sum(1 for w in words if w in _MS_MARKERS)
    en = sum(1 for w in words if w in _EN_MARKERS)
    if ms + en == 0:
        return detect_language(text)
    ratio = ms / (ms + en)
    return "ms" if ratio >= 0.8 else "en" if ratio <= 0.2 else "mixed"


def guess_jurisdiction(applicability: str, text: str) -> str:
    """FEDERAL / SARAWAK / FEDERAL_SARAWAK / UNKNOWN from the PEMAKAIAN text."""
    # Ignore "does not apply to ..." sentences: they name the OTHER jurisdiction.
    sentences = re.split(r"(?<=[.;])\s+", (applicability or "").lower())
    a = " ".join(s for s in sentences if not re.search(r"tidak terpakai|does not apply|not applicable", s))
    head = (text or "")[:1500].lower()
    adopted = re.search(r"diterima pakai oleh (?:kerajaan |perkhidmatan awam )?negeri sarawak|adopted by (?:the )?sarawak", a)
    sarawak = re.search(r"(?<!tidak )terpakai kepada[^.]*negeri sarawak|perkhidmatan awam negeri sarawak|sarawak state (?:civil )?service", a)
    federal = re.search(r"persekutuan|federal", a)
    if federal and adopted:
        return "FEDERAL_SARAWAK"
    if sarawak and not federal:
        return "SARAWAK"
    if federal:
        return "FEDERAL"
    if "negeri sarawak" in head:
        return "SARAWAK"
    return "UNKNOWN"


def guess_cluster(text: str) -> str:
    """Topic cluster from keywords (editable in the admin view)."""
    t = (text or "").lower()
    rules = [
        ("travel-claims", ("tuntutan", "perjalanan", "perbatuan", "travel claim", "mileage")),
        ("leave", ("cuti", "leave")),
        ("flexible-work", ("bekerja dari rumah", "hibrid", "work from home", "hybrid")),
        ("ict-data", ("cloud", "awan", "pusat data", "data centre")),
    ]
    best, best_hits = "", 0
    for cluster, words in rules:
        hits = sum(t.count(w) for w in words)
        if hits > best_hits:
            best, best_hits = cluster, hits
    return best


def guess_doc_type(title: str, text: str) -> str:
    t = f"{title}\n{text[:800]}".lower()
    if "minit mesyuarat" in t or "minutes of" in t:
        return "minutes"
    if "laporan" in title.lower() or "report" in title.lower():
        return "report"
    if re.search(r"\bsop\b|prosedur operasi", t):
        return "sop"
    if "garis panduan" in t or "guideline" in t:
        return "guideline"
    return "circular"


def extract_metadata(pages: list[Page], filename: str = "") -> dict:
    """Regex metadata suggestions. Only fields that were found are returned."""
    text = full_text(pages)
    head = text[:2500]
    meta: dict = {}

    ref_line = _field(head, ["Rujukan", "No\\. Rujukan", "Reference", "Nombor"])
    refs = find_refs(ref_line) or find_refs(head[:600])
    if refs:
        meta["circular_no"] = refs[0]["circular_no"]
        meta["series"] = series_for(refs[0]["circular_no"])

    title = _field(head, ["Tajuk", "Perkara", "Title", "Subject"])
    if not title:
        for line in head.split("\n"):
            s = _clean_line(line).strip()
            if s and not _is_noise(line) and ":" not in s and not find_refs(s) and heading_of(line) is None:
                title = s
                break
    if title:
        meta["title"] = title

    issuer = _field(head, ["Dikeluarkan oleh", "Daripada", "Issued by", "Issuer"])
    if issuer:
        meta["issuer"] = issuer

    issued = parse_any_date(_field(head, ["Tarikh dikeluarkan", "Tarikh", "Date issued", "Date"]))
    if issued:
        meta["issue_date"] = issued
    eff = parse_any_date(_field(head, ["Tarikh (?:berkuat|kuat) kuasa", "Effective date"]))
    if not eff:
        m = re.search(r"(?i)(?:berkuat kuasa mulai|berkuat kuasa pada|takes effect on|with effect from|effective from)\s+([^\n.]+)", text)
        eff = parse_any_date(m.group(1)) if m else None
    if eff:
        meta["effective_date"] = eff
    expiry = parse_any_date(_field(head, ["Tarikh tamat", "Expiry date", "Tamat tempoh"]))
    if expiry:
        meta["expiry_date"] = expiry

    applicability = section_text(pages, ("PEMAKAIAN", "SCOPE", "APPLICABILITY"))
    if applicability:
        meta["applicability"] = re.sub(r"\s+", " ", applicability)[:500]
    meta["jurisdiction"] = guess_jurisdiction(applicability, text)

    if re.search(r"(?i)sekali sahaja|one-off|one off|arahan sementara", text):
        meta["one_off"] = True

    klass = _field(head, ["Klasifikasi", "Classification"]).upper()
    top_lines = {line.strip().upper() for line in head.split("\n")[:12]}
    if "SULIT" in klass or "SULIT" in top_lines:
        meta["classification_level"] = 2
    elif "TERHAD" in klass or "TERHAD" in top_lines:
        meta["classification_level"] = 1
    else:
        meta["classification_level"] = 0

    meta["language"] = detect_doc_language(text[:4000])
    cluster = guess_cluster(text)
    if cluster:
        meta["cluster"] = cluster
    meta["doc_type"] = guess_doc_type(meta.get("title", ""), text)
    return meta
