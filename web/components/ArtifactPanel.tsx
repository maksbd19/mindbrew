import { cn, card, cardTitle } from "@/lib/ui";

export default function ArtifactPanel({
  title,
  subtitle,
  headerActions,
  children,
  className,
  bodyClassName,
  noPadding,
}: {
  title: string;
  subtitle?: string;
  headerActions?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  bodyClassName?: string;
  noPadding?: boolean;
}) {
  return (
    <section className={cn(card, "overflow-x-hidden", className)}>
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-border-subtle px-5 py-4">
        <div className="min-w-0">
          <h2 className={cardTitle}>{title}</h2>
          {subtitle && <p className="mt-0.5 text-[13px] text-muted">{subtitle}</p>}
        </div>
        {headerActions}
      </div>
      <div className={cn(!noPadding && "px-5 py-4", bodyClassName)}>{children}</div>
    </section>
  );
}

export function DetailRow({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="grid grid-cols-1 gap-1 border-b border-border-subtle py-3 last:border-b-0 sm:grid-cols-[10rem_1fr] sm:gap-6">
      <dt className="text-[12px] font-medium uppercase tracking-wide text-muted">{label}</dt>
      <dd className="min-w-0 break-words text-[14px] leading-relaxed text-foreground">{children}</dd>
    </div>
  );
}

export function ArtifactSection({
  title,
  children,
  className,
}: {
  title: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={cn("mt-6 first:mt-0", className)}>
      <h3 className="mb-3 text-[13px] font-semibold text-foreground">{title}</h3>
      {children}
    </section>
  );
}

export function MetricChip({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: React.ReactNode;
  tone?: "neutral" | "success" | "warning" | "danger";
}) {
  const toneClass =
    tone === "success"
      ? "border-emerald-900/50 bg-emerald-950/30 text-emerald-300"
      : tone === "warning"
        ? "border-amber-900/50 bg-amber-950/30 text-amber-300"
        : tone === "danger"
          ? "border-red-900/50 bg-red-950/30 text-red-300"
          : "border-border bg-surface-raised text-muted-light";

  return (
    <div className={cn("rounded-md border px-3 py-2", toneClass)}>
      <div className="text-[10px] font-medium uppercase tracking-wide opacity-70">{label}</div>
      <div className="mt-0.5 text-[13px] font-medium capitalize">{value}</div>
    </div>
  );
}
