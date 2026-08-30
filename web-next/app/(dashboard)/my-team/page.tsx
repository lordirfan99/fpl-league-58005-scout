import { MetricCard } from "@/components/metric-card";
import { PageHeader } from "@/components/page-header";
import { Pitch } from "@/components/pitch";
import { getAutopilotData } from "@/lib/autopilot";
import { getDashboardData } from "@/lib/data";

export default async function MyTeamPage() {
  const [data, autopilot] = await Promise.all([getDashboardData(), getAutopilotData()]);
  const { manager } = data;
  const plan = autopilot?.plan;
  const decision = plan?.decision_summary;
  const historical = plan?.gw != null && plan.gw !== data.gameweek;
  const deadline = plan?.deadline ? new Date(plan.deadline) : null;
  return <div className="page-stack">
    <PageHeader eyebrow={`${historical ? "LAST TEAM CAPTURE" : "MY TEAM"} · GW${data.gameweek}`} title={manager.entry_name} description={`${manager.player_name} · FPL ID ${manager.entry_id.toLocaleString()}${historical ? ` · This is a completed-GW review, not the current GW${plan?.gw} lineup.` : ""}`} updated={data.fetchedAt ? new Date(data.fetchedAt).toLocaleString("en-MY", { dateStyle: "medium", timeStyle: "short" }) : undefined} />
    {historical ? <section className="execution-note"><span className="status-dot warning" /><div><strong>Historical squad view</strong><p>This pitch is the latest captured GW{data.gameweek} team. For the upcoming GW{plan?.gw} decision, use the Assistant or Autopilot plan rather than treating these player event totals as live instructions.</p></div></section> : null}
    <section className="metric-grid"><MetricCard label={`GW${data.gameweek} points`} value={`${manager.gw_points}`} detail="Completed-snapshot points" /><MetricCard label="Overall points" value={`${manager.total_points}`} detail={`Rank ${manager.overall_rank.toLocaleString()}`} /><MetricCard label="League rank" value={`#${manager.league_rank}`} detail="At captured snapshot" /><MetricCard label="Next deadline" value={plan?.gw ? `GW${plan.gw}` : "—"} detail={deadline ? deadline.toLocaleString("en-MY", { dateStyle: "medium", timeStyle: "short" }) : "Plan unavailable"} tone={historical ? "warning" : undefined} /></section>
    <div className="content-grid team-layout"><section className="surface pitch-surface"><div className="section-heading"><div><span>CAPTURED STARTING XI</span><h2>{historical ? `GW${data.gameweek} review` : "Pitch view"}</h2></div><span className="section-chip">11 + 4</span></div><Pitch squad={manager.squad} bootstrap={data.bootstrap} showEventPoints={!historical} /></section><aside className="insight-rail"><section className="surface insight-card primary"><span>NEXT DEADLINE ACTION</span><h2>{decision?.recommended_action === "LINEUP ONLY" ? "Set lineup, hold transfer" : decision?.recommended_action ?? "Open decision board"}</h2><p>{decision?.reason ?? "A fresh bot decision has not been published yet."}</p><a href="/assistant">Open decision board</a></section><section className="surface insight-card"><span>PLANNING TARGET</span><strong>{plan?.gw ? `GW${plan.gw}` : "—"}</strong><p>{plan?.status === "rejected" ? "Plan is read-only until the source refresh is complete." : "Use this target across Assistant, Planner and Autopilot."}</p></section><section className="surface insight-card"><span>AVAILABILITY</span><strong>{plan?.target_starters?.some((player) => player.status !== "a") ? "Check flags" : "All clear"}</strong><p>{plan?.target_starters?.filter((player) => player.status !== "a").map((player) => player.name).join(", ") || "No flagged players in the target XI."}</p></section></aside></div>
  </div>;
}
