"""Confidence factor computation and methodology text."""

from __future__ import annotations

from mindbrew_v2.models import Citation, FBAValidationResult, PathwayCandidate

PATHWAY_CONFIDENCE_RUBRIC = """
**Pathway confidence rubric**
- **strong**: Direct literature precedent with reported titer in target or closely related host
- **partial**: Pathway known in literature but host, titer, or product match not demonstrated for this case
- **inferred**: Assembled from KEGG/reaction logic without direct product evidence
""".strip()

FBA_VERDICT_METHODOLOGY = """
**FBA verdict thresholds**
- **pass**: Solver status optimal, yield ≥ 0.5 mol product / mol substrate, no failure flags
- **marginal**: Optimal with yield ≥ 0.2, or optimal with unresolved bottlenecks
- **fail**: Non-optimal status or infeasible design

**FBA calibration tiers**
- **exploratory**: ≥3 medium/growth inputs missing — rank designs relative to each other only
- **partial**: 1–2 medium inputs missing — bottlenecks informative; in silico upper bound
- **medium_calibrated**: Medium/growth pinned; no product literature refs
- **literature_calibrated**: Biomass/product fully pinned with literature
- **invalid**: Infeasible or solver error
""".strip()


def compute_confidence_factors(candidate: PathwayCandidate) -> list[str]:
    factors: list[str] = []

    verified = sum(1 for c in candidate.citations if c.validation_status == "verified")
    unverified = sum(1 for c in candidate.citations if c.validation_status == "unverified")
    invalid = sum(1 for c in candidate.citations if c.validation_status == "invalid")

    if verified:
        factors.append(f"{verified} verified citation{'s' if verified != 1 else ''}")
    if unverified:
        factors.append(f"{unverified} unverified citation{'s' if unverified != 1 else ''}")
    if invalid:
        factors.append(f"{invalid} invalid citation{'s' if invalid != 1 else ''}")
    if not candidate.citations:
        factors.append("no citations attached")

    if candidate.reported_titer:
        factors.append("reported titer present")
    else:
        factors.append("no reported titer")

    steps = candidate.reaction_steps
    if steps:
        het = sum(1 for s in steps if s.heterologous)
        factors.append(f"{het}/{len(steps)} steps heterologous")

    if candidate.literature_provenance:
        factors.append(f"provenance: {', '.join(candidate.literature_provenance)}")

    ec_count = sum(1 for s in steps if s.enzyme_ec and "-" not in s.enzyme_ec)
    if ec_count:
        factors.append(f"{ec_count} EC number{'s' if ec_count != 1 else ''} specified")

    return factors


def enrich_pathway_candidate(candidate: PathwayCandidate) -> PathwayCandidate:
    factors = compute_confidence_factors(candidate)
    return candidate.model_copy(update={"confidence_factors": factors})


def build_verdict_rationale(result: FBAValidationResult) -> str:
    parts: list[str] = [result.verdict.capitalize()]
    y = result.yield_corrected_mol_per_mol_substrate
    if y is not None:
        parts.append(f"yield {y:.2f} mol/mol")
        if result.verdict == "pass":
            parts.append("(threshold for pass is ≥0.5)")
        elif result.verdict == "marginal":
            parts.append("(threshold for pass is ≥0.5; marginal at ≥0.2)")
    else:
        parts.append(f"status={result.status}")

    if result.failure_reasons:
        parts.append(f"flags: {'; '.join(result.failure_reasons)}")
    elif result.verdict == "pass":
        parts.append("no failure flags")

    if result.calibration_level:
        parts.append(f"calibration level: {result.calibration_level}")

    return "; ".join(parts)


def build_calibration_rationale(raw: dict) -> tuple[str, list[str]]:
    calibration = raw.get("calibration", {})
    parts: list[str] = []
    warnings: list[str] = []

    level = calibration.get("confidence_level", "")
    if level:
        parts.append(f"Calibration tier: {level}")

    recommended = calibration.get("recommended_use")
    if recommended:
        parts.append(f"Recommended use: {recommended}")

    missing = calibration.get("missing_literature_inputs") or []
    if missing:
        parts.append(f"Missing literature inputs: {', '.join(missing)}")

    for w in calibration.get("warnings") or []:
        warnings.append(str(w))

    agent = calibration.get("agent_guidance")
    if agent:
        parts.append(str(agent))

    return "; ".join(parts), warnings


def collect_all_citations(
    candidates: list[PathwayCandidate],
    literature_plan_citations: list[Citation] | None = None,
    fba_results: list[FBAValidationResult] | None = None,
) -> list[Citation]:
    seen: set[tuple[str | None, str | None]] = set()
    out: list[Citation] = []

    def add(c: Citation) -> None:
        key = (c.doi, c.pmid)
        if key in seen and key != (None, None):
            return
        seen.add(key)
        out.append(c)

    for cand in candidates:
        for c in cand.citations:
            add(c)
    if literature_plan_citations:
        for c in literature_plan_citations:
            add(c)
    if fba_results:
        for r in fba_results:
            for c in r.literature_refs:
                add(c)

    return out


def format_references_markdown(citations: list[Citation]) -> str:
    if not citations:
        return "_No references available._"

    lines: list[str] = []
    for i, c in enumerate(citations, start=1):
        label = c.title or c.doi or c.pmid or "Untitled"
        meta = ", ".join(x for x in [c.authors, c.journal, c.year] if x)
        if c.url:
            lines.append(f"{i}. [{label}]({c.url}){f' — {meta}' if meta else ''}")
        else:
            lines.append(f"{i}. {label}{f' — {meta}' if meta else ''}")
        if c.validation_status != "verified":
            lines.append(f"   _({c.validation_status} — could not verify against Crossref/PubMed)_")
    return "\n".join(lines)


def format_citation_validation_summary(citations: list[Citation]) -> str:
    verified = sum(1 for c in citations if c.validation_status == "verified")
    unverified = sum(1 for c in citations if c.validation_status == "unverified")
    invalid = sum(1 for c in citations if c.validation_status == "invalid")
    return (
        f"- Verified: {verified}\n"
        f"- Unverified: {unverified}\n"
        f"- Invalid: {invalid}"
    )
