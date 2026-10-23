"""A focused learning summary with optional source references."""
import json
import streamlit as st
from .catalog import TOPICS
from .engine import digest, local_outline
from .sample_cases import reviewed_cases

CONCEPTS = {
    "fractions": ("Common denominators", r"\frac{a}{b}+\frac{c}{d}=\frac{ad+bc}{bd}\quad(b,d\ne0)", "Explain why the denominators must describe equal-sized parts."),
    "equations": ("Inverse operations", r"ax+b=c\quad\Rightarrow\quad x=\frac{c-b}{a}\quad(a\ne0)", "Solve an equation, then substitute your answer to check both sides."),
    "graphs": ("Slope and intercept", r"y=mx+b\qquad m=\frac{\Delta y}{\Delta x}\quad(\Delta x\ne0)", "Identify the slope and intercept, then calculate a point on the line."),
    "quadratics": ("Factors and roots", r"(x-r_1)(x-r_2)=0\quad\Rightarrow\quad x=r_1\ \text{or}\ x=r_2", "Factor a quadratic and check each root in the original equation."),
    "probability": ("Equally likely outcomes", r"P(A)=\frac{\text{favourable outcomes}}{\text{all outcomes}}", "State the sample space and explain why its outcomes are equally likely."),
}
STATUSES = ["To review", "Studying", "Ready to practise"]


def build_summary(pages, outline, topics=None):
    """Keep quotations as quotations; never treat source working as verified."""
    selected = list(dict.fromkeys(t for t in (topics if topics is not None else
                                             [i["topic"] for i in outline["topics"]]) if t in TOPICS))
    evidence = {t: [] for t in selected}
    for page in pages:
        for item in local_outline([page])["topics"]:
            if item["topic"] in evidence:
                evidence[item["topic"]].append({"source_id": page["id"], "name": page["name"], "page": page["page"], "quote": item["quote"]})
    for item in outline["topics"]:
        page = next((p for p in pages if p["id"] == item["source_id"]), None)
        if (item["topic"] in evidence and page and item["quote"].strip()
                and " ".join(item["quote"].split()).casefold() in " ".join(page["text"].split()).casefold()
                and not any(e["source_id"] == page["id"] for e in evidence[item["topic"]])):
            evidence[item["topic"]].append({"source_id": page["id"], "name": page["name"], "page": page["page"], "quote": item["quote"]})
    found = {e["source_id"] for items in evidence.values() for e in items}
    return {"version": digest({"pages": pages, "topics": selected}), "topics": selected,
            "reviewed_mistakes": reviewed_cases(pages),
            "sources": len({p["name"] for p in pages}), "pages": len(pages),
            "characters": sum(len(p["text"]) for p in pages), "evidence": evidence,
            "needs_review": [p["id"] for p in pages if not p["text"].strip()
                             or "[unclear]" in p["text"].casefold() or p.get("uncertainties")],
            "unmatched": [p["id"] for p in pages if p["id"] not in found],
            "highlights": [{"source_id": p["id"], "name": p["name"], "page": p["page"],
                            "lines": [line.strip()[:300] for line in p["text"].splitlines() if line.strip()][:4]}
                           for p in pages]}


def board_for(owner, summary):
    board = owner.get("study_board", {})
    if board.get("version") != summary["version"]:
        board = {"version": summary["version"], "statuses": {t: STATUSES[0] for t in summary["topics"]}}
    return board



def skill_counts(cases, assessments=None):
    for label, attempt in assessments or []:
        if attempt and attempt.get("results"):
            rows = []
            for topic in dict.fromkeys(r["topic"] for r in attempt["results"]):
                results = [r for r in attempt["results"] if r["topic"] == topic]
                correct = sum(bool(r["correct"]) for r in results)
                rows.append({"Topic": TOPICS[topic]["name"], "Correct": correct,
                             "Needs practice": len(results)-correct, "Reviewed": len(results)})
            return label, rows
    rows = []
    for case in cases:
        observations = case["observations"]
        correct = sum(bool(o["correct"]) for o in observations)
        rows.append({"Topic": TOPICS[case["id"]]["name"], "Correct": correct,
                     "Needs practice": len(observations)-correct, "Reviewed": len(observations)})
    return "Fictional worksheet review", rows


def render_skill_chart(cases, assessments, key):
    source, rows = skill_counts(cases, assessments)
    total = sum(row["Reviewed"] for row in rows)
    limit = max(row["Reviewed"] for row in rows)
    st.markdown("#### Learning profile")
    st.caption(f"{source} · {total} marked answers · counts from the available work, not an overall ability estimate.")
    strengths, weaknesses = st.tabs(["Strengths", "Weaknesses"])
    for panel, field, color, subtitle in [
        (strengths, "Correct", "#38866a", "What is going well"),
        (weaknesses, "Needs practice", "#d7a14f", "Where to focus next"),
    ]:
        with panel:
            count = sum(row[field] for row in rows)
            st.markdown(f"**{subtitle} · {count} of {total} answers**")
            st.vega_lite_chart(rows, {
                "height": 290,
                "encoding": {
                    "x": {"field": "Topic", "type": "nominal", "title": None,
                          "sort": ["Fractions", "Linear equations", "Linear graphs"],
                          "axis": {"labelLimit": 110, "labelAngle": 0, "labelFontSize": 11}},
                    "y": {"field": field, "type": "quantitative", "title": "Answers",
                          "scale": {"domain": [0, limit], "nice": False},
                          "axis": {"values": list(range(limit+1)), "format": "d"}},
                    "tooltip": [{"field": "Topic"}, {"field": field, "type": "quantitative"},
                                {"field": "Reviewed", "type": "quantitative", "title": "Answers reviewed"}],
                },
                "layer": [
                    {"mark": {"type": "bar", "color": color, "cornerRadiusTopLeft": 4, "cornerRadiusTopRight": 4, "width": {"band": 0.55}}},
                    {"mark": {"type": "text", "dy": -10, "fontSize": 13, "color": "#294b38"},
                     "encoding": {"text": {"field": field, "type": "quantitative"}}},
                ],
                "config": {"view": {"stroke": None}, "axis": {"gridColor": "#e5ece3"}},
            }, width="stretch", height=290, key=f"{key}_chart_{field}")
            st.caption("Same vertical scale in both views. Hover over a bar to see how many answers were reviewed.")
            if field == "Correct" and cases and source == "Fictional worksheet review":
                for case in cases:
                    st.write(f"**{TOPICS[case['id']]['name']}:** {case['strength']}")
            if field == "Needs practice" and cases:
                render_mistakes(cases)
    if source == "Fictional worksheet review":
        with st.expander("See the marked examples behind these bars"):
            for case in cases:
                st.markdown(f"**{TOPICS[case['id']]['name']} · {case['source_name']}**")
                for observation in case["observations"]:
                    st.text(observation["evidence"])
                    if not observation["correct"]:
                        st.caption("Reference answer: " + observation["reference_answer"])


def render(pages, outline, *, key, owner, topics=None, save=None, heading=True, assessments=None):
    summary = build_summary(pages, outline, topics)
    # Retain previously saved board data for compatibility and export.
    board = board_for(owner, summary)
    if owner.get("study_board") != board:
        owner["study_board"] = board
        if save:
            save()
    prefix = f"summary_{key}_{summary['version'][:12]}"
    cases = summary["reviewed_mistakes"]
    with st.container(key=f"dashboard_{key}"):
        if heading:
            st.subheader("Your learning summary")
        names = ", ".join(TOPICS[t]["name"] for t in summary["topics"])
        st.caption(f"{summary['pages']} pages / sections · " + (names or "No topics selected yet"))
        if summary["needs_review"]:
            st.warning("Check the original pages: some text is missing, unclear, or flagged during transcription.")
        if cases or assessments:
            render_skill_chart(cases, assessments, prefix)
        else:
            if outline["method"].startswith("AI"):
                st.caption("AI-drafted overview · check against your sources")
                st.write(outline["summary"])
            else:
                st.write("Your materials cover **" + names + "**. Check the excerpts below before building practice." if names
                         else "Review the text and select the topics you want to practise.")
                st.caption("Local topic scan and source excerpts; student working is not a verified solution.")
            for item in summary["highlights"][:3]:
                with st.container(border=True):
                    st.caption(f"{item['name']} · page {item['page']}")
                    st.text("\n".join(item["lines"]) or "No text yet. Add it in the transcript review.")
        if summary["unmatched"]:
            st.caption(f"{len(summary['unmatched'])} section(s) have no match to the selected topics. You can inspect them in the source details below.")
        if outline.get("unsupported"):
            st.info("Outside the current question bank: " + ", ".join(outline["unsupported"]))
        if outline.get("discarded"):
            st.warning("Some AI source references failed verification and were removed.")

        st.markdown("#### Practise next")
        if cases:
            for case in cases:
                st.write(f"**{TOPICS[case['id']]['name']}:** {case['check']}")
        else:
            for topic in summary["topics"]:
                st.write(f"**{TOPICS[topic]['name']}:** {CONCEPTS[topic][2]}")
        st.caption("Confirm your reviewed material, then continue to the mock exam.")

        with st.expander("Check sources & formulas"):
            st.caption("Optional reference · general formulas are StudyBridge reference material, not extracted from your upload.")
            for topic in summary["topics"]:
                with st.expander(TOPICS[topic]["name"] + " · formula and evidence"):
                    st.latex(CONCEPTS[topic][1])
                    st.write(TOPICS[topic]["tip"])
                    matches = summary["evidence"][topic]
                    for evidence in matches:
                        st.caption(f"{evidence['name']} · page {evidence['page']}")
                        st.text(evidence["quote"])
                    if not matches:
                        st.caption("Manually selected topic; no source match found.")
            search = st.text_input("Search source text", key=f"{prefix}_search", placeholder="Find a word or equation", max_chars=120)
            visible = [p for p in pages if search.casefold() in p["text"].casefold() or search.casefold() in p["name"].casefold()]
            st.caption(f"{len(visible)} of {len(pages)} sections shown")
            for page in visible:
                with st.expander(f"{page['name']} · page {page['page']}", expanded=bool(search)):
                    st.text(page["text"] or "No text has been entered.")
            report = {"summary": summary, "study_board": owner.get("study_board"),
                      "method": outline["method"], "note": "Source excerpts are unverified; any saved study status is self-reported."}
            st.download_button("Download summary", json.dumps(report, ensure_ascii=False, indent=2),
                               "studybridge-summary.json", "application/json", key=f"{prefix}_export")


def render_mistakes(cases):
    st.markdown("#### What to fix")
    st.caption("Prepared review of the bundled fictional worksheets · not a live AI diagnosis.")
    for index, case in enumerate(cases):
        with st.expander(case["title"].split(" · ", 1)[-1], expanded=index == 0):
            st.write(case["finding"])
            st.latex(case["correction"])
            st.write("**Try this approach:** " + case["next_step"])
            with st.expander("See the student's working and follow-up answer"):
                st.caption(f"{case['source_name']} · page {case['page']}")
                st.text(case["evidence"])
                st.write("**Already demonstrated:** " + case["strength"])
                st.write(case["check"])
                st.latex(case["check_answer"])
