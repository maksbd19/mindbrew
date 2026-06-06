"""Deterministic URL builders for biological entities."""

from __future__ import annotations

import re
from typing import TypedDict
from urllib.parse import quote_plus


class BioLink(TypedDict):
    label: str
    url: str


_PARTIAL_EC = re.compile(r"-{2,}|\.-|\.$")


def ec_link(ec: str | None) -> BioLink | None:
    if not ec or _PARTIAL_EC.search(ec):
        return None
    clean = ec.strip()
    return {"label": "KEGG", "url": f"https://www.genome.jp/entry/ec:{clean}"}


def gene_link(gene: str, organism: str | None = None) -> BioLink | None:
    if not gene or not gene.strip():
        return None
    query = f"gene:{gene.strip()}"
    if organism:
        query += f"+AND+organism_name:{quote_plus(organism)}"
    return {
        "label": "UniProt",
        "url": f"https://www.uniprot.org/uniprotkb?query={query}",
    }


def kegg_compound_link(kegg_id: str | None) -> BioLink | None:
    if not kegg_id:
        return None
    kid = kegg_id.strip()
    if not kid.startswith("C"):
        kid = f"C{kid}" if kid.isdigit() else kid
    return {"label": "KEGG", "url": f"https://www.genome.jp/entry/{kid}"}


def doi_link(doi: str | None) -> BioLink | None:
    if not doi:
        return None
    clean = doi.strip().removeprefix("https://doi.org/").removeprefix("http://doi.org/")
    if clean.startswith("10.1101/"):
        return {"label": "bioRxiv", "url": f"https://www.biorxiv.org/content/{clean}"}
    return {"label": "DOI", "url": f"https://doi.org/{clean}"}


def pmid_link(pmid: str | None) -> BioLink | None:
    if not pmid:
        return None
    clean = re.sub(r"\D", "", pmid.strip())
    if not clean:
        return None
    return {"label": "PubMed", "url": f"https://pubmed.ncbi.nlm.nih.gov/{clean}/"}


def citation_url(doi: str | None = None, pmid: str | None = None) -> str | None:
    if pmid:
        link = pmid_link(pmid)
        if link:
            return link["url"]
    if doi:
        link = doi_link(doi)
        if link:
            return link["url"]
    return None
