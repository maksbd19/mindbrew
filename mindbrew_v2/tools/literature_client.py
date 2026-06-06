"""Literature pathway search via retrieval-augmented LLM extraction."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from mindbrew_v2.config.llm import structured_extract
from mindbrew_v2.models import PathwayCandidate, ResearchBrief
from mindbrew_v2.settings import get_settings, is_offline
from mindbrew_v2.tools.literature_retrieval import (
    RetrievedDocument,
    format_context_block,
    retrieve_literature_context,
    retrieval_source_tags,
)


class PathwayCandidateList(BaseModel):
    candidates: list[PathwayCandidate] = Field(default_factory=list)


def build_literature_prompt(
    brief: ResearchBrief,
    revision_notes: str | None = None,
    context_docs: list[RetrievedDocument] | None = None,
) -> str:
    feedstock = brief.feedstock.name or brief.feedstock.compound_class or "feedstock"
    target = brief.target.name or brief.target.compound_class or "target product"
    organism = ", ".join(brief.organism) if brief.organism else "suitable host organism"
    constraints = "; ".join(brief.constraints) if brief.constraints else "none"

    prompt = f"""Identify 3-7 metabolic pathways to convert {feedstock} into {target} in {organism}.
Target function: {brief.target_function}
For each pathway return: reaction_steps, enzymes (EC + gene names),
heterologous vs native, literature citations (DOI/PMID), reported titers, confidence,
and confidence_rationale (1-2 sentences explaining the confidence label).

Confidence rubric:
- strong: direct literature precedent with reported titer in target or similar host
- partial: pathway known but host/titer not demonstrated for this case
- inferred: assembled from KEGG/reaction logic without direct product evidence

Constraints: {constraints}. Do NOT predict yields — pathway identification only."""
    if revision_notes:
        prompt += f"\n\nReviewer revision notes:\n{revision_notes}"

    if context_docs:
        settings = get_settings()
        context = format_context_block(context_docs, settings.literature_context_max_chars)
        if context:
            prompt += f"\n\n{context}"

    return prompt


def search_pathways(brief: ResearchBrief, revision_notes: str | None = None) -> list[dict[str, Any]]:
    from mindbrew_v2.progress import log

    context_docs = retrieve_literature_context(brief)
    prompt = build_literature_prompt(brief, revision_notes, context_docs)

    if is_offline():
        log("Offline mode: simulating pathway search via structured LLM parser")
    elif context_docs:
        log(f"Running RAG literature search ({len(context_docs)} retrieved documents)…")
    else:
        log("Running literature pathway search via LLM…")

    log("Extracting pathway candidates via structured LLM…")
    result = structured_extract(prompt, PathwayCandidateList, role="parser")
    provenance = retrieval_source_tags(context_docs)
    candidates = [c.model_dump() for c in result.candidates]
    log(f"Extracted {len(candidates)} pathway candidate(s)")
    if provenance:
        for candidate in candidates:
            existing = candidate.get("biomni_provenance") or []
            candidate["biomni_provenance"] = list(dict.fromkeys([*existing, *provenance]))
    return candidates
