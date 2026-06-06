"""Eval harness base types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class EvalCase:
    id: str
    phase: str
    ticket: str
    description: str = ""
    tier: str = "offline"
    input: dict[str, Any] = field(default_factory=dict)
    gold: dict[str, Any] = field(default_factory=dict)
    expected: str = ""
    assertions: list[dict[str, Any]] = field(default_factory=list)
    requires_live_api: bool = False
    weight: float = 1.0


@dataclass
class EvalResult:
    case_id: str
    phase: str
    passed: bool
    failures: list[str] = field(default_factory=list)
    weight: float = 1.0


class Scorer(Protocol):
    def score(self, case: EvalCase) -> EvalResult: ...
