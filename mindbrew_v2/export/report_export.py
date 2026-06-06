"""Convert outcome report markdown to PDF and Word documents."""

from __future__ import annotations

import io
import re

import markdown
from docx import Document
from docx.shared import Inches, Pt
from xhtml2pdf import pisa

_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_SAFE_FILENAME_RE = re.compile(r"[^\w\s-]", re.UNICODE)
_WHITESPACE_RE = re.compile(r"\s+")


def safe_filename(title: str, fallback: str = "brewmind-report") -> str:
    cleaned = _SAFE_FILENAME_RE.sub("", title).strip()
    cleaned = _WHITESPACE_RE.sub("-", cleaned).strip("-")
    return cleaned[:80] or fallback


def _markdown_to_html(markdown_text: str) -> str:
    body = markdown.markdown(
        markdown_text,
        extensions=["extra", "sane_lists", "nl2br"],
    )
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<style>
@page {{
  size: letter;
  margin: 0.85in;
}}
body {{
  font-family: Helvetica, Arial, sans-serif;
  font-size: 11pt;
  line-height: 1.45;
  color: #111827;
}}
h1 {{
  font-size: 20pt;
  margin: 0 0 0.35in 0;
  color: #0f172a;
}}
h2 {{
  font-size: 13pt;
  margin: 0.28in 0 0.12in 0;
  color: #1e293b;
  border-bottom: 1px solid #e2e8f0;
  padding-bottom: 0.04in;
}}
p {{
  margin: 0 0 0.12in 0;
}}
ul, ol {{
  margin: 0 0 0.12in 0;
  padding-left: 0.22in;
}}
li {{
  margin-bottom: 0.05in;
}}
strong {{
  color: #0f172a;
}}
</style>
</head>
<body>
{body}
</body>
</html>"""


def export_report_pdf(markdown_text: str) -> bytes:
    html = _markdown_to_html(markdown_text)
    buffer = io.BytesIO()
    status = pisa.CreatePDF(html, dest=buffer, encoding="utf-8")
    if status.err:
        raise RuntimeError("Failed to generate PDF")
    return buffer.getvalue()


def _add_formatted_runs(paragraph, text: str) -> None:
    parts = _BOLD_RE.split(text)
    for index, part in enumerate(parts):
        if not part:
            continue
        run = paragraph.add_run(part)
        if index % 2 == 1:
            run.bold = True


def _configure_docx_styles(doc: Document) -> None:
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)

    for level, size in ((1, 22), (2, 14), (3, 12)):
        style = doc.styles[f"Heading {level}"]
        style.font.name = "Calibri"
        style.font.size = Pt(size)
        style.font.bold = True


def export_report_docx(markdown_text: str) -> bytes:
    doc = Document()
    _configure_docx_styles(doc)
    section = doc.sections[0]
    section.top_margin = Inches(0.85)
    section.bottom_margin = Inches(0.85)
    section.left_margin = Inches(0.9)
    section.right_margin = Inches(0.9)

    lines = markdown_text.splitlines()
    paragraph_buffer: list[str] = []
    list_buffer: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph_buffer
        if not paragraph_buffer:
            return
        text = " ".join(part.strip() for part in paragraph_buffer if part.strip())
        paragraph_buffer = []
        if not text:
            return
        paragraph = doc.add_paragraph()
        _add_formatted_runs(paragraph, text)

    def flush_list() -> None:
        nonlocal list_buffer
        if not list_buffer:
            return
        for item in list_buffer:
            paragraph = doc.add_paragraph(style="List Bullet")
            _add_formatted_runs(paragraph, item)
        list_buffer = []

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()

        if not stripped:
            flush_list()
            flush_paragraph()
            continue

        if stripped.startswith("# "):
            flush_list()
            flush_paragraph()
            doc.add_heading(stripped[2:].strip(), level=1)
            continue

        if stripped.startswith("## "):
            flush_list()
            flush_paragraph()
            doc.add_heading(stripped[3:].strip(), level=2)
            continue

        if stripped.startswith("### "):
            flush_list()
            flush_paragraph()
            doc.add_heading(stripped[4:].strip(), level=3)
            continue

        if stripped.startswith("- "):
            flush_paragraph()
            list_buffer.append(stripped[2:].strip())
            continue

        if line.startswith("  ") and list_buffer:
            list_buffer[-1] = f"{list_buffer[-1]} {stripped}"
            continue

        flush_list()
        paragraph_buffer.append(stripped)

    flush_list()
    flush_paragraph()

    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


def export_report_markdown_preview(markdown_text: str) -> str:
    """Return HTML preview used by tests and optional future endpoints."""
    return _markdown_to_html(markdown_text)
