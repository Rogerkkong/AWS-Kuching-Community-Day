"""FEATURE D - golden-set evaluation, Baseline vs Navigator (guide 9.2-9.3, FR-19).

    result = run(store, "data/golden_set.csv")    # {"baseline", "navigator", "rows", "by_type", "meta"}
    paths = write_results(result)                  # eval/results/summary.md, results.csv, results.json
    cached = load_cached()                         # what the Evaluation tab shows by default

Every golden question goes through ask.ask() twice with the question's user profile:
  baseline   mode="baseline": same retrieval and answer step, NO status filter, NO jurisdiction
             logic, NO amendment handling, NO excluded list (a typical document chatbot)
  navigator  the full system

golden_set.csv columns (Appendix C):
  id, question, language (ms|en|mixed), type (normal|trap_cancelled|jurisdiction|unanswerable|access),
  user_profile (FED-T0|SWK-T0|FED-T1), expected_doc, expected_clause,
  must_not_cite  ";"-separated doc_ids; "DOC@4.2" means only clause 4.2 of DOC (an amended clause)
  answer_keywords ";"-separated groups that must all appear, "|" separates alternatives;
                  "refusal" (or an empty expected_doc) means the right answer is a refusal

Metrics (per mode, guide 9.3):
  recall_at_5              expected document among the top-5 retrieved passages
  mrr                      mean of 1 / rank of the first passage from the expected document
  citation_accuracy        answered, and the primary citation [S1] is the expected document + clause
  cancelled_citation_rate  trap questions where a must_not_cite document is cited as current
                           (cited without a "historical" / "amended" label)
  refusal_accuracy         questions with no permitted answer (unanswerable + access) that were refused
  false_refusal_rate       answerable questions that were refused
  jurisdiction_accuracy    jurisdiction questions whose primary citation is the right jurisdiction's rule
  correct_current_rate     right document + clause, keywords present, nothing stale presented as current,
                           no leak (or a correct refusal): the "correct AND current" headline
  access_leaks             answers that expose a document above the asker's clearance (must be 0)
  latency_p50_ms / p95     wall-clock time of ask()

The run uses a private copy of the store (fresh runtime folder) by default, so the golden
questions never pollute the demo's query log or analytics, and uploads made during a live
demo do not change the numbers.
"""

from __future__ import annotations

import csv
import json
import re
import shutil
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable

import numpy as np

from . import access
from . import ask as ask_mod
from .config import PROTOTYPE_DIR
from .models import AskResponse, Citation, User

GOLDEN_PATH = PROTOTYPE_DIR / "data" / "golden_set.csv"
RESULTS_DIR = PROTOTYPE_DIR / "eval" / "results"
GOLDEN_COLUMNS = (
    "id", "question", "language", "type", "user_profile",
    "expected_doc", "expected_clause", "must_not_cite", "answer_keywords",
)
TYPES = ("normal", "trap_cancelled", "jurisdiction", "unanswerable", "access")
LANGUAGES = ("ms", "en", "mixed")
MODES = ("baseline", "navigator")
REFUSAL_KEYWORD = "refusal"

# key -> (label BM, label EN, target text, kind). kind: rate | ms | count
METRICS: dict[str, tuple[str, str, str, str]] = {
    "correct_current_rate": ("Jawapan betul & semasa", "Correct & current answers", "-", "rate"),
    "cancelled_citation_rate": ("Kadar petikan pekeliling dibatalkan", "Cancelled-citation rate", "<= 5%", "rate"),
    "recall_at_5": ("Recall@5", "Recall@5", ">= 0.80", "rate"),
    "mrr": ("MRR", "MRR", ">= 0.60", "score"),
    "citation_accuracy": ("Ketepatan petikan", "Citation accuracy", ">= 0.85", "rate"),
    "jurisdiction_accuracy": ("Ketepatan bidang kuasa", "Jurisdiction accuracy", "-", "rate"),
    "refusal_accuracy": ("Ketepatan penolakan", "Refusal accuracy", ">= 0.80", "rate"),
    "false_refusal_rate": ("Kadar penolakan salah", "False-refusal rate", "-", "rate"),
    "access_leaks": ("Kebocoran akses", "Access leaks", "0", "count"),
    "latency_p50_ms": ("Latensi p50", "Latency p50", "<= 8 s", "ms"),
    "latency_p95_ms": ("Latensi p95", "Latency p95", "<= 15 s", "ms"),
}

CSV_FIELDS = (
    "id", "mode", "type", "language", "user_profile", "question", "expected_doc", "expected_clause",
    "must_not_cite", "answerable", "should_refuse", "refusal_ok", "expected_rank", "in_top5", "reciprocal_rank",
    "primary_citation", "citations", "citation_ok", "stale_as_current", "stale_labelled", "excluded",
    "keywords_ok", "leak", "leak_detail", "correct_current", "confidence", "primary_status", "latency_ms",
    "llm_mode", "failure", "retrieved_top5", "answer",
)


# ----------------------------------------------------------------------------
# Golden set
# ----------------------------------------------------------------------------


def parse_must_not(text: str) -> list[tuple[str, str]]:
    """'SPP-3-2019;SPP-1-2023@4.2' -> [('SPP-3-2019', ''), ('SPP-1-2023', '4.2')]."""
    out = []
    for part in (text or "").split(";"):
        part = part.strip()
        if part:
            doc_id, _, clause = part.partition("@")
            out.append((doc_id.strip(), clause.strip()))
    return out


def parse_keywords(text: str) -> list[list[str]]:
    """'60 hari;e-Tuntutan|eclaim' -> [['60 hari'], ['e-Tuntutan', 'eclaim']]. 'refusal' -> []."""
    text = (text or "").strip()
    if not text or text.lower() == REFUSAL_KEYWORD:
        return []
    groups = []
    for group in text.split(";"):
        alts = [a.strip() for a in group.split("|") if a.strip()]
        if alts:
            groups.append(alts)
    return groups


def load_golden(path: str | Path | None = None) -> list[dict]:
    """Read golden_set.csv into dicts (raw columns + parsed must_not / keywords / should_refuse)."""
    path = Path(path or GOLDEN_PATH)
    rows = []
    with path.open(encoding="utf-8-sig", newline="") as fh:
        for raw in csv.DictReader(fh):
            row = {k: (raw.get(k) or "").strip() for k in GOLDEN_COLUMNS}
            if not row["id"] or not row["question"]:
                continue
            row["must_not"] = parse_must_not(row["must_not_cite"])
            row["keywords"] = parse_keywords(row["answer_keywords"])
            row["should_refuse"] = not row["expected_doc"]
            rows.append(row)
    return rows


def validate_golden(store, rows: list[dict]) -> list[str]:
    """Problems with the golden set against the loaded corpus ([] = fine)."""
    problems = []
    for row in rows:
        rid = row["id"]
        if row["type"] not in TYPES:
            problems.append(f"{rid}: unknown type {row['type']!r}")
        if row["language"] not in LANGUAGES:
            problems.append(f"{rid}: unknown language {row['language']!r}")
        if row["user_profile"] not in store.users:
            problems.append(f"{rid}: unknown user_profile {row['user_profile']!r}")
        doc_id = row["expected_doc"]
        if doc_id:
            if doc_id not in store.docs:
                problems.append(f"{rid}: expected_doc {doc_id} not in corpus")
            elif row["expected_clause"]:
                clauses = {c.clause_ref for c in store.chunks_by_doc.get(doc_id, [])}
                if row["expected_clause"] not in clauses:
                    problems.append(f"{rid}: clause {row['expected_clause']} not found in {doc_id}")
        for bad_doc, _ in row["must_not"]:
            if bad_doc not in store.docs:
                problems.append(f"{rid}: must_not_cite {bad_doc} not in corpus")
        if row["type"] == "trap_cancelled" and not row["must_not"]:
            problems.append(f"{rid}: trap question without must_not_cite")
    return problems


# ----------------------------------------------------------------------------
# Checks for one answer
# ----------------------------------------------------------------------------


def clause_matches(cited: str, expected: str) -> bool:
    """'4.1' matches '4.1'; a section-level expectation '4' also accepts '4.1', '4.2'."""
    cited, expected = (cited or "").strip(), (expected or "").strip()
    if not expected:
        return True
    return cited == expected or cited.startswith(expected + ".")


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).casefold()


def keywords_found(answer: str, groups: list[list[str]]) -> bool:
    """Every group has at least one alternative in the answer (case-insensitive)."""
    text = _norm(answer)
    return all(any(_norm(alt) in text for alt in group) for group in groups)


def _words(text: str) -> list[str]:
    """Lower-case words; numbers keep inner separators ('3,000', '0.80'), trailing punctuation is dropped."""
    return re.findall(r"[0-9a-z]+(?:[.,][0-9a-z]+)*", (text or "").casefold())


def _shingles(text: str, n: int = 5) -> set[str]:
    words = _words(text)
    return {" ".join(words[i:i + n]) for i in range(max(0, len(words) - n + 1))}


class LeakChecker:
    """Finds content from documents above a user's clearance in an AskResponse.

    Independent of ask.py: checks doc ids in retrieved / cited / excluded / comparison /
    extra, restricted circular numbers and titles, and any 5-word phrase that exists ONLY
    in restricted documents (so shared boilerplate like the watermark is ignored).
    """

    def __init__(self, store):
        self.store = store
        self._cache: dict[int, tuple[set[str], set[str], set[str]]] = {}

    def markers(self, user: User | None) -> tuple[set[str], set[str], set[str]]:
        level = access.clearance(user)
        if level not in self._cache:
            visible = access.visible_doc_ids(self.store, user)
            hidden = [d for d in self.store.docs.values() if d.doc_id not in visible]
            open_shingles: set[str] = set()
            for doc_id in visible:
                open_shingles |= _shingles(self.store.doc_text(doc_id))
            secret: set[str] = set()
            for doc in hidden:
                secret |= _shingles(self.store.doc_text(doc.doc_id)) - open_shingles
            names = {d.circular_no for d in hidden if d.circular_no} | {d.title for d in hidden if d.title}
            self._cache[level] = ({d.doc_id for d in hidden}, names, secret)
        return self._cache[level]

    def check(self, user: User | None, resp: AskResponse) -> list[str]:
        """Leak descriptions ([] = clean)."""
        hidden_ids, names, secret = self.markers(user)
        if not hidden_ids:
            return []
        found = []
        for hit in resp.retrieved:
            if hit.doc.doc_id in hidden_ids:
                found.append(f"retrieved {hit.doc.doc_id}")
        for cit in resp.citations:
            if cit.doc_id in hidden_ids:
                found.append(f"cited {cit.doc_id}")
        for item in resp.excluded:
            if item.get("doc_id") in hidden_ids:
                found.append(f"excluded list {item.get('doc_id')}")
        blob = json.dumps(
            {"comparison": resp.comparison, "extra": resp.extra, "excluded": resp.excluded},
            ensure_ascii=False, default=str,
        )
        for doc_id in hidden_ids:
            if doc_id in blob:
                found.append(f"metadata mentions {doc_id}")
        text = resp.answer or ""
        for name in names:
            if name and name in text:
                found.append(f"answer names {name!r}")
        answer_shingles = _shingles(text + " " + " ".join(c.snippet for c in resp.citations))
        overlap = answer_shingles & secret
        if overlap:
            found.append(f"answer quotes restricted text ({sorted(overlap)[0]!r})")
        return sorted(set(found))


def _cit_text(c: Citation) -> str:
    return f"{c.doc_id} {c.clause_ref} [{c.status}]"


def _is_stale(cit: Citation, must_not: list[tuple[str, str]]) -> bool:
    return any(cit.doc_id == doc_id and (not clause or clause_matches(cit.clause_ref, clause)) for doc_id, clause in must_not)


def evaluate_answer(row: dict, mode: str, resp: AskResponse, user: User | None, leaks: LeakChecker, latency_ms: float) -> dict:
    """Score one ask() response against its golden row. Returns a flat, JSON-friendly dict."""
    expected = row["expected_doc"]
    retrieved_docs = [h.doc.doc_id for h in resp.retrieved]
    rank = next((i for i, d in enumerate(retrieved_docs, 1) if d == expected), 0) if expected else 0
    cites = list(resp.citations)
    primary = cites[0] if cites else None
    roles = {c.get("label"): c.get("role", "current") for c in resp.extra.get("context", []) if isinstance(c, dict)}

    citation_ok = bool(
        expected and resp.answerable and primary
        and primary.doc_id == expected and clause_matches(primary.clause_ref, row["expected_clause"])
    )
    stale = [c for c in cites if _is_stale(c, row["must_not"])]
    # "presented as current": the baseline never labels status; the navigator labels
    # historical / amended passages, which then do not count as current.
    stale_current = [c for c in stale if mode == "baseline" or roles.get(c.label, "current") == "current"]
    stale_labelled = [c for c in stale if c not in stale_current]
    leak = leaks.check(user, resp)
    refusal_ok = bool(row["should_refuse"] and not resp.answerable and not leak)
    kw_ok = (not resp.answerable) if row["should_refuse"] else bool(resp.answerable and keywords_found(resp.answer, row["keywords"]))

    if row["should_refuse"]:
        correct = refusal_ok
    else:
        correct = bool(resp.answerable and citation_ok and kw_ok and not stale_current and not leak)

    failure = ""
    if leak:
        failure = "access leak"
    elif row["should_refuse"] and resp.answerable:
        failure = "answered (should refuse)"
    elif not row["should_refuse"] and not resp.answerable:
        failure = "refused (answer exists)"
    elif stale_current:
        failure = "cited stale rule as current: " + ", ".join(_cit_text(c) for c in stale_current)
    elif not row["should_refuse"] and not citation_ok:
        failure = f"primary citation {(_cit_text(primary) if primary else '-')} (expected {expected} {row['expected_clause']})"
    elif not row["should_refuse"] and not kw_ok:
        failure = "answer keywords missing: " + row["answer_keywords"]

    return {
        "id": row["id"],
        "mode": mode,
        "type": row["type"],
        "language": row["language"],
        "user_profile": row["user_profile"],
        "question": row["question"],
        "expected_doc": expected,
        "expected_clause": row["expected_clause"],
        "must_not_cite": row["must_not_cite"],
        "answerable": bool(resp.answerable),
        "should_refuse": bool(row["should_refuse"]),
        "refusal_ok": refusal_ok,
        "expected_rank": rank,
        "in_top5": bool(rank and rank <= 5),
        "reciprocal_rank": round(1.0 / rank, 4) if rank else 0.0,
        "primary_citation": _cit_text(primary) if primary else "",
        "citations": "; ".join(f"[{c.label}] " + _cit_text(c) for c in cites),
        "citation_ok": citation_ok,
        "stale_as_current": "; ".join(_cit_text(c) for c in stale_current),
        "stale_labelled": "; ".join(_cit_text(c) for c in stale_labelled),
        "excluded": "; ".join(str(e.get("circular_no") or e.get("doc_id")) for e in resp.excluded),
        "keywords_ok": bool(kw_ok),
        "leak": bool(leak),
        "leak_detail": "; ".join(leak),
        "correct_current": bool(correct),
        "confidence": resp.confidence,
        "primary_status": resp.primary_status,
        "latency_ms": round(latency_ms, 2),
        "llm_mode": resp.llm_mode,
        "failure": failure,
        "retrieved_top5": "; ".join(f"{h.doc.doc_id} {h.chunk.clause_ref}" for h in resp.retrieved[:5]),
        "answer": resp.answer or "",
    }


# ----------------------------------------------------------------------------
# Metrics
# ----------------------------------------------------------------------------


def _mean(values: list) -> float | None:
    return round(float(np.mean(values)), 3) if values else None


def compute_metrics(rows: list[dict]) -> dict:
    """Guide 9.3 metrics for the rows of ONE mode."""
    answerable = [r for r in rows if not r["should_refuse"]]
    refuse = [r for r in rows if r["should_refuse"]]
    traps = [r for r in rows if r["type"] == "trap_cancelled"]
    juris = [r for r in rows if r["type"] == "jurisdiction"]
    latencies = [r["latency_ms"] for r in rows]
    return {
        "n": len(rows),
        "correct_current_rate": _mean([r["correct_current"] for r in rows]),
        "correct_current": sum(r["correct_current"] for r in rows),
        "recall_at_5": _mean([r["in_top5"] for r in answerable]),
        "mrr": _mean([r["reciprocal_rank"] for r in answerable]),
        "citation_accuracy": _mean([r["citation_ok"] for r in answerable]),
        "cancelled_citation_rate": _mean([bool(r["stale_as_current"]) for r in traps]),
        "cancelled_citations": sum(bool(r["stale_as_current"]) for r in traps),
        "trap_n": len(traps),
        "jurisdiction_accuracy": _mean([r["citation_ok"] for r in juris]),
        "refusal_accuracy": _mean([r["refusal_ok"] for r in refuse]),
        "refusal_n": len(refuse),
        "false_refusal_rate": _mean([not r["answerable"] for r in answerable]),
        "access_leaks": sum(r["leak"] for r in rows),
        "latency_p50_ms": round(float(np.percentile(latencies, 50)), 1) if latencies else None,
        "latency_p95_ms": round(float(np.percentile(latencies, 95)), 1) if latencies else None,
    }


def by_type(rows: list[dict]) -> dict:
    """{type: {mode: {"n", "correct"}}} for the per-type table."""
    out: dict[str, dict] = {}
    for qtype in TYPES:
        for mode in MODES:
            subset = [r for r in rows if r["type"] == qtype and r["mode"] == mode]
            if subset:
                out.setdefault(qtype, {})[mode] = {"n": len(subset), "correct": sum(r["correct_current"] for r in subset)}
    return out


# ----------------------------------------------------------------------------
# Run
# ----------------------------------------------------------------------------


@contextmanager
def _eval_store(store, isolated: bool):
    """A private copy of the base corpus (empty runtime folder) so the run leaves no trace."""
    if not isolated:
        yield store
        return
    from .store import Store

    tmp = tempfile.mkdtemp(prefix="mixup-eval-")
    try:
        settings = store.settings.with_changes(runtime_dir=Path(tmp))
        yield Store(settings, llm=store.llm)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def run(
    store,
    golden_path: str | Path | None = None,
    isolated: bool = True,
    modes: Iterable[str] = MODES,
    progress: Callable[[int, int, str], None] | None = None,
) -> dict:
    """Run every golden question in each mode. Returns {"baseline", "navigator", "rows", "by_type", "meta"}."""
    golden = load_golden(golden_path)
    modes = [m for m in modes if m in MODES]
    started = time.perf_counter()
    with _eval_store(store, isolated) as st:
        problems = validate_golden(st, golden)
        leaks = LeakChecker(st)
        rows: list[dict] = []
        total = len(golden) * len(modes)
        for i, row in enumerate(golden):
            user = st.users.get(row["user_profile"])
            for j, mode in enumerate(modes):
                if progress:
                    progress(i * len(modes) + j, total, row["id"])
                t0 = time.perf_counter()
                resp = ask_mod.ask(st, user, row["question"], mode=mode)
                latency = (time.perf_counter() - t0) * 1000
                rows.append(evaluate_answer(row, mode, resp, user, leaks, latency))
        llm = st.llm
        meta = {
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "golden_path": str(Path(golden_path or GOLDEN_PATH).name),
            "n_questions": len(golden),
            "languages": {lang: sum(1 for r in golden if r["language"] == lang) for lang in LANGUAGES},
            "types": {t: sum(1 for r in golden if r["type"] == t) for t in TYPES},
            "llm_provider": getattr(llm, "provider", "offline"),
            "llm_label": getattr(llm, "label", getattr(llm, "provider", "offline")),
            "today": st.today.isoformat(),
            "corpus_docs": len(st.docs),
            "restricted_docs": sum(1 for d in st.docs.values() if d.classification_level > 0),
            "isolated": isolated,
            "problems": problems,
            "duration_s": round(time.perf_counter() - started, 2),
        }
    if progress:
        progress(total, total, "")
    result = {"meta": meta, "rows": rows, "by_type": by_type(rows)}
    for mode in MODES:
        result[mode] = compute_metrics([r for r in rows if r["mode"] == mode]) if mode in modes else {}
    return result


# ----------------------------------------------------------------------------
# Formatting and files
# ----------------------------------------------------------------------------


def format_value(key: str, value) -> str:
    """0.083 -> '8.3%', latency -> '12.4 ms', counts as integers, None -> 'n/a'."""
    if value is None:
        return "n/a"
    kind = METRICS.get(key, ("", "", "", "score"))[3]
    if kind == "rate":
        return f"{value * 100:.1f}%"
    if kind == "ms":
        return f"{value:,.0f} ms" if value >= 100 else f"{value:.1f} ms"
    if kind == "count":
        return str(int(value))
    return f"{value:.3f}"


def _fraction(metrics: dict, key: str, count_key: str | None, n_key: str) -> str:
    text = format_value(key, metrics.get(key))
    if count_key and metrics.get(n_key):
        text += f" ({metrics.get(count_key, 0)}/{metrics[n_key]})"
    return text


def comparison_table(result: dict, lang: str = "en") -> list[dict]:
    """Rows {"key", "metric", "baseline", "navigator", "target"} for the UI and summary.md."""
    out = []
    for key, (ms, en, target, _) in METRICS.items():
        cells = {}
        for mode in MODES:
            metrics = result.get(mode) or {}
            if key == "cancelled_citation_rate":
                cells[mode] = _fraction(metrics, key, "cancelled_citations", "trap_n")
            elif key == "correct_current_rate":
                cells[mode] = _fraction(metrics, key, "correct_current", "n")
            else:
                cells[mode] = format_value(key, metrics.get(key))
        out.append({
            "key": key, "metric": en if lang == "en" else ms,
            "baseline": cells["baseline"], "navigator": cells["navigator"], "target": target,
        })
    return out


def text_table(result: dict) -> str:
    """Plain-text comparison table for the CLI."""
    rows = comparison_table(result, "en")
    headers = ("Metric", "Baseline (plain RAG)", "Navigator", "Target")
    data = [(r["metric"], r["baseline"], r["navigator"], r["target"]) for r in rows]
    widths = [max(len(str(x)) for x in col) for col in zip(headers, *data)]
    line = lambda cells: "  ".join(str(c).ljust(w) for c, w in zip(cells, widths))  # noqa: E731
    return "\n".join([line(headers), line(["-" * w for w in widths])] + [line(d) for d in data])


def summary_markdown(result: dict) -> str:
    """eval/results/summary.md: comparison table, per-type table, failures, method note."""
    meta = result.get("meta", {})
    base, nav = result.get("baseline") or {}, result.get("navigator") or {}
    langs = meta.get("languages", {})
    types = meta.get("types", {})
    lines = [
        "# Evaluation: Baseline (plain RAG) vs MixUp Navigator",
        "",
        f"Generated {meta.get('generated_at', '-')} | status date (today) {meta.get('today', '-')} | "
        f"model mode: **{meta.get('llm_label', meta.get('llm_provider', 'offline'))}** | "
        f"{meta.get('n_questions', 0)} golden questions "
        f"({langs.get('ms', 0)} BM, {langs.get('en', 0)} EN, {langs.get('mixed', 0)} mixed) | "
        f"{meta.get('corpus_docs', 0)} synthetic documents",
        "",
    ]
    if base and nav:
        lines += [
            f"**Headline:** on trap questions about cancelled or replaced rules, the baseline presented a stale "
            f"circular as current in {format_value('cancelled_citation_rate', base.get('cancelled_citation_rate'))} "
            f"of cases ({base.get('cancelled_citations', 0)}/{base.get('trap_n', 0)}); the Navigator in "
            f"{format_value('cancelled_citation_rate', nav.get('cancelled_citation_rate'))} "
            f"({nav.get('cancelled_citations', 0)}/{nav.get('trap_n', 0)}). "
            f"Correct and current answers: baseline {base.get('correct_current', 0)}/{base.get('n', 0)}, "
            f"Navigator {nav.get('correct_current', 0)}/{nav.get('n', 0)}. Access leaks: "
            f"baseline {base.get('access_leaks', 0)}, Navigator {nav.get('access_leaks', 0)}.",
            "",
        ]
    lines += ["| Metric | Baseline (plain RAG) | Navigator | Target |", "|---|---|---|---|"]
    for r in comparison_table(result, "en"):
        lines.append(f"| {r['metric']} | {r['baseline']} | {r['navigator']} | {r['target']} |")
    lines += ["", "## By question type (correct and current)", "", "| Type | n | Baseline | Navigator |", "|---|---|---|---|"]
    for qtype, modes in result.get("by_type", {}).items():
        b, n = modes.get("baseline", {}), modes.get("navigator", {})
        count = types.get(qtype) or b.get("n") or n.get("n") or 0
        lines.append(f"| {qtype} | {count} | {b.get('correct', '-')} | {n.get('correct', '-')} |")

    nav_fail = [r for r in result.get("rows", []) if r["mode"] == "navigator" and not r["correct_current"]]
    lines += ["", "## Navigator misses (reported honestly)", ""]
    if nav_fail:
        for r in nav_fail:
            lines.append(f"- **{r['id']}** ({r['type']}, {r['user_profile']}) {r['question']} - {r['failure']}")
    else:
        lines.append("- None on this golden set.")
    base_stale = [r for r in result.get("rows", []) if r["mode"] == "baseline" and r["stale_as_current"]]
    if base_stale:
        lines += ["", "## Where the baseline cited a stale rule as current", ""]
        for r in base_stale:
            lines.append(f"- **{r['id']}** {r['question']} - {r['stale_as_current']}")
    if meta.get("problems"):
        lines += ["", "## Golden-set problems", ""] + [f"- {p}" for p in meta["problems"]]

    lines += [
        "",
        "## Method",
        "",
        "- **Corpus:** synthetic documents only (watermarked SINTETIK - CONTOH SAHAJA, fictional issuers): a 3-step "
        "travel-claim chain (SPP 3/2019 cancelled by SPP 1/2023, amended by SPP 2/2025), Federal vs Sarawak child-care "
        "leave, annual leave (PP 2/2018 replaced by PP 3/2024), a one-off emergency WFH instruction, a current hybrid-work "
        "guideline, a cloud guideline pair in English, and one TERHAD and one SULIT document.",
        "- **Golden set:** `data/golden_set.csv`, written by Team MixUp from those documents (Appendix C format): "
        f"{', '.join(f'{v} {k}' for k, v in types.items())}. Each row names the user profile (FED-T0, SWK-T0, FED-T1), "
        "the expected document and clause, and the circulars that must not be cited as current.",
        f"- **Model mode:** {meta.get('llm_label', meta.get('llm_provider', 'offline'))}. In offline mode answers are "
        "deterministic and extractive (BM25 + bilingual glossary retrieval, no LLM), so the run is repeatable.",
        "- **Baseline:** the same retrieval and answer step (`ask(..., mode=\"baseline\")`) with no status filter, no "
        "jurisdiction logic, no amendment handling and no excluded list: what a typical document chatbot does. The clearance "
        "filter lives in the search layer, so it applies to both systems; access leaks are checked independently "
        "(restricted doc ids, circular numbers, titles and any 5-word phrase found only in restricted documents).",
        "- **Definitions:** Recall@5 and MRR use the rank of the first passage from the expected document. Citation "
        "accuracy needs the primary citation [S1] to be the expected document and clause. Cancelled-citation rate counts "
        "trap questions where a must_not_cite document (or amended clause) is cited without a historical/amended label. "
        "Correct & current = right document and clause, answer keywords present, nothing stale presented as current, no "
        "leak; for unanswerable and access questions, a refusal.",
        "- **Isolation:** each run uses a private copy of the base corpus with an empty runtime folder, so live uploads "
        "and the demo query log do not affect the numbers, and the run does not appear in Analytics.",
        "- **Self-measured** by Team MixUp on a laptop (latency includes retrieval and answer generation only). The golden "
        "set is small, so treat the numbers as indicative, not as a benchmark.",
        "- **Reproduce:** `python scripts/evaluate.py` (writes this file, `results.csv` and `results.json`).",
        "",
    ]
    return "\n".join(lines)


def write_results(result: dict, out_dir: str | Path | None = None) -> dict[str, Path]:
    """Write summary.md, results.csv (one row per question x mode) and results.json (for the UI)."""
    out = Path(out_dir or RESULTS_DIR)
    out.mkdir(parents=True, exist_ok=True)
    paths = {"summary": out / "summary.md", "csv": out / "results.csv", "json": out / "results.json"}
    paths["summary"].write_text(summary_markdown(result), encoding="utf-8")
    with paths["csv"].open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(CSV_FIELDS), extrasaction="ignore")
        writer.writeheader()
        for row in result.get("rows", []):
            writer.writerow({k: row.get(k, "") for k in CSV_FIELDS})
    paths["json"].write_text(json.dumps(result, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return paths


def load_cached(out_dir: str | Path | None = None) -> dict | None:
    """The last saved run (results.json), or None."""
    path = Path(out_dir or RESULTS_DIR) / "results.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) and "rows" in data else None
