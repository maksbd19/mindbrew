"""Tests for user-facing agent error formatting."""

import json

import pytest
from pydantic import BaseModel, ValidationError

from mindbrew_v2.errors import StructuredExtractError, agent_error_detail, agent_error_event, format_agent_error


def test_format_agent_error_json_decode():
    exc = json.JSONDecodeError("Expecting ',' delimiter", "doc", 27209)
    message = format_agent_error(exc)
    assert "Expecting" not in message
    assert "delimiter" not in message
    assert "restart" in message.lower()


def test_format_agent_error_validation():
    class Sample(BaseModel):
        count: int

    try:
        Sample.model_validate({"count": "nope"})
    except ValidationError as exc:
        message = format_agent_error(exc)
    assert "ValidationError" not in message
    assert "unexpected format" in message.lower()


def test_format_agent_error_langgraph_wrapper():
    root = json.JSONDecodeError("Expecting value", "doc", 0)

    class TaskError(Exception):
        pass

    wrapped = TaskError("During task with name 'literature_search'")
    wrapped.__cause__ = root
    message = format_agent_error(wrapped)
    assert "literature_search" not in message
    assert "Expecting" not in message


def test_format_agent_error_structured_extract():
    cause = json.JSONDecodeError("bad", "doc", 1)
    exc = StructuredExtractError(role="parser", schema="PathwayCandidateList", cause=cause)
    assert format_agent_error(exc) == str(exc)


def test_format_agent_error_keeps_short_plain_message():
    assert format_agent_error(RuntimeError("Connection timed out")) == "Connection timed out"


def test_format_agent_error_hides_traceback():
    technical = 'File "/app/graph.py", line 44\nJSONDecodeError: Expecting \',\' delimiter'
    assert format_agent_error(RuntimeError(technical)) != technical


def test_agent_error_detail_includes_traceback():
    try:
        raise ValueError("bad payload")
    except ValueError as exc:
        detail = agent_error_detail(exc)
    assert "ValueError: bad payload" in detail
    assert "test_agent_error_detail_includes_traceback" in detail


def test_agent_error_event_includes_message_and_detail():
    exc = json.JSONDecodeError("Expecting ',' delimiter", "doc", 27209)
    event = agent_error_event(exc)
    assert event["type"] == "error"
    assert "Expecting" not in event["message"]
    assert "Expecting ',' delimiter" in event["detail"]
    assert "JSONDecodeError" in event["detail"]
