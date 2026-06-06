"""Phase 1 — Biomni literature pathway search."""

from __future__ import annotations

from mindbrew_v2.models import PathwayCandidate, ResearchBrief
from mindbrew_v2.tools.biomni_client import search_pathways
from mindbrew_v2.tools.citation_resolver import resolve_citations
from mindbrew_v2.tools.confidence import enrich_pathway_candidate


def run_biomni_search(
    brief: ResearchBrief,
    revision_notes: str | None = None,
) -> list[PathwayCandidate]:
    from mindbrew_v2.tools.biomni_client import PathwayCandidateList

    raw = search_pathways(brief, revision_notes)
    parsed = PathwayCandidateList.model_validate({"candidates": raw})
    return [_enrich_candidate(c) for c in parsed.candidates]


def _enrich_candidate(candidate: PathwayCandidate) -> PathwayCandidate:
    resolved = resolve_citations(candidate.citations)
    updated = candidate.model_copy(update={"citations": resolved})
    return enrich_pathway_candidate(updated)
