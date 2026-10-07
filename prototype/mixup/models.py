"""Plain data classes shared by every MixUp module."""

from __future__ import annotations

from dataclasses import dataclass, field

# Document status values
STATUS_IN_FORCE = "in_force"  # current rule; answers should come from these
STATUS_SUPERSEDED = "superseded"  # replaced by a newer document
STATUS_RECORD = "record"  # minutes, reports: records, not rules
STATUSES = (STATUS_IN_FORCE, STATUS_SUPERSEDED, STATUS_RECORD)

# Document types (doc_type values)
DOC_TYPES = ("circular", "guideline", "sop", "policy", "minutes", "report", "other")

# Edge relations in the version graph
REL_SUPERSEDES = "supersedes"  # (new, old): new replaces old
REL_REFERENCES = "references"  # (a, b): a mentions b
REL_CONFLICTS = "conflicts"  # (a, b): both in force but disagree
REL_DISCUSSED_IN = "discussed_in"  # (doc, minutes): doc was discussed in the minutes
RELATIONS = (REL_SUPERSEDES, REL_REFERENCES, REL_CONFLICTS, REL_DISCUSSED_IN)


@dataclass
class DocMeta:
    """One row of data/manifest.csv: what we know about a document."""

    doc_id: str  # short stable id, e.g. "PK-2024-01"
    title: str
    doc_type: str = "other"  # one of DOC_TYPES
    issuer: str = ""
    number: str = ""  # official number, e.g. "Bil. 1/2024"
    date_issued: str = ""  # ISO date "YYYY-MM-DD"
    language: str = "en"  # "ms" | "en" | "mixed"
    status: str = STATUS_IN_FORCE  # one of STATUSES
    supersedes: list[str] = field(default_factory=list)  # doc_ids this one replaces
    superseded_by: str = ""  # doc_id that replaced this one ("" if none)
    file: str = ""  # path relative to data/, e.g. "documents/PK-2024-01.md"
    source_url: str = ""  # empty for fictional sample documents
    summary: str = ""
    tags: list[str] = field(default_factory=list)  # topic tags, e.g. ["travel-claims"]

    @property
    def is_superseded(self) -> bool:
        return self.status == STATUS_SUPERSEDED

    @property
    def short_label(self) -> str:
        """Number if we have one, otherwise the doc_id. Good for chips and notices."""
        return self.number or self.doc_id


@dataclass
class Page:
    """A page (PDF) or section (Markdown/TXT/DOCX) of a document."""

    doc_id: str
    page_no: int  # 1-based page number, or section number for text files
    text: str
    heading: str = ""


@dataclass
class Chunk:
    """A searchable piece of a page (about 900 characters)."""

    chunk_id: str  # "<doc_id>#p<page_no>-c<i>"
    doc_id: str
    page_no: int
    heading: str
    text: str


@dataclass
class SearchHit:
    """A search result: the chunk, its score and the document it came from."""

    chunk: Chunk
    score: float
    doc: DocMeta


@dataclass
class Citation:
    """A source label like [S1] mapped back to a document location."""

    label: str  # "S1"
    doc_id: str
    title: str
    number: str
    page_no: int
    heading: str
    snippet: str
    status: str


@dataclass
class Answer:
    """What Ask MixUp returns to the UI."""

    text: str  # answer text containing [S1]-style labels
    citations: list[Citation] = field(default_factory=list)
    language: str = "en"  # language of the question: "ms" | "en" | "mixed"
    confidence: str = "low"  # "high" | "medium" | "low" | "none"
    notices: list[str] = field(default_factory=list)  # e.g. supersession notices
    mode: str = "offline"  # "ai" | "offline"
    hits: list[SearchHit] = field(default_factory=list)  # retrieved passages
    # superseded->latest pairs relevant to this answer, for "What changed?" buttons:
    # [{"old_id": "PK-2021-03", "new_id": "PK-2024-01"}, ...]
    related_versions: list[dict] = field(default_factory=list)
