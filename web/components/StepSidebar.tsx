"use client";

import { cn } from "@/lib/ui";

const STEPS = [
  { id: "cp1_spec", label: "1 — Spec" },
  { id: "cp2_pathways", label: "2 — Pathways" },
  { id: "cp3_fba_plan", label: "3 — FBA Plan" },
  { id: "cp3b_literature_plan", label: "3b — Lit Plan" },
  { id: "cp4_fba_results", label: "4 — Results" },
  { id: "cp5_report", label: "5 — Report" },
];

export default function StepSidebar({
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
    <nav className="w-[200px] shrink-0">
      <h3 className="mb-2 mt-0 text-sm text-muted">Steps</h3>
      <ul className="m-0 list-none p-0">
        {visible.map((s) => {
          const done = completedSteps.has(s.id);
          const active = s.id === currentStep;
          return (
            <li key={s.id} className="mb-1.5">
              <button
                type="button"
                onClick={() => onSelect(s.id)}
                className={cn(
                  "w-full cursor-pointer rounded-md border px-2.5 py-1.5 text-left text-sm transition-colors",
                  active
                    ? "border-primary bg-[#2a3550] text-foreground"
                    : "border-border bg-transparent text-foreground hover:border-accent/40"
                )}
              >
                {done ? "✓ " : ""}
                {s.label}
              </button>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
