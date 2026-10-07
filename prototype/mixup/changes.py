"""FEATURE B - "what changed" between two versions of a rule (guide 7.7, FR-12).

    what_changed(store, user, old_id, new_id) -> {
        "aligned": [{"clause_old", "clause_new", "type", "old_text", "new_text", "diff_html",
                     "old_html", "new_html", "section", "similarity", "quantities"}],
        "summary_ms", "summary_en", "effective_date" (ISO str | None), "who_is_affected",
        "mode" ("offline" | provider), "warnings", "old_label", "new_label", "relation_type",
        "scope", "counts", "highlights"}

type is ADDED | REMOVED | CHANGED | SAME.

Alignment: by clause number (when the heading or text agrees), otherwise by difflib word
similarity >= 0.80 (the guide's threshold), then by heading + similarity >= 0.5. Unmatched
clauses are ADDED / REMOVED. A clause-scoped AMENDS relation ("clauses: 4.2") is handled
specially: each amended clause of the old circular is matched to the most similar clause of
the amending circular and every other clause stays in force (SAME).

Summaries: the CHANGE_SUMMARY prompt when an LLM is on (numbers are checked against the
diff), else a deterministic BM + EN template that lists changed amounts, durations and
percentages ("Tempoh tuntutan berubah daripada 30 hari kepada 60 hari").
Results are cached in runtime/change_cache.json. Both documents must be visible to the user.
Document text is untrusted: every HTML fragment is escaped here.
"""

from __future__ import annotations

import difflib
import hashlib
import html
import json
import re
from datetime import date

from . import access
from .llm import call_json
from .models import AMENDS, CANCELS, REFERENCES, SUPERSEDES
from .prompts import CHANGE_SUMMARY, CHANGE_SUMMARY_SCHEMA, CHANGE_SUMMARY_SYSTEM

CACHE = "change_cache.json"
CACHE_MAX = 200
SIM_THRESHOLD = 0.80  # guide 7.7
SECTION_SIM = 0.50  # same heading, reworded clause
NUMBER_SIM = 0.30  # same clause number under the same heading
NUMBER_OTHER_SIM = 0.50  # same clause number under a different heading
NEAR_SIM = 0.65  # leftover clauses that moved to another heading
QUANTITY_SIM = 0.35  # leftover clauses that share a kind of number (days, RM, %)
MAX_SUMMARY_WORDS = 120

ADDED, REMOVED, CHANGED, SAME = "ADDED", "REMOVED", "CHANGED", "SAME"
TYPE_LABELS = {
    ADDED: ("Ditambah", "Added", "green"),
    REMOVED: ("Dibuang", "Removed", "red"),
    CHANGED: ("Dipinda", "Changed", "orange"),
    SAME: ("Tiada perubahan", "Unchanged", "gray"),
}
# Sections that are boilerplate for a summary (still shown in the table).
BOILERPLATE = {
    "TUJUAN", "LATAR BELAKANG", "TARIKH KUAT KUASA", "PEMBATALAN", "PINDAAN", "PURPOSE", "BACKGROUND",
    "EFFECTIVE DATE", "SUPERSESSION", "CANCELLATION", "AMENDMENT",
}
APPLICABILITY_SECTIONS = ("PEMAKAIAN", "SCOPE", "APPLICATION", "APPLICABILITY")
NOT_STATED = "Tidak dinyatakan / Not stated"
NOT_AVAILABLE = (
    "Dokumen tidak tersedia untuk tahap akses anda. / Document not available at your clearance."
)
VERBS = {
    CANCELS: ("membatalkan", "cancels"),
    SUPERSEDES: ("menggantikan", "supersedes"),
    AMENDS: ("meminda", "amends"),
    REFERENCES: ("merujuk", "references"),
}
MONTHS_MS = ["Januari", "Februari", "Mac", "April", "Mei", "Jun", "Julai", "Ogos", "September", "Oktober",
             "November", "Disember"]
MONTHS_EN = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
             "November", "December"]
# Glossary words too generic to name the topic of a clause.
GENERIC_TERMS = {
    "kadar", "rate", "tempoh", "period", "deadline", "pegawai", "officer", "sistem", "system", "pekeliling",
    "circular", "surat pekeliling", "circular letter", "perkhidmatan awam", "public service", "persekutuan",
    "federal", "hari", "days", "hari bekerja", "working days", "tahun", "year", "bulan", "month", "minggu", "week",
    "seminggu", "per week", "sekilometer", "per km", "per kilometre", "kenderaan", "vehicle", "kenderaan sendiri",
    "own vehicle", "dikemukakan", "submitted", "mengemukakan", "submit", "ketua jabatan", "head of department",
    "penyelia", "supervisor", "diluluskan", "approved", "berkuat kuasa", "in force", "dipinda", "amended",
    "dibatalkan", "cancelled", "penjawat awam", "civil servant", "garis panduan", "guideline",
}

# ---------------------------------------------------------------------------- text helpers

_WATERMARK = re.compile(r"SINTETIK\s*-\s*CONTOH SAHAJA|SYNTHETIC\s*-\s*SAMPLE ONLY", re.I)
_WORD = re.compile(r"rm\d+(?:[.,]\d+)?|\d+(?:[.,/]\d+)*|[^\W_]+(?:-[^\W_]+)*", re.I)


_CLAUSE_START = re.compile(r"^(?:(\d{1,2}(?:\.\d{1,2})+)\.?|(\d{1,2})\.)\s+")


def _lines(text: str) -> list[str]:
    """Non-empty lines without the watermark or separators."""
    lines = [ln.strip() for ln in (text or "").splitlines()]
    return [ln for ln in lines if ln and ln != "---" and not _WATERMARK.search(ln)]


def _words(text: str) -> list[str]:
    return _WORD.findall((text or "").lower())


def similarity(a: str, b: str) -> float:
    """difflib word-level similarity (0..1)."""
    wa, wb = _words(a), _words(b)
    if not wa and not wb:
        return 1.0
    return difflib.SequenceMatcher(None, wa, wb, autojunk=False).ratio()


def _norm(text: str) -> str:
    return " ".join(_words(text))


def _excerpt(text: str, n_words: int = 14) -> str:
    words = (text or "").split()
    return " ".join(words[:n_words]) + (" ..." if len(words) > n_words else "")


def word_diff(old: str, new: str) -> tuple[str, str, str]:
    """(inline_html, old_html, new_html): word-level diff, HTML-escaped.

    Deletions are <del> (struck through, red), insertions <ins> (underlined, green),
    so the change is visible without relying on colour alone.
    """
    a, b = (old or "").split(), (new or "").split()
    inline, left, right = [], [], []
    esc = lambda words: html.escape(" ".join(words))  # noqa: E731
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == "equal":
            text = esc(a[i1:i2])
            inline.append(text)
            left.append(text)
            right.append(text)
            continue
        if i2 > i1:
            d = f'<del class="pn-del">{esc(a[i1:i2])}</del>'
            inline.append(d)
            left.append(d)
        if j2 > j1:
            ins = f'<ins class="pn-ins">{esc(b[j1:j2])}</ins>'
            inline.append(ins)
            right.append(ins)
    return " ".join(inline), " ".join(left), " ".join(right)


def format_date(value, lang: str = "ms") -> str:
    """date -> '1 Julai 2025' / '1 July 2025'."""
    if not isinstance(value, date):
        return str(value or "")
    months = MONTHS_EN if lang == "en" else MONTHS_MS
    return f"{value.day} {months[value.month - 1]} {value.year}"


# ---------------------------------------------------------------------------- quantities

_AMOUNT = re.compile(
    r"RM\s?(\d[\d,]*(?:\.\d+)?)(\s*(?:sekilometer|per\s?km|/km|per\s+kilomet(?:re|er)))?", re.I
)
_DURATION = re.compile(
    r"(?<![\d./])(\d+)\s*(hari bekerja|working days?|hari|days?|minggu|weeks?|bulan|months?|tahun|years?|jam|hours?)"
    r"\b(?!\s*\d)",
    re.I,
)
_PERCENT = re.compile(r"(?<![\d.])(\d+(?:\.\d+)?)\s*(%|peratus|per ?cent)", re.I)
_UNITS = {
    "hari bekerja": "wday", "working day": "wday", "working days": "wday", "hari": "day", "day": "day",
    "days": "day", "minggu": "week", "week": "week", "weeks": "week", "bulan": "month", "month": "month",
    "months": "month", "tahun": "year", "year": "year", "years": "year", "jam": "hour", "hour": "hour",
    "hours": "hour",
}
_UNIT_TEXT = {  # unit -> (BM, EN singular, EN plural)
    "wday": ("hari bekerja", "working day", "working days"), "day": ("hari", "day", "days"),
    "week": ("minggu", "week", "weeks"), "month": ("bulan", "month", "months"), "year": ("tahun", "year", "years"),
    "hour": ("jam", "hour", "hours"),
}


def quantities(text: str) -> list[dict]:
    """Amounts (RM), durations and percentages in a clause, in reading order.

    Each: {"kind": amount|duration|percent, "value": float, "unit", "pos", "ms", "en"}.
    """
    found = []
    for m in _AMOUNT.finditer(text or ""):
        raw = m.group(1).rstrip(",")
        per_km = bool(m.group(2))
        value = float(raw.replace(",", ""))
        found.append({"kind": "amount", "value": value, "unit": "km" if per_km else "", "pos": m.start(),
                      "ms": f"RM{raw}" + (" sekilometer" if per_km else ""),
                      "en": f"RM{raw}" + (" per km" if per_km else "")})
    for m in _DURATION.finditer(text or ""):
        unit = _UNITS.get(m.group(2).lower(), "day")
        n = int(m.group(1))
        ms, en1, en2 = _UNIT_TEXT[unit]
        found.append({"kind": "duration", "value": float(n), "unit": unit, "pos": m.start(),
                      "ms": f"{n} {ms}", "en": f"{n} {en1 if n == 1 else en2}"})
    for m in _PERCENT.finditer(text or ""):
        found.append({"kind": "percent", "value": float(m.group(1)), "unit": "%", "pos": m.start(),
                      "ms": f"{m.group(1)}%", "en": f"{m.group(1)}%"})
    return sorted(found, key=lambda q: q["pos"])


def quantity_changes(old_text: str, new_text: str) -> list[dict]:
    """Pairs of the same kind of quantity (in order) whose value or unit changed."""
    old_q, new_q = quantities(old_text), quantities(new_text)
    out = []
    for kind in ("duration", "amount", "percent"):
        a = [q for q in old_q if q["kind"] == kind]
        b = [q for q in new_q if q["kind"] == kind]
        for qa, qb in zip(a, b):
            if (qa["value"], qa["unit"]) != (qb["value"], qb["unit"]):
                out.append({"kind": kind, "old": qa, "new": qb})
    return out


def _topic(text: str, glossary, doc_lang: str) -> tuple[str, str] | None:
    """(BM, EN) name of what a clause is about, from the glossary (earliest, longest phrase)."""
    low = (text or "").lower()
    best = None  # (position, -length, ms, en)
    for en, ms in glossary or []:
        phrase = en if doc_lang == "en" else ms
        if not phrase or phrase.lower() in GENERIC_TERMS:
            continue
        m = re.search(rf"(?<![\w-]){re.escape(phrase.lower())}(?![\w-])", low)
        if m:
            key = (m.start(), -len(phrase), ms, en)
            if best is None or key < best:
                best = key
    return (best[2], best[3]) if best else None


def _quantity_sentences(row: dict, ref_ms: str, ref_en: str, glossary, doc_lang: str) -> tuple[list, list, list]:
    """BM/EN sentences + highlight dicts for the quantity changes of one aligned row."""
    ms_out, en_out, highlights = [], [], []
    topic = _topic(row["old_text"] or row["new_text"], glossary, doc_lang)
    for qc in row.get("quantities", []):
        kind = qc["kind"]
        if kind == "duration":
            noun_ms, noun_en = "Tempoh", "period"
        elif kind == "amount":
            is_rate = re.search(r"\b(kadar|rate)\b", (row["old_text"] + " " + row["new_text"]).lower())
            noun_ms, noun_en = ("Kadar", "rate") if is_rate else ("Amaun", "amount")
        else:
            noun_ms, noun_en = "Peratusan", "percentage"
        subject_ms = f"{noun_ms} {topic[0]}" if topic else noun_ms
        subject_en = f"the {topic[1]} {noun_en}" if topic else f"the {noun_en}"
        ms = f"{ref_ms}: {subject_ms} berubah daripada {qc['old']['ms']} kepada {qc['new']['ms']}."
        en = f"{ref_en}: {subject_en} changes from {qc['old']['en']} to {qc['new']['en']}."
        ms_out.append(ms)
        en_out.append(en)
        highlights.append({"clause_old": row["clause_old"], "clause_new": row["clause_new"], "kind": kind,
                           "old": qc["old"]["ms"], "new": qc["new"]["ms"], "old_en": qc["old"]["en"],
                           "new_en": qc["new"]["en"], "ms": ms, "en": en})
    return ms_out, en_out, highlights


# ---------------------------------------------------------------------------- clauses + alignment


def doc_clauses(store, user, doc_id: str) -> list[dict]:
    """Ordered clauses of a document: [{"ref", "section", "text", "page"}] (access-checked).

    Each numbered line ("4.", "4.1") starts a clause, even when the chunker merged short
    clauses into one chunk; "(a)" items stay with their parent. The header block before
    the first heading is skipped.
    """
    chunks = access.get_chunks(store, user, doc_id)
    body = [c for c in chunks if (c.section or "").strip()] or chunks
    out: dict[str, dict] = {}
    for c in body:
        section = (c.section or "").strip().upper()
        ref = (c.clause_ref or c.section or str(c.chunk_index)).strip()
        for line in _lines(c.text):
            m = _CLAUSE_START.match(line)
            if m:
                ref = m.group(1) or m.group(2)
                line = line[m.end():]
            if ref in out:
                out[ref]["text"] = f"{out[ref]['text']} {line}".strip()
            else:
                out[ref] = {"ref": ref, "section": section, "text": line, "page": c.page_start}
    return [c for c in out.values() if c["text"]]


def align(old: list[dict], new: list[dict]) -> list[tuple[int | None, int | None, float]]:
    """Align clause lists -> [(old_index | None, new_index | None, similarity)] in reading order."""
    sims = [[similarity(o["text"], n["text"]) for n in new] for o in old]
    pairs: dict[int, int] = {}
    used: set[int] = set()

    def accept(candidates):
        for _, i, j in sorted(candidates, reverse=True):
            if i not in pairs and j not in used:
                pairs[i] = j
                used.add(j)

    # 1. Same clause number, when the heading matches (or the text is clearly related).
    same_ref = []
    for i, o in enumerate(old):
        for j, n in enumerate(new):
            if o["ref"] == n["ref"]:
                limit = NUMBER_SIM if o["section"] == n["section"] else NUMBER_OTHER_SIM
                if sims[i][j] >= limit:
                    same_ref.append((sims[i][j] + 1.0, i, j))
    # 2. Any clause with similarity >= 0.80 (guide); 3. same heading and >= 0.5.
    strong = [(sims[i][j], i, j) for i in range(len(old)) for j in range(len(new)) if sims[i][j] >= SIM_THRESHOLD]
    accept(same_ref + strong)
    accept([(sims[i][j], i, j) for i in range(len(old)) for j in range(len(new))
            if sims[i][j] >= SECTION_SIM and old[i]["section"] == new[j]["section"]])
    # 4. Same clause number and heading, even when reworded (e.g. paper form -> e-claim).
    accept([(sims[i][j], i, j) for i in range(len(old)) for j in range(len(new))
            if old[i]["ref"] == new[j]["ref"] and old[i]["section"] == new[j]["section"]])
    # 5. Near matches moved to another heading; 6. related clauses carrying the same kind of
    #    number (e.g. "decides within 30 working days" -> "within 14 working days").
    accept([(sims[i][j], i, j) for i in range(len(old)) for j in range(len(new)) if sims[i][j] >= NEAR_SIM])
    kinds_old = [{q["kind"] for q in quantities(o["text"])} for o in old]
    kinds_new = [{q["kind"] for q in quantities(n["text"])} for n in new]
    accept([(sims[i][j], i, j) for i in range(len(old)) for j in range(len(new))
            if sims[i][j] >= QUANTITY_SIM and kinds_old[i] & kinds_new[j]])

    # Merge into reading order: new document order, removed clauses at their old position.
    rows: list[tuple[int | None, int | None, float]] = []
    removed = sorted(i for i in range(len(old)) if i not in pairs)
    by_new = {j: i for i, j in pairs.items()}
    for j in range(len(new)):
        i = by_new.get(j)
        if i is not None:
            while removed and removed[0] < i:
                rows.append((removed.pop(0), None, 0.0))
            rows.append((i, j, sims[i][j]))
        else:
            rows.append((None, j, 0.0))
    rows.extend((i, None, 0.0) for i in removed)
    return rows


def _row(o: dict | None, n: dict | None, sim: float) -> dict:
    old_text, new_text = (o or {}).get("text", ""), (n or {}).get("text", "")
    if o and n:
        kind = SAME if _norm(old_text) == _norm(new_text) else CHANGED
    else:
        kind = ADDED if n else REMOVED
    inline, left, right = word_diff(old_text, new_text)
    return {
        "clause_old": (o or {}).get("ref", ""),
        "clause_new": (n or {}).get("ref", ""),
        "type": kind,
        "old_text": old_text,
        "new_text": new_text,
        "diff_html": inline,
        "old_html": left,
        "new_html": right,
        "section": (n or o or {}).get("section", ""),
        "page_old": (o or {}).get("page"),
        "page_new": (n or {}).get("page"),
        "similarity": round(sim, 3),
        "quantities": quantity_changes(old_text, new_text) if kind == CHANGED else [],
    }


def _scoped_refs(scope: str) -> list[str]:
    """'clauses: 4.2, 4.3' -> ['4.2', '4.3']; 'whole' -> []."""
    if not scope or not scope.lower().startswith("clauses"):
        return []
    return [r for r in re.split(r"[,\s;]+", scope.split(":", 1)[-1]) if r]


def _amendment_rows(old: list[dict], new: list[dict], refs: list[str]) -> list[dict]:
    """Clause-scoped amendment: each amended clause vs the most similar clause of the amending text."""
    rows = []
    for o in old:
        if o["ref"] not in refs:
            rows.append(_row(o, o, 1.0))  # stays in force unchanged
            continue
        best_j, best = None, 0.0
        for j, n in enumerate(new):
            s = similarity(o["text"], n["text"])
            if s > best:
                best_j, best = j, s
        if best_j is not None and best >= SECTION_SIM:
            rows.append(_row(o, new[best_j], best))
        else:  # amending text not found: show the clause as amended without a counterpart
            row = _row(o, None, 0.0)
            row["type"] = CHANGED
            rows.append(row)
    return rows


# ---------------------------------------------------------------------------- summaries


def _relation_between(store, old_id: str, new_id: str):
    """The (verified first) relation new -> old, if any."""
    rels = [r for r in store.relations if not r.rejected and r.source_doc_id == new_id and r.target_doc_id == old_id]
    rels.sort(key=lambda r: (not r.verified, r.relation_type == REFERENCES))
    return rels[0] if rels else None


def _applicability(store, user, doc) -> str:
    text = (doc.applicability or "").strip()
    if not text:
        for c in access.get_chunks(store, user, doc.doc_id):
            if (c.section or "").strip().upper() in APPLICABILITY_SECTIONS:
                text = c.text
                break
    text = re.sub(r"^\(?\d+(?:\.\d+)*[.)]?\s+", "", " ".join(text.split()))
    return text or NOT_STATED


def _offline_summary(ctx: dict, rows: list[dict], glossary) -> tuple[str, str, list[dict]]:
    """Deterministic BM + EN summary listing changed amounts/durations first."""
    old_label, new_label, rel_type, scope_refs = ctx["old_label"], ctx["new_label"], ctx["relation_type"], ctx["refs"]
    doc_lang = ctx["doc_lang"]
    if rel_type == AMENDS and scope_refs:
        refs = ", ".join(scope_refs)
        intro_ms = f"{new_label} meminda perenggan {refs} {old_label} sahaja; peruntukan lain kekal berkuat kuasa."
        intro_en = f"{new_label} amends clause {refs} of {old_label} only; other provisions remain in force."
    elif rel_type in VERBS:
        intro_ms = f"{new_label} {VERBS[rel_type][0]} {old_label}."
        intro_en = f"{new_label} {VERBS[rel_type][1]} {old_label}."
    else:
        intro_ms = f"Perbandingan {old_label} dengan {new_label}."
        intro_en = f"Comparison of {old_label} with {new_label}."

    quantity_ms, quantity_en, other_ms, other_en, highlights = [], [], [], [], []
    for row in rows:
        if row["type"] == SAME:
            continue
        old_ref, new_ref = row["clause_old"], row["clause_new"]
        if rel_type == AMENDS and scope_refs:
            ref_ms, ref_en = f"Perenggan {old_ref}", f"Clause {old_ref}"
        elif old_ref and new_ref and old_ref != new_ref:
            ref_ms, ref_en = f"Perenggan {old_ref} (kini {new_ref})", f"Clause {old_ref} (now {new_ref})"
        else:
            ref_ms, ref_en = f"Perenggan {old_ref or new_ref}", f"Clause {old_ref or new_ref}"
        if row["quantities"]:
            ms, en, hl = _quantity_sentences(row, ref_ms, ref_en, glossary, doc_lang)
            quantity_ms += ms
            quantity_en += en
            highlights += hl
            continue
        if row["section"] in BOILERPLATE:
            continue
        if row["type"] == CHANGED and row["new_text"]:
            other_ms.append(f"{ref_ms} dipinda; teks baharu: “{_excerpt(row['new_text'])}”.")
            other_en.append(f"{ref_en} revised; new text: “{_excerpt(row['new_text'])}”.")
        elif row["type"] == ADDED:
            other_ms.append(f"Perenggan baharu {new_ref}: “{_excerpt(row['new_text'])}”.")
            other_en.append(f"New clause {new_ref}: “{_excerpt(row['new_text'])}”.")
        elif row["type"] == REMOVED:
            other_ms.append(f"{ref_ms} dibuang: “{_excerpt(row['old_text'], 10)}”.")
            other_en.append(f"{ref_en} removed: “{_excerpt(row['old_text'], 10)}”.")

    def compose(intro: str, quantity: list, other: list, tail: str, more: str, none: str) -> str:
        parts, used = [intro], len(intro.split()) + len(tail.split())
        body = quantity + other
        if not body:
            parts.append(none)
        for i, sentence in enumerate(body):
            n = len(sentence.split())
            if used + n > MAX_SUMMARY_WORDS and i > 0:
                parts.append(more.format(n=len(body) - i))
                break
            parts.append(sentence)
            used += n
        if tail:
            parts.append(tail)
        return " ".join(parts)

    eff = ctx["effective_date"]
    tail_ms = f"Berkuat kuasa mulai {format_date(eff, 'ms')}." if eff else ""
    tail_en = f"Effective from {format_date(eff, 'en')}." if eff else ""
    summary_ms = compose(intro_ms, quantity_ms, other_ms, tail_ms, "Dan {n} perubahan lain (lihat jadual).",
                         "Tiada perubahan kandungan utama dikesan.")
    summary_en = compose(intro_en, quantity_en, other_en, tail_en, "And {n} other change(s) (see the table).",
                         "No substantive content changes detected.")
    return summary_ms, summary_en, highlights


_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")


def _numbers_ok(summary: str, allowed_text: str) -> bool:
    """True when every number in an LLM summary appears in the diff (no invented numbers)."""
    allowed = {n.replace(",", "") for n in _NUMBER.findall(allowed_text)}
    for n in _NUMBER.findall(summary or ""):
        if n.replace(",", "") not in allowed and n.rstrip(".0") not in allowed:
            return False
    return True


def _llm_summary(store, ctx: dict, rows: list[dict]) -> tuple[dict | None, str | None]:
    """CHANGE_SUMMARY prompt (guide B5). Returns (data, warning); data None -> keep the template."""
    diff = [
        {"clause_old": r["clause_old"], "clause_new": r["clause_new"], "type": r["type"],
         "old_text": r["old_text"][:700], "new_text": r["new_text"][:700]}
        for r in rows if r["type"] != SAME
    ][:25]
    if not diff:
        return None, None
    prompt = CHANGE_SUMMARY.format(
        old_circular_no=ctx["old_label"], old_title=ctx["old_title"], new_circular_no=ctx["new_label"],
        new_title=ctx["new_title"], diff_json=json.dumps(diff, ensure_ascii=False),
    )
    data, warning = call_json(store.llm, CHANGE_SUMMARY_SYSTEM, prompt, CHANGE_SUMMARY_SCHEMA)
    if not data:
        return None, warning
    allowed = " ".join(f"{d['clause_old']} {d['clause_new']} {d['old_text']} {d['new_text']}" for d in diff)
    allowed += f" {ctx['old_label']} {ctx['new_label']} {ctx['effective_date'] or ''} {len(diff)} {ctx['who']}"
    eff = ctx["effective_date"]
    if eff:
        allowed += f" {eff.day} {eff.month} {eff.year}"
    if not (data.get("summary_ms") and data.get("summary_en")):
        return None, "Model returned an empty change summary; using the offline template."
    if not (_numbers_ok(data["summary_ms"], allowed) and _numbers_ok(data["summary_en"], allowed)):
        return None, "Model summary mentioned numbers not in the text; using the offline template."
    return data, None


# ---------------------------------------------------------------------------- main entry


def _empty(warning: str | None = None) -> dict:
    return {
        "aligned": [], "summary_ms": "", "summary_en": "", "effective_date": None, "who_is_affected": NOT_STATED,
        "mode": "offline", "warnings": [warning] if warning else [], "old_label": "", "new_label": "",
        "relation_type": "", "scope": "", "counts": {}, "highlights": [],
    }


def _cache_key(store, old_id: str, new_id: str, rel, old_clauses, new_clauses) -> str:
    payload = json.dumps([old_clauses, new_clauses, getattr(rel, "relation_type", ""), getattr(rel, "scope", ""),
                          str(getattr(rel, "effective_date", ""))], ensure_ascii=False, sort_keys=True)
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]
    return f"{old_id}|{new_id}|{getattr(store.llm, 'provider', 'offline')}|{digest}"


def what_changed(store, user, old_id: str, new_id: str, use_cache: bool = True) -> dict:
    """Clause-aligned diff of old_id -> new_id with BM + EN summaries (see module docstring)."""
    old, new = access.get_doc(store, user, old_id), access.get_doc(store, user, new_id)
    if old is None or new is None:
        return _empty(NOT_AVAILABLE)
    old_clauses, new_clauses = doc_clauses(store, user, old_id), doc_clauses(store, user, new_id)
    rel = _relation_between(store, old_id, new_id)
    key = _cache_key(store, old_id, new_id, rel, old_clauses, new_clauses)
    cache = store.read_json(CACHE, {}) if use_cache else {}
    if isinstance(cache, dict) and key in cache:
        return cache[key]

    rel_type = rel.relation_type if rel else ""
    refs = _scoped_refs(rel.scope) if rel and rel.relation_type == AMENDS else []
    if refs:
        rows = _amendment_rows(old_clauses, new_clauses, refs)
    else:
        rows = [_row(old_clauses[i] if i is not None else None, new_clauses[j] if j is not None else None, s)
                for i, j, s in align(old_clauses, new_clauses)]
        if rel_type == AMENDS:  # whole-document amendment: untouched old clauses stay in force
            for row in rows:
                if row["type"] == REMOVED:
                    row["type"] = SAME
                    row["new_text"], row["new_html"] = row["old_text"], html.escape(row["old_text"])

    effective = (rel.effective_date if rel and rel.effective_date else None) or new.effective_date
    who = _applicability(store, user, new)
    ctx = {"old_label": old.label, "new_label": new.label, "old_title": old.title, "new_title": new.title,
           "relation_type": rel_type, "refs": refs, "effective_date": effective, "who": who,
           "doc_lang": "en" if (new.language == "en" or old.language == "en") else "ms"}
    summary_ms, summary_en, highlights = _offline_summary(ctx, rows, store.glossary)
    result = {
        "aligned": rows,
        "summary_ms": summary_ms,
        "summary_en": summary_en,
        "effective_date": effective.isoformat() if effective else None,
        "who_is_affected": who,
        "mode": "offline",
        "warnings": [],
        "old_id": old_id,
        "new_id": new_id,
        "old_label": old.label,
        "new_label": new.label,
        "relation_type": rel_type,
        "scope": rel.scope if rel else "",
        "counts": {t: sum(1 for r in rows if r["type"] == t) for t in (CHANGED, ADDED, REMOVED, SAME)},
        "highlights": highlights,
    }

    llm_warning = None
    if getattr(store.llm, "provider", "offline") != "offline":
        data, llm_warning = _llm_summary(store, ctx, rows)
        if data:
            result.update(summary_ms=data["summary_ms"], summary_en=data["summary_en"],
                          mode=store.llm.provider, llm_changes=data.get("changes", []))
            if data.get("who_is_affected") and who == NOT_STATED:
                result["who_is_affected"] = data["who_is_affected"]
        elif llm_warning:
            result["warnings"].append(llm_warning)

    if use_cache and not llm_warning:
        cache = cache if isinstance(cache, dict) else {}
        cache[key] = result
        while len(cache) > CACHE_MAX:
            cache.pop(next(iter(cache)))
        store.write_json(CACHE, cache)
    return result


def type_label(kind: str, lang: str = "ms") -> tuple[str, str]:
    """('Dipinda', 'orange') for the diff table."""
    ms, en, colour = TYPE_LABELS.get(kind, (kind, kind, "gray"))
    return (en if lang == "en" else ms), colour
