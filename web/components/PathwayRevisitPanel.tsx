"use client";

import { actionBar, btnSecondary, card, cn } from "@/lib/ui";

export default function PathwayRevisitPanel({
  selectedPathwayName,
  committedPathwayName,
  selectionChanged,
  busy,
  onRestart,
}: {
  selectedPathwayName: string | null;
  committedPathwayName: string | null;
  selectionChanged: boolean;
  busy?: boolean;
  onRestart: () => void;
}) {
  return (
    <div className={cn(card, "p-4")}>
      <span className="text-[12px] font-medium uppercase tracking-wide text-muted">Pathway selection</span>
      {selectedPathwayName ? (
        <p className="mt-1.5 text-[14px] font-medium text-foreground">{selectedPathwayName}</p>
      ) : (
        <p className="mt-1.5 text-[13px] text-muted">Select a pathway above to continue.</p>
      )}

      {committedPathwayName && (
        <p className="mb-0 mt-2 text-[13px] text-muted">
          Last applied: <span className="text-foreground">{committedPathwayName}</span>
        </p>
      )}

      {selectionChanged && (
        <p className="mb-0 mt-2 text-[13px] text-amber-300">
          This differs from the pathway used in later steps. Restart to re-run downstream analysis.
        </p>
      )}

      <div className={cn(actionBar, "mt-4")}>
        <button
          type="button"
          className={btnSecondary}
          disabled={busy || !selectedPathwayName}
          onClick={onRestart}
        >
          {busy ? "Restarting…" : "Restart step with selection"}
        </button>
      </div>
    </div>
  );
}
