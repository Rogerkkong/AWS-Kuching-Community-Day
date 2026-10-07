"""MixUp - Streamlit entry point.

Run:  streamlit run app.py
Each tab lives in ui/<name>_tab.py and exposes render(ctx).
"""

from __future__ import annotations

import streamlit as st

from mixup.config import Settings, load_settings
from mixup.context import AppContext, build_context
from mixup.llm import LLM, make_llm
from mixup.models import STATUS_IN_FORCE, STATUS_SUPERSEDED
from ui import ask_tab, common, library_tab, map_tab, minutes_tab, upload_tab

st.set_page_config(page_title="MixUp", page_icon=":material/hub:", layout="wide")

TABS = [
    ("Ask", ask_tab),
    ("MixUp Map", map_tab),
    ("Smart Upload", upload_tab),
    ("Minutes & Conflicts", minutes_tab),
    ("Library", library_tab),
]


@st.cache_resource(show_spinner=False)
def _llm_for(settings_key: str, _settings: Settings) -> LLM:
    """One LLM client per distinct settings (Streamlit keeps it between reruns)."""
    return make_llm(_settings)


def current_settings() -> Settings:
    """Settings from env/.env plus any overrides chosen in the sidebar."""
    base = load_settings()
    overrides = st.session_state.get("app_overrides") or {}
    return base.with_changes(**overrides) if overrides else base


def get_context(settings: Settings) -> AppContext:
    """Build the AppContext once per browser session; swap the LLM when settings change."""
    llm = _llm_for(repr(settings), settings)
    ctx = st.session_state.get("app_ctx")
    if ctx is None or ctx.data_dir != settings.data_dir or ctx.settings.embeddings != settings.embeddings:
        with st.spinner("Loading documents..."):
            ctx = build_context(settings, llm=llm)
        st.session_state["app_ctx"] = ctx
    else:
        ctx.settings = settings
        ctx.llm = llm
    return ctx


def render_sidebar(ctx: AppContext, settings: Settings) -> None:
    with st.sidebar:
        st.markdown("### Mode")
        common.mode_banner(ctx)

        st.markdown("### Library")
        docs = list(ctx.docs.values())
        col1, col2 = st.columns(2)
        col1.metric("Documents", len(docs))
        col2.metric("Uploaded", len(ctx.uploaded_ids))
        col1.metric("In force", sum(d.status == STATUS_IN_FORCE for d in docs))
        col2.metric("Superseded", sum(d.status == STATUS_SUPERSEDED for d in docs))
        for problem in ctx.load_errors:
            st.caption(f"Warning: {problem}")

        if st.button("Reset demo", help="Remove uploaded documents and start fresh", width="stretch"):
            ctx.reset_uploads()
            common.clear_tab_state()
            st.toast("Demo reset: uploaded documents removed.")
            st.rerun()

        with st.expander("Settings"):
            offline = st.toggle("Force offline mode", value=settings.offline, help="No AWS calls at all")
            efforts = ["low", "medium", "high"]
            effort = st.selectbox(
                "AI effort for answers",
                efforts,
                index=efforts.index(settings.effort) if settings.effort in efforts else 0,
                help="low = fastest answers",
            )
            cache = st.toggle("Reuse cached AI answers", value=settings.cache, help="Identical questions answer instantly")
            new = {"offline": offline, "effort": effort, "cache": cache}
            old = {"offline": settings.offline, "effort": settings.effort, "cache": settings.cache}
            if new != old:
                st.session_state["app_overrides"] = new
                st.rerun()
            st.caption(f"Model: {settings.model} | Region: {settings.aws_region}")
            if st.button("Test connection", disabled=not ctx.llm.online):
                ok, message = ctx.llm.ping()
                (st.success if ok else st.error)(message)

        st.divider()
        st.caption(common.FICTIONAL_NOTE)


def safe_render(module, ctx: AppContext) -> None:
    """Draw one tab; if it crashes, show a friendly message and keep the others alive."""
    try:
        module.render(ctx)
    except Exception as exc:  # never let one tab take down the demo
        st.error(f"This tab hit a problem ({type(exc).__name__}). The other tabs still work.")
        with st.expander("Details for the team"):
            st.exception(exc)


def main() -> None:
    settings = current_settings()
    ctx = get_context(settings)

    st.title("MixUp")
    st.markdown(
        "**Find the right rule, in the right language, in its latest version.** "
        "Bilingual (BM/EN) answers with sources from government documents."
    )
    render_sidebar(ctx, settings)

    tabs = st.tabs([name for name, _ in TABS])
    for tab, (_, module) in zip(tabs, TABS):
        with tab:
            safe_render(module, ctx)


main()
