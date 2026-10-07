"""Plain data classes and constants shared by every module.

Dates are datetime.date (or None). Status / relation / jurisdiction values are
the upper-case strings from the build guide (section 6).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

# --- Document status (guide 6.1) ---------------------------------------------
IN_FORCE = "IN_FORCE"
AMENDED = "AMENDED"
CANCELLED = "CANCELLED"
ONE_OFF = "ONE_OFF"
UNKNOWN = "UNKNOWN"
STATUSES = (IN_FORCE, AMENDED, CANCELLED, ONE_OFF, UNKNOWN)
DEFAULT_STATUSES = (IN_FORCE, AMENDED, UNKNOWN)  # what normal search may use
HISTORICAL_STATUSES = (CANCELLED, ONE_OFF)  # only with "Include historical"

# (BM label, EN label, colour). Status is always shown as text + colour.
STATUS_LABELS = {
    IN_FORCE: ("Berkuat kuasa", "In force", "green"),
    AMENDED: ("Dipinda", "Amended", "orange"),
    CANCELLED: ("Dibatalkan", "Cancelled", "red"),
    ONE_OFF: ("Sekali sahaja", "One-off", "gray"),
    UNKNOWN: ("Belum disahkan", "Not verified", "gray"),
}

# --- Relations (guide 6.2) -------------------------------------------------
CANCELS = "CANCELS"
SUPERSEDES = "SUPERSEDES"
AMENDS = "AMENDS"
REFERENCES = "REFERENCES"
RELATION_TYPES = (CANCELS, SUPERSEDES, AMENDS, REFERENCES)
KILLING_RELATIONS = (CANCELS, SUPERSEDES)

# --- Jurisdiction ------------------------------------------------------------
FEDERAL = "FEDERAL"
SARAWAK = "SARAWAK"
FEDERAL_SARAWAK = "FEDERAL_SARAWAK"  # federal circular adopted / published for Sarawak
JURISDICTION_UNKNOWN = "UNKNOWN"
JURISDICTIONS = (FEDERAL, SARAWAK, FEDERAL_SARAWAK, JURISDICTION_UNKNOWN)
JURISDICTION_LABELS = {
    FEDERAL: ("Persekutuan", "Federal"),
    SARAWAK: ("Negeri Sarawak", "Sarawak State"),
    FEDERAL_SARAWAK: ("Persekutuan (diterima pakai Sarawak)", "Federal (adopted by Sarawak)"),
    JURISDICTION_UNKNOWN: ("Tidak diketahui", "Unknown"),
}


def jurisdiction_matches(doc_jurisdiction: str, user_jurisdiction: str) -> bool:
    """True when a document's jurisdiction is the 'home' one for the user."""
    if user_jurisdiction == SARAWAK:
        return doc_jurisdiction in (SARAWAK, FEDERAL_SARAWAK)
    return doc_jurisdiction in (FEDERAL, FEDERAL_SARAWAK)


# --- Classification tiers (guide 7.8) ------------------------------------------
TERBUKA, TERHAD, SULIT = 0, 1, 2
CLASSIFICATION_LABELS = {TERBUKA: ("Terbuka", "Open"), TERHAD: ("Terhad", "Restricted"), SULIT: ("Sulit", "Confidential")}

# --- Other enumerations ------------------------------------------------------------
SERIES = ("PP", "SPP", "SE", "PEKELILING_PERBENDAHARAAN", "STATE", "OTHER")
DOC_TYPES = ("circular", "guideline", "sop", "minutes", "report")
ROLES = ("OFFICER", "POLICY_OWNER", "ADMIN")


@dataclass
class Document:
    """One circular / guideline / SOP / minutes / report (a row of metadata.csv)."""

    doc_id: str
    circular_no: str = ""  # normalised, e.g. "SPP 1/2023"
    series: str = "OTHER"
    title: str = ""
    issuer: str = ""
    doc_type: str = "circular"
    jurisdiction: str = JURISDICTION_UNKNOWN
    cluster: str = ""
    issue_date: date | None = None
    effective_date: date | None = None
    expiry_date: date | None = None
    one_off: bool = False
    classification_level: int = TERBUKA
    language: str = "ms"  # ms | en | mixed
    applicability: str = ""  # from the PEMAKAIAN section
    source_url: str = ""
    file: str = ""  # path relative to data/ (or runtime/ for uploads)
    status: str = UNKNOWN  # computed by status.py
    status_reason: str = ""
    origin: str = "base"  # base | upload
    page_count: int = 0
    ocr_pages: list[int] = field(default_factory=list)  # pages with < 30 chars ("needs OCR")

    @property
    def label(self) -> str:
        """Circular number if known, else the doc_id (for chips and notices)."""
        return self.circular_no or self.doc_id

    @property
    def is_current(self) -> bool:
        return self.status in (IN_FORCE, AMENDED, UNKNOWN)


@dataclass
class Page:
    """A PDF page, or a section of a .md/.txt/.docx file (section number = page number)."""

    doc_id: str
    page_no: int  # 1-based
    text: str
    heading: str = ""
    needs_ocr: bool = False


@dataclass
class Chunk:
    """A clause-aware searchable passage."""

    chunk_id: str  # "<doc_id>#<chunk_index>"
    doc_id: str
    chunk_index: int
    clause_ref: str  # "4.2", or the section name for un-numbered text
    breadcrumb: str  # "SPP 1/2023 > PEMAKAIAN > 4.1"
    section: str  # "PEMAKAIAN" ("" before the first heading)
    page_start: int
    page_end: int
    text: str


@dataclass
class Relation:
    """An edge in the supersession graph: source_doc --relation_type--> target_doc."""

    relation_id: str
    source_doc_id: str
    target_doc_id: str = ""  # "" when the referenced circular is not in the corpus
    target_ref_text: str = ""  # e.g. "Surat Pekeliling Perkhidmatan Bilangan 3 Tahun 2019"
    relation_type: str = REFERENCES
    scope: str = "whole"  # "whole" or "clauses: 4.2"
    effective_date: date | None = None
    evidence_text: str = ""
    evidence_page: int | None = None
    confidence: float = 1.0
    verified: bool = False  # only verified relations change a status
    origin: str = "csv"  # csv | extracted | manual
    rejected: bool = False  # rejected in the verification queue


@dataclass
class User:
    """A demo profile (no passwords; production would use MyGovUC / agency SSO)."""

    user_id: str
    name: str
    role: str = "OFFICER"
    clearance_level: int = TERBUKA
    jurisdiction: str = FEDERAL
    grade: str = ""
    scheme: str = ""


@dataclass
class Hit:
    """A search result: the chunk, its document and scores."""

    chunk: Chunk
    doc: Document
    score: float
    rank: int = 0  # 1-based
    coverage: float = 0.0  # share of the question's keywords found (0..1)
    matched: list[str] = field(default_factory=list)  # query tokens found


@dataclass
class Citation:
    """[S#] label mapped back to circular + clause + page."""

    label: str  # "S1"
    doc_id: str
    circular_no: str
    title: str
    clause_ref: str
    page: int
    status: str
    status_reason: str
    jurisdiction: str
    snippet: str
    chunk_id: str = ""


@dataclass
class AskResponse:
    """What ask.ask() returns to the UI and to the evaluation harness."""

    answer: str
    language: str = "ms"
    confidence: str = "LOW"  # HIGH | MEDIUM | LOW
    citations: list[Citation] = field(default_factory=list)
    primary_status: str = ""
    excluded: list[dict] = field(default_factory=list)  # [{doc_id, circular_no, status_reason}]
    jurisdiction_conflict: bool = False
    comparison: dict | None = None  # the other jurisdiction's rule, if any
    answerable: bool = False
    mode: str = "navigator"  # navigator | baseline
    query_log_id: str = ""
    warnings: list[str] = field(default_factory=list)
    retrieved: list[Hit] = field(default_factory=list)  # ranked passages (for evaluation)
    latency_ms: int = 0
    llm_mode: str = "offline"  # offline | ollama | bedrock (what produced the text)
    extra: dict[str, Any] = field(default_factory=dict)
