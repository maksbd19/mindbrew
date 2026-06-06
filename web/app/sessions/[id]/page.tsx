"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import type { Session, StreamEvent } from "@/lib/api";
import {
  getSession,
  getSessionEvents,
  interruptSession,
  resumeSession,
  restartSessionStep,
  retrySession,
  streamUrl,
  submitDecision,
} from "@/lib/api";
import StepSidebar from "@/components/StepSidebar";
import StreamLog, { activePhaseFromEvents } from "@/components/StreamLog";
import ArtifactView from "@/components/ArtifactView";
import ReviseDialog from "@/components/ReviseDialog";
import {
  actionBar,
  btnPrimary,
  btnSecondary,
  card,
  cn,
  container,
  link,
  statusChipClass,
} from "@/lib/ui";

function lastError(events: StreamEvent[]): string | null {
  for (let i = events.length - 1; i >= 0; i--) {
    if (events[i].type === "error" && events[i].message) return events[i].message!;
  }
  return null;
}

function mergeEvents(prev: StreamEvent[], incoming: StreamEvent[]): StreamEvent[] {
  if (incoming.length === 0) return prev;
  const seen = new Set(prev.map((e) => e.seq).filter((s): s is number => s != null));
  const merged = [...prev];
  for (const evt of incoming) {
    if (evt.seq != null) {
      if (seen.has(evt.seq)) continue;
      seen.add(evt.seq);
    }
    merged.push(evt);
  }
  return merged;
}

function proceedBlockReason(
  stepId: string,
  artifact: Record<string, unknown> | null
): string | null {
  if (stepId !== "cp1_spec" || !artifact?.brief) return null;
  const brief = artifact.brief as { gatekeeper_verdict?: string; clarifying_questions?: string[] };
  if (brief.gatekeeper_verdict === "REJECT") {
    return "Proceed is blocked: the gatekeeper rejected this brief as out of scope. Revise the brief or start a new session.";
  }
  if (brief.gatekeeper_verdict === "CLARIFY") {
    const qs = brief.clarifying_questions?.filter(Boolean) ?? [];
    return qs.length
      ? `Proceed is blocked until these are resolved: ${qs.join("; ")}`
      : "Proceed is blocked: the gatekeeper needs more detail. Revise the brief first.";
  }
  return null;
}

export default function SessionDetailPage() {
  const params = useParams();
  const sessionId = params.id as string;

  const [session, setSession] = useState<Session | null>(null);
  const [viewStep, setViewStep] = useState("cp1_spec");
  const [events, setEvents] = useState<StreamEvent[]>([]);
  const [actionError, setActionError] = useState("");
  const [deciding, setDeciding] = useState(false);
  const [restarting, setRestarting] = useState(false);
  const [pendingAction, setPendingAction] = useState<"proceed" | "revise" | "restart" | null>(null);
  const lastSeqRef = useRef(0);

  const applySession = useCallback((s: Session) => {
    setSession(s);
    setViewStep(s.current_step);
  }, []);

  const refresh = useCallback(async () => {
    const s = await getSession(sessionId);
    applySession(s);
    return s;
  }, [sessionId, applySession]);

  const syncEvents = useCallback(async () => {
    const rows = await getSessionEvents(sessionId, lastSeqRef.current);
    if (rows.length === 0) return;
    const lastSeq = rows[rows.length - 1].seq;
    if (lastSeq != null) lastSeqRef.current = lastSeq;
    setEvents((prev) => mergeEvents(prev, rows));
  }, [sessionId]);

  const handleStreamEvent = useCallback(
    (evt: StreamEvent) => {
      if (evt.seq != null && evt.seq > lastSeqRef.current) {
        lastSeqRef.current = evt.seq;
      }
      setEvents((prev) => mergeEvents(prev, [evt]));
      if (evt.type === "awaiting_user") {
        if (evt.step_id) setViewStep(evt.step_id);
        refresh();
      }
      if (evt.type === "interrupted" || evt.type === "user_interrupt" || evt.type === "error") {
        refresh();
      }
      if (evt.type === "step_complete" || evt.type === "done") {
        refresh();
      }
    },
    [refresh]
  );

  useEffect(() => {
    lastSeqRef.current = 0;
    setEvents([]);
    refresh();
    syncEvents().catch(() => {});
  }, [sessionId, refresh, syncEvents]);

  useEffect(() => {
    let es: EventSource | null = null;
    let closed = false;

    function connect() {
      if (closed) return;
      es = new EventSource(streamUrl(sessionId, lastSeqRef.current));
      es.onmessage = (msg) => {
        try {
          handleStreamEvent(JSON.parse(msg.data));
        } catch {
          /* ignore parse errors */
        }
      };
      es.onerror = () => {
        es?.close();
        if (!closed) window.setTimeout(connect, 2000);
      };
    }

    connect();
    return () => {
      closed = true;
      es?.close();
    };
  }, [sessionId, handleStreamEvent]);

  useEffect(() => {
    if (!session || (!deciding && !restarting && session.status !== "running" && !session.agent_active)) return;
    const id = window.setInterval(async () => {
      try {
        await refresh();
        await syncEvents();
      } catch {
        /* ignore transient poll errors */
      }
    }, 1500);
    return () => window.clearInterval(id);
  }, [session?.status, session?.agent_active, deciding, restarting, refresh, syncEvents]);

  const completedSteps = new Set(
    (session?.steps || [])
      .filter((s) => s.status === "completed" || s.status === "awaiting_user")
      .map((s) => s.step_id)
  );

  const stepRecord = session?.steps.find((s) => s.step_id === viewStep);
  const artifact = (stepRecord?.artifact as Record<string, unknown> | null) ?? null;

  const agentActive = Boolean(session?.agent_active) || session?.status === "running";
  const showStop = agentActive;
  const showResume = session?.status === "interrupted";
  const showRestartStep =
    Boolean(session?.current_step) &&
    (session?.status === "awaiting_user" ||
      session?.status === "failed" ||
      session?.status === "interrupted");
  const streamError = lastError(events);
  const activePhase = activePhaseFromEvents(events);

  async function handleInterrupt() {
    setActionError("");
    try {
      await interruptSession(sessionId);
      await refresh();
      await syncEvents();
    } catch (e) {
      setActionError(String(e));
    }
  }

  async function handleResume() {
    setActionError("");
    try {
      await resumeSession(sessionId);
      await refresh();
    } catch (e) {
      setActionError(String(e));
    }
  }

  async function handleRestartStep() {
    const stepId = session?.current_step || viewStep;
    setActionError("");
    setRestarting(true);
    setPendingAction("restart");
    try {
      const started = await restartSessionStep(sessionId, stepId);
      applySession(started);

      for (let i = 0; i < 180; i++) {
        await syncEvents();
        const s = await refresh();
        if (
          s.status === "awaiting_user" ||
          s.status === "completed" ||
          s.status === "failed" ||
          s.status === "interrupted"
        ) {
          break;
        }
        if (s.status === "running" && !s.agent_active) {
          setActionError("Agent stopped before finishing this step. Check the stream log below or use Restart step.");
          break;
        }
        await new Promise((resolve) => window.setTimeout(resolve, 1500));
      }
    } catch (e) {
      setActionError(e instanceof Error ? e.message : String(e));
      await refresh();
    } finally {
      setRestarting(false);
      setPendingAction(null);
    }
  }

  async function handleRetry() {
    setActionError("");
    try {
      await retrySession(sessionId);
      lastSeqRef.current = 0;
      setEvents([]);
      await refresh();
    } catch (e) {
      setActionError(String(e));
    }
  }

  async function sendDecision(action: "proceed" | "revise", opts: Record<string, unknown> = {}) {
    const stepId = session?.current_step || viewStep;
    setActionError("");
    setDeciding(true);
    setPendingAction(action);

    const body = {
      action,
      notes: (opts.notes as string | undefined) ?? undefined,
      selected_pathway_ids:
        (opts.selectedPathwayIds as string[] | undefined) ??
        (opts.selected_pathway_ids as string[] | undefined),
      primary_pathway_id:
        (opts.primaryPathwayId as string | undefined) ??
        (opts.primary_pathway_id as string | undefined),
    };

    try {
      const started = await submitDecision(sessionId, stepId, body);
      applySession(started);

      for (let i = 0; i < 180; i++) {
        await syncEvents();
        const s = await refresh();
        if (s.status === "awaiting_user" || s.status === "completed" || s.status === "failed" || s.status === "interrupted") {
          break;
        }
        if (s.status === "running" && !s.agent_active) {
          setActionError("Agent stopped before finishing this step. Check the stream log below or use Retry.");
          break;
        }
        await new Promise((resolve) => window.setTimeout(resolve, 1500));
      }
    } catch (e) {
      setActionError(e instanceof Error ? e.message : String(e));
      await refresh();
    } finally {
      setDeciding(false);
      setPendingAction(null);
    }
  }

  const pathwayIds =
    artifact && "pathway_candidates" in artifact
      ? ((artifact.pathway_candidates as { id: string; name: string }[]) || []).map((p) => ({
          id: p.id,
          name: p.name,
        }))
      : [];

  const proceedBlocked = proceedBlockReason(viewStep, artifact);
  const showDecisionPanel =
    session?.status === "awaiting_user" &&
    session.current_step === viewStep &&
    !deciding &&
    !restarting;
  const showHeaderRestart = showRestartStep && !showStop && !showDecisionPanel;
  const workingMessage =
    pendingAction === "revise"
      ? "Applying your revision — re-running the agent on this step…"
      : pendingAction === "restart"
        ? "Restarting this step — prior step results are kept…"
      : pendingAction === "proceed"
        ? "Proceeding to the next step — this may take a minute…"
        : "Agent is working on the current step…";

  return (
    <div className={container}>
      <div className="mb-4">
        <Link href="/" className={link}>
          ← Sessions
        </Link>
        <p className="mt-2 whitespace-pre-wrap text-[0.95rem] leading-relaxed text-muted-light">
          {session?.raw_brief || "Loading…"}
        </p>
        <div className={cn(actionBar, "mt-3")}>
          {session && <span className={statusChipClass(session.status)}>{session.status}</span>}
          {showStop && (
            <button type="button" className={btnSecondary} onClick={handleInterrupt}>
              Stop agent
            </button>
          )}
          {showResume && (
            <button type="button" className={btnPrimary} onClick={handleResume}>
              Resume
            </button>
          )}
          {showHeaderRestart && (
            <button type="button" className={btnSecondary} onClick={handleRestartStep} disabled={restarting}>
              {restarting ? "Restarting…" : "Restart step"}
            </button>
          )}
          {session?.status === "failed" && (
            <button type="button" className={btnPrimary} onClick={handleRetry}>
              Retry
            </button>
          )}
        </div>
        {(streamError || actionError) && (
          <div className={cn(card, "mt-3 border-red-900/60 text-sm text-danger")}>
            {streamError && <p className="m-0">{streamError}</p>}
            {actionError && <p className={streamError ? "mb-0 mt-2" : "m-0"}>{actionError}</p>}
            {session?.status === "failed" && streamError?.includes("Connection") && (
              <p className="mb-0 mt-2 text-muted">
                Tip: set <code className="rounded border border-border bg-page px-1 py-0.5 text-xs">BREWMIND_OFFLINE=true</code> in{" "}
                <code className="rounded border border-border bg-page px-1 py-0.5 text-xs">.env</code> for local dev without
                Nebius, or verify your API key and network.
              </p>
            )}
          </div>
        )}
      </div>

      <div className="flex items-stretch gap-6">
        <StepSidebar
          currentStep={viewStep}
          completedSteps={completedSteps}
          onSelect={setViewStep}
          validationMode={session?.validation_mode || null}
        />
        <div className="flex min-h-[calc(100vh-10rem)] min-w-0 flex-1 flex-col">
          <div className="flex-1 space-y-4 overflow-y-auto pb-4">
            {(showStop || deciding || restarting) && session && (
              <div className="flex flex-wrap items-center gap-2 text-sm text-muted-light">
                <span className={statusChipClass(session.status)}>{session.status}</span>
                {activePhase && (
                  <>
                    <span className="text-gray-600">·</span>
                    <span className="truncate">{activePhase}</span>
                  </>
                )}
              </div>
            )}
            <StreamLog events={events} running={showStop || deciding || restarting} />
            {(deciding || restarting || (session?.status === "running" && session.agent_active)) && (
              <div className={cn(card, "border-blue-900/50 text-sm text-muted")}>
                <p className="m-0 text-accent">{workingMessage}</p>
                <p className="mb-0 mt-2">
                  Status: <strong className="text-foreground">{session?.status}</strong>
                  {session?.current_step ? ` · checkpoint ${session.current_step}` : ""}
                </p>
                {activePhase && (
                  <p className="mb-0 mt-1.5 text-muted-light">Latest: {activePhase}</p>
                )}
              </div>
            )}
            <ArtifactView stepId={viewStep} artifact={artifact} />
          </div>
          {showDecisionPanel && (
            <ReviseDialog
              showPathwaySelect={viewStep === "cp2_pathways"}
              pathwayIds={pathwayIds}
              proceedDisabled={Boolean(proceedBlocked)}
              proceedDisabledReason={proceedBlocked}
              busy={deciding || restarting}
              onRestart={handleRestartStep}
              onProceed={(opts) => sendDecision("proceed", opts)}
              onRevise={(notes) => sendDecision("revise", { notes })}
            />
          )}
        </div>
      </div>
    </div>
  );
}
