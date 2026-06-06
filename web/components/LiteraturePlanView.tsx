import type { GeneSuggestion, LiteraturePlan } from "@/lib/bioLinks";
import { cn } from "@/lib/ui";
import ArtifactPanel, { ArtifactSection } from "./ArtifactPanel";
import CitationBadge from "./CitationBadge";
import EnzymeChip from "./EnzymeChip";

function actionTone(action: string): "neutral" | "warning" | "success" {
  switch (action.toLowerCase()) {
    case "knockout":
      return "warning";
    case "heterologous":
      return "success";
    default:
      return "neutral";
  }
}

function actionLabel(action: string): string {
  return action.replace(/_/g, " ");
}

function ActionBadge({ action }: { action: string }) {
  const tone = actionTone(action);
  const toneClass =
    tone === "warning"
      ? "border-amber-900/50 bg-amber-950/30 text-amber-300"
      : tone === "success"
        ? "border-primary/40 bg-primary/10 text-accent"
        : "border-border-subtle bg-surface text-muted-light";

  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center rounded-full border px-2.5 py-1 text-[11px] font-medium uppercase tracking-wide",
        toneClass
      )}
    >
      {actionLabel(action)}
    </span>
  );
}

function GeneSuggestionCard({
  suggestion,
  organism,
}: {
  suggestion: GeneSuggestion;
  organism: string | null;
}) {
  return (
    <article className="overflow-hidden rounded-lg border border-border-subtle bg-surface-raised/40 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <EnzymeChip name={suggestion.gene} organism={organism} />
        <ActionBadge action={suggestion.action} />
      </div>

      {suggestion.rationale && (
        <p className="mt-3 text-[14px] leading-relaxed text-muted-light">{suggestion.rationale}</p>
      )}

      <div className="mt-4 border-t border-border-subtle pt-3">
        {suggestion.citation ? (
          <CitationBadge citation={suggestion.citation} />
        ) : (
          <span className="text-[12px] text-danger">No citation</span>
        )}
      </div>
    </article>
  );
}

export default function LiteraturePlanView({
  plan,
  organism,
}: {
  plan: LiteraturePlan;
  organism?: string[];
}) {
  const org = organism?.[0] ?? null;

  return (
    <ArtifactPanel title="Literature pathway plan" subtitle={plan.pathway_name}>
      {(plan.reaction_map ?? []).length > 0 && (
        <ArtifactSection title="Reaction map">
          <ol className="space-y-2 pl-0">
            {(plan.reaction_map ?? []).map((s) => (
              <li
                key={s.step_number}
                className="rounded-md border border-border-subtle bg-surface-raised/50 px-3 py-2.5 text-[13px]"
              >
                <span className="text-foreground">{s.description}</span>
                <div className="mt-1.5 flex flex-wrap gap-1">
                  {(s.gene_names ?? []).map((g) => (
                    <EnzymeChip key={g} name={g} ec={s.enzyme_ec} enzymeName={s.enzyme_name} organism={org} />
                  ))}
                </div>
              </li>
            ))}
          </ol>
        </ArtifactSection>
      )}

      {(plan.gene_suggestions ?? []).length > 0 && (
        <ArtifactSection title="Gene suggestions">
          <div className="space-y-3">
            {(plan.gene_suggestions ?? []).map((g) => (
              <GeneSuggestionCard key={g.gene} suggestion={g} organism={org} />
            ))}
          </div>
        </ArtifactSection>
      )}

      {(plan.citations ?? []).length > 0 && (
        <ArtifactSection title="Pathway references">
          <div className="space-y-1">
            {(plan.citations ?? []).map((c, i) => (
              <CitationBadge key={`plan-cit-${i}`} citation={c} />
            ))}
          </div>
        </ArtifactSection>
      )}

      {(["known_risks", "gaps", "next_steps"] as const).map((key) => {
        const items = plan[key] as string[] | undefined;
        if (!items?.length) return null;
        const label = key.replace(/_/g, " ");
        return (
          <ArtifactSection key={key} title={label.charAt(0).toUpperCase() + label.slice(1)}>
            <ul className="space-y-1.5 text-[13px] text-muted-light">
              {items.map((item) => (
                <li key={item} className="flex gap-2">
                  <span className="text-muted">•</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </ArtifactSection>
        );
      })}
    </ArtifactPanel>
  );
}
