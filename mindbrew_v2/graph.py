"""LangGraph agent with HITL checkpoints."""

from __future__ import annotations

import time
from typing import Callable, Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.errors import GraphInterrupt
from langgraph.graph import END, StateGraph
from langgraph.types import interrupt

from mindbrew_v2.config.gem import provisional_validation_mode
from mindbrew_v2.models import ValidationMode
from mindbrew_v2.phases.formalize import formalize_pathways
from mindbrew_v2.phases.intake import run_intake
from mindbrew_v2.phases.literature_plan import build_literature_plan
from mindbrew_v2.phases.literature_search import run_literature_search
from mindbrew_v2.phases.report import generate_report
from mindbrew_v2.progress import log, node_end, node_start
from mindbrew_v2.telemetry import start_span
from mindbrew_v2.tools.fba_client import rank_fba_results, score_pathway
from mindbrew_v2.tools.literature_retrieval import RetrievedDocument

NODE_LABELS: dict[str, str] = {
    "intake": "Parsing research brief (intake + agent status)",
    "cp1_spec_review": "Spec review checkpoint",
    "literature_search": "Literature pathway search (LLM)",
    "cp2_pathway_review": "Pathway selection checkpoint",
    "formalize": "Formalizing pathways for FBA",
    "cp3_fba_plan_review": "FBA plan review checkpoint",
    "score_pathway": "Running FBA scoring",
    "cp4_fba_review": "FBA results review checkpoint",
    "literature_plan": "Building literature pathway plan",
    "cp3b_lit_plan_review": "Literature plan review checkpoint",
    "generate_report": "Generating final report",
    "cp5_report_review": "Report review checkpoint",
}


def _tracked(name: str, fn: Callable[[dict], dict]) -> Callable[[dict], dict]:
    label = NODE_LABELS.get(name, name)

    def wrapped(state: dict) -> dict:
        started = time.perf_counter()
        node_start(name, label, stage="work")
        log(f"Starting: {label}")
        with start_span("graph.node", {"node_id": name, "stage": "work", "label": label}):
            try:
                result = fn(state)
                node_end(name, label, stage="work", status="ok", started_at=started)
                log(f"Finished: {label}")
                return result
            except Exception as exc:
                node_end(name, label, stage="work", status="error", started_at=started)
                log(f"Failed: {label} — {exc}", level="error")
                raise

    return wrapped


def _tracked_review(name: str, fn: Callable[[dict], dict]) -> Callable[[dict], dict]:
    label = NODE_LABELS.get(name, name)

    def wrapped(state: dict) -> dict:
        started = time.perf_counter()
        node_start(name, label, stage="review")
        log(f"Checkpoint: {label}")
        with start_span("graph.node", {"node_id": name, "stage": "review", "label": label}):
            try:
                result = fn(state)
                node_end(name, label, stage="review", status="ok", started_at=started)
                return result
            except GraphInterrupt:
                log(f"Checkpoint paused: {label} — awaiting user decision")
                raise
            except Exception as exc:
                node_end(name, label, stage="review", status="error", started_at=started)
                log(f"Checkpoint failed: {label} — {exc}", level="error")
                raise

    return wrapped


def build_graph(checkpointer=None):
    graph = StateGraph(dict)

    graph.add_node("intake", _tracked("intake", _node_intake))
    graph.add_node("cp1_spec_review", _tracked_review("cp1_spec_review", _node_cp1))
    graph.add_node("literature_search", _tracked("literature_search", _node_literature_search))
    graph.add_node("cp2_pathway_review", _tracked_review("cp2_pathway_review", _node_cp2))
    graph.add_node("formalize", _tracked("formalize", _node_formalize))
    graph.add_node("cp3_fba_plan_review", _tracked_review("cp3_fba_plan_review", _node_cp3))
    graph.add_node("score_pathway", _tracked("score_pathway", _node_score))
    graph.add_node("cp4_fba_review", _tracked_review("cp4_fba_review", _node_cp4))
    graph.add_node("literature_plan", _tracked("literature_plan", _node_literature_plan))
    graph.add_node("cp3b_lit_plan_review", _tracked_review("cp3b_lit_plan_review", _node_cp3b))
    graph.add_node("generate_report", _tracked("generate_report", _node_report))
    graph.add_node("cp5_report_review", _tracked_review("cp5_report_review", _node_cp5))

    graph.set_entry_point("intake")
    graph.add_edge("intake", "cp1_spec_review")
    graph.add_conditional_edges(
        "cp1_spec_review",
        _after_cp1,
        {"proceed": "literature_search", "revise": "intake", "reject": END},
    )
    graph.add_edge("literature_search", "cp2_pathway_review")
    graph.add_conditional_edges(
        "cp2_pathway_review",
        _after_cp2_branch,
        {"revise": "literature_search", "fba": "formalize", "literature": "literature_plan"},
    )
    graph.add_edge("formalize", "cp3_fba_plan_review")
    graph.add_conditional_edges("cp3_fba_plan_review", _after_cp3, {"proceed": "score_pathway", "revise": "formalize"})
    graph.add_edge("score_pathway", "cp4_fba_review")
    graph.add_conditional_edges(
        "cp4_fba_review",
        _after_cp4,
        {"proceed": "generate_report", "revise": "literature_search"},
    )
    graph.add_edge("literature_plan", "cp3b_lit_plan_review")
    graph.add_conditional_edges("cp3b_lit_plan_review", _after_cp3b, {"proceed": "generate_report", "revise": "literature_plan"})
    graph.add_edge("generate_report", "cp5_report_review")
    graph.add_conditional_edges("cp5_report_review", _after_cp5, {"proceed": END, "revise": "generate_report"})

    cp = checkpointer or MemorySaver()
    return graph.compile(checkpointer=cp)


def _revision_notes(state: dict) -> str | None:
    return state.get("revision_notes")


def _parse_literature_context(state: dict) -> list[RetrievedDocument]:
    raw = state.get("literature_context") or []
    return [RetrievedDocument.model_validate(item) for item in raw]


def _node_intake(state: dict) -> dict:
    ticket = state["ticket"]
    from mindbrew_v2.models import Ticket

    t = Ticket.model_validate(ticket) if isinstance(ticket, dict) else ticket
    brief = run_intake(t, _revision_notes(state))
    selection = provisional_validation_mode(brief)
    return {
        **state,
        "brief": brief.model_dump(),
        "validation_mode": selection.validation_mode.value,
        "gem_profile": None,
        "gem_selection_reason": selection.reason,
        "revision_notes": None,
    }


def _node_cp1(state: dict) -> dict:
    interrupt({
        "checkpoint": "cp1_spec",
        "artifact": {
            "brief": state.get("brief"),
            "validation_mode": state.get("validation_mode"),
            "gem_profile": state.get("gem_profile"),
            "gem_selection_reason": state.get("gem_selection_reason"),
        },
    })
    return state


def _node_literature_search(state: dict) -> dict:
    from mindbrew_v2.models import ResearchBrief

    brief = ResearchBrief.model_validate(state["brief"])
    candidates, context_docs = run_literature_search(brief, _revision_notes(state))
    return {
        **state,
        "pathway_candidates": [c.model_dump() for c in candidates],
        "literature_context": [d.model_dump() for d in context_docs],
        "revision_notes": None,
    }


def _node_cp2(state: dict) -> dict:
    brief = state.get("brief") or {}
    interrupt({
        "checkpoint": "cp2_pathways",
        "artifact": {
            "pathway_candidates": state.get("pathway_candidates", []),
            "organism": brief.get("organism", []),
        },
    })
    return state


def _after_cp2_branch(state: dict) -> Literal["revise", "fba", "literature"]:
    action = _last_decision(state, "cp2_pathways")
    if action == "revise":
        return "revise"
    mode = state.get("validation_mode")
    if not mode and state.get("brief"):
        from mindbrew_v2.models import ResearchBrief

        brief = ResearchBrief.model_validate(state["brief"])
        mode = provisional_validation_mode(brief).validation_mode.value
    if not mode:
        mode = ValidationMode.LITERATURE_PATHWAY.value
    return "fba" if mode == ValidationMode.FBA.value else "literature"


def _node_formalize(state: dict) -> dict:
    from mindbrew_v2.models import PathwayCandidate, ResearchBrief

    brief = ResearchBrief.model_validate(state["brief"])
    candidates_raw = state.get("approved_candidates") or state.get("pathway_candidates", [])
    candidates = [PathwayCandidate.model_validate(c) for c in candidates_raw]
    override = state.get("gem_override")
    result = formalize_pathways(
        brief,
        candidates,
        literature_context=_parse_literature_context(state),
        gem_override=override,
    )
    prior_mode = state.get("validation_mode") or ValidationMode.FBA.value
    updates: dict = {
        **state,
        "gem_profile": result.gem.model_dump() if result.gem else state.get("gem_profile"),
        "gem_discovery": result.discovery.model_dump() if result.discovery else None,
        "find_ids_summary": result.find_ids_summary,
        "biomass_validation": result.biomass_validation,
        "biomass_validation_warning": result.biomass_validation_warning,
        "score_payloads": [p.model_dump() for p in result.payloads],
        "formalize_skipped": result.skipped,
        "validation_mode": prior_mode,
        "revision_notes": None,
    }
    if result.gem is None:
        updates["gem_selection_reason"] = result.skipped[0] if result.skipped else "No local GEM"
    return updates


def _node_cp3(state: dict) -> dict:
    interrupt({
        "checkpoint": "cp3_fba_plan",
        "artifact": {
            "gem_profile": state.get("gem_profile"),
            "gem_discovery": state.get("gem_discovery"),
            "find_ids_summary": state.get("find_ids_summary"),
            "biomass_validation": state.get("biomass_validation"),
            "biomass_validation_warning": state.get("biomass_validation_warning"),
            "score_payloads": state.get("score_payloads", []),
            "skipped": state.get("formalize_skipped", []),
        },
    })
    return state


def _node_score(state: dict) -> dict:
    from mindbrew_v2.models import ScorePathwayPayload

    payloads = [ScorePathwayPayload.model_validate(p) for p in state.get("score_payloads", [])]
    results = [score_pathway(p) for p in payloads]
    ranked = rank_fba_results(results)
    return {**state, "fba_results": [r.model_dump() for r in ranked]}


def _node_cp4(state: dict) -> dict:
    interrupt({"checkpoint": "cp4_fba_results", "artifact": {"fba_results": state.get("fba_results", [])}})
    return state


def _node_literature_plan(state: dict) -> dict:
    from mindbrew_v2.models import PathwayCandidate, ResearchBrief

    brief = ResearchBrief.model_validate(state["brief"])
    candidates_raw = state.get("approved_candidates") or state.get("pathway_candidates", [])
    candidates = [PathwayCandidate.model_validate(c) for c in candidates_raw]
    primary_id = state.get("primary_pathway_id")
    primary = next((c for c in candidates if c.id == primary_id), candidates[0] if candidates else None)
    if not primary:
        return {**state, "literature_plan": None}
    plan = build_literature_plan(brief, primary, _revision_notes(state))
    return {**state, "literature_plan": plan.model_dump(), "revision_notes": None}


def _node_cp3b(state: dict) -> dict:
    brief = state.get("brief") or {}
    interrupt({
        "checkpoint": "cp3b_literature_plan",
        "artifact": {
            "literature_plan": state.get("literature_plan"),
            "organism": brief.get("organism", []),
        },
    })
    return state


def _node_report(state: dict) -> dict:
    from mindbrew_v2.models import (
        FBAValidationResult,
        GemDiscoveryResult,
        LiteraturePathwayPlan,
        PathwayCandidate,
        ResearchBrief,
        ScorePathwayPayload,
        ValidationMode,
    )

    brief = ResearchBrief.model_validate(state["brief"])
    mode = ValidationMode(state.get("validation_mode", "literature"))
    candidates = [PathwayCandidate.model_validate(c) for c in state.get("pathway_candidates", [])]
    fba = [FBAValidationResult.model_validate(r) for r in state.get("fba_results", [])] if state.get("fba_results") else None
    lit = LiteraturePathwayPlan.model_validate(state["literature_plan"]) if state.get("literature_plan") else None
    discovery = GemDiscoveryResult.model_validate(state["gem_discovery"]) if state.get("gem_discovery") else None
    payloads = (
        [ScorePathwayPayload.model_validate(p) for p in state.get("score_payloads", [])]
        if state.get("score_payloads")
        else None
    )
    report = generate_report(
        brief,
        mode,
        candidates,
        state.get("primary_pathway_id"),
        fba,
        lit,
        _revision_notes(state),
        gem_discovery=discovery,
        gem_profile=state.get("gem_profile"),
        gem_selection_reason=state.get("gem_selection_reason"),
        biomass_validation_warning=state.get("biomass_validation_warning"),
        session_title=state.get("session_title"),
        score_payloads=payloads,
        formalize_skipped=state.get("formalize_skipped"),
    )
    return {**state, "report": report.model_dump(), "revision_notes": None}


def _node_cp5(state: dict) -> dict:
    interrupt({"checkpoint": "cp5_report", "artifact": {"report": state.get("report")}})
    return state


def _last_decision(state: dict, checkpoint: str) -> str:
    for d in reversed(state.get("human_decisions", [])):
        if d.get("checkpoint") == checkpoint:
            if d.get("action") == "reject":
                return "reject"
            if d.get("action") == "revise":
                return "revise"
            return "proceed"
    return "proceed"


def _after_cp1(state: dict) -> str:
    verdict = (state.get("brief") or {}).get("gatekeeper_verdict", "PROCEED")
    if verdict == "REJECT":
        return "reject"
    return _last_decision(state, "cp1_spec")


def _after_cp3(state: dict) -> str:
    return _last_decision(state, "cp3_fba_plan")


def _after_cp4(state: dict) -> str:
    action = _last_decision(state, "cp4_fba_results")
    return "revise" if action == "revise" else "proceed"


def _after_cp3b(state: dict) -> str:
    return _last_decision(state, "cp3b_literature_plan")


def _after_cp5(state: dict) -> str:
    return _last_decision(state, "cp5_report")
