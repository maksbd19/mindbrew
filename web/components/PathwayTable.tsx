"use client";

import { Fragment, useState } from "react";
import type { PathwayCandidate } from "@/lib/bioLinks";
import { cn, confidenceColorClass, dataTable, dataTableCell, dataTableHead } from "@/lib/ui";
import ArtifactPanel from "./ArtifactPanel";
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
    <ArtifactPanel
      title="Pathway candidates"
      subtitle={`${candidates.length} candidate${candidates.length === 1 ? "" : "s"} identified`}
      noPadding
      bodyClassName="overflow-x-auto"
    >
      <table className={dataTable}>
        <thead>
          <tr className="bg-surface-raised/50">
            <th className={cn(dataTableHead, "w-12")} />
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
                <tr className="border-b border-border-subtle transition-colors hover:bg-surface-hover/50">
                  <td className={dataTableCell}>
                    <button
                      type="button"
                      onClick={() => toggle(c.id)}
                      aria-expanded={isOpen}
                      aria-label={isOpen ? "Collapse pathway details" : "Expand pathway details"}
                      className={cn(
                        "inline-flex h-7 w-7 items-center justify-center rounded-md border text-[13px] transition-colors",
                        isOpen
                          ? "border-primary bg-primary/10 text-accent"
                          : "border-border bg-surface-raised text-muted hover:border-primary/40 hover:text-accent"
                      )}
                    >
                      {isOpen ? "▾" : "▸"}
                    </button>
                  </td>
                  <td className={cn(dataTableCell, "font-medium text-foreground")}>{c.name}</td>
                  <td className={dataTableCell}>
                    <div className="flex flex-wrap gap-1">
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
                    </div>
                  </td>
                  <td className={dataTableCell}>
                    <span className={cn("text-[13px] font-medium capitalize", confidenceColorClass(c.confidence))}>
                      {c.confidence}
                    </span>
                  </td>
                </tr>
                {isOpen && (
                  <tr>
                    <td colSpan={4} className="border-b border-border-subtle bg-surface-raised/30 px-5 py-4">
                      {c.description && (
                        <p className="mb-4 text-[14px] leading-relaxed text-muted-light">{c.description}</p>
                      )}
                      {steps.length > 0 && (
                        <div className="mb-4">
                          <h4 className="mb-2 text-[12px] font-semibold uppercase tracking-wide text-muted">
                            Reaction steps
                          </h4>
                          <ol className="space-y-2 pl-0">
                            {steps.map((s) => (
                              <li
                                key={s.step_number}
                                className="rounded-md border border-border-subtle bg-surface px-3 py-2.5 text-[13px]"
                              >
                                <span className="text-foreground">{s.description}</span>
                                <div className="mt-1.5 flex flex-wrap gap-1">
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
                                    <span className="inline-flex items-center rounded-full bg-amber-950/40 px-2 py-0.5 text-[11px] text-amber-300">
                                      heterologous
                                    </span>
                                  )}
                                </div>
                              </li>
                            ))}
                          </ol>
                        </div>
                      )}
                      {c.reported_titer && (
                        <p className="mb-4 text-[13px]">
                          <span className="font-medium text-muted">Reported titer: </span>
                          <span className="text-foreground">{c.reported_titer}</span>
                        </p>
                      )}
                      <ConfidencePanel
                        label={c.confidence}
                        rationale={c.confidence_rationale}
                        factors={c.confidence_factors}
                      />
                      {(c.citations ?? []).length > 0 && (
                        <div className="mt-4">
                          <h4 className="mb-2 text-[12px] font-semibold uppercase tracking-wide text-muted">
                            References
                          </h4>
                          <div className="space-y-1">
                            {(c.citations ?? []).map((cit, i) => (
                              <CitationBadge key={`${c.id}-cit-${i}`} citation={cit} />
                            ))}
                          </div>
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
    </ArtifactPanel>
  );
}
