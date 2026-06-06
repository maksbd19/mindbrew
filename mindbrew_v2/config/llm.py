"""Central LLM configuration — Nebius Token Factory (OpenAI-compatible)."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, TypeVar

import yaml
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, ValidationError

from mindbrew_v2.settings import get_settings, is_offline
from mindbrew_v2.errors import StructuredExtractError
from mindbrew_v2.progress import llm_call, log, log_timing
from mindbrew_v2.telemetry import start_span

T = TypeVar("T", bound=BaseModel)

_ROLE_MAX_TOKENS: dict[str, int] = {
    "parser": 16384,
    "intake": 4096,
}

_JSON_RETRY_HINT = (
    "Your previous response was invalid or incomplete JSON. "
    "Return ONLY a single valid JSON object matching the schema. "
    "No markdown fences or commentary. Keep arrays concise."
)


def _load_models_yaml() -> dict:
    path = Path(__file__).parent / "models.yaml"
    if not path.exists():
        return {}
    with path.open() as f:
        return yaml.safe_load(f) or {}


def get_model_for_role(role: str) -> str:
    settings = get_settings()
    roles = _load_models_yaml()
    return roles.get(role, settings.nebius_model)


def get_llm(role: str = "default", temperature: float = 0, max_tokens: int | None = None) -> ChatOpenAI:
    settings = get_settings()
    resolved_role = role if role != "default" else "intake"
    kwargs: dict[str, Any] = {
        "model": get_model_for_role(resolved_role),
        "base_url": settings.nebius_base_url,
        "api_key": settings.nebius_api_key,
        "temperature": temperature,
    }
    tokens = max_tokens if max_tokens is not None else _ROLE_MAX_TOKENS.get(resolved_role)
    if tokens is not None:
        kwargs["max_tokens"] = tokens
    return ChatOpenAI(**kwargs)


def clean_llm_json_text(text: str) -> str:
    """Strip markdown fences and isolate the outermost JSON object."""
    stripped = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", stripped, flags=re.IGNORECASE)
    if fence:
        stripped = fence.group(1).strip()

    start = stripped.find("{")
    end = stripped.rfind("}") + 1
    if start >= 0 and end > start:
        return stripped[start:end]
    return stripped


def parse_llm_json(text: str) -> Any:
    return json.loads(clean_llm_json_text(text))


def _usage_from_message(response: BaseMessage) -> tuple[int | None, int | None]:
    usage = getattr(response, "usage_metadata", None)
    if not usage:
        return None, None
    if isinstance(usage, dict):
        return usage.get("input_tokens"), usage.get("output_tokens")
    return getattr(usage, "input_tokens", None), getattr(usage, "output_tokens", None)


def _emit_llm_telemetry(
    *,
    role: str,
    model: str,
    started: float,
    response: BaseMessage | None = None,
    status: str = "ok",
) -> None:
    duration_ms = int((time.perf_counter() - started) * 1000)
    input_tokens, output_tokens = _usage_from_message(response) if response else (None, None)
    llm_call(
        role=role,
        model=model,
        duration_ms=duration_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        status="error" if status == "error" else "ok",
    )
    log_timing(f"LLM [{role}]", time.perf_counter() - started)


def _try_structured_output(llm: ChatOpenAI, schema: type[T], messages: list[BaseMessage]) -> T | None:
    for method in ("json_schema", "json_mode", "function_calling"):
        try:
            structured = llm.with_structured_output(schema, method=method)
            result = structured.invoke(messages)
            if isinstance(result, schema):
                return result
            if isinstance(result, dict):
                return schema.model_validate(result)
        except Exception:
            continue
    return None


def structured_extract(
    prompt: str,
    schema: type[T],
    system: str = "Return valid JSON matching the schema exactly.",
    role: str = "parser",
    max_attempts: int = 3,
) -> T:
    if is_offline():
        return _offline_structured(schema, prompt)

    model = get_model_for_role(role)
    log(f"LLM [{role}] calling {model}…")
    started = time.perf_counter()

    llm = get_llm(role=role)
    messages: list[BaseMessage] = [
        SystemMessage(content=f"{system}\nSchema: {schema.model_json_schema()}"),
        HumanMessage(content=prompt),
    ]

    with start_span("llm.call", {"role": role, "model": model}):
        structured = _try_structured_output(llm, schema, messages)
        if structured is not None:
            _emit_llm_telemetry(role=role, model=model, started=started)
            return structured

        last_error: Exception | None = None
        last_response: AIMessage | None = None
        for attempt in range(max_attempts):
            response = llm.invoke(messages)
            last_response = response if isinstance(response, AIMessage) else None
            text = str(response.content)
            try:
                data = parse_llm_json(text)
                result = schema.model_validate(data)
                _emit_llm_telemetry(role=role, model=model, started=started, response=last_response)
                return result
            except (json.JSONDecodeError, ValidationError) as exc:
                last_error = exc
                log(
                    f"LLM [{role}] structured parse failed "
                    f"(attempt {attempt + 1}/{max_attempts}): {exc}"
                )
                if attempt + 1 >= max_attempts:
                    break
                messages = [
                    *messages,
                    AIMessage(content=text),
                    HumanMessage(content=_JSON_RETRY_HINT),
                ]

        _emit_llm_telemetry(
            role=role,
            model=model,
            started=started,
            response=last_response,
            status="error",
        )
    assert last_error is not None
    raise StructuredExtractError(
        role=role,
        schema=schema.__name__,
        cause=last_error,
    ) from last_error


def _offline_structured(schema: type[T], prompt: str) -> T:
    """Deterministic offline responses for eval/CI."""
    from mindbrew_v2.offline.fixtures import offline_structured_response

    data = offline_structured_response(schema, prompt)
    return schema.model_validate(data)
