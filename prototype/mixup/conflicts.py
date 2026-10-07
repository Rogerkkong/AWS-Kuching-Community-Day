"""FEATURE D - Conflict Check between two in-force documents.

STUB created by Foundation. Feature D replaces check() and find_candidates().
"""

from __future__ import annotations

from .context import AppContext


def check(ctx: AppContext, doc_a: str, doc_b: str) -> dict:
    """Return {"conflicts": [{"topic","doc_a_says","doc_b_says","severity","suggestion"}], "mode"}."""
    return {"conflicts": [], "mode": "offline"}


def find_candidates(ctx: AppContext) -> list[tuple[str, str, str]]:
    """Return [(doc_a, doc_b, reason)] pairs worth checking for conflicts."""
    return []
