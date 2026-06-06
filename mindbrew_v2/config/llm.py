"""Central LLM configuration — Nebius Token Factory (OpenAI-compatible)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypeVar

import yaml
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from mindbrew_v2.settings import get_settings, is_offline

T = TypeVar("T", bound=BaseModel)


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


def get_llm(role: str = "default", temperature: float = 0) -> ChatOpenAI:
    settings = get_settings()
    return ChatOpenAI(
        model=get_model_for_role(role if role != "default" else "intake"),
        base_url=settings.nebius_base_url,
        api_key=settings.nebius_api_key,
        temperature=temperature,
    )


def structured_extract(
    prompt: str,
    schema: type[T],
    system: str = "Return valid JSON matching the schema exactly.",
    role: str = "parser",
) -> T:
    if is_offline():
        return _offline_structured(schema, prompt)

    llm = get_llm(role=role)
    messages = [
        SystemMessage(content=f"{system}\nSchema: {schema.model_json_schema()}"),
        HumanMessage(content=prompt),
    ]
    response = llm.invoke(messages)
    text = str(response.content)
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        text = text[start:end]
    data = json.loads(text)
    return schema.model_validate(data)


def _offline_structured(schema: type[T], prompt: str) -> T:
    """Deterministic offline responses for eval/CI."""
    from mindbrew_v2.offline.fixtures import offline_structured_response

    data = offline_structured_response(schema, prompt)
    return schema.model_validate(data)
