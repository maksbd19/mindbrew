import { keggCompoundLink } from "@/lib/bioLinks";
import { link } from "@/lib/ui";
import { formatDisplayPath } from "@/lib/format";
import ArtifactPanel, { DetailRow } from "./ArtifactPanel";

function formatOrganism(organism: unknown): string {
  if (Array.isArray(organism)) return organism.join(", ");
  if (typeof organism === "string") return organism;
  if (organism == null) return "—";
  return JSON.stringify(organism);
}

export default function SpecView({
  brief,
  validationMode,
  gemProfile,
  gemSelectionReason,
}: {
  brief: Record<string, unknown>;
  validationMode?: string;
  gemProfile?: Record<string, unknown> | null;
  gemSelectionReason?: string;
}) {
  const feedstock = brief.feedstock as Record<string, unknown> | undefined;
  const target = brief.target as Record<string, unknown> | undefined;
  const feedstockLink = keggCompoundLink(feedstock?.kegg_id as string | undefined);
  const targetLink = keggCompoundLink(target?.kegg_id as string | undefined);

  return (
    <ArtifactPanel title="Research brief" subtitle="Parsed specification from your R&D ticket">
      <dl>
        <DetailRow label="Target function">{String(brief.target_function || "—")}</DetailRow>
        <DetailRow label="Organism">{formatOrganism(brief.organism)}</DetailRow>
        <DetailRow label="Feedstock">
          {String(feedstock?.name || feedstock?.class || "—")}
          {feedstockLink && (
            <>
              {" "}
              <a href={feedstockLink.url} target="_blank" rel="noopener noreferrer" className={link}>
                {feedstockLink.label}
              </a>
            </>
          )}
        </DetailRow>
        <DetailRow label="Target product">
          {String(target?.name || target?.class || "—")}
          {targetLink && (
            <>
              {" "}
              <a href={targetLink.url} target="_blank" rel="noopener noreferrer" className={link}>
                {targetLink.label}
              </a>
            </>
          )}
        </DetailRow>
        <DetailRow label="Validation">{String(validationMode || "pending")}</DetailRow>
        {gemProfile && (
          <DetailRow label="GEM model">
            {String(gemProfile.gem_id || formatDisplayPath(gemProfile.model_ref) || "—")}
          </DetailRow>
        )}
      </dl>

      {gemSelectionReason && (
        <p className="mt-4 rounded-md border border-border-subtle bg-surface-raised px-3 py-2.5 text-[13px] leading-relaxed text-muted-light">
          <span className="font-medium text-foreground">GEM selection: </span>
          {gemSelectionReason}
        </p>
      )}

      {Array.isArray(brief.clarifying_questions) && brief.clarifying_questions.length > 0 && (
        <div className="mt-4 rounded-md border border-red-900/40 bg-red-950/20 px-3 py-3">
          <p className="text-[12px] font-medium uppercase tracking-wide text-red-300">Clarifications needed</p>
          <ul className="mt-2 space-y-1.5 text-[13px] text-red-200">
            {(brief.clarifying_questions as string[]).map((q) => (
              <li key={q} className="flex gap-2">
                <span className="text-red-400">•</span>
                <span>{q}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </ArtifactPanel>
  );
}
