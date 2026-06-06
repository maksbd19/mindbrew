"""Pathways phase scorer."""

from __future__ import annotations

import json
from pathlib import Path

from mindbrew_v2.eval.scorers.base import EvalCase, EvalResult
from mindbrew_v2.models import ResearchBrief, Ticket
from mindbrew_v2.phases.biomni import run_biomni_search
from mindbrew_v2.phases.intake import run_intake

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def score_pathways(case: EvalCase) -> EvalResult:
    failures = []
    if case.input.get("pathways_ref"):
        data = json.loads((FIXTURES / case.input["pathways_ref"]).read_text())
        candidates = data
    else:
        raw = case.input.get("raw_brief", "")
        ticket = Ticket(id=case.id, raw_brief=raw)
        brief = run_intake(ticket)
        candidates = [c.model_dump() for c in run_biomni_search(brief)]

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

    return EvalResult(case.id, case.phase, len(failures) == 0, failures, case.weight)
