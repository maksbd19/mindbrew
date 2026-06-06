"""Infer concise session titles from user briefs."""

from __future__ import annotations

from pydantic import BaseModel, Field

from mindbrew_v2.config.llm import structured_extract
from mindbrew_v2.settings import is_offline


class SessionTitleExtract(BaseModel):
    title: str = Field(description="Short session title, max 12 words, no quotes")


def brief_title_snippet(raw_brief: str, limit: int = 80) -> str:
    text = raw_brief.strip().replace("\n", " ")
    if not text:
        return "New session"
    return text if len(text) <= limit else text[: limit - 1] + "…"


def is_auto_title(title: str, raw_brief: str) -> bool:
    snippet = brief_title_snippet(raw_brief)
    normalized = title.strip()
    return not normalized or normalized == snippet or normalized == "New session"


def _offline_title(raw_brief: str) -> str:
    words = raw_brief.strip().replace("\n", " ").split()
    if not words:
        return "New session"
    title = " ".join(words[:10])
    return title[:255]


def infer_session_title(raw_brief: str) -> str:
    brief = raw_brief.strip()
    if not brief:
        return "New session"
    if is_offline():
        return _offline_title(brief)

    result = structured_extract(
        prompt=(
            "Write a concise session title for this metabolic engineering R&D brief.\n\n"
            f"{brief}"
        ),
        schema=SessionTitleExtract,
        system=(
            "Return valid JSON matching the schema exactly. "
            "The title should name the organism, feedstock, or product when present. "
            "Use title case. No quotes or trailing punctuation. Max 12 words."
        ),
        role="intake",
    )
    title = result.title.strip().strip('"').strip("'")
    return title[:255] if title else brief_title_snippet(brief)
