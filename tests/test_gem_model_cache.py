"""Tests for GEM model cache."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("BREWMIND_OFFLINE", "true")

from mindbrew_v2.tools.gem_model_cache import ensure_model, get_cache_dir

BUNDLED_MODEL = Path(__file__).resolve().parents[1] / "data" / "models" / "iYLI647.xml"


@pytest.fixture
def cache_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("GEM_MODEL_CACHE_DIR", str(tmp_path))
    from mindbrew_v2.settings import get_settings

    get_settings.cache_clear()
    return tmp_path


def test_ensure_model_seeds_from_bundled(cache_dir):
    if not BUNDLED_MODEL.is_file():
        pytest.skip("data/models/iYLI647.xml not present")
    path, source, error = ensure_model(
        "iyli647",
        str(BUNDLED_MODEL),
        model_name="iYLI647",
    )
    assert error is None
    assert source == "bundled"
    assert path is not None
    assert Path(path).is_file()
    index = json.loads((cache_dir / "index.json").read_text())
    assert "iyli647" in index["models"]


def test_ensure_model_cache_hit(cache_dir):
    if not BUNDLED_MODEL.is_file():
        pytest.skip("data/models/iYLI647.xml not present")
    first, _, _ = ensure_model("iyli647", str(BUNDLED_MODEL))
    second, source, error = ensure_model("iyli647", str(BUNDLED_MODEL))
    assert error is None
    assert source == "cache"
    assert first == second


def test_get_cache_dir_default(monkeypatch):
    monkeypatch.delenv("GEM_MODEL_CACHE_DIR", raising=False)
    from mindbrew_v2.settings import get_settings

    get_settings.cache_clear()
    path = get_cache_dir()
    assert path.name == "gem_models"
