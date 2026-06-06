"""User-facing agent error messages."""

from __future__ import annotations

import json
import traceback
from collections.abc import Iterator

from pydantic import ValidationError

_JSON_USER_MESSAGE = (
    "The language model returned a response the agent could not parse. "
    "Try restarting this step, or revise your brief to request fewer pathways or simpler constraints."
)

_VALIDATION_USER_MESSAGE = (
    "The language model returned data in an unexpected format. "
    "Try restarting this step."
)

_GENERIC_USER_MESSAGE = (
    "The agent encountered an unexpected error. "
    "Check the agent log for details, or try restarting this step."
)

_TECHNICAL_MARKERS = (
    "JSONDecodeError",
    "Expecting ",
    "delimiter:",
    "Traceback (most recent call last)",
    "During task with name",
    'File "',
    "ValidationError",
    "pydantic",
    "langgraph/",
    "langchain",
)


class StructuredExtractError(RuntimeError):
    """Raised when structured LLM output cannot be parsed after retries."""

    def __init__(self, *, role: str, schema: str, cause: Exception):
        self.role = role
        self.schema = schema
        self.cause_error = cause
        if isinstance(cause, json.JSONDecodeError):
            message = _JSON_USER_MESSAGE
        elif isinstance(cause, ValidationError):
            message = _VALIDATION_USER_MESSAGE
        else:
            message = _GENERIC_USER_MESSAGE
        super().__init__(message)


def _iter_exception_chain(exc: BaseException) -> Iterator[BaseException]:
    seen: set[int] = set()
    stack = [exc]
    while stack:
        current = stack.pop()
        marker = id(current)
        if marker in seen:
            continue
        seen.add(marker)
        yield current
        if current.__cause__ is not None:
            stack.append(current.__cause__)
        context = current.__context__
        if context is not None and context is not current.__cause__:
            stack.append(context)


def _looks_technical(message: str) -> bool:
    text = message.strip()
    if not text:
        return True
    if len(text) > 280 or text.count("\n") > 2:
        return True
    return any(marker in text for marker in _TECHNICAL_MARKERS)


def format_agent_error(exc: BaseException) -> str:
    """Convert an internal exception into a short message suitable for the UI."""
    for err in _iter_exception_chain(exc):
        if isinstance(err, StructuredExtractError):
            return str(err)
        if isinstance(err, json.JSONDecodeError):
            return _JSON_USER_MESSAGE
        if isinstance(err, ValidationError):
            return _VALIDATION_USER_MESSAGE

    message = str(exc).strip()
    if _looks_technical(message):
        return _GENERIC_USER_MESSAGE
    return message


def agent_error_detail(exc: BaseException) -> str:
    """Full technical detail for agent log entries."""
    return "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)).strip()


def agent_error_event(exc: BaseException) -> dict[str, str]:
    """Build a stream error payload with user message and full log detail."""
    return {
        "type": "error",
        "message": format_agent_error(exc),
        "detail": agent_error_detail(exc),
    }
