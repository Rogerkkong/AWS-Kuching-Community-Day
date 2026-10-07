"""AppContext: everything a feature needs (documents, search index, version graph, AI).

    ctx = build_context(load_settings())        # in the app
    ctx.docs["PK-2024-01"].title                # metadata
    ctx.doc_text("PK-2024-01")                  # full text
    ctx.index.search("tuntutan perjalanan")     # search
    ctx.versions.latest("PK-2021-03")           # -> "PK-2024-01"
    ctx.llm.text(system, prompt)                # AI (raises LLMError when offline)

Base documents live in data/manifest.csv + data/documents/. Uploads live in
data/uploads/ with their own manifest_uploads.csv, so "Reset demo" just deletes
that folder's contents. The base manifest is never modified.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .config import Settings
from .ingest import (
    SUPPORTED_EXTENSIONS,
    chunk_pages,
    load_manifest,
    pages_to_text,
    read_document,
    save_manifest,
)
from .llm import LLM, make_llm
from .models import STATUS_IN_FORCE, STATUS_RECORD, STATUS_SUPERSEDED, STATUSES, Chunk, DocMeta, Page
from .search import Index, make_embedder
from .versions import VersionGraph

BASE_MANIFEST = "manifest.csv"
UPLOADS_DIR = "uploads"
UPLOAD_MANIFEST = "manifest_uploads.csv"


@dataclass
class AppContext:
    """Shared state for the whole app. Rebuilt by reload() after uploads/reset."""

    settings: Settings
    llm: LLM
    docs: dict[str, DocMeta]
    chunks: list[Chunk]
    index: Index
    versions: VersionGraph
    data_dir: Path
    pages: dict[str, list[Page]] = field(default_factory=dict)  # doc_id -> pages
    uploaded_ids: list[str] = field(default_factory=list)  # doc_ids added via Smart Upload
    load_errors: list[str] = field(default_factory=list)  # e.g. missing files
    revision: int = 0  # +1 after every add_document/reset (use it as a cache key in the UI)

    # -- convenience --------------------------------------------------------------

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / UPLOADS_DIR

    @property
    def upload_manifest_path(self) -> Path:
        return self.uploads_dir / UPLOAD_MANIFEST

    def get_doc(self, doc_id: str) -> DocMeta | None:
        return self.docs.get(doc_id)

    def doc_text(self, doc_id: str) -> str:
        """Full text of a document (headings included), '' if unknown."""
        return pages_to_text(self.pages.get(doc_id, []))

    def in_force_docs(self) -> list[DocMeta]:
        return [d for d in self.docs.values() if d.status == STATUS_IN_FORCE]

    def latest_doc(self, doc_id: str) -> DocMeta | None:
        """The newest version of a document (itself if not superseded)."""
        return self.docs.get(self.versions.latest(doc_id))

    # -- changing the library -----------------------------------------------------

    def reload(self) -> None:
        """Re-read manifests and files from disk and rebuild index + graph."""
        fresh = _load(self.settings, self.data_dir)
        self.docs = fresh["docs"]
        self.pages = fresh["pages"]
        self.chunks = fresh["chunks"]
        self.index = fresh["index"]
        self.versions = fresh["versions"]
        self.uploaded_ids = fresh["uploaded_ids"]
        self.load_errors = fresh["load_errors"]
        self.revision += 1

    def add_document(self, meta: DocMeta, file_bytes: bytes, filename: str) -> DocMeta:
        """Save an uploaded document, mark what it supersedes, and refresh everything.

        Returns the stored DocMeta (its doc_id may be adjusted to stay unique).
        """
        ext = Path(filename).suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file type '{ext}'. Use PDF, DOCX, MD or TXT.")

        uploads = load_manifest(self.upload_manifest_path)
        base_ids = set(self.docs) - set(uploads)
        doc_id = re.sub(r"[^A-Za-z0-9_-]+", "-", meta.doc_id or "").strip("-") or f"UPLOAD-{len(uploads) + 1}"
        candidate, n = doc_id, 2
        while candidate in base_ids:  # never overwrite a base document
            candidate = f"{doc_id}-{n}"
            n += 1
        doc_id = candidate

        # Replacing an earlier upload with the same id: remove its old file.
        if doc_id in uploads and uploads[doc_id].file:
            old_path = self.data_dir / uploads[doc_id].file
            if old_path.exists():
                old_path.unlink()

        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        stored_name = f"{doc_id}{ext}"
        (self.uploads_dir / stored_name).write_bytes(file_bytes)

        meta.doc_id = doc_id
        meta.file = f"{UPLOADS_DIR}/{stored_name}"
        if meta.status not in STATUSES or meta.status == STATUS_SUPERSEDED:
            meta.status = STATUS_RECORD if meta.doc_type in ("minutes", "report") else STATUS_IN_FORCE
        meta.supersedes = [s for s in dict.fromkeys(meta.supersedes) if s in self.docs and s != doc_id]
        meta.superseded_by = ""

        uploads[doc_id] = meta
        save_manifest(self.upload_manifest_path, uploads.values())
        self.reload()
        return self.docs[doc_id]

    def reset_uploads(self) -> None:
        """Delete every uploaded document (keeps data/uploads/.gitkeep) and reload."""
        if self.uploads_dir.exists():
            for path in self.uploads_dir.iterdir():
                if path.is_file() and path.name != ".gitkeep":
                    path.unlink()
        self.reload()


# ----------------------------------------------------------------------------
# Loading
# ----------------------------------------------------------------------------


def _apply_supersession(docs: dict[str, DocMeta]) -> None:
    """Make status/supersedes/superseded_by consistent across all documents."""
    for doc in docs.values():
        for old_id in doc.supersedes:
            old = docs.get(old_id)
            if old is not None:
                old.status = STATUS_SUPERSEDED
                old.superseded_by = doc.doc_id
    for doc in docs.values():
        if doc.superseded_by and doc.superseded_by in docs:
            doc.status = STATUS_SUPERSEDED
            newer = docs[doc.superseded_by]
            if doc.doc_id not in newer.supersedes:
                newer.supersedes.append(doc.doc_id)


def _load(settings: Settings, data_dir: Path) -> dict:
    base = load_manifest(data_dir / BASE_MANIFEST)
    uploads = load_manifest(data_dir / UPLOADS_DIR / UPLOAD_MANIFEST)
    docs: dict[str, DocMeta] = dict(base)
    for doc_id, meta in uploads.items():
        if doc_id not in docs:  # base documents always win
            docs[doc_id] = meta
    _apply_supersession(docs)

    pages: dict[str, list[Page]] = {}
    chunks: list[Chunk] = []
    errors: list[str] = []
    for doc in docs.values():
        path = data_dir / doc.file if doc.file else None
        if path is None or not path.exists():
            errors.append(f"{doc.doc_id}: file not found ({doc.file or 'no file'})")
            pages[doc.doc_id] = []
            continue
        try:
            doc_pages = read_document(path, doc.doc_id)
        except Exception as exc:  # one bad file must not break the app
            errors.append(f"{doc.doc_id}: could not read file ({type(exc).__name__})")
            doc_pages = []
        pages[doc.doc_id] = doc_pages
        chunks.extend(chunk_pages(doc_pages))

    texts = {doc_id: pages_to_text(p) for doc_id, p in pages.items()}
    return {
        "docs": docs,
        "pages": pages,
        "chunks": chunks,
        "index": Index(chunks, docs, embedder=make_embedder(settings)),
        "versions": VersionGraph(docs, texts),
        "uploaded_ids": [d for d in uploads if d in docs and d not in base],
        "load_errors": errors,
    }


def build_context(settings: Settings, llm: LLM | None = None) -> AppContext:
    """Load everything from settings.data_dir. Pass llm to inject a FakeLLM in tests."""
    data_dir = Path(settings.data_dir)
    fresh = _load(settings, data_dir)
    return AppContext(
        settings=settings,
        llm=llm if llm is not None else make_llm(settings),
        docs=fresh["docs"],
        chunks=fresh["chunks"],
        index=fresh["index"],
        versions=fresh["versions"],
        data_dir=data_dir,
        pages=fresh["pages"],
        uploaded_ids=fresh["uploaded_ids"],
        load_errors=fresh["load_errors"],
    )


# Module-level wrappers (same behaviour as the methods).
def add_document(ctx: AppContext, meta: DocMeta, file_bytes: bytes, filename: str) -> DocMeta:
    return ctx.add_document(meta, file_bytes, filename)


def reset_uploads(ctx: AppContext) -> None:
    ctx.reset_uploads()
