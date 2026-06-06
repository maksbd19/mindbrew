"""Human checkpoint helpers."""

from mindbrew_v2.models import CheckpointId, HumanDecision, StepId

CHECKPOINT_TO_STEP: dict[CheckpointId, StepId] = {
    "cp1_spec": StepId.CP1_SPEC,
    "cp2_pathways": StepId.CP2_PATHWAYS,
    "cp3_fba_plan": StepId.CP3_FBA_PLAN,
    "cp3b_literature_plan": StepId.CP3B_LITERATURE_PLAN,
    "cp4_fba_results": StepId.CP4_FBA_RESULTS,
    "cp5_report": StepId.CP5_REPORT,
}

STEP_TO_CHECKPOINT: dict[StepId, CheckpointId] = {v: k for k, v in CHECKPOINT_TO_STEP.items()}

# Work node to re-run when restarting a checkpoint step (prior-step state is preserved).
STEP_WORK_NODE: dict[StepId, str] = {
    StepId.CP1_SPEC: "intake",
    StepId.CP2_PATHWAYS: "biomni_search",
    StepId.CP3_FBA_PLAN: "formalize",
    StepId.CP3B_LITERATURE_PLAN: "literature_plan",
    StepId.CP4_FBA_RESULTS: "score_pathway",
    StepId.CP5_REPORT: "generate_report",
}

WORK_NODE_TO_STEP: dict[str, str] = {node: step.value for step, node in STEP_WORK_NODE.items()}

STEP_REVIEW_NODE: dict[StepId, str] = {step_id: node for node, step_id in (
    ("cp1_spec_review", StepId.CP1_SPEC),
    ("cp2_pathway_review", StepId.CP2_PATHWAYS),
    ("cp3_fba_plan_review", StepId.CP3_FBA_PLAN),
    ("cp3b_lit_plan_review", StepId.CP3B_LITERATURE_PLAN),
    ("cp4_fba_review", StepId.CP4_FBA_RESULTS),
    ("cp5_report_review", StepId.CP5_REPORT),
)}

_FBA_PIPELINE = (
    StepId.CP1_SPEC,
    StepId.CP2_PATHWAYS,
    StepId.CP3_FBA_PLAN,
    StepId.CP4_FBA_RESULTS,
    StepId.CP5_REPORT,
)
_LITERATURE_PIPELINE = (
    StepId.CP1_SPEC,
    StepId.CP2_PATHWAYS,
    StepId.CP3B_LITERATURE_PLAN,
    StepId.CP5_REPORT,
)

# Fields cleared when restarting a step (includes downstream artifacts).
_STEP_CLEAR_FIELDS: dict[StepId, dict[str, object]] = {
    StepId.CP1_SPEC: {
        "brief": None,
        "validation_mode": None,
        "gem_profile": None,
        "gem_selection_reason": None,
        "pathway_candidates": [],
        "approved_candidates": [],
        "primary_pathway_id": None,
        "score_payloads": [],
        "formalize_skipped": [],
        "fba_results": [],
        "literature_plan": None,
        "report": None,
    },
    StepId.CP2_PATHWAYS: {
        "pathway_candidates": [],
        "approved_candidates": [],
        "primary_pathway_id": None,
        "score_payloads": [],
        "formalize_skipped": [],
        "fba_results": [],
        "literature_plan": None,
        "report": None,
    },
    StepId.CP3_FBA_PLAN: {
        "score_payloads": [],
        "formalize_skipped": [],
        "fba_results": [],
        "report": None,
    },
    StepId.CP3B_LITERATURE_PLAN: {
        "literature_plan": None,
        "report": None,
    },
    StepId.CP4_FBA_RESULTS: {
        "fba_results": [],
        "report": None,
    },
    StepId.CP5_REPORT: {
        "report": None,
    },
}

# LangGraph node names (interrupt_before targets) → checkpoint ids
NODE_TO_CHECKPOINT: dict[str, CheckpointId] = {
    "cp1_spec_review": "cp1_spec",
    "cp2_pathway_review": "cp2_pathways",
    "cp3_fba_plan_review": "cp3_fba_plan",
    "cp3b_lit_plan_review": "cp3b_literature_plan",
    "cp4_fba_review": "cp4_fba_results",
    "cp5_report_review": "cp5_report",
}


def artifact_for_checkpoint(checkpoint: CheckpointId, state: dict) -> dict:
    if checkpoint == "cp1_spec":
        return {
            "brief": state.get("brief"),
            "validation_mode": state.get("validation_mode"),
            "gem_profile": state.get("gem_profile"),
            "gem_selection_reason": state.get("gem_selection_reason"),
        }
    if checkpoint == "cp2_pathways":
        brief = state.get("brief") or {}
        return {
            "pathway_candidates": state.get("pathway_candidates", []),
            "organism": brief.get("organism", []),
        }
    if checkpoint == "cp3_fba_plan":
        return {
            "gem_profile": state.get("gem_profile"),
            "score_payloads": state.get("score_payloads", []),
            "skipped": state.get("formalize_skipped", []),
        }
    if checkpoint == "cp4_fba_results":
        return {"fba_results": state.get("fba_results", [])}
    if checkpoint == "cp3b_literature_plan":
        brief = state.get("brief") or {}
        return {
            "literature_plan": state.get("literature_plan"),
            "organism": brief.get("organism", []),
        }
    if checkpoint == "cp5_report":
        return {"report": state.get("report")}
    return {}


def checkpoint_summary(checkpoint: CheckpointId, artifact: dict) -> str:
    summaries = {
        "cp1_spec": "Review parsed research specification and GEM availability",
        "cp2_pathways": "Select pathway(s) from literature search results",
        "cp3_fba_plan": "Review FBA formalization plan before scoring",
        "cp3b_literature_plan": "Review literature pathway plan (no GEM)",
        "cp4_fba_results": "Review FBA validation results",
        "cp5_report": "Approve final CRO-ready report",
    }
    base = summaries.get(checkpoint, checkpoint)
    if checkpoint == "cp1_spec" and artifact.get("validation_mode"):
        base += f" — mode: {artifact['validation_mode']}"
    return base


def step_pipeline(state: dict) -> tuple[StepId, ...]:
    mode = state.get("validation_mode")
    if mode == "fba":
        return _FBA_PIPELINE
    if mode == "literature":
        return _LITERATURE_PIPELINE
    return _FBA_PIPELINE


def downstream_steps(state: dict, step_id: StepId) -> list[StepId]:
    pipeline = step_pipeline(state)
    if step_id not in pipeline:
        return []
    idx = pipeline.index(step_id)
    return list(pipeline[idx + 1 :])


def work_node_for_step(step_id: StepId) -> str:
    node = STEP_WORK_NODE.get(step_id)
    if not node:
        raise ValueError(f"No work node configured for step {step_id}")
    return node


# Review node whose outgoing edge targets the work node — used to reposition the graph
# before re-running a step that failed mid-node (not paused at its checkpoint).
_STEP_RESTART_ANCHOR: dict[StepId, str | None] = {
    StepId.CP1_SPEC: None,
    StepId.CP2_PATHWAYS: "cp1_spec_review",
    StepId.CP3_FBA_PLAN: "cp2_pathway_review",
    StepId.CP3B_LITERATURE_PLAN: "cp2_pathway_review",
    StepId.CP4_FBA_RESULTS: "cp3_fba_plan_review",
}


def restart_anchor_for_step(step_id: StepId, state: dict) -> str | None:
    """Return the review node to anchor on when restarting outside a checkpoint pause."""
    if step_id == StepId.CP5_REPORT:
        return (
            "cp4_fba_review"
            if state.get("validation_mode") == "fba"
            else "cp3b_lit_plan_review"
        )
    return _STEP_RESTART_ANCHOR.get(step_id)


def review_node_for_step(step_id: StepId) -> str:
    node = STEP_REVIEW_NODE.get(step_id)
    if not node:
        raise ValueError(f"No review node configured for step {step_id}")
    return node


def paused_at_step_checkpoint(snapshot, step_id: StepId) -> bool:
    if not snapshot.next:
        return False
    return snapshot.next[0] == review_node_for_step(step_id)


def prepare_step_restart_state(state: dict, step_id: StepId) -> dict:
    """Clear this step's outputs and downstream artifacts; keep prior-step memory."""
    updated = dict(state)
    clears = _STEP_CLEAR_FIELDS.get(step_id, {})
    updated.update(clears)
    updated["revision_notes"] = None

    checkpoint = STEP_TO_CHECKPOINT[step_id]
    updated["human_decisions"] = [
        d for d in updated.get("human_decisions", []) if d.get("checkpoint") != checkpoint
    ]
    return updated


def merge_step_artifact_into_state(state: dict, step_id: StepId, artifact: dict) -> dict:
    """Restore graph fields from a persisted step artifact when missing in state."""
    updated = dict(state)
    if step_id == StepId.CP1_SPEC:
        if updated.get("brief") is None and artifact.get("brief") is not None:
            updated["brief"] = artifact["brief"]
        if updated.get("validation_mode") is None and artifact.get("validation_mode") is not None:
            updated["validation_mode"] = artifact["validation_mode"]
        if updated.get("gem_profile") is None and artifact.get("gem_profile") is not None:
            updated["gem_profile"] = artifact["gem_profile"]
        if updated.get("gem_selection_reason") is None and artifact.get("gem_selection_reason") is not None:
            updated["gem_selection_reason"] = artifact["gem_selection_reason"]
    elif step_id == StepId.CP2_PATHWAYS:
        if not updated.get("pathway_candidates") and artifact.get("pathway_candidates") is not None:
            updated["pathway_candidates"] = artifact["pathway_candidates"]
    elif step_id == StepId.CP3_FBA_PLAN:
        if updated.get("gem_profile") is None and artifact.get("gem_profile") is not None:
            updated["gem_profile"] = artifact["gem_profile"]
        if not updated.get("score_payloads") and artifact.get("score_payloads") is not None:
            updated["score_payloads"] = artifact["score_payloads"]
        if not updated.get("formalize_skipped") and artifact.get("skipped") is not None:
            updated["formalize_skipped"] = artifact["skipped"]
    elif step_id == StepId.CP4_FBA_RESULTS:
        if not updated.get("fba_results") and artifact.get("fba_results") is not None:
            updated["fba_results"] = artifact["fba_results"]
    elif step_id == StepId.CP3B_LITERATURE_PLAN:
        if updated.get("literature_plan") is None and artifact.get("literature_plan") is not None:
            updated["literature_plan"] = artifact["literature_plan"]
    elif step_id == StepId.CP5_REPORT:
        if updated.get("report") is None and artifact.get("report") is not None:
            updated["report"] = artifact["report"]
    return updated


def restore_prior_step_memory(state: dict, step_id: StepId, step_rows: list) -> dict:
    """Rebuild upstream state from persisted step artifacts when graph memory is missing."""
    by_id = {row.step_id: row for row in step_rows}
    updated = dict(state)
    for sid in step_pipeline(updated):
        if sid == step_id:
            break
        row = by_id.get(sid.value)
        if row and row.artifact:
            updated = merge_step_artifact_into_state(updated, sid, row.artifact)
        if sid == StepId.CP2_PATHWAYS and row:
            for decision in reversed(row.human_decisions or []):
                if decision.get("action") == "proceed":
                    selected = decision.get("selected_pathway_ids") or []
                    candidates = updated.get("pathway_candidates") or []
                    if selected:
                        updated["approved_candidates"] = [
                            c for c in candidates if c.get("id") in selected
                        ]
                    primary = decision.get("primary_pathway_id")
                    if primary:
                        updated["primary_pathway_id"] = primary
                    elif selected:
                        updated["primary_pathway_id"] = selected[0]
                    break
    return updated


def decision_block_reason(decision: HumanDecision, state: dict) -> str | None:
    """Return an error message when a human decision cannot be applied, else None."""
    from mindbrew_v2.settings import get_settings

    if decision.action == "revise":
        max_revisions = state.get("max_revisions", get_settings().max_revisions)
        if state.get("revision_number", 0) >= max_revisions:
            return (
                f"Cannot revise: maximum revision limit ({max_revisions}) reached. "
                "Proceed or start a new session."
            )

    if decision.action != "proceed":
        return None

    if decision.checkpoint == "cp1_spec":
        brief = state.get("brief") or {}
        verdict = brief.get("gatekeeper_verdict")
        if verdict == "REJECT":
            return (
                "Cannot proceed: the agent rejected this brief as outside biocatalysis / "
                "fermentation scope. Revise the brief or start a new session."
            )
        if verdict == "CLARIFY":
            questions = brief.get("clarifying_questions") or []
            base = "Cannot proceed: the agent needs clarification before continuing."
            if questions:
                return base + " Open questions: " + "; ".join(questions)
            return base + " Revise the brief with more detail."

    if decision.checkpoint == "cp2_pathways":
        candidates = state.get("pathway_candidates") or []
        if not candidates:
            return "Cannot proceed: no pathway candidates were found. Revise the search or retry."
        selected = decision.selected_pathway_ids or []
        if not selected:
            return "Cannot proceed: select at least one pathway before continuing."

    return None


def apply_decision_to_state(state: dict, decision: HumanDecision) -> dict:
    updated = dict(state)
    decisions = list(updated.get("human_decisions", []))
    decisions.append(decision.model_dump())
    updated["human_decisions"] = decisions
    updated["pending_checkpoint"] = None

    if decision.action == "proceed":
        if decision.selected_pathway_ids:
            candidates = updated.get("pathway_candidates", [])
            updated["approved_candidates"] = [
                c for c in candidates if c.get("id") in decision.selected_pathway_ids
            ]
        if decision.primary_pathway_id:
            updated["primary_pathway_id"] = decision.primary_pathway_id
        elif decision.selected_pathway_ids:
            updated["primary_pathway_id"] = decision.selected_pathway_ids[0]
    elif decision.action == "revise":
        updated["revision_number"] = updated.get("revision_number", 0) + 1
        updated["revision_notes"] = decision.notes or ""

    return updated
