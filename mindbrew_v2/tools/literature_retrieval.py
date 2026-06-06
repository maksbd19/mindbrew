"""Orchestrate literature retrieval from Lamin/bionty, PubMed, and Crossref."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from mindbrew_v2.models import PathwayCandidate, ResearchBrief
from mindbrew_v2.settings import get_settings, is_offline

DocumentSource = Literal[
    "lamin_pathway",
    "lamin_organism",
    "lamin_gene",
    "lamin_artifact",
    "pubmed",
    "crossref",
]


class RetrievedDocument(BaseModel):
    source: DocumentSource
    title: str
    snippet: str
    url: str | None = None
    doi: str | None = None
    pmid: str | None = None
    ontology_id: str | None = None


def build_retrieval_queries(brief: ResearchBrief) -> list[str]:
    feedstock = brief.feedstock.name or brief.feedstock.compound_class or ""
    target = brief.target.name or brief.target.compound_class or ""
    organism = ", ".join(brief.organism) if brief.organism else ""

    queries: list[str] = []
    if feedstock and target:
        base = f"{feedstock} {target} metabolic pathway"
        queries.append(f"{base} {organism}".strip())
        queries.append(f"{target} biosynthesis {organism}".strip())

    for compound in (feedstock, target, brief.feedstock.compound_class, brief.target.compound_class):
        if compound and compound not in queries:
            queries.append(f"{compound} metabolic engineering {organism}".strip())

    if brief.target_function:
        queries.append(f"{brief.target_function} {target} {organism}".strip())

    seen: set[str] = set()
    unique: list[str] = []
    for q in queries:
        normalized = " ".join(q.split())
        if normalized and normalized not in seen:
            seen.add(normalized)
            unique.append(normalized)
    return unique[:4]


def build_gem_retrieval_queries(
    brief: ResearchBrief,
    candidates: list[PathwayCandidate] | None = None,
) -> list[str]:
    organism = ", ".join(brief.organism) if brief.organism else ""
    feedstock = brief.feedstock.name or brief.feedstock.compound_class or ""
    target = brief.target.name or brief.target.compound_class or ""
    queries = [
        f"{organism} genome-scale metabolic model".strip(),
        f"{organism} GSMM {feedstock} validation".strip(),
        f"{target} metabolic model {organism}".strip(),
    ]
    if candidates:
        for cand in candidates[:2]:
            for citation in cand.citations[:1]:
                if citation.title:
                    queries.append(f"{citation.title} metabolic model")
    seen: set[str] = set()
    unique: list[str] = []
    for query in queries:
        normalized = " ".join(query.split())
        if normalized and normalized not in seen:
            seen.add(normalized)
            unique.append(normalized)
    return unique[:4]


def merge_retrieval_docs(
    existing: list[RetrievedDocument],
    new_docs: list[RetrievedDocument],
) -> list[RetrievedDocument]:
    seen = {_doc_dedup_key(doc) for doc in existing}
    merged = list(existing)
    for doc in new_docs:
        key = _doc_dedup_key(doc)
        if key not in seen:
            seen.add(key)
            merged.append(doc)
    return merged


def retrieve_queries(queries: list[str]) -> list[RetrievedDocument]:
    if is_offline() or not queries:
        return []
    settings = get_settings()
    if not settings.literature_retrieval_enabled:
        return []
    docs: list[RetrievedDocument] = []
    seen_keys: set[str] = set()
    for query in queries:
        docs.extend(_safe_retrieve(query, settings, seen_keys))
    return docs


def format_context_block(docs: list[RetrievedDocument], max_chars: int) -> str:
    if not docs:
        return ""

    sections: dict[str, list[str]] = {
        "Pathway ontology (Lamin/bionty)": [],
        "Organisms & genes (Lamin/bionty)": [],
        "Public datasets (Lamin)": [],
        "Literature": [],
    }

    for doc in docs:
        line = _format_document_line(doc)
        if doc.source == "lamin_pathway":
            sections["Pathway ontology (Lamin/bionty)"].append(line)
        elif doc.source in ("lamin_organism", "lamin_gene"):
            sections["Organisms & genes (Lamin/bionty)"].append(line)
        elif doc.source == "lamin_artifact":
            sections["Public datasets (Lamin)"].append(line)
        else:
            sections["Literature"].append(line)

    parts = [
        "## Retrieved evidence (ground pathway candidates in these sources; cite DOI/PMID when used)"
    ]
    for heading, lines in sections.items():
        if lines:
            parts.append(f"\n### {heading}")
            parts.extend(f"- {line}" for line in lines)

    text = "\n".join(parts)
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rsplit("\n", 1)[0] + "..."


def retrieval_source_tags(docs: list[RetrievedDocument]) -> list[str]:
    tags: list[str] = []
    for doc in docs:
        if doc.source not in tags:
            tags.append(doc.source)
    return tags


def retrieve_literature_context(brief: ResearchBrief) -> list[RetrievedDocument]:
    if is_offline():
        return []

    settings = get_settings()
    if not settings.literature_retrieval_enabled:
        return []

    import time

    from mindbrew_v2.progress import log, tool_end, tool_start
    from mindbrew_v2.telemetry import start_span

    queries = build_retrieval_queries(brief)
    if not queries:
        return []

    tool_id = "literature.retrieve"
    label = f"Literature retrieval ({len(queries)} queries)"
    tool_start(tool_id, label)
    started = time.perf_counter()

    with start_span("tool.call", {"tool_id": tool_id, "query_count": len(queries)}):
        docs: list[RetrievedDocument] = []
        seen_keys: set[str] = set()

        for index, query in enumerate(queries, start=1):
            preview = query if len(query) <= 120 else f"{query[:117]}…"
            log(f"Query {index}/{len(queries)}: {preview}")
            docs.extend(_safe_retrieve(query, settings, seen_keys))

        duration_ms = int((time.perf_counter() - started) * 1000)
        tool_end(tool_id, label, duration_ms=duration_ms, status="ok")
        log(
            f"Retrieved {len(docs)} documents "
            f"({', '.join(retrieval_source_tags(docs)) or 'none'}) "
            f"in {duration_ms / 1000:.1f}s"
        )
        return docs


def _safe_retrieve(query: str, settings, seen_keys: set[str]) -> list[RetrievedDocument]:
    from mindbrew_v2.progress import log

    found: list[RetrievedDocument] = []
    backends = (
        ("lamin", _fetch_lamin),
        ("pubmed", _fetch_pubmed),
        ("crossref", _fetch_crossref),
    )

    for name, fetcher in backends:
        try:
            raw = fetcher(query, settings)
            new_count = 0
            for doc in raw:
                key = _doc_dedup_key(doc)
                if key not in seen_keys:
                    seen_keys.add(key)
                    found.append(doc)
                    new_count += 1
            log(f"{name}: {len(raw)} hits ({new_count} new)")
        except Exception as exc:
            log(f"Retrieval backend {name} failed: {exc}", level="warning")

    return found


def _fetch_lamin(query: str, settings) -> list[RetrievedDocument]:
    from mindbrew_v2.tools.lamin_client import search_lamin

    return search_lamin(
        query,
        public_dbs=settings.lamin_public_db_list(),
        max_ontology_hits=settings.literature_max_ontology_hits,
        max_artifact_hits=settings.literature_max_artifact_hits,
    )


def _fetch_pubmed(query: str, settings) -> list[RetrievedDocument]:
    from mindbrew_v2.tools.pubmed_search import search_pubmed

    return search_pubmed(query, max_results=settings.literature_max_pubmed_hits)


def _fetch_crossref(query: str, settings) -> list[RetrievedDocument]:
    from mindbrew_v2.tools.crossref_search import search_crossref

    return search_crossref(query, max_results=settings.literature_max_crossref_hits)


def _format_document_line(doc: RetrievedDocument) -> str:
    prefix = ""
    if doc.pmid:
        prefix = f"PMID {doc.pmid}: "
    elif doc.doi:
        prefix = f"DOI {doc.doi}: "
    elif doc.ontology_id:
        prefix = f"{doc.ontology_id}: "

    snippet = doc.snippet.strip()
    if snippet and snippet != doc.title:
        return f"{prefix}{doc.title} — {snippet}"
    return f"{prefix}{doc.title}"


def _doc_dedup_key(doc: RetrievedDocument) -> str:
    if doc.pmid:
        return f"pmid:{doc.pmid}"
    if doc.doi:
        return f"doi:{doc.doi}"
    if doc.ontology_id:
        return f"onto:{doc.ontology_id}:{doc.source}"
    return f"{doc.source}:{doc.title}"
