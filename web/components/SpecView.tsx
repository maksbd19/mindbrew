import { keggCompoundLink } from "@/lib/bioLinks";
import { card, cardTitle, link } from "@/lib/ui";

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
    <div className={card}>
      <h3 className={cardTitle}>Research brief</h3>
      <p>
        <strong>Target function:</strong> {String(brief.target_function || "")}
      </p>
      <p>
        <strong>Organism:</strong> {JSON.stringify(brief.organism)}
      </p>
      <p>
        <strong>Feedstock:</strong> {String(feedstock?.name || feedstock?.class || "")}
        {feedstockLink && (
          <>
            {" "}
            <a href={feedstockLink.url} target="_blank" rel="noopener noreferrer" className={link}>
              {feedstockLink.label}
            </a>
          </>
        )}
      </p>
      <p>
        <strong>Target:</strong> {String(target?.name || target?.class || "")}
        {targetLink && (
          <>
            {" "}
            <a href={targetLink.url} target="_blank" rel="noopener noreferrer" className={link}>
              {targetLink.label}
            </a>
          </>
        )}
      </p>
      <p>
        <strong>Validation:</strong> {String(validationMode || "pending")}
      </p>
      {gemProfile && (
        <p>
          <strong>GEM:</strong> {String(gemProfile.gem_id || gemProfile.model_ref || "")}
        </p>
      )}
      {gemSelectionReason && (
        <p className="text-sm text-muted">
          <strong>GEM selection:</strong> {gemSelectionReason}
        </p>
      )}
      {brief.gatekeeper_verdict != null && (
        <p>
          <strong>Gatekeeper:</strong>{" "}
          <span className={brief.gatekeeper_verdict === "PROCEED" ? "text-accent" : "text-danger"}>
            {String(brief.gatekeeper_verdict)}
          </span>
        </p>
      )}
      {Array.isArray(brief.clarifying_questions) && brief.clarifying_questions.length > 0 && (
        <ul className="text-sm text-danger">
          {(brief.clarifying_questions as string[]).map((q) => (
            <li key={q}>{q}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
