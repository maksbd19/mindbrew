import { SESSION_STEPS } from "./steps";

const STEP_LABELS: Record<string, string> = Object.fromEntries(
  SESSION_STEPS.map((s) => [s.id, s.label])
);

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

export function formatDisplayPath(path: string | null | undefined | unknown): string {
  if (path == null || typeof path !== "string" || !path) return "";
  const normalized = path.replace(/\\/g, "/");
  const name = normalized.split("/").filter(Boolean).pop();
  return name ?? path;
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
