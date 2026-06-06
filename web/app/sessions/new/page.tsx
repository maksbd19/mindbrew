"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createSession } from "@/lib/api";
import { actionBar, btnPrimary, btnSecondary, cn, container, inputBase } from "@/lib/ui";

const DEMO_TICKETS = [
  {
    id: "ticket1",
    title: "Silicone Replacement",
    brief: `We're looking for a natural replacement for silicones in our premium haircare line. We want something that delivers the same smoothness and frizz control as dimethicone, but is fully natural and sustainably sourced. We'd like to make it from a common plant oil through fermentation. Can you figure out the best way to produce it and what it would take to manufacture?`,
  },
  {
    id: "ticket2",
    title: "Scalp Microbiome",
    brief: `We're developing a scalp-health ingredient that supports a balanced scalp microbiome and helps with dandruff. We want something fermentation-derived that can calm the scalp, strengthen its barrier, and keep the microbiome in check.`,
  },
  {
    id: "ticket3",
    title: "Cuticle Repair",
    brief: `We're creating a repair treatment for damaged hair that rebuilds the cuticle and helps it hold moisture. We'd like a natural, skin-identical lipid ingredient made from a plant oil.`,
  },
];

export default function NewSessionPage() {
  const router = useRouter();
  const [brief, setBrief] = useState(DEMO_TICKETS[0].brief);
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
      <p className="text-muted">Paste an R&D brief or pick a demo ticket.</p>

      <div className={cn(actionBar, "mb-4 mt-2")}>
        {DEMO_TICKETS.map((t) => (
          <button key={t.id} type="button" className={btnSecondary} onClick={() => setBrief(t.brief)}>
            {t.title}
          </button>
        ))}
      </div>

      <textarea
        value={brief}
        onChange={(e) => setBrief(e.target.value)}
        rows={12}
        className={cn(inputBase, "rounded-lg bg-surface p-4")}
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
