"use client";

import Link from "next/link";
import type { Session } from "@/lib/api";
import { card, statusChipClass } from "@/lib/ui";

export default function SessionList({ sessions }: { sessions: Session[] }) {
  if (!sessions.length) {
    return (
      <div className={card}>
        <p>No sessions yet. Start a new ticket to begin.</p>
      </div>
    );
  }

  return (
    <div>
      {sessions.map((s) => (
        <Link key={s.id} href={`/sessions/${s.id}`}>
          <div className={`${card} cursor-pointer transition-colors hover:border-accent/40`}>
            <div className="flex justify-between gap-4">
              <strong>{s.title}</strong>
              <span className={statusChipClass(s.status)}>{s.status}</span>
            </div>
            <p className="mt-2 text-sm text-muted">{s.raw_brief.slice(0, 120)}…</p>
          </div>
        </Link>
      ))}
    </div>
  );
}
