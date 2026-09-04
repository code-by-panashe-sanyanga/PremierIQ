import { NextRequest, NextResponse } from "next/server";

const WINDOW_MS = 60_000;
const MAX_HITS = 90;
const hits = new Map<string, number[]>();

function clientIp(req: NextRequest) {
  return (
    req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ||
    req.headers.get("x-real-ip") ||
    "local"
  );
}

export function middleware(req: NextRequest) {
  if (!req.nextUrl.pathname.startsWith("/api")) {
    return NextResponse.next();
  }
  const ip = clientIp(req);
  const now = Date.now();
  const recent = (hits.get(ip) || []).filter((stamp) => now - stamp < WINDOW_MS);
  if (recent.length >= MAX_HITS) {
    return NextResponse.json({ detail: "Too many requests." }, { status: 429 });
  }
  recent.push(now);
  hits.set(ip, recent);
  return NextResponse.next();
}

export const config = {
  matcher: "/api/:path*",
};
