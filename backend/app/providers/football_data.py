from __future__ import annotations
import os
import time
import httpx

BASE_URL = "https://api.football-data.org/v4"
CACHE_TTL = 60
PREV_SEASON_TTL = 1800
SCORERS_TTL = 300

_cache: dict[str, tuple[float, dict]] = {}


def _headers():
    key = os.environ.get("FOOTBALL_DATA_API_KEY", "")
    return {"X-Auth-Token": key} if key else {}


async def _get(path: str, params: dict | None = None, ttl: int = CACHE_TTL) -> dict:
    cache_key = f"{path}?{params}"
    cached = _cache.get(cache_key)
    if cached and time.time() - cached[0] < ttl:
        return cached[1]

    async with httpx.AsyncClient(base_url=BASE_URL, headers=_headers(), timeout=12) as client:
        try:
            resp = await client.get(path, params=params or {})
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as exc:
            raise RuntimeError("Football data request failed") from exc

    _cache[cache_key] = (time.time(), data)
    return data


async def standings(competition: str = "PL") -> dict:
    return await _get(f"/competitions/{competition}/standings")


async def teams(competition: str = "PL") -> dict:
    return await _get(f"/competitions/{competition}/teams")


async def team(team_id: int) -> dict:
    return await _get(f"/teams/{team_id}")


async def matches_for_team(team_id: int, status: str = "SCHEDULED", limit: int = 5) -> dict:
    return await _get(f"/teams/{team_id}/matches", {"status": status, "limit": limit})


async def competition_matches(competition: str = "PL", season: int | None = None) -> dict:
    params = {"season": season} if season is not None else None
    ttl = PREV_SEASON_TTL if season is not None else CACHE_TTL
    return await _get(f"/competitions/{competition}/matches", params, ttl=ttl)


async def scorers(competition: str = "PL", limit: int = 20) -> dict:
    return await _get(f"/competitions/{competition}/scorers", {"limit": limit}, ttl=SCORERS_TTL)


def cache_fetched_at(path: str, params: dict | None = None) -> float | None:
    cached = _cache.get(f"{path}?{params}")
    return cached[0] if cached else None
