"""Build human-readable FBA calculation steps from score_pathway output."""

from __future__ import annotations

from typing import Any

from mindbrew_v2.models import CalculationStep


def _fmt(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.4g}"
    return str(value)


def _format_bounds(bounds: Any) -> str:
    if isinstance(bounds, (list, tuple)) and len(bounds) >= 2:
        return f"[{_fmt(bounds[0])}, {_fmt(bounds[1])}]"
    return _fmt(bounds)


def _exchange_summary(
    exchanges: Any,
    bounds_lookup: dict[str, Any] | None = None,
) -> str:
    if not exchanges:
        return "default model medium"

    if isinstance(exchanges, dict) and (
        "exchange_bounds_set" in exchanges or "exchange_not_found" in exchanges
    ):
        applied = exchanges.get("exchange_bounds_set") or []
        missing = exchanges.get("exchange_not_found") or []
        lookup = bounds_lookup or {}
        parts: list[str] = []
        for rxn in applied[:6]:
            bounds = lookup.get(rxn)
            if bounds is not None:
                parts.append(f"{rxn}: {_format_bounds(bounds)}")
            else:
                parts.append(rxn)
        if len(applied) > 6:
            parts.append(f"+{len(applied) - 6} more")
        if missing:
            parts.append(f"not found: {', '.join(missing[:4])}")
        return "; ".join(parts) if parts else "default model medium"

    if isinstance(exchanges, dict):
        parts = [
            f"{rxn}: {_format_bounds(bounds)}"
            for rxn, bounds in list(exchanges.items())[:6]
        ]
        if len(exchanges) > 6:
            parts.append(f"+{len(exchanges) - 6} more")
        return "; ".join(parts)

    return "default model medium"


def build_calculation_steps(raw: dict[str, Any]) -> list[CalculationStep]:
    """Turn raw FBA tool output into ordered calculation steps for the UI."""
    steps: list[CalculationStep] = []
    ctx = raw.get("simulation_context") or {}
    edits = raw.get("edits_applied") or {}
    carbon = raw.get("carbon_audit") or {}
    calibration = raw.get("calibration") or {}
    growth = ctx.get("growth_constraints") or {}

    step_no = 1

    scenario_bits: list[str] = []
    if ctx.get("use_minimal_medium"):
        scenario_bits.append("minimal medium (non-feedstock exchanges closed)")
    if ctx.get("carbon_source_rxn"):
        uptake = ctx.get("carbon_source_uptake")
        scenario_bits.append(
            f"carbon source {ctx['carbon_source_rxn']} "
            f"(uptake ≤ {_fmt(uptake)} mmol/gDW/h)"
        )
    if ctx.get("biomass_rxn"):
        scenario_bits.append(f"biomass reaction {ctx['biomass_rxn']}")
    if ctx.get("substrate_moles_per_product") not in (None, 1, 1.0):
        scenario_bits.append(
            f"substrate moles per product: {_fmt(ctx['substrate_moles_per_product'])}"
        )
    notes = ctx.get("simulation_notes") or []
    if notes:
        scenario_bits.append("notes: " + "; ".join(str(n) for n in notes[:3]))

    steps.append(
        CalculationStep(
            step=step_no,
            title="Configure simulation scenario",
            detail=" · ".join(scenario_bits) if scenario_bits else "Model default medium and growth settings",
        )
    )
    step_no += 1

    exchange_applied = ctx.get("exchange_constraints_applied")
    steps.append(
        CalculationStep(
            step=step_no,
            title="Apply exchange constraints",
            detail=_exchange_summary(exchange_applied, ctx.get("exchange_constraints")),
        )
    )
    step_no += 1

    inserted = raw.get("inserted_reactions") or []
    if inserted:
        steps.append(
            CalculationStep(
                step=step_no,
                title="Insert heterologous reactions",
                detail=", ".join(inserted),
            )
        )
        step_no += 1

    edit_bits: list[str] = []
    knocked = edits.get("knocked_out") or edits.get("knockouts") or []
    if knocked:
        edit_bits.append(f"knockouts: {', '.join(knocked)}")
    overrides = edits.get("bound_overrides") or {}
    if overrides:
        override_parts = [
            f"{rxn} {_format_bounds(b)}" for rxn, b in list(overrides.items())[:5]
        ]
        edit_bits.append("bound overrides: " + "; ".join(override_parts))
    not_found = edits.get("not_found") or []
    if not_found:
        edit_bits.append(f"not found in model: {', '.join(not_found)}")
    if edit_bits:
        steps.append(
            CalculationStep(
                step=step_no,
                title="Apply strain edits",
                detail=" · ".join(edit_bits),
            )
        )
        step_no += 1

    growth_bits: list[str] = []
    if growth.get("max_growth_unconstrained") is not None:
        growth_bits.append(f"unconstrained μ_max = {_fmt(growth['max_growth_unconstrained'])} h⁻¹")
    if growth.get("min_growth_applied") is not None:
        growth_bits.append(f"μ floor = {_fmt(growth['min_growth_applied'])} h⁻¹")
    if growth.get("max_growth_applied") is not None:
        growth_bits.append(f"μ cap = {_fmt(growth['max_growth_applied'])} h⁻¹")
    steps.append(
        CalculationStep(
            step=step_no,
            title="Pin growth constraints",
            detail=" · ".join(growth_bits) if growth_bits else "No explicit growth floor/cap applied",
        )
    )
    step_no += 1

    objective = raw.get("objective_used", "product")
    steps.append(
        CalculationStep(
            step=step_no,
            title="Set optimization objective",
            detail=f"Maximize {objective} flux under growth constraints",
        )
    )
    step_no += 1

    status = raw.get("status", "unknown")
    steps.append(
        CalculationStep(
            step=step_no,
            title="Solve flux balance analysis",
            detail=f"Solver status: {status}",
        )
    )
    step_no += 1

    if status == "optimal":
        flux_bits = [
            f"product flux = {_fmt(raw.get('predicted_product_flux'))} mmol/gDW/h",
            f"growth rate = {_fmt(raw.get('growth_rate'))} h⁻¹",
        ]
        steps.append(
            CalculationStep(
                step=step_no,
                title="Read optimal fluxes",
                detail=" · ".join(flux_bits),
            )
        )
        step_no += 1

        raw_yield = raw.get("yield_mol_per_mol_substrate")
        corrected = raw.get("yield_corrected_mol_per_mol_substrate")
        if raw_yield is not None or corrected is not None:
            yield_bits = []
            if raw_yield is not None:
                yield_bits.append(f"raw yield = {_fmt(raw_yield)} mol product / mol substrate")
            if corrected is not None:
                denom = ctx.get("substrate_moles_per_product") or 1.0
                yield_bits.append(
                    f"corrected yield = {_fmt(corrected)} mol/mol "
                    f"(÷ {_fmt(denom)} substrate equivalents per product)"
                )
            steps.append(
                CalculationStep(
                    step=step_no,
                    title="Calculate molar yield",
                    detail=" · ".join(yield_bits),
                )
            )
            step_no += 1

    if carbon:
        sole = carbon.get("feedstock_is_sole_carbon_source")
        audit_bits = [
            f"feedstock is sole carbon source: {sole}",
            f"total carbon import = {_fmt(carbon.get('total_carbon_import_mmol_per_h'))} mmol C/gDW/h",
        ]
        side_doors = carbon.get("side_door_carbon_imports") or []
        if side_doors:
            ids = ", ".join(e.get("exchange", "?") for e in side_doors[:4])
            audit_bits.append(f"side-door imports: {ids}")
        for warning in carbon.get("warnings") or []:
            audit_bits.append(str(warning))
        steps.append(
            CalculationStep(
                step=step_no,
                title="Audit boundary carbon balance",
                detail=" · ".join(audit_bits),
            )
        )
        step_no += 1

    bottlenecks = raw.get("bottlenecks") or []
    if bottlenecks:
        lines = []
        for bn in bottlenecks[:5]:
            if not isinstance(bn, dict):
                continue
            rxn = bn.get("reaction", "?")
            flux = _fmt(bn.get("flux"))
            span = bn.get("span")
            at_bound = bn.get("at_bound")
            extra = f", FVA span {_fmt(span)}" if span is not None else ""
            bound = " (at bound)" if at_bound else ""
            lines.append(f"{rxn}: flux {flux}{extra}{bound}")
        steps.append(
            CalculationStep(
                step=step_no,
                title="Identify flux bottlenecks",
                detail=" · ".join(lines),
            )
        )
        step_no += 1

    cal_bits = []
    if calibration.get("confidence_level"):
        cal_bits.append(f"tier: {calibration['confidence_level']}")
    if calibration.get("product_confidence_level"):
        cal_bits.append(f"product calibration: {calibration['product_confidence_level']}")
    missing = calibration.get("missing_literature_inputs") or []
    if missing:
        cal_bits.append(f"missing inputs: {', '.join(missing)}")
    if calibration.get("recommended_use"):
        cal_bits.append(str(calibration["recommended_use"]))
    steps.append(
        CalculationStep(
            step=step_no,
            title="Assess calibration confidence",
            detail=" · ".join(cal_bits) if cal_bits else "Default exploratory calibration",
        )
    )

    message = (raw.get("message") or "").strip()
    if message and message != "OK":
        steps.append(
            CalculationStep(
                step=step_no + 1,
                title="Solver notes",
                detail=message.replace("[warn] ", "").strip(),
            )
        )

    return steps
