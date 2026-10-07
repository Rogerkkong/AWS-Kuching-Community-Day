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


STYLE = """
<style>
/* MixUp Navigator look: clean cards, purple accent (matches the pitch deck) */
#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"] {visibility: hidden; height: 0;}
.block-container {padding-top: 1.2rem; padding-bottom: 3rem; max-width: 1180px;}
html, body, [class*="css"] {font-family: Inter, -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;}
.mx-hero {display: flex; justify-content: space-between; align-items: flex-end; gap: 1rem;
  padding: 1.4rem 1.6rem; border-radius: 1rem; margin-bottom: 1rem;
  background: linear-gradient(135deg, #1E1B4B 0%, #4C1D95 60%, #6D28D9 100%); color: #fff;}
.mx-brand {display: flex; align-items: center; gap: .7rem;}
.mx-logo {display: inline-flex; align-items: center; justify-content: center; width: 2.4rem; height: 2.4rem;
  border-radius: .6rem; background: #fff; color: #4C1D95; font-weight: 800; letter-spacing: .02em;}
.mx-name {font-size: 2rem; font-weight: 800; letter-spacing: -.02em;}
.mx-tag {margin-top: .5rem; font-size: 1.05rem; font-weight: 600; color: #EDE9FE;}
.mx-tag-sub {font-size: .9rem; color: #C4B5FD; margin-top: .15rem;}
.mx-team {color: #DDD6FE;}
.mx-hero-right {display: flex; flex-direction: column; gap: .4rem; align-items: flex-end;}
.mx-chip {font-size: .78rem; padding: .3rem .7rem; border-radius: 999px; background: rgba(255,255,255,.14);
  border: 1px solid rgba(255,255,255,.25); color: #F5F3FF; white-space: nowrap;}
.mx-chip-ok {background: rgba(16,185,129,.18); border-color: rgba(110,231,183,.5); color: #D1FAE5;}
.stTabs [data-baseweb="tab-list"] {gap: .25rem; border-bottom: 1px solid #E5E7EB;}
.stTabs [data-baseweb="tab"] {padding: .55rem .9rem; border-radius: .6rem .6rem 0 0; font-weight: 600;}
.stTabs [aria-selected="true"] {background: #F5F3FF;}
div[data-testid="stExpander"], div[data-testid="stForm"] {border-radius: .75rem;}
[data-testid="stSidebar"] .stButton button {width: 100%;}
@media (max-width: 800px) {.mx-hero {flex-direction: column; align-items: flex-start;} .mx-hero-right {align-items: flex-start;}}
</style>
"""


def inject_style() -> None:
    st.markdown(STYLE, unsafe_allow_html=True)


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
    inject_style()
    tag_main, tag_sub = (TAGLINE_EN, TAGLINE_MS) if ctx.lang == "en" else (TAGLINE_MS, TAGLINE_EN)
    offline = "Luar talian: semua jawapan dijana pada komputer ini" if ctx.lang == "ms" else "Offline: every answer is produced on this computer"
    st.markdown(
        f"""
<div class="mx-hero">
  <div class="mx-hero-left">
    <div class="mx-brand"><span class="mx-logo">MX</span><span class="mx-name">{PRODUCT_NAME}</span></div>
    <div class="mx-tag">{tag_main}</div>
    <div class="mx-tag-sub">{tag_sub} · <span class="mx-team">{ctx.t('by_team')}</span></div>
  </div>
  <div class="mx-hero-right">
    <span class="mx-chip mx-chip-ok">&#9679; {offline}</span>
    <span class="mx-chip">SINTETIK · CONTOH SAHAJA</span>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
    tabs = st.tabs([name for name, _ in TABS])
    for tab, (_, module) in zip(tabs, TABS):
        with tab:
            safe_render(module, ctx)


main()
