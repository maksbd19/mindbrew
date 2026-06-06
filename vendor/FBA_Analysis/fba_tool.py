"""Offline FBA stub — replaced by yanglu12/FBA_Analysis git submodule in production."""

def score_pathway(
    model_ref=None,
    scenario=None,
    carbon_source_rxn=None,
    candidate_reactions=None,
    product_metabolite=None,
    knockouts=None,
    substrate_moles_per_product=1.0,
    objective="product",
    **kwargs,
):
    has_ko = bool(knockouts)
    if has_ko:
        return {
            "status": "optimal",
            "predicted_product_flux": 0.42,
            "yield_corrected_mol_per_mol_substrate": 0.65,
            "bottlenecks": [{"reaction": "TAG_synthesis", "flux": 0.1, "at_bound": False}],
            "calibration": {"confidence_level": "partial"},
            "carbon_audit": {"feedstock_is_sole_carbon_source": True},
            "edits_applied": {"knocked_out": knockouts or [], "not_found": []},
        }
    return {
        "status": "optimal",
        "predicted_product_flux": 0.08,
        "yield_corrected_mol_per_mol_substrate": 0.12,
        "bottlenecks": [
            {"reaction": "ACOAO8p", "flux": 2.5, "at_bound": True},
            {"reaction": "DGA1", "flux": 1.2, "at_bound": False},
        ],
        "calibration": {"confidence_level": "exploratory"},
        "carbon_audit": {"feedstock_is_sole_carbon_source": True},
        "edits_applied": {"knocked_out": [], "not_found": []},
    }
