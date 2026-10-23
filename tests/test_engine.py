import copy
import json
import random
from fractions import Fraction
from io import BytesIO

import pytest
from pypdf import PdfReader

from studybridge.catalog import TOPICS, SAMPLE_TEXT
from studybridge.engine import (new_workspace, make_course, local_outline, question, verify_question, numeric_answer,
    build_exam, grade_exam, calibration, exam_intact, digest, preview_order, sandbox_totals)
from studybridge.materials import pasted_pages, extract_file
from studybridge.ai import validate_outline
from studybridge.exports import exam_pdf
from studybridge.ledger import load_ledger, csv_bytes


@pytest.fixture
def setup():
    state = new_workspace()
    pages = pasted_pages(SAMPLE_TEXT)
    course = make_course("Maths", pages, local_outline(pages), list(TOPICS))
    state["courses"].append(course)
    return state, course


@pytest.mark.parametrize("topic", TOPICS)
@pytest.mark.parametrize("difficulty", ["Foundation", "Challenge"])
def test_template_answers_are_consistent(topic, difficulty):
    for seed in range(100):
        q = question(topic, difficulty, random.Random(seed), "Multiple choice")
        assert verify_question(q)
        assert len(set(q["choices"])) == 4
        assert q["answer"] in q["choices"]
        altered = copy.deepcopy(q)
        altered["answer"] = str(numeric_answer(q["answer"]) + 10)
        assert not verify_question(altered)


@pytest.mark.parametrize("raw,expected", [("50%", Fraction(1, 2)), ("2/4", Fraction(1, 2)), ("x = -3", Fraction(-3)), (".25", Fraction(1, 4))])
def test_numeric_equivalence(raw, expected):
    assert numeric_answer(raw) == expected


@pytest.mark.parametrize("raw", ["__import__('os').system('echo bad')", "1/0", "2+2", "nan", "1e999999", ""])
def test_unsafe_or_ambiguous_answer_rejected(raw):
    with pytest.raises(ValueError):
        numeric_answer(raw)


def exam_for(state, course, **options):
    args = dict(topics=course["topics"], count=12, minutes=30, difficulty="Foundation", mode="Exam simulation", mix=True, calibrate=True, seed=12)
    args.update(options)
    return build_exam(course, state, **args)


def test_grading_and_snapshot_tamper_detection(setup):
    state, course = setup
    exam = exam_for(state, course)
    answers = {q["id"]: q["answer"] for q in exam["questions"]}
    result = grade_exam(exam, answers)
    assert result["earned"] == result["possible"] == 24
    answers[exam["questions"][0]["id"]] = ""
    assert grade_exam(exam, answers)["earned"] == 22
    exam["questions"][0]["answer"] = "9999"
    assert not exam_intact(exam)
    with pytest.raises(ValueError):
        grade_exam(exam, answers)


def test_short_mixed_paper_includes_both_question_formats(setup):
    state, course = setup
    exam = exam_for(state, course, count=5)
    assert sum(bool(q["choices"]) for q in exam["questions"]) == 3
    assert sum(not q["choices"] for q in exam["questions"]) == 2


def test_future_calibration_does_not_rewrite_past(setup):
    state, course = setup
    exam = exam_for(state, course)
    old = copy.deepcopy(exam)
    state["exams"].append(exam)
    review = calibration(exam, {"equations": 90, "graphs": 10}, "Real exam", pasted_pages("Real exam: equations and linear graphs."), "")
    state["calibrations"].append(review)
    future = exam_for(state, course, seed=55)
    assert exam == old and exam_intact(exam)
    assert exam["history_ids"] == []
    assert future["history_ids"] == [review["id"]]
    assert future["distribution"]["equations"] > exam["distribution"]["equations"]
    assert review["coverage"] == 100
    assert set(review["extra"]) == {"fractions", "quadratics", "probability"}
    assert not ({q["prompt"] for q in exam["questions"]} & {q["prompt"] for q in future["questions"]})


def test_weakness_does_not_change_exam_prediction(setup):
    state, course = setup
    baseline = exam_for(state, course)
    state["mistakes"] = [{"topic": "fractions", "course_id": course["id"]}]*5
    assert exam_for(state, course)["distribution"] == baseline["distribution"]
    targeted = exam_for(state, course, mode="Targeted practice")
    assert targeted["distribution"]["fractions"] > baseline["distribution"]["fractions"]


def test_scope_changes_leave_prior_sources_intact(setup):
    state, course = setup
    exam = exam_for(state, course)
    course["pages"][0]["text"] = "Different material"
    course["source_hash"] = digest(course["pages"])
    course["topics"] = ["fractions"]
    assert exam_intact(exam)
    assert exam["source_hash"] != course["source_hash"]
    with pytest.raises(ValueError):
        exam_for(state, course, topics=["equations"])


def test_sandbox_refund_never_creates_real_transfer(setup):
    state, _ = setup
    first = preview_order(state)
    preview_order(state)
    assert sandbox_totals(state["sandbox_orders"])["pledged_cents"] == 600
    first["refunded"] = True
    assert sandbox_totals(state["sandbox_orders"]) == {"orders": 1, "pledged_cents": 300, "paid_cents": 0}
    assert load_ledger()["batches"] == []


def test_pdf_student_copy_does_not_reveal_answers(setup):
    state, course = setup
    exam = exam_for(state, course)
    paper = exam_pdf(exam)
    key = exam_pdf(exam, True)
    paper_text = "\n".join(p.extract_text() for p in PdfReader(BytesIO(paper)).pages)
    key_text = "\n".join(p.extract_text() for p in PdfReader(BytesIO(key)).pages)
    assert "ANSWER KEY" not in paper_text and "Answer:" not in paper_text
    assert "ANSWER KEY" in key_text and "Answer:" in key_text
    assert "Yifan Yan" in paper_text
    assert len(extract_file("exam.pdf", paper)) > 0


def test_unverified_ai_quotes_are_dropped():
    pages = pasted_pages("We will study fractions and linear equations.")
    result = {"summary": "Topics", "unsupported": [], "topics": [
        {"topic": "fractions", "source_id": pages[0]["id"], "quote": "study fractions", "reason": "Present"},
        {"topic": "graphs", "source_id": pages[0]["id"], "quote": "slope of graphs", "reason": "Invented"}]}
    checked = validate_outline(result, pages)
    assert len(checked["topics"]) == 1 and checked["discarded"] == 1


def test_extraction_rejects_unsupported_and_empty():
    with pytest.raises(ValueError):
        extract_file("photo.png", b"anything")
    with pytest.raises(ValueError):
        extract_file("empty.txt", b"  ")


def test_ledger_rejects_unreceipted_transfer(tmp_path):
    data = {"batches": [{"id": "1", "eligible_orders": 2, "pledge_per_order_cents": 300, "adjustment_cents": 0, "sent_cents": 600}], "corrections": []}
    path = tmp_path / "ledger.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="receipt"):
        load_ledger(path)
    data["batches"][0]["receipt_url"] = "https://example.com/receipt"
    path.write_text(json.dumps(data))
    assert load_ledger(path)["batches"][0]["outstanding_cents"] == 0


def test_csv_formula_injection_is_neutralized():
    text = csv_bytes([{"label": "=SUM(A1:A9)"}]).decode("utf-8-sig")
    assert "'=SUM" in text

