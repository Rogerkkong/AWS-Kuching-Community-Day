"""Signed knowledge packs: build, verify, tamper rejection, clearance gating, update diff."""

from mixup import packs


def _user(store, clearance):
    return next(u for u in store.users.values() if u.clearance_level == clearance)


def test_build_signs_one_pack_per_tier(store):
    entries = packs.build_packs(store, 1)
    assert [e["tier"] for e in entries] == [0, 1, 2]
    for e in entries:
        ok, reason = packs.verify_pack(store, store.runtime_dir / packs.DIST_DIR / e["file"], e)
        assert ok, reason
    assert packs.next_version(store) == 2


def test_uncleared_officer_is_never_offered_restricted_packs(store):
    packs.build_packs(store, 1)
    offered = packs.check_updates(store, _user(store, 0))
    assert [e["tier"] for e in offered] == [0]
    offered = packs.check_updates(store, _user(store, 2))
    assert [e["tier"] for e in offered] == [0, 1, 2]


def test_tampered_pack_is_rejected_and_previous_stays(store):
    user = _user(store, 0)
    [v1] = [e for e in packs.build_packs(store, 1) if e["tier"] == 0]
    assert packs.install_update(store, user, v1)["ok"]
    [v2] = [e for e in packs.build_packs(store, 2) if e["tier"] == 0]
    bad = packs.tampered_copy(store, v2)
    result = packs.install_update(store, user, v2, source_path=bad)
    assert not result["ok"] and "SHA-256" in result["reason"]
    assert packs.installed(store)["0"]["version"] == 1  # rollback: v1 still active


def test_forged_signature_is_rejected(store):
    user = _user(store, 0)
    [v1] = [e for e in packs.build_packs(store, 1) if e["tier"] == 0]
    forged = dict(v1, signature=v1["signature"][:-4] + "AAAA")
    result = packs.install_update(store, user, forged)
    assert not result["ok"] and "Ed25519" in result["reason"]


def test_update_diff_creates_status_change_notifications(store):
    from mixup import alerts

    user = _user(store, 0)
    [v1] = [e for e in packs.build_packs(store, 1) if e["tier"] == 0]
    packs.install_update(store, user, v1)
    # A newly verified cancellation changes a status; the next pack must report it.
    victim = next(d for d in store.docs.values() if d.classification_level == 0 and d.status == "IN_FORCE")
    victim.status, victim.status_reason = "CANCELLED", "Dibatalkan oleh TEST 1/2026"
    [v2] = [e for e in packs.build_packs(store, 2) if e["tier"] == 0]
    result = packs.install_update(store, user, v2)
    assert result["ok"]
    assert any(c["doc_id"] == victim.doc_id and c["to"] == "CANCELLED" for c in result["diff"]["status_changes"])
    titles = [n["title"] for n in alerts.notifications(store, user)]
    assert any(victim.circular_no in t and "CANCELLED" in t for t in titles)
