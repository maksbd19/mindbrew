import type { Citation, FbaResult } from "@/lib/bioLinks";
import ArtifactPanel, { ArtifactSection, MetricChip } from "./ArtifactPanel";
import CitationBadge from "./CitationBadge";
import ConfidencePanel from "./ConfidencePanel";

function verdictTone(verdict: string): "success" | "warning" | "danger" | "neutral" {
  const v = verdict.toLowerCase();
  if (v === "pass" || v === "strong") return "success";
  if (v === "marginal" || v === "partial") return "warning";
  if (v === "fail") return "danger";
  return "neutral";
}

export default function FbaResultsView({ results }: { results: FbaResult[] }) {
  return (
    <ArtifactPanel
      title="FBA validation results"
      subtitle={`${results.length} pathway${results.length === 1 ? "" : "s"} scored`}
    >
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
                  label="Yield"
                  value={`${r.yield_corrected_mol_per_mol_substrate.toFixed(2)} mol/mol`}
                />
              )}
              <MetricChip label="Calibration" value={r.calibration_level} />
            </div>

            {r.verdict_rationale && (
              <p className="mt-3 text-[14px] leading-relaxed text-muted-light">{r.verdict_rationale}</p>
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
    </ArtifactPanel>
  );
}
