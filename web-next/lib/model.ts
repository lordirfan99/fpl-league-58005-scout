import type { Bootstrap, Fixture, Manager, Pick, Position } from "./types";
import { getElite } from "./data";

export type CompetitivePhase = "CATCH" | "MATCH" | "ATTACK";
export type CompetitiveRole = "ALIGN" | "CONTROLLED_EDGE" | "INVESTIGATE" | "AVOID" | "NEUTRAL";

export interface PlayerSignal extends Pick {
  xpts: number;
  form: number;
  eliteOwnership: number;
  eliteCaptaincy: number;
  fixture: string;
  fdr: number | null;
  risk: boolean;
  score: number;
  modelSupport: boolean;
  eliteCore: boolean;
  role: CompetitiveRole;
}

export interface CompetitiveProfile {
  phase: CompetitivePhase;
  phaseReason: string;
  alignment: number;
  targetAlignment: number;
  coreOwned: number;
  coreSize: number;
  criticalMissing: PlayerSignal[];
  modelEdges: PlayerSignal[];
  disagreements: PlayerSignal[];
  weights: {
    eliteConsensus: number;
    projection: number;
    currentSeasonEvidence: number;
  };
}

function fixtureFor(team: string, fixtures: Fixture[]) {
  const match = fixtures.find((item) => item.team_h === team || item.team_a === team);
  if (!match) return { label: "Fixture TBC", fdr: null };
  return match.team_h === team
    ? { label: `${match.team_a} (H)`, fdr: match.team_h_difficulty }
    : { label: `${match.team_h} (A)`, fdr: match.team_a_difficulty };
}

function calibrationWeights(gameweek: number) {
  if (gameweek <= 2) return { eliteConsensus: 0.45, projection: 0.45, currentSeasonEvidence: 0.10 };
  if (gameweek <= 4) return { eliteConsensus: 0.40, projection: 0.45, currentSeasonEvidence: 0.15 };
  if (gameweek <= 8) return { eliteConsensus: 0.30, projection: 0.45, currentSeasonEvidence: 0.25 };
  return { eliteConsensus: 0.25, projection: 0.45, currentSeasonEvidence: 0.30 };
}

function roleFor(eliteOwnership: number, modelSupport: boolean, risk: boolean): CompetitiveRole {
  if (risk) return "AVOID";
  if (eliteOwnership >= 60 && modelSupport) return "ALIGN";
  if (eliteOwnership < 35 && modelSupport) return "CONTROLLED_EDGE";
  if (eliteOwnership >= 60 && !modelSupport) return "INVESTIGATE";
  if (eliteOwnership < 20 && !modelSupport) return "AVOID";
  return "NEUTRAL";
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
    const modelSupport = !risk && (xpts >= 4.5 || (xpts >= 3.8 && form >= 4.0));
    const eliteCore = eliteOwnership >= 60;
    const role = roleFor(eliteOwnership, modelSupport, risk);
    return { ...pick, xpts, form, eliteOwnership, eliteCaptaincy, fixture: next.label, fdr: next.fdr, risk, modelSupport, eliteCore, role, score: xpts * 0.62 + form * 0.12 + eliteOwnership * 0.045 + eliteCaptaincy * 0.10 + fixtureBoost - (risk ? 6 : 0) };
  });
  return { signals, elite };
}

export function buildRecommendations(manager: Manager, managers: Manager[], bootstrap: Bootstrap, fixtures: Fixture[], gameweek = 1) {
  const { signals, elite } = buildSignals(managers, bootstrap, fixtures), byId = new Map(signals.map((player) => [player.element, player])), owned = new Set(manager.squad.map((pick) => pick.element)), squad = manager.squad.map((pick) => byId.get(pick.element)).filter(Boolean) as PlayerSignal[], starters = squad.filter((pick) => pick.multiplier > 0), missing = signals.filter((player) => !owned.has(player.element) && player.eliteOwnership >= 20 && !player.risk).sort((a, b) => b.score - a.score);
  const weakest = new Map<Position, PlayerSignal>();
  squad.forEach((player) => { const current = weakest.get(player.position); if (!current || player.score < current.score) weakest.set(player.position, player); });
  const transfers = missing.map((incoming) => {
    const outgoing = weakest.get(incoming.position);
    return outgoing ? { incoming, outgoing, xptsGain: incoming.xpts - outgoing.xpts, signalGain: incoming.score - outgoing.score } : null;
  }).filter((item): item is NonNullable<typeof item> => Boolean(item && item.signalGain > 0.5)).sort((a, b) => b.signalGain - a.signalGain).slice(0, 5);
  const captains = [...starters].sort((a, b) => b.score - a.score).slice(0, 4), risks = squad.filter((player) => player.risk), overlap = squad.filter((player) => player.eliteOwnership > 0).length;
  const eliteAverage = elite.reduce((sum, entry) => sum + entry.gw_points, 0) / Math.max(1, elite.length);

  const core = signals.filter((player) => player.eliteCore && !player.risk);
  const coreOwned = core.filter((player) => owned.has(player.element)).length;
  const alignment = core.length ? coreOwned / core.length * 100 : 100;
  const targetAlignment = gameweek <= 4 ? 82 : gameweek <= 8 ? 78 : 72;
  const phase: CompetitivePhase = gameweek <= 4 && alignment < targetAlignment ? "CATCH" : alignment >= targetAlignment ? "MATCH" : "ATTACK";
  const phaseReason = phase === "CATCH"
    ? "Under-aligned with the validated elite core: converge before taking unnecessary variance."
    : phase === "MATCH"
      ? "Core structure is competitive: preserve the baseline and use only model-supported deviations."
      : "Alignment is below target outside the early catch window: use selective leverage rather than blind convergence.";
  const competitive: CompetitiveProfile = {
    phase,
    phaseReason,
    alignment: Math.round(alignment * 10) / 10,
    targetAlignment,
    coreOwned,
    coreSize: core.length,
    criticalMissing: core.filter((player) => !owned.has(player.element) && player.modelSupport).sort((a, b) => b.eliteOwnership - a.eliteOwnership).slice(0, 6),
    modelEdges: signals.filter((player) => !owned.has(player.element) && player.role === "CONTROLLED_EDGE").sort((a, b) => b.score - a.score).slice(0, 6),
    disagreements: signals.filter((player) => player.role === "INVESTIGATE").sort((a, b) => b.eliteOwnership - a.eliteOwnership).slice(0, 6),
    weights: calibrationWeights(gameweek),
  };

  return { transfers, captains, risks, missing: missing.slice(0, 6), overlap, eliteAverage, eliteCount: elite.length, competitive };
}
