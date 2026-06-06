"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { deleteSession } from "@/lib/api";
import { btnSecondary, cn } from "@/lib/ui";

export default function DeleteSessionButton({
  sessionId,
  sessionTitle,
}: {
  sessionId: string;
  sessionTitle: string;
}) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function handleDelete() {
    const label = sessionTitle.trim() || "this session";
    if (!window.confirm(`Delete "${label}"? This cannot be undone.`)) return;

    setBusy(true);
    setError("");
    try {
      await deleteSession(sessionId);
      router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <button
        type="button"
        className={cn(btnSecondary, "text-danger hover:border-red-900/50 hover:bg-red-950/20")}
        disabled={busy}
        onClick={() => void handleDelete()}
      >
        {busy ? "Deleting…" : "Delete"}
      </button>
      {error && <span className="text-[12px] text-danger">{error}</span>}
    </div>
  );
}
