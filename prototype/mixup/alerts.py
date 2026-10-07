"""FEATURE B - subscriptions and in-app alerts (guide 7.7, FR-13).

    subscribe(store, user_id, cluster=None, doc_id=None) -> dict
    unsubscribe(store, user_id, cluster=None, doc_id=None) -> bool
    is_following(store, user_id, cluster=None, doc_id=None) -> bool
    subscriptions(store, user_id=None) -> list[dict]
    on_new_relations(store, relations) -> list[dict]   notifications created
    notifications(store, user) -> list[dict]           newest first, access-filtered
    mark_all_read(store, user); mark_read(store, user, notification_id)

When a verified relation CANCELS, SUPERSEDES or AMENDS document D, every user who follows
D or D's cluster (and may see both documents) gets one notification with the BM/EN summary
from changes.what_changed. Seed (when runtime/subscriptions.json does not exist yet, e.g.
after "Reset demo"): every OFFICER (the Federal and Sarawak officers) follows the
travel-claims cluster, so ingesting SPP 1/2026 lights up their bell.

Notification: {"id", "user_id", "doc_id" (affected D), "new_doc_id", "relation_id", "relation_type",
               "title", "title_en", "summary_ms", "summary_en", "effective_date", "created_at", "read"}
Files: runtime/subscriptions.json, runtime/notifications.json
"""

from __future__ import annotations

import uuid
from datetime import datetime

from . import access, changes
from .models import AMENDS, CANCELS, SUPERSEDES

SUBSCRIPTIONS = "subscriptions.json"
NOTIFICATIONS = "notifications.json"
ALERT_TYPES = (CANCELS, SUPERSEDES, AMENDS)
SEED_CLUSTER = "travel-claims"
SUMMARY_MAX_CHARS = 600
TITLE_VERBS = {
    CANCELS: ("dibatalkan oleh", "cancelled by"),
    SUPERSEDES: ("digantikan oleh", "superseded by"),
    AMENDS: ("dipinda oleh", "amended by"),
}


def _uid(user_or_id) -> str | None:
    return user_or_id if isinstance(user_or_id, str) else getattr(user_or_id, "user_id", None)


def _seed(store) -> list[dict]:
    """Demo seed: Federal and Sarawak officers follow the travel-claims cluster."""
    return [
        {"user_id": u.user_id, "cluster": SEED_CLUSTER, "doc_id": None}
        for u in store.users.values()
        if u.role == "OFFICER" and u.jurisdiction in ("FEDERAL", "SARAWAK")
    ]


def subscriptions(store, user_id: str | None = None) -> list[dict]:
    """All subscriptions (or one user's). Seeds the demo list on first use."""
    subs = store.read_json(SUBSCRIPTIONS, None)
    if subs is None:
        subs = _seed(store)
        store.write_json(SUBSCRIPTIONS, subs)
    return [s for s in subs if user_id is None or s.get("user_id") == user_id]


def _same(sub: dict, user_id: str, cluster: str | None, doc_id: str | None) -> bool:
    return sub.get("user_id") == user_id and sub.get("cluster") == cluster and sub.get("doc_id") == doc_id


def subscribe(store, user_id: str, cluster: str | None = None, doc_id: str | None = None) -> dict:
    """Follow a cluster or a document (idempotent)."""
    user_id = _uid(user_id)
    subs = subscriptions(store)
    sub = {"user_id": user_id, "cluster": cluster or None, "doc_id": doc_id or None}
    if not any(_same(s, user_id, sub["cluster"], sub["doc_id"]) for s in subs):
        subs.append(sub)
        store.write_json(SUBSCRIPTIONS, subs)
    return sub


def unsubscribe(store, user_id: str, cluster: str | None = None, doc_id: str | None = None) -> bool:
    """Stop following; True if something was removed."""
    user_id = _uid(user_id)
    subs = subscriptions(store)
    kept = [s for s in subs if not _same(s, user_id, cluster or None, doc_id or None)]
    if len(kept) != len(subs):
        store.write_json(SUBSCRIPTIONS, kept)
        return True
    return False


def is_following(store, user_id: str, cluster: str | None = None, doc_id: str | None = None) -> bool:
    user_id = _uid(user_id)
    return any(_same(s, user_id, cluster or None, doc_id or None) for s in subscriptions(store))


def followers(store, doc) -> list[str]:
    """user_ids following this document or its cluster (each once, in subscription order)."""
    out: list[str] = []
    for s in subscriptions(store):
        hit = (s.get("doc_id") and s["doc_id"] == doc.doc_id) or (
            s.get("cluster") and doc.cluster and s["cluster"] == doc.cluster and not s.get("doc_id")
        )
        if hit and s.get("user_id") not in out:
            out.append(s["user_id"])
    return out


def _shorten(text: str, limit: int = SUMMARY_MAX_CHARS) -> str:
    text = (text or "").strip()
    return text if len(text) <= limit else text[: limit - 3].rsplit(" ", 1)[0] + "..."


def on_new_relations(store, relations) -> list[dict]:
    """Create notifications for followers of each newly verified CANCELS/SUPERSEDES/AMENDS target.

    Unverified, rejected and REFERENCES relations are ignored. One notification per
    (user, relation); users who may not see both documents get nothing.
    """
    rows = store.read_json(NOTIFICATIONS, []) or []
    seen = {(n.get("user_id"), n.get("relation_id")) for n in rows}
    created: list[dict] = []
    for rel in relations or []:
        if rel is None or rel.relation_type not in ALERT_TYPES or not rel.verified or rel.rejected:
            continue
        target, source = store.docs.get(rel.target_doc_id), store.docs.get(rel.source_doc_id)
        if target is None or source is None:
            continue
        verb_ms, verb_en = TITLE_VERBS[rel.relation_type]
        for user_id in followers(store, target):
            user = store.users.get(user_id)
            if user is None or (user_id, rel.relation_id) in seen:
                continue
            if not (access.can_see(user, target) and access.can_see(user, source)):
                continue
            diff = changes.what_changed(store, user, target.doc_id, source.doc_id)
            note = {
                "id": f"N-{uuid.uuid4().hex[:10]}",
                "user_id": user_id,
                "doc_id": target.doc_id,
                "new_doc_id": source.doc_id,
                "relation_id": rel.relation_id,
                "relation_type": rel.relation_type,
                "title": f"{target.label} {verb_ms} {source.label}",
                "title_en": f"{target.label} {verb_en} {source.label}",
                "summary_ms": _shorten(diff.get("summary_ms", "")),
                "summary_en": _shorten(diff.get("summary_en", "")),
                "effective_date": diff.get("effective_date"),
                "cluster": target.cluster,
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "read": False,
            }
            rows.append(note)
            created.append(note)
            seen.add((user_id, rel.relation_id))
    if created:
        store.write_json(NOTIFICATIONS, rows)
    return created


def notifications(store, user) -> list[dict]:
    """The user's notifications, newest first, only about documents they may see."""
    uid = getattr(user, "user_id", None)
    rows = [n for n in (store.read_json(NOTIFICATIONS, []) or []) if n.get("user_id") == uid]
    rows = [
        n for n in rows
        if access.can_see(user, store.docs.get(n.get("doc_id")))
        and (not n.get("new_doc_id") or access.can_see(user, store.docs.get(n.get("new_doc_id"))))
    ]
    return sorted(rows, key=lambda n: n.get("created_at", ""), reverse=True)


def unread_count(store, user) -> int:
    return sum(1 for n in notifications(store, user) if not n.get("read"))


def mark_all_read(store, user) -> None:
    """Mark every notification of this user as read (sidebar bell)."""
    rows = store.read_json(NOTIFICATIONS, []) or []
    for n in rows:
        if n.get("user_id") == getattr(user, "user_id", None):
            n["read"] = True
    store.write_json(NOTIFICATIONS, rows)


def mark_read(store, user, notification_id: str) -> None:
    rows = store.read_json(NOTIFICATIONS, []) or []
    for n in rows:
        if n.get("id") == notification_id and n.get("user_id") == getattr(user, "user_id", None):
            n["read"] = True
    store.write_json(NOTIFICATIONS, rows)
