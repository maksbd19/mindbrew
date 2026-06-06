"""Tests for human decision validation at checkpoints."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("BREWMIND_OFFLINE", "true")
os.environ.setdefault("MAX_REVISIONS", "3")

from mindbrew_v2.models import HumanDecision
from mindbrew_v2.phases.checkpoints import decision_block_reason, prepare_pathway_switch_state


def _state(**overrides) -> dict:
    base = {
        "brief": {"gatekeeper_verdict": "PROCEED"},
        "pathway_candidates": [{"id": "pw1", "name": "Pathway 1"}],
        "revision_number": 0,
        "max_revisions": 3,
    }
    base.update(overrides)
    return base


def test_cp1_reject_blocks_proceed():
    decision = HumanDecision(checkpoint="cp1_spec", action="proceed")
    state = _state(brief={"gatekeeper_verdict": "REJECT"})
    reason = decision_block_reason(decision, state)
    assert reason is not None
    assert "rejected" in reason.lower()


def test_cp1_clarify_allows_proceed():
    decision = HumanDecision(checkpoint="cp1_spec", action="proceed")
    state = _state(
        brief={
            "gatekeeper_verdict": "CLARIFY",
            "clarifying_questions": ["Which organism?"],
        }
    )
    assert decision_block_reason(decision, state) is None


def test_cp2_empty_candidates_blocks_proceed():
    decision = HumanDecision(checkpoint="cp2_pathways", action="proceed")
    state = _state(pathway_candidates=[])
    reason = decision_block_reason(decision, state)
    assert reason is not None
    assert "no pathway candidates" in reason.lower()


def test_cp2_missing_selection_blocks_proceed():
    decision = HumanDecision(checkpoint="cp2_pathways", action="proceed")
    state = _state()
    reason = decision_block_reason(decision, state)
    assert reason is not None
    assert "select at least one pathway" in reason.lower()


def test_cp2_with_selection_allows_proceed():
    decision = HumanDecision(
        checkpoint="cp2_pathways",
        action="proceed",
        selected_pathway_ids=["pw1"],
        primary_pathway_id="pw1",
    )
    reason = decision_block_reason(decision, _state())
    assert reason is None


def test_revision_cap_blocks_revise():
    decision = HumanDecision(checkpoint="cp1_spec", action="revise", notes="more detail")
    state = _state(revision_number=3, max_revisions=3)
    reason = decision_block_reason(decision, state)
    assert reason is not None
    assert "maximum revision limit" in reason.lower()


def test_prepare_pathway_switch_replaces_old_cp2_decision():
    state = {
        "validation_mode": "fba",
        "pathway_candidates": [{"id": "pw1", "name": "One"}, {"id": "pw2", "name": "Two"}],
        "primary_pathway_id": "pw1",
        "score_payloads": [{"pathway_id": "pw1"}],
        "human_decisions": [
            {"checkpoint": "cp1_spec", "action": "proceed"},
            {"checkpoint": "cp2_pathways", "action": "proceed", "selected_pathway_ids": ["pw1"]},
            {"checkpoint": "cp3_fba_plan", "action": "proceed"},
        ],
    }
    decision = HumanDecision(
        checkpoint="cp2_pathways",
        action="proceed",
        selected_pathway_ids=["pw2"],
        primary_pathway_id="pw2",
    )
    updated = prepare_pathway_switch_state(state, decision)
    assert updated["primary_pathway_id"] == "pw2"
    assert updated["score_payloads"] == []
    checkpoints = [d.get("checkpoint") for d in updated["human_decisions"]]
    assert checkpoints == ["cp1_spec", "cp2_pathways"]


def test_revision_below_cap_allows_revise():
    decision = HumanDecision(checkpoint="cp1_spec", action="revise", notes="more detail")
    state = _state(revision_number=2, max_revisions=3)
    assert decision_block_reason(decision, state) is None
