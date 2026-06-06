"""LangGraph runner with SSE event conversion and interrupt support."""

from __future__ import annotations

import asyncio
import logging
import threading
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

from langgraph.types import Command

from api.db.database import get_session_factory
from api.services.run_registry import get_run_registry
from api.services.session_store import append_stream_event, update_session_status, upsert_step
from mindbrew_v2.errors import agent_error_event
from mindbrew_v2.graph import build_graph
from mindbrew_v2.models import HumanDecision, StepId, Ticket
from mindbrew_v2.phases.checkpoints import (
    CHECKPOINT_TO_STEP,
    NODE_TO_CHECKPOINT,
    WORK_NODE_TO_STEP,
    apply_decision_to_state,
    artifact_for_checkpoint,
    checkpoint_summary,
    decision_block_reason,
    downstream_steps,
    paused_at_step_checkpoint,
    prepare_step_restart_state,
    restart_anchor_for_step,
    restore_prior_step_memory,
    step_pipeline,
    STEP_TO_CHECKPOINT,
    work_node_for_step,
    STEP_WORK_NODE,
)

logger = logging.getLogger(__name__)

_graph = None
_checkpointer = None
_checkpointer_ctx = None
_GRAPH_VERSION = 3
_graph_version: int | None = None


class SessionInterrupted(Exception):
    """Raised when the user stops a running graph."""


def get_checkpointer():
    global _checkpointer, _checkpointer_ctx
    if _checkpointer is None:
        from api.db.database import normalize_database_url, psycopg_conn_string
        from mindbrew_v2.settings import ConfigurationError, get_settings

        settings = get_settings()
        url = normalize_database_url(settings.database_url)
        if url.startswith("sqlite"):
            from langgraph.checkpoint.memory import MemorySaver

            _checkpointer = MemorySaver()
        else:
            try:
                from langgraph.checkpoint.postgres import PostgresSaver

                _checkpointer_ctx = PostgresSaver.from_conn_string(
                    psycopg_conn_string(settings.database_url)
                )
                _checkpointer = _checkpointer_ctx.__enter__()
                _checkpointer.setup()
            except Exception as exc:
                raise ConfigurationError(
                    "Postgres LangGraph checkpointer failed to initialize. "
                    "Verify DATABASE_URL and that the database is reachable, "
                    "or use sqlite:// for local in-memory checkpoints."
                ) from exc
    return _checkpointer


def get_graph():
    global _graph, _graph_version
    if _graph is None or _graph_version != _GRAPH_VERSION:
        _graph = build_graph(checkpointer=get_checkpointer())
        _graph_version = _GRAPH_VERSION
    return _graph


def validate_decision(session_id: str, decision: HumanDecision, db) -> str | None:
    """Return an error message when a decision cannot be applied, else None."""
    from api.services.session_store import get_session

    row = get_session(db, session_id)
    if not row:
        return "Session not found"
    if row.status != "awaiting_user":
        return f"Cannot apply decision while session status is '{row.status}' (expected awaiting_user)."
    step_id = CHECKPOINT_TO_STEP.get(decision.checkpoint, StepId.CP1_SPEC).value
    if row.current_step != step_id:
        return f"Decision expected at step '{row.current_step}', not '{step_id}'."
    if is_session_active(session_id):
        return "Agent is already processing. Wait for the current step to finish."

    graph = get_graph()
    config = {"configurable": {"thread_id": session_id}}
    snapshot = graph.get_state(config)
    if not snapshot.values:
        return "No agent checkpoint found for this session. Start a new session or use Retry."
    current = dict(snapshot.values)
    return decision_block_reason(decision, current)


def _initial_state(session_id: str, raw_brief: str) -> dict:
    from mindbrew_v2.settings import get_settings

    return {
        "ticket": Ticket(id=session_id, raw_brief=raw_brief).model_dump(),
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
        "max_revisions": get_settings().max_revisions,
        "revision_notes": None,
    }


async def _iter_graph_stream(session_id: str, graph_input: Any, config: dict) -> AsyncIterator[tuple[str, Any]]:
    """Run sync graph.stream in a worker thread; yield progress events and graph chunks."""
    from mindbrew_v2.progress import get_current_node, heartbeat, reset_progress_emitter, set_progress_emitter
    from mindbrew_v2.settings import get_settings

    registry = get_run_registry()
    cancel = registry.register(session_id)
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()
    graph = get_graph()
    interval = get_settings().progress_heartbeat_interval_sec
    stop_heartbeat = threading.Event()

    def heartbeat_loop() -> None:
        while not stop_heartbeat.wait(interval):
            _, label = get_current_node()
            heartbeat(label=f"Still running: {label}" if label else "Still working…")

    def worker() -> None:
        token = set_progress_emitter(lambda evt: loop.call_soon_threadsafe(queue.put_nowait, ("progress", evt)))
        hb = threading.Thread(target=heartbeat_loop, daemon=True)
        hb.start()
        try:
            for chunk in graph.stream(graph_input, config):
                if cancel.is_set():
                    loop.call_soon_threadsafe(queue.put_nowait, ("interrupt", SessionInterrupted()))
                    return
                loop.call_soon_threadsafe(queue.put_nowait, ("chunk", chunk))
            loop.call_soon_threadsafe(queue.put_nowait, ("done", None))
        except Exception as exc:
            loop.call_soon_threadsafe(queue.put_nowait, ("error", exc))
        finally:
            stop_heartbeat.set()
            hb.join(timeout=1.0)
            reset_progress_emitter(token)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    try:
        while True:
            kind, item = await queue.get()
            if kind == "done":
                break
            if kind == "interrupt":
                raise item
            if kind == "error":
                raise item
            yield kind, item
    finally:
        registry.unregister(session_id)
        thread.join(timeout=0.5)


def _extract_interrupt(chunk: dict) -> dict | None:
    if not isinstance(chunk, dict) or "__interrupt__" not in chunk:
        return None
    val = chunk["__interrupt__"]
    if isinstance(val, (list, tuple)) and val:
        item = val[0]
        return item.value if hasattr(item, "value") else item
    if isinstance(val, dict):
        return val
    # interrupt_before yields an empty tuple — resolved via graph state later
    return {"__pending__": True}


def _checkpoint_from_graph_state(graph, config: dict) -> tuple[str, dict] | None:
    snapshot = graph.get_state(config)
    if not snapshot.next:
        return None
    next_node = snapshot.next[0]
    checkpoint = NODE_TO_CHECKPOINT.get(next_node)
    if not checkpoint:
        return None
    state = dict(snapshot.values) if snapshot.values else {}
    return checkpoint, artifact_for_checkpoint(checkpoint, state)


async def _emit_awaiting_user(
    session_id: str,
    db,
    checkpoint: str,
    artifact: dict,
) -> dict:
    step = CHECKPOINT_TO_STEP.get(checkpoint, StepId.CP1_SPEC).value
    upsert_step(db, session_id, step, "awaiting_user", artifact=artifact)
    update_session_status(db, session_id, "awaiting_user", current_step=step)
    evt = {
        "type": "awaiting_user",
        "step_id": step,
        "summary": checkpoint_summary(checkpoint, artifact),
        "artifact": artifact,
    }
    append_stream_event(db, session_id, "awaiting_user", evt)
    return evt


async def _handle_progress(session_id: str, db, event: dict) -> dict:
    """Persist a live progress/log event and return it for SSE."""
    row = append_stream_event(db, session_id, event["type"], event)
    return _enrich_event(event, row.seq, row.created_at)


def _enrich_event(event: dict, seq: int | None = None, created_at: datetime | None = None) -> dict:
    enriched = dict(event)
    if seq is not None:
        enriched["seq"] = seq
    if created_at is not None:
        enriched["ts"] = created_at.astimezone(UTC).isoformat()
    elif "ts" not in enriched:
        enriched["ts"] = datetime.now(UTC).isoformat()
    return enriched


async def _handle_chunk(session_id: str, chunk: dict, db, graph, config: dict) -> dict | None:
    """Process one graph chunk; return event to yield, or None."""
    interrupt_value = _extract_interrupt(chunk)
    if interrupt_value:
        if interrupt_value.get("__pending__"):
            resolved = _checkpoint_from_graph_state(graph, config)
            if not resolved:
                return None
            checkpoint, artifact = resolved
        else:
            checkpoint = interrupt_value.get("checkpoint", "cp1_spec")
            artifact = interrupt_value.get("artifact", {})
        return await _emit_awaiting_user(session_id, db, checkpoint, artifact)

    node_name = list(chunk.keys())[0] if chunk else None
    if node_name and node_name != "__interrupt__":
        step_id = WORK_NODE_TO_STEP.get(node_name, node_name)
        evt = {"type": "step_complete", "step_id": step_id, "node_id": node_name}
        append_stream_event(db, session_id, "step_complete", evt)
        return evt
    return None


async def _emit_interrupted(session_id: str, db, step_id: str | None = None) -> dict:
    update_session_status(db, session_id, "interrupted", current_step=step_id)
    evt = {
        "type": "interrupted",
        "step_id": step_id,
        "message": "Agent run stopped by user",
    }
    append_stream_event(db, session_id, "interrupted", evt)
    return evt


async def _finalize_graph_run(session_id: str, db, graph, config: dict) -> dict | None:
    """If the graph paused at a checkpoint, emit awaiting_user instead of completing."""
    resolved = _checkpoint_from_graph_state(graph, config)
    if not resolved:
        return None
    checkpoint, artifact = resolved
    return await _emit_awaiting_user(session_id, db, checkpoint, artifact)


async def _run_graph_loop(session_id: str, db, graph, config: dict, graph_input: Any) -> AsyncIterator[dict]:
    async for kind, payload in _iter_graph_stream(session_id, graph_input, config):
        if kind == "progress":
            yield await _handle_progress(session_id, db, payload)
            continue
        evt = await _handle_chunk(session_id, payload, db, graph, config)
        if evt:
            if evt["type"] == "awaiting_user":
                yield evt
                return
            yield evt

    pending = await _finalize_graph_run(session_id, db, graph, config)
    if pending:
        yield pending
        return

    update_session_status(db, session_id, "completed", current_step=StepId.CP5_REPORT.value)
    yield {"type": "step_complete", "step_id": "done"}


async def run_session_graph(session_id: str, raw_brief: str) -> AsyncIterator[dict]:
    graph = get_graph()
    config = {"configurable": {"thread_id": session_id}}
    state = _initial_state(session_id, raw_brief)
    db = get_session_factory()()
    current_step = StepId.CP1_SPEC.value

    try:
        yield {"type": "step_start", "step_id": current_step}
        append_stream_event(db, session_id, "step_start", {"step_id": current_step})

        async for evt in _run_graph_loop(session_id, db, graph, config, state):
            yield evt
    except SessionInterrupted:
        evt = await _emit_interrupted(session_id, db, current_step)
        yield evt
    except asyncio.CancelledError:
        evt = await _emit_interrupted(session_id, db, current_step)
        yield evt
        raise
    except Exception as exc:
        db.rollback()
        logger.exception("Session %s failed", session_id)
        update_session_status(db, session_id, "failed")
        err = agent_error_event(exc)
        append_stream_event(db, session_id, "error", err)
        yield err
    finally:
        db.close()


async def resume_session(session_id: str, decision: HumanDecision) -> AsyncIterator[dict]:
    graph = get_graph()
    config = {"configurable": {"thread_id": session_id}}
    db = get_session_factory()()
    step_id = CHECKPOINT_TO_STEP.get(decision.checkpoint, StepId.CP1_SPEC).value

    from api.services.session_store import append_decision, get_session

    row = get_session(db, session_id)
    if not row:
        yield {"type": "error", "message": "Session not found"}
        db.close()
        return
    if row.status not in ("awaiting_user", "running"):
        yield {
            "type": "error",
            "message": f"Cannot apply decision while session status is '{row.status}'.",
        }
        db.close()
        return
    if row.current_step != step_id:
        yield {
            "type": "error",
            "message": f"Decision expected at step '{row.current_step}', not '{step_id}'.",
        }
        db.close()
        return

    append_decision(db, session_id, step_id, decision)

    snapshot = graph.get_state(config)
    if not snapshot.values:
        yield {
            "type": "error",
            "message": "No agent checkpoint found for this session. Try Retry to restart the run.",
        }
        db.close()
        return

    current = dict(snapshot.values)

    block_reason = decision_block_reason(decision, current)
    if block_reason:
        err = {"type": "error", "message": block_reason}
        append_stream_event(db, session_id, "error", err)
        yield err
        db.close()
        return

    if decision.action == "reject":
        update_session_status(db, session_id, "failed")
        upsert_step(db, session_id, step_id, "completed")
        err = {"type": "error", "message": "Session rejected by user"}
        append_stream_event(db, session_id, "error", err)
        yield err
        db.close()
        return

    current = apply_decision_to_state(current, decision)
    graph.update_state(config, current)
    step_status = "completed" if decision.action == "proceed" else "running"
    upsert_step(
        db,
        session_id,
        step_id,
        step_status,
        artifact=artifact_for_checkpoint(decision.checkpoint, current),
    )

    try:
        update_session_status(
            db,
            session_id,
            "running",
            current_step=step_id,
            validation_mode=current.get("validation_mode"),
        )
        async for evt in _run_graph_loop(session_id, db, graph, config, Command(resume=True)):
            yield evt
    except SessionInterrupted:
        evt = await _emit_interrupted(session_id, db, step_id)
        yield evt
    except asyncio.CancelledError:
        evt = await _emit_interrupted(session_id, db, step_id)
        yield evt
        raise
    except Exception as exc:
        db.rollback()
        logger.exception("Session %s resume failed", session_id)
        update_session_status(db, session_id, "failed")
        err = agent_error_event(exc)
        append_stream_event(db, session_id, "error", err)
        yield err
    finally:
        db.close()


def validate_session_retry(session_id: str, db) -> str | None:
    """Return an error message when a failed/interrupted session cannot be retried."""
    from api.services.session_store import get_session

    graph = get_graph()
    config = {"configurable": {"thread_id": session_id}}
    snapshot = graph.get_state(config)
    row = get_session(db, session_id)
    if snapshot.values or (row and row.steps):
        step_id = row.current_step if row else StepId.CP1_SPEC.value
        return validate_step_restart(session_id, step_id, db)
    return None


def validate_step_restart(session_id: str, step_id: str, db) -> str | None:
    """Return an error message when a step cannot be restarted, else None."""
    from api.services.session_store import get_session

    try:
        sid = StepId(step_id)
    except ValueError:
        return f"Invalid step_id: {step_id}"
    if sid not in STEP_WORK_NODE:
        return f"Invalid step_id: {step_id}"

    row = get_session(db, session_id)
    if not row:
        return "Session not found"
    if row.current_step != step_id:
        if row.status not in ("awaiting_user", "failed", "interrupted"):
            return f"Can only restart the active step '{row.current_step}', not '{step_id}'."
        pipeline = step_pipeline({"validation_mode": row.validation_mode})
        try:
            target_idx = list(pipeline).index(sid)
            current_idx = list(pipeline).index(StepId(row.current_step))
        except ValueError:
            return f"Can only restart the active step '{row.current_step}', not '{step_id}'."
        if target_idx >= current_idx:
            return f"Can only restart the active step '{row.current_step}', not '{step_id}'."
    if row.status not in ("awaiting_user", "failed", "interrupted"):
        return f"Cannot restart step while session status is '{row.status}'."
    if is_session_active(session_id):
        return "Agent is already processing. Stop the agent first or wait for it to finish."
    return None


def _load_restart_state(session_id: str, step_id: StepId, raw_brief: str, db) -> dict | None:
    """Load graph state for restart, restoring prior-step memory from DB if needed."""
    from api.services.session_store import get_session

    row = get_session(db, session_id)
    if not row:
        return None

    graph = get_graph()
    config = {"configurable": {"thread_id": session_id}}
    snapshot = graph.get_state(config)
    base = dict(snapshot.values) if snapshot.values else _initial_state(session_id, raw_brief)
    state = prepare_step_restart_state(base, step_id)
    return restore_prior_step_memory(state, step_id, row.steps or [])


def _archive_pathway_run_if_needed(db, session_id: str, step_id: StepId, current: dict) -> None:
    """Persist downstream FBA artifacts before restarting pathway selection."""
    from sqlalchemy import select

    from api.db.models import StepRow

    if step_id != StepId.CP2_PATHWAYS:
        return

    cp3 = db.scalars(
        select(StepRow).where(
            StepRow.session_id == session_id,
            StepRow.step_id == StepId.CP3_FBA_PLAN.value,
        )
    ).first()
    if not cp3 or not cp3.artifact:
        return
    score_payloads = cp3.artifact.get("score_payloads") or []
    if not score_payloads:
        return

    cp4 = db.scalars(
        select(StepRow).where(
            StepRow.session_id == session_id,
            StepRow.step_id == StepId.CP4_FBA_RESULTS.value,
        )
    ).first()
    cp2 = db.scalars(
        select(StepRow).where(
            StepRow.session_id == session_id,
            StepRow.step_id == StepId.CP2_PATHWAYS.value,
        )
    ).first()

    primary = current.get("primary_pathway_id")
    if not primary and score_payloads:
        primary = score_payloads[0].get("pathway_id")

    entry = {
        "pathway_id": primary,
        "revision_number": current.get("revision_number", 0),
        "cp3_fba_plan": cp3.artifact,
    }
    if cp4 and cp4.artifact:
        entry["cp4_fba_results"] = cp4.artifact

    cp2_artifact = dict(cp2.artifact if cp2 and cp2.artifact else {})
    history = list(cp2_artifact.get("_pathway_run_history") or [])
    if history:
        last = history[-1]
        if last.get("pathway_id") == entry["pathway_id"] and last.get("revision_number") == entry["revision_number"]:
            return
    history.append(entry)
    cp2_artifact["_pathway_run_history"] = history
    upsert_step(
        db,
        session_id,
        StepId.CP2_PATHWAYS.value,
        cp2.status if cp2 else "completed",
        artifact=cp2_artifact,
    )


async def restart_session_step(session_id: str, step_id: str) -> AsyncIterator[dict]:
    """Re-run the current step while preserving artifacts from prior steps."""
    from api.services.session_store import get_session

    graph = get_graph()
    config = {"configurable": {"thread_id": session_id}}
    db = get_session_factory()()

    try:
        sid = StepId(step_id)
    except ValueError:
        yield {"type": "error", "message": f"Invalid step_id: {step_id}"}
        db.close()
        return

    row = get_session(db, session_id)
    if not row:
        yield {"type": "error", "message": "Session not found"}
        db.close()
        return

    block = validate_step_restart(session_id, step_id, db)
    if block:
        yield {"type": "error", "message": block}
        db.close()
        return

    current = _load_restart_state(session_id, sid, row.raw_brief, db)
    if not current:
        yield {"type": "error", "message": "Could not load session state for restart."}
        db.close()
        return

    _archive_pathway_run_if_needed(db, session_id, sid, current)

    snapshot = graph.get_state(config)
    if snapshot.values and paused_at_step_checkpoint(snapshot, sid):
        checkpoint = STEP_TO_CHECKPOINT[sid]
        routed = dict(current)
        routed["human_decisions"] = list(routed.get("human_decisions", [])) + [
            {"checkpoint": checkpoint, "action": "revise", "notes": None}
        ]
        routed["revision_number"] = routed.get("revision_number", 0) + 1
        graph.update_state(config, routed)
        graph_input: Any = Command(resume=True)
    else:
        # Anchor graph position with as_node so a stale next pointer does not run
        # alongside Command(goto=...), which causes concurrent __root__ writes.
        anchor = restart_anchor_for_step(sid, current)
        if anchor:
            graph.update_state(config, current, as_node=anchor)
        else:
            graph.update_state(config, current)
        graph_input = None

    for downstream in downstream_steps(current, sid):
        upsert_step(db, session_id, downstream.value, "pending", artifact=None)

    upsert_step(db, session_id, step_id, "running", revision_number=current.get("revision_number", 0))
    update_session_status(
        db,
        session_id,
        "running",
        current_step=step_id,
        validation_mode=current.get("validation_mode"),
    )
    evt = {"type": "step_restart", "step_id": step_id, "message": f"Restarting step {step_id}"}
    append_stream_event(db, session_id, "step_restart", evt)
    yield evt

    try:
        async for run_evt in _run_graph_loop(session_id, db, graph, config, graph_input):
            yield run_evt
    except SessionInterrupted:
        evt = await _emit_interrupted(session_id, db, step_id)
        yield evt
    except asyncio.CancelledError:
        evt = await _emit_interrupted(session_id, db, step_id)
        yield evt
        raise
    except Exception as exc:
        db.rollback()
        logger.exception("Session %s step restart failed", session_id)
        update_session_status(db, session_id, "failed")
        err = agent_error_event(exc)
        append_stream_event(db, session_id, "error", err)
        yield err
    finally:
        db.close()


async def retry_session_graph(session_id: str, raw_brief: str) -> AsyncIterator[dict]:
    """Retry after failure — restart current step with prior memory when possible."""
    from api.services.session_store import get_session

    graph = get_graph()
    config = {"configurable": {"thread_id": session_id}}
    snapshot = graph.get_state(config)
    db = get_session_factory()()
    row = get_session(db, session_id)
    db.close()

    if snapshot.values or (row and row.steps):
        step_id = row.current_step if row else StepId.CP1_SPEC.value
        async for evt in restart_session_step(session_id, step_id):
            yield evt
    else:
        async for evt in run_session_graph(session_id, raw_brief):
            yield evt


def is_session_active(session_id: str) -> bool:
    return get_run_registry().is_active(session_id)


def interrupt_session(session_id: str) -> bool:
    return get_run_registry().interrupt(session_id)


async def continue_session_graph(session_id: str) -> AsyncIterator[dict]:
    """Resume graph from last LangGraph checkpoint after user interrupt."""
    graph = get_graph()
    config = {"configurable": {"thread_id": session_id}}
    db = get_session_factory()()
    row_step = StepId.CP1_SPEC.value

    try:
        async for evt in _run_graph_loop(session_id, db, graph, config, Command(resume=True)):
            if evt.get("step_id"):
                row_step = evt["step_id"]
            yield evt
    except SessionInterrupted:
        evt = await _emit_interrupted(session_id, db, row_step)
        yield evt
    except asyncio.CancelledError:
        evt = await _emit_interrupted(session_id, db, row_step)
        yield evt
        raise
    except Exception as exc:
        db.rollback()
        logger.exception("Session %s continue failed", session_id)
        update_session_status(db, session_id, "failed")
        err = agent_error_event(exc)
        append_stream_event(db, session_id, "error", err)
        yield err
    finally:
        db.close()
