"""CLI for the golden-set evaluation (FEATURE D). STUB created by Foundation.

Usage:  python scripts/evaluate.py [--golden data/golden_set.csv]
Feature D implements mixup.evaluate.run() and the report writing.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mixup import evaluate  # noqa: E402
from mixup.store import Store  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Baseline vs Navigator on the golden set")
    parser.add_argument("--golden", default=str(ROOT / "data" / "golden_set.csv"))
    args = parser.parse_args()
    result = evaluate.run(Store(), args.golden)
    print(json.dumps({"baseline": result["baseline"], "navigator": result["navigator"]}, indent=2, default=str))


if __name__ == "__main__":
    main()
