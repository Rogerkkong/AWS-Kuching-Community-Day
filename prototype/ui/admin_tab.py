"""Feature C - Admin: upload a circular, edit its metadata, verify extracted relations.

Flow on screen: Parse -> Metadata -> Relations -> Save (searchable, statuses unchanged)
-> Verification queue (Approve / Reject / Edit) -> statuses recomputed + alerts.
Only ADMIN and POLICY_OWNER users see the tools; others get a notice.

Contract: render(ctx: ui.common.UIContext) -> None. Session-state keys start with "admin_".
"""

from __future__ import annotations

import hashlib
from datetime import date

import streamlit as st

from mixup import access, admin
from mixup.ingest import chunk_document
from mixup.models import (
    CLASSIFICATION_LABELS,
    DOC_TYPES,
    JURISDICTIONS,
    RELATION_TYPES,
    SERIES,
)
from ui import common

DEMO_FILE = ("upload_demo", "SPP-1-2026.md")
HERO_QUESTION = (
    "Dalam tempoh berapa hari tuntutan perjalanan perlu dikemukakan?",
    "Within how many days must a travel claim be submitted?",
)
STEP_LABELS = {
    "parse": ("1. Hurai fail", "1. Parse"),
    "metadata": ("2. Metadata", "2. Metadata"),
    "relations": ("3. Hubungan", "3. Relations"),
}
RELATION_LABELS = {
    "CANCELS": ("Membatalkan", "Cancels", "red"),
    "SUPERSEDES": ("Menggantikan", "Supersedes", "red"),
    "AMENDS": ("Meminda", "Amends", "orange"),
    "REFERENCES": ("Merujuk", "References", "gray"),
}
EVENT_LABELS = {
    "analyze": ("Analisis", "Analysed"),
    "commit": ("Disimpan", "Saved"),
    "approve": ("Diluluskan", "Approved"),
    "reject": ("Ditolak", "Rejected"),
    "duplicate": ("Pendua", "Duplicate"),
    "error": ("Gagal", "Failed"),
}
SOURCE_LABELS = {"regex": "regex", "llm": "LLM", "metadata.csv": "metadata.csv", "manual": "manual"}
DATE_MIN, DATE_MAX = date(1980, 1, 1), date(2040, 12, 31)


# ----------------------------------------------------------------------------
# Small helpers
# ----------------------------------------------------------------------------


def _relation_badge(rtype: str, lang: str) -> str:
    ms, en, color = RELATION_LABELS.get(rtype, (rtype, rtype, "gray"))
    return f":{color}-badge[{en if lang == 'en' else ms}]"


def _effect_preview(ctx: common.UIContext, rel, source, target) -> str:
    """What approving this relation would do to the target's status."""
    if target is None:
        return ctx.tr("Pekeliling sasaran tiada dalam perpustakaan: tiada status berubah.",
                      "Target circular is not in the library: no status will change.")
    if rel.relation_type in ("CANCELS", "SUPERSEDES"):
        new = f"Dibatalkan oleh {source.label if source else rel.source_doc_id}"
        return ctx.tr(f"Jika diluluskan: {target.label} menjadi **{new}**.",
                      f"If approved: {target.label} becomes **{new}** (cancelled).")
    if rel.relation_type == "AMENDS":
        return ctx.tr(f"Jika diluluskan: {target.label} menjadi Dipinda ({rel.scope}).",
                      f"If approved: {target.label} becomes Amended ({rel.scope}).")
    return ctx.tr("Rujukan sahaja: tiada status berubah.", "Reference only: no status change.")


def _analyze(ctx: common.UIContext, filename: str, data: bytes) -> None:
    """Run admin.analyze_upload and keep the result in session_state."""
    st.session_state.pop("admin_error", None)
    st.session_state.pop("admin_committed", None)
    try:
        with st.spinner(ctx.tr("Menganalisis dokumen...", "Analysing the document...")):
            analysis = admin.analyze_upload(ctx.store, filename, data, ctx.user)
        analysis["form_rev"] = 0
        st.session_state["admin_analysis"] = analysis
    except ValueError as exc:
        st.session_state.pop("admin_analysis", None)
        st.session_state["admin_error"] = str(exc)


def _store_result(ctx: common.UIContext, result: dict, action: str) -> None:
    """Remember the latest decision so the status changes stay on screen after rerun."""
    changes = [
        c for c in result.get("status_changes", [])
        if access.can_see(ctx.user, ctx.store.docs.get(c["doc_id"]))
    ]
    st.session_state.pop("admin_committed", None)
    st.session_state["admin_result"] = {
        "action": action,
        "changes": changes,
        "notifications": len(result.get("notifications", [])),
        "warnings": list(result.get("warnings", [])),
    }


# ----------------------------------------------------------------------------
# Sections
# ----------------------------------------------------------------------------


def _upload_section(ctx: common.UIContext) -> None:
    st.subheader(ctx.tr("Muat naik pekeliling baharu", "Upload a new circular"))
    st.caption(ctx.tr(
        "Hurai -> Metadata -> Hubungan -> Simpan. Dokumen boleh dicari serta-merta, tetapi status pekeliling lain "
        "hanya berubah selepas hubungan diluluskan dalam barisan pengesahan.",
        "Parse -> Metadata -> Relations -> Save. The document is searchable at once, but other circulars' statuses "
        "only change after a relation is approved in the verification queue.",
    ))
    nonce = st.session_state.get("admin_uploader_n", 0)
    left, right = st.columns([3, 2], vertical_alignment="bottom")
    with left:
        upload = st.file_uploader(
            ctx.tr("Fail PDF, DOCX, MD atau TXT", "PDF, DOCX, MD or TXT file"),
            type=["pdf", "docx", "md", "txt"],
            key=f"admin_uploader_{nonce}",
        )
    with right:
        demo = st.button(
            ctx.tr("Guna pekeliling demo SPP 1/2026", "Use demo circular SPP 1/2026"),
            icon=":material/upload_file:", width="stretch", key="admin_demo",
        )
    if demo:
        path = ctx.store.data_dir.joinpath(*DEMO_FILE)
        try:
            _analyze(ctx, path.name, path.read_bytes())
        except OSError:
            st.session_state["admin_error"] = f"Demo file not found: {path}"
    elif upload is not None:
        data = upload.getvalue()
        sha = hashlib.sha256(data).hexdigest()
        if sha != st.session_state.get("admin_upload_sha"):  # analyse each new file once
            st.session_state["admin_upload_sha"] = sha
            _analyze(ctx, upload.name, data)
    if st.session_state.get("admin_error"):
        st.error(ctx.tr("Fail tidak dapat diproses: ", "The file could not be processed: ") + st.session_state["admin_error"])
    committed = st.session_state.get("admin_committed")
    if committed and committed in ctx.store.docs:
        doc = ctx.store.docs[committed]
        st.success(ctx.tr(
            f"{doc.label} disimpan dan kini boleh dicari ({common.status_label(doc.status, 'ms')}). "
            "Status pekeliling lain belum berubah: sahkan hubungan di bawah.",
            f"{doc.label} saved and searchable now ({common.status_label(doc.status, 'en')}). "
            "Other circulars' statuses have not changed yet: verify the relations below.",
        ), icon=":material/task_alt:")


def _steps(ctx: common.UIContext, analysis: dict) -> None:
    cols = st.columns(len(analysis["steps"]))
    for col, step in zip(cols, analysis["steps"]):
        ms, en = STEP_LABELS.get(step["step"], (step["step"], step["step"]))
        icon = ":material/check_circle:" if step["ok"] else ":material/warning:"
        badge = ":green-badge[OK]" if step["ok"] else ctx.tr(":orange-badge[Semak]", ":orange-badge[Check]")
        with col.container(border=True):
            st.markdown(f"{icon} **{en if ctx.lang == 'en' else ms}** {badge}")
            st.caption(step["detail"])


def _metadata_form(ctx: common.UIContext, analysis: dict) -> None:
    """Editable metadata (regex/LLM suggestions; metadata.csv values already applied)."""
    doc = analysis["doc"]
    rev = f"{analysis['sha256'][:8]}_{analysis.get('form_rev', 0)}"
    clusters = sorted({*common.CLUSTER_LABELS, *(d.cluster for d in ctx.store.docs.values() if d.cluster), doc.cluster or ""})
    with st.form(f"admin_meta_form_{rev}"):
        st.markdown(ctx.tr("**Metadata (boleh disunting)**", "**Metadata (editable)**"))
        a, b, c = st.columns(3)
        edits = {
            "circular_no": a.text_input(ctx.t("circular"), doc.circular_no, key=f"admin_f_{rev}_no"),
            "series": b.selectbox("Siri / Series", SERIES, index=SERIES.index(doc.series) if doc.series in SERIES else len(SERIES) - 1,
                                  key=f"admin_f_{rev}_series"),
            "doc_type": c.selectbox(ctx.t("type"), DOC_TYPES, index=DOC_TYPES.index(doc.doc_type) if doc.doc_type in DOC_TYPES else 0,
                                    format_func=lambda t: common.doc_type_label(t, ctx.lang), key=f"admin_f_{rev}_type"),
        }
        edits["title"] = st.text_input(ctx.tr("Tajuk", "Title"), doc.title, key=f"admin_f_{rev}_title")
        a, b = st.columns(2)
        edits["issuer"] = a.text_input(ctx.t("issuer"), doc.issuer, key=f"admin_f_{rev}_issuer")
        edits["source_url"] = b.text_input(ctx.tr("URL sumber", "Source URL"), doc.source_url, key=f"admin_f_{rev}_url")
        a, b, c = st.columns(3)
        edits["jurisdiction"] = a.selectbox(
            ctx.t("jurisdiction"), JURISDICTIONS,
            index=JURISDICTIONS.index(doc.jurisdiction) if doc.jurisdiction in JURISDICTIONS else len(JURISDICTIONS) - 1,
            format_func=lambda j: common.jurisdiction_label(j, ctx.lang), key=f"admin_f_{rev}_jur")
        edits["cluster"] = b.selectbox(ctx.t("cluster"), clusters, index=clusters.index(doc.cluster or ""),
                                       format_func=lambda k: common.cluster_label(k, ctx.lang) if k else "-",
                                       key=f"admin_f_{rev}_cluster")
        edits["classification_level"] = c.selectbox(
            ctx.tr("Klasifikasi", "Classification"), [0, 1, 2], index=min(max(int(doc.classification_level or 0), 0), 2),
            format_func=lambda n: CLASSIFICATION_LABELS[n][1 if ctx.lang == "en" else 0], key=f"admin_f_{rev}_class")
        a, b, c = st.columns(3)
        edits["issue_date"] = a.date_input(ctx.t("issued"), doc.issue_date, min_value=DATE_MIN, max_value=DATE_MAX,
                                           key=f"admin_f_{rev}_issued")
        edits["effective_date"] = b.date_input(ctx.tr("Tarikh kuat kuasa", "Effective date"), doc.effective_date,
                                               min_value=DATE_MIN, max_value=DATE_MAX, key=f"admin_f_{rev}_eff")
        edits["expiry_date"] = c.date_input(ctx.tr("Tarikh tamat (pilihan)", "Expiry date (optional)"), doc.expiry_date,
                                            min_value=DATE_MIN, max_value=DATE_MAX, key=f"admin_f_{rev}_exp")
        a, b = st.columns(2)
        langs = ["ms", "en", "mixed"]
        edits["language"] = a.selectbox(ctx.tr("Bahasa", "Language"), langs,
                                        index=langs.index(doc.language) if doc.language in langs else 0, key=f"admin_f_{rev}_lang")
        edits["one_off"] = b.checkbox(ctx.tr("Arahan sekali sahaja", "One-off instruction"), doc.one_off, key=f"admin_f_{rev}_oneoff")
        edits["applicability"] = st.text_area(ctx.t("applicability"), doc.applicability, height=80, key=f"admin_f_{rev}_appl")
        submitted = st.form_submit_button(ctx.tr("Kemas kini metadata", "Update metadata"), icon=":material/edit:")
    if submitted:
        edits["classification_level"] = int(edits["classification_level"])
        admin.apply_metadata_edits(ctx.store, analysis, edits)
        analysis["form_rev"] = analysis.get("form_rev", 0) + 1
        st.rerun()
    sources = analysis.get("meta_sources", {})
    if sources:
        shown = ", ".join(f"{k}: {SOURCE_LABELS.get(v, v)}" for k, v in sorted(sources.items()))
        st.caption(ctx.tr("Sumber nilai (metadata.csv sentiasa menang): ", "Value sources (metadata.csv always wins): ") + shown)


def _candidates_preview(ctx: common.UIContext, analysis: dict) -> None:
    st.markdown(ctx.tr("**Calon hubungan (belum disahkan)**", "**Relation candidates (unverified)**"))
    if not analysis["candidates"]:
        st.caption(ctx.tr("Tiada rujukan kepada pekeliling lain ditemui.", "No references to other circulars found."))
        return
    for rel in analysis["candidates"]:
        target = access.get_doc(ctx.store, ctx.user, rel.target_doc_id) if rel.target_doc_id else None
        target_text = f"**{target.label}** {common.status_badge(target.status, ctx.lang)}" if target else f"*{rel.target_ref_text}*"
        st.markdown(f"{_relation_badge(rel.relation_type, ctx.lang)} {target_text}  "
                    f":gray[{ctx.t('page')} {rel.evidence_page} | {ctx.tr('keyakinan', 'confidence')} {rel.confidence:.0%}]")
        st.markdown(f"> {rel.evidence_text}")


def _analysis_section(ctx: common.UIContext) -> None:
    analysis = st.session_state.get("admin_analysis")
    if not analysis:
        return
    doc = analysis["doc"]
    with st.container(border=True):
        st.markdown(f"#### {ctx.tr('Hasil analisis', 'Analysis')}: `{analysis['filename']}`")
        _steps(ctx, analysis)
        for warning in analysis.get("warnings", []):
            st.warning(warning, icon=":material/warning:")
        if analysis.get("replaces_upload"):
            st.info(ctx.tr(f"{doc.label} pernah dimuat naik: menyimpan semula akan menggantikannya (keputusan pengesahan dikekalkan).",
                           f"{doc.label} was uploaded before: saving again replaces it (verification decisions are kept)."))
        _metadata_form(ctx, analysis)
        chunks = chunk_document(doc, analysis["page_list"])
        with st.expander(ctx.tr(f"Petikan mengikut klausa ({len(chunks)})", f"Clause-aware chunks ({len(chunks)})")):
            for chunk in chunks[:12]:
                st.markdown(f"`{chunk.breadcrumb}` :gray[{ctx.t('page')} {chunk.page_start}]")
                st.caption(chunk.text[:200])
        _candidates_preview(ctx, analysis)
        if analysis.get("duplicate_of"):
            st.info(ctx.tr("Dokumen ini sudah ada dalam perpustakaan; tiada apa yang akan diubah.",
                           "This document is already in the library; nothing will change."))
        left, right = st.columns(2)
        if left.button(ctx.tr("Simpan & hantar ke barisan pengesahan", "Save & send to verification queue"),
                       type="primary", icon=":material/save:", width="stretch", key="admin_commit",
                       disabled=bool(analysis.get("duplicate_of"))):
            try:
                doc_id = admin.commit_upload(ctx.store, analysis, ctx.user)
            except admin.AdminPermissionError as exc:
                st.error(str(exc))
                return
            st.session_state["admin_committed"] = doc_id
            st.session_state.pop("admin_analysis", None)
            st.session_state.pop("admin_result", None)
            st.session_state["admin_uploader_n"] = st.session_state.get("admin_uploader_n", 0) + 1
            st.rerun()
        if right.button(ctx.tr("Batal", "Discard"), icon=":material/close:", width="stretch", key="admin_discard"):
            st.session_state.pop("admin_analysis", None)
            st.session_state["admin_uploader_n"] = st.session_state.get("admin_uploader_n", 0) + 1
            st.rerun()


def _last_result(ctx: common.UIContext) -> None:
    result = st.session_state.get("admin_result")
    if not result:
        return
    if result["changes"]:
        lines = []
        for c in result["changes"]:
            old = common.status_label(c["old_status"], ctx.lang)
            new = common.status_label(c["new_status"], ctx.lang)
            reason = f" ({c['new_reason']})" if c["new_reason"] else ""
            lines.append(f"- **{c['circular_no']}**: {old} -> {new}{reason}")
        st.success(ctx.tr("Status dikemas kini:", "Statuses updated:") + "\n" + "\n".join(lines), icon=":material/published_with_changes:")
        question = HERO_QUESTION[1] if ctx.lang == "en" else HERO_QUESTION[0]
        st.info(ctx.tr(f"Tanya semula di tab Tanya: \"{question}\" - jawapan kini hanya daripada pekeliling yang berkuat kuasa.",
                       f"Ask again in the Ask tab: \"{question}\" - the answer now uses only circulars in force."),
                icon=":material/lightbulb:")
    elif result["action"] == "reject":
        st.info(ctx.tr("Hubungan ditolak. Tiada status berubah.", "Relation rejected. No status changed."))
    else:
        st.info(ctx.tr("Hubungan diluluskan. Tiada status berubah.", "Relation approved. No status changed."))
    if result["notifications"]:
        st.caption(ctx.tr(f"{result['notifications']} notifikasi dihantar kepada pengikut.",
                          f"{result['notifications']} notification(s) sent to followers."))
    for warning in result["warnings"]:
        st.caption(warning)


def _edit_form(ctx: common.UIContext, rel) -> None:
    """Edit relation type / target / scope / date, then approve."""
    visible = access.visible_docs(ctx.store, ctx.user)
    targets = [""] + sorted(d for d in visible if d != rel.source_doc_id)
    with st.form(f"admin_edit_{rel.relation_id}"):
        rtype = st.selectbox(ctx.tr("Jenis hubungan", "Relation type"), RELATION_TYPES,
                             index=RELATION_TYPES.index(rel.relation_type) if rel.relation_type in RELATION_TYPES else 3,
                             format_func=lambda t: RELATION_LABELS[t][1 if ctx.lang == "en" else 0],
                             key=f"admin_e_{rel.relation_id}_type")
        target = st.selectbox(ctx.tr("Pekeliling sasaran", "Target circular"), targets,
                              index=targets.index(rel.target_doc_id) if rel.target_doc_id in targets else 0,
                              format_func=lambda d: f"{visible[d].label} - {visible[d].title[:50]}" if d else ctx.tr("(tiada dalam perpustakaan)", "(not in library)"),
                              key=f"admin_e_{rel.relation_id}_target")
        scope = st.text_input(ctx.tr("Skop", "Scope"), rel.scope, help="whole | clauses: 4.2", key=f"admin_e_{rel.relation_id}_scope")
        eff = st.date_input(ctx.tr("Tarikh kuat kuasa", "Effective date"), rel.effective_date, min_value=DATE_MIN,
                            max_value=DATE_MAX, key=f"admin_e_{rel.relation_id}_eff")
        saved = st.form_submit_button(ctx.tr("Simpan & luluskan", "Save & approve"), icon=":material/check:")
    if saved:
        edits = {"relation_type": rtype, "target_doc_id": target, "scope": scope, "effective_date": eff}
        try:
            result = admin.verify_relation(ctx.store, rel.relation_id, True, edits, ctx.user)
        except (admin.AdminPermissionError, KeyError, ValueError) as exc:
            st.error(str(exc))
            return
        _store_result(ctx, result, "approve")
        st.rerun()


def _relation_card(ctx: common.UIContext, rel) -> None:
    store = ctx.store
    source = access.get_doc(store, ctx.user, rel.source_doc_id)
    target = access.get_doc(store, ctx.user, rel.target_doc_id) if rel.target_doc_id else None
    with st.container(border=True):
        target_text = (f"**{target.label}** {common.status_badge(target.status, ctx.lang, target.status_reason)}"
                       if target else f"*{rel.target_ref_text}* :gray-badge[{ctx.tr('tiada dalam perpustakaan', 'not in library')}]")
        st.markdown(f"**{source.label if source else rel.source_doc_id}** {_relation_badge(rel.relation_type, ctx.lang)} {target_text}")
        st.caption(
            f"{ctx.t('page')} {rel.evidence_page or '-'} | {ctx.tr('Skop', 'Scope')}: {rel.scope} | "
            f"{ctx.tr('Keyakinan', 'Confidence')}: {rel.confidence:.0%} | {ctx.t('effective')}: {rel.effective_date or '-'} | "
            f"{ctx.tr('Asal', 'Origin')}: {rel.origin}"
        )
        if rel.evidence_text:
            st.markdown(f"> {rel.evidence_text}")
        st.caption(_effect_preview(ctx, rel, source, target))
        a, b, c = st.columns([1, 1, 2])
        approve = a.button(ctx.tr("Luluskan", "Approve"), icon=":material/check:", type="primary",
                           key=f"admin_ok_{rel.relation_id}", width="stretch")
        reject = b.button(ctx.tr("Tolak", "Reject"), icon=":material/close:", key=f"admin_no_{rel.relation_id}", width="stretch")
        with c.popover(ctx.tr("Sunting", "Edit"), icon=":material/edit:", width="stretch"):
            _edit_form(ctx, rel)
    if approve or reject:
        try:
            result = admin.verify_relation(store, rel.relation_id, bool(approve), None, ctx.user)
        except (admin.AdminPermissionError, KeyError, ValueError) as exc:
            st.error(str(exc))
            return
        _store_result(ctx, result, "approve" if approve else "reject")
        st.rerun()


def _queue_section(ctx: common.UIContext) -> None:
    st.subheader(ctx.tr("Barisan pengesahan hubungan", "Relation verification queue"))
    st.caption(ctx.tr("Hanya hubungan yang disahkan mengubah status (guide 7.3).",
                      "Only verified relations change a status (guide 7.3)."))
    pending = admin.pending_relations(ctx.store, ctx.user)
    if not pending:
        st.caption(ctx.tr("Tiada hubungan menunggu pengesahan.", "No relations waiting for verification."))
        return
    by_source: dict[str, list] = {}
    for rel in pending:
        by_source.setdefault(rel.source_doc_id, []).append(rel)
    for source_id, rels in by_source.items():
        source = access.get_doc(ctx.store, ctx.user, source_id)
        head, button = st.columns([3, 1], vertical_alignment="center")
        head.markdown(f"**{source.label if source else source_id}** {source.title if source else ''} "
                      f":gray[({len(rels)} {ctx.tr('calon', 'candidate(s)')})]")
        if len(rels) > 1 and button.button(ctx.tr(f"Luluskan semua ({len(rels)})", f"Approve all ({len(rels)})"),
                                           key=f"admin_all_{source_id}", width="stretch"):
            try:
                result = admin.approve_all(ctx.store, source_id, ctx.user)
            except admin.AdminPermissionError as exc:
                st.error(str(exc))
                return
            _store_result(ctx, result, "approve")
            st.rerun()
        for rel in rels:
            _relation_card(ctx, rel)


def _log_section(ctx: common.UIContext) -> None:
    rows = admin.ingest_log(ctx.store, ctx.user)
    with st.expander(ctx.tr(f"Log pengingesan ({len(rows)})", f"Ingestion log ({len(rows)})"), icon=":material/history:"):
        if not rows:
            st.caption(ctx.tr("Belum ada aktiviti.", "No activity yet."))
            return
        table = [
            {
                ctx.tr("Masa", "Time"): r.get("time", ""),
                ctx.tr("Peristiwa", "Event"): EVENT_LABELS.get(r.get("event"), (r.get("event"),) * 2)[1 if ctx.lang == "en" else 0],
                ctx.tr("Pengguna", "User"): r.get("user_id", ""),
                ctx.tr("Dokumen", "Document"): r.get("doc_id") or r.get("filename", ""),
                ctx.tr("Butiran", "Detail"): r.get("detail", ""),
            }
            for r in rows[:200]
        ]
        st.dataframe(table, hide_index=True, width="stretch")


def _reset_section(ctx: common.UIContext) -> None:
    st.caption(ctx.tr("Set semula demo memadam muat naik, keputusan pengesahan, notifikasi dan log.",
                      "Reset demo deletes uploads, verification decisions, notifications and logs."))
    if st.button(ctx.t("reset_demo"), icon=":material/restart_alt:", key="admin_reset"):
        ctx.store.reset_runtime()
        common.clear_tab_state()
        st.toast(ctx.t("reset_done"))
        st.rerun()


def render(ctx: common.UIContext) -> None:
    """Admin tab: upload, metadata editor, verification queue, ingestion log, reset."""
    if not admin.can_admin(ctx.user):
        st.info(ctx.tr(
            "Tab Pentadbir hanya untuk Admin dan Pemilik Dasar. Tukar pengguna demo di bar sisi.",
            "The Admin tab is for Admin and Policy owner users only. Switch the demo user in the sidebar.",
        ), icon=":material/lock:")
        return
    _upload_section(ctx)
    _analysis_section(ctx)
    st.divider()
    _last_result(ctx)
    _queue_section(ctx)
    st.divider()
    _log_section(ctx)
    _reset_section(ctx)
