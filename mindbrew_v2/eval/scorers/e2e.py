"""End-to-end eval scorer."""

from __future__ import annotations

from mindbrew_v2.config.gem import provisional_validation_mode
from mindbrew_v2.eval.scorers.base import EvalCase, EvalResult
from mindbrew_v2.eval.scorers.gold_assertions import (
    check_gold_brief_fields,
    check_gold_pathway_enzymes,
    resolve_gold_ref,
)
from mindbrew_v2.models import FBAValidationResult, Ticket, ValidationMode
from mindbrew_v2.phases.formalize import formalize_pathways
from mindbrew_v2.phases.literature_search import run_literature_search
from mindbrew_v2.phases.intake import run_intake
from mindbrew_v2.phases.literature_plan import build_literature_plan
from mindbrew_v2.phases.report import generate_report
from mindbrew_v2.tools.fba_client import rank_fba_results, score_pathway


def _needs_fba_pipeline(assertions: list[dict]) -> bool:
    return any(a.get("type") in ("fba_full_pipeline", "fba_verdict_in") for a in assertions)


def _run_fba_pipeline(brief, candidates) -> tuple[list, list | None]:
    result = formalize_pathways(brief, candidates)
    if not result.payloads:
        return [], None
    fba_results = [score_pathway(p) for p in result.payloads]
    return fba_results, rank_fba_results(fba_results)


def score_e2e(case: EvalCase) -> EvalResult:
    failures = []
    raw = case.input.get("raw_brief", "")
    ticket = Ticket(id=case.id, raw_brief=raw)
    brief = run_intake(ticket)
    selection = provisional_validation_mode(brief)
    candidates = run_literature_search(brief)[0]
    candidate_dicts = [c.model_dump() for c in candidates]

    fba_results: list[FBAValidationResult] | None = None
    ranked_fba: list[FBAValidationResult] | None = None
    formalize_result = None

    for assertion in case.assertions:
        atype = assertion.get("type")
        if atype == "validation_mode_in":
            if selection.validation_mode.value not in assertion.get("values", []):
                failures.append(f"mode: {selection.validation_mode}")
        elif atype == "pathways_not_empty":
            if not candidates:
                failures.append("no pathway candidates")
        elif atype == "candidate_count_min":
            minimum = assertion.get("value", 1)
            if len(candidates) < minimum:
                failures.append(f"candidate_count_min: {len(candidates)} < {minimum}")
        elif atype == "lit_plan_has_genes":
            if not candidates:
                failures.append("no candidates for lit plan")
                continue
            plan = build_literature_plan(brief, candidates[0])
            if not plan.gene_suggestions:
                failures.append("literature plan missing gene suggestions")
        elif atype == "gold_brief_fields":
            brief_ref = resolve_gold_ref(case.gold, assertion, "brief_ref")
            if not brief_ref:
                failures.append("gold_brief_fields: missing brief_ref")
            else:
                failures.extend(check_gold_brief_fields(brief, brief_ref))
        elif atype == "gold_pathway_enzymes":
            pathways_ref = resolve_gold_ref(case.gold, assertion, "pathways_ref")
            failures.extend(
                check_gold_pathway_enzymes(
                    candidate_dicts,
                    enzymes=assertion.get("values"),
                    gold_pathways_ref=pathways_ref,
                )
            )
        elif atype in ("fba_full_pipeline", "fba_verdict_in"):
            if selection.validation_mode != ValidationMode.FBA:
                failures.append(f"expected FBA mode, got {selection.validation_mode}")
                continue
            if ranked_fba is None:
                fba_results, ranked_fba = _run_fba_pipeline(brief, candidates)
                if formalize_result is None:
                    formalize_result = formalize_pathways(brief, candidates)
                if not ranked_fba:
                    failures.append(f"no FBA results; skipped={formalize_result.skipped if formalize_result else []}")
                    continue
            top = ranked_fba[0]
            expected = assertion.get("values") or assertion.get("verdict_values") or ["pass", "marginal"]
            if atype == "fba_full_pipeline" and top.status != assertion.get("status", "optimal"):
                failures.append(f"fba status: {top.status} != {assertion.get('status', 'optimal')}")
            if top.verdict not in expected:
                failures.append(f"fba verdict: {top.verdict} not in {expected}")
        elif atype == "report_has_sections":
            if ranked_fba is None and _needs_fba_pipeline(case.assertions):
                if selection.validation_mode == ValidationMode.FBA:
                    fba_results, ranked_fba = _run_fba_pipeline(brief, candidates)
                    formalize_result = formalize_pathways(brief, candidates)
            report = generate_report(
                brief,
                selection.validation_mode,
                candidates,
                candidates[0].id if candidates else None,
                fba_results=ranked_fba or fba_results,
                score_payloads=formalize_result.payloads if formalize_result else None,
            )
            md = report.markdown.lower()
            for section in assertion.get("values", []):
                if section.replace("_", " ") not in md and section not in md:
                    failures.append(f"report missing section: {section}")

    return EvalResult(case.id, case.phase, len(failures) == 0, failures, case.weight)
