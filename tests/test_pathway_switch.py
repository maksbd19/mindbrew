"""Pathway switch validation allows retry after failure."""

from __future__ import annotations

import os

os.environ.setdefault("BREWMIND_OFFLINE", "true")

from mindbrew_v2.models import HumanDecision


class _SessionRow:
    def __init__(
        self,
        *,
        status: str = "failed",
        current_step: str = "cp3_fba_plan",
        validation_mode: str = "fba",
        steps: list | None = None,
    ):
        self.status = status
        self.current_step = current_step
        self.validation_mode = validation_mode
        self.steps = steps or []


def test_validate_pathway_switch_allows_failed_session(monkeypatch):
    from api.services import graph_runner

    row = _SessionRow()
    decision = HumanDecision(
        checkpoint="cp2_pathways",
        action="proceed",
        selected_pathway_ids=["pw1"],
        primary_pathway_id="pw1",
    )

    monkeypatch.setattr(graph_runner, "is_session_active", lambda _sid: False)
    monkeypatch.setattr(
        "api.services.session_store.get_session",
        lambda _db, _sid: row,
    )
    snapshot = type(
        "S",
        (),
        {
            "values": {
                "pathway_candidates": [{"id": "pw1", "name": "Path 1"}],
                "validation_mode": "fba",
            }
        },
    )()

    class _Graph:
        def get_state(self, _config):
            return snapshot

    monkeypatch.setattr(graph_runner, "get_graph", lambda: _Graph())

    assert graph_runner.validate_pathway_switch("sess-1", decision, object()) is None


def test_validate_pathway_switch_rejects_running_session(monkeypatch):
    from api.services import graph_runner

    row = _SessionRow(status="running")
    decision = HumanDecision(
        checkpoint="cp2_pathways",
        action="proceed",
        selected_pathway_ids=["pw1"],
    )

    monkeypatch.setattr(graph_runner, "is_session_active", lambda _sid: False)

    reason = graph_runner._user_action_block_reason("sess-1", row.status)
    assert reason is not None
    assert "running" in reason
