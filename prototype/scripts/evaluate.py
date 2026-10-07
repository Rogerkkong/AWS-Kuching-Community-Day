"""Golden-set evaluation CLI (FEATURE D): Baseline (plain RAG) vs Navigator.

Usage:
    python scripts/evaluate.py                      # offline, writes eval/results/
    python scripts/evaluate.py --provider ollama    # same questions with a local model
    python scripts/evaluate.py --golden data/golden_set.csv --out eval/results --no-write

Writes eval/results/summary.md (comparison table + method note), results.csv (one row per
question and mode) and results.json (read by the Evaluation tab), then prints the table.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mixup import evaluate  # noqa: E402
from mixup.config import PROVIDERS, load_settings  # noqa: E402
from mixup.store import Store  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Baseline vs Navigator on the golden set")
    parser.add_argument("--golden", default=str(evaluate.GOLDEN_PATH), help="golden_set.csv path")
    parser.add_argument("--out", default=str(evaluate.RESULTS_DIR), help="output folder")
    parser.add_argument("--provider", choices=PROVIDERS, default=None, help="override LLM_PROVIDER")
    parser.add_argument("--no-write", action="store_true", help="print only, do not write files")
    args = parser.parse_args(argv)

    settings = load_settings()
    if args.provider:
        settings = settings.with_changes(llm_provider=args.provider)
    store = Store(settings)
    if args.provider and store.llm.provider != args.provider:
        print(f"Note: provider {args.provider!r} unavailable, running {store.llm.provider!r}.", file=sys.stderr)

    result = evaluate.run(store, args.golden)
    meta = result["meta"]
    print(
        f"Golden set: {meta['n_questions']} questions | mode: {meta['llm_label']} | today: {meta['today']} "
        f"| {meta['duration_s']} s\n"
    )
    print(evaluate.text_table(result))
    misses = [r for r in result["rows"] if r["mode"] == "navigator" and not r["correct_current"]]
    if misses:
        print("\nNavigator misses:")
        for r in misses:
            print(f"  {r['id']} [{r['type']}] {r['question']} -> {r['failure']}")
    for problem in meta.get("problems", []):
        print(f"Golden-set problem: {problem}", file=sys.stderr)
    if not args.no_write:
        paths = evaluate.write_results(result, args.out)
        print("\nWrote " + ", ".join(str(p) for p in paths.values()))
    return 1 if result["navigator"].get("access_leaks") else 0


if __name__ == "__main__":
    sys.exit(main())
