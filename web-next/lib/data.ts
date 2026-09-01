import "server-only";
import type { Bootstrap, DashboardData, Fixture, FixtureHorizon, LeagueSnapshot, LeagueSummary, Manager, ManagerSummary } from "./types";

const DATA_BASE = process.env.FPL_DATA_BASE_URL ?? "https://fpl-scout-intelligence.netlify.app/data";
const API_BASE = (process.env.FPL_API_BASE_URL ?? "https://fpl-scout-api-bztsnhv3ea-uc.a.run.app").replace(/\/$/, "");
const memoryCache = new Map<string, { expiresAt: number; value: unknown }>();
export const MY_TEAM_ID = 2797967;
export const DEFAULT_LEAGUE_ID = 58005;
export const DEFAULT_GAMEWEEK = 1;
export type LeagueDashboardData = Omit<DashboardData, "manager"> & { manager?: Manager };

class ApiRequestError extends Error {
  constructor(public status: number, path: string) {
    super(`Scout API returned ${status} for ${path}`);
  }
}

async function requestApi<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!response.ok) throw new ApiRequestError(response.status, path);
  return response.json() as Promise<T>;
}

export async function getCompactCatalog(): Promise<Bootstrap> {
  const payload = await requestApi<{ players: Bootstrap["elements"]; teams: Bootstrap["teams"]; events: Bootstrap["events"] }>("/v1/catalog/compact");
  return { elements: payload.players, teams: payload.teams, events: payload.events };
}

export async function getLeagueSummary(
  leagueId = DEFAULT_LEAGUE_ID,
  options: { gameweek?: number; page?: number; query?: string } = {},
): Promise<LeagueSummary> {
  const params = new URLSearchParams({ page: String(options.page ?? 1), page_size: "50" });
  if (options.query) params.set("q", options.query);
  if (options.gameweek === undefined) {
    return requestApi<LeagueSummary>(`/v1/leagues/${leagueId}/summary?${params}`);
  }
  const resolved = options.gameweek;
  for (let candidate = resolved; candidate >= 1; candidate -= 1) {
    try {
      return await requestApi<LeagueSummary>(`/v1/leagues/${leagueId}/summary?gw=${candidate}&${params}`);
    } catch (error) {
      if (!(error instanceof ApiRequestError) || ![404, 409].includes(error.status)) throw error;
    }
  }
  throw new Error(`No league summary available for league ${leagueId}`);
}

export async function getLeagueDirectory(leagueId = DEFAULT_LEAGUE_ID, gameweek?: number) {
  const suffix = gameweek === undefined ? "" : `?gw=${gameweek}`;
  const payload = await requestApi<{ gameweek: number; managers: ManagerSummary[] }>(`/v1/leagues/${leagueId}/directory${suffix}`);
  return payload;
}

export async function getLeagueManager(leagueId: number, gameweek: number, entryId: number): Promise<Manager> {
  return requestApi<Manager>(`/v1/leagues/${leagueId}/managers/${entryId}?gw=${gameweek}`);
}

export async function getTransferOptimizer(leagueId: number, gameweek: number) {
  return requestApi<{
    status: string; optimizer_version: string; target_gameweeks: number[]; free_transfers: number;
    plans: Array<{ transfer_count: number; net_ev?: number; gross_horizon_gain?: number; hit_cost: number; free_transfer_opportunity_cost?: number; bank_after: number; transfers?: Array<{ out_name: string; in_name: string; position: string; weighted_gain: number }> }>;
    disclaimer: string;
  }>(`/v1/optimizer/transfers?league_id=${leagueId}&gw=${gameweek}&horizon=5&max_transfers=2`);
}

async function readJson<T>(path: string): Promise<T> {
  const cached = memoryCache.get(path);
  if (cached && cached.expiresAt > Date.now()) return cached.value as T;
  const response = await fetch(`${DATA_BASE}/${path}`, { cache: "no-store" });
  if (!response.ok) throw new Error(`Data source returned ${response.status} for ${path}`);
  const value = await response.json() as T;
  memoryCache.set(path, { expiresAt: Date.now() + 300_000, value });
  return value;
}

export async function getDashboardData(leagueId = DEFAULT_LEAGUE_ID, gameweek?: number): Promise<DashboardData> {
  const data = await getLeagueData(leagueId, gameweek);
  if (!data.manager) throw new Error(`Team ${MY_TEAM_ID} is not present in league ${leagueId} for GW${data.gameweek}`);
  return { ...data, manager: data.manager };
}

export async function getPlannerData(targetGameweek?: number) {
  const dashboard = await getDashboardData();
  // Planning always begins at the explicitly supplied upcoming deadline.
  // Without it, fall back to the next GW after the latest captured review.
  const fromGameweek = Math.min(Math.max(targetGameweek ?? dashboard.gameweek + 1, dashboard.gameweek + 1), 38);
  const toGameweek = Math.min(fromGameweek + 4, 38);
  let fixtureHorizon: FixtureHorizon;
  if (API_BASE) {
    const response = await fetch(`${API_BASE}/v1/fixtures?from_gw=${fromGameweek}&to_gw=${toGameweek}`, { cache: "no-store" });
    if (!response.ok) throw new Error(`Scout API returned ${response.status} for fixture horizon`);
    fixtureHorizon = ((await response.json()) as { gameweeks: FixtureHorizon }).gameweeks;
  } else {
    fixtureHorizon = (await readJson<{ gameweeks: FixtureHorizon }>("fixtures_cache.json")).gameweeks;
  }
  return { ...dashboard, fixtureHorizon, fromGameweek, toGameweek };
}

export async function getLeagueData(leagueId = DEFAULT_LEAGUE_ID, gameweek?: number): Promise<LeagueDashboardData> {
  if (API_BASE) return getLeagueDataFromApi(leagueId, gameweek);
  const bootstrap = await readJson<Bootstrap>("bootstrap_cache.json");
  const resolvedGameweek = gameweek ?? bootstrap.events.find((event) => event.is_current)?.id ?? DEFAULT_GAMEWEEK;
  const [snapshot, fixturePayload] = await Promise.all([
    readJson<LeagueSnapshot>(`gw${resolvedGameweek}_league${leagueId}_data.json`),
    readJson<Record<string, Fixture[]>>(`gw${Math.min(resolvedGameweek + 1, 38)}_fixtures.json`).catch((): Record<string, Fixture[]> => ({})),
  ]);
  const manager = snapshot.competitors.find((entry) => entry.entry_id === MY_TEAM_ID);
  return { manager, managers: snapshot.competitors, bootstrap, fixture: fixturePayload[`gw${Math.min(resolvedGameweek + 1, 38)}`] ?? [], gameweek: resolvedGameweek, leagueId, fetchedAt: snapshot.fetched_at, requestedGameweek: resolvedGameweek, snapshotStatus: "exact" };
}

async function getLeagueDataFromApi(leagueId: number, gameweek?: number): Promise<LeagueDashboardData> {
  type IdentityPayload = { current_gameweek: number };
  type TeamPayload = { meta: { generated_at?: string; snapshot_at?: string }; manager: Manager; fixtures: Fixture[] };
  type LeaguePayload = { meta?: { generated_at?: string; snapshot_at?: string }; managers: Manager[] };
  type CatalogPayload = { players: Bootstrap["elements"]; teams: Bootstrap["teams"]; events: Bootstrap["events"] };
  const request = requestApi;
  const resolvedGameweek = gameweek ?? (await request<IdentityPayload>("/v1/me")).current_gameweek ?? DEFAULT_GAMEWEEK;
  // A league-analysis page must work even when the configured team is not a
  // member of the selected league (for example the public prize league).
  // Treat the personal-team lookup as optional; the league snapshot remains
  // the source of truth for elite/cohort pages.
  const catalog = await request<CatalogPayload>("/v1/catalog");
  // League snapshots arrive after the live gameweek advances.  If the
  // selected league has not been collected for the current GW yet, walk back
  // to the newest available snapshot instead of rendering an application
  // error page.  This is especially important for large/public leagues.
  let league: LeaguePayload | null = null;
  let snapshotGameweek = resolvedGameweek;
  let snapshotStatus: DashboardData["snapshotStatus"] = "exact";
  let liveProvisional = false;
  for (let candidate = resolvedGameweek; candidate >= 1; candidate -= 1) {
    try {
      league = await request<LeaguePayload>(`/v1/leagues/${leagueId}?gw=${candidate}`);
      snapshotGameweek = candidate;
      break;
    } catch (error) {
      if (!(error instanceof ApiRequestError) || ![404, 409].includes(error.status)) throw error;
      if (candidate === resolvedGameweek && error.status === 409) {
        const live = await request<LeaguePayload & { gameweek: number; provisional?: boolean }>(`/v1/leagues/${leagueId}/live`).catch(() => null);
        if (live?.managers?.length) {
          league = live;
          snapshotGameweek = live.gameweek;
          liveProvisional = true;
          break;
        }
      }
      if (candidate === resolvedGameweek) snapshotStatus = error.status === 409 ? "fallback_provisional" : "fallback_missing";
    }
  }
  if (!league) throw new Error(`No league snapshot available for league ${leagueId}`);
  const team = await request<TeamPayload>(`/v1/me/team?league_id=${leagueId}&gw=${snapshotGameweek}`).catch(() => null);
  return {
    manager: league.managers.find((entry) => entry.entry_id === MY_TEAM_ID),
    managers: league.managers,
    bootstrap: { elements: catalog.players, teams: catalog.teams, events: catalog.events },
    fixture: team?.fixtures ?? [],
    gameweek: snapshotGameweek,
    leagueId,
    fetchedAt: team?.meta.snapshot_at ?? team?.meta.generated_at ?? league.meta?.snapshot_at ?? league.meta?.generated_at,
    requestedGameweek: resolvedGameweek,
    snapshotStatus: snapshotGameweek === resolvedGameweek ? "exact" : snapshotStatus,
    liveProvisional,
  };
}

export function getElite(managers: Manager[]) {
  const count = Math.max(1, Math.ceil(managers.length * 0.05));
  return [...managers].sort((a, b) => (a.overall_rank || Number.MAX_SAFE_INTEGER) - (b.overall_rank || Number.MAX_SAFE_INTEGER)).slice(0, count);
}
