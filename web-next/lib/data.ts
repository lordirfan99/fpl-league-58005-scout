import "server-only";
import type { Bootstrap, DashboardData, Fixture, FixtureHorizon, LeagueSnapshot, Manager } from "./types";

const DATA_BASE = process.env.FPL_DATA_BASE_URL ?? "https://fpl-scout-intelligence.netlify.app/data";
const API_BASE = (process.env.FPL_API_BASE_URL ?? "https://fpl-scout-api-bztsnhv3ea-uc.a.run.app").replace(/\/$/, "");
const memoryCache = new Map<string, { expiresAt: number; value: unknown }>();
export const MY_TEAM_ID = 2797967;
export const DEFAULT_LEAGUE_ID = 58005;
export const DEFAULT_GAMEWEEK = 1;
export type LeagueDashboardData = Omit<DashboardData, "manager"> & { manager?: Manager };

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

export async function getPlannerData() {
  const dashboard = await getDashboardData();
  const fromGameweek = Math.min(dashboard.gameweek + 1, 38);
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
  return { manager, managers: snapshot.competitors, bootstrap, fixture: fixturePayload[`gw${Math.min(resolvedGameweek + 1, 38)}`] ?? [], gameweek: resolvedGameweek, leagueId, fetchedAt: snapshot.fetched_at };
}

async function getLeagueDataFromApi(leagueId: number, gameweek?: number): Promise<LeagueDashboardData> {
  type IdentityPayload = { current_gameweek: number };
  type TeamPayload = { meta: { generated_at?: string }; manager: Manager; fixtures: Fixture[] };
  type LeaguePayload = { managers: Manager[] };
  type CatalogPayload = { players: Bootstrap["elements"]; teams: Bootstrap["teams"]; events: Bootstrap["events"] };
  const request = async <T>(path: string) => {
    const response = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
    if (!response.ok) throw new Error(`Scout API returned ${response.status} for ${path}`);
    return response.json() as Promise<T>;
  };
  const resolvedGameweek = gameweek ?? (await request<IdentityPayload>("/v1/me")).current_gameweek ?? DEFAULT_GAMEWEEK;
  const [team, league, catalog] = await Promise.all([
    request<TeamPayload>(`/v1/me/team?league_id=${DEFAULT_LEAGUE_ID}&gw=${resolvedGameweek}`),
    request<LeaguePayload>(`/v1/leagues/${leagueId}?gw=${resolvedGameweek}`),
    request<CatalogPayload>("/v1/catalog"),
  ]);
  return {
    manager: league.managers.find((entry) => entry.entry_id === MY_TEAM_ID),
    managers: league.managers,
    bootstrap: { elements: catalog.players, teams: catalog.teams, events: catalog.events },
    fixture: team.fixtures,
    gameweek: resolvedGameweek,
    leagueId,
    fetchedAt: team.meta.generated_at,
  };
}

export function getElite(managers: Manager[]) {
  const count = Math.max(1, Math.ceil(managers.length * 0.05));
  return [...managers].sort((a, b) => (a.overall_rank || Number.MAX_SAFE_INTEGER) - (b.overall_rank || Number.MAX_SAFE_INTEGER)).slice(0, count);
}
