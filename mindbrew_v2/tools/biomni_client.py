"""Biomni A1 adapter — literature pathway search."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from mindbrew_v2.config.llm import get_model_for_role, structured_extract
from mindbrew_v2.models import PathwayCandidate, ResearchBrief
from mindbrew_v2.settings import get_settings, is_offline


class PathwayCandidateList(BaseModel):
    candidates: list[PathwayCandidate] = Field(default_factory=list)


def build_biomni_prompt(brief: ResearchBrief, revision_notes: str | None = None) -> str:
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
    return prompt


def search_pathways(brief: ResearchBrief, revision_notes: str | None = None) -> list[dict[str, Any]]:
    from mindbrew_v2.progress import log

    prompt = build_biomni_prompt(brief, revision_notes)

    if is_offline():
        log("Offline mode: simulating pathway search via structured LLM parser")
        result = structured_extract(prompt, PathwayCandidateList, role="parser")
        return [c.model_dump() for c in result.candidates]

    log("Initializing Biomni A1 agent (literature search — typically 2–20 min)")
    raw = _call_biomni_a1(prompt)
    log(f"Biomni returned {len(raw):,} characters; extracting structured pathway candidates…")
    return _parse_biomni_response(raw, prompt)


def _call_biomni_a1(prompt: str) -> str:
    from mindbrew_v2.progress import log

    settings = get_settings()
    try:
        from biomni.agent import A1
        from biomni.config import default_config

        default_config.llm = get_model_for_role("biomni")
        default_config.source = "Custom"
        default_config.base_url = settings.nebius_base_url
        default_config.api_key = settings.nebius_api_key
        default_config.timeout_seconds = 1200

        log("Loading Biomni data lake and starting agent.go()…")
        agent = A1(
            path=settings.biomni_data_path,
            expected_data_lake_files=[],
        )
        log("Biomni agent running — searching literature and tools (no streaming; please wait)…")
        return str(agent.go(prompt))
    except ImportError:
        log("Biomni package not installed; falling back to LLM parser")
        return _mock_biomni_response(prompt)


def _mock_biomni_response(prompt: str) -> str:
    """Fallback when biomni package not installed."""
    result = structured_extract(prompt, PathwayCandidateList, role="parser")
    return str([c.model_dump() for c in result.candidates])


def _parse_biomni_response(raw: str, original_prompt: str) -> list[dict[str, Any]]:
    extract_prompt = f"""Extract structured pathway candidates from this Biomni response.

Original request:
{original_prompt}

Biomni response:
{raw[:12000]}
"""
    result = structured_extract(extract_prompt, PathwayCandidateList, role="parser")
    return [c.model_dump() for c in result.candidates]
