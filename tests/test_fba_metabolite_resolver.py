"""Tests for literature-based FBA metabolite inference."""

from __future__ import annotations

import os

os.environ.setdefault("BREWMIND_OFFLINE", "true")

from mindbrew_v2.models import CompoundSpec, PathwayCandidate, ReactionStep, ResearchBrief
from mindbrew_v2.phases.fba_metabolite_resolver import infer_fba_metabolite_mapping
from mindbrew_v2.tools.fba_client import _offline_find_ids


def _wax_candidate() -> PathwayCandidate:
    return PathwayCandidate(
        id="pw_wax_ester_far_ws",
        name="Wax ester via FAR + WS",
        enzymes=["FAR", "WS"],
        reaction_steps=[
            ReactionStep(
                step_number=1,
                description="Fatty acyl-CoA → fatty alcohol",
                enzyme_name="fatty acyl-CoA reductase (FAR)",
                gene_names=["FAR"],
            ),
            ReactionStep(
                step_number=2,
                description="Fatty alcohol + acyl-CoA → wax ester",
                enzyme_name="wax ester synthase (WS)",
                gene_names=["WS"],
            ),
        ],
    )


def test_infer_wax_ester_mapping_from_literature():
    brief = ResearchBrief(
        ticket_id="t1",
        raw_brief="wax ester from plant oil",
        target=CompoundSpec(name="wax ester", compound_class="wax_ester"),
        feedstock=CompoundSpec(name="plant oil", compound_class="plant_oil"),
    )
    find_ids = _offline_find_ids(["wax ester"])
    mapping = infer_fba_metabolite_mapping(brief, _wax_candidate(), find_ids)
    assert mapping.pathway_template == "far_ws"
    assert mapping.product_metabolite == "wax_ester_c"
    assert mapping.fatty_alcohol_metabolite == "oleyl_alcohol_c"
    assert mapping.substrate_moles_per_product == 2.0
