"""Phase 4 — Outcome report generator."""

from __future__ import annotations

from pydantic import BaseModel

from mindbrew_v2.config.llm import structured_extract
from mindbrew_v2.models import (
    FBAValidationResult,
    GemDiscoveryResult,
    LiteraturePathwayPlan,
    OutcomeReport,
    PathwayCandidate,
    ResearchBrief,
    ScorePathwayPayload,
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
    project_summary: str
    target_molecule_specification: str
    feedstock_starting_material: str
    production_strategy: str
    genetic_engineering_plan: str
    predicted_performance: str
    validation_plan: str
    risk_bottleneck_assessment: str
    regulatory_positioning: str


def _compound_inline(compound) -> str:
    parts = [compound.name, compound.compound_class]
    parts = [p for p in parts if p]
    label = " / ".join(parts) if parts else "—"
    if compound.kegg_id:
        label += f" ({compound.kegg_id})"
    if compound.notes:
        label += f" — {compound.notes}"
    return label


def _build_target_scaffold(brief: ResearchBrief) -> str:
    lines = [
        f"Target: {_compound_inline(brief.target)}",
        f"Target function: {brief.target_function or '—'}",
    ]
    if brief.constraints:
        lines.append("Constraints: " + "; ".join(brief.constraints))
    return "\n".join(lines)


def _build_feedstock_scaffold(brief: ResearchBrief) -> str:
    return f"Feedstock: {_compound_inline(brief.feedstock)}"


def _pathway_name(candidates: list[PathwayCandidate], pathway_id: str) -> str:
    cand = next((c for c in candidates if c.id == pathway_id), None)
    if cand:
        return f"{cand.name} ({pathway_id})"
    return pathway_id


def _format_stoichiometry(stoich: dict[str, float]) -> str:
    parts: list[str] = []
    for met, coeff in stoich.items():
        sign = "−" if coeff < 0 else "+"
        abs_c = abs(coeff)
        coef_str = "" if abs_c == 1 else f"{abs_c:g} "
        parts.append(f"{sign}{coef_str}{met}")
    return " ".join(parts)


def _format_pathway_block(
    candidate: PathwayCandidate,
    primary_pathway_id: str | None,
    *,
    markdown: bool = False,
) -> str:
    primary_tag = " [PRIMARY]" if candidate.id == primary_pathway_id else ""
    heading = f"{candidate.name} ({candidate.id}){primary_tag}"
    if markdown:
        lines = [f"#### {heading}", ""]
    else:
        lines = [f"--- {heading} ---"]

    if candidate.description:
        lines.append(f"Description: {candidate.description}")
    lines.append(f"Confidence: {candidate.confidence}")
    if candidate.confidence_rationale:
        lines.append(f"Rationale: {candidate.confidence_rationale}")
    if candidate.confidence_factors:
        lines.append(f"Factors: {', '.join(candidate.confidence_factors)}")
    if candidate.reported_titer:
        lines.append(f"Literature reported titer: {candidate.reported_titer}")
    if candidate.enzymes:
        lines.append(f"Enzymes: {', '.join(candidate.enzymes)}")
    if candidate.reaction_steps:
        lines.append("Metabolic steps:")
        for step in candidate.reaction_steps:
            enzymes = step.enzyme_name or step.enzyme_ec or ", ".join(step.gene_names) or "—"
            het = " (heterologous)" if step.heterologous else ""
            lines.append(f"  {step.step_number}. {step.description} — {enzymes}{het}")
            if step.gene_names:
                lines.append(f"     Genes: {', '.join(step.gene_names)}")
    if candidate.citations:
        lines.append(f"Citations: {len(candidate.citations)} source(s)")
    return "\n".join(lines)


def _build_pathways_scaffold(
    candidates: list[PathwayCandidate],
    primary_pathway_id: str | None,
) -> str:
    if not candidates:
        return "No pathway candidates available."
    blocks = [_format_pathway_block(c, primary_pathway_id) for c in candidates]
    return "\n\n".join(blocks)


def _build_fba_plan_scaffold(
    score_payloads: list[ScorePathwayPayload] | None,
    candidates: list[PathwayCandidate],
    formalize_skipped: list[str] | None = None,
) -> str:
    lines: list[str] = []
    if score_payloads:
        for payload in score_payloads:
            lines.append(f"--- {_pathway_name(candidates, payload.pathway_id)} ---")
            lines.append(f"Model: {payload.model_ref}")
            lines.append(f"Scenario: {payload.scenario}")
            if payload.carbon_source_rxn:
                lines.append(f"Carbon source reaction: {payload.carbon_source_rxn}")
            if payload.product_metabolite:
                lines.append(f"Product metabolite: {payload.product_metabolite}")
            if payload.knockouts:
                lines.append("Knockouts: " + ", ".join(payload.knockouts))
            if payload.candidate_reactions:
                lines.append("Candidate reactions:")
                for rxn in payload.candidate_reactions:
                    stoich = _format_stoichiometry(rxn.stoichiometry) if rxn.stoichiometry else "—"
                    genes = ", ".join(rxn.gene_associations) if rxn.gene_associations else "—"
                    lines.append(f"  - {rxn.id}: {rxn.name or rxn.id} | {stoich} | genes: {genes}")
            lines.append("")
    if formalize_skipped:
        lines.append("Skipped during formalization:")
        lines.extend(f"  - {item}" for item in formalize_skipped)
    return "\n".join(lines).strip() if lines else "No FBA plan data available."


def _build_fba_results_scaffold(
    fba_results: list[FBAValidationResult] | None,
    candidates: list[PathwayCandidate],
) -> str:
    if not fba_results:
        return "No FBA validation results available."
    lines: list[str] = []
    ranked = sorted(fba_results, key=lambda r: r.rank or 999)
    for r in ranked:
        rank_label = f"rank {r.rank}" if r.rank is not None else "unranked"
        lines.append(f"--- {_pathway_name(candidates, r.pathway_id)} ({rank_label}) ---")
        lines.append(
            f"Verdict: {r.verdict} | Status: {r.status} | Calibration: {r.calibration_level}"
        )
        if r.yield_corrected_mol_per_mol_substrate is not None:
            lines.append(f"Yield (corrected): {r.yield_corrected_mol_per_mol_substrate} mol/mol substrate")
        if r.yield_mol_per_mol_substrate is not None:
            lines.append(f"Yield (raw): {r.yield_mol_per_mol_substrate} mol/mol substrate")
        if r.predicted_product_flux is not None:
            lines.append(f"Product flux: {r.predicted_product_flux}")
        if r.growth_rate is not None:
            lines.append(f"Growth rate: {r.growth_rate}")
        if r.verdict_rationale:
            lines.append(f"Verdict rationale: {r.verdict_rationale}")
        if r.calibration_rationale:
            lines.append(f"Calibration rationale: {r.calibration_rationale}")
        if r.calibration_warnings:
            lines.append("Calibration warnings: " + "; ".join(r.calibration_warnings))
        if r.failure_reasons:
            lines.append("Failure reasons: " + "; ".join(r.failure_reasons))
        if r.bottlenecks:
            lines.append("Bottlenecks:")
            for b in r.bottlenecks:
                bound = " (at bound)" if b.at_bound else ""
                span = f", FVA span={b.flux_span}" if b.flux_span is not None else ""
                lines.append(f"  - {b.reaction}: flux={b.flux}{span}{bound} — {b.explanation}")
        if r.calculation_steps:
            lines.append("Calculation steps:")
            for step in r.calculation_steps:
                lines.append(f"  {step.step}. {step.title}: {step.detail}")
        lines.append("")
    return "\n".join(lines).strip()


def _build_pathway_analysis_markdown(
    candidates: list[PathwayCandidate],
    primary_pathway_id: str | None,
) -> str:
    if not candidates:
        return "_No pathway candidates available._"
    blocks = [_format_pathway_block(c, primary_pathway_id, markdown=True) for c in candidates]
    return "\n\n".join(blocks)


def _build_fba_data_markdown(
    score_payloads: list[ScorePathwayPayload] | None,
    fba_results: list[FBAValidationResult] | None,
    candidates: list[PathwayCandidate],
    formalize_skipped: list[str] | None = None,
) -> str:
    sections: list[str] = []
    if score_payloads:
        plan_lines = ["#### FBA Plan", ""]
        for payload in score_payloads:
            plan_lines.append(f"##### {_pathway_name(candidates, payload.pathway_id)}")
            plan_lines.append(f"- **Model:** {payload.model_ref}")
            plan_lines.append(f"- **Scenario:** {payload.scenario}")
            if payload.carbon_source_rxn:
                plan_lines.append(f"- **Carbon source:** {payload.carbon_source_rxn}")
            if payload.product_metabolite:
                plan_lines.append(f"- **Product metabolite:** {payload.product_metabolite}")
            if payload.knockouts:
                plan_lines.append(f"- **Knockouts:** {', '.join(payload.knockouts)}")
            if payload.candidate_reactions:
                plan_lines.append("- **Candidate reactions:**")
                for rxn in payload.candidate_reactions:
                    stoich = _format_stoichiometry(rxn.stoichiometry) if rxn.stoichiometry else "—"
                    genes = ", ".join(rxn.gene_associations) if rxn.gene_associations else "—"
                    plan_lines.append(f"  - `{rxn.id}`: {rxn.name or rxn.id} — {stoich} (genes: {genes})")
            plan_lines.append("")
        sections.append("\n".join(plan_lines).strip())
    if formalize_skipped:
        skip_lines = ["#### Skipped Pathways", ""]
        skip_lines.extend(f"- {item}" for item in formalize_skipped)
        sections.append("\n".join(skip_lines))
    if fba_results:
        result_lines = ["#### FBA Results", ""]
        ranked = sorted(fba_results, key=lambda r: r.rank or 999)
        for r in ranked:
            rank_label = f" (rank {r.rank})" if r.rank is not None else ""
            result_lines.append(f"##### {_pathway_name(candidates, r.pathway_id)}{rank_label} — {r.verdict}")
            result_lines.append(f"- **Status:** {r.status}")
            result_lines.append(f"- **Calibration:** {r.calibration_level}")
            if r.yield_corrected_mol_per_mol_substrate is not None:
                result_lines.append(
                    f"- **Yield (corrected):** {r.yield_corrected_mol_per_mol_substrate} mol/mol substrate"
                )
            if r.predicted_product_flux is not None:
                result_lines.append(f"- **Product flux:** {r.predicted_product_flux}")
            if r.growth_rate is not None:
                result_lines.append(f"- **Growth rate:** {r.growth_rate}")
            if r.verdict_rationale:
                result_lines.append(f"- **Verdict rationale:** {r.verdict_rationale}")
            if r.calibration_warnings:
                result_lines.extend(f"- **Warning:** {w}" for w in r.calibration_warnings)
            if r.failure_reasons:
                result_lines.extend(f"- **Failure:** {f}" for f in r.failure_reasons)
            if r.bottlenecks:
                result_lines.append("- **Bottlenecks:**")
                for b in r.bottlenecks:
                    bound = " (at bound)" if b.at_bound else ""
                    result_lines.append(f"  - `{b.reaction}`: flux={b.flux}{bound} — {b.explanation}")
            if r.calculation_steps:
                result_lines.append("- **Calculation steps:**")
                for step in r.calculation_steps:
                    result_lines.append(f"  {step.step}. **{step.title}:** {step.detail}")
            result_lines.append("")
        sections.append("\n".join(result_lines).strip())
    if not sections:
        return "_No FBA data available._"
    return "\n\n".join(sections)


def _build_production_scaffold(
    primary: PathwayCandidate | None,
    mode: ValidationMode,
    brief: ResearchBrief,
    gem_profile: dict | None = None,
) -> str:
    from mindbrew_v2.paths import display_path

    method = "FBA-validated whole-cell fermentation" if mode == ValidationMode.FBA else "literature-backed pathway"
    lines = [
        f"Method: {method}",
        f"Chassis organism: {', '.join(brief.organism) if brief.organism else '—'}",
    ]
    if gem_profile:
        gem_label = gem_profile.get("gem_id") or display_path(gem_profile.get("model_ref"))
        if gem_label:
            lines.append(f"GEM model: {gem_label}")
    if primary:
        lines.append(f"Primary pathway: {primary.name}")
        if primary.description:
            lines.append(f"Description: {primary.description}")
        if primary.reaction_steps:
            lines.append("Metabolic steps:")
            for step in primary.reaction_steps:
                enzymes = step.enzyme_name or step.enzyme_ec or ", ".join(step.gene_names) or "—"
                het = " (heterologous)" if step.heterologous else ""
                lines.append(f"  {step.step_number}. {step.description} — {enzymes}{het}")
    return "\n".join(lines)


def _build_genetic_scaffold(
    literature_plan: LiteraturePathwayPlan | None,
    candidates: list[PathwayCandidate],
    score_payloads: list[ScorePathwayPayload] | None,
    primary_pathway_id: str | None,
) -> str:
    lines: list[str] = []

    if literature_plan and literature_plan.gene_suggestions:
        by_action: dict[str, list[str]] = {}
        for g in literature_plan.gene_suggestions:
            label = f"{g.gene}: {g.rationale}"
            if g.citation and (g.citation.doi or g.citation.pmid):
                label += f" [{g.citation.doi or g.citation.pmid}]"
            by_action.setdefault(g.action, []).append(label)
        for action, items in by_action.items():
            lines.append(f"{action}:")
            lines.extend(f"  - {item}" for item in items)

    if score_payloads:
        for payload in score_payloads:
            if payload.knockouts:
                lines.append(f"FBA knockouts ({payload.pathway_id}):")
                lines.extend(f"  - {ko}" for ko in payload.knockouts)

    for candidate in candidates:
        if not candidate.reaction_steps:
            continue
        tag = " [PRIMARY]" if candidate.id == primary_pathway_id else ""
        lines.append(f"Pathway genes ({candidate.id}){tag}:")
        for step in candidate.reaction_steps:
            for gene in step.gene_names:
                gene_tag = "heterologous" if step.heterologous else "native"
                lines.append(f"  - {gene} ({gene_tag}, step {step.step_number})")

    return "\n".join(lines) if lines else "No genetic engineering data available."


def _build_performance_scaffold(
    fba_results: list[FBAValidationResult] | None,
    candidates: list[PathwayCandidate],
    primary_pathway_id: str | None,
) -> str:
    lines: list[str] = []
    for candidate in candidates:
        if candidate.reported_titer:
            tag = " [PRIMARY]" if candidate.id == primary_pathway_id else ""
            lines.append(f"Literature titer ({candidate.id}){tag}: {candidate.reported_titer}")
    if fba_results:
        lines.append("")
        lines.append(_build_fba_results_scaffold(fba_results, candidates))
    return "\n".join(lines).strip() if lines else "No performance predictions available."


def _build_risk_scaffold(
    fba_results: list[FBAValidationResult] | None,
    literature_plan: LiteraturePathwayPlan | None,
) -> str:
    lines: list[str] = []
    if literature_plan and literature_plan.known_risks:
        lines.append("Known risks:")
        lines.extend(f"  - {r}" for r in literature_plan.known_risks)
    if fba_results:
        for r in fba_results:
            if r.bottlenecks:
                lines.append(f"Bottlenecks ({r.pathway_id}):")
                for b in r.bottlenecks:
                    bound = " (at bound)" if b.at_bound else ""
                    lines.append(f"  - {b.reaction}: flux={b.flux}{bound} — {b.explanation}")
            if r.failure_reasons:
                lines.append(f"Failure flags ({r.pathway_id}): {'; '.join(r.failure_reasons)}")
    return "\n".join(lines) if lines else "No risk data available."


def _build_validation_scaffold(
    literature_plan: LiteraturePathwayPlan | None,
    mode: ValidationMode,
) -> str:
    lines = [f"Validation mode: {mode.value}"]
    if literature_plan:
        if literature_plan.next_steps:
            lines.append("Suggested next steps:")
            lines.extend(f"  - {s}" for s in literature_plan.next_steps)
        if literature_plan.gaps:
            lines.append("Known gaps:")
            lines.extend(f"  - {g}" for g in literature_plan.gaps)
    return "\n".join(lines)


def _report_title(session_title: str | None) -> str:
    if session_title and session_title.strip():
        return session_title.strip()
    return "R&D Proposal to CRO"


def _build_report_prompt(
    brief: ResearchBrief,
    validation_mode: ValidationMode,
    primary: PathwayCandidate | None,
    candidates: list[PathwayCandidate],
    primary_pathway_id: str | None,
    target_scaffold: str,
    feedstock_scaffold: str,
    production_scaffold: str,
    genetic_scaffold: str,
    performance_scaffold: str,
    risk_scaffold: str,
    validation_scaffold: str,
    pathways_scaffold: str,
    fba_plan_scaffold: str,
    gem_summary: str,
    revision_notes: str | None,
) -> str:
    pathway_lines: list[str] = []
    for c in candidates:
        tag = " [PRIMARY]" if c.id == primary_pathway_id else ""
        pathway_lines.append(
            f"- {c.name} ({c.id}){tag}: confidence={c.confidence}, "
            f"factors={', '.join(c.confidence_factors) or 'none'}"
        )
    pathway_summary = "All pathway candidates:\n" + "\n".join(pathway_lines) if pathway_lines else ""
    if primary:
        pathway_summary += (
            f"\n\nPrimary pathway for this proposal: {primary.name}\n"
            f"Confidence rationale: {primary.confidence_rationale or 'not provided'}"
        )

    prompt = f"""Generate an R&D Proposal to CRO using the industry-standard structure below.
Write CRO-ready prose for each section. Use the scaffold data provided — do not invent yields or gene names not supported by the scaffolds.
The primary pathway drives the proposal narrative; reference other candidates and FBA comparisons where the scaffolds provide data.

User brief:
{brief.raw_brief[:800]}

Validation mode: {validation_mode.value}
{pathway_summary}

Section scaffolds (ground truth from pipeline):

--- Target molecule ---
{target_scaffold}

--- Feedstock ---
{feedstock_scaffold}

--- All pathway candidates ---
{pathways_scaffold}

--- Production strategy (primary pathway) ---
{production_scaffold}

--- Genetic engineering (all pathways) ---
{genetic_scaffold}

--- Predicted performance (all pathways + FBA) ---
{performance_scaffold}

--- FBA plan (all pathways) ---
{fba_plan_scaffold}

--- Risk & bottlenecks ---
{risk_scaffold}

--- Validation ---
{validation_scaffold}

--- GEM discovery ---
{gem_summary or 'N/A'}

Section guidance:
1. Project Summary — one paragraph: molecule, feedstock, application, business context.
2. Target Molecule Specification — compound name/structure, molecular weight, INCI name, functional property.
3. Feedstock & Starting Material — source, purity/supply, rationale for choice.
4. Production Strategy — method (fermentation vs biocatalysis), chassis organism, metabolic pathway steps.
5. Genetic Engineering Plan — genes to insert, knock out, down-regulate; rationale for flux redirection.
6. Predicted Performance — expected yield range, literature benchmarks, fermentation conditions.
7. Validation Plan — what to measure (yield, purity, structure), efficacy proxy tests, success criteria.
8. Risk & Bottleneck Assessment — competing pathways, toxic intermediates, scale-up considerations.
9. Regulatory Positioning — GMO status, COSMOS/ECOCERT eligibility, EU SCCS and target market considerations.
"""
    if brief.constraints:
        prompt += f"\nRegulatory/business constraints from brief: {'; '.join(brief.constraints)}"
    if revision_notes:
        prompt += f"\nRevision notes: {revision_notes}"
    return prompt


def generate_report(
    brief: ResearchBrief,
    validation_mode: ValidationMode,
    candidates: list[PathwayCandidate],
    primary_pathway_id: str | None,
    fba_results: list[FBAValidationResult] | None = None,
    literature_plan: LiteraturePathwayPlan | None = None,
    revision_notes: str | None = None,
    gem_discovery=None,
    gem_profile: dict | None = None,
    gem_selection_reason: str | None = None,
    biomass_validation_warning: str | None = None,
    session_title: str | None = None,
    score_payloads: list[ScorePathwayPayload] | None = None,
    formalize_skipped: list[str] | None = None,
) -> OutcomeReport:
    from mindbrew_v2.progress import log

    log("Generating outcome report…")
    primary = next((c for c in candidates if c.id == primary_pathway_id), candidates[0] if candidates else None)

    disc: GemDiscoveryResult | None = None
    if gem_discovery is not None:
        disc = (
            gem_discovery
            if isinstance(gem_discovery, GemDiscoveryResult)
            else GemDiscoveryResult.model_validate(gem_discovery)
        )

    gem_summary = ""
    if disc is not None:
        gem_summary = (
            f"Discovered GSMM: {disc.model_name or 'unknown'} ({disc.confidence})\n"
            f"Rationale: {disc.rationale}\n"
            f"Local SBML available: {disc.sbml_available_locally}"
        )
        if biomass_validation_warning:
            gem_summary += f"\nBiomass validation warning: {biomass_validation_warning}"
    if gem_selection_reason:
        gem_summary += f"\nGEM selection: {gem_selection_reason}"

    target_scaffold = _build_target_scaffold(brief)
    feedstock_scaffold = _build_feedstock_scaffold(brief)
    pathways_scaffold = _build_pathways_scaffold(candidates, primary_pathway_id)
    fba_plan_scaffold = _build_fba_plan_scaffold(score_payloads, candidates, formalize_skipped)
    production_scaffold = _build_production_scaffold(primary, validation_mode, brief, gem_profile)
    genetic_scaffold = _build_genetic_scaffold(
        literature_plan, candidates, score_payloads, primary_pathway_id
    )
    performance_scaffold = _build_performance_scaffold(fba_results, candidates, primary_pathway_id)
    risk_scaffold = _build_risk_scaffold(fba_results, literature_plan)
    validation_scaffold = _build_validation_scaffold(literature_plan, validation_mode)
    pathway_analysis_md = _build_pathway_analysis_markdown(candidates, primary_pathway_id)
    fba_data_md = _build_fba_data_markdown(score_payloads, fba_results, candidates, formalize_skipped)

    prompt = _build_report_prompt(
        brief,
        validation_mode,
        primary,
        candidates,
        primary_pathway_id,
        target_scaffold,
        feedstock_scaffold,
        production_scaffold,
        genetic_scaffold,
        performance_scaffold,
        risk_scaffold,
        validation_scaffold,
        pathways_scaffold,
        fba_plan_scaffold,
        gem_summary,
        revision_notes,
    )

    extracted = structured_extract(prompt, ReportExtract, role="parser")

    lit_citations = literature_plan.citations if literature_plan else None
    all_citations = collect_all_citations(candidates, lit_citations, fba_results)
    references = format_references_markdown(all_citations)
    validation_summary = format_citation_validation_summary(all_citations)

    title = _report_title(session_title)

    markdown = f"""# {title}

## 1. Project Summary
{extracted.project_summary}

## 2. Target Molecule Specification
{extracted.target_molecule_specification}

## 3. Feedstock & Starting Material
{extracted.feedstock_starting_material}

## 4. Production Strategy
{extracted.production_strategy}

## 5. Genetic Engineering Plan
{extracted.genetic_engineering_plan}

## 6. Predicted Performance
{extracted.predicted_performance}

## 7. Validation Plan
{extracted.validation_plan}

## 8. Risk & Bottleneck Assessment
{extracted.risk_bottleneck_assessment}

## 9. Regulatory Positioning
{extracted.regulatory_positioning}

## 10. References
{references}

## Appendix

### Pathway Analysis

{pathway_analysis_md}

### FBA Validation

{fba_data_md}

### Confidence Methodology

{PATHWAY_CONFIDENCE_RUBRIC}

{FBA_VERDICT_METHODOLOGY}

### Citation Validation
{validation_summary}
"""

    log("Outcome report generated")
    return OutcomeReport(
        validation_mode=validation_mode,
        project_summary=extracted.project_summary,
        target_molecule_specification=extracted.target_molecule_specification,
        feedstock_starting_material=extracted.feedstock_starting_material,
        production_strategy=extracted.production_strategy,
        genetic_engineering_plan=extracted.genetic_engineering_plan,
        predicted_performance=extracted.predicted_performance,
        validation_plan=extracted.validation_plan,
        risk_bottleneck_assessment=extracted.risk_bottleneck_assessment,
        regulatory_positioning=extracted.regulatory_positioning,
        markdown=markdown,
    )
