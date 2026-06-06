"use client";

import type { ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import type { FbaResult, LiteraturePlan, PathwayCandidate } from "@/lib/bioLinks";
import type { PathwayRunHistoryEntry } from "@/lib/pathwaySelection";
import { stepArtifactHasContent } from "@/lib/stepArtifact";
import { formatStepLabel } from "@/lib/format";
import ArtifactPanel from "./ArtifactPanel";
import FbaPlanView from "./FbaPlanView";
import FbaResultsView from "./FbaResultsView";
import LiteraturePlanView from "./LiteraturePlanView";
import PathwayTable from "./PathwayTable";
import PriorArtifactCollapsible from "./PriorArtifactCollapsible";
import ReportExportActions from "./ReportExportActions";
import SpecView from "./SpecView";
import StepRunningPanel from "./StepRunningPanel";

function ArtifactFrame({ children }: { children: React.ReactNode }) {
  return <div className="min-w-0 max-w-full">{children}</div>;
}

type FbaContext = {
  selectedPathway: { id: string; name: string } | null;
  priorRuns: PathwayRunHistoryEntry[];
  resolvePathwayName: (pathwayId: string | undefined) => string;
};

type ScorePayload = {
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
};

function renderStepArtifact({
  stepId,
  artifact,
  sessionId,
  pathwaySelection,
  pathwayActionBar,
  fbaContext,
  embedded = false,
}: {
  stepId: string;
  artifact: Record<string, unknown>;
  sessionId?: string;
  pathwaySelection?: {
    selectedId: string | null;
    onSelectionChange: (id: string | null) => void;
  };
  pathwayActionBar?: ReactNode;
  fbaContext?: FbaContext;
  embedded?: boolean;
}): ReactNode {
  if (stepId === "cp5_report" && artifact.report) {
    const report = artifact.report as { markdown?: string };
    if (embedded) {
      return (
        <div className="prose prose-invert max-w-none overflow-x-auto text-[14px] leading-relaxed prose-headings:tracking-tight prose-p:text-muted-light prose-li:text-muted-light">
          <ReactMarkdown>{report.markdown || JSON.stringify(report, null, 2)}</ReactMarkdown>
        </div>
      );
    }
    return (
      <ArtifactPanel
        title="Final report"
        subtitle="Validated pathway blueprint"
        headerActions={sessionId ? <ReportExportActions sessionId={sessionId} /> : undefined}
        noPadding
        bodyClassName="p-0"
      >
        <div className="prose prose-invert max-w-none overflow-x-auto px-5 py-4 text-[14px] leading-relaxed prose-headings:tracking-tight prose-p:text-muted-light prose-li:text-muted-light">
          <ReactMarkdown>{report.markdown || JSON.stringify(report, null, 2)}</ReactMarkdown>
        </div>
      </ArtifactPanel>
    );
  }

  if (stepId === "cp2_pathways" && Array.isArray(artifact.pathway_candidates)) {
    return (
      <PathwayTable
        candidates={artifact.pathway_candidates as PathwayCandidate[]}
        organism={artifact.organism as string[] | undefined}
        selectable={Boolean(pathwaySelection)}
        selectedId={pathwaySelection?.selectedId ?? null}
        onSelectionChange={pathwaySelection?.onSelectionChange}
        actionBar={pathwayActionBar}
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
        payloads={(artifact.score_payloads as ScorePayload[]) ?? []}
        skipped={artifact.skipped as string[] | undefined}
        gemProfile={artifact.gem_profile as Record<string, unknown> | null}
        gemDiscovery={artifact.gem_discovery as Record<string, unknown> | null}
        biomassValidationWarning={artifact.biomass_validation_warning as string | null}
        findIdsSummary={artifact.find_ids_summary as Record<string, unknown> | null}
        selectedPathway={embedded ? null : (fbaContext?.selectedPathway ?? null)}
        priorRuns={embedded ? undefined : fbaContext?.priorRuns}
        resolvePathwayName={embedded ? undefined : fbaContext?.resolvePathwayName}
        embedded={embedded}
      />
    );
  }

  if (stepId === "cp3b_literature_plan") {
    if (artifact.literature_plan) {
      return (
        <LiteraturePlanView
          plan={artifact.literature_plan as LiteraturePlan}
          organism={artifact.organism as string[] | undefined}
        />
      );
    }
    return (
      <ArtifactPanel title="Literature plan" subtitle="Pathway validation without GEM">
        <div className="flex flex-col items-center py-10 text-center">
          <p className="text-[14px] font-medium text-foreground">No literature plan yet</p>
          <p className="mt-1 max-w-sm text-[13px] text-muted">
            Results will appear here once the agent completes this checkpoint.
          </p>
        </div>
      </ArtifactPanel>
    );
  }

  if (stepId === "cp4_fba_results") {
    return (
      <FbaResultsView
        results={(artifact.fba_results as FbaResult[] | undefined) ?? []}
        selectedPathway={embedded ? null : (fbaContext?.selectedPathway ?? null)}
        priorRuns={embedded ? undefined : fbaContext?.priorRuns}
        resolvePathwayName={embedded ? undefined : fbaContext?.resolvePathwayName}
        embedded={embedded}
      />
    );
  }

  const stepLabel = formatStepLabel(stepId);
  return (
    <ArtifactPanel title={stepLabel} subtitle="Raw artifact data">
      <pre className="m-0 overflow-x-auto rounded-md border border-border-subtle bg-surface-raised p-4 font-mono text-[12px] leading-relaxed text-muted-light">
        {JSON.stringify(artifact, null, 2)}
      </pre>
    </ArtifactPanel>
  );
}

export default function ArtifactView({
  stepId,
  artifact,
  sessionId,
  pathwaySelection,
  pathwayActionBar,
  fbaContext,
  running = false,
  priorArtifact,
  runningMessage,
}: {
  stepId: string;
  artifact: Record<string, unknown> | null;
  sessionId?: string;
  pathwaySelection?: {
    selectedId: string | null;
    onSelectionChange: (id: string | null) => void;
  };
  pathwayActionBar?: ReactNode;
  fbaContext?: FbaContext;
  running?: boolean;
  priorArtifact?: Record<string, unknown> | null;
  runningMessage?: string;
}) {
  const stepLabel = formatStepLabel(stepId);

  if (running) {
    const hasPrior = priorArtifact && stepArtifactHasContent(stepId, priorArtifact);
    return (
      <ArtifactFrame>
        <StepRunningPanel title={stepLabel} message={runningMessage} />
        {hasPrior && (
          <PriorArtifactCollapsible
            title="Previous results"
            subtitle="From the last completed run of this step"
            className="mt-4"
          >
            {renderStepArtifact({
              stepId,
              artifact: priorArtifact,
              sessionId,
              fbaContext,
              embedded: true,
            })}
          </PriorArtifactCollapsible>
        )}
      </ArtifactFrame>
    );
  }

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

  return <ArtifactFrame>{renderStepArtifact({ stepId, artifact, sessionId, pathwaySelection, pathwayActionBar, fbaContext })}</ArtifactFrame>;
}
