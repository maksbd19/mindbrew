import type { Citation } from "@/lib/bioLinks";
import { card, cardTitle } from "@/lib/ui";
import CitationBadge from "./CitationBadge";

type ScorePayload = {
  pathway_id: string;
  model_ref?: string;
  scenario?: string;
  candidate_reactions?: Array<{ id: string; name: string; gene_associations?: string[] }>;
  source_citations?: Citation[];
};

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
          {(p.candidate_reactions ?? []).length > 0 && (
            <ul className="my-1.5 list-disc pl-5">
              {(p.candidate_reactions ?? []).map((r) => (
                <li key={r.id}>
                  {r.name || r.id}
                  {r.gene_associations?.length ? (
                    <span className="text-muted"> — genes: {r.gene_associations.join(", ")}</span>
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
