"use client";

import { useState } from "react";
import { btnSecondary, cn, inputBase } from "@/lib/ui";

export default function ReviseForm({
  onRevise,
  busy,
}: {
  onRevise: (notes: string) => void;
  busy?: boolean;
}) {
  const [notes, setNotes] = useState("");

  function submit() {
    onRevise(notes);
    setNotes("");
  }

  return (
    <div className="mt-4 border-t border-border-subtle pt-4">
      <label htmlFor="revision-notes" className="mb-2 block text-[13px] font-medium text-foreground">
        Add revision notes
      </label>
      <textarea
        id="revision-notes"
        placeholder="Describe what to change — this becomes part of the conversation"
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        rows={3}
        disabled={busy}
        className={cn(inputBase, "mb-2 text-[13px]")}
      />
      <button
        type="button"
        className={btnSecondary}
        disabled={busy || !notes.trim()}
        onClick={submit}
      >
        {busy ? "Working…" : "Revise"}
      </button>
    </div>
  );
}
