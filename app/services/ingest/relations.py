"""Relation extraction between rules: regex candidates -> RELATION prompt -> unverified rows.
data/relations.csv is loaded as verified ground truth."""
from __future__ import annotations

import csv
import json
import re
import sqlite3
from pathlib import Path

from app.services.generation import prompts
from app.services.ingest.parse import Page

# The brief's reference regex, with the series wrapped in a capture group.
REF_RE = re.compile(
    r"((?:surat\s+)?pekeliling\s+(?:perkhidmatan|perbendaharaan)|\b(?:spp|pp|se)\b)\s*(?:bilangan|bil\.?)\s*"
    r"(\d{1,3})\s*(?:tahun|/)\s*((?:19|20)\d{2})",
    re.I,
)
# Extension (DECISIONS.md): Sarawak state circulars, "Pekeliling Am Sarawak Bilangan 4 Tahun 2023".
SARAWAK_REF_RE = re.compile(r"(pekeliling\s+am\s+sarawak|\bpas\b)\s*(?:bilangan|bil\.?)\s*(\d{1,3})\s*(?:tahun|/)\s*((?:19|20)\d{2})", re.I)
# Looser form used on user questions ("PP 3/2018", "SPP 5/2011", "PAS 4/2023").
QUERY_REF_RE = re.compile(r"\b(spp|pp|pas|se|pb|gp)\s*(?:bil(?:angan)?\.?\s*)?(\d{1,3})\s*(?:/|tahun)\s*((?:19|20)\d{2})\b", re.I)

TRIGGERS = ("dibatalkan", "membatalkan", "dimansuhkan", "tidak lagi terpakai", "digantikan", "menggantikan",
            "dipinda", "pindaan", "cancelled", "superseded", "revoked", "replaces", "amends")
RELATION_TYPES = {"CANCELS", "SUPERSEDES", "AMENDS", "REFERENCES"}
SENTENCE_RE = re.compile(r"(?<=[.;:])\s+(?=[A-Z0-9(])")


def normalize_series(series_text: str) -> str:
    s = re.sub(r"\s+", " ", series_text.strip().lower())
    if s.startswith("surat pekeliling perkhidmatan") or s == "spp":
        return "SPP"
    if s.startswith("pekeliling perkhidmatan") or s == "pp":
        return "PP"
    if s.startswith("pekeliling perbendaharaan") or s == "pb":
        return "PB"
    if s.startswith("pekeliling am sarawak") or s == "pas":
        return "PAS"
    return s.upper()


def normalize_ref(series_text: str, number: str, year: str) -> str:
    return f"{normalize_series(series_text)} {int(number)}/{year}"


def find_refs(text: str) -> list[tuple[str, str]]:
    """All (normalised ref, matched text) in a passage of document text."""
    out = []
    for regex in (REF_RE, SARAWAK_REF_RE):
        for m in regex.finditer(text):
            out.append((normalize_ref(m.group(1), m.group(2), m.group(3)), m.group(0)))
    return out


def refs_in_query(text: str) -> list[str]:
    refs = [normalize_ref(m.group(1), m.group(2), m.group(3)) for m in QUERY_REF_RE.finditer(text)]
    refs += [r for r, _ in find_refs(text)]
    return list(dict.fromkeys(refs))


HEADING_LINE_RE = re.compile(r"^(\d{1,2}(?:\.\d{1,2})*\.?\s+)?[A-Z][A-Z0-9 ,'()/&\-]{2,}:?$")
CLAUSE_PREFIX_RE = re.compile(r"^(\d{1,2}(?:\.\d{1,2})*\.?|\(\w{1,3}\))\s+")


def _sentences(pages: list[Page]):
    """Sentences per page; headings and clause numbers are boundaries, not part of the evidence text."""
    for page in pages:
        blocks, current = [], []
        for line in page.text.split("\n"):
            line = line.strip()
            if not line:
                continue
            if HEADING_LINE_RE.match(line) or CLAUSE_PREFIX_RE.match(line):
                if current:
                    blocks.append(" ".join(current))
                current = []
                if HEADING_LINE_RE.match(line):
                    continue
                line = CLAUSE_PREFIX_RE.sub("", line)
            current.append(line)
        if current:
            blocks.append(" ".join(current))
        for block in blocks:
            for sentence in SENTENCE_RE.split(block):
                if sentence.strip():
                    yield page.number, sentence.strip()


def find_candidates(pages: list[Page], own_no: str) -> list[dict]:
    seen, out = set(), []
    for page_no, sentence in _sentences(pages):
        low = sentence.lower()
        if not any(t in low for t in TRIGGERS):
            continue
        for ref, matched in find_refs(sentence):
            if ref == own_no or (ref, sentence) in seen:
                continue
            seen.add((ref, sentence))
            out.append({"ref_text": ref, "matched": matched, "sentence": sentence, "page": page_no})
    return out


def classify(candidates: list[dict], meta: dict, client) -> list[dict]:
    """RELATION prompt; falls back to keyword rules if the model fails."""
    from app.services.inference.client import parse_json_loose

    if not candidates:
        return []
    payload = [{"ref_text": c["ref_text"], "sentence": c["sentence"], "page": c["page"]} for c in candidates]
    results: list[dict] = []
    if client is not None:
        try:
            reply = client.chat([{"role": "user", "content": prompts.RELATION.format(
                circular_no=meta["circular_no"], title=meta.get("title", ""),
                candidates_json=json.dumps(payload, ensure_ascii=False))}], json_mode=True, max_tokens=800, timeout=240)
            data = parse_json_loose(reply)
            if isinstance(data, dict):  # some models wrap the list
                data = next((v for v in data.values() if isinstance(v, list)), [data])
            results = [d for d in data if isinstance(d, dict)]
        except Exception:  # noqa: BLE001
            results = []
    by_ref = {r.get("ref_text"): r for r in results}
    out = []
    for c in candidates:
        r = by_ref.get(c["ref_text"]) or _keyword_relation(c)
        rel = str(r.get("relation", "")).upper()
        if rel not in RELATION_TYPES:
            rel = _keyword_relation(c)["relation"]
        try:
            conf = float(r.get("confidence", 0.5))
        except (TypeError, ValueError):
            conf = 0.5
        eff = r.get("effective_date") if isinstance(r.get("effective_date"), str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", r.get("effective_date") or "") else None
        out.append({"ref_text": c["ref_text"], "relation": rel, "scope": r.get("scope") or "whole",
                    "effective_date": eff, "evidence": c["sentence"], "page": c["page"], "confidence": conf})
    return out


def _keyword_relation(c: dict) -> dict:
    s = c["sentence"].lower()
    if any(k in s for k in ("digantikan", "menggantikan", "superseded", "replaces")):
        rel = "SUPERSEDES"
    elif any(k in s for k in ("dibatalkan", "membatalkan", "dimansuhkan", "tidak lagi terpakai", "cancelled", "revoked")):
        rel = "CANCELS"
    elif any(k in s for k in ("dipinda", "pindaan", "amends")):
        rel = "AMENDS"
    else:
        rel = "REFERENCES"
    return {"relation": rel, "confidence": 0.5}


def store_extracted(conn: sqlite3.Connection, source_doc_id: int, relations: list[dict]) -> int:
    """Insert unverified relations (skipping exact duplicates); targets resolved by normalised number."""
    added = 0
    for r in relations:
        target = conn.execute("SELECT id FROM documents WHERE circular_no = ?", (r["ref_text"],)).fetchone()
        exists = conn.execute(
            "SELECT 1 FROM relations WHERE source_doc_id = ? AND target_ref_text = ? AND relation_type = ?",
            (source_doc_id, r["ref_text"], r["relation"])).fetchone()
        if exists:
            continue
        conn.execute(
            """INSERT INTO relations (source_doc_id, target_doc_id, target_ref_text, relation_type, scope,
               effective_date, evidence_text, evidence_page, confidence, verified)
               VALUES (?,?,?,?,?,?,?,?,?,0)""",
            (source_doc_id, target[0] if target else None, r["ref_text"], r["relation"], r.get("scope"),
             r.get("effective_date"), r.get("evidence"), r.get("page"), r.get("confidence")))
        added += 1
    return added


def resolve_targets(conn: sqlite3.Connection) -> None:
    """Link relations whose target arrived later (e.g. the cancelled circular was ingested afterwards)."""
    conn.execute("""UPDATE relations SET target_doc_id =
                    (SELECT id FROM documents WHERE documents.circular_no = relations.target_ref_text)
                    WHERE target_doc_id IS NULL""")


def load_ground_truth(conn: sqlite3.Connection, csv_path: Path) -> int:
    """data/relations.csv rows become verified relations (merging with extracted duplicates)."""
    if not csv_path.exists():
        return 0
    count = 0
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            src = conn.execute("SELECT id FROM documents WHERE circular_no = ?", (row["source_circular_no"].strip(),)).fetchone()
            if not src:
                continue
            ref = row["target_circular_no"].strip()
            rel = row["relation_type"].strip().upper()
            tgt = conn.execute("SELECT id FROM documents WHERE circular_no = ?", (ref,)).fetchone()
            existing = conn.execute(
                "SELECT id FROM relations WHERE source_doc_id = ? AND target_ref_text = ?", (src[0], ref)).fetchall()
            values = (tgt[0] if tgt else None, rel, row.get("scope") or "whole", row.get("effective_date") or None,
                      row.get("evidence_text") or None, int(row["evidence_page"]) if row.get("evidence_page") else None)
            if existing:
                keep = existing[0][0]
                conn.execute("""UPDATE relations SET target_doc_id=?, relation_type=?, scope=?, effective_date=?,
                                evidence_text=COALESCE(?, evidence_text), evidence_page=COALESCE(?, evidence_page),
                                confidence=1.0, verified=1 WHERE id=?""", (*values, keep))
                conn.executemany("DELETE FROM relations WHERE id = ?", [(e[0],) for e in existing[1:]])
            else:
                conn.execute("""INSERT INTO relations (source_doc_id, target_doc_id, target_ref_text, relation_type,
                                scope, effective_date, evidence_text, evidence_page, confidence, verified)
                                VALUES (?,?,?,?,?,?,?,?,1.0,1)""", (src[0], values[0], ref, *values[1:]))
            count += 1
    return count
