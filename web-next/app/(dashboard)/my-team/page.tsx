import { MetricCard } from "@/components/metric-card";
import { PageHeader } from "@/components/page-header";
import { Pitch } from "@/components/pitch";
import { getCompetitiveRecommendation } from "@/lib/competitive";
import { getDashboardData } from "@/lib/data";

export default async function MyTeamPage() {
  const data = await getDashboardData();
  const { manager } = data;
  const recommendation = await getCompetitiveRecommendation(data.leagueId, data.gameweek);
  const top = recommendation.transfers[0];
  return <div className="page-stack">
    <PageHeader eyebrow={`MY TEAM · GAMEWEEK ${data.gameweek}`} title={manager.entry_name} description={`${manager.player_name} · FPL ID ${manager.entry_id.toLocaleString()}`} updated={data.fetchedAt ? new Date(data.fetchedAt).toLocaleString("en-MY", { dateStyle: "medium", timeStyle: "short" }) : undefined} />
    <section className="metric-grid"><MetricCard label="Gameweek points" value={`${manager.gw_points}`} detail="Official snapshot" /><MetricCard label="Overall points" value={`${manager.total_points}`} detail={`Rank ${manager.overall_rank.toLocaleString()}`} /><MetricCard label="League rank" value={`#${manager.league_rank}`} detail="KK Old Boys" /><MetricCard label="Squad value" value={`£${manager.squad_cost.toFixed(1)}m`} detail={`${manager.transfers_made} transfers`} /></section>
    <div className="content-grid team-layout"><section className="surface pitch-surface"><div className="section-heading"><div><span>STARTING XI</span><h2>Pitch view</h2></div><span className="section-chip">11 + 4</span></div><Pitch squad={manager.squad} bootstrap={data.bootstrap} /></section><aside className="insight-rail"><section className="surface insight-card primary"><span>NEXT ACTION</span><h2>{top && top.signalGain > 5 ? "Review one transfer" : "Hold your transfer"}</h2><p>{top ? `${top.outgoing.name} → ${top.incoming.name} is the strongest current V4 signal. ${top.gainBasis}.` : "No move clears the V4 competitive-signal threshold."}</p><a href="/assistant">Open decision board</a></section><section className="surface insight-card"><span>ELITE ALIGNMENT</span><strong>{recommendation.eliteOverlap}/15</strong><p>Your squad overlap with the selected elite cohort.</p></section><section className="surface insight-card"><span>AVAILABILITY</span><strong>{recommendation.risks.length ? `${recommendation.risks.length} flags` : "All clear"}</strong><p>{recommendation.risks.map((player) => player.name).join(", ") || "No current injury or minutes warnings."}</p></section></aside></div>
  </div>;
}
