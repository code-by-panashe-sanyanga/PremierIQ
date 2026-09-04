from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from math import asin, cos, radians, sin, sqrt

import numpy as np

FORMATION = {
    "4-4-2": 0,
    "4-3-3": 0.04,
    "4-2-3-1": 0.03,
    "3-5-2": 0.02,
    "5-3-2": -0.04,
    "3-4-3": 0.05,
}

FORMATION_PERSONA = {
    "4-4-2": "BALANCED",
    "4-3-3": "ATTACKING",
    "4-2-3-1": "CONTROL",
    "3-5-2": "WIDE",
    "5-3-2": "DEFENSIVE",
    "3-4-3": "ATTACKING",
}

FINISHED_STATUSES = {"FINISHED", "AWARDED"}
REMAINING_STATUSES = {"SCHEDULED", "TIMED", "IN_PLAY", "PAUSED", "LIVE"}
SEASON_WEIGHT = 0.60
FORM_WEIGHT = 0.30
VENUE_WEIGHT = 0.10
H2H_WEIGHT = 0.05
SECOND_HALF_WEIGHT = 0.05
FORM_WINDOW = 5
MIN_VENUE_SAMPLE = 3
MIN_H2H_SAMPLE = 2
MIN_SECOND_HALF_SAMPLE = 3


def normalize_formation(value: str | None, default: str = "4-3-3") -> str:
    if value in FORMATION:
        return value
    return default


def strengths_from_standing(row: dict) -> tuple[float, float]:
    """Season attack/defence as goals scored/conceded per game."""
    played = max(1, int(row.get("playedGames") or 0))
    attack = float(row.get("goalsFor") or 0) / played
    defence = float(row.get("goalsAgainst") or 0) / played
    return round(max(0.3, attack), 2), round(max(0.3, defence), 2)


def parse_utc(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def age_years(date_of_birth: str | None) -> int | None:
    if not date_of_birth:
        return None
    try:
        born = datetime.fromisoformat(date_of_birth[:10]).date()
    except ValueError:
        return None
    today = datetime.now(timezone.utc).date()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def rest_days_between(prev: datetime | None, nxt: datetime | None) -> int | None:
    if prev is None or nxt is None:
        return None
    if prev.tzinfo is None:
        prev = prev.replace(tzinfo=timezone.utc)
    if nxt.tzinfo is None:
        nxt = nxt.replace(tzinfo=timezone.utc)
    return max(0, (nxt - prev).days)


def rest_days_since(last_utc: str | None, as_of: datetime | None = None) -> int | None:
    last = parse_utc(last_utc)
    if last is None:
        return None
    return rest_days_between(last, as_of or datetime.now(timezone.utc))


def rest_fatigue(days: int | None) -> float:
    if days is None:
        return 0.0
    if days <= 2:
        return 0.06
    if days <= 3:
        return 0.03
    return 0.0


def _half_time(match: dict) -> tuple[int, int] | None:
    ht = (match.get("score") or {}).get("halfTime") or {}
    home, away = ht.get("home"), ht.get("away")
    if home is None or away is None:
        return None
    try:
        return int(home), int(away)
    except (TypeError, ValueError):
        return None


def _full_time(match: dict) -> tuple[int, int] | None:
    ft = (match.get("score") or {}).get("fullTime") or {}
    home, away = ft.get("home"), ft.get("away")
    if home is None or away is None:
        return None
    try:
        return int(home), int(away)
    except (TypeError, ValueError):
        return None


def finished_appearances(matches: list[dict], team_id: int) -> list[dict]:
    rows: list[dict] = []
    for match in matches:
        if match.get("status") not in FINISHED_STATUSES:
            continue
        home_id = (match.get("homeTeam") or {}).get("id")
        away_id = (match.get("awayTeam") or {}).get("id")
        if team_id not in (home_id, away_id):
            continue
        score = _full_time(match)
        if score is None:
            continue
        is_home = home_id == team_id
        gf, ga = (score[0], score[1]) if is_home else (score[1], score[0])
        if gf > ga:
            result = "W"
        elif gf == ga:
            result = "D"
        else:
            result = "L"
        ht = _half_time(match)
        if ht is not None:
            gf_ht, ga_ht = (ht[0], ht[1]) if is_home else (ht[1], ht[0])
            gf_2h, ga_2h = gf - gf_ht, ga - ga_ht
        else:
            gf_ht = ga_ht = gf_2h = ga_2h = None
        rows.append(
            {
                "utc_date": match.get("utcDate") or "",
                "matchday": match.get("matchday"),
                "home": is_home,
                "gf": gf,
                "ga": ga,
                "gf_ht": gf_ht,
                "ga_ht": ga_ht,
                "gf_2h": gf_2h,
                "ga_2h": ga_2h,
                "result": result,
                "gd": gf - ga,
                "opponent_id": away_id if is_home else home_id,
            }
        )
    rows.sort(key=lambda row: row["utc_date"], reverse=True)
    return rows


def remaining_fixtures(matches: list[dict], known_ids: set[int]) -> list[dict]:
    fixtures: list[dict] = []
    for match in matches:
        if match.get("status") not in REMAINING_STATUSES:
            continue
        home_id = (match.get("homeTeam") or {}).get("id")
        away_id = (match.get("awayTeam") or {}).get("id")
        if home_id not in known_ids or away_id not in known_ids:
            continue
        if home_id == away_id:
            continue
        referee = None
        refs = match.get("referees") or []
        if refs and isinstance(refs[0], dict) and refs[0].get("name"):
            referee = refs[0]["name"]
        fixtures.append(
            {
                "id": match.get("id"),
                "home_id": home_id,
                "away_id": away_id,
                "home_name": (match.get("homeTeam") or {}).get("name"),
                "away_name": (match.get("awayTeam") or {}).get("name"),
                "home_crest": (match.get("homeTeam") or {}).get("crest"),
                "away_crest": (match.get("awayTeam") or {}).get("crest"),
                "home_tla": (match.get("homeTeam") or {}).get("tla"),
                "away_tla": (match.get("awayTeam") or {}).get("tla"),
                "utc_date": match.get("utcDate"),
                "matchday": match.get("matchday"),
                "status": match.get("status"),
                "last_updated": match.get("lastUpdated"),
                "referee": referee,
            }
        )
    fixtures.sort(key=lambda row: row["utc_date"] or "")
    return fixtures


def upcoming_fixtures(matches: list[dict], known_ids: set[int], limit: int = 12) -> list[dict]:
    now = datetime.now(timezone.utc)
    out = []
    for fx in remaining_fixtures(matches, known_ids):
        kickoff = parse_utc(fx.get("utc_date"))
        if kickoff and kickoff < now and fx.get("status") not in {"IN_PLAY", "PAUSED", "LIVE"}:
            continue
        out.append(fx)
        if len(out) >= limit:
            break
    return out


def head_to_head(matches: list[dict], home_id: int, away_id: int) -> dict | None:
    rows = []
    for match in matches:
        if match.get("status") not in FINISHED_STATUSES:
            continue
        hid = (match.get("homeTeam") or {}).get("id")
        aid = (match.get("awayTeam") or {}).get("id")
        if {hid, aid} != {home_id, away_id}:
            continue
        score = _full_time(match)
        if score is None:
            continue
        rows.append(
            {
                "utc_date": match.get("utcDate"),
                "home_id": hid,
                "away_id": aid,
                "home_goals": score[0],
                "away_goals": score[1],
                "score": f"{score[0]}-{score[1]}",
            }
        )
    if not rows:
        return None
    rows.sort(key=lambda row: row["utc_date"] or "", reverse=True)
    home_gf = 0.0
    home_ga = 0.0
    for row in rows:
        if row["home_id"] == home_id:
            home_gf += row["home_goals"]
            home_ga += row["away_goals"]
        else:
            home_gf += row["away_goals"]
            home_ga += row["home_goals"]
    n = len(rows)
    return {
        "played": n,
        "matches": rows[:6],
        "attack": round(max(0.3, home_gf / n), 2),
        "defence": round(max(0.3, home_ga / n), 2),
        "usable_in_model": n >= MIN_H2H_SAMPLE,
    }


def _rates(rows: list[dict], recency: bool = False) -> dict | None:
    if not rows:
        return None
    n = len(rows)
    if recency and n > 1:
        weights = [n - i for i in range(n)]
        wsum = float(sum(weights))
        attack = max(0.3, sum(row["gf"] * w for row, w in zip(rows, weights)) / wsum)
        defence = max(0.3, sum(row["ga"] * w for row, w in zip(rows, weights)) / wsum)
        recency_weighted = True
    else:
        attack = max(0.3, sum(row["gf"] for row in rows) / n)
        defence = max(0.3, sum(row["ga"] for row in rows) / n)
        recency_weighted = False
    wins = sum(1 for row in rows if row["result"] == "W")
    draws = sum(1 for row in rows if row["result"] == "D")
    losses = sum(1 for row in rows if row["result"] == "L")
    return {
        "played": n,
        "attack": round(attack, 2),
        "defence": round(defence, 2),
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "form": "".join(row["result"] for row in rows),
        "avg_gd": round(sum(row["gd"] for row in rows) / n, 2),
        "recency_weighted": recency_weighted,
    }


def _second_half_rates(rows: list[dict]) -> dict | None:
    usable = [row for row in rows if row.get("gf_2h") is not None and row.get("ga_2h") is not None]
    if len(usable) < MIN_SECOND_HALF_SAMPLE:
        return None
    n = len(usable)
    return {
        "played": n,
        "attack": round(max(0.3, sum(row["gf_2h"] for row in usable) / n), 2),
        "defence": round(max(0.3, sum(row["ga_2h"] for row in usable) / n), 2),
    }


def last_completed_summary(appearances: list[dict]) -> dict | None:
    if not appearances:
        return None
    row = appearances[0]
    out: dict = {
        "utc_date": row.get("utc_date") or None,
        "matchday": row.get("matchday"),
        "result": row.get("result"),
        "score": f"{row['gf']}-{row['ga']}",
        "home": row.get("home"),
    }
    if row.get("gf_ht") is not None and row.get("ga_ht") is not None:
        out["half_time"] = f"{row['gf_ht']}-{row['ga_ht']}"
        out["second_half"] = f"{row['gf_2h']}-{row['ga_2h']}"
    return out


def last_finished_utc(appearances: list[dict]) -> str | None:
    if not appearances:
        return None
    return appearances[0].get("utc_date") or None


def blend_strengths(
    season_attack: float,
    season_defence: float,
    form: dict | None,
    venue: dict | None,
    h2h: dict | None = None,
    second_half: dict | None = None,
) -> dict:
    weights = [SEASON_WEIGHT]
    attacks = [season_attack]
    defences = [season_defence]
    used = {
        "season": SEASON_WEIGHT,
        "form": 0.0,
        "home_away": 0.0,
        "h2h": 0.0,
        "second_half": 0.0,
    }
    if form:
        weights.append(FORM_WEIGHT)
        attacks.append(form["attack"])
        defences.append(form["defence"])
        used["form"] = FORM_WEIGHT
    if venue:
        weights.append(VENUE_WEIGHT)
        attacks.append(venue["attack"])
        defences.append(venue["defence"])
        used["home_away"] = VENUE_WEIGHT
    if h2h:
        weights.append(H2H_WEIGHT)
        attacks.append(h2h["attack"])
        defences.append(h2h["defence"])
        used["h2h"] = H2H_WEIGHT
    if second_half:
        weights.append(SECOND_HALF_WEIGHT)
        attacks.append(second_half["attack"])
        defences.append(second_half["defence"])
        used["second_half"] = SECOND_HALF_WEIGHT
    total = sum(weights)
    attack = sum((weight / total) * value for weight, value in zip(weights, attacks))
    defence = sum((weight / total) * value for weight, value in zip(weights, defences))
    scale = 1.0 / total
    return {
        "attack": round(max(0.3, attack), 2),
        "defence": round(max(0.3, defence), 2),
        "weights": {key: round(value * scale, 2) for key, value in used.items()},
        "used_form": bool(form),
        "used_home_away": bool(venue),
        "used_h2h": bool(h2h),
        "used_second_half": bool(second_half),
    }


def profile_team(
    team_id: int,
    standing: dict,
    appearances: list[dict],
    venue: str,
    prior_appearances: list[dict] | None = None,
    h2h_rates: dict | None = None,
) -> dict:
    prior_appearances = prior_appearances or []
    season_attack, season_defence = strengths_from_standing(standing)
    recent = appearances[:FORM_WINDOW]
    form = _rates(recent, recency=True)
    venue_flag = venue == "home"
    venue_rows = [row for row in appearances if row["home"] is venue_flag]
    venue_source = "current"
    if len(venue_rows) < MIN_VENUE_SAMPLE:
        venue_rows = venue_rows + [row for row in prior_appearances if row["home"] is venue_flag]
        venue_source = "current_plus_prior"
    venue_rates = _rates(venue_rows) if len(venue_rows) >= MIN_VENUE_SAMPLE else None
    if venue_rates is None:
        venue_source = None
    second_half = _second_half_rates(appearances + prior_appearances)
    h2h_blend = None
    if h2h_rates and h2h_rates.get("usable_in_model"):
        h2h_blend = {"attack": h2h_rates["attack"], "defence": h2h_rates["defence"]}
    blended = blend_strengths(season_attack, season_defence, form, venue_rates, h2h_blend, second_half)
    gd_sample = [row["gd"] for row in recent] if len(recent) >= 3 else []
    volatility = float(np.std(gd_sample)) if gd_sample else 0.0
    return {
        "season_attack": season_attack,
        "season_defence": season_defence,
        "form": form,
        "venue": venue_rates,
        "venue_source": venue_source,
        "second_half": second_half,
        **blended,
        "volatility": round(volatility, 2),
        "played": int(standing.get("playedGames") or 0),
        "points": int(standing.get("points") or 0),
        "name": (standing.get("team") or {}).get("name") or standing.get("name"),
        "crest": (standing.get("team") or {}).get("crest") or standing.get("crest"),
        "recent_results": [row["result"] for row in recent],
        "last_completed": last_completed_summary(appearances),
        "last_finished_utc": last_finished_utc(appearances),
    }


def _scenario_bucket(home_goals: int, away_goals: int) -> str:
    margin = home_goals - away_goals
    total = home_goals + away_goals
    if margin >= 2:
        return "home_dominance"
    if margin <= -2:
        return "away_upset"
    if total >= 4:
        return "high_scoring"
    if total <= 1:
        return "low_scoring"
    return "close_match"


SCENARIO_LABELS = {
    "home_dominance": "Home Dominance",
    "close_match": "Close Match",
    "away_upset": "Away Upset",
    "high_scoring": "High Scoring",
    "low_scoring": "Low Scoring",
}


def model_confidence(
    probabilities: dict,
    home_profile: dict,
    away_profile: dict,
    live_data: bool,
) -> dict:
    ranked = sorted(
        [
            probabilities["home_win"],
            probabilities["draw"],
            probabilities["away_win"],
        ],
        reverse=True,
    )
    separation = ranked[0] - ranked[1]
    sep_score = min(1.0, separation / 22.0)

    data_score = 0.4
    if home_profile["used_form"] and away_profile["used_form"]:
        data_score += 0.22
    elif home_profile["used_form"] or away_profile["used_form"]:
        data_score += 0.1
    if home_profile["used_home_away"] and away_profile["used_home_away"]:
        data_score += 0.12
    elif home_profile["used_home_away"] or away_profile["used_home_away"]:
        data_score += 0.05
    if home_profile["played"] >= 5 and away_profile["played"] >= 5:
        data_score += 0.16
    elif home_profile["played"] >= 1 and away_profile["played"] >= 1:
        data_score += 0.06
    if not live_data:
        data_score -= 0.18

    volatility = (home_profile["volatility"] + away_profile["volatility"]) / 2
    vol_penalty = min(0.22, volatility / 8)

    raw = 100 * (0.32 + 0.42 * sep_score + 0.26 * max(0.0, data_score)) - vol_penalty * 100
    sample = min(home_profile["played"], away_profile["played"])
    if sample < 5:
        raw -= 16
    if not (home_profile["used_form"] and away_profile["used_form"]):
        raw -= 8
    value = int(np.clip(round(raw), 28, 92))
    if sample < 5:
        value = min(value, 64)
    if value >= 75:
        level = "HIGH CONFIDENCE"
        copy = "The simulation shows a clear statistical advantage, although match outcomes remain uncertain."
    elif value >= 55:
        level = "MODERATE CONFIDENCE"
        copy = "The sides are separable in the model, but recent results and match noise still leave this open."
    else:
        level = "LOW CONFIDENCE"
        copy = "The simulation is tightly clustered or built on limited match samples. Treat this as a weak signal."
    return {
        "value": value,
        "level": level,
        "copy": f"MODEL CONFIDENCE IS {level.split()[0]}. {copy}",
        "drivers": {
            "probability_separation": round(separation, 2),
            "used_recent_form": home_profile["used_form"] and away_profile["used_form"],
            "used_home_away": home_profile["used_home_away"] and away_profile["used_home_away"],
            "live_data": live_data,
            "volatility": round(volatility, 2),
        },
    }


def predict(
    home_attack,
    home_defence,
    away_attack,
    away_defence,
    simulations=10000,
    home_formation="4-3-3",
    away_formation="4-2-3-1",
    recent_form_home=None,
    recent_form_away=None,
    weather_impact_home=0.0,
    weather_impact_away=0.0,
    fatigue_home=0.0,
    fatigue_away=0.0,
):
    recent_form_home = recent_form_home or []
    recent_form_away = recent_form_away or []
    form_h = (sum(recent_form_home) / len(recent_form_home) - 1.5) * 0.05 if recent_form_home else 0
    form_a = (sum(recent_form_away) / len(recent_form_away) - 1.5) * 0.05 if recent_form_away else 0
    hx = max(
        0.1,
        (home_attack + away_defence) / 2
        + FORMATION.get(home_formation, 0)
        + form_h
        + weather_impact_home
        - fatigue_home,
    )
    ax = max(
        0.1,
        (away_attack + home_defence) / 2
        + FORMATION.get(away_formation, 0)
        + form_a
        + weather_impact_away
        - fatigue_away,
    )
    h = np.random.poisson(hx, simulations)
    a = np.random.poisson(ax, simulations)
    score_counts: Counter[tuple[int, int]] = Counter(zip(h.tolist(), a.tolist()))
    best = max(score_counts, key=score_counts.get)
    home_wins = int((h > a).sum())
    draws = int((h == a).sum())
    away_wins = int((h < a).sum())
    buckets = Counter(_scenario_bucket(int(x), int(y)) for x, y in zip(h, a))
    top = score_counts.most_common(5)
    return {
        "expected_goals": {"home": round(float(hx), 2), "away": round(float(ax), 2)},
        "probabilities": {
            "home_win": round(home_wins / simulations * 100, 2),
            "draw": round(draws / simulations * 100, 2),
            "away_win": round(away_wins / simulations * 100, 2),
        },
        "outcome_counts": {
            "home_win": home_wins,
            "draw": draws,
            "away_win": away_wins,
        },
        "most_likely_score": f"{best[0]}-{best[1]}",
        "scorelines": [
            {
                "score": f"{hs}-{ags}",
                "count": count,
                "pct": round(count / simulations * 100, 1),
            }
            for (hs, ags), count in top
        ],
        "scenarios": [
            {
                "id": key,
                "label": SCENARIO_LABELS[key],
                "count": buckets.get(key, 0),
                "pct": round(buckets.get(key, 0) / simulations * 100, 1),
            }
            for key in ("home_dominance", "close_match", "away_upset", "high_scoring", "low_scoring")
        ],
        "simulations": simulations,
        "factors": [
            "season attack/defence (weighted)",
            "recent completed matches when available",
            "home/away splits when available",
            "completed head-to-head when available",
            "second-half trend when half-time scores exist",
            "formation scenario",
            "weather impact",
            "away travel fatigue",
            "rest-day congestion when kickoffs exist",
            "Monte Carlo Poisson simulation",
        ],
        "warning": "Statistical estimate, not a guarantee.",
        "formations": {
            "home": home_formation,
            "away": away_formation,
            "home_persona": FORMATION_PERSONA.get(home_formation, "CUSTOM"),
            "away_persona": FORMATION_PERSONA.get(away_formation, "CUSTOM"),
            "assumed": True,
        },
    }


def simulate_season(teams):
    """Legacy random-points helper. Prefer simulate_remaining_season()."""
    table = []
    for i, team in enumerate(teams):
        pts = int(np.random.normal(62 - i * 2, 9))
        table.append({"team": team["name"], "points": max(0, pts)})
    return sorted(table, key=lambda row: row["points"], reverse=True)


def calendar_rest_penalties(
    fixtures: list[dict],
    last_utc_by_team: dict[int, str | None],
) -> tuple[list[float], list[float], int]:
    last_dt = {tid: parse_utc(utc) for tid, utc in last_utc_by_team.items()}
    order = sorted(range(len(fixtures)), key=lambda i: fixtures[i].get("utc_date") or "")
    home_pen = [0.0] * len(fixtures)
    away_pen = [0.0] * len(fixtures)
    applied = 0
    for i in order:
        fx = fixtures[i]
        kickoff = parse_utc(fx.get("utc_date"))
        hid, aid = fx["home_id"], fx["away_id"]
        hf = rest_fatigue(rest_days_between(last_dt.get(hid), kickoff))
        af = rest_fatigue(rest_days_between(last_dt.get(aid), kickoff))
        home_pen[i] = hf
        away_pen[i] = af
        if hf or af:
            applied += 1
        if kickoff is not None:
            last_dt[hid] = kickoff
            last_dt[aid] = kickoff
    return home_pen, away_pen, applied


def simulate_remaining_season(
    home_profiles: dict[int, dict],
    away_profiles: dict[int, dict],
    fixtures: list[dict],
    simulations: int = 2000,
    last_utc_by_team: dict[int, str | None] | None = None,
) -> dict:
    if not fixtures or not home_profiles:
        return {
            "available": False,
            "mode": "unavailable",
            "reason": "No remaining Premier League fixtures were returned by the data provider.",
            "simulations": 0,
            "fixture_count": 0,
            "teams": [],
        }

    ids = list(home_profiles.keys())
    index = {tid: i for i, tid in enumerate(ids)}
    n_teams = len(ids)
    start_points = np.array([home_profiles[tid]["points"] for tid in ids], dtype=float)
    home_rest, away_rest, rest_applied = calendar_rest_penalties(fixtures, last_utc_by_team or {})
    home_xg = np.array(
        [
            max(
                0.1,
                (home_profiles[fx["home_id"]]["attack"] + away_profiles[fx["away_id"]]["defence"]) / 2
                - home_rest[i],
            )
            for i, fx in enumerate(fixtures)
        ]
    )
    away_xg = np.array(
        [
            max(
                0.1,
                (away_profiles[fx["away_id"]]["attack"] + home_profiles[fx["home_id"]]["defence"]) / 2
                - away_rest[i],
            )
            for i, fx in enumerate(fixtures)
        ]
    )
    home_goals = np.random.poisson(home_xg, (simulations, len(fixtures)))
    away_goals = np.random.poisson(away_xg, (simulations, len(fixtures)))
    points = np.repeat(start_points[None, :], simulations, axis=0)
    home_idx = np.array([index[fx["home_id"]] for fx in fixtures])
    away_idx = np.array([index[fx["away_id"]] for fx in fixtures])

    home_win = home_goals > away_goals
    draw = home_goals == away_goals
    away_win = home_goals < away_goals
    for fixture_i in range(len(fixtures)):
        h = home_idx[fixture_i]
        a = away_idx[fixture_i]
        points[:, h] += 3 * home_win[:, fixture_i] + 1 * draw[:, fixture_i]
        points[:, a] += 3 * away_win[:, fixture_i] + 1 * draw[:, fixture_i]

    order = np.argsort(-points, axis=1, kind="mergesort")
    positions = np.empty_like(order)
    rows = np.arange(simulations)[:, None]
    positions[rows, order] = np.arange(1, n_teams + 1)

    teams_out = []
    for tid in ids:
        i = index[tid]
        pos = positions[:, i]
        teams_out.append(
            {
                "team_id": tid,
                "name": home_profiles[tid]["name"],
                "crest": home_profiles[tid].get("crest"),
                "current_points": home_profiles[tid]["points"],
                "title": round(float((pos == 1).mean() * 100), 1),
                "top4": round(float((pos <= 4).mean() * 100), 1),
                "top6": round(float((pos <= 6).mean() * 100), 1),
                "relegation": round(float((pos > n_teams - 3).mean() * 100), 1),
                "expected_points": round(float(points[:, i].mean()), 1),
                "expected_position": round(float(pos.mean()), 1),
                "most_common_position": int(Counter(pos.tolist()).most_common(1)[0][0]),
            }
        )
    teams_out.sort(key=lambda row: (-row["title"], -row["top4"], row["expected_position"]))
    note = "Each remaining listed fixture is simulated from current team strength. Future matchday weather is not applied."
    if rest_applied:
        note += (
            f" Rest-day congestion was applied on {rest_applied} listed fixtures where a side had 3 or fewer days between kickoffs."
        )
    return {
        "available": True,
        "mode": "remaining_fixtures",
        "note": note,
        "simulations": simulations,
        "fixture_count": len(fixtures),
        "rest_modified_fixtures": rest_applied,
        "teams": teams_out,
    }


def distance_km(lat1, lon1, lat2, lon2):
    radius = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * radius * asin(sqrt(a))


def key_factors(
    home_name: str,
    away_name: str,
    result: dict,
    weather: dict,
    travel_km: float,
    fatigue: float,
    rest: dict | None = None,
    h2h: dict | None = None,
) -> list[dict]:
    xg = result["expected_goals"]
    impact = weather.get("performance_impact", 0)
    impact_txt = f"{impact:+.2f} xG".replace("+", "+") if impact else "0.00 xG"
    model = result.get("model") or {}
    feels = weather.get("feels_like_c")
    gust = weather.get("wind_gust_kph")
    humidity = weather.get("humidity_pct")
    feels_txt = f", feels like {feels}°C" if feels is not None else ""
    gust_txt = f", gust {gust} kph" if gust is not None else ""
    humidity_txt = f", humidity {humidity}%" if humidity is not None else ""
    items = [
        {
            "code": "01",
            "title": "ATTACKING OUTPUT",
            "body": (
                f"{home_name} {xg['home']} xG versus {away_name} {xg['away']} xG, blended from season rates"
                f"{', recent completed matches' if model.get('used_form') else ''}"
                f"{' and home/away splits' if model.get('used_home_away') else ''}"
                f"{' plus completed head-to-head' if model.get('used_h2h') else ''}"
                f"{' and second-half scoring rates' if model.get('used_second_half') else ''}."
            ),
        },
        {
            "code": "02",
            "title": "MATCH CONDITIONS",
            "body": (
                f"{weather.get('condition', 'Unknown')} at {weather.get('temperature_c', '—')}°C"
                f"{feels_txt}, wind {weather.get('wind_kph', '—')} kph{gust_txt}"
                f", precipitation {weather.get('precipitation_mm', '—')} mm{humidity_txt}. "
                f"Model impact {impact_txt}."
            ),
        },
        {
            "code": "03",
            "title": "AWAY TRAVEL",
            "body": (
                f"{away_name} travel {travel_km} km. Fatigue penalty {fatigue:.2f} xG on the away attack, "
                "capped at 0.15."
            ),
        },
    ]
    if rest and (rest.get("home_days") is not None or rest.get("away_days") is not None):
        parts = []
        if rest.get("home_days") is not None:
            parts.append(f"{home_name} {rest['home_days']} days")
        if rest.get("away_days") is not None:
            parts.append(f"{away_name} {rest['away_days']} days")
        if parts:
            relative = rest.get("relative_to")
            when = f" before kickoff {relative}" if relative else " as of now"
            items.append(
                {
                    "code": "04",
                    "title": "REST DAYS",
                    "body": f"{'; '.join(parts)}{when}. Congestion penalty applies at 3 days or fewer.",
                }
            )
    if h2h and h2h.get("played"):
        latest = (h2h.get("matches") or [None])[0]
        latest_txt = ""
        if latest and latest.get("utc_date") and latest.get("score"):
            latest_txt = f" Most recent completed meeting {latest['utc_date'][:10]} finished {latest['score']}."
        items.append(
            {
                "code": "05",
                "title": "HEAD TO HEAD",
                "body": f"{h2h['played']} completed meetings on record.{latest_txt}",
            }
        )
    for i, item in enumerate(items, 1):
        item["code"] = f"{i:02d}"
    return items
