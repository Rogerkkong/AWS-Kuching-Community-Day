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
/* MixUp Navigator: paper background, navy accent, serif headline (teammate design) */
#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"] {visibility: hidden; height: 0;}
.block-container {padding-top: 1rem; padding-bottom: 4rem; max-width: 1240px;}
.mx-top {display: flex; justify-content: space-between; align-items: center; gap: 1rem;
  padding: .2rem 0 .8rem 0; border-bottom: 1px solid #DAD5CB; margin-bottom: .6rem;}
.mx-top h1 {font-family: "IBM Plex Sans", system-ui, sans-serif; font-size: 1.25rem; font-weight: 600; margin: 0; color: #1A1D21;}
.mx-top .mx-sub {font-size: .85rem; color: #6B7178; margin-top: .1rem;}
.mx-pills {display: flex; gap: .5rem;}
.mx-pill {font-size: .8rem; padding: .35rem .8rem; border-radius: 999px; background: #fff; border: 1px solid #DAD5CB; color: #5D636B; white-space: nowrap;}
.mx-pill b {color: #1A1D21; font-weight: 600;}
.mx-pill .mx-count {background: #9A241C; color: #fff; border-radius: 999px; padding: .05rem .5rem; font-family: "IBM Plex Mono", monospace; font-size: .75rem; margin-left: .3rem;}
.mx-update {background: #FBF3DF; border: 1px solid #F0DDA8; border-left: 4px solid #E0A93A; color: #3D4247;
  padding: .6rem .9rem; border-radius: .4rem; font-size: .9rem; margin: .2rem 0 1rem 0;}
.mx-update b {color: #7A4F00; margin-right: .6rem;}
.mx-hero h2 {font-family: "IBM Plex Serif", Georgia, "Times New Roman", serif; font-size: 2.1rem; line-height: 1.2; font-weight: 600;
  color: #1A1D21; margin: 1.2rem 0 .6rem 0; max-width: 34rem;}
.mx-hero p {color: #5D636B; font-size: 1rem; max-width: 36rem; line-height: 1.55; margin-bottom: 1rem;}
.mx-kicker {font-family: "IBM Plex Mono", Menlo, monospace; font-size: .72rem; letter-spacing: .12em; text-transform: uppercase; color: #6B7178;}
.mx-brand {padding: .4rem 0 .9rem 0; border-bottom: 1px solid #2C3E48; margin-bottom: .8rem;}
.mx-brand .mx-b1 {font-family: "IBM Plex Serif", Georgia, serif; font-size: 1.6rem; font-weight: 600; color: #FFFFFF; line-height: 1.1;}
.mx-brand .mx-b2 {font-family: "IBM Plex Mono", Menlo, monospace; font-size: .7rem; letter-spacing: .25em; color: #9FB0BA; margin-top: .15rem;}
.mx-statusbar {position: fixed; left: 0; right: 0; bottom: 0; z-index: 999; background: #E9E6E0; border-top: 1px solid #D6D1C7;
  color: #3D4247; font-family: "IBM Plex Mono", Menlo, monospace; font-size: .75rem; padding: .35rem 1.2rem; text-align: right;}
.mx-statusbar .mx-dot {color: #1E6B41; margin-right: .3rem;}
.stTabs [data-baseweb="tab-list"] {gap: .1rem; border-bottom: 1px solid #DAD5CB;}
.stTabs [data-baseweb="tab"] {padding: .5rem .8rem; font-weight: 500; color: #5D636B;}
.stTabs [aria-selected="true"] {color: #1A1D21; font-weight: 600;}
div[data-testid="stExpander"] {background: #FFFFFF; border: 1px solid #DAD5CB; border-radius: .5rem;}
[data-testid="stSidebar"] .stButton button {width: 100%;}
[data-testid="stSidebar"] hr {border-color: #2C3E48;}
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
        st.markdown('<div class="mx-brand"><div class="mx-b1">MixUp</div><div class="mx-b2">NAVIGATOR</div></div>', unsafe_allow_html=True)
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
    notes = alerts.notifications(store, ctx.user)
    unread = sum(1 for n in notes if not n.get("read"))
    jur = common.jurisdiction_label(ctx.user.jurisdiction, ctx.lang)
    t = ctx.tr
    st.markdown(
        f"""
<div class="mx-top">
  <div><h1>{t('Tanya', 'Ask')}</h1><div class="mx-sub">{t('Jawapan dengan petikan daripada pekeliling yang berkuat kuasa', 'Cited answers from circulars in force')}</div></div>
  <div class="mx-pills">
    <span class="mx-pill">{t('Bidang kuasa', 'Jurisdiction')} <b>{jur}</b></span>
    <span class="mx-pill"><b>{t('Notifikasi', 'Notifications')}</b><span class="mx-count">{unread}</span></span>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
    if unread:
        latest = next((n for n in notes if not n.get("read")), {})
        st.markdown(
            f'<div class="mx-update"><b>{t("Kemas kini tersedia", "Update available")}</b>{latest.get("title", "")} · '
            f'{t("ditandatangani oleh penerbit", "signed by the publisher")}</div>',
            unsafe_allow_html=True,
        )
    st.markdown(
        f"""
<div class="mx-hero">
  <h2>{t('Tanya tentang peraturan yang berkuat kuasa hari ini.', 'Ask about the rules in force today.')}</h2>
  <p>{t('Jawapan hanya diambil daripada pekeliling yang masih terpakai, dengan petikan perenggan dan halaman. Pekeliling yang dibatalkan akan dinyatakan, bukan dipetik.',
       'Answers come only from circulars still in force, citing the clause and page. Cancelled circulars are flagged, never quoted.')}</p>
</div>
""",
        unsafe_allow_html=True,
    )
    tabs = st.tabs([name for name, _ in TABS])
    for tab, (_, module) in zip(tabs, TABS):
        with tab:
            safe_render(module, ctx)
    st.markdown(
        f'<div class="mx-statusbar"><span class="mx-dot">&#9679;</span>{t("Rangkaian: luar talian", "Network: offline")} &nbsp;·&nbsp; '
        f'{t("Model", "Model")}: {mode_label(store.llm)} &nbsp;·&nbsp; {t("sedia", "ready")} &nbsp;·&nbsp; {len(store.docs)} {t("pekeliling", "circulars")} '
        f'&nbsp;·&nbsp; {PRODUCT_NAME} · Team MixUp</div>',
        unsafe_allow_html=True,
    )


main()
