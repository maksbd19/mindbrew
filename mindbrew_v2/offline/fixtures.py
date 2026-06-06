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
            "biomni_provenance": ["literature_search", "kegg_pathway"],
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
            "biomni_provenance": ["literature_search"],
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
        "what_worked": "Wax ester FAR+WS pathway shows strongest literature and FBA support.",
        "what_didnt": "Fatty alcohol-only route lacks emollient match to dimethicone profile.",
        "recommendations": "Proceed with FAR+WS in Y. lipolytica; knock out β-oxidation genes.",
        "appendix": "Literature provenance: literature + KEGG. Model: iYLI647.",
    }
