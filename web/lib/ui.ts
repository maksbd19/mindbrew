import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const container = "mx-auto max-w-6xl px-6 py-6";

export const card = "mb-3 rounded-lg border border-border bg-surface p-4";

export const cardTitle = "mb-3 text-base font-semibold text-foreground";

export const cardSubtitle = "mb-2 text-sm font-semibold text-muted";

export const btnBase =
  "inline-flex items-center justify-center rounded-md px-4 py-2 text-sm font-medium whitespace-nowrap transition-colors disabled:cursor-not-allowed disabled:opacity-55";

export const btnPrimary = cn(btnBase, "bg-primary text-white hover:bg-primary-hover");

export const btnSecondary = cn(btnBase, "bg-secondary text-foreground hover:bg-secondary-hover");

export const actionBar = "flex flex-wrap items-center gap-2";

export const inputBase =
  "w-full rounded-md border border-border bg-page px-3 py-2 text-foreground placeholder:text-muted focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent";

export const link = "text-accent hover:underline";

export const dataTable = "w-full border-collapse text-sm";

export const dataTableHead = "text-left text-muted";

export const dataTableCell = "border-b border-border px-2 py-1.5 align-top";

export function statusChipClass(status: string): string {
  const base = "inline-block rounded-full px-2 py-0.5 text-xs";
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
      return cn(base, "bg-secondary text-foreground");
  }
}

export function eventColorClass(type: string, level?: string): string {
  if (type === "error" || level === "error") return "text-danger";
  if (type === "log") return "text-muted-light";
  if (type === "node_start") return "text-accent";
  if (type === "node_end" || type === "step_complete") return "text-success";
  if (type === "awaiting_user") return "text-warning";
  if (type === "decision_accepted") return "text-purple-300";
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
