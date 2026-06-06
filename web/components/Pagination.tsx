import Link from "next/link";
import { cn } from "@/lib/ui";

type PaginationProps = {
  page: number;
  totalPages: number;
  total: number;
  pageSize: number;
};

function pageHref(page: number): string {
  return page <= 1 ? "/" : `/?page=${page}`;
}

function visiblePages(current: number, total: number): (number | "ellipsis")[] {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);

  const pages: (number | "ellipsis")[] = [1];
  const start = Math.max(2, current - 1);
  const end = Math.min(total - 1, current + 1);

  if (start > 2) pages.push("ellipsis");
  for (let i = start; i <= end; i++) pages.push(i);
  if (end < total - 1) pages.push("ellipsis");
  pages.push(total);

  return pages;
}

export default function Pagination({ page, totalPages, total, pageSize }: PaginationProps) {
  if (totalPages <= 1) return null;

  const start = (page - 1) * pageSize + 1;
  const end = Math.min(page * pageSize, total);

  return (
    <div className="flex flex-col gap-3 border-t border-border-subtle px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
      <p className="text-[13px] text-muted">
        Showing <span className="font-medium text-foreground">{start}–{end}</span> of{" "}
        <span className="font-medium text-foreground">{total}</span>
      </p>

      <nav aria-label="Pagination" className="flex items-center gap-1">
        {page > 1 ? (
          <Link
            href={pageHref(page - 1)}
            className="inline-flex h-8 items-center rounded-md border border-border px-3 text-[13px] text-muted transition-colors hover:border-border hover:bg-surface-hover hover:text-foreground"
          >
            Previous
          </Link>
        ) : (
          <span className="inline-flex h-8 cursor-not-allowed items-center rounded-md border border-border-subtle px-3 text-[13px] text-muted/50">
            Previous
          </span>
        )}

        <div className="hidden items-center gap-1 sm:flex">
          {visiblePages(page, totalPages).map((p, i) =>
            p === "ellipsis" ? (
              <span key={`e-${i}`} className="px-2 text-[13px] text-muted">
                …
              </span>
            ) : (
              <Link
                key={p}
                href={pageHref(p)}
                aria-current={p === page ? "page" : undefined}
                className={cn(
                  "inline-flex h-8 min-w-8 items-center justify-center rounded-md px-2.5 text-[13px] transition-colors",
                  p === page
                    ? "bg-primary text-white"
                    : "text-muted hover:bg-surface-hover hover:text-foreground"
                )}
              >
                {p}
              </Link>
            )
          )}
        </div>

        {page < totalPages ? (
          <Link
            href={pageHref(page + 1)}
            className="inline-flex h-8 items-center rounded-md border border-border px-3 text-[13px] text-muted transition-colors hover:border-border hover:bg-surface-hover hover:text-foreground"
          >
            Next
          </Link>
        ) : (
          <span className="inline-flex h-8 cursor-not-allowed items-center rounded-md border border-border-subtle px-3 text-[13px] text-muted/50">
            Next
          </span>
        )}
      </nav>
    </div>
  );
}
