"""Offline fixtures for eval and development without API keys."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


def offline_structured_response(schema: type[BaseModel], prompt: str) -> dict[str, Any]:
    name = schema.__name__
    text = prompt.lower()

    if name == "IntakeResult":
        return _intake_result(text)
    if name == "PathwayCandidateList":
        return {"candidates": _pathway_candidates(text)}
    if name == "LiteraturePlanExtract":
        return _literature_plan_extract()
    if name == "ReportExtract":
        return _report_extract(text)
    if name == "FbaMetaboliteMapping":
        return _fba_metabolite_mapping(text)

    return {}


def _intake_result(text: str) -> dict[str, Any]:
    if "python" in text and "debug" in text:
        return {
            "gatekeeper_verdict": "REJECT",
            "organism": [],
            "feedstock": {"name": "", "class": ""},
            "target": {"name": "", "class": ""},
            "target_function": "",
            "constraints": [],
            "tasks": [],
            "clarifying_questions": [],
        }

    organism = ["Yarrowia lipolytica"]
    feedstock_class = "plant_oil"
    target_class = "wax_ester"
    target_function = "silicone replacement, frizz control, smoothness, dimethicone-like"

    if "microbiome" in text or "dandruff" in text or "scalp" in text:
        organism = []
        feedstock_class = ""
        target_class = "postbiotic"
        target_function = "scalp microbiome balance, dandruff, barrier support"
    elif "cuticle" in text or "ceramide" in text or "barrier lipid" in text:
        feedstock_class = "plant_oil"
        target_class = "ceramide_like_lipid"
        target_function = "cuticle repair, moisture retention, barrier lipid"

    return {
        "gatekeeper_verdict": "PROCEED",
        "organism": organism,
        "feedstock": {"name": "plant oil", "class": feedstock_class},
        "target": {"name": "fermentation-derived lipid", "class": target_class},
        "target_function": target_function,
        "constraints": ["natural", "sustainably sourced"],
        "tasks": ["pathway identification", "production outline"],
        "clarifying_questions": [],
    }


def _pathway_candidates(text: str) -> list[dict[str, Any]]:
    return [
        {
            "id": "pw_wax_ester_far_ws",
            "name": "Wax ester via FAR + WS",
            "description": "Fatty acyl-CoA reduced to alcohol (FAR) then esterified (WS)",
            "reaction_steps": [
                {
                    "step_number": 1,
                    "description": "Fatty acyl-CoA → fatty alcohol",
                    "enzyme_ec": "1.2.1.84",
                    "enzyme_name": "fatty acyl-CoA reductase (FAR)",
                    "gene_names": ["FAR"],
                    "heterologous": True,
                },
                {
                    "step_number": 2,
                    "description": "Fatty alcohol + acyl-CoA → wax ester",
                    "enzyme_ec": "2.3.1.---",
                    "enzyme_name": "wax ester synthase (WS)",
                    "gene_names": ["WS", "WSD1"],
                    "heterologous": True,
                },
            ],
            "enzymes": ["FAR", "WS", "wax ester synthase"],
            "citations": [{"doi": "10.1002/bit.26067", "title": "Wax ester production in Y. lipolytica"}],
            "reported_titer": "1.5 g/L literature",
            "confidence": "strong",
            "confidence_rationale": "Direct literature precedent with reported titer in Y. lipolytica for wax ester production.",
            "literature_provenance": ["literature_search", "kegg_pathway"],
        },
        {
            "id": "pw_fatty_alcohol",
            "name": "Fatty alcohol direct route",
            "description": "Terminal fatty alcohol as emollient",
            "reaction_steps": [
                {
                    "step_number": 1,
                    "description": "Fatty acyl-CoA → fatty alcohol",
                    "enzyme_name": "FAR",
                    "gene_names": ["FAR"],
                    "heterologous": True,
                }
            ],
            "enzymes": ["FAR"],
            "citations": [{"pmid": "12345678", "title": "Fatty alcohol emollients"}],
            "confidence": "partial",
            "confidence_rationale": "FAR route known but emollient profile for this target function not directly demonstrated.",
            "literature_provenance": ["literature_search"],
        },
    ]


def _literature_plan_extract() -> dict[str, Any]:
    return {
        "gene_suggestions": [
            {
                "gene": "FAR",
                "action": "heterologous",
                "rationale": "Literature precedent for wax ester precursors",
                "citation": {"doi": "10.1002/bit.26067", "title": "Wax ester production in Y. lipolytica"},
            },
            {
                "gene": "WS",
                "action": "heterologous",
                "rationale": "Wax ester synthase from jojoba orthologs",
                "citation": {"doi": "10.1002/bit.26067", "title": "Wax ester production in Y. lipolytica"},
            },
        ],
        "known_risks": ["β-oxidation competition", "TAG storage diversion"],
        "gaps": ["No flux validation without registered GEM"],
        "next_steps": ["Wet-lab feasibility", "Register GEM for FBA"],
    }


def _report_extract(text: str) -> dict[str, Any]:
    return {
        "project_summary": (
            "This proposal targets C34–C36 wax esters produced from sunflower-derived oleic acid "
            "via whole-cell fermentation in Yarrowia lipolytica for premium haircare silicone replacement."
        ),
        "target_molecule_specification": (
            "C34–C36 wax esters (C18:1/C16:0 and C18:1/C18:0). INCI: Jojoba Esters (proposed). "
            "Functional property: frizz control and dimethicone-like smoothness."
        ),
        "feedstock_starting_material": (
            "Sunflower oil / C18:1 oleic acid feedstock. Chosen for sustainability and fatty acid profile match."
        ),
        "production_strategy": (
            "Whole-cell fermentation in Y. lipolytica using FAR + WS enzymatic steps from fatty acyl-CoA to wax ester."
        ),
        "genetic_engineering_plan": (
            "Insert: FAR (fatty acyl reductase), WS (wax ester synthase). "
            "Knock out: β-oxidation (POX1–6, MFE1). Down-regulate: TAG synthesis (DGA1, DGA2, LRO1, ARE1)."
        ),
        "predicted_performance": (
            "Expected yield 5–8 g/L based on literature precedent (MhFAR + AbWS at 7.58 g/L). "
            "Fermentation at 28°C, pH 5.5, glucose carbon source, 120 h duration."
        ),
        "validation_plan": (
            "Measure yield by HPLC/GC, confirm ester structure by MS. "
            "Efficacy proxy: frizz test and TEWL. Success: ≥5 g/L with ≥90% target ester purity."
        ),
        "risk_bottleneck_assessment": (
            "Competing β-oxidation and TAG storage pathways may reduce yield. "
            "Monitor fatty alcohol intermediates. Scale-up: oxygen transfer and foam control."
        ),
        "regulatory_positioning": (
            "GMO-derived ingredient; COSMOS/ECOCERT eligibility depends on host and process certification. "
            "EU SCCS review required; NMPA filing for China market."
        ),
    }


def _fba_metabolite_mapping(text: str) -> dict[str, Any]:
    if "far" in text and ("ws" in text or "wax" in text or "wax ester" in text):
        return {
            "product_metabolite": "wax_ester_c",
            "fatty_alcohol_metabolite": "oleyl_alcohol_c",
            "substrate_moles_per_product": 2.0,
            "product_search_terms": ["wax ester", "wax", "ester"],
            "pathway_template": "far_ws",
            "rationale": "FAR+WS wax ester pathway from literature; 2 mol C18 per C36 product.",
        }
    product = "product_c"
    if "ceramide" in text:
        product = "ceramide_c"
    elif "alcohol" in text:
        product = "fatty_alcohol_c"
    return {
        "product_metabolite": product,
        "fatty_alcohol_metabolite": None,
        "substrate_moles_per_product": 1.0,
        "product_search_terms": [product.replace("_c", "")],
        "pathway_template": "generic",
        "rationale": "Generic single-product mapping from target description.",
    }
