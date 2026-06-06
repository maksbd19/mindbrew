import { keggCompoundLink } from "@/lib/bioLinks";
import { cn, link } from "@/lib/ui";
import ArtifactPanel, { DetailRow } from "./ArtifactPanel";

function formatOrganism(organism: unknown): string {
  if (Array.isArray(organism)) return organism.join(", ");
  if (typeof organism === "string") return organism;
  if (organism == null) return "—";
  return JSON.stringify(organism);
}

function gatekeeperTone(verdict: unknown): "success" | "warning" | "danger" | "neutral" {
  const v = String(verdict || "").toUpperCase();
  if (v === "PROCEED") return "success";
  if (v === "CLARIFY") return "warning";
  if (v === "REJECT") return "danger";
  return "neutral";
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
  const gatekeeper = brief.gatekeeper_verdict;
  const tone = gatekeeperTone(gatekeeper);

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
            {String(gemProfile.gem_id || gemProfile.model_ref || "—")}
          </DetailRow>
        )}
      </dl>

      {gemSelectionReason && (
        <p className="mt-4 rounded-md border border-border-subtle bg-surface-raised px-3 py-2.5 text-[13px] leading-relaxed text-muted-light">
          <span className="font-medium text-foreground">GEM selection: </span>
          {gemSelectionReason}
        </p>
      )}

      {gatekeeper != null && (
        <div
          className={cn(
            "mt-4 rounded-md border px-3 py-2.5",
            tone === "success" && "border-emerald-900/50 bg-emerald-950/20",
            tone === "warning" && "border-amber-900/50 bg-amber-950/20",
            tone === "danger" && "border-red-900/50 bg-red-950/20",
            tone === "neutral" && "border-border-subtle bg-surface-raised"
          )}
        >
          <span className="text-[12px] font-medium uppercase tracking-wide text-muted">Gatekeeper</span>
          <p
            className={cn(
              "mt-1 text-[14px] font-semibold",
              tone === "success" && "text-emerald-300",
              tone === "warning" && "text-amber-300",
              tone === "danger" && "text-red-300",
              tone === "neutral" && "text-foreground"
            )}
          >
            {String(gatekeeper)}
          </p>
        </div>
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
