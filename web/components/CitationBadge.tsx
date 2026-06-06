import { citationUrl, type Citation } from "@/lib/bioLinks";
import { citationStatusColor, cn, link } from "@/lib/ui";

const STATUS_ICON: Record<string, string> = {
  verified: "✓",
  unverified: "⚠",
  invalid: "✗",
};

export default function CitationBadge({ citation }: { citation: Citation }) {
  const url = citationUrl(citation);
  const status = citation.validation_status ?? "unverified";
  const label =
    citation.title ||
    (citation.doi ? `DOI ${citation.doi}` : citation.pmid ? `PMID ${citation.pmid}` : "Citation");
  const meta = [citation.authors, citation.journal, citation.year].filter(Boolean).join(", ");

  return (
    <div className="mb-1.5 text-sm">
      <span className={cn("mr-1.5", citationStatusColor(status))}>{STATUS_ICON[status] ?? "?"}</span>
      {url ? (
        <a href={url} target="_blank" rel="noopener noreferrer" className={link}>
          {label}
        </a>
      ) : (
        <span>{label}</span>
      )}
      {meta && <span className="ml-1.5 text-muted">— {meta}</span>}
      {status !== "verified" && (
        <span className={cn("ml-1.5 text-xs", citationStatusColor(status))}>({status})</span>
      )}
      {citation.snippet && (
        <div className="mt-0.5 text-xs text-muted">{citation.snippet}</div>
      )}
    </div>
  );
}
