"""Formalization layer — PathwayCandidate → FBA payloads."""

from __future__ import annotations

import json
from pathlib import Path

from mindbrew_v2.config.gem import select_gem
from mindbrew_v2.models import GemProfile, PathwayCandidate, ResearchBrief, ScorePathwayPayload
from mindbrew_v2.phases.fba_payloads import build_payload_from_find_ids
from mindbrew_v2.tools.fba_client import run_find_ids


def formalize_pathways(
    brief: ResearchBrief,
    candidates: list[PathwayCandidate],
    gem_override: str | None = None,
) -> tuple[GemProfile | None, list[ScorePathwayPayload], list[str]]:
    from mindbrew_v2.progress import log

    log(f"Formalizing {len(candidates)} pathway(s) for FBA…")
    selection = select_gem(brief, override_gem_id=gem_override)
    if selection.gem is None:
        return None, [], ["No GEM available — use literature pathway branch"]

    gem = selection.gem
    log(f"Selected GEM {gem.gem_id} ({gem.model_ref})")
    find_ids = run_find_ids(gem.model_ref)
    payloads: list[ScorePathwayPayload] = []
    skipped: list[str] = []

    for cand in candidates:
        payload = build_payload_from_find_ids(cand, gem, find_ids)
        if payload:
            payloads.append(payload)
        else:
            skipped.append(f"{cand.id}: could not map enzymes to model reactions")

    log(f"Formalization complete: {len(payloads)} payload(s), {len(skipped)} skipped")
    return gem, payloads, skipped


def load_fixture_payload(path: str) -> ScorePathwayPayload:
    data = json.loads(Path(path).read_text())
    return ScorePathwayPayload.model_validate(data)
