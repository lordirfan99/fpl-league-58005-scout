import type { Bootstrap, Fixture, Manager, Pick, Position } from "./types";
import { getElite } from "./data";

export interface PlayerSignal extends Pick {
  xpts: number;
  form: number;
  eliteOwnership: number;
  eliteCaptaincy: number;
  fixture: string;
  fdr: number | null;
  risk: boolean;
  score: number;
}

function fixtureFor(team: string, fixtures: Fixture[]) {
  const match = fixtures.find((item) => item.team_h === team || item.team_a === team);
  if (!match) return { label: "Fixture TBC", fdr: null };
  return match.team_h === team
    ? { label: `${match.team_a} (H)`, fdr: match.team_h_difficulty }
    : { label: `${match.team_h} (A)`, fdr: match.team_a_difficulty };
}

export function buildSignals(managers: Manager[], bootstrap: Bootstrap, fixtures: Fixture[]) {
  const elite = getElite(managers), eliteOwned = new Map<number, number>(), eliteCaptains = new Map<number, number>(), unique = new Map<number, Pick>();
  managers.forEach((manager) => manager.squad.forEach((pick) => unique.set(pick.element, pick)));
  elite.forEach((manager) => manager.squad.forEach((pick) => {
    eliteOwned.set(pick.element, (eliteOwned.get(pick.element) ?? 0) + 1);
    if (pick.is_captain) eliteCaptains.set(pick.element, (eliteCaptains.get(pick.element) ?? 0) + 1);
  }));
  const index = new Map(bootstrap.elements.map((player) => [player.id, player]));
  const signals = [...unique.values()].map<PlayerSignal>((pick) => {
    const player = index.get(pick.element), next = fixtureFor(pick.team, fixtures);
    const xpts = Number(player?.ep_next ?? 0), form = Number(player?.form ?? 0), eliteOwnership = (eliteOwned.get(pick.element) ?? 0) / elite.length * 100, eliteCaptaincy = (eliteCaptains.get(pick.element) ?? 0) / elite.length * 100, chance = player?.chance_of_playing_next_round ?? 100, risk = player?.status !== "a" || chance < 75;
    const fixtureBoost = next.fdr ? (6 - next.fdr) * 0.35 : 0;
    return { ...pick, xpts, form, eliteOwnership, eliteCaptaincy, fixture: next.label, fdr: next.fdr, risk, score: xpts * 0.56 + form * 0.14 + eliteOwnership * 0.08 + eliteCaptaincy * 0.16 + fixtureBoost - (risk ? 6 : 0) };
  });
  return { signals, elite };
}

export function buildRecommendations(manager: Manager, managers: Manager[], bootstrap: Bootstrap, fixtures: Fixture[]) {
  const { signals, elite } = buildSignals(managers, bootstrap, fixtures), byId = new Map(signals.map((player) => [player.element, player])), owned = new Set(manager.squad.map((pick) => pick.element)), squad = manager.squad.map((pick) => byId.get(pick.element)).filter(Boolean) as PlayerSignal[], starters = squad.slice(0, 11), missing = signals.filter((player) => !owned.has(player.element) && player.eliteOwnership >= 20 && !player.risk).sort((a, b) => b.score - a.score);
  const weakest = new Map<Position, PlayerSignal>();
  squad.forEach((player) => { const current = weakest.get(player.position); if (!current || player.score < current.score) weakest.set(player.position, player); });
  const transfers = missing.map((incoming) => {
    const outgoing = weakest.get(incoming.position);
    return outgoing ? { incoming, outgoing, xptsGain: incoming.xpts - outgoing.xpts, signalGain: incoming.score - outgoing.score } : null;
  }).filter((item): item is NonNullable<typeof item> => Boolean(item && item.signalGain > 0.5)).sort((a, b) => b.signalGain - a.signalGain).slice(0, 5);
  const captains = [...starters].sort((a, b) => b.score - a.score).slice(0, 4), risks = squad.filter((player) => player.risk), overlap = squad.filter((player) => player.eliteOwnership > 0).length;
  const eliteAverage = elite.reduce((sum, entry) => sum + entry.gw_points, 0) / elite.length;
  return { transfers, captains, risks, missing: missing.slice(0, 6), overlap, eliteAverage, eliteCount: elite.length };
}
