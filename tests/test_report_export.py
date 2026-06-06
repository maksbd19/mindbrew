"""Tests for report export."""

from __future__ import annotations

from mindbrew_v2.export.report_export import (
    export_report_docx,
    export_report_markdown_preview,
    export_report_pdf,
    safe_filename,
)

SAMPLE_MARKDOWN = """# R&D Proposal to CRO

## Executive Summary

### Proposal at a Glance

| Item | Value |
| --- | --- |
| Target molecule | wax ester |
| Feedstock | oleic acid |

## 1. Project Summary
Produce wax esters from plant oil via fermentation for haircare applications.

## 5. Genetic Engineering Plan
Insert FAR and WS; knock out β-oxidation genes.

## 7. Validation Plan
Measure yield by HPLC/GC; frizz test as efficacy proxy.

## 10. References
1. Example citation (2024)

## Appendix

### Confidence Methodology
Pathway confidence rubric text.

### Citation Validation
All citations verified.
"""


def test_safe_filename():
    assert safe_filename("My Report Title!") == "My-Report-Title"
    assert safe_filename("   ") == "brewmind-report"


def test_export_report_pdf():
    content = export_report_pdf(SAMPLE_MARKDOWN)
    assert content.startswith(b"%PDF")
    assert len(content) > 500


def test_markdown_preview_organizes_sections_without_color_styling():
    html = export_report_markdown_preview(SAMPLE_MARKDOWN)
    assert "report-header" in html
    assert "section-executive" in html
    assert "section-proposal" in html
    assert "section-appendix" in html
    assert 'class="data-table"' in html
    assert 'width="100%"' in html
    assert "footerContent" in html
    assert "pdf:pagenumber" in html
    assert "R&amp;amp;D" not in html
    assert "R&amp;D Proposal to CRO" in html
    assert "#0f2942" not in html
    assert "#2563eb" not in html
    assert "background-color: #1e3a5f" not in html


def test_export_report_docx():
    content = export_report_docx(SAMPLE_MARKDOWN)
    assert content.startswith(b"PK")
    assert len(content) > 1000
