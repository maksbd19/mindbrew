"""FBA client — find_ids + score_pathway via integrated mindbrew_v2.fba package."""

from __future__ import annotations

from typing import Any

from mindbrew_v2.fba.find_ids import build_report
from mindbrew_v2.fba.scoring import score_pathway as _score_pathway
from mindbrew_v2.paths import display_path
from mindbrew_v2.models import (
    Bottleneck,
    Citation,
    FBAValidationResult,
    GemProfile,
    ScorePathwayPayload,
)
from mindbrew_v2.settings import is_offline
from mindbrew_v2.tools.citation_resolver import resolve_citations
from mindbrew_v2.tools.confidence import build_calibration_rationale, build_verdict_rationale
from mindbrew_v2.tools.fba_calculation_steps import build_calculation_steps


def run_find_ids(model_ref: str, extra_terms: list[str] | None = None) -> dict[str, Any]:
    if is_offline():
        return _offline_find_ids(extra_terms=extra_terms or [])

    import time

    from mindbrew_v2.progress import log, tool_end, tool_start
    from mindbrew_v2.telemetry import start_span

    tool_id = "fba.find_ids"
    label = f"FBA find_ids ({display_path(model_ref)})"
    tool_start(tool_id, label)
    started = time.perf_counter()

    with start_span("tool.call", {"tool_id": tool_id, "model_ref": model_ref}):
        try:
            report = build_report(model_ref, extra_terms or [])
            duration_ms = int((time.perf_counter() - started) * 1000)
            if report.get("status") == "ok":
                tool_end(tool_id, label, duration_ms=duration_ms, status="ok")
                log(f"FBA find_ids finished in {duration_ms / 1000:.1f}s")
                return report
            message = report.get("message", report)
            tool_end(tool_id, label, duration_ms=duration_ms, status="error")
            log(f"FBA find_ids preflight failed: {message}", level="error")
            raise RuntimeError(f"FBA find_ids preflight failed for {display_path(model_ref)}: {message}")
        except Exception as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            tool_end(tool_id, label, duration_ms=duration_ms, status="error")
            log(f"FBA find_ids error: {exc}", level="error")
            raise RuntimeError(f"FBA find_ids failed for {display_path(model_ref)}") from exc


def run_biomass_validation(gem: GemProfile) -> dict[str, Any]:
    if is_offline():
        return {
            "status": "optimal",
            "growth_rate": 0.24,
            "objective_used": "biomass",
            "message": "Offline biomass validation stub",
        }

    if not gem.biomass_validation_scenario:
        return {"status": "skipped", "message": "No biomass validation scenario configured"}

    import time

    from mindbrew_v2.progress import log, tool_end, tool_start
    from mindbrew_v2.telemetry import start_span

    tool_id = "fba.biomass_validation"
    label = f"Biomass validation ({gem.gem_id})"
    tool_start(tool_id, label)
    started = time.perf_counter()

    with start_span("tool.call", {"tool_id": tool_id, "gem_id": gem.gem_id}):
        try:
            data = _score_pathway(
                gem.model_ref,
                scenario=gem.biomass_validation_scenario,
                objective="biomass",
            )
            duration_ms = int((time.perf_counter() - started) * 1000)
            tool_end(tool_id, label, duration_ms=duration_ms, status="ok")
            log(
                f"Biomass validation ({gem.gem_id}, {data.get('status')}) "
                f"finished in {duration_ms / 1000:.1f}s"
            )
            return data
        except Exception as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            tool_end(tool_id, label, duration_ms=duration_ms, status="error")
            log(f"Biomass validation error: {exc}", level="error")
            return {"status": "error", "message": str(exc)}


def score_pathway(payload: ScorePathwayPayload) -> FBAValidationResult:
    if is_offline():
        return _offline_score(payload)

    import time

    from mindbrew_v2.progress import log, tool_end, tool_start
    from mindbrew_v2.telemetry import start_span

    tool_id = "fba.score_pathway"
    label = f"FBA score_pathway ({payload.pathway_id})"
    tool_start(tool_id, label)
    started = time.perf_counter()

    with start_span("tool.call", {"tool_id": tool_id, "pathway_id": payload.pathway_id}):
        try:
            data = _score_pathway(**_payload_to_fba_dict(payload))
            parsed = _parse_fba_result(payload.pathway_id, data)
            duration_ms = int((time.perf_counter() - started) * 1000)
            tool_end(tool_id, label, duration_ms=duration_ms, status="ok")
            log(
                f"FBA score_pathway ({payload.pathway_id}, {parsed.status}) "
                f"finished in {duration_ms / 1000:.1f}s"
            )
            return parsed
        except Exception as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            tool_end(tool_id, label, duration_ms=duration_ms, status="error")
            log(f"FBA score_pathway error for {payload.pathway_id}: {exc}", level="error")
            raise RuntimeError(f"FBA score_pathway failed for {payload.pathway_id}") from exc


def rank_fba_results(results: list[FBAValidationResult]) -> list[FBAValidationResult]:
    optimal = [r for r in results if r.status == "optimal"]
    optimal.sort(
        key=lambda r: r.yield_corrected_mol_per_mol_substrate or 0,
        reverse=True,
    )
    for i, r in enumerate(optimal, start=1):
        r.rank = i
    non_optimal = [r for r in results if r.status != "optimal"]
    for r in non_optimal:
        r.rank = None
    return optimal + non_optimal


def interpret_failures(result: FBAValidationResult, raw: dict | None = None) -> FBAValidationResult:
    reasons: list[str] = []
    raw = raw or {}

    for bn in result.bottlenecks:
        if "ACOAO" in bn.reaction.upper():
            bn.explanation = "β-oxidation draining acyl-CoA pool"
            reasons.append(bn.explanation)
        elif any(x in bn.reaction.upper() for x in ("DGA1", "LRO1", "TAG")):
            bn.explanation = "Carbon diverted to storage lipids"
            reasons.append(bn.explanation)
        elif bn.at_bound:
            bn.explanation = f"Flux at bound ({bn.flux:.2f})"

    carbon_audit = raw.get("carbon_audit", {})
    if carbon_audit.get("feedstock_is_sole_carbon_source") is False:
        reasons.append("Glucose side-door open — yield vs feedstock untrustworthy")

    calibration = raw.get("calibration", {})
    confidence = calibration.get("confidence_level", result.calibration_level)
    if confidence in ("exploratory", "invalid"):
        reasons.append(f"Calibration tier {confidence} — relative ranking only")

    if calibration.get("confidence_level") == "invalid":
        reasons.append("Infeasible design — check medium constraints")

    edits = raw.get("edits_applied", {})
    not_found = edits.get("not_found", [])
    if not_found:
        reasons.append(f"Knockout IDs not found: {not_found}")

    result.failure_reasons = reasons
    result.edits_not_found = list(not_found)

    can_pass = (
        result.status == "optimal"
        and confidence not in ("exploratory", "invalid")
        and carbon_audit.get("feedstock_is_sole_carbon_source") is not False
        and not not_found
    )

    if can_pass and result.yield_corrected_mol_per_mol_substrate:
        y = result.yield_corrected_mol_per_mol_substrate
        if y >= 0.5 and not reasons:
            result.verdict = "pass"
        elif y >= 0.2:
            result.verdict = "marginal"
        else:
            result.verdict = "marginal"
    elif result.status == "optimal":
        result.verdict = "marginal"
    else:
        result.verdict = "fail"

    cal_rationale, cal_warnings = build_calibration_rationale(raw)
    result.calibration_rationale = cal_rationale
    result.calibration_warnings = cal_warnings
    result.verdict_rationale = build_verdict_rationale(result)

    return result


def _reaction_spec(reaction) -> dict[str, Any]:
    data = reaction.model_dump()
    bounds = data.pop("bounds", (0.0, 1000.0))
    data.pop("gene_associations", None)
    data["lower_bound"] = bounds[0]
    data["upper_bound"] = bounds[1]
    return data


def _payload_to_fba_dict(payload: ScorePathwayPayload) -> dict[str, Any]:
    return {
        "model_ref": payload.model_ref,
        "scenario": payload.scenario,
        "carbon_source_rxn": payload.carbon_source_rxn,
        "candidate_reactions": [_reaction_spec(r) for r in payload.candidate_reactions],
        "product_metabolite": payload.product_metabolite,
        "knockouts": payload.knockouts,
        "substrate_moles_per_product": payload.substrate_moles_per_product,
        "objective": payload.objective,
    }


def _parse_fba_result(pathway_id: str, data: dict) -> FBAValidationResult:
    bottlenecks = [
        Bottleneck(
            reaction=b.get("reaction", ""),
            flux=float(b.get("flux", 0)),
            at_bound=bool(b.get("at_bound", False)),
            explanation=b.get("explanation", ""),
            min_flux=float(b["min"]) if b.get("min") is not None else None,
            max_flux=float(b["max"]) if b.get("max") is not None else None,
            flux_span=float(b["span"]) if b.get("span") is not None else None,
        )
        for b in data.get("bottlenecks", [])
    ]
    calibration = data.get("calibration", {})
    carbon = data.get("carbon_audit", {}) or {}
    ctx = data.get("simulation_context") or {}

    lit_refs = _parse_literature_refs(calibration)

    result = FBAValidationResult(
        pathway_id=pathway_id,
        status=data.get("status", "unknown"),
        objective_used=data.get("objective_used", ""),
        predicted_product_flux=data.get("predicted_product_flux"),
        growth_rate=data.get("growth_rate"),
        yield_mol_per_mol_substrate=data.get("yield_mol_per_mol_substrate"),
        yield_corrected_mol_per_mol_substrate=data.get("yield_corrected_mol_per_mol_substrate"),
        calculation_steps=build_calculation_steps(data),
        simulation_context=ctx,
        inserted_reactions=list(data.get("inserted_reactions") or []),
        edits_applied=dict(data.get("edits_applied") or {}),
        solver_message=(data.get("message") or "").strip(),
        bottlenecks=bottlenecks,
        calibration_level=calibration.get("confidence_level", "exploratory"),
        product_confidence_level=calibration.get("product_confidence_level", ""),
        carbon_audit_sole_source=carbon.get("feedstock_is_sole_carbon_source"),
        carbon_audit=carbon,
        literature_refs=lit_refs,
    )
    return interpret_failures(result, data)


def _parse_literature_refs(calibration: dict) -> list[Citation]:
    raw_refs = calibration.get("literature_refs") or calibration.get("product_literature_refs") or []
    citations: list[Citation] = []
    for ref in raw_refs:
        if isinstance(ref, str):
            if ref.startswith("10."):
                citations.append(Citation(doi=ref))
            elif ref.isdigit():
                citations.append(Citation(pmid=ref))
        elif isinstance(ref, dict):
            citations.append(
                Citation(
                    doi=ref.get("doi"),
                    pmid=str(ref.get("pmid")) if ref.get("pmid") else None,
                    title=ref.get("title", ""),
                )
            )
    return resolve_citations(citations)


def _offline_find_ids(extra_terms: list[str] | None = None) -> dict[str, Any]:
    extra_terms = extra_terms or []
    searches: dict[str, list[dict[str, str]]] = {
        "wax": [{"id": "wax_ester_c", "name": "wax ester", "compartment": "c"}],
        "ester": [{"id": "wax_ester_c", "name": "wax ester", "compartment": "c"}],
        "alcohol": [{"id": "oleyl_alcohol_c", "name": "oleyl alcohol", "compartment": "c"}],
        "oleate": [{"id": "ocdcea_e", "name": "oleate", "compartment": "e"}],
        "oleic": [{"id": "odecoa_c", "name": "oleoyl-CoA", "compartment": "c"}],
        "octadec": [{"id": "odecoa_c", "name": "octadecenoyl-CoA", "compartment": "c"}],
    }
    for term in extra_terms:
        key = term.lower()
        if key not in searches and "wax" in key:
            searches[key] = [{"id": "wax_ester_c", "name": term, "compartment": "c"}]
        elif key not in searches and "alcohol" in key:
            searches[key] = [{"id": "oleyl_alcohol_c", "name": term, "compartment": "c"}]

    return {
        "status": "ok",
        "recommended": {
            "carbon_source_rxn": "EX_ocdcea_LPAREN_e_RPAREN_",
            "oleoyl_coa_metabolite": "odecoa_c",
            "nadph_metabolite": "nadph_c",
            "nadp_metabolite": "nadp_c",
            "coa_metabolite": "coa_c",
        },
        "peroxisomal_acyl_coa_oxidases": [
            {"id": "ACOAO8p", "name": "octadecenoyl-CoA oxidase (peroxisomal)"},
            {"id": "ACOAO4p", "name": "acyl-CoA oxidase (peroxisomal)"},
        ],
        "gene_alias_resolution": {
            "POX1": [{"type": "reaction", "id": "ACOAO8p"}],
            "DGA1": [{"type": "reaction", "id": "DGA1"}],
        },
        "summary": {"has_gene_associations": True},
        "searches": {"metabolites": searches},
    }


def _offline_score(payload: ScorePathwayPayload) -> FBAValidationResult:
    has_ko = bool(payload.knockouts)
    if has_ko:
        data = {
            "status": "optimal",
            "objective_used": "product",
            "predicted_product_flux": 0.42,
            "growth_rate": 0.01,
            "yield_mol_per_mol_substrate": 0.65,
            "yield_corrected_mol_per_mol_substrate": 0.65,
            "simulation_context": {
                "carbon_source_rxn": payload.carbon_source_rxn,
                "carbon_source_uptake": 10.0,
                "biomass_rxn": "BIOMASS",
                "use_minimal_medium": True,
                "substrate_moles_per_product": payload.substrate_moles_per_product,
                "growth_constraints": {
                    "max_growth_unconstrained": 0.35,
                    "min_growth_applied": 0.01,
                    "max_growth_applied": 0.1,
                },
            },
            "inserted_reactions": [r.id for r in payload.candidate_reactions],
            "bottlenecks": [{"reaction": "TAG_synthesis", "flux": 0.1, "span": 0.0, "at_bound": False}],
            "calibration": {
                "confidence_level": "partial",
                "product_confidence_level": "unvalidated",
                "recommended_use": "Rank designs relative to each other; bottlenecks informative",
                "missing_literature_inputs": ["product exchange bound"],
            },
            "carbon_audit": {
                "feedstock_is_sole_carbon_source": True,
                "total_carbon_import_mmol_per_h": 12.4,
            },
            "edits_applied": {"knocked_out": payload.knockouts, "not_found": []},
        }
    else:
        data = {
            "status": "optimal",
            "objective_used": "product",
            "predicted_product_flux": 0.08,
            "growth_rate": 0.01,
            "yield_mol_per_mol_substrate": 0.12,
            "yield_corrected_mol_per_mol_substrate": 0.12,
            "simulation_context": {
                "carbon_source_rxn": payload.carbon_source_rxn,
                "carbon_source_uptake": 10.0,
                "biomass_rxn": "BIOMASS",
                "growth_constraints": {"min_growth_applied": 0.01},
            },
            "inserted_reactions": [r.id for r in payload.candidate_reactions],
            "bottlenecks": [
                {"reaction": "ACOAO8p", "flux": 2.5, "span": 0.0, "at_bound": True},
                {"reaction": "DGA1", "flux": 1.2, "span": 0.4, "at_bound": False},
            ],
            "calibration": {
                "confidence_level": "exploratory",
                "product_confidence_level": "unvalidated",
                "recommended_use": "Exploratory ranking only — medium not fully calibrated",
                "warnings": ["β-oxidation not knocked out"],
            },
            "carbon_audit": {"feedstock_is_sole_carbon_source": True},
            "edits_applied": {"not_found": []},
        }
    return _parse_fba_result(payload.pathway_id, data)
