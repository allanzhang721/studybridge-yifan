"""Practilume — independent Streamlit application by Yifan Yan."""
from __future__ import annotations

import copy
import html
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from studybridge import ai, current_ui
from studybridge.catalog import TOPICS, SAMPLE_TEXT, SAMPLE_EXAM
from studybridge.engine import (new_workspace, make_course, local_outline, build_exam, grade_exam,
    topic_performance, calibration, preview_order, sandbox_totals, digest, identifier, now, exam_intact)
from studybridge.exports import exam_pdf
from studybridge.ledger import load_ledger, totals, csv_bytes
from studybridge.materials import collect_materials, pasted_pages
from studybridge.storage import Store, ConflictError
from studybridge.examples import EXAMPLES, example_course
from studybridge import worksheet_ui, demo_ui, summary_dashboard, impact_visuals
from studybridge import demo as demo_flow

st.set_page_config(page_title="Practilume | Learn Forward, Give Back", page_icon="🌱", layout="wide", initial_sidebar_state="auto")
st.markdown(f"<style>{(ROOT / 'assets/style.css').read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

for key, value in {"workspace": new_workspace(), "page": "Demo & examples" if st.query_params.get("demo") == "1" else "Overview", "username": None, "revision": 0,
                   "selected_course": None, "active_exam": None, "draft": None, "flash": None}.items():
    if key not in st.session_state:
        st.session_state[key] = value

# Keep already-open sessions working after merging the two destinations.
if st.session_state.page in ("Guided demo", "Example library"):
    if st.session_state.page == "Example library":
        st.session_state.guided_demo_view = "Topic examples"
    st.session_state.page = "Demo & examples"


def h(text):
    return html.escape(str(text))


def state():
    return st.session_state.workspace


def save():
    if st.session_state.username:
        st.session_state.save_pending = True
        try:
            st.session_state.revision = Store().save(st.session_state.username, state(), st.session_state.revision)
        except ConflictError:
            st.session_state.save_error = "Another tab saved changes first. Your unsaved work is still here. Export it before loading the saved version."
            st.rerun()
        except (OSError, sqlite3.Error, ValueError):
            st.session_state.save_error = "Saving failed. Your changes are still in this session. Retry saving or export a copy before leaving."
            st.rerun()
        else:
            st.session_state.save_pending = False
            st.session_state.save_error = None
            st.session_state.last_saved = now()


def save_recovery():
    if not st.session_state.get("save_pending"):
        return
    st.error(st.session_state.get("save_error") or "Your latest changes have not been saved.")
    st.download_button("Export unsaved work", json.dumps(state(), ensure_ascii=False, indent=2), "practilume-unsaved-records.json", "application/json")
    if st.button("Retry saving"):
        save()
        st.rerun()
    discard = st.checkbox("I have exported my unsaved changes and want to load the saved version.")
    if st.button("Load saved version", disabled=not discard):
        try:
            loaded, revision = Store().load(st.session_state.username)
        except (OSError, sqlite3.Error, ValueError):
            st.error("The saved workspace is unavailable. Your current work has been kept.")
            st.stop()
        st.session_state.workspace, st.session_state.revision = loaded, revision
        st.session_state.save_pending = False
        st.session_state.save_error = None
        st.session_state.selected_course, st.session_state.active_exam, st.session_state.draft = None, None, None
        st.rerun()
    st.stop()


def go(page, message=None):
    st.session_state.page = page
    st.session_state.flash = message
    st.rerun()


def header(eyebrow, title, description):
    st.markdown(f'<div class="eyebrow">{h(eyebrow)}</div><div class="page-title">{h(title)}</div><div class="page-sub">{h(description)}</div>', unsafe_allow_html=True)


def section(title):
    st.markdown(f'<div class="section-title">{h(title)}</div>', unsafe_allow_html=True)


def stat(label, value, detail):
    st.markdown(f'<div class="stat"><div class="stat-label">{h(label)}</div><div class="stat-value">{h(value)}</div><div class="stat-detail">{h(detail)}</div></div>', unsafe_allow_html=True)


def empty(message):
    st.markdown(f'<div class="empty">{h(message)}</div>', unsafe_allow_html=True)


def selected_course(key="course_selector"):
    courses = state()["courses"]
    if not courses:
        empty("Your next step starts with a course. Add your notes or try the sample course.")
        if st.button("Add a course", key=f"empty_{key}", type="primary"):
            go("My courses")
        return None
    ids = [c["id"] for c in courses]
    current = st.session_state.selected_course
    chosen = st.selectbox("Course", ids, index=ids.index(current) if current in ids else 0,
                          format_func=lambda cid: next(c["title"] for c in courses if c["id"] == cid), key=key)
    st.session_state.selected_course = chosen
    return next(c for c in courses if c["id"] == chosen)


def load_sample():
    sample = demo_flow.new_demo()
    demo_flow.load_images(sample, demo_flow.sample_files())
    demo_flow.confirm_course(sample, [image["text"] for image in sample["images"]])
    candidate = sample["course"]
    candidate["title"] = "Sample · Fractions, equations & graphs"
    existing = next((c for c in state()["courses"] if c["source_hash"] == candidate["source_hash"]), None)
    course = existing or candidate
    if not existing:
        if len(state()["courses"]) >= 10:
            st.error("This workspace already has the prototype's maximum of 10 courses.")
            return
        state()["courses"].append(course)
        save()
    st.session_state.selected_course = course["id"]
    st.session_state.library_course = course["id"]
    go("My courses", "The demo's three mistake worksheets are ready, with the same learning summary and chart. No example exam scores were added to your records.")


def use_ai_budget():
    if state()["ai_calls"] >= 20:
        raise ValueError("This workspace has reached the prototype's 20 AI-request limit. Local generation remains available.")
    state()["ai_calls"] += 1
    save()


with st.sidebar:
    st.markdown('<div class="brand"><div class="brand-mark">↗</div><div><div class="brand-name">Practilume</div><div class="brand-sub">LEARN FORWARD. GIVE BACK.</div></div></div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-label">YOUR STUDY SPACE</div>', unsafe_allow_html=True)
    for name, label in [("Overview", "◈  Overview"), ("Worksheet images", "▧  Worksheet images"), ("My courses", "▤  My courses"), ("Mock exams", "✎  Mock exams"),
                        ("Review & practice", "↻  Review & practice"), ("Impact ledger", "♡  Impact ledger"), ("Plans & account", "⚙  Plans & account")]:
        if st.button(label, key=f"nav_{name}", type="primary" if st.session_state.page == name else "secondary", width="stretch"):
            go(name)
    st.markdown('<div class="sidebar-label">WORKSPACE</div>', unsafe_allow_html=True)
    st.caption(f"Signed in as {st.session_state.username}" if st.session_state.username else "Guest workspace · session only")
    if st.session_state.get("save_pending"):
        st.caption("Not saved · your changes need attention")
    elif st.session_state.username:
        saved_at = st.session_state.get("last_saved")
        st.caption(f"Saved · {saved_at}" if saved_at else "Saved workspace loaded")
        st.caption("Confirmed courses, exams and submitted reviews save automatically.")
    else:
        st.caption("Accounts save on this server only. Export backups; cloud restarts can remove local records.")
    st.caption("Plus preview · no payment" if state()["plus_preview"] else "Free learning tools")
    st.caption("AI model: " + ai.configuration()[1] if ai.configured() else "Local demo · AI not connected")
    if st.button("Save & manage workspace", width="stretch"):
        go("Plans & account")
    st.markdown('<div class="sidebar-note">Small steps. Real understanding.<br>Free practice today, with a transparent plan to support education tomorrow.</div><div class="sidebar-author">Created by <b>Yifan Yan</b><br>An independent Explain It! extension</div>', unsafe_allow_html=True)

save_recovery()

if st.session_state.flash:
    st.success(st.session_state.flash)
    st.session_state.flash = None


def overview():
    st.markdown('<div class="eyebrow">YOUR NEXT CHAPTER STARTS HERE</div>', unsafe_allow_html=True)
    st.markdown('''<div class="hero"><div class="hero-copy"><span class="pill">A LITTLE MORE CLARITY. EVERY DAY.</span>
    <h1>Your course.<br>Your pace. Your next step.</h1><p>Turn class notes into focused practice. Build a mock exam, understand your mistakes, and make the next attempt count.</p></div>
    <svg class="hero-art" viewBox="0 0 220 220" aria-hidden="true"><circle cx="112" cy="115" r="90" fill="#d5e3c7"/><rect x="47" y="50" width="125" height="145" rx="12" fill="#fff" transform="rotate(-9 110 120)"/><rect x="62" y="38" width="125" height="145" rx="12" fill="#f6faef" stroke="#9fbea4"/><path d="M84 143 L105 120 L127 130 L163 85" fill="none" stroke="#087f6b" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/><path d="M149 85h14v14" fill="none" stroke="#087f6b" stroke-width="5"/><path d="M84 65h67M84 76h42" stroke="#c0d1b8" stroke-width="5" stroke-linecap="round"/><circle cx="179" cy="173" r="26" fill="#194d3b"/><path d="M168 173l8 8 15-17" stroke="#dbefc7" stroke-width="4" fill="none" stroke-linecap="round"/></svg></div>''', unsafe_allow_html=True)
    a, b, c = st.columns([1.2, 1.4, 1.4])
    if a.button("Start full demo →", type="primary", width="stretch"):
        st.session_state.guided_demo_view = "Complete worked example"
        go("Demo & examples")
    if b.button("Build my study space", width="stretch"):
        go("My courses")
    if c.button("Explore sample course", width="stretch"):
        load_sample()
    if st.button("Browse visual examples →", key="browse_examples"):
        st.session_state.guided_demo_view = "Topic examples"
        go("Demo & examples")
    if st.button("Try sample worksheet images →", key="browse_worksheets"):
        go("Worksheet images")
    st.write("")
    attempts = state()["attempts"]
    possible = sum(a["possible"] for a in attempts)
    accuracy = f"{round(100*sum(a['earned'] for a in attempts)/possible)}%" if possible else "—"
    try:
        public_ledger = load_ledger()
        donated = f"¥{totals(public_ledger)['sent_cents']/100:,.2f}"
        donation_detail = "Public ledger · excludes previews"
    except (ValueError, KeyError, OSError):
        donated, donation_detail = "—", "Ledger unavailable · figures withheld"
    for col, values in zip(st.columns(4), [("Your courses", len(state()["courses"]), "Your materials, organised"),
        ("Mock exams", len(state()["exams"]), "Saved before you take them"), ("Practice accuracy", accuracy, "From completed practice only"),
        ("Live donations", donated, donation_detail)]):
        with col:
            stat(*values)
    left, right = st.columns([1.7, 1], gap="large")
    with left:
        section("Pick up where you left off")
        if state()["courses"]:
            for course in state()["courses"][-3:]:
                tags = "".join(f'<span class="tag">{h(TOPICS[t]["name"])}</span>' for t in course["topics"])
                st.markdown(f'<div class="course-card"><span class="course-icon">▤</span><h3>{h(course["title"])}</h3><p>{len(course["pages"])} source sections · {len(course["topics"])} confirmed topics</p>{tags}</div>', unsafe_allow_html=True)
                if st.button("Continue this course →", key=f"continue_{course['id']}"):
                    st.session_state.selected_course = course["id"]
                    go("Mock exams")
        else:
            st.markdown('<div class="course-card"><span class="course-icon">▤</span><h3>A fresh page for your learning.</h3><p>Add your class notes, revision outline, or a text-based PDF. Start with a sample if you just want to see how it works.</p><span class="tag">PDF</span><span class="tag">TXT</span><span class="tag">MARKDOWN</span></div>', unsafe_allow_html=True)
    with right:
        section("A clearer way to prepare")
        for number, title, text in [("01", "Find your focus", "Organise the course and identify what needs practice."),
            ("02", "Try a fresh paper", "Generate checked maths questions within your confirmed scope."),
            ("03", "Learn from the attempt", "Review worked answers and practise new variations.")]:
            st.markdown(f'<div class="step"><span class="step-number">{number}</span><div><b>{title}</b><p>{text}</p></div></div>', unsafe_allow_html=True)
        st.markdown('<div class="notice">Built with purpose. Our proposed study-pack model supports education projects with a public donation ledger. Payment collection has not launched.</div>', unsafe_allow_html=True)


def examples_page():
    st.subheader("One topic. A little more clarity.")
    st.caption("Explore a visual lesson, reveal its worked solution, then practise with new questions. These prepared examples use no AI calls.")
    worked_math = {
        "fractions": (r"\frac{1}{3}+\frac{1}{4}\ne\frac{2}{7}", r"\frac{1}{3}+\frac{1}{4}=\frac{4}{12}+\frac{3}{12}=\frac{7}{12}", "Use equal-sized parts before adding."),
        "graphs": (r"y=2x+1,\quad x=4", r"y=2\times4+1=9", "The slope is 2; the y-intercept is 1."),
        "probability": (r"P(\text{even})=?", r"P(\text{even})=\frac{3}{6}=\frac{1}{2}", "The favourable outcomes are 2, 4 and 6 out of six equally likely outcomes."),
    }
    with st.expander("About the demo engine and optional AI"):
        configured_key, configured_model = ai.configuration()
        if configured_key and configured_model:
            st.write(f"**Configured AI model:** `{configured_model}`")
            st.caption("Configuration detected. This status does not verify account access or a successful API request.")
        else:
            st.write("**Current mode: local maths engine. No AI model is connected.**")
            st.caption("Topic scanning, question generation and answer checking work locally. Optional AI features need the operator's API key and model setting.")
        st.markdown("**Suggested starting model:** [`gpt-6-luna`](https://developers.openai.com/api/docs/models/gpt-6-luna). It supports text/image input and structured outputs. Test its explanations on your course material before choosing a production model.")
        st.write("AI is used for organising text, transcribing worksheet images for your review, and explaining mistakes. The local engine computes and verifies the supported numerical answers.")
    st.caption("The previews below are original Practilume illustrations. The source buttons open the separately credited online pictures. Loading an example uses prepared text; it does not run OCR or make an AI request.")
    for example in EXAMPLES:
        with st.container(border=True):
            visual, content = st.columns([1.15, 1], gap="large")
            with visual:
                st.image(example["svg"], width="stretch")
                st.caption("Practilume illustration · " + example["description"])
            with content:
                st.markdown(f"#### {example['title']}")
                st.latex(worked_math[example["id"]][0])
                with st.expander("See the worked example"):
                    st.latex(worked_math[example["id"]][1])
                    st.write(worked_math[example["id"]][2])
                if st.button("Practise this topic →", key=f"example_{example['id']}", type="primary"):
                    course = example_course(example)
                    existing = next((c for c in state()["courses"] if c["source_hash"] == course["source_hash"]), None)
                    if existing is None and len(state()["courses"]) >= 10:
                        st.error("This workspace already has the prototype's maximum of 10 courses.")
                    else:
                        if existing is None:
                            state()["courses"].append(course)
                            save()
                        st.session_state.selected_course = (existing or course)["id"]
                        go("Mock exams", "Checked example notes loaded. Confirm the scope to generate five fresh questions.")
                st.link_button("Open the online reference picture ↗", example["source"])
                st.caption(example["reference_title"] + " · " + example["credit"])
                st.markdown(f"[Reference image licence]({example['license_url']})")
                with st.expander("Read or download the example notes"):
                    st.write(example["notes"])
                    st.download_button("Download checked notes", example["notes"], f"practilume-{example['id']}.txt", "text/plain", key=f"notes_{example['id']}")
    st.caption("These are learning references, not partnerships or evidence of educational impact. External pictures open on their original websites.")


def courses_page():
    header("01 / FIND YOUR FOCUS", "Make your course your own.", "Bring the material you already study. Confirm the scope, then turn it into a clear next step.")
    library_tab, add_tab = st.tabs(["My course library", "Add materials"])
    with add_tab:
        if st.button("Have worksheet photos? Open image import →"):
            go("Worksheet images")
        with st.container(border=True):
            st.markdown("#### Start with your classroom materials")
            st.caption("PDF, TXT or Markdown · 8 MB per file · 40,000 characters per import. Text-based PDFs only. Use image import above for PNG/JPEG pages.")
            title = st.text_input("Course title", placeholder="e.g. Year 9 mathematics · autumn term", key="import_title", max_chars=90)
            files = st.file_uploader("Upload course materials", type=["pdf", "txt", "md"], accept_multiple_files=True, key="course_uploads")
            notes = st.text_area("Or paste your notes / exam scope", height=160, key="course_notes", placeholder="Include the topics, examples, and any assessment requirements...")
            ai_on = st.checkbox("Use AI to organise these materials", disabled=not ai.configured(), key="outline_ai")
            if ai_on:
                consent = st.checkbox("Send this material to the configured AI provider for analysis", key="outline_consent")
            else:
                consent = True
                st.caption("Local scan is available without an API connection. Confirm its keyword matches yourself.")
            if st.button("Analyse materials", type="primary", disabled=not consent):
                try:
                    if not title.strip():
                        raise ValueError("Give your course a title first.")
                    pages = collect_materials(files, notes)
                    with st.spinner("Organising topics and checking sources…"):
                        if ai_on:
                            use_ai_budget()
                        outline = ai.analyze(pages) if ai_on else local_outline(pages)
                    st.session_state.draft = {"title": title, "pages": pages, "outline": outline, "id": identifier()}
                except ValueError as exc:
                    st.error(str(exc))
        draft = st.session_state.draft
        if draft:
            topics = st.multiselect("Confirm supported topics", list(TOPICS), default=[i["topic"] for i in draft["outline"]["topics"]],
                                    format_func=lambda t: TOPICS[t]["name"], key=f"draft_topics_{draft['id']}")
            summary_dashboard.render(draft["pages"], draft["outline"], topics=topics, key=f"draft_{draft['id']}", owner=draft)
            st.caption("Selected topics can be added manually. The exam bank covers a limited set of short numerical skills, not every topic in a school syllabus.")
            if st.button("Save course", type="primary", disabled=not topics):
                try:
                    if len(state()["courses"]) >= 10:
                        raise ValueError("This prototype supports up to 10 courses per workspace.")
                    course = make_course(draft["title"], draft["pages"], draft["outline"], topics)
                    course["study_board"] = copy.deepcopy(draft["study_board"])
                    state()["courses"].append(course)
                    st.session_state.selected_course = course["id"]
                    st.session_state.draft = None
                    save()
                    go("Mock exams", "Course saved. Choose your scope and build your first paper.")
                except ValueError as exc:
                    st.error(str(exc))
    with library_tab:
        if st.button("Load sample maths course", type="primary" if not state()["courses"] else "secondary"):
            load_sample()
        if not state()["courses"]:
            empty("No courses yet. Add your own material in the next tab, or start with a fictional sample.")
            return
        course = selected_course("library_course")
        report_tab, practice_tab, materials_tab = st.tabs(["Learning report", "Practice", "Materials"])
        course_exam_ids = {e["id"] for e in state()["exams"] if e["course_id"] == course["id"]}
        course_attempts = [a for a in state()["attempts"] if a["exam_id"] in course_exam_ids]
        assessments = [("Latest saved attempt", course_attempts[-1])] if course_attempts else None
        with report_tab:
            summary_dashboard.render(course["pages"], course["outline"], topics=course["topics"],
                                     key=f"course_{course['id']}", owner=course, save=save, assessments=assessments)
        with practice_tab:
            section("Your confirmed topics")
            performance = topic_performance(state(), course["id"])
            for t in course["topics"]:
                p = performance[t]
                with st.container(border=True):
                    st.markdown(f"**{TOPICS[t]['icon']}  {TOPICS[t]['name']}**")
                    st.caption(TOPICS[t]["tip"])
                    if p["count"]:
                        st.progress(p["correct"]/p["count"], text=f"{p['correct']} / {p['count']} practice answers correct · limited evidence")
                    else:
                        st.caption("Not assessed yet — try a short mock exam.")
            if st.button("Create a mock exam →", type="primary"):
                go("Mock exams")
            with st.expander("Add a previous mistake"):
                with st.form(f"mistake_{course['id']}"):
                    t = st.selectbox("Topic", course["topics"], format_func=lambda t: TOPICS[t]["name"])
                    text = st.text_area("Question and what went wrong", max_chars=2000)
                    if st.form_submit_button("Add to my practice priorities"):
                        if len(text.strip()) < 10:
                            st.error("Add a little more detail about the mistake.")
                        else:
                            state()["mistakes"].append({"id": identifier(), "course_id": course["id"], "topic": t, "text": text, "created": now()})
                            save()
                            go("Review & practice", "Mistake saved as a personal practice priority.")
        with materials_tab:
            section("Source notebook")
            for p in course["pages"]:
                with st.expander(f"{p['name']} · page {p['page']}"):
                    st.text(p["text"])
            st.caption(f"Source version {course['source_hash'][:12]}")
            with st.expander("Update next exam scope"):
                with st.form(f"scope_{course['id']}"):
                    revised = st.multiselect("Upcoming topics", list(TOPICS), default=course["topics"], format_func=lambda t: TOPICS[t]["name"])
                    extra = st.text_area("New scope note (optional)", max_chars=5000)
                    if st.form_submit_button("Save upcoming scope"):
                        if revised:
                            course["topics"] = revised
                            if extra.strip():
                                course["pages"].append({"id": f"scope-{identifier()}", "name": "Updated exam scope", "page": 1, "text": extra.strip()})
                            course["source_hash"] = digest(course["pages"])
                            course["outline"] = local_outline(course["pages"])
                            save()
                            go("My courses", "Upcoming scope updated. Previous exam snapshots stay unchanged.")
                        else:
                            st.error("Select at least one topic.")



def exams_page():
    header("02 / PRACTISE WITH PURPOSE", "A fresh paper. A clearer picture.", "Build a practice exam from your confirmed scope. Answers are computed and checked before the paper is saved.")
    course = selected_course("exam_course")
    if not course:
        return
    build_tab, take_tab, calibrate_tab = st.tabs(["Build a paper", "Take an exam", "After the real exam"])
    with build_tab:
        left, right = st.columns([1.65, 1], gap="large")
        with left, st.container(border=True):
            st.markdown("#### Your exam blueprint")
            with st.form("exam_blueprint"):
                topics = st.multiselect("Topics in this exam", course["topics"], default=course["topics"], format_func=lambda t: TOPICS[t]["name"])
                mode = st.radio("Purpose", ["Exam simulation", "Targeted practice"], horizontal=True)
                a, b = st.columns(2)
                count = a.select_slider("Questions", options=[5, 8, 12, 16], value=5)
                minutes = b.select_slider("Time guide", options=[10, 20, 30, 40, 60], value=20)
                difficulty = st.selectbox("Difficulty", ["Foundation", "Challenge"])
                mix = st.checkbox("Mix multiple-choice and short-answer questions", value=True)
                calibrated = st.checkbox("Use previously reviewed real exams to adjust topic balance", value=True)
                confirmed = st.checkbox("I have checked that these topics match my current exam scope.")
                submitted = st.form_submit_button("Generate my mock exam", type="primary", width="stretch")
            if submitted:
                try:
                    if not confirmed:
                        raise ValueError("Confirm the current exam scope first.")
                    if count > 5 and not state()["plus_preview"]:
                        raise ValueError("The free short mock has 5 questions. Open Plans & account to try the free Plus preview; no payment is collected.")
                    exam = build_exam(course, state(), topics, count, minutes, difficulty, mode, mix, calibrated)
                    state()["exams"].append(exam)
                    st.session_state.active_exam = exam["id"]
                    save()
                    st.success("Your paper is ready. Open the ‘Take an exam’ tab.")
                except ValueError as exc:
                    st.error(str(exc))
        with right:
            section("Designed for useful practice")
            st.markdown("**Scope first.** Your current course selection always takes priority over past papers.\n\n**Fresh variations.** Previously generated question wording is excluded within this course.\n\n**Checkable answers.** This version uses a bounded mathematical question bank with exact final-answer grading.")
            st.info("These are practice papers, not predicted original exam questions. Similar difficulty between papers is not statistically calibrated.")
            n = sum(c["course_id"] == course["id"] for c in state()["calibrations"])
            st.caption(f"{n} real-exam review(s) available for future topic balancing.")
    with take_tab:
        exams = [e for e in state()["exams"] if e["course_id"] == course["id"]]
        if not exams:
            empty("Build your first paper in the previous tab. It will appear here.")
        else:
            ids = [e["id"] for e in reversed(exams)]
            active = st.session_state.active_exam
            eid = st.selectbox("Saved paper", ids, index=ids.index(active) if active in ids else 0,
                format_func=lambda eid: next(f"{e['created'][:16].replace('T',' ')} · {len(e['questions'])} questions · {e['mode']} · {eid[:5]}" for e in exams if e["id"] == eid))
            exam = next(e for e in exams if e["id"] == eid)
            render_exam(exam)
    with calibrate_tab:
        calibration_ui(course)


def render_exam(exam):
    if not exam_intact(exam):
        st.error("The saved exam did not pass its snapshot check. Export your records and contact the operator.")
        return
    attempt = next((a for a in state()["attempts"] if a["exam_id"] == exam["id"]), None)
    a, b, c = st.columns(3)
    a.metric("Questions", len(exam["questions"]))
    b.metric("Time guide", f"{exam['minutes']} min")
    c.metric("Marks", sum(q["marks"] for q in exam["questions"]))
    st.caption("Untimed practice · final-answer marks only. Submit once; use a fresh paper for a clean retest.")
    st.download_button("↓ Download student paper", exam_pdf(exam), file_name=f"practilume-{exam['id'][:6]}-paper.pdf", mime="application/pdf", key=f"paper_{exam['id']}")
    with st.expander("View saved blueprint & evidence"):
        st.dataframe([{"Topic": TOPICS[t]["name"], "Questions": n} for t, n in exam["distribution"].items()], hide_index=True, width="stretch")
        st.caption(f"Frozen {exam['created']} · fingerprint {exam['fingerprint'][:24]}")
        st.caption(f"Calibration records used: {len(exam['history_ids'])}. This local fingerprint detects accidental changes; it is not external notarisation.")
        for item in exam["evidence"]:
            if item["topic"] in exam["topics"]:
                st.write(f"**{TOPICS[item['topic']]['name']}** — {item['source_id']}")
                st.text(item["quote"])
    if attempt:
        st.success(f"Completed · {attempt['earned']} / {attempt['possible']} marks. Open Review & practice for your next steps.")
        st.download_button("↓ Download answer key", exam_pdf(exam, answers=True), file_name=f"practilume-{exam['id'][:6]}-answers.pdf", mime="application/pdf", key=f"key_{exam['id']}")
        if st.button("Review this attempt →", type="primary"):
            st.session_state.active_exam = exam["id"]
            go("Review & practice")
        return
    with st.form(f"take_{exam['id']}"):
        answers = {}
        for i, q in enumerate(exam["questions"], 1):
            st.markdown(f'<div class="question-number">QUESTION {i:02d} · {h(TOPICS[q["topic"]]["name"])} · {q["marks"]} MARKS</div><div class="question-prompt">{h(q["prompt"])}</div>', unsafe_allow_html=True)
            if q["choices"]:
                answers[q["id"]] = st.radio(f"Answer {i}", q["choices"], index=None, horizontal=True, key=f"answer_{q['id']}") or ""
            else:
                answers[q["id"]] = st.text_input(f"Answer {i}", placeholder="e.g. 5, -2, 3/4 or 50%", key=f"answer_{q['id']}", max_chars=60)
            st.write("")
        ready = st.checkbox("I am ready to submit. Blank answers will receive zero marks.")
        if st.form_submit_button("Submit & see my next steps", type="primary", width="stretch"):
            if not ready:
                st.error("Confirm you are ready to submit.")
            else:
                result = grade_exam(exam, answers)
                state()["attempts"].append(result)
                save()
                st.session_state.active_exam = exam["id"]
                go("Review & practice", "Attempt saved. Let’s turn it into a useful next step.")


def calibration_ui(course):
    st.markdown("#### Help your next mock reflect the course")
    st.write("After the real exam, attach its text and enter the marks allocated to each topic. We compare this with a previously saved simulation and keep both versions.")
    exams = [e for e in state()["exams"] if e["course_id"] == course["id"] and e["mode"] == "Exam simulation"
             and not any(c["exam_id"] == e["id"] for c in state()["calibrations"])]
    if exams:
        with st.form("calibration"):
            eid = st.selectbox("Compare with this pre-exam snapshot", [e["id"] for e in exams], format_func=lambda eid: next(f"{e['created'][:16]} · {eid[:6]}" for e in exams if e["id"] == eid))
            label = st.text_input("Real exam label", placeholder="e.g. October unit test", max_chars=100)
            files = st.file_uploader("Real exam (PDF / TXT / MD)", type=["pdf", "txt", "md"], accept_multiple_files=True, key="real_exam_files")
            text = st.text_area("Or paste the exam text", height=110, max_chars=40000)
            st.caption("Enter total marks per topic, not your own score. Unsupported topics are outside this comparison; do not relabel them as a supported topic.")
            marks = {}
            cols = st.columns(3)
            for i, t in enumerate(TOPICS):
                marks[t] = cols[i % 3].number_input(TOPICS[t]["name"] + " marks", min_value=0, max_value=500, value=0, step=1, key=f"actual_{t}")
            note = st.text_input("Notes about changed scope or unsupported topics", max_chars=1500)
            checked = st.checkbox("This is a post-exam review. I checked the topic marks against the attached paper.")
            if st.form_submit_button("Save review & update future papers", type="primary"):
                try:
                    if not checked or not label.strip():
                        raise ValueError("Add a label and confirm that you checked the marks.")
                    pages = collect_materials(files, text, "Post-exam source")
                    exam = next(e for e in exams if e["id"] == eid)
                    review = calibration(exam, marks, label, pages, note)
                    state()["calibrations"].append(review)
                    save()
                    go("Mock exams", "Review saved. It can inform future papers; the original snapshot has not changed.")
                except ValueError as exc:
                    st.error(str(exc))
    else:
        st.info("Create an exam-simulation paper first. Each snapshot can have one post-exam review.")
    st.download_button("Download a fictional post-exam sample", SAMPLE_EXAM, "fictional-post-exam.txt", "text/plain")
    reviews = [c for c in state()["calibrations"] if c["course_id"] == course["id"]]
    if reviews:
        section("Your calibration record")
        st.dataframe([{"Real exam": c["label"], "Supported-mark coverage (%)": c["coverage"],
                       "Distribution error (pp) ↓": c["distribution_error"], "Uniform baseline error (pp) ↓": c["baseline_error"],
                       "Missed topics": ", ".join(TOPICS[t]["name"] for t in c["missed"]) or "None",
                       "Extra topics": ", ".join(TOPICS[t]["name"] for t in c["extra"]) or "None"} for c in reviews], hide_index=True, width="stretch")
        st.caption("Distribution error is half the sum of absolute topic-share differences, in percentage points. Lower is closer. Coverage alone can be inflated by including every topic. Comparisons cover only the supported marks you entered; they do not prove question prediction or learning impact.")
        for review in reviews:
            with st.expander(f"Source & update record · {review['label']}"):
                st.caption(f"Saved {review['created']} · original fingerprint {review['exam_fingerprint'][:20]}")
                st.write(review["note"] or "No scope change noted.")
                st.json(review["actual_marks"])
                for page in review["pages"]:
                    st.text(page["text"])


def review_page():
    header("03 / MAKE THE NEXT ATTEMPT COUNT", "Mistakes are a starting point.", "See the worked solution, find the step that needs attention, and try a fresh variation.")
    course = selected_course("review_course")
    if not course:
        return
    performance = topic_performance(state(), course["id"])
    rows = [{"Topic": TOPICS[t]["name"], "Correct": p["correct"], "Attempted": p["count"],
             "Accuracy (%)": round(100*p["correct"]/p["count"]) if p["count"] else None} for t, p in performance.items() if p["count"]]
    if rows:
        st.dataframe(rows, hide_index=True, width="stretch")
        st.caption("Practice evidence only. These percentages are not a prediction of your real exam score.")
    exams = {e["id"]: e for e in state()["exams"] if e["course_id"] == course["id"]}
    attempts = [a for a in state()["attempts"] if a["exam_id"] in exams]
    if attempts:
        active = st.session_state.active_exam
        ids = [a["id"] for a in reversed(attempts)]
        default = next((a["id"] for a in attempts if a["exam_id"] == active), ids[0])
        aid = st.selectbox("Completed attempt", ids, index=ids.index(default), format_func=lambda aid: next(f"{a['created'][:16]} · {a['earned']}/{a['possible']} marks · {a['id'][:5]}" for a in attempts if a["id"] == aid))
        attempt = next(a for a in attempts if a["id"] == aid)
        exam = exams[attempt["exam_id"]]
        if not exam_intact(exam):
            st.error("This exam snapshot changed; review has been paused.")
            return
        st.download_button("Download worked answer key", exam_pdf(exam, True), f"answers-{exam['id'][:6]}.pdf", "application/pdf")
        for i, (q, result) in enumerate(zip(exam["questions"], attempt["results"]), 1):
            with st.expander(f"{'✓' if result['correct'] else '↻'}  Question {i} · {TOPICS[q['topic']]['name']} · {result['earned']}/{result['possible']} marks", expanded=not result["correct"]):
                st.write(q["prompt"])
                st.write(f"**Your answer:** {result['submitted'] or 'No answer'}  ·  **Correct answer:** {q['answer']}")
                if result["issue"]:
                    st.caption(result["issue"])
                for j, step in enumerate(q["steps"], 1):
                    st.write(f"{j}. {step}")
                st.info(TOPICS[q["topic"]]["tip"])
                if ai.configured():
                    working = st.text_area("Share your working for an AI explanation (optional)", key=f"working_{q['id']}", max_chars=3000)
                    consent = st.checkbox("Send this question and my working to the AI provider", key=f"coach_consent_{q['id']}")
                    if st.button("Explain my possible mistake", key=f"coach_{q['id']}", disabled=not consent):
                        try:
                            use_ai_budget()
                            with st.spinner("Thinking through your working…"):
                                result["coaching"] = ai.coach(q, result["submitted"], working)
                            save()
                        except ValueError as exc:
                            st.error(str(exc))
                    if result.get("coaching"):
                        advice = result["coaching"]
                        st.write(advice["observation"])
                        for step in advice["next_steps"]:
                            st.write("• " + step)
                        st.write("**Think about:** " + advice["check_question"])
                        st.caption(advice["uncertainty"])
    else:
        empty("Complete a mock exam to see worked answers and your own practice history.")
    mistakes = [m for m in state()["mistakes"] if m["course_id"] == course["id"]]
    for mistake in mistakes:
        with st.expander("Your saved mistake · " + TOPICS[mistake["topic"]]["name"]):
            st.text(mistake["text"])
    if attempts or mistakes:
        if st.button("Build a fresh 5-question practice set", type="primary"):
            priorities = []
            for t in course["topics"]:
                p = performance[t]
                score = (1-p["correct"]/p["count"] if p["count"] else 0.5) + sum(m["topic"] == t for m in mistakes)
                priorities.append((score, t))
            focused = [t for _, t in sorted(priorities, reverse=True)[:3]]
            exam = build_exam(course, state(), focused, 5, 20, "Foundation", "Targeted practice", False, False)
            state()["exams"].append(exam)
            st.session_state.active_exam = exam["id"]
            save()
            go("Mock exams", "Fresh practice is ready in ‘Take an exam’. Previous wording has been excluded.")


def impact_page():
    header("LEARNING WITH A PURPOSE", "Every contribution, accounted for.", "A public record of what is promised, what is transferred, and what evidence is available.")
    try:
        ledger = load_ledger()
    except (ValueError, KeyError, OSError) as exc:
        st.error("The public ledger could not be validated. Figures are withheld until the operator fixes the record.")
        return
    total = totals(ledger)
    st.info(ledger["status"])
    impact_visuals.live_trail(ledger, total)
    record, principles, feedback = st.tabs(["Public ledger", "Blockchain & proof", "Questions & responses"])
    with record:
        st.write(ledger["policy"])
        if ledger["batches"]:
            st.dataframe(ledger["batches"], hide_index=True, width="stretch")
            for batch in ledger["batches"]:
                with st.expander(f"Evidence · {batch['id']}"):
                    for key, label in [("project_url", "Official project"), ("receipt_url", "Transfer evidence"), ("confirmation_url", "Recipient confirmation"), ("report_url", "Implementation report")]:
                        if batch.get(key):
                            st.link_button(label, batch[key])
        else:
            empty("No live batches yet. There is no selected recipient, collected payment, or completed donation to report.")
        a, b = st.columns(2)
        a.download_button("Download public ledger · CSV", csv_bytes(ledger["batches"]), "practilume-public-ledger.csv", "text/csv", width="stretch")
        b.download_button("Download ledger & history · JSON", json.dumps(ledger, indent=2), "practilume-public-ledger.json", "application/json", width="stretch")
        st.caption("Local record checksum: " + digest(ledger)[:24] + ". A checksum alone is not independent proof or a blockchain record.")
        with st.expander("Corrections and reconciliation history"):
            if ledger["corrections"]:
                st.json(ledger["corrections"])
            else:
                st.caption("No corrections recorded.")
        if state()["sandbox_orders"]:
            section("Your private sandbox preview")
            preview = sandbox_totals(state()["sandbox_orders"])
            st.warning(f"Simulation only: {preview['orders']} eligible preview order(s), ¥{preview['pledged_cents']/100:.2f} hypothetical accrual, ¥0 transferred. These values are excluded from every live total.")
            for order in state()["sandbox_orders"]:
                cols = st.columns([3, 1])
                cols[0].caption(f"Preview {order['id'][:6]} · {'refunded in sandbox' if order['refunded'] else 'hypothetical ¥3 accrual'}")
                if cols[1].button("Simulate refund", key=f"refund_{order['id']}", disabled=order["refunded"]):
                    order["refunded"] = True
                    save()
                    st.rerun()
    with feedback:
        st.caption("Questions are private until an operator reviews and publishes them with a response. Public posts do not show your username. There are no verified recipient accounts in this version.")
        if st.session_state.username:
            with st.form("public_question"):
                body = st.text_area("Ask about the ledger or report an inconsistency", max_chars=1500)
                consent = st.checkbox("I agree to publication of this question without my username. I have not included personal information.")
                if st.form_submit_button("Submit for review"):
                    try:
                        if not consent:
                            raise ValueError("Please confirm that this question can be published without your username.")
                        number = Store().submit_feedback(st.session_state.username, body)
                        st.success(f"Question #{number} saved for review.")
                    except ValueError as exc:
                        st.error(str(exc))
        else:
            st.info("Create a private workspace account to submit a question. Published responses are visible to everyone.")
        posts = Store().feedback(st.session_state.username)
        if not posts:
            empty("No published questions yet.")
        for post in posts:
            with st.container(border=True):
                st.caption(f"Question #{post['id']} · {post['created'][:10]} · {post['status']}")
                st.write(post["body"])
                for created, role, reply in post["replies"]:
                    st.markdown(f"**{role}** · {created[:10]}")
                    st.write(reply)
    with principles:
        impact_visuals.render_proof_demo()


def account_page():
    header("ROOM TO GROW", "A useful free start. More when you need it.", "Explore the complete learning workflow. Paid checkout is not enabled; Plus can be tried through a clearly marked sandbox preview.")
    left, right = st.columns(2, gap="large")
    with left, st.container(border=True):
        st.markdown("#### Free learning")
        st.markdown('<div class="price">¥0 <small>/ start learning</small></div>', unsafe_allow_html=True)
        st.markdown("✓ Course material organiser\n\n✓ Five-question mock exams\n\n✓ Checked final answers and worked solutions\n\n✓ Personal mistake notebook\n\n✓ Basic real-exam review")
        if st.button("Continue with free learning", width="stretch"):
            go("My courses")
    with right, st.container(border=True):
        st.markdown("#### Study pack · pricing proposal")
        st.markdown('<div class="price">¥29 <small>/ proposed pack</small></div>', unsafe_allow_html=True)
        st.markdown("✓ Everything in Free\n\n✓ Longer papers, up to 16 questions\n\n✓ Fresh variations and targeted practice\n\n✓ Downloadable papers and answer keys\n\n♡ Proposed ¥3 allocation to education projects")
        st.caption("No payment. No actual donation. Preview records stay in your private sandbox.")
        if st.button("Try Plus preview · no payment", type="primary", width="stretch", disabled=state()["plus_preview"]):
            preview_order(state())
            save()
            go("Mock exams", "Plus preview enabled. A hypothetical order was added to your private sandbox; no funds were collected.")
        if state()["plus_preview"]:
            st.success("Plus preview is active.")
    section("Your private workspace")
    st.caption("Public prototype: saved work uses this server's local storage and may be lost when the app restarts or redeploys. Export your learning records to keep a copy.")
    if st.session_state.username:
        st.write(f"Signed in as **{st.session_state.username}**. Course text and study records are saved in this app's local database.")
        cols = st.columns(2)
        cols[0].download_button("Export my learning records", json.dumps(state(), ensure_ascii=False, indent=2), "practilume-my-records.json", "application/json", width="stretch")
        if cols[1].button("Sign out", width="stretch"):
            logout()
        with st.expander("Delete my account and learning records"):
            confirm = st.checkbox("Delete my saved courses, attempts and feedback from this app. I have exported anything I need.")
            if st.button("Delete my local account", disabled=not confirm):
                Store().delete_account(st.session_state.username)
                logout()
    else:
        st.info("Guest records last for this browser session. Create an account to save them locally on the app server, or export a copy. No email address is needed.")
        sign_in, register = st.tabs(["Sign in", "Create workspace"])
        with sign_in, st.form("sign_in"):
            username = st.text_input("Username", key="login_username", max_chars=24)
            password = st.text_input("Password", type="password", key="login_password", max_chars=128)
            st.caption("Signing in loads that account's saved records. Export guest work first if you want to keep it.")
            if st.form_submit_button("Sign in", type="primary"):
                try:
                    user = Store().authenticate(username, password)
                    loaded, revision = Store().load(user)
                    st.session_state.username, st.session_state.workspace, st.session_state.revision = user, loaded, revision
                    st.session_state.selected_course, st.session_state.active_exam, st.session_state.draft = None, None, None
                    st.session_state.image_review = None
                    go("Overview", "Welcome back. Your saved workspace is ready.")
                except ValueError as exc:
                    st.error(str(exc))
        with register, st.form("register"):
            username = st.text_input("Choose a username", key="new_username", max_chars=24)
            password = st.text_input("Choose a password (10+ characters)", type="password", key="new_password", max_chars=128)
            again = st.text_input("Repeat password", type="password", key="new_password_again", max_chars=128)
            consent = st.checkbox("Save my current guest study records to this private local account.")
            if st.form_submit_button("Create workspace", type="primary"):
                try:
                    if password != again or not consent:
                        raise ValueError("Passwords must match, and you must agree to save the workspace.")
                    user = Store().register(username, password)
                    st.session_state.username, st.session_state.revision = user, 0
                    save()
                    go("Overview", "Your workspace is saved. Keep your password; email recovery is not implemented in this local prototype.")
                except ValueError as exc:
                    st.error(str(exc))
        st.download_button("Export guest learning records", json.dumps(state(), ensure_ascii=False, indent=2), "practilume-guest-records.json", "application/json")
    with st.expander("Privacy, AI and prototype scope"):
        st.write("Raw uploaded files are processed in memory. Extracted text and learning records are stored locally only for signed-in accounts. Guest sessions are not saved as accounts. Other users cannot browse your courses. Public ledger questions are moderated separately.")
        st.write("Optional AI analysis sends the selected text or worksheet images to OpenAI only after you check the relevant consent box. Responses use store=False; this is not a promise of zero provider retention. The operator supplies credentials, and students never enter API keys.")
        st.write("This release covers five bounded maths skill families with exact final-answer grading. Image transcription requires your review; it is not automatic handwriting grading. It does not provide human marking, live payments, verified charity onboarding, or blockchain settlement. Local accounts have no email recovery; a production deployment needs persistent storage, backups, HTTPS and stronger account operations.")
        st.caption("AI assistance: " + ("configured by the operator" if ai.configured() else "not configured · local tools remain available"))


def logout():
    for key in list(st.session_state):
        del st.session_state[key]
    st.rerun()


def demo_page():
    with st.container(key="demo_hub"):
        demo_ui.render(go, examples_page)


render_page = {"Overview": lambda: current_ui.overview(state(), go, demo_page, load_sample), "Demo & examples": lambda: current_ui.overview(state(), go, demo_page, load_sample), "Worksheet images": lambda: current_ui.upload(state(), save, go, use_ai_budget), "My courses": lambda: current_ui.courses(state(), save), "Mock exams": lambda: current_ui.exams(state(), save, use_ai_budget),
 "Review & practice": review_page, "Impact ledger": current_ui.impact, "Plans & account": account_page}[st.session_state.page]
with st.empty().container():
    render_page()
st.markdown('<div class="footer">PRACTILUME · Created by Yifan Yan · Learn at your pace. Make your next step count.</div>', unsafe_allow_html=True)
