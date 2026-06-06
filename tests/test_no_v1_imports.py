"""Ensure v2 never imports v1."""

from pathlib import Path


def test_no_v1_imports():
    root = Path(__file__).resolve().parents[1]
    for path in (root / "mindbrew_v2").rglob("*.py"):
        text = path.read_text()
        assert "mindbrew_v1" not in text, f"{path} references mindbrew_v1"
