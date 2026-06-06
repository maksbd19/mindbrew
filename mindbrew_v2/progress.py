"""Thread-safe progress events for long-running graph nodes."""

from __future__ import annotations

import threading
from contextvars import ContextVar, Token
from typing import Any, Callable

_Emitter: ContextVar[Callable[[dict[str, Any]], None] | None] = ContextVar(
    "progress_emitter", default=None
)

_emitter_lock = threading.Lock()
_shared_emitter: Callable[[dict[str, Any]], None] | None = None

_node_lock = threading.Lock()
_current_node_id: str | None = None
_current_node_label: str | None = None


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
    global _current_node_id, _current_node_label
    with _node_lock:
        _current_node_id = None
        _current_node_label = None


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


def node_start(node_id: str, label: str) -> None:
    global _current_node_id, _current_node_label
    with _node_lock:
        _current_node_id = node_id
        _current_node_label = label
    emit_progress({"type": "node_start", "node_id": node_id, "content": label})


def node_end(node_id: str, label: str) -> None:
    global _current_node_id, _current_node_label

    emit_progress({"type": "node_end", "node_id": node_id, "content": label})
    with _node_lock:
        if _current_node_id == node_id:
            _current_node_id = None
            _current_node_label = None
