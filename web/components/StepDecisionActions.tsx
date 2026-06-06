"use client";

import { useState } from "react";
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
  onRestart,
  showPathwaySelect,
  pathwayIds,
  agentStatus,
  proceedDisabled,
  proceedDisabledReason,
  busy,
}: {
  onProceed: (opts: { selectedPathwayIds?: string[]; primaryPathwayId?: string }) => void;
  onRestart?: () => void;
  showPathwaySelect?: boolean;
  pathwayIds?: { id: string; name: string }[];
  agentStatus?: string | null;
  proceedDisabled?: boolean;
  proceedDisabledReason?: string | null;
  busy?: boolean;
}) {
  const [selected, setSelected] = useState<string[]>(pathwayIds?.[0] ? [pathwayIds[0].id] : []);
  const tone = agentStatus != null ? agentStatusTone(agentStatus) : null;

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
      {showPathwaySelect && pathwayIds && (
        <div className="mb-3">
          <strong className="text-sm">Select pathway(s)</strong>
          {pathwayIds.map((p) => (
            <label key={p.id} className="mt-1 block text-sm">
              <input
                type="checkbox"
                className="mr-1.5"
                checked={selected.includes(p.id)}
                onChange={(e) => {
                  if (e.target.checked) setSelected([...selected, p.id]);
                  else setSelected(selected.filter((id) => id !== p.id));
                }}
              />
              {p.name}
            </label>
          ))}
        </div>
      )}
      {proceedDisabledReason && (
        <p className="mb-3 text-sm text-danger">{proceedDisabledReason}</p>
      )}
      <div className={actionBar}>
        <button
          type="button"
          className={btnPrimary}
          disabled={busy || proceedDisabled}
          onClick={() =>
            onProceed({
              selectedPathwayIds: selected.length ? selected : undefined,
              primaryPathwayId: selected[0],
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
      </div>
    </div>
  );
}
