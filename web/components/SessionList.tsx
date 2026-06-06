import Link from "next/link";
import type { SessionSummary } from "@/lib/api";
import { formatFullDate, formatRelativeDate, formatStatusLabel, formatStepLabel } from "@/lib/format";
import { card, dataTable, dataTableCell, dataTableHead, pageSubtitle, statusChipClass } from "@/lib/ui";
import Pagination from "@/components/Pagination";

type SessionListProps = {
  sessions: SessionSummary[];
  page: number;
  totalPages: number;
  total: number;
  pageSize: number;
  error?: string;
};

export default function SessionList({
  sessions,
  page,
  totalPages,
  total,
  pageSize,
  error,
}: SessionListProps) {
  if (error) {
    return (
      <div className={`${card} p-6`}>
        <p className="text-[14px] text-danger">{error}</p>
      </div>
    );
  }

  if (!total) {
    return (
      <div className={`${card} flex flex-col items-center px-6 py-16 text-center`}>
        <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-surface-raised text-xl text-muted">
          ◎
        </div>
        <h2 className="text-[15px] font-semibold text-foreground">No sessions yet</h2>
        <p className={pageSubtitle}>Create your first session to start building pathway blueprints.</p>
        <Link
          href="/sessions/new"
          className="mt-6 inline-flex h-9 items-center rounded-md bg-primary px-4 text-[13px] font-medium text-white transition-colors hover:bg-primary-hover"
        >
          New session
        </Link>
      </div>
    );
  }

  return (
    <div className={card}>
      <div className="border-b border-border-subtle px-5 py-4">
        <h2 className="text-[15px] font-semibold text-foreground">Sessions</h2>
        <p className="mt-0.5 text-[13px] text-muted">
          {total} session{total === 1 ? "" : "s"} total
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className={dataTable}>
          <thead>
            <tr className="bg-surface-raised/50">
              <th className={dataTableHead}>Title</th>
              <th className={dataTableHead}>Status</th>
              <th className={dataTableHead}>Step</th>
              <th className={dataTableHead}>Updated</th>
            </tr>
          </thead>
          <tbody>
            {sessions.map((s) => (
              <tr
                key={s.id}
                className="group border-b border-border-subtle last:border-b-0 transition-colors hover:bg-surface-hover"
              >
                <td className={dataTableCell}>
                  <Link href={`/sessions/${s.id}`} className="block min-w-[240px]">
                    <span className="font-medium text-foreground transition-colors group-hover:text-accent">
                      {s.title}
                    </span>
                    {s.brief_preview && (
                      <p className="mt-0.5 line-clamp-1 text-[13px] text-muted">{s.brief_preview}</p>
                    )}
                  </Link>
                </td>
                <td className={dataTableCell}>
                  <span className={statusChipClass(s.status)}>{formatStatusLabel(s.status)}</span>
                </td>
                <td className={`${dataTableCell} text-[13px] text-muted-light`}>
                  {formatStepLabel(s.current_step)}
                </td>
                <td className={`${dataTableCell} whitespace-nowrap text-[13px] text-muted`}>
                  <time dateTime={s.updated_at} title={formatFullDate(s.updated_at)}>
                    {formatRelativeDate(s.updated_at)}
                  </time>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Pagination page={page} totalPages={totalPages} total={total} pageSize={pageSize} />
    </div>
  );
}
