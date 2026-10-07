"""Documents, lineage, page images and clause diffs, always through the user's allowed packs."""
from __future__ import annotations

import re

import pymupdf
from fastapi import APIRouter, Query, Request
from fastapi.responses import Response

from app import db
from app.services.retrieval.filters import fetch_document, fetch_documents, open_packs
from app.services.validity.lineage import change_view, lineage

router = APIRouter(prefix="/api", tags=["documents"])


@router.get("/documents")
def list_documents(request: Request, status: str | None = None, jurisdiction: str | None = None,
                   cluster: str | None = None, doc_type: str | None = None) -> dict:
    st = request.app.state.pn
    user = st.current_user()
    where, params = ["1=1"], []
    for col, val in (("status", status), ("jurisdiction", jurisdiction), ("cluster", cluster), ("doc_type", doc_type)):
        if val:
            values = [v for v in val.split(",") if v]
            where.append(f"d.{col} IN ({','.join('?' * len(values))})")
            params += values
    with open_packs(st, user) as (handles, warnings):
        docs = fetch_documents(handles, int(user["clearance_level"]), " AND ".join(where), params)
    docs.sort(key=lambda d: (d.get("issue_date") or ""), reverse=True)
    return {"documents": docs, "warnings": warnings}


@router.get("/documents/{doc_id}")
def get_document(doc_id: int, request: Request) -> dict:
    st = request.app.state.pn
    user = st.current_user()
    clearance = int(user["clearance_level"])
    with open_packs(st, user) as (handles, _):
        found = fetch_document(handles, clearance, doc_id)
        if not found:
            raise LookupError("Document not found")
        doc, h = found
        chunks = db.rows(h.conn.execute(
            "SELECT id, chunk_index, clause_ref, breadcrumb, page_start, page_end, text FROM chunks WHERE document_id = ? "
            "ORDER BY chunk_index", (doc_id,)))
        pdf = h.conn.execute("SELECT pdf FROM files WHERE document_id = ?", (doc_id,)).fetchone()
        pages = 0
        if pdf and pdf[0]:
            with pymupdf.open(stream=pdf[0], filetype="pdf") as d:
                pages = d.page_count
    return {"document": doc, "chunks": chunks, "page_count": pages, "pack_tier": h.tier}


@router.get("/documents/{doc_id}/lineage")
def get_lineage(doc_id: int, request: Request) -> dict:
    st = request.app.state.pn
    user = st.current_user()
    with open_packs(st, user) as (handles, _):
        return lineage(handles, int(user["clearance_level"]), doc_id)


def _fragments(text: str) -> list[str]:
    """Search fragments for highlighting: each clause line, cut to a length PyMuPDF can find on one line."""
    out = []
    for line in text.split("\n"):
        line = re.sub(r"^PERKARA \d+:.*? - (KEPUTUSAN|TINDAKAN): ", "", line.strip())
        line = re.sub(r"^(KEPUTUSAN|TINDAKAN|KEHADIRAN): ", "", line)
        words = line.split()
        for i in range(0, len(words), 7):
            frag = " ".join(words[i:i + 7])
            if len(frag) >= 12:
                out.append(frag)
    return out[:80]


@router.get("/documents/{doc_id}/pages/{page}.png")
def page_image(doc_id: int, page: int, request: Request, highlight: str | None = Query(None, max_length=6000),
               zoom: float = Query(1.6, ge=0.5, le=3.0)) -> Response:
    st = request.app.state.pn
    user = st.current_user()
    with open_packs(st, user) as (handles, _):
        found = fetch_document(handles, int(user["clearance_level"]), doc_id)
        if not found:
            raise LookupError("Document not found")
        _, h = found
        row = h.conn.execute("SELECT pdf FROM files WHERE document_id = ?", (doc_id,)).fetchone()
    if not row or not row[0]:
        raise LookupError("No PDF stored for this document")
    with pymupdf.open(stream=row[0], filetype="pdf") as d:
        if not 1 <= page <= d.page_count:
            raise LookupError("Page out of range")
        p = d[page - 1]
        hits = 0
        for frag in _fragments(highlight or ""):
            quads = p.search_for(frag, quads=True)
            if quads:
                annot = p.add_highlight_annot(quads)
                annot.set_colors(stroke=(1.0, 0.85, 0.3))
                annot.update()
                hits += 1
        png = p.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom)).tobytes("png")
        count = d.page_count
    return Response(png, media_type="image/png",
                    headers={"X-Page-Count": str(count), "X-Highlights": str(hits), "Cache-Control": "no-store"})


@router.get("/diff")
def diff(request: Request, old: int, new: int) -> dict:
    st = request.app.state.pn
    user = st.current_user()
    with open_packs(st, user) as (handles, _):
        return change_view(handles, int(user["clearance_level"]), old, new)
