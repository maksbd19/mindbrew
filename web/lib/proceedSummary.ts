import { formatStepLabel } from "@/lib/format";
import { nextPipelineStep } from "@/lib/steps";

type ProceedAction = {
  label: string;
  summary: string | null;
};

function compoundLabel(spec: unknown): string | null {
  if (!spec || typeof spec !== "object") return null;
  const record = spec as Record<string, unknown>;
  const name = String(record.name || record.class || "").trim();
  return name || null;
}

function formatOrganism(organism: unknown): string | null {
  if (Array.isArray(organism)) {
    const names = organism.map(String).filter(Boolean);
    return names.length > 0 ? names.join(", ") : null;
  }
  if (typeof organism === "string" && organism.trim()) return organism.trim();
  return null;
}

function pathwayName(
  candidates: unknown,
  pathwayId: string | null | undefined
): string | null {
  if (!pathwayId || !Array.isArray(candidates)) return null;
  const match = candidates.find(
    (item): item is { id: string; name?: string } =>
      Boolean(item && typeof item === "object" && "id" in item && item.id === pathwayId)
  );
  return match ? String(match.name || match.id) : pathwayId;
}

function joinParts(parts: Array<string | null | undefined>): string | null {
  const filtered = parts.map((part) => part?.trim()).filter(Boolean) as string[];
  return filtered.length > 0 ? filtered.join(" · ") : null;
}

/** One-line summary of the artifact at the current checkpoint. */
export function checkpointArtifactSummary(
  stepId: string,
  artifact: Record<string, unknown> | null | undefined,
  opts?: {
    selectedPathwayId?: string | null;
    validationMode?: string | null;
  }
): string | null {
  if (!artifact) return null;

  switch (stepId) {
    case "cp1_spec": {
      const brief = artifact.brief as Record<string, unknown> | undefined;
      if (!brief) return null;
      const target = compoundLabel(brief.target);
      const feedstock = compoundLabel(brief.feedstock);
      const organism = formatOrganism(brief.organism);
      const mode = String(artifact.validation_mode || opts?.validationMode || "").trim();
      return joinParts([
        target && feedstock ? `${target} from ${feedstock}` : target || feedstock,
        organism,
        mode ? `${mode} validation` : null,
      ]);
    }
    case "cp2_pathways": {
      const candidates = artifact.pathway_candidates;
      const count = Array.isArray(candidates) ? candidates.length : 0;
      const selected = pathwayName(candidates, opts?.selectedPathwayId);
      return joinParts([
        count > 0 ? `${count} pathway${count === 1 ? "" : "s"} found` : null,
        selected ? `selected: ${selected}` : null,
      ]);
    }
    case "cp3_fba_plan": {
      const payloads = artifact.score_payloads;
      const skipped = artifact.skipped;
      const payloadCount = Array.isArray(payloads) ? payloads.length : 0;
      const skippedCount = Array.isArray(skipped) ? skipped.length : 0;
      const gemProfile = artifact.gem_profile as Record<string, unknown> | undefined;
      const gem = gemProfile
        ? String(gemProfile.gem_id || gemProfile.model_name || "").trim()
        : null;
      return joinParts([
        payloadCount > 0
          ? `${payloadCount} FBA payload${payloadCount === 1 ? "" : "s"} ready`
          : "No FBA payloads",
        gem ? `GEM ${gem}` : null,
        skippedCount > 0 ? `${skippedCount} skipped` : null,
      ]);
    }
    case "cp3b_literature_plan": {
      const plan = artifact.literature_plan as Record<string, unknown> | undefined;
      if (!plan) return null;
      const genes = Array.isArray(plan.gene_suggestions) ? plan.gene_suggestions.length : 0;
      const risks = Array.isArray(plan.known_risks) ? plan.known_risks.length : 0;
      const pathway = String(plan.pathway_name || plan.pathway_id || "").trim();
      return joinParts([
        pathway || null,
        genes > 0 ? `${genes} gene edit${genes === 1 ? "" : "s"}` : null,
        risks > 0 ? `${risks} known risk${risks === 1 ? "" : "s"}` : null,
      ]);
    }
    case "cp4_fba_results": {
      const results = artifact.fba_results;
      if (!Array.isArray(results) || results.length === 0) return null;
      const ranked = [...results].sort(
        (a, b) =>
          Number((a as { rank?: number }).rank ?? 999) -
          Number((b as { rank?: number }).rank ?? 999)
      );
      const top = ranked[0] as {
        verdict?: string;
        yield_corrected_mol_per_mol_substrate?: number;
        pathway_id?: string;
      };
      const verdictCounts = results.reduce<Record<string, number>>((acc, item) => {
        const verdict = String((item as { verdict?: string }).verdict || "unknown");
        acc[verdict] = (acc[verdict] || 0) + 1;
        return acc;
      }, {});
      const verdictSummary = Object.entries(verdictCounts)
        .map(([verdict, count]) => `${count} ${verdict}`)
        .join(", ");
      const yieldPart =
        top.yield_corrected_mol_per_mol_substrate != null
          ? `${top.yield_corrected_mol_per_mol_substrate} mol/mol`
          : null;
      return joinParts([
        `${results.length} pathway${results.length === 1 ? "" : "s"} scored`,
        verdictSummary,
        top.verdict && yieldPart ? `top: ${top.verdict} (${yieldPart})` : top.verdict ? `top: ${top.verdict}` : null,
      ]);
    }
    case "cp5_report": {
      const report = artifact.report as { markdown?: string } | undefined;
      if (!report?.markdown) return null;
      const sectionCount = (report.markdown.match(/^## \d+\./gm) || []).length;
      return joinParts([
        "CRO report ready",
        sectionCount > 0 ? `Executive summary + ${sectionCount} proposal sections` : null,
      ]);
    }
    default:
      return null;
  }
}

export function proceedActionLabel(
  currentStepId: string,
  validationMode: string | null,
  artifact: Record<string, unknown> | null | undefined,
  opts?: {
    selectedPathwayId?: string | null;
  }
): ProceedAction {
  const nextStep = nextPipelineStep(currentStepId, validationMode);
  const summary = checkpointArtifactSummary(currentStepId, artifact, {
    selectedPathwayId: opts?.selectedPathwayId,
    validationMode,
  });

  if (currentStepId === "cp5_report") {
    return { label: "Approve report", summary };
  }

  const label = nextStep ? `Proceed to ${formatStepLabel(nextStep)}` : "Proceed";
  return { label, summary };
}

export function pathwayProceedActionLabel(
  validationMode: string | null,
  artifact: Record<string, unknown> | null | undefined,
  opts: {
    selectedPathwayId?: string | null;
    isActiveStep: boolean;
    selectionChanged: boolean;
  }
): ProceedAction {
  const nextStep = nextPipelineStep("cp2_pathways", validationMode);
  const summary = checkpointArtifactSummary("cp2_pathways", artifact, {
    selectedPathwayId: opts.selectedPathwayId,
    validationMode,
  });

  if (!opts.isActiveStep) {
    return {
      label: nextStep ? `Re-run from ${formatStepLabel(nextStep)}` : "Re-run analysis",
      summary: joinParts([
        summary,
        opts.selectionChanged ? "pathway changed since last run" : null,
      ]),
    };
  }

  return {
    label: nextStep ? `Proceed to ${formatStepLabel(nextStep)}` : "Proceed",
    summary,
  };
}
