"""Tests for literature retrieval (Lamin + PubMed + Crossref RAG)."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("BREWMIND_OFFLINE", "true")

from mindbrew_v2.models import CompoundSpec, PathwayCandidate, ResearchBrief
from mindbrew_v2.tools.literature_retrieval import (
    RetrievedDocument,
    build_retrieval_queries,
    format_context_block,
    retrieve_literature_context,
    retrieval_source_tags,
)


@pytest.fixture
def sample_brief() -> ResearchBrief:
    return ResearchBrief(
        ticket_id="t1",
        raw_brief="Convert oleate to wax ester in Yarrowia lipolytica",
        organism=["Yarrowia lipolytica"],
        feedstock=CompoundSpec(name="oleate", compound_class="plant_oil"),
        target=CompoundSpec(name="wax ester", compound_class="wax_ester"),
        target_function="silicone replacement emollient",
        constraints=["no GMO allergens"],
    )


def test_build_retrieval_queries(sample_brief: ResearchBrief):
    queries = build_retrieval_queries(sample_brief)
    assert len(queries) >= 2
    assert any("oleate" in q and "wax ester" in q for q in queries)
    assert any("biosynthesis" in q for q in queries)


def test_format_context_block_groups_sources():
    docs = [
        RetrievedDocument(
            source="lamin_pathway",
            title="lipid metabolic process",
            snippet="The chemical reactions involving lipids.",
            ontology_id="GO:0006629",
        ),
        RetrievedDocument(
            source="pubmed",
            title="Wax ester production",
            snippet="Abstract text here.",
            pmid="12345678",
        ),
        RetrievedDocument(
            source="crossref",
            title="Engineered pathway",
            snippet="Methods for wax ester.",
            doi="10.1002/bit.26067",
        ),
    ]
    text = format_context_block(docs, max_chars=8000)
    assert "Pathway ontology" in text
    assert "GO:0006629" in text
    assert "PMID 12345678" in text
    assert "DOI 10.1002/bit.26067" in text


def test_format_context_block_truncates():
    docs = [
        RetrievedDocument(
            source="pubmed",
            title=f"Paper {i}",
            snippet="x" * 200,
            pmid=str(i),
        )
        for i in range(20)
    ]
    text = format_context_block(docs, max_chars=500)
    assert len(text) <= 503
    assert text.endswith("...")


def test_retrieval_source_tags():
    docs = [
        RetrievedDocument(source="pubmed", title="A", snippet="a", pmid="1"),
        RetrievedDocument(source="pubmed", title="B", snippet="b", pmid="2"),
        RetrievedDocument(source="lamin_pathway", title="C", snippet="c", ontology_id="GO:1"),
    ]
    assert retrieval_source_tags(docs) == ["pubmed", "lamin_pathway"]


def test_retrieve_literature_context_offline(sample_brief: ResearchBrief):
    with patch("mindbrew_v2.tools.literature_retrieval.is_offline", return_value=True):
        assert retrieve_literature_context(sample_brief) == []


def test_search_pubmed_parses_results():
    from mindbrew_v2.tools.pubmed_search import search_pubmed

    esearch_resp = MagicMock()
    esearch_resp.json.return_value = {"esearchresult": {"idlist": ["12345"]}}
    esearch_resp.raise_for_status = MagicMock()

    esummary_resp = MagicMock()
    esummary_resp.json.return_value = {
        "result": {
            "12345": {
                "title": "Wax ester in yeast.",
                "fulljournalname": "Biotech Journal",
                "articleids": [{"idtype": "doi", "value": "10.1002/bit.26067"}],
            }
        }
    }
    esummary_resp.raise_for_status = MagicMock()

    efetch_resp = MagicMock()
    efetch_resp.status_code = 200
    efetch_resp.text = "PMID- 12345\nAB  - Engineered wax ester pathway in Yarrowia."

    def mock_get(url, **kwargs):
        if "esearch" in url:
            return esearch_resp
        if "esummary" in url:
            return esummary_resp
        return efetch_resp

    with patch("httpx.Client") as mock_client:
        mock_client.return_value.__enter__.return_value.get = mock_get
        docs = search_pubmed("wax ester yarrowia", max_results=3)

    assert len(docs) == 1
    assert docs[0].pmid == "12345"
    assert docs[0].doi == "10.1002/bit.26067"
    assert "Wax ester" in docs[0].title


def test_search_crossref_parses_results():
    from mindbrew_v2.tools.crossref_search import search_crossref

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "message": {
            "items": [
                {
                    "DOI": "10.1002/bit.26067",
                    "title": ["Production of wax esters"],
                    "abstract": "<jats:p>Abstract about wax esters.</jats:p>",
                    "published-print": {"date-parts": [[2018]]},
                }
            ]
        }
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.Client") as mock_client:
        mock_client.return_value.__enter__.return_value.get.return_value = mock_response
        docs = search_crossref("wax ester", max_results=1)

    assert len(docs) == 1
    assert docs[0].doi == "10.1002/bit.26067"
    assert "wax esters" in docs[0].snippet.lower()


def test_search_pathways_adds_provenance(sample_brief: ResearchBrief):
    from mindbrew_v2.tools import literature_client

    context = [
        RetrievedDocument(source="pubmed", title="Paper", snippet="snippet", pmid="99"),
    ]
    mock_result = literature_client.PathwayCandidateList(
        candidates=[
            PathwayCandidate(
                id="pw1",
                name="Pathway A",
                biomni_provenance=["literature_search"],
            )
        ]
    )

    with (
        patch(
            "mindbrew_v2.tools.literature_client.retrieve_literature_context",
            return_value=context,
        ),
        patch(
            "mindbrew_v2.tools.literature_client.structured_extract",
            return_value=mock_result,
        ),
        patch("mindbrew_v2.tools.literature_client.is_offline", return_value=False),
    ):
        results = literature_client.search_pathways(sample_brief)

    assert results[0]["biomni_provenance"] == ["literature_search", "pubmed"]
