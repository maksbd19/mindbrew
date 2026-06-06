"""Session persistence service."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.db.models import SessionRow, StepRow, StreamEventRow
from mindbrew_v2.models import HumanDecision, StepId


def create_session(db: Session, raw_brief: str, title: str | None = None) -> SessionRow:
    snippet = raw_brief.strip().replace("\n", " ")[:80]
    row = SessionRow(
        title=title or snippet or "New session",
        raw_brief=raw_brief,
        status="running",
        current_step=StepId.CP1_SPEC.value,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_sessions(db: Session, *, page: int = 1, page_size: int = 20) -> tuple[list[SessionRow], int]:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    total = db.scalar(select(func.count()).select_from(SessionRow)) or 0
    rows = list(
        db.scalars(
            select(SessionRow)
            .order_by(SessionRow.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return rows, total


def get_session(db: Session, session_id: str) -> SessionRow | None:
    return db.get(SessionRow, session_id)


def delete_session(db: Session, session_id: str) -> bool:
    row = db.get(SessionRow, session_id)
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


def update_session_status(
    db: Session,
    session_id: str,
    status: str,
    current_step: str | None = None,
    validation_mode: str | None = None,
) -> None:
    row = db.get(SessionRow, session_id)
    if not row:
        return
    row.status = status
    if current_step:
        row.current_step = current_step
    if validation_mode:
        row.validation_mode = validation_mode
    row.updated_at = datetime.now(timezone.utc)
    db.commit()


def upsert_step(
    db: Session,
    session_id: str,
    step_id: str,
    status: str,
    artifact: dict | None = None,
    revision_number: int | None = None,
) -> StepRow:
    existing = db.scalars(
        select(StepRow).where(StepRow.session_id == session_id, StepRow.step_id == step_id)
    ).first()
    if existing:
        existing.status = status
        if artifact is not None:
            existing.artifact = artifact
        if revision_number is not None:
            existing.revision_number = revision_number
        db.commit()
        db.refresh(existing)
        return existing

    row = StepRow(
        session_id=session_id,
        step_id=step_id,
        status=status,
        artifact=artifact,
        revision_number=revision_number or 0,
        human_decisions=[],
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def append_decision(db: Session, session_id: str, step_id: str, decision: HumanDecision) -> None:
    row = db.scalars(
        select(StepRow).where(StepRow.session_id == session_id, StepRow.step_id == step_id)
    ).first()
    if not row:
        row = StepRow(session_id=session_id, step_id=step_id, status="completed", human_decisions=[])
        db.add(row)
    decisions = list(row.human_decisions or [])
    decisions.append(decision.model_dump())
    row.human_decisions = decisions
    db.commit()


def append_stream_event(db: Session, session_id: str, event_type: str, payload: dict) -> StreamEventRow:
    count = db.scalar(
        select(StreamEventRow.seq)
        .where(StreamEventRow.session_id == session_id)
        .order_by(StreamEventRow.seq.desc())
        .limit(1)
    )
    seq = (count or 0) + 1
    row = StreamEventRow(session_id=session_id, seq=seq, event_type=event_type, payload=payload)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_stream_events(db: Session, session_id: str, after_seq: int = 0) -> list[StreamEventRow]:
    return list(
        db.scalars(
            select(StreamEventRow)
            .where(StreamEventRow.session_id == session_id, StreamEventRow.seq > after_seq)
            .order_by(StreamEventRow.seq)
        ).all()
    )
