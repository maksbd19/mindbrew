"use client";

import { useState } from "react";
import type { FbaResult } from "@/lib/bioLinks";
import type { PathwayRunHistoryEntry } from "@/lib/pathwaySelection";
import { cn } from "@/lib/ui";
import FbaPlanView from "./FbaPlanView";
import FbaResultsView from "./FbaResultsView";

function HistoryEntry({
  entry,
  pathwayName,
  defaultOpen = false,
  emphasis = "plan",
}: {
  entry: PathwayRunHistoryEntry;
  pathwayName: string;
  defaultOpen?: boolean;
  emphasis?: "plan" | "results";
}) {
  const [open, setOpen] = useState(defaultOpen);
  const cp3 = entry.cp3_fba_plan ?? {};
  const payloads = (cp3.score_payloads as Parameters<typeof FbaPlanView>[0]["payloads"]) ?? [];
  const cp4 = entry.cp4_fba_results ?? {};
  const fbaResults = (cp4.fba_results as FbaResult[] | undefined) ?? [];

  return (
    <div className="overflow-hidden rounded-lg border border-border-subtle bg-surface-raised/30">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left transition-colors hover:bg-surface-hover/40"
      >
        <div className="min-w-0">
          <p className="text-[14px] font-medium text-foreground">{pathwayName}</p>
          <p className="mt-0.5 font-mono text-[11px] text-muted">
            {entry.pathway_id}
            {entry.revision_number != null ? ` · revision ${entry.revision_number}` : ""}
          </p>
        </div>
        <span className="shrink-0 text-[12px] text-muted">
          {open ? "Hide ▴" : "Show ▾"}
        </span>
      </button>

      {open && (
        <div className="space-y-4 border-t border-border-subtle px-4 py-4">
          {emphasis === "results" ? (
            <>
              {fbaResults.length > 0 ? (
                <FbaResultsView results={fbaResults} embedded />
              ) : (
                <p className="m-0 text-[13px] text-muted">No FBA results were saved for this run.</p>
              )}
              {payloads.length > 0 && (
                <div>
                  <p className="mb-2 text-[12px] font-medium uppercase tracking-wide text-muted">FBA plan</p>
                  <FbaPlanView
                    payloads={payloads}
                    skipped={cp3.skipped as string[] | undefined}
                    gemProfile={cp3.gem_profile as Record<string, unknown> | null}
                    embedded
                  />
                </div>
              )}
            </>
          ) : (
            <>
              {payloads.length > 0 ? (
                <FbaPlanView
                  payloads={payloads}
                  skipped={cp3.skipped as string[] | undefined}
                  gemProfile={cp3.gem_profile as Record<string, unknown> | null}
                  embedded
                />
              ) : (
                <p className="m-0 text-[13px] text-muted">No FBA plan was saved for this run.</p>
              )}
              {fbaResults.length > 0 && <FbaResultsView results={fbaResults} embedded />}
            </>
          )}
        </div>
      )}
    </div>
  );
}

export default function PriorPathwayRuns({
  entries,
  resolvePathwayName,
  emphasis = "plan",
}: {
  entries: PathwayRunHistoryEntry[];
  resolvePathwayName: (pathwayId: string | undefined) => string;
  emphasis?: "plan" | "results";
}) {
  const [open, setOpen] = useState(false);

  if (entries.length === 0) return null;

  return (
    <div className="mt-6 overflow-hidden rounded-lg border border-border-subtle">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className={cn(
          "flex w-full items-center justify-between gap-3 px-4 py-3 text-left transition-colors",
          "bg-surface-raised/50 hover:bg-surface-hover/40"
        )}
      >
        <div>
          <p className="text-[13px] font-semibold text-foreground">
            {emphasis === "results" ? "Previous FBA results" : "Previous pathway runs"}
          </p>
          <p className="mt-0.5 text-[12px] text-muted">
            {entries.length} earlier run{entries.length === 1 ? "" : "s"} with saved downstream results
          </p>
        </div>
        <span className="shrink-0 text-[12px] text-muted">{open ? "Hide ▴" : "Show ▾"}</span>
      </button>

      {open && (
        <div className="space-y-3 border-t border-border-subtle bg-surface/40 p-4">
          {entries.map((entry, index) => (
            <HistoryEntry
              key={`${entry.pathway_id}-${entry.revision_number}-${index}`}
              entry={entry}
              pathwayName={resolvePathwayName(entry.pathway_id)}
              emphasis={emphasis}
            />
          ))}
        </div>
      )}
    </div>
  );
}
