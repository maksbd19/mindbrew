import type { Citation } from "@/lib/bioLinks";
import type { PathwayChoice, PathwayRunHistoryEntry } from "@/lib/pathwaySelection";
import ArtifactPanel, { ArtifactSection } from "./ArtifactPanel";
import CitationBadge from "./CitationBadge";
import PriorPathwayRuns from "./PriorPathwayRuns";

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

function PlanPayloads({
  payloads,
  skipped,
}: {
  payloads: ScorePayload[];
  skipped?: string[];
}) {
  return (
    <>
      <div className="space-y-4">
        {payloads.map((p) => (
          <div key={p.pathway_id} className="rounded-lg border border-border-subtle bg-surface-raised/50 p-4">
            <h3 className="font-mono text-[14px] font-semibold text-accent">{p.pathway_id}</h3>

            <dl className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
              {p.carbon_source_rxn && (
                <div>
                  <dt className="text-[11px] font-medium uppercase tracking-wide text-muted">Carbon source</dt>
                  <dd className="mt-0.5 font-mono text-[13px] text-foreground">{p.carbon_source_rxn}</dd>
                </div>
              )}
              {p.product_metabolite && (
                <div>
                  <dt className="text-[11px] font-medium uppercase tracking-wide text-muted">Product</dt>
                  <dd className="mt-0.5 font-mono text-[13px] text-foreground">{p.product_metabolite}</dd>
                </div>
              )}
              {p.scenario && (
                <div className="sm:col-span-2">
                  <dt className="text-[11px] font-medium uppercase tracking-wide text-muted">Scenario</dt>
                  <dd className="mt-0.5 break-all font-mono text-[13px] text-foreground">{p.scenario}</dd>
                </div>
              )}
              {(p.knockouts ?? []).length > 0 && (
                <div className="sm:col-span-2">
                  <dt className="text-[11px] font-medium uppercase tracking-wide text-muted">Knockouts</dt>
                  <dd className="mt-0.5 font-mono text-[13px] text-foreground">{(p.knockouts ?? []).join(", ")}</dd>
                </div>
              )}
              {p.substrate_moles_per_product != null && p.substrate_moles_per_product !== 1 && (
                <div>
                  <dt className="text-[11px] font-medium uppercase tracking-wide text-muted">Substrate mol/product</dt>
                  <dd className="mt-0.5 text-[13px] text-foreground">{p.substrate_moles_per_product}</dd>
                </div>
              )}
            </dl>

            {(p.candidate_reactions ?? []).length > 0 && (
              <ArtifactSection title="Candidate reactions">
                <ul className="space-y-2">
                  {(p.candidate_reactions ?? []).map((r) => (
                    <li key={r.id} className="rounded-md border border-border-subtle bg-surface px-3 py-2.5">
                      <div className="text-[13px]">
                        <span className="font-mono font-medium text-accent">{r.id}</span>
                        {r.name ? <span className="text-muted"> — {r.name}</span> : null}
                      </div>
                      {r.stoichiometry && Object.keys(r.stoichiometry).length > 0 && (
                        <div className="mt-1.5 font-mono text-[12px] text-muted-light">
                          {formatStoichiometry(r.stoichiometry)}
                        </div>
                      )}
                      {r.gene_associations?.length ? (
                        <div className="mt-1 text-[12px] text-muted">
                          Genes: {r.gene_associations.join(", ")}
                        </div>
                      ) : null}
                    </li>
                  ))}
                </ul>
              </ArtifactSection>
            )}

            {(p.source_citations ?? []).length > 0 && (
              <ArtifactSection title="Source literature">
                <div className="space-y-1">
                  {(p.source_citations ?? []).map((c, i) => (
                    <CitationBadge key={`${p.pathway_id}-src-${i}`} citation={c} />
                  ))}
                </div>
              </ArtifactSection>
            )}
          </div>
        ))}
      </div>

      {(skipped ?? []).length > 0 && (
        <div className="mt-4 rounded-md border border-red-900/40 bg-red-950/20 px-3 py-3">
          <p className="text-[12px] font-medium uppercase tracking-wide text-red-300">Skipped pathways</p>
          <ul className="mt-2 space-y-1 text-[13px] text-red-200">
            {(skipped ?? []).map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        </div>
      )}
    </>
  );
}

export default function FbaPlanView({
  payloads,
  skipped,
  gemProfile,
  selectedPathway,
  priorRuns,
  resolvePathwayName,
  embedded = false,
}: {
  payloads: ScorePayload[];
  skipped?: string[];
  gemProfile?: Record<string, unknown> | null;
  selectedPathway?: PathwayChoice | null;
  priorRuns?: PathwayRunHistoryEntry[];
  resolvePathwayName?: (pathwayId: string | undefined) => string;
  embedded?: boolean;
}) {
  const body = <PlanPayloads payloads={payloads} skipped={skipped} />;

  if (embedded) {
    return body;
  }

  return (
    <ArtifactPanel
      title="FBA formalization plan"
      subtitle={
        gemProfile
          ? `Model: ${String(gemProfile.model_ref || gemProfile.gem_id || "")} · ${String(gemProfile.scenario || "")}`
          : `${payloads.length} pathway payload${payloads.length === 1 ? "" : "s"}`
      }
    >
      {selectedPathway && (
        <div className="mb-5 rounded-lg border border-primary/30 bg-primary/5 px-4 py-3">
          <p className="text-[11px] font-medium uppercase tracking-wide text-muted">Selected pathway</p>
          <p className="mt-1 text-[15px] font-semibold text-foreground">{selectedPathway.name}</p>
          <p className="mt-0.5 font-mono text-[11px] text-muted">{selectedPathway.id}</p>
        </div>
      )}

      {body}

      {priorRuns && priorRuns.length > 0 && resolvePathwayName && (
        <PriorPathwayRuns entries={priorRuns} resolvePathwayName={resolvePathwayName} />
      )}
    </ArtifactPanel>
  );
}
