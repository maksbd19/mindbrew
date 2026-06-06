"""Shared gold-label assertion helpers for live eval cases."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mindbrew_v2.models import ResearchBrief

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"

_GOLD_BRIEF_FIELDS = ("gatekeeper_verdict", "organism", "feedstock", "target")


def resolve_gold_ref(case_gold: dict[str, Any], assertion: dict[str, Any], key: str) -> str | None:
    if assertion.get(key):
        return assertion[key]
    return case_gold.get(key)


def load_gold_brief(ref: str) -> ResearchBrief:
    return ResearchBrief.model_validate(json.loads((FIXTURES / ref).read_text()))


def load_gold_pathways(ref: str) -> list[dict[str, Any]]:
    data = json.loads((FIXTURES / ref).read_text())
    return data if isinstance(data, list) else data.get("candidates", [])


def check_gold_brief_fields(
    brief: ResearchBrief,
    gold_ref: str,
    *,
    fields: tuple[str, ...] = _GOLD_BRIEF_FIELDS,
) -> list[str]:
    failures: list[str] = []
    gold = load_gold_brief(gold_ref)

    for field_name in fields:
        if field_name == "gatekeeper_verdict":
            if gold.gatekeeper_verdict and brief.gatekeeper_verdict != gold.gatekeeper_verdict:
                failures.append(
                    f"gold_brief_fields: gatekeeper {brief.gatekeeper_verdict} != {gold.gatekeeper_verdict}"
                )
        elif field_name == "organism":
            if gold.organism and sorted(brief.organism) != sorted(gold.organism):
                failures.append(f"gold_brief_fields: organism {brief.organism} != {gold.organism}")
        elif field_name == "feedstock":
            if gold.feedstock.compound_class and brief.feedstock.compound_class != gold.feedstock.compound_class:
                failures.append(
                    f"gold_brief_fields: feedstock.class "
                    f"{brief.feedstock.compound_class} != {gold.feedstock.compound_class}"
                )
        elif field_name == "target":
            if gold.target.compound_class and brief.target.compound_class != gold.target.compound_class:
                failures.append(
                    f"gold_brief_fields: target.class "
                    f"{brief.target.compound_class} != {gold.target.compound_class}"
                )

    return failures


def enzymes_in_candidates(candidates: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for cand in candidates:
        parts.extend(cand.get("enzymes", []))
        for step in cand.get("reaction_steps", []):
            parts.append(step.get("enzyme_name") or "")
            parts.extend(step.get("gene_names", []))
    return " ".join(parts).lower()


def check_gold_pathway_enzymes(
    candidates: list[dict[str, Any]],
    *,
    enzymes: list[str] | None = None,
    gold_pathways_ref: str | None = None,
) -> list[str]:
    failures: list[str] = []
    required = [e.lower() for e in (enzymes or [])]

    if not required and gold_pathways_ref:
        gold_candidates = load_gold_pathways(gold_pathways_ref)
        required = []
        for cand in gold_candidates:
            for enzyme in cand.get("enzymes", []):
                required.append(enzyme.lower())
            for step in cand.get("reaction_steps", []):
                for gene in step.get("gene_names", []):
                    required.append(gene.lower())
        required = list(dict.fromkeys(required))

    if not required:
        failures.append("gold_pathway_enzymes: no enzymes specified")
        return failures

    text = enzymes_in_candidates(candidates)
    missing = [e for e in required if e not in text]
    if missing:
        failures.append(f"gold_pathway_enzymes: missing {missing}")

    return failures


def check_candidate_count_min(candidates: list[Any], minimum: int) -> list[str]:
    if len(candidates) < minimum:
        return [f"candidate_count_min: {len(candidates)} < {minimum}"]
    return []
