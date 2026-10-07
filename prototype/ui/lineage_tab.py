"""Feature B - Lineage, what changed, alerts (guide 7.7, FR-10 / FR-12 / FR-13).

render(ctx): document picker -> lineage graph + timeline (status badges, evidence quotes)
-> "What changed?" pair picker -> BM/EN summaries + side-by-side clause diff -> follow buttons.

Hand-off from the Ask tab (set before or while this tab renders):
    st.session_state["lineage_focus_doc"] = "SPP-1-2023"                 # or "ask_lineage_doc"
    st.session_state["lineage_focus_pair"] = ("SPP-3-2019", "SPP-1-2023") # optional, or "old|new"
session_state keys used here start with "lineage_".
"""

from __future__ import annotations

import html

import streamlit as st

from mixup import access, alerts, changes, lineage
from mixup.llm import PROVIDER_LABELS
from ui import common

DEFAULT_DOC = "SPP-3-2019"  # hero chain of the demo
CUSTOM = "__custom__"
FOCUS_DOC_KEYS = ("lineage_focus_doc", "ask_lineage_doc", "ask_focus_doc")
FOCUS_PAIR_KEYS = ("lineage_focus_pair", "ask_lineage_pair")
TAG_COLOURS = {  # diff row type -> (background, text)
    "ADDED": ("rgba(46,125,50,.18)", "#2e7d32"),
    "REMOVED": ("rgba(198,40,40,.16)", "#c62828"),
    "CHANGED": ("rgba(178,106,0,.18)", "#b26a00"),
    "SAME": ("rgba(128,128,128,.15)", "inherit"),
}
DIFF_CSS = """
<style>
.pn-diff {width:100%; border-collapse:collapse; font-size:0.92em; margin-top:4px}
.pn-diff th, .pn-diff td {border:1px solid rgba(128,128,128,.35); padding:6px 8px; vertical-align:top; text-align:left}
.pn-diff th {background:rgba(128,128,128,.10)}
.pn-del {background:rgba(198,40,40,.18); text-decoration:line-through; color:inherit}
.pn-ins {background:rgba(46,125,50,.22); text-decoration:underline; color:inherit}
.pn-tag {font-weight:600; padding:1px 6px; border-radius:4px; font-size:0.85em; white-space:nowrap}
</style>
"""


# ---------------------------------------------------------------------------- helpers


def _pair_key(old_id: str, new_id: str) -> str:
    return f"{old_id}|{new_id}"


def _set_doc(doc_id: str) -> None:
    """Button callback: focus another document (runs before the widgets are drawn)."""
    st.session_state["lineage_doc"] = doc_id


def _open_pair(doc_id: str, old_id: str, new_id: str) -> None:
    st.session_state["lineage_doc"] = doc_id
    st.session_state[f"lineage_pair_{doc_id}"] = _pair_key(old_id, new_id)


def _toggle_follow(store, user_id: str, cluster, doc_id, following: bool) -> None:
    if following:
        alerts.unsubscribe(store, user_id, cluster=cluster, doc_id=doc_id)
    else:
        alerts.subscribe(store, user_id, cluster=cluster, doc_id=doc_id)


def _as_pair(value):
    if isinstance(value, str) and "|" in value:
        value = value.split("|", 1)
    return tuple(value) if value and len(value) == 2 else None


def _apply_focus(options: list[str]) -> None:
    """Pre-select the document / pair the Ask tab asked for.

    lineage_focus_doc / lineage_focus_pair are consumed (popped) so every click applies;
    ask_* keys belong to the Ask tab, so they are applied once per distinct value.
    """
    doc, pair = st.session_state.pop("lineage_focus_doc", None), _as_pair(st.session_state.pop("lineage_focus_pair", None))
    if not (doc or pair):
        doc = next((st.session_state.get(k) for k in FOCUS_DOC_KEYS[1:] if st.session_state.get(k)), None)
        pair = _as_pair(next((st.session_state.get(k) for k in FOCUS_PAIR_KEYS[1:] if st.session_state.get(k)), None))
        request = (doc, pair)
        if request == (None, None) or st.session_state.get("lineage_focus_applied") == request:
            return
        st.session_state["lineage_focus_applied"] = request
    target = doc if doc in options else (pair[0] if pair and pair[0] in options else None)
    if target:
        st.session_state["lineage_doc"] = target
        if pair:
            st.session_state[f"lineage_pair_{target}"] = _pair_key(pair[0], pair[1])


REASON_EN = (("Dibatalkan oleh", "Cancelled by"), ("Digantikan oleh", "Superseded by"), ("Dipinda oleh", "Amended by"),
             ("Arahan sekali sahaja", "One-off instruction"), ("Tamat tempoh", "Expired"),
             ("Status belum disahkan", "Status not verified"), ("dokumen terhad", "a restricted document"))


def _status_md(status: str, reason: str, lang: str) -> str:
    """Badge (text + colour) plus the reason in the interface language."""
    if lang == "en":
        for ms, en in REASON_EN:
            reason = (reason or "").replace(ms, en)
    badge = common.status_badge(status, lang)
    return f"{badge} {reason}" if reason else badge


def _doc_option_label(store, doc_id: str, lang: str) -> str:
    doc = store.docs[doc_id]
    return f"{doc.label} - {doc.title} [{common.status_label(doc.status, lang)}]"


# ---------------------------------------------------------------------------- sections


def _render_notifications(ctx: common.UIContext) -> None:
    notes = alerts.notifications(ctx.store, ctx.user)
    unread = sum(1 for n in notes if not n.get("read"))
    label = ctx.tr(f"Notifikasi saya ({unread} baharu)", f"My notifications ({unread} new)")
    with st.expander(label, icon=":material/notifications:", expanded=bool(unread)):
        if not notes:
            st.caption(ctx.t("no_notifications"))
        for i, n in enumerate(notes[:10]):
            title = n.get("title_en") if ctx.lang == "en" and n.get("title_en") else n.get("title", "")
            marker = "" if n.get("read") else ":red-badge[" + ctx.tr("Baharu", "New") + "] "
            st.markdown(f"{marker}**{title}**")
            st.caption(n.get("summary_en") if ctx.lang == "en" else n.get("summary_ms"))
            if n.get("doc_id") in ctx.store.docs and n.get("new_doc_id") in ctx.store.docs:
                st.button(
                    ctx.tr("Lihat perubahan", "See what changed"), key=f"lineage_note_{i}_{n.get('id')}",
                    on_click=_open_pair, args=(n["doc_id"], n["doc_id"], n["new_doc_id"]),
                    icon=":material/difference:",
                )
        if unread and st.button(ctx.t("mark_read"), key="lineage_mark_read"):
            alerts.mark_all_read(ctx.store, ctx.user)
            st.rerun()


def _render_follow(ctx: common.UIContext, doc) -> None:
    store, uid = ctx.store, ctx.user.user_id
    c1, c2 = st.columns(2)
    following_doc = alerts.is_following(store, uid, doc_id=doc.doc_id)
    c1.button(
        ctx.tr("Berhenti ikuti dokumen ini", "Unfollow this document") if following_doc
        else ctx.tr("Ikuti dokumen ini", "Follow this document"),
        key="lineage_follow_doc", on_click=_toggle_follow, args=(store, uid, None, doc.doc_id, following_doc),
        icon=":material/notifications_off:" if following_doc else ":material/notification_add:", width="stretch",
    )
    if doc.cluster:
        following_cluster = alerts.is_following(store, uid, cluster=doc.cluster)
        name = common.cluster_label(doc.cluster, ctx.lang)
        c2.button(
            ctx.tr(f"Berhenti ikuti topik: {name}", f"Unfollow topic: {name}") if following_cluster
            else ctx.tr(f"Ikuti topik: {name}", f"Follow topic: {name}"),
            key="lineage_follow_cluster", on_click=_toggle_follow,
            args=(store, uid, doc.cluster, None, following_cluster),
            icon=":material/notifications_off:" if following_cluster else ":material/notification_add:",
            width="stretch",
        )
    st.caption(ctx.tr(
        "Anda akan menerima notifikasi apabila pekeliling baharu meminda atau membatalkan peraturan yang diikuti.",
        "You get a notification when a new circular amends or cancels a rule you follow.",
    ))


def _render_timeline(ctx: common.UIContext, lin: dict, root_id: str) -> None:
    store = ctx.store
    nodes = {n["doc_id"]: n for n in lin["nodes"]}
    st.markdown(f"**{ctx.tr('Garis masa', 'Timeline')}**")
    for n in lin["nodes"]:
        if n.get("hidden"):
            st.markdown(f":material/lock: :gray[{n['label_en'] if ctx.lang == 'en' else n['label']}]")
            continue
        if n.get("external"):
            st.markdown(f":material/help: **{n['label']}** :gray[({ctx.tr('tiada dalam perpustakaan', 'not in the library')})]")
            continue
        with st.container(border=True):
            root = " :blue-badge[" + ctx.tr("Dipilih", "Selected") + "]" if n.get("is_root") else ""
            st.markdown(
                f"**{n['circular_no']}** {n['title']}  \n"
                f"{_status_md(n['status'], n.get('status_reason', ''), ctx.lang)} "
                f"{common.jurisdiction_badge(n['jurisdiction'], ctx.lang)}{root}"
            )
            st.caption(
                f"{ctx.t('issued')}: {n.get('issue_date') or '-'} | {ctx.t('effective')}: {n.get('effective_date') or '-'}"
            )
            for e in lin["edges"]:
                if e["source"] != n["doc_id"] or not e.get("target"):
                    continue
                target = nodes.get(e["target"], {})
                target_label = target.get("circular_no") or (
                    target.get("label_en") if ctx.lang == "en" else target.get("label")
                ) or e["target"]
                verb = lineage.edge_label(e["type"], ctx.lang)
                scope = lineage.scope_label(e.get("scope", ""), ctx.lang)
                flag = "" if e.get("verified") else " :orange-badge[" + ctx.tr("Belum disahkan", "Not verified") + "]"
                page = f" ({ctx.t('page').lower()} {e['page']})" if e.get("page") else ""
                st.markdown(f"&rarr; *{verb}* **{target_label}**{(' - ' + scope) if scope else ''}{page}{flag}")
                if e.get("evidence"):
                    st.caption(f"“{e['evidence']}”")
            b1, b2 = st.columns([1, 2])
            if n["doc_id"] != root_id:
                b1.button(ctx.tr("Fokus", "Focus"), key=f"lineage_focus_btn_{n['doc_id']}", on_click=_set_doc,
                          args=(n["doc_id"],), icon=":material/center_focus_strong:")
            with b2.popover(ctx.tr("Lihat dokumen", "View document"), icon=":material/description:"):
                pages = access.get_pages(store, ctx.user, n["doc_id"])
                if not pages:
                    st.warning(ctx.t("source_hidden"))
                for p in pages:
                    st.markdown(f"**{ctx.t('page')} {p.page_no}** {html.escape(p.heading or '')}")
                    st.text(p.text)


def _diff_table(ctx: common.UIContext, result: dict, show_same: bool) -> str:
    """Side-by-side clause table (HTML; every text fragment is already escaped by changes.py)."""
    old_label = html.escape(result.get("old_label", ""))
    new_label = html.escape(result.get("new_label", ""))
    head = (
        f"<tr><th>{html.escape(ctx.t('clause'))}</th><th>{html.escape(ctx.tr('Perubahan', 'Change'))}</th>"
        f"<th>{old_label}</th><th>{new_label}</th></tr>"
    )
    body = []
    for row in result["aligned"]:
        if row["type"] == "SAME" and not show_same:
            continue
        label, _ = changes.type_label(row["type"], ctx.lang)
        bg, fg = TAG_COLOURS.get(row["type"], TAG_COLOURS["SAME"])
        ref_old, ref_new = html.escape(row["clause_old"] or "-"), html.escape(row["clause_new"] or "-")
        ref = ref_old if ref_old == ref_new else f"{ref_old} &rarr; {ref_new}"
        tag = f"<span class='pn-tag' style='background:{bg};color:{fg}'>{html.escape(label)}</span>"
        old_cell = row["old_html"] if row["type"] != "SAME" else html.escape(row["old_text"])
        new_cell = row["new_html"] if row["type"] != "SAME" else html.escape(row["new_text"])
        if row["type"] == "SAME" and result.get("relation_type") == "AMENDS":
            new_cell = f"<i>{html.escape(ctx.tr('Kekal berkuat kuasa (tidak dipinda)', 'Still in force (not amended)'))}</i>"
        body.append(f"<tr><td>{ref}</td><td>{tag}</td><td>{old_cell}</td><td>{new_cell}</td></tr>")
    if not body:
        body.append(f"<tr><td colspan='4'>{html.escape(ctx.tr('Tiada perbezaan.', 'No differences.'))}</td></tr>")
    return DIFF_CSS + f"<table class='pn-diff'>{head}{''.join(body)}</table>"


def _render_changes(ctx: common.UIContext, lin: dict, doc_id: str, options: list[str]) -> None:
    store = ctx.store
    st.subheader(ctx.tr("Apa yang berubah?", "What changed?"), anchor=False)
    pairs = lineage.change_pairs(lin)
    pair_options = [_pair_key(old, new) for old, new, _, _ in pairs] + [CUSTOM]
    types = {_pair_key(old, new): rtype for old, new, rtype, _ in pairs}
    key = f"lineage_pair_{doc_id}"
    if st.session_state.get(key) not in pair_options:
        st.session_state[key] = pair_options[0]

    def pair_label(value: str) -> str:
        if value == CUSTOM:
            return ctx.tr("Pilih dua dokumen sendiri...", "Pick any two documents...")
        old, new = value.split("|", 1)
        verb = lineage.edge_label(types.get(value, ""), ctx.lang)
        return f"{store.docs[old].label} → {store.docs[new].label} ({store.docs[new].label} {verb} {store.docs[old].label})"

    if not pairs:
        st.caption(ctx.tr("Tiada pindaan atau pembatalan direkodkan untuk dokumen ini.",
                          "No amendment or cancellation is recorded for this document."))
    choice = st.selectbox(ctx.tr("Pasangan versi", "Version pair"), pair_options, key=key, format_func=pair_label)
    if choice == CUSTOM:
        c1, c2 = st.columns(2)
        fmt = lambda d: _doc_option_label(store, d, ctx.lang)  # noqa: E731
        if st.session_state.get("lineage_custom_old") not in options:
            st.session_state["lineage_custom_old"] = doc_id
        if st.session_state.get("lineage_custom_new") not in options:
            cluster = store.docs[doc_id].cluster
            same = [d for d in reversed(options) if d != doc_id and store.docs[d].cluster == cluster]
            st.session_state["lineage_custom_new"] = (same or [d for d in options if d != doc_id] or [doc_id])[0]
        old_id = c1.selectbox(ctx.tr("Versi lama", "Old version"), options, key="lineage_custom_old", format_func=fmt)
        new_id = c2.selectbox(ctx.tr("Versi baharu", "New version"), options, key="lineage_custom_new", format_func=fmt)
    else:
        old_id, new_id = choice.split("|", 1)
    if old_id == new_id:
        st.info(ctx.tr("Pilih dua dokumen yang berbeza.", "Pick two different documents."))
        return

    with st.spinner(ctx.tr("Membandingkan perenggan...", "Comparing clauses...")):
        result = changes.what_changed(store, ctx.user, old_id, new_id)
    for warning in result.get("warnings", []):
        st.warning(warning)
    if not result["aligned"]:
        return

    mode = result.get("mode", "offline")
    mode_text = ctx.tr("Templat luar talian", "Offline template") if mode == "offline" else PROVIDER_LABELS.get(mode, mode)
    old_doc, new_doc = store.docs[old_id], store.docs[new_id]
    st.markdown(
        f"**{old_doc.label}** {common.status_badge(old_doc.status, ctx.lang)} → "
        f"**{new_doc.label}** {common.status_badge(new_doc.status, ctx.lang)}  "
        f":gray-badge[{ctx.tr('Ringkasan', 'Summary')}: {mode_text}]"
    )
    if result.get("highlights"):
        chips = []
        for h in result["highlights"]:
            ref = h["clause_old"] or h["clause_new"]
            old_v, new_v = (h["old_en"], h["new_en"]) if ctx.lang == "en" else (h["old"], h["new"])
            chips.append(f":orange-badge[{ctx.t('clause')} {ref}] ~~{old_v}~~ → **{new_v}**")
        st.markdown("  \n".join(chips))

    first, second = (("summary_en", "English"), ("summary_ms", "Bahasa Melayu")) if ctx.lang == "en" else (
        ("summary_ms", "Bahasa Melayu"), ("summary_en", "English"))
    c1, c2 = st.columns(2)
    for col, (field, title) in zip((c1, c2), (first, second)):
        with col.container(border=True):
            st.markdown(f"**{title}**")
            st.markdown(result.get(field) or "-")
    counts = result.get("counts", {})
    st.caption(
        f"{ctx.t('effective')}: {result.get('effective_date') or '-'} | "
        f"{ctx.tr('Siapa terlibat', 'Who is affected')}: {result.get('who_is_affected')} | "
        + ", ".join(f"{changes.type_label(t, ctx.lang)[0]}: {counts.get(t, 0)}" for t in ("CHANGED", "ADDED", "REMOVED"))
    )
    default_same = result.get("relation_type") == "AMENDS"
    show_same = st.toggle(ctx.tr("Tunjuk perenggan yang tidak berubah", "Show unchanged clauses"),
                          value=default_same, key=f"lineage_show_same_{old_id}_{new_id}")
    st.markdown(_diff_table(ctx, result, show_same), unsafe_allow_html=True)
    st.caption(ctx.tr(
        "Teks dipotong = dibuang (merah); teks bergaris bawah = ditambah (hijau). Perenggan dijajarkan mengikut nombor, "
        "atau persamaan teks jika nombor berubah.",
        "Struck-through text = removed (red); underlined text = added (green). Clauses are aligned by number, "
        "or by text similarity when the numbering changed.",
    ))


# ---------------------------------------------------------------------------- tab


def render(ctx: common.UIContext) -> None:
    store = ctx.store
    visible = access.visible_docs(store, ctx.user)
    if not visible:
        st.info(ctx.tr("Tiada dokumen untuk tahap akses anda.", "No documents at your clearance."))
        return
    options = [d.doc_id for d in sorted(
        visible.values(), key=lambda d: (d.cluster, d.issue_date or d.effective_date or store.today, d.label)
    )]
    _apply_focus(options)
    if st.session_state.get("lineage_doc") not in options:
        st.session_state["lineage_doc"] = DEFAULT_DOC if DEFAULT_DOC in options else options[0]

    _render_notifications(ctx)
    doc_id = st.selectbox(
        ctx.tr("Pilih pekeliling", "Choose a circular"), options, key="lineage_doc",
        format_func=lambda d: _doc_option_label(store, d, ctx.lang),
    )
    doc = access.get_doc(store, ctx.user, doc_id)
    if doc is None:  # defensive: the options are already access-filtered
        st.warning(ctx.t("source_hidden"))
        return
    st.markdown(
        f"{common.doc_heading(doc, ctx.lang)} {common.jurisdiction_badge(doc.jurisdiction, ctx.lang)}"
    )
    reason = lineage.safe_reason(store, ctx.user, doc.status_reason)
    if ctx.lang == "en":
        for ms, en in REASON_EN:
            reason = reason.replace(ms, en)
    st.caption(" | ".join(p for p in (
        reason, common.doc_type_label(doc.doc_type, ctx.lang), common.jurisdiction_label(doc.jurisdiction, ctx.lang),
        f"{ctx.t('effective')} {doc.effective_date or '-'}", doc.issuer) if p))
    _render_follow(ctx, doc)

    st.subheader(ctx.tr("Salasilah", "Lineage"), anchor=False)
    lin = lineage.get_lineage(store, ctx.user, doc_id)
    graph_col, timeline_col = st.columns([3, 2])
    with graph_col:
        if len(lin["nodes"]) > 1:
            st.graphviz_chart(lineage.to_dot(lin, ctx.lang), width="stretch")
        else:
            st.info(ctx.tr("Tiada hubungan direkodkan untuk dokumen ini.", "No relations are recorded for this document."))
        st.caption(ctx.tr(
            "Warna dan label: hijau = Berkuat kuasa, jingga = Dipinda, merah = Dibatalkan, kelabu = Belum disahkan / "
            "Sekali sahaja. Anak panah: dokumen baharu → dokumen yang dibatalkan/dipinda. Garis putus-putus = "
            "belum disahkan; bertitik = rujukan sahaja.",
            "Colour and label: green = In force, amber = Amended, red = Cancelled, grey = Not verified / One-off. "
            "Arrows: newer document → the document it cancels/amends. Dashed = not verified; dotted = reference only.",
        ))
    with timeline_col:
        _render_timeline(ctx, lin, doc_id)

    st.divider()
    _render_changes(ctx, lin, doc_id, options)
