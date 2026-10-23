"""Deterministic exam generation, exact grading, and forward-only calibration."""
from __future__ import annotations

import copy
import hashlib
import json
import math
import random
import re
import uuid
from datetime import datetime, timezone
from fractions import Fraction

from .catalog import TOPICS


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def identifier() -> str:
    return uuid.uuid4().hex[:16]


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def new_workspace() -> dict:
    return {"version": 1, "courses": [], "exams": [], "attempts": [], "calibrations": [],
            "mistakes": [], "sandbox_orders": [], "plus_preview": False, "ai_calls": 0}


def local_outline(pages: list[dict]) -> dict:
    """Keyword evidence is transparent, not presented as an AI understanding score."""
    hits = []
    for topic, meta in TOPICS.items():
        for page in pages:
            lines = [line.strip() for line in page["text"].splitlines() if line.strip()]
            line = next((line for line in lines if any(k in line.lower() for k in meta["keywords"])), None)
            if line:
                hits.append({"topic": topic, "source_id": page["id"], "quote": line[:220],
                             "reason": "Keyword match. Confirm this topic belongs in your exam scope."})
                break
    return {"summary": "Confirm the topic matches below before building an exam.", "topics": hits,
            "unsupported": [], "method": "Local keyword scan"}


def make_course(title: str, pages: list[dict], outline: dict, topics: list[str]) -> dict:
    if not title.strip() or not pages or not topics or any(t not in TOPICS for t in topics):
        raise ValueError("Add a course title, source material, and at least one supported topic.")
    return {"id": identifier(), "title": title.strip()[:90], "created": now(), "pages": copy.deepcopy(pages),
            "outline": copy.deepcopy(outline), "topics": list(dict.fromkeys(topics)),
            "source_hash": digest(pages)}


def fraction_text(value) -> str:
    f = Fraction(value)
    return str(f.numerator) if f.denominator == 1 else f"{f.numerator}/{f.denominator}"


def numeric_answer(raw: str) -> Fraction:
    text = str(raw).strip().replace("−", "-").replace(" ", "")
    if text.lower().startswith(("x=", "y=")):
        text = text[2:]
    if len(text) > 60 or not re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:/[+-]?\d+)?%?", text):
        raise ValueError("Use a number, fraction such as 3/4, or percentage. Expressions are not evaluated.")
    percent = text.endswith("%")
    text = text.rstrip("%")
    try:
        if "/" in text:
            a, b = text.split("/")
            value = Fraction(a) / Fraction(b)
        else:
            value = Fraction(text)
    except (ValueError, ZeroDivisionError):
        raise ValueError("Enter a valid number or a fraction with a non-zero denominator.") from None
    return value / 100 if percent else value


def question(topic: str, difficulty: str, rng: random.Random, kind: str = "Short answer") -> dict:
    hard = difficulty == "Challenge"
    n = 15 if hard else 8
    if topic == "fractions":
        a, b, c, d = rng.randint(1, n), rng.randint(2, n + 2), rng.randint(1, n), rng.randint(2, n + 2)
        subtract = hard and rng.choice([True, False])
        result = Fraction(a, b) - Fraction(c, d) if subtract else Fraction(a, b) + Fraction(c, d)
        op = "-" if subtract else "+"
        prompt = f"Calculate {a}/{b} {op} {c}/{d}. Give your answer as a simplified fraction."
        steps = [f"Use the common denominator {b*d}.", f"The numerator is {a*d} {op} {c*b}.", f"Simplify to {fraction_text(result)}."]
        params = [a, b, c, d, subtract]
    elif topic == "equations":
        a, x, b = rng.randint(2, n), rng.randint(-n if hard else 1, n), rng.randint(1, n)
        c = a*x + b
        result = Fraction(x)
        prompt = f"Solve for x: {a}x + {b} = {c}."
        steps = [f"Subtract {b} from both sides: {a}x = {c-b}.", f"Divide by {a}: x = {x}.", f"Check: {a} × ({x}) + {b} = {c}."]
        params = [a, b, c]
    elif topic == "graphs":
        m, b, x = rng.choice([i for i in range(-n, n + 1) if i]), rng.randint(1, n), rng.randint(-4 if hard else 1, n)
        slope = rng.choice([True, False])
        result = Fraction(m if slope else m*x+b)
        prompt = f"A straight line has equation y = {m}x + {b}. " + ("What is its slope?" if slope else f"Find y when x = {x}.")
        steps = ["Compare with y = mx + b.", f"The coefficient of x is {m}, so the slope is {m}."] if slope else [f"Substitute x = {x}.", f"y = {m} × ({x}) + {b} = {m*x+b}."]
        params = [m, b, x, slope]
    elif topic == "quadratics":
        r1, r2 = sorted(rng.sample(range(1, n + 3), 2))
        result = Fraction(r2)
        prompt = f"Find the larger root of x² - {r1+r2}x + {r1*r2} = 0."
        steps = [f"Find two numbers with sum {r1+r2} and product {r1*r2}: {r1} and {r2}.", f"Factor: (x - {r1})(x - {r2}) = 0.", f"The roots are {r1} and {r2}; the larger is {r2}."]
        params = [r1, r2]
    elif topic == "probability":
        red, blue, green = rng.randint(2, n), rng.randint(2, n), rng.randint(1, n) if hard else 0
        total = red + blue + green
        result = Fraction(red, total)
        prompt = f"A bag contains {red} red and {blue} blue counters" + (f" and {green} green counters" if green else "") + ". One counter is drawn at random. What is the probability it is red?"
        steps = [f"There are {total} counters in total.", f"There are {red} favourable outcomes.", f"P(red) = {red}/{total} = {fraction_text(result)}."]
        params = [red, blue, green]
    else:
        raise ValueError("Unsupported topic.")
    answer = fraction_text(result)
    choices = []
    if kind == "Multiple choice":
        offsets = rng.sample([-3, -2, -1, 1, 2, 3], 3)
        choices = [answer] + [fraction_text(result + Fraction(v, max(1, result.denominator))) for v in offsets]
        rng.shuffle(choices)
    return {"id": identifier(), "topic": topic, "prompt": prompt, "answer": answer, "steps": steps,
            "marks": 2, "kind": kind, "choices": choices, "params": params,
            "difficulty": difficulty, "verification": "Computed from template parameters"}


def verify_question(q: dict) -> bool:
    """Independent recomputation before an exam is released."""
    p, t = q["params"], q["topic"]
    if t == "fractions":
        expected = Fraction(p[0], p[1]) + (-1 if p[4] else 1)*Fraction(p[2], p[3])
    elif t == "equations":
        expected = Fraction(p[2]-p[1], p[0])
    elif t == "graphs":
        expected = Fraction(p[0] if p[3] else p[0]*p[2]+p[1])
    elif t == "quadratics":
        expected = Fraction(max(p))
    elif t == "probability":
        expected = Fraction(p[0], sum(p))
    else:
        return False
    return numeric_answer(q["answer"]) == expected and (not q["choices"] or len(set(q["choices"])) == 4 and q["answer"] in q["choices"])


def allocate(weights: dict[str, float], count: int) -> dict[str, int]:
    if count < len(weights) or not weights:
        raise ValueError("Choose at least one question per selected topic.")
    total = sum(max(0, v) for v in weights.values())
    normalized = {k: max(0, v)/total if total else 1/len(weights) for k, v in weights.items()}
    left = count-len(weights)
    raw = {k: normalized[k]*left for k in weights}
    result = {k: 1+math.floor(raw[k]) for k in weights}
    for k in sorted(weights, key=lambda k: raw[k]-math.floor(raw[k]), reverse=True)[:count-sum(result.values())]:
        result[k] += 1
    return result


def topic_performance(state: dict, course_id: str) -> dict:
    result = {t: {"correct": 0, "count": 0} for t in TOPICS}
    exam_ids = {e["id"] for e in state["exams"] if e["course_id"] == course_id}
    for attempt in state["attempts"]:
        if attempt["exam_id"] in exam_ids:
            for row in attempt["results"]:
                result[row["topic"]]["count"] += 1
                result[row["topic"]]["correct"] += int(row["correct"])
    return result


def build_exam(course: dict, state: dict, topics: list[str], count: int, minutes: int,
               difficulty: str, mode: str, mix: bool, calibrate: bool, seed: int | None = None) -> dict:
    if not topics or any(t not in course["topics"] for t in topics):
        raise ValueError("Select topics within the confirmed course scope.")
    if not len(topics) <= count <= 20 or not 5 <= minutes <= 180:
        raise ValueError("Unsupported exam size or duration.")
    weights = {t: 1.0 for t in topics}
    history = [c for c in state["calibrations"] if c["course_id"] == course["id"]]
    used_history = []
    if mode == "Targeted practice":
        performance = topic_performance(state, course["id"])
        for t in topics:
            p = performance[t]
            weights[t] = 1 + (2 * (1-p["correct"]/p["count"]) if p["count"] else 0)
            weights[t] += min(2, sum(m["topic"] == t and m["course_id"] == course["id"] for m in state["mistakes"]))
    elif calibrate and history:
        # Blend a uniform prior with observed mark shares. This is not a probability of future questions.
        recent = history[-3:]
        used_history = [h["id"] for h in recent]
        for t in topics:
            shares = [h["actual_marks"].get(t, 0)/max(1, sum(h["actual_marks"].values())) for h in recent]
            weights[t] = 0.5/len(topics) + 0.5*sum(shares)/len(shares)
    distribution = allocate(weights, count)
    rng = random.Random(seed if seed is not None else random.SystemRandom().randrange(2**32))
    questions, seen = [], set()
    previous = {q["prompt"] for e in state["exams"] if e["course_id"] == course["id"] for q in e["questions"]}
    for t, amount in distribution.items():
        for i in range(amount):
            for _ in range(500):
                q = question(t, difficulty, rng, "Multiple choice" if mix and len(questions) % 2 == 0 else "Short answer")
                if q["prompt"] not in seen and q["prompt"] not in previous:
                    break
            else:
                raise ValueError("This topic's fresh question pool is exhausted. Choose a different difficulty or start a new course.")
            if not verify_question(q):
                raise ValueError("An answer failed verification. No exam was saved.")
            seen.add(q["prompt"])
            questions.append(q)
    rng.shuffle(questions)
    baseline = allocate({t: 1 for t in topics}, count)
    payload = {"id": identifier(), "course_id": course["id"], "course_title": course["title"],
               "created": now(), "source_hash": course["source_hash"],
               "source_snapshot": [{"id": p["id"], "name": p["name"], "hash": digest(p["text"])} for p in course["pages"]],
               "topics": topics[:], "minutes": minutes, "mode": mode, "difficulty": difficulty,
               "questions": questions, "distribution": distribution, "baseline_distribution": baseline,
               "history_ids": used_history, "rubric": "2 marks for each correct final answer. No automatic method marks.",
               "evidence": copy.deepcopy(course["outline"]["topics"])}
    payload["fingerprint"] = digest(payload)
    return payload


def exam_intact(exam: dict) -> bool:
    return exam.get("fingerprint") == digest({k: v for k, v in exam.items() if k != "fingerprint"})


def grade_exam(exam: dict, answers: dict[str, str]) -> dict:
    if not exam_intact(exam):
        raise ValueError("The saved exam snapshot has changed. Grading was stopped.")
    results = []
    for q in exam["questions"]:
        raw = answers.get(q["id"], "").strip()
        try:
            correct = numeric_answer(raw) == numeric_answer(q["answer"])
            issue = ""
        except ValueError as exc:
            correct, issue = False, "Unanswered" if not raw else str(exc)
        results.append({"question_id": q["id"], "topic": q["topic"], "submitted": raw,
                        "correct": correct, "earned": q["marks"] if correct else 0,
                        "possible": q["marks"], "issue": issue})
    return {"id": identifier(), "exam_id": exam["id"], "created": now(), "results": results,
            "earned": sum(r["earned"] for r in results), "possible": sum(r["possible"] for r in results)}


def distribution_error(predicted: dict, actual: dict) -> float:
    ptotal, atotal = sum(predicted.values()), sum(actual.values())
    if ptotal <= 0 or atotal <= 0:
        raise ValueError("Both distributions need positive totals.")
    return round(100 * sum(abs(predicted.get(t, 0)/ptotal-actual.get(t, 0)/atotal) for t in set(predicted)|set(actual))/2, 1)


def calibration(exam: dict, actual_marks: dict, label: str, pages: list[dict], note: str) -> dict:
    if not exam_intact(exam):
        raise ValueError("The original exam failed its snapshot check.")
    if any(t not in TOPICS or not isinstance(m, int) or m < 0 or m > 500 for t, m in actual_marks.items()):
        raise ValueError("Marks must be whole numbers from 0 to 500 for supported topics.")
    actual = {t: m for t, m in actual_marks.items() if m}
    if not actual or not pages:
        raise ValueError("Attach the post-exam source and enter its topic marks.")
    predicted = exam["distribution"]
    hits = set(predicted) & set(actual)
    return {"id": identifier(), "course_id": exam["course_id"], "exam_id": exam["id"], "created": now(),
            "label": label.strip()[:100], "actual_marks": actual, "pages": copy.deepcopy(pages), "note": note[:1500],
            "exam_fingerprint": exam["fingerprint"], "coverage": round(100*sum(actual[t] for t in hits)/sum(actual.values()), 1),
            "missed": sorted(set(actual)-set(predicted)), "extra": sorted(set(predicted)-set(actual)),
            "distribution_error": distribution_error(predicted, actual),
            "baseline_error": distribution_error(exam["baseline_distribution"], actual)}


def preview_order(state: dict) -> dict:
    """Sandbox only. Never mixed into the public ledger or treated as a payment."""
    order = {"id": identifier(), "created": now(), "price_cents": 2900, "pledge_cents": 300,
             "status": "sandbox", "refunded": False}
    state["sandbox_orders"].append(order)
    state["plus_preview"] = True
    return order


def sandbox_totals(orders: list[dict]) -> dict:
    eligible = [o for o in orders if not o["refunded"]]
    return {"orders": len(eligible), "pledged_cents": sum(o["pledge_cents"] for o in eligible), "paid_cents": 0}

