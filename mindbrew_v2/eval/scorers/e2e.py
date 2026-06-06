"""End-to-end eval scorer."""

from __future__ import annotations

from mindbrew_v2.config.gem import provisional_validation_mode
from mindbrew_v2.eval.scorers.base import EvalCase, EvalResult
from mindbrew_v2.models import PathwayCandidate, Ticket, ValidationMode
from mindbrew_v2.phases.literature_search import run_literature_search
from mindbrew_v2.phases.intake import run_intake
from mindbrew_v2.phases.literature_plan import build_literature_plan
from mindbrew_v2.phases.report import generate_report


def score_e2e(case: EvalCase) -> EvalResult:
    failures = []
    raw = case.input.get("raw_brief", "")
    ticket = Ticket(id=case.id, raw_brief=raw)
    brief = run_intake(ticket)
    selection = provisional_validation_mode(brief)
    candidates = run_literature_search(brief)[0]

    for assertion in case.assertions:
        atype = assertion.get("type")
        if atype == "validation_mode_in":
            if selection.validation_mode.value not in assertion.get("values", []):
                failures.append(f"mode: {selection.validation_mode}")
        elif atype == "pathways_not_empty":
            if not candidates:
                failures.append("no pathway candidates")
        elif atype == "lit_plan_has_genes":
            if not candidates:
                failures.append("no candidates for lit plan")
                continue
            plan = build_literature_plan(brief, candidates[0])
            if not plan.gene_suggestions:
                failures.append("literature plan missing gene suggestions")
        elif atype == "report_has_sections":
            report = generate_report(
                brief,
                selection.validation_mode,
                candidates,
                candidates[0].id if candidates else None,
            )
            md = report.markdown.lower()
            for section in assertion.get("values", []):
                if section.replace("_", " ") not in md and section not in md:
                    failures.append(f"report missing section: {section}")

    return EvalResult(case.id, case.phase, len(failures) == 0, failures, case.weight)
