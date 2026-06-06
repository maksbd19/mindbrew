"use client";

import { Fragment, useState } from "react";
import type { PathwayCandidate } from "@/lib/bioLinks";
import { card, cardTitle, cn, dataTable, dataTableCell, dataTableHead } from "@/lib/ui";
import CitationBadge from "./CitationBadge";
import ConfidencePanel from "./ConfidencePanel";
import EnzymeChip from "./EnzymeChip";

export default function PathwayTable({
  candidates,
  organism,
}: {
  candidates: PathwayCandidate[];
  organism?: string[];
}) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const org = organism?.[0] ?? null;

  const toggle = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <div className={card}>
      <h3 className={cardTitle}>Pathway candidates</h3>
      <table className={dataTable}>
        <thead>
          <tr>
            <th className={`${dataTableHead} w-10`} />
            <th className={dataTableHead}>Name</th>
            <th className={dataTableHead}>Enzymes</th>
            <th className={dataTableHead}>Confidence</th>
          </tr>
        </thead>
        <tbody>
          {candidates.map((c) => {
            const isOpen = expanded.has(c.id);
            const steps = c.reaction_steps ?? [];
            return (
              <Fragment key={c.id}>
                <tr className="border-b border-border">
                  <td className={dataTableCell}>
                    <button
                      type="button"
                      onClick={() => toggle(c.id)}
                      aria-expanded={isOpen}
                      aria-label={isOpen ? "Collapse pathway details" : "Expand pathway details"}
                      className={cn(
                        "inline-flex h-7 w-7 items-center justify-center rounded-md border text-sm transition-colors",
                        isOpen
                          ? "border-primary bg-[#2a3550] text-accent"
                          : "border-border bg-secondary text-muted-light hover:border-accent hover:bg-[#2a3550] hover:text-accent"
                      )}
                    >
                      {isOpen ? "▾" : "▸"}
                    </button>
                  </td>
                  <td className={dataTableCell}>{c.name}</td>
                  <td className={dataTableCell}>
                    {(c.enzymes ?? []).map((e) => {
                      const step = steps.find(
                        (s) =>
                          s.enzyme_name?.toUpperCase().includes(e.toUpperCase()) ||
                          s.gene_names?.some((g) => g.toUpperCase() === e.toUpperCase())
                      );
                      return (
                        <EnzymeChip
                          key={e}
                          name={e}
                          ec={step?.enzyme_ec}
                          enzymeName={step?.enzyme_name}
                          organism={org}
                        />
                      );
                    })}
                  </td>
                  <td className={`${dataTableCell} capitalize`}>{c.confidence}</td>
                </tr>
                {isOpen && (
                  <tr>
                    <td colSpan={4} className="bg-surface px-3 py-2">
                      {c.description && <p className="mb-2 text-muted-light">{c.description}</p>}
                      {steps.length > 0 && (
                        <div className="mb-2">
                          <strong className="text-xs">Reaction steps</strong>
                          <ol className="my-1 list-decimal pl-5">
                            {steps.map((s) => (
                              <li key={s.step_number} className="mb-1.5">
                                <span>{s.description}</span>
                                {(s.gene_names ?? []).map((g) => (
                                  <EnzymeChip
                                    key={g}
                                    name={g}
                                    ec={s.enzyme_ec}
                                    enzymeName={s.enzyme_name}
                                    organism={org}
                                  />
                                ))}
                                {s.heterologous && (
                                  <span className="ml-1.5 text-xs text-unverified">heterologous</span>
                                )}
                              </li>
                            ))}
                          </ol>
                        </div>
                      )}
                      {c.reported_titer && (
                        <p className="mb-2 text-sm">
                          <strong>Titer:</strong> {c.reported_titer}
                        </p>
                      )}
                      <ConfidencePanel
                        label={c.confidence}
                        rationale={c.confidence_rationale}
                        factors={c.confidence_factors}
                      />
                      {(c.citations ?? []).length > 0 && (
                        <div className="mt-2">
                          <strong className="text-xs">References</strong>
                          {(c.citations ?? []).map((cit, i) => (
                            <CitationBadge key={`${c.id}-cit-${i}`} citation={cit} />
                          ))}
                        </div>
                      )}
                    </td>
                  </tr>
                )}
              </Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
