"""One continuous, interactive product walkthrough with explicit example data."""
import json
import streamlit as st

from . import demo as flow
from . import demo_story
from . import math_ui
from . import summary_dashboard
from .catalog import TOPICS
from .engine import exam_intact, preview_order, sandbox_totals
from .exports import exam_pdf
from .materials import collect_materials, pasted_pages


def next_step(demo, label="Continue →"):
    st.button(label, type="primary", key=f"demo_next_{demo['step']}", on_click=flow.advance, args=(demo,))


def confirm_review(demo):
    try:
        if not st.session_state.get(f"demo_scope_{demo['id']}"):
            raise ValueError("Confirm the text and topics before continuing.")
        texts = [st.session_state[f"demo_text_{demo['id']}_{i}"] for i in range(len(demo["images"]))]
        flow.confirm_course(demo, texts)
        flow.advance(demo)
    except ValueError as exc:
        demo["error"] = str(exc)


def submit_answers(demo, exam, prefix, practice):
    if not st.session_state.get(f"{prefix}_ready"):
        demo["error"] = "Confirm you are ready to submit."
        return
    answers = {q["id"]: st.session_state.get(f"{prefix}_{q['id']}", "") for q in exam["questions"]}
    flow.submit(demo, answers, practice)
    if not practice:
        flow.advance(demo)


def confirm_post_exam(demo):
    try:
        if not st.session_state.get(f"demo_post_confirm_{demo['id']}"):
            raise ValueError("Check the marks before updating future papers.")
        marks = {t: st.session_state[f"demo_marks_{demo['id']}_{t}"] for t in demo["course"]["topics"]}
        flow.update_future(demo, marks, demo["post_pages"])
    except ValueError as exc:
        demo["error"] = str(exc)


def show_results(exam, attempt):
    st.metric("Practice result", f"{attempt['earned']} / {attempt['possible']}")
    st.dataframe([{"Question": i+1, "Topic": TOPICS[r["topic"]]["name"], "Your answer": r["submitted"] or "Blank",
                   "Result": "Correct" if r["correct"] else "Needs practice"} for i, r in enumerate(attempt["results"])], hide_index=True, width="stretch")
    for i, (question, result) in enumerate(zip(exam["questions"], attempt["results"]), 1):
        if not result["correct"]:
            with st.expander(f"Question {i}: work through the correction", expanded=True):
                math_ui.question(question, i)
                math_ui.correction(question, result["submitted"])
                st.info(TOPICS[question["topic"]]["tip"])
    st.caption("Final-answer grading. A wrong answer identifies something to practise; it does not by itself establish why you made the mistake.")


def answer_form(demo, exam, practice=False):
    prefix = f"demo_{demo['id']}_{'retest' if practice else 'mock'}"
    example_flag = "retest_examples" if practice else "answer_examples"
    label = "Fill example retest answers" if practice else "Fill example answers · includes 3 mistakes"
    if st.button(label, key=f"{prefix}_fill"):
        for qid, value in flow.example_answers(exam, include_mistakes=not practice).items():
            st.session_state[f"{prefix}_{qid}"] = value
        demo[example_flag] = True
    if demo[example_flag]:
        st.warning("Example answers are filled in for the walkthrough. You can edit them. The score is a demonstration, not evidence of a student's learning.")
    st.caption("Type your own answers or use the labelled examples above. Blank answers receive zero marks.")
    with st.form(prefix):
        answers = {}
        for i, q in enumerate(exam["questions"], 1):
            with st.container(border=True):
                math_ui.question(q, i)
                answers[q["id"]] = st.text_input(f"Answer {i}", key=f"{prefix}_{q['id']}", max_chars=60, placeholder="Enter a number or fraction, e.g. 7/12")
        st.checkbox("I am ready to submit this demo attempt.", key=f"{prefix}_ready")
        st.form_submit_button("Submit practice" if practice else "Submit mock exam", type="primary",
                              on_click=submit_answers, args=(demo, exam, prefix, practice))


def render(go, render_examples):
    if "guided_demo" not in st.session_state:
        st.session_state.guided_demo = flow.new_demo()
    demo = st.session_state.guided_demo
    step = demo["step"]
    if demo.get("error"):
        st.error(demo.pop("error"))
    st.markdown('''<div class="demo-hero"><div class="demo-hero-copy"><div class="demo-kicker">STUDYBRIDGE / DEMO &amp; EXAMPLES</div>
    <h1>A page of notes.<br>A clearer path forward.</h1>
    <p>See the whole journey, try it yourself, or explore a single topic. Your next step starts here.</p>
    <div class="demo-badges"><span>Sample materials included</span><span>No API needed</span><span>By Yifan Yan</span></div></div>
    <div class="demo-hero-aside"><b>Learn. Practise. Refine.</b><span>Bring your materials</span><span>Understand your mistakes</span><span>Prepare your next paper</span></div></div>''', unsafe_allow_html=True)
    view = st.radio("Explore the demo", ["Complete worked example", "Try it step by step", "Topic examples"], horizontal=True, key="guided_demo_view", label_visibility="collapsed")
    if view == "Topic examples":
        render_examples()
        return
    if view == "Complete worked example":
        if "worked_demo" not in st.session_state:
            st.session_state.worked_demo = flow.worked_example()
        demo_story.render(st.session_state.worked_demo)
        return
    st.caption("Interactive walkthrough · separate from your saved courses · no API calls or charges")
    st.progress((step+1)/len(flow.STEPS), text=flow.STEPS[step])
    st.markdown('<div class="demo-trail">' + ''.join(f'<span class="demo-stop {"active" if i == step else "done" if i < demo["unlocked"] else ""}">{name}</span>' for i, name in enumerate(flow.STEPS)) + '</div>', unsafe_allow_html=True)
    with st.expander("Revisit a step or restart"):
        chosen = st.selectbox("Available steps", range(demo["unlocked"]+1), index=step, format_func=lambda i: flow.STEPS[i], key=f"demo_jump_{demo['id']}_{step}")
        def jump():
            demo["step"] = st.session_state[f"demo_jump_{demo['id']}_{step}"]
        def restart():
            st.session_state.guided_demo = flow.new_demo()
        st.button("Go to selected step", on_click=jump)
        st.button("Restart this demo", on_click=restart)

    with st.empty().container():
        render_step(demo, go)


def render_step(demo, go):
    step = demo["step"]
    if step == 0:
        st.subheader("Start with the pages you already study")
        st.write("Three pages from a fictional revision attempt: adding fraction denominators, using the wrong inverse operation, and confusing slope with intercept. Each includes correct work, a visible mistake and a follow-up question.")
        def start_samples():
            if not demo["images"]:
                flow.load_images(demo, flow.sample_files())
                demo["input_method"] = "Loaded bundled samples"
            flow.advance(demo)
        st.button("Start with sample images →", type="primary", on_click=start_samples)
        st.caption("This button loads the sample pages and takes you directly to text review. Or upload the PNGs yourself below.")
        files = flow.sample_files()
        for column, (name, data) in zip(st.columns(3), files):
            column.image(data, caption=name, width="stretch")
            column.download_button("Download image", data, name, "image/png", key=f"demo_download_{name}")
        st.write("**Try the upload:** download the images above, then drop all three into the uploader. Or load the same sample files with one click.")
        uploads = st.file_uploader("Upload the three demo worksheet images", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key=f"demo_upload_{demo['id']}", disabled=demo["course"] is not None)
        left, right = st.columns(2)
        load = left.button("Load the 3 sample images", disabled=demo["course"] is not None)
        upload = right.button("Use my uploaded demo images", disabled=not uploads or demo["course"] is not None)
        if load or upload:
            try:
                flow.load_images(demo, files if load else [(u.name, u.getvalue()) for u in uploads])
                demo["input_method"] = "Loaded bundled samples" if load else "Uploaded sample PNGs"
            except ValueError as exc:
                st.error(str(exc))
        if demo["images"]:
            st.success(f"{len(demo['images'])} images ready · {demo['input_method']}")
            next_step(demo, "Next: review the image text →")
        st.caption("This story uses the supplied samples. Use Worksheet images in the sidebar for your own pictures and optional AI transcription.")

    elif step == 1:
        st.subheader("Check what the app will learn from")
        st.info("The demo uses prepared transcripts matched to the exact sample images. This is not a live AI reading. In the regular upload flow, AI can draft the text for your review.")
        texts = []
        for i, image in enumerate(demo["images"]):
            with st.expander(image["name"], expanded=i == 0):
                left, right = st.columns([1, 1.5])
                left.image(image["bytes"], width="stretch")
                saved_text = demo["course"]["pages"][i]["text"] if demo["course"] else image["text"]
                texts.append(right.text_area("Check and edit the transcript", saved_text, height=380,
                                             key=f"demo_text_{demo['id']}_{i}", max_chars=12000, disabled=demo["course"] is not None))
        st.write("**Confirmed scope:** fractions, linear equations and linear graphs.")
        st.caption("All three worksheets deliberately contain incorrect student working. Preserve the errors as evidence to discuss; the dashboard keeps their prepared corrections separate.")
        if demo["course"] is None:
            st.checkbox("I checked the text and confirm these three topics.", key=f"demo_scope_{demo['id']}")
            st.button("Confirm course & continue →", type="primary", on_click=confirm_review, args=(demo,))
        else:
            st.success("Course scope saved. Restart the demo to try different inputs.")
            next_step(demo)

    elif step == 2:
        st.subheader("Build and take a mock exam")
        with st.expander("Your reviewed material dashboard", expanded=demo["exam"] is None):
            summary_dashboard.render(demo["course"]["pages"], demo["course"]["outline"], topics=demo["course"]["topics"],
                                     key=f"interactive_{demo['id']}", owner=demo["course"])
        st.write("Generate eight numerical questions from the three confirmed topics. Their answers are computed and checked before the paper is saved.")
        if demo["exam"] is None:
            if st.button("Generate the demo mock exam", type="primary"):
                flow.generate_first(demo)
                st.rerun()
        else:
            exam = demo["exam"]
            st.caption("8 questions · 16 marks · 20-minute guide · full-paper demo access")
            st.download_button("Download this mock · PDF", exam_pdf(exam), "demo-mock.pdf", "application/pdf")
            if demo["attempt"] is None:
                answer_form(demo, exam)
            else:
                st.success("This mock has a saved attempt.")
                next_step(demo, "See the marking →")

    elif step == 3:
        st.subheader("Turn the result into a learning decision")
        if demo["answer_examples"]:
            st.caption("This attempt used example answers, possibly edited by you. It is a demo score.")
        show_results(demo["exam"], demo["attempt"])
        weak = list(dict.fromkeys(TOPICS[r["topic"]]["name"] for r in demo["attempt"]["results"] if not r["correct"]))
        st.write("**Next practice:** " + (", ".join(weak) if weak else "All three topics, using unseen questions."))
        st.download_button("Download the worked answers · PDF", exam_pdf(demo["exam"], True), "demo-worked-answers.pdf", "application/pdf")
        next_step(demo, "Next: practise with new questions →")

    elif step == 4:
        st.subheader("Try fresh questions on the missed topics")
        if demo["practice"] is None:
            st.write("The next set uses your marked answers to choose its topics. It excludes question wording already seen in this course.")
            if st.button("Generate targeted practice", type="primary"):
                flow.generate_practice(demo)
                st.rerun()
        else:
            st.write("**Practice focus:** " + ", ".join(TOPICS[t]["name"] for t in demo["practice"]["topics"]))
            if demo["retest"] is None:
                answer_form(demo, demo["practice"], practice=True)
            else:
                show_results(demo["practice"], demo["retest"])
                if demo["retest_examples"]:
                    st.info("The filled retest answers demonstrate the flow. They do not demonstrate actual learning improvement.")
                next_step(demo, "Next: learn from a completed real exam →")

    elif step == 5:
        st.subheader("Use the actual exam structure for the next mock")
        st.write("After a classroom exam, attach the paper and confirm its topic marks. This demo paper places more weight on equations than our original mock did.")
        st.download_button("Download the fictional post-exam paper", flow.POST_EXAM, "demo-post-exam.txt", "text/plain")
        if demo["review"] is None:
            uploads = st.file_uploader("Attach a completed exam · PDF / TXT / MD", type=["pdf", "txt", "md"], accept_multiple_files=True, key=f"demo_post_{demo['id']}")
            if st.button("Load the fictional completed exam"):
                demo["post_pages"] = pasted_pages(flow.POST_EXAM, "Fictional classroom exam")
            if uploads and st.button("Use the attached completed exam"):
                try:
                    demo["post_pages"] = collect_materials(uploads, "")
                except ValueError as exc:
                    st.error(str(exc))
            if demo["post_pages"]:
                with st.expander("Read the attached exam", expanded=True):
                    for page in demo["post_pages"]:
                        st.text(page["text"])
                st.caption("Enter marks allocated to each topic, not the student's score. Defaults match the fictional sample; change them if you attach a different paper.")
                cols = st.columns(3)
                marks = {t: cols[i].number_input(TOPICS[t]["name"] + " marks", min_value=0, max_value=500,
                                                value=v, step=1, key=f"demo_marks_{demo['id']}_{t}")
                         for i, (t, v) in enumerate({"fractions":2, "equations":14, "graphs":4}.items())}
                st.checkbox("I checked the topic marks against the attached exam.", key=f"demo_post_confirm_{demo['id']}")
                st.button("Update & generate the next mock", type="primary", on_click=confirm_post_exam, args=(demo,))
        else:
            review = demo["review"]
            total = sum(review["actual_marks"].values())
            st.dataframe([{"Topic": TOPICS[t]["name"], "Original mock questions": demo["exam"]["distribution"][t],
                           "Actual exam marks (%)": round(100*review["actual_marks"].get(t, 0)/total),
                           "Next mock questions": demo["future"]["distribution"][t]} for t in demo["course"]["topics"]], hide_index=True, width="stretch")
            if exam_intact(demo["exam"]) and demo["exam"]["fingerprint"] == demo["original_fingerprint"]:
                st.success("The original mock is unchanged. The new paper uses this separate post-exam review.")
            st.caption("This shows how topic balance updates from past evidence. Whether it predicts a future exam better must be tested on a later, unseen exam.")
            st.download_button("Download the updated mock · PDF", exam_pdf(demo["future"]), "demo-next-mock.pdf", "application/pdf")
            next_step(demo, "Next: see the education-giving model →")

    elif step == 6:
        st.subheader("Connect a study pack to transparent giving")
        st.write("The proposed pack costs ¥29, with ¥3 allocated to education giving for each eligible non-refunded order. Try the accounting below.")
        st.warning("Simulation only. No payment, donation, recipient confirmation, or impact is recorded in the public ledger.")
        if not demo["workspace"]["sandbox_orders"] and st.button("Simulate a study-pack purchase", type="primary"):
            preview_order(demo["workspace"])
            st.rerun()
        orders = demo["workspace"]["sandbox_orders"]
        if orders:
            values = sandbox_totals(orders)
            a, b, c = st.columns(3)
            a.metric("Hypothetical allocation", f"¥{values['pledged_cents']/100:.2f}")
            b.metric("Actually charged", "¥0")
            c.metric("Actually transferred", "¥0")
            st.write("A live transfer would need a published recipient, payment evidence and a receipt. A recipient response would need its own verification.")
            if st.button("Simulate a refund", disabled=orders[0]["refunded"]):
                orders[0]["refunded"] = True
                st.rerun()
            if orders[0]["refunded"]:
                st.info("Refund simulated: the hypothetical education allocation is now ¥0.")
            next_step(demo, "Finish: see the entire journey →")

    else:
        st.subheader("You have completed the whole flow")
        first, second = demo["attempt"], demo["retest"]
        st.dataframe([
            {"Step": "Images → course", "What happened": f"3 worksheet images; reviewed transcripts; 3 confirmed topics."},
            {"Step": "Course → mock", "What happened": "8 checked questions; a saved pre-exam paper."},
            {"Step": "Answers → feedback", "What happened": f"Marked {first['earned']}/{first['possible']}; worked corrections shown."},
            {"Step": "Mistakes → fresh practice", "What happened": f"5 unseen questions; retest {second['earned']}/{second['possible']}."},
            {"Step": "Actual exam → next mock", "What happened": "Reviewed topic marks informed a new mock; the earlier paper stayed intact."},
            {"Step": "Study pack → giving", "What happened": "A purchase/refund simulation with zero real money moved."},
        ], hide_index=True, width="stretch")
        if demo["answer_examples"] or demo["retest_examples"]:
            st.caption("Some answers were supplied for demonstration. These results are not learning-outcome evidence.")
        st.download_button("Download my demo journey · JSON", json.dumps(demo["workspace"], ensure_ascii=False, indent=2), "studybridge-demo-journey.json", "application/json")
        st.write("**Now try it with your own materials.** Your demo stays separate from your personal courses and the public donation ledger.")
        if st.button("Start with my own worksheet →", type="primary"):
            go("Worksheet images")

