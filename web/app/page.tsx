import { listSessions, type PaginatedSessions } from "@/lib/api";
import SessionList from "@/components/SessionList";
import { container, pageSubtitle, pageTitle } from "@/lib/ui";

const PAGE_SIZE = 15;

export default async function HomePage({
  searchParams,
}: {
  searchParams: { page?: string };
}) {
  const page = Math.max(1, Number(searchParams.page) || 1);
  let data: PaginatedSessions = { items: [], total: 0, page: 1, page_size: PAGE_SIZE, total_pages: 1 };
  let error: string | undefined;

  try {
    data = await listSessions({ page, pageSize: PAGE_SIZE });
  } catch {
    error = "Could not load sessions. Make sure the API server is running.";
  }

  return (
    <div className={container}>
      <header className="mb-6">
        <h1 className={pageTitle}>Sessions</h1>
        <p className={pageSubtitle}>Computationally validated pathway blueprints</p>
      </header>
      <SessionList
        sessions={data.items}
        page={data.page}
        totalPages={data.total_pages}
        total={data.total}
        pageSize={data.page_size}
        error={error}
      />
    </div>
  );
}
