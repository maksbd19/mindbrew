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
