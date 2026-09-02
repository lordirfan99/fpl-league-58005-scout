import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const API_BASE = (process.env.FPL_API_BASE_URL ?? "https://fpl-scout-api-bztsnhv3ea-uc.a.run.app").replace(/\/$/, "");
const allowed = new Set(["status", "actions", "emergency-lock"]);

async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  const key = path.join("/");
  if (!allowed.has(key)) return NextResponse.json({ error: "not_found" }, { status: 404 });
  const authorization = request.headers.get("authorization");
  if (!authorization) return NextResponse.json({ error: "owner_authentication_required" }, { status: 401 });
  const response = await fetch(`${API_BASE}/v3/control/${key}`, {
    method: request.method,
    headers: { authorization, "content-type": "application/json" },
    body: request.method === "GET" ? undefined : await request.text(),
    cache: "no-store",
  });
  return new NextResponse(await response.text(), {
    status: response.status,
    headers: { "content-type": response.headers.get("content-type") ?? "application/json", "cache-control": "no-store" },
  });
}

export const GET = proxy;
export const POST = proxy;
