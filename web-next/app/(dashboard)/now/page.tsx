import Link from "next/link";
import { AlertTriangle, ArrowRight, CheckCircle2, Clock3, ShieldCheck } from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { getCompetitiveRecommendation } from "@/lib/competitive";
import { getDashboardData } from "@/lib/data";
import { deriveSeasonContext } from "@/lib/season";

export default async function NowPage() {
  const data = await getDashboardData().catch(() => null);
  const season = data ? deriveSeasonContext(data.bootstrap.events, { finalizedGw: data.gameweek }) : null;
  const target = season?.nextDeadlineGw;
  const rec = data && target ? await getCompetitiveRecommendation(data.leagueId, target).catch(() => null) : null;
  const locked = ["locked", "live_review", "finalized"].includes(rec?.packetStatus ?? "");
  const move = rec?.transfers[0];
  const captain = rec?.captains[0];
  const deadline = season?.nextDeadline ? new Date(season.nextDeadline) : null;
  return <div className="page-stack now-workspace">
    <PageHeader eyebrow={`NOW · ${rec?.packetStatus?.replace("_", " ").toUpperCase() ?? "CONNECTING"}`} title={locked ? "Deadline locked" : "Your next FPL decision"} description="One clear, read-only plan with evidence. Apply every FPL change manually." updated={rec?.meta.snapshotAt ? new Date(rec.meta.snapshotAt).toLocaleString("en-MY") : undefined} />
    <section className="decision-hero"><div><span className="hero-kicker">GW{target ?? "—"} · {rec?.competitive.phase ?? "REVIEW"}</span><h2>{locked ? "Review live outcomes" : move ? <>{move.outgoing.name} <ArrowRight size={22} /> {move.incoming.name}</> : "Plan is being prepared"}</h2><p>{locked ? "Your pre-deadline advisory is frozen. Follow points, rank and differentials in Live." : rec?.competitive.phaseReason ?? "Waiting for valid baseline and official inputs."}</p></div><div className="hero-score"><span>Deadline</span><strong>{season?.hoursToDeadline == null ? "—" : season.hoursToDeadline < 24 ? `${Math.ceil(season.hoursToDeadline)}h` : `${Math.floor(season.hoursToDeadline / 24)}d`}</strong></div></section>
    <section className="now-actions">
      <article><CheckCircle2 /><span>Primary plan</span><strong>{move ? `${move.outgoing.name} → ${move.incoming.name}` : "Hold pending"}</strong><small>{locked ? "Locked evidence" : "Apply manually after team news"}</small></article>
      <article><ShieldCheck /><span>Captain</span><strong>{captain?.name ?? "Pending"}</strong><small>{locked ? "No post-deadline advice" : "Confirm final lineup news"}</small></article>
      <article><Clock3 /><span>Deadline</span><strong>{deadline ? deadline.toLocaleString("en-MY", { dateStyle: "medium", timeStyle: "short" }) : "TBC"}</strong><small>Source GW{rec?.sourceGameweek ?? "—"} · {rec?.meta.qualityStatus ?? "unknown"}</small></article>
      <article className={rec?.risks.length ? "warning" : ""}><AlertTriangle /><span>Risk check</span><strong>{rec?.risks.length ? `${rec.risks.length} to review` : "No flagged squad risks"}</strong><small>Availability is checked before a recommendation is shown.</small></article>
    </section>
    <section className="surface"><div className="section-heading"><div><span>WHAT NEXT</span><h2>{locked ? "Live review only" : "Review and approve your plan"}</h2><p>{locked ? "Use the live workspace for points and rank movement. The next candidate starts after finalization." : "Review the official-data plan, then create a time-limited Telegram approval from Plan."}</p></div></div><div className="workspace-links"><Link href="/plan">Open Plan</Link><Link href="/live">Open Live review</Link><Link href="/journal">Open journal</Link></div></section>
    {!locked && rec?.transfers.slice(1, 4).length ? <section className="surface"><div className="section-heading"><div><span>ALTERNATIVES</span><h2>Only meaningful trade-offs</h2></div></div><div className="planner-grid">{rec.transfers.slice(1, 4).map((option) => <article key={`${option.outgoing.element}-${option.incoming.element}`}><span>{option.outgoing.name}</span><strong>→ {option.incoming.name}</strong><small>+{option.xptsGain.toFixed(1)} next-GW gross xPts · verify final news</small></article>)}</div></section> : null}
  </div>;
}
