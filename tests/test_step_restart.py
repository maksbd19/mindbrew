"""Step restart preserves prior-step memory."""

import os

import pytest

os.environ["BREWMIND_OFFLINE"] = "true"

from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from mindbrew_v2.graph import build_graph
from mindbrew_v2.models import StepId
from mindbrew_v2.models import HumanDecision
from mindbrew_v2.phases.checkpoints import (
    prepare_pathway_switch_state,
    prepare_step_restart_state,
    paused_at_step_checkpoint,
    restart_anchor_for_step,
    restore_prior_step_memory,
)


def _base_state(session_id: str = "restart-test") -> dict:
    return {
        "ticket": {"id": session_id, "raw_brief": "wax ester yarrowia"},
        "brief": {"ticket_id": session_id, "raw_brief": "wax ester", "organism": ["Yarrowia lipolytica"]},
        "pathway_candidates": [{"id": "p1", "name": "Path A"}],
        "approved_candidates": [{"id": "p1", "name": "Path A"}],
        "gem_profile": {"gem_id": "iyli647"},
        "validation_mode": "fba",
        "literature_plan": None,
        "primary_pathway_id": "p1",
        "score_payloads": [{"pathway_id": "p1"}],
        "fba_results": [{"pathway_id": "p1", "status": "optimal"}],
        "report": {"markdown": "# Report"},
        "pending_checkpoint": None,
        "human_decisions": [
            {"checkpoint": "cp1_spec", "action": "proceed"},
            {"checkpoint": "cp2_pathways", "action": "proceed", "selected_pathway_ids": ["p1"]},
        ],
        "revision_number": 0,
        "max_revisions": 5,
        "revision_notes": None,
    }


class _StepRow:
    def __init__(self, step_id: str, artifact: dict, human_decisions: list | None = None):
        self.step_id = step_id
        self.artifact = artifact
        self.human_decisions = human_decisions or []


def test_prepare_pathway_switch_keeps_candidates_clears_downstream():
    state = _base_state()
    state["pathway_candidates"] = [{"id": "p1", "name": "Path A"}, {"id": "p2", "name": "Path B"}]
    decision = HumanDecision(
        checkpoint="cp2_pathways",
        action="proceed",
        selected_pathway_ids=["p2"],
        primary_pathway_id="p2",
    )
    updated = prepare_pathway_switch_state(state, decision)
    assert updated["brief"]["organism"] == ["Yarrowia lipolytica"]
    assert len(updated["pathway_candidates"]) == 2
    assert updated["primary_pathway_id"] == "p2"
    assert updated["approved_candidates"] == [{"id": "p2", "name": "Path B"}]
    assert updated["score_payloads"] == []
    assert updated["fba_results"] == []
    assert updated["report"] is None
    cp2_decisions = [d for d in updated["human_decisions"] if d.get("checkpoint") == "cp2_pathways"]
    assert len(cp2_decisions) == 1
    assert cp2_decisions[0]["primary_pathway_id"] == "p2"


def test_prepare_step_restart_cp2_keeps_brief():
    state = _base_state()
    updated = prepare_step_restart_state(state, StepId.CP2_PATHWAYS)
    assert updated["brief"]["organism"] == ["Yarrowia lipolytica"]
    assert updated["pathway_candidates"] == []
    assert updated["score_payloads"] == []
    assert updated["report"] is None


def test_prepare_step_restart_cp1_keeps_ticket():
    state = _base_state()
    updated = prepare_step_restart_state(state, StepId.CP1_SPEC)
    assert updated["ticket"]["raw_brief"] == "wax ester yarrowia"
    assert updated["brief"] is None
    assert updated["pathway_candidates"] == []


def test_restore_prior_step_memory_from_db_rows():
    rows = [
        _StepRow(
            "cp1_spec",
            {
                "brief": {"ticket_id": "x", "raw_brief": "wax", "organism": ["Yarrowia lipolytica"]},
                "validation_mode": "fba",
                "gem_profile": {"gem_id": "iyli647"},
            },
        ),
        _StepRow(
            "cp2_pathways",
            {"pathway_candidates": [{"id": "p1", "name": "Path A"}]},
            human_decisions=[{"action": "proceed", "selected_pathway_ids": ["p1"], "primary_pathway_id": "p1"}],
        ),
    ]
    state = {
        "ticket": {"id": "x", "raw_brief": "wax ester yarrowia"},
        "validation_mode": None,
        "brief": None,
        "pathway_candidates": [],
        "approved_candidates": [],
        "primary_pathway_id": None,
    }
    restored = restore_prior_step_memory(state, StepId.CP3_FBA_PLAN, rows)
    assert restored["brief"]["organism"] == ["Yarrowia lipolytica"]
    assert restored["validation_mode"] == "fba"
    assert restored["pathway_candidates"][0]["id"] == "p1"
    assert restored["approved_candidates"][0]["id"] == "p1"
    assert restored["primary_pathway_id"] == "p1"


def test_cp2_restart_restores_brief_from_db_when_checkpoint_missing():
    rows = [
        _StepRow(
            "cp1_spec",
            {
                "brief": {"ticket_id": "x", "raw_brief": "wax", "organism": ["Yarrowia lipolytica"]},
                "validation_mode": "fba",
            },
        ),
    ]
    checkpoint_state = prepare_step_restart_state(
        {
            **_base_state("x"),
            "brief": None,
            "validation_mode": None,
            "pathway_candidates": [{"id": "p1", "name": "Path A"}],
        },
        StepId.CP2_PATHWAYS,
    )
    restored = restore_prior_step_memory(checkpoint_state, StepId.CP2_PATHWAYS, rows)
    assert restored["brief"]["organism"] == ["Yarrowia lipolytica"]
    assert restored["validation_mode"] == "fba"
    assert restored["pathway_candidates"] == []


@pytest.mark.asyncio
async def test_revise_routing_restarts_cp1_with_ticket_memory():
    graph = build_graph(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "goto-cp1"}}
    state = {
        "ticket": {"id": "goto-cp1", "raw_brief": "wax ester yarrowia"},
        "brief": None,
        "pathway_candidates": [],
        "approved_candidates": [],
        "gem_profile": None,
        "validation_mode": None,
        "literature_plan": None,
        "primary_pathway_id": None,
        "score_payloads": [],
        "fba_results": [],
        "report": None,
        "pending_checkpoint": None,
        "human_decisions": [],
        "revision_number": 0,
        "max_revisions": 5,
        "revision_notes": None,
    }
    for chunk in graph.stream(state, config):
        if "__interrupt__" in chunk:
            break

    snap = graph.get_state(config)
    restarted = prepare_step_restart_state(dict(snap.values), StepId.CP1_SPEC)
    restarted["human_decisions"] = [{"checkpoint": "cp1_spec", "action": "revise", "notes": None}]
    graph.update_state(config, restarted)
    for chunk in graph.stream(Command(resume=True), config):
        if "__interrupt__" in chunk:
            break

    after = graph.get_state(config)
    assert after.values["ticket"]["raw_brief"] == "wax ester yarrowia"
    assert after.values["brief"] is not None
    assert after.values["brief"]["organism"] == ["Yarrowia lipolytica"]


def test_restart_mid_node_uses_anchor_not_goto():
    """Restarting after a mid-node failure must not run goto + stale next concurrently."""
    from langgraph.errors import InvalidUpdateError

    graph = build_graph(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "mid-node-fail"}}
    state = {
        "ticket": {"id": "mid-node-fail", "raw_brief": "wax ester yarrowia"},
        "brief": {"ticket_id": "mid-node-fail", "raw_brief": "wax", "organism": ["Yarrowia lipolytica"]},
        "pathway_candidates": [{"id": "p1", "name": "Path A"}],
        "approved_candidates": [],
        "validation_mode": "literature",
        "human_decisions": [{"checkpoint": "cp1_spec", "action": "proceed"}],
        "revision_number": 0,
        "max_revisions": 5,
        "revision_notes": None,
    }
    # Simulate stale checkpoint memory: plain update_state leaves next on a revise route.
    graph.update_state(config, state, as_node="literature_search")
    current = prepare_step_restart_state(dict(graph.get_state(config).values), StepId.CP2_PATHWAYS)
    graph.update_state(config, current)
    snap = graph.get_state(config)
    assert snap.next != ("literature_search",)
    assert not paused_at_step_checkpoint(snap, StepId.CP2_PATHWAYS)

    with pytest.raises(InvalidUpdateError):
        for _ in graph.stream(Command(goto="literature_search"), config):
            pass

    anchor = restart_anchor_for_step(StepId.CP2_PATHWAYS, current)
    graph.update_state(config, current, as_node=anchor)
    assert graph.get_state(config).next == ("literature_search",)

    for chunk in graph.stream(None, config):
        if "__interrupt__" in chunk:
            break

    assert graph.get_state(config).next == ("cp2_pathway_review",)
