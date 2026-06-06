"""Thread-safe progress events for long-running graph nodes."""

from __future__ import annotations

from contextvars import ContextVar, Token
from typing import Any, Callable

_Emitter: ContextVar[Callable[[dict[str, Any]], None] | None] = ContextVar(
    "progress_emitter", default=None
)


def set_progress_emitter(fn: Callable[[dict[str, Any]], None] | None) -> Token:
    return _Emitter.set(fn)


def reset_progress_emitter(token: Token) -> None:
    _Emitter.reset(token)


def emit_progress(event: dict[str, Any]) -> None:
    fn = _Emitter.get()
    if fn:
        fn(event)


def log(message: str, *, level: str = "info") -> None:
    emit_progress({"type": "log", "content": message, "level": level})


def node_start(node_id: str, label: str) -> None:
    emit_progress({"type": "node_start", "node_id": node_id, "content": label})


def node_end(node_id: str, label: str) -> None:
    emit_progress({"type": "node_end", "node_id": node_id, "content": label})
