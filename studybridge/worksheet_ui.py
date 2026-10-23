"""Worksheet upload and human-reviewed transcription interface."""
from io import BytesIO
from copy import deepcopy
import zipfile

import streamlit as st

from . import ai, summary_dashboard
from .catalog import TOPICS
from .engine import identifier, local_outline, make_course
from .worksheets import ASSETS, SAMPLES, prepare_images


def render(save, go, use_ai_budget):
    st.markdown('<div class="eyebrow">UPLOAD / UNDERSTAND / PRACTISE</div><div class="page-title">Your materials, made clearer.</div><div class="page-sub">Review your lesson pictures, understand what needs work, and choose your next practice.</div>', unsafe_allow_html=True)
    st.caption("Original fictional worksheets by Yifan Yan. These are test materials, not real students' records.")
    package = BytesIO()
    with zipfile.ZipFile(package, "w", zipfile.ZIP_DEFLATED) as archive:
        for sample in SAMPLES:
            for suffix in ("png", "txt"):
                archive.write(ASSETS / f"{sample['id']}.{suffix}", f"{sample['id']}.{suffix}")
    st.download_button("Download all 3 worksheets + transcripts", package.getvalue(), "studybridge-sample-worksheets.zip", "application/zip")
    if st.button("Try all 3 mistake examples", type="primary"):
        st.session_state.image_review = {"id": identifier(), "images": prepare_images(
            [(f"{s['id']}.png", (ASSETS / f"{s['id']}.png").read_bytes()) for s in SAMPLES])}
        st.rerun()
    with st.expander("Try a sample worksheet", expanded=not st.session_state.get("image_review")):
        for col, sample in zip(st.columns(3), SAMPLES):
            with col, st.container(border=True):
                path = ASSETS / f"{sample['id']}.png"
                st.image(str(path), caption=sample["title"], width=150)
                st.caption(sample["kind"])
                st.download_button("Download PNG", path.read_bytes(), path.name, "image/png", key=f"png_{sample['id']}")
                if st.button("Try this worksheet", key=f"worksheet_{sample['id']}"):
                    st.session_state.image_review = {"id": identifier(), "images": prepare_images([(path.name, path.read_bytes())])}
                    st.rerun()
    st.subheader("Or upload your own pictures")
    files = st.file_uploader("Worksheet images · PNG or JPEG", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="worksheet_uploads")
    st.caption("Up to 3 images · 5 MB each · 12 megapixels each. Raw images stay in this browser session on the server; saved courses contain reviewed text and image hashes.")
    if st.button("Preview uploaded images", disabled=not files):
        try:
            images = prepare_images([(f.name, f.getvalue()) for f in files])
            st.session_state.image_review = {"id": identifier(), "images": images}
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))
    draft = st.session_state.get("image_review")
    if not draft:
        return
    st.subheader("Upload → review → summary → practice")
    st.info("Bundled samples include prepared transcripts. For other images, type the text below or ask AI to read it. Neither path creates a course until you confirm.")
    consent = st.checkbox("Send these images to OpenAI for transcription", key=f"image_consent_{draft['id']}", disabled=not ai.configured())
    if not ai.configured():
        st.caption("AI is not connected. Sample transcripts and manual typing remain available.")
    if st.button("Read images with AI", disabled=not (ai.configured() and consent)):
        try:
            use_ai_budget()
            with st.spinner("Reading your pages…"):
                reading = ai.transcribe(draft["images"])
            for item in draft["images"]:
                result = reading[item["id"]]
                item.update(text=result["text"], uncertainties=result["uncertainties"], method="AI transcription · user review required")
            draft["id"] = identifier()  # New widget keys prevent stale text overriding new readings.
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))
    dashboard_tab, transcript_tab = st.tabs(["Learning summary", "Review transcripts"])
    edited = []
    with transcript_tab:
        for i, item in enumerate(draft["images"], 1):
            with st.container(border=True):
                left, right = st.columns([1, 1.3])
                left.image(item["bytes"], caption=f"{i}. {item['name']}", width="stretch")
                right.caption(item["method"])
                for uncertainty in item["uncertainties"]:
                    right.warning(uncertainty)
                value = right.text_area(f"Reviewed text · page {i}", item["text"], height=420, max_chars=12000, key=f"image_text_{draft['id']}_{i}")
                edited.append({"id": f"image-{item['id']}", "name": item["name"], "page": i, "text": value.strip(),
                               "image_hash": item["id"], "transcription_method": item["method"], "uncertainties": item["uncertainties"]})
    title = st.text_input("Name this image-based course", value="My worksheet practice", max_chars=90, key=f"image_title_{draft['id']}")
    outline = local_outline(edited)
    topics = st.multiselect("Confirm practice topics", list(TOPICS), default=[i["topic"] for i in outline["topics"]],
                            format_func=lambda t: TOPICS[t]["name"], key=f"image_topics_{draft['id']}")
    with dashboard_tab:
        st.caption("Draft preview · check the transcript before confirming. Your edits refresh this summary.")
        summary_dashboard.render(edited, outline, topics=topics, key=f"image_{draft['id']}", owner=draft)
    checked = st.checkbox("I checked every transcript, corrected unclear symbols, and confirmed the practice topics.", key=f"image_checked_{draft['id']}")
    if st.button("Save reviewed course →", type="primary"):
        if not checked or not topics or not title.strip() or any(len(p["text"]) < 20 for p in edited):
            st.error("Add a title, at least 20 characters per page, select topics, and confirm your review.")
        elif len(st.session_state.workspace["courses"]) >= 10:
            st.error("This prototype supports up to 10 courses per workspace.")
        else:
            outline["method"] = "User-reviewed image text · local topic scan"
            course = make_course(title.strip(), edited, outline, topics)
            course["study_board"] = deepcopy(draft["study_board"])
            st.session_state.workspace["courses"].append(course)
            st.session_state.selected_course = course["id"]
            save()
            st.session_state.image_review = None
            go("Mock exams", "Reviewed image text saved. Build a fresh paper from the confirmed scope.")
    if st.button("Discard this image review"):
        st.session_state.image_review = None
        st.rerun()
