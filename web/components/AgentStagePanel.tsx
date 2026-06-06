"use client";

import { useEffect, useMemo, useState } from "react";
import type { StreamEvent } from "@/lib/api";
import { card, cn } from "@/lib/ui";

type CompletedNode = {
  nodeId: string;
  label: string;
  stage?: string;
  durationMs?: number;
  status?: string;
};

export type AgentStageState = {
  activeNode: { nodeId: string; label: string; stage?: string; startedAt?: string } | null;
  subActivity: string | null;
  completedNodes: CompletedNode[];
  mode: "working" | "review" | "idle";
};

export function deriveAgentStageState(events: StreamEvent[]): AgentStageState {
  const openNodes = new Map<string, { label: string; stage?: string; startedAt?: string }>();
  const completedNodes: CompletedNode[] = [];
  let subActivity: string | null = null;
  const openTools = new Map<string, string>();

  for (const event of events) {
    if (event.type === "node_start" && event.node_id) {
      openNodes.set(event.node_id, {
        label: event.content || event.node_id,
        stage: event.stage,
        startedAt: event.ts,
      });
    }

    if (event.type === "node_end" && event.node_id) {
      openNodes.delete(event.node_id);
      completedNodes.push({
        nodeId: event.node_id,
        label: event.content || event.node_id,
        stage: event.stage,
        durationMs: event.duration_ms,
        status: event.status,
      });
    }

    if (event.type === "tool_start" && event.tool_id) {
      openTools.set(event.tool_id, event.content || event.tool_id);
      subActivity = event.content || event.tool_id;
    }

    if (event.type === "tool_end" && event.tool_id) {
      openTools.delete(event.tool_id);
    }

    if (event.type === "llm_call") {
      const tokens =
        event.input_tokens != null || event.output_tokens != null
          ? ` · ${event.input_tokens ?? "?"}→${event.output_tokens ?? "?"} tok`
          : "";
      subActivity = `${event.role || "LLM"} · ${event.model || "model"} (${event.duration_ms ?? "?"}ms${tokens})`;
    }
  }

  if (openTools.size > 0) {
    subActivity = [...openTools.values()].at(-1) ?? subActivity;
  }

  const activeEntry = [...openNodes.entries()].at(-1);
  const activeNode = activeEntry
    ? {
        nodeId: activeEntry[0],
        label: activeEntry[1].label,
        stage: activeEntry[1].stage,
        startedAt: activeEntry[1].startedAt,
      }
    : null;

  let mode: AgentStageState["mode"] = "idle";
  if (activeNode) {
    mode = activeNode.stage === "review" ? "review" : "working";
  }

  return { activeNode, subActivity, completedNodes, mode };
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function elapsedSince(ts?: string): string | null {
  if (!ts) return null;
  const start = new Date(ts).getTime();
  if (Number.isNaN(start)) return null;
  const sec = Math.max(0, Math.floor((Date.now() - start) / 1000));
  if (sec < 60) return `${sec}s`;
  const min = Math.floor(sec / 60);
  return `${min}m ${sec % 60}s`;
}

function modeBadge(mode: AgentStageState["mode"]) {
  if (mode === "working") {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full bg-chip-running-bg px-2 py-0.5 text-[11px] font-medium text-chip-running-text">
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-accent" />
        Working
      </span>
    );
  }
  if (mode === "review") {
    return (
      <span className="rounded-full bg-chip-awaiting-bg px-2 py-0.5 text-[11px] font-medium text-chip-awaiting-text">
        Awaiting review
      </span>
    );
  }
  return null;
}

export default function AgentStagePanel({
  events,
  running = false,
}: {
  events: StreamEvent[];
  running?: boolean;
}) {
  const [, tick] = useState(0);
  const state = useMemo(() => deriveAgentStageState(events), [events]);

  useEffect(() => {
    if (!running || !state.activeNode?.startedAt) return;
    const id = window.setInterval(() => tick((n) => n + 1), 1000);
    return () => window.clearInterval(id);
  }, [running, state.activeNode?.startedAt]);

  const elapsed = state.activeNode ? elapsedSince(state.activeNode.startedAt) : null;
  const recentCompleted = state.completedNodes.slice(-4).reverse();

  if (!running && !state.activeNode && recentCompleted.length === 0) {
    return null;
  }

  return (
    <section className={cn(card, "px-4 py-3 text-[13px] sm:px-5")}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-semibold text-foreground">Agent stage</span>
            {modeBadge(state.mode)}
            {elapsed && running && (
              <span className="text-[11px] text-muted">elapsed {elapsed}</span>
            )}
          </div>
          {state.activeNode ? (
            <p className="mb-0 mt-1.5 truncate text-foreground">{state.activeNode.label}</p>
          ) : (
            <p className="mb-0 mt-1.5 text-muted">No active node</p>
          )}
          {state.subActivity && (
            <p className="mb-0 mt-1 truncate font-mono text-[11px] text-muted-light">
              {state.subActivity}
            </p>
          )}
        </div>
      </div>

      {recentCompleted.length > 0 && (
        <ul className="mb-0 mt-3 space-y-1 border-t border-border-subtle pt-3 text-[11px] text-muted-light">
          {recentCompleted.map((node) => (
            <li key={`${node.nodeId}-${node.durationMs ?? "x"}`} className="flex items-center gap-2">
              <span
                className={cn(
                  "shrink-0",
                  node.status === "error" ? "text-danger" : "text-success"
                )}
              >
                {node.status === "error" ? "✕" : "✓"}
              </span>
              <span className="min-w-0 truncate">{node.label}</span>
              {node.durationMs != null && (
                <span className="ml-auto shrink-0 tabular-nums text-muted/70">
                  {formatDuration(node.durationMs)}
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
