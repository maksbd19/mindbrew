"""Phase 1 — literature pathway search via retrieval-augmented LLM."""

from __future__ import annotations

from mindbrew_v2.models import PathwayCandidate, ResearchBrief
from mindbrew_v2.tools.citation_resolver import resolve_citations
from mindbrew_v2.tools.confidence import enrich_pathway_candidate
from mindbrew_v2.tools.literature_client import search_pathways
from mindbrew_v2.tools.literature_retrieval import RetrievedDocument, retrieve_literature_context


def run_literature_search(
    brief: ResearchBrief,
    revision_notes: str | None = None,
    cached_docs: list[RetrievedDocument] | None = None,
) -> tuple[list[PathwayCandidate], list[RetrievedDocument]]:
    from mindbrew_v2.tools.literature_client import PathwayCandidateList

    context_docs = cached_docs if cached_docs is not None else retrieve_literature_context(brief)
    raw = search_pathways(brief, revision_notes, context_docs=context_docs)
    parsed = PathwayCandidateList.model_validate({"candidates": raw})
    from mindbrew_v2.progress import log

    log(f"Enriching {len(parsed.candidates)} pathway candidate(s) with citations…")
    candidates = [_enrich_candidate(c) for c in parsed.candidates]
    return candidates, context_docs


def _enrich_candidate(candidate: PathwayCandidate) -> PathwayCandidate:
    resolved = resolve_citations(candidate.citations)
    updated = candidate.model_copy(update={"citations": resolved})
    return enrich_pathway_candidate(updated)
