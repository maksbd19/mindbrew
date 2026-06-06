"use client";

import { useState, type ReactNode } from "react";
import { cn } from "@/lib/ui";

export default function PriorArtifactCollapsible({
  title = "Previous results",
  subtitle,
  children,
  className,
}: {
  title?: string;
  subtitle?: string;
  children: ReactNode;
  className?: string;
}) {
  const [open, setOpen] = useState(false);

  return (
    <div className={cn("overflow-hidden rounded-lg border border-border-subtle bg-surface-raised/30", className)}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left transition-colors hover:bg-surface-hover/40"
      >
        <div className="min-w-0">
          <p className="text-[14px] font-medium text-foreground">{title}</p>
          {subtitle ? <p className="mt-0.5 text-[12px] text-muted">{subtitle}</p> : null}
        </div>
        <span className="shrink-0 text-[12px] text-muted">{open ? "Hide ▴" : "Show ▾"}</span>
      </button>
      {open && <div className="border-t border-border-subtle px-4 py-4">{children}</div>}
    </div>
  );
}
