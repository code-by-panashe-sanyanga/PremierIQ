"use client";

import type { StandingRow } from "@/lib/api";

export default function Ticker({ table }: { table: StandingRow[] }) {
  if (!table.length) return null;
  const items = [...table, ...table]; // duplicate for seamless loop

  return (
    <div className="marquee-wrap">
      <div className="marquee-track">
        {items.map((row, i) => (
          <div className="marquee-item" key={`${row.team_id}-${i}`}>
            <img src={row.crest} alt="" className="crest" />
            <strong>{row.short_name}</strong>
            <span>#{row.position}</span>
            <span>·</span>
            <span>{row.points} PTS</span>
          </div>
        ))}
      </div>
    </div>
  );
}
