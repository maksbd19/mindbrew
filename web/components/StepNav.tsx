"use client";

import { SESSION_STEPS, pipelineStepOrdinal, stepInPipeline } from "@/lib/steps";
import { formatStepLabel } from "@/lib/format";
import { cn } from "@/lib/ui";

export default function StepNav({
  currentStep,
  completedSteps,
  onSelect,
  validationMode,
}: {
  currentStep: string;
  completedSteps: Set<string>;
  onSelect: (stepId: string) => void;
  validationMode: string | null;
}) {
  return (
    <nav aria-label="Session steps" className="mb-6 w-full overflow-x-auto border-b border-border-subtle">
      <div className="flex min-w-max gap-0.5">
        {SESSION_STEPS.map((s) => {
          const done = completedSteps.has(s.id);
          const active = s.id === currentStep;
          const inPipeline = stepInPipeline(s.id, validationMode);
          const visitable = inPipeline || !validationMode;
          const ordinal = pipelineStepOrdinal(s.id, validationMode);
          const label = s.label || formatStepLabel(s.id);

          return (
            <button
              key={s.id}
              type="button"
              disabled={!visitable}
              onClick={() => {
                if (visitable) onSelect(s.id);
              }}
              aria-current={active ? "step" : undefined}
              aria-disabled={!visitable || undefined}
              title={inPipeline ? undefined : "Not used in this session's validation path"}
              className={cn(
                "relative flex items-center gap-2 whitespace-nowrap px-4 py-3 text-[13px] font-medium transition-colors",
                active
                  ? "text-foreground after:absolute after:inset-x-0 after:bottom-0 after:h-0.5 after:bg-primary"
                  : visitable
                    ? "text-muted hover:text-foreground"
                    : "cursor-not-allowed text-muted/50"
              )}
            >
              <span
                className={cn(
                  "flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold",
                  active
                    ? "bg-primary text-white"
                    : done && inPipeline
                      ? "bg-chip-completed-bg text-chip-completed-text"
                      : inPipeline
                        ? "bg-surface-raised text-muted"
                        : "bg-surface-raised/60 text-muted/50"
                )}
              >
                {done && inPipeline ? "✓" : ordinal ?? "—"}
              </span>
              {label}
            </button>
          );
        })}
      </div>
    </nav>
  );
}
