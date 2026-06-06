"use client";

import { useEffect, useRef } from "react";
import type { StreamEvent } from "@/lib/api";
import { card, cn, eventColorClass } from "@/lib/ui";

const TYPE_LABELS: Record<string, string> = {
  log: "log",
  node_start: "start",
  node_end: "done",
  step_start: "step",
  step_complete: "step",
  decision_accepted: "decision",
  awaiting_user: "awaiting",
  interrupted: "stop",
  error: "error",
};

function eventText(e: StreamEvent): string {
  if (e.content) return e.content;
  if (e.summary) return e.summary;
  if (e.message) return e.message;
  if (e.step_id) return e.step_id;
  if (e.node_id) return e.node_id;
  return "";
}

export function activePhaseFromEvents(events: StreamEvent[]): string | null {
  for (let i = events.length - 1; i >= 0; i--) {
    const e = events[i];
    if (e.type === "log") return e.content || null;
    if (e.type === "node_start") return e.content || e.node_id || null;
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

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [events.length]);

  return (
    <div
      className={cn(
        card,
        "mb-4 overflow-auto font-mono text-xs",
        running ? "h-80" : "h-52"
      )}
    >
      <div className="mb-2 flex items-center gap-2">
        <strong>Agent log</strong>
        {running && <span className="text-xs text-accent">● live</span>}
        <span className="ml-auto text-[0.7rem] text-gray-500">
          {events.length} event{events.length === 1 ? "" : "s"}
        </span>
      </div>
      {events.length === 0 && !running && (
        <p className="m-0 text-muted">Waiting for agent events…</p>
      )}
      {events.length === 0 && running && (
        <p className="m-0 text-muted">Agent started — waiting for first log line…</p>
      )}
      {events.map((e, i) => {
        const label = TYPE_LABELS[e.type] || e.type;
        const text = eventText(e);
        return (
          <div
            key={i}
            className={cn("mt-1 break-words leading-snug", eventColorClass(e.type, e.level))}
          >
            <span className="text-gray-500">[{label}]</span> {text}
          </div>
        );
      })}
      <div ref={bottom} />
    </div>
  );
}
