"use client";

import ReactMarkdown from "react-markdown";
import type { FbaResult, LiteraturePlan, PathwayCandidate } from "@/lib/bioLinks";
import type { PathwayRunHistoryEntry } from "@/lib/pathwaySelection";
import { formatStepLabel } from "@/lib/format";
import ArtifactPanel from "./ArtifactPanel";
import FbaPlanView from "./FbaPlanView";
import FbaResultsView from "./FbaResultsView";
import LiteraturePlanView from "./LiteraturePlanView";
import PathwayTable from "./PathwayTable";
import SpecView from "./SpecView";

function ArtifactFrame({ children }: { children: React.ReactNode }) {
  return <div className="min-w-0 max-w-full">{children}</div>;
}

export default function ArtifactView({
  stepId,
  artifact,
  pathwaySelection,
  fbaContext,
}: {
  stepId: string;
  artifact: Record<string, unknown> | null;
  pathwaySelection?: {
    selectedId: string | null;
    onSelectionChange: (id: string | null) => void;
  };
  fbaContext?: {
    selectedPathway: { id: string; name: string } | null;
    priorRuns: PathwayRunHistoryEntry[];
    resolvePathwayName: (pathwayId: string | undefined) => string;
  };
}) {
  const stepLabel = formatStepLabel(stepId);

  if (!artifact) {
    return (
      <ArtifactFrame>
        <ArtifactPanel title={stepLabel} subtitle="Step output">
          <div className="flex flex-col items-center py-10 text-center">
            <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-surface-raised text-muted">
              ◌
            </div>
            <p className="text-[14px] font-medium text-foreground">No artifact yet</p>
            <p className="mt-1 max-w-sm text-[13px] text-muted">
              Results will appear here once the agent completes this checkpoint.
            </p>
          </div>
        </ArtifactPanel>
      </ArtifactFrame>
    );
  }

  if (stepId === "cp5_report" && artifact.report) {
    const report = artifact.report as { markdown?: string };
    return (
      <ArtifactFrame>
        <ArtifactPanel title="Final report" subtitle="Validated pathway blueprint" noPadding bodyClassName="p-0">
          <div className="prose prose-invert max-w-none overflow-x-auto px-5 py-4 text-[14px] leading-relaxed prose-headings:tracking-tight prose-p:text-muted-light prose-li:text-muted-light">
            <ReactMarkdown>{report.markdown || JSON.stringify(report, null, 2)}</ReactMarkdown>
          </div>
        </ArtifactPanel>
      </ArtifactFrame>
    );
  }

  if (stepId === "cp2_pathways" && artifact.pathway_candidates) {
    return (
      <ArtifactFrame>
        <PathwayTable
          candidates={artifact.pathway_candidates as PathwayCandidate[]}
          organism={artifact.organism as string[] | undefined}
          selectable={Boolean(pathwaySelection)}
          selectedId={pathwaySelection?.selectedId ?? null}
          onSelectionChange={pathwaySelection?.onSelectionChange}
        />
      </ArtifactFrame>
    );
  }

  if (stepId === "cp1_spec" && artifact.brief) {
    return (
      <ArtifactFrame>
        <SpecView
          brief={artifact.brief as Record<string, unknown>}
          validationMode={artifact.validation_mode as string | undefined}
          gemProfile={artifact.gem_profile as Record<string, unknown> | null}
          gemSelectionReason={artifact.gem_selection_reason as string | undefined}
        />
      </ArtifactFrame>
    );
  }

  if (stepId === "cp3_fba_plan") {
    return (
      <ArtifactFrame>
        <FbaPlanView
          payloads={(artifact.score_payloads as Array<{
            pathway_id: string;
            model_ref?: string;
            scenario?: string;
            carbon_source_rxn?: string;
            product_metabolite?: string;
            knockouts?: string[];
            substrate_moles_per_product?: number;
            candidate_reactions?: Array<{
              id: string;
              name: string;
              stoichiometry?: Record<string, number>;
              gene_associations?: string[];
            }>;
            source_citations?: import("@/lib/bioLinks").Citation[];
          }>) ?? []}
          skipped={artifact.skipped as string[] | undefined}
          gemProfile={artifact.gem_profile as Record<string, unknown> | null}
          selectedPathway={fbaContext?.selectedPathway ?? null}
          priorRuns={fbaContext?.priorRuns}
          resolvePathwayName={fbaContext?.resolvePathwayName}
        />
      </ArtifactFrame>
    );
  }

  if (stepId === "cp3b_literature_plan" && artifact.literature_plan) {
    return (
      <ArtifactFrame>
        <LiteraturePlanView
          plan={artifact.literature_plan as LiteraturePlan}
          organism={artifact.organism as string[] | undefined}
        />
      </ArtifactFrame>
    );
  }

  if (stepId === "cp4_fba_results" && artifact.fba_results) {
    return (
      <ArtifactFrame>
        <FbaResultsView results={artifact.fba_results as FbaResult[]} />
      </ArtifactFrame>
    );
  }

  return (
    <ArtifactFrame>
      <ArtifactPanel title={stepLabel} subtitle="Raw artifact data">
        <pre className="m-0 overflow-x-auto rounded-md border border-border-subtle bg-surface-raised p-4 font-mono text-[12px] leading-relaxed text-muted-light">
          {JSON.stringify(artifact, null, 2)}
        </pre>
      </ArtifactPanel>
    </ArtifactFrame>
  );
}
