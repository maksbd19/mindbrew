const STEP_LABELS: Record<string, string> = {
  cp1_spec: "Spec",
  cp2_pathways: "Pathways",
  cp3_fba_plan: "FBA Plan",
  cp3b_literature_plan: "Literature",
  cp4_fba_results: "FBA Results",
  cp5_report: "Report",
};

const STATUS_LABELS: Record<string, string> = {
  awaiting_user: "Awaiting review",
  running: "Running",
  completed: "Completed",
  interrupted: "Interrupted",
  failed: "Failed",
};

export function formatStepLabel(stepId: string): string {
  return STEP_LABELS[stepId] ?? stepId.replace(/_/g, " ");
}

export function formatStatusLabel(status: string): string {
  return STATUS_LABELS[status] ?? status.replace(/_/g, " ");
}

export function formatRelativeDate(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";

  const now = Date.now();
  const diffMs = now - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHr = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHr / 24);

  if (diffSec < 60) return "Just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHr < 24) return `${diffHr}h ago`;
  if (diffDay < 7) return `${diffDay}d ago`;

  return date.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: date.getFullYear() !== new Date().getFullYear() ? "numeric" : undefined,
  });
}

export function formatFullDate(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}
