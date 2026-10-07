"""FEATURE A - Ask (hero flow). STUB created by Foundation; Feature A replaces the body.

Contract (keep this signature):
    ask(store, user, question, include_historical=False, mode="navigator") -> AskResponse

mode="navigator": validity filter (IN_FORCE/AMENDED/UNKNOWN), jurisdiction logic,
excluded list, citation validation + refusal. mode="baseline": same retrieval and
answer step but NO status filter and NO jurisdiction logic (plain RAG).

This stub only returns the best passage extractively so the app runs end to end.
"""

from __future__ import annotations

import time

from . import logging as qlog
from .models import DEFAULT_STATUSES, AskResponse, User
from .prompts import REFUSAL
from .search import citation_from_hit, search
from .textutil import detect_language


def ask(store, user: User | None, question: str, include_historical: bool = False, mode: str = "navigator") -> AskResponse:
    """Answer a question from the circulars the user may see (stub: extractive top passage)."""
    start = time.time()
    language = detect_language(question)
    statuses = None if (include_historical or mode == "baseline") else DEFAULT_STATUSES
    hits = search(store, user, question, k=store.settings.top_k, statuses=statuses)
    if not hits or hits[0].coverage < 0.5:
        resp = AskResponse(answer=REFUSAL, language=language, answerable=False, mode=mode, retrieved=hits)
    else:
        top = hits[0]
        cit = citation_from_hit("S1", top)
        resp = AskResponse(
            answer=f"{cit.snippet} [S1]",
            language=language,
            confidence="MEDIUM",
            citations=[cit],
            primary_status=top.doc.status,
            answerable=True,
            mode=mode,
            retrieved=hits,
            warnings=["Stub answer (Feature A not implemented yet)."],
        )
    resp.latency_ms = int((time.time() - start) * 1000)
    resp.query_log_id = qlog.log_query(store, user, {"query": question, "mode": mode, "answerable": resp.answerable})
    return resp
