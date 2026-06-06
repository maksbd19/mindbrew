"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createSession } from "@/lib/api";
import { actionBar, btnPrimary, cn, container, inputBase } from "@/lib/ui";

export default function NewSessionPage() {
  const router = useRouter();
  const [brief, setBrief] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function submit() {
    setLoading(true);
    setError("");
    try {
      const session = await createSession(brief);
      router.push(`/sessions/${session.id}`);
    } catch (e) {
      setError(String(e));
      setLoading(false);
    }
  }

  return (
    <div className={container}>
      <h1 className="text-2xl font-semibold">New session</h1>
      <p className="text-muted">Paste an R&D brief to start a new session.</p>

      <textarea
        value={brief}
        onChange={(e) => setBrief(e.target.value)}
        rows={12}
        className={cn(inputBase, "mt-4 rounded-lg bg-surface p-4")}
      />

      {error && <p className="mt-2 text-danger">{error}</p>}

      <div className={cn(actionBar, "mt-4")}>
        <button type="button" className={btnPrimary} onClick={submit} disabled={loading || !brief.trim()}>
          {loading ? "Starting…" : "Start session"}
        </button>
      </div>
    </div>
  );
}
