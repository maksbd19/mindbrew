from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class TicketStatus(str, Enum):
    DRAFT = "draft"
    RUNNING = "running"
    AWAITING_REVIEW = "awaiting_review"
    COMPLETED = "completed"
    REJECTED = "rejected"


class ValidationMode(str, Enum):
    FBA = "fba"
    LITERATURE_PATHWAY = "literature"


class StepId(str, Enum):
    CP1_SPEC = "cp1_spec"
    CP2_PATHWAYS = "cp2_pathways"
    CP3_FBA_PLAN = "cp3_fba_plan"
    CP3B_LITERATURE_PLAN = "cp3b_literature_plan"
    CP4_FBA_RESULTS = "cp4_fba_results"
    CP5_REPORT = "cp5_report"


CheckpointId = Literal[
    "cp1_spec",
    "cp2_pathways",
    "cp3_fba_plan",
    "cp3b_literature_plan",
    "cp4_fba_results",
    "cp5_report",
]


class CompoundSpec(BaseModel):
    name: str = ""
    compound_class: str = Field(default="", alias="class")
    kegg_id: str | None = None
    notes: str = ""

    model_config = {"populate_by_name": True}


class Ticket(BaseModel):
    id: str
    raw_brief: str
    submitted_by: str = "bioinformatician"
    status: TicketStatus = TicketStatus.DRAFT
    current_phase: str = "intake"
    awaiting_action: str | None = None


class ResearchBrief(BaseModel):
    ticket_id: str
    raw_brief: str
    organism: list[str] = Field(default_factory=list)
    feedstock: CompoundSpec = Field(default_factory=CompoundSpec)
    target: CompoundSpec = Field(default_factory=CompoundSpec)
    target_function: str = ""
    constraints: list[str] = Field(default_factory=list)
    tasks: list[str] = Field(default_factory=list)
    selected_gem_id: str | None = None
    gatekeeper_verdict: str | None = None
    clarifying_questions: list[str] = Field(default_factory=list)


class Citation(BaseModel):
    doi: str | None = None
    pmid: str | None = None
    title: str = ""
    snippet: str = ""
    url: str | None = None
    authors: str = ""
    year: str = ""
    journal: str = ""
    validation_status: Literal["verified", "unverified", "invalid"] = "unverified"


class ReactionStep(BaseModel):
    step_number: int
    description: str
    substrates: list[str] = Field(default_factory=list)
    products: list[str] = Field(default_factory=list)
    enzyme_ec: str | None = None
    enzyme_name: str | None = None
    gene_names: list[str] = Field(default_factory=list)
    heterologous: bool = False


class PathwayCandidate(BaseModel):
    id: str
    name: str
    description: str = ""
    reaction_steps: list[ReactionStep] = Field(default_factory=list)
    enzymes: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    reported_titer: str | None = None
    confidence: Literal["strong", "partial", "inferred"] = "partial"
    confidence_rationale: str = ""
    confidence_factors: list[str] = Field(default_factory=list)
    literature_provenance: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _migrate_provenance(cls, data: Any) -> Any:
        if isinstance(data, dict) and "biomni_provenance" in data and "literature_provenance" not in data:
            data = {**data, "literature_provenance": data.pop("biomni_provenance")}
        return data


class GemDiscoveryResult(BaseModel):
    organism: str = ""
    model_name: str = ""
    model_id: str | None = None
    validation_paper: Citation | None = None
    feedstock_used_in_validation: str | None = None
    biomass_context: str | None = None
    rationale: str = ""
    confidence: Literal["strong", "partial", "inferred"] = "partial"
    sbml_available_locally: bool = False
    sbml_url: str | None = None
    sbml_source: str | None = None
    literature_refs: list[Citation] = Field(default_factory=list)


class GemProfile(BaseModel):
    gem_id: str
    model_ref: str
    scenario: str
    organism: str = ""
    feedstock_class: str = ""
    model_name: str = ""
    model_cache_path: str = ""
    cache_source: str = ""
    discovery_rationale: str = ""
    discovery_confidence: str = ""
    validation_paper: Citation | None = None
    literature_refs: list[Citation] = Field(default_factory=list)
    biomass_validation_scenario: str = ""


class GemSelectionResult(BaseModel):
    gem: GemProfile | None = None
    validation_mode: ValidationMode
    reason: str = ""
    discovery: GemDiscoveryResult | None = None


class CandidateReaction(BaseModel):
    id: str
    name: str = ""
    stoichiometry: dict[str, float] = Field(default_factory=dict)
    bounds: tuple[float, float] = (0.0, 1000.0)
    gene_associations: list[str] = Field(default_factory=list)


class ScorePathwayPayload(BaseModel):
    pathway_id: str
    model_ref: str
    scenario: str
    carbon_source_rxn: str = ""
    candidate_reactions: list[CandidateReaction] = Field(default_factory=list)
    product_metabolite: str = ""
    knockouts: list[str] = Field(default_factory=list)
    substrate_moles_per_product: float = 1.0
    objective: str = "product"
    source_citations: list[Citation] = Field(default_factory=list)


class Bottleneck(BaseModel):
    reaction: str
    flux: float = 0.0
    at_bound: bool = False
    explanation: str = ""
    min_flux: float | None = None
    max_flux: float | None = None
    flux_span: float | None = None


class CalculationStep(BaseModel):
    step: int
    title: str
    detail: str = ""


class FBAValidationResult(BaseModel):
    pathway_id: str
    status: str
    objective_used: str = ""
    predicted_product_flux: float | None = None
    growth_rate: float | None = None
    yield_mol_per_mol_substrate: float | None = None
    yield_corrected_mol_per_mol_substrate: float | None = None
    calculation_steps: list[CalculationStep] = Field(default_factory=list)
    simulation_context: dict[str, Any] = Field(default_factory=dict)
    inserted_reactions: list[str] = Field(default_factory=list)
    edits_applied: dict[str, Any] = Field(default_factory=dict)
    solver_message: str = ""
    bottlenecks: list[Bottleneck] = Field(default_factory=list)
    calibration_level: str = "exploratory"
    product_confidence_level: str = ""
    carbon_audit_sole_source: bool | None = None
    carbon_audit: dict[str, Any] = Field(default_factory=dict)
    edits_not_found: list[str] = Field(default_factory=list)
    verdict: Literal["pass", "marginal", "fail"] = "fail"
    failure_reasons: list[str] = Field(default_factory=list)
    rank: int | None = None
    calibration_rationale: str = ""
    verdict_rationale: str = ""
    calibration_warnings: list[str] = Field(default_factory=list)
    literature_refs: list[Citation] = Field(default_factory=list)


class GeneSuggestion(BaseModel):
    gene: str
    action: Literal["overexpress", "knockout", "heterologous"]
    rationale: str = ""
    citation: Citation | None = None


class LiteraturePathwayPlan(BaseModel):
    pathway_id: str
    pathway_name: str
    reaction_map: list[ReactionStep] = Field(default_factory=list)
    suggested_hosts: list[str] = Field(default_factory=list)
    gene_suggestions: list[GeneSuggestion] = Field(default_factory=list)
    known_risks: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)


class HumanDecision(BaseModel):
    checkpoint: CheckpointId
    action: Literal["proceed", "revise", "reject"]
    notes: str | None = None
    selected_pathway_ids: list[str] | None = None
    primary_pathway_id: str | None = None


class OutcomeReport(BaseModel):
    validation_mode: ValidationMode
    project_summary: str = ""
    target_molecule_specification: str = ""
    feedstock_starting_material: str = ""
    production_strategy: str = ""
    genetic_engineering_plan: str = ""
    predicted_performance: str = ""
    validation_plan: str = ""
    risk_bottleneck_assessment: str = ""
    regulatory_positioning: str = ""
    markdown: str = ""


class StreamEvent(BaseModel):
    type: str
    content: str | None = None
    tool: str | None = None
    input: dict | None = None
    output: str | None = None
    step_id: str | None = None
    artifact: dict | None = None
    message: str | None = None
    summary: str | None = None
