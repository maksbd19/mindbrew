"""Phase 4 — Outcome report generator."""

from __future__ import annotations

from pydantic import BaseModel

from mindbrew_v2.config.llm import structured_extract
from mindbrew_v2.models import (
    FBAValidationResult,
    LiteraturePathwayPlan,
    OutcomeReport,
    PathwayCandidate,
    ResearchBrief,
    ValidationMode,
)
from mindbrew_v2.tools.confidence import (
    FBA_VERDICT_METHODOLOGY,
    PATHWAY_CONFIDENCE_RUBRIC,
    collect_all_citations,
    format_citation_validation_summary,
    format_references_markdown,
)


class ReportExtract(BaseModel):
    what_worked: str
    what_didnt: str
    recommendations: str
    appendix: str = ""


def generate_report(
    brief: ResearchBrief,
    validation_mode: ValidationMode,
    candidates: list[PathwayCandidate],
    primary_pathway_id: str | None,
    fba_results: list[FBAValidationResult] | None = None,
    literature_plan: LiteraturePathwayPlan | None = None,
    revision_notes: str | None = None,
) -> OutcomeReport:
    from mindbrew_v2.progress import log

    log("Generating outcome report…")
    primary = next((c for c in candidates if c.id == primary_pathway_id), candidates[0] if candidates else None)

    fba_summary = ""
    if fba_results:
        ranked = sorted(fba_results, key=lambda r: r.rank or 999)
        lines = []
        for r in ranked:
            line = (
                f"- {r.pathway_id}: {r.verdict} (status={r.status}, "
                f"yield={r.yield_corrected_mol_per_mol_substrate}, "
                f"calibration={r.calibration_level})"
            )
            if r.verdict_rationale:
                line += f"\n  Rationale: {r.verdict_rationale}"
            if r.failure_reasons:
                line += f"\n  Flags: {'; '.join(r.failure_reasons)}"
            lines.append(line)
        fba_summary = "\n".join(lines)

    lit_summary = ""
    if literature_plan:
        genes = []
        for g in literature_plan.gene_suggestions:
            cite = ""
            if g.citation and (g.citation.doi or g.citation.pmid):
                cite = f" [{g.citation.doi or g.citation.pmid}]"
            genes.append(f"{g.gene} ({g.action}): {g.rationale}{cite}")
        lit_summary = (
            f"Literature plan: {literature_plan.pathway_name}\n"
            f"Gene suggestions:\n" + "\n".join(f"  - {g}" for g in genes)
        )

    pathway_summary = ""
    if primary:
        pathway_summary = (
            f"Primary pathway: {primary.name}\n"
            f"Confidence: {primary.confidence}\n"
            f"Rationale: {primary.confidence_rationale or 'not provided'}\n"
            f"Factors: {', '.join(primary.confidence_factors) or 'none'}\n"
            f"Citations: {len(primary.citations)}"
        )

    prompt = f"""Generate CRO-ready outcome report sections.
Brief: {brief.raw_brief[:500]}
Validation mode: {validation_mode.value}
{pathway_summary}
FBA results:
{fba_summary or 'N/A'}
Literature plan:
{lit_summary or 'N/A'}
"""
    if revision_notes:
        prompt += f"\nRevision: {revision_notes}"

    extracted = structured_extract(prompt, ReportExtract, role="parser")

    tier_label = "FBA-validated" if validation_mode == ValidationMode.FBA else "literature-only"
    ticket_summary = (
        f"**Ticket:** {brief.ticket_id}\n\n"
        f"**Target function:** {brief.target_function}\n\n"
        f"**Validation tier:** {tier_label}\n"
    )

    lit_citations = literature_plan.citations if literature_plan else None
    all_citations = collect_all_citations(candidates, lit_citations, fba_results)
    references = format_references_markdown(all_citations)
    validation_summary = format_citation_validation_summary(all_citations)

    markdown = f"""# Brewmind Pathway Blueprint

## Ticket Summary
{ticket_summary}

## What Worked
{extracted.what_worked}

## What Didn't Work
{extracted.what_didnt}

## Recommendations
{extracted.recommendations}

## Appendix
{extracted.appendix}

## Confidence Methodology

{PATHWAY_CONFIDENCE_RUBRIC}

{FBA_VERDICT_METHODOLOGY}

## Citation Validation
{validation_summary}

## References
{references}
"""

    log("Outcome report generated")
    return OutcomeReport(
        ticket_summary=ticket_summary,
        validation_mode=validation_mode,
        what_worked=extracted.what_worked,
        what_didnt=extracted.what_didnt,
        recommendations=extracted.recommendations,
        appendix=extracted.appendix,
        markdown=markdown,
    )
