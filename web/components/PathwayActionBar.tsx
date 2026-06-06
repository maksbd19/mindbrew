"use client";

import { actionBar, btnPrimary, btnSecondary, cn } from "@/lib/ui";

export default function PathwayActionBar({
  selectedPathwayName,
  committedPathwayName,
  selectionChanged,
  isActiveStep,
  proceedLabel,
  proceedSummary,
  canProceed,
  busy,
  clarificationsPending,
  statusHint,
  onProceed,
  onRestart,
  onReject,
}: {
  selectedPathwayName: string | null;
  committedPathwayName: string | null;
  selectionChanged: boolean;
  isActiveStep: boolean;
  proceedLabel: string;
  proceedSummary?: string | null;
  canProceed: boolean;
  busy?: boolean;
  clarificationsPending?: boolean;
  statusHint?: string | null;
  onProceed: () => void;
  onRestart?: () => void;
  onReject?: () => void;
}) {
  return (
    <div className="rounded-lg border border-border-subtle bg-surface-raised/50 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <span className="text-[12px] font-medium uppercase tracking-wide text-muted">Selected pathway</span>
          {selectedPathwayName ? (
            <p className="mt-1 text-[14px] font-medium text-foreground">{selectedPathwayName}</p>
          ) : (
            <p className="mt-1 text-[13px] text-muted">Select a pathway below to continue.</p>
          )}
          {committedPathwayName && !isActiveStep && (
            <p className="mb-0 mt-1.5 text-[12px] text-muted">
              Last applied: <span className="text-foreground">{committedPathwayName}</span>
            </p>
          )}
          {proceedSummary && (
            <p className="mb-0 mt-2 text-[13px] leading-relaxed text-muted-light">{proceedSummary}</p>
          )}
        </div>
        <div className={cn(actionBar, "shrink-0")}>
          <button
            type="button"
            className={btnPrimary}
            disabled={busy || !canProceed}
            onClick={onProceed}
          >
            {busy ? "Working…" : proceedLabel}
          </button>
          {onRestart && (
            <button type="button" className={btnSecondary} disabled={busy} onClick={onRestart}>
              Restart step
            </button>
          )}
          {onReject && (
            <button
              type="button"
              className={cn(btnSecondary, "text-danger hover:border-red-900/50 hover:bg-red-950/20")}
              disabled={busy}
              onClick={onReject}
            >
              Reject
            </button>
          )}
        </div>
      </div>

      {!isActiveStep && (
        <p className="mb-0 mt-3 text-[13px] text-muted">
          {selectionChanged
            ? "This differs from the last applied pathway. Proceed to re-run downstream analysis."
            : "Proceed to re-run downstream analysis for the selected pathway."}
        </p>
      )}

      {clarificationsPending && (
        <p className="mb-0 mt-3 rounded-md border border-amber-900/50 bg-amber-950/20 px-3 py-2.5 text-[13px] text-amber-200">
          The agent needs clarification. Revise the brief to address open questions, or proceed anyway if you
          have enough context.
        </p>
      )}

      {statusHint && (
        <p className="mb-0 mt-3 text-[13px] text-muted">{statusHint}</p>
      )}
    </div>
  );
}
