"""A session-only walkthrough using the application's actual learning engine."""
from fractions import Fraction
from .catalog import TOPICS
from .engine import (new_workspace, identifier, local_outline, make_course, build_exam,
                     grade_exam, calibration, numeric_answer, fraction_text, exam_intact, preview_order)
from .materials import pasted_pages
from .worksheets import ASSETS, SAMPLES, prepare_images

STEPS = ["Upload images", "Review the text", "Take a mock", "Understand mistakes",
         "Practise again", "Update the next mock", "See the giving model", "Your full journey"]
POST_EXAM = """FICTIONAL POST-EXAM PAPER — GUIDED DEMO
This is a demonstration of a completed classroom assessment, not a real exam.
Q1. Calculate 2/3 + 1/4. [2 marks] Topic: fractions.
Q2. Solve 4x + 3 = 19 and show your working. [6 marks] Topic: equations.
Q3. Solve 5x - 2 = 23 and check your solution. [8 marks] Topic: equations.
Q4. For y = 3x + 1, find y when x = 2. [4 marks] Topic: graphs.
Topic allocation: fractions 2; equations 14; graphs 4. Total: 20 marks.
These classroom marks are used only to compare topic shares, not to grade this paper.
"""


def new_demo():
    return {"id": identifier(), "step": 0, "unlocked": 0, "workspace": new_workspace(),
            "images": [], "course": None, "exam": None, "attempt": None,
            "practice": None, "retest": None, "review": None, "future": None,
            "answer_examples": False, "retest_examples": False, "post_pages": []}


def advance(demo):
    demo["step"] = min(len(STEPS)-1, demo["step"]+1)
    demo["unlocked"] = max(demo["unlocked"], demo["step"])


def sample_files():
    return [(f"{s['id']}.png", (ASSETS / f"{s['id']}.png").read_bytes()) for s in SAMPLES]


def load_images(demo, files):
    images = prepare_images(files)
    expected = {i["id"] for i in prepare_images(sample_files())}
    if {i["id"] for i in images} != expected:
        raise ValueError("For this guided story, upload all three supplied sample PNGs. Use Worksheet images for your own materials.")
    demo["images"] = images


def confirm_course(demo, texts):
    if len(texts) != len(demo["images"]) or any(not 20 <= len(t.strip()) <= 12000 for t in texts):
        raise ValueError("Review all three transcripts; each needs 20–12,000 characters.")
    pages = [{"id": f"demo-image-{image['id']}", "name": image["name"], "page": i+1,
              "text": text.strip(), "image_hash": image["id"], "transcription_method": image["method"]}
             for i, (image, text) in enumerate(zip(demo["images"], texts))]
    course = make_course("Demo · My next maths test", pages, local_outline(pages), ["fractions", "equations", "graphs"])
    demo["course"] = course
    demo["workspace"]["courses"] = [course]


def generate_first(demo):
    if demo["exam"] is None:
        demo["exam"] = build_exam(demo["course"], demo["workspace"], demo["course"]["topics"], 8, 20,
                                   "Foundation", "Exam simulation", False, False, seed=204)
        demo["workspace"]["exams"].append(demo["exam"])
        demo["original_fingerprint"] = demo["exam"]["fingerprint"]
    return demo["exam"]


def example_answers(exam, include_mistakes):
    answers, missed = {}, set()
    for q in exam["questions"]:
        value = numeric_answer(q["answer"])
        if include_mistakes and q["topic"] not in missed:
            p = q["params"]
            if q["topic"] == "fractions":
                value = Fraction(p[0] - p[2] if p[4] else p[0] + p[2], p[1] + p[3])
            elif q["topic"] == "equations":
                value = Fraction(p[2] + p[1], p[0])
            elif q["topic"] == "graphs":
                value = Fraction(p[1] if p[3] else p[1]*p[2]+p[0])
            if value != numeric_answer(q["answer"]):
                missed.add(q["topic"])
        answers[q["id"]] = fraction_text(value)
    return answers


def submit(demo, answers, practice=False):
    exam_key, attempt_key = ("practice", "retest") if practice else ("exam", "attempt")
    if demo[attempt_key] is None:
        demo[attempt_key] = grade_exam(demo[exam_key], answers)
        demo["workspace"]["attempts"].append(demo[attempt_key])
    return demo[attempt_key]


def generate_practice(demo):
    if demo["practice"] is None:
        wrong = {r["topic"] for r in demo["attempt"]["results"] if not r["correct"]}
        topics = [t for t in demo["course"]["topics"] if t in wrong] or demo["course"]["topics"]
        demo["practice"] = build_exam(demo["course"], demo["workspace"], topics, 5, 10,
                                       "Foundation", "Targeted practice", False, False, seed=305)
        demo["workspace"]["exams"].append(demo["practice"])
    return demo["practice"]


def update_future(demo, marks, pages):
    if demo["review"] is not None:
        return
    original = demo["exam"]
    if original["fingerprint"] != demo["original_fingerprint"] or not exam_intact(original):
        raise ValueError("The original paper changed. Restart the demo before calibrating.")
    review = calibration(original, marks, "Guided post-exam review", pages, "User-reviewed topic marks. This demo does not measure future predictive accuracy.")
    # Build against a candidate state so a generation failure cannot leave half an update.
    candidate = {**demo["workspace"], "calibrations": [*demo["workspace"]["calibrations"], review]}
    future = build_exam(demo["course"], candidate, demo["course"]["topics"], 8, 20,
                        "Foundation", "Exam simulation", False, True, seed=406)
    demo["workspace"]["calibrations"].append(review)
    demo["workspace"]["exams"].append(future)
    demo["review"], demo["future"] = review, future


def worked_example():
    """Build one clearly labelled complete example without external side effects."""
    demo = new_demo()
    load_images(demo, sample_files())
    demo["input_method"] = "Bundled example images"
    confirm_course(demo, [i["text"] for i in demo["images"]])
    first = generate_first(demo)
    submit(demo, example_answers(first, True))
    practice = generate_practice(demo)
    submit(demo, example_answers(practice, False), practice=True)
    update_future(demo, {"fractions":2, "equations":14, "graphs":4}, pasted_pages(POST_EXAM, "Fictional classroom exam"))
    preview_order(demo["workspace"])
    demo.update(answer_examples=True, retest_examples=True, step=7, unlocked=7)
    return demo
