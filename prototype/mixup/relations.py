"""Relations between circulars: load the verified ground truth (relations.csv)
and extract new candidates from a document's text (guide 7.3, layers 1-2).

Extracted candidates are always unverified; only an admin approval (verification
queue) lets them change a status.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Iterable

from .config import parse_date
from .models import AMENDS, CANCELS, REFERENCES, RELATION_TYPES, SUPERSEDES, Document, Page, Relation
from .textutil import find_refs, split_sentences

# Guide 7.3 word lists (+ a few English forms used by the English guidelines).
CANCEL_WORDS = [
    "dibatalkan", "membatalkan", "dimansuhkan", "tidak lagi terpakai",
    "digantikan", "menggantikan", "cancelled", "superseded", "revoked", "replaces",
    "supersedes", "cancels", "replaced",
]
AMEND_WORDS = ["dipinda", "pindaan", "meminda", "amended", "amends"]
SUPERSEDE_WORDS = ["digantikan", "menggantikan", "superseded", "supersedes", "replaces", "replaced"]
REFERENCE_WORDS = ["dibaca bersama", "merujuk", "read together", "with reference to", "mengambil kira"]

RELATION_COLUMNS = [
    "relation_id", "source_doc_id", "target_doc_id", "target_ref_text", "relation_type", "scope",
    "effective_date", "evidence_text", "evidence_page", "confidence", "verified", "origin", "rejected",
]

_SCOPE_RE = re.compile(r"(?i)(?:perenggan|para(?:graph)?|klausa|clause)s?\s+(\d+(?:\.\d+)*(?:\s*(?:,|dan|and)\s*\d+(?:\.\d+)*)*)")


# ----------------------------------------------------------------------------
# CSV
# ----------------------------------------------------------------------------


def _bool(value) -> bool:
    return str(value or "").strip().lower() in ("1", "true", "yes", "y")


def _float(value, default: float = 1.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _int(value) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def relation_from_row(row: dict, default_origin: str = "csv") -> Relation:
    """One CSV row -> Relation."""
    rtype = (row.get("relation_type") or REFERENCES).strip().upper()
    return Relation(
        relation_id=(row.get("relation_id") or "").strip(),
        source_doc_id=(row.get("source_doc_id") or "").strip(),
        target_doc_id=(row.get("target_doc_id") or "").strip(),
        target_ref_text=(row.get("target_ref_text") or "").strip(),
        relation_type=rtype if rtype in RELATION_TYPES else REFERENCES,
        scope=(row.get("scope") or "whole").strip(),
        effective_date=parse_date(row.get("effective_date")),
        evidence_text=(row.get("evidence_text") or "").strip(),
        evidence_page=_int(row.get("evidence_page")),
        confidence=_float(row.get("confidence"), 1.0),
        verified=_bool(row.get("verified")),
        origin=(row.get("origin") or default_origin).strip(),
        rejected=_bool(row.get("rejected")),
    )


def load_relations_csv(path: str | Path, default_origin: str = "csv") -> list[Relation]:
    """Read relations.csv (verified=true rows are ground truth). Missing file -> []."""
    path = Path(path)
    if not path.exists():
        return []
    out = []
    with path.open(newline="", encoding="utf-8") as fh:
        for i, row in enumerate(csv.DictReader(fh), start=1):
            if not (row.get("source_doc_id") or "").strip():
                continue
            rel = relation_from_row(row, default_origin)
            rel.relation_id = rel.relation_id or f"{default_origin.upper()}-{i:03d}"
            out.append(rel)
    return out


def save_relations_csv(path: str | Path, relations: Iterable[Relation]) -> None:
    """Write relations to CSV (used for runtime/relations_pending.csv)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=RELATION_COLUMNS)
        writer.writeheader()
        for r in relations:
            writer.writerow(
                {
                    "relation_id": r.relation_id,
                    "source_doc_id": r.source_doc_id,
                    "target_doc_id": r.target_doc_id,
                    "target_ref_text": r.target_ref_text,
                    "relation_type": r.relation_type,
                    "scope": r.scope,
                    "effective_date": r.effective_date.isoformat() if r.effective_date else "",
                    "evidence_text": r.evidence_text,
                    "evidence_page": r.evidence_page if r.evidence_page is not None else "",
                    "confidence": f"{r.confidence:.2f}",
                    "verified": "true" if r.verified else "false",
                    "origin": r.origin,
                    "rejected": "true" if r.rejected else "false",
                }
            )


# ----------------------------------------------------------------------------
# Candidate extraction (regex) and classification
# ----------------------------------------------------------------------------


def _nearest_word(sentence: str, pos: int) -> tuple[str, str] | None:
    """(word, kind) of the cancel/amend/reference word closest to character pos."""
    low = sentence.lower()
    best = None
    for kind, words in (("cancel", CANCEL_WORDS), ("amend", AMEND_WORDS), ("ref", REFERENCE_WORDS)):
        for word in words:
            for m in re.finditer(re.escape(word), low):
                dist = abs(m.start() - pos)
                if best is None or dist < best[0]:
                    best = (dist, word, kind)
    return (best[1], best[2]) if best else None


def classify_regex(sentence: str, ref_pos: int) -> tuple[str, float]:
    """Relation type + confidence for one reference inside a sentence."""
    found = _nearest_word(sentence, ref_pos)
    if found is None:
        return REFERENCES, 0.4
    word, kind = found
    if kind == "amend":
        return AMENDS, 0.8
    if kind == "cancel":
        return (SUPERSEDES, 0.75) if word in SUPERSEDE_WORDS else (CANCELS, 0.85)
    return REFERENCES, 0.6


def scope_of(sentence: str, relation_type: str) -> str:
    """'pindaan kepada perenggan 4.2' -> 'clauses: 4.2'; otherwise 'whole'."""
    if relation_type != AMENDS:
        return "whole"
    m = _SCOPE_RE.search(sentence)
    if not m:
        return "whole"
    clauses = re.split(r"\s*(?:,|dan|and)\s*", m.group(1))
    return "clauses: " + ", ".join(c for c in clauses if c)


def _relation_id(source_id: str, ref: str, rtype: str) -> str:
    digest = hashlib.sha1(f"{source_id}|{ref}|{rtype}".encode("utf-8")).hexdigest()[:8]
    return f"X-{digest}"


def extract_candidates(doc: Document, pages: list[Page], docs_by_circular: dict[str, str] | None = None) -> list[Relation]:
    """Regex candidates: circular references in sentences with cancel/amend words.

    docs_by_circular maps normalised circular numbers ("SPP 1/2023") to doc_ids,
    used to resolve target_doc_id. Results are unverified.
    """
    docs_by_circular = docs_by_circular or {}
    keywords = CANCEL_WORDS + AMEND_WORDS + REFERENCE_WORDS
    out: dict[tuple[str, str], Relation] = {}
    for page in pages:
        for sentence in split_sentences(page.text):
            low = sentence.lower()
            if not any(w in low for w in keywords):
                continue
            for ref in find_refs(sentence):
                if ref["circular_no"] == doc.circular_no:
                    continue  # the document mentioning itself
                rtype, conf = classify_regex(sentence, ref["start"])
                key = (ref["circular_no"], rtype)
                if key in out:
                    continue
                out[key] = Relation(
                    relation_id=_relation_id(doc.doc_id, ref["circular_no"], rtype),
                    source_doc_id=doc.doc_id,
                    target_doc_id=docs_by_circular.get(ref["circular_no"], ""),
                    target_ref_text=ref["raw"],
                    relation_type=rtype,
                    scope=scope_of(sentence, rtype),
                    effective_date=doc.effective_date or doc.issue_date,
                    evidence_text=sentence.strip(),
                    evidence_page=page.page_no,
                    confidence=conf,
                    verified=False,
                    origin="extracted",
                )
    # One candidate per referenced circular: keep the strongest relation type.
    priority = {CANCELS: 3, SUPERSEDES: 3, AMENDS: 2, REFERENCES: 1}
    best: dict[str, Relation] = {}
    for (ref, rtype), rel in out.items():
        if ref not in best or priority[rtype] > priority[best[ref].relation_type]:
            best[ref] = rel
    return list(best.values())


def classify_with_llm(llm, doc: Document, candidates: list[Relation]) -> tuple[list[Relation], str | None]:
    """Refine regex candidates with the RELATION prompt (B4). Returns (relations, warning).

    Offline or on any error the regex classification is kept unchanged.
    """
    if not candidates or llm is None or getattr(llm, "provider", "offline") == "offline":
        return candidates, None
    from . import prompts
    from .llm import LLMError

    payload = [{"ref_text": c.target_ref_text, "sentence": c.evidence_text, "page": c.evidence_page} for c in candidates]
    user = prompts.RELATION.format(circular_no=doc.circular_no, title=doc.title, candidates_json=json.dumps(payload, ensure_ascii=False))
    try:
        data = llm.json(prompts.RELATION_SYSTEM, user, prompts.RELATION_SCHEMA)
    except LLMError as err:
        return candidates, f"LLM relation check skipped: {err}"
    items = data.get("relations") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return candidates, "LLM relation check returned an unexpected shape; regex result kept."
    by_ref = {c.target_ref_text: c for c in candidates}
    for item in items:
        cand = by_ref.get(str(item.get("ref_text", "")))
        rtype = str(item.get("relation", "")).upper()
        if cand is None or rtype not in RELATION_TYPES:
            continue  # UNCLEAR or unknown -> keep the regex guess
        cand.relation_type = rtype
        cand.scope = str(item.get("scope") or cand.scope)
        cand.effective_date = parse_date(item.get("effective_date")) or cand.effective_date
        try:
            cand.confidence = float(item.get("confidence", cand.confidence))
        except (TypeError, ValueError):
            pass
    return candidates, None
