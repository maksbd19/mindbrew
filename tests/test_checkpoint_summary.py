"""Tests for checkpoint summary text."""

from mindbrew_v2.phases.checkpoints import checkpoint_summary


def test_checkpoint_summary_spec_includes_brief_details():
    summary = checkpoint_summary(
        "cp1_spec",
        {
            "brief": {
                "target": {"name": "wax ester"},
                "feedstock": {"name": "oleic acid"},
                "organism": ["Yarrowia lipolytica"],
            },
            "validation_mode": "fba",
        },
    )
    assert "wax ester from oleic acid" in summary
    assert "Yarrowia lipolytica" in summary
    assert "fba validation" in summary


def test_checkpoint_summary_fba_plan_includes_payloads_and_gem():
    summary = checkpoint_summary(
        "cp3_fba_plan",
        {
            "score_payloads": [{"pathway_id": "pw1"}, {"pathway_id": "pw2"}],
            "skipped": ["pw3: no mapping"],
            "gem_profile": {"gem_id": "iYLI647"},
        },
    )
    assert "2 FBA payloads ready" in summary
    assert "GEM iYLI647" in summary
    assert "1 skipped" in summary


def test_checkpoint_summary_fba_results_includes_verdicts():
    summary = checkpoint_summary(
        "cp4_fba_results",
        {
            "fba_results": [
                {"pathway_id": "pw1", "verdict": "pass", "rank": 1, "yield_corrected_mol_per_mol_substrate": 0.82},
                {"pathway_id": "pw2", "verdict": "marginal", "rank": 2},
            ],
        },
    )
    assert "2 pathways scored" in summary
    assert "top: pass (0.82 mol/mol)" in summary
