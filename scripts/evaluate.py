"""Golden-set evaluation: BASELINE (same pipeline, no status filter, no jurisdiction logic, no status in
the prompt) vs NAVIGATOR, in Officer mode against installed packs.

Usage: python scripts/evaluate.py [--golden data/golden_set.csv] [--data-dir DIR] [--source dist_packs]
                                  [--limit N] [--only NAVIGATOR|BASELINE]

By default a fresh temporary Officer data folder is created and the packs in --source are installed
(verified) into it. Writes eval/results/summary.md and eval/results/results.csv.
"""
from __future__ import annotations

import argparse
import csv
import dataclasses
import json
import re
import statistics
import sys
import tempfile
import time
from pathlib import Path

import _bootstrap  # noqa: F401
from app.config import REFUSAL_MESSAGE, get_settings
from app.main import create_app
from app.services.generation.answer import ask_events
from app.services.inference.client import get_client
from app.services.packs.install import install_updates

ROOT = Path(__file__).resolve().parent.parent
PROFILES = {"FED-T0": 1, "SWK-T0": 2, "FED-T1": 3}
REFUSING_TYPES = {"unanswerable", "access"}


def clause_match(expected: str, got: str | None) -> bool:
    if not expected:
        return True
    if not got:
        return False
    if expected == got or got.startswith(expected) or expected.startswith(got + " "):
        return True
    m = re.fullmatch(r"(\d+(?:\.\d+)*)-(\d+(?:\.\d+)*)", got)
    if m and re.fullmatch(r"\d+(?:\.\d+)*", expected):
        key = lambda x: [int(p) for p in x.split(".")]  # noqa: E731
        try:
            return key(m.group(1)) <= key(expected) <= key(m.group(2))
        except ValueError:
            return False
    return expected.split(".")[0] == got.split(".")[0] and "." not in got


def run_question(state, row: dict, baseline: bool) -> dict:
    with state.app_db() as conn:
        user = dict(conn.execute("SELECT * FROM users WHERE id = ?", (PROFILES[row["user_profile"]],)).fetchone())
    t0 = time.perf_counter()
    events = []
    for block in ask_events(state, user, row["question"], baseline=baseline, log=False):
        lines = block.strip().split("\n")
        events.append((lines[0][7:], json.loads(lines[1][6:])))
    elapsed = time.perf_counter() - t0
    sources = events[0][1].get("sources", []) if events and events[0][0] == "sources" else []
    final = events[-1][1] if events and events[-1][0] == "final" else {}
    return {"sources": sources, "final": final, "excluded": events[0][1].get("excluded", []) if events else [],
            "elapsed": elapsed, "user": user}


def score(row: dict, out: dict) -> dict:
    sources, final, user = out["sources"], out["final"], out["user"]
    expected, must_not = row["expected_doc"], row["must_not_cite"]
    by_id = {s["id"]: s for s in sources}
    cited = [by_id[c] for c in final.get("citations", []) if c in by_id]
    answered = bool(final.get("answerable"))
    rank = next((i for i, s in enumerate(sources[:5], 1) if s["circular_no"] == expected), None) if expected else None
    clause_hit = any(s["circular_no"] == expected and clause_match(row["expected_clause"], s["clause_ref"]) for s in sources[:5]) if expected else None
    cited_expected = any(s["circular_no"] == expected for s in cited) if expected else None
    cited_bad = bool(must_not) and any(s["circular_no"] == must_not for s in cited)
    leak = any(s.get("tier", 0) > user["clearance_level"] for s in sources) or \
        (row["type"] == "access" and must_not and must_not in json.dumps(final, ensure_ascii=False))
    actions = final.get("actions") or []
    action_ok = [any(by_id.get(f"S{n}", {}).get("circular_no") == expected for n in a["citations"]) for a in actions]
    answer_text = final.get("answer") or ""
    keywords = [k for k in row["answer_keywords"].split(";") if k and k != "refusal"]
    return {
        "id": row["id"], "type": row["type"], "language": row["language"], "profile": row["user_profile"],
        "answered": answered, "refused": final.get("answer") == REFUSAL_MESSAGE,
        "rank": rank, "recall5": rank is not None if expected else None, "clause_hit": clause_hit,
        "cited_expected": cited_expected, "cited_cancelled": cited_bad, "leak": bool(leak),
        "keywords_ok": all(k.lower() in answer_text.lower() for k in keywords) if keywords and answered else None,
        "actions": len(actions), "actions_ok": sum(action_ok),
        "sources_ms": final.get("sources_ms"), "total_ms": final.get("total_ms"),
        "top": " | ".join(f"{s['circular_no']} {s['clause_ref']} {s['status']}" for s in sources[:3]),
        "excluded": ",".join(e["circular_no"] for e in out["excluded"]),
        "answer": answer_text.replace("\n", " ")[:300],
    }


def pct(xs) -> str:
    xs = [x for x in xs if x is not None]
    return f"{100 * sum(bool(x) for x in xs) / len(xs):.0f}%" if xs else "-"


def summarise(rows: list[dict]) -> dict:
    with_expected = [r for r in rows if r["recall5"] is not None]
    traps = [r for r in rows if r["type"] == "trap_cancelled"]
    refusers = [r for r in rows if r["type"] in REFUSING_TYPES or (r["type"] == "trap_cancelled" and r["recall5"] is None)]
    answerable = [r for r in rows if r["recall5"] is not None]
    actions = [r for r in rows if r["actions"]]
    times_s = [r["sources_ms"] for r in rows if r["sources_ms"] is not None]
    times_t = [r["total_ms"] for r in rows if r["total_ms"] is not None]

    def p(values, q):
        if not values:
            return None
        values = sorted(values)
        return values[min(len(values) - 1, int(round(q * (len(values) - 1))))]

    return {
        "Recall@5 (doc)": pct([r["recall5"] for r in with_expected]),
        "Recall@5 (clause)": pct([r["clause_hit"] for r in with_expected]),
        "MRR": f"{statistics.mean([(1 / r['rank']) if r['rank'] else 0 for r in with_expected]):.2f}" if with_expected else "-",
        "Citation accuracy": pct([r["cited_expected"] for r in answerable if r["answered"]]),
        "Cancelled-citation rate (traps)": pct([r["cited_cancelled"] for r in traps]),
        "Refusal accuracy (should refuse)": pct([r["refused"] for r in refusers]),
        "False refusals (answerable)": pct([r["refused"] for r in answerable]),
        "Action citation accuracy": f"{100 * sum(r['actions_ok'] for r in actions) / max(1, sum(r['actions'] for r in actions)):.0f}%" if actions else "-",
        "Answer keywords present": pct([r["keywords_ok"] for r in rows]),
        "Access leaks": str(sum(r["leak"] for r in rows)),
        "Time to sources p50 / p95 (s)": f"{p(times_s, .5) / 1000:.2f} / {p(times_s, .95) / 1000:.2f}" if times_s else "-",
        "Complete answer p50 / p95 (s)": f"{p(times_t, .5) / 1000:.2f} / {p(times_t, .95) / 1000:.2f}" if times_t else "-",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--golden", default=str(ROOT / "data" / "golden_set.csv"))
    ap.add_argument("--data-dir", default=None, help="use an existing Officer data folder (installed packs)")
    ap.add_argument("--source", default=None, help="pack update source to install from (default dist_packs/)")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--only", choices=["NAVIGATOR", "BASELINE"], default=None)
    args = ap.parse_args()

    base = get_settings()
    tmp = None
    if args.data_dir:
        data_dir = Path(args.data_dir)
    else:
        tmp = tempfile.TemporaryDirectory()
        data_dir = Path(tmp.name)
    settings = dataclasses.replace(base, data_dir=data_dir)
    t_cold = time.perf_counter()
    app = create_app("officer", "eval", settings)
    state = app.state.pn
    if not args.data_dir:
        res = install_updates(state, args.source or str(base.dist_packs_dir))
        failed = [r for r in res.get("results", []) if not r["ok"]]
        if failed or not res.get("results"):
            print("Could not install packs:", failed or res.get("error"))
            return 1
    health = get_client().health()
    if not health.get("reachable"):
        print("Inference backend not reachable:", health.get("detail"))
        return 2
    get_client().warm_up()

    rows = list(csv.DictReader(open(args.golden, encoding="utf-8-sig")))[: args.limit]
    modes = [args.only] if args.only else ["BASELINE", "NAVIGATOR"]
    results: dict[str, list[dict]] = {}
    cold_start = None
    for mode in modes:
        results[mode] = []
        for i, row in enumerate(rows, 1):
            out = run_question(state, row, baseline=(mode == "BASELINE"))
            if cold_start is None:
                cold_start = time.perf_counter() - t_cold
            results[mode].append(score(row, out))
            print(f"[{mode}] {i}/{len(rows)} {row['id']} {out['elapsed']:.1f}s", flush=True)

    summary = {m: summarise(r) for m, r in results.items()}
    out_dir = ROOT / "eval" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "results.csv").open("w", newline="", encoding="utf-8") as f:
        fields = ["mode"] + list(next(iter(results.values()))[0].keys())
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for mode, rs in results.items():
            for r in rs:
                w.writerow({"mode": mode, **r})

    metrics = list(next(iter(summary.values())).keys())
    lines = ["# Evaluation summary", "",
             f"Backend: **{settings.inference_backend}** (chat `{settings.llm_model if settings.inference_backend != 'fake' else 'fake-extractive'}`, "
             f"embeddings `{settings.embedding_model_id}`) · {len(rows)} golden questions · CPU · "
             f"cold start to first answer {cold_start:.1f} s", "",
             "| Metric | " + " | ".join(modes) + " |", "|---|" + "---|" * len(modes)]
    for m in metrics:
        lines.append(f"| {m} | " + " | ".join(summary[mode][m] for mode in modes) + " |")
    lines += ["", "BASELINE = same retrieval and model, but no status filter, no jurisdiction logic and no status in the "
              "prompt (a typical document chatbot). Cancelled-citation rate = trap questions whose answer cites the "
              "cancelled circular. Access leaks must be 0.", ""]
    if settings.inference_backend == "fake":
        lines.append("_Note: the fake backend produces extractive answers without a language model; retrieval, filter, "
                     "citation and access metrics are meaningful, answer-quality metrics are not._")
    (out_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    width = max(len(m) for m in metrics)
    print("\n" + f"{'Metric':<{width}}  " + "  ".join(f"{m:>12}" for m in modes))
    for m in metrics:
        print(f"{m:<{width}}  " + "  ".join(f"{summary[mode][m]:>12}" for mode in modes))
    print(f"\nWrote {out_dir / 'summary.md'} and {out_dir / 'results.csv'}")
    if tmp:
        del app, state
        try:
            tmp.cleanup()
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
