"""Notifications bell and subscriptions."""
from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app import db

router = APIRouter(prefix="/api", tags=["alerts"])


@router.get("/alerts")
def alerts(request: Request) -> dict:
    st = request.app.state.pn
    user = st.current_user()
    with st.app_db() as conn:
        items = db.rows(conn.execute(
            "SELECT * FROM notifications WHERE user_id = ? AND (tier IS NULL OR tier <= ?) ORDER BY id DESC LIMIT 50",
            (user["id"], user["clearance_level"])))
    return {"notifications": items, "unread": sum(1 for n in items if not n["read"])}


@router.post("/alerts/{alert_id}/read")
def mark_read(alert_id: int, request: Request) -> dict:
    st = request.app.state.pn
    user = st.current_user()
    with st.app_db() as conn:
        conn.execute("UPDATE notifications SET read = 1 WHERE id = ? AND user_id = ?", (alert_id, user["id"]))
    return {"ok": True}


@router.post("/alerts/read-all")
def mark_all_read(request: Request) -> dict:
    st = request.app.state.pn
    user = st.current_user()
    with st.app_db() as conn:
        conn.execute("UPDATE notifications SET read = 1 WHERE user_id = ?", (user["id"],))
    return {"ok": True}


class SubscriptionBody(BaseModel):
    cluster: str | None = None
    circular_no: str | None = None


@router.get("/subscriptions")
def list_subscriptions(request: Request) -> dict:
    st = request.app.state.pn
    user = st.current_user()
    with st.app_db() as conn:
        return {"subscriptions": db.rows(conn.execute("SELECT * FROM subscriptions WHERE user_id = ?", (user["id"],)))}


@router.post("/subscriptions")
def subscribe(body: SubscriptionBody, request: Request) -> dict:
    if not body.cluster and not body.circular_no:
        raise LookupError("Give a cluster or a circular number")
    st = request.app.state.pn
    user = st.current_user()
    with st.app_db() as conn:
        cur = conn.execute("INSERT INTO subscriptions (user_id, cluster, circular_no) VALUES (?,?,?)",
                           (user["id"], body.cluster, body.circular_no))
    return {"id": cur.lastrowid}


@router.delete("/subscriptions/{sub_id}")
def unsubscribe(sub_id: int, request: Request) -> dict:
    st = request.app.state.pn
    user = st.current_user()
    with st.app_db() as conn:
        conn.execute("DELETE FROM subscriptions WHERE id = ? AND user_id = ?", (sub_id, user["id"]))
    return {"ok": True}
