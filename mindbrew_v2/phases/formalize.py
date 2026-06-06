"""Formalization layer — PathwayCandidate → FBA payloads."""

from __future__ import annotations

import json
from pathlib import Path

from mindbrew_v2.config.gem import select_gem
from mindbrew_v2.models import (
    CandidateReaction,
    GemProfile,
    PathwayCandidate,
    ResearchBrief,
    ScorePathwayPayload,
)
from mindbrew_v2.settings import get_settings, is_offline
from mindbrew_v2.tools.fba_client import run_find_ids


def formalize_pathways(
    brief: ResearchBrief,
    candidates: list[PathwayCandidate],
    gem_override: str | None = None,
) -> tuple[GemProfile | None, list[ScorePathwayPayload], list[str]]:
    selection = select_gem(brief, override_gem_id=gem_override)
    if selection.gem is None:
        return None, [], ["No GEM available — use literature pathway branch"]

    gem = selection.gem
    find_ids = run_find_ids(gem.model_ref)
    payloads: list[ScorePathwayPayload] = []
    skipped: list[str] = []

    for cand in candidates:
        payload = _formalize_candidate(cand, gem, find_ids)
        if payload:
            payloads.append(payload)
        else:
            skipped.append(f"{cand.id}: could not map enzymes to model reactions")

    return gem, payloads, skipped


def _formalize_candidate(
    cand: PathwayCandidate,
    gem: GemProfile,
    find_ids: dict,
) -> ScorePathwayPayload | None:
    recommended = find_ids.get("recommended", {})
    carbon_source = recommended.get("carbon_source_rxn", "EX_ole_e")

    enzyme_names = {e.upper() for e in cand.enzymes}
    for step in cand.reaction_steps:
        if step.enzyme_name:
            enzyme_names.add(step.enzyme_name.upper())
        enzyme_names.update(g.upper() for g in step.gene_names)

    has_far = any("FAR" in e for e in enzyme_names)
    has_ws = any("WS" in e or "WAX" in e for e in enzyme_names)

    if not (has_far or has_ws):
        if is_offline() and "wax" in cand.name.lower():
            has_far, has_ws = True, True
        else:
            return None

    reactions: list[CandidateReaction] = []
    if has_far:
        reactions.append(
            CandidateReaction(
                id="FAR_rxn",
                name="fatty acyl-CoA reductase",
                stoichiometry={"fatty_acyl_coa": -1.0, "fatty_alcohol": 1.0},
                gene_associations=["FAR"],
            )
        )
    if has_ws:
        reactions.append(
            CandidateReaction(
                id="WS_rxn",
                name="wax ester synthase",
                stoichiometry={"fatty_alcohol": -1.0, "fatty_acyl_coa": -1.0, "wax_ester_c": 1.0},
                gene_associations=["WS", "WSD1"],
            )
        )

    knockouts = find_ids.get("gene_alias_resolution", {}).get("recommended_knockouts", [])
    if isinstance(knockouts, dict):
        knockouts = list(knockouts.values())

    if is_offline():
        knockouts = knockouts or ["ACOAO8p", "ACOAO4p"]

    return ScorePathwayPayload(
        pathway_id=cand.id,
        model_ref=gem.model_ref,
        scenario=gem.scenario,
        carbon_source_rxn=carbon_source,
        candidate_reactions=reactions,
        product_metabolite=recommended.get("product_metabolite", "wax_ester_c"),
        knockouts=list(knockouts)[:5],
        substrate_moles_per_product=1.0,
        objective="product",
        source_citations=cand.citations,
    )


def load_fixture_payload(path: str) -> ScorePathwayPayload:
    data = json.loads(Path(path).read_text())
    return ScorePathwayPayload.model_validate(data)
