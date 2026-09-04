from __future__ import annotations
import os
import time
import httpx

CACHE_TTL = 600
_cache: dict[int, tuple[float, dict]] = {}

OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"

OPENWEATHER_GROUPS = {
    2: ("Thunderstorm", "⛈️"),
    3: ("Drizzle", "🌦️"),
    5: ("Rain", "🌧️"),
    6: ("Snow", "🌨️"),
    7: ("Fog", "🌫️"),
    8: ("Clouds", "☁️"),
}

OPENWEATHER_EXACT = {
    500: ("Light rain", "🌦️"),
    501: ("Rain", "🌧️"),
    502: ("Heavy rain", "🌧️"),
    503: ("Heavy rain", "🌧️"),
    504: ("Heavy rain", "🌧️"),
    511: ("Freezing rain", "🌧️"),
    520: ("Rain showers", "🌦️"),
    521: ("Rain showers", "🌧️"),
    522: ("Violent showers", "⛈️"),
    600: ("Light snow", "🌨️"),
    601: ("Snow", "🌨️"),
    602: ("Heavy snow", "❄️"),
    800: ("Clear sky", "☀️"),
    801: ("Mainly clear", "🌤️"),
    802: ("Partly cloudy", "⛅"),
    803: ("Overcast", "☁️"),
    804: ("Overcast", "☁️"),
}

WEATHER_CODES = {
    0: ("Clear sky", "☀️"),
    1: ("Mainly clear", "🌤️"),
    2: ("Partly cloudy", "⛅"),
    3: ("Overcast", "☁️"),
    45: ("Fog", "🌫️"),
    48: ("Fog", "🌫️"),
    51: ("Light drizzle", "🌦️"),
    53: ("Drizzle", "🌦️"),
    55: ("Dense drizzle", "🌧️"),
    61: ("Light rain", "🌦️"),
    63: ("Rain", "🌧️"),
    65: ("Heavy rain", "🌧️"),
    71: ("Light snow", "🌨️"),
    73: ("Snow", "🌨️"),
    75: ("Heavy snow", "❄️"),
    80: ("Rain showers", "🌦️"),
    81: ("Rain showers", "🌧️"),
    82: ("Violent showers", "⛈️"),
    95: ("Thunderstorm", "⛈️"),
    96: ("Thunderstorm + hail", "⛈️"),
    99: ("Thunderstorm + hail", "⛈️"),
}


def _impact(temp_c: float, wind_kph: float, precip_mm: float) -> float:
    impact = 0.0
    if wind_kph > 30:
        impact -= 0.08
    elif wind_kph > 20:
        impact -= 0.04
    if precip_mm > 5:
        impact -= 0.08
    elif precip_mm > 0.5:
        impact -= 0.03
    if temp_c < 2 or temp_c > 28:
        impact -= 0.03
    return round(impact, 2)


def _pack(
    temp: float,
    wind_kph: float,
    precip: float,
    condition: str,
    icon: str,
    feels_like: float | None = None,
    humidity: int | None = None,
    wind_gust_kph: float | None = None,
    cloud_pct: int | None = None,
) -> dict:
    effective_wind = max(wind_kph, wind_gust_kph) if wind_gust_kph is not None else wind_kph
    return {
        "temperature_c": round(temp, 1),
        "feels_like_c": round(feels_like, 1) if feels_like is not None else None,
        "humidity_pct": humidity,
        "wind_kph": round(wind_kph, 1),
        "wind_gust_kph": round(wind_gust_kph, 1) if wind_gust_kph is not None else None,
        "cloud_pct": cloud_pct,
        "precipitation_mm": round(precip, 1),
        "condition": condition,
        "icon": icon,
        "performance_impact": _impact(temp, effective_wind, precip),
    }


def _openweather_label(weather_id: int, fallback: str) -> tuple[str, str]:
    if weather_id in OPENWEATHER_EXACT:
        return OPENWEATHER_EXACT[weather_id]
    group = OPENWEATHER_GROUPS.get(weather_id // 100)
    if group:
        return group
    label = fallback.replace("_", " ").title() or "Unknown"
    return label, "🌡️"


async def _from_openweather(lat: float, lon: float, api_key: str) -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            OPENWEATHER_URL,
            params={"lat": lat, "lon": lon, "appid": api_key, "units": "metric"},
        )
        resp.raise_for_status()
        data = resp.json()

    condition = data.get("weather") or [{}]
    weather_id = int(condition[0].get("id") or 0)
    description = condition[0].get("description") or "Unknown"
    label, icon = _openweather_label(weather_id, description)
    main = data.get("main") or {}
    wind = data.get("wind") or {}
    rain = data.get("rain") or {}
    snow = data.get("snow") or {}
    clouds = data.get("clouds") or {}
    temp = float(main.get("temp", 15.0))
    feels = main.get("feels_like")
    humidity = main.get("humidity")
    wind_ms = float(wind.get("speed", 0.0))
    gust_ms = wind.get("gust")
    precip = float(rain.get("1h") or rain.get("3h") or snow.get("1h") or snow.get("3h") or 0.0)
    return _pack(
        temp,
        wind_ms * 3.6,
        precip,
        label,
        icon,
        feels_like=float(feels) if feels is not None else None,
        humidity=int(humidity) if humidity is not None else None,
        wind_gust_kph=float(gust_ms) * 3.6 if gust_ms is not None else None,
        cloud_pct=int(clouds["all"]) if clouds.get("all") is not None else None,
    )


async def _from_open_meteo(lat: float, lon: float) -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,wind_gusts_10m,precipitation,cloud_cover,weather_code",
            },
        )
        resp.raise_for_status()
        current = resp.json().get("current", {})

    code = current.get("weather_code", 0)
    label, icon = WEATHER_CODES.get(code, ("Unknown", "🌡️"))
    temp = float(current.get("temperature_2m", 15.0))
    apparent = current.get("apparent_temperature")
    humidity = current.get("relative_humidity_2m")
    wind = float(current.get("wind_speed_10m", 0.0))
    gust = current.get("wind_gusts_10m")
    precip = float(current.get("precipitation", 0.0))
    clouds = current.get("cloud_cover")
    return _pack(
        temp,
        wind,
        precip,
        label,
        icon,
        feels_like=float(apparent) if apparent is not None else None,
        humidity=int(humidity) if humidity is not None else None,
        wind_gust_kph=float(gust) if gust is not None else None,
        cloud_pct=int(clouds) if clouds is not None else None,
    )


async def current_weather(lat: float, lon: float) -> dict:
    cache_key = round(lat * 100) * 100000 + round(lon * 100)
    cached = _cache.get(cache_key)
    if cached and time.time() - cached[0] < CACHE_TTL:
        return cached[1]

    api_key = os.environ.get("OPENWEATHER_API_KEY", "").strip()
    if api_key:
        try:
            result = await _from_openweather(lat, lon, api_key)
        except Exception:
            result = await _from_open_meteo(lat, lon)
    else:
        result = await _from_open_meteo(lat, lon)

    _cache[cache_key] = (time.time(), result)
    return result
