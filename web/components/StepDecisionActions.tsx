"use client";

import { actionBar, btnPrimary, btnSecondary, card, cn } from "@/lib/ui";

function agentStatusTone(verdict: unknown): "success" | "warning" | "danger" | "neutral" {
  const v = String(verdict || "").toUpperCase();
  if (v === "PROCEED") return "success";
  if (v === "CLARIFY") return "warning";
  if (v === "REJECT") return "danger";
  return "neutral";
}

export default function StepDecisionActions({
  onProceed,
  onReject,
  onRestart,
  showPathwaySelect,
  selectedPathway,
  agentStatus,
  proceedDisabled,
  proceedDisabledReason,
  busy,
}: {
  onProceed: (opts: { selectedPathwayIds?: string[]; primaryPathwayId?: string }) => void;
  onReject?: () => void;
  onRestart?: () => void;
  showPathwaySelect?: boolean;
  selectedPathway?: { id: string; name: string } | null;
  agentStatus?: string | null;
  proceedDisabled?: boolean;
  proceedDisabledReason?: string | null;
  busy?: boolean;
}) {
  const tone = agentStatus != null ? agentStatusTone(agentStatus) : null;
  const pathwaySelectionRequired = Boolean(showPathwaySelect);
  const hasPathwaySelection = Boolean(selectedPathway);
  const proceedBlockedByPathways = pathwaySelectionRequired && !hasPathwaySelection;

  return (
    <div className={cn(card, "p-4")}>
      {agentStatus != null && tone && (
        <div
          className={cn(
            "mb-3 rounded-md border px-3 py-2.5",
            tone === "success" && "border-emerald-900/50 bg-emerald-950/20",
            tone === "warning" && "border-amber-900/50 bg-amber-950/20",
            tone === "danger" && "border-red-900/50 bg-red-950/20",
            tone === "neutral" && "border-border-subtle bg-surface-raised"
          )}
        >
          <span className="text-[12px] font-medium uppercase tracking-wide text-muted">Agent Status</span>
          <p
            className={cn(
              "mt-1 text-[14px] font-semibold",
              tone === "success" && "text-emerald-300",
              tone === "warning" && "text-amber-300",
              tone === "danger" && "text-red-300",
              tone === "neutral" && "text-foreground"
            )}
          >
            {String(agentStatus)}
          </p>
        </div>
      )}
      {pathwaySelectionRequired && (
        <div className="mb-3">
          <span className="text-[12px] font-medium uppercase tracking-wide text-muted">Selected pathway</span>
          {hasPathwaySelection ? (
            <p className="mt-1.5 text-[14px] font-medium text-foreground">{selectedPathway!.name}</p>
          ) : (
            <p className="mt-1.5 text-[13px] text-muted">
              Select a pathway above to proceed.
            </p>
          )}
        </div>
      )}
      {proceedDisabledReason && (
        <p className="mb-3 text-sm text-danger">{proceedDisabledReason}</p>
      )}
      <div className={actionBar}>
        <button
          type="button"
          className={btnPrimary}
          disabled={busy || proceedDisabled || proceedBlockedByPathways}
          onClick={() =>
            onProceed({
              selectedPathwayIds: selectedPathway ? [selectedPathway.id] : undefined,
              primaryPathwayId: selectedPathway?.id,
            })
          }
        >
          {busy ? "Working…" : "Proceed"}
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
  );
}
