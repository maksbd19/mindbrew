/** Whether a persisted step artifact has displayable content. */
export function stepArtifactHasContent(
  stepId: string,
  artifact: Record<string, unknown> | null | undefined
): boolean {
  if (!artifact) return false;
  switch (stepId) {
    case "cp1_spec":
      return Boolean(artifact.brief);
    case "cp2_pathways":
      return Array.isArray(artifact.pathway_candidates) && artifact.pathway_candidates.length > 0;
    case "cp3_fba_plan":
      return (
        (Array.isArray(artifact.score_payloads) && artifact.score_payloads.length > 0) ||
        (Array.isArray(artifact.skipped) && artifact.skipped.length > 0)
      );
    case "cp3b_literature_plan":
      return Boolean(artifact.literature_plan);
    case "cp4_fba_results":
      return Array.isArray(artifact.fba_results) && artifact.fba_results.length > 0;
    case "cp5_report":
      return Boolean((artifact.report as { markdown?: string } | undefined)?.markdown);
    default:
      return Object.keys(artifact).length > 0;
  }
}
