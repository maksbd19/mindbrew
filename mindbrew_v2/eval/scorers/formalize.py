"""Formalize phase scorer."""

from __future__ import annotations

import json
from pathlib import Path

from mindbrew_v2.config.gem import select_gem
from mindbrew_v2.eval.scorers.base import EvalCase, EvalResult
from mindbrew_v2.models import PathwayCandidate, ResearchBrief, Ticket
from mindbrew_v2.phases.formalize import formalize_pathways, load_fixture_payload
from mindbrew_v2.phases.intake import run_intake

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def score_formalize(case: EvalCase) -> EvalResult:
    failures = []

    if case.input.get("brief_ref"):
        brief = ResearchBrief.model_validate(json.loads((FIXTURES / case.input["brief_ref"]).read_text()))
    else:
        ticket = Ticket(id=case.id, raw_brief=case.input.get("raw_brief", ""))
        brief = run_intake(ticket)

    for assertion in case.assertions:
        atype = assertion.get("type")
        if atype == "gem_id_equals":
            sel = select_gem(brief)
            expected = assertion.get("value")
            actual = sel.gem.gem_id if sel.gem else None
            if actual != expected:
                failures.append(f"gem_id: expected {expected}, got {actual}")
        elif atype == "validation_mode_in":
            sel = select_gem(brief)
            if sel.validation_mode.value not in assertion.get("values", []):
                failures.append(f"validation_mode: {sel.validation_mode}")
        elif atype == "payload_valid":
            pathways_ref = case.input.get("pathways_ref", "pathways/ticket1_candidates.json")
            cands = [
                PathwayCandidate.model_validate(c)
                for c in json.loads((FIXTURES / pathways_ref).read_text())
            ]
            _, payloads, skipped = formalize_pathways(brief, cands)
            if not payloads:
                failures.append(f"no payloads; skipped={skipped}")

    return EvalResult(case.id, case.phase, len(failures) == 0, failures, case.weight)
