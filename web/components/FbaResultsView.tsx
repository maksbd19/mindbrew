import type { Citation, FbaResult } from "@/lib/bioLinks";
import { card, cardTitle } from "@/lib/ui";
import CitationBadge from "./CitationBadge";
import ConfidencePanel from "./ConfidencePanel";

export default function FbaResultsView({ results }: { results: FbaResult[] }) {
  return (
    <div className={card}>
      <h3 className={cardTitle}>FBA validation results</h3>
      {results.map((r) => (
        <div key={r.pathway_id} className="border-b border-border py-3 text-sm last:border-b-0">
          <div className="mb-1.5 flex flex-wrap gap-4">
            <strong>{r.pathway_id}</strong>
            {r.rank != null && <span className="text-muted">Rank #{r.rank}</span>}
            <span className="capitalize">Verdict: {r.verdict}</span>
            <span>Status: {r.status}</span>
            {r.yield_corrected_mol_per_mol_substrate != null && (
              <span>Yield: {r.yield_corrected_mol_per_mol_substrate.toFixed(2)} mol/mol</span>
            )}
            <span>Calibration: {r.calibration_level}</span>
          </div>

          {r.verdict_rationale && <p className="my-1 text-muted-light">{r.verdict_rationale}</p>}

          {r.calibration_rationale && (
            <p className="my-1 text-xs text-muted">{r.calibration_rationale}</p>
          )}

          {(r.calibration_warnings ?? []).length > 0 && (
            <ul className="my-1 list-disc pl-5 text-xs text-unverified">
              {(r.calibration_warnings ?? []).map((w) => (
                <li key={w}>{w}</li>
              ))}
            </ul>
          )}

          {(r.failure_reasons ?? []).length > 0 && (
            <ul className="my-1 list-disc pl-5 text-xs text-danger">
              {(r.failure_reasons ?? []).map((f) => (
                <li key={f}>{f}</li>
              ))}
            </ul>
          )}

          {(r.bottlenecks ?? []).length > 0 && (
            <div className="mt-1.5">
              <strong className="text-xs">Bottlenecks</strong>
              <ul className="list-disc pl-5 text-xs">
                {(r.bottlenecks ?? []).map((b) => (
                  <li key={b.reaction}>
                    {b.reaction} (flux {b.flux.toFixed(2)}
                    {b.at_bound ? ", at bound" : ""})
                    {b.explanation && <span className="text-muted"> — {b.explanation}</span>}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <ConfidencePanel label={r.verdict} rationale={r.verdict_rationale} methodologyType="fba" />

          {(r.literature_refs ?? []).length > 0 && (
            <div className="mt-2">
              <strong className="text-xs">Calibration literature</strong>
              {(r.literature_refs ?? []).map((c: Citation, i: number) => (
                <CitationBadge key={`${r.pathway_id}-lit-${i}`} citation={c} />
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
