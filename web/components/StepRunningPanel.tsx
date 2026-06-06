"use client";

import ArtifactPanel from "./ArtifactPanel";

export default function StepRunningPanel({
  title,
  message = "The agent is working on this step. Results will appear here when ready.",
}: {
  title: string;
  message?: string;
}) {
  return (
    <ArtifactPanel title={title} subtitle="In progress">
      <div className="flex flex-col items-center py-12 text-center">
        <div
          className="mb-4 h-10 w-10 animate-spin rounded-full border-2 border-border border-t-accent"
          aria-hidden
        />
        <p className="text-[14px] font-medium text-foreground">Running…</p>
        <p className="mt-2 max-w-md text-[13px] leading-relaxed text-muted">{message}</p>
      </div>
    </ArtifactPanel>
  );
}
