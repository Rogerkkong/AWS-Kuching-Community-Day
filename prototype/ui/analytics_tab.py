"""Feature D - Analytics dashboard (FR-16): unanswered and low-confidence questions by cluster,
top questions and topics, cancelled circulars most often excluded, feedback.

All access rules live in mixup.analytics.summary (officers see their own questions; policy
owners and admins see questions at or below their clearance).
Contract: render(ctx: ui.common.UIContext) -> None. Session-state keys start with "analytics_".
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from mixup import analytics
from ui import common

SERIES_COLOR = "#2a78d6"  # single series: categorical slot 1


def _pct(value: float) -> str:
    return f"{(value or 0) * 100:.0f}%"


def _kpis(ctx: common.UIContext, data: dict) -> None:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(ctx.tr("Soalan", "Questions"), data["total_queries"], border=True)
    c2.metric(
        ctx.tr("Tidak terjawab", "Unanswered"),
        f"{data['unanswered']} ({_pct(data['unanswered_rate'])})",
        border=True,
    )
    c3.metric(
        ctx.tr("Keyakinan rendah", "Low confidence"),
        f"{data['low_confidence']} ({_pct(data['low_confidence_rate'])})",
        border=True,
    )
    fb = data["feedback"]
    c4.metric(
        ctx.tr("Maklum balas", "Feedback"),
        f"+{fb['up']} / -{fb['down']}",
        delta=ctx.tr(f"{fb['wrong_status']} laporan status salah", f"{fb['wrong_status']} wrong-status reports"),
        delta_color="off",
        border=True,
    )


def _question_list(ctx: common.UIContext, items: list[dict], empty: str) -> None:
    if not items:
        st.caption(empty)
        return
    rows = []
    for it in items:
        row = {
            ctx.tr("Soalan", "Question"): it["question"],
            ctx.t("cluster"): common.cluster_label(it.get("cluster") or "", ctx.lang),
            ctx.tr("Masa", "Time"): (it.get("created_at") or "")[:16].replace("T", " "),
        }
        if "user_id" in it:
            row[ctx.tr("Pengguna", "User")] = it["user_id"]
        rows.append(row)
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")


def _clusters(ctx: common.UIContext, data: dict) -> None:
    if not data["by_cluster"]:
        return
    df = pd.DataFrame(
        [
            {
                ctx.t("cluster"): common.cluster_label(c["cluster"], ctx.lang),
                ctx.tr("Soalan", "Questions"): c["total"],
                ctx.tr("Tidak terjawab", "Unanswered"): c["unanswered"],
                ctx.tr("Keyakinan rendah", "Low confidence"): c["low_confidence"],
                ctx.tr("Kadar tidak terjawab", "Unanswered rate"): _pct(c["unanswered_rate"]),
            }
            for c in data["by_cluster"]
        ]
    )
    st.dataframe(df, hide_index=True, width="stretch")


def _excluded(ctx: common.UIContext, data: dict) -> None:
    items = data["most_excluded"]
    if not items:
        st.caption(ctx.tr("Belum ada pekeliling dikecualikan.", "No circulars excluded yet."))
        return
    count_col = ctx.tr("Kali dikecualikan", "Times excluded")
    chart = pd.DataFrame({ctx.t("circular"): [i["circular_no"] for i in items], count_col: [i["count"] for i in items]})
    st.bar_chart(chart.set_index(ctx.t("circular")), horizontal=True, color=SERIES_COLOR, height=60 + 40 * len(items))
    for it in items:
        st.markdown(
            f"**{it['circular_no']}** {it['title']} {common.status_badge(it['status'], ctx.lang, it['status_reason'])} "
            f"- {it['count']}x"
        )


def render(ctx: common.UIContext) -> None:
    st.subheader(ctx.tr("Analitik soalan", "Question analytics"))
    data = analytics.summary(ctx.store, ctx.user)
    if data["scope"] == "all":
        scope = ctx.tr(
            "Anda melihat semua soalan pada atau di bawah tahap akses anda (Pemilik Dasar / Admin).",
            "You see every question asked at or below your clearance (policy owner / admin).",
        )
    else:
        scope = ctx.tr(
            "Anda melihat soalan anda sendiri sahaja. Pemilik Dasar dan Admin melihat semua soalan.",
            "You see your own questions only. Policy owners and admins see all questions.",
        )
    st.caption(scope)
    if data["hidden_rows"]:
        st.caption(
            ctx.tr(
                f"{data['hidden_rows']} soalan disembunyikan kerana melibatkan dokumen di atas tahap akses anda.",
                f"{data['hidden_rows']} questions hidden because they involve documents above your clearance.",
            )
        )
    if not data["total_queries"]:
        st.info(ctx.tr("Belum ada soalan. Cuba tab Tanya dahulu.", "No questions yet. Try the Ask tab first."))
        return

    _kpis(ctx, data)
    st.caption(
        ctx.tr(
            f"Latensi p50 {data['latency_p50_ms']:.0f} ms, p95 {data['latency_p95_ms']:.0f} ms | "
            f"{data['excluded_answers']} jawapan mengecualikan pekeliling lapuk | "
            f"{data['jurisdiction_conflicts']} perbandingan Persekutuan/Sarawak | "
            f"{data['baseline_queries']} larian chatbot biasa (tidak dikira)",
            f"Latency p50 {data['latency_p50_ms']:.0f} ms, p95 {data['latency_p95_ms']:.0f} ms | "
            f"{data['excluded_answers']} answers excluded stale circulars | "
            f"{data['jurisdiction_conflicts']} Federal/Sarawak comparisons | "
            f"{data['baseline_queries']} typical-chatbot runs (not counted)",
        )
    )

    left, right = st.columns(2)
    with left:
        st.markdown("##### " + ctx.tr("Soalan tidak terjawab (jurang kandungan)", "Unanswered questions (content gaps)"))
        _question_list(ctx, data["unanswered_questions"], ctx.tr("Tiada.", "None."))
    with right:
        st.markdown("##### " + ctx.tr("Jawapan keyakinan rendah", "Low-confidence answers"))
        _question_list(ctx, data["low_confidence_questions"], ctx.tr("Tiada.", "None."))

    st.markdown("##### " + ctx.tr("Mengikut kluster", "By cluster"))
    _clusters(ctx, data)

    left, right = st.columns(2)
    with left:
        st.markdown("##### " + ctx.tr("Soalan paling kerap", "Top questions"))
        if data["top_questions"]:
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            ctx.tr("Soalan", "Question"): q["question"],
                            ctx.tr("Kali", "Count"): q["count"],
                            ctx.tr("Dijawab", "Answered"): q["answered"],
                        }
                        for q in data["top_questions"]
                    ]
                ),
                hide_index=True,
                width="stretch",
            )
    with right:
        st.markdown("##### " + ctx.tr("Pekeliling lapuk paling kerap dikecualikan", "Cancelled circulars most often excluded"))
        _excluded(ctx, data)

    if data["wrong_status_reports"] or data["feedback_comments"]:
        st.markdown("##### " + ctx.tr("Maklum balas pengguna", "User feedback"))
        for rep in data["wrong_status_reports"]:
            st.markdown(
                ":orange-badge[" + ctx.tr("Status salah dilaporkan", "Wrong status reported") + f"] {rep['question']}"
                + (f" - _{rep['comment']}_" if rep.get("comment") else "")
            )
        for com in data["feedback_comments"]:
            sign = "+1" if com["rating"] > 0 else ("-1" if com["rating"] < 0 else "")
            st.markdown(f"{sign} {com['question']} - _{com['comment']}_")
