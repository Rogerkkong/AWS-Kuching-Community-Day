"""Packs tab: Publisher builds signed packs; Officer checks, verifies and installs updates.

Demonstrates the desktop edition's update mechanism (guide 7.7-7.8) in FAST MODE:
SHA-256 checksum + Ed25519 signature + embedding-model check, atomic install with
rollback, clearance-gated delivery and "what changed" notifications.
"""

from __future__ import annotations

import streamlit as st

from mixup import admin, packs
from mixup.models import CLASSIFICATION_LABELS
from ui import common


def _publisher_section(ctx: common.UIContext) -> None:
    st.subheader(ctx.tr("Penerbit: bina pek bertandatangan", "Publisher: build signed packs"))
    if not admin.can_admin(ctx.user):
        st.caption(ctx.tr(
            "Hanya Admin / Pemilik Dasar boleh membina pek. Tukar pengguna demo di bar sisi.",
            "Only Admin / Policy owner users can build packs. Switch the demo user in the sidebar.",
        ))
        return
    version = packs.next_version(ctx.store)
    st.caption(ctx.tr(
        f"Satu pek SQLite/JSON bagi setiap tahap (Terbuka, Terhad, Sulit) dengan hash SHA-256 dan tandatangan Ed25519. Versi seterusnya: v{version}.",
        f"One pack per clearance tier (Terbuka, Terhad, Sulit) with a SHA-256 hash and an Ed25519 signature. Next version: v{version}.",
    ))
    if st.button(ctx.tr(f"Bina pek v{version}", f"Build packs v{version}"), key="packs_build", type="primary", icon=":material/inventory_2:"):
        entries = packs.build_packs(ctx.store, version)
        st.success(ctx.tr(f"{len(entries)} pek dibina dan ditandatangani.", f"{len(entries)} packs built and signed."))
    manifest = packs.read_manifest(ctx.store).get("packs", [])
    if manifest:
        st.markdown("**manifest.json**")
        st.dataframe(
            [{"tier": CLASSIFICATION_LABELS.get(int(p["tier"]), ("?", "?"))[1 if ctx.lang == "en" else 0],
              "version": p["version"], "file": p["file"], "sha256": p["sha256"][:16] + "...",
              "signature": p["signature"][:12] + "...", "documents": p.get("document_count", "")}
             for p in manifest],
            hide_index=True, width="stretch",
        )


def _officer_section(ctx: common.UIContext) -> None:
    st.subheader(ctx.tr("Pegawai: semak kemas kini", "Officer: check for updates"))
    have = packs.installed(ctx.store)
    cols = st.columns(3)
    for i, tier in enumerate(packs.TIERS):
        label = common.classification_badge(tier, ctx.lang)
        cur = have.get(str(tier))
        allowed = tier <= ctx.user.clearance_level
        with cols[i]:
            st.markdown(label)
            if not allowed:
                st.caption(ctx.tr("Tidak dibenarkan untuk pengguna ini", "Not delivered to this user"))
            elif cur:
                st.caption(f"v{cur['version']} · {cur['installed_at'][:16]}")
            else:
                st.caption(ctx.tr("Belum dipasang", "Not installed"))

    updates = packs.check_updates(ctx.store, ctx.user)
    if updates:
        st.warning(ctx.tr(
            "Kemas kini tersedia: " + ", ".join(f"v{u['version']} ({packs.tier_name(int(u['tier']))})" for u in updates),
            "Update available: " + ", ".join(f"v{u['version']} ({packs.tier_name(int(u['tier']))})" for u in updates),
        ), icon=":material/system_update:")
    c1, c2 = st.columns(2)
    if c1.button(ctx.tr("Semak kemas kini & pasang", "Check for updates & install"), key="packs_check", type="primary", icon=":material/download:"):
        if not updates:
            st.info(ctx.tr("Tiada kemas kini baharu.", "No new updates."))
        for entry in updates:
            result = packs.install_update(ctx.store, ctx.user, entry)
            _show_result(ctx, result)
        if updates:
            st.rerun()
    if updates and c2.button(ctx.tr("Simulasi pek diubah suai (ditolak)", "Simulate tampered pack (rejected)"), key="packs_tamper", icon=":material/gpp_bad:"):
        entry = updates[0]
        bad = packs.tampered_copy(ctx.store, entry)
        _show_result(ctx, packs.install_update(ctx.store, ctx.user, entry, source_path=bad))

    st.caption(ctx.tr(
        "Setiap pek disemak sebelum dipasang: checksum SHA-256, tandatangan Ed25519 penerbit dan model embedding. "
        "Pek yang gagal ditolak dan versi lama kekal aktif. Dalam mod pantas ini, jawapan dibaca terus daripada perpustakaan langsung; "
        "pek menunjukkan mekanisme kemas kini edisi desktop.",
        "Every pack is verified before install: SHA-256 checksum, the publisher's Ed25519 signature and the embedding model. "
        "A failing pack is rejected and the previous version stays active. In this fast mode the answers read the live library; "
        "packs demonstrate the desktop edition's update mechanism.",
    ))


def _show_result(ctx: common.UIContext, result: dict) -> None:
    tier = packs.tier_name(result["tier"])
    if not result["ok"]:
        st.error(ctx.tr(
            f"Pek v{result['version']} ({tier}) DITOLAK: {result['reason']}. Versi sebelumnya kekal aktif.",
            f"Pack v{result['version']} ({tier}) REJECTED: {result['reason']}. The previous version stays active.",
        ), icon=":material/gpp_bad:")
        return
    diff = result["diff"] or {}
    st.success(ctx.tr(
        f"Pek v{result['version']} ({tier}) disahkan dan dipasang.",
        f"Pack v{result['version']} ({tier}) verified and installed.",
    ), icon=":material/verified:")
    changes = diff.get("status_changes", [])
    added = diff.get("added", [])
    if changes or added:
        st.markdown("**" + ctx.tr("Apa yang berubah", "What changed") + "**")
        for c in changes:
            st.markdown(f"- {c['circular_no']}: {common.status_badge(c['from'], ctx.lang)} → {common.status_badge(c['to'], ctx.lang)} {c['reason']}")
        for d in added:
            st.markdown(f"- {ctx.tr('Baharu', 'New')}: {d['circular_no']} — {d['title']}")
        st.caption(ctx.tr("Notifikasi dihantar ke loceng di bar sisi.", "Notifications were sent to the bell in the sidebar."))
    else:
        st.caption(ctx.tr("Tiada perubahan status berbanding versi sebelumnya.", "No status changes compared with the previous version."))


def render(ctx: common.UIContext) -> None:
    """Packs tab: publisher build on the left, officer update on the right."""
    st.caption(ctx.tr(
        "Edisi desktop: pek pengetahuan bertandatangan dihantar melalui folder kongsi, intranet atau USB; pegawai bekerja luar talian.",
        "Desktop edition: signed knowledge packs travel via a shared folder, intranet or USB; officers work offline.",
    ))
    left, right = st.columns(2)
    with left:
        _publisher_section(ctx)
    with right:
        _officer_section(ctx)
