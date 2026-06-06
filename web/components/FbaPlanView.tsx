import type { Citation } from "@/lib/bioLinks";
import { card, cardTitle } from "@/lib/ui";
import CitationBadge from "./CitationBadge";

type CandidateReaction = {
  id: string;
  name: string;
  stoichiometry?: Record<string, number>;
  gene_associations?: string[];
};

type ScorePayload = {
  pathway_id: string;
  model_ref?: string;
  scenario?: string;
  carbon_source_rxn?: string;
  product_metabolite?: string;
  knockouts?: string[];
  substrate_moles_per_product?: number;
  candidate_reactions?: CandidateReaction[];
  source_citations?: Citation[];
};

function formatStoichiometry(stoich: Record<string, number>): string {
  const parts = Object.entries(stoich).map(([met, coeff]) => {
    const sign = coeff < 0 ? "−" : "+";
    const abs = Math.abs(coeff);
    const coefStr = abs === 1 ? "" : `${abs} `;
    return `${sign}${coefStr}${met}`;
  });
  return parts.join(" ");
}

export default function FbaPlanView({
  payloads,
  skipped,
  gemProfile,
}: {
  payloads: ScorePayload[];
  skipped?: string[];
  gemProfile?: Record<string, unknown> | null;
}) {
  return (
    <div className={card}>
      <h3 className={cardTitle}>FBA formalization plan</h3>
      {gemProfile && (
        <p className="text-sm text-muted">
          Model: {String(gemProfile.model_ref || gemProfile.gem_id || "")} /{" "}
          {String(gemProfile.scenario || "")}
        </p>
      )}
      {payloads.map((p) => (
        <div key={p.pathway_id} className="border-b border-border py-3 text-sm last:border-b-0">
          <strong>{p.pathway_id}</strong>
          <dl className="my-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-xs">
            {p.carbon_source_rxn && (
              <>
                <dt className="text-muted">Carbon source</dt>
                <dd className="font-mono">{p.carbon_source_rxn}</dd>
              </>
            )}
            {p.product_metabolite && (
              <>
                <dt className="text-muted">Product</dt>
                <dd className="font-mono">{p.product_metabolite}</dd>
              </>
            )}
            {p.scenario && (
              <>
                <dt className="text-muted">Scenario</dt>
                <dd className="break-all font-mono">{p.scenario}</dd>
              </>
            )}
            {(p.knockouts ?? []).length > 0 && (
              <>
                <dt className="text-muted">Knockouts</dt>
                <dd className="font-mono">{(p.knockouts ?? []).join(", ")}</dd>
              </>
            )}
            {p.substrate_moles_per_product != null && p.substrate_moles_per_product !== 1 && (
              <>
                <dt className="text-muted">Substrate mol/product</dt>
                <dd>{p.substrate_moles_per_product}</dd>
              </>
            )}
          </dl>
          {(p.candidate_reactions ?? []).length > 0 && (
            <ul className="my-1.5 list-none space-y-2 pl-0">
              {(p.candidate_reactions ?? []).map((r) => (
                <li key={r.id} className="rounded border border-border/60 px-2 py-1.5">
                  <div>
                    <strong>{r.id}</strong>
                    {r.name ? <span className="text-muted"> — {r.name}</span> : null}
                  </div>
                  {r.stoichiometry && Object.keys(r.stoichiometry).length > 0 && (
                    <div className="mt-1 font-mono text-xs text-muted">
                      {formatStoichiometry(r.stoichiometry)}
                    </div>
                  )}
                  {r.gene_associations?.length ? (
                    <div className="mt-0.5 text-xs text-muted">
                      genes: {r.gene_associations.join(", ")}
                    </div>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
          {(p.source_citations ?? []).length > 0 && (
            <div className="mt-1.5">
              <strong className="text-xs">Source literature</strong>
              {(p.source_citations ?? []).map((c, i) => (
                <CitationBadge key={`${p.pathway_id}-src-${i}`} citation={c} />
              ))}
            </div>
          )}
        </div>
      ))}
      {(skipped ?? []).length > 0 && (
        <div className="mt-3 text-sm text-danger">
          <strong>Skipped:</strong>
          <ul className="list-disc pl-5">
            {(skipped ?? []).map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
