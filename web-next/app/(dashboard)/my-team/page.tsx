import { MetricCard } from "@/components/metric-card";
import { PageHeader } from "@/components/page-header";
import { Pitch } from "@/components/pitch";
import { getAutopilotData } from "@/lib/autopilot";
import { getDashboardData } from "@/lib/data";
import { getLiveTeam } from "@/lib/live";
import type { Pick } from "@/lib/types";

const positionFromElementType = (elementType?: number): Pick["position"] => elementType === 1 ? "GKP" : elementType === 2 ? "DEF" : elementType === 3 ? "MID" : "FWD";

export default async function MyTeamPage() {
  const [data, autopilot, live] = await Promise.all([getDashboardData(), getAutopilotData(), getLiveTeam()]);
  const { manager } = data;
  const plan = autopilot?.plan;
  const decision = plan?.decision_summary;
  const liveGameweek = live?.gameweek ?? autopilot?.dashboard.gw;
  const liveTeam = liveGameweek != null && liveGameweek >= data.gameweek && ((live?.picks?.length === 15) || (autopilot?.dashboard.players?.length === 15));
  const displayGameweek = liveTeam ? liveGameweek : data.gameweek;
  const livePlayers = live?.picks?.length === 15 ? live.picks.map((pick) => ({ element: pick.element, name: pick.web_name, position: positionFromElementType(data.bootstrap.elements.find((player) => player.id === pick.element)?.element_type), team: data.bootstrap.teams.find((team) => team.id === pick.team)?.name ?? "—", cost: pick.now_cost / 10, multiplier: pick.multiplier, is_captain: pick.is_captain, is_vice_captain: pick.is_vice_captain })) : autopilot?.dashboard.players?.length === 15 ? autopilot.dashboard.players.map((player) => ({ element: player.id ?? 0, name: player.name ?? "Unknown", position: ((player.position ?? player.pos ?? "MID") as Pick["position"]), team: String(player.club ?? "—"), cost: Number(player.cost ?? 0) / 10, multiplier: player.role === "C" ? 2 : 1, is_captain: player.role === "C", is_vice_captain: player.role === "VC" })) : [];
  const squad: Pick[] = liveTeam ? livePlayers : manager.squad;
  const historical = !liveTeam && plan?.gw != null && plan.gw !== data.gameweek;
  const deadline = plan?.deadline ? new Date(plan.deadline) : null;
  const livePoints = live?.points;
  const liveTotal = live?.entry.total_points;
  const liveOverallRank = live?.entry.overall_rank;
  const liveLeagueRank = live?.league?.entry_rank;
  const playerMeta = (pick: Pick) => {
    const player = data.bootstrap.elements.find((row) => row.id === pick.element);
    const teamId = player?.team;
    const relevantFixtures = live?.fixtures.filter((fixture) => fixture.team_h === teamId || fixture.team_a === teamId) ?? [];
    if (relevantFixtures.some((fixture) => fixture.started)) return `${live?.picks.find((row) => row.element === pick.element)?.points ?? 0} pts`;
    const nextFixture = relevantFixtures[0];
    if (!nextFixture || !teamId) return "Fixture TBC";
    const opponentId = nextFixture.team_h === teamId ? nextFixture.team_a : nextFixture.team_h;
    const opponent = data.bootstrap.teams.find((team) => team.id === opponentId)?.short_name ?? "TBC";
    return `${opponent} (${nextFixture.team_h === teamId ? "H" : "A"})`;
  };
  return <div className="page-stack">
    <PageHeader eyebrow={`${liveTeam ? "OFFICIAL LIVE TEAM" : historical ? "LAST TEAM CAPTURE" : "MY TEAM"} · GW${displayGameweek}`} title={live?.entry.entry_name || manager.entry_name} description={`${live?.entry.player_name || manager.player_name} · FPL ID ${manager.entry_id.toLocaleString()}${liveTeam ? ` · Current GW${displayGameweek} squad, score and ranks from official FPL.` : historical ? ` · This is a completed-GW review, not the current GW${plan?.gw} lineup.` : ""}`} updated={liveTeam && live?.fetched_at ? new Date(live.fetched_at).toLocaleString("en-MY", { dateStyle: "medium", timeStyle: "short" }) : data.fetchedAt ? new Date(data.fetchedAt).toLocaleString("en-MY", { dateStyle: "medium", timeStyle: "short" }) : undefined} />
    {liveTeam ? <section className="execution-note"><span className="status-dot" /><div><strong>GW{displayGameweek} official live data</strong><p>The squad, provisional score, total points and ranks below come directly from FPL. They refresh when this page loads and can still change until the Gameweek is finalised.</p></div></section> : null}
    {historical ? <section className="execution-note"><span className="status-dot warning" /><div><strong>Historical squad view</strong><p>This pitch is the latest captured GW{data.gameweek} team. For the upcoming GW{plan?.gw} decision, use the Assistant or Autopilot plan rather than treating these player event totals as live instructions.</p></div></section> : null}
    <section className="metric-grid"><MetricCard label={`GW${displayGameweek} points`} value={liveTeam && livePoints != null ? `${livePoints}` : `${manager.gw_points}`} detail={liveTeam ? "Official live · provisional" : "Completed snapshot"} tone={liveTeam ? "warning" : undefined} /><MetricCard label="Overall points" value={`${liveTeam && liveTotal != null ? liveTotal : manager.total_points}`} detail={`Overall rank #${(liveTeam && liveOverallRank ? liveOverallRank : manager.overall_rank).toLocaleString()}`} /><MetricCard label="League rank" value={`#${liveTeam && liveLeagueRank ? liveLeagueRank.toLocaleString() : manager.league_rank.toLocaleString()}`} detail={liveTeam && live?.league ? `${live.league.name} · ${live.league.rank_count.toLocaleString()} teams` : "Latest completed snapshot"} /><MetricCard label="Next deadline" value={plan?.gw ? `GW${plan.gw}` : "—"} detail={deadline ? deadline.toLocaleString("en-MY", { dateStyle: "medium", timeStyle: "short" }) : "Not published"} tone={historical ? "warning" : undefined} /></section>
    <div className="content-grid team-layout"><section className="surface pitch-surface"><div className="section-heading"><div><span>{liveTeam ? "OFFICIAL LIVE STARTING XI" : "CAPTURED STARTING XI"}</span><h2>{historical ? `GW${data.gameweek} review` : liveTeam ? `GW${displayGameweek} team` : "Pitch view"}</h2></div><span className="section-chip">11 + 4</span></div><Pitch squad={squad} bootstrap={data.bootstrap} metaForPick={liveTeam ? playerMeta : undefined} /></section><aside className="insight-rail"><section className="surface insight-card primary"><span>NEXT DEADLINE ACTION</span><h2>{decision?.recommended_action === "LINEUP ONLY" ? "Set lineup, hold transfer" : decision?.recommended_action ?? "Open decision board"}</h2><p>{decision?.reason ?? "A fresh bot decision has not been published yet."}</p><a href="/assistant">Open decision board</a></section><section className="surface insight-card"><span>PLANNING TARGET</span><strong>{plan?.gw ? `GW${plan.gw}` : "—"}</strong><p>{plan?.status === "rejected" ? "Plan is read-only until the source refresh is complete." : "Use this target across Assistant, Planner and Autopilot."}</p></section><section className="surface insight-card"><span>AVAILABILITY</span><strong>{plan?.target_starters?.some((player) => player.status !== "a") ? "Check flags" : "All clear"}</strong><p>{plan?.target_starters?.filter((player) => player.status !== "a").map((player) => player.name).join(", ") || "No flagged players in the target XI."}</p></section></aside></div>
  </div>;
}
