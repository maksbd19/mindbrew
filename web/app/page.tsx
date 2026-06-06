import Link from "next/link";
import { listSessions, type Session } from "@/lib/api";
import SessionList from "@/components/SessionList";
import { btnPrimary, container } from "@/lib/ui";

export default async function HomePage() {
  let sessions: Session[] = [];
  try {
    sessions = await listSessions();
  } catch {
    sessions = [];
  }

  return (
    <div className={container}>
      <header className="mb-6 flex items-center justify-between gap-4">
        <div>
          <h1 className="m-0 text-2xl font-semibold">Brewmind</h1>
          <p className="mt-1 text-muted">Computationally validated pathway blueprints</p>
        </div>
        <Link href="/sessions/new" className={btnPrimary}>
          New session
        </Link>
      </header>
      <SessionList sessions={sessions} />
    </div>
  );
}
