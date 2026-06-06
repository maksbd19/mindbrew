"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
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
  suggestSessionTitle,
  updateSessionTitle,
} from "@/lib/api";
import StepNav from "@/components/StepNav";
import AgentStagePanel from "@/components/AgentStagePanel";
import StreamLog, { activePhaseFromEvents } from "@/components/StreamLog";
import SessionContextPanel from "@/components/SessionContextPanel";
import EditableSessionTitle from "@/components/EditableSessionTitle";
import ArtifactView from "@/components/ArtifactView";
import PathwayRevisitPanel from "@/components/PathwayRevisitPanel";
import StepDecisionActions from "@/components/StepDecisionActions";
import {
  actionBar,
  btnPrimary,
  btnSecondary,
  card,
  cn,
  container,
  statusChipClass,
} from "@/lib/ui";
import { formatStatusLabel } from "@/lib/format";
import {
  committedPathwayId,
  pathwayCandidatesFromStep,
  pathwayRunHistory,
  resolvePathwayChoice,
} from "@/lib/pathwaySelection";

/** Recovery markers — errors before these are stale and should not show in the banner. */
const ERROR_RECOVERY_TYPES = new Set([
  "step_restart_requested",
  "step_restart",
  "session_retry",
  "decision_accepted",
  "awaiting_user",
  "step_complete",
  "interrupted",
  "user_resume",
]);

function activeStreamError(events: StreamEvent[]): string | null {
  for (let i = events.length - 1; i >= 0; i--) {
    const evt = events[i];
    if (evt.type === "error" && evt.message) return evt.message;
    if (ERROR_RECOVERY_TYPES.has(evt.type)) return null;
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

type BriefGatekeeper = {
  gatekeeper_verdict?: string;
  clarifying_questions?: string[];
};

function clarifyingQuestions(brief: BriefGatekeeper | null | undefined): string[] {
  return brief?.clarifying_questions?.filter(Boolean) ?? [];
}

function clarificationsPending(brief: BriefGatekeeper | null | undefined): boolean {
  if (!brief) return false;
  return clarifyingQuestions(brief).length > 0 || brief.gatekeeper_verdict === "CLARIFY";
}

function effectiveAgentStatus(brief: BriefGatekeeper | null | undefined): string | null {
  if (!brief) return null;
  if (clarifyingQuestions(brief).length > 0) return "CLARIFY";
  return brief.gatekeeper_verdict ?? null;
}

function proceedBlockReason(
  stepId: string,
  artifact: Record<string, unknown> | null
): string | null {
  if (stepId !== "cp1_spec" || !artifact?.brief) return null;
  const brief = artifact.brief as BriefGatekeeper;
  if (brief.gatekeeper_verdict === "REJECT") {
    return "Proceed is blocked: the agent rejected this brief as out of scope. Revise the brief or start a new session.";
  }
  return null;
}

function clarificationConversationPrompt(brief: BriefGatekeeper | null | undefined): string | null {
  if (!clarificationsPending(brief)) return null;
  const questions = clarifyingQuestions(brief);
  if (questions.length > 0) {
    return questions.map((q) => `• ${q}`).join("\n");
  }
  return "The agent needs more detail before continuing.";
}

function confirmProceedDespiteClarifications(questions: string[]): boolean {
  const list = questions.length
    ? `\n\nOpen questions:\n${questions.map((q) => `• ${q}`).join("\n")}`
    : "";
  return window.confirm(
    `The agent flagged clarifications before continuing.${list}\n\nProceed to the next step anyway?`
  );
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
  const [pendingAction, setPendingAction] = useState<"proceed" | "revise" | "reject" | "restart" | null>(null);
  const [titleSuggesting, setTitleSuggesting] = useState(false);
  const [selectedPathwayId, setSelectedPathwayId] = useState<string | null>(null);
  const lastSeqRef = useRef(0);

  const stepRecord = session?.steps.find((s) => s.step_id === viewStep);
  const artifact = (stepRecord?.artifact as Record<string, unknown> | null) ?? null;
  const pathwayCandidates =
    artifact && "pathway_candidates" in artifact
      ? ((artifact.pathway_candidates as { id: string; name: string }[]) || [])
      : [];
  const pathwayCandidateKey = pathwayCandidates.map((p) => p.id).join(",");
  const cp2Step = session?.steps.find((s) => s.step_id === "cp2_pathways");
  const cp2Candidates = useMemo(() => pathwayCandidatesFromStep(cp2Step), [cp2Step]);
  const committedPathwayIdValue = useMemo(
    () => committedPathwayId(cp2Step?.human_decisions),
    [cp2Step?.human_decisions]
  );
  const priorPathwayRuns = useMemo(() => pathwayRunHistory(cp2Step), [cp2Step]);

  const resolvePathwayName = useCallback(
    (pathwayId: string | undefined) =>
      resolvePathwayChoice(cp2Candidates, pathwayId)?.name ?? pathwayId ?? "Unknown pathway",
    [cp2Candidates]
  );

  const applySession = useCallback((s: Session, opts?: { followStep?: boolean }) => {
    setSession(s);
    if (opts?.followStep) {
      setViewStep(s.current_step);
    }
  }, []);

  const refresh = useCallback(
    async (opts?: { followStep?: boolean }) => {
      const s = await getSession(sessionId);
      applySession(s, opts);
      return s;
    },
    [sessionId, applySession]
  );

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
    refresh({ followStep: true });
    syncEvents().catch(() => {});
  }, [sessionId, refresh, syncEvents]);

  useEffect(() => {
    let cancelled = false;
    setTitleSuggesting(true);
    suggestSessionTitle(sessionId)
      .then((s) => {
        if (!cancelled) applySession(s);
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setTitleSuggesting(false);
      });
    return () => {
      cancelled = true;
    };
  }, [sessionId, applySession]);

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

  useEffect(() => {
    if (viewStep !== "cp2_pathways") {
      setSelectedPathwayId(null);
      return;
    }
    setSelectedPathwayId(committedPathwayIdValue);
  }, [viewStep, committedPathwayIdValue, pathwayCandidateKey]);

  const completedSteps = new Set(
    (session?.steps || [])
      .filter((s) => s.status === "completed" || s.status === "awaiting_user")
      .map((s) => s.step_id)
  );

  const agentActive = Boolean(session?.agent_active) || session?.status === "running";
  const showStop = agentActive;
  const showResume = session?.status === "interrupted";
  const showRestartStep =
    Boolean(session?.current_step) &&
    (session?.status === "awaiting_user" ||
      session?.status === "failed" ||
      session?.status === "interrupted");
  const streamError = restarting ? null : activeStreamError(events);
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
      applySession(started, { followStep: true });
      setEvents((prev) =>
        mergeEvents(prev, [{ type: "step_restart_requested", step_id: stepId }])
      );

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
          setActionError("Agent stopped before finishing this step. Check the agent log above or use Restart step.");
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
    setRestarting(true);
    setPendingAction("restart");
    try {
      const started = await retrySession(sessionId);
      applySession(started, { followStep: true });
      lastSeqRef.current = 0;
      setEvents([]);

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
          setActionError("Agent stopped before finishing this step. Check the agent log above or use Retry.");
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

  async function sendDecision(action: "proceed" | "revise" | "reject", opts: Record<string, unknown> = {}) {
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
      applySession(started, { followStep: true });

      for (let i = 0; i < 180; i++) {
        await syncEvents();
        const s = await refresh();
        if (s.status === "awaiting_user" || s.status === "completed" || s.status === "failed" || s.status === "interrupted") {
          break;
        }
        if (s.status === "running" && !s.agent_active) {
          setActionError("Agent stopped before finishing this step. Check the agent log above or use Retry.");
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

  async function handleRestartPathwayStep() {
    setActionError("");
    setRestarting(true);
    setPendingAction("restart");
    try {
      const started = await restartSessionStep(sessionId, "cp2_pathways");
      applySession(started, { followStep: true });
      setEvents((prev) =>
        mergeEvents(prev, [{ type: "step_restart_requested", step_id: "cp2_pathways" }])
      );

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
          setActionError("Agent stopped before finishing this step. Check the agent log above or use Restart step.");
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

  async function handleTitleSave(title: string) {
    setActionError("");
    try {
      const updated = await updateSessionTitle(sessionId, title);
      applySession(updated);
    } catch (e) {
      setActionError(e instanceof Error ? e.message : String(e));
      throw e;
    }
  }

  async function handleTitleRegenerate() {
    setActionError("");
    const updated = await suggestSessionTitle(sessionId, true);
    applySession(updated);
  }

  const briefGatekeeper =
    artifact?.brief && typeof artifact.brief === "object"
      ? (artifact.brief as BriefGatekeeper)
      : null;
  const proceedBlocked = proceedBlockReason(viewStep, artifact);
  const agentStatus = effectiveAgentStatus(briefGatekeeper);
  const pendingClarifications = clarificationsPending(briefGatekeeper);
  const openClarifyingQuestions = clarifyingQuestions(briefGatekeeper);
  const clarificationPrompt = clarificationConversationPrompt(briefGatekeeper);

  function handleProceed(opts: {
    selectedPathwayIds?: string[];
    primaryPathwayId?: string;
  }) {
    if (pendingClarifications && !confirmProceedDespiteClarifications(openClarifyingQuestions)) {
      return;
    }
    void sendDecision("proceed", opts);
  }
  const selectedPathway =
    pathwayCandidates.find((p) => p.id === selectedPathwayId) ??
    resolvePathwayChoice(cp2Candidates, selectedPathwayId);
  const committedPathway = resolvePathwayChoice(cp2Candidates, committedPathwayIdValue);
  const pathwaySelectionEnabled =
    viewStep === "cp2_pathways" &&
    pathwayCandidates.length > 0 &&
    !deciding &&
    !restarting &&
    !showStop;
  const showDecisionPanel =
    session?.status === "awaiting_user" &&
    session.current_step === viewStep &&
    !deciding &&
    !restarting;
  const showPathwayRevisitPanel =
    pathwaySelectionEnabled && !showDecisionPanel && viewStep === "cp2_pathways";
  const pathwaySelectionChanged =
    Boolean(selectedPathwayId) && selectedPathwayId !== committedPathwayIdValue;
  const fbaSelectedPathway = resolvePathwayChoice(cp2Candidates, committedPathwayIdValue);
  const showHeaderRestart = showRestartStep && !showStop && !showDecisionPanel;
  const workingMessage =
    pendingAction === "revise"
      ? "Applying your revision — re-running the agent on this step…"
      : pendingAction === "restart"
        ? "Restarting this step — prior step results are kept…"
      : pendingAction === "proceed"
        ? "Proceeding to the next step — this may take a minute…"
        : pendingAction === "reject"
          ? "Rejecting this session…"
          : "Agent is working on the current step…";

  return (
    <div className="flex min-h-[calc(100dvh-3.5rem)] w-full flex-col overflow-x-hidden">
      <div className={cn(container, "flex min-h-0 w-full flex-1 flex-col py-5")}>
        <div className="shrink-0">
          <Link href="/" className="text-[13px] text-muted transition-colors hover:text-accent">
            ← Back to sessions
          </Link>
          <div className="mt-3 flex flex-wrap items-start justify-between gap-3">
            <EditableSessionTitle
              title={session?.title || ""}
              suggesting={titleSuggesting}
              onSave={handleTitleSave}
              onRegenerate={handleTitleRegenerate}
            />
            <div className={actionBar}>
              {session && (
                <span className={statusChipClass(session.status)}>{formatStatusLabel(session.status)}</span>
              )}
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
          </div>
          {(streamError || actionError) && (
            <div className={cn(card, "mt-3 border-red-900/60 p-4 text-[13px] text-danger")}>
              {streamError && <p className="m-0">{streamError}</p>}
              {actionError && <p className={streamError ? "mb-0 mt-2" : "m-0"}>{actionError}</p>}
              {session?.status === "failed" && streamError?.includes("Connection") && (
                <p className="mb-0 mt-2 text-muted">
                  Tip: set{" "}
                  <code className="rounded border border-border bg-page px-1 py-0.5 text-xs">
                    BREWMIND_OFFLINE=true
                  </code>{" "}
                  in{" "}
                  <code className="rounded border border-border bg-page px-1 py-0.5 text-xs">.env</code> for local dev
                  without Nebius, or verify your API key and network.
                </p>
              )}
            </div>
          )}
        </div>

        <div className="mt-3 shrink-0 space-y-3">
          <AgentStagePanel events={events} running={showStop || deciding || restarting} />
          <StreamLog events={events} running={showStop || deciding || restarting} />
        </div>

        <div className="mt-4 grid min-h-0 min-w-0 flex-1 grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_22rem]">
          <div className="min-h-0 min-w-0 max-w-full space-y-4 overflow-x-hidden overflow-y-auto [scrollbar-gutter:stable]">
            <StepNav
              currentStep={viewStep}
              completedSteps={completedSteps}
              onSelect={setViewStep}
              validationMode={session?.validation_mode || null}
            />

            {(showStop || deciding || restarting) && session && (
              <div className="flex flex-wrap items-center gap-2 text-[13px] text-muted-light">
                <span className={statusChipClass(session.status)}>{formatStatusLabel(session.status)}</span>
                {activePhase && (
                  <>
                    <span className="text-muted/40">·</span>
                    <span className="truncate">{activePhase}</span>
                  </>
                )}
              </div>
            )}

            {(deciding || restarting || (session?.status === "running" && session.agent_active)) && (
              <div className={cn(card, "border-blue-900/50 p-4 text-[13px] text-muted")}>
                <p className="m-0 text-accent">{workingMessage}</p>
                <p className="mb-0 mt-2">
                  Status: <strong className="text-foreground">{session?.status}</strong>
                  {session?.current_step ? ` · checkpoint ${session.current_step}` : ""}
                </p>
              </div>
            )}

            <ArtifactView
              stepId={viewStep}
              artifact={artifact}
              pathwaySelection={
                pathwaySelectionEnabled
                  ? { selectedId: selectedPathwayId, onSelectionChange: setSelectedPathwayId }
                  : undefined
              }
              fbaContext={
                viewStep === "cp3_fba_plan"
                  ? {
                      selectedPathway: fbaSelectedPathway,
                      priorRuns: priorPathwayRuns,
                      resolvePathwayName,
                    }
                  : undefined
              }
            />

            {showPathwayRevisitPanel && (
              <PathwayRevisitPanel
                selectedPathwayName={selectedPathway?.name ?? null}
                committedPathwayName={committedPathway?.name ?? null}
                selectionChanged={pathwaySelectionChanged}
                busy={restarting}
                onRestart={handleRestartPathwayStep}
              />
            )}

            {showDecisionPanel && (
              <StepDecisionActions
                showPathwaySelect={viewStep === "cp2_pathways"}
                selectedPathway={selectedPathway}
                agentStatus={agentStatus}
                clarificationsPending={pendingClarifications}
                proceedDisabled={Boolean(proceedBlocked)}
                proceedDisabledReason={proceedBlocked}
                busy={deciding || restarting}
                onRestart={handleRestartStep}
                onProceed={handleProceed}
                onReject={() => {
                  if (window.confirm("Reject this session? The run will stop and cannot be resumed.")) {
                    void sendDecision("reject");
                  }
                }}
              />
            )}
          </div>

          <aside className="flex min-h-0 min-w-0 flex-col lg:sticky lg:top-[4.5rem] lg:max-h-[calc(100dvh-5.5rem)] lg:overflow-y-auto">
            <SessionContextPanel
              session={session}
              showRevise={showDecisionPanel}
              reviseBusy={deciding || restarting}
              clarificationPrompt={showDecisionPanel ? clarificationPrompt : null}
              onRevise={(notes) => sendDecision("revise", { notes })}
            />
          </aside>
        </div>
      </div>
    </div>
  );
}
