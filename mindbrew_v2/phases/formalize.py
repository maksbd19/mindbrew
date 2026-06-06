"""Formalization layer — PathwayCandidate → FBA payloads."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from mindbrew_v2.config.gem import select_gem
from mindbrew_v2.paths import display_path
from mindbrew_v2.models import (
    GemDiscoveryResult,
    GemProfile,
    PathwayCandidate,
    ResearchBrief,
    ScorePathwayPayload,
    ValidationMode,
)
from mindbrew_v2.phases.fba_metabolite_resolver import infer_fba_metabolite_mapping, search_terms_from_brief
from mindbrew_v2.phases.fba_payloads import build_payload_from_find_ids, summarize_find_ids
from mindbrew_v2.phases.gem_discovery import discover_gem
from mindbrew_v2.tools.fba_client import run_biomass_validation, run_find_ids
from mindbrew_v2.tools.literature_retrieval import RetrievedDocument


@dataclass
class FormalizeResult:
    gem: GemProfile | None = None
    payloads: list[ScorePathwayPayload] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    discovery: GemDiscoveryResult | None = None
    find_ids_summary: dict | None = None
    biomass_validation: dict | None = None
    biomass_validation_warning: str | None = None
    validation_mode: ValidationMode = ValidationMode.LITERATURE_PATHWAY


def formalize_pathways(
    brief: ResearchBrief,
    candidates: list[PathwayCandidate],
    *,
    literature_context: list[RetrievedDocument] | None = None,
    gem_override: str | None = None,
    discovery: GemDiscoveryResult | None = None,
) -> FormalizeResult:
    from mindbrew_v2.progress import log

    log(f"Formalizing {len(candidates)} pathway(s) for FBA…")
    resolved_discovery = discovery or discover_gem(brief, candidates, literature_context)
    selection = select_gem(brief, resolved_discovery, override_gem_id=gem_override)

    if selection.gem is None:
        return FormalizeResult(
            skipped=["No GEM available — resolve SBML cache or select literature branch at pathways"],
            discovery=selection.discovery or resolved_discovery,
            validation_mode=ValidationMode.FBA,
        )

    gem = selection.gem
    log(f"Selected GEM {gem.gem_id} ({gem.model_name}) — {display_path(gem.model_cache_path)}")

    find_ids = run_find_ids(gem.model_ref, extra_terms=search_terms_from_brief(brief))
    if find_ids.get("status") != "ok":
        message = find_ids.get("message", "find_ids failed")
        return FormalizeResult(
            gem=gem,
            skipped=[f"find_ids preflight failed: {message}"],
            discovery=selection.discovery,
            find_ids_summary=summarize_find_ids(find_ids),
            validation_mode=ValidationMode.FBA,
        )

    biomass_validation = run_biomass_validation(gem)
    biomass_warning = None
    if biomass_validation.get("status") != "optimal":
        biomass_warning = (
            f"Biomass validation non-optimal (status={biomass_validation.get('status')}) — "
            "product flux ranking is exploratory until medium is calibrated."
        )
        log(biomass_warning, level="warning")

    payloads: list[ScorePathwayPayload] = []
    skipped: list[str] = []
    for cand in candidates:
        mapping = infer_fba_metabolite_mapping(brief, cand, find_ids)
        payload = build_payload_from_find_ids(cand, gem, find_ids, mapping)
        if payload:
            payloads.append(payload)
        else:
            skipped.append(f"{cand.id}: could not map enzymes to model reactions")

    log(f"Formalization complete: {len(payloads)} payload(s), {len(skipped)} skipped")
    return FormalizeResult(
        gem=gem,
        payloads=payloads,
        skipped=skipped,
        discovery=selection.discovery,
        find_ids_summary=summarize_find_ids(find_ids),
        biomass_validation=biomass_validation,
        biomass_validation_warning=biomass_warning,
        validation_mode=ValidationMode.FBA,
    )


def load_fixture_payload(path: str) -> ScorePathwayPayload:
    data = json.loads(Path(path).read_text())
    return ScorePathwayPayload.model_validate(data)
