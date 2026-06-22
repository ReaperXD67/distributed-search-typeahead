"""Generate the submission-ready PROJECT_REPORT.pdf from PROJECT_REPORT.md."""

from __future__ import annotations

import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Flowable,
    Image,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "PROJECT_REPORT.md"
OUTPUT = ROOT / "output" / "pdf" / "PROJECT_REPORT.pdf"
SCREENSHOT = ROOT / "docs" / "screenshots" / "home.png"
VIDEO_URL = "https://drive.google.com/file/d/1MpjkRs8duS4mZLpqcqrK3bg0dXgdk5ct/view?usp=sharing"

INK = colors.HexColor("#111827")
NAVY = colors.HexColor("#13294B")
TEAL = colors.HexColor("#0F9D8A")
PALE = colors.HexColor("#EAF7F4")
MIST = colors.HexColor("#F3F6FA")
SLATE = colors.HexColor("#667085")
LINE = colors.HexColor("#D8DEE8")


class ArchitectureDiagram(Flowable):
    def __init__(self, width: float = 170 * mm, height: float = 90 * mm) -> None:
        super().__init__()
        self.width = width
        self.height = height

    def _box(self, canvas, x, y, w, h, title, subtitle, fill=colors.white):
        canvas.setFillColor(fill)
        canvas.setStrokeColor(LINE)
        canvas.roundRect(x, y, w, h, 5, fill=1, stroke=1)
        canvas.setFillColor(NAVY)
        canvas.setFont("Helvetica-Bold", 8)
        canvas.drawCentredString(x + w / 2, y + h / 2 + 3, title)
        if subtitle:
            canvas.setFillColor(SLATE)
            canvas.setFont("Helvetica", 5.8)
            canvas.drawCentredString(x + w / 2, y + h / 2 - 7, subtitle)

    def _arrow(self, canvas, x1, y1, x2, y2, label=""):
        canvas.setStrokeColor(colors.HexColor("#8AA5B5"))
        canvas.setFillColor(colors.HexColor("#8AA5B5"))
        canvas.setLineWidth(1)
        canvas.line(x1, y1, x2, y2)
        angle = 4
        if abs(x2 - x1) >= abs(y2 - y1):
            direction = 1 if x2 > x1 else -1
            canvas.line(x2, y2, x2 - direction * angle, y2 + angle / 2)
            canvas.line(x2, y2, x2 - direction * angle, y2 - angle / 2)
        else:
            direction = 1 if y2 > y1 else -1
            canvas.line(x2, y2, x2 + angle / 2, y2 - direction * angle)
            canvas.line(x2, y2, x2 - angle / 2, y2 - direction * angle)
        if label:
            canvas.setFont("Helvetica", 5.5)
            canvas.setFillColor(SLATE)
            canvas.drawCentredString((x1 + x2) / 2, (y1 + y2) / 2 + 3, label)

    def draw(self) -> None:
        c = self.canv
        w = self.width
        box_w = 29 * mm
        box_h = 15 * mm
        top_y = self.height - 24 * mm
        x_positions = [2 * mm, 47 * mm, 92 * mm, 137 * mm]

        self._box(c, x_positions[0], top_y, box_w, box_h, "User browser", "React interaction")
        self._box(c, x_positions[1], top_y, box_w, box_h, "Nginx + UI", "Static host and proxy")
        self._box(c, x_positions[2], top_y, box_w, box_h, "FastAPI", "Async API service", PALE)
        self._box(c, x_positions[3], top_y, box_w, box_h, "Hash ring", "SHA-256 + 128 vnodes")
        for left, right in zip(x_positions, x_positions[1:]):
            self._arrow(c, left + box_w, top_y + box_h / 2, right, top_y + box_h / 2)

        redis_y = top_y - 27 * mm
        redis_w = 26 * mm
        for index, x in enumerate([89 * mm, 119 * mm, 149 * mm], start=1):
            self._box(c, x, redis_y, redis_w, 13 * mm, f"Redis {index}", "Suggestion cache")
        self._arrow(c, x_positions[3] + box_w / 2, top_y, 132 * mm, redis_y + 13 * mm)

        bottom_y = 3 * mm
        self._box(c, 6 * mm, bottom_y, 33 * mm, box_h, "Trending sets", "Minute buckets + TTL")
        self._box(c, 50 * mm, bottom_y, 31 * mm, box_h, "Redis Stream", "AOF durable queue")
        self._box(c, 92 * mm, bottom_y, 31 * mm, box_h, "Batch worker", "Aggregate + retry")
        self._box(c, 137 * mm, bottom_y, 31 * mm, box_h, "PostgreSQL", "Durable source of truth", PALE)

        api_center_x = x_positions[2] + box_w / 2
        self._arrow(c, api_center_x, top_y, 22.5 * mm, bottom_y + box_h, "ZINCRBY")
        self._arrow(c, api_center_x, top_y, 65.5 * mm, bottom_y + box_h, "XADD")
        self._arrow(c, 81 * mm, bottom_y + box_h / 2, 92 * mm, bottom_y + box_h / 2)
        self._arrow(c, 123 * mm, bottom_y + box_h / 2, 137 * mm, bottom_y + box_h / 2)


def inline_markup(text: str) -> str:
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(
        r"\[([^\]]+)\]\((https?://[^)]+)\)",
        r'<link href="\2" color="#0F9D8A"><u>\1</u></link>',
        text,
    )
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`([^`]+)`", r'<font name="Courier">\1</font>', text)
    return text


def page_chrome(canvas, doc) -> None:
    canvas.saveState()
    width, height = A4
    canvas.setStrokeColor(LINE)
    canvas.line(20 * mm, height - 15 * mm, width - 20 * mm, height - 15 * mm)
    canvas.setFillColor(NAVY)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(20 * mm, height - 11 * mm, "SUGGEST")
    canvas.setFillColor(SLATE)
    canvas.setFont("Helvetica", 7)
    canvas.drawRightString(width - 20 * mm, height - 11 * mm, "Distributed Search Typeahead - Project Report")
    canvas.line(20 * mm, 14 * mm, width - 20 * mm, 14 * mm)
    canvas.drawString(20 * mm, 9 * mm, "HLD101 Assignment")
    canvas.drawRightString(width - 20 * mm, 9 * mm, f"Page {doc.page}")
    canvas.restoreState()


def cover_chrome(canvas, doc) -> None:
    canvas.saveState()
    width, height = A4
    canvas.setFillColor(NAVY)
    canvas.rect(0, height - 57 * mm, width, 57 * mm, fill=1, stroke=0)
    canvas.setFillColor(TEAL)
    canvas.rect(0, height - 60 * mm, width, 3 * mm, fill=1, stroke=0)
    canvas.restoreState()


def build_styles():
    sample = getSampleStyleSheet()
    return {
        "cover_title": ParagraphStyle(
            "CoverTitle", parent=sample["Title"], fontName="Helvetica-Bold", fontSize=28,
            leading=33, textColor=colors.white, alignment=TA_CENTER, spaceAfter=8 * mm,
        ),
        "cover_subtitle": ParagraphStyle(
            "CoverSubtitle", parent=sample["Normal"], fontName="Helvetica", fontSize=12,
            leading=17, textColor=colors.HexColor("#D8E5F4"), alignment=TA_CENTER,
        ),
        "h1": ParagraphStyle(
            "H1", parent=sample["Heading1"], fontName="Helvetica-Bold", fontSize=18,
            leading=22, textColor=NAVY, spaceBefore=6 * mm, spaceAfter=3 * mm,
            keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "H2", parent=sample["Heading2"], fontName="Helvetica-Bold", fontSize=12,
            leading=15, textColor=TEAL, spaceBefore=4 * mm, spaceAfter=2 * mm,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "Body", parent=sample["BodyText"], fontName="Helvetica", fontSize=8.6,
            leading=12.4, textColor=INK, spaceAfter=2.2 * mm, alignment=TA_LEFT,
        ),
        "table_header": ParagraphStyle(
            "TableHeader", parent=sample["BodyText"], fontName="Helvetica-Bold", fontSize=8,
            leading=10.5, textColor=colors.white,
        ),
        "bullet": ParagraphStyle(
            "Bullet", parent=sample["BodyText"], fontName="Helvetica", fontSize=8.4,
            leading=11.8, textColor=INK, leftIndent=5 * mm, firstLineIndent=-3 * mm,
            bulletIndent=1 * mm, spaceAfter=1.4 * mm,
        ),
        "code": ParagraphStyle(
            "Code", parent=sample["Code"], fontName="Courier", fontSize=7.2,
            leading=10, textColor=colors.HexColor("#243447"), backColor=MIST,
            borderColor=LINE, borderWidth=0.5, borderPadding=6, spaceAfter=3 * mm,
        ),
        "caption": ParagraphStyle(
            "Caption", parent=sample["Normal"], fontName="Helvetica-Oblique", fontSize=7,
            leading=9, textColor=SLATE, alignment=TA_CENTER, spaceAfter=3 * mm,
        ),
    }


def make_table(rows, available_width, styles):
    columns = max(len(row) for row in rows)
    normalized = [row + [""] * (columns - len(row)) for row in rows]
    wrapped = []
    for row_number, row in enumerate(normalized):
        style = styles["table_header"] if row_number == 0 else styles["body"]
        wrapped.append([Paragraph(inline_markup(cell), style) for cell in row])
    widths = [available_width / columns] * columns
    table = Table(wrapped, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, MIST]),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def parse_markdown(lines, styles, width):
    story = []
    paragraph_buffer = []
    index = 0

    def flush_paragraph():
        if paragraph_buffer:
            joined = " ".join(item.strip() for item in paragraph_buffer)
            story.append(Paragraph(inline_markup(joined), styles["body"]))
            paragraph_buffer.clear()

    while index < len(lines):
        line = lines[index].rstrip()
        if line.startswith("# "):
            index += 1
            continue
        if line.startswith("## "):
            flush_paragraph()
            title = line[3:].strip()
            story.append(Paragraph(inline_markup(title), styles["h1"]))
            if title.startswith("1. Architecture"):
                story.append(Spacer(1, 2 * mm))
                story.append(ArchitectureDiagram())
                story.append(Paragraph("Figure 1. Production data flow and storage responsibilities.", styles["caption"]))
            index += 1
            continue
        if line.startswith("### "):
            flush_paragraph()
            story.append(Paragraph(inline_markup(line[4:].strip()), styles["h2"]))
            index += 1
            continue
        if line.startswith("```mermaid"):
            flush_paragraph()
            index += 1
            while index < len(lines) and not lines[index].startswith("```"):
                index += 1
            index += 1
            continue
        if line.startswith("```"):
            flush_paragraph()
            code_lines = []
            index += 1
            while index < len(lines) and not lines[index].startswith("```"):
                code_lines.append(lines[index].rstrip())
                index += 1
            story.append(Preformatted("\n".join(code_lines), styles["code"], maxLineLength=95))
            index += 1
            continue
        if line.startswith("|"):
            flush_paragraph()
            table_lines = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_lines.append(lines[index].strip())
                index += 1
            rows = []
            for number, raw in enumerate(table_lines):
                cells = [cell.strip() for cell in raw.strip("|").split("|")]
                if number == 1 and all(set(cell) <= {"-", ":"} for cell in cells):
                    continue
                rows.append(cells)
            story.append(make_table(rows, width, styles))
            story.append(Spacer(1, 3 * mm))
            continue
        if re.match(r"^\d+\. ", line):
            flush_paragraph()
            number, content = line.split(". ", 1)
            story.append(Paragraph(inline_markup(content), styles["bullet"], bulletText=f"{number}."))
            index += 1
            continue
        if line.startswith("- "):
            flush_paragraph()
            story.append(Paragraph(inline_markup(line[2:]), styles["bullet"], bulletText="-"))
            index += 1
            continue
        if not line.strip():
            flush_paragraph()
        else:
            paragraph_buffer.append(line)
        index += 1
    flush_paragraph()
    return story


def build() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    styles = build_styles()
    doc = SimpleDocTemplate(
        str(OUTPUT), pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=21 * mm, bottomMargin=19 * mm, title="Suggest Project Report",
        author="Aman Kumar", subject="HLD101 Search Typeahead Assignment",
    )

    story = [Spacer(1, 3 * mm)]
    story.append(Paragraph("SUGGEST", styles["cover_title"]))
    story.append(Paragraph("Distributed Search Typeahead System", styles["cover_subtitle"]))
    story.append(Spacer(1, 15 * mm))
    if SCREENSHOT.exists():
        image = Image(str(SCREENSHOT), width=170 * mm, height=95.6 * mm)
        story.append(image)
        story.append(Spacer(1, 8 * mm))
    metadata = Table([
        ["Course", "HLD101 Search Typeahead Assignment"],
        ["Prepared by", "Aman Kumar"],
        ["Repository", "github.com/ReaperXD67/distributed-search-typeahead"],
        [
            "Demo video",
            Paragraph(
                f'<link href="{VIDEO_URL}" color="#0F9D8A"><u>Watch project demonstration</u></link>',
                styles["body"],
            ),
        ],
        ["Report date", "22 June 2026"],
    ], colWidths=[32 * mm, 118 * mm], hAlign="CENTER")
    metadata.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), MIST),
        ("TEXTCOLOR", (0, 0), (0, -1), NAVY),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(metadata)
    story.append(PageBreak())

    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    content_start = next(
        index for index, line in enumerate(lines) if line.strip() == "## Executive Summary"
    )
    lines = lines[content_start:]
    story.extend(parse_markdown(lines, styles, doc.width))
    doc.build(story, onFirstPage=cover_chrome, onLaterPages=page_chrome)
    print(f"Generated {OUTPUT}")


if __name__ == "__main__":
    build()
