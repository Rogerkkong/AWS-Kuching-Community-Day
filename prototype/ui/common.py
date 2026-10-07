"""Shared UI helpers: UIContext, BM/EN labels, badges (text + colour, never colour
alone), source card and source viewer.

Every tab module exposes render(ctx: UIContext). Use ctx.t("key") for shared
labels or ctx.tr("teks BM", "EN text") for tab-specific strings.
Session-state keys must be prefixed with the tab name (ask_, lineage_, admin_, ...).
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass

import streamlit as st

from mixup import access
from mixup.models import (
    CLASSIFICATION_LABELS,
    JURISDICTION_LABELS,
    STATUS_LABELS,
    Citation,
    Document,
    User,
)

# key -> (BM, EN)
LABELS: dict[str, tuple[str, str]] = {
    "tagline": ("Jangan rujuk pekeliling yang telah dibatalkan lagi.", "Never cite a cancelled circular again."),
    "by_team": ("oleh Team MixUp", "by Team MixUp"),
    "tab_ask": ("Tanya", "Ask"),
    "tab_lineage": ("Salasilah & Perubahan", "Lineage & Changes"),
    "tab_admin": ("Pentadbir", "Admin"),
    "tab_eval": ("Penilaian", "Evaluation"),
    "tab_analytics": ("Analitik", "Analytics"),
    "tab_library": ("Perpustakaan", "Library"),
    "demo_user": ("Pengguna demo", "Demo user"),
    "jurisdiction": ("Bidang kuasa", "Jurisdiction"),
    "clearance": ("Tahap akses", "Clearance"),
    "grade": ("Gred", "Grade"),
    "interface_language": ("Bahasa antara muka", "Interface language"),
    "llm_mode": ("Mod model", "Model mode"),
    "notifications": ("Notifikasi", "Notifications"),
    "no_notifications": ("Tiada notifikasi.", "No notifications."),
    "mark_read": ("Tandakan semua dibaca", "Mark all as read"),
    "reset_demo": ("Set semula demo", "Reset demo"),
    "reset_done": ("Demo telah diset semula.", "Demo reset."),
    "synthetic_note": (
        "Semua dokumen ialah SINTETIK - CONTOH SAHAJA (penerbit rekaan).",
        "All documents are SYNTHETIC - SAMPLE ONLY (fictional issuers).",
    ),
    "sso_note": (
        "Demo tanpa kata laluan. Produksi akan menggunakan MyGovUC / SSO agensi.",
        "Demo without passwords. Production would use MyGovUC / agency single sign-on.",
    ),
    "status": ("Status", "Status"),
    "circular": ("Pekeliling", "Circular"),
    "clause": ("Perenggan", "Clause"),
    "page": ("Halaman", "Page"),
    "effective": ("Berkuat kuasa", "Effective"),
    "issued": ("Dikeluarkan", "Issued"),
    "issuer": ("Penerbit", "Issuer"),
    "cluster": ("Kluster", "Cluster"),
    "type": ("Jenis", "Type"),
    "applicability": ("Pemakaian", "Applicability"),
    "view_source": ("Lihat sumber", "View source"),
    "source_hidden": ("Dokumen ini tidak tersedia untuk tahap akses anda.", "This document is not available at your clearance."),
    "all": ("Semua", "All"),
    "search_library": ("Cari tajuk atau nombor", "Search title or number"),
    "documents": ("Dokumen", "Documents"),
    "needs_ocr": ("Halaman perlu OCR", "Pages needing OCR"),
    "stub": ("Ciri ini sedang dibina.", "This feature is being built."),
}

CLUSTER_LABELS = {
    "travel-claims": ("Tuntutan perjalanan", "Travel claims"),
    "leave": ("Cuti", "Leave"),
    "flexible-work": ("Bekerja fleksibel", "Flexible work"),
    "ict-data": ("ICT & data", "ICT & data"),
    "governance": ("Tadbir urus", "Governance"),
}
DOC_TYPE_LABELS = {
    "circular": ("Pekeliling", "Circular"),
    "guideline": ("Garis panduan", "Guideline"),
    "sop": ("SOP", "SOP"),
    "minutes": ("Minit mesyuarat", "Minutes"),
    "report": ("Laporan", "Report"),
}
CONFIDENCE_LABELS = {
    "HIGH": ("Keyakinan tinggi", "High confidence", "green"),
    "MEDIUM": ("Keyakinan sederhana", "Medium confidence", "orange"),
    "LOW": ("Keyakinan rendah", "Low confidence", "gray"),
}
TAB_PREFIXES = ("ask_", "lineage_", "admin_", "eval_", "analytics_", "library_")


@dataclass
class UIContext:
    """What every tab receives."""

    store: object  # mixup.store.Store
    user: User
    lang: str = "ms"  # interface language: "ms" | "en"

    def t(self, key: str) -> str:
        """Shared label in the interface language (falls back to the key)."""
        pair = LABELS.get(key)
        return pair[1 if self.lang == "en" else 0] if pair else key

    def tr(self, ms: str, en: str) -> str:
        """Inline bilingual string: ctx.tr('Tanya', 'Ask')."""
        return en if self.lang == "en" else ms


def _pick(pair, lang: str) -> str:
    return pair[1] if lang == "en" else pair[0]


def _badge(text: str, color: str) -> str:
    safe = text.replace("[", "(").replace("]", ")")
    return f":{color}-badge[{safe}]"


def status_label(status: str, lang: str = "ms") -> str:
    ms, en, _ = STATUS_LABELS.get(status, (status or "?", status or "?", "gray"))
    return en if lang == "en" else ms


def status_badge(status: str, lang: str = "ms", reason: str = "") -> str:
    """Markdown badge, e.g. ':green-badge[Berkuat kuasa]'. Text + colour, never colour alone."""
    ms, en, color = STATUS_LABELS.get(status, (status or "?", status or "?", "gray"))
    text = en if lang == "en" else ms
    if reason:
        text = f"{text}: {reason}"
    return _badge(text, color)


def classification_badge(level: int, lang: str = "ms") -> str:
    pair = CLASSIFICATION_LABELS.get(int(level or 0), ("?", "?"))
    color = {0: "blue", 1: "orange", 2: "red"}.get(int(level or 0), "gray")
    return _badge(_pick(pair, lang), color)


def jurisdiction_label(jurisdiction: str, lang: str = "ms") -> str:
    return _pick(JURISDICTION_LABELS.get(jurisdiction, (jurisdiction, jurisdiction)), lang)


def jurisdiction_badge(jurisdiction: str, lang: str = "ms") -> str:
    color = {"FEDERAL": "blue", "SARAWAK": "violet", "FEDERAL_SARAWAK": "blue"}.get(jurisdiction, "gray")
    return _badge(jurisdiction_label(jurisdiction, lang), color)


def confidence_badge(level: str, lang: str = "ms") -> str:
    ms, en, color = CONFIDENCE_LABELS.get((level or "").upper(), (level or "?", level or "?", "gray"))
    return _badge(en if lang == "en" else ms, color)


def cluster_label(cluster: str, lang: str = "ms") -> str:
    return _pick(CLUSTER_LABELS.get(cluster, (cluster or "-", cluster or "-")), lang)


def doc_type_label(doc_type: str, lang: str = "ms") -> str:
    return _pick(DOC_TYPE_LABELS.get(doc_type, (doc_type, doc_type)), lang)


def user_label(user: User, lang: str = "ms") -> str:
    """'Pegawai Sarawak (Terbuka) - Negeri Sarawak - Terbuka'."""
    level = _pick(CLASSIFICATION_LABELS.get(user.clearance_level, ("?", "?")), lang)
    return f"{user.name} | {jurisdiction_label(user.jurisdiction, lang)} | {level}"


def doc_heading(doc: Document, lang: str = "ms") -> str:
    """Markdown: '**SPP 1/2023** Title  :orange-badge[Dipinda]'."""
    return f"**{doc.label}** {doc.title} {status_badge(doc.status, lang)}"


def doc_caption(doc: Document, lang: str = "ms") -> str:
    parts = [
        doc_type_label(doc.doc_type, lang),
        jurisdiction_label(doc.jurisdiction, lang),
        f"{'Effective' if lang == 'en' else 'Berkuat kuasa'} {doc.effective_date or '-'}",
        doc.issuer,
    ]
    if doc.status_reason:
        parts.insert(0, doc.status_reason)
    return " | ".join(p for p in parts if p)


def highlight(text: str, needle: str) -> str:
    """HTML-escape text and mark the passage (or its first 80 chars) with <mark>."""
    safe = html.escape(text or "")
    needle = (needle or "").strip()
    if not needle:
        return safe
    for candidate in (needle, needle[:80]):
        esc = html.escape(candidate.strip())
        if esc and esc in safe:
            return safe.replace(esc, f"<mark>{esc}</mark>", 1)
    # fall back: highlight the first line of the passage
    first = html.escape(needle.split("\n")[0].strip())
    return safe.replace(first, f"<mark>{first}</mark>", 1) if first and first in safe else safe


def show_source(ctx: UIContext, doc_id: str, page: int | None = None, passage: str = "") -> None:
    """Source viewer: the cited page with the passage highlighted (access-checked)."""
    doc = access.get_doc(ctx.store, ctx.user, doc_id)
    if doc is None:
        st.warning(ctx.t("source_hidden"))
        return
    pages = access.get_pages(ctx.store, ctx.user, doc_id)
    st.markdown(doc_heading(doc, ctx.lang))
    st.caption(doc_caption(doc, ctx.lang))
    if not pages:
        return
    numbers = [p.page_no for p in pages]
    chosen = page if page in numbers else numbers[0]
    if len(numbers) > 1:
        chosen = st.select_slider(
            ctx.t("page"), options=numbers, value=chosen, key=f"src_page_{doc_id}_{page}_{abs(hash(passage)) % 10_000}"
        )
    current = next(p for p in pages if p.page_no == chosen)
    body = highlight(current.text, passage if chosen == page else "")
    body = re.sub(r"(?m)^(#{1,6})\s*", "", body).replace("\n", "<br>")
    st.markdown(
        f"<div style='border:1px solid #bbb;border-radius:6px;padding:12px;font-family:Georgia,serif;"
        f"background:var(--secondary-background-color, #f7f7f7)'>"
        f"<div style='font-size:0.8em;opacity:0.7'>{html.escape(doc.label)} | {ctx.t('page')} {chosen}/{len(numbers)}"
        f"{' | ' + ctx.t('needs_ocr') if current.needs_ocr else ''}</div>{body}</div>",
        unsafe_allow_html=True,
    )


def source_card(ctx: UIContext, citation: Citation, passage: str = "") -> None:
    """One cited source: [S1] circular, clause, page, status badge, snippet + 'View source'."""
    with st.container(border=True):
        st.markdown(
            f"**[{citation.label}] {citation.circular_no}** {citation.title}  "
            f"{status_badge(citation.status, ctx.lang)} {jurisdiction_badge(citation.jurisdiction, ctx.lang)}"
        )
        st.caption(
            f"{ctx.t('clause')} {citation.clause_ref} | {ctx.t('page')} {citation.page}"
            + (f" | {citation.status_reason}" if citation.status_reason else "")
        )
        if citation.snippet:
            st.markdown(f"> {citation.snippet}")
        with st.expander(ctx.t("view_source")):
            show_source(ctx, citation.doc_id, citation.page, passage or citation.snippet.replace(" ...", ""))


def stub_notice(ctx: UIContext, feature: str) -> None:
    st.info(f"{ctx.t('stub')} ({feature})", icon=":material/construction:")


def clear_tab_state() -> None:
    """Forget every tab's session_state (used by Reset demo)."""
    for key in list(st.session_state.keys()):
        if str(key).startswith(TAB_PREFIXES) or str(key).startswith("src_page_"):
            del st.session_state[key]
