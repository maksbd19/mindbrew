"""Intake phase scorer."""

from __future__ import annotations

from mindbrew_v2.eval.scorers.base import EvalCase, EvalResult
from mindbrew_v2.models import Ticket
from mindbrew_v2.phases.intake import run_intake


def score_intake(case: EvalCase) -> EvalResult:
    raw = case.input.get("raw_brief", "")
    ticket = Ticket(id=case.id, raw_brief=raw)
    brief = run_intake(ticket)
    failures = []

    for assertion in case.assertions:
        atype = assertion.get("type")
        if atype == "field_contains":
            val = getattr(brief, assertion["field"], "") or ""
            if isinstance(val, list):
                val = " ".join(val)
            elif hasattr(val, "compound_class"):
                val = f"{val.name} {val.compound_class}"
            else:
                val = str(val)
            for needle in assertion.get("values", []):
                if needle.lower() not in val.lower():
                    failures.append(f"field_contains: {assertion['field']} missing '{needle}'")
        elif atype == "field_in":
            obj = getattr(brief, assertion["field"], None)
            cls = obj.compound_class if hasattr(obj, "compound_class") else str(obj)
            if cls not in assertion.get("values", []):
                failures.append(f"field_in: {assertion['field']}={cls} not in {assertion['values']}")
        elif atype == "gatekeeper_verdict_in":
            if brief.gatekeeper_verdict not in assertion.get("values", []):
                failures.append(f"gatekeeper: {brief.gatekeeper_verdict}")

    return EvalResult(case.id, case.phase, len(failures) == 0, failures, case.weight)
