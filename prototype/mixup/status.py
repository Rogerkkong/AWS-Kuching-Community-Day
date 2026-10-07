"""Validity engine: compute each document's status from verified relations
and dates, exactly as in guide 7.3.

Order of the rules:
  1. verified CANCELS/SUPERSEDES whose effective date <= today -> CANCELLED "Dibatalkan oleh <no>"
  2. one_off                                                   -> ONE_OFF   "Arahan sekali sahaja"
  3. expiry_date <= today                                      -> CANCELLED "Tamat tempoh"
  4. verified AMENDS                                           -> AMENDED   "Dipinda oleh <list>"
  5. effective_date <= today                                   -> IN_FORCE
  6. otherwise                                                 -> UNKNOWN   "Status belum disahkan"
"""

from __future__ import annotations

from datetime import date
from typing import Iterable

from .models import AMENDED, AMENDS, CANCELLED, IN_FORCE, KILLING_RELATIONS, ONE_OFF, UNKNOWN, Document, Relation

REASON_ONE_OFF = "Arahan sekali sahaja"
REASON_EXPIRED = "Tamat tempoh"
REASON_UNKNOWN = "Status belum disahkan"


def relation_effective_date(rel: Relation, docs: dict[str, Document]) -> date | None:
    """The relation's date, else the source's effective date, else its issue date."""
    if rel.effective_date:
        return rel.effective_date
    source = docs.get(rel.source_doc_id)
    if source is None:
        return None
    return source.effective_date or source.issue_date


def _label(doc_id: str, docs: dict[str, Document]) -> str:
    doc = docs.get(doc_id)
    return doc.label if doc else doc_id


def compute_status(doc: Document, incoming: Iterable[Relation], docs: dict[str, Document], today: date) -> tuple[str, str]:
    """(status, reason) for one document. `incoming` = relations whose target is doc."""
    incoming = [r for r in incoming if r.verified and not r.rejected and r.target_doc_id == doc.doc_id]

    killers = []
    for rel in incoming:
        if rel.relation_type in KILLING_RELATIONS:
            eff = relation_effective_date(rel, docs)
            if eff is None or eff <= today:  # a verified relation with no date counts as effective
                killers.append((eff or date.min, rel))
    if killers:
        killers.sort(key=lambda pair: pair[0])
        return CANCELLED, "Dibatalkan oleh " + _label(killers[0][1].source_doc_id, docs)

    if doc.one_off:
        return ONE_OFF, REASON_ONE_OFF

    if doc.expiry_date and doc.expiry_date <= today:
        return CANCELLED, REASON_EXPIRED

    amenders = [r for r in incoming if r.relation_type == AMENDS]
    if amenders:
        names = list(dict.fromkeys(_label(r.source_doc_id, docs) for r in amenders))
        return AMENDED, "Dipinda oleh " + ", ".join(names)

    if doc.effective_date and doc.effective_date <= today:
        return IN_FORCE, ""

    return UNKNOWN, REASON_UNKNOWN


def recompute_all(docs: dict[str, Document], relations: Iterable[Relation], today: date) -> dict[str, tuple[str, str]]:
    """Recompute every status in place. Returns {doc_id: (old_status, new_status)} for changes."""
    by_target: dict[str, list[Relation]] = {}
    for rel in relations:
        if rel.target_doc_id:
            by_target.setdefault(rel.target_doc_id, []).append(rel)
    changes = {}
    for doc in docs.values():
        old = doc.status
        doc.status, doc.status_reason = compute_status(doc, by_target.get(doc.doc_id, []), docs, today)
        if doc.status != old:
            changes[doc.doc_id] = (old, doc.status)
    return changes
