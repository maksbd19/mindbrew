"use client";

import { useState } from "react";
import { actionBar, btnPrimary, btnSecondary, cn, inputBase } from "@/lib/ui";

export default function ReviseDialog({
  onProceed,
  onRevise,
  onRestart,
  showPathwaySelect,
  pathwayIds,
  proceedDisabled,
  proceedDisabledReason,
  busy,
}: {
  onProceed: (opts: { notes?: string; selectedPathwayIds?: string[]; primaryPathwayId?: string }) => void;
  onRevise: (notes: string) => void;
  onRestart?: () => void;
  showPathwaySelect?: boolean;
  pathwayIds?: { id: string; name: string }[];
  proceedDisabled?: boolean;
  proceedDisabledReason?: string | null;
  busy?: boolean;
}) {
  const [notes, setNotes] = useState("");
  const [selected, setSelected] = useState<string[]>(pathwayIds?.[0] ? [pathwayIds[0].id] : []);

  return (
    <div className="z-10 shrink-0 border-t border-border bg-surface p-4 shadow-[0_-8px_24px_rgba(0,0,0,0.35)]">
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
      <textarea
        placeholder="Revision notes (optional)"
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        rows={2}
        className={cn(inputBase, "mb-2")}
      />
      <div className={actionBar}>
        <button
          type="button"
          className={btnPrimary}
          disabled={busy || proceedDisabled}
          onClick={() =>
            onProceed({
              notes: notes || undefined,
              selectedPathwayIds: selected.length ? selected : undefined,
              primaryPathwayId: selected[0],
            })
          }
        >
          {busy ? "Working…" : "Proceed"}
        </button>
        <button type="button" className={btnSecondary} disabled={busy} onClick={() => onRevise(notes)}>
          Revise
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
