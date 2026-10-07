"""FEATURE D - golden-set evaluation, baseline vs navigator (FR-19). STUB created by Foundation.

Contract (keep this signature):
    run(store, golden_path) -> {"baseline": metrics, "navigator": metrics, "rows": [...]}

metrics: {"recall_at_5", "mrr", "citation_accuracy", "cancelled_citation_rate",
          "refusal_accuracy", "access_leaks", "latency_p50_ms", "latency_p95_ms", "n"}
Writes eval/results/summary.md and eval/results/results.csv (scripts/evaluate.py is the CLI).
"""

from __future__ import annotations


def run(store, golden_path) -> dict:
    """Stub: Feature D implements the harness."""
    return {"baseline": {}, "navigator": {}, "rows": []}
