"""Proactive PubMed search via NCBI E-utilities."""

from __future__ import annotations

import httpx

from mindbrew_v2.tools.literature_retrieval import RetrievedDocument

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def search_pubmed(query: str, max_results: int = 8) -> list[RetrievedDocument]:
    pmids = _esearch(query, max_results)
    if not pmids:
        return []

    summaries = _esummary(pmids)
    abstracts = _efetch_abstracts(pmids)

    docs: list[RetrievedDocument] = []
    for pmid in pmids:
        summary = summaries.get(pmid, {})
        title = (summary.get("title") or "").rstrip(".")
        if not title:
            continue

        snippet = abstracts.get(pmid) or summary.get("fulljournalname") or summary.get("source") or ""
        doi = _extract_doi(summary)

        docs.append(
            RetrievedDocument(
                source="pubmed",
                title=title,
                snippet=snippet[:500],
                url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                pmid=pmid,
                doi=doi,
            )
        )
    return docs


def _esearch(query: str, max_results: int) -> list[str]:
    with httpx.Client(timeout=15.0) as client:
        resp = client.get(
            f"{EUTILS_BASE}/esearch.fcgi",
            params={
                "db": "pubmed",
                "term": query,
                "retmax": max_results,
                "retmode": "json",
                "sort": "relevance",
            },
        )
        resp.raise_for_status()
        ids = resp.json().get("esearchresult", {}).get("idlist", [])
        return [str(i) for i in ids[:max_results]]


def _esummary(pmids: list[str]) -> dict[str, dict]:
    with httpx.Client(timeout=15.0) as client:
        resp = client.get(
            f"{EUTILS_BASE}/esummary.fcgi",
            params={"db": "pubmed", "id": ",".join(pmids), "retmode": "json"},
        )
        resp.raise_for_status()
        result = resp.json().get("result", {})
        return {pid: result.get(pid, {}) for pid in pmids if pid in result}


def _efetch_abstracts(pmids: list[str]) -> dict[str, str]:
    with httpx.Client(timeout=20.0) as client:
        resp = client.get(
            f"{EUTILS_BASE}/efetch.fcgi",
            params={
                "db": "pubmed",
                "id": ",".join(pmids),
                "rettype": "abstract",
                "retmode": "text",
            },
        )
        if resp.status_code != 200:
            return {}

    abstracts: dict[str, str] = {}
    current_pmid: str | None = None
    lines: list[str] = []

    for line in resp.text.splitlines():
        if line.startswith("PMID-"):
            if current_pmid and lines:
                abstracts[current_pmid] = " ".join(lines).strip()[:500]
            current_pmid = line.replace("PMID-", "").strip().split()[0]
            lines = []
        elif line.strip() and not line.startswith("TI  -") and current_pmid:
            cleaned = line.strip()
            if cleaned and not cleaned.startswith("AB  -"):
                lines.append(cleaned.replace("AB  - ", ""))
            elif cleaned.startswith("AB  -"):
                lines.append(cleaned.replace("AB  - ", ""))

    if current_pmid and lines:
        abstracts[current_pmid] = " ".join(lines).strip()[:500]

    return abstracts


def _extract_doi(summary: dict) -> str | None:
    eloc = summary.get("elocationid") or ""
    if eloc.startswith("doi:"):
        return eloc.replace("doi:", "").strip()
    for aid in summary.get("articleids") or []:
        if aid.get("idtype") == "doi":
            return aid.get("value")
    return None
