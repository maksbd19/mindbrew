"use client";

import type { Session } from "@/lib/api";
import ArtifactPanel from "./ArtifactPanel";
import ReviseForm from "./ReviseForm";
import { formatStepLabel } from "@/lib/format";
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
}: {
  role: "user" | "system";
  label: string;
  body?: string | null;
  meta?: string;
}) {
  return (
    <div
      className={cn(
        "rounded-md border px-3 py-2.5 text-[13px]",
        role === "user"
          ? "border-border bg-surface-raised"
          : "border-border-subtle bg-surface"
      )}
    >
      <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
        <span className="font-medium text-foreground">{label}</span>
        {meta && <span className="text-[11px] text-muted">{meta}</span>}
      </div>
      {body?.trim() && (
        <p className="mb-0 mt-1.5 whitespace-pre-wrap leading-relaxed text-muted-light">{body}</p>
      )}
    </div>
  );
}

export default function SessionContextPanel({
  session,
  showRevise,
  reviseBusy,
  onRevise,
}: {
  session: Session | null;
  showRevise?: boolean;
  reviseBusy?: boolean;
  onRevise?: (notes: string) => void;
}) {
  const decisions = session ? collectDecisions(session) : [];

  return (
    <div className="flex min-h-0 min-w-0 flex-col gap-4">
      <ArtifactPanel title="Your brief" subtitle="Original R&D ticket">
        <p className="m-0 whitespace-pre-wrap text-[13px] leading-relaxed text-muted-light">
          {session?.raw_brief || "Loading…"}
        </p>
      </ArtifactPanel>

      <ArtifactPanel title="Conversation" subtitle="Your decisions and revision notes">
        <div className="space-y-2">
          {decisions.map((item, i) => {
            const { decision } = item;
            const checkpoint = decision.checkpoint || item.stepId;
            const meta = formatStepLabel(checkpoint);
            const action = formatAction(decision.action);
            const extras: string[] = [];
            if (decision.selected_pathway_ids?.length) {
              extras.push(`${decision.selected_pathway_ids.length} pathway(s) selected`);
            }
            const detail = extras.length ? extras.join(" · ") : undefined;

            return (
              <ConversationEntry
                key={`${item.stepId}-${i}`}
                role="user"
                label={action.charAt(0).toUpperCase() + action.slice(1)}
                meta={meta}
                body={decision.notes?.trim() || detail || undefined}
              />
            );
          })}
          {session && decisions.length === 0 && !showRevise && (
            <p className="m-0 text-[13px] text-muted">No decisions yet — review checkpoints as they complete.</p>
          )}
        </div>
        {showRevise && onRevise && (
          <ReviseForm busy={reviseBusy} onRevise={onRevise} />
        )}
      </ArtifactPanel>
    </div>
  );
}
