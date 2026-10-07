"""FEATURE B - subscriptions and in-app alerts (FR-13). STUB created by Foundation.

Contract (keep these signatures):
    subscribe(store, user_id, cluster=None, doc_id=None)
    notifications(store, user) -> list[dict]   newest first, access-filtered
    on_new_relations(store, relations) -> list[dict]   notifications created
    mark_all_read(store, user)                 (used by the sidebar bell)

Notification dict: {"id", "user_id", "doc_id", "new_doc_id", "title", "summary_ms",
                    "summary_en", "created_at", "read"}
Files: runtime/subscriptions.json, runtime/notifications.json
"""

from __future__ import annotations

from . import access

SUBSCRIPTIONS = "subscriptions.json"
NOTIFICATIONS = "notifications.json"


def subscribe(store, user_id: str, cluster: str | None = None, doc_id: str | None = None) -> dict:
    """Follow a cluster or a document."""
    subs = store.read_json(SUBSCRIPTIONS, [])
    sub = {"user_id": user_id, "cluster": cluster, "doc_id": doc_id}
    if sub not in subs:
        subs.append(sub)
        store.write_json(SUBSCRIPTIONS, subs)
    return sub


def notifications(store, user) -> list[dict]:
    """The user's notifications, newest first, only about documents they may see."""
    rows = [n for n in store.read_json(NOTIFICATIONS, []) if n.get("user_id") == getattr(user, "user_id", None)]
    rows = [n for n in rows if access.can_see(user, store.docs.get(n.get("doc_id"))) and (
        not n.get("new_doc_id") or access.can_see(user, store.docs.get(n.get("new_doc_id"))))]
    return sorted(rows, key=lambda n: n.get("created_at", ""), reverse=True)


def mark_all_read(store, user) -> None:
    rows = store.read_json(NOTIFICATIONS, [])
    for n in rows:
        if n.get("user_id") == getattr(user, "user_id", None):
            n["read"] = True
    store.write_json(NOTIFICATIONS, rows)


def on_new_relations(store, relations) -> list[dict]:
    """Stub: Feature B creates notifications for subscribers of the affected doc/cluster."""
    return []
