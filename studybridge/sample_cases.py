"""Authored fictional student work and its reviewed teaching annotations."""
SAMPLES = [
    {"id": "fractions", "title": "01 · Fractions: unequal parts", "kind": "Conceptual error · adding denominators",
     "strength": "Adds fractions correctly when the denominators already match.",
     "evidence": "Student line 1: 1/3 + 1/4 = (1 + 1)/(3 + 4) = 2/7.",
     "finding": "The student adds denominators instead of converting to equal-sized parts.",
     "correction": r"\frac{1}{3}+\frac{1}{4}=\frac{4}{12}+\frac{3}{12}=\frac{7}{12}",
     "next_step": "Draw thirds and quarters on equal-sized bars; convert both to twelfths before adding.",
     "check": "Try 2/3 + 1/4 and explain what the denominator means.",
     "check_answer": r"\frac{2}{3}+\frac{1}{4}=\frac{8}{12}+\frac{3}{12}=\frac{11}{12}",
     "text": """PAGE 01: FRACTIONS - A REVISION ATTEMPT
Learning goal: add fractions with unlike denominators.

WHAT I CAN ALREADY DO
Question: calculate 2/7 + 3/7.
Student answer: 5/7. The parts are the same size.

STUDENT WORK TO REVIEW (CONTAINS A MISTAKE)
Question: calculate 1/3 + 1/4.
Student line 1: 1/3 + 1/4 = (1 + 1)/(3 + 4) = 2/7.
Student explanation: I added the top numbers and the bottom numbers.
Confidence before checking: high.

REVIEW PROMPT
Can adding a positive fraction make 1/3 smaller?
Draw the two fractions using equal-sized bars.

TRY A NEW QUESTION
Calculate 2/3 + 1/4. Explain what each denominator means.

Exam scope: fraction addition and subtraction.
Fictional student work; review the reasoning, not just the final answer."""},
    {"id": "equations", "title": "02 · Equations: keep the balance", "kind": "Procedure error · inverse operations",
     "strength": "Solves a simple multiplication equation: 4x = 20 gives x = 5.",
     "evidence": "Student line 1: 3x = 25.",
     "finding": "The first step adds 5 to the right-hand side instead of subtracting 5 from both sides.",
     "correction": r"\begin{aligned}3x+5&=20\\3x&=20-5=15\\x&=5\end{aligned}",
     "next_step": "Write the same operation on both sides, then substitute the solution to check the balance.",
     "check": "Solve 6x + 5 = 29 and check your answer in the original equation.",
     "check_answer": r"6x=29-5=24\quad\Rightarrow\quad x=4;\qquad6(4)+5=29",
     "text": """PAGE 02: LINEAR EQUATIONS - A REVISION ATTEMPT
Learning goal: solve equations using inverse operations.

WHAT I CAN ALREADY DO
Question: solve 4x = 20.
Student answer: x = 5. I divided both sides by 4.

STUDENT WORK TO REVIEW (CONTAINS A MISTAKE)
Question: solve 3x + 5 = 20.
Student line 1: 3x = 25.
Student line 2: x = 25/3.
Student explanation: I moved +5 to the right and added it.
Check: 3(25/3) + 5 = 30, which does not equal 20.
Confidence before checking: medium.

REVIEW PROMPT
Find the first step that breaks equality.
What operation should be applied to both sides?

TRY A NEW QUESTION
Solve 6x + 5 = 29. Check by substitution.

Exam scope: one-variable linear equations.
Fictional student work; review the reasoning, not just the final answer."""},
    {"id": "graphs", "title": "03 · Graphs: slope or intercept?", "kind": "Interpretation error · mixing graph features",
     "strength": "Substitutes x = 2 correctly into y = 2x + 1 to obtain y = 5.",
     "evidence": "Student answer: slope = 1; y-intercept = 2.",
     "finding": "The student swaps the coefficient of x and the constant when naming the graph features.",
     "correction": r"y=\underbrace{2}_{m}x+\underbrace{1}_{b}\qquad m=2,\quad b=1",
     "next_step": "Compare y = mx + b with a value table: the change in y identifies slope; x = 0 identifies intercept.",
     "check": "For y = -2x + 5, state the slope and y-intercept, then find y at x = 3.",
     "check_answer": r"m=-2,\quad b=5;\qquad y=-2(3)+5=-1",
     "text": """PAGE 03: LINEAR GRAPHS - A REVISION ATTEMPT
Learning goal: connect an equation with slope and intercept.

WHAT I CAN ALREADY DO
Equation: y = 2x + 1. Find y when x = 2.
Student working: y = 2(2) + 1 = 5.

STUDENT WORK TO REVIEW (CONTAINS A MISTAKE)
Question: state the slope and y-intercept of y = 2x + 1.
Student answer: slope = 1; y-intercept = 2.
Student explanation: the last number is the slope.
Confidence before checking: high.

VALUE TABLE FOR CHECKING
x = 0, y = 1; x = 1, y = 3; x = 2, y = 5.
What is y at x = 0? How much does y change per step?

TRY A NEW QUESTION
For y = -2x + 5, state slope and intercept.
Then find y when x = 3.

Exam scope: slope and evaluating linear functions.
Fictional student work; review the reasoning, not just the final answer."""},
]


# Five visible observations per page, with varied results. The original worked
# examples remain intact; additional answers make the summary more informative.
_OBSERVATIONS = {
    "fractions": [
        ("Student answer: 5/7. The parts are the same size.", True, "5/7"),
        ("Student line 1: 1/3 + 1/4 = (1 + 1)/(3 + 4) = 2/7.", False, "7/12"),
        ("A. 2/5 + 1/5: student answer 3/5. Correct.", True, "3/5"),
        ("B. 1/2 + 1/3: student answer 2/5. Needs practice.", False, "5/6"),
        ("C. 3/4 - 1/6: student answer 2/2. Needs practice.", False, "7/12"),
    ],
    "equations": [
        ("Student answer: x = 5. I divided both sides by 4.", True, "5"),
        ("Student line 2: x = 25/3.", False, "5"),
        ("A. 2x + 4 = 16: student answer x = 6. Correct.", True, "6"),
        ("B. 5x - 2 = 23: student answer x = 5. Correct.", True, "5"),
        ("C. 4x + 3 = 19: student answer x = 11/2. Needs practice.", False, "4"),
    ],
    "graphs": [
        ("Student working: y = 2(2) + 1 = 5.", True, "5"),
        ("Student answer: slope = 1; y-intercept = 2.", False, "slope = 2; y-intercept = 1"),
        ("A. y = 2x + 1 at x = 0: student answer y = 1. Correct.", True, "1"),
        ("B. y = 2x + 1 at x = 3: student answer y = 7. Correct.", True, "7"),
        ("C. y = -3x + 4 at x = 2: student answer y = -2. Correct.", True, "-2"),
    ],
}
for _sample in SAMPLES:
    _rows = _OBSERVATIONS[_sample["id"]]
    _sample["observations"] = [{"evidence": line, "correct": correct, "reference_answer": answer}
                               for line, correct, answer in _rows]
    _additional = "REVIEWED PRACTICE CHECK\n" + "\n".join(row[0] for row in _rows[2:])
    _sample["text"] = _sample["text"].replace("TRY A NEW QUESTION", _additional + "\n\nTRY A NEW QUESTION")


def reviewed_cases(pages):
    """Only attach authored annotations to exact, unchanged bundled source pages."""
    from hashlib import sha256
    from .worksheets import ASSETS
    cases = []
    for page in pages:
        for sample in SAMPLES:
            if (page.get("image_hash") == sha256((ASSETS / f"{sample['id']}.png").read_bytes()).hexdigest()
                    and page["text"].strip() == sample["text"].strip()):
                cases.append({k: v for k, v in sample.items() if k != "text"} | {
                    "source_id": page["id"], "source_name": page["name"], "page": page["page"]})
                break
    return cases
