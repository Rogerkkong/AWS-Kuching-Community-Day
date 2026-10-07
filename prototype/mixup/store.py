"""Store: every document, chunk, relation and user, held in memory (FAST MODE
replacement for PostgreSQL). Loaded from data/ and data/runtime/.

    store = Store()                       # loads data/, computes statuses
    store.docs["SPP-1-2023"].status       # 'AMENDED'
    store.search(user, "tempoh tuntutan") # BM25 with validity + clearance filters
    store.add_document(doc, pages)        # live ingestion (persisted in runtime/uploads)
    store.add_relations([...]); store.recompute()
    store.reset_runtime()                 # "Reset demo"

Base files (read-only):  data/metadata.csv, data/relations.csv, data/users.json,
                         data/glossary.json, data/documents/*
Runtime files (gitignored, cleared by Reset demo): data/runtime/uploads/,
  relations_pending.csv, notifications.json, subscriptions.json,
  query_log.jsonl, change_cache.json, llm_cache/
"""

from __future__ import annotations

import csv
import json
import re
import shutil
from dataclasses import asdict, fields
from datetime import date
from pathlib import Path
from typing import Any

from .config import Settings, load_settings, parse_date
from .ingest import chunk_document, extract_metadata, full_text, parse_file
from .llm import LLM, make_llm
from .models import Chunk, Document, Page, Relation, User
from .relations import load_relations_csv, save_relations_csv
from .search import BM25Index, build_index
from .search import search as _search
from .status import recompute_all
from .textutil import load_glossary, normalize_circular_no

METADATA_COLUMNS = [
    "doc_id", "circular_no", "series", "title", "issuer", "doc_type", "jurisdiction", "cluster",
    "issue_date", "effective_date", "expiry_date", "one_off", "classification_level", "language",
    "applicability", "source_url", "file",
]
PENDING_RELATIONS = "relations_pending.csv"
UPLOADS = "uploads"


def _to_bool(value) -> bool:
    return str(value).strip().lower() in ("1", "true", "yes", "y")


def _coerce(name: str, value: Any) -> Any:
    """Convert a CSV/JSON value to the Document field's type."""
    if name in ("issue_date", "effective_date", "expiry_date"):
        return parse_date(value)
    if name == "one_off":
        return value if isinstance(value, bool) else _to_bool(value)
    if name in ("classification_level", "page_count"):
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0
    if name == "ocr_pages":
        return [int(x) for x in (value or [])]
    return value if value is not None else ""


def make_document(doc_id: str, auto: dict, manual: dict | None = None) -> Document:
    """Document from regex suggestions (auto) overridden by non-empty manual values."""
    values: dict[str, Any] = {}
    names = {f.name for f in fields(Document)}
    for source in (auto or {}, manual or {}):
        for key, value in source.items():
            if key in names and key != "doc_id" and value is not None and str(value).strip() != "":
                values[key] = _coerce(key, value)
    if values.get("circular_no"):
        values["circular_no"] = normalize_circular_no(values["circular_no"]) or values["circular_no"]
    return Document(doc_id=doc_id, **values)


def document_to_json(doc: Document) -> dict:
    data = asdict(doc)
    for key in ("issue_date", "effective_date", "expiry_date"):
        data[key] = data[key].isoformat() if data[key] else ""
    return data


def document_from_json(data: dict) -> Document:
    names = {f.name for f in fields(Document)}
    return Document(**{k: _coerce(k, v) if k != "doc_id" else v for k, v in data.items() if k in names})


def load_users(path: Path) -> dict[str, User]:
    """users.json -> {user_id: User} (keeps file order)."""
    try:
        rows = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        rows = []
    users = {}
    names = {f.name for f in fields(User)}
    for row in rows:
        if row.get("user_id"):
            users[row["user_id"]] = User(**{k: v for k, v in row.items() if k in names})
    if not users:
        users["FED-T0"] = User(user_id="FED-T0", name="Pegawai Persekutuan (Terbuka)")
    return users


class Store:
    """In-memory data for the whole app. One instance is shared by every tab."""

    def __init__(self, settings: Settings | None = None, llm: LLM | None = None, load: bool = True):
        self.settings = settings or load_settings()
        self.data_dir = Path(self.settings.data_dir)
        self.runtime_dir = Path(self.settings.runtime_dir)
        self.llm: LLM = llm or make_llm(self.settings)
        self._clear()
        if load:
            self.load()

    # ------------------------------------------------------------------ state

    def _clear(self) -> None:
        self.docs: dict[str, Document] = {}
        self.pages: dict[str, list[Page]] = {}
        self.chunks: list[Chunk] = []
        self.chunks_by_doc: dict[str, list[Chunk]] = {}
        self.relations: list[Relation] = []
        self.users: dict[str, User] = {}
        self.glossary: list[tuple[str, str]] = []
        self.index: BM25Index = BM25Index()
        self.load_errors: list[str] = []
        self.last_status_changes: dict[str, tuple[str, str]] = {}
        self._edited_relation_ids: set[str] = set()
        self.revision = getattr(self, "revision", 0)

    @property
    def today(self) -> date:
        """Date used by the status engine (MIXUP_TODAY in tests)."""
        return self.settings.current_date()

    # ------------------------------------------------------------------ loading

    def load(self) -> None:
        """(Re)load everything from data/ and data/runtime/, then recompute statuses."""
        self._clear()
        self.glossary = load_glossary(self.data_dir / "glossary.json")
        self.users = load_users(self.data_dir / "users.json")
        self._load_base_documents()
        self._load_uploads()
        base = load_relations_csv(self.data_dir / "relations.csv", "csv")
        pending = load_relations_csv(self.runtime_path(PENDING_RELATIONS, create=False), "extracted")
        by_id = {r.relation_id: r for r in base}
        for rel in pending:  # runtime edits/approvals override the base row with the same id
            by_id[rel.relation_id] = rel
            if rel.origin == "csv":
                self._edited_relation_ids.add(rel.relation_id)
        self.relations = list(by_id.values())
        self.index = build_index(self.chunks, self.docs)
        self.recompute()

    def _load_base_documents(self) -> None:
        path = self.data_dir / "metadata.csv"
        if not path.exists():
            self.load_errors.append("data/metadata.csv not found")
            return
        with path.open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                doc_id = (row.get("doc_id") or "").strip()
                if not doc_id:
                    continue
                file_path = self.data_dir / (row.get("file") or "").strip()
                try:
                    pages = parse_file(file_path, doc_id)
                except Exception as exc:  # one broken file must not stop the demo
                    self.load_errors.append(f"{doc_id}: cannot read {row.get('file')} ({type(exc).__name__})")
                    continue
                doc = make_document(doc_id, extract_metadata(pages, file_path.name), row)
                doc.origin = "base"
                self._register(doc, pages)

    def _load_uploads(self) -> None:
        folder = self.runtime_dir / UPLOADS
        if not folder.exists():
            return
        for meta_path in sorted(folder.glob("*/doc.json")):
            try:
                data = json.loads(meta_path.read_text(encoding="utf-8"))
                doc = document_from_json(data["document"])
                pages = parse_file(meta_path.parent / data["filename"], doc.doc_id)
            except Exception as exc:
                self.load_errors.append(f"upload {meta_path.parent.name}: {type(exc).__name__}")
                continue
            self._register(doc, pages)

    def _register(self, doc: Document, pages: list[Page]) -> None:
        """Add/replace a document with its pages and chunks (index updated by caller)."""
        doc.page_count = len(pages)
        doc.ocr_pages = [p.page_no for p in pages if p.needs_ocr]
        chunks = chunk_document(doc, pages)
        if doc.doc_id in self.docs:
            self.chunks = [c for c in self.chunks if c.doc_id != doc.doc_id]
        self.docs[doc.doc_id] = doc
        self.pages[doc.doc_id] = pages
        self.chunks_by_doc[doc.doc_id] = chunks
        self.chunks.extend(chunks)

    # ------------------------------------------------------------------ status

    def recompute(self) -> dict[str, tuple[str, str]]:
        """Recompute every status. Returns {doc_id: (old, new)} for documents that changed."""
        changes = recompute_all(self.docs, self.relations, self.today)
        self.last_status_changes = changes
        self.revision += 1
        return changes

    # ------------------------------------------------------------------ lookups

    def get_doc(self, doc_id: str) -> Document | None:
        """Raw lookup (NO access check). UI code must use access.get_doc(store, user, id)."""
        return self.docs.get(doc_id)

    def doc_by_circular(self, circular_no: str) -> Document | None:
        """'SPP 1/2023' (or any spelling the regex understands) -> Document."""
        key = normalize_circular_no(circular_no) or (circular_no or "").strip()
        for doc in self.docs.values():
            if doc.circular_no == key:
                return doc
        return None

    def circular_map(self) -> dict[str, str]:
        """{normalised circular_no: doc_id} for resolving relation targets."""
        return {d.circular_no: d.doc_id for d in self.docs.values() if d.circular_no}

    def doc_text(self, doc_id: str) -> str:
        return full_text(self.pages.get(doc_id, []))

    def get_relation(self, relation_id: str) -> Relation | None:
        return next((r for r in self.relations if r.relation_id == relation_id), None)

    def verified_relations(self) -> list[Relation]:
        return [r for r in self.relations if r.verified and not r.rejected]

    def pending_relations(self) -> list[Relation]:
        """Unverified, not rejected (the verification queue)."""
        return [r for r in self.relations if not r.verified and not r.rejected]

    def incoming(self, doc_id: str, verified_only: bool = True) -> list[Relation]:
        """Relations whose target is doc_id."""
        rels = self.verified_relations() if verified_only else [r for r in self.relations if not r.rejected]
        return [r for r in rels if r.target_doc_id == doc_id]

    def outgoing(self, doc_id: str, verified_only: bool = True) -> list[Relation]:
        """Relations whose source is doc_id."""
        rels = self.verified_relations() if verified_only else [r for r in self.relations if not r.rejected]
        return [r for r in rels if r.source_doc_id == doc_id]

    def get_user(self, user_id: str) -> User | None:
        return self.users.get(user_id)

    def default_user(self) -> User:
        return next(iter(self.users.values()))

    # ------------------------------------------------------------------ search

    def search(self, user: User | None, query: str, **kwargs):
        """Shortcut for search.search(store, user, query, **kwargs)."""
        return _search(self, user, query, **kwargs)

    # ------------------------------------------------------------------ changes

    def unique_doc_id(self, wanted: str) -> str:
        """Safe doc_id ('SPP 1/2026' -> 'SPP-1-2026'); never collides with a base document."""
        base = re.sub(r"[^A-Za-z0-9]+", "-", wanted or "").strip("-") or "UPLOAD"
        candidate, n = base, 2
        while candidate in self.docs and self.docs[candidate].origin == "base":
            candidate = f"{base}-{n}"
            n += 1
        return candidate

    def add_document(self, doc: Document, pages: list[Page], raw: bytes | None = None, filename: str | None = None) -> str:
        """Ingest a new document live: chunk, index, persist to runtime/uploads, recompute.

        `raw`/`filename` are the original upload (kept so a restart reloads it).
        Returns the final doc_id.
        """
        if doc.doc_id in self.docs and self.docs[doc.doc_id].origin == "base":
            doc.doc_id = self.unique_doc_id(doc.doc_id)
        doc.origin = "upload"
        for page in pages:
            page.doc_id = doc.doc_id
        self.index.remove_doc(doc.doc_id)
        self._register(doc, pages)
        self.index.add(self.chunks_by_doc[doc.doc_id], self.docs)

        folder = self.runtime_dir / UPLOADS / doc.doc_id
        folder.mkdir(parents=True, exist_ok=True)
        if raw is None or not filename:  # keep the parsed pages (form-feed separated) so a reload works
            filename = "document.txt"
            raw = "\f".join(p.text for p in pages).encode("utf-8")
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(filename).name)
        (folder / safe_name).write_bytes(raw)
        doc.file = f"runtime/{UPLOADS}/{doc.doc_id}/{safe_name}"
        meta = {"document": document_to_json(doc), "filename": safe_name}
        (folder / "doc.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        self.recompute()
        return doc.doc_id

    def add_relations(self, relations: list[Relation], persist: bool = True) -> None:
        """Add (or replace by relation_id) relations, e.g. extracted candidates. Call recompute() after."""
        by_id = {r.relation_id: r for r in self.relations}
        for rel in relations:
            by_id[rel.relation_id] = rel
        self.relations = list(by_id.values())
        if persist:
            self.save_relations()

    def update_relation(self, relation_id: str, **changes) -> Relation | None:
        """Edit one relation (verified=True, relation_type=..., target_doc_id=...) and persist.

        Does not recompute statuses; call store.recompute() afterwards.
        """
        rel = self.get_relation(relation_id)
        if rel is None:
            return None
        for key, value in changes.items():
            if key == "effective_date":
                value = parse_date(value)
            if hasattr(rel, key):
                setattr(rel, key, value)
        if rel.origin == "csv":
            self._edited_relation_ids.add(rel.relation_id)
        self.save_relations()
        return rel

    def save_relations(self) -> None:
        """Persist runtime relations (extracted + edited) to runtime/relations_pending.csv."""
        runtime = [r for r in self.relations if r.origin != "csv" or r.relation_id in self._edited_relation_ids]
        save_relations_csv(self.runtime_path(PENDING_RELATIONS), runtime)

    def set_llm_provider(self, provider: str) -> LLM:
        """Switch offline / ollama / bedrock at runtime (sidebar)."""
        self.llm = make_llm(self.settings, provider)
        return self.llm

    # ------------------------------------------------------------------ runtime files

    def runtime_path(self, name: str, create: bool = True) -> Path:
        """Path of a runtime file (folder created on demand)."""
        if create:
            self.runtime_dir.mkdir(parents=True, exist_ok=True)
        return self.runtime_dir / name

    def read_json(self, name: str, default: Any = None) -> Any:
        try:
            return json.loads(self.runtime_path(name, create=False).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return default

    def write_json(self, name: str, data: Any) -> None:
        path = self.runtime_path(name)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        tmp.replace(path)

    def append_jsonl(self, name: str, record: dict) -> None:
        with self.runtime_path(name).open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")

    def read_jsonl(self, name: str) -> list[dict]:
        path = self.runtime_path(name, create=False)
        if not path.exists():
            return []
        out = []
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
        return out

    def reset_runtime(self) -> None:
        """'Reset demo': delete everything in runtime/ (uploads, logs, alerts...) and reload."""
        if self.runtime_dir.exists():
            for path in self.runtime_dir.iterdir():
                if path.name == ".gitkeep":
                    continue
                if path.is_dir():
                    shutil.rmtree(path, ignore_errors=True)
                else:
                    path.unlink(missing_ok=True)
        self.load()
