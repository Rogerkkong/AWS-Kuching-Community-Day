"""Which document replaced which: the version graph, plus text detectors.

Edges are (src, dst, relation):
  (new, old, "supersedes")     new document replaces old
  (a, b, "references")         a mentions b
  (a, b, "conflicts")          a and b are both in force but disagree (added by features)
  (doc, minutes, "discussed_in")  doc is discussed in the meeting minutes
"""

from __future__ import annotations

import re
from typing import Iterable

from .models import (
    REL_CONFLICTS,
    REL_DISCUSSED_IN,
    REL_REFERENCES,
    REL_SUPERSEDES,
    STATUS_SUPERSEDED,
    DocMeta,
)
from .textutil import normalize, split_sentences

# "Bil. 3/2021", "Bil. 3 Tahun 2021", "No. 3/2021", "PK 3/2021", "No. 3 of 2021"
NUMBER_RE = re.compile(r"(?<![\d/])(\d{1,3})\s*(?:/|\s+tahun\s+|\s+of\s+)((?:19|20)\d{2})\b", re.IGNORECASE)

# "X supersedes Y": the superseded document comes AFTER these words.
ACTIVE_RE = re.compile(
    r"\b(membatalkan|menggantikan|memansuhkan|supersedes?|superseding|replaces?|replacing|"
    r"cancels?|cancelling|revokes?|revoking|repeals?)\b",
    re.IGNORECASE,
)
# "Y is hereby revoked": the superseded document comes BEFORE these words.
PASSIVE_RE = re.compile(
    r"(dengan ini dibatalkan|adalah dibatalkan|dibatalkan|digantikan|dimansuhkan|"
    r"tidak lagi berkuat kuasa|is hereby revoked|is hereby cancelled|is hereby repealed|"
    r"are hereby revoked|is hereby superseded|is superseded|is replaced|is revoked|is cancelled|"
    r"no longer in force)",
    re.IGNORECASE,
)


def number_keys(text: str) -> set[tuple[int, str]]:
    """All (number, year) pairs in a text: "Bil. 3 Tahun 2021" -> {(3, "2021")}."""
    return {(int(n), year) for n, year in NUMBER_RE.findall(text or "")}


def _mentions(sentence: str, docs: dict[str, DocMeta], exclude_id: str | None) -> list[tuple[str, int]]:
    """Find documents mentioned in a sentence. Returns [(doc_id, char_position)]."""
    found: dict[str, int] = {}
    # 1) by number, e.g. "Bil. 3/2021"
    for m in NUMBER_RE.finditer(sentence):
        key = (int(m.group(1)), m.group(2))
        for doc in docs.values():
            if doc.doc_id != exclude_id and key in number_keys(doc.number):
                found.setdefault(doc.doc_id, m.start())
    # 2) by title or doc_id
    norm_sentence = normalize(sentence)
    lower_sentence = sentence.lower()
    for doc in docs.values():
        if doc.doc_id == exclude_id or doc.doc_id in found:
            continue
        pos = lower_sentence.find(doc.doc_id.lower())
        if pos >= 0:
            found[doc.doc_id] = pos
            continue
        title = normalize(doc.title.split(" - ")[0]) if " - " in doc.title else normalize(doc.title)
        if len(title) >= 12 and title in norm_sentence:
            # normalizing only drops punctuation/extra spaces, so this position is close enough
            found[doc.doc_id] = norm_sentence.find(title)
    return list(found.items())


def detect_supersession(
    text: str, docs: dict[str, DocMeta], exclude_id: str | None = None
) -> list[tuple[str, str]]:
    """Find documents that `text` says it cancels/replaces.

    Returns [(doc_id, evidence_sentence)], e.g.
    [("PK-2021-03", "Pekeliling ini membatalkan Pekeliling Perkhidmatan Bil. 3 Tahun 2021 ...")]
    """
    results: dict[str, str] = {}
    for sentence in split_sentences(text):
        active = list(ACTIVE_RE.finditer(sentence))
        passive = list(PASSIVE_RE.finditer(sentence))
        if not active and not passive:
            continue
        for doc_id, pos in _mentions(sentence, docs, exclude_id):
            # "X supersedes Y": Y after the verb.  "Y is hereby revoked": Y before the phrase.
            after_active = any(pos > m.start() for m in active)
            before_passive = any(pos < m.start() for m in passive)
            if after_active or before_passive:
                results.setdefault(doc_id, sentence.strip())
    return list(results.items())


def detect_references(
    text: str, docs: dict[str, DocMeta], exclude_id: str | None = None
) -> list[tuple[str, str]]:
    """Find documents that `text` mentions (by number, title or doc_id), without saying it replaces them.

    Returns [(doc_id, evidence_sentence)].
    """
    superseded = {doc_id for doc_id, _ in detect_supersession(text, docs, exclude_id)}
    results: dict[str, str] = {}
    for sentence in split_sentences(text):
        for doc_id, _pos_ in _mentions(sentence, docs, exclude_id):
            if doc_id not in superseded:
                results.setdefault(doc_id, sentence.strip())
    return list(results.items())


class VersionGraph:
    """Relationships between documents.

    Built from the manifest (supersedes / superseded_by) and, when `texts`
    ({doc_id: full text}) is given, from mentions inside documents.
    """

    def __init__(self, docs: dict[str, DocMeta], texts: dict[str, str] | None = None):
        self.docs = docs
        self.texts = texts or {}
        self.edges: list[tuple[str, str, str]] = []
        self.rebuild()

    # -- building ---------------------------------------------------------------

    def rebuild(self) -> None:
        """Recompute all edges from docs and texts (keeps manually added conflict edges)."""
        manual = [e for e in self.edges if e[2] == REL_CONFLICTS]
        self.edges = []
        for doc in self.docs.values():
            for old in doc.supersedes:
                if old in self.docs:
                    self.add_edge(doc.doc_id, old, REL_SUPERSEDES)
            if doc.superseded_by and doc.superseded_by in self.docs:
                self.add_edge(doc.superseded_by, doc.doc_id, REL_SUPERSEDES)
        for doc_id, text in self.texts.items():
            if doc_id not in self.docs:
                continue
            is_minutes = self.docs[doc_id].doc_type == "minutes"
            for other, _evidence in detect_references(text, self.docs, exclude_id=doc_id):
                if self._linked(doc_id, other):
                    continue
                if is_minutes:
                    self.add_edge(other, doc_id, REL_DISCUSSED_IN)
                else:
                    self.add_edge(doc_id, other, REL_REFERENCES)
        for edge in manual:
            self.add_edge(*edge)

    def add_edge(self, src: str, dst: str, relation: str) -> None:
        """Add an edge once (no duplicates)."""
        edge = (src, dst, relation)
        if src != dst and edge not in self.edges:
            self.edges.append(edge)

    def _linked(self, a: str, b: str) -> bool:
        return any({s, d} == {a, b} for s, d, _ in self.edges)

    # -- questions --------------------------------------------------------------

    def successors(self, doc_id: str) -> list[str]:
        """Documents that directly supersede doc_id."""
        return [s for s, d, r in self.edges if r == REL_SUPERSEDES and d == doc_id]

    def predecessors(self, doc_id: str) -> list[str]:
        """Documents that doc_id directly supersedes."""
        return [d for s, d, r in self.edges if r == REL_SUPERSEDES and s == doc_id]

    def is_superseded(self, doc_id: str) -> bool:
        doc = self.docs.get(doc_id)
        return bool(self.successors(doc_id)) or (doc is not None and doc.status == STATUS_SUPERSEDED)

    def latest(self, doc_id: str) -> str:
        """Follow 'superseded by' links to the newest document (cycle-safe)."""
        current = doc_id
        seen = {current}
        while True:
            nxt = self.successors(current)
            if not nxt:
                return current
            # if two documents claim to supersede it, take the most recently issued
            nxt.sort(key=lambda d: self.docs[d].date_issued if d in self.docs else "")
            current = nxt[-1]
            if current in seen:
                return current
            seen.add(current)

    def chain(self, doc_id: str) -> list[str]:
        """All versions oldest -> newest, e.g. ["PK-2021-03", "PK-2024-01"]."""
        oldest = doc_id
        seen = {oldest}
        while True:
            prev = self.predecessors(oldest)
            prev = [p for p in prev if p not in seen]
            if not prev:
                break
            prev.sort(key=lambda d: self.docs[d].date_issued if d in self.docs else "")
            oldest = prev[0]
            seen.add(oldest)
        result = [oldest]
        current = oldest
        while True:
            nxt = [n for n in self.successors(current) if n not in result]
            if not nxt:
                return result
            nxt.sort(key=lambda d: self.docs[d].date_issued if d in self.docs else "")
            current = nxt[-1]
            result.append(current)

    def edges_for(self, doc_id: str, relations: Iterable[str] | None = None) -> list[tuple[str, str, str]]:
        """Edges touching doc_id (optionally only some relations)."""
        rels = set(relations) if relations is not None else None
        return [e for e in self.edges if doc_id in (e[0], e[1]) and (rels is None or e[2] in rels)]
