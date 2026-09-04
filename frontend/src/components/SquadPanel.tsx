"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Users, MapPin, ThermometerSun } from "lucide-react";
import { api, type Team, type TeamDetail, type Weather } from "@/lib/api";
import TiltCard from "./TiltCard";
import IqLoader from "./IqLoader";

function jerseyClass(position: string | null) {
  if (!position) return "pos-default";
  const p = position.toLowerCase();
  if (p.includes("goal")) return "pos-goalkeeper";
  if (p.includes("defence") || p.includes("back")) return "pos-defence";
  if (p.includes("mid")) return "pos-midfield";
  if (p.includes("offence") || p.includes("forward") || p.includes("wing")) return "pos-offence";
  return "pos-default";
}

function initials(name: string) {
  return name.split(" ").map((n) => n[0]).slice(0, 2).join("");
}

export default function SquadPanel({ teams }: { teams: Team[] }) {
  const [teamId, setTeamId] = useState<number>(teams[0]?.id ?? 0);
  const [detail, setDetail] = useState<TeamDetail | null>(null);
  const [weather, setWeather] = useState<Weather | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!teamId) return;
    setLoading(true);
    Promise.all([api.teamDetail(teamId), api.teamWeather(teamId)])
      .then(([d, w]) => {
        setDetail(d);
        setWeather(w.weather);
      })
      .catch(() => {
        setDetail(null);
        setWeather(null);
      })
      .finally(() => setLoading(false));
  }, [teamId]);

  return (
    <div>
      <div style={{ maxWidth: 320, marginBottom: 28 }}>
        <select value={teamId} onChange={(e) => setTeamId(Number(e.target.value))}>
          {teams.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
            </option>
          ))}
        </select>
      </div>

      {detail && (
        <div className="grid-2" style={{ marginBottom: 28 }}>
          <TiltCard>
            <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 16 }}>
              {detail.crest ? <img src={detail.crest} alt="" className="crest-lg" /> : null}
              <div>
                <div className="stat-value" style={{ fontSize: "1.6rem" }}>
                  {detail.name}
                </div>
                <div className="muted">
                  Coach: {detail.coach_detail?.name || detail.coach || "—"}
                  {detail.coach_detail?.nationality ? ` · ${detail.coach_detail.nationality}` : ""}
                  {detail.coach_detail?.age != null ? ` · ${detail.coach_detail.age}` : ""}
                </div>
              </div>
            </div>
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              <div className="badge">
                <MapPin size={13} />
                {detail.venue}, {detail.city}
              </div>
              {detail.founded != null && <div className="badge">Founded {detail.founded}</div>}
              {detail.club_colors && <div className="badge">{detail.club_colors}</div>}
              {detail.coach_detail?.contract_until && (
                <div className="badge">Contract to {detail.coach_detail.contract_until}</div>
              )}
              {detail.website && (
                <a className="badge" href={detail.website} target="_blank" rel="noreferrer">
                  {detail.website.replace(/^https?:\/\//, "")}
                </a>
              )}
            </div>
          </TiltCard>

          <TiltCard>
            <div className="section-label">
              <span className="dot" />
              Stadium Conditions
            </div>
            {weather ? (
              <>
                <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
                  <span style={{ fontSize: "2.6rem" }}>{weather.icon}</span>
                  <div>
                    <div className="stat-value" style={{ fontSize: "2rem" }}>
                      {weather.temperature_c}°C
                    </div>
                    <div className="muted">{weather.condition}</div>
                  </div>
                </div>
                <div style={{ display: "flex", gap: 12, marginTop: 16, flexWrap: "wrap" }}>
                  <span className="badge">
                    <ThermometerSun size={13} />
                    Wind {weather.wind_kph} kph
                  </span>
                  {weather.feels_like_c != null && <span className="badge">Feels {weather.feels_like_c}°C</span>}
                  {weather.humidity_pct != null && <span className="badge">Humidity {weather.humidity_pct}%</span>}
                  {weather.wind_gust_kph != null && <span className="badge">Gust {weather.wind_gust_kph} kph</span>}
                  {weather.performance_impact !== 0 && (
                    <span className="badge" style={{ background: "rgba(255,91,106,0.12)", color: "var(--accent3)", borderColor: "rgba(255,91,106,0.3)" }}>
                      Performance impact {weather.performance_impact}
                    </span>
                  )}
                </div>
              </>
            ) : (
              <p className="muted">Loading conditions…</p>
            )}
          </TiltCard>
        </div>
      )}

      {detail && (detail.squad || []).some((p) => p.goals != null) && (
        <div style={{ marginBottom: 28 }}>
          <div className="section-label">
            <span className="dot" />
            Club scorers
          </div>
          <div className="card scroll-x" style={{ marginTop: 16 }}>
            <table>
              <thead>
                <tr>
                  <th>Player</th>
                  <th>Goals</th>
                  <th>Assists</th>
                  <th>Played</th>
                </tr>
              </thead>
              <tbody>
                {[...detail.squad]
                  .filter((p) => p.goals != null)
                  .sort((a, b) => (b.goals || 0) - (a.goals || 0))
                  .map((p) => (
                    <tr key={p.id}>
                      <td>
                        <strong>{p.name}</strong>
                        {p.position ? <span className="muted"> · {p.position}</span> : null}
                      </td>
                      <td>{p.goals}</td>
                      <td>{p.assists ?? "—"}</td>
                      <td>{p.played_matches ?? "—"}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="section-label">
        <Users size={14} />
        Squad
      </div>
      {loading && <IqLoader label="FETCHING SQUAD INTELLIGENCE" />}
      <div className="grid-3">
        {(detail?.squad || []).map((p, i) => (
          <motion.div
            key={p.id}
            className="player-card"
            initial={{ opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: Math.min(i, 20) * 0.02 }}
          >
            <div className={`jersey ${jerseyClass(p.position)}`}>{initials(p.name)}</div>
            <div>
              <div style={{ fontWeight: 700, fontSize: "0.9rem" }}>{p.name}</div>
              <div className="muted">
                {p.shirt_number != null ? `#${p.shirt_number} · ` : ""}
                {p.position || "—"}
                {p.nationality ? ` · ${p.nationality}` : ""}
                {p.age != null ? ` · ${p.age}` : ""}
                {p.goals != null ? ` · ${p.goals} gls` : ""}
                {p.assists != null ? ` · ${p.assists} ast` : ""}
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
