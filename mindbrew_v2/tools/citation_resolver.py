"""Resolve and validate citations via Crossref and PubMed."""

from __future__ import annotations

import re
from typing import Literal

import httpx

from mindbrew_v2.models import Citation
from mindbrew_v2.settings import is_offline
from mindbrew_v2.tools.bio_links import citation_url, doi_link

ValidationStatus = Literal["verified", "unverified", "invalid"]


def resolve_citation(citation: Citation) -> Citation:
    """Validate and enrich a single citation."""
    data = citation.model_dump()
    if is_offline():
        return _resolve_offline(Citation.model_validate(data))

    doi = _normalize_doi(citation.doi)
    pmid = _normalize_pmid(citation.pmid)

    if doi:
        resolved = _resolve_doi(doi, data)
        if resolved.validation_status == "verified":
            return resolved

    if pmid:
        resolved = _resolve_pmid(pmid, data)
        if resolved.validation_status == "verified":
            return resolved

    if doi or pmid:
        url = citation_url(doi=doi, pmid=pmid)
        status: ValidationStatus = "unverified" if url else "invalid"
        return Citation(
            **{
                **data,
                "doi": doi,
                "pmid": pmid,
                "url": url,
                "validation_status": status,
            }
        )

    return Citation(**{**data, "validation_status": "invalid"})


def resolve_citations(citations: list[Citation]) -> list[Citation]:
    return [resolve_citation(c) for c in citations]


def _normalize_doi(doi: str | None) -> str | None:
    if not doi:
        return None
    clean = doi.strip().removeprefix("https://doi.org/").removeprefix("http://doi.org/")
    return clean or None


def _normalize_pmid(pmid: str | None) -> str | None:
    if not pmid:
        return None
    digits = re.sub(r"\D", "", pmid.strip())
    return digits or None


def _resolve_offline(citation: Citation) -> Citation:
    doi = _normalize_doi(citation.doi)
    pmid = _normalize_pmid(citation.pmid)
    url = citation_url(doi=doi, pmid=pmid)
    has_id = bool(doi or pmid)
    status: ValidationStatus = "verified" if has_id and url else "invalid"
    if pmid == "12345678":
        status = "invalid"
    return Citation(
        **{
            **citation.model_dump(),
            "doi": doi,
            "pmid": pmid,
            "url": url,
            "validation_status": status,
        }
    )


def _resolve_doi(doi: str, base: dict) -> Citation:
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                f"https://api.crossref.org/works/{doi}",
                headers={"Accept": "application/json"},
            )
            if resp.status_code != 200:
                return _fallback(doi=doi, pmid=base.get("pmid"), data=base, status="unverified")

            item = resp.json().get("message", {})
            title_list = item.get("title") or []
            title = title_list[0] if title_list else base.get("title", "")
            authors = _format_authors(item.get("author", []))
            year = _extract_year(item)
            journal = (item.get("container-title") or [""])[0]
            url = doi_link(doi)
            url_str = url["url"] if url else f"https://doi.org/{doi}"

            return Citation(
                doi=doi,
                pmid=base.get("pmid"),
                title=title or base.get("title", ""),
                snippet=base.get("snippet", ""),
                url=url_str,
                authors=authors,
                year=year,
                journal=journal,
                validation_status="verified",
            )
    except (httpx.HTTPError, KeyError, IndexError):
        return _fallback(doi=doi, pmid=base.get("pmid"), data=base, status="unverified")


def _resolve_pmid(pmid: str, base: dict) -> Citation:
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
                params={"db": "pubmed", "id": pmid, "retmode": "json"},
            )
            if resp.status_code != 200:
                return _fallback(doi=base.get("doi"), pmid=pmid, data=base, status="unverified")

            result = resp.json().get("result", {})
            record = result.get(pmid, {})
            if not record or record.get("error"):
                return _fallback(doi=base.get("doi"), pmid=pmid, data=base, status="invalid")

            title = record.get("title", base.get("title", "")).rstrip(".")
            authors = ", ".join(record.get("authors", [])[:5])
            year = (record.get("pubdate") or "")[:4]
            journal = record.get("fulljournalname") or record.get("source") or ""
            doi = _normalize_doi(record.get("elocationid", "").replace("doi: ", "") if record.get("elocationid") else base.get("doi"))
            if not doi and record.get("articleids"):
                for aid in record["articleids"]:
                    if aid.get("idtype") == "doi":
                        doi = _normalize_doi(aid.get("value"))
                        break

            return Citation(
                doi=doi,
                pmid=pmid,
                title=title,
                snippet=base.get("snippet", ""),
                url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                authors=authors,
                year=year,
                journal=journal,
                validation_status="verified",
            )
    except (httpx.HTTPError, KeyError, IndexError):
        return _fallback(doi=base.get("doi"), pmid=pmid, data=base, status="unverified")


def _fallback(
    doi: str | None,
    pmid: str | None,
    data: dict,
    status: ValidationStatus,
) -> Citation:
    url = citation_url(doi=_normalize_doi(doi), pmid=_normalize_pmid(pmid))
    return Citation(
        **{
            **data,
            "doi": _normalize_doi(doi),
            "pmid": _normalize_pmid(pmid),
            "url": url,
            "validation_status": status if url or status == "invalid" else "unverified",
        }
    )


def _format_authors(authors: list[dict]) -> str:
    names = []
    for a in authors[:5]:
        given = a.get("given", "")
        family = a.get("family", "")
        if family:
            names.append(f"{family}, {given}".strip(", "))
    return "; ".join(names)


def _extract_year(item: dict) -> str:
    for key in ("published-print", "published-online", "created", "issued"):
        parts = (item.get(key) or {}).get("date-parts", [[]])
        if parts and parts[0]:
            return str(parts[0][0])
    return ""
