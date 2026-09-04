"use client";

import { useEffect, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { CloudRain, Plane, Sparkles, Zap } from "lucide-react";
import { api, type Formation, type Prediction, type Team, type UpcomingFixture, type Weather } from "@/lib/api";
import TiltCard from "./TiltCard";
import FormationBoard from "./FormationBoard";
import ConditionsCard from "./ConditionsCard";
import IqLoader from "./IqLoader";

const STAGES = [
  "INITIALISING MATCH MODEL",
  "CALCULATING ATTACKING STRENGTH",
  "ANALYSING MATCH CONDITIONS",
  "CALCULATING TRAVEL FATIGUE",
  "RUNNING 10,000 SIMULATIONS",
];

function formatKickoff(iso: string | null) {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    weekday: "short",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function CountUp({ value, reduced }: { value: number; reduced: boolean }) {
  const [shown, setShown] = useState(reduced ? value : 0);
  useEffect(() => {
    if (reduced) {
      setShown(value);
      return;
    }
    const start = performance.now();
    const duration = 900;
    let frame = 0;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      setShown(Math.round(value * (1 - Math.pow(1 - t, 3))));
      if (t < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [value, reduced]);
  return <>{shown.toLocaleString()}</>;
}

export default function MatchPredictor({ teams }: { teams: Team[] }) {
  const reduced = useReducedMotion() ?? false;
  const [homeId, setHomeId] = useState<number>(teams[0]?.id ?? 0);
  const [awayId, setAwayId] = useState<number>(teams[1]?.id ?? 0);
  const [homeFormation, setHomeFormation] = useState<Formation>("4-3-3");
  const [awayFormation, setAwayFormation] = useState<Formation>("4-2-3-1");
  const [weather, setWeather] = useState<Weather | null>(null);
  const [prediction, setPrediction] = useState<Prediction | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [phase, setPhase] = useState<"idle" | "running" | "presenting" | "done">("idle");
  const [stage, setStage] = useState(0);
  const [progress, setProgress] = useState(0);
  const [fixtures, setFixtures] = useState<UpcomingFixture[]>([]);

  const home = teams.find((t) => t.id === homeId);
  const away = teams.find((t) => t.id === awayId);

  useEffect(() => {
    api
      .upcomingFixtures(12)
      .then((res) => {
        const next = res.fixtures || [];
        setFixtures(next);
        const first = next[0];
        if (
          first &&
          teams.some((t) => t.id === first.home_id) &&
          teams.some((t) => t.id === first.away_id)
        ) {
          setHomeId(first.home_id);
          setAwayId(first.away_id);
        }
      })
      .catch(() => setFixtures([]));
  }, [teams]);

  useEffect(() => {
    if (!homeId) return;
    api
      .teamWeather(homeId)
      .then((w) => setWeather(w.weather))
      .catch(() => setWeather(null));
  }, [homeId]);

  useEffect(() => {
    if (phase !== "running") return;
    if (reduced) return;
    setStage(0);
    setProgress(8);
    const timers = STAGES.map((_, i) =>
      window.setTimeout(() => {
        setStage(i);
        setProgress(Math.min(85, 12 + i * 16));
      }, i * 550)
    );
    return () => timers.forEach(clearTimeout);
  }, [phase, reduced]);

  async function run() {
    if (homeId === awayId) {
      setError("Pick two different clubs.");
      return;
    }
    setError(null);
    setPrediction(null);
    setPhase("running");
    try {
      const result = await api.predictLive(homeId, awayId, homeFormation, awayFormation);
      if (reduced) {
        setPrediction(result);
        setPhase("done");
        return;
      }
      setProgress(100);
      setStage(STAGES.length - 1);
      setPrediction(result);
      setPhase("presenting");
      window.setTimeout(() => setPhase("done"), 1400);
    } catch (e: unknown) {
      setPhase("idle");
      setError(e instanceof Error ? e.message : "Prediction failed");
    }
  }

  const showSequence = phase === "running" || phase === "presenting";

  return (
    <div>
      <div className="grid-2">
        <TiltCard>
          <div className="section-label">
            <span className="dot" />
            Select Teams
          </div>
          {fixtures.length > 0 && (
            <div className="fixture-strip" role="list">
              {fixtures.map((fx) => {
                const active = fx.home_id === homeId && fx.away_id === awayId;
                const kickoff = formatKickoff(fx.utc_date);
                return (
                  <button
                    key={fx.id ?? `${fx.home_id}-${fx.away_id}-${fx.utc_date}`}
                    type="button"
                    role="listitem"
                    className={`fixture-chip${active ? " on" : ""}`}
                    onClick={() => {
                      setHomeId(fx.home_id);
                      setAwayId(fx.away_id);
                    }}
                  >
                    <span className="fixture-teams">
                      {fx.home_crest ? <img src={fx.home_crest} alt="" className="crest" /> : null}
                      {fx.home_tla || fx.home_name} v {fx.away_tla || fx.away_name}
                      {fx.away_crest ? <img src={fx.away_crest} alt="" className="crest" /> : null}
                    </span>
                    <span className="muted">
                      {fx.matchday != null ? `MD${fx.matchday}` : null}
                      {fx.matchday != null && kickoff ? " · " : null}
                      {kickoff}
                    </span>
                  </button>
                );
              })}
            </div>
          )}
          <div className="vs-block">
            <select value={homeId} onChange={(e) => setHomeId(Number(e.target.value))}>
              {teams.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.short_name}
                </option>
              ))}
            </select>
            <span className="vs-text">VS</span>
            <select value={awayId} onChange={(e) => setAwayId(Number(e.target.value))}>
              {teams.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.short_name}
                </option>
              ))}
            </select>
          </div>
          <div style={{ display: "flex", justifyContent: "center", gap: 40, margin: "8px 0 20px" }}>
            {home?.crest ? <img src={home.crest} alt={home.name} className="crest-lg" /> : null}
            {away?.crest ? <img src={away.crest} alt={away.name} className="crest-lg" /> : null}
          </div>
          <FormationBoard
            home={homeFormation}
            away={awayFormation}
            onHome={setHomeFormation}
            onAway={setAwayFormation}
          />
        </TiltCard>

        <div style={{ display: "grid", gap: 24 }}>
          <TiltCard>
            <ConditionsCard weather={weather} />
          </TiltCard>
          <button className="primary" onClick={run} disabled={phase === "running"} style={{ width: "100%", justifyContent: "center" }}>
            <Zap size={18} />
            {phase === "running" ? "SIMULATION IN FLIGHT…" : "RUN 10,000 SIMULATIONS"}
          </button>
          {error && <p className="error">{error}</p>}
        </div>
      </div>

      <AnimatePresence mode="wait">
        {showSequence && (
          <motion.div
            key="sim"
            className="sim-engine"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
          >
            <div className="section-label">
              <span className="dot" />
              Simulation Engine
            </div>
            <p className="muted">
              {phase === "running"
                ? "Waiting on the live model. Stage copy is the presentation sequence, not a fake backend progress bar."
                : "Visual presentation of completed results — the 10,000 simulations have already finished."}
            </p>
            <ul className="sim-stages">
              {STAGES.map((label, i) => (
                <li key={label} className={i <= stage ? "on" : ""}>
                  {label}
                </li>
              ))}
            </ul>
            <div className="sim-bar" aria-hidden="true">
              <motion.span animate={{ width: `${progress}%` }} transition={{ duration: 0.4 }} />
            </div>
            <div className="muted">{progress}%</div>
            {phase === "running" && <IqLoader label="PREPARING SIMULATION" />}
          </motion.div>
        )}
      </AnimatePresence>

      {prediction && (phase === "presenting" || phase === "done") && (
        <motion.div className="outcome-counts" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          <div>
            <div className="muted">Home wins</div>
            <div className="stat-value">
              <CountUp value={prediction.outcome_counts?.home_win ?? 0} reduced={reduced} />
            </div>
          </div>
          <div>
            <div className="muted">Draws</div>
            <div className="stat-value">
              <CountUp value={prediction.outcome_counts?.draw ?? 0} reduced={reduced} />
            </div>
          </div>
          <div>
            <div className="muted">Away wins</div>
            <div className="stat-value">
              <CountUp value={prediction.outcome_counts?.away_win ?? 0} reduced={reduced} />
            </div>
          </div>
        </motion.div>
      )}

            {prediction && (phase === "done" || phase === "presenting") && (
        <motion.div className="iq-results" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
          <div className="grid-2">
            <TiltCard>
              <div className="section-label">
                <span className="dot" />
                Win Probabilities
              </div>
              <div className="muted">Expected goals</div>
              <div className="stat-value">
                {prediction.expected_goals.home} – {prediction.expected_goals.away}
              </div>
              <span className="badge" style={{ margin: "12px 0 18px" }}>
                Most likely {prediction.most_likely_score}
              </span>
              <div className="prob-track">
                <motion.div className="prob-seg" initial={{ width: 0 }} animate={{ width: `${prediction.probabilities.home_win}%` }} style={{ background: "var(--accent)" }}>
                  {prediction.probabilities.home_win}%
                </motion.div>
                <motion.div className="prob-seg" initial={{ width: 0 }} animate={{ width: `${prediction.probabilities.draw}%` }} style={{ background: "#ffcf5c" }}>
                  {prediction.probabilities.draw}%
                </motion.div>
                <motion.div className="prob-seg" initial={{ width: 0 }} animate={{ width: `${prediction.probabilities.away_win}%` }} style={{ background: "var(--accent3)" }}>
                  {prediction.probabilities.away_win}%
                </motion.div>
              </div>
              <p className="muted" style={{ marginTop: 10 }}>
                Home · Draw · Away — {prediction.simulations.toLocaleString()} Poisson simulations. {prediction.warning}
              </p>
              {prediction.context && (
                <div style={{ display: "flex", gap: 12, marginTop: 16, flexWrap: "wrap" }}>
                  <div className="badge">
                    <CloudRain size={13} />
                    {prediction.context.weather.condition}
                  </div>
                  <div className="badge">
                    <Plane size={13} />
                    {prediction.context.away_travel_km} km
                  </div>
                  {prediction.context.rest?.home_days != null && (
                    <div className="badge">Home rest {prediction.context.rest.home_days}d</div>
                  )}
                  {prediction.context.rest?.away_days != null && (
                    <div className="badge">Away rest {prediction.context.rest.away_days}d</div>
                  )}
                  {prediction.context.fixture?.referee && (
                    <div className="badge">{prediction.context.fixture.referee}</div>
                  )}
                </div>
              )}
              {prediction.model?.used_prior_venue && (
                <p className="muted" style={{ marginTop: 12 }}>
                  Home/away rates include previous-season matches because this season’s venue sample is still small.
                </p>
              )}
              {prediction.model?.fallback_season_only && (
                <p className="muted" style={{ marginTop: 12 }}>
                  Recent match history was unavailable. This run used season-level rates only.
                </p>
              )}
            </TiltCard>

            <TiltCard>
              <div className="section-label">
                <span className="dot" />
                Model Confidence
              </div>
              <div className="confidence-bar" aria-label={`Model confidence ${prediction.confidence?.value ?? 0} percent`}>
                <span style={{ width: `${prediction.confidence?.value ?? 0}%` }} />
              </div>
              <div className="stat-value" style={{ fontSize: "2.4rem" }}>
                {prediction.confidence?.value ?? "—"}%
              </div>
              <div className="badge" style={{ marginTop: 8 }}>
                {prediction.confidence?.level || "UNSCORED"}
              </div>
              <p className="muted" style={{ marginTop: 12 }}>
                {prediction.confidence?.copy}
              </p>
              <p className="muted">Not betting advice. Not a chance of winning.</p>
            </TiltCard>
          </div>

          {prediction.scorelines && prediction.scorelines.length > 0 && (
            <TiltCard>
              <div className="section-label">
                <span className="dot" />
                Top Scorelines
              </div>
              <div className="scoreline-list">
                {prediction.scorelines.map((row) => (
                  <div key={row.score} className="scoreline-row">
                    <strong>{row.score.replace("-", "–")}</strong>
                    <div className="scoreline-track">
                      <span style={{ width: `${Math.max(row.pct, 2)}%` }} />
                    </div>
                    <span>{row.pct.toFixed(1)}%</span>
                  </div>
                ))}
              </div>
            </TiltCard>
          )}

          {prediction.scenarios && (
            <TiltCard>
              <div className="section-label">
                <span className="dot" />
                Match Scenarios
              </div>
              <p className="muted" style={{ marginTop: -8 }}>
                Mutually exclusive buckets from the same {prediction.simulations.toLocaleString()} simulations.
              </p>
              <div className="scenario-grid">
                {prediction.scenarios.map((s) => (
                  <div key={s.id} className="scenario-cell">
                    <div className="muted">{s.label}</div>
                    <div className="stat-value" style={{ fontSize: "2rem" }}>
                      {s.pct}%
                    </div>
                  </div>
                ))}
              </div>
            </TiltCard>
          )}

          {(prediction.context?.head_to_head?.played ||
            prediction.context?.home_last_completed ||
            prediction.context?.away_last_completed) && (
            <TiltCard>
              <div className="section-label">
                <span className="dot" />
                Recorded Matches
              </div>
              {prediction.context?.home_last_completed && (
                <p className="muted" style={{ marginTop: 8 }}>
                  {prediction.context.home_team} last completed {prediction.context.home_last_completed.score}
                  {prediction.context.home_last_completed.half_time
                    ? ` (HT ${prediction.context.home_last_completed.half_time})`
                    : ""}
                  {prediction.context.home_last_completed.utc_date
                    ? ` on ${prediction.context.home_last_completed.utc_date.slice(0, 10)}`
                    : ""}
                  .
                </p>
              )}
              {prediction.context?.away_last_completed && (
                <p className="muted">
                  {prediction.context.away_team} last completed {prediction.context.away_last_completed.score}
                  {prediction.context.away_last_completed.half_time
                    ? ` (HT ${prediction.context.away_last_completed.half_time})`
                    : ""}
                  {prediction.context.away_last_completed.utc_date
                    ? ` on ${prediction.context.away_last_completed.utc_date.slice(0, 10)}`
                    : ""}
                  .
                </p>
              )}
              {prediction.context?.head_to_head?.played ? (
                <div className="h2h-list">
                  <div className="muted" style={{ marginBottom: 8 }}>
                    {prediction.context.head_to_head.played} completed meetings
                    {prediction.model?.used_h2h ? " · used in the blend" : " · sample too small for the blend"}
                  </div>
                  {prediction.context.head_to_head.matches.map((row) => (
                    <div key={`${row.utc_date}-${row.score}`} className="h2h-row">
                      <span>{row.utc_date ? row.utc_date.slice(0, 10) : "—"}</span>
                      <strong>{row.score.replace("-", "–")}</strong>
                    </div>
                  ))}
                </div>
              ) : null}
            </TiltCard>
          )}

          <TiltCard>
            <div className="iq-brief">
              <div className="section-label">
                <span className="dot" />
                IQ Briefing
              </div>
              <hr className="iq-rule" />
              {prediction.ai ? (
                <>
                  <h3 className="iq-headline">{prediction.ai.headline}</h3>
                  <p className="lede" style={{ marginTop: 12 }}>
                    {prediction.ai.analysis}
                  </p>
                  <div className="badge" style={{ marginTop: 12 }}>
                    <Sparkles size={13} />
                    {prediction.ai.model} · narrator only
                  </div>
                </>
              ) : (
                <p className="muted">Gemini briefing unavailable. The statistical simulation above still stands.</p>
              )}
              <div className="key-factors">
                <div className="muted" style={{ letterSpacing: "0.2em", marginBottom: 12 }}>
                  KEY FACTORS
                </div>
                {(prediction.key_factors || []).map((factor) => (
                  <div key={factor.code} className="key-factor">
                    <div className="key-code">
                      {factor.code} {factor.title}
                    </div>
                    <p>{factor.body}</p>
                  </div>
                ))}
              </div>
            </div>
          </TiltCard>
        </motion.div>
      )}
    </div>
  );
}
