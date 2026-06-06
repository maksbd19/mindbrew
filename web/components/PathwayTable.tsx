"use client";

import { useState, type ReactNode } from "react";
import type { PathwayCandidate } from "@/lib/bioLinks";
import { cn } from "@/lib/ui";
import ArtifactPanel, { ArtifactSection, MetricChip } from "./ArtifactPanel";
import CitationBadge from "./CitationBadge";
import ConfidencePanel from "./ConfidencePanel";
import EnzymeChip from "./EnzymeChip";

function confidenceTone(label: string): "success" | "warning" | "danger" | "neutral" {
  switch (label.toLowerCase()) {
    case "strong":
    case "pass":
      return "success";
    case "partial":
    case "marginal":
      return "warning";
    case "weak":
    case "fail":
      return "danger";
    default:
      return "neutral";
  }
}

function PathwayCard({
  candidate: c,
  organism,
  selectable,
  isSelected,
  isExpanded,
  onSelect,
  onToggleExpanded,
}: {
  candidate: PathwayCandidate;
  organism?: string | null;
  selectable: boolean;
  isSelected: boolean;
  isExpanded: boolean;
  onSelect: () => void;
  onToggleExpanded: () => void;
}) {
  const steps = c.reaction_steps ?? [];
  const enzymes = c.enzymes ?? [];
  const citations = c.citations ?? [];

  return (
    <article
      className={cn(
        "overflow-hidden rounded-lg border transition-colors",
        selectable && isSelected
          ? "border-primary/50 bg-primary/5 ring-1 ring-primary/25"
          : "border-border-subtle bg-surface-raised/40 hover:border-border"
      )}
    >
      <div className="p-4">
        <div className="min-w-0">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0 flex-1">
              <h3 className="text-[15px] font-semibold leading-snug text-foreground">{c.name}</h3>
              <p className="mt-0.5 font-mono text-[11px] text-muted">{c.id}</p>
            </div>
            <div className="flex shrink-0 flex-wrap items-stretch gap-2">
              <MetricChip label="Confidence" value={c.confidence} tone={confidenceTone(c.confidence)} />
              {selectable && (
                <button
                  type="button"
                  onClick={onSelect}
                  aria-pressed={isSelected}
                  className={cn(
                    "inline-flex items-center justify-center rounded-md border px-3 py-2 text-[12px] font-medium transition-colors",
                    isSelected
                      ? "border-primary/50 bg-primary/15 text-accent"
                      : "border-border bg-surface-raised text-muted hover:border-primary/40 hover:text-foreground"
                  )}
                >
                  {isSelected ? "Selected" : "Select"}
                </button>
              )}
            </div>
          </div>

          {c.description && (
            <p
              className={cn(
                "mt-3 text-[14px] leading-relaxed text-muted-light",
                !isExpanded && "line-clamp-3"
              )}
            >
              {c.description}
            </p>
          )}

          <div className="mt-4 flex flex-wrap items-center gap-2">
            {c.reported_titer && (
              <span className="inline-flex items-center rounded-full border border-border-subtle bg-surface px-2.5 py-1 text-[12px] text-muted-light">
                <span className="font-medium text-muted">Titer</span>
                <span className="mx-1.5 text-border">·</span>
                <span className="text-foreground">{c.reported_titer}</span>
              </span>
            )}
            {steps.length > 0 && (
              <span className="inline-flex items-center rounded-full border border-border-subtle bg-surface px-2.5 py-1 text-[12px] text-muted">
                {steps.length} reaction step{steps.length === 1 ? "" : "s"}
              </span>
            )}
            {citations.length > 0 && (
              <span className="inline-flex items-center rounded-full border border-border-subtle bg-surface px-2.5 py-1 text-[12px] text-muted">
                {citations.length} reference{citations.length === 1 ? "" : "s"}
              </span>
            )}
          </div>

          {enzymes.length > 0 && (
            <div className="mt-4">
              <p className="mb-2 text-[11px] font-medium uppercase tracking-wide text-muted">Key enzymes</p>
              <div className="flex flex-wrap gap-1.5">
                {enzymes.map((e) => {
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
                      organism={organism}
                    />
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>

      {isExpanded && (
        <div className="space-y-5 border-t border-border-subtle bg-surface/40 px-4 py-4">
          {steps.length > 0 && (
            <ArtifactSection title="Reaction steps">
              <ol className="space-y-2">
                {steps.map((s) => (
                  <li
                    key={s.step_number}
                    className="rounded-md border border-border-subtle bg-surface px-3 py-3"
                  >
                    <div className="flex gap-3">
                      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-surface-raised text-[11px] font-semibold text-muted">
                        {s.step_number}
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="text-[13px] leading-relaxed text-foreground">{s.description}</p>
                        <div className="mt-2 flex flex-wrap gap-1">
                          {(s.gene_names ?? []).map((g) => (
                            <EnzymeChip
                              key={g}
                              name={g}
                              ec={s.enzyme_ec}
                              enzymeName={s.enzyme_name}
                              organism={organism}
                            />
                          ))}
                          {s.heterologous && (
                            <span className="inline-flex items-center rounded-full bg-amber-950/40 px-2 py-0.5 text-[11px] text-amber-300">
                              heterologous
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </li>
                ))}
              </ol>
            </ArtifactSection>
          )}

          {(c.confidence_rationale || (c.confidence_factors ?? []).length > 0) && (
            <ConfidencePanel
              label={c.confidence}
              rationale={c.confidence_rationale}
              factors={c.confidence_factors}
            />
          )}

          {citations.length > 0 && (
            <ArtifactSection title="References">
              <div className="space-y-1.5">
                {citations.map((cit, i) => (
                  <CitationBadge key={`${c.id}-cit-${i}`} citation={cit} />
                ))}
              </div>
            </ArtifactSection>
          )}
        </div>
      )}

      <button
        type="button"
        onClick={onToggleExpanded}
        aria-expanded={isExpanded}
        aria-label={isExpanded ? "Collapse pathway details" : "Expand pathway details"}
        className={cn(
          "flex w-full items-center justify-center gap-1.5 border-t border-border-subtle px-4 py-2.5 text-[12px] font-medium transition-colors",
          isExpanded
            ? "bg-surface/60 text-accent hover:bg-surface-hover/50"
            : "bg-surface/30 text-muted hover:bg-surface-hover/50 hover:text-accent"
        )}
      >
        {isExpanded ? "Collapse" : "Expand"}
        <span aria-hidden className="text-[10px]">
          {isExpanded ? "▴" : "▾"}
        </span>
      </button>
    </article>
  );
}

export default function PathwayTable({
  candidates,
  organism,
  selectable = false,
  selectedId = null,
  onSelectionChange,
  actionBar,
}: {
  candidates: PathwayCandidate[];
  organism?: string[];
  selectable?: boolean;
  selectedId?: string | null;
  onSelectionChange?: (id: string | null) => void;
  actionBar?: ReactNode;
}) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const org = organism?.[0] ?? null;

  const toggleExpanded = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectPathway = (id: string) => {
    if (!onSelectionChange) return;
    onSelectionChange(selectedId === id ? null : id);
  };

  return (
    <ArtifactPanel
      title="Pathway candidates"
      subtitle={`${candidates.length} candidate${candidates.length === 1 ? "" : "s"} identified`}
    >
      {actionBar && <div className="mb-4">{actionBar}</div>}
      <div className="space-y-3">
        {candidates.map((c) => (
          <PathwayCard
            key={c.id}
            candidate={c}
            organism={org}
            selectable={selectable}
            isSelected={selectedId === c.id}
            isExpanded={expanded.has(c.id)}
            onSelect={() => selectPathway(c.id)}
            onToggleExpanded={() => toggleExpanded(c.id)}
          />
        ))}
      </div>
    </ArtifactPanel>
  );
}
