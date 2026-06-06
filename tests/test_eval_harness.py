"""Eval harness structure and offline regression tests."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
import yaml

from mindbrew_v2.eval.run_eval import load_cases, run_eval

EVAL_DIR = Path(__file__).resolve().parents[1] / "mindbrew_v2" / "eval"
FIXTURES = EVAL_DIR / "fixtures"


@pytest.fixture(autouse=True)
def offline_env(monkeypatch):
    monkeypatch.setenv("BREWMIND_OFFLINE", "true")


def test_offline_eval_passes():
    results = run_eval(tier="offline", live=False)
    assert results, "expected offline eval cases"
    failed = [r for r in results if not r.passed]
    assert not failed, f"failures: {failed}"


def test_live_cases_have_gold_fixtures():
    cases = load_cases(tier="live")
    assert len(cases) >= 3
    for case in cases:
        assert case.requires_live_api
        brief_ref = case.gold.get("brief_ref")
        assert brief_ref, f"{case.id} missing gold.brief_ref"
        assert (FIXTURES / brief_ref).is_file(), f"missing {brief_ref}"
        if case.gold.get("pathways_ref"):
            assert (FIXTURES / case.gold["pathways_ref"]).is_file()


def test_live_cases_yaml_parses():
    path = EVAL_DIR / "gold" / "live_cases.yaml"
    data = yaml.safe_load(path.read_text())
    assert len(data.get("cases", [])) == 3


def test_offline_tier_excludes_live_cases():
    offline = load_cases(tier="offline")
    live = load_cases(tier="live")
    offline_ids = {c.id for c in offline}
    live_ids = {c.id for c in live}
    assert not offline_ids & live_ids


def test_gold_brief_fixtures_are_valid_json():
    for path in (FIXTURES / "expected").rglob("brief.json"):
        data = json.loads(path.read_text())
        assert "gatekeeper_verdict" in data or "organism" in data


def test_sample_runner_offline_mode(monkeypatch):
    monkeypatch.setenv("BREWMIND_OFFLINE", "false")
    from mindbrew_v2.eval.run_sample_cases import configure_runtime, run_sample_cases
    from mindbrew_v2.settings import get_settings

    rows = run_sample_cases(live_llm=False, case_ids=["sample_reject_intake_v1"])
    assert get_settings().brewmind_offline is True
    assert len(rows) == 1
    assert rows[0][2] in ("pass", "fail")

    configure_runtime(live_llm=True)
    assert get_settings().brewmind_offline is False
