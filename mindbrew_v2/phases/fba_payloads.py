"""Build ScorePathwayPayload from find_ids report and pathway candidates."""

from __future__ import annotations

from mindbrew_v2.models import CandidateReaction, GemProfile, PathwayCandidate, ScorePathwayPayload

PRODUCT_METABOLITE = "wax_ester_c"
OLEYL_ALCOHOL = "oleyl_alcohol_c"
WAX_SUBSTRATE_MOLES = 2.0


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


def build_wax_ester_reactions(
    recommended: dict,
    has_far: bool,
    has_ws: bool,
) -> list[CandidateReaction] | None:
    oleoyl = recommended.get("oleoyl_coa_metabolite")
    nadph = recommended.get("nadph_metabolite")
    nadp = recommended.get("nadp_metabolite")
    coa = recommended.get("coa_metabolite")
    if not all([oleoyl, nadph, nadp, coa]):
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
                    OLEYL_ALCOHOL: 1.0,
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
                    OLEYL_ALCOHOL: -1.0,
                    oleoyl: -1.0,
                    PRODUCT_METABOLITE: 1.0,
                    coa: 1.0,
                },
                gene_associations=["WS", "WSD1"],
            )
        )
    return reactions or None


def resolve_knockouts(find_ids: dict, tokens: set[str]) -> list[str]:
    knockouts: list[str] = []

    for row in find_ids.get("peroxisomal_acyl_coa_oxidases", []):
        rid = row.get("id") if isinstance(row, dict) else row
        if rid and rid not in knockouts:
            knockouts.append(rid)

    alias_map = find_ids.get("gene_alias_resolution", {})
    for token in tokens:
        for gene, hits in alias_map.items():
            if gene in token or token in gene:
                for hit in hits:
                    if hit.get("type") == "reaction":
                        rid = hit.get("id")
                        if rid and rid not in knockouts:
                            knockouts.append(rid)

    if any("DGA" in token or "LRO" in token or "TAG" in token for token in tokens):
        for gene in ("DGA1", "LRO1", "ARE1"):
            for hit in alias_map.get(gene, []):
                if hit.get("type") == "reaction":
                    rid = hit.get("id")
                    if rid and rid not in knockouts:
                        knockouts.append(rid)

    return knockouts[:5]


def build_payload_from_find_ids(
    cand: PathwayCandidate,
    gem: GemProfile,
    find_ids: dict,
) -> ScorePathwayPayload | None:
    recommended = find_ids.get("recommended", {})
    tokens = collect_enzyme_tokens(cand)
    has_far, has_ws = has_far_ws(tokens)

    if not has_far and not has_ws:
        return None

    reactions = build_wax_ester_reactions(recommended, has_far, has_ws)
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
        product_metabolite=PRODUCT_METABOLITE,
        knockouts=resolve_knockouts(find_ids, tokens),
        substrate_moles_per_product=WAX_SUBSTRATE_MOLES,
        objective="product",
        source_citations=cand.citations,
    )
