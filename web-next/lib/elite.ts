import type { Manager, Pick, Position } from "./types";
import { getElite } from "./data";

const positions: Position[] = ["GKP", "DEF", "MID", "FWD"];
const squadLimits: Record<Position, number> = { GKP: 2, DEF: 5, MID: 5, FWD: 3 };

type CountRow = { name: string; count: number; percentage: number };

function median(values: number[]) {
  const sorted = [...values].sort((a, b) => a - b), middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
}

function formation(manager: Manager) {
  const starters = manager.squad.slice(0, 11);
  return `${starters.filter((pick) => pick.position === "DEF").length}-${starters.filter((pick) => pick.position === "MID").length}-${starters.filter((pick) => pick.position === "FWD").length}`;
}

function rows(counter: Map<string, number>, denominator: number): CountRow[] {
  return [...counter].map(([name, count]) => ({ name, count, percentage: count / denominator * 100 })).sort((a, b) => b.count - a.count);
}

export function analyzeElite(managers: Manager[]) {
  const elite = getElite(managers);
  const playerById = new Map<number, Pick>(), eliteOwned = new Map<number, number>(), eliteStarted = new Map<number, number>(), leagueOwned = new Map<number, number>(), captainCounts = new Map<string, number>(), formationCounts = new Map<string, number>(), transferCounts = new Map<string, number>(), chipCounts = new Map<string, number>();
  managers.forEach((manager) => manager.squad.forEach((pick) => {
    playerById.set(pick.element, pick);
    leagueOwned.set(pick.element, (leagueOwned.get(pick.element) ?? 0) + 1);
  }));
  elite.forEach((manager) => {
    formationCounts.set(formation(manager), (formationCounts.get(formation(manager)) ?? 0) + 1);
    captainCounts.set(manager.captain || "Unknown", (captainCounts.get(manager.captain || "Unknown") ?? 0) + 1);
    manager.squad.forEach((pick, index) => {
      eliteOwned.set(pick.element, (eliteOwned.get(pick.element) ?? 0) + 1);
      if (index < 11) eliteStarted.set(pick.element, (eliteStarted.get(pick.element) ?? 0) + 1);
    });
    manager.transfer_details?.forEach((move) => {
      const label = `${move.out || "Unknown"} → ${move.in || "Unknown"}`;
      transferCounts.set(label, (transferCounts.get(label) ?? 0) + 1);
    });
    manager.chips_used?.forEach((chip) => {
      const name = chip.name ?? chip.chip_name ?? "Unknown";
      chipCounts.set(name, (chipCounts.get(name) ?? 0) + 1);
    });
  });

  const commonFormation = rows(formationCounts, elite.length)[0]?.name ?? "3-4-3";
  const [defenders, midfielders, forwards] = commonFormation.split("-").map(Number);
  const starterLimits: Record<Position, number> = { GKP: 1, DEF: defenders, MID: midfielders, FWD: forwards };
  const chosen = new Set<number>();
  const template: Pick[] = [];
  positions.forEach((position) => {
    const candidates = [...playerById.values()].filter((pick) => pick.position === position).sort((a, b) => (eliteStarted.get(b.element) ?? 0) - (eliteStarted.get(a.element) ?? 0));
    candidates.slice(0, starterLimits[position]).forEach((pick) => { chosen.add(pick.element); template.push({ ...pick, multiplier: 1, is_captain: false, is_vice_captain: false }); });
  });
  positions.forEach((position) => {
    const needed = squadLimits[position] - starterLimits[position];
    [...playerById.values()].filter((pick) => pick.position === position && !chosen.has(pick.element)).sort((a, b) => (eliteOwned.get(b.element) ?? 0) - (eliteOwned.get(a.element) ?? 0)).slice(0, needed).forEach((pick) => { chosen.add(pick.element); template.push({ ...pick, multiplier: 0, is_captain: false, is_vice_captain: false }); });
  });
  const captainOrder = rows(captainCounts, elite.length);
  const captain = template.find((pick) => pick.name === captainOrder[0]?.name);
  const vice = template.find((pick) => pick.name === captainOrder[1]?.name);
  if (captain) { captain.is_captain = true; captain.multiplier = 2; }
  if (vice) vice.is_vice_captain = true;

  const ownership = [...eliteOwned].map(([element, count]) => {
    const pick = playerById.get(element)!;
    const elitePercentage = count / elite.length * 100, leaguePercentage = (leagueOwned.get(element) ?? 0) / managers.length * 100;
    return { ...pick, count, elitePercentage, leaguePercentage, edge: elitePercentage - leaguePercentage, starterPercentage: (eliteStarted.get(element) ?? 0) / elite.length * 100 };
  }).sort((a, b) => b.elitePercentage - a.elitePercentage);

  const points = elite.map((manager) => manager.gw_points), minimum = Math.floor(Math.min(...points) / 10) * 10, maximum = Math.ceil(Math.max(...points) / 10) * 10;
  const pointsDistribution = [];
  for (let start = minimum; start < maximum; start += 10) {
    const count = points.filter((value) => value >= start && value < start + 10).length;
    pointsDistribution.push({ label: `${start}–${start + 9}`, count, percentage: count / elite.length * 100 });
  }
  const templateIds = new Set(template.map((pick) => pick.element));
  const managerRows = elite.map((manager) => ({ ...manager, formation: formation(manager), templateOverlap: manager.squad.filter((pick) => templateIds.has(pick.element)).length })).sort((a, b) => a.overall_rank - b.overall_rank);

  return {
    elite, template, ownership, captaincy: captainOrder, formations: rows(formationCounts, elite.length), transfers: rows(transferCounts, elite.length), chips: rows(chipCounts, elite.length), pointsDistribution, managerRows, commonFormation,
    averageGw: points.reduce((sum, value) => sum + value, 0) / elite.length,
    medianGw: median(points),
    averageTotal: elite.reduce((sum, manager) => sum + manager.total_points, 0) / elite.length,
    averageValue: elite.reduce((sum, manager) => sum + manager.squad_cost, 0) / elite.length,
    averageRank: Math.round(elite.reduce((sum, manager) => sum + manager.overall_rank, 0) / elite.length),
    topScore: Math.max(...points),
  };
}
