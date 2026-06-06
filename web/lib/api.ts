/** Browser: same-origin proxy (/api → FastAPI). Server: direct backend URL. */
function apiBase(): string {
  if (typeof window !== "undefined") {
    return process.env.NEXT_PUBLIC_API_URL || "/api";
  }
  return process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
}

export const API_URL = apiBase();

export type Session = {
  id: string;
  title: string;
  raw_brief: string;
  status: string;
  current_step: string;
  validation_mode: string | null;
  agent_active?: boolean;
  created_at: string;
  updated_at: string;
  steps: StepRecord[];
};

export type StepRecord = {
  step_id: string;
  status: string;
  revision_number: number;
  artifact: Record<string, unknown> | null;
  human_decisions: unknown[];
};

export type StreamEvent = {
  type: string;
  step_id?: string;
  node_id?: string;
  content?: string;
  level?: string;
  artifact?: Record<string, unknown>;
  summary?: string;
  message?: string;
  action?: string;
};

export async function listSessions(): Promise<Session[]> {
  const res = await fetch(`${API_URL}/sessions`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to list sessions");
  return res.json();
}

export async function getSession(id: string): Promise<Session> {
  const res = await fetch(`${API_URL}/sessions/${id}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Session not found");
  return res.json();
}

export async function createSession(rawBrief: string, title?: string): Promise<Session> {
  const res = await fetch(`${API_URL}/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ raw_brief: rawBrief, title }),
  });
  if (!res.ok) throw new Error("Failed to create session");
  return res.json();
}

async function parseApiError(res: Response, fallback: string): Promise<string> {
  const body = await res.json().catch(() => ({}));
  const detail = body.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((d: { msg?: string }) => d.msg || "").join(", ") || fallback;
  return fallback;
}

export async function interruptSession(id: string): Promise<void> {
  const res = await fetch(`${API_URL}/sessions/${id}/interrupt`, { method: "POST" });
  if (!res.ok) throw new Error(await parseApiError(res, "Failed to interrupt session"));
}

export async function resumeSession(id: string): Promise<void> {
  const res = await fetch(`${API_URL}/sessions/${id}/resume`, { method: "POST" });
  if (!res.ok) throw new Error(await parseApiError(res, "Failed to resume session"));
}

export async function retrySession(id: string): Promise<Session> {
  const res = await fetch(`${API_URL}/sessions/${id}/retry`, { method: "POST" });
  if (!res.ok) throw new Error(await parseApiError(res, "Failed to retry session"));
  return res.json();
}

export async function getSessionEvents(id: string, afterSeq = 0): Promise<(StreamEvent & { seq: number })[]> {
  const res = await fetch(`${API_URL}/sessions/${id}/events?after_seq=${afterSeq}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to load session events");
  return res.json();
}
export async function deleteSession(id: string): Promise<void> {
  await fetch(`${API_URL}/sessions/${id}`, { method: "DELETE" });
}

export async function restartSessionStep(sessionId: string, stepId: string): Promise<Session> {
  const res = await fetch(`${API_URL}/sessions/${sessionId}/steps/${stepId}/restart`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(await parseApiError(res, "Failed to restart step"));
  return res.json();
}

export async function submitDecision(
  sessionId: string,
  stepId: string,
  body: {
    action: string;
    notes?: string;
    selected_pathway_ids?: string[];
    primary_pathway_id?: string;
  }
): Promise<Session> {
  const res = await fetch(`${API_URL}/sessions/${sessionId}/steps/${stepId}/decide`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await parseApiError(res, "Decision request failed"));
  return res.json();
}

export function streamUrl(sessionId: string, afterSeq = 0): string {
  return `${API_URL}/sessions/${sessionId}/stream?after_seq=${afterSeq}`;
}

export function decideUrl(sessionId: string, stepId: string): string {
  return `${API_URL}/sessions/${sessionId}/steps/${stepId}/decide`;
}
