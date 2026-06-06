"""Tests for LLM JSON parsing helpers."""

import pytest

from mindbrew_v2.config.llm import clean_llm_json_text, parse_llm_json


def test_clean_llm_json_text_strips_markdown_fence():
    raw = 'Here is the result:\n```json\n{"candidates": []}\n```'
    assert clean_llm_json_text(raw) == '{"candidates": []}'


def test_clean_llm_json_text_isolates_object():
    raw = 'prefix {"a": 1, "b": {"c": 2}} suffix'
    assert parse_llm_json(raw) == {"a": 1, "b": {"c": 2}}


def test_parse_llm_json_rejects_invalid():
    with pytest.raises(Exception):
        parse_llm_json('{"broken": true,}')
