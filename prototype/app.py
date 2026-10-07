"""MixUp Navigator by Team MixUp - Streamlit entry point (FAST MODE).

Run:  streamlit run app.py
Each tab lives in ui/<name>_tab.py and exposes render(ctx: ui.common.UIContext).
"""

from __future__ import annotations

import streamlit as st

from mixup import PRODUCT_NAME, TAGLINE_EN, TAGLINE_MS, alerts
from mixup.config import PROVIDERS, load_settings
from mixup.llm import mode_label
from mixup.models import CLASSIFICATION_LABELS
from mixup.store import Store
from ui import admin_tab, analytics_tab, ask_tab, common, eval_tab, library_tab, lineage_tab, packs_tab

st.set_page_config(page_title=PRODUCT_NAME, page_icon=":material/policy:", layout="wide")

TABS = [
    ("Tanya / Ask", ask_tab),
    ("Salasilah & Perubahan / Lineage & Changes", lineage_tab),
    ("Pentadbir / Admin", admin_tab),
    ("Pek / Packs", packs_tab),
    ("Penilaian / Evaluation", eval_tab),
    ("Analitik / Analytics", analytics_tab),
    ("Perpustakaan / Library", library_tab),
]
MODE_COLORS = {"offline": "gray", "ollama": "green", "bedrock": "blue"}


@st.cache_resource(show_spinner="Memuatkan pekeliling / Loading circulars...")
def get_store() -> Store:
    """One Store for the whole app (shared by every browser session)."""
    return Store(load_settings())


def render_sidebar(store: Store) -> common.UIContext:
    """User switcher, BM/EN toggle, model mode, notifications bell, Reset demo."""
    with st.sidebar:
        lang_choice = st.segmented_control(
            "Bahasa / Language", ["BM", "EN"], default="BM", key="app_lang", selection_mode="single"
        )
        lang = "en" if lang_choice == "EN" else "ms"
        ctx_lang = common.UIContext(store=store, user=store.default_user(), lang=lang)

        user_ids = list(store.users)
        user_id = st.selectbox(
            ctx_lang.t("demo_user"),
            user_ids,
            key="app_user_id",
            format_func=lambda uid: store.users[uid].name,
        )
        user = store.users.get(user_id) or store.default_user()
        ctx = common.UIContext(store=store, user=user, lang=lang)
        level = CLASSIFICATION_LABELS.get(user.clearance_level, ("?", "?"))[1 if lang == "en" else 0]
        st.markdown(
            f"{common.jurisdiction_badge(user.jurisdiction, lang)} "
            f"{common.classification_badge(user.clearance_level, lang)}"
        )
        st.caption(
            f"{ctx.t('jurisdiction')}: {common.jurisdiction_label(user.jurisdiction, lang)} | "
            f"{ctx.t('clearance')}: {user.clearance_level} ({level}) | {ctx.t('grade')}: {user.grade or '-'} | {user.role}"
        )

        # Notifications bell
        try:
            notes = alerts.notifications(store, user)
        except Exception:  # the bell must never break the page
            notes = []
        unread = sum(1 for n in notes if not n.get("read"))
        with st.popover(f"{ctx.t('notifications')} ({unread})", icon=":material/notifications:", width="stretch"):
            if not notes:
                st.caption(ctx.t("no_notifications"))
            for n in notes[:10]:
                marker = "" if n.get("read") else "**[baru/new]** "
                summary = n.get("summary_en") if lang == "en" else n.get("summary_ms")
                st.markdown(f"{marker}{n.get('title', '')}")
                if summary:
                    st.caption(summary)
            if unread and st.button(ctx.t("mark_read"), key="app_mark_read"):
                getattr(alerts, "mark_all_read", lambda *_: None)(store, user)
                st.rerun()

        # Model mode
        st.markdown(f"**{ctx.t('llm_mode')}:** :{MODE_COLORS.get(store.llm.provider, 'gray')}-badge[{mode_label(store.llm)}]")
        provider = st.selectbox(
            ctx.t("llm_mode"),
            PROVIDERS,
            index=PROVIDERS.index(store.llm.provider) if store.llm.provider in PROVIDERS else 0,
            key="app_provider",
            label_visibility="collapsed",
            format_func=lambda p: {"offline": "Offline", "ollama": "Ollama (local)", "bedrock": "Claude on Bedrock"}[p],
        )
        if provider == store.llm.provider:
            st.session_state.pop("app_provider_applied", None)
        elif st.session_state.get("app_provider_applied") != provider:  # try once per choice
            store.set_llm_provider(provider)
            st.session_state["app_provider_applied"] = provider
            st.rerun()
        reason = getattr(store.llm, "reason", "") if store.llm.provider == "offline" and provider != "offline" else ""
        if reason or store.llm.last_error:
            st.caption(reason or store.llm.last_error)
        st.caption(f"Hari ini / Today: {store.today.isoformat()}")

        if st.button(ctx.t("reset_demo"), icon=":material/restart_alt:", width="stretch", key="app_reset"):
            store.reset_runtime()
            common.clear_tab_state()
            st.toast(ctx.t("reset_done"))
            st.rerun()
        for problem in store.load_errors:
            st.caption(f"Warning: {problem}")
        st.divider()
        st.caption(ctx.t("synthetic_note"))
        st.caption(ctx.t("sso_note"))
    return ctx


def safe_render(module, ctx: common.UIContext) -> None:
    """Draw one tab; if it crashes, keep the other tabs alive."""
    try:
        module.render(ctx)
    except Exception as exc:  # never let one tab take down the demo
        st.error(ctx.tr(f"Tab ini menghadapi masalah ({type(exc).__name__}).", f"This tab hit a problem ({type(exc).__name__})."))
        with st.expander("Details"):
            st.exception(exc)


def main() -> None:
    store = get_store()
    ctx = render_sidebar(store)
    st.title(PRODUCT_NAME)
    tagline = f"*{TAGLINE_EN}*  \n{TAGLINE_MS}" if ctx.lang == "en" else f"*{TAGLINE_MS}*  \n{TAGLINE_EN}"
    st.markdown(f"{tagline}  \n:gray[{ctx.t('by_team')}]")
    tabs = st.tabs([name for name, _ in TABS])
    for tab, (_, module) in zip(tabs, TABS):
        with tab:
            safe_render(module, ctx)


main()
