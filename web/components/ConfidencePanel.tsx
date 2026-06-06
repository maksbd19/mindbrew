"use client";

import { useState } from "react";
import { FBA_VERDICT_METHODOLOGY, PATHWAY_CONFIDENCE_RUBRIC } from "@/lib/bioLinks";
import { cn, confidenceColorClass, link } from "@/lib/ui";

export default function ConfidencePanel({
  label,
  rationale,
  factors,
  methodologyType = "pathway",
}: {
  label: string;
  rationale?: string;
  factors?: string[];
  methodologyType?: "pathway" | "fba";
}) {
  const [showMethodology, setShowMethodology] = useState(false);

  return (
    <div className="mt-2 text-sm">
      <div>
        <span className={cn("mr-2 font-semibold capitalize", confidenceColorClass(label))}>{label}</span>
        {rationale && <span className="text-muted-light">{rationale}</span>}
      </div>
      {factors && factors.length > 0 && (
        <ul className="my-1.5 list-disc pl-5 text-muted">
          {factors.map((f) => (
            <li key={f}>{f}</li>
          ))}
        </ul>
      )}
      <button
        type="button"
        onClick={() => setShowMethodology(!showMethodology)}
        className={cn(link, "mt-1 p-0 text-xs")}
      >
        {showMethodology ? "Hide" : "Show"} scoring methodology
      </button>
      {showMethodology && (
        <pre className="mt-1.5 whitespace-pre-wrap rounded bg-surface p-2 text-xs text-muted">
          {methodologyType === "fba" ? FBA_VERDICT_METHODOLOGY : PATHWAY_CONFIDENCE_RUBRIC}
        </pre>
      )}
    </div>
  );
}
