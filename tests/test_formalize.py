"""Tests for FBA formalization payloads."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("BREWMIND_OFFLINE", "true")

from mindbrew_v2.models import (
    CandidateReaction,
    Citation,
    GemProfile,
    PathwayCandidate,
    ReactionStep,
)
from mindbrew_v2.phases.fba_payloads import (
    build_payload_from_find_ids,
    build_wax_ester_reactions,
    has_far_ws,
    resolve_knockouts,
)
from mindbrew_v2.phases.formalize import formalize_pathways
from mindbrew_v2.tools.fba_client import _offline_find_ids, run_find_ids

VENDOR_ROOT = Path(__file__).resolve().parents[1] / "vendor" / "FBA_Analysis"
MODEL_REF = str(VENDOR_ROOT / "iYLI647.xml")


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
                heterologous=True,
            ),
            ReactionStep(
                step_number=2,
                description="Fatty alcohol + acyl-CoA → wax ester",
                enzyme_name="wax ester synthase (WS)",
                gene_names=["WS"],
                heterologous=True,
            ),
        ],
        citations=[Citation(doi="10.1000/example", title="Wax ester production")],
    )


def _gem_profile() -> GemProfile:
    return GemProfile(
        gem_id="iyli647",
        model_ref=MODEL_REF,
        scenario=str(VENDOR_ROOT / "scenarios/wax_ester_oleate_n_limited.yaml"),
        organism="Yarrowia lipolytica",
        feedstock_class="plant_oil",
    )


def test_has_far_ws_detects_enzymes():
    tokens = {"FAR", "WAX ESTER SYNTHASE"}
    has_far, has_ws = has_far_ws(tokens)
    assert has_far is True
    assert has_ws is True


def test_build_wax_ester_reactions_uses_model_ids():
    recommended = _offline_find_ids()["recommended"]
    reactions = build_wax_ester_reactions(recommended, has_far=True, has_ws=True)
    assert reactions is not None
    assert len(reactions) == 2
    far = reactions[0]
    assert far.id == "FAR"
    assert "odecoa_c" in far.stoichiometry
    assert "nadph_c" in far.stoichiometry
    assert "oleyl_alcohol_c" in far.stoichiometry


def test_resolve_knockouts_from_gene_alias():
    find_ids = _offline_find_ids()
    knockouts = resolve_knockouts(find_ids, {"POX1", "FAR"})
    assert "ACOAO8p" in knockouts


def test_build_payload_offline_schema():
    payload = build_payload_from_find_ids(_wax_candidate(), _gem_profile(), _offline_find_ids())
    assert payload is not None
    assert payload.carbon_source_rxn == "EX_ocdcea_LPAREN_e_RPAREN_"
    assert payload.product_metabolite == "wax_ester_c"
    assert payload.substrate_moles_per_product == 2.0
    assert payload.candidate_reactions[0].id == "FAR"
    assert payload.candidate_reactions[1].id == "WS"


def test_formalize_skips_non_wax_pathway(tmp_path, monkeypatch):
    from mindbrew_v2.models import ResearchBrief

    monkeypatch.setenv("GEM_MODEL_CACHE_DIR", str(tmp_path))
    from mindbrew_v2.settings import get_settings

    get_settings.cache_clear()

    brief = ResearchBrief(
        ticket_id="t1",
        raw_brief="plant oil wax ester production",
        organism=["Yarrowia lipolytica"],
        feedstock={"class": "plant_oil"},
        target={"class": "wax_ester"},
    )
    cand = PathwayCandidate(id="pw_other", name="Unknown pathway", enzymes=["XYZ1"])
    result = formalize_pathways(brief, [cand])
    if VENDOR_ROOT.joinpath("iYLI647.xml").is_file():
        assert result.gem is not None
    assert result.payloads == []
    assert len(result.skipped) == 1


@pytest.mark.integration
def test_run_find_ids_resolves_real_carbon_source(tmp_path, monkeypatch):
    pytest.importorskip("cobra")
    from unittest.mock import patch

    if not Path(MODEL_REF).is_file():
        pytest.skip("vendor iYLI647.xml not present")
    monkeypatch.setenv("GEM_MODEL_CACHE_DIR", str(tmp_path))
    from mindbrew_v2.settings import get_settings

    get_settings.cache_clear()
    from mindbrew_v2.tools.gem_model_cache import ensure_model

    cached, _, _ = ensure_model("iyli647", MODEL_REF)
    with patch("mindbrew_v2.tools.fba_client.is_offline", return_value=False):
        report = run_find_ids(cached or MODEL_REF)
    assert report.get("status") == "ok"
    carbon = report["recommended"]["carbon_source_rxn"]
    assert carbon != "EX_ole_e"
    assert "EX_" in carbon
    assert report["recommended"]["oleoyl_coa_metabolite"] == "odecoa_c"
