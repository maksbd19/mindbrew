"""Session API routes."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from api.db.database import get_db, get_session_factory
from api.services import graph_runner
from api.services.graph_runner import _enrich_event
from api.services.session_store import (
    append_stream_event,
    create_session,
    delete_session,
    get_session,
    get_stream_events,
    list_sessions,
    update_session_status,
    update_session_title,
)
from api.services.title_inference import infer_session_title, is_auto_title
from mindbrew_v2.export.report_export import export_report_docx, export_report_pdf, safe_filename
from mindbrew_v2.models import HumanDecision, StepId
from mindbrew_v2.phases.checkpoints import STEP_TO_CHECKPOINT

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["sessions"])

_running: dict[str, asyncio.Task] = {}


class CreateSessionRequest(BaseModel):
    raw_brief: str
    title: str | None = None


class DecideRequest(BaseModel):
    action: str
    notes: str | None = None
    selected_pathway_ids: list[str] | None = None
    primary_pathway_id: str | None = None


class SwitchPathwayRequest(BaseModel):
    selected_pathway_ids: list[str]
    primary_pathway_id: str | None = None


class UpdateSessionRequest(BaseModel):
    title: str


class SuggestTitleRequest(BaseModel):
    force: bool = False


def _session_summary_dict(row) -> dict[str, Any]:
    return {
        "id": row.id,
        "title": row.title,
        "brief_preview": _brief_preview(row.raw_brief),
        "status": row.status,
        "current_step": row.current_step,
        "validation_mode": row.validation_mode,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _session_to_dict(row, session_id: str | None = None) -> dict[str, Any]:
    sid = session_id or row.id
    agent_active = sid in _running or graph_runner.is_session_active(sid)
    return {
        "id": row.id,
        "title": row.title,
        "raw_brief": row.raw_brief,
        "status": row.status,
        "current_step": row.current_step,
        "validation_mode": row.validation_mode,
        "agent_active": agent_active,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        "steps": [
            {
                "step_id": s.step_id,
                "status": s.status,
                "revision_number": s.revision_number,
                "artifact": s.artifact,
                "human_decisions": s.human_decisions or [],
            }
            for s in (row.steps or [])
        ],
    }


def _track_task(session_id: str, coro) -> asyncio.Task:
    task = asyncio.create_task(coro)

    def _done(t: asyncio.Task) -> None:
        _running.pop(session_id, None)
        if t.cancelled():
            return
        exc = t.exception()
        if exc:
            logger.exception("Background task for session %s failed", session_id, exc_info=exc)

    task.add_done_callback(_done)
    _running[session_id] = task
    return task


def _brief_preview(raw_brief: str, limit: int = 120) -> str:
    text = " ".join(raw_brief.split())
    return text if len(text) <= limit else f"{text[: limit - 1]}…"


def _report_from_session(row) -> tuple[str, str]:
    for step in row.steps or []:
        if step.step_id != "cp5_report" or not step.artifact:
            continue
        report = step.artifact.get("report") or {}
        markdown = report.get("markdown")
        if isinstance(markdown, str) and markdown.strip():
            filename_base = safe_filename(row.title or "brewmind-report")
            return markdown, filename_base
    raise HTTPException(404, "Report not available")


@router.get("/{session_id}/report/export")
def export_report(
    session_id: str,
    format: Literal["pdf", "docx"],
    db: Session = Depends(get_db),
):
    row = get_session(db, session_id)
    if not row:
        raise HTTPException(404, "Session not found")

    markdown, filename_base = _report_from_session(row)
    try:
        if format == "pdf":
            content = export_report_pdf(markdown)
            media_type = "application/pdf"
            filename = f"{filename_base}.pdf"
        else:
            content = export_report_docx(markdown)
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            filename = f"{filename_base}.docx"
    except RuntimeError as exc:
        raise HTTPException(500, str(exc)) from exc

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _reject_action(db: Session, session_id: str, action: str, reason: str) -> None:
    append_stream_event(
        db,
        session_id,
        "action_rejected",
        {"type": "action_rejected", "action": action, "message": reason},
    )


def _event_payload(ev) -> dict[str, Any]:
    return _enrich_event({"type": ev.event_type, **ev.payload}, ev.seq, ev.created_at)


@router.get("")
def list_all(page: int = 1, page_size: int = 20, db: Session = Depends(get_db)):
    rows, total = list_sessions(db, page=page, page_size=page_size)
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    total_pages = max(1, (total + page_size - 1) // page_size) if total else 1
    return {
        "items": [_session_summary_dict(r) for r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.post("")
async def create(body: CreateSessionRequest, db: Session = Depends(get_db)):
    row = create_session(db, body.raw_brief, body.title)
    append_stream_event(
        db,
        row.id,
        "session_created",
        {
            "type": "session_created",
            "session_id": row.id,
            "content": _brief_preview(body.raw_brief),
        },
    )
    _track_task(row.id, _run_graph_background(row.id, body.raw_brief))
    if body.title is None:
        asyncio.create_task(_infer_title_background(row.id, body.raw_brief))
    return _session_to_dict(row)


async def _infer_title_background(session_id: str, raw_brief: str) -> None:
    from api.db.database import get_session_factory

    try:
        title = await asyncio.to_thread(infer_session_title, raw_brief)
    except Exception:
        logger.exception("Failed to infer title for session %s", session_id)
        return

    db = get_session_factory()()
    try:
        row = get_session(db, session_id)
        if row and is_auto_title(row.title, row.raw_brief):
            update_session_title(db, session_id, title)
            graph_runner.sync_session_title(session_id, title)
    finally:
        db.close()


async def _run_graph_background(session_id: str, raw_brief: str):
    async for _ in graph_runner.run_session_graph(session_id, raw_brief):
        pass


async def _run_continue_background(session_id: str):
    async for _ in graph_runner.continue_session_graph(session_id):
        pass


async def _run_decide_background(session_id: str, decision: HumanDecision):
    async for _ in graph_runner.resume_session(session_id, decision):
        pass


async def _run_restart_background(session_id: str, step_id: str):
    async for _ in graph_runner.restart_session_step(session_id, step_id):
        pass


async def _run_pathway_switch_background(
    session_id: str,
    selected_pathway_ids: list[str],
    primary_pathway_id: str | None,
):
    async for _ in graph_runner.switch_pathway_and_proceed(
        session_id, selected_pathway_ids, primary_pathway_id
    ):
        pass


@router.get("/{session_id}")
def get_one(session_id: str, db: Session = Depends(get_db)):
    row = get_session(db, session_id)
    if not row:
        raise HTTPException(404, "Session not found")
    return _session_to_dict(row)


@router.patch("/{session_id}")
def update_one(session_id: str, body: UpdateSessionRequest, db: Session = Depends(get_db)):
    row = get_session(db, session_id)
    if not row:
        raise HTTPException(404, "Session not found")
    updated = update_session_title(db, session_id, body.title)
    if not updated:
        raise HTTPException(404, "Session not found")
    graph_runner.sync_session_title(session_id, updated.title)
    return _session_to_dict(updated, session_id)


@router.post("/{session_id}/title/suggest")
async def suggest_title(
    session_id: str,
    body: SuggestTitleRequest | None = None,
    db: Session = Depends(get_db),
):
    row = get_session(db, session_id)
    if not row:
        raise HTTPException(404, "Session not found")

    force = body.force if body else False
    if not force and not is_auto_title(row.title, row.raw_brief):
        return _session_to_dict(row, session_id)

    try:
        title = await asyncio.to_thread(infer_session_title, row.raw_brief)
    except Exception as exc:
        logger.exception("Failed to infer title for session %s", session_id)
        raise HTTPException(502, "Could not generate title") from exc

    updated = update_session_title(db, session_id, title)
    if not updated:
        raise HTTPException(404, "Session not found")
    graph_runner.sync_session_title(session_id, updated.title)
    return _session_to_dict(updated, session_id)


@router.post("/{session_id}/interrupt")
async def interrupt(session_id: str, db: Session = Depends(get_db)):
    row = get_session(db, session_id)
    if not row:
        raise HTTPException(404, "Session not found")

    agent_active = session_id in _running or graph_runner.is_session_active(session_id)
    if not agent_active and row.status != "running":
        # Already stopped — idempotent success
        return {"ok": True, "status": row.status, "message": "Agent is not running"}

    graph_runner.interrupt_session(session_id)
    task = _running.pop(session_id, None)
    if task and not task.done():
        task.cancel()

    if row.status == "running" or agent_active:
        update_session_status(db, session_id, "interrupted", current_step=row.current_step)
        append_stream_event(
            db,
            session_id,
            "user_interrupt",
            {
                "type": "user_interrupt",
                "step_id": row.current_step,
                "content": "Agent run stopped by user",
            },
        )

    return {"ok": True, "status": "interrupted"}


@router.post("/{session_id}/retry")
async def retry_failed(session_id: str, db: Session = Depends(get_db)):
    row = get_session(db, session_id)
    if not row:
        raise HTTPException(404, "Session not found")
    if row.status not in ("failed", "interrupted"):
        _reject_action(db, session_id, "session_retry", f"Session cannot be retried (status={row.status})")
        raise HTTPException(409, f"Session cannot be retried (status={row.status})")
    if session_id in _running:
        _reject_action(db, session_id, "session_retry", "Session is already running")
        raise HTTPException(409, "Session is already running")

    error = graph_runner.validate_session_retry(session_id, db)
    if error:
        _reject_action(db, session_id, "session_retry", error)
        raise HTTPException(409, error)

    append_stream_event(
        db,
        session_id,
        "session_retry",
        {"type": "session_retry", "step_id": row.current_step, "content": "Retrying failed session"},
    )
    _track_task(session_id, _run_retry_background(session_id, row.raw_brief))
    db.refresh(row)
    return _session_to_dict(row, session_id)


async def _run_retry_background(session_id: str, raw_brief: str):
    async for _ in graph_runner.retry_session_graph(session_id, raw_brief):
        pass


@router.post("/{session_id}/resume")
async def resume_interrupted(session_id: str, db: Session = Depends(get_db)):
    row = get_session(db, session_id)
    if not row:
        raise HTTPException(404, "Session not found")
    if row.status != "interrupted":
        _reject_action(db, session_id, "user_resume", f"Session is not interrupted (status={row.status})")
        raise HTTPException(409, f"Session is not interrupted (status={row.status})")
    if session_id in _running:
        _reject_action(db, session_id, "user_resume", "Session is already running")
        raise HTTPException(409, "Session is already running")
    update_session_status(db, session_id, "running")
    append_stream_event(
        db,
        session_id,
        "user_resume",
        {"type": "user_resume", "step_id": row.current_step, "content": "Resuming interrupted session"},
    )
    _track_task(session_id, _run_continue_background(session_id))
    return {"ok": True, "status": "running"}


@router.delete("/{session_id}")
def remove(session_id: str, db: Session = Depends(get_db)):
    if not get_session(db, session_id):
        raise HTTPException(404, "Session not found")
    graph_runner.interrupt_session(session_id)
    task = _running.pop(session_id, None)
    if task:
        task.cancel()
    if not delete_session(db, session_id):
        raise HTTPException(404, "Session not found")
    return {"ok": True}


@router.get("/{session_id}/events")
def list_events(session_id: str, after_seq: int = 0, db: Session = Depends(get_db)):
    if not get_session(db, session_id):
        raise HTTPException(404, "Session not found")
    events = get_stream_events(db, session_id, after_seq=after_seq)
    return [_event_payload(ev) for ev in events]


@router.get("/{session_id}/stream")
async def stream(session_id: str, after_seq: int = 0):
    SessionLocal = get_session_factory()
    probe = SessionLocal()
    try:
        if not get_session(probe, session_id):
            raise HTTPException(404, "Session not found")
    finally:
        probe.close()

    async def event_generator():
        seen = after_seq
        while True:
            db = SessionLocal()
            try:
                row = get_session(db, session_id)
                if not row:
                    break
                events = get_stream_events(db, session_id, after_seq=seen)
                status = row.status
                for ev in events:
                    seen = ev.seq
                    yield {"event": "message", "data": json.dumps(_event_payload(ev))}
            finally:
                db.close()

            agent_active = session_id in _running or graph_runner.is_session_active(session_id)
            if (
                status in ("awaiting_user", "completed", "failed", "interrupted")
                and not events
                and not agent_active
            ):
                if status == "completed":
                    yield {"event": "message", "data": json.dumps({"type": "done"})}
                break
            await asyncio.sleep(0.25 if agent_active else 0.5)

    return EventSourceResponse(event_generator())


@router.post("/{session_id}/pathway/switch")
async def switch_pathway(session_id: str, body: SwitchPathwayRequest, db: Session = Depends(get_db)):
    row = get_session(db, session_id)
    if not row:
        raise HTTPException(404, "Session not found")

    decision = HumanDecision(
        checkpoint="cp2_pathways",
        action="proceed",
        selected_pathway_ids=body.selected_pathway_ids,
        primary_pathway_id=body.primary_pathway_id,
    )
    error = graph_runner.validate_pathway_switch(session_id, decision, db)
    if error:
        _reject_action(db, session_id, "pathway_switch_requested", error)
        raise HTTPException(409, error)

    if session_id in _running:
        _reject_action(db, session_id, "pathway_switch_requested", "Agent is already processing")
        raise HTTPException(409, "Agent is already processing")

    append_stream_event(
        db,
        session_id,
        "pathway_switch_requested",
        {
            "type": "pathway_switch_requested",
            "primary_pathway_id": body.primary_pathway_id or (body.selected_pathway_ids[0] if body.selected_pathway_ids else None),
        },
    )
    _track_task(
        session_id,
        _run_pathway_switch_background(session_id, body.selected_pathway_ids, body.primary_pathway_id),
    )
    db.refresh(row)
    return _session_to_dict(row, session_id)


@router.post("/{session_id}/steps/{step_id}/restart")
async def restart_step(session_id: str, step_id: str, db: Session = Depends(get_db)):
    row = get_session(db, session_id)
    if not row:
        raise HTTPException(404, "Session not found")

    error = graph_runner.validate_step_restart(session_id, step_id, db)
    if error:
        _reject_action(db, session_id, "step_restart_requested", error)
        raise HTTPException(409, error)

    if session_id in _running:
        _reject_action(db, session_id, "step_restart_requested", "Agent is already processing")
        raise HTTPException(409, "Agent is already processing")

    append_stream_event(
        db,
        session_id,
        "step_restart_requested",
        {"type": "step_restart_requested", "step_id": step_id},
    )
    _track_task(session_id, _run_restart_background(session_id, step_id))
    db.refresh(row)
    return _session_to_dict(row, session_id)


@router.post("/{session_id}/steps/{step_id}/decide")
async def decide(
    session_id: str,
    step_id: str,
    body: DecideRequest,
    db: Session = Depends(get_db),
):
    row = get_session(db, session_id)
    if not row:
        raise HTTPException(404, "Session not found")

    try:
        sid = StepId(step_id)
        checkpoint = STEP_TO_CHECKPOINT[sid]
    except (ValueError, KeyError):
        raise HTTPException(400, f"Invalid step_id: {step_id}")

    decision = HumanDecision(
        checkpoint=checkpoint,
        action=body.action,  # type: ignore[arg-type]
        notes=body.notes,
        selected_pathway_ids=body.selected_pathway_ids,
        primary_pathway_id=body.primary_pathway_id,
    )

    error = graph_runner.validate_decision(session_id, decision, db)
    if error:
        _reject_action(db, session_id, "decide", error)
        raise HTTPException(409, error)

    if session_id in _running:
        _reject_action(db, session_id, "decide", "Agent is already processing")
        raise HTTPException(409, "Agent is already processing")

    update_session_status(db, session_id, "running", current_step=step_id)
    notes_snippet = None
    if body.notes:
        notes_snippet = body.notes if len(body.notes) <= 80 else f"{body.notes[:77]}…"
    append_stream_event(
        db,
        session_id,
        "decision_accepted",
        {
            "type": "decision_accepted",
            "action": body.action,
            "step_id": step_id,
            "notes": notes_snippet,
        },
    )
    _track_task(session_id, _run_decide_background(session_id, decision))
    db.refresh(row)
    return _session_to_dict(row, session_id)
