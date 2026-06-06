export type BioLink = { label: string; url: string };

const PARTIAL_EC = /-{2,}|\.-|\.$/;

export function ecLink(ec: string | null | undefined): BioLink | null {
  if (!ec || PARTIAL_EC.test(ec)) return null;
  return { label: "KEGG", url: `https://www.genome.jp/entry/ec:${ec.trim()}` };
}

export function geneLink(gene: string, organism?: string | null): BioLink | null {
  if (!gene?.trim()) return null;
  let query = `gene:${gene.trim()}`;
  if (organism) {
    query += `+AND+organism_name:${encodeURIComponent(organism)}`;
  }
  return {
    label: "UniProt",
    url: `https://www.uniprot.org/uniparc?query=${encodeURIComponent(query)}`,
  };
}


export function keggCompoundLink(keggId: string | null | undefined): BioLink | null {
  if (!keggId) return null;
  const kid = keggId.trim().startsWith("C") ? keggId.trim() : keggId.trim();
  return { label: "KEGG", url: `https://www.genome.jp/entry/${kid}` };
}

export function doiLink(doi: string | null | undefined): BioLink | null {
  if (!doi) return null;
  const clean = doi
    .trim()
    .replace(/^https?:\/\/doi\.org\//, "");
  if (clean.startsWith("10.1101/")) {
    return { label: "bioRxiv", url: `https://www.biorxiv.org/content/${clean}` };
  }
  return { label: "DOI", url: `https://doi.org/${clean}` };
}

export function pmidLink(pmid: string | null | undefined): BioLink | null {
  if (!pmid) return null;
  const clean = pmid.replace(/\D/g, "");
  if (!clean) return null;
  return { label: "PubMed", url: `https://pubmed.ncbi.nlm.nih.gov/${clean}/` };
}

export function citationUrl(citation: {
  doi?: string | null;
  pmid?: string | null;
  url?: string | null;
}): string | null {
  if (citation.url) return citation.url;
  if (citation.pmid) return pmidLink(citation.pmid)?.url ?? null;
  if (citation.doi) return doiLink(citation.doi)?.url ?? null;
  return null;
}

export type Citation = {
  doi?: string | null;
  pmid?: string | null;
  title?: string;
  snippet?: string;
  url?: string | null;
  authors?: string;
  year?: string;
  journal?: string;
  validation_status?: "verified" | "unverified" | "invalid";
};

export type ReactionStep = {
  step_number: number;
  description: string;
  enzyme_ec?: string | null;
  enzyme_name?: string | null;
  gene_names?: string[];
  heterologous?: boolean;
};

export type PathwayCandidate = {
  id: string;
  name: string;
  description?: string;
  confidence: string;
  confidence_rationale?: string;
  confidence_factors?: string[];
  enzymes?: string[];
  reaction_steps?: ReactionStep[];
  citations?: Citation[];
  reported_titer?: string | null;
  literature_provenance?: string[];
  /** @deprecated use literature_provenance */
  biomni_provenance?: string[];
};

export type FbaCalculationStep = {
  step: number;
  title: string;
  detail?: string;
};

export type FbaResult = {
  pathway_id: string;
  status: string;
  verdict: string;
  objective_used?: string;
  predicted_product_flux?: number | null;
  growth_rate?: number | null;
  yield_mol_per_mol_substrate?: number | null;
  yield_corrected_mol_per_mol_substrate?: number | null;
  product_confidence_level?: string;
  calibration_level?: string;
  carbon_audit_sole_source?: boolean | null;
  carbon_audit?: Record<string, unknown>;
  calculation_steps?: FbaCalculationStep[];
  simulation_context?: Record<string, unknown>;
  inserted_reactions?: string[];
  edits_applied?: Record<string, unknown>;
  solver_message?: string;
  calibration_rationale?: string;
  calibration_warnings?: string[];
  verdict_rationale?: string;
  failure_reasons?: string[];
  rank?: number | null;
  bottlenecks?: Array<{
    reaction: string;
    flux: number;
    at_bound: boolean;
    explanation?: string;
    min_flux?: number | null;
    max_flux?: number | null;
    flux_span?: number | null;
  }>;
  literature_refs?: Citation[];
};

export type GeneSuggestion = {
  gene: string;
  action: string;
  rationale?: string;
  citation?: Citation | null;
};

export type LiteraturePlan = {
  pathway_id: string;
  pathway_name: string;
  reaction_map?: ReactionStep[];
  gene_suggestions?: GeneSuggestion[];
  citations?: Citation[];
  known_risks?: string[];
  gaps?: string[];
  next_steps?: string[];
  suggested_hosts?: string[];
};

export const PATHWAY_CONFIDENCE_RUBRIC = `Pathway confidence rubric:
• strong — direct literature precedent with reported titer in target or similar host
• partial — pathway known but host/titer not demonstrated for this case
• inferred — assembled from KEGG/reaction logic without direct product evidence`;

export const FBA_VERDICT_METHODOLOGY = `FBA verdict thresholds:
• pass — optimal, yield ≥ 0.5 mol/mol, no failure flags
• marginal — optimal with yield ≥ 0.2 or unresolved bottlenecks
• fail — non-optimal or infeasible

Calibration tiers: exploratory → partial → medium_calibrated → literature_calibrated`;
