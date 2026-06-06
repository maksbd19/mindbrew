"""Infer FBA metabolite IDs and stoichiometry from target product and literature."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from mindbrew_v2.config.llm import structured_extract
from mindbrew_v2.models import PathwayCandidate, ResearchBrief


class FbaMetaboliteMapping(BaseModel):
    product_metabolite: str = Field(description="Target product metabolite id in the GSMM (usually _c compartment)")
    fatty_alcohol_metabolite: str | None = Field(
        default=None,
        description="Fatty alcohol intermediate for FAR+WS wax/lipid ester pathways",
    )
    substrate_moles_per_product: float = Field(
        default=1.0,
        description="Feedstock mol per product mol from pathway stoichiometry",
    )
    product_search_terms: list[str] = Field(default_factory=list)
    pathway_template: str = Field(default="generic", description="far_ws or generic")
    rationale: str = ""


def _slug_metabolite_id(label: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")
    return f"{slug}_c" if slug else "product_c"


def search_terms_from_brief(brief: ResearchBrief) -> list[str]:
    terms: list[str] = []
    for value in (
        brief.target.name,
        brief.target.compound_class,
        brief.feedstock.name,
        brief.feedstock.compound_class,
        brief.target_function,
    ):
        if value:
            terms.append(value)
    if brief.target.kegg_id:
        terms.append(brief.target.kegg_id)
    if brief.feedstock.kegg_id:
        terms.append(brief.feedstock.kegg_id)
    return terms


def _pathway_literature_context(cand: PathwayCandidate) -> str:
    lines = [f"Pathway: {cand.name}", f"Description: {cand.description}"]
    for step in cand.reaction_steps:
        lines.append(
            f"Step {step.step_number}: {step.description} "
            f"(enzyme={step.enzyme_name or 'unknown'}, genes={', '.join(step.gene_names) or 'none'})"
        )
    for cite in cand.citations[:5]:
        label = cite.title or cite.doi or cite.pmid or "citation"
        snippet = f" — {cite.snippet}" if cite.snippet else ""
        lines.append(f"Citation: {label}{snippet}")
    return "\n".join(lines)


def _find_ids_metabolite_hits(find_ids: dict, term: str) -> list[dict]:
    searches = find_ids.get("searches", {}).get("metabolites", {})
    hits: list[dict] = []
    term_lower = term.lower()
    for key, rows in searches.items():
        if term_lower in key.lower() or key.lower() in term_lower:
            hits.extend(rows)
    if term_lower in searches:
        hits.extend(searches[term_lower])
    return hits


def _pick_model_metabolite(
    find_ids: dict,
    terms: list[str],
    *,
    prefer_compartment: str = "c",
    require_substring: str | None = None,
    exclude_substrings: tuple[str, ...] = (),
) -> str | None:
    seen: set[str] = set()
    candidates: list[dict] = []
    for term in terms:
        for hit in _find_ids_metabolite_hits(find_ids, term):
            mid = hit.get("id")
            if not mid or mid in seen:
                continue
            seen.add(mid)
            candidates.append(hit)

    if not candidates:
        return None

    filtered = candidates
    if require_substring:
        filtered = [
            hit
            for hit in candidates
            if require_substring in hit.get("id", "").lower()
            or require_substring in hit.get("name", "").lower()
        ] or candidates
    if exclude_substrings:
        filtered = [
            hit
            for hit in filtered
            if not any(ex in hit.get("id", "").lower() or ex in hit.get("name", "").lower() for ex in exclude_substrings)
        ] or filtered

    def score(hit: dict) -> tuple[int, str]:
        compartment = hit.get("compartment", "")
        compartment_match = compartment == prefer_compartment
        return (0 if compartment_match else 1, hit.get("id", ""))

    filtered.sort(key=score)
    return filtered[0]["id"]


def _ground_mapping(mapping: FbaMetaboliteMapping, find_ids: dict, brief: ResearchBrief) -> FbaMetaboliteMapping:
    product_terms = list(mapping.product_search_terms)
    product_terms.extend(
        term
        for term in (
            brief.target.name,
            brief.target.compound_class,
            mapping.product_metabolite.replace("_c", "").replace("_", " "),
        )
        if term
    )

    resolved_product = _pick_model_metabolite(find_ids, product_terms)
    product_metabolite = resolved_product or mapping.product_metabolite

    fatty_alcohol = mapping.fatty_alcohol_metabolite
    if mapping.pathway_template == "far_ws":
        alcohol_terms = ["fatty alcohol", "oleyl alcohol", "hexadecanol", "octadecanol"]
        if fatty_alcohol:
            alcohol_terms.append(fatty_alcohol.replace("_c", "").replace("_", " "))
        resolved_alcohol = _pick_model_metabolite(
            find_ids,
            alcohol_terms,
            require_substring="alcohol",
            exclude_substrings=("coa", "acyl"),
        )
        fatty_alcohol = resolved_alcohol or fatty_alcohol or "fatty_alcohol_c"

    return mapping.model_copy(
        update={
            "product_metabolite": product_metabolite,
            "fatty_alcohol_metabolite": fatty_alcohol,
        }
    )


def infer_fba_metabolite_mapping(
    brief: ResearchBrief,
    cand: PathwayCandidate,
    find_ids: dict,
) -> FbaMetaboliteMapping:
    recommended = find_ids.get("recommended", {})
    search_summary = find_ids.get("searches", {}).get("metabolites", {})
    highlighted = {
        term: rows[:5]
        for term, rows in search_summary.items()
        if rows and term in {"wax", "ester", "alcohol", "oleate", "oleic", "octadec"}
    }

    prompt = f"""Infer FBA metabolite mapping for flux balance analysis.

Target product:
- name: {brief.target.name or 'unknown'}
- class: {brief.target.compound_class or 'unknown'}
- kegg_id: {brief.target.kegg_id or 'none'}

Feedstock:
- name: {brief.feedstock.name or 'unknown'}
- class: {brief.feedstock.compound_class or 'unknown'}
- kegg_id: {brief.feedstock.kegg_id or 'none'}

Organism: {', '.join(brief.organism) if brief.organism else 'unknown'}
Target function: {brief.target_function or 'none'}

Pathway literature:
{_pathway_literature_context(cand)}

Model pool metabolites already resolved (find_ids recommended):
- acyl-CoA pool: {recommended.get('oleoyl_coa_metabolite')}
- carbon source exchange: {recommended.get('carbon_source_rxn')}

Relevant model metabolite search hits:
{highlighted}

Rules:
1. product_metabolite must be a valid cobra-style id (lowercase, underscores, cytoplasm suffix _c).
2. If the target is a wax ester made via FAR+WS, use pathway_template=far_ws, set fatty_alcohol_metabolite,
   and substrate_moles_per_product from stoichiometry (typically 2.0 mol C18 feedstock per C36 wax ester).
3. Derive ids and stoichiometry from the pathway description and citations, not from unrelated products.
4. product_search_terms should help locate an existing metabolite in the GSMM; include chemical synonyms.
5. If no model hit exists, propose a new reasonable id (e.g. wax_ester_c for wax esters).
"""
    mapping = structured_extract(prompt, FbaMetaboliteMapping, role="parser")
    if not mapping.product_metabolite:
        mapping = mapping.model_copy(update={"product_metabolite": _slug_metabolite_id(brief.target.name or brief.target.compound_class or "product")})
    return _ground_mapping(mapping, find_ids, brief)
