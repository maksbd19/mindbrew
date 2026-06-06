import type { ReactNode } from "react";
import Link from "next/link";
import { btnPrimary, cn } from "@/lib/ui";

export default function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-50 border-b border-border-subtle bg-page/80 backdrop-blur-md">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between gap-4 px-6">
          <Link href="/" className="group flex items-center gap-2.5">
            <span className="flex h-7 w-7 items-center justify-center rounded-md bg-primary/15 text-sm font-semibold text-accent">
              M
            </span>
            <span className="text-[15px] font-semibold tracking-tight text-foreground group-hover:text-accent transition-colors">
              Mindbrew
            </span>
          </Link>
          <Link href="/sessions/new" className={cn(btnPrimary, "h-8 px-3.5 text-[13px]")}>
            New session
          </Link>
        </div>
      </header>
      <main className="w-full overflow-x-hidden">{children}</main>
    </div>
  );
}
