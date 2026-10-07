"""Feature D - Evaluation tab: Baseline (typical chatbot) vs Navigator on the golden set.

Shows the last saved run (eval/results/results.json) by default; "Run evaluation" re-runs
all golden questions in both modes and saves the files again.
Contract: render(ctx: ui.common.UIContext) -> None. Session-state keys start with "eval_".
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from mixup import evaluate
from ui import common

# Categorical slots 1 and 2 of the reference palette (fixed order: Baseline, Navigator).
SERIES_COLORS = ["#2a78d6", "#eb6834"]
TYPE_LABELS = {
    "normal": ("Biasa", "Normal"),
    "trap_cancelled": ("Perangkap: dibatalkan", "Trap: cancelled rule"),
    "jurisdiction": ("Bidang kuasa", "Jurisdiction"),
    "unanswerable": ("Tiada jawapan", "Unanswerable"),
    "access": ("Kawalan akses", "Access control"),
}


def _type_label(ctx: common.UIContext, qtype: str) -> str:
    pair = TYPE_LABELS.get(qtype, (qtype, qtype))
    return ctx.tr(*pair)


def _ok_badge(ctx: common.UIContext, ok: bool, yes: tuple[str, str], no: tuple[str, str]) -> str:
    """Text + colour, never colour alone."""
    return f":green-badge[{ctx.tr(*yes)}]" if ok else f":red-badge[{ctx.tr(*no)}]"


def _run(ctx: common.UIContext) -> dict:
    bar = st.progress(0.0, text=ctx.tr("Menjalankan soalan emas...", "Running golden questions..."))

    def progress(done: int, total: int, qid: str) -> None:
        bar.progress(min(1.0, done / max(total, 1)), text=f"{qid} ({done}/{total})" if qid else "")

    result = evaluate.run(ctx.store, evaluate.GOLDEN_PATH, progress=progress)
    bar.empty()
    try:
        evaluate.write_results(result)
    except OSError as exc:  # read-only folder: still show the results
        st.warning(ctx.tr(f"Keputusan tidak disimpan ({exc}).", f"Results not saved ({exc})."))
    return result


def _headline(ctx: common.UIContext, result: dict) -> None:
    base, nav = result.get("baseline") or {}, result.get("navigator") or {}
    c1, c2, c3 = st.columns(3)
    c1.metric(
        ctx.tr("Petik pekeliling dibatalkan sebagai semasa", "Cites a cancelled rule as current"),
        evaluate.format_value("cancelled_citation_rate", nav.get("cancelled_citation_rate")),
        delta=ctx.tr(
            f"chatbot biasa: {evaluate.format_value('cancelled_citation_rate', base.get('cancelled_citation_rate'))}",
            f"typical chatbot: {evaluate.format_value('cancelled_citation_rate', base.get('cancelled_citation_rate'))}",
        ),
        delta_color="off",
        border=True,
    )
    c2.metric(
        ctx.tr("Jawapan betul & semasa", "Correct & current answers"),
        f"{nav.get('correct_current', 0)}/{nav.get('n', 0)}",
        delta=ctx.tr(
            f"chatbot biasa: {base.get('correct_current', 0)}/{base.get('n', 0)}",
            f"typical chatbot: {base.get('correct_current', 0)}/{base.get('n', 0)}",
        ),
        delta_color="off",
        border=True,
    )
    c3.metric(
        ctx.tr("Kebocoran akses", "Access leaks"),
        str(nav.get("access_leaks", 0)),
        delta=ctx.tr("sasaran: 0", "target: 0"),
        delta_color="off",
        border=True,
    )


def _explain(ctx: common.UIContext) -> None:
    st.markdown(
        ctx.tr(
            "- **Chatbot biasa (baseline)** menggunakan carian dan langkah jawapan yang sama, tetapi tanpa penapis "
            "status, tanpa logik bidang kuasa dan tanpa senarai dikecualikan.\n"
            "- **Kadar petikan dibatalkan**: soalan perangkap di mana pekeliling yang dibatalkan (atau perenggan "
            "yang telah dipinda) dipetik seolah-olah masih berkuat kuasa. Lebih rendah lebih baik.\n"
            "- **Ketepatan penolakan**: soalan tanpa jawapan yang dibenarkan (tiada dalam korpus, atau dokumen "
            "terhad) yang ditolak dengan betul. Lebih tinggi lebih baik.\n"
            "- **Kebocoran akses** mesti 0: kandungan Terhad/Sulit tidak pernah sampai kepada pengguna Terbuka.",
            "- The **typical chatbot (baseline)** uses the same search and answer step, but no status filter, no "
            "jurisdiction logic and no excluded list.\n"
            "- **Cancelled-citation rate**: trap questions where a cancelled circular (or an amended clause) is "
            "quoted as if it were still in force. Lower is better.\n"
            "- **Refusal accuracy**: questions with no permitted answer (not in the corpus, or restricted) that were "
            "correctly refused. Higher is better.\n"
            "- **Access leaks** must be 0: Terhad/Sulit content never reaches a Terbuka user.",
        )
    )


def _chart(ctx: common.UIContext, result: dict) -> None:
    base, nav = result.get("baseline") or {}, result.get("navigator") or {}
    names = [ctx.tr("Kadar petikan dibatalkan", "Cancelled-citation rate"), ctx.tr("Ketepatan penolakan", "Refusal accuracy")]
    keys = ["cancelled_citation_rate", "refusal_accuracy"]
    col_base, col_nav = ctx.tr("Chatbot biasa", "Typical chatbot"), "Navigator"
    df = pd.DataFrame(
        {
            ctx.tr("Metrik", "Metric"): names,
            col_base: [round((base.get(k) or 0) * 100, 1) for k in keys],
            col_nav: [round((nav.get(k) or 0) * 100, 1) for k in keys],
        }
    ).set_index(ctx.tr("Metrik", "Metric"))
    st.bar_chart(df, stack=False, color=SERIES_COLORS, y_label="%", height=280)
    st.caption(
        ctx.tr(
            "Peratus. Kadar petikan dibatalkan: lebih rendah lebih baik. Ketepatan penolakan: lebih tinggi lebih baik.",
            "Percent. Cancelled-citation rate: lower is better. Refusal accuracy: higher is better.",
        )
    )


def _metrics_table(ctx: common.UIContext, result: dict) -> None:
    rows = evaluate.comparison_table(result, ctx.lang)
    df = pd.DataFrame(
        [
            {
                ctx.tr("Metrik", "Metric"): r["metric"],
                ctx.tr("Chatbot biasa", "Typical chatbot"): r["baseline"],
                "Navigator": r["navigator"],
                ctx.tr("Sasaran", "Target"): r["target"],
            }
            for r in rows
        ]
    )
    st.dataframe(df, hide_index=True, width="stretch")


def _by_type(ctx: common.UIContext, result: dict) -> None:
    data = []
    for qtype, modes in result.get("by_type", {}).items():
        b, n = modes.get("baseline", {}), modes.get("navigator", {})
        total = b.get("n") or n.get("n") or 0
        data.append(
            {
                ctx.tr("Jenis soalan", "Question type"): _type_label(ctx, qtype),
                "n": total,
                ctx.tr("Chatbot biasa", "Typical chatbot"): f"{b.get('correct', 0)}/{total}",
                "Navigator": f"{n.get('correct', 0)}/{total}",
            }
        )
    if data:
        st.dataframe(pd.DataFrame(data), hide_index=True, width="stretch")


def _answer_panel(ctx: common.UIContext, row: dict, title: str) -> None:
    with st.container(border=True):
        st.markdown(f"**{title}**")
        st.markdown(
            _ok_badge(ctx, row["correct_current"], ("Betul & semasa", "Correct & current"), ("Salah / lapuk", "Wrong / stale"))
            + " "
            + (":gray-badge[" + ctx.tr("Ditolak", "Refused") + "]" if not row["answerable"] else "")
        )
        if row.get("failure"):
            st.caption(row["failure"])
        if row.get("stale_as_current"):
            st.markdown(":red-badge[" + ctx.tr("Petik lapuk sebagai semasa", "Stale rule cited as current") + "] "
                        + row["stale_as_current"])
        if row.get("stale_labelled"):
            st.caption(ctx.tr("Dipetik dengan label sejarah: ", "Cited with a historical label: ") + row["stale_labelled"])
        if row.get("excluded"):
            st.caption(ctx.tr("Dikecualikan: ", "Excluded: ") + row["excluded"])
        st.caption(ctx.tr("Petikan: ", "Citations: ") + (row.get("citations") or "-"))
        st.caption(ctx.tr("5 petikan teratas: ", "Top-5 passages: ") + (row.get("retrieved_top5") or "-"))
        with st.expander(ctx.tr("Jawapan penuh", "Full answer")):
            st.markdown(row.get("answer") or "-")


def _drilldown(ctx: common.UIContext, result: dict) -> None:
    rows = result.get("rows", [])
    if not rows:
        return
    types = ["all"] + [t for t in evaluate.TYPES if any(r["type"] == t for r in rows)]
    c1, c2 = st.columns([1, 1])
    qtype = c1.selectbox(
        ctx.tr("Jenis soalan", "Question type"), types, key="eval_type",
        format_func=lambda t: ctx.t("all") if t == "all" else _type_label(ctx, t),
    )
    only_diff = c2.toggle(ctx.tr("Hanya yang berbeza / gagal", "Only differences / misses"), key="eval_only_diff")
    pairs: dict[str, dict] = {}
    for r in rows:
        pairs.setdefault(r["id"], {})[r["mode"]] = r
    ids = []
    for qid, modes in pairs.items():
        nav, base = modes.get("navigator"), modes.get("baseline")
        first = nav or base
        if qtype != "all" and first["type"] != qtype:
            continue
        if only_diff and nav and base and nav["correct_current"] and base["correct_current"]:
            continue
        ids.append(qid)
    if not ids:
        st.caption(ctx.tr("Tiada soalan untuk penapis ini.", "No questions for this filter."))
        return

    def label(qid: str) -> str:
        r = pairs[qid].get("navigator") or pairs[qid].get("baseline")
        return f"{qid} [{r['user_profile']}, {r['language']}] {r['question']}"

    qid = st.selectbox(ctx.tr("Soalan", "Question"), ids, key="eval_question", format_func=label)
    modes = pairs[qid]
    first = modes.get("navigator") or modes.get("baseline")
    expected = first["expected_doc"] or ctx.tr("(patut ditolak)", "(should be refused)")
    clause = f" {ctx.t('clause').lower()} {first['expected_clause']}" if first.get("expected_clause") else ""
    st.caption(
        f"{_type_label(ctx, first['type'])} | {ctx.tr('Dijangka', 'Expected')}: {expected}{clause}"
        + (f" | {ctx.tr('Tidak boleh dipetik', 'Must not cite')}: {first['must_not_cite']}" if first.get("must_not_cite") else "")
    )
    left, right = st.columns(2)
    with left:
        if "baseline" in modes:
            _answer_panel(ctx, modes["baseline"], ctx.tr("Chatbot biasa (baseline)", "Typical chatbot (baseline)"))
    with right:
        if "navigator" in modes:
            _answer_panel(ctx, modes["navigator"], "MixUp Navigator")


def render(ctx: common.UIContext) -> None:
    st.subheader(ctx.tr("Penilaian: chatbot biasa lwn Navigator", "Evaluation: typical chatbot vs Navigator"))
    st.caption(
        ctx.tr(
            "Set soalan emas (data/golden_set.csv) dijalankan melalui kedua-dua sistem dengan profil pengguna setiap soalan.",
            "The golden set (data/golden_set.csv) is run through both systems with each question's user profile.",
        )
    )
    if st.button(ctx.tr("Jalankan penilaian", "Run evaluation"), icon=":material/play_arrow:", key="eval_run"):
        try:
            st.session_state["eval_result"] = _run(ctx)
        except Exception as exc:  # keep the cached numbers on screen
            st.error(ctx.tr(f"Penilaian gagal ({type(exc).__name__}: {exc}).", f"Evaluation failed ({type(exc).__name__}: {exc})."))
    result = st.session_state.get("eval_result") or evaluate.load_cached()
    if not result:
        st.info(ctx.tr("Belum ada keputusan. Klik 'Jalankan penilaian'.", "No results yet. Click 'Run evaluation'."))
        return
    meta = result.get("meta", {})
    langs = meta.get("languages", {})
    st.caption(
        f"{ctx.tr('Dijana', 'Generated')} {meta.get('generated_at', '-')} | {ctx.t('llm_mode')}: "
        f"{meta.get('llm_label', meta.get('llm_provider', '-'))} | {ctx.tr('Tarikh status', 'Status date')}: "
        f"{meta.get('today', '-')} | {meta.get('n_questions', 0)} {ctx.tr('soalan', 'questions')} "
        f"({langs.get('ms', 0)} BM, {langs.get('en', 0)} EN, {langs.get('mixed', 0)} {ctx.tr('campur', 'mixed')})"
    )
    for problem in meta.get("problems", []):
        st.warning(problem)

    _headline(ctx, result)
    left, right = st.columns([3, 2])
    with left:
        _metrics_table(ctx, result)
    with right:
        _chart(ctx, result)
    _explain(ctx)
    st.markdown("##### " + ctx.tr("Mengikut jenis soalan (betul & semasa)", "By question type (correct & current)"))
    _by_type(ctx, result)
    st.markdown("##### " + ctx.tr("Perincian setiap soalan", "Per-question drill-down"))
    _drilldown(ctx, result)
    st.caption(
        ctx.tr(
            "Kaedah: korpus SINTETIK, diukur sendiri oleh Team MixUp; set soalan kecil, jadi angka ini petunjuk sahaja. "
            "Butiran penuh dalam eval/results/summary.md.",
            "Method: SYNTHETIC corpus, self-measured by Team MixUp; the golden set is small, so treat the numbers as "
            "indicative. Full details in eval/results/summary.md.",
        )
    )
