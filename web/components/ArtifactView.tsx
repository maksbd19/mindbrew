"use client";

import ReactMarkdown from "react-markdown";
import type { FbaResult, LiteraturePlan, PathwayCandidate } from "@/lib/bioLinks";
import { card, cn } from "@/lib/ui";
import FbaPlanView from "./FbaPlanView";
import FbaResultsView from "./FbaResultsView";
import LiteraturePlanView from "./LiteraturePlanView";
import PathwayTable from "./PathwayTable";
import SpecView from "./SpecView";

export default function ArtifactView({
  stepId,
  artifact,
}: {
  stepId: string;
  artifact: Record<string, unknown> | null;
}) {
  if (!artifact) {
    return (
      <div className={card}>
        <p className="text-muted">No artifact for this step yet.</p>
      </div>
    );
  }

  if (stepId === "cp5_report" && artifact.report) {
    const report = artifact.report as { markdown?: string };
    return (
      <div className={cn(card, "prose prose-invert max-w-none overflow-auto max-h-[480px] text-sm")}>
        <ReactMarkdown>{report.markdown || JSON.stringify(report, null, 2)}</ReactMarkdown>
      </div>
    );
  }

  if (stepId === "cp2_pathways" && artifact.pathway_candidates) {
    return (
      <PathwayTable
        candidates={artifact.pathway_candidates as PathwayCandidate[]}
        organism={artifact.organism as string[] | undefined}
      />
    );
  }

  if (stepId === "cp1_spec" && artifact.brief) {
    return (
      <SpecView
        brief={artifact.brief as Record<string, unknown>}
        validationMode={artifact.validation_mode as string | undefined}
        gemProfile={artifact.gem_profile as Record<string, unknown> | null}
        gemSelectionReason={artifact.gem_selection_reason as string | undefined}
      />
    );
  }

  if (stepId === "cp3_fba_plan") {
    return (
      <FbaPlanView
        payloads={(artifact.score_payloads as Array<{
          pathway_id: string;
          model_ref?: string;
          scenario?: string;
          candidate_reactions?: Array<{ id: string; name: string; gene_associations?: string[] }>;
          source_citations?: import("@/lib/bioLinks").Citation[];
        }>) ?? []}
        skipped={artifact.skipped as string[] | undefined}
        gemProfile={artifact.gem_profile as Record<string, unknown> | null}
      />
    );
  }

  if (stepId === "cp3b_literature_plan" && artifact.literature_plan) {
    return (
      <LiteraturePlanView
        plan={artifact.literature_plan as LiteraturePlan}
        organism={artifact.organism as string[] | undefined}
      />
    );
  }

  if (stepId === "cp4_fba_results" && artifact.fba_results) {
    return <FbaResultsView results={artifact.fba_results as FbaResult[]} />;
  }

  return (
    <div className={cn(card, "max-h-[480px] overflow-auto")}>
      <pre className="m-0 text-xs">{JSON.stringify(artifact, null, 2)}</pre>
    </div>
  );
}
