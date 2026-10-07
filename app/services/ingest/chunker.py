"""Structure-aware chunking for circulars, SOPs, guidelines and meeting minutes.

Circulars: a chunk is one numbered section (heading + its sub-clauses). Sections longer than
MAX_WORDS are split at sub-clause boundaries. Chunks never cross documents and keep the breadcrumb
"circular_no > heading > clause" plus page_start/page_end.

Minutes: split on PERKARA (agenda item), KEPUTUSAN (decision) and TINDAKAN (action); every chunk
carries its agenda item title and the breadcrumb carries the meeting date.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.services.ingest.parse import Page

MIN_WORDS, MAX_WORDS = 150, 500  # targets; structure wins for short sections (see DECISIONS.md)

TOP_RE = re.compile(r"^(\d{1,2})\.\s+(.+)$")
SUB_RE = re.compile(r"^(\d{1,2}(?:\.\d{1,2})+)\.?\s+(.+)$")
ITEM_RE = re.compile(r"^\((\w{1,3})\)\s+(.+)$")
CAPS_HEADINGS = ("TUJUAN", "LATAR BELAKANG", "PEMAKAIAN", "TARIKH KUAT KUASA", "PEMBATALAN", "LAMPIRAN")
CAPS_RE = re.compile(r"^(" + "|".join(CAPS_HEADINGS) + r")\b[A-Z0-9 ,'()/&\-]*$")
PERKARA_RE = re.compile(r"^PERKARA\s+(\d{1,3})\s*[:.\-]?\s*(.*)$", re.I)
KEPUTUSAN_RE = re.compile(r"^KEPUTUSAN\s*:?\s*(.*)$")
TINDAKAN_RE = re.compile(r"^TINDAKAN\s*:?\s*(.*)$")
KEHADIRAN_RE = re.compile(r"^KEHADIRAN\s*:?\s*(.*)$")

MONTHS_MS = ["Januari", "Februari", "Mac", "April", "Mei", "Jun", "Julai", "Ogos", "September", "Oktober",
             "November", "Disember"]


def malay_date(iso: str | None) -> str:
    if not iso:
        return "tarikh tidak diketahui"
    y, m, d = iso.split("-")
    return f"{int(d)} {MONTHS_MS[int(m) - 1]} {y}"


@dataclass
class Chunk:
    chunk_index: int
    clause_ref: str
    breadcrumb: str
    page_start: int
    page_end: int
    text: str
    ocr: bool = False


@dataclass
class _Unit:
    ref: str | None
    lines: list[str]
    page_start: int
    page_end: int

    def add(self, line: str, page: int, continuation: bool) -> None:
        if continuation and self.lines:
            self.lines[-1] = f"{self.lines[-1]} {line}"
        else:
            self.lines.append(line)
        self.page_end = page

    @property
    def text(self) -> str:
        return "\n".join(self.lines)

    @property
    def words(self) -> int:
        return len(self.text.split())


@dataclass
class _Section:
    num: str | None
    heading: str
    page_start: int
    units: list[_Unit] = field(default_factory=list)
    kind: str = "section"


def _lines(pages: list[Page]):
    for p in pages:
        for line in p.text.split("\n"):
            line = line.strip()
            if line:
                yield p.number, line, p.ocr


def _is_heading_text(text: str) -> bool:
    letters = [c for c in text if c.isalpha()]
    return bool(letters) and text.upper() == text and len(text) <= 120


def chunk_document(pages: list[Page], meta: dict) -> list[Chunk]:
    if meta.get("doc_type") == "minutes":
        return _chunk_minutes(pages, meta)
    return _chunk_rules(pages, meta)


# ------------------------------------------------------------------------------------------ rules
def _chunk_rules(pages: list[Page], meta: dict) -> list[Chunk]:
    no = meta.get("circular_no", "")
    sections: list[_Section] = []
    preamble = _Section(None, "Pendahuluan", pages[0].number if pages else 1, kind="preamble")
    current: _Section | None = None
    any_ocr = any(p.ocr for p in pages)

    for page, line, _ in _lines(pages):
        sub, top, item = SUB_RE.match(line), TOP_RE.match(line), ITEM_RE.match(line)
        if sub and current is not None:
            current.units.append(_Unit(sub.group(1), [line], page, page))
        elif top and not sub:
            num, rest = top.group(1), top.group(2).strip()
            if _is_heading_text(rest):
                current = _Section(num, rest, page)
            else:  # numbered paragraph without a heading
                current = _Section(num, "", page)
                current.units.append(_Unit(num, [line], page, page))
            sections.append(current)
        elif CAPS_RE.match(line) and not item:
            current = _Section(None, line, page)
            sections.append(current)
        elif current is None:
            if not preamble.units:
                preamble.units.append(_Unit(None, [], page, page))
            preamble.units[-1].add(line, page, continuation=False)
        else:
            if not current.units or item:
                current.units.append(_Unit(current.units[-1].ref if (item and current.units) else current.num,
                                           [line], page, page))
                if item and len(current.units) > 1:
                    # (a), (b) items stay inside the clause they belong to.
                    last = current.units.pop()
                    current.units[-1].add(last.text, page, continuation=False)
            else:
                current.units[-1].add(line, page, continuation=True)

    chunks: list[Chunk] = []
    # Preamble only when it carries real content (real circulars open with a salutation paragraph).
    if preamble.units and preamble.units[0].words >= 40 and not sections:
        sections.insert(0, preamble)
    elif preamble.units and preamble.units[0].words >= 40:
        sections.insert(0, preamble)

    for sec in sections:
        if not sec.units:
            continue
        heading_line = (f"{sec.num}. {sec.heading}" if sec.num and sec.heading else sec.heading or "").strip()
        groups: list[list[_Unit]] = [[]]
        for unit in sec.units:
            if groups[-1] and sum(u.words for u in groups[-1]) + unit.words > MAX_WORDS:
                groups.append([])
            groups[-1].append(unit)
        for group in groups:
            refs = [u.ref for u in group if u.ref]
            if not refs:
                clause = sec.num or sec.heading.title()
            elif len(refs) == 1 or refs[0] == refs[-1]:
                clause = refs[0]
            else:
                clause = f"{refs[0]}-{refs[-1]}"
            body = "\n".join(u.text for u in group)
            text = f"{heading_line}\n{body}".strip() if heading_line else body
            crumb_head = sec.heading.title() if sec.heading else f"Perenggan {sec.num}"
            chunks.append(Chunk(len(chunks), clause, f"{no} > {crumb_head} > {clause}",
                                min(u.page_start for u in group), max(u.page_end for u in group),
                                text, any_ocr))
    return chunks


# ---------------------------------------------------------------------------------------- minutes
def _chunk_minutes(pages: list[Page], meta: dict) -> list[Chunk]:
    no = meta.get("circular_no", "")
    when = malay_date(meta.get("issue_date"))
    any_ocr = any(p.ocr for p in pages)
    chunks: list[Chunk] = []
    item_no, item_title = None, ""
    unit: _Unit | None = None
    unit_kind = ""

    def flush() -> None:
        nonlocal unit
        if unit is None or not unit.lines:
            unit = None
            return
        if unit_kind == "Kehadiran":
            clause, head, label = "Kehadiran", "Kehadiran", "KEHADIRAN"
        elif unit_kind == "Perkara":
            clause, head, label = f"Perkara {item_no}", f"Perkara {item_no}: {item_title.title()}", None
        else:
            clause = f"Perkara {item_no} - {unit_kind}"
            head, label = f"Perkara {item_no}: {item_title.title()}", unit_kind.upper()
        context = f"PERKARA {item_no}: {item_title}" if item_no else ""
        body = unit.text
        if label and label != "KEHADIRAN":
            text = f"{context} - {label}: {body}" if context else f"{label}: {body}"
        elif label == "KEHADIRAN":
            text = f"KEHADIRAN: {body}"
        else:
            text = f"{context}\n{body}" if context else body
        for part in _split_words(text):
            chunks.append(Chunk(len(chunks), clause, f"{no} ({when}) > {head}" + (f" > {unit_kind}" if unit_kind not in ("Perkara", "Kehadiran") else ""),
                                unit.page_start, unit.page_end, part, any_ocr))
        unit = None

    for page, line, _ in _lines(pages):
        pm, km, tm, hm = PERKARA_RE.match(line), KEPUTUSAN_RE.match(line), TINDAKAN_RE.match(line), KEHADIRAN_RE.match(line)
        if pm:
            flush()
            item_no, item_title, unit_kind = pm.group(1), pm.group(2).strip(), "Perkara"
            unit = _Unit(None, [], page, page)
        elif km or tm or hm:
            flush()
            unit_kind = "Keputusan" if km else ("Tindakan" if tm else "Kehadiran")
            rest = (km or tm or hm).group(1).strip()
            unit = _Unit(None, [rest] if rest else [], page, page)
        elif unit is not None:
            unit.add(line, page, continuation=bool(unit.lines))
    flush()
    return chunks


def _split_words(text: str) -> list[str]:
    words = text.split(" ")
    if len(words) <= MAX_WORDS:
        return [text]
    return [" ".join(words[i:i + MAX_WORDS]) for i in range(0, len(words), MAX_WORDS)]
