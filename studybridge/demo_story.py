"""A complete, visible worked journey with real generated outputs."""
import json

import streamlit as st

from . import math_ui, summary_dashboard
from .catalog import TOPICS
from .engine import exam_intact
from .exports import exam_pdf


def stage(number, title, description):
    st.subheader(title, anchor=f"demo-stage-{number}")
    st.caption(description)


def render(demo):
    st.markdown('''<nav class="demo-jump" aria-label="Walkthrough sections">
    <a href="#demo-stage-1">Materials</a><a href="#demo-stage-3">Mock exam</a>
    <a href="#demo-stage-4">Feedback</a><a href="#demo-stage-6">Next paper</a>
    <a href="#demo-stage-7">Giving</a></nav>''', unsafe_allow_html=True)
    st.caption("Prepared image transcripts and supplied student answers. Papers are generated and marked locally; all money figures are simulations.")
    with st.container(border=True, key="story_materials"):
        stage(1, "Start with your study pages", "INPUT · Three fictional revision pages: a conceptual error, a procedure error and an interpretation error.")
        for col, image, name in zip(st.columns(3), demo["images"], ["Fractions", "Equations", "Linear graphs"]):
            with col:
                st.image(image["bytes"], width=180)
                st.markdown(f"**{name}**")
                st.download_button("Download PNG", image["bytes"], image["name"], "image/png", key=f"story_image_{name}")
    with st.container(border=True):
        stage(2, "Summarise the work, not just the topics", "REVIEW · Three distinct errors become three concrete learning actions.")
        summary_dashboard.render(demo["course"]["pages"], demo["course"]["outline"], topics=demo["course"]["topics"],
                                 key="worked_demo", owner=demo["course"], heading=False,
                                 assessments=[("Mock attempt", demo["attempt"]), ("Retest", demo["retest"])])
    with st.container(border=True):
        stage(3, "Generate a mock exam", "OUTPUT · 8 questions / 16 marks · confirmed topics · computed answers")
        preview = [next(q for q in demo["exam"]["questions"] if q["topic"] == t) for t in demo["course"]["topics"]]
        for col, q in zip(st.columns(3), preview):
            with col, st.container(border=True):
                math_ui.question(q, demo["exam"]["questions"].index(q)+1)
        st.download_button("Download full mock · PDF", exam_pdf(demo["exam"]), "worked-demo-mock.pdf", "application/pdf", key="story_mock")
        st.caption("The supplied mock answers include one mistake per topic, using the three patterns from the worksheets. Five of eight answers are correct.")
    with st.container(border=True):
        stage(4, "Turn mistakes into a next step", "FEEDBACK · Checked answers and worked corrections")
        score, focus = st.columns([1, 2])
        score.metric("Example mock result", f"{demo['attempt']['earned']} / {demo['attempt']['possible']}")
        focus.info("Practice focus: fractions, equations and graphs. The supplied answers demonstrate the three worksheet error patterns; they are not evidence about a real learner.")
        wrong = [(q, r) for q, r in zip(demo["exam"]["questions"], demo["attempt"]["results"]) if not r["correct"]]
        for q, result in wrong:
            with st.container(border=True):
                math_ui.question(q)
                math_ui.correction(q, result["submitted"])
                st.caption(TOPICS[q["topic"]]["tip"])
        st.caption("Supplied example answers; this score is not a real student's performance.")
    with st.container(border=True):
        stage(5, "Practise, then try again", "NEXT ACTION · 5 fresh questions on the missed topics")
        preview = [next(q for q in demo["practice"]["questions"] if q["topic"] == t) for t in demo["practice"]["topics"]]
        for col, q in zip(st.columns(len(preview)), preview):
            with col:
                math_ui.question(q)
                with st.expander("Reveal the worked answer"):
                    math_ui.solution(q)
        st.metric("Example retest result", f"{demo['retest']['earned']} / {demo['retest']['possible']}")
        st.caption("Correct example answers demonstrate a retest. This is not measured learning improvement.")
    with st.container(border=True):
        stage(6, "Use the real exam to inform the next mock", "UPDATE · More evidence changes the next paper, while the original stays saved.")
        st.write("In the fictional classroom exam, equations account for **14 of 20 marks**. The next mock adjusts its topic balance.")
        for col, topic in zip(st.columns(3), demo["course"]["topics"]):
            with col:
                before = demo["exam"]["distribution"][topic]
                after = demo["future"]["distribution"][topic]
                st.metric(TOPICS[topic]["name"], f"{before} → {after}")
                st.caption(f"Questions · {demo['review']['actual_marks'].get(topic, 0)}/20 classroom exam marks")
        if exam_intact(demo["exam"]) and demo["exam"]["fingerprint"] == demo["original_fingerprint"]:
            st.success("Original mock preserved. The updated mock contains 2 fraction, 4 equation and 2 graph questions.")
        st.download_button("Download updated mock · PDF", exam_pdf(demo["future"]), "worked-demo-next-mock.pdf", "application/pdf", key="story_future")
        st.caption("An update from past evidence, not a promise of prediction accuracy. That needs testing on a later exam.")
    with st.container(border=True):
        stage(7, "Make the giving allocation visible", "GIVING PREVIEW · Proposed study-pack policy; no money moves in this demo.")
        a, b, c = st.columns(3)
        a.metric("Example pack price", "¥29")
        b.metric("Hypothetical allocation", "¥3")
        c.metric("Actually transferred", "¥0")
        st.write("**If the pack is refunded:** its hypothetical allocation returns to ¥0. A live donation would need recipient details, payment evidence and a receipt in the public ledger.")
        st.caption("No real payment or donation occurred. Demo figures are excluded from live totals.")
    with st.container(border=True):
        stage(8, "The complete journey", "TAKEAWAY · A clear next step after every piece of evidence.")
        st.write("**3 images → reviewed course → mock exam → worked feedback → fresh practice → updated mock → transparent giving preview.**")
        st.download_button("Download example record · JSON", json.dumps(demo["workspace"], ensure_ascii=False, indent=2), "studybridge-worked-example.json", "application/json", key="story_record")

