"""MixUp Map tab (FEATURE B). STUB created by Foundation; Feature B replaces render().

session_state keys used here start with "map_" (e.g. "map_highlight": doc_id to highlight).
"""

from __future__ import annotations

import streamlit as st

from mixup import graph


def render(ctx) -> None:
    st.subheader("MixUp Map")
    st.caption("How documents relate: supersedes, references, conflicts, discussed in minutes.")
    highlight = st.session_state.get("map_highlight")
    st.graphviz_chart(graph.build_dot(ctx, highlight=highlight), width="stretch")
