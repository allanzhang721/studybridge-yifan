from pathlib import Path
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "legacy_app.py"


def button(app, label):
    return next(b for b in app.button if b.label == label)


def test_sample_exam_grading_and_preview_journey(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDYBRIDGE_DB_PATH", str(tmp_path / "ui.sqlite"))
    app = AppTest.from_file(str(APP)).run(timeout=20)
    assert not app.exception
    button(app, "Explore sample course").click().run()
    assert not app.exception
    button(app, "Create a mock exam →").click().run()
    next(c for c in app.checkbox if "checked that these topics" in c.label).check()
    button(app, "Generate my mock exam").click().run(timeout=20)
    assert not app.exception
    exam = app.session_state["workspace"]["exams"][0]
    for q in exam["questions"]:
        if q["choices"]:
            app.radio(key=f"answer_{q['id']}").set_value(q["answer"])
        else:
            app.text_input(key=f"answer_{q['id']}").set_value(q["answer"])
    next(c for c in app.checkbox if "ready to submit" in c.label).check()
    button(app, "Submit & see my next steps").click().run(timeout=20)
    assert not app.exception
    assert app.session_state["workspace"]["attempts"][0]["earned"] == 10
    app.button(key="nav_Plans & account").click().run()
    button(app, "Try Plus preview · no payment").click().run()
    assert not app.exception
    assert app.session_state["workspace"]["plus_preview"]
    app.button(key="nav_Impact ledger").click().run()
    assert not app.exception
    assert any("Simulation only" in w.value for w in app.warning)
    button(app, "Simulate refund").click().run()
    assert app.session_state["workspace"]["sandbox_orders"][0]["refunded"]


def test_all_navigation_pages_load(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDYBRIDGE_DB_PATH", str(tmp_path / "nav.sqlite"))
    app = AppTest.from_file(str(APP)).run()
    for page in ["Demo & examples", "Worksheet images", "My courses", "Mock exams", "Review & practice", "Impact ledger", "Plans & account", "Overview"]:
        app.button(key=f"nav_{page}").click().run(timeout=20)
        assert not app.exception, page


def test_my_courses_sample_matches_demo_and_does_not_duplicate():
    from studybridge.summary_dashboard import build_summary
    app = AppTest.from_file(str(APP)).run()
    app.button(key="nav_My courses").click().run()
    button(app, "Load sample maths course").click().run()
    assert not app.exception
    course = app.session_state["workspace"]["courses"][0]
    assert course["topics"] == ["fractions", "equations", "graphs"]
    assert {"Learning report", "Practice", "Materials", "Strengths", "Weaknesses"}.issubset({t.label for t in app.tabs})
    summary = build_summary(course["pages"], course["outline"], course["topics"])
    assert len(summary["reviewed_mistakes"]) == 3
    assert all("image_hash" in page and "bytes" not in page for page in course["pages"])
    assert not app.session_state["workspace"]["exams"]
    assert not app.session_state["workspace"]["attempts"]
    button(app, "Load sample maths course").click().run()
    assert not app.exception
    assert len(app.session_state["workspace"]["courses"]) == 1
    assert app.session_state["selected_course"] == course["id"]


def test_worksheet_review_is_required_and_keeps_corrections(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDYBRIDGE_DB_PATH", str(tmp_path / "images.sqlite"))
    app = AppTest.from_file(str(APP)).run()
    app.button(key="browse_worksheets").click().run()
    app.button(key="worksheet_equations").click().run()
    assert not app.exception
    assert button(app, "Read images with AI").disabled
    button(app, "Save reviewed course →").click().run()
    assert len(app.session_state["workspace"]["courses"]) == 0
    textarea = next(t for t in app.text_area if "Reviewed text" in t.label)
    assert "3x = 25" in textarea.value
    textarea.set_value(textarea.value + "\nReviewer note: the student should subtract 5, giving 3x = 15.")
    next(c for c in app.checkbox if "checked every transcript" in c.label).check()
    button(app, "Save reviewed course →").click().run()
    assert not app.exception
    course = app.session_state["workspace"]["courses"][0]
    assert "Reviewer note" in course["pages"][0]["text"]
    assert "image_hash" in course["pages"][0]
    assert "bytes" not in course["pages"][0]
    assert app.session_state["workspace"]["ai_calls"] == 0


def test_visual_example_loads_course_and_generates_new_practice(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDYBRIDGE_DB_PATH", str(tmp_path / "example.sqlite"))
    app = AppTest.from_file(str(APP)).run()
    app.button(key="browse_examples").click().run()
    assert not app.exception
    app.button(key="example_fractions").click().run()
    course = app.session_state["workspace"]["courses"][0]
    assert course["topics"] == ["fractions"]
    assert "not AI image extraction" in course["pages"][0]["text"]
    assert app.session_state["workspace"]["ai_calls"] == 0
    next(c for c in app.checkbox if "checked that these topics" in c.label).check()
    button(app, "Generate my mock exam").click().run()
    assert not app.exception
    exam = app.session_state["workspace"]["exams"][0]
    assert len(exam["questions"]) == 5
    assert all(q["topic"] == "fractions" for q in exam["questions"])
    app.button(key="nav_Demo & examples").click().run()
    app.radio(key="guided_demo_view").set_value("Topic examples").run()
    app.button(key="example_fractions").click().run()
    assert len(app.session_state["workspace"]["courses"]) == 1


def test_calibration_and_saved_workspace_survive_sign_in(tmp_path, monkeypatch):
    from studybridge.catalog import SAMPLE_EXAM
    from studybridge.engine import exam_intact

    monkeypatch.setenv("STUDYBRIDGE_DB_PATH", str(tmp_path / "saved.sqlite"))
    app = AppTest.from_file(str(APP)).run()
    button(app, "Explore sample course").click().run()
    button(app, "Create a mock exam →").click().run()
    next(c for c in app.checkbox if "checked that these topics" in c.label).check()
    button(app, "Generate my mock exam").click().run()
    original = app.session_state["workspace"]["exams"][0]["fingerprint"]
    next(t for t in app.text_input if t.label == "Real exam label").set_value("October test")
    next(t for t in app.text_area if t.label == "Or paste the exam text").set_value(SAMPLE_EXAM)
    for topic, marks in {"fractions":2, "equations":8, "graphs":6, "quadratics":4}.items():
        app.number_input(key=f"actual_{topic}").set_value(marks)
    next(c for c in app.checkbox if "post-exam review" in c.label).check()
    button(app, "Save review & update future papers").click().run()
    assert not app.exception
    assert len(app.session_state["workspace"]["calibrations"]) == 1
    exam = app.session_state["workspace"]["exams"][0]
    assert exam_intact(exam) and exam["fingerprint"] == original
    app.button(key="nav_Plans & account").click().run()
    app.text_input(key="new_username").set_value("qa_student")
    app.text_input(key="new_password").set_value("Practilume123!")
    app.text_input(key="new_password_again").set_value("Practilume123!")
    next(c for c in app.checkbox if "Save my current guest" in c.label).check()
    button(app, "Create workspace").click().run()
    assert not app.exception
    assert app.session_state["username"] == "qa_student"
    app.button(key="nav_Plans & account").click().run()
    button(app, "Sign out").click().run()
    assert not app.session_state["workspace"]["courses"]
    app.button(key="nav_Plans & account").click().run()
    app.text_input(key="login_username").set_value("qa_student")
    app.text_input(key="login_password").set_value("Practilume123!")
    button(app, "Sign in").click().run()
    assert not app.exception
    assert len(app.session_state["workspace"]["calibrations"]) == 1
    assert app.session_state["workspace"]["exams"][0]["fingerprint"] == original


