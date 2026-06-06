import type { StepRecord } from "@/lib/api";

export type PathwayChoice = { id: string; name: string };

export type PathwayRunHistoryEntry = {
  pathway_id?: string;
  revision_number?: number;
  cp3_fba_plan?: Record<string, unknown>;
  cp4_fba_results?: Record<string, unknown>;
};

type HumanDecision = {
  action?: string;
  checkpoint?: string;
  primary_pathway_id?: string;
  selected_pathway_ids?: string[];
};

export function committedPathwayId(humanDecisions: unknown[] | undefined): string | null {
  if (!humanDecisions?.length) return null;
  for (let i = humanDecisions.length - 1; i >= 0; i--) {
    const d = humanDecisions[i] as HumanDecision;
    if (d.action !== "proceed") continue;
    if (d.checkpoint && d.checkpoint !== "cp2_pathways") continue;
    if (d.primary_pathway_id) return d.primary_pathway_id;
    if (d.selected_pathway_ids?.[0]) return d.selected_pathway_ids[0];
  }
  return null;
}

export function resolvePathwayChoice(
  candidates: PathwayChoice[],
  pathwayId: string | null | undefined
): PathwayChoice | null {
  if (!pathwayId) return null;
  return candidates.find((p) => p.id === pathwayId) ?? { id: pathwayId, name: pathwayId };
}

export function pathwayRunHistory(cp2Step: StepRecord | undefined): PathwayRunHistoryEntry[] {
  const artifact = cp2Step?.artifact;
  if (!artifact || !Array.isArray(artifact._pathway_run_history)) return [];
  return artifact._pathway_run_history as PathwayRunHistoryEntry[];
}

export function pathwayCandidatesFromStep(step: StepRecord | undefined): PathwayChoice[] {
  const raw = step?.artifact?.pathway_candidates;
  if (!Array.isArray(raw)) return [];
  return raw
    .filter((p): p is { id: string; name: string } => Boolean(p && typeof p === "object" && "id" in p))
    .map((p) => ({ id: String(p.id), name: String(p.name || p.id) }));
}
