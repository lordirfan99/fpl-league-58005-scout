import { FlaskConical, ShieldCheck } from "lucide-react";
import { MetricCard } from "@/components/metric-card";
import { PageHeader } from "@/components/page-header";
import { ProjectionPitch } from "@/components/projection-pitch";
import { getAutopilotData, type AutopilotPlayer, type ShadowTransfer } from "@/lib/autopilot";
import { getDashboardData } from "@/lib/data";
import type { Bootstrap } from "@/lib/types";
import { getV5Projections, type V5Player } from "@/lib/v5";

const outfield = ["DEF", "MID", "FWD"];

function formation(players: AutopilotPlayer[]) {
  return outfield.map((position) => players.filter((player) => (player.position ?? player.pos) === position).length).join("-");
}

function scoringPoints(players: AutopilotPlayer[], captainId?: number) {
  return players.reduce((total, player) => total + Number(player.xpts ?? 0), 0)
    + Number(players.find((player) => player.id === captainId)?.xpts ?? 0);
}

function namesOnly(players: AutopilotPlayer[], other: Set<number>) {
  return players.filter((player) => player.id != null && !other.has(player.id)).map((player) => player.name).filter(Boolean) as string[];
}

const legalFormations = [[3, 4, 3], [3, 5, 2], [4, 4, 2], [4, 3, 3], [4, 5, 1], [5, 3, 2], [5, 4, 1], [5, 2, 3]];

function selectV5Lineup(players: V5Player[]) {
  const byPosition = (position: string) => players.filter((player) => player.position === position).toSorted((a, b) => b.xpts_mean - a.xpts_mean);
  const goalkeepers = byPosition("GKP"), defenders = byPosition("DEF"), midfielders = byPosition("MID"), forwards = byPosition("FWD");
  let best: V5Player[] = [];
  for (const [def, mid, fwd] of legalFormations) {
    const lineup = [...goalkeepers.slice(0, 1), ...defenders.slice(0, def), ...midfielders.slice(0, mid), ...forwards.slice(0, fwd)];
    if (lineup.length === 11 && lineup.reduce((sum, player) => sum + player.xpts_mean, 0) > best.reduce((sum, player) => sum + player.xpts_mean, 0)) best = lineup;
  }
  const selected = new Set(best.map((player) => player.element));
  const bench = [...goalkeepers.filter((player) => !selected.has(player.element)), ...players.filter((player) => player.position !== "GKP" && !selected.has(player.element)).toSorted((a, b) => b.xpts_mean - a.xpts_mean)];
  const captain = best.toSorted((a, b) => b.xpts_mean - a.xpts_mean)[0];
  const convert = (player: V5Player): AutopilotPlayer => ({ id: player.element, name: player.name, position: player.position, club: player.team, xpts: player.xpts_mean });
  return { lineup: best.map(convert), bench: bench.slice(0, 4).map(convert), captainId: captain?.element, points: best.reduce((sum, player) => sum + player.xpts_mean, captain?.xpts_mean ?? 0), robustPoints: best.reduce((sum, player) => sum + player.p10, captain?.p10 ?? 0) };
}

function ModelXi({ label, version, mode, lineup, bench, captainId, viceId, points, robustPoints, unique, uniqueLabel = "UNIQUE VS PRODUCTION XI", comparisonAvailable = true, transfers, transferNote, bootstrap }: { label: string; version: string; mode: "champion" | "shadow" | "lab"; lineup: AutopilotPlayer[]; bench: AutopilotPlayer[]; captainId?: number; viceId?: number; points: number; robustPoints?: number; unique: string[]; uniqueLabel?: string; comparisonAvailable?: boolean; transfers?: ShadowTransfer[]; transferNote?: string; bootstrap: Bootstrap }) {
  return <section className={`surface model-xi ${mode}`}>
    <div className="section-heading"><div><span>{label}</span><h2>{version}</h2><p>{mode === "champion" ? "Executable only through Telegram approval." : mode === "lab" ? "Legal XI from the live squad; transfer optimization is not part of V5 yet." : "Research candidate; cannot execute or promote itself."}</p></div><span className="section-chip">{mode === "champion" ? <><ShieldCheck size={12} /> PRODUCTION</> : <><FlaskConical size={12} /> {mode === "lab" ? "LAB ONLY" : "SHADOW ONLY"}</>}</span></div>
    <div className="model-xi-stats"><div><span>Formation</span><strong>{formation(lineup)}</strong></div><div><span>XI + captain</span><strong>{points.toFixed(1)}</strong></div><div><span>Robust score</span><strong>{robustPoints == null ? "—" : robustPoints.toFixed(1)}</strong></div><div><span>Captain</span><strong>{lineup.find((player) => player.id === captainId)?.name ?? "—"}</strong></div></div>
    <ProjectionPitch lineup={lineup} bench={bench} captainId={captainId} viceId={viceId} bootstrap={bootstrap} />
    <div className="model-xi-evidence"><div><span>{uniqueLabel}</span><p>{comparisonAvailable ? unique.join(", ") || "None — the compared XIs match." : "N/A — a same-gameweek comparison is not available."}</p></div><div><span>FIRST-GW TRANSFERS</span><p>{transferNote ?? (transfers?.length ? transfers.map((move) => `${move.out_name ?? "?"} → ${move.in_name ?? "?"}`).join(" · ") : "None")}</p></div></div>
  </section>;
}

export default async function ModelComparePage() {
  const [autopilot, dashboard, v5] = await Promise.all([getAutopilotData(), getDashboardData(), getV5Projections()]);
  const plan = autopilot?.plan;
  const candidate = autopilot?.shadow_v42;
  const championLineup = plan?.target_starters ?? [];
  const championBench = plan?.bench ?? [];
  const candidateLineup = candidate && candidate.gw === plan?.gw ? candidate.lineup ?? [] : [];
  const candidateBench = candidate && candidate.gw === plan?.gw ? candidate.bench ?? [] : [];
  const championIds = new Set(championLineup.flatMap((player) => player.id == null ? [] : [player.id]));
  const candidateIds = new Set(candidateLineup.flatMap((player) => player.id == null ? [] : [player.id]));
  const overlap = [...championIds].filter((id) => candidateIds.has(id)).length;
  const championCaptain = plan?.captain?.id;
  const championPoints = plan?.decision_summary?.uncertainty?.mean_with_captain ?? scoringPoints(championLineup, championCaptain);
  const candidatePoints = candidate?.mean_points_with_captain ?? scoringPoints(candidateLineup, candidate?.captain_id);
  const candidateReady = candidateLineup.length === 11 && candidateBench.length === 4;
  const liveSquadIds = new Set((autopilot?.dashboard.players ?? []).flatMap((player) => player.id == null ? [] : [player.id]));
  const v5Selection = v5.available && v5.gameweek === plan?.gw ? selectV5Lineup(v5.players.filter((player) => liveSquadIds.has(player.element))) : null;
  const v5Ready = v5Selection?.lineup.length === 11 && v5Selection.bench.length === 4;

  return <div className="page-stack model-compare-page">
    <PageHeader eyebrow={`MODEL XI LAB · GW${plan?.gw ?? dashboard.gameweek}`} title="Compare model team selections" description="The same player images and formation view as My Team, using each model’s own selected XI, bench order and captain." updated={plan?.generated_at ? new Date(plan.generated_at).toLocaleString("en-MY", { dateStyle: "medium", timeStyle: "short" }) : undefined} />
    <section className="metric-grid"><MetricCard label="Production model" value={plan?.projection_version ?? plan?.model_version ?? "—"} detail="Current champion" tone="positive" /><MetricCard label="V4.2 shadow" value={candidateReady ? candidate?.formation ?? "Ready" : "Unavailable"} detail={candidate?.model_version ?? "No same-GW artifact"} tone={candidateReady ? "warning" : undefined} /><MetricCard label="V5 lineup lab" value={v5Ready ? formation(v5Selection?.lineup ?? []) : "Unavailable"} detail={v5.projection_version} tone={v5Ready ? "warning" : undefined} /><MetricCard label="V4 XI overlap" value={candidateReady ? `${overlap}/11` : "—"} detail="Champion versus V4.2" /></section>
    {plan && championLineup.length === 11 ? <div className="model-compare-grid"><ModelXi label="CHAMPION XI" version={plan.projection_version ?? plan.model_version ?? "competitive-v4.0"} mode="champion" lineup={championLineup} bench={championBench} captainId={championCaptain} viceId={plan.vice?.id} points={championPoints} unique={candidateReady ? namesOnly(championLineup, candidateIds) : []} uniqueLabel="UNIQUE VS V4.2 XI" comparisonAvailable={candidateReady} transfers={plan.transfers} bootstrap={dashboard.bootstrap} />{candidateReady ? <ModelXi label="CANDIDATE XI" version={candidate?.model_version ?? "competitive-v4.2-shadow"} mode="shadow" lineup={candidateLineup} bench={candidateBench} captainId={candidate?.captain_id} points={candidatePoints} robustPoints={candidate?.robust_points_with_captain} unique={namesOnly(candidateLineup, championIds)} transfers={candidate?.transfers} bootstrap={dashboard.bootstrap} /> : <section className="surface model-xi-empty"><FlaskConical /><h2>No comparable V4.2 team sheet</h2><p>{candidate && candidate.gw !== plan.gw ? `Latest shadow is GW${candidate.gw}; production is GW${plan.gw}. Cross-gameweek comparison is blocked.` : candidate?.optimizer_error ?? "Run the synchronized pipeline to generate the current candidate XI."}</p></section>}{v5Ready && v5Selection ? <ModelXi label="V5 LINEUP LAB" version={v5.projection_version} mode="lab" lineup={v5Selection.lineup} bench={v5Selection.bench} captainId={v5Selection.captainId} points={v5Selection.points} robustPoints={v5Selection.robustPoints} unique={namesOnly(v5Selection.lineup, championIds)} transferNote="Not modeled — V5 currently optimizes the XI from your live 15 only." bootstrap={dashboard.bootstrap} /> : <section className="surface model-xi-empty"><FlaskConical /><h2>No comparable V5 lineup</h2><p>{v5.available && v5.gameweek !== plan.gw ? `V5 targets GW${v5.gameweek}; production is GW${plan.gw}. Cross-gameweek comparison is blocked.` : v5.reason ?? "V5 does not have all 15 live-squad projections."}</p></section>}</div> : <section className="surface model-xi-empty"><ShieldCheck /><h2>Canonical plan unavailable</h2><p>Generate a fresh synchronized plan before comparing model selections.</p></section>}
    <p className="execution-note"><strong>Interpretation:</strong> a different XI shows a model disagreement, not proof that one model will score more. V4.2 remains shadow-only until its live calibration gates pass and you explicitly approve promotion.</p>
  </div>;
}
