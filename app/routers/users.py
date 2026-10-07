"""Demo user profiles and switcher (no passwords; demo only)."""
from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app import db
from app.config import TIER_LABELS

router = APIRouter(prefix="/api/users", tags=["users"])


def _public(u: dict) -> dict:
    return {**u, "clearance_label": TIER_LABELS.get(u["clearance_level"], str(u["clearance_level"]))}


@router.get("")
def list_users(request: Request) -> dict:
    st = request.app.state.pn
    with st.app_db() as conn:
        users = [_public(u) for u in db.rows(conn.execute("SELECT * FROM users ORDER BY id"))]
    if st.mode == "officer":
        users = [u for u in users if u["role"] == "OFFICER"]
    return {"users": users, "current": _public(st.current_user())}


class SwitchBody(BaseModel):
    user_id: int


@router.post("/switch")
def switch_user(body: SwitchBody, request: Request) -> dict:
    st = request.app.state.pn
    with st.app_db() as conn:
        if conn.execute("SELECT 1 FROM users WHERE id = ?", (body.user_id,)).fetchone() is None:
            raise LookupError("Unknown user")
        db.set_setting(conn, "current_user_id", str(body.user_id))
    return {"current": _public(st.current_user())}
