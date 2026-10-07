"""Library tab (FEATURE B). STUB created by Foundation; Feature B replaces render().

session_state keys used here start with "library_".
"""

from __future__ import annotations

import streamlit as st

from ui import common


def render(ctx) -> None:
    st.subheader("Library")
    st.caption(common.FICTIONAL_NOTE)
    for doc in sorted(ctx.docs.values(), key=lambda d: d.date_issued, reverse=True):
        with st.container(border=True):
            st.markdown(common.doc_heading(doc))
            st.caption(common.doc_caption(doc))
            if doc.summary:
                st.write(doc.summary)
