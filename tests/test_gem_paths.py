"""Tests for GEM path resolution."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("BREWMIND_OFFLINE", "true")

from mindbrew_v2.config.gem import build_gem_profile, load_registry, provisional_validation_mode, resolve_scenario_path
from mindbrew_v2.models import ResearchBrief
from mindbrew_v2.phases.gem_discovery import discover_gem

VENDOR_MODEL = Path(__file__).resolve().parents[1] / "vendor" / "FBA_Analysis" / "iYLI647.xml"


@pytest.fixture
def cache_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("GEM_MODEL_CACHE_DIR", str(tmp_path))
    from mindbrew_v2.settings import get_settings

    get_settings.cache_clear()
    return tmp_path


def test_provisional_validation_mode_wax_brief():
    brief = ResearchBrief(
        ticket_id="t1",
        raw_brief="plant oil wax ester from oleaginous yeast",
        organism=["Yarrowia lipolytica"],
        feedstock={"class": "plant_oil"},
        target={"class": "wax_ester"},
    )
    sel = provisional_validation_mode(brief)
    assert sel.validation_mode.value == "fba"


def test_resolve_scenario_path():
    entry = next(e for e in load_registry() if e.id == "iyli647")
    path = resolve_scenario_path(entry, "plant_oil")
    assert path.endswith("wax_ester_oleate_n_limited.yaml")
    assert Path(path).is_file()


def test_build_gem_profile_uses_cache(cache_dir):
    if not VENDOR_MODEL.is_file():
        pytest.skip("vendor iYLI647.xml not present")
    entry = next(e for e in load_registry() if e.id == "iyli647")
    brief = ResearchBrief(
        ticket_id="t1",
        raw_brief="wax ester from plant oil",
        organism=["Yarrowia lipolytica"],
    )
    discovery = discover_gem(brief, [])
    gem, error = build_gem_profile(entry, brief, discovery=discovery)
    assert error == ""
    assert gem is not None
    assert gem.model_cache_path
    assert Path(gem.model_ref).is_file()
    assert "iyli647" in gem.model_cache_path.lower() or gem.gem_id == "iyli647"
