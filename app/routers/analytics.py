"""Feedback and the opt-in anonymised usage export."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.services.analytics.export import build_report, export_report
from app.services.analytics.logging import record_feedback

router = APIRouter(prefix="/api", tags=["analytics"])


class FeedbackBody(BaseModel):
    query_log_id: int
    rating: Literal["up", "down"]
    comment: str | None = None


@router.post("/feedback")
def feedback(body: FeedbackBody, request: Request) -> dict:
    return {"ok": record_feedback(request.app.state.pn, body.query_log_id, body.rating, body.comment)}


@router.post("/analytics/export")
def export(request: Request) -> dict:
    st = request.app.state.pn
    with st.app_db() as conn:
        path = export_report(conn, st.settings.exports_dir)
        report = build_report(conn)
    return {"path": str(path), "report": report}
