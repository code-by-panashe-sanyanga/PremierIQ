"use client";

import { useEffect, useState } from "react";
import { Trophy, Radio, Users2, MapPinned, Flag, ArrowDown } from "lucide-react";
import { api, type Team, type StandingRow, type SeasonIq, type Scorer, type SeasonMeta } from "@/lib/api";
import Reveal from "@/components/Reveal";
import Ticker from "@/components/Ticker";
import StandingsTable from "@/components/StandingsTable";
import MatchPredictor from "@/components/MatchPredictor";
import SquadPanel from "@/components/SquadPanel";
import StadiumMap from "@/components/StadiumMap";
import SeasonIqPanel from "@/components/SeasonIq";
import DataFreshness from "@/components/DataFreshness";
import IqLoader from "@/components/IqLoader";

const SECTIONS = [
  { id: "standings", label: "Standings", icon: Trophy },
  { id: "predictor", label: "Match IQ", icon: Radio },
  { id: "squads", label: "Squads", icon: Users2 },
  { id: "map", label: "Stadiums", icon: MapPinned },
  { id: "season", label: "Season IQ", icon: Flag },
];

export default function Home() {
  const [teams, setTeams] = useState<Team[]>([]);
  const [table, setTable] = useState<StandingRow[]>([]);
  const [teamsMeta, setTeamsMeta] = useState<{ source?: string; fetched_at?: string }>({});
  const [tableMeta, setTableMeta] = useState<{
    source?: string;
    fetched_at?: string;
    current_matchday?: number | null;
    season?: SeasonMeta | null;
  }>({});
  const [season, setSeason] = useState<SeasonIq | null>(null);
  const [scorers, setScorers] = useState<Scorer[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .teams()
      .then((t) => {
        setTeams(t.teams);
        setTeamsMeta({ source: t.source, fetched_at: t.fetched_at });
      })
      .catch((e) => setError(e.message));
    api
      .standings()
      .then((s) => {
        setTable(s.table);
        setTableMeta({
          source: s.source,
          fetched_at: s.fetched_at,
          current_matchday: s.current_matchday,
          season: s.season,
        });
      })
      .catch((e) => setError(e.message));
    api
      .seasonIq()
      .then(setSeason)
      .catch(() =>
        setSeason({
          available: false,
          mode: "unavailable",
          reason: "Season IQ could not be loaded.",
          simulations: 0,
          fixture_count: 0,
          teams: [],
        })
      );
    api
      .scorers()
      .then((s) => setScorers(s.scorers || []))
      .catch(() => setScorers([]));
  }, []);

  return (
    <main>
      <nav className="nav">
        <div className="nav-logo">
          PREMIER<span style={{ color: "var(--accent)" }}>IQ</span>
        </div>
        <div className="nav-links">
          {SECTIONS.map((s) => (
            <a key={s.id} href={`#${s.id}`} className="nav-link">
              {s.label}
            </a>
          ))}
        </div>
      </nav>

      <section className="hero">
        <div className="hero-badge">
            <span className="live-dot" />
            LIVE PREMIER LEAGUE DATA
            {tableMeta.season?.label ? ` · SEASON ${tableMeta.season.label}` : ""}
            {tableMeta.current_matchday != null ? ` · MATCHDAY ${tableMeta.current_matchday}` : ""}
          </div>

        <h1 className="display">
          PREDICT.
          <br />
          <span className="outline">ANALYSE.</span>
          <br />
          SIMULATE.
        </h1>

        <p className="lede">
          Premier League match and season outlooks from live standings, recent results and match conditions, run through 10,000 statistical simulations.
        </p>

        {error && <p className="error" style={{ marginTop: 20 }}>⚠ {error}</p>}

        <div className="scroll-cue">
          <span className="scroll-line" />
          <ArrowDown size={14} />
          scroll
        </div>
      </section>

      {table.length > 0 && <Ticker table={table} />}

      <section id="standings" className="section">
        <Reveal>
          <div className="section-label">
            <span className="dot" />
            League Table
          </div>
          <h2 className="display" style={{ fontSize: "clamp(2rem, 5vw, 3.5rem)" }}>
            CURRENT STANDINGS
          </h2>
          <div style={{ marginTop: 16 }}>
            <DataFreshness
              source={tableMeta.source || teamsMeta.source}
              fetchedAt={tableMeta.fetched_at}
              matchday={tableMeta.current_matchday}
              providerUpdatedAt={tableMeta.season?.last_updated}
            />
          </div>
        </Reveal>
        <Reveal delay={0.15}>
          <div className="card" style={{ marginTop: 32 }}>
            {table.length ? <StandingsTable table={table} /> : <IqLoader label="FETCHING LEAGUE DATA" />}
          </div>
        </Reveal>
        {scorers.length > 0 && (
          <Reveal delay={0.2}>
            <div className="section-label" style={{ marginTop: 40 }}>
              <span className="dot" />
              Competition scorers
            </div>
            <div className="card scroll-x" style={{ marginTop: 16 }}>
              <table>
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Player</th>
                    <th>Club</th>
                    <th>G</th>
                    <th>A</th>
                    <th>P</th>
                  </tr>
                </thead>
                <tbody>
                  {scorers.map((row, i) => (
                    <tr key={row.player_id ?? `${row.name}-${i}`}>
                      <td>{i + 1}</td>
                      <td>
                        <strong>{row.name}</strong>
                        {row.age != null ? <span className="muted"> · {row.age}</span> : null}
                      </td>
                      <td>
                        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                          {row.crest ? <img src={row.crest} alt="" className="crest" /> : null}
                          {row.team_name}
                        </div>
                      </td>
                      <td>{row.goals ?? "—"}</td>
                      <td>{row.assists ?? "—"}</td>
                      <td>{row.played_matches ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Reveal>
        )}
      </section>

      <section id="predictor" className="section">
        <Reveal>
          <div className="section-label">
            <span className="dot" />
            Match IQ Engine
          </div>
          <h2 className="display" style={{ fontSize: "clamp(2rem, 5vw, 3.5rem)" }}>
            MATCH IQ
          </h2>
          <p className="lede">Select clubs, set a tactical scenario, read the conditions, then run 10,000 simulations.</p>
        </Reveal>
        <div style={{ marginTop: 32 }}>
          {teams.length ? <MatchPredictor teams={teams} /> : <IqLoader label="CALCULATING TEAM STRENGTH" />}
        </div>
      </section>

      <section id="squads" className="section">
        <Reveal>
          <span className="sticker">Club Intelligence</span>
          <h2 className="display" style={{ fontSize: "clamp(2rem, 5vw, 3.5rem)", marginTop: 24 }}>
            SQUAD INTELLIGENCE
          </h2>
        </Reveal>
        <Reveal delay={0.15}>
          <div style={{ marginTop: 32 }}>{teams.length ? <SquadPanel teams={teams} /> : <IqLoader label="FETCHING SQUAD INTELLIGENCE" />}</div>
        </Reveal>
      </section>

      <section id="map" className="section">
        <Reveal>
          <h2 className="display" style={{ fontSize: "clamp(2rem, 5vw, 3.5rem)" }}>
            TEAM LOCATIONS
          </h2>
        </Reveal>
        <div style={{ marginTop: 32 }}>{teams.length ? <StadiumMap teams={teams} /> : <IqLoader label="ANALYSING WEATHER" />}</div>
      </section>

      <section id="season" className="section">
        <Reveal>
          <div className="section-label">
            <span className="dot" />
            Remaining Fixtures
          </div>
          <h2 className="display" style={{ fontSize: "clamp(2rem, 5vw, 3.5rem)" }}>
            SEASON IQ
          </h2>
          <p className="lede">Title, top four and relegation probabilities from the remaining listed fixtures.</p>
        </Reveal>
        <div style={{ marginTop: 32 }}>
          {season ? <SeasonIqPanel season={season} /> : <IqLoader label="SIMULATING REMAINING FIXTURES" />}
        </div>
      </section>

      <footer>
        <span>PremierIQ © 2026</span>
        <span>Data: football-data.org · OpenWeather · OpenFreeMap · Gemini</span>
      </footer>
    </main>
  );
}
