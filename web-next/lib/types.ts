export type Position = "GKP" | "DEF" | "MID" | "FWD";

export interface Pick {
  element: number;
  name: string;
  position: Position;
  team: string;
  cost: number;
  multiplier: number;
  is_captain: boolean;
  is_vice_captain: boolean;
  selected_by?: number;
}

export interface Manager {
  entry_id: number;
  entry_name: string;
  player_name: string;
  gw_points: number;
  total_points: number;
  overall_rank: number;
  league_rank: number;
  league_last_rank?: number;
  squad_cost: number;
  captain: string;
  transfers_made: number;
  squad: Pick[];
  transfer_details?: Array<{ out: string; in: string }>;
  chips_used?: Array<{ name?: string; chip_name?: string }>;
}

export interface LeagueSnapshot {
  fetched_at?: string;
  competitors: Manager[];
}

export interface BootstrapPlayer {
  id: number;
  web_name: string;
  first_name: string;
  second_name: string;
  team: number;
  element_type: number;
  photo: string;
  now_cost: number;
  form: string;
  points_per_game: string;
  selected_by_percent: string;
  ep_next: string;
  event_points: number;
  status: string;
  chance_of_playing_next_round: number | null;
  news: string;
}

export interface BootstrapTeam { id: number; name: string; short_name: string; code: number }
export interface BootstrapEvent { id: number; name: string; is_current: boolean; deadline_time: string; finished: boolean }
export interface Bootstrap { elements: BootstrapPlayer[]; teams: BootstrapTeam[]; events: BootstrapEvent[] }
export interface Fixture { event?: number; team_h: string; team_a: string; team_h_difficulty: number; team_a_difficulty: number; kickoff_time?: string | null }
export type FixtureHorizon = Record<string, Fixture[]>;

export interface DashboardData {
  manager: Manager;
  managers: Manager[];
  bootstrap: Bootstrap;
  fixture: Fixture[];
  gameweek: number;
  leagueId: number;
  fetchedAt?: string;
}
