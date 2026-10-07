"""Feature A - Ask (hero flow). STUB created by Foundation; Feature A replaces render().

Contract: render(ctx: ui.common.UIContext) -> None
session_state keys used here must start with "ask_".
"""

from __future__ import annotations

import streamlit as st

from mixup import ask
from ui import common


def render(ctx: common.UIContext) -> None:
    common.stub_notice(ctx, "Feature A - Ask (hero flow)")
    question = st.text_input(ctx.tr("Tanya tentang pekeliling...", "Ask about circulars..."), key="ask_question")
    historical = st.toggle(ctx.tr("Sertakan sejarah", "Include historical"), key="ask_historical")
    if question:
        resp = ask.ask(ctx.store, ctx.user, question, include_historical=historical)
        st.markdown(resp.answer)
        for citation in resp.citations:
            common.source_card(ctx, citation)
