"use client";

import { FORMATIONS, type Formation } from "@/lib/api";

const SHAPE: Record<string, number[]> = {
  "4-4-2": [1, 4, 4, 2],
  "4-3-3": [1, 4, 3, 3],
  "4-2-3-1": [1, 4, 2, 3, 1],
  "3-5-2": [1, 3, 5, 2],
  "5-3-2": [1, 5, 3, 2],
  "3-4-3": [1, 3, 4, 3],
};

export const PERSONA: Record<string, string> = {
  "4-4-2": "BALANCED",
  "4-3-3": "ATTACKING",
  "4-2-3-1": "CONTROL",
  "3-5-2": "WIDE",
  "5-3-2": "DEFENSIVE",
  "3-4-3": "ATTACKING",
};

function MiniPitch({ formation }: { formation: string }) {
  const rows = SHAPE[formation] || [1, 4, 3, 3];
  return (
    <div className="mini-pitch" aria-hidden="true">
      {rows.map((count, i) => (
        <div className="mini-pitch-row" key={`${formation}-${i}`}>
          {Array.from({ length: count }, (_, j) => (
            <span className="mini-dot" key={j} />
          ))}
        </div>
      ))}
    </div>
  );
}

export default function FormationBoard({
  home,
  away,
  onHome,
  onAway,
}: {
  home: Formation;
  away: Formation;
  onHome: (value: Formation) => void;
  onAway: (value: Formation) => void;
}) {
  return (
    <div className="tactical-setup">
      <div className="section-label">
        <span className="dot" />
        Tactical Setup
      </div>
      <p className="muted" style={{ marginTop: -12, marginBottom: 18 }}>
        Simulation assumptions — not confirmed match lineups.
      </p>
      <div className="tactical-grid">
        <div>
          <div className="muted">HOME</div>
          <select value={home} onChange={(e) => onHome(e.target.value as Formation)}>
            {FORMATIONS.map((f) => (
              <option key={f} value={f}>
                {f} · {PERSONA[f]}
              </option>
            ))}
          </select>
          <MiniPitch formation={home} />
          <div className="stat-value" style={{ fontSize: "1.6rem", marginTop: 10 }}>
            {home}
          </div>
          <div className="badge">{PERSONA[home]}</div>
        </div>
        <div className="vs-text">VS</div>
        <div>
          <div className="muted">AWAY</div>
          <select value={away} onChange={(e) => onAway(e.target.value as Formation)}>
            {FORMATIONS.map((f) => (
              <option key={f} value={f}>
                {f} · {PERSONA[f]}
              </option>
            ))}
          </select>
          <MiniPitch formation={away} />
          <div className="stat-value" style={{ fontSize: "1.6rem", marginTop: 10 }}>
            {away}
          </div>
          <div className="badge">{PERSONA[away]}</div>
        </div>
      </div>
    </div>
  );
}
