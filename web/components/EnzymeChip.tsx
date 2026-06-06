import { ecLink, geneLink } from "@/lib/bioLinks";
import { cn, link } from "@/lib/ui";

export default function EnzymeChip({
  name,
  ec,
  organism,
  enzymeName,
}: {
  name: string;
  ec?: string | null;
  organism?: string | null;
  enzymeName?: string | null;
}) {
  const kegg = ec ? ecLink(ec) : null;
  const uniprot = geneLink(name, organism);
  const title = enzymeName ? `${name} — ${enzymeName}` : name;

  return (
    <span
      className="mr-1 mt-0.5 inline-block rounded border border-enzyme-border bg-enzyme-bg px-1.5 py-0.5 text-[0.78rem]"
      title={title}
    >
      {name}
      {ec && <span className="ml-1 text-[0.7rem] text-muted">EC {ec}</span>}
      {kegg && (
        <a href={kegg.url} target="_blank" rel="noopener noreferrer" className={cn(link, "ml-1 text-[0.72rem]")}>
          {kegg.label}
        </a>
      )}
      {uniprot && (
        <a href={uniprot.url} target="_blank" rel="noopener noreferrer" className={cn(link, "ml-1 text-[0.72rem]")}>
          {uniprot.label}
        </a>
      )}
    </span>
  );
}
