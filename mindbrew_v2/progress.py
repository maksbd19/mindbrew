"""Thread-safe progress events for long-running graph nodes."""

from __future__ import annotations

import threading
import time
from contextvars import ContextVar, Token
from typing import Any, Callable, Literal

from mindbrew_v2.telemetry import record_metric

_Emitter: ContextVar[Callable[[dict[str, Any]], None] | None] = ContextVar(
    "progress_emitter", default=None
)

_emitter_lock = threading.Lock()
_shared_emitter: Callable[[dict[str, Any]], None] | None = None

_node_lock = threading.Lock()
_current_node_id: str | None = None
_current_node_label: str | None = None
_node_started_at: float | None = None


def set_progress_emitter(fn: Callable[[dict[str, Any]], None] | None) -> Token:
    global _shared_emitter
    with _emitter_lock:
        _shared_emitter = fn
    return _Emitter.set(fn)


def reset_progress_emitter(token: Token) -> None:
    global _shared_emitter
    _Emitter.reset(token)
    with _emitter_lock:
        _shared_emitter = None
    clear_current_node()


def emit_progress(event: dict[str, Any]) -> None:
    fn = _Emitter.get()
    if fn is None:
        with _emitter_lock:
            fn = _shared_emitter
    if fn:
        fn(event)


def get_current_node() -> tuple[str | None, str | None]:
    with _node_lock:
        return _current_node_id, _current_node_label


def clear_current_node() -> None:
    global _current_node_id, _current_node_label, _node_started_at
    with _node_lock:
        _current_node_id = None
        _current_node_label = None
        _node_started_at = None


def log(message: str, *, level: str = "info", phase: str | None = None) -> None:
    event: dict[str, Any] = {"type": "log", "content": message, "level": level}
    if phase:
        event["phase"] = phase
    emit_progress(event)


def log_phase(phase: str, detail: str, *, level: str = "info") -> None:
    log(detail, level=level, phase=phase)


def log_timing(label: str, seconds: float) -> None:
    log(f"{label} finished in {seconds:.1f}s")


def heartbeat(node_id: str | None = None, label: str | None = None) -> None:
    nid, nlbl = get_current_node()
    emit_progress(
        {
            "type": "heartbeat",
            "node_id": node_id or nid,
            "content": label or nlbl or "Still working…",
        }
    )


def node_start(
    node_id: str,
    label: str,
    *,
    stage: Literal["work", "review"] = "work",
) -> None:
    global _current_node_id, _current_node_label, _node_started_at
    with _node_lock:
        _current_node_id = node_id
        _current_node_label = label
        _node_started_at = time.perf_counter()

    event = {
        "type": "node_start",
        "node_id": node_id,
        "content": label,
        "stage": stage,
    }
    emit_progress(event)


def node_end(
    node_id: str,
    label: str,
    *,
    stage: Literal["work", "review"] = "work",
    status: Literal["ok", "error"] = "ok",
    started_at: float | None = None,
) -> None:
    global _current_node_id, _current_node_label, _node_started_at

    duration_ms: int | None = None
    with _node_lock:
        start = started_at if started_at is not None else _node_started_at
        if start is not None:
            duration_ms = int((time.perf_counter() - start) * 1000)

    event: dict[str, Any] = {
        "type": "node_end",
        "node_id": node_id,
        "content": label,
        "stage": stage,
        "status": status,
    }
    if duration_ms is not None:
        event["duration_ms"] = duration_ms
    emit_progress(event)

    if duration_ms is not None:
        record_metric(
            "node.duration_ms",
            float(duration_ms),
            {"node_id": node_id, "stage": stage, "status": status},
        )

    with _node_lock:
        if _current_node_id == node_id:
            _current_node_id = None
            _current_node_label = None
            _node_started_at = None


def tool_start(tool_id: str, label: str) -> None:
    event = {
        "type": "tool_start",
        "tool_id": tool_id,
        "content": label,
    }
    emit_progress(event)


def tool_end(
    tool_id: str,
    label: str,
    *,
    duration_ms: int,
    status: Literal["ok", "error"] = "ok",
) -> None:
    event = {
        "type": "tool_end",
        "tool_id": tool_id,
        "content": label,
        "duration_ms": duration_ms,
        "status": status,
    }
    emit_progress(event)
    record_metric(
        "tool.duration_ms",
        float(duration_ms),
        {"tool_id": tool_id, "status": status},
    )


def llm_call(
    *,
    role: str,
    model: str,
    duration_ms: int,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    status: Literal["ok", "error"] = "ok",
) -> None:
    event: dict[str, Any] = {
        "type": "llm_call",
        "role": role,
        "model": model,
        "duration_ms": duration_ms,
        "status": status,
        "content": f"LLM [{role}] {model} ({duration_ms}ms)",
    }
    if input_tokens is not None:
        event["input_tokens"] = input_tokens
    if output_tokens is not None:
        event["output_tokens"] = output_tokens
    emit_progress(event)
    record_metric(
        "llm.duration_ms",
        float(duration_ms),
        {"role": role, "model": model, "status": status},
    )
