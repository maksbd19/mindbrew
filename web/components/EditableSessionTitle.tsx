"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { cn, inputBase, pageTitle } from "@/lib/ui";

export default function EditableSessionTitle({
  title,
  suggesting = false,
  disabled = false,
  onSave,
}: {
  title: string;
  suggesting?: boolean;
  disabled?: boolean;
  onSave: (title: string) => Promise<void>;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(title);
  const [saving, setSaving] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!editing) setDraft(title);
  }, [title, editing]);

  useEffect(() => {
    if (editing) inputRef.current?.focus();
  }, [editing]);

  const startEditing = useCallback(() => {
    if (disabled || saving || suggesting) return;
    setDraft(title);
    setEditing(true);
  }, [disabled, saving, suggesting, title]);

  const cancelEditing = useCallback(() => {
    setDraft(title);
    setEditing(false);
  }, [title]);

  const commit = useCallback(async () => {
    const next = draft.trim();
    if (!next || next === title.trim()) {
      cancelEditing();
      return;
    }
    setSaving(true);
    try {
      await onSave(next);
      setEditing(false);
    } catch {
      /* parent surfaces errors */
    } finally {
      setSaving(false);
    }
  }, [cancelEditing, draft, onSave, title]);

  const displayTitle = title.trim() || "Session";

  if (editing) {
    return (
      <input
        ref={inputRef}
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={() => void commit()}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            void commit();
          }
          if (e.key === "Escape") {
            e.preventDefault();
            cancelEditing();
          }
        }}
        disabled={saving}
        maxLength={255}
        aria-label="Session title"
        className={cn(
          inputBase,
          pageTitle,
          "min-w-0 flex-1 border-transparent bg-transparent px-1 py-0 shadow-none focus:border-primary"
        )}
      />
    );
  }

  return (
    <div className="flex min-w-0 flex-1 items-center gap-2">
      <button
        type="button"
        onClick={startEditing}
        disabled={disabled || saving || suggesting}
        title="Click to edit title"
        className={cn(
          pageTitle,
          "group min-w-0 truncate rounded-md px-1 py-0.5 text-left transition-colors",
          "hover:bg-surface-raised focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50",
          (disabled || saving || suggesting) && "cursor-default hover:bg-transparent"
        )}
      >
        {displayTitle}
        {!disabled && !saving && !suggesting && (
          <span className="ml-2 text-[12px] font-normal text-muted opacity-0 transition-opacity group-hover:opacity-100">
            Edit
          </span>
        )}
      </button>
      {suggesting && (
        <span className="shrink-0 text-[12px] text-muted">Generating title…</span>
      )}
    </div>
  );
}
