const API_URL = "";

export const FORMATIONS = ["4-4-2", "4-3-3", "4-2-3-1", "3-5-2", "5-3-2", "3-4-3"] as const;
export type Formation = (typeof FORMATIONS)[number];

export type Team = {
  id: number;
  name: string;
  short_name: string;
  tla: string;
  crest: string;
  venue: string;
  city: string;
  lat: number;
  lon: number;
  website?: string | null;
  club_colors?: string | null;
  founded?: number | null;
  last_updated?: string | null;
};

export type SeasonMeta = {
  current_matchday: number | null;
  start_date: string | null;
  end_date: string | null;
  label: string | null;
  last_updated: string | null;
  winner: string | null;
};

export type StandingRow = {
  position: number;
  team_id: number;
  name: string;
  short_name: string;
  crest: string;
  played: number;
  won: number;
  draw: number;
  lost: number;
  points: number;
  goals_for: number;
  goals_against: number;
  goal_difference: number;
  form: string | null;
};

export type Weather = {
  temperature_c: number;
  feels_like_c?: number | null;
  humidity_pct?: number | null;
  wind_kph: number;
  wind_gust_kph?: number | null;
  cloud_pct?: number | null;
  precipitation_mm: number;
  condition: string;
  icon: string;
  performance_impact: number;
};

export type Player = {
  id: number;
  name: string;
  position: string | null;
  nationality: string | null;
  date_of_birth?: string | null;
  age?: number | null;
  shirt_number?: number | null;
  goals?: number | null;
  assists?: number | null;
  penalties?: number | null;
  played_matches?: number | null;
};

export type CoachDetail = {
  name: string | null;
  nationality: string | null;
  date_of_birth: string | null;
  age: number | null;
  contract_start: string | null;
  contract_until: string | null;
};

export type TeamDetail = {
  id: number;
  name: string;
  crest: string;
  venue: string;
  website?: string | null;
  address?: string | null;
  coach: string | null;
  coach_detail?: CoachDetail | null;
  club_colors: string | null;
  founded: number | null;
  last_updated?: string | null;
  squad: Player[];
  stadium: string;
  city: string;
  lat: number;
  lon: number;
};

export type Scorer = {
  player_id: number | null;
  name: string | null;
  nationality: string | null;
  position: string | null;
  date_of_birth: string | null;
  age: number | null;
  team_id: number | null;
  team_name: string | null;
  crest: string | null;
  played_matches: number | null;
  goals: number | null;
  assists: number | null;
  penalties: number | null;
};

export type UpcomingFixture = {
  id: number | null;
  home_id: number;
  away_id: number;
  home_name: string | null;
  away_name: string | null;
  home_crest: string | null;
  away_crest: string | null;
  home_tla: string | null;
  away_tla: string | null;
  utc_date: string | null;
  matchday: number | null;
  status: string | null;
  last_updated: string | null;
  referee: string | null;
};

export type HeadToHeadMatch = {
  utc_date: string | null;
  home_id: number | null;
  away_id: number | null;
  home_goals: number;
  away_goals: number;
  score: string;
};

export type LastCompleted = {
  utc_date: string | null;
  matchday: number | null;
  result: string | null;
  score: string;
  home: boolean | null;
  half_time?: string;
  second_half?: string;
};

export type Scoreline = { score: string; count: number; pct: number };
export type Scenario = { id: string; label: string; count: number; pct: number };
export type KeyFactor = { code: string; title: string; body: string };

export type Prediction = {
  expected_goals: { home: number; away: number };
  probabilities: { home_win: number; draw: number; away_win: number };
  outcome_counts?: { home_win: number; draw: number; away_win: number };
  most_likely_score: string;
  scorelines?: Scoreline[];
  scenarios?: Scenario[];
  simulations: number;
  factors: string[];
  warning: string;
  formations?: {
    home: string;
    away: string;
    home_persona: string;
    away_persona: string;
    assumed: boolean;
  };
  confidence?: {
    value: number;
    level: string;
    copy: string;
  };
  key_factors?: KeyFactor[];
  model?: {
    live_matches: boolean;
    used_form: boolean;
    used_home_away: boolean;
    used_h2h?: boolean;
    used_second_half?: boolean;
    used_prior_venue?: boolean;
    fallback_season_only: boolean;
  };
  context?: {
    home_team: string;
    away_team: string;
    weather: Weather;
    away_travel_km: number;
    away_fatigue_penalty: number;
    rest?: {
      home_days: number | null;
      away_days: number | null;
      home_fatigue: number;
      away_fatigue: number;
      relative_to: string | null;
    };
    head_to_head?: {
      played: number;
      matches: HeadToHeadMatch[];
      attack: number;
      defence: number;
      usable_in_model: boolean;
    } | null;
    fixture?: UpcomingFixture | null;
    home_last_completed?: LastCompleted | null;
    away_last_completed?: LastCompleted | null;
    season?: SeasonMeta | null;
    fetched_at?: string;
  };
  ai?: {
    model: string;
    headline: string;
    analysis: string;
    factors?: string[];
  } | null;
};

export type SeasonTeam = {
  team_id: number;
  name: string;
  crest: string | null;
  current_points: number;
  title: number;
  top4: number;
  top6: number;
  relegation: number;
  expected_points: number;
  expected_position: number;
  most_common_position: number;
};

export type SeasonIq = {
  available: boolean;
  mode: string;
  reason?: string;
  note?: string;
  simulations: number;
  fixture_count: number;
  rest_modified_fixtures?: number;
  prior_season_matches?: number;
  source?: string;
  fetched_at?: string;
  season?: SeasonMeta | null;
  teams: SeasonTeam[];
};

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`);
  if (!res.ok) throw new Error(`${path} failed (${res.status})`);
  return res.json();
}

export const api = {
  teams: () => getJSON<{ source: string; fetched_at?: string; teams: Team[] }>("/api/teams"),
  standings: () =>
    getJSON<{
      source: string;
      fetched_at?: string;
      current_matchday?: number | null;
      season?: SeasonMeta | null;
      table: StandingRow[];
    }>("/api/standings"),
  teamDetail: (id: number) => getJSON<TeamDetail>(`/api/teams/${id}`),
  teamWeather: (id: number) => getJSON<{ stadium: { stadium: string; city: string }; weather: Weather }>(`/api/teams/${id}/weather`),
  scorers: () =>
    getJSON<{ source: string; fetched_at?: string; season?: SeasonMeta | null; scorers: Scorer[] }>("/api/scorers"),
  upcomingFixtures: (limit = 12) =>
    getJSON<{ source: string; fetched_at?: string; current_matchday?: number | null; fixtures: UpcomingFixture[] }>(
      `/api/fixtures/upcoming?limit=${limit}`
    ),
  stadiumDistance: (a: number, b: number) =>
    getJSON<{ from: string; to: string; distance_km: number }>(`/api/stadiums/distance/${a}/${b}`),
  predictLive: (homeId: number, awayId: number, homeFormation: string, awayFormation: string) =>
    getJSON<Prediction>(
      `/api/predict/${homeId}/${awayId}?home_formation=${encodeURIComponent(homeFormation)}&away_formation=${encodeURIComponent(awayFormation)}`
    ),
  seasonIq: () => getJSON<SeasonIq>("/api/season/iq"),
  simulateSeason: async () => getJSON<SeasonIq>("/api/season/iq"),
};
