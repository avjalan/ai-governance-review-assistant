"""Generate a detailed, downloadable LaunchGate assessment."""

from io import BytesIO
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether

_REGULAR_FONT = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
_BOLD_FONT = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")

if _REGULAR_FONT.exists() and _BOLD_FONT.exists():
    pdfmetrics.registerFont(TTFont("LaunchGate-Regular", str(_REGULAR_FONT)))
    pdfmetrics.registerFont(TTFont("LaunchGate-Bold", str(_BOLD_FONT)))
    BODY_FONT = "LaunchGate-Regular"
    BOLD_FONT = "LaunchGate-Bold"
else:
    # Built-in PDF fonts work on macOS, Windows, and Linux without local files.
    BODY_FONT = "Helvetica"
    BOLD_FONT = "Helvetica-Bold"


def _text(value):
    return str(value or "Not provided").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_pdf_report(record, reduction_options):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=.65*inch, leftMargin=.65*inch, topMargin=.65*inch, bottomMargin=.65*inch)
    styles = getSampleStyleSheet()
    for style in styles.byName.values():
        style.fontName = BODY_FONT
    styles["Title"].fontName = styles["Heading1"].fontName = styles["Heading2"].fontName = styles["Heading3"].fontName = BOLD_FONT
    styles.add(ParagraphStyle(name="TitleDark", parent=styles["Title"], fontName=BOLD_FONT, textColor=colors.HexColor("#5138A5"), alignment=TA_CENTER, spaceAfter=16))
    styles.add(ParagraphStyle(name="Section", parent=styles["Heading2"], fontName=BOLD_FONT, textColor=colors.HexColor("#5138A5"), spaceBefore=14, spaceAfter=8))
    styles.add(ParagraphStyle(name="Small", parent=styles["BodyText"], fontName=BODY_FONT, fontSize=8.5, leading=11, textColor=colors.HexColor("#555555")))
    story = [Paragraph("LaunchGate AI Use Case Review", styles["TitleDark"]), Paragraph(f"Review {_text(record.get('review_id'))} | {_text(record.get('generated_at_utc'))}", styles["Small"]), Spacer(1, 12)]
    story += [Paragraph("Preliminary decision", styles["Section"]), Paragraph(_text(record.get("gate")).replace("_", " "), styles["Heading3"])]
    for reason in record.get("gate_reasons", []):
        story.append(Paragraph("• " + _text(reason), styles["BodyText"]))
    assessment = record.get("assessment", {})
    story += [Spacer(1, 8), Paragraph(_text(assessment.get("executive_summary")), styles["BodyText"])]

    story += [Paragraph("How this review was produced", styles["Section"]), Paragraph("LaunchGate combines deterministic launch gates with AI-assisted analysis. Hard blockers and missing-evidence rules are evaluated separately from the model's narrative risk analysis. The control themes are informed by NIST AI RMF, ISO/IEC 42001 management-system concepts, and OWASP guidance for LLM applications. This report is decision support, not a certification or legal opinion.", styles["BodyText"])]

    domains = assessment.get("risk_domains", {})
    rows = [["Area", "Score", "What drives it"]]
    labels = {"privacy":"Privacy", "security":"Security", "ai_security":"AI security", "reliability":"Reliability", "intellectual_property":"Intellectual property", "compliance":"Compliance"}
    for key, label in labels.items():
        item = domains.get(key, {})
        rows.append([label, f"{item.get('score', 0)}/10", Paragraph(_text(item.get("rationale")), styles["Small"])])
    table = Table(rows, colWidths=[1.35*inch, .65*inch, 4.45*inch], repeatRows=1)
    table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#5138A5")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),.35,colors.HexColor("#D8D3E8")),("VALIGN",(0,0),(-1,-1),"TOP"),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#F7F5FC")]),("FONTNAME",(0,0),(-1,0),BOLD_FONT),("FONTNAME",(0,1),(-1,-1),BODY_FONT),("FONTSIZE",(0,0),(-1,-1),8.5),("LEADING",(0,0),(-1,-1),11),("LEFTPADDING",(0,0),(-1,-1),6),("RIGHTPADDING",(0,0),(-1,-1),6),("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6)]))
    story += [Paragraph("Risk detail", styles["Section"]), table]

    story += [Paragraph("Ways to reduce risk", styles["Section"])]
    for option in reduction_options:
        story.append(Paragraph(f"<b>{_text(option['title'])}</b> - {_text(option['action'])}", styles["BodyText"]))

    sections = [("Information still needed", record.get("deterministic_evidence_requirements", []) + assessment.get("missing_evidence", []), "question"), ("Recommended actions", assessment.get("recommended_actions", []), "action"), ("Tests before launch", assessment.get("evaluation_plan", []), "test"), ("People to involve", assessment.get("required_reviews", []), "reviewer"), ("What could go wrong", assessment.get("threat_scenarios", []), "scenario")]
    for title, items, primary in sections:
        block = [Paragraph(title, styles["Section"])]
        if not items:
            block.append(Paragraph("No items identified.", styles["Small"]))
        for item in items:
            if isinstance(item, dict):
                headline = item.get(primary, "Item")
                detail = item.get("why_it_matters") or item.get("reason") or item.get("mitigation") or item.get("success_criterion") or ""
                block.append(Paragraph(f"<b>{_text(headline)}</b><br/>{_text(detail)}", styles["BodyText"]))
            else:
                block.append(Paragraph("• " + _text(item), styles["BodyText"]))
        story.append(KeepTogether(block))

    story += [Paragraph("Use case record", styles["Section"])]
    for key, value in record.get("system", {}).items():
        story.append(Paragraph(f"<b>{_text(key.replace('_',' ').title())}:</b> {_text(value)}", styles["Small"]))
    story += [Spacer(1, 14), Paragraph("Framework note", styles["Section"]), Paragraph("Framework references are used as organizing guidance only. LaunchGate does not claim that completing this review establishes compliance with NIST, ISO/IEC 42001, OWASP, or any law. A qualified owner must verify evidence and approve deployment.", styles["Small"])]

    def footer(canvas, document):
        canvas.saveState()
        canvas.setFont(BODY_FONT, 8)
        canvas.setFillColor(colors.HexColor("#777777"))
        canvas.drawString(.65*inch, .35*inch, "LaunchGate - preliminary decision support")
        canvas.drawRightString(7.85*inch, .35*inch, f"Page {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
