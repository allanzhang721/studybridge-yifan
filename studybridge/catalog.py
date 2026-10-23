"""Supported, computationally checked mathematics skills."""

TOPICS = {
    "fractions": {"name": "Fractions", "icon": "◒", "keywords": ["fraction", "denominator", "分数", "通分"], "tip": "Find a common denominator before adding. Simplify your final fraction."},
    "equations": {"name": "Linear equations", "icon": "＝", "keywords": ["equation", "solve", "方程", "代数"], "tip": "Undo addition first, then division. Substitute your answer into the original equation."},
    "graphs": {"name": "Linear graphs", "icon": "↗", "keywords": ["gradient", "slope", "linear graph", "斜率", "一次函数"], "tip": "In y = mx + b, m is the slope and b is the y-intercept. Keep track of signs."},
    "quadratics": {"name": "Quadratics", "icon": "∪", "keywords": ["quadratic", "factor", "二次", "因式"], "tip": "Use factors to locate the roots. Check each root by substitution."},
    "probability": {"name": "Probability", "icon": "◇", "keywords": ["probability", "random", "概率", "随机"], "tip": "Count favourable outcomes and all possible outcomes using the same sample space."},
}

SAMPLE_TEXT = """YEAR 9 MATHEMATICS — REVISION OUTLINE

Page 1: Fractions
Add and subtract fractions with different denominators. Simplify answers.
Example: 1/3 + 1/6 = 1/2.

Page 2: Linear equations
Solve one-variable equations. Explain inverse operations and check by substitution.
Example: 3x + 5 = 20, so x = 5.

Page 3: Linear graphs
Interpret slope and intercept in y = mx + b. Find y for a given x.
Example: y = 2x + 3. At x = 4, y = 11.

Page 4: Quadratics
Factor monic quadratics and identify their real integer roots.
Example: x^2 - 5x + 6 = (x - 2)(x - 3). The roots are 2 and 3.

Page 5: Probability
Calculate the probability of a single draw from a finite collection.
Example: a bag has 3 red and 2 blue counters. P(red) = 3/5.

Exam scope: all five topics above. Short numerical answers.
This is a fictional demonstration course, not a real teacher's assessment.
"""

SAMPLE_EXAM = """FICTIONAL POST-EXAM PAPER — FOR CALIBRATION PRACTICE ONLY
Q1. Add 2/3 and 1/4. [2 marks] Topic: fractions.
Q2. Solve the equation 4x + 3 = 19. [4 marks] Topic: equations.
Q3. Solve the equation 5x - 2 = 23. [4 marks] Topic: equations.
Q4. For the linear graph y = 3x + 1, find y when x = 2. [4 marks] Topic: graphs.
Q5. State the gradient of y = -2x + 7. [2 marks] Topic: graphs.
Q6. Find the larger root of the quadratic x^2 - 7x + 12 = 0. [4 marks] Topic: quadratics.
"""

