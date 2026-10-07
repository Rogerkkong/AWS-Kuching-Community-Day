"""Library tab (Foundation): every document the user may see, with status,
jurisdiction, classification and a source viewer. Access-filtered via
access.visible_docs - restricted documents never appear for low clearance.

session_state keys start with "library_".
"""

from __future__ import annotations

import streamlit as st

from mixup import access
from mixup.models import STATUSES
from ui import common


def render(ctx: common.UIContext) -> None:
    store = ctx.store
    docs = sorted(
        access.visible_docs(store, ctx.user).values(),
        key=lambda d: (d.cluster, d.effective_date or d.issue_date or store.today),
    )
    st.caption(ctx.t("synthetic_note"))

    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
    text = c1.text_input(ctx.t("search_library"), key="library_text").strip().lower()
    all_label = ctx.t("all")
    statuses = c2.selectbox(
        ctx.t("status"), [all_label] + list(STATUSES), key="library_status",
        format_func=lambda s: s if s == all_label else common.status_label(s, ctx.lang),
    )
    clusters = sorted({d.cluster for d in docs if d.cluster})
    cluster = c3.selectbox(
        ctx.t("cluster"), [all_label] + clusters, key="library_cluster",
        format_func=lambda c: c if c == all_label else common.cluster_label(c, ctx.lang),
    )
    jurisdictions = sorted({d.jurisdiction for d in docs})
    jur = c4.selectbox(
        ctx.t("jurisdiction"), [all_label] + jurisdictions, key="library_jur",
        format_func=lambda j: j if j == all_label else common.jurisdiction_label(j, ctx.lang),
    )

    shown = [
        d for d in docs
        if (not text or text in f"{d.title} {d.circular_no} {d.doc_id}".lower())
        and (statuses == all_label or d.status == statuses)
        and (cluster == all_label or d.cluster == cluster)
        and (jur == all_label or d.jurisdiction == jur)
    ]
    st.markdown(f"**{len(shown)}** {ctx.t('documents').lower()}")

    for doc in shown:
        with st.container(border=True):
            st.markdown(
                f"{common.doc_heading(doc, ctx.lang)} {common.jurisdiction_badge(doc.jurisdiction, ctx.lang)} "
                f"{common.classification_badge(doc.classification_level, ctx.lang)}"
            )
            st.caption(common.doc_caption(doc, ctx.lang))
            with st.expander(ctx.t("view_source")):
                if doc.applicability:
                    st.markdown(f"**{ctx.t('applicability')}:** {doc.applicability}")
                if doc.ocr_pages:
                    st.warning(f"{ctx.t('needs_ocr')}: {doc.ocr_pages}")
                common.show_source(ctx, doc.doc_id, 1)
                chunks = access.get_chunks(store, ctx.user, doc.doc_id)
                st.caption(" · ".join(f"{c.clause_ref} (p{c.page_start})" for c in chunks))
