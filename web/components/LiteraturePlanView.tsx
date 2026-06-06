import type { LiteraturePlan } from "@/lib/bioLinks";
import { dataTable, dataTableCell, dataTableHead } from "@/lib/ui";
import ArtifactPanel, { ArtifactSection } from "./ArtifactPanel";
import CitationBadge from "./CitationBadge";
import EnzymeChip from "./EnzymeChip";

export default function LiteraturePlanView({
  plan,
  organism,
}: {
  plan: LiteraturePlan;
  organism?: string[];
}) {
  const org = organism?.[0] ?? null;

  return (
    <ArtifactPanel title="Literature pathway plan" subtitle={plan.pathway_name}>
      {(plan.reaction_map ?? []).length > 0 && (
        <ArtifactSection title="Reaction map">
          <ol className="space-y-2 pl-0">
            {(plan.reaction_map ?? []).map((s) => (
              <li
                key={s.step_number}
                className="rounded-md border border-border-subtle bg-surface-raised/50 px-3 py-2.5 text-[13px]"
              >
                <span className="text-foreground">{s.description}</span>
                <div className="mt-1.5 flex flex-wrap gap-1">
                  {(s.gene_names ?? []).map((g) => (
                    <EnzymeChip key={g} name={g} ec={s.enzyme_ec} enzymeName={s.enzyme_name} organism={org} />
                  ))}
                </div>
              </li>
            ))}
          </ol>
        </ArtifactSection>
      )}

      {(plan.gene_suggestions ?? []).length > 0 && (
        <ArtifactSection title="Gene suggestions">
          <div className="-mx-5 overflow-x-auto">
            <table className={dataTable}>
              <thead>
                <tr className="bg-surface-raised/50">
                  <th className={dataTableHead}>Gene</th>
                  <th className={dataTableHead}>Action</th>
                  <th className={dataTableHead}>Rationale</th>
                  <th className={dataTableHead}>Citation</th>
                </tr>
              </thead>
              <tbody>
                {(plan.gene_suggestions ?? []).map((g) => (
                  <tr key={g.gene} className="border-b border-border-subtle hover:bg-surface-hover/50">
                    <td className={dataTableCell}>
                      <EnzymeChip name={g.gene} organism={org} />
                    </td>
                    <td className={dataTableCell}>{g.action}</td>
                    <td className={`${dataTableCell} text-[13px] text-muted-light`}>{g.rationale}</td>
                    <td className={dataTableCell}>
                      {g.citation ? (
                        <CitationBadge citation={g.citation} />
                      ) : (
                        <span className="text-[12px] text-danger">No citation</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </ArtifactSection>
      )}

      {(plan.citations ?? []).length > 0 && (
        <ArtifactSection title="Pathway references">
          <div className="space-y-1">
            {(plan.citations ?? []).map((c, i) => (
              <CitationBadge key={`plan-cit-${i}`} citation={c} />
            ))}
          </div>
        </ArtifactSection>
      )}

      {(["known_risks", "gaps", "next_steps"] as const).map((key) => {
        const items = plan[key] as string[] | undefined;
        if (!items?.length) return null;
        const label = key.replace(/_/g, " ");
        return (
          <ArtifactSection key={key} title={label.charAt(0).toUpperCase() + label.slice(1)}>
            <ul className="space-y-1.5 text-[13px] text-muted-light">
              {items.map((item) => (
                <li key={item} className="flex gap-2">
                  <span className="text-muted">•</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </ArtifactSection>
        );
      })}
    </ArtifactPanel>
  );
}
