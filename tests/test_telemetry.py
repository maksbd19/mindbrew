"""Telemetry configuration and graph run config."""

from __future__ import annotations

import os
from unittest.mock import patch

from api.services.graph_runner import _graph_run_config
from mindbrew_v2.telemetry import (
    configure_langsmith,
    init_telemetry,
    record_metric,
    reset_session_context,
    set_session_context,
    start_span,
)


def test_graph_run_config_includes_metadata_and_tags():
    config = _graph_run_config("session-abc-123")
    assert config["configurable"]["thread_id"] == "session-abc-123"
    assert config["metadata"]["session_id"] == "session-abc-123"
    assert config["tags"] == ["brewmind"]
    assert config["run_name"] == "session-session-"


def test_configure_langsmith_noop_without_api_key(monkeypatch):
    monkeypatch.delenv("LANGCHAIN_TRACING_V2", raising=False)
    with patch("mindbrew_v2.settings.get_settings") as mock_settings:
        mock_settings.return_value.langsmith_api_key = None
        assert configure_langsmith() is False


def test_configure_langsmith_sets_env_when_key_present(monkeypatch):
    monkeypatch.setenv("LANGSMITH_API_KEY", "test-key")
    monkeypatch.delenv("LANGCHAIN_TRACING_V2", raising=False)
    monkeypatch.delenv("LANGSMITH_PROJECT", raising=False)

    with patch("mindbrew_v2.settings.get_settings") as mock_settings:
        mock_settings.return_value.langsmith_api_key = "test-key"
        mock_settings.return_value.langsmith_project = "brewmind-test"
        assert configure_langsmith() is True

    assert os.environ["LANGCHAIN_TRACING_V2"] == "true"
    assert os.environ["LANGSMITH_API_KEY"] == "test-key"
    assert os.environ["LANGSMITH_PROJECT"] == "brewmind-test"


def test_start_span_noop_when_otel_disabled():
    with start_span("test.span", {"foo": "bar"}) as span:
        assert span is None


def test_record_metric_noop_when_otel_disabled():
    record_metric("node.duration_ms", 42.0, {"node_id": "intake"})


def test_session_context_roundtrip():
    token = set_session_context("sess-1")
    try:
        from mindbrew_v2.telemetry import get_session_context

        assert get_session_context() == "sess-1"
    finally:
        reset_session_context(token)

    from mindbrew_v2.telemetry import get_session_context

    assert get_session_context() is None


def test_init_telemetry_idempotent_without_otel_endpoint(monkeypatch):
    import mindbrew_v2.telemetry as telemetry

    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    telemetry._initialized = False
    with patch("mindbrew_v2.settings.get_settings") as mock_settings:
        mock_settings.return_value.otel_exporter_otlp_endpoint = None
        mock_settings.return_value.langsmith_api_key = None
        init_telemetry()
        init_telemetry()
