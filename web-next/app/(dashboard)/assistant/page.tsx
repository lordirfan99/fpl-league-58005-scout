import { ArrowRight, Bot, CircleAlert, Cpu, ShieldCheck, Sparkles } from "lucide-react";
import { MetricCard } from "@/components/metric-card";
import { PageHeader } from "@/components/page-header";
import { getAutopilotData } from "@/lib/autopilot";
import { getDashboardData } from "@/lib/data";
import { getCompetitiveRecommendation } from "@/lib/competitive";

export default async function AssistantPage() {
  const [data, autopilot] = await Promise.all([getDashboardData(), getAutopilotData()]);
  const { manager } = data;
  const elite = await getCompetitiveRecommendation(data.leagueId, data.gameweek);
  const competitive = elite.competitive;
  const botPlan = autopilot?.plan;
  const botMove = botPlan?.transfers?.[0];
  const botCaptain = botPlan?.captain;
  const botConnected = Boolean(autopilot);

  return <div className="page-stack">
    <PageHeader eyebrow={`DECISION ASSISTANT · ${competitive.modelVersion.toUpperCase()}`} title="Your weekly decision board" description="Catch the elite baseline first, then preserve it and attack only with model-supported edges." updated={botPlan?.generated_at ? new Date(botPlan.generated_at).toLocaleString("en-MY", { dateStyle: "medium", timeStyle: "short" }) : elite.meta.snapshotAt ? new Date(elite.meta.snapshotAt).toLocaleString("en-MY", { dateStyle: "medium", timeStyle: "short" }) : undefined} />
    <section className="decision-hero"><div><span className="hero-kicker">{competitive.phase} PHASE · {botConnected ? "GCP AUTOPILOT AUTHORITY" : "WEBSITE SHADOW MODE"}</span><h2>{botMove ? <>{botMove.out_name} <ArrowRight size={22} /> {botMove.in_name}</> : competitive.phase === "CATCH" ? "Close the structural gap first" : "Hold and protect flexibility"}</h2><p>{competitive.phaseReason} {botMove ? `${botMove.hit ? "Paid" : "Free"} transfer · ${format(botMove.gain)} horizon xPts gain.` : "No executable bot transfer is available."} Telegram remains the approval and execution channel.</p></div><div className="hero-score"><span>Alignment</span><strong>{competitive.alignment.toFixed(0)}%</strong></div></section>
    <section className="metric-grid"><MetricCard label="Your GW" value={`${manager.gw_points} pts`} detail={`${(manager.gw_points - elite.eliteAverage).toFixed(1)} vs elite`} tone={manager.gw_points >= elite.eliteAverage ? "positive" : "warning"} /><MetricCard label="Elite alignment" value={`${competitive.alignment.toFixed(0)}%`} detail={`${competitive.coreOwned}/${competitive.coreSize} core · target ${competitive.targetAlignment}%`} tone={competitive.alignment >= competitive.targetAlignment ? "positive" : "warning"} /><MetricCard label="Data quality" value={elite.meta.qualityStatus.toUpperCase()} detail={elite.meta.freshnessHours == null ? "Snapshot age unknown" : `${elite.meta.freshnessHours.toFixed(1)}h old`} tone={elite.meta.stale || elite.meta.qualityStatus !== "valid" ? "warning" : "positive"} /><MetricCard label="Competitive mode" value={competitive.phase} detail={`GW${data.gameweek} · ${competitive.modelVersion}`} tone={competitive.phase === "CATCH" || competitive.phase === "CHASE" ? "warning" : "positive"} /></section>
    <div className="content-grid decision-grid">
      <section className="surface"><div className="section-heading"><div><span>AUTHORITATIVE PLAN</span><h2>GCP bot action</h2></div><span className="section-chip"><Cpu size={12} /> {botPlan?.status ?? "offline"}</span></div><div className="action-list">{botMove ? <article className="action-row"><span className="action-state do">BOT</span><div><strong>{botMove.out_name} <ArrowRight size={14} /> {botMove.in_name}</strong><small>{botMove.out_pos} · {botMove.hit ? "Includes hit" : "Free transfer"}</small><p>{format(botMove.gain_gw1)} next-GW gain · {format(botMove.gain)} horizon gain</p></div><b>+{format(botMove.gain)}<small>horizon</small></b></article> : <div className="empty-state"><ShieldCheck /><h3>No executable transfer</h3><p>The website will not substitute an elite heuristic for the bot.</p></div>}</div></section>
      <section className="surface"><div className="section-heading"><div><span>ELITE ALIGNMENT</span><h2>Critical core gaps</h2></div><span className="section-chip">{competitive.phase}</span></div><div className="captain-list">{competitive.criticalMissing.length ? competitive.criticalMissing.slice(0, 4).map((player, index) => <article className="captain-row" key={player.element}><span>{index + 1}</span><div><strong>{player.name}</strong><small>{player.position} · {player.team} · {player.fixture}</small></div><b>{player.eliteOwnership.toFixed(1)}%<small>elite</small></b><em>ELITE + MODEL AGREE</em></article>) : <div className="empty-state"><ShieldCheck /><h3>No critical core gap</h3><p>Your current structure already covers the validated elite core.</p></div>}</div></section>
    </div>
    <div className="content-grid decision-grid">
      <section className="surface"><div className="section-heading"><div><span>CONTROLLED EDGE</span><h2>Model-backed deviations</h2></div><span className="section-chip"><Sparkles size={13} /> Shadow only</span></div><div className="captain-list">{competitive.modelEdges.length ? competitive.modelEdges.slice(0, 4).map((player, index) => <article className="captain-row" key={player.element}><span>{index + 1}</span><div><strong>{player.name}</strong><small>{player.position} · {player.fixture}</small></div><b>{player.xpts.toFixed(1)}<small>xPts</small></b><em>{player.eliteOwnership.toFixed(1)}% elite</em></article>) : <div className="empty-state"><ShieldCheck /><h3>No clean edge yet</h3><p>Do not force a differential while the model has no supported deviation.</p></div>}</div></section>
      <section className="surface"><div className="section-heading"><div><span>DISAGREEMENT CHECK</span><h2>Elite-only signals</h2></div><span className="section-chip">Investigate</span></div><div className="captain-list">{competitive.disagreements.length ? competitive.disagreements.slice(0, 4).map((player, index) => <article className="captain-row" key={player.element}><span>{index + 1}</span><div><strong>{player.name}</strong><small>{player.position} · {player.fixture}</small></div><b>{player.eliteOwnership.toFixed(1)}%<small>elite</small></b><em>MODEL NOT CONFIRMED</em></article>) : <div className="empty-state"><ShieldCheck /><h3>No major disagreement</h3><p>Elite consensus and the projection filter are broadly aligned.</p></div>}</div></section>
    </div>
    <section className="surface"><div className="section-heading"><div><span>MONITOR</span><h2>Elite players missing from your squad</h2></div><span className="section-chip"><Sparkles size={13} /> Top signals</span></div><div className="monitor-grid">{elite.missing.map((player) => <article key={player.element}><span className="monitor-icon">{player.risk ? <CircleAlert /> : <ShieldCheck />}</span><div><strong>{player.name}</strong><small>{player.position} · {player.team}</small><p>{player.fixture} · FDR {player.fdr ?? "—"} · {player.role}</p></div><b>{player.eliteOwnership.toFixed(1)}%<small>elite</small></b></article>)}</div></section>
    <div className="execution-note"><BotStatus connected={botConnected} /></div>
  </div>;
}

function format(value?: number) { return typeof value === "number" ? value.toFixed(1) : "—"; }

function BotStatus({ connected }: { connected: boolean }) {
  return <><span className={connected ? "status-dot" : "status-dot warning"} /><div><strong>{connected ? "Live GCP bot connected in read-only mode" : "GCP bot connection unavailable"}</strong><p>{connected ? "The website shows the bot’s real plan and supporting league intelligence. Telegram remains the only approval and execution authority." : "League intelligence is still available, but it cannot be promoted to an executable action while the bot is disconnected."}</p></div></>;
}
