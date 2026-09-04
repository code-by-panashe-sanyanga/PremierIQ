"use client";

import type { Weather } from "@/lib/api";

function effectClass(condition: string) {
  const c = condition.toLowerCase();
  if (c.includes("rain") || c.includes("drizzle") || c.includes("shower") || c.includes("thunder")) return "rain";
  if (c.includes("wind")) return "wind";
  if (c.includes("fog") || c.includes("mist")) return "fog";
  if (c.includes("snow")) return "fog";
  return "";
}

export default function ConditionsCard({ weather }: { weather: Weather | null }) {
  const effect = weather ? effectClass(weather.condition) : "";
  return (
    <div className={`conditions-card ${effect}`}>
      {effect === "rain" && <div className="wx-rain" aria-hidden="true" />}
      {effect === "fog" && <div className="wx-fog" aria-hidden="true" />}
      <div className="section-label">
        <span className="dot" />
        Match Conditions
      </div>
      {weather ? (
        <>
          <div className="conditions-hero">
            <span className="wx-icon">{weather.icon}</span>
            <div>
              <div className="stat-value" style={{ fontSize: "1.8rem" }}>
                {weather.condition}
              </div>
              <div className="muted">Home stadium · current reading</div>
            </div>
          </div>
          <div className="conditions-metrics">
            <div>
              <div className="muted">Temperature</div>
              <strong>{weather.temperature_c}°C</strong>
            </div>
            {weather.feels_like_c != null && (
              <div>
                <div className="muted">Feels like</div>
                <strong>{weather.feels_like_c}°C</strong>
              </div>
            )}
            <div>
              <div className="muted">Wind</div>
              <strong>{weather.wind_kph} km/h</strong>
            </div>
            {weather.wind_gust_kph != null && (
              <div>
                <div className="muted">Gust</div>
                <strong>{weather.wind_gust_kph} km/h</strong>
              </div>
            )}
            <div>
              <div className="muted">Precipitation</div>
              <strong>{weather.precipitation_mm} mm</strong>
            </div>
            {weather.humidity_pct != null && (
              <div>
                <div className="muted">Humidity</div>
                <strong>{weather.humidity_pct}%</strong>
              </div>
            )}
            {weather.cloud_pct != null && (
              <div>
                <div className="muted">Cloud cover</div>
                <strong>{weather.cloud_pct}%</strong>
              </div>
            )}
            <div>
              <div className="muted">Model impact</div>
              <strong>{weather.performance_impact === 0 ? "0.00 xG" : `${weather.performance_impact.toFixed(2)} xG`}</strong>
            </div>
          </div>
        </>
      ) : (
        <p className="muted">Select a home club to read stadium conditions.</p>
      )}
    </div>
  );
}
