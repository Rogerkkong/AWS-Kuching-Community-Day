"""Smart Upload tab (FEATURE C). STUB created by Foundation; Feature C replaces render().

session_state keys used here start with "upload_".
"""

from __future__ import annotations

import streamlit as st

from mixup import upload


def render(ctx) -> None:
    st.subheader("Smart Upload")
    st.caption("Upload a PDF, DOCX, MD or TXT. MixUp reads it and finds which document it replaces.")
    file = st.file_uploader("Document", type=["pdf", "docx", "md", "txt"], key="upload_file")
    if file is None:
        return
    data = file.getvalue()
    if st.button("Analyze", key="upload_analyze"):
        st.session_state["upload_analysis"] = upload.analyze(ctx, file.name, data)
    analysis = st.session_state.get("upload_analysis")
    if analysis is None:
        return
    meta = analysis["meta"]
    st.write(f"**{meta.title}** ({analysis['pages']} sections)")
    for item in analysis["supersedes"]:
        st.warning(f"Replaces {item['doc_id']}: {item['evidence']}")
    if st.button("Confirm and add to library", key="upload_commit", type="primary"):
        doc_id = upload.commit(ctx, analysis, data, file.name)
        st.session_state.pop("upload_analysis", None)
        st.success(f"Added {doc_id}. Library, map and answers are updated.")
