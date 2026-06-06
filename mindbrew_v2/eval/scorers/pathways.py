"""Pathways phase scorer."""

from __future__ import annotations

import json
from pathlib import Path

from mindbrew_v2.eval.scorers.base import EvalCase, EvalResult
from mindbrew_v2.eval.scorers.gold_assertions import (
    check_candidate_count_min,
    check_gold_pathway_enzymes,
    resolve_gold_ref,
)
from mindbrew_v2.models import Ticket
from mindbrew_v2.phases.literature_search import run_literature_search
from mindbrew_v2.phases.intake import run_intake

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def score_pathways(case: EvalCase) -> EvalResult:
    failures = []
    if case.input.get("pathways_ref"):
        data = json.loads((FIXTURES / case.input["pathways_ref"]).read_text())
        candidates = data if isinstance(data, list) else data.get("candidates", [])
    else:
        raw = case.input.get("raw_brief", "")
        ticket = Ticket(id=case.id, raw_brief=raw)
        brief = run_intake(ticket)
        candidates = [c.model_dump() for c in run_literature_search(brief)[0]]

    for assertion in case.assertions:
        atype = assertion.get("type")
        if atype == "any_candidate_has_enzymes":
            enzymes_needed = [e.lower() for e in assertion.get("values", [])]
            found = False
            for cand in candidates:
                text = " ".join(cand.get("enzymes", [])).lower()
                for step in cand.get("reaction_steps", []):
                    text += " " + (step.get("enzyme_name") or "").lower()
                if all(e in text for e in enzymes_needed):
                    found = True
                    break
            if not found:
                failures.append(f"missing enzymes: {enzymes_needed}")
        elif atype == "min_citation_count":
            min_c = assertion.get("value", 1)
            total = sum(len(c.get("citations", [])) for c in candidates)
            if total < min_c:
                failures.append(f"citations {total} < {min_c}")
        elif atype == "candidate_text_contains":
            needles = [v.lower() for v in assertion.get("values", [])]
            text_blob = " ".join(
                [
                    cand.get("name", "") + " " + cand.get("description", "") + " " + " ".join(cand.get("enzymes", []))
                    for cand in candidates
                ]
            ).lower()
            if not any(needle in text_blob for needle in needles):
                failures.append(f"candidate_text_contains: none of {needles} found")
        elif atype == "candidate_count_min":
            failures.extend(check_candidate_count_min(candidates, assertion.get("value", 1)))
        elif atype == "gold_pathway_enzymes":
            pathways_ref = resolve_gold_ref(case.gold, assertion, "pathways_ref")
            failures.extend(
                check_gold_pathway_enzymes(
                    candidates,
                    enzymes=assertion.get("values"),
                    gold_pathways_ref=pathways_ref,
                )
            )

    return EvalResult(case.id, case.phase, len(failures) == 0, failures, case.weight)
