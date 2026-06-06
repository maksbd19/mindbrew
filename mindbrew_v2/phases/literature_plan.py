"""Literature pathway plan when no GEM matches."""

from __future__ import annotations

from pydantic import BaseModel, Field

from mindbrew_v2.config.llm import structured_extract
from mindbrew_v2.models import (
    GeneSuggestion,
    LiteraturePathwayPlan,
    PathwayCandidate,
    ResearchBrief,
)
from mindbrew_v2.tools.citation_resolver import resolve_citation, resolve_citations


class LiteraturePlanExtract(BaseModel):
    gene_suggestions: list[GeneSuggestion] = Field(default_factory=list)
    known_risks: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)


def build_literature_plan(
    brief: ResearchBrief,
    candidate: PathwayCandidate,
    revision_notes: str | None = None,
) -> LiteraturePathwayPlan:
    from mindbrew_v2.progress import log

    log(f"Building literature plan for pathway: {candidate.name}")
    prompt = f"""Build a literature-backed pathway plan for:
Pathway: {candidate.name}
Description: {candidate.description}
Organism context: {brief.organism}
Target: {brief.target_function}
Enzymes: {candidate.enzymes}
Citations: {[c.model_dump() for c in candidate.citations]}

For each gene_suggestion you MUST include a citation with DOI or PMID supporting the modification.
"""
    if revision_notes:
        prompt += f"\nRevision notes: {revision_notes}"

    extracted = structured_extract(
        prompt,
        LiteraturePlanExtract,
        system="Extract gene modification suggestions from literature precedent.",
        role="parser",
    )

    hosts = brief.organism or candidate.reaction_steps and ["See literature for host"] or []
    if not hosts:
        hosts = ["Host to be validated — no GEM registered"]

    gene_suggestions = [
        GeneSuggestion(
            gene=g.gene,
            action=g.action,
            rationale=g.rationale,
            citation=resolve_citation(g.citation) if g.citation else None,
        )
        for g in extracted.gene_suggestions
    ]

    plan_citations = resolve_citations(candidate.citations)
    for g in gene_suggestions:
        if g.citation:
            plan_citations.append(g.citation)

    log(f"Literature plan ready: {len(gene_suggestions)} gene suggestion(s)")
    return LiteraturePathwayPlan(
        pathway_id=candidate.id,
        pathway_name=candidate.name,
        reaction_map=candidate.reaction_steps,
        suggested_hosts=list(brief.organism) if brief.organism else ["Literature-suggested host TBD"],
        gene_suggestions=gene_suggestions,
        known_risks=extracted.known_risks,
        gaps=extracted.gaps,
        next_steps=extracted.next_steps,
        citations=plan_citations,
    )
