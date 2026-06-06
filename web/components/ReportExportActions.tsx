"use client";

import { useState } from "react";
import { downloadReportExport } from "@/lib/api";
import { btnSecondary, cn } from "@/lib/ui";

export default function ReportExportActions({ sessionId }: { sessionId: string }) {
  const [busyFormat, setBusyFormat] = useState<"pdf" | "docx" | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleExport(format: "pdf" | "docx") {
    setBusyFormat(format);
    setError(null);
    try {
      await downloadReportExport(sessionId, format);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export failed");
    } finally {
      setBusyFormat(null);
    }
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <div className="flex flex-wrap items-center justify-end gap-2">
        <button
          type="button"
          className={cn(btnSecondary, "h-8 px-3 text-[12px]")}
          disabled={busyFormat !== null}
          onClick={() => void handleExport("pdf")}
        >
          {busyFormat === "pdf" ? "Exporting…" : "Download PDF"}
        </button>
        <button
          type="button"
          className={cn(btnSecondary, "h-8 px-3 text-[12px]")}
          disabled={busyFormat !== null}
          onClick={() => void handleExport("docx")}
        >
          {busyFormat === "docx" ? "Exporting…" : "Download Word"}
        </button>
      </div>
      {error && <p className="m-0 text-[12px] text-danger">{error}</p>}
    </div>
  );
}
