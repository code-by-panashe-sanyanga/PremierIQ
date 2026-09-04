import { NextRequest } from "next/server";

export const dynamic = "force-dynamic";

function apiBase() {
  return (process.env.API_INTERNAL_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
}

async function proxy(req: NextRequest, path: string[]) {
  const target = new URL(`${apiBase()}/api/${path.join("/")}`);
  target.search = req.nextUrl.search;

  const headers = new Headers();
  const accept = req.headers.get("accept");
  const contentType = req.headers.get("content-type");
  if (accept) headers.set("accept", accept);
  if (contentType) headers.set("content-type", contentType);

  const init: RequestInit = { method: req.method, headers, redirect: "manual" };
  if (req.method !== "GET" && req.method !== "HEAD") {
    init.body = await req.arrayBuffer();
  }

  const upstream = await fetch(target, init);
  const out = new Headers();
  const pass = ["content-type", "cache-control"];
  for (const key of pass) {
    const value = upstream.headers.get(key);
    if (value) out.set(key, value);
  }
  return new Response(upstream.body, { status: upstream.status, headers: out });
}

type Ctx = { params: Promise<{ path: string[] }> };

export async function GET(req: NextRequest, ctx: Ctx) {
  return proxy(req, (await ctx.params).path);
}

export async function POST(req: NextRequest, ctx: Ctx) {
  return proxy(req, (await ctx.params).path);
}

export async function OPTIONS() {
  return new Response(null, { status: 204 });
}
