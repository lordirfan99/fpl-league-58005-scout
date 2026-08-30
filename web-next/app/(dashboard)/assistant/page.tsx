import Link from "next/link";
import { ArrowRight, Bot, Clock3, ShieldCheck } from "lucide-react";
import { MetricCard } from "@/components/metric-card";
import { PageHeader } from "@/components/page-header";
import { getAutopilotData } from "@/lib/autopilot";
import { getDashboardData } from "@/lib/data";

const number = (value?: number) => typeof value === "number" ? value.toFixed(1) : "—";

export default async function AssistantPage() {
  const [autopilot, review] = await Promise.all([getAutopilotData(), getDashboardData().catch(() => null)]);
  const plan = autopilot?.plan;
  const decision = plan?.decision_summary;
  const move = plan?.transfers?.[0];
  const deadline = plan?.deadline ? new Date(plan.deadline) : null;
  const hoursRemaining = deadline ? Math.max(0, (deadline.getTime() - Date.now()) / 3_600_000) : null;
  const isLocked = plan?.status === "rejected";
  const action = decision?.recommended_action ?? (move ? "TRANSFER" : "REVIEW");
  const captain = plan?.captain?.name ?? decision?.captain_rankings?.find((item) => item.eligible)?.name;

  return <div className="page-stack">
    <PageHeader eyebrow={`DECISION ASSISTANT · TARGET GW${plan?.gw ?? "—"}`} title="Your next deadline, made clear" description="One current recommendation, clearly separated from historical team and league research." updated={plan?.generated_at ? new Date(plan.generated_at).toLocaleString("en-MY", { dateStyle: "medium", timeStyle: "short" }) : undefined} />
    <section className="decision-hero"><div><span className="hero-kicker">NEXT DEADLINE · GW{plan?.gw ?? "—"} · {isLocked ? "READ-ONLY REVIEW" : "PLAN READY"}</span><h2>{move ? <>{move.out_name} <ArrowRight size={22} /> {move.in_name}</> : action === "LINEUP ONLY" ? "Set your lineup — no transfer" : action}</h2><p>{decision?.reason ?? "A fresh canonical recommendation is not available yet."} {isLocked ? " The dashboard will not submit changes; use this as a review before Telegram approval." : " Review the plan before approving it through Telegram."}</p><Link href="/autopilot">Open full decision evidence</Link></div><div className="hero-score"><span>{hoursRemaining == null ? "Deadline" : "Time left"}</span><strong>{hoursRemaining == null ? "—" : hoursRemaining < 24 ? `${Math.ceil(hoursRemaining)}h` : `${Math.floor(hoursRemaining / 24)}d`}</strong></div></section>
    <section className="metric-grid"><MetricCard label="Action now" value={action === "LINEUP ONLY" ? "Set XI" : action} detail={move ? "Transfer candidate supplied" : "No transfer is proposed"} tone={isLocked ? "warning" : "positive"} /><MetricCard label="Target gameweek" value={`GW${plan?.gw ?? "—"}`} detail={deadline ? deadline.toLocaleString("en-MY", { dateStyle: "medium", timeStyle: "short" }) : "Deadline TBC"} /><MetricCard label="Data integrity" value={decision?.source_manifest?.status?.toUpperCase() ?? "CHECK"} detail={isLocked ? "Valid plan, execution locked" : "Sources ready for review"} tone={isLocked ? "warning" : "positive"} /><MetricCard label="Historical review" value={review ? `GW${review.gameweek}` : "—"} detail={review && plan?.gw !== review.gameweek ? "Research is not used as a live action" : "Aligned with decision target"} /></section>
    <div className="content-grid decision-grid">
      <section className="surface"><div className="section-heading"><div><span>WHAT TO DO</span><h2>{action === "LINEUP ONLY" ? "Lineup action" : "Transfer action"}</h2></div><span className="section-chip">GW{plan?.gw ?? "—"}</span></div>{move ? <article className="action-row"><span className="action-state do">MOVE</span><div><strong>{move.out_name} <ArrowRight size={14} /> {move.in_name}</strong><small>{move.hit ? "Includes a points hit" : "Uses a free transfer"}</small><p>{number(move.gain_gw1)} projected next-GW gain · {number(move.gain)} three-GW gain</p></div><b>Review<small>before approval</small></b></article> : <div className="empty-state"><ShieldCheck /><h3>Keep your transfer</h3><p>No move clears the bot’s current threshold. Focus on the XI and captain.</p></div>}</section>
      <section className="surface"><div className="section-heading"><div><span>LINEUP CHECK</span><h2>Captain and formation</h2></div><span className="section-chip">Model recommendation</span></div><div className="captain-list"><article className="captain-row recommended"><span>C</span><div><strong>{captain ?? "Captain pending"}</strong><small>{decision?.formation?.selected ?? "Formation pending"} · GW{plan?.gw ?? "—"}</small></div><b>{number(plan?.captain?.xpts)}<small>xPts</small></b><em>{decision?.approval_scope ?? "Confirm final team news before approval"}</em></article></div></section>
    </div>
    <section className="surface"><div className="section-heading"><div><span>WHY YOU CAN TRUST THIS</span><h2>Decision readiness</h2><p>Each status answers a different question, so “valid” is never confused with “fresh”.</p></div></div><div className="validation-grid"><div className={decision?.source_manifest?.official_fpl?.status === "ready" ? "passed" : "failed"}><ShieldCheck /><span>Integrity: official FPL {decision?.source_manifest?.official_fpl?.status ?? "unknown"}</span></div><div className={deadline && hoursRemaining != null && hoursRemaining > 0 ? "passed" : "failed"}><Clock3 /><span>Deadline: {deadline ? deadline.toLocaleString("en-MY", { dateStyle: "medium", timeStyle: "short" }) : "unknown"}</span></div><div className={isLocked ? "failed" : "passed"}><Bot /><span>Execution: {isLocked ? "locked — review only" : "ready for Telegram review"}</span></div></div></section>
    {review && plan?.gw !== review.gameweek ? <section className="execution-note"><Clock3 /><div><strong>Historical research is deliberately separated</strong><p>Your last captured team and league review is GW{review.gameweek}; the next decision is GW{plan?.gw}. The dashboard will not use that older review to manufacture a current transfer recommendation.</p></div></section> : null}
  </div>;
}
