"""Formalize phase scorer."""

from __future__ import annotations

import json
from pathlib import Path

from mindbrew_v2.config.gem import provisional_validation_mode, select_gem
from mindbrew_v2.eval.scorers.base import EvalCase, EvalResult
from mindbrew_v2.models import PathwayCandidate, ResearchBrief, Ticket
from mindbrew_v2.phases.formalize import formalize_pathways
from mindbrew_v2.phases.gem_discovery import discover_gem
from mindbrew_v2.phases.intake import run_intake

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _load_pathway_candidates(case: EvalCase) -> list[PathwayCandidate]:
    pathways_ref = case.input.get("pathways_ref", "pathways/ticket1_candidates.json")
    raw = json.loads((FIXTURES / pathways_ref).read_text())
    items = raw if isinstance(raw, list) else raw.get("candidates", [])
    return [PathwayCandidate.model_validate(c) for c in items]


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
            discovery = discover_gem(brief, [])
            sel = select_gem(brief, discovery)
            expected = assertion.get("value")
            actual = sel.gem.gem_id if sel.gem else None
            if actual != expected:
                failures.append(f"gem_id: expected {expected}, got {actual}")
        elif atype == "validation_mode_in":
            sel = provisional_validation_mode(brief)
            if sel.validation_mode.value not in assertion.get("values", []):
                failures.append(f"validation_mode: {sel.validation_mode}")
        elif atype in ("payload_valid", "formalize_no_payloads"):
            cands = _load_pathway_candidates(case)
            result = formalize_pathways(brief, cands)
            if atype == "payload_valid" and not result.payloads:
                failures.append(f"no payloads; skipped={result.skipped}")
            if atype == "formalize_no_payloads":
                if result.payloads:
                    failures.append(f"expected no payloads, got {len(result.payloads)}")
                if not result.skipped:
                    failures.append("expected skipped pathways, got none")

    return EvalResult(case.id, case.phase, len(failures) == 0, failures, case.weight)
