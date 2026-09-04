from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import BaseModel, Field
from app.services.engine import (
    predict,
    simulate_remaining_season,
    distance_km,
    finished_appearances,
    remaining_fixtures,
    upcoming_fixtures,
    head_to_head,
    profile_team,
    model_confidence,
    key_factors,
    normalize_formation,
    parse_utc,
    rest_days_since,
    rest_fatigue,
    age_years,
)
from app.services.stadiums import STADIUM_COORDS, stadium_for
from app.services import weather as weather_service
from app.services import gemini as gemini_service
from app.providers import football_data as fd
from app.security import public_error_detail

router = APIRouter()


def _now_iso(ts: float | None = None) -> str:
    if ts is None:
        return datetime.now(timezone.utc).isoformat()
    return datetime.fromtimestamp(ts, timezone.utc).isoformat()


async def _competition_matches(season: int | None = None) -> list[dict]:
    try:
        data = await fd.competition_matches(season=season)
        return data.get("matches") or []
    except Exception:
        return []


def _season_meta(payload: dict | None) -> dict:
    payload = payload or {}
    season = payload.get("season") or {}
    start = season.get("startDate")
    end = season.get("endDate")
    label = None
    if start and end and len(start) >= 4 and len(end) >= 4:
        label = f"{start[:4]}/{end[2:4]}" if start[:4] != end[:4] else start[:4]
    return {
        "current_matchday": season.get("currentMatchday"),
        "start_date": start,
        "end_date": end,
        "label": label,
        "last_updated": payload.get("lastUpdated"),
        "winner": (season.get("winner") or {}).get("name") if isinstance(season.get("winner"), dict) else season.get("winner"),
    }


def _previous_season_year(payload: dict | None) -> int | None:
    start = ((payload or {}).get("season") or {}).get("startDate")
    if not start or len(start) < 4:
        return None
    try:
        return int(start[:4]) - 1
    except ValueError:
        return None


async def _previous_season_matches(standings_payload: dict | None) -> list[dict]:
    year = _previous_season_year(standings_payload)
    if year is None:
        return []
    return await _competition_matches(season=year)


def _pack_coach(raw: dict | None) -> dict | None:
    if not raw:
        return None
    name = raw.get("name") or " ".join(part for part in [raw.get("firstName"), raw.get("lastName")] if part).strip() or None
    if not name and raw.get("nationality") is None and raw.get("dateOfBirth") is None:
        return None
    contract = raw.get("contract") or {}
    return {
        "name": name,
        "nationality": raw.get("nationality"),
        "date_of_birth": raw.get("dateOfBirth"),
        "age": age_years(raw.get("dateOfBirth")),
        "contract_start": contract.get("start"),
        "contract_until": contract.get("until"),
    }


def _pack_player(raw: dict, scorer: dict | None = None) -> dict:
    return {
        "id": raw.get("id"),
        "name": raw.get("name"),
        "position": raw.get("position") or raw.get("section"),
        "nationality": raw.get("nationality"),
        "date_of_birth": raw.get("dateOfBirth"),
        "age": age_years(raw.get("dateOfBirth")),
        "shirt_number": raw.get("shirtNumber"),
        "goals": (scorer or {}).get("goals"),
        "assists": (scorer or {}).get("assists"),
        "penalties": (scorer or {}).get("penalties"),
        "played_matches": (scorer or {}).get("playedMatches") or (scorer or {}).get("played_matches"),
    }


def _pack_scorer(row: dict) -> dict:
    player = row.get("player") or {}
    team = row.get("team") or {}
    return {
        "player_id": player.get("id"),
        "name": player.get("name"),
        "nationality": player.get("nationality"),
        "position": player.get("position") or player.get("section"),
        "date_of_birth": player.get("dateOfBirth"),
        "age": age_years(player.get("dateOfBirth")),
        "team_id": team.get("id"),
        "team_name": team.get("name"),
        "crest": team.get("crest"),
        "played_matches": row.get("playedMatches"),
        "goals": row.get("goals"),
        "assists": row.get("assists"),
        "penalties": row.get("penalties"),
    }


async def _scorers_rows() -> tuple[list[dict], dict]:
    try:
        data = await fd.scorers()
        return [_pack_scorer(row) for row in (data.get("scorers") or [])], data
    except Exception:
        return [], {}


def _standings_table(payload: dict) -> list[dict]:
    tables = payload.get("standings") or []
    total = next((block for block in tables if block.get("type") == "TOTAL"), tables[0] if tables else None)
    return (total or {}).get("table") or []

def _location_fields(team_id: int, live_venue: str | None = None) -> dict:
    loc = stadium_for(team_id)
    venue = loc["stadium"] if team_id in STADIUM_COORDS else (live_venue or loc["stadium"])
    return {"venue": venue, "stadium": venue, "city": loc["city"], "lat": loc["lat"], "lon": loc["lon"]}


def _fallback_team(team_id: int, name: str, short_name: str, tla: str) -> dict:
    return {
        "id": team_id,
        "name": name,
        "short_name": short_name,
        "tla": tla,
        "crest": f"https://crests.football-data.org/{team_id}.png",
        **_location_fields(team_id),
    }


FALLBACK_TEAMS = [
    _fallback_team(57, "Arsenal FC", "Arsenal", "ARS"),
    _fallback_team(61, "Chelsea FC", "Chelsea", "CHE"),
    _fallback_team(64, "Liverpool FC", "Liverpool", "LIV"),
    _fallback_team(65, "Manchester City FC", "Man City", "MCI"),
    _fallback_team(66, "Manchester United FC", "Man United", "MUN"),
    _fallback_team(73, "Tottenham Hotspur FC", "Tottenham", "TOT"),
]


async def _standings_payload() -> dict:
    return await fd.standings()


async def _standings_rows():
    return _standings_table(await _standings_payload())


@router.get("/standings")
async def standings():
    try:
        payload = await _standings_payload()
        table = _standings_table(payload)
        season = _season_meta(payload)
        return {
            "source": "live",
            "fetched_at": _now_iso(fd.cache_fetched_at("/competitions/PL/standings")),
            "current_matchday": season["current_matchday"],
            "season": season,
            "table": [
                {
                    "position": row["position"],
                    "team_id": row["team"]["id"],
                    "name": row["team"]["name"],
                    "short_name": row["team"]["shortName"],
                    "crest": row["team"]["crest"],
                    "played": row["playedGames"],
                    "won": row["won"],
                    "draw": row["draw"],
                    "lost": row["lost"],
                    "points": row["points"],
                    "goals_for": row["goalsFor"],
                    "goals_against": row["goalsAgainst"],
                    "goal_difference": row["goalDifference"],
                    "form": row.get("form"),
                }
                for row in table
            ],
        }
    except Exception:
        return {
            "source": "fallback",
            "fetched_at": _now_iso(),
            "current_matchday": None,
            "season": None,
            "table": [],
        }


@router.get("/teams")
async def teams():
    try:
        data = await fd.teams()
        return {
            "source": "live",
            "fetched_at": _now_iso(fd.cache_fetched_at("/competitions/PL/teams")),
            "teams": [
                {
                    "id": t["id"],
                    "name": t["name"],
                    "short_name": t["shortName"],
                    "tla": t["tla"],
                    "crest": t["crest"],
                    "website": t.get("website"),
                    "club_colors": t.get("clubColors"),
                    "founded": t.get("founded"),
                    "last_updated": t.get("lastUpdated"),
                    **_location_fields(t["id"], t.get("venue")),
                }
                for t in data["teams"]
            ],
        }
    except Exception:
        return {"source": "fallback", "fetched_at": _now_iso(), "teams": FALLBACK_TEAMS}


@router.get("/teams/{team_id}")
async def team_detail(team_id: int = Path(ge=1, le=999_999)):
    try:
        t = await fd.team(team_id)
        scorers, _ = await _scorers_rows()
        by_player = {row["player_id"]: row for row in scorers if row.get("player_id")}
        coach = _pack_coach(t.get("coach") if isinstance(t.get("coach"), dict) else None)
        return {
            "source": "live",
            "fetched_at": _now_iso(),
            "id": t["id"],
            "name": t["name"],
            "crest": t["crest"],
            "website": t.get("website"),
            "address": t.get("address"),
            "club_colors": t.get("clubColors"),
            "founded": t.get("founded"),
            "last_updated": t.get("lastUpdated"),
            "coach": coach["name"] if coach else None,
            "coach_detail": coach,
            "squad": [_pack_player(p, by_player.get(p.get("id"))) for p in t.get("squad", [])],
            **_location_fields(team_id, t.get("venue")),
        }
    except Exception:
        raise HTTPException(status_code=502, detail=public_error_detail())


@router.get("/scorers")
async def competition_scorers():
    rows, payload = await _scorers_rows()
    if not rows:
        return {
            "source": "fallback",
            "fetched_at": _now_iso(),
            "season": _season_meta(payload) if payload else None,
            "scorers": [],
        }
    return {
        "source": "live",
        "fetched_at": _now_iso(fd.cache_fetched_at("/competitions/PL/scorers", {"limit": 20})),
        "season": _season_meta(payload),
        "scorers": rows,
    }


@router.get("/fixtures/upcoming")
async def fixtures_upcoming(limit: int = Query(12, ge=1, le=40)):
    try:
        matches = await _competition_matches()
        if not matches:
            return {
                "source": "fallback",
                "fetched_at": _now_iso(),
                "current_matchday": None,
                "fixtures": [],
            }
        ids: set[int] = set()
        for match in matches:
            home_id = (match.get("homeTeam") or {}).get("id")
            away_id = (match.get("awayTeam") or {}).get("id")
            if home_id:
                ids.add(home_id)
            if away_id:
                ids.add(away_id)
        fx = upcoming_fixtures(matches, ids, limit=max(1, min(limit, 40)))
        matchdays = [row.get("matchday") for row in fx if row.get("matchday") is not None]
        return {
            "source": "live",
            "fetched_at": _now_iso(fd.cache_fetched_at("/competitions/PL/matches")),
            "current_matchday": matchdays[0] if matchdays else None,
            "fixtures": fx,
        }
    except Exception:
        return {
            "source": "fallback",
            "fetched_at": _now_iso(),
            "current_matchday": None,
            "fixtures": [],
        }


ALLOWED_MATCH_STATUS = {
    "SCHEDULED",
    "TIMED",
    "LIVE",
    "IN_PLAY",
    "PAUSED",
    "FINISHED",
    "POSTPONED",
    "CANCELLED",
    "AWARDED",
}


@router.get("/teams/{team_id}/matches")
async def team_matches(
    team_id: int = Path(ge=1, le=999_999),
    status: str = Query("SCHEDULED"),
    limit: int = Query(5, ge=1, le=20),
):
    if status not in ALLOWED_MATCH_STATUS:
        status = "SCHEDULED"
    try:
        data = await fd.matches_for_team(team_id, status=status, limit=limit)
        return {
            "source": "live",
            "matches": [
                {
                    "id": m["id"],
                    "utc_date": m["utcDate"],
                    "competition": m["competition"]["name"],
                    "status": m["status"],
                    "home": {"id": m["homeTeam"]["id"], "name": m["homeTeam"]["name"], "crest": m["homeTeam"]["crest"]},
                    "away": {"id": m["awayTeam"]["id"], "name": m["awayTeam"]["name"], "crest": m["awayTeam"]["crest"]},
                    "score": m.get("score", {}).get("fullTime"),
                    "half_time": m.get("score", {}).get("halfTime"),
                    "matchday": m.get("matchday"),
                }
                for m in data.get("matches", [])
            ],
        }
    except Exception:
        return {"source": "fallback", "matches": []}


@router.get("/teams/{team_id}/weather")
async def team_weather(team_id: int = Path(ge=1, le=999_999)):
    stadium = stadium_for(team_id)
    forecast = await weather_service.current_weather(stadium["lat"], stadium["lon"])
    return {"stadium": stadium, "weather": forecast}


@router.get("/stadiums/distance/{a}/{b}")
def stadium_distance(a: int = Path(ge=1, le=999_999), b: int = Path(ge=1, le=999_999)):
    x, y = stadium_for(a), stadium_for(b)
    return {
        "from": x["stadium"],
        "to": y["stadium"],
        "distance_km": round(distance_km(x["lat"], x["lon"], y["lat"], y["lon"]), 1),
    }


class MatchRequest(BaseModel):
    home_attack: float = Field(1.6, ge=0.1, le=5)
    home_defence: float = Field(1.1, ge=0.1, le=5)
    away_attack: float = Field(1.4, ge=0.1, le=5)
    away_defence: float = Field(1.2, ge=0.1, le=5)
    simulations: int = Field(10000, ge=100, le=10000)
    home_formation: str = "4-3-3"
    away_formation: str = "4-2-3-1"
    recent_form_home: list[float] = Field(default_factory=list, max_length=10)
    recent_form_away: list[float] = Field(default_factory=list, max_length=10)


@router.post("/predict")
def prediction(req: MatchRequest):
    """Manual prediction with custom attack/defence inputs."""
    payload = req.model_dump()
    payload["home_formation"] = normalize_formation(payload.get("home_formation"), "4-3-3")
    payload["away_formation"] = normalize_formation(payload.get("away_formation"), "4-2-3-1")
    return predict(**payload)


@router.get("/predict/{home_id}/{away_id}")
async def prediction_live(
    home_id: int = Path(ge=1, le=999_999),
    away_id: int = Path(ge=1, le=999_999),
    simulations: int = Query(10000, ge=100, le=10000),
    home_formation: str = Query("4-3-3"),
    away_formation: str = Query("4-2-3-1"),
):
    """Live prediction from standings, recent matches when available, weather, travel, and assumed formations."""
    home_formation = normalize_formation(home_formation, "4-3-3")
    away_formation = normalize_formation(away_formation, "4-2-3-1")
    try:
        payload = await _standings_payload()
        table = _standings_table(payload)
        rows = {row["team"]["id"]: row for row in table}
        if home_id not in rows or away_id not in rows:
            raise HTTPException(status_code=404, detail="Unknown team id")
        home_row, away_row = rows[home_id], rows[away_id]
        matches = await _competition_matches()
        prior_matches = await _previous_season_matches(payload)
        live_matches = bool(matches)
        home_apps = finished_appearances(matches, home_id)
        away_apps = finished_appearances(matches, away_id)
        home_prior = finished_appearances(prior_matches, home_id)
        away_prior = finished_appearances(prior_matches, away_id)
        h2h = head_to_head(matches + prior_matches, home_id, away_id)
        home_h2h = h2h
        away_h2h = None
        if h2h and h2h.get("usable_in_model"):
            away_h2h = {
                "attack": h2h["defence"],
                "defence": h2h["attack"],
                "usable_in_model": True,
            }
        home_profile = profile_team(home_id, home_row, home_apps, "home", home_prior, home_h2h)
        away_profile = profile_team(away_id, away_row, away_apps, "away", away_prior, away_h2h)

        home_stadium, away_stadium = stadium_for(home_id), stadium_for(away_id)
        forecast = await weather_service.current_weather(home_stadium["lat"], home_stadium["lon"])
        travel_km = distance_km(home_stadium["lat"], home_stadium["lon"], away_stadium["lat"], away_stadium["lon"])
        away_travel_fatigue = round(min(0.15, travel_km / 6000), 2)

        remaining = remaining_fixtures(matches, set(rows))
        listed = next(
            (fx for fx in remaining if fx["home_id"] == home_id and fx["away_id"] == away_id),
            None,
        )
        kickoff = parse_utc((listed or {}).get("utc_date"))
        home_rest_days = rest_days_since(home_profile.get("last_finished_utc"), kickoff)
        away_rest_days = rest_days_since(away_profile.get("last_finished_utc"), kickoff)
        home_rest_fatigue = rest_fatigue(home_rest_days)
        away_rest_fatigue = rest_fatigue(away_rest_days)
        rest = {
            "home_days": home_rest_days,
            "away_days": away_rest_days,
            "home_fatigue": home_rest_fatigue,
            "away_fatigue": away_rest_fatigue,
            "relative_to": (listed or {}).get("utc_date"),
        }

        result = predict(
            home_profile["attack"],
            home_profile["defence"],
            away_profile["attack"],
            away_profile["defence"],
            simulations=simulations,
            home_formation=home_formation,
            away_formation=away_formation,
            weather_impact_home=forecast["performance_impact"],
            weather_impact_away=forecast["performance_impact"],
            fatigue_home=home_rest_fatigue,
            fatigue_away=away_travel_fatigue + away_rest_fatigue,
        )
        result["model"] = {
            "live_matches": live_matches,
            "used_form": home_profile["used_form"] or away_profile["used_form"],
            "used_home_away": home_profile["used_home_away"] or away_profile["used_home_away"],
            "used_h2h": home_profile["used_h2h"] or away_profile["used_h2h"],
            "used_second_half": home_profile["used_second_half"] or away_profile["used_second_half"],
            "used_prior_venue": home_profile.get("venue_source") == "current_plus_prior"
            or away_profile.get("venue_source") == "current_plus_prior",
            "home_weights": home_profile["weights"],
            "away_weights": away_profile["weights"],
            "home_form": home_profile["form"],
            "away_form": away_profile["form"],
            "home_venue": home_profile["venue"],
            "away_venue": away_profile["venue"],
            "home_venue_source": home_profile.get("venue_source"),
            "away_venue_source": away_profile.get("venue_source"),
            "home_second_half": home_profile.get("second_half"),
            "away_second_half": away_profile.get("second_half"),
            "prior_season_matches": len(prior_matches),
            "fallback_season_only": not live_matches,
        }
        result["confidence"] = model_confidence(result["probabilities"], home_profile, away_profile, live_matches)
        result["key_factors"] = key_factors(
            home_row["team"]["name"],
            away_row["team"]["name"],
            result,
            forecast,
            round(travel_km, 1),
            away_travel_fatigue,
            rest=rest,
            h2h=h2h,
        )
        result["context"] = {
            "home_team": home_row["team"]["name"],
            "away_team": away_row["team"]["name"],
            "weather": forecast,
            "away_travel_km": round(travel_km, 1),
            "away_fatigue_penalty": away_travel_fatigue,
            "rest": rest,
            "head_to_head": h2h,
            "fixture": listed,
            "home_last_completed": home_profile.get("last_completed"),
            "away_last_completed": away_profile.get("last_completed"),
            "season": _season_meta(payload),
            "fetched_at": _now_iso(),
        }
        gemini_facts = {
            "home": home_row["team"]["name"],
            "away": away_row["team"]["name"],
            "expected_goals": result["expected_goals"],
            "probabilities": result["probabilities"],
            "most_likely_score": result["most_likely_score"],
            "scorelines": result["scorelines"],
            "scenarios": result["scenarios"],
            "confidence": result["confidence"]["level"],
            "weather": forecast.get("condition"),
            "temperature_c": forecast.get("temperature_c"),
            "away_travel_km": round(travel_km, 1),
            "formations_assumed": True,
            "home_formation": home_formation,
            "away_formation": away_formation,
        }
        if home_rest_days is not None:
            gemini_facts["home_rest_days"] = home_rest_days
        if away_rest_days is not None:
            gemini_facts["away_rest_days"] = away_rest_days
        if h2h and h2h.get("played"):
            gemini_facts["h2h_played"] = h2h["played"]
        result["ai"] = await asyncio.to_thread(gemini_service.brief_prediction, gemini_facts)
        return result
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=502, detail=public_error_detail())


async def _season_iq(simulations: int = 2000):
    try:
        payload = await _standings_payload()
        table = _standings_table(payload)
        rows = {row["team"]["id"]: row for row in table}
        matches = await _competition_matches()
        season = _season_meta(payload)
        if not matches:
            return {
                "available": False,
                "mode": "unavailable",
                "reason": "Fixture data could not be retrieved from the live provider.",
                "source": "fallback",
                "fetched_at": _now_iso(),
                "season": season,
                "simulations": 0,
                "fixture_count": 0,
                "teams": [],
            }
        prior_matches = await _previous_season_matches(payload)
        home_profiles = {}
        away_profiles = {}
        last_utc_by_team: dict[int, str | None] = {}
        for team_id, row in rows.items():
            apps = finished_appearances(matches, team_id)
            prior = finished_appearances(prior_matches, team_id)
            home_profiles[team_id] = profile_team(team_id, row, apps, "home", prior)
            away_profiles[team_id] = profile_team(team_id, row, apps, "away", prior)
            last_utc_by_team[team_id] = home_profiles[team_id].get("last_finished_utc")
        fixtures = remaining_fixtures(matches, set(rows))
        result = simulate_remaining_season(
            home_profiles,
            away_profiles,
            fixtures,
            simulations=simulations,
            last_utc_by_team=last_utc_by_team,
        )
        result["source"] = "live"
        result["fetched_at"] = _now_iso(fd.cache_fetched_at("/competitions/PL/matches"))
        result["season"] = season
        result["prior_season_matches"] = len(prior_matches)
        return result
    except Exception:
        return {
            "available": False,
            "mode": "unavailable",
            "reason": "Live standings or fixtures were unavailable.",
            "source": "fallback",
            "fetched_at": _now_iso(),
            "season": None,
            "simulations": 0,
            "fixture_count": 0,
            "teams": [],
        }


@router.get("/season/iq")
async def season_iq(simulations: int = Query(2000, ge=100, le=5000)):
    return await _season_iq(simulations)


@router.post("/season/simulate")
async def season():
    return await _season_iq()
