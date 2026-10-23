"""Printable student papers and separate answer keys."""
from io import BytesIO
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, KeepTogether, HRFlowable


def exam_pdf(exam: dict, answers: bool = False) -> bytes:
    out = BytesIO()
    font = "Helvetica"
    if any(ord(c) > 0x2FFF for c in exam["course_title"]):
        if "STSong-Light" not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        font = "STSong-Light"
    styles = getSampleStyleSheet()
    body = ParagraphStyle("StudyBody", fontName=font, fontSize=11, leading=17, spaceAfter=8, textColor=colors.HexColor("#183831"))
    title = ParagraphStyle("StudyTitle", parent=body, fontSize=23, leading=29, spaceAfter=12)
    small = ParagraphStyle("StudySmall", parent=body, fontSize=9, leading=13, textColor=colors.HexColor("#536B63"))
    heading = ParagraphStyle("StudyQuestion", parent=body, fontSize=11, leading=17, spaceAfter=8)
    doc = SimpleDocTemplate(out, pagesize=A4, rightMargin=48, leftMargin=48, topMargin=48, bottomMargin=48,
                            title=exam["course_title"] + (" - Answer key" if answers else " - Mock exam"), author="Yifan Yan")
    story = [Paragraph("STUDYBRIDGE / " + ("ANSWER KEY" if answers else "MOCK EXAM"), small),
             Paragraph(escape(exam["course_title"]), title),
             Paragraph(f"{len(exam['questions'])} questions  |  {sum(q['marks'] for q in exam['questions'])} marks  |  {exam['minutes']} minutes", body),
             Paragraph("Practice assessment. This is not a prediction of an actual examination.", small),
             Paragraph(f"Snapshot: {escape(exam['fingerprint'][:20])} | Created: {escape(exam['created'][:10])}", small),
             HRFlowable(width="100%", color=colors.HexColor("#BDD9CE")), Spacer(1, 16)]
    if not answers:
        story.extend([Paragraph("Name: __________________________    Date: ______________", body),
                      Paragraph(escape(exam["rubric"]), small), Spacer(1, 12)])
    for i, q in enumerate(exam["questions"], 1):
        block = [Paragraph(f"<b>{i}.</b> {escape(q['prompt'])} <b>[{q['marks']} marks]</b>", heading)]
        if answers:
            block.append(Paragraph(f"<b>Answer: {escape(q['answer'])}</b>", body))
            block.extend(Paragraph(escape(step), small) for step in q["steps"])
        else:
            if q["choices"]:
                block.extend(Paragraph(f"{chr(65+j)}. {escape(choice)}", small) for j, choice in enumerate(q["choices"]))
            block.append(Spacer(1, 34))
            block.append(HRFlowable(width="100%", color=colors.HexColor("#DEE7E2"), thickness=0.5))
        block.append(Spacer(1, 18))
        story.append(KeepTogether(block))

    def footer(canvas, document):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#536B63"))
        canvas.drawString(48, 28, "StudyBridge | Created by Yifan Yan")
        canvas.drawRightString(A4[0]-48, 28, f"Page {document.page}")
        canvas.restoreState()
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return out.getvalue()

