from copy import deepcopy
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from studybridge import demo
from studybridge.engine import exam_intact
from studybridge.materials import pasted_pages


def test_demo_runs_actual_engine_and_preserves_history():
    d = demo.new_demo()
    demo.load_images(d, demo.sample_files())
    demo.confirm_course(d, [i["text"] for i in d["images"]])
    first = demo.generate_first(d)
    original = deepcopy(first)
    attempt = demo.submit(d, demo.example_answers(first, True))
    assert attempt["earned"] == 10 and attempt["possible"] == 16
    assert {r["topic"] for r in attempt["results"] if not r["correct"]} == {"fractions", "equations", "graphs"}
    assert demo.generate_first(d) is first
    assert demo.submit(d, {}) is attempt
    practice = demo.generate_practice(d)
    assert set(practice["topics"]) == {"fractions", "equations", "graphs"}
    assert not {q["prompt"] for q in first["questions"]} & {q["prompt"] for q in practice["questions"]}
    assert demo.submit(d, demo.example_answers(practice, False), True)["earned"] == 10
    demo.update_future(d, {"fractions":2, "equations":14, "graphs":4}, pasted_pages(demo.POST_EXAM))
    assert first == original and exam_intact(first)
    assert first["history_ids"] == []
    assert d["future"]["history_ids"] == [d["review"]["id"]]
    assert first["distribution"]["equations"] == 3
    assert d["future"]["distribution"]["equations"] == 4
    demo.update_future(d, {}, [])
    assert len(d["workspace"]["calibrations"]) == 1
    assert len(d["workspace"]["exams"]) == 3


def test_demo_requires_its_full_sample_set_and_reviewed_text():
    d = demo.new_demo()
    with pytest.raises(ValueError, match="all three"):
        demo.load_images(d, demo.sample_files()[:1])
    demo.load_images(d, demo.sample_files())
    with pytest.raises(ValueError, match="Review all three"):
        demo.confirm_course(d, [""]*3)
    assert d["course"] is None


def test_entire_guided_ui_flow_is_isolated_and_restartable(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDYBRIDGE_DB_PATH", str(tmp_path/"guided.sqlite"))
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/"app.py")).run()

    def click(label):
        next(b for b in app.button if b.label == label).click().run(timeout=20)
        assert not app.exception

    def check(label):
        next(c for c in app.checkbox if label in c.label).check()

    # The walkthrough is now embedded directly in Overview.
    app.radio(key="guided_demo_view").set_value("Try it step by step").run()
    click("Load the 3 sample images")
    click("Next: review the image text →")
    click("Confirm course & continue →")
    assert app.session_state["guided_demo"]["step"] == 1  # Confirmation is mandatory.
    check("I checked the text")
    click("Confirm course & continue →")
    click("Generate the demo mock exam")
    click("Fill example answers · includes 3 mistakes")
    check("I am ready to submit")
    click("Submit mock exam")
    assert app.session_state["guided_demo"]["attempt"]["earned"] == 10
    click("Next: practise with new questions →")
    click("Generate targeted practice")
    click("Fill example retest answers")
    check("I am ready to submit")
    click("Submit practice")
    click("Next: learn from a completed real exam →")
    click("Load the fictional completed exam")
    check("I checked the topic marks")
    click("Update & generate the next mock")
    click("Next: see the education-giving model →")
    click("Simulate a study-pack purchase")
    click("Simulate a refund")
    click("Finish: see the entire journey →")
    d = app.session_state["guided_demo"]
    assert d["step"] == 7 and d["unlocked"] == 7
    assert d["workspace"]["sandbox_orders"][0]["refunded"]
    assert not app.session_state["workspace"]["courses"]
    assert not app.session_state["workspace"]["sandbox_orders"]
    assert app.session_state["workspace"]["ai_calls"] == 0
    # Revisiting doesn't erase later work; restarting changes only the demo.
    app.selectbox(key=f"demo_jump_{d['id']}_7").select(0)
    click("Go to selected step")
    assert app.session_state["guided_demo"]["future"]
    click("Restart this demo")
    assert app.session_state["guided_demo"]["step"] == 0
    assert app.session_state["guided_demo"]["exam"] is None


def test_demo_deep_link_opens_first_step():
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/"app.py"))
    app.query_params["demo"] = "1"
    app.run()
    assert not app.exception
    assert app.session_state["page"] == "Demo & examples"


def test_default_demo_shows_every_stage_without_unlocking():
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/"app.py"))
    app.query_params["demo"] = "1"
    app.run(timeout=20)
    assert not app.exception
    assert app.radio(key="guided_demo_view").value == "Complete worked example"
    assert len(app.latex) >= 12
    assert any(r"\frac" in formula.value for formula in app.latex)
    assert not any(b.key in ("nav_Example library", "nav_Guided demo") for b in app.button)
    assert len(app.subheader) == 8
    assert app.subheader[-1].value == "The complete journey"
    assert all(not h.value[0].isdigit() for h in app.subheader)
    assert app.session_state["worked_demo"]["attempt"]["earned"] == 10
    assert not app.session_state["workspace"]["courses"]
    assert not app.session_state["workspace"]["sandbox_orders"]
    app.radio(key="guided_demo_view").set_value("Try it step by step").run()
    next(b for b in app.button if b.label == "Start with sample images →").click().run()
    assert not app.exception
    assert app.session_state["guided_demo"]["step"] == 1
    assert len(app.session_state["guided_demo"]["images"]) == 3


