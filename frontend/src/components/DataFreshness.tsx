"use client";

import { useEffect, useState } from "react";

export default function DataFreshness({
  source,
  fetchedAt,
  matchday,
  providerUpdatedAt,
}: {
  source?: string;
  fetchedAt?: string;
  matchday?: number | null;
  providerUpdatedAt?: string | null;
}) {
  const stamp = providerUpdatedAt || fetchedAt;
  const live = source === "live";
  const [now, setNow] = useState<number | null>(null);

  useEffect(() => {
    setNow(Date.now());
    const timer = window.setInterval(() => setNow(Date.now()), 15000);
    return () => window.clearInterval(timer);
  }, []);

  const seconds =
    stamp && now != null ? Math.max(0, Math.round((now - new Date(stamp).getTime()) / 1000)) : null;
  const age =
    seconds == null
      ? null
      : seconds < 60
        ? `${seconds} SECOND${seconds === 1 ? "" : "S"} AGO`
        : `${Math.round(seconds / 60)} MIN AGO`;

  if (!live) {
    return (
      <div className="freshness fallback" role="status">
        ⚠ FALLBACK DATA · LIVE PROVIDER UNAVAILABLE
      </div>
    );
  }

  return (
    <div className="freshness live" role="status">
      <span className="live-dot" />
      LIVE DATA
      {matchday != null ? ` · MATCHDAY ${matchday}` : ""}
      {age ? ` · UPDATED ${age}` : ""}
    </div>
  );
}

