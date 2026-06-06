"""Phase 0 — Intake: ticket → ResearchBrief."""

from __future__ import annotations

from pydantic import BaseModel, Field

from mindbrew_v2.config.llm import structured_extract
from mindbrew_v2.models import CompoundSpec, ResearchBrief, Ticket


class IntakeResult(BaseModel):
    gatekeeper_verdict: str
    organism: list[str] = Field(default_factory=list)
    feedstock: CompoundSpec = Field(default_factory=CompoundSpec)
    target: CompoundSpec = Field(default_factory=CompoundSpec)
    target_function: str = ""
    constraints: list[str] = Field(default_factory=list)
    tasks: list[str] = Field(default_factory=list)
    clarifying_questions: list[str] = Field(default_factory=list)


INTAKE_SYSTEM = """You are a biocatalysis intake agent for R&D tickets.
Parse the plain-language brief into structured fields.
Gatekeeper verdict: PROCEED for biocatalysis/fermentation/lipid/microbiome tickets;
CLARIFY if genuinely ambiguous; REJECT for non-biocatalysis queries.
Ask at most 1-2 clarifying questions only when necessary."""


def run_intake(ticket: Ticket, revision_notes: str | None = None) -> ResearchBrief:
    from mindbrew_v2.progress import log

    prompt = f"Ticket ID: {ticket.id}\n\nBrief:\n{ticket.raw_brief}"
    if revision_notes:
        prompt += f"\n\nRevision feedback from reviewer:\n{revision_notes}"

    log("Calling LLM to parse brief and check agent status…")
    result = structured_extract(
        prompt,
        IntakeResult,
        system=INTAKE_SYSTEM,
        role="intake",
    )
    log(f"Agent status: {result.gatekeeper_verdict}")

    return ResearchBrief(
        ticket_id=ticket.id,
        raw_brief=ticket.raw_brief,
        organism=result.organism,
        feedstock=result.feedstock,
        target=result.target,
        target_function=result.target_function,
        constraints=result.constraints,
        tasks=result.tasks,
        gatekeeper_verdict=result.gatekeeper_verdict,
        clarifying_questions=result.clarifying_questions,
    )
