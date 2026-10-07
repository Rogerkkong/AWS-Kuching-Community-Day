"""Feature A - Ask tab (hero flow): question box, example chips, answer card with status badge,
confidence and [S#] source chips, source viewer, "Dikecualikan" notice, Federal / Sarawak
comparison, baseline side by side, lineage / what-changed buttons and feedback.

Contract: render(ctx: ui.common.UIContext) -> None. Session-state keys start with "ask_".
The lineage buttons set the lineage tab's hand-off keys lineage_focus_doc / lineage_focus_pair
and app_tab (switches tabs when app.py uses st.tabs(..., key="app_tab", on_change="rerun")).
"""

from __future__ import annotations

import html

import streamlit as st

from mixup import access, ask
from mixup import logging as qlog
from mixup.llm import PROVIDER_LABELS
from mixup.models import AskResponse, Citation
from ui import common

LINEAGE_TAB = "Salasilah & Perubahan / Lineage & Changes"

# (question, BM label, EN label)
EXAMPLES = [
    ("Berapakah kadar elaun perbatuan untuk tuntutan perjalanan?", "Perangkap: kadar perbatuan", "Trap: mileage rate"),
    ("Berapa lama tempoh untuk mengemukakan tuntutan perjalanan?", "Perangkap: tempoh tuntutan", "Trap: claim deadline"),
    ("How many days of childcare leave can I take?", "Persekutuan vs Sarawak", "Federal vs Sarawak"),
    ("Boleh saya claim mileage kalau guna kereta sendiri?", "Soalan campur BM/EN", "Mixed BM/EN"),
    ("What is the work-from-home policy for private contractors?", "Tiada jawapan", "Unanswerable"),
]


# ----------------------------------------------------------------------------
# Callbacks (run before the next script run, so they may set widget state)
# ----------------------------------------------------------------------------


def _use_example() -> None:
    choice = st.session_state.get("ask_example")
    if choice:
        st.session_state["ask_question"] = choice


def _goto_lineage(doc_id: str, focus: str, pair: tuple[str, str] | None) -> None:
    """Hand-off to the lineage tab (its documented keys), then switch tabs if app.py allows it."""
    st.session_state["lineage_focus_doc"] = doc_id
    if focus == "changes" and pair:
        st.session_state["lineage_focus_pair"] = pair
    else:
        st.session_state.pop("lineage_focus_pair", None)
    st.session_state["app_tab"] = LINEAGE_TAB  # works when app.py uses st.tabs(..., key="app_tab", on_change="rerun")
    st.session_state["ask_goto_notice"] = focus


def _on_thumbs(store, query_log_id: str, user_id: str, key: str) -> None:
    value = st.session_state.get(key)
    if value is not None:
        qlog.add_feedback(store, query_log_id, 1 if value == 1 else -1, user_id=user_id)


def _on_report(store, query_log_id: str, user_id: str, key: str) -> None:
    comment = (st.session_state.get(key) or "").strip()
    qlog.add_feedback(store, query_log_id, 0, comment or "wrong status", kind="wrong_status", user_id=user_id)
    st.session_state[key] = ""
    st.session_state["ask_reported"] = query_log_id


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------


def _safe_md(text: str) -> str:
    """Document text is untrusted: break link/image syntax and LaTeX before st.markdown."""
    return (text or "").replace("](", "]​(").replace("$", "\\$").replace("<", "&lt;")


def _answer_md(text: str) -> str:
    """[S1] -> a small badge so citations stand out."""
    out = _safe_md(text)
    for n in range(1, 21):
        out = out.replace(f"[S{n}]", f" :blue-badge[S{n}]")
    return out


def _cached(name: str, key: tuple, compute):
    """Run ask() once per (question, user, options, model, data revision); reruns reuse it."""
    slot = st.session_state.get(name)
    if slot and slot.get("key") == key:
        return slot["resp"]
    resp = compute()
    st.session_state[name] = {"key": key, "resp": resp}
    return resp


def _citation_label(ctx: common.UIContext, c: Citation) -> str:
    return f"{c.label} · {c.circular_no} · {ctx.t('clause')} {c.clause_ref} · {ctx.t('page')} {c.page} · {common.status_label(c.status, ctx.lang)}"


def _excluded_notice(ctx: common.UIContext, resp: AskResponse) -> None:
    if not resp.excluded:
        return
    st.warning(ask.excluded_line(resp.excluded, ctx.lang), icon=":material/block:")
    with st.expander(ctx.tr("Kenapa dikecualikan?", "Why excluded?")):
        for item in resp.excluded:
            replaced = item.get("replaced_by")
            replaced_txt = ""
            if replaced and replaced in ctx.store.docs and access.get_doc(ctx.store, ctx.user, replaced):
                replaced_txt = f" → {ctx.tr('rujuk', 'see')} **{ctx.store.docs[replaced].label}**"
            st.markdown(
                f"**{item['circular_no']}** {_safe_md(item.get('title', ''))} "
                f"{common.status_badge(item['status'], ctx.lang, item.get('status_reason', ''))}{replaced_txt}"
            )
        st.caption(
            ctx.tr(
                "Dokumen ini akan muncul dalam 10 hasil teratas tanpa penapis status, tetapi tidak lagi berkuat kuasa.",
                "These documents would rank in the top 10 without the status filter, but are no longer in force.",
            )
        )


def _sources(ctx: common.UIContext, resp: AskResponse, kind: str) -> None:
    """Clickable [S#] chips + source viewer with the cited passage highlighted (FR-09)."""
    if not resp.citations:
        return
    by_label = {c.label: c for c in resp.citations}
    key = f"ask_src_{kind}_{resp.query_log_id}"
    choice = st.pills(
        ctx.tr("Sumber (klik untuk lihat)", "Sources (click to view)"),
        options=list(by_label),
        default=resp.citations[0].label,
        format_func=lambda lbl: _citation_label(ctx, by_label[lbl]),
        key=key,
    )
    if choice and choice in by_label:
        _source_viewer(ctx, by_label[choice], f"{kind}_{resp.query_log_id}")


def _source_viewer(ctx: common.UIContext, c: Citation, key: str) -> None:
    """The cited page with the passage highlighted (access-checked; unique widget keys per answer)."""
    doc = access.get_doc(ctx.store, ctx.user, c.doc_id)
    pages = access.get_pages(ctx.store, ctx.user, c.doc_id)
    if doc is None or not pages:
        st.warning(ctx.t("source_hidden"))
        return
    st.markdown(common.doc_heading(doc, ctx.lang))
    st.caption(common.doc_caption(doc, ctx.lang))
    numbers = [p.page_no for p in pages]
    chosen = c.page if c.page in numbers else numbers[0]
    if len(numbers) > 1:
        chosen = st.select_slider(ctx.t("page"), options=numbers, value=chosen, key=f"ask_page_{key}_{c.label}")
    page = next(p for p in pages if p.page_no == chosen)
    passage = ask.source_passage(ctx.store, ctx.user, c) if chosen == c.page else ""
    body = common.highlight(page.text, passage)
    body = "<br>".join(line.lstrip("#").strip() for line in body.split("\n"))
    ocr = f" | {ctx.t('needs_ocr')}" if page.needs_ocr else ""
    st.markdown(
        "<div style='border:1px solid #bbb;border-radius:6px;padding:12px;font-family:Georgia,serif;"
        "background:var(--secondary-background-color, #f7f7f7)'>"
        f"<div style='font-size:0.8em;opacity:0.7'>{html.escape(doc.label)} | {ctx.t('clause')} {html.escape(c.clause_ref)} | "
        f"{ctx.t('page')} {chosen}/{len(numbers)}{ocr}</div>{body}</div>",
        unsafe_allow_html=True,
    )


def _comparison(ctx: common.UIContext, resp: AskResponse) -> None:
    """Federal vs Sarawak side by side, the user's jurisdiction first (FR-11)."""
    comp = resp.comparison
    if not comp:
        return
    st.markdown(f"**{ctx.tr('Perbandingan bidang kuasa', 'Jurisdiction comparison')}**")
    cols = st.columns(2)
    for col, side, mine in ((cols[0], comp["home"], True), (cols[1], comp["other"], False)):
        with col, st.container(border=True):
            tag = ctx.tr("profil anda", "your profile") if mine else ctx.tr("untuk perbandingan", "for comparison")
            st.markdown(f"{common.jurisdiction_badge(side['jurisdiction'], ctx.lang)} _{tag}_")
            if side.get("quantities"):
                st.markdown(f"### {html.escape(side['quantities'][0])}")
            st.markdown(
                f"**{side['circular_no']}** {ctx.t('clause')} {side['clause_ref']}, {ctx.t('page')} {side['page']} "
                f"{common.status_badge(side['status'], ctx.lang)} :blue-badge[{side['label']}]"
            )
            st.markdown(f"> {_safe_md(side['rule'])}")
            if side.get("applicability"):
                st.caption(f"{ctx.t('applicability')}: {_safe_md(side['applicability'])}")
    if comp.get("differs"):
        st.caption(ctx.tr("Peraturan berbeza antara bidang kuasa.", "The rules differ between jurisdictions."))


def _lineage_buttons(ctx: common.UIContext, resp: AskResponse) -> None:
    if not resp.citations:
        return
    primary = resp.citations[0]
    pair = ask.change_pair(ctx.store, ctx.user, primary.doc_id)
    c1, c2, _ = st.columns([1, 1, 2])
    c1.button(
        ctx.tr("Lihat salasilah", "View lineage"), icon=":material/account_tree:", key=f"ask_lin_{resp.query_log_id}",
        on_click=_goto_lineage, args=(primary.doc_id, "lineage", pair), width="stretch",
    )
    c2.button(
        ctx.tr("Apa yang berubah?", "What changed?"), icon=":material/difference:", key=f"ask_chg_{resp.query_log_id}",
        on_click=_goto_lineage, args=(primary.doc_id, "changes", pair), disabled=pair is None, width="stretch",
        help=None if pair else ctx.tr("Tiada versi lain untuk dibandingkan.", "No other version to compare."),
    )


def _feedback(ctx: common.UIContext, resp: AskResponse) -> None:
    """Thumbs up/down and 'report wrong status' (FR-17), stored with the query log."""
    qid = resp.query_log_id
    c1, c2 = st.columns([1, 3])
    with c1:
        fb_key = f"ask_fb_{qid}"
        st.feedback("thumbs", key=fb_key, on_change=_on_thumbs, args=(ctx.store, qid, ctx.user.user_id, fb_key))
    with c2, st.popover(ctx.tr("Laporkan status salah", "Report wrong status"), icon=":material/flag:"):
        rep_key = f"ask_rep_{qid}"
        st.text_input(ctx.tr("Apa yang salah?", "What is wrong?"), key=rep_key)
        st.button(ctx.tr("Hantar", "Send"), key=f"ask_rep_btn_{qid}", on_click=_on_report,
                  args=(ctx.store, qid, ctx.user.user_id, rep_key))
    if st.session_state.get("ask_reported") == qid:
        st.caption(ctx.tr("Terima kasih. Laporan dihantar kepada pemilik dasar.", "Thanks. The report was sent to the policy owner."))


def _answer_card(ctx: common.UIContext, resp: AskResponse, kind: str) -> None:
    """One answer: badges, text, notes, excluded list, sources, comparison, actions."""
    navigator = kind == "nav"
    with st.container(border=True):
        badges = []
        if resp.answerable and resp.primary_status:
            badges.append(common.status_badge(resp.primary_status, ctx.lang))
        badges.append(common.confidence_badge(resp.confidence, ctx.lang))
        if resp.jurisdiction_conflict:
            badges.append(":violet-badge[" + ctx.tr("Persekutuan & Sarawak berbeza", "Federal & Sarawak differ") + "]")
        badges.append(":gray-badge[" + PROVIDER_LABELS.get(resp.llm_mode, resp.llm_mode) + "]")
        st.markdown(" ".join(badges))

        if not resp.answerable:
            st.warning(_safe_md(resp.answer), icon=":material/help:")
        else:
            st.markdown(_answer_md(resp.answer))
            if not navigator:
                cancelled = sorted({c.circular_no for c in resp.citations if c.status in ("CANCELLED", "ONE_OFF")})
                if cancelled:
                    st.error(
                        ctx.tr("Chatbot ini memetik pekeliling yang tidak lagi berkuat kuasa: ",
                               "This chatbot cited circulars that are no longer in force: ") + ", ".join(cancelled),
                        icon=":material/warning:",
                    )
        note = resp.extra.get("jurisdiction_note")
        if note and resp.llm_mode != "offline":  # offline answers already carry the note
            st.info(_safe_md(note), icon=":material/location_on:")
        if navigator:
            _excluded_notice(ctx, resp)
            appl = resp.extra.get("applicability")
            if appl and resp.answerable:
                doc = ctx.store.docs.get(appl["doc_id"])
                where = f"{doc.label if doc else ''} {ctx.t('clause')} {appl.get('clause_ref') or '-'}"
                st.caption(f"{ctx.t('applicability')} ({where}): {_safe_md(appl['text'])}")
        for warning in resp.warnings:
            st.caption(f":orange[{_safe_md(warning)}]")
        st.caption(
            f"ID log: `{resp.query_log_id}` | {resp.latency_ms} ms | "
            + ctx.tr("Bahasa soalan", "Question language") + f": {resp.language}"
        )

    if navigator:
        _comparison(ctx, resp)
    _sources(ctx, resp, kind)
    if navigator and resp.answerable:
        _lineage_buttons(ctx, resp)
    if navigator:
        _feedback(ctx, resp)


# ----------------------------------------------------------------------------
# Tab
# ----------------------------------------------------------------------------


def render(ctx: common.UIContext) -> None:
    store, user = ctx.store, ctx.user
    level = common.CLASSIFICATION_LABELS.get(user.clearance_level, ("?", "?"))[1 if ctx.lang == "en" else 0]
    st.caption(
        ctx.tr("Menjawab untuk", "Answering for")
        + f": **{user.name}** | {common.jurisdiction_label(user.jurisdiction, ctx.lang)} | {level}"
        + (f" | {ctx.t('grade')} {user.grade}" if user.grade else "")
    )

    st.pills(
        ctx.tr("Contoh soalan", "Example questions"),
        options=[q for q, _, _ in EXAMPLES],
        format_func=lambda q: next((en if ctx.lang == "en" else ms) for qq, ms, en in EXAMPLES if qq == q),
        key="ask_example",
        on_change=_use_example,
    )
    c1, c2 = st.columns([5, 1], vertical_alignment="bottom")
    c1.text_input(
        ctx.tr("Soalan anda", "Your question"),
        key="ask_question",
        placeholder="Tanya tentang pekeliling... / Ask about circulars...",
    )
    c2.button(ctx.tr("Tanya", "Ask"), type="primary", icon=":material/search:", width="stretch", key="ask_go")
    t1, t2 = st.columns(2)
    historical = t1.toggle(
        ctx.tr("Sertakan sejarah (pekeliling dibatalkan)", "Include historical (cancelled circulars)"),
        key="ask_historical",
    )
    compare = t2.toggle(
        ctx.tr("Bandingkan dengan chatbot biasa (baseline)", "Compare with a typical chatbot (baseline)"),
        key="ask_compare",
    )

    notice = st.session_state.pop("ask_goto_notice", None)
    if notice:
        st.toast(ctx.tr("Buka tab Salasilah & Perubahan.", "Open the Lineage & Changes tab."), icon=":material/account_tree:")

    question = (st.session_state.get("ask_question") or "").strip()
    if not question:
        st.info(
            ctx.tr(
                "Jawapan hanya daripada pekeliling yang berkuat kuasa, dengan petikan perenggan dan halaman. "
                "Pekeliling yang dibatalkan dikecualikan dan disenaraikan.",
                "Answers come only from circulars currently in force, citing clause and page. "
                "Cancelled circulars are excluded and listed.",
            ),
            icon=":material/verified:",
        )
        return

    base_key = (question, user.user_id, store.llm.provider, store.revision)
    with st.spinner(ctx.tr("Mencari dalam pekeliling yang berkuat kuasa...", "Searching circulars in force...")):
        nav = _cached("ask_nav", base_key + (historical,), lambda: ask.ask(store, user, question, include_historical=historical))
        base = _cached("ask_base", base_key, lambda: ask.ask(store, user, question, mode="baseline")) if compare else None

    if base is not None:
        left, right = st.columns(2)
        with left:
            st.markdown("#### " + ctx.tr("Chatbot biasa (baseline)", "Typical chatbot (baseline)"))
            st.caption(ctx.tr("Carian sama, tanpa penapis status atau bidang kuasa.",
                              "Same search, no status or jurisdiction filter."))
            _answer_card(ctx, base, "base")
        with right:
            st.markdown("#### MixUp Navigator")
            st.caption(ctx.tr("Hanya pekeliling berkuat kuasa, ikut profil anda.", "Only circulars in force, for your profile."))
            _answer_card(ctx, nav, "nav")
    else:
        _answer_card(ctx, nav, "nav")
