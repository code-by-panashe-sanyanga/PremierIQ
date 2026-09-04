"use client";

import { useEffect, useRef, useState } from "react";
import type { Map as MaplibreMap } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { api, type Team, type Weather } from "@/lib/api";

const STYLE_URL = "https://tiles.openfreemap.org/styles/liberty";
const PLANET_URL = "https://tiles.openfreemap.org/planet";

function escapeHtml(value: string) {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function venueOf(team: Team) {
  return team.venue || (team as Team & { stadium?: string }).stadium || "";
}

function tryPaint(map: MaplibreMap, id: string, prop: string, value: unknown) {
  try {
    map.setPaintProperty(id, prop as never, value as never);
  } catch {
    /* layer does not take this paint property */
  }
}

function styleNightMap(map: MaplibreMap) {
  const layers = map.getStyle().layers ?? [];

  for (const layer of layers) {
    const id = layer.id;
    const key = id.toLowerCase();

    if (layer.type === "background") {
      tryPaint(map, id, "background-color", "#1a2333");
      continue;
    }

    if (layer.type === "raster" || key.includes("natural_earth")) {
      tryPaint(map, id, "raster-saturation", -0.7);
      tryPaint(map, id, "raster-brightness-min", 0);
      tryPaint(map, id, "raster-brightness-max", 0.28);
      tryPaint(map, id, "raster-contrast", 0.25);
      tryPaint(map, id, "raster-opacity", 0.55);
      continue;
    }

    if (layer.type === "fill") {
      if (key === "building") {
        tryPaint(map, id, "fill-color", "#4a5368");
        tryPaint(map, id, "fill-opacity", 0.9);
      } else if (key === "water" || key.startsWith("water_")) {
        tryPaint(map, id, "fill-color", "#0a3060");
        tryPaint(map, id, "fill-opacity", 1);
      } else if (key.includes("wood") || key.includes("park") || key.includes("grass") || key.includes("cemetery")) {
        tryPaint(map, id, "fill-color", "#1c3328");
      } else if (key.includes("sand") || key.includes("ice")) {
        tryPaint(map, id, "fill-color", "#3a3d48");
      } else if (key.includes("hospital") || key.includes("school") || key.includes("pitch") || key.includes("track")) {
        tryPaint(map, id, "fill-color", "#2a3144");
      } else if (key.includes("residential") || key.includes("landuse") || key.includes("landcover") || key.includes("aeroway")) {
        tryPaint(map, id, "fill-color", "#2c3548");
      }
      continue;
    }

    if (layer.type === "line") {
      if (key.includes("water")) {
        tryPaint(map, id, "line-color", "#0b2744");
      } else if (key.includes("casing") || key.includes("case")) {
        tryPaint(map, id, "line-color", "#141b28");
      } else if (key.includes("rail")) {
        tryPaint(map, id, "line-color", "#6a7184");
      } else if (key.includes("boundary")) {
        tryPaint(map, id, "line-color", "#8b93a8");
      } else if (key.includes("road") || key.includes("bridge") || key.includes("tunnel") || key.includes("motorway") || key.includes("highway")) {
        tryPaint(map, id, "line-color", "#9099b5");
      }
      continue;
    }

    if (layer.type === "symbol") {
      tryPaint(map, id, "text-color", "#e8edf7");
      tryPaint(map, id, "text-halo-color", "#121820");
      tryPaint(map, id, "text-halo-width", 1.2);
      tryPaint(map, id, "icon-color", "#d5dbe8");
    }
  }

  const extrusion = {
    "fill-extrusion-color": [
      "interpolate",
      ["linear"],
      ["coalesce", ["get", "render_height"], 12],
      0,
      "#9aa3bf",
      18,
      "#b4bdd6",
      45,
      "#cfd6ea",
      120,
      "#e4e8f4",
    ],
    "fill-extrusion-opacity": 0.94,
    "fill-extrusion-vertical-gradient": true,
  } as const;

  if (map.getLayer("building-3d")) {
    tryPaint(map, "building-3d", "fill-extrusion-color", extrusion["fill-extrusion-color"]);
    tryPaint(map, "building-3d", "fill-extrusion-opacity", extrusion["fill-extrusion-opacity"]);
    tryPaint(map, "building-3d", "fill-extrusion-vertical-gradient", true);
  } else if (!map.getLayer("3d-buildings")) {
    const sources = map.getStyle().sources ?? {};
    let sourceId = sources.openmaptiles ? "openmaptiles" : Object.keys(sources).find((id) => {
      const source = sources[id] as { type?: string };
      return source?.type === "vector";
    });
    if (!sourceId) {
      map.addSource("openfreemap", { type: "vector", url: PLANET_URL });
      sourceId = "openfreemap";
    }
    const labelLayerId = layers.find((layer) => {
      const layout = layer.layout as { "text-field"?: unknown } | undefined;
      return layer.type === "symbol" && Boolean(layout?.["text-field"]);
    })?.id;
    map.addLayer(
      {
        id: "3d-buildings",
        source: sourceId,
        "source-layer": "building",
        type: "fill-extrusion",
        minzoom: 13,
        filter: ["!=", ["get", "hide_3d"], true],
        paint: {
          ...extrusion,
          "fill-extrusion-height": ["coalesce", ["get", "render_height"], 12],
          "fill-extrusion-base": ["coalesce", ["get", "render_min_height"], 0],
        } as never,
      },
      labelLayerId
    );
  }

  try {
    map.setSky({
      "sky-color": "#0b1524",
      "sky-horizon-blend": 0.2,
      "horizon-color": "#24344c",
      "horizon-fog-blend": 0.1,
      "fog-color": "#152033",
      "fog-ground-blend": 0,
      "atmosphere-blend": 0,
    });
  } catch {
    /* still a readable night map without sky */
  }
}

export default function StadiumMap({ teams }: { teams: Team[] }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MaplibreMap | null>(null);
  const selectRef = useRef<(team: Team) => void>(() => {});
  const [failed, setFailed] = useState(false);
  const [selected, setSelected] = useState<Team | null>(null);
  const [weather, setWeather] = useState<Weather | null>(null);

  selectRef.current = (team: Team) => {
    setSelected(team);
    setWeather(null);
    api
      .teamWeather(team.id)
      .then((payload) => setWeather(payload.weather))
      .catch(() => setWeather(null));
  };

  useEffect(() => {
    if (!teams.length) return;

    let cancelled = false;
    let map: MaplibreMap | null = null;
    let observer: ResizeObserver | null = null;
    let raf = 0;

    const plotted = teams.filter((t) => Number.isFinite(t.lat) && Number.isFinite(t.lon));

    const start = async () => {
      const container = containerRef.current;
      if (cancelled || !container) return;

      try {
        const maplibre = (await import("maplibre-gl")) as any;
        if (cancelled || !containerRef.current) return;

        const lib = (maplibre as { default?: typeof maplibre }).default ?? maplibre;
        const Map = lib.Map;
        const NavigationControl = lib.NavigationControl;
        const Marker = lib.Marker;
        const Popup = lib.Popup;

        map = new Map({
          container: containerRef.current,
          style: STYLE_URL,
          center: [-1.8, 53.0],
          zoom: 5.4,
          pitch: 52,
          bearing: -16,
          maxPitch: 85,
          attributionControl: { compact: true },
          cooperativeGestures: true,
          maxBounds: [
            [-12, 48.5],
            [5, 60.5],
          ],
        });
        mapRef.current = map;
        map.addControl(new NavigationControl({ visualizePitch: true }), "top-right");

        plotted.forEach((t) => {
          const el = document.createElement("div");
          el.className = "stadium-marker";
          el.setAttribute("role", "button");
          el.setAttribute("aria-label", t.name);

          if (t.crest) {
            const img = document.createElement("img");
            img.src = t.crest;
            img.alt = "";
            img.draggable = false;
            el.appendChild(img);
          } else {
            el.textContent = t.tla || t.name.slice(0, 3);
          }

          const venue = venueOf(t);
          const subtitle = [venue, t.city].filter(Boolean).join(", ");

          el.addEventListener("click", () => {
            selectRef.current(t);
            map?.flyTo({
              center: [t.lon, t.lat],
              zoom: 16.2,
              pitch: 62,
              bearing: -22,
              duration: 1800,
              essential: true,
            });
          });

          new Marker({ element: el, anchor: "center", pitchAlignment: "viewport" })
            .setLngLat([t.lon, t.lat])
            .setPopup(
              new Popup({ offset: 22, maxWidth: "260px", className: "stadium-popup" }).setHTML(
                `<strong>${escapeHtml(t.name)}</strong>${subtitle ? `<br/>${escapeHtml(subtitle)}` : ""}`
              )
            )
            .addTo(map!);
        });

        const frameUk = (duration = 0) => {
          if (!map || !plotted.length) return;
          const lngs = plotted.map((t) => t.lon);
          const lats = plotted.map((t) => t.lat);
          map.fitBounds(
            [
              [Math.min(...lngs), Math.min(...lats)],
              [Math.max(...lngs), Math.max(...lats)],
            ],
            { padding: 80, maxZoom: 6.5, pitch: 52, bearing: -16, duration }
          );
        };

        frameUk();

        let styled = false;
        const applyNight = () => {
          if (cancelled || !map) return;
          try {
            styleNightMap(map);
          } catch {
            /* liberty still shows the UK without the night restyle */
          }
          if (styled) return;
          styled = true;
          map.resize();
          frameUk(900);
        };

        map.on("style.load", applyNight);
        if (map.isStyleLoaded()) applyNight();

        const resize = () => map?.resize();
        requestAnimationFrame(resize);
        observer = new ResizeObserver(resize);
        observer.observe(containerRef.current);
      } catch {
        if (!cancelled) setFailed(true);
      }
    };

    void start();

    return () => {
      cancelled = true;
      cancelAnimationFrame(raf);
      observer?.disconnect();
      map?.remove();
      mapRef.current = null;
    };
  }, [teams]);

  if (failed) {
    return (
      <div className="map-wrap map-fallback">
        <p className="muted">Map tiles could not be loaded. Grounds are listed below.</p>
        <ul>
          {teams.map((t) => (
            <li key={t.id}>
              {t.name} — {venueOf(t) || t.city}
            </li>
          ))}
        </ul>
      </div>
    );
  }

  return (
    <div className="map-shell">
      <div ref={containerRef} className="map-wrap" />
      {selected && (
        <aside className="stadium-intel" aria-live="polite">
          {selected.crest ? <img src={selected.crest} alt="" className="crest-lg" /> : null}
          <div className="stat-value" style={{ fontSize: "1.5rem" }}>
            {selected.name}
          </div>
          <p className="muted" style={{ margin: "6px 0 12px" }}>
            {venueOf(selected)}
            {selected.city ? ` · ${selected.city}` : ""}
          </p>
          {weather ? (
            <div className="intel-weather">
              <span>{weather.icon}</span>
              <div>
                <strong>{weather.condition}</strong>
                <div className="muted">
                  {weather.temperature_c}°C
                  {weather.feels_like_c != null ? ` · feels ${weather.feels_like_c}°C` : ""}
                  {weather.humidity_pct != null ? ` · ${weather.humidity_pct}% humidity` : ""}
                  {weather.wind_kph != null ? ` · wind ${weather.wind_kph} kph` : ""}
                  {weather.wind_gust_kph != null ? ` · gust ${weather.wind_gust_kph} kph` : ""}
                </div>
              </div>
            </div>
          ) : (
            <p className="muted">Reading stadium conditions…</p>
          )}
        </aside>
      )}
    </div>
  );
}
