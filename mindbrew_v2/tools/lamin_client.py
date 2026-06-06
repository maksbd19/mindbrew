"""Public Lamin/bionty ontology and artifact search."""

from __future__ import annotations

from mindbrew_v2.tools.literature_retrieval import RetrievedDocument


def search_lamin(
    query: str,
    *,
    public_dbs: list[str],
    max_ontology_hits: int = 5,
    max_artifact_hits: int = 5,
) -> list[RetrievedDocument]:
    docs: list[RetrievedDocument] = []
    docs.extend(_search_ontologies(query, max_ontology_hits))
    docs.extend(_search_artifacts(query, public_dbs, max_artifact_hits))
    return docs


def _search_ontologies(query: str, max_hits: int) -> list[RetrievedDocument]:
    try:
        import bionty.base as bt_base
    except ImportError:
        return []

    docs: list[RetrievedDocument] = []
    docs.extend(_search_ontology_registry(bt_base.Pathway(), query, "lamin_pathway", max_hits))
    docs.extend(_search_ontology_registry(bt_base.Organism(), query, "lamin_organism", max(2, max_hits // 2)))
    docs.extend(_search_ontology_registry(bt_base.Gene(), query, "lamin_gene", max(2, max_hits // 2)))
    return docs


def _search_ontology_registry(registry, query: str, source: str, max_hits: int) -> list[RetrievedDocument]:
    docs: list[RetrievedDocument] = []
    try:
        hits = registry.search(query)
        if hasattr(hits, "head"):
            df = hits.head(max_hits)
        else:
            return docs

        if df is None or getattr(df, "empty", True):
            return docs

        for _, row in df.iterrows():
            name = str(row.get("name", "") or row.get("symbol", "") or "")
            if not name:
                continue
            ontology_id = str(row.get("ontology_id", "") or row.get("uid", "") or "")
            definition = str(row.get("definition", "") or row.get("description", "") or "")
            docs.append(
                RetrievedDocument(
                    source=source,
                    title=name,
                    snippet=definition[:500],
                    ontology_id=ontology_id or None,
                    url=f"https://bioportal.bioontology.org/ontologies/{ontology_id.split(':')[0]}"
                    if ontology_id and ":" in ontology_id
                    else None,
                )
            )
    except Exception:
        return docs
    return docs


def _search_artifacts(query: str, public_dbs: list[str], max_hits: int) -> list[RetrievedDocument]:
    try:
        import lamindb as ln
    except ImportError:
        return []

    docs: list[RetrievedDocument] = []
    for db_name in public_dbs:
        db_name = db_name.strip()
        if not db_name:
            continue
        try:
            db = ln.DB(db_name)
            hits = db.Artifact.search(query)
            df = hits.to_dataframe() if hasattr(hits, "to_dataframe") else None
            if df is None or df.empty:
                continue

            for _, row in df.head(max_hits).iterrows():
                uid = str(row.get("uid", "") or row.get("id", "") or "")
                key = str(row.get("key", "") or "")
                description = str(row.get("description", "") or "")
                title = key or uid or "artifact"
                url = f"https://lamin.ai/{db_name}/artifact/{uid}" if uid else f"https://lamin.ai/explore"
                docs.append(
                    RetrievedDocument(
                        source="lamin_artifact",
                        title=title,
                        snippet=description[:500] if description else f"Public dataset in {db_name}",
                        url=url,
                        ontology_id=uid or None,
                    )
                )
        except Exception:
            continue
    return docs
