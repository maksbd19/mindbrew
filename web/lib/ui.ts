import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const container = "mx-auto w-full max-w-6xl px-6 py-8";

export const pageTitle = "text-xl font-semibold tracking-tight text-foreground";

export const pageSubtitle = "mt-1 text-[14px] text-muted";

export const card = "rounded-lg border border-border bg-surface shadow-card";

export const cardTitle = "text-[15px] font-semibold text-foreground";

export const cardSubtitle = "text-[13px] font-medium text-muted";

export const btnBase =
  "inline-flex items-center justify-center rounded-md px-4 py-2 text-[13px] font-medium whitespace-nowrap transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:ring-offset-2 focus-visible:ring-offset-page disabled:cursor-not-allowed disabled:opacity-50";

export const btnPrimary = cn(btnBase, "bg-primary text-white hover:bg-primary-hover");

export const btnSecondary = cn(
  btnBase,
  "border border-border bg-surface-raised text-foreground hover:bg-surface-hover"
);

export const actionBar = "flex flex-wrap items-center gap-2";

export const inputBase =
  "w-full rounded-md border border-border bg-surface px-3 py-2 text-[14px] text-foreground placeholder:text-muted focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20";

export const link = "text-accent hover:text-accent-muted hover:underline";

export const dataTable = "w-full text-left text-[14px]";

export const dataTableHead =
  "border-b border-border-subtle px-5 py-3 text-[11px] font-medium uppercase tracking-wider text-muted";

export const dataTableCell = "px-5 py-3.5 align-middle";

export function statusChipClass(status: string): string {
  const base = "inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-medium";
  switch (status) {
    case "awaiting_user":
      return cn(base, "bg-chip-awaiting-bg text-chip-awaiting-text");
    case "completed":
      return cn(base, "bg-chip-completed-bg text-chip-completed-text");
    case "running":
      return cn(base, "bg-chip-running-bg text-chip-running-text");
    case "interrupted":
    case "failed":
      return cn(base, "bg-chip-interrupted-bg text-chip-interrupted-text");
    default:
      return cn(base, "bg-secondary text-muted-light");
  }
}

export function eventColorClass(type: string, level?: string): string {
  if (type === "error" || level === "error") return "text-danger";
  if (level === "warning") return "text-warning";
  if (type === "log") return "text-muted";
  if (type === "heartbeat") return "text-muted/60 italic";
  if (type === "node_start") return "text-accent";
  if (type === "node_end" || type === "step_complete") return "text-success";
  if (type === "tool_start") return "text-accent";
  if (type === "tool_end") return "text-success";
  if (type === "llm_call") return "text-purple-300";
  if (type === "awaiting_user") return "text-warning";
  if (type === "decision_accepted") return "text-purple-300";
  if (type === "action_rejected") return "text-danger";
  return "text-muted";
}

export function confidenceColorClass(label: string): string {
  switch (label.toLowerCase()) {
    case "strong":
    case "pass":
      return "text-verified";
    case "partial":
    case "marginal":
      return "text-unverified";
    case "inferred":
      return "text-muted";
    case "fail":
      return "text-invalid";
    default:
      return "text-foreground";
  }
}

export function citationStatusColor(status: string): string {
  switch (status) {
    case "verified":
      return "text-verified";
    case "unverified":
      return "text-unverified";
    case "invalid":
      return "text-invalid";
    default:
      return "text-muted";
  }
}
