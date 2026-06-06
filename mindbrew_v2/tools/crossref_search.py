"""Proactive Crossref works search."""

from __future__ import annotations

import httpx

from mindbrew_v2.tools.citation_resolver import _normalize_doi
from mindbrew_v2.tools.literature_retrieval import RetrievedDocument


def search_crossref(query: str, max_results: int = 5) -> list[RetrievedDocument]:
    with httpx.Client(timeout=15.0) as client:
        resp = client.get(
            "https://api.crossref.org/works",
            params={"query": query, "rows": max_results},
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        items = resp.json().get("message", {}).get("items", [])

    docs: list[RetrievedDocument] = []
    for item in items:
        titles = item.get("title") or []
        title = titles[0] if titles else ""
        if not title:
            continue

        doi = _normalize_doi(item.get("DOI"))
        abstract = _extract_abstract(item)
        year = _extract_year(item)

        snippet_parts = [p for p in (abstract, year) if p]
        docs.append(
            RetrievedDocument(
                source="crossref",
                title=title,
                snippet=" — ".join(snippet_parts)[:500] if snippet_parts else title[:500],
                url=f"https://doi.org/{doi}" if doi else None,
                doi=doi,
            )
        )
    return docs


def _extract_abstract(item: dict) -> str:
    abstract = item.get("abstract")
    if isinstance(abstract, str):
        return abstract.replace("<jats:p>", "").replace("</jats:p>", "").strip()
    return ""


def _extract_year(item: dict) -> str:
    for key in ("published-print", "published-online", "created", "issued"):
        parts = (item.get(key) or {}).get("date-parts", [[]])
        if parts and parts[0]:
            return str(parts[0][0])
    return ""
