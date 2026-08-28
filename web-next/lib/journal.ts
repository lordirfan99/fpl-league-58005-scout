import "server-only";

const API_BASE = (process.env.FPL_API_BASE_URL ?? "https://fpl-scout-api-bztsnhv3ea-uc.a.run.app").replace(/\/$/, "");
export const JOURNAL_EXPORT_URL = `${API_BASE}/v1/journal/2026-27/export?filename=gameweeks.csv`;

export interface JournalSummary {
  gw_points: number; total_points: number; overall_rank: number; league_rank: number;
  elite_average: number; points_vs_reference: number; captain?: string; captain_points?: number;
  transfers: number; hit_cost: number; chip?: string; phase?: string; alignment?: number;
}
export interface JournalIndexRow { gameweek: number; status: string; summary: JournalSummary; quality: { status: string; issues: string[] }; record_hash: string }
export interface JournalIndex { schema_version: number; season: string; updated_at?: string; gameweeks: JournalIndexRow[]; totals: { completed: number; points: number } }
export interface JournalPlayer { element: number; name: string; team: string; position: string; multiplier: number; is_captain: boolean; is_vice_captain: boolean; points: number; minutes: number }
export interface JournalEntry {
  season: string; gameweek: number; generated_at: string; status: string; summary: JournalSummary;
  decision: { captured: boolean; decision_id?: string; model_version: string; packet_status?: string; competitive: Record<string, unknown>; plan?: Record<string, unknown>; v5_projection_version?: string };
  outcome: { squad: JournalPlayer[]; transfers: Array<{ out?: string; in?: string }>; chips: Array<Record<string, unknown>> };
  league: { competitors: number; top_owned: Array<{ name: string; pct: number }>; captain_choices: Array<{ name: string; percentage: number }>; formations: Array<Record<string, unknown>>; transfer_trends: Record<string, unknown>; chips: Record<string, number> };
  evaluation: { v5: { rows: number; mae?: number }; fpl_ep_next: { rows: number; mae?: number }; horizons: unknown[] };
  learning: { automated: string[]; public_lesson?: string }; quality: { status: string; issues: string[] };
  provenance: { snapshot_at?: string; analysis_at?: string; predeadline_at?: string; sources: string[] }; record_hash: string;
}

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!response.ok) throw new Error(`Journal API returned ${response.status} for ${path}`);
  return response.json() as Promise<T>;
}
export const getJournalIndex = (season = "2026-27") => request<JournalIndex>(`/v1/journal?season=${encodeURIComponent(season)}`);
export const getJournalEntry = (season: string, gameweek: number) => request<JournalEntry>(`/v1/journal/${encodeURIComponent(season)}/gw/${gameweek}`);
