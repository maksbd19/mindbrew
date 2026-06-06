"""Tests for bio link URL builders."""

from mindbrew_v2.tools.bio_links import (
    citation_url,
    doi_link,
    ec_link,
    gene_link,
    kegg_compound_link,
    pmid_link,
)


def test_ec_link_full():
    link = ec_link("1.2.1.84")
    assert link is not None
    assert link["url"] == "https://www.genome.jp/entry/ec:1.2.1.84"


def test_ec_link_partial_returns_none():
    assert ec_link("2.3.1.---") is None
    assert ec_link(None) is None


def test_gene_link_with_organism():
    link = gene_link("FAR", "Yarrowia lipolytica")
    assert link is not None
    assert "gene:FAR" in link["url"]
    assert "Yarrowia" in link["url"]


def test_doi_link_biorxiv():
    link = doi_link("10.1101/2024.01.01.123456")
    assert link is not None
    assert "biorxiv.org" in link["url"]


def test_doi_link_standard():
    link = doi_link("10.1002/bit.26067")
    assert link is not None
    assert link["url"] == "https://doi.org/10.1002/bit.26067"


def test_pmid_link():
    link = pmid_link("12345678")
    assert link is not None
    assert link["url"] == "https://pubmed.ncbi.nlm.nih.gov/12345678/"


def test_kegg_compound_link():
    link = kegg_compound_link("C00001")
    assert link is not None
    assert "C00001" in link["url"]


def test_citation_url_prefers_pmid():
    url = citation_url(doi="10.1002/bit.26067", pmid="999")
    assert url is not None
    assert "pubmed" in url
