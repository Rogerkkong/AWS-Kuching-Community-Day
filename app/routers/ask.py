"""POST /api/ask -> Server-Sent Events: sources, token..., final."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.services.generation.answer import ask_events

router = APIRouter(prefix="/api", tags=["ask"])


class AskBody(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    include_historical: bool = False


@router.post("/ask")
def ask(body: AskBody, request: Request) -> StreamingResponse:
    st = request.app.state.pn
    user = st.current_user()
    return StreamingResponse(ask_events(st, user, body.query.strip(), body.include_historical),
                             media_type="text/event-stream",
                             headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})
