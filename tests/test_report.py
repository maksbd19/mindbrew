"""Tests for report section formatting."""

from mindbrew_v2.models import (
    CompoundSpec,
    FBAValidationResult,
    GeneSuggestion,
    LiteraturePathwayPlan,
    PathwayCandidate,
    ReactionStep,
    ResearchBrief,
    ScorePathwayPayload,
    ValidationMode,
)
from mindbrew_v2.phases.report import (
    _build_feedstock_scaffold,
    _build_fba_data_markdown,
    _build_fba_plan_scaffold,
    _build_genetic_scaffold,
    _build_pathway_analysis_markdown,
    _build_pathways_scaffold,
    _build_performance_scaffold,
    _build_production_scaffold,
    _build_risk_scaffold,
    _build_target_scaffold,
    _build_validation_scaffold,
    _report_title,
)


def test_report_title_uses_session_title():
    assert _report_title("Wax Ester Pathway") == "Wax Ester Pathway"
    assert _report_title("  My Title  ") == "My Title"
    assert _report_title(None) == "R&D Proposal to CRO"
    assert _report_title("") == "R&D Proposal to CRO"


def test_build_target_scaffold():
    brief = ResearchBrief(
        ticket_id="t1",
        raw_brief="raw",
        target_function="Silicone replacement",
        target=CompoundSpec(name="wax ester", compound_class="lipid"),
        constraints=["Natural only"],
    )
    md = _build_target_scaffold(brief)
    assert "wax ester / lipid" in md
    assert "Silicone replacement" in md
    assert "Natural only" in md


def test_build_feedstock_scaffold():
    brief = ResearchBrief(
        ticket_id="t1",
        raw_brief="raw",
        feedstock=CompoundSpec(name="oleic acid", compound_class="fatty acid", kegg_id="C01832"),
    )
    md = _build_feedstock_scaffold(brief)
    assert "oleic acid / fatty acid (C01832)" in md


def test_build_production_scaffold():
    brief = ResearchBrief(
        ticket_id="t1",
        raw_brief="raw",
        organism=["Yarrowia lipolytica"],
    )
    primary = PathwayCandidate(
        id="pw1",
        name="FAR + WS",
        description="Wax ester pathway",
        reaction_steps=[
            ReactionStep(
                step_number=1,
                description="Fatty acyl-CoA → fatty alcohol",
                enzyme_name="FAR",
                gene_names=["FAR"],
                heterologous=True,
            ),
        ],
    )
    md = _build_production_scaffold(primary, ValidationMode.FBA, brief, gem_profile={"gem_id": "iYLI647"})
    assert "FBA-validated whole-cell fermentation" in md
    assert "Yarrowia lipolytica" in md
    assert "FAR + WS" in md
    assert "FAR (heterologous)" in md
    assert "iYLI647" in md


def test_build_genetic_scaffold_with_literature_and_knockouts():
    lit = LiteraturePathwayPlan(
        pathway_id="pw1",
        pathway_name="FAR + WS",
        gene_suggestions=[
            GeneSuggestion(gene="FAR", action="heterologous", rationale="Fatty acyl reductase"),
            GeneSuggestion(gene="POX1", action="knockout", rationale="Block β-oxidation"),
        ],
    )
    payload = ScorePathwayPayload(
        pathway_id="pw1",
        model_ref="model.xml",
        scenario="default",
        knockouts=["ACOAO8p"],
    )
    md = _build_genetic_scaffold(lit, [], [payload], "pw1")
    assert "heterologous:" in md
    assert "FAR:" in md
    assert "knockout:" in md
    assert "POX1:" in md
    assert "ACOAO8p" in md


def test_build_pathways_scaffold_includes_all_candidates():
    candidates = [
        PathwayCandidate(id="pw1", name="FAR + WS", confidence="strong"),
        PathwayCandidate(id="pw2", name="Direct alcohol", confidence="partial"),
    ]
    md = _build_pathways_scaffold(candidates, "pw1")
    assert "FAR + WS (pw1) [PRIMARY]" in md
    assert "Direct alcohol (pw2)" in md


def test_build_fba_plan_scaffold_includes_all_payloads():
    candidates = [PathwayCandidate(id="pw1", name="FAR + WS")]
    payloads = [
        ScorePathwayPayload(
            pathway_id="pw1",
            model_ref="model.xml",
            scenario="default",
            knockouts=["ACOAO8p"],
            candidate_reactions=[
                {
                    "id": "FAR",
                    "name": "Fatty acyl reductase",
                    "stoichiometry": {"fatty_acyl_coa": -1, "fatty_alcohol": 1},
                    "gene_associations": ["FAR"],
                }
            ],
        )
    ]
    md = _build_fba_plan_scaffold(payloads, candidates, ["pw2: no mapping"])
    assert "FAR + WS (pw1)" in md
    assert "ACOAO8p" in md
    assert "pw2: no mapping" in md


def test_build_pathway_analysis_markdown():
    candidates = [
        PathwayCandidate(id="pw1", name="FAR + WS", description="Wax ester route"),
    ]
    md = _build_pathway_analysis_markdown(candidates, "pw1")
    assert "#### FAR + WS (pw1) [PRIMARY]" in md
    assert "Wax ester route" in md


def test_build_fba_data_markdown():
    candidates = [PathwayCandidate(id="pw1", name="FAR + WS")]
    fba = [
        FBAValidationResult(
            pathway_id="pw1",
            status="optimal",
            yield_corrected_mol_per_mol_substrate=0.8,
            verdict="pass",
            rank=1,
            verdict_rationale="Strong flux to product",
        ),
    ]
    md = _build_fba_data_markdown(None, fba, candidates)
    assert "#### FBA Results" in md
    assert "pass" in md
    assert "Strong flux to product" in md


def test_build_performance_scaffold():
    candidates = [
        PathwayCandidate(id="pw1", name="FAR + WS", reported_titer="7.58 g/L"),
        PathwayCandidate(id="pw2", name="Direct alcohol", reported_titer="2 g/L"),
    ]
    fba = [
        FBAValidationResult(
            pathway_id="pw1",
            status="optimal",
            yield_corrected_mol_per_mol_substrate=0.8,
            verdict="pass",
            rank=1,
        ),
    ]
    md = _build_performance_scaffold(fba, candidates, "pw1")
    assert "7.58 g/L" in md
    assert "2 g/L" in md
    assert "verdict: pass" not in md  # detailed scaffold uses "Verdict: pass"
    assert "Verdict: pass" in md


def test_build_risk_scaffold():
    lit = LiteraturePathwayPlan(
        pathway_id="pw1",
        pathway_name="FAR + WS",
        known_risks=["β-oxidation competition"],
    )
    md = _build_risk_scaffold(None, lit)
    assert "β-oxidation competition" in md


def test_build_validation_scaffold():
    lit = LiteraturePathwayPlan(
        pathway_id="pw1",
        pathway_name="FAR + WS",
        next_steps=["Wet-lab feasibility"],
        gaps=["No flux validation"],
    )
    md = _build_validation_scaffold(lit, ValidationMode.LITERATURE_PATHWAY)
    assert "literature" in md
    assert "Wet-lab feasibility" in md
    assert "No flux validation" in md
