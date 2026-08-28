import { Activity, Beaker, BrainCircuit, CheckCircle2, FlaskConical, LockKeyhole, ShieldCheck } from "lucide-react";
import { MetricCard } from "@/components/metric-card";
import { PageHeader } from "@/components/page-header";
import { V5PlayerExplorer } from "@/components/v5-player-explorer";
import { getV5Projections } from "@/lib/v5";

export default async function V5LabPage() {
  const data = await getV5Projections();
  const top = data.players[0];
  const ready = data.players.filter((player) => player.quality_issues.length === 0).length;
  return <div className="page-stack v5-page">
    <PageHeader eyebrow="PLAYER INTELLIGENCE · RESEARCH LANE" title="V5 Projection Lab" description="Independent football projections, uncertainty and decision research—kept outside the live execution path." updated={data.generated_at ? new Date(data.generated_at).toLocaleString("en-MY", { timeZone: "Asia/Kuala_Lumpur" }) : undefined} />
    <section className="v5-hero">
      <div><span><FlaskConical size={15} /> ISOLATED LABORATORY</span><h2>Predict football first.<br />Fight the league second.</h2><p>V5 separates raw player ability and fixture outcomes from ownership, rank and captaincy pressure. It cannot replace production or execute an FPL action.</p></div>
      <div className={`v5-live-orb ${data.available ? "online" : "offline"}`}><Activity size={25} /><strong>{data.available ? "LIVE" : "LOCAL"}</strong><small>{data.projection_version}</small></div>
    </section>
    <div className="model-lanes">
      <article><ShieldCheck /><span>PRODUCTION</span><strong>competitive-v4.0</strong><small>Current decision authority</small></article>
      <article><LockKeyhole /><span>ACTIVE SHADOW</span><strong>V4.2</strong><small>Frozen promotion lifecycle</small></article>
      <article className="lab"><Beaker /><span>RESEARCH</span><strong>projection-v5.0-lab</strong><small>No execution authority</small></article>
    </div>
    {data.available ? <>
      <div className="metric-grid"><MetricCard label="Target gameweek" value={`GW${data.gameweek}`} detail="Next deadline-safe projection" /><MetricCard label="Player universe" value={String(data.players.length)} detail="Not restricted by ownership" tone="positive" /><MetricCard label="Quality-ready" value={`${ready}/${data.players.length}`} detail="Complete current inputs" /><MetricCard label="Top projection" value={top ? `${top.xpts_mean.toFixed(1)} xPts` : "—"} detail={top?.name ?? "No player rows"} /></div>
      <V5PlayerExplorer players={data.players} />
    </> : <section className="surface v5-unavailable"><BrainCircuit /><div><span>DEPLOYMENT REQUIRED</span><h2>V5 API is not live yet</h2><p>The dashboard is ready, but the public API has not deployed <code>/v1/projections/current</code>. Production remains safe and unchanged.</p><small>{data.reason}</small></div></section>}
    <section className="shadow-safety"><div><CheckCircle2 /><div><strong>Ownership-independent</strong><small>Raw xPts never reads elite ownership or league rank.</small></div></div><div><LockKeyhole /><div><strong>Read-only by design</strong><small>No browser or API endpoint can mutate your FPL team.</small></div></div><div><ShieldCheck /><div><strong>Promotion gated</strong><small>V5 stays LAB until V4.2 closes and V5 passes its own evidence gates.</small></div></div></section>
  </div>;
}
