"use client";

import type { Session } from "@/lib/api";
import ArtifactPanel from "./ArtifactPanel";
import ReviseForm from "./ReviseForm";
import { formatStepLabel } from "@/lib/format";
import { formatDecisionPathwaySummary, pathwayCandidatesFromStep } from "@/lib/pathwaySelection";
import { cn } from "@/lib/ui";

type HumanDecision = {
  checkpoint?: string;
  action?: string;
  notes?: string | null;
  selected_pathway_ids?: string[];
  primary_pathway_id?: string;
};

function formatAction(action?: string): string {
  if (!action) return "responded";
  return action.replace(/_/g, " ");
}

function collectDecisions(session: Session): { stepId: string; decision: HumanDecision }[] {
  const items: { stepId: string; decision: HumanDecision }[] = [];
  for (const step of session.steps) {
    for (const raw of step.human_decisions || []) {
      items.push({ stepId: step.step_id, decision: raw as HumanDecision });
    }
  }
  return items;
}

function ConversationEntry({
  role,
  label,
  body,
  meta,
  tone = "default",
}: {
  role: "user" | "system";
  label: string;
  body?: string | null;
  meta?: string;
  tone?: "default" | "warning";
}) {
  return (
    <div
      className={cn(
        "rounded-md border px-3 py-2.5 text-[13px]",
        tone === "warning" && "border-amber-900/50 bg-amber-950/20",
        tone === "default" &&
          (role === "user"
            ? "border-border bg-surface-raised"
            : "border-border-subtle bg-surface")
      )}
    >
      <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
        <span className="font-medium text-foreground">{label}</span>
        {meta && <span className="text-[11px] text-muted">{meta}</span>}
      </div>
      {body?.trim() && (
        <p
          className={cn(
            "mb-0 mt-1.5 whitespace-pre-wrap leading-relaxed",
            tone === "warning" ? "text-amber-100" : "text-muted-light"
          )}
        >
          {body}
        </p>
      )}
    </div>
  );
}

export default function SessionContextPanel({
  session,
  showRevise,
  reviseBusy,
  onRevise,
  clarificationPrompt,
}: {
  session: Session | null;
  showRevise?: boolean;
  reviseBusy?: boolean;
  onRevise?: (notes: string) => void;
  clarificationPrompt?: string | null;
}) {
  const decisions = session ? collectDecisions(session) : [];
  const pathwayCandidates = pathwayCandidatesFromStep(
    session?.steps.find((s) => s.step_id === "cp2_pathways")
  );

  return (
    <div className="flex h-full min-h-0 min-w-0 flex-col gap-4">
      <ArtifactPanel title="Your brief" subtitle="Original R&D ticket" className="shrink-0">
        <p className="m-0 whitespace-pre-wrap text-[13px] leading-relaxed text-muted-light">
          {session?.raw_brief || "Loading…"}
        </p>
      </ArtifactPanel>

      <ArtifactPanel
        title="Conversation"
        subtitle="Your decisions and revision notes"
        className="flex min-h-0 flex-1 flex-col"
        bodyClassName="flex min-h-0 flex-1 flex-col"
      >
        <div className="space-y-2">
          {decisions.map((item, i) => {
            const { decision } = item;
            const checkpoint = decision.checkpoint || item.stepId;
            const meta = formatStepLabel(checkpoint);
            const action = formatAction(decision.action);
            const pathwayDetail = formatDecisionPathwaySummary(pathwayCandidates, decision);
            const detail = decision.notes?.trim() || pathwayDetail || undefined;

            return (
              <ConversationEntry
                key={`${item.stepId}-${i}`}
                role="user"
                label={action.charAt(0).toUpperCase() + action.slice(1)}
                meta={meta}
                body={detail}
              />
            );
          })}
          {session && decisions.length === 0 && !showRevise && !clarificationPrompt && (
            <p className="m-0 text-[13px] text-muted">No decisions yet — review checkpoints as they complete.</p>
          )}
          {showRevise && clarificationPrompt && (
            <ConversationEntry
              role="system"
              label="Clarifications needed"
              meta="Agent"
              body={clarificationPrompt}
              tone="warning"
            />
          )}
        </div>
        {showRevise && onRevise && (
          <ReviseForm
            busy={reviseBusy}
            onRevise={onRevise}
            hasClarifications={Boolean(clarificationPrompt)}
          />
        )}
      </ArtifactPanel>
    </div>
  );
}
