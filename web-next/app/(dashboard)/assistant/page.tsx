import { ArrowRight, Bot, CircleAlert, Cpu, ShieldCheck, Sparkles } from "lucide-react";
import { MetricCard } from "@/components/metric-card";
import { PageHeader } from "@/components/page-header";
import { getAutopilotData } from "@/lib/autopilot";
import { getDashboardData } from "@/lib/data";
import { buildRecommendations } from "@/lib/model";

export default async function AssistantPage() {
  const [data, autopilot] = await Promise.all([getDashboardData(), getAutopilotData()]);
  const { manager } = data;
  const elite = buildRecommendations(manager, data.managers, data.bootstrap, data.fixture);
  const botPlan = autopilot?.plan;
  const botMove = botPlan?.transfers?.[0];
  const botCaptain = botPlan?.captain;
  const botConnected = Boolean(autopilot);

  return <div className="page-stack">
    <PageHeader eyebrow="DECISION ASSISTANT" title="Your weekly decision board" description="GCP Autopilot makes the plan; league and elite signals explain the context." updated={botPlan?.generated_at ? new Date(botPlan.generated_at).toLocaleString("en-MY", { dateStyle: "medium", timeStyle: "short" }) : data.fetchedAt ? new Date(data.fetchedAt).toLocaleString("en-MY", { dateStyle: "medium", timeStyle: "short" }) : undefined} />
    <section className="decision-hero"><div><span className="hero-kicker">{botConnected ? "GCP AUTOPILOT AUTHORITY" : "WEBSITE SHADOW MODE"}</span><h2>{botMove ? <>{botMove.out_name} <ArrowRight size={22} /> {botMove.in_name}</> : "Hold and protect flexibility"}</h2><p>{botMove ? `${botMove.hit ? "Paid" : "Free"} transfer · ${format(botMove.gain)} horizon xPts gain · Telegram remains the approval and execution channel.` : "No executable bot transfer is available. Elite signals remain monitoring evidence only."}</p></div><div className="hero-score"><span>{botConnected ? "Model" : "Mode"}</span><strong>{botPlan?.engine_display ?? "Shadow"}</strong></div></section>
    <section className="metric-grid"><MetricCard label="Your GW" value={`${manager.gw_points} pts`} detail={`${(manager.gw_points - elite.eliteAverage).toFixed(1)} vs elite`} tone={manager.gw_points >= elite.eliteAverage ? "positive" : "warning"} /><MetricCard label="Elite overlap" value={`${elite.overlap}/15`} detail={`${elite.eliteCount} manager cohort`} /><MetricCard label="Bot captain" value={botCaptain?.name ?? "—"} detail={botCaptain?.xpts != null ? `${format(botCaptain.xpts)} xPts` : "Awaiting bot plan"} /><MetricCard label="Target xPts" value={format(botPlan?.target_net_scoring_xpts)} detail={botPlan?.status ?? "Not connected"} tone={botConnected ? "positive" : "warning"} /></section>
    <div className="content-grid decision-grid">
      <section className="surface"><div className="section-heading"><div><span>AUTHORITATIVE PLAN</span><h2>GCP bot action</h2></div><span className="section-chip"><Cpu size={12} /> {botPlan?.status ?? "offline"}</span></div><div className="action-list">{botMove ? <article className="action-row"><span className="action-state do">BOT</span><div><strong>{botMove.out_name} <ArrowRight size={14} /> {botMove.in_name}</strong><small>{botMove.out_pos} · {botMove.hit ? "Includes hit" : "Free transfer"}</small><p>{format(botMove.gain_gw1)} next-GW gain · {format(botMove.gain)} horizon gain</p></div><b>+{format(botMove.gain)}<small>horizon</small></b></article> : <div className="empty-state"><ShieldCheck /><h3>No executable transfer</h3><p>The website will not substitute an elite heuristic for the bot.</p></div>}</div></section>
      <section className="surface"><div className="section-heading"><div><span>ELITE CONTEXT</span><h2>Shadow alternatives</h2></div><span className="section-chip">Not executable</span></div><div className="captain-list">{elite.transfers.slice(0, 4).map((move, index) => <article className="captain-row" key={`${move.outgoing.element}-${move.incoming.element}`}><span>{index + 1}</span><div><strong>{move.outgoing.name} → {move.incoming.name}</strong><small>{move.incoming.eliteOwnership.toFixed(1)}% elite · {move.incoming.fixture}</small></div><b>{move.xptsGain >= 0 ? "+" : ""}{move.xptsGain.toFixed(1)}<small>xPts</small></b><em>Comparison signal only</em></article>)}</div></section>
    </div>
    <section className="surface"><div className="section-heading"><div><span>MONITOR</span><h2>Elite players missing from your squad</h2></div><span className="section-chip"><Sparkles size={13} /> Top signals</span></div><div className="monitor-grid">{elite.missing.map((player) => <article key={player.element}><span className="monitor-icon">{player.risk ? <CircleAlert /> : <ShieldCheck />}</span><div><strong>{player.name}</strong><small>{player.position} · {player.team}</small><p>{player.fixture} · FDR {player.fdr ?? "—"}</p></div><b>{player.eliteOwnership.toFixed(1)}%<small>elite</small></b></article>)}</div></section>
    <div className="execution-note"><BotStatus connected={botConnected} /></div>
  </div>;
}

function format(value?: number) { return typeof value === "number" ? value.toFixed(1) : "—"; }

function BotStatus({ connected }: { connected: boolean }) {
  return <><span className={connected ? "status-dot" : "status-dot warning"} /><div><strong>{connected ? "Live GCP bot connected in read-only mode" : "GCP bot connection unavailable"}</strong><p>{connected ? "The website shows the bot’s real plan and supporting league intelligence. Telegram remains the only approval and execution authority." : "League intelligence is still available, but it cannot be promoted to an executable action while the bot is disconnected."}</p></div></>;
}
