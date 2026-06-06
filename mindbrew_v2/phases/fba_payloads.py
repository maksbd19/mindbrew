"""Build ScorePathwayPayload from find_ids report and pathway candidates."""

from __future__ import annotations

from mindbrew_v2.models import CandidateReaction, GemProfile, PathwayCandidate, ScorePathwayPayload
from mindbrew_v2.phases.fba_metabolite_resolver import FbaMetaboliteMapping


def collect_enzyme_tokens(cand: PathwayCandidate) -> set[str]:
    tokens: set[str] = set()
    for enzyme in cand.enzymes:
        tokens.add(enzyme.upper())
    for step in cand.reaction_steps:
        if step.enzyme_name:
            tokens.add(step.enzyme_name.upper())
        tokens.update(g.upper() for g in step.gene_names)
    return tokens


def has_far_ws(tokens: set[str]) -> tuple[bool, bool]:
    has_far = any("FAR" in token for token in tokens)
    has_ws = any("WS" in token or "WAX" in token for token in tokens)
    return has_far, has_ws


def build_far_ws_reactions(
    recommended: dict,
    mapping: FbaMetaboliteMapping,
    has_far: bool,
    has_ws: bool,
) -> list[CandidateReaction] | None:
    oleoyl = recommended.get("oleoyl_coa_metabolite")
    nadph = recommended.get("nadph_metabolite")
    nadp = recommended.get("nadp_metabolite")
    coa = recommended.get("coa_metabolite")
    fatty_alcohol = mapping.fatty_alcohol_metabolite
    product = mapping.product_metabolite
    if not all([oleoyl, nadph, nadp, coa, fatty_alcohol, product]):
        return None

    reactions: list[CandidateReaction] = []
    if has_far:
        reactions.append(
            CandidateReaction(
                id="FAR",
                name="fatty acyl-CoA reductase",
                stoichiometry={
                    oleoyl: -1.0,
                    nadph: -2.0,
                    fatty_alcohol: 1.0,
                    coa: 1.0,
                    nadp: 2.0,
                },
                gene_associations=["FAR"],
            )
        )
    if has_ws:
        reactions.append(
            CandidateReaction(
                id="WS",
                name="wax ester synthase",
                stoichiometry={
                    fatty_alcohol: -1.0,
                    oleoyl: -1.0,
                    product: 1.0,
                    coa: 1.0,
                },
                gene_associations=["WS", "WSD1"],
            )
        )
    return reactions or None


def resolve_knockouts(find_ids: dict, tokens: set[str]) -> list[str]:
    knockouts: list[str] = []
    alias_map = find_ids.get("gene_alias_resolution", {})

    for token in tokens:
        for gene, hits in alias_map.items():
            if token == gene.upper() or token.startswith(gene.upper()):
                for hit in hits:
                    if hit.get("type") == "reaction":
                        rid = hit.get("id")
                        if rid and rid not in knockouts:
                            knockouts.append(rid)

    if any("DGA" in token or "LRO" in token or "TAG" in token or "POX" in token for token in tokens):
        for gene in ("POX1", "POX2", "POX3", "POX4", "POX5", "POX6", "DGA1", "LRO1", "ARE1"):
            for hit in alias_map.get(gene, []):
                if hit.get("type") == "reaction":
                    rid = hit.get("id")
                    if rid and rid not in knockouts:
                        knockouts.append(rid)

    return knockouts


def build_generic_reactions(
    cand: PathwayCandidate,
    recommended: dict,
    mapping: FbaMetaboliteMapping,
) -> list[CandidateReaction] | None:
    """Best-effort mapping when FAR/WS template does not apply."""
    acyl_pool = recommended.get("oleoyl_coa_metabolite")
    product = mapping.product_metabolite
    if not acyl_pool or not product or not cand.reaction_steps:
        return None
    reactions: list[CandidateReaction] = []
    for index, step in enumerate(cand.reaction_steps, start=1):
        rxn_id = step.enzyme_name or step.gene_names[0] if step.gene_names else f"RXN_{index}"
        rxn_id = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in rxn_id.upper())[:20]
        stoich: dict[str, float] = {}
        if step.substrates:
            stoich[acyl_pool] = stoich.get(acyl_pool, 0) - 1.0
        if step.products:
            stoich[product] = stoich.get(product, 0) + 1.0
        if not stoich:
            continue
        reactions.append(
            CandidateReaction(
                id=rxn_id,
                name=step.description or rxn_id,
                stoichiometry=stoich,
                gene_associations=list(step.gene_names),
            )
        )
    return reactions or None


def build_payload_from_find_ids(
    cand: PathwayCandidate,
    gem: GemProfile,
    find_ids: dict,
    mapping: FbaMetaboliteMapping,
) -> ScorePathwayPayload | None:
    recommended = find_ids.get("recommended", {})
    tokens = collect_enzyme_tokens(cand)
    has_far, has_ws = has_far_ws(tokens)

    reactions: list[CandidateReaction] | None = None
    use_far_ws = mapping.pathway_template == "far_ws" or has_far or has_ws
    if use_far_ws and (has_far or has_ws):
        reactions = build_far_ws_reactions(recommended, mapping, has_far, has_ws)
    if not reactions:
        reactions = build_generic_reactions(cand, recommended, mapping)

    if not reactions:
        return None

    carbon_source = recommended.get("carbon_source_rxn", "")
    if not carbon_source:
        return None

    return ScorePathwayPayload(
        pathway_id=cand.id,
        model_ref=gem.model_ref,
        scenario=gem.scenario,
        carbon_source_rxn=carbon_source,
        candidate_reactions=reactions,
        product_metabolite=mapping.product_metabolite,
        knockouts=resolve_knockouts(find_ids, tokens),
        substrate_moles_per_product=mapping.substrate_moles_per_product,
        objective="product",
        source_citations=cand.citations,
    )


def summarize_find_ids(find_ids: dict) -> dict:
    recommended = find_ids.get("recommended", {})
    summary = find_ids.get("summary", {})
    return {
        "status": find_ids.get("status"),
        "carbon_source_rxn": recommended.get("carbon_source_rxn"),
        "oleoyl_coa_metabolite": recommended.get("oleoyl_coa_metabolite"),
        "has_gene_associations": summary.get("has_gene_associations"),
        "peroxisomal_acyl_coa_oxidases": find_ids.get("peroxisomal_acyl_coa_oxidases", []),
    }
