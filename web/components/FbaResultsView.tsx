import type { Citation, FbaCalculationStep, FbaResult } from "@/lib/bioLinks";
import type { PathwayChoice, PathwayRunHistoryEntry } from "@/lib/pathwaySelection";
import ArtifactPanel, { ArtifactSection, MetricChip } from "./ArtifactPanel";
import CitationBadge from "./CitationBadge";
import ConfidencePanel from "./ConfidencePanel";
import PriorPathwayRuns from "./PriorPathwayRuns";

function CalculationStepsPanel({ steps }: { steps: FbaCalculationStep[] }) {
  return (
    <ArtifactSection title="Calculation steps">
      <ol className="space-y-3">
        {steps.map((s) => (
          <li key={s.step} className="rounded-md border border-border-subtle bg-surface px-3 py-2.5">
            <div className="flex gap-3">
              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-surface-raised font-mono text-[11px] font-semibold text-accent">
                {s.step}
              </span>
              <div className="min-w-0">
                <p className="text-[13px] font-medium text-foreground">{s.title}</p>
                {s.detail ? (
                  <p className="mt-1 text-[12px] leading-relaxed text-muted-light">{s.detail}</p>
                ) : null}
              </div>
            </div>
          </li>
        ))}
      </ol>
    </ArtifactSection>
  );
}

function verdictTone(verdict: string): "success" | "warning" | "danger" | "neutral" {
  const v = verdict.toLowerCase();
  if (v === "pass" || v === "strong") return "success";
  if (v === "marginal" || v === "partial") return "warning";
  if (v === "fail") return "danger";
  return "neutral";
}

export default function FbaResultsView({
  results,
  embedded = false,
  selectedPathway,
  priorRuns,
  resolvePathwayName,
}: {
  results: FbaResult[];
  embedded?: boolean;
  selectedPathway?: PathwayChoice | null;
  priorRuns?: PathwayRunHistoryEntry[];
  resolvePathwayName?: (pathwayId: string | undefined) => string;
}) {
  const priorRunsWithResults =
    priorRuns?.filter((entry) => {
      const results = entry.cp4_fba_results?.fba_results;
      return Array.isArray(results) && results.length > 0;
    }) ?? [];

  const body = (
    <div className="space-y-4">
      {results.map((r) => (
          <div key={r.pathway_id} className="rounded-lg border border-border-subtle bg-surface-raised/50 p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <h3 className="font-mono text-[14px] font-semibold text-accent">{r.pathway_id}</h3>
              {r.rank != null && (
                <span className="rounded-full bg-surface-raised px-2.5 py-0.5 text-[11px] font-medium text-muted">
                  Rank #{r.rank}
                </span>
              )}
            </div>

            <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
              <MetricChip label="Verdict" value={r.verdict} tone={verdictTone(r.verdict)} />
              <MetricChip label="Status" value={r.status} />
              {r.yield_corrected_mol_per_mol_substrate != null && (
                <MetricChip
                  label="Yield (corrected)"
                  value={`${r.yield_corrected_mol_per_mol_substrate.toFixed(2)} mol/mol`}
                />
              )}
              {r.yield_mol_per_mol_substrate != null &&
                r.yield_mol_per_mol_substrate !== r.yield_corrected_mol_per_mol_substrate && (
                  <MetricChip
                    label="Yield (raw)"
                    value={`${r.yield_mol_per_mol_substrate.toFixed(2)} mol/mol`}
                  />
                )}
              {r.predicted_product_flux != null && (
                <MetricChip
                  label="Product flux"
                  value={`${r.predicted_product_flux.toFixed(3)} mmol/gDW/h`}
                />
              )}
              {r.growth_rate != null && (
                <MetricChip label="Growth" value={`${r.growth_rate.toFixed(3)} h⁻¹`} />
              )}
              <MetricChip label="Calibration" value={r.calibration_level ?? ""} />
              {r.product_confidence_level && (
                <MetricChip label="Product cal." value={r.product_confidence_level} />
              )}
            </div>

            {r.carbon_audit_sole_source === false && (
              <p className="mt-2 text-[13px] text-amber-200">
                Carbon audit: feedstock is not the sole carbon source — yield vs feedstock is untrustworthy.
              </p>
            )}

            {r.verdict_rationale && (
              <p className="mt-3 text-[14px] leading-relaxed text-muted-light">{r.verdict_rationale}</p>
            )}

            {(r.calculation_steps ?? []).length > 0 && (
              <div className="mt-4">
                <CalculationStepsPanel steps={r.calculation_steps ?? []} />
              </div>
            )}

            {r.solver_message && r.solver_message !== "OK" && (
              <p className="mt-3 rounded-md border border-amber-900/40 bg-amber-950/20 px-3 py-2.5 text-[13px] text-amber-200">
                {r.solver_message}
              </p>
            )}

            {r.calibration_rationale && (
              <p className="mt-2 text-[13px] text-muted">{r.calibration_rationale}</p>
            )}

            {(r.calibration_warnings ?? []).length > 0 && (
              <ul className="mt-3 space-y-1 rounded-md border border-amber-900/40 bg-amber-950/20 px-3 py-2.5 text-[13px] text-amber-200">
                {(r.calibration_warnings ?? []).map((w) => (
                  <li key={w}>{w}</li>
                ))}
              </ul>
            )}

            {(r.failure_reasons ?? []).length > 0 && (
              <ul className="mt-3 space-y-1 rounded-md border border-red-900/40 bg-red-950/20 px-3 py-2.5 text-[13px] text-red-200">
                {(r.failure_reasons ?? []).map((f) => (
                  <li key={f}>{f}</li>
                ))}
              </ul>
            )}

            {(r.bottlenecks ?? []).length > 0 && (
              <ArtifactSection title="Bottlenecks">
                <ul className="space-y-2">
                  {(r.bottlenecks ?? []).map((b) => (
                    <li
                      key={b.reaction}
                      className="rounded-md border border-border-subtle bg-surface px-3 py-2 text-[13px]"
                    >
                      <span className="font-mono text-foreground">{b.reaction}</span>
                      <span className="text-muted">
                        {" "}
                        · flux {b.flux.toFixed(2)}
                        {b.flux_span != null ? ` · FVA span ${b.flux_span.toFixed(2)}` : ""}
                        {b.at_bound ? " (at bound)" : ""}
                      </span>
                      {b.explanation && <p className="mt-1 text-muted-light">{b.explanation}</p>}
                    </li>
                  ))}
                </ul>
              </ArtifactSection>
            )}

            <div className="mt-3">
              <ConfidencePanel label={r.verdict} rationale={r.verdict_rationale} methodologyType="fba" />
            </div>

            {(r.literature_refs ?? []).length > 0 && (
              <ArtifactSection title="Calibration literature">
                <div className="space-y-1">
                  {(r.literature_refs ?? []).map((c: Citation, i: number) => (
                    <CitationBadge key={`${r.pathway_id}-lit-${i}`} citation={c} />
                  ))}
                </div>
              </ArtifactSection>
            )}
          </div>
        ))}
      </div>
  );

  if (embedded) {
    return (
      <div>
        <p className="mb-3 text-[13px] font-semibold text-foreground">FBA validation results</p>
        {body}
      </div>
    );
  }

  return (
    <ArtifactPanel
      title="FBA validation results"
      subtitle={`${results.length} pathway${results.length === 1 ? "" : "s"} scored`}
    >
      {selectedPathway && (
        <div className="mb-5 rounded-lg border border-primary/30 bg-primary/5 px-4 py-3">
          <p className="text-[11px] font-medium uppercase tracking-wide text-muted">Selected pathway</p>
          <p className="mt-1 text-[15px] font-semibold text-foreground">{selectedPathway.name}</p>
          <p className="mt-0.5 font-mono text-[11px] text-muted">{selectedPathway.id}</p>
        </div>
      )}

      {body}

      {priorRunsWithResults.length > 0 && resolvePathwayName && (
        <PriorPathwayRuns
          entries={priorRunsWithResults}
          resolvePathwayName={resolvePathwayName}
          emphasis="results"
        />
      )}
    </ArtifactPanel>
  );
}
