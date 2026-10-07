"""Ask tab (FEATURE A). STUB created by Foundation; Feature A replaces render().

session_state keys used here start with "ask_".
"""

from __future__ import annotations

import streamlit as st

from mixup import answer
from ui import common


def render(ctx) -> None:
    st.subheader("Ask MixUp")
    st.caption("Ask in Bahasa Malaysia, English, or both. Answers come only from the documents.")
    question = st.text_input("Your question", key="ask_question", placeholder="Berapa hari tempoh tuntutan perjalanan?")
    if st.button("Ask", key="ask_button", type="primary") and question.strip():
        st.session_state["ask_answer"] = answer.ask(ctx, question.strip())
    result = st.session_state.get("ask_answer")
    if result is None:
        return
    st.markdown(result.text)
    st.markdown(common.confidence_badge(result.confidence))
    for notice in result.notices:
        st.warning(notice)
    for citation in result.citations:
        common.source_card(citation)
    common.mode_caption(result.mode)
