"""Ask orchestration: retrieval -> "sources" event -> streamed tokens -> validated "final" event."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterator

from app.config import REFUSAL_MESSAGE
from app.services.analytics.logging import log_query
from app.services.generation import prompts
from app.services.generation.citations import has_valid_citation, parse_actions, validate_answer
from app.services.generation.stream import AnswerStreamParser
from app.services.ingest.chunker import malay_date
from app.services.inference.client import get_client
from app.services.retrieval import filters, hybrid, rerank, rewrite


@dataclass
class Retrieval:
    rq: rewrite.RewrittenQuery
    selected: list[hybrid.Candidate] = field(default_factory=list)
    excluded: list[dict] = field(default_factory=list)
    conflict: bool = False
    rerank_kind: str = "none"
    top_score: float | None = None
    warnings: list[dict] = field(default_factory=list)
    packs: list[dict] = field(default_factory=list)


def retrieve(state, user: dict, question: str, include_historical: bool = False, client=None,
             baseline: bool = False) -> Retrieval:
    """baseline=True reproduces a plain RAG pipeline (no status filter, no jurisdiction logic) for evaluation."""
    settings = state.settings
    client = client or get_client()
    rq = rewrite.rewrite(question, user, client, settings)
    result = Retrieval(rq=rq)
    try:
        qvec = client.embed([rq.embedding_text()])[0]
    except Exception as exc:  # noqa: BLE001
        qvec = None
        result.warnings.append({"code": "embedding_failed", "message": f"Carian vektor tidak tersedia: {exc}"})
    clearance = int(user["clearance_level"])
    statuses = filters.ALL_STATUSES if baseline else filters.allowed_statuses(include_historical, rq.wants_history)
    with filters.open_packs(state, user) as (handles, warnings):
        result.warnings += warnings
        result.packs = [{"tier": h.tier, "version": h.version} for h in handles]
        if not handles:
            return result
        candidates = hybrid.search(handles, rq, qvec, statuses, clearance, settings)
        try:
            ranked, kind = rerank.rerank(rq.rerank_text(), candidates, client, settings, handles, qvec)
        except Exception as exc:  # noqa: BLE001 - reranker failure: keep fused order
            ranked, kind = candidates[: settings.rerank_candidates], "none"
            for c in ranked:
                c.score = c.rrf
            result.warnings.append({"code": "rerank_failed", "message": str(exc)})
        result.rerank_kind = kind
        strong = settings.confidence_thresholds.get(kind, settings.confidence_thresholds["none"])["medium"]
        floor = settings.min_source_score.get(kind, 0.0)
        ranked = [c for c in ranked if c.score >= floor]
        if baseline:
            result.selected = ranked[: settings.context_passages]
        else:
            result.selected, result.conflict = hybrid.apply_jurisdiction(
                ranked, user, rq, settings.context_passages, strong, settings.conflict_ratio)
            result.selected = hybrid.inject_amendments(handles, result.selected, statuses, clearance,
                                                       settings.context_passages)
            if not include_historical and not rq.wants_history and result.selected:
                excluded = hybrid.excluded_candidates(handles, rq, qvec, clearance, settings, statuses)
                if excluded:
                    # Only report cancelled documents that are genuinely relevant to this question.
                    scored, _ = rerank.rerank(rq.rerank_text(), excluded, client, settings, handles, qvec)
                    bar = max(strong, 0.6 * max(c.score for c in result.selected))
                    result.excluded = [hybrid.excluded_payload(c) for c in scored if c.score >= bar]
    result.top_score = max((c.score for c in result.selected), default=None)
    return result


def source_payload(r: Retrieval) -> list[dict]:
    out = []
    for i, c in enumerate(r.selected, start=1):
        ch = c.chunk
        out.append({
            "id": f"S{i}", "n": i, "chunk_id": ch["chunk_id"], "document_id": ch["document_id"],
            "circular_no": ch["circular_no"], "title": ch["title"], "doc_type": ch["doc_type"],
            "jurisdiction": ch["jurisdiction"], "status": ch["status"], "status_reason": ch["status_reason"],
            "issue_date": ch["issue_date"], "effective_date": ch["effective_date"], "clause_ref": ch["clause_ref"],
            "breadcrumb": ch["breadcrumb"], "page": ch["page_start"], "page_end": ch["page_end"], "text": ch["text"],
            "score": round(c.score, 4), "role": c.role, "tier": ch["classification_level"],
        })
    return out


def build_messages(user: dict, question: str, sources: list[dict], hide_status: bool = False) -> list[dict]:
    """hide_status=True is the evaluation baseline: a plain RAG pipeline that knows nothing about validity."""
    blocks = []
    for s in sources:
        status = s["status"]
        if status in ("CANCELLED", "AMENDED", "ONE_OFF") and s.get("status_reason"):
            status = f"{status} ({s['status_reason']})"
        if hide_status:
            status = "-"
        blocks.append(prompts.ANSWER_PASSAGE.format(
            n=s["n"], doc_no=s["circular_no"], title=s["title"], doc_type=s["doc_type"], doc_jurisdiction=s["jurisdiction"],
            status=status, date=malay_date(s.get("issue_date")), clause_ref=s["clause_ref"], page=s["page"],
            passage_text=s["text"]))
    return [{"role": "system", "content": prompts.ANSWER_SYSTEM},
            {"role": "user", "content": prompts.ANSWER_USER.format(
                jurisdiction=user.get("jurisdiction"), grade=user.get("grade") or "tidak dinyatakan",
                scheme=user.get("scheme") or "tidak dinyatakan", question=question, context="\n\n".join(blocks))}]


def comparison_payload(sources: list[dict], user: dict, r: Retrieval) -> dict | None:
    if not r.conflict:
        return None
    target = r.rq.jurisdiction_hint or user.get("jurisdiction") or "FEDERAL"
    mine = next((s for s in sources if s["role"] == "primary" and s["doc_type"] not in ("minutes", "report")), None)
    other = next((s for s in sources if s["role"] == "comparison"), None)
    if not mine or not other:
        return None
    return {"user_jurisdiction": target, "mine": mine["id"], "other": other["id"]}


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def ask_events(state, user: dict, question: str, include_historical: bool = False, baseline: bool = False,
               log: bool = True) -> Iterator[str]:
    """Never ends silently: any unexpected failure becomes an "error" event and a traceback in the server log."""
    try:
        yield from _ask_events(state, user, question, include_historical, baseline, log)
    except Exception as exc:  # noqa: BLE001
        import traceback

        traceback.print_exc()
        yield sse("error", {"message": f"Ralat pelayan / Server error: {type(exc).__name__}: {exc}"})


def _ask_events(state, user: dict, question: str, include_historical: bool, baseline: bool,
                log: bool) -> Iterator[str]:
    settings = state.settings
    client = get_client()
    t0 = time.perf_counter()
    try:
        r = retrieve(state, user, question, include_historical, client, baseline=baseline)
    except Exception as exc:  # noqa: BLE001
        import traceback

        traceback.print_exc()
        yield sse("error", {"message": f"Carian gagal / Search failed: {type(exc).__name__}: {exc}"})
        return
    sources = source_payload(r)
    sources_ms = int((time.perf_counter() - t0) * 1000)
    conf = rerank.confidence(r.top_score, r.rerank_kind, settings)
    yield sse("sources", {
        "sources": sources, "excluded": r.excluded, "jurisdiction_conflict": r.conflict,
        "comparison": comparison_payload(sources, user, r), "confidence": conf, "rerank": r.rerank_kind,
        "warnings": r.warnings, "packs": r.packs, "sources_ms": sources_ms,
        "rewritten": {"queries_ms": r.rq.queries_ms, "queries_en": r.rq.queries_en, "refs": r.rq.circular_refs,
                      "topic": r.rq.topic, "wants_history": r.rq.wants_history, "source": r.rq.source},
        "include_historical": include_historical or r.rq.wants_history,
    })

    valid = {s["n"] for s in sources}
    answer, actions, used, answerable, warnings = REFUSAL_MESSAGE, [], [], False, list(r.warnings)
    if not r.packs:
        warnings.append({"code": "no_packs", "message": "Tiada pek pengetahuan dipasang / No knowledge pack installed."})
    elif sources:
        parser = AnswerStreamParser()
        try:
            for piece in client.chat_stream(build_messages(user, question, sources, hide_status=baseline),
                                            max_tokens=settings.answer_max_tokens):
                for section, text in parser.feed(piece):
                    yield sse("token", {"section": section, "text": text})
                if parser.answerable is False:
                    break
            for section, text in parser.finish():
                yield sse("token", {"section": section, "text": text})
            if parser.answerable:
                clean, used, _removed = validate_answer(parser.answer_text, valid)
                actions = parse_actions(parser.actions_text, valid)
                if clean and has_valid_citation(clean, valid):
                    answer, answerable = clean, True
                else:
                    actions, used = [], []
        except Exception as exc:  # noqa: BLE001 - LLM failure: sources stay visible
            warnings.append({"code": "llm_failed",
                             "message": f"Model bahasa gagal menjana jawapan; sila semak sumber di bawah. / "
                                        f"The language model failed; please read the sources. ({exc})"})
            answer = None
    total_ms = int((time.perf_counter() - t0) * 1000)
    if not answerable:
        conf = "LOW"
    log_id = None
    if log:
        try:
            log_id = log_query(state, user, question, r, answerable, conf, total_ms, sources_ms)
        except Exception:  # noqa: BLE001
            log_id = None
    yield sse("final", {
        "answer": answer, "answerable": answerable, "refusal": (answer == REFUSAL_MESSAGE),
        "citations": [f"S{n}" for n in used], "actions": actions, "confidence": conf,
        "query_log_id": log_id, "warnings": warnings, "sources_ms": sources_ms, "total_ms": total_ms,
        "model": settings.llm_model if settings.inference_backend != "fake" else "fake-extractive",
        "finished_at": datetime.now().isoformat(timespec="seconds"),
    })
