import { NextRequest } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function backendBase(): string {
  return process.env.API_URL || "http://127.0.0.1:8000";
}

export async function GET(
  req: NextRequest,
  { params }: { params: { sessionId: string } }
) {
  const afterSeq = req.nextUrl.searchParams.get("after_seq") ?? "0";
  const target = `${backendBase()}/sessions/${params.sessionId}/stream?after_seq=${afterSeq}`;

  const upstream = await fetch(target, {
    headers: { Accept: "text/event-stream" },
    cache: "no-store",
  });

  if (!upstream.body) {
    return new Response(null, {
      status: upstream.status,
      statusText: upstream.statusText,
    });
  }

  return new Response(upstream.body, {
    status: upstream.status,
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}
