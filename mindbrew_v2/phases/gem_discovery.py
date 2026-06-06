"""Literature-driven GEM discovery."""

from __future__ import annotations

from pydantic import BaseModel, Field

from mindbrew_v2.config.llm import structured_extract
from mindbrew_v2.models import Citation, GemDiscoveryResult, PathwayCandidate, ResearchBrief
from mindbrew_v2.settings import is_offline
from mindbrew_v2.tools.literature_retrieval import (
    RetrievedDocument,
    build_gem_retrieval_queries,
    format_context_block,
    merge_retrieval_docs,
    retrieve_queries,
)


class _GemDiscoveryExtract(BaseModel):
    organism: str = ""
    model_name: str = ""
    feedstock_used_in_validation: str | None = None
    biomass_context: str | None = None
    rationale: str = ""
    confidence: str = "partial"
    sbml_url: str | None = None
    sbml_source: str | None = None
    literature_refs: list[Citation] = Field(default_factory=list)


GEM_DISCOVERY_SYSTEM = """You identify genome-scale metabolic models (GSMM) from literature evidence.
Only cite models and SBML URLs explicitly mentioned in the retrieved documents.
Do not invent model names, DOIs, or download URLs."""


def discover_gem(
    brief: ResearchBrief,
    candidates: list[PathwayCandidate],
    literature_context: list[RetrievedDocument] | None = None,
) -> GemDiscoveryResult:
    from mindbrew_v2.progress import log
    from mindbrew_v2.settings import get_settings

    if is_offline():
        return _offline_discovery(brief)

    cached = list(literature_context or [])
    extra_queries = build_gem_retrieval_queries(brief, candidates)
    if extra_queries:
        log(f"GEM discovery: fetching {len(extra_queries)} additional literature queries…")
        cached = merge_retrieval_docs(cached, retrieve_queries(extra_queries))

    settings = get_settings()
    context = format_context_block(cached, settings.literature_context_max_chars)
    organism = ", ".join(brief.organism) if brief.organism else "unspecified host"
    feedstock = brief.feedstock.name or brief.feedstock.compound_class or "feedstock"
    target = brief.target.name or brief.target.compound_class or "target"

    prompt = f"""From the literature below, identify the best genome-scale metabolic model (GSMM)
for simulating {target} production from {feedstock} in {organism}.

Return:
- model_name (e.g. iYLI647, iML1515)
- organism
- feedstock_used_in_validation (if stated)
- biomass_context (e.g. N-limited, glucose minimal medium)
- rationale (1-2 sentences, cite evidence)
- confidence: strong | partial | inferred
- sbml_url: direct SBML/XML download URL ONLY if explicitly listed in sources (else null)
- sbml_source: e.g. BiGG, paper supplementary (else null)
- literature_refs: DOI/PMID citations from retrieved docs

{context or "No retrieved literature — infer cautiously from brief fields only."}

Brief summary: {brief.raw_brief[:400]}
"""
    extracted = structured_extract(prompt, _GemDiscoveryExtract, system=GEM_DISCOVERY_SYSTEM, role="parser")
    confidence = extracted.confidence if extracted.confidence in ("strong", "partial", "inferred") else "partial"
    validation_paper = extracted.literature_refs[0] if extracted.literature_refs else None
    log(f"GEM discovery: {extracted.model_name or 'unknown'} ({confidence})")
    return GemDiscoveryResult(
        organism=extracted.organism or organism,
        model_name=extracted.model_name,
        validation_paper=validation_paper,
        feedstock_used_in_validation=extracted.feedstock_used_in_validation,
        biomass_context=extracted.biomass_context,
        rationale=extracted.rationale,
        confidence=confidence,
        sbml_url=extracted.sbml_url,
        sbml_source=extracted.sbml_source,
        literature_refs=extracted.literature_refs,
    )


def _offline_discovery(brief: ResearchBrief) -> GemDiscoveryResult:
    text = (brief.raw_brief + " " + brief.target_function).lower()
    if any(k in text for k in ("wax", "lipid", "plant oil", "silicone", "dimethicone", "oleate")):
        return GemDiscoveryResult(
            organism="Yarrowia lipolytica",
            model_name="iYLI647",
            model_id="iyli647",
            validation_paper=Citation(doi="10.1186/s12918-018-0542-4", title="Mishra et al. 2018 iYLI647"),
            feedstock_used_in_validation="oleate",
            biomass_context="N-limited lipid accumulation",
            rationale="Oleaginous yeast GSMM for plant-oil / wax ester tickets (offline fixture).",
            confidence="strong",
            literature_refs=[Citation(doi="10.1186/s12918-018-0542-4")],
        )
    return GemDiscoveryResult(
        organism=brief.organism[0] if brief.organism else "",
        model_name="",
        rationale="No GSMM identified in offline mode for this brief.",
        confidence="inferred",
    )
