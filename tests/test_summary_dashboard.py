from pathlib import Path

from streamlit.testing.v1 import AppTest

from studybridge.engine import local_outline
from studybridge.summary_dashboard import build_summary, board_for


APP = Path(__file__).resolve().parents[1] / "legacy_app.py"


def test_profile_counts_are_backed_by_visible_marked_work():
    from studybridge.demo import worked_example
    from studybridge.summary_dashboard import skill_counts
    course = worked_example()["course"]
    cases = build_summary(course["pages"], course["outline"], course["topics"])["reviewed_mistakes"]
    source, rows = skill_counts(cases)
    assert source == "Fictional worksheet review"
    assert [(r["Correct"], r["Needs practice"], r["Reviewed"]) for r in rows] == [(2, 3, 5), (3, 2, 5), (4, 1, 5)]
    for case in cases:
        page = next(p for p in course["pages"] if p["id"] == case["source_id"])
        assert all(o["evidence"] in page["text"] for o in case["observations"])
    # A real saved attempt takes precedence over fictional worksheet results.
    label, actual = skill_counts(cases, [("Latest saved attempt", {"results": [
        {"topic": "fractions", "correct": True}, {"topic": "fractions", "correct": False}]})])
    assert label == "Latest saved attempt"
    assert actual == [{"Topic": "Fractions", "Correct": 1, "Needs practice": 1, "Reviewed": 2}]


def test_three_authored_reviews_require_unchanged_bundled_pages():
    from copy import deepcopy
    from studybridge.demo import worked_example
    course = worked_example()["course"]
    summary = build_summary(course["pages"], course["outline"], course["topics"])
    cases = summary["reviewed_mistakes"]
    assert {c["id"] for c in cases} == {"fractions", "equations", "graphs"}
    assert len({c["kind"] for c in cases}) == 3
    for case in cases:
        page = next(p for p in course["pages"] if p["id"] == case["source_id"])
        assert case["evidence"] in page["text"]
    changed = deepcopy(course["pages"])
    changed[0]["text"] = changed[0]["text"].replace("= 2/7.", "= 7/12.")
    changed[1].pop("image_hash")
    remaining = build_summary(changed, course["outline"], course["topics"])["reviewed_mistakes"]
    assert [c["id"] for c in remaining] == ["graphs"]


def test_summary_preserves_evidence_and_flags_unmatched_and_unclear_pages():
    pages = [
        {"id": "a", "name": "lesson.txt", "page": 1, "text": "Linear equations\nStudent wrote 3x = 25.\n[unclear]"},
        {"id": "b", "name": "history.txt", "page": 1, "text": "The history of ancient Rome."},
    ]
    outline = local_outline(pages)
    outline["topics"].append({"topic": "graphs", "source_id": "missing", "quote": "Slope is 2", "reason": "invalid"})
    summary = build_summary(pages, outline, ["equations", "graphs"])
    assert summary["sources"] == 2 and summary["pages"] == 2
    assert summary["needs_review"] == ["a"]
    assert summary["unmatched"] == ["b"]
    assert summary["evidence"]["graphs"] == []
    assert "Student wrote 3x = 25." in summary["highlights"][0]["lines"]
    assert summary["evidence"]["equations"][0]["quote"] in pages[0]["text"]


def test_changed_source_resets_self_reported_readiness():
    pages = [{"id": "a", "name": "lesson.txt", "page": 1, "text": "Fractions and denominators"}]
    summary = build_summary(pages, local_outline(pages))
    owner = {"study_board": {"version": summary["version"], "statuses": {"fractions": "Ready to practise"}}}
    assert board_for(owner, summary)["statuses"]["fractions"] == "Ready to practise"
    pages[0]["text"] += "\nNew example: 1/3 + 1/4."
    changed = build_summary(pages, local_outline(pages))
    assert board_for(owner, changed)["statuses"]["fractions"] == "To review"


def test_simple_summary_keeps_saved_records_without_board_controls(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDYBRIDGE_DB_PATH", str(tmp_path / "dashboard.sqlite"))
    app = AppTest.from_file(str(APP)).run()
    app.button(key="nav_Worksheet images").click().run()
    app.button(key="worksheet_equations").click().run()
    assert not app.exception
    assert any(t.label == "Learning summary" for t in app.tabs)
    assert not any(t.label in ("Summary", "Concepts & formulas", "Study board", "Source explorer") for t in app.tabs)
    assert not any(s.label.endswith(" status") for s in app.selectbox)
    assert any(e.label == "Check sources & formulas" for e in app.expander)
    # A board saved by the previous version must survive the simpler interface.
    app.session_state["image_review"]["study_board"]["statuses"]["equations"] = "Studying"
    next(c for c in app.checkbox if "checked every transcript" in c.label).check()
    next(b for b in app.button if b.label == "Save reviewed course →").click().run()
    assert not app.exception
    course = app.session_state["workspace"]["courses"][0]
    assert course["study_board"]["statuses"]["equations"] == "Studying"
    app.button(key="nav_My courses").click().run()
    assert not app.exception
    assert app.session_state["workspace"]["courses"][0]["study_board"]["statuses"]["equations"] == "Studying"


def test_text_import_has_dashboard_before_course_save():
    app = AppTest.from_file(str(APP)).run()
    app.button(key="nav_My courses").click().run()
    app.text_input(key="import_title").set_value("My fractions lesson")
    app.text_area(key="course_notes").set_value("Fractions: use a common denominator. Example: 1/3 + 1/4 = 7/12.")
    next(b for b in app.button if b.label == "Analyse materials").click().run()
    assert not app.exception
    assert app.session_state["draft"]["study_board"]["statuses"] == {"fractions": "To review"}
    assert not app.session_state["workspace"]["courses"]
    next(b for b in app.button if b.label == "Save course").click().run()
    assert not app.exception
    assert app.session_state["workspace"]["courses"][0]["study_board"]["statuses"] == {"fractions": "To review"}

