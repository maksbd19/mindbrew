"""Tests for report export."""

from __future__ import annotations

from mindbrew_v2.export.report_export import export_report_docx, export_report_pdf, safe_filename

SAMPLE_MARKDOWN = """# R&D Proposal to CRO

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


def test_export_report_docx():
    content = export_report_docx(SAMPLE_MARKDOWN)
    assert content.startswith(b"PK")
    assert len(content) > 1000
