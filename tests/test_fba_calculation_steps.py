from mindbrew_v2.tools.fba_calculation_steps import build_calculation_steps
from mindbrew_v2.tools.fba_client import _parse_fba_result


def test_build_calculation_steps_from_score_output():
    raw = {
        "status": "optimal",
        "objective_used": "product",
        "predicted_product_flux": 0.42,
        "growth_rate": 0.01,
        "yield_mol_per_mol_substrate": 0.84,
        "yield_corrected_mol_per_mol_substrate": 0.42,
        "simulation_context": {
            "carbon_source_rxn": "EX_ocdcea_LPAREN_e_RPAREN_",
            "carbon_source_uptake": 10.0,
            "biomass_rxn": "BIOMASS_YL",
            "use_minimal_medium": True,
            "substrate_moles_per_product": 2.0,
            "growth_constraints": {
                "max_growth_unconstrained": 0.24,
                "min_growth_applied": 0.024,
            },
            "exchange_constraints_applied": {
                "EX_o2_e": [-20, 0],
            },
        },
        "inserted_reactions": ["FAR", "WS"],
        "edits_applied": {"knocked_out": ["ACOAO4p"], "not_found": []},
        "bottlenecks": [{"reaction": "WS", "flux": 0.42, "span": 0.0, "at_bound": True}],
        "carbon_audit": {
            "feedstock_is_sole_carbon_source": True,
            "total_carbon_import_mmol_per_h": 59.5,
        },
        "calibration": {
            "confidence_level": "partial",
            "product_confidence_level": "unvalidated",
            "missing_literature_inputs": ["product exchange bound"],
            "recommended_use": "Rank designs relative to each other",
        },
        "message": "OK",
    }

    steps = build_calculation_steps(raw)

    assert len(steps) >= 8
    assert steps[0].title == "Configure simulation scenario"
    assert "EX_ocdcea" in steps[0].detail
    assert any(s.title == "Insert heterologous reactions" for s in steps)
    assert any(s.title == "Calculate molar yield" for s in steps)
    assert any(s.title == "Assess calibration confidence" for s in steps)


def test_build_calculation_steps_handles_fba_tool_exchange_format():
    raw = {
        "status": "optimal",
        "objective_used": "product",
        "simulation_context": {
            "exchange_constraints": {
                "EX_o2_e": [-1000.0, 0.0],
                "EX_nh4_e": [-1.0, 0.0],
            },
            "exchange_constraints_applied": {
                "exchange_bounds_set": ["EX_o2_e", "EX_nh4_e"],
                "exchange_not_found": [],
            },
        },
        "calibration": {},
        "carbon_audit": {},
        "bottlenecks": [],
        "edits_applied": {},
    }

    steps = build_calculation_steps(raw)
    exchange_step = next(s for s in steps if s.title == "Apply exchange constraints")

    assert "EX_o2_e: [-1000, 0]" in exchange_step.detail
    assert "EX_nh4_e: [-1, 0]" in exchange_step.detail


def test_parse_fba_result_includes_calculation_steps():
    result = _parse_fba_result(
        "P1",
        {
            "status": "optimal",
            "objective_used": "product",
            "predicted_product_flux": 0.1,
            "growth_rate": 0.01,
            "yield_corrected_mol_per_mol_substrate": 0.1,
            "simulation_context": {"carbon_source_rxn": "EX_glc_e"},
            "calibration": {"confidence_level": "exploratory"},
            "carbon_audit": {"feedstock_is_sole_carbon_source": True},
            "bottlenecks": [],
            "edits_applied": {},
        },
    )

    assert result.calculation_steps
    assert result.objective_used == "product"
    assert result.simulation_context["carbon_source_rxn"] == "EX_glc_e"
