"""Cache SBML GEM model files on disk."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import urlopen

from mindbrew_v2.settings import PROJECT_ROOT, get_settings

BUNDLED_MODELS_DIR = PROJECT_ROOT / "data" / "models"
INDEX_FILE = "index.json"


def get_cache_dir() -> Path:
    settings = get_settings()
    raw = settings.gem_model_cache_dir or "data/gem_models"
    path = Path(raw)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    path.mkdir(parents=True, exist_ok=True)
    return path


def _load_index(cache_dir: Path) -> dict[str, Any]:
    index_path = cache_dir / INDEX_FILE
    if index_path.exists():
        return json.loads(index_path.read_text())
    return {"models": {}}


def _save_index(cache_dir: Path, index: dict[str, Any]) -> None:
    (cache_dir / INDEX_FILE).write_text(json.dumps(index, indent=2))


def _resolve_bundled_path(model_ref: str | None) -> Path | None:
    if not model_ref:
        return None
    path = Path(model_ref)
    if path.is_absolute() and path.is_file():
        return path
    candidates = [
        PROJECT_ROOT / model_ref,
        BUNDLED_MODELS_DIR / model_ref.replace("data/models/", ""),
        BUNDLED_MODELS_DIR / Path(model_ref).name,
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def ensure_model(
    gem_id: str,
    model_ref: str | None = None,
    *,
    model_name: str | None = None,
    sbml_url: str | None = None,
    source_doi: str | None = None,
) -> tuple[str | None, str | None, str | None]:
    """Return (absolute_cache_path, source, error_message)."""
    cache_dir = get_cache_dir()
    index = _load_index(cache_dir)
    key = (gem_id or model_name or "unknown").lower()

    existing = index.get("models", {}).get(key)
    if existing:
        cached_path = Path(existing["path"])
        if cached_path.is_file():
            return str(cached_path.resolve()), "cache", None

    dest = cache_dir / f"{key}.xml"

    bundled = _resolve_bundled_path(model_ref)
    if bundled:
        shutil.copy2(bundled, dest)
        index.setdefault("models", {})[key] = {
            "path": str(dest.resolve()),
            "source": "bundled",
            "seed_ref": model_ref,
            "cached_at": _now_iso(),
        }
        _save_index(cache_dir, index)
        return str(dest.resolve()), "bundled", None

    if sbml_url:
        try:
            with urlopen(sbml_url, timeout=120) as response:
                dest.write_bytes(response.read())
            index.setdefault("models", {})[key] = {
                "path": str(dest.resolve()),
                "source": "literature",
                "sbml_url": sbml_url,
                "doi": source_doi,
                "cached_at": _now_iso(),
            }
            _save_index(cache_dir, index)
            return str(dest.resolve()), "literature", None
        except OSError as exc:
            return None, None, f"Failed to fetch SBML from {sbml_url}: {exc}"

    return None, None, "No bundled model or literature SBML URL available"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
