"use client";

import DataFreshness from "./DataFreshness";
import type { SeasonIq } from "@/lib/api";

export default function SeasonIqPanel({ season }: { season: SeasonIq }) {
  if (!season.available) {
    return (
      <p className="muted">
        Season IQ is not shown as a simulated table because remaining fixture data was not returned.
        {season.reason ? ` ${season.reason}` : ""}
      </p>
    );
  }

  return (
    <div>
      <DataFreshness
        source={season.source}
        fetchedAt={season.fetched_at}
        matchday={season.season?.current_matchday}
        providerUpdatedAt={season.season?.last_updated}
      />
      <p className="muted" style={{ margin: "12px 0 24px", maxWidth: 640 }}>
        {season.fixture_count} remaining listed fixtures × {season.simulations.toLocaleString()} season runs.
        {season.note ? ` ${season.note}` : ""}
      </p>
      <div className="card scroll-x">
        <table>
          <thead>
            <tr>
              <th>Club</th>
              <th>Title</th>
              <th>Top 4</th>
              <th>Top 6</th>
              <th>Relegation</th>
              <th>Exp pts</th>
              <th>Exp pos</th>
              <th>Modal pos</th>
            </tr>
          </thead>
          <tbody>
            {season.teams.map((row) => (
              <tr key={row.team_id}>
                <td>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    {row.crest ? <img src={row.crest} alt="" className="crest" /> : null}
                    <strong>{row.name}</strong>
                  </div>
                </td>
                <td>{row.title}%</td>
                <td>{row.top4}%</td>
                <td>{row.top6}%</td>
                <td>{row.relegation}%</td>
                <td>{row.expected_points}</td>
                <td>{row.expected_position}</td>
                <td>{row.most_common_position}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
