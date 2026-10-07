"""FEATURE D - Minutes -> decisions and action items.

STUB created by Foundation. Feature D replaces the body of extract_actions().
"""

from __future__ import annotations

from .context import AppContext


def extract_actions(ctx: AppContext, doc_id: str) -> dict:
    """Return {"decisions": [str], "actions": [{"action","owner","due","related_doc"}], "mode"}."""
    return {"decisions": [], "actions": [], "mode": "offline"}
