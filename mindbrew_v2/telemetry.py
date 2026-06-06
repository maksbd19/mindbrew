"""LangSmith, OpenTelemetry, and structured logging helpers."""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Any, Iterator

_session_id: ContextVar[str | None] = ContextVar("telemetry_session_id", default=None)
_initialized = False
_otel_enabled = False
_tracer = None
_meter = None
_histograms: dict[str, Any] = {}


def configure_langsmith() -> bool:
    """Enable LangSmith tracing via standard LangChain env vars when configured."""
    from mindbrew_v2.settings import get_settings

    settings = get_settings()
    if not settings.langsmith_api_key:
        return False

    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    os.environ.setdefault("LANGSMITH_API_KEY", settings.langsmith_api_key)
    os.environ.setdefault("LANGSMITH_PROJECT", settings.langsmith_project)
    return True


def init_telemetry(*, instrument_fastapi: Any | None = None) -> None:
    """Initialize observability backends once at application startup."""
    global _initialized, _otel_enabled, _tracer, _meter

    if _initialized:
        return
    _initialized = True

    configure_langsmith()

    from mindbrew_v2.settings import get_settings

    settings = get_settings()
    if not settings.otel_exporter_otlp_endpoint:
        return

    try:
        from opentelemetry import metrics, trace
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:
        logging.getLogger(__name__).warning(
            "OTEL_EXPORTER_OTLP_ENDPOINT is set but opentelemetry packages are not installed. "
            "Install with: uv sync --extra observability"
        )
        return

    resource = Resource.create({"service.name": settings.otel_service_name})
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{settings.otel_exporter_otlp_endpoint}/v1/traces"))
    )
    trace.set_tracer_provider(tracer_provider)
    _tracer = trace.get_tracer("brewmind")

    metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=f"{settings.otel_exporter_otlp_endpoint}/v1/metrics")
    )
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)
    _meter = metrics.get_meter("brewmind")

    _histograms["node.duration_ms"] = _meter.create_histogram(
        "brewmind.node.duration_ms",
        unit="ms",
        description="LangGraph node execution duration",
    )
    _histograms["llm.duration_ms"] = _meter.create_histogram(
        "brewmind.llm.duration_ms",
        unit="ms",
        description="LLM call duration",
    )
    _histograms["tool.duration_ms"] = _meter.create_histogram(
        "brewmind.tool.duration_ms",
        unit="ms",
        description="Tool execution duration",
    )

    if instrument_fastapi is not None:
        try:
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

            FastAPIInstrumentor.instrument_app(instrument_fastapi)
        except ImportError:
            logging.getLogger(__name__).warning(
                "opentelemetry-instrumentation-fastapi not installed; skipping FastAPI instrumentation"
            )

    _otel_enabled = True


def set_session_context(session_id: str | None) -> Token:
    return _session_id.set(session_id)


def reset_session_context(token: Token) -> None:
    _session_id.reset(token)


def get_session_context() -> str | None:
    return _session_id.get()


@contextmanager
def start_span(name: str, attributes: dict[str, Any] | None = None) -> Iterator[Any]:
    """Create an OTel span when enabled; otherwise yield a no-op handle."""
    if not _otel_enabled or _tracer is None:
        yield None
        return

    attrs = dict(attributes or {})
    session_id = get_session_context()
    if session_id:
        attrs.setdefault("session_id", session_id)

    with _tracer.start_as_current_span(name, attributes=attrs) as span:
        yield span


def record_metric(name: str, value: float, attributes: dict[str, Any] | None = None) -> None:
    if not _otel_enabled or _meter is None:
        return

    attrs = dict(attributes or {})
    session_id = get_session_context()
    if session_id:
        attrs.setdefault("session_id", session_id)

    histogram = _histograms.get(name)
    if histogram is not None:
        histogram.record(value, attributes=attrs)


def log_agent_event(
    logger: logging.Logger,
    level: int,
    message: str,
    *,
    session_id: str | None = None,
    exc_info: BaseException | bool | None = None,
    **fields: Any,
) -> None:
    """Emit a structured log line with optional session and telemetry fields."""
    extra = {k: v for k, v in fields.items() if v is not None}
    sid = session_id or get_session_context()
    if sid:
        extra["session_id"] = sid
    logger.log(level, message, extra=extra or None, exc_info=exc_info)
