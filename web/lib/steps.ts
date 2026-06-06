/**
 * Session checkpoint steps — keep in sync with
 * mindbrew_v2/phases/checkpoints.py CHECKPOINT_TO_STEP and StepId enum.
 */
export const SESSION_STEP_IDS = [
  "cp1_spec",
  "cp2_pathways",
  "cp3_fba_plan",
  "cp3b_literature_plan",
  "cp4_fba_results",
  "cp5_report",
] as const;

export type SessionStepId = (typeof SESSION_STEP_IDS)[number];

export const SESSION_STEPS: { id: SessionStepId; label: string }[] = [
  { id: "cp1_spec", label: "Spec" },
  { id: "cp2_pathways", label: "Pathways" },
  { id: "cp3_fba_plan", label: "FBA Plan" },
  { id: "cp3b_literature_plan", label: "Literature" },
  { id: "cp4_fba_results", label: "FBA Results" },
  { id: "cp5_report", label: "Report" },
];

/** Ordered steps for the active validation pipeline (all six when mode is unknown). */
export function pipelineStepsForMode(validationMode: string | null): readonly SessionStepId[] {
  if (validationMode === "fba") {
    return ["cp1_spec", "cp2_pathways", "cp3_fba_plan", "cp4_fba_results", "cp5_report"];
  }
  if (validationMode === "literature") {
    return ["cp1_spec", "cp2_pathways", "cp3b_literature_plan", "cp5_report"];
  }
  return SESSION_STEP_IDS;
}

/** Whether a step belongs to the active validation pipeline (for styling and navigation). */
export function stepInPipeline(stepId: string, validationMode: string | null): boolean {
  if (!validationMode) return true;
  return pipelineStepsForMode(validationMode).includes(stepId as SessionStepId);
}

/** 1-based index within the active pipeline, or null when the step is skipped for this session. */
export function pipelineStepOrdinal(
  stepId: string,
  validationMode: string | null
): number | null {
  const idx = pipelineStepsForMode(validationMode).indexOf(stepId as SessionStepId);
  return idx >= 0 ? idx + 1 : null;
}

export function isSessionStepId(stepId: string): stepId is SessionStepId {
  return (SESSION_STEP_IDS as readonly string[]).includes(stepId);
}

/** Next step in the active pipeline after `stepId`, or null at the end. */
export function nextPipelineStep(
  stepId: string,
  validationMode: string | null
): SessionStepId | null {
  const pipeline = pipelineStepsForMode(validationMode);
  const idx = pipeline.indexOf(stepId as SessionStepId);
  if (idx < 0 || idx >= pipeline.length - 1) return null;
  return pipeline[idx + 1];
}
