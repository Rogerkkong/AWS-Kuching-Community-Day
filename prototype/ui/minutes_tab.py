"""Minutes & Conflicts tab (FEATURE D). STUB created by Foundation; Feature D replaces render().

session_state keys used here start with "minutes_".
"""

from __future__ import annotations

import streamlit as st

from mixup import conflicts, minutes


def render(ctx) -> None:
    st.subheader("Minutes -> Actions")
    minute_ids = [d.doc_id for d in ctx.docs.values() if d.doc_type == "minutes"]
    if minute_ids:
        doc_id = st.selectbox("Meeting minutes", minute_ids, key="minutes_doc")
        if st.button("Extract decisions and actions", key="minutes_extract"):
            st.session_state["minutes_result"] = minutes.extract_actions(ctx, doc_id)
        result = st.session_state.get("minutes_result")
        if result:
            st.write(result)

    st.subheader("Conflict Check")
    in_force = [d.doc_id for d in ctx.in_force_docs()]
    if len(in_force) >= 2:
        col_a, col_b = st.columns(2)
        doc_a = col_a.selectbox("Document A", in_force, key="minutes_conflict_a")
        doc_b = col_b.selectbox("Document B", in_force, index=1, key="minutes_conflict_b")
        if st.button("Check for conflicts", key="minutes_conflict_check"):
            st.session_state["minutes_conflicts"] = conflicts.check(ctx, doc_a, doc_b)
        result = st.session_state.get("minutes_conflicts")
        if result:
            st.write(result)
