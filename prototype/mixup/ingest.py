"""Reading documents and the manifest, and cutting text into chunks.

Supported files:
  .pdf        one Page per PDF page (pypdf)
  .md         one Page per Markdown heading section (section number = page_no)
  .txt        split on form-feed characters if present, else on heading-like lines
  .docx       paragraphs grouped per Word heading (python-docx)
"""

from __future__ import annotations

import csv
import io
import re
from pathlib import Path
from typing import Iterable

from .models import Chunk, DocMeta, Page

MANIFEST_COLUMNS = [
    "doc_id",
    "title",
    "doc_type",
    "issuer",
    "number",
    "date_issued",
    "language",
    "status",
    "supersedes",
    "superseded_by",
    "file",
    "source_url",
    "summary",
    "tags",
]
SUPPORTED_EXTENSIONS = (".pdf", ".md", ".markdown", ".txt", ".docx")


# ----------------------------------------------------------------------------
# Manifest (CSV) <-> DocMeta
# ----------------------------------------------------------------------------


def _split_list(value: str) -> list[str]:
    return [v.strip() for v in re.split(r"[;|]", value or "") if v.strip()]


def load_manifest(path: str | Path) -> dict[str, DocMeta]:
    """Read a manifest CSV into {doc_id: DocMeta}. A missing file gives {}."""
    path = Path(path)
    docs: dict[str, DocMeta] = {}
    if not path.exists():
        return docs
    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            doc_id = (row.get("doc_id") or "").strip()
            if not doc_id:
                continue
            docs[doc_id] = DocMeta(
                doc_id=doc_id,
                title=(row.get("title") or doc_id).strip(),
                doc_type=(row.get("doc_type") or "other").strip(),
                issuer=(row.get("issuer") or "").strip(),
                number=(row.get("number") or "").strip(),
                date_issued=(row.get("date_issued") or "").strip(),
                language=(row.get("language") or "en").strip(),
                status=(row.get("status") or "in_force").strip(),
                supersedes=_split_list(row.get("supersedes", "")),
                superseded_by=(row.get("superseded_by") or "").strip(),
                file=(row.get("file") or "").strip(),
                source_url=(row.get("source_url") or "").strip(),
                summary=(row.get("summary") or "").strip(),
                tags=_split_list(row.get("tags", "")),
            )
    return docs


def save_manifest(path: str | Path, docs: Iterable[DocMeta]) -> None:
    """Write DocMeta objects to a manifest CSV (lists joined with ';')."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=MANIFEST_COLUMNS)
        writer.writeheader()
        for d in docs:
            writer.writerow(
                {
                    "doc_id": d.doc_id,
                    "title": d.title,
                    "doc_type": d.doc_type,
                    "issuer": d.issuer,
                    "number": d.number,
                    "date_issued": d.date_issued,
                    "language": d.language,
                    "status": d.status,
                    "supersedes": ";".join(d.supersedes),
                    "superseded_by": d.superseded_by,
                    "file": d.file,
                    "source_url": d.source_url,
                    "summary": d.summary,
                    "tags": ";".join(d.tags),
                }
            )


# ----------------------------------------------------------------------------
# Reading files into pages
# ----------------------------------------------------------------------------

_MD_HEADING = re.compile(r"^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
# Plain-text headings: "1. TUJUAN", "2.1 Scope", "PURPOSE", "BAHAGIAN A - SKOP"
_TXT_HEADING = re.compile(r"^\s*(?:\d+(?:\.\d+)*\.?\s+[A-Z][^\n]{1,78}|[A-Z][A-Z0-9 ,&()/\-]{3,78})\s*$")


def _sections(lines: list[str], is_heading) -> list[tuple[str, str]]:
    """Group lines into (heading, body) sections. Text before the first heading has heading ''."""
    sections: list[tuple[str, list[str]]] = [("", [])]
    for line in lines:
        heading = is_heading(line)
        if heading is not None:
            sections.append((heading, []))
        else:
            sections[-1][1].append(line)
    out = []
    pending_heading = ""
    for heading, body_lines in sections:
        body = "\n".join(body_lines).strip()
        if not body:
            # Heading with no text (e.g. a title right before a sub-heading): carry it forward.
            pending_heading = " > ".join(h for h in (pending_heading, heading) if h)
            continue
        full_heading = " > ".join(h for h in (pending_heading, heading) if h) if pending_heading else heading
        pending_heading = ""
        out.append((full_heading, body))
    return out


def _md_heading(line: str) -> str | None:
    m = _MD_HEADING.match(line)
    return m.group(2).strip() if m else None


def _txt_heading(line: str) -> str | None:
    if _MD_HEADING.match(line):
        return _md_heading(line)
    stripped = line.strip()
    if stripped and len(stripped) <= 80 and _TXT_HEADING.match(stripped) and not stripped.endswith((".", ",", ";")):
        return stripped
    return None


def _pages_from_text(doc_id: str, text: str, markdown: bool) -> list[Page]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if not markdown and "\f" in text:
        pages = []
        for i, part in enumerate(text.split("\f"), start=1):
            body = part.strip()
            if body:
                first = body.splitlines()[0].strip()
                pages.append(Page(doc_id=doc_id, page_no=i, text=body, heading=first[:80]))
        return pages
    sections = _sections(text.split("\n"), _md_heading if markdown else _txt_heading)
    return [Page(doc_id=doc_id, page_no=i, text=body, heading=heading) for i, (heading, body) in enumerate(sections, 1)]


def _pages_from_pdf(doc_id: str, data: bytes) -> list[Page]:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    pages = []
    for i, pdf_page in enumerate(reader.pages, start=1):
        try:
            body = (pdf_page.extract_text() or "").strip()
        except Exception:  # a broken page should not kill the whole upload
            body = ""
        if body:
            first = body.splitlines()[0].strip()
            pages.append(Page(doc_id=doc_id, page_no=i, text=body, heading=first[:80]))
    return pages


def _pages_from_docx(doc_id: str, data: bytes) -> list[Page]:
    import docx  # python-docx

    document = docx.Document(io.BytesIO(data))
    lines: list[str] = []
    headings: set[int] = set()
    for para in document.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        style = (para.style.name if para.style is not None else "") or ""
        if style.lower().startswith(("heading", "title")):
            headings.add(len(lines))
        lines.append(text)
    # Tables (common in circulars) are added as pipe-separated rows at the end.
    for table in document.tables:
        for row in table.rows:
            lines.append(" | ".join(cell.text.strip() for cell in row.cells))

    index = {"i": -1}

    def is_heading(line: str) -> str | None:
        index["i"] += 1
        return line if index["i"] in headings else None

    sections = _sections(lines, is_heading)
    return [Page(doc_id=doc_id, page_no=i, text=body, heading=heading) for i, (heading, body) in enumerate(sections, 1)]


def read_document_bytes(filename: str, data: bytes, doc_id: str | None = None) -> list[Page]:
    """Read an uploaded file's bytes into Pages. Raises ValueError for unsupported types."""
    ext = Path(filename).suffix.lower()
    doc_id = doc_id or Path(filename).stem
    if ext == ".pdf":
        return _pages_from_pdf(doc_id, data)
    if ext == ".docx":
        return _pages_from_docx(doc_id, data)
    if ext in (".md", ".markdown", ".txt"):
        text = data.decode("utf-8", errors="replace")
        return _pages_from_text(doc_id, text, markdown=ext != ".txt")
    raise ValueError(f"Unsupported file type '{ext}'. Use PDF, DOCX, MD or TXT.")


def read_document(path: str | Path, doc_id: str | None = None) -> list[Page]:
    """Read a file from disk into Pages (see module docstring for the rules)."""
    path = Path(path)
    return read_document_bytes(path.name, path.read_bytes(), doc_id or path.stem)


def pages_to_text(pages: list[Page]) -> str:
    """Join pages back into one string (headings included) for prompts and regexes."""
    parts = []
    for p in pages:
        parts.append(f"{p.heading}\n{p.text}" if p.heading else p.text)
    return "\n\n".join(parts)


# ----------------------------------------------------------------------------
# Chunking
# ----------------------------------------------------------------------------


def _windows(text: str, size: int, overlap: int) -> list[str]:
    """Cut text into ~size-character windows that overlap and end on a word boundary."""
    text = text.strip()
    if len(text) <= size:
        return [text] if text else []
    pieces = []
    start = 0
    while start < len(text):
        end = min(len(text), start + size)
        if end < len(text):
            # prefer to cut at a paragraph, then a sentence, then a space
            window = text[start:end]
            cut = max(window.rfind("\n\n"), window.rfind(". "), window.rfind("\n"))
            if cut < size * 0.5:
                cut = window.rfind(" ")
            if cut > size * 0.3:
                end = start + cut + 1
        piece = text[start:end].strip()
        if piece:
            pieces.append(piece)
        if end >= len(text):
            break
        next_start = max(end - overlap, start + 1)
        # move the overlap start to a word boundary
        space = text.find(" ", next_start)
        start = space + 1 if 0 <= space < end else next_start
    return pieces


def chunk_pages(pages: list[Page], size: int = 900, overlap: int = 150) -> list[Chunk]:
    """Split pages into Chunks of about `size` characters with `overlap` characters shared."""
    chunks: list[Chunk] = []
    for page in pages:
        for i, piece in enumerate(_windows(page.text, size, overlap)):
            chunks.append(
                Chunk(
                    chunk_id=f"{page.doc_id}#p{page.page_no}-c{i}",
                    doc_id=page.doc_id,
                    page_no=page.page_no,
                    heading=page.heading,
                    text=piece,
                )
            )
    return chunks
