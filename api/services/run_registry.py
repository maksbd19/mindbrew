"""Track in-flight graph runs and cooperative cancel signals."""

from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass, field


@dataclass
class RunHandle:
    cancel: threading.Event = field(default_factory=threading.Event)
    task: asyncio.Task | None = None


class RunRegistry:
    def __init__(self) -> None:
        self._runs: dict[str, RunHandle] = {}

    def register(self, session_id: str, task: asyncio.Task | None = None) -> threading.Event:
        handle = RunHandle(task=task)
        self._runs[session_id] = handle
        return handle.cancel

    def attach_task(self, session_id: str, task: asyncio.Task) -> None:
        handle = self._runs.get(session_id)
        if handle:
            handle.task = task

    def is_running(self, session_id: str) -> bool:
        return session_id in self._runs

    def is_active(self, session_id: str) -> bool:
        return session_id in self._runs

    def interrupt(self, session_id: str) -> bool:
        handle = self._runs.get(session_id)
        if not handle:
            return False
        handle.cancel.set()
        if handle.task and not handle.task.done():
            handle.task.cancel()
        return True

    def unregister(self, session_id: str) -> None:
        self._runs.pop(session_id, None)


_registry = RunRegistry()


def get_run_registry() -> RunRegistry:
    return _registry
