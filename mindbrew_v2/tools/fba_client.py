"""FBA_Analysis client — find_ids + score_pathway via direct import."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from mindbrew_v2.models import (
    Bottleneck,
    Citation,
    FBAValidationResult,
    ScorePathwayPayload,
)
from mindbrew_v2.settings import is_offline
from mindbrew_v2.tools.citation_resolver import resolve_citations
from mindbrew_v2.tools.confidence import build_calibration_rationale, build_verdict_rationale

VENDOR_ROOT = Path(__file__).resolve().parents[2] / "vendor" / "FBA_Analysis"


def _is_vendor_stub() -> bool:
    find_ids_path = VENDOR_ROOT / "find_ids.py"
    if not find_ids_path.exists():
        return True
    return "Offline find_ids stub" in find_ids_path.read_text()


def _fba_imports() -> tuple[Any, Any]:
    if _is_vendor_stub():
        raise ImportError(
            "vendor/FBA_Analysis contains offline stubs. "
            "Run: git submodule update --init vendor/FBA_Analysis"
        )
    vendor = str(VENDOR_ROOT)
    if vendor not in sys.path:
        sys.path.insert(0, vendor)
    from find_ids import build_report
    from fba_tool import score_pathway as sp

    return build_report, sp


def run_find_ids(model_ref: str) -> dict[str, Any]:
    if is_offline():
        return _offline_find_ids()

    import time

    from mindbrew_v2.progress import log, log_timing

    log(f"FBA find_ids running for {model_ref}…")
    started = time.perf_counter()

    try:
        build_report, _ = _fba_imports()
        report = build_report(model_ref, [])
        if report.get("status") == "ok":
            log_timing(f"FBA find_ids ({model_ref})", time.perf_counter() - started)
            return report
        message = report.get("message", report)
        log(f"FBA find_ids preflight failed: {message}", level="error")
        raise RuntimeError(f"FBA find_ids preflight failed for {model_ref}: {message}")
    except ImportError as exc:
        log(str(exc), level="error")
        raise
    except Exception as exc:
        log(f"FBA find_ids error: {exc}", level="error")
        raise RuntimeError(f"FBA find_ids failed for {model_ref}") from exc


def score_pathway(payload: ScorePathwayPayload) -> FBAValidationResult:
    if is_offline():
        return _offline_score(payload)

    import time

    from mindbrew_v2.progress import log, log_timing

    log(f"FBA score_pathway running for {payload.pathway_id}…")
    started = time.perf_counter()

    try:
        _, sp = _fba_imports()
        data = sp(**_payload_to_fba_dict(payload))
        parsed = _parse_fba_result(payload.pathway_id, data)
        log_timing(
            f"FBA score_pathway ({payload.pathway_id}, {parsed.status})",
            time.perf_counter() - started,
        )
        return parsed
    except ImportError as exc:
        log(str(exc), level="error")
        raise
    except Exception as exc:
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
    if calibration.get("confidence_level") == "invalid":
        reasons.append("Infeasible design — check medium constraints")

    edits = raw.get("edits_applied", {})
    not_found = edits.get("not_found", [])
    if not_found:
        reasons.append(f"Knockout IDs not found: {not_found}")

    result.failure_reasons = reasons

    if result.status == "optimal" and result.yield_corrected_mol_per_mol_substrate:
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


def _payload_to_fba_dict(payload: ScorePathwayPayload) -> dict[str, Any]:
    return {
        "model_ref": payload.model_ref,
        "scenario": payload.scenario,
        "carbon_source_rxn": payload.carbon_source_rxn,
        "candidate_reactions": [r.model_dump() for r in payload.candidate_reactions],
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
        )
        for b in data.get("bottlenecks", [])
    ]
    calibration = data.get("calibration", {})
    carbon = data.get("carbon_audit", {})

    lit_refs = _parse_literature_refs(calibration)

    result = FBAValidationResult(
        pathway_id=pathway_id,
        status=data.get("status", "unknown"),
        predicted_product_flux=data.get("predicted_product_flux"),
        yield_corrected_mol_per_mol_substrate=data.get("yield_corrected_mol_per_mol_substrate"),
        bottlenecks=bottlenecks,
        calibration_level=calibration.get("confidence_level", "exploratory"),
        carbon_audit_sole_source=carbon.get("feedstock_is_sole_carbon_source"),
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


def _offline_find_ids() -> dict[str, Any]:
    return {
        "status": "ok",
        "recommended": {
            "carbon_source_rxn": "EX_ole_e",
            "oleoyl_coa_metabolite": "odecoa_c",
            "nadph_metabolite": "nadph_c",
            "nadp_metabolite": "nadp_c",
            "coa_metabolite": "coa_c",
        },
        "peroxisomal_acyl_coa_oxidases": [
            {"id": "ACOAO8p", "name": "octadecenoyl-CoA oxidase (peroxisomal)"},
            {"id": "ACOAO4p", "name": "acyl-CoA oxidase (peroxisomal)"},
        ],
        "gene_alias_resolution": {},
    }


def _offline_score(payload: ScorePathwayPayload) -> FBAValidationResult:
    has_ko = bool(payload.knockouts)
    if has_ko:
        data = {
            "status": "optimal",
            "predicted_product_flux": 0.42,
            "yield_corrected_mol_per_mol_substrate": 0.65,
            "bottlenecks": [{"reaction": "TAG_synthesis", "flux": 0.1, "at_bound": False}],
            "calibration": {
                "confidence_level": "partial",
                "recommended_use": "Rank designs relative to each other; bottlenecks informative",
                "missing_literature_inputs": ["product exchange bound"],
            },
            "carbon_audit": {"feedstock_is_sole_carbon_source": True},
        }
    else:
        data = {
            "status": "optimal",
            "predicted_product_flux": 0.08,
            "yield_corrected_mol_per_mol_substrate": 0.12,
            "bottlenecks": [
                {"reaction": "ACOAO8p", "flux": 2.5, "at_bound": True},
                {"reaction": "DGA1", "flux": 1.2, "at_bound": False},
            ],
            "calibration": {
                "confidence_level": "exploratory",
                "recommended_use": "Exploratory ranking only — medium not fully calibrated",
                "warnings": ["β-oxidation not knocked out"],
            },
            "carbon_audit": {"feedstock_is_sole_carbon_source": True},
        }
    return _parse_fba_result(payload.pathway_id, data)
