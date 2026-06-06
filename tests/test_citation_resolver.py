"""Tests for citation resolver (offline mode)."""

import os

import pytest

os.environ.setdefault("BREWMIND_OFFLINE", "true")

from mindbrew_v2.models import Citation
from mindbrew_v2.tools.citation_resolver import resolve_citation, resolve_citations


def test_resolve_doi_offline():
    c = resolve_citation(Citation(doi="10.1002/bit.26067", title="Wax ester"))
    assert c.validation_status == "verified"
    assert c.url is not None
    assert "doi.org" in c.url


def test_resolve_invalid_pmid_offline():
    c = resolve_citation(Citation(pmid="12345678", title="Placeholder"))
    assert c.validation_status == "invalid"


def test_resolve_no_id_invalid():
    c = resolve_citation(Citation(title="No identifiers"))
    assert c.validation_status == "invalid"


def test_resolve_citations_batch():
    citations = resolve_citations([
        Citation(doi="10.1002/bit.26067"),
        Citation(pmid="12345678"),
    ])
    assert len(citations) == 2
    assert citations[0].validation_status == "verified"
    assert citations[1].validation_status == "invalid"


def test_resolve_pmid_with_dict_authors():
    from unittest.mock import MagicMock, patch

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "result": {
            "99999": {
                "title": "Wax ester production in yeast.",
                "authors": [{"name": "Smith J"}, {"name": "Doe A"}],
                "pubdate": "2018 Jan",
                "fulljournalname": "Biotechnology Journal",
                "articleids": [{"idtype": "doi", "value": "10.1002/bit.26067"}],
            }
        }
    }

    with patch("httpx.Client") as mock_client:
        mock_client.return_value.__enter__.return_value.get.return_value = mock_response
        with patch("mindbrew_v2.tools.citation_resolver.is_offline", return_value=False):
            c = resolve_citation(Citation(pmid="99999", title="Placeholder"))

    assert c.validation_status == "verified"
    assert c.authors == "Smith J, Doe A"
    assert c.doi == "10.1002/bit.26067"
