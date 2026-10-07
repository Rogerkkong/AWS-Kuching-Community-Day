"""Access control: the single choke point for classification tiers.

Clearance levels: 0 Terbuka, 1 Terhad, 2 Sulit. A user sees a document only if
doc.classification_level <= user.clearance_level. EVERY path that returns
content (search, excluded list, lineage, diff, library, source viewer,
analytics, notifications) must go through these helpers. This is enforced in
code, never by the LLM.

A missing user (None) is treated as clearance 0 (safest default).
"""

from __future__ import annotations

from typing import Iterable, TypeVar

from .models import Document, Page, Relation, User

T = TypeVar("T")

HIDDEN_PLACEHOLDER_MS = "{n} dokumen terhad disembunyikan"
HIDDEN_PLACEHOLDER_EN = "{n} restricted document(s) hidden"


def clearance(user: User | None) -> int:
    """The user's clearance level (0 when unknown)."""
    try:
        return int(user.clearance_level) if user is not None else 0
    except (TypeError, ValueError):
        return 0


def can_see(user: User | None, doc: Document | None) -> bool:
    """True if the user may see this document (None doc -> False)."""
    return doc is not None and int(doc.classification_level or 0) <= clearance(user)


def visible_docs(store, user: User | None) -> dict[str, Document]:
    """{doc_id: Document} the user may see."""
    return {doc_id: d for doc_id, d in store.docs.items() if can_see(user, d)}


def visible_doc_ids(store, user: User | None) -> set[str]:
    return set(visible_docs(store, user))


def get_doc(store, user: User | None, doc_id: str) -> Document | None:
    """The document, or None if it does not exist OR the user may not see it."""
    doc = store.docs.get(doc_id)
    return doc if can_see(user, doc) else None


def get_pages(store, user: User | None, doc_id: str) -> list[Page]:
    """Pages for the source viewer; [] when hidden."""
    return list(store.pages.get(doc_id, [])) if get_doc(store, user, doc_id) else []


def get_chunks(store, user: User | None, doc_id: str) -> list:
    """Chunks of one document; [] when hidden."""
    return list(store.chunks_by_doc.get(doc_id, [])) if get_doc(store, user, doc_id) else []


def _doc_id_of(item) -> str | None:
    """doc_id of a Document, Chunk, Hit, Citation, dict or Relation-like item."""
    if isinstance(item, dict):
        return item.get("doc_id") or item.get("document_id")
    if hasattr(item, "doc") and hasattr(item.doc, "doc_id"):
        return item.doc.doc_id
    return getattr(item, "doc_id", None)


def filter_chunks(store, user: User | None, items: Iterable[T]) -> list[T]:
    """Keep only items (Chunks, Hits, Citations, dicts with doc_id) the user may see.

    Items whose document is unknown are dropped (fail closed).
    """
    allowed = visible_doc_ids(store, user)
    return [item for item in items if _doc_id_of(item) in allowed]


def filter_docs(store, user: User | None, items: Iterable[T]) -> list[T]:
    """Same as filter_chunks, for Documents or {doc_id: ...} dicts (e.g. log rows)."""
    return filter_chunks(store, user, items)


def filter_relations(store, user: User | None, relations: Iterable[Relation]) -> list[Relation]:
    """Relations whose source AND (known) target are visible to the user."""
    allowed = visible_doc_ids(store, user)
    out = []
    for rel in relations:
        if rel.source_doc_id not in allowed:
            continue
        if rel.target_doc_id and rel.target_doc_id not in allowed:
            continue
        out.append(rel)
    return out


def hidden_count(store, user: User | None, doc_ids: Iterable[str]) -> int:
    """How many of these (existing) documents are hidden from the user."""
    return sum(1 for d in set(doc_ids) if d in store.docs and not can_see(user, store.docs[d]))


def hidden_placeholder(n: int, lang: str = "ms") -> str:
    """'1 dokumen terhad disembunyikan' (never reveals titles or numbers)."""
    return (HIDDEN_PLACEHOLDER_EN if lang == "en" else HIDDEN_PLACEHOLDER_MS).format(n=n)
