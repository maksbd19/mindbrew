from mindbrew_v2.paths import display_path, sanitize_fba_plan_artifact
from mindbrew_v2.phases.checkpoints import artifact_for_display


def test_display_path_returns_basename():
    assert display_path("/Users/dev/brewmind/data/gem_models/iyli647.xml") == "iyli647.xml"
    assert display_path("vendor/FBA_Analysis/scenarios/sunflower_oil.yaml") == "sunflower_oil.yaml"


def test_sanitize_fba_plan_artifact_shortens_paths():
    artifact = {
        "gem_profile": {
            "gem_id": "iyli647",
            "model_ref": "/Users/dev/brewmind/data/gem_models/iyli647.xml",
            "model_cache_path": "/Users/dev/brewmind/data/gem_models/iyli647.xml",
            "scenario": "/Users/dev/brewmind/vendor/FBA_Analysis/scenarios/sunflower_oil.yaml",
            "biomass_validation_scenario": "/Users/dev/brewmind/vendor/FBA_Analysis/scenarios/iyli647_glucose_validation.yaml",
        },
        "score_payloads": [
            {
                "pathway_id": "P1",
                "model_ref": "/Users/dev/brewmind/data/gem_models/iyli647.xml",
                "scenario": "/Users/dev/brewmind/vendor/FBA_Analysis/scenarios/sunflower_oil.yaml",
            }
        ],
    }

    cleaned = sanitize_fba_plan_artifact(artifact)

    assert cleaned["gem_profile"]["model_ref"] == "iyli647.xml"
    assert cleaned["gem_profile"]["model_cache_path"] == "iyli647.xml"
    assert cleaned["gem_profile"]["scenario"] == "sunflower_oil.yaml"
    assert cleaned["gem_profile"]["biomass_validation_scenario"] == "iyli647_glucose_validation.yaml"
    assert cleaned["score_payloads"][0]["model_ref"] == "iyli647.xml"
    assert cleaned["score_payloads"][0]["scenario"] == "sunflower_oil.yaml"
    assert artifact["gem_profile"]["model_ref"].startswith("/Users/")


def test_artifact_for_display_only_sanitizes_cp3():
    artifact = {
        "gem_profile": {"model_ref": "/tmp/model.xml"},
        "score_payloads": [],
    }
    cleaned = artifact_for_display("cp3_fba_plan", artifact)
    assert cleaned["gem_profile"]["model_ref"] == "model.xml"

    other = artifact_for_display("cp2_pathways", artifact)
    assert other["gem_profile"]["model_ref"] == "/tmp/model.xml"
