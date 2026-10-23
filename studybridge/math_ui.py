"""Presentation of checked question parameters; never parse user text as TeX."""
from fractions import Fraction

import streamlit as st

from .catalog import TOPICS


def number_tex(value):
    value = Fraction(value)
    sign = "-" if value < 0 else ""
    if value.denominator == 1:
        return str(value.numerator)
    return rf"{sign}\frac{{{abs(value.numerator)}}}{{{value.denominator}}}"


def question_math(q):
    """Return instruction, formula, and solution from the engine's numeric params."""
    p, topic = q["params"], q["topic"]
    answer = number_tex(q["answer"])
    if topic == "fractions":
        a, b, c, d, subtract = p
        op = "-" if subtract else "+"
        formula = rf"\frac{{{a}}}{{{b}}} {op} \frac{{{c}}}{{{d}}}"
        solution = rf"{formula} = \frac{{{a*d} {op} {c*b}}}{{{b*d}}} = {answer}"
        return "Calculate and simplify your fraction.", formula, solution
    if topic == "equations":
        a, b, c = p
        formula = f"{a}x + {b} = {c}"
        solution = rf"\begin{{aligned}}{a}x + {b} &= {c} \\ {a}x &= {c} - {b} = {c-b} \\ x &= \frac{{{c-b}}}{{{a}}} = {answer}\end{{aligned}}"
        return "Solve for x.", formula, solution
    if topic == "graphs":
        m, b, x, slope = p
        coefficient = "" if m == 1 else "-" if m == -1 else str(m)
        formula = f"y = {coefficient}x + {b}"
        instruction = "Find the slope of this line." if slope else f"Find y when x = {x}."
        solution = rf"y = mx + b \quad\Rightarrow\quad m = {m}" if slope else rf"y = {m}\times({x}) + {b} = {answer}"
        return instruction, formula, solution
    if topic == "quadratics":
        a, b = p
        return ("Find the larger root.", f"x^2 - {a+b}x + {a*b} = 0",
                rf"(x-{a})(x-{b}) = 0 \quad\Rightarrow\quad x \in \{{{a}, {b}\}}")
    if topic == "probability":
        red, blue, green = p
        return (q["prompt"], "", rf"P(\text{{red}}) = \frac{{{red}}}{{{red+blue+green}}} = {answer}")
    return q["prompt"], "", ""


def question(q, index=None):
    st.caption(f"{'QUESTION ' + str(index) + ' · ' if index else ''}{TOPICS[q['topic']]['name']} · {q['marks']} marks")
    instruction, formula, _ = question_math(q)
    st.write(instruction)
    if formula:
        st.latex(formula)


def solution(q):
    formula = question_math(q)[2]
    if formula:
        st.latex(formula)
    else:
        for step in q["steps"]:
            st.write(step)


def correction(q, submitted):
    left, right = st.columns(2)
    with left:
        st.caption("SUBMITTED ANSWER")
        # Student input is deliberately plain text, never interpolated into TeX.
        st.text(submitted or "Blank")
    with right:
        st.caption("CORRECT ANSWER")
        st.latex(number_tex(q["answer"]))
    solution(q)
