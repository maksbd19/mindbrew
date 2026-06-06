"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import type { StreamEvent } from "@/lib/api";
import { btnSecondary, card, cn, eventColorClass } from "@/lib/ui";

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

function LogContent({
  events,
  running,
  staleAge,
  showStaleBanner,
  className,
}: {
  events: StreamEvent[];
  running: boolean;
  staleAge: number | null;
  showStaleBanner: boolean;
  className?: string;
}) {
  const bottom = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [events.length]);

  return (
    <div className={cn("overflow-y-auto px-4 py-3 font-mono text-[12px] leading-relaxed sm:px-6", className)}>
      {showStaleBanner && (
        <div className="mb-3 flex items-center gap-2 rounded-md border border-blue-900/40 bg-blue-950/30 px-3 py-2 text-[13px] text-muted-light">
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
            className={cn("mt-0.5 break-words", eventColorClass(e.type, e.level))}
          >
            {ts && <span className="mr-1.5 text-muted/60">[{ts}]</span>}
            <span className="text-muted/70">[{label}]</span> {text}
          </div>
        );
      })}
      <div ref={bottom} />
    </div>
  );
}

export default function StreamLog({
  events,
  running = false,
  column = false,
}: {
  events: StreamEvent[];
  running?: boolean;
  /** Render as a side-panel column (fills available height). */
  column?: boolean;
}) {
  const [, tick] = useState(0);
  const [fullscreen, setFullscreen] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  useEffect(() => {
    if (!running) return;
    const id = window.setInterval(() => tick((n) => n + 1), 1000);
    return () => window.clearInterval(id);
  }, [running]);

  useEffect(() => {
    if (!fullscreen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        setFullscreen(false);
      }
    };
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKey, true);
    return () => {
      document.body.style.overflow = prevOverflow;
      window.removeEventListener("keydown", onKey, true);
    };
  }, [fullscreen]);

  const staleAge = useMemo(() => (running ? lastEventAgeSec(events) : null), [events, running, tick]);
  const showStaleBanner = running && staleAge != null && staleAge > 20;

  const enterFullscreen = useCallback(() => setFullscreen(true), []);
  const exitFullscreen = useCallback(() => setFullscreen(false), []);

  const header = (isFullscreen: boolean) => (
    <div className="flex shrink-0 items-center gap-3 border-b border-border-subtle px-4 py-2.5">
      <div className="flex min-w-0 items-center gap-2">
        <span className="text-[13px] font-semibold text-foreground">Agent log</span>
        {running && (
          <span className="inline-flex items-center gap-1.5 text-[11px] font-medium text-accent">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-accent" />
            live
          </span>
        )}
      </div>
      <span className="ml-auto text-[11px] text-muted">
        {events.length} event{events.length === 1 ? "" : "s"}
      </span>
      <button
        type="button"
        onClick={isFullscreen ? exitFullscreen : enterFullscreen}
        className={cn(btnSecondary, "relative z-10 h-7 shrink-0 px-2.5 text-[11px]")}
        aria-label={isFullscreen ? "Exit fullscreen" : "Enter fullscreen"}
      >
        {isFullscreen ? "Exit fullscreen" : "Fullscreen"}
      </button>
    </div>
  );

  const panel = (
    <section
      className={cn(
        card,
        "flex flex-col overflow-hidden",
        column ? "h-full min-h-[280px] rounded-lg" : "w-full rounded-none border-x-0 border-b-0"
      )}
    >
      {header(false)}
      <LogContent
        events={events}
        running={running}
        staleAge={staleAge}
        showStaleBanner={showStaleBanner}
        className={cn(
          column ? "min-h-0 flex-1" : running ? "h-72 sm:h-80" : "h-48 sm:h-56"
        )}
      />
    </section>
  );

  const fullscreenOverlay =
    mounted &&
    createPortal(
      <div className="fixed inset-0 z-[200] flex flex-col bg-page">
        {header(true)}
        <LogContent
          events={events}
          running={running}
          staleAge={staleAge}
          showStaleBanner={showStaleBanner}
          className="min-h-0 flex-1"
        />
      </div>,
      document.body
    );

  return (
    <>
      {panel}
      {fullscreen && fullscreenOverlay}
    </>
  );
}
