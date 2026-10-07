"""FEATURE C - admin: live upload, metadata editor, verification queue (guide 4.3, 7.3,
FR-01..FR-05, US-11).

    analyze_upload(store, filename, data, user=None) -> analysis dict (nothing saved yet)
        {"doc": Document (proposed), "candidates": [Relation (unverified)], "pages": int,
         "warnings": [...], "page_list": [Page], "steps": [...], "meta_sources": {field: source},
         "duplicate_of": doc_id | None, "replaces_upload": bool, "filename", "data", "sha256", ...}
    apply_metadata_edits(store, analysis, edits) -> analysis    (the metadata form, before commit)
    commit_upload(store, analysis, user=None) -> doc_id
        saves the file (runtime/uploads), makes it searchable, queues the candidates in
        runtime/relations_pending.csv. Existing statuses do NOT change yet.
    pending_relations(store, user=None) -> [Relation]            (the verification queue)
    verify_relation(store, relation_id, approve, edits=None, user=None) -> dict
        approve / reject / edit+approve; recomputes statuses and creates alerts.
    ingest_log(store, user=None) -> [dict]                       (newest first)

Only ADMIN and POLICY_OWNER users may commit or verify. Passing user=None means a trusted
caller (tests, scripts); the UI always passes the signed-in demo user. Every list shown to a
user goes through mixup.access.

Order of metadata sources (guide FR-02): regex, then the LLM fills gaps (online modes only),
then data/metadata.csv always wins.
"""

from __future__ import annotations

import csv
import hashlib
from dataclasses import fields
from datetime import datetime
from pathlib import Path

from . import access
from .ingest import SUPPORTED_EXTENSIONS, chunk_document, extract_metadata, full_text, parse_bytes
from .llm import call_json
from .models import RELATION_TYPES, Document, Relation, User
from .relations import classify_with_llm, extract_candidates
from .store import METADATA_COLUMNS, make_document
from .textutil import normalize_circular_no, series_for

ADMIN_ROLES = ("ADMIN", "POLICY_OWNER")
INGEST_LOG = "ingest_log.jsonl"
UPLOAD_METADATA = "metadata_uploads.csv"
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
LLM_METADATA_CHARS = 6000
LLM_METADATA_FIELDS = (
    "circular_no", "series", "title", "issuer", "issue_date", "effective_date",
    "jurisdiction", "applicability", "one_off", "language",
)
EDITABLE_FIELDS = (
    "circular_no", "series", "title", "issuer", "doc_type", "jurisdiction", "cluster", "issue_date",
    "effective_date", "expiry_date", "one_off", "classification_level", "language", "applicability",
    "source_url",
)
RELATION_EDIT_FIELDS = ("relation_type", "target_doc_id", "scope", "effective_date")


class AdminPermissionError(PermissionError):
    """Raised when a non-admin user tries to commit or verify."""


# ----------------------------------------------------------------------------
# Permissions and log
# ----------------------------------------------------------------------------


def can_admin(user: User | None) -> bool:
    """True for ADMIN and POLICY_OWNER demo users."""
    return user is not None and getattr(user, "role", "") in ADMIN_ROLES


def _require_admin(user: User | None, action: str) -> None:
    """user=None is a trusted caller (tests, scripts); otherwise the role must allow it."""
    if user is not None and not can_admin(user):
        raise AdminPermissionError(f"{getattr(user, 'name', 'This user')} may not {action} (admin or policy owner only).")


def _log(store, event: str, user: User | None = None, **detail) -> None:
    """Append one line to runtime/ingest_log.jsonl (append-only)."""
    record = {"time": datetime.now().isoformat(timespec="seconds"), "event": event,
              "user_id": getattr(user, "user_id", None) or "system"}
    record.update({k: v for k, v in detail.items() if v is not None})
    try:
        store.append_jsonl(INGEST_LOG, record)
    except OSError:
        pass  # the log must never break ingestion


def ingest_log(store, user: User | None = None) -> list[dict]:
    """Ingestion log, newest first. Rows about documents the user may not see are hidden."""
    rows = list(reversed(store.read_jsonl(INGEST_LOG)))
    if user is None:
        return rows
    out = []
    for row in rows:
        ids = [row.get("doc_id"), row.get("target_doc_id")]
        if int(row.get("level") or 0) > access.clearance(user):
            continue  # an analysed (not yet saved) document above the user's clearance
        if all(not d or d not in store.docs or access.can_see(user, store.docs[d]) for d in ids):
            out.append(row)
    return out


# ----------------------------------------------------------------------------
# Analysis (nothing is saved)
# ----------------------------------------------------------------------------


def _manual_rows(store) -> list[dict]:
    """Rows of data/metadata.csv (the manual values that always win)."""
    path = Path(store.data_dir) / "metadata.csv"
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        return [row for row in csv.DictReader(fh)]


def _manual_row_for(store, doc_id: str, circular_no: str) -> dict | None:
    """metadata.csv row matching the upload by doc_id or normalised circular number."""
    for row in _manual_rows(store):
        row_no = normalize_circular_no(row.get("circular_no") or "") or (row.get("circular_no") or "").strip()
        if (row.get("doc_id") or "").strip() == doc_id or (circular_no and row_no == circular_no):
            return row
    return None


def _llm_metadata(store, pages, meta: dict, sources: dict) -> tuple[str, str | None]:
    """Fill fields the regex missed with the METADATA prompt (B3). Returns (mode, warning)."""
    if getattr(store.llm, "provider", "offline") == "offline":
        return "regex", None
    from . import prompts

    text = full_text(pages)[:LLM_METADATA_CHARS]
    data, warning = call_json(store.llm, prompts.METADATA_SYSTEM, prompts.METADATA.format(text=text), prompts.METADATA_SCHEMA)
    if not isinstance(data, dict):
        return "regex", warning
    for key in LLM_METADATA_FIELDS:
        value = data.get(key)
        if value is None or (isinstance(value, str) and not value.strip()):
            continue
        weak = key == "jurisdiction" and meta.get(key) in (None, "", "UNKNOWN")
        if key == "circular_no":
            value = normalize_circular_no(str(value)) or ""
            if not value:
                continue
        if key == "one_off":
            if value is True and not meta.get("one_off"):
                meta["one_off"], sources["one_off"] = True, "llm"
            continue
        if not meta.get(key) or weak:
            meta[key], sources[key] = value, "llm"
    if meta.get("circular_no") and not meta.get("series"):
        meta["series"] = series_for(meta["circular_no"])
    return "llm", warning


def _stable_relation_id(source_doc_id: str, rel: Relation) -> str:
    """Same upload -> same ids (idempotent re-upload), independent of the relation type."""
    ref = normalize_circular_no(rel.target_ref_text) or rel.target_ref_text or rel.target_doc_id
    return "X-" + hashlib.sha1(f"{source_doc_id}|{ref}".encode("utf-8")).hexdigest()[:8]


def _extract_relations(store, doc: Document, pages) -> tuple[list[Relation], str, str | None]:
    """Regex candidates, refined by the RELATION prompt (B4) when a model is available."""
    candidates = extract_candidates(doc, pages, store.circular_map())
    for rel in candidates:
        rel.source_doc_id = doc.doc_id
        rel.relation_id = _stable_relation_id(doc.doc_id, rel)
        rel.verified, rel.rejected, rel.origin = False, False, "extracted"
    online = getattr(store.llm, "provider", "offline") != "offline"
    candidates, warning = classify_with_llm(store.llm, doc, candidates)
    mode = "llm" if online and warning is None and candidates else "regex"
    return candidates, mode, warning


def _relation_warnings(store, doc: Document, candidates: list[Relation]) -> list[str]:
    out = []
    for rel in candidates:
        if not rel.target_doc_id:
            out.append(f"{rel.target_ref_text}: not in the library; approving it will not change any status.")
        elif rel.target_doc_id == doc.doc_id:
            out.append(f"{rel.target_ref_text}: points to the uploaded document itself.")
    return out


def analyze_upload(store, filename: str, data: bytes, user: User | None = None) -> dict:
    """Parse -> metadata -> relation candidates for an uploaded file. Nothing is saved.

    Raises ValueError (logged as an ingestion failure) for empty, too large or unsupported files.
    """
    filename = Path(filename or "upload.txt").name
    ext = Path(filename).suffix.lower()
    try:
        if not data:
            raise ValueError("The file is empty.")
        if len(data) > MAX_UPLOAD_BYTES:
            raise ValueError(f"The file is larger than {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.")
        if ext not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file type '{ext or '?'}'. Use PDF, DOCX, MD or TXT.")
        pages = parse_bytes(filename, data, Path(filename).stem)
    except ValueError as exc:
        _log(store, "error", user, filename=filename, detail=str(exc))
        raise
    except Exception as exc:  # broken PDF/DOCX: report, never crash the admin view
        message = f"Cannot read {filename} ({type(exc).__name__})."
        _log(store, "error", user, filename=filename, detail=message)
        raise ValueError(message) from exc

    warnings: list[str] = []
    steps: list[dict] = []
    ocr = [p.page_no for p in pages if p.needs_ocr]
    if not pages or len(ocr) == len(pages):
        warnings.append("No text layer found: the file needs OCR, which is not available offline.")
    elif ocr:
        warnings.append(f"Pages needing OCR (not available offline): {ocr}")
    steps.append({"step": "parse", "ok": bool(pages) and len(ocr) < len(pages),
                  "detail": f"{len(pages)} page(s)/section(s)" + (f", OCR needed: {ocr}" if ocr else "")})

    # Metadata: regex -> LLM (fills gaps) -> metadata.csv (always wins)
    meta = extract_metadata(pages, filename)
    sources = {key: "regex" for key in meta}
    meta_mode, warning = _llm_metadata(store, pages, meta, sources)
    if warning:
        warnings.append(warning)
    circular_no = meta.get("circular_no") or ""
    wanted_id = store.unique_doc_id(circular_no or Path(filename).stem)
    manual = _manual_row_for(store, wanted_id, circular_no)
    if manual:
        for key, value in manual.items():
            if key in EDITABLE_FIELDS and str(value or "").strip():
                sources[key] = "metadata.csv"
    doc = make_document(wanted_id, meta, manual)
    for page in pages:
        page.doc_id = doc.doc_id
    if not doc.circular_no:
        warnings.append("No circular number found; please fill it in before saving.")
    if user is not None and doc.classification_level > access.clearance(user):
        warnings.append("The classification is above your clearance: you will not see this document after saving.")
    steps.append({"step": "metadata", "ok": bool(doc.circular_no),
                  "detail": f"{doc.label} ({meta_mode}" + (", metadata.csv" if manual else "") + ")"})

    # Duplicates: a base document is never replaced; an earlier upload is (idempotent).
    base = store.doc_by_circular(doc.circular_no) if doc.circular_no else None
    duplicate_of = base.doc_id if base is not None and base.origin == "base" else None
    if duplicate_of:
        warnings.append(f"{doc.label} is already in the library ({duplicate_of}); saving will not change it.")
    existing = store.docs.get(doc.doc_id)
    replaces_upload = existing is not None and existing.origin == "upload"

    candidates, rel_mode, warning = _extract_relations(store, doc, pages)
    if warning:
        warnings.append(warning)
    warnings.extend(_relation_warnings(store, doc, candidates))
    steps.append({"step": "relations", "ok": True,
                  "detail": f"{len(candidates)} candidate(s) ({rel_mode})"})

    analysis = {
        "doc": doc, "candidates": candidates, "pages": len(pages), "warnings": warnings, "page_list": pages,
        "filename": filename, "data": data, "sha256": hashlib.sha256(data).hexdigest(), "steps": steps,
        "meta_sources": sources, "metadata_mode": meta_mode, "relation_mode": rel_mode,
        "chunks": len(chunk_document(doc, pages)), "duplicate_of": duplicate_of, "replaces_upload": replaces_upload,
    }
    _log(store, "analyze", user, filename=filename, doc_id=doc.doc_id, level=doc.classification_level,
         detail=f"{doc.label}: {len(pages)} page(s), {len(candidates)} relation candidate(s)")
    return analysis


def apply_metadata_edits(store, analysis: dict, edits: dict) -> dict:
    """Apply the metadata form to the proposed document (before commit). Edited values win.

    A new circular number gives a new doc_id and re-runs relation extraction.
    """
    old: Document = analysis["doc"]
    current = {f.name: getattr(old, f.name) for f in fields(Document) if f.name in EDITABLE_FIELDS}
    clean = {k: v for k, v in (edits or {}).items() if k in EDITABLE_FIELDS}
    doc = make_document(old.doc_id, {**current, **clean})  # an emptied field falls back to its default
    if doc.circular_no != old.circular_no:
        doc.doc_id = store.unique_doc_id(doc.circular_no or old.doc_id)
        if doc.circular_no and not clean.get("series"):
            doc.series = series_for(doc.circular_no)
        for page in analysis["page_list"]:
            page.doc_id = doc.doc_id
        candidates, mode, _ = _extract_relations(store, doc, analysis["page_list"])
        analysis["candidates"], analysis["relation_mode"] = candidates, mode
        base = store.doc_by_circular(doc.circular_no) if doc.circular_no else None
        analysis["duplicate_of"] = base.doc_id if base is not None and base.origin == "base" else None
        existing = store.docs.get(doc.doc_id)
        analysis["replaces_upload"] = existing is not None and existing.origin == "upload"
    for rel in analysis["candidates"]:
        rel.source_doc_id = doc.doc_id
        rel.effective_date = doc.effective_date or doc.issue_date
    for key in clean:
        if getattr(doc, key) != getattr(old, key, None):
            analysis["meta_sources"][key] = "manual"
    analysis["doc"] = doc
    analysis["chunks"] = len(chunk_document(doc, analysis["page_list"]))
    return analysis


# ----------------------------------------------------------------------------
# Commit
# ----------------------------------------------------------------------------


def _save_upload_metadata(store, doc: Document) -> None:
    """Keep runtime/metadata_uploads.csv (same columns as metadata.csv) in step with uploads."""
    path = store.runtime_path(UPLOAD_METADATA)
    rows: list[dict] = []
    if path.exists():
        with path.open(newline="", encoding="utf-8") as fh:
            rows = [r for r in csv.DictReader(fh) if r.get("doc_id") != doc.doc_id]
    row = {}
    for col in METADATA_COLUMNS:
        value = getattr(doc, col, "")
        if hasattr(value, "isoformat"):
            value = value.isoformat()
        elif isinstance(value, bool):
            value = "true" if value else "false"
        row[col] = "" if value is None else value
    rows.append(row)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=METADATA_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def commit_upload(store, analysis: dict, user: User | None = None) -> str:
    """Save the document (searchable at once) and queue its candidates as UNVERIFIED.

    No existing status changes here: only verify_relation() can do that. Re-uploading the same
    file is idempotent (same doc_id and relation ids; earlier approvals/rejections are kept).
    """
    _require_admin(user, "upload circulars")
    doc: Document = analysis["doc"]
    if analysis.get("duplicate_of"):
        _log(store, "duplicate", user, doc_id=analysis["duplicate_of"], filename=analysis.get("filename"),
             detail=f"{doc.label} already in the library; nothing changed")
        return analysis["duplicate_of"]

    doc_id = store.add_document(doc, analysis["page_list"], analysis.get("data"), analysis.get("filename"))
    queued, kept = [], 0
    for rel in analysis.get("candidates", []):
        rel.source_doc_id = doc_id
        rel.relation_id = _stable_relation_id(doc_id, rel)
        previous = store.get_relation(rel.relation_id)
        if previous is not None and (previous.verified or previous.rejected):
            kept += 1  # keep the admin's earlier decision
            continue
        rel.verified, rel.rejected = False, False
        queued.append(rel)
    if queued:
        store.add_relations(queued)
    store.recompute()
    _save_upload_metadata(store, store.docs[doc_id])
    detail = f"{doc.label} saved ({analysis.get('pages', 0)} page(s)); {len(queued)} relation(s) queued"
    if kept:
        detail += f", {kept} earlier decision(s) kept"
    _log(store, "commit", user, doc_id=doc_id, filename=analysis.get("filename"), detail=detail)
    return doc_id


# ----------------------------------------------------------------------------
# Verification queue
# ----------------------------------------------------------------------------


def pending_relations(store, user: User | None = None) -> list[Relation]:
    """Unverified, not rejected relations; filtered by the user's clearance when given."""
    rels = store.pending_relations()
    if user is not None:
        rels = access.filter_relations(store, user, rels)
    return sorted(rels, key=lambda r: (r.source_doc_id, -r.confidence, r.target_ref_text))


def recent_decisions(store, user: User | None = None, limit: int = 20) -> list[dict]:
    """Latest approve/reject entries from the ingestion log (for the admin view)."""
    rows = [r for r in ingest_log(store, user) if r.get("event") in ("approve", "reject")]
    return rows[:limit]


def _clean_relation_edits(store, edits: dict | None) -> dict:
    """Validate the edit form: known relation type, existing target, ISO date."""
    out = {}
    for key, value in (edits or {}).items():
        if key not in RELATION_EDIT_FIELDS or value is None:
            continue
        if key == "relation_type":
            value = str(value).upper()
            if value not in RELATION_TYPES:
                raise ValueError(f"Unknown relation type '{value}'.")
        if key == "target_doc_id" and value and value not in store.docs:
            raise ValueError(f"Unknown target document '{value}'.")
        if key == "scope":
            value = str(value).strip() or "whole"
        out[key] = value
    return out


def describe_change(store, doc_id: str, old: tuple[str, str], new: tuple[str, str]) -> dict:
    """One status change, e.g. SPP 1/2023: AMENDED (Dipinda oleh ...) -> CANCELLED (Dibatalkan oleh SPP 1/2026)."""
    doc = store.docs.get(doc_id)
    return {"doc_id": doc_id, "circular_no": doc.label if doc else doc_id,
            "old_status": old[0], "old_reason": old[1], "new_status": new[0], "new_reason": new[1]}


def verify_relation(store, relation_id: str, approve: bool, edits: dict | None = None, user: User | None = None) -> dict:
    """Approve (verified) or reject a candidate, optionally after edits; then recompute
    statuses and create alerts. Returns {"relation", "status_changes", "notifications", "warnings"}.

    Raises AdminPermissionError for non-admin users (or relations they may not see),
    KeyError for an unknown relation and ValueError for invalid edits.
    """
    _require_admin(user, "verify relations")
    rel = store.get_relation(relation_id)
    if rel is None:
        raise KeyError(f"Unknown relation {relation_id}")
    if user is not None and not access.filter_relations(store, user, [rel]):
        raise AdminPermissionError("This relation involves a document above your clearance.")
    changes = _clean_relation_edits(store, edits)
    edited = sorted(changes)
    before = {d.doc_id: (d.status, d.status_reason) for d in store.docs.values()}
    changes.update({"verified": True, "rejected": False} if approve else {"verified": False, "rejected": True})
    rel = store.update_relation(relation_id, **changes)
    store.recompute()
    status_changes = [
        describe_change(store, d.doc_id, before.get(d.doc_id, ("", "")), (d.status, d.status_reason))
        for d in store.docs.values()
        if before.get(d.doc_id) != (d.status, d.status_reason)
    ]

    notes, warnings = [], []
    source, target = store.docs.get(rel.source_doc_id), store.docs.get(rel.target_doc_id)
    if approve and source and target and source.classification_level > target.classification_level \
            and rel.relation_type != "REFERENCES":
        warnings.append(f"{target.label}'s status reason now names a more restricted document ({source.label}).")
    if approve:
        try:
            from . import alerts  # lazy: Feature B may still be a stub

            notes = alerts.on_new_relations(store, [rel]) or []
        except Exception as exc:  # alerts must never block a verification
            warnings.append(f"Alerts not sent ({type(exc).__name__}).")
    _log(store, "approve" if approve else "reject", user, doc_id=rel.source_doc_id,
         target_doc_id=rel.target_doc_id or None, relation_id=rel.relation_id,
         detail=f"{source.label if source else rel.source_doc_id} {rel.relation_type} "
                f"{target.label if target else rel.target_ref_text}"
                + (f" (edited: {', '.join(edited)})" if edited else "")
                + (f"; {len(status_changes)} status change(s)" if status_changes else ""))
    return {"relation": rel, "status_changes": status_changes, "notifications": notes, "warnings": warnings}


def approve_all(store, source_doc_id: str, user: User | None = None) -> dict:
    """Approve every pending candidate of one uploaded document (demo shortcut)."""
    _require_admin(user, "verify relations")
    total = {"status_changes": [], "notifications": [], "warnings": [], "approved": 0}
    for rel in pending_relations(store, user):
        if rel.source_doc_id != source_doc_id:
            continue
        result = verify_relation(store, rel.relation_id, True, None, user)
        total["status_changes"].extend(result["status_changes"])
        total["notifications"].extend(result["notifications"])
        total["warnings"].extend(result["warnings"])
        total["approved"] += 1
    return total
