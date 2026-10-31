"""Original visual examples with independently linked educational references.

The SVGs are Practilume illustrations, not downloaded or traced reference images.
"""
from .engine import local_outline, make_course


def frame(content: str, label: str) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="600" height="330" viewBox="0 0 600 330" role="img" aria-label="{label}">
    <rect width="600" height="330" rx="18" fill="#edf3e7"/>
    <g font-family="Arial, sans-serif" fill="#183831">{content}</g></svg>'''


EXAMPLES = [
    {
        "id": "fractions", "title": "See why fractions need common units", "topic": "fractions",
        "description": "One third and one quarter become four twelfths and three twelfths.",
        "source": "https://commons.wikimedia.org/wiki/File:Somme_fractions_un_tiers_plus_un_quart.svg",
        "reference_title": "Fraction addition diagram", "credit": "Cdang · CC0 1.0",
        "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
        "notes": "Fractions: add and subtract fractions with unlike denominators. Example: 1/3 + 1/4. Use denominator 12: 4/12 + 3/12 = 7/12. A common mistake is adding both numerators and denominators to get 2/7. Count equal-sized parts instead. Practice new addition and subtraction examples and simplify the answers.",
        "prompt": "Why is 1/3 + 1/4 not 2/7?", "answer": "The parts have different sizes. Convert them to twelfths: 4/12 + 3/12 = 7/12.",
        "svg": frame('''<text x="32" y="43" font-size="16" font-weight="bold">FRACTIONS / SAME-SIZED PARTS</text>
        <text x="32" y="92" font-size="26">1/3 + 1/4</text><text x="32" y="131" font-size="18">4/12 + 3/12 = 7/12</text>
        <rect x="32" y="163" width="312" height="70" fill="#fff" stroke="#8eac9b"/>
        <rect x="32" y="163" width="104" height="70" fill="#087f6b"/>
        <rect x="136" y="163" width="78" height="70" fill="#c1d892"/>
        <path d="M58 163v70 M84 163v70 M110 163v70 M136 163v70 M162 163v70 M188 163v70 M214 163v70 M240 163v70 M266 163v70 M292 163v70 M318 163v70" stroke="#8eac9b"/>
        <text x="373" y="210" font-size="42" font-weight="bold">7/12</text>
        <text x="32" y="279" font-size="16">Seven shaded parts. Twelve equal parts in total.</text>''', 'One third plus one quarter equals seven twelfths'),
    },
    {
        "id": "graphs", "title": "Read the slope of a straight line", "topic": "graphs",
        "description": "Connect the coefficient in an equation with a visible rise and run.",
        "source": "https://commons.wikimedia.org/wiki/File:Wiki_slope_in_2d.svg",
        "reference_title": "Slope diagram", "credit": "Maschen; revisions by Lfahlberg and Svjo · CC BY-SA 3.0",
        "license_url": "https://creativecommons.org/licenses/by-sa/3.0/",
        "notes": "Linear graphs: for y = mx + b, the slope is m and the y-intercept is b. Example: y = 2x + 1 has slope 2. When x increases by 1, y increases by 2. Points (0, 1) and (1, 3) lie on this line. At x = 4, y = 9. Practice identifying slope and evaluating y for a given x. Do not confuse the intercept 1 with the slope 2.",
        "prompt": "For y = 2x + 1, what is y when x = 4?", "answer": "Substitute x = 4: y = 2 × 4 + 1 = 9. The slope is 2, not 1.",
        "svg": frame('''<text x="32" y="43" font-size="16" font-weight="bold">LINEAR GRAPHS / RISE OVER RUN</text>
        <path d="M55 265H310 M85 280V70" fill="none" stroke="#8eac9b" stroke-width="2"/>
        <path d="M60 255L240 75" stroke="#087f6b" stroke-width="4"/>
        <path d="M85 230H185V130" stroke="#809956" stroke-width="2" stroke-dasharray="6 4" fill="none"/>
        <circle cx="85" cy="230" r="5" fill="#087f6b"/><circle cx="185" cy="130" r="5" fill="#087f6b"/>
        <text x="113" y="252" font-size="16">run 1</text><text x="195" y="184" font-size="16">rise 2</text>
        <text x="65" y="306" font-size="13">Illustration; axis scales differ.</text>
        <text x="340" y="125" font-size="30">y = 2x + 1</text>
        <text x="340" y="176" font-size="21">slope = 2 / 1 = 2</text>
        <text x="340" y="217" font-size="17">At x = 4, y = 9.</text>''', 'Slope is rise two divided by run one'),
    },
    {
        "id": "probability", "title": "Count the possible outcomes", "topic": "probability",
        "description": "Start with a fair die, then practise the same counting idea with counters.",
        "source": "https://commons.wikimedia.org/wiki/File:Fair_dice_probability_distribution.svg",
        "reference_title": "Fair-die probability diagram", "credit": "Oleg Alexandrov · public domain",
        "license_url": "https://commons.wikimedia.org/wiki/File:Fair_dice_probability_distribution.svg#Licensing",
        "notes": "Probability: for equally likely outcomes, divide the number of favourable outcomes by the total. A fair six-sided die has six equally likely outcomes. P(rolling 4) = 1/6 and P(an even number) = 3/6 = 1/2. The same counting idea applies to a single random draw: a bag with three red and three blue counters has P(red) = 3/6 = 1/2. This app generates single-draw counter problems for practice.",
        "prompt": "What is the probability of an even result on a fair six-sided die?", "answer": "The favourable results are 2, 4 and 6. There are six equally likely results, so the probability is 3/6 = 1/2.",
        "svg": frame('''<text x="32" y="43" font-size="16" font-weight="bold">PROBABILITY / COUNT BEFORE DIVIDING</text>
        <text x="32" y="95" font-size="22">A fair six-sided die</text>''' + ''.join(
            f'<rect x="{32+i*90}" y="125" width="68" height="68" rx="12" fill="{"#087f6b" if (i+1)%2==0 else "#fff"}" stroke="#8eac9b"/>'
            f'<text x="{66+i*90}" y="170" text-anchor="middle" font-size="30" fill="{"#fff" if (i+1)%2==0 else "#183831"}">{i+1}</text>'
            for i in range(6)) + '''<text x="32" y="243" font-size="24">P(even) = 3/6 = 1/2</text>
        <text x="32" y="283" font-size="16">Three favourable outcomes out of six equally likely ones.</text>''', 'Outcomes two four and six give probability one half'),
    },
]


def example_course(example: dict) -> dict:
    pages = [{"id": f"example-{example['id']}", "name": f"Practilume checked notes · {example['title']}", "page": 1,
              "text": example["notes"] + "\nThese are manually prepared demonstration notes, not AI image extraction.\nExternal visual reference: " + example["source"]}]
    return make_course(example["title"], pages, local_outline(pages), [example["topic"]])
