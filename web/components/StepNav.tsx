"use client";

import { formatStepLabel } from "@/lib/format";
import { cn } from "@/lib/ui";

const STEPS = [
  { id: "cp1_spec", label: "Spec" },
  { id: "cp2_pathways", label: "Pathways" },
  { id: "cp3_fba_plan", label: "FBA Plan" },
  { id: "cp3b_literature_plan", label: "Literature" },
  { id: "cp4_fba_results", label: "Results" },
  { id: "cp5_report", label: "Report" },
];

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
  const visible = STEPS.filter((s) => {
    if (validationMode === "literature") {
      return !["cp3_fba_plan", "cp4_fba_results"].includes(s.id);
    }
    if (validationMode === "fba") {
      return s.id !== "cp3b_literature_plan";
    }
    return true;
  });

  return (
    <nav aria-label="Session steps" className="mb-6 w-full overflow-x-auto border-b border-border-subtle">
      <div className="flex min-w-max gap-0.5">
        {visible.map((s, index) => {
          const done = completedSteps.has(s.id);
          const active = s.id === currentStep;
          const label = s.label || formatStepLabel(s.id);

          return (
            <button
              key={s.id}
              type="button"
              onClick={() => onSelect(s.id)}
              aria-current={active ? "step" : undefined}
              className={cn(
                "relative flex items-center gap-2 whitespace-nowrap px-4 py-3 text-[13px] font-medium transition-colors",
                active
                  ? "text-foreground after:absolute after:inset-x-0 after:bottom-0 after:h-0.5 after:bg-primary"
                  : "text-muted hover:text-foreground"
              )}
            >
              <span
                className={cn(
                  "flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold",
                  active
                    ? "bg-primary text-white"
                    : done
                      ? "bg-chip-completed-bg text-chip-completed-text"
                      : "bg-surface-raised text-muted"
                )}
              >
                {done ? "✓" : index + 1}
              </span>
              {label}
            </button>
          );
        })}
      </div>
    </nav>
  );
}
