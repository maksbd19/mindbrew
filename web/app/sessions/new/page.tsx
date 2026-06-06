"use client";

import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { createSession } from "@/lib/api";
import { actionBar, btnPrimary, btnSecondary, card, cn, container, inputBase, pageSubtitle, pageTitle } from "@/lib/ui";

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
      <header className="mb-6">
        <Link href="/" className="text-[13px] text-muted transition-colors hover:text-accent">
          ← Back to sessions
        </Link>
        <h1 className={cn(pageTitle, "mt-3")}>New session</h1>
        <p className={pageSubtitle}>Paste an R&D brief to start a new session.</p>
      </header>

      <div className={cn(card, "p-5")}>
        <label htmlFor="brief" className="mb-2 block text-[13px] font-medium text-muted-light">
          R&D brief
        </label>
        <textarea
          id="brief"
          value={brief}
          onChange={(e) => setBrief(e.target.value)}
          rows={14}
          placeholder="Describe your research objective, constraints, and target organism or pathway…"
          className={cn(inputBase, "resize-y bg-surface-raised")}
        />

        {error && <p className="mt-3 text-[13px] text-danger">{error}</p>}

        <div className={cn(actionBar, "mt-5")}>
          <button type="button" className={btnPrimary} onClick={submit} disabled={loading || !brief.trim()}>
            {loading ? "Starting…" : "Start session"}
          </button>
          <Link href="/" className={btnSecondary}>
            Cancel
          </Link>
        </div>
      </div>
    </div>
  );
}
