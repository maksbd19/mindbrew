"""Path helpers for user-facing display."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

_GEM_PATH_KEYS = ("model_ref", "model_cache_path", "scenario", "biomass_validation_scenario")
_PAYLOAD_PATH_KEYS = ("model_ref", "scenario")


def display_path(path: str | None) -> str:
    """Return the file or directory name for logs and UI (not the full path)."""
    if not path:
        return ""
    return Path(path).name


def _sanitize_path_fields(data: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    cleaned = dict(data)
    for key in keys:
        value = cleaned.get(key)
        if isinstance(value, str) and value:
            cleaned[key] = display_path(value)
    return cleaned


def sanitize_fba_plan_artifact(artifact: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of the FBA plan artifact with filesystem paths shortened for UI."""
    out = copy.deepcopy(artifact)
    gem = out.get("gem_profile")
    if isinstance(gem, dict):
        out["gem_profile"] = _sanitize_path_fields(gem, _GEM_PATH_KEYS)
    payloads = out.get("score_payloads")
    if isinstance(payloads, list):
        out["score_payloads"] = [
            _sanitize_path_fields(item, _PAYLOAD_PATH_KEYS) if isinstance(item, dict) else item
            for item in payloads
        ]
    return out
