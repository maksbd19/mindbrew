import type { LiteraturePlan } from "@/lib/bioLinks";
import { card, cardSubtitle, cardTitle, dataTable, dataTableCell, dataTableHead } from "@/lib/ui";
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
    <div className={card}>
      <h3 className={cardTitle}>Literature pathway plan: {plan.pathway_name}</h3>

      {(plan.reaction_map ?? []).length > 0 && (
        <section className="mb-4">
          <h4 className={cardSubtitle}>Reaction map</h4>
          <ol className="list-decimal pl-5 text-sm">
            {(plan.reaction_map ?? []).map((s) => (
              <li key={s.step_number} className="mb-1.5">
                {s.description}
                {(s.gene_names ?? []).map((g) => (
                  <EnzymeChip key={g} name={g} ec={s.enzyme_ec} enzymeName={s.enzyme_name} organism={org} />
                ))}
              </li>
            ))}
          </ol>
        </section>
      )}

      {(plan.gene_suggestions ?? []).length > 0 && (
        <section className="mb-4">
          <h4 className={cardSubtitle}>Gene suggestions</h4>
          <table className={dataTable}>
            <thead>
              <tr>
                <th className={dataTableHead}>Gene</th>
                <th className={dataTableHead}>Action</th>
                <th className={dataTableHead}>Rationale</th>
                <th className={dataTableHead}>Citation</th>
              </tr>
            </thead>
            <tbody>
              {(plan.gene_suggestions ?? []).map((g) => (
                <tr key={g.gene} className="border-b border-border">
                  <td className={dataTableCell}>
                    <EnzymeChip name={g.gene} organism={org} />
                  </td>
                  <td className={dataTableCell}>{g.action}</td>
                  <td className={`${dataTableCell} text-muted-light`}>{g.rationale}</td>
                  <td className={dataTableCell}>
                    {g.citation ? (
                      <CitationBadge citation={g.citation} />
                    ) : (
                      <span className="text-xs text-danger">No citation</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {(plan.citations ?? []).length > 0 && (
        <section>
          <h4 className={cardSubtitle}>Pathway references</h4>
          {(plan.citations ?? []).map((c, i) => (
            <CitationBadge key={`plan-cit-${i}`} citation={c} />
          ))}
        </section>
      )}

      {["known_risks", "gaps", "next_steps"].map((key) => {
        const items = plan[key as keyof LiteraturePlan] as string[] | undefined;
        if (!items?.length) return null;
        const label = key.replace(/_/g, " ");
        return (
          <section key={key} className="mt-3">
            <h4 className={`${cardSubtitle} capitalize`}>{label}</h4>
            <ul className="list-disc pl-5 text-sm">
              {items.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </section>
        );
      })}
    </div>
  );
}
