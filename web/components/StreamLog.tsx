"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { StreamEvent } from "@/lib/api";
import { card, cn, eventColorClass } from "@/lib/ui";

const TYPE_LABELS: Record<string, string> = {
  log: "log",
  heartbeat: "heartbeat",
  node_start: "start",
  node_end: "done",
  step_start: "step",
  step_complete: "step",
  decision_accepted: "decision",
  session_created: "created",
  user_interrupt: "stop",
  interrupted: "stop",
  user_resume: "resume",
  session_retry: "retry",
  step_restart: "restart",
  step_restart_requested: "restart",
  action_rejected: "rejected",
  awaiting_user: "awaiting",
  error: "error",
};

function formatTimestamp(ts?: string): string | null {
  if (!ts) return null;
  const date = new Date(ts);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

function eventText(e: StreamEvent): string {
  if (e.content) return e.content;
  if (e.summary) return e.summary;
  if (e.message) return e.message;
  if (e.notes) return `notes: ${e.notes}`;
  if (e.step_id) return e.step_id;
  if (e.node_id) return e.node_id;
  return "";
}

export function activePhaseFromEvents(events: StreamEvent[]): string | null {
  for (let i = events.length - 1; i >= 0; i--) {
    const e = events[i];
    if (e.type === "heartbeat") return e.content || null;
    if (e.type === "log") return e.content || null;
    if (e.type === "node_start") return e.content || e.node_id || null;
  }
  return null;
}

function lastEventAgeSec(events: StreamEvent[]): number | null {
  for (let i = events.length - 1; i >= 0; i--) {
    const ts = events[i].ts;
    if (!ts) continue;
    const age = (Date.now() - new Date(ts).getTime()) / 1000;
    if (!Number.isNaN(age)) return age;
  }
  return null;
}

export default function StreamLog({
  events,
  running = false,
}: {
  events: StreamEvent[];
  running?: boolean;
}) {
  const bottom = useRef<HTMLDivElement>(null);
  const [, tick] = useState(0);

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [events.length]);

  useEffect(() => {
    if (!running) return;
    const id = window.setInterval(() => tick((n) => n + 1), 1000);
    return () => window.clearInterval(id);
  }, [running]);

  const staleAge = useMemo(() => (running ? lastEventAgeSec(events) : null), [events, running, tick]);
  const showStaleBanner = running && staleAge != null && staleAge > 20;

  return (
    <div
      className={cn(
        card,
        "mb-4 overflow-auto font-mono text-xs",
        running ? "h-96" : "h-52"
      )}
    >
      <div className="mb-2 flex items-center gap-2">
        <strong>Agent log</strong>
        {running && <span className="text-xs text-accent">● live</span>}
        <span className="ml-auto text-[0.7rem] text-gray-500">
          {events.length} event{events.length === 1 ? "" : "s"}
        </span>
      </div>
      {showStaleBanner && (
        <div className="mb-2 flex items-center gap-2 rounded border border-blue-900/40 bg-blue-950/30 px-2 py-1.5 text-muted-light">
          <span className="animate-pulse text-accent">●</span>
          Still working… last update {Math.round(staleAge!)}s ago
        </div>
      )}
      {events.length === 0 && !running && (
        <p className="m-0 text-muted">Waiting for agent events…</p>
      )}
      {events.length === 0 && running && (
        <p className="m-0 text-muted">Agent started — waiting for first log line…</p>
      )}
      {events.map((e, i) => {
        const label = TYPE_LABELS[e.type] || e.type;
        const text = eventText(e);
        const ts = formatTimestamp(e.ts);
        return (
          <div
            key={e.seq ?? i}
            className={cn("mt-1 break-words leading-snug", eventColorClass(e.type, e.level))}
          >
            {ts && <span className="mr-1.5 text-gray-600">[{ts}]</span>}
            <span className="text-gray-500">[{label}]</span> {text}
          </div>
        );
      })}
      <div ref={bottom} />
    </div>
  );
}
