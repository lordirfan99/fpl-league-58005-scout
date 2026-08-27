import { ArrowRight, Bot, CircleAlert, Clock3, Radio, ShieldCheck } from "lucide-react";
import { MetricCard } from "@/components/metric-card";
import { PageHeader } from "@/components/page-header";
import { getAutopilotData } from "@/lib/autopilot";

const number = (value?: number, digits = 1) => typeof value === "number" ? value.toFixed(digits) : "—";

export default async function AutopilotPage() {
  const data = await getAutopilotData();
  if (!data) return <Disconnected />;
  const { dashboard, plan } = data;
  const decision = plan?.decision_summary;
  const move = plan?.transfers?.[0];
  const action = decision?.recommended_action ?? (move ? "TRANSFER" : "REVIEW");
  const source = decision?.source_manifest;
  const sourceReady = source?.status === "ready";
  const validations = Object.entries(plan?.validation ?? {}).filter(([, value]) => typeof value === "boolean");

  return <div className="page-stack">
    <PageHeader eyebrow="GCP AUTOPILOT" title="V4.1 decision control room" description="The same canonical plan used by Telegram. This website never recomputes or executes a decision." updated={plan?.generated_at ? new Date(plan.generated_at).toLocaleString("en-MY", { dateStyle: "medium", timeStyle: "short" }) : undefined} />
    <section className="decision-hero"><div><span className="hero-kicker">LIVE PLAN · GW{plan?.gw ?? dashboard.gw} · {decision?.team_diff?.approval_action ?? "REVIEW"}</span><h2>{move ? <>{move.out_name} <ArrowRight size={22} /> {move.in_name}</> : action}</h2><p>{decision?.reason ?? "No canonical decision is available."}</p></div><div className="hero-score"><span>XI + captain</span><strong>{number(decision?.uncertainty?.mean_with_captain ?? plan?.target_net_scoring_xpts ?? dashboard.projected_xpts)}</strong></div></section>
    <section className="metric-grid">
      <MetricCard label="Gameweek" value={`GW${plan?.gw ?? dashboard.gw ?? "—"}`} detail={dashboard.deadline?.hours != null ? `${dashboard.deadline.hours}h to deadline` : "Deadline TBC"} />
      <MetricCard label="Three-GW utility" value={number(plan?.horizon_gain)} detail="Risk-adjusted gain" tone="positive" />
      <MetricCard label="Optimizer" value={decision?.optimizer?.version ?? plan?.optimizer_version ?? "—"} detail={`${decision?.optimizer?.name ?? "horizon MILP"} · ${decision?.optimizer?.status ?? "unknown"}`} />
      <MetricCard label="Source contract" value={sourceReady ? "READY" : "SAFE MODE"} detail={`Run ${plan?.run_id?.slice(0, 12) ?? "unknown"}`} tone={sourceReady ? "positive" : "warning"} />
    </section>
    {decision ? <section className="surface">
      <div className="section-heading"><div><span>ONE CANONICAL DECISION</span><h2>{action} · {decision.formation?.selected ?? "—"}</h2><p>{decision.formation?.explanation}</p></div><span className="section-chip">Schema v{decision.schema_version ?? plan?.schema_version ?? "—"}</span></div>
      <div className="validation-grid"><div className="passed"><ShieldCheck /><span>{decision.approval_scope}</span></div><div className={sourceReady ? "passed" : "failed"}><Radio /><span>Official {source?.official_fpl?.status ?? "unknown"} · account {source?.account?.status ?? "unknown"} · league {source?.league?.status ?? "unknown"}</span></div></div>
      <p className="execution-note"><strong>Plan:</strong> {plan?.plan_id?.slice(0, 12) ?? "—"} · <strong>Run:</strong> {plan?.run_id ?? "—"}<br /><strong>Live-team changes:</strong> {decision.team_diff?.started?.length ? `start ${decision.team_diff.started.join(", ")}` : "no XI swap"}{decision.team_diff?.benched?.length ? `; bench ${decision.team_diff.benched.join(", ")}` : ""}{decision.team_diff?.captain_to ? `; captain ${decision.team_diff.captain_from ?? "current"} → ${decision.team_diff.captain_to}` : ""}</p>
      {decision.roadmap?.length ? <div className="data-table-wrap"><table className="data-table"><thead><tr><th>GW</th><th>Action</th><th>Formation</th><th>FT</th><th>Bank</th><th>Mean</th><th>Robust</th></tr></thead><tbody>{decision.roadmap.map((row, index) => <tr key={row.gw ?? index}><td>GW{row.gw}</td><td>{row.action}{row.status === "conditional" ? " (conditional)" : ""}</td><td>{row.formation ?? "—"}</td><td>{row.free_transfers_before ?? "—"} → {row.free_transfers_after ?? "—"}</td><td>£{number(row.bank_after)}m</td><td>{number(row.mean_points_with_captain)}</td><td>{number(row.robust_points_with_captain)}</td></tr>)}</tbody></table></div> : null}
      <p className="execution-note">Approximate 80% range: <strong>{number(decision.uncertainty?.outcome_low)}–{number(decision.uncertainty?.outcome_high)}</strong> · calibrated n={decision.uncertainty?.calibration?.n ?? "—"}. This is uncertainty, not a guarantee.</p>
    </section> : null}
    <div className="content-grid autopilot-grid">
      <section className="surface"><div className="section-heading"><div><span>BOT DECISION</span><h2>{decision?.team_diff?.approval_action ?? "Proposed action"}</h2></div><span className="section-chip">{plan?.status ?? "monitoring"}</span></div>{move ? <article className="bot-transfer"><div><small>SELL</small><strong>{move.out_name}</strong><span>{move.out_pos}</span></div><ArrowRight /><div><small>BUY</small><strong>{move.in_name}</strong><span>+{number(move.gain_gw1)} next GW</span></div></article> : <div className="empty-state"><ShieldCheck /><h3>{action}</h3><p>{decision?.reason ?? "No transfer proposed."}</p></div>}<div className="bot-captains"><div><span>Captain</span><strong>{plan?.captain?.name ?? "—"}</strong><small>{number(plan?.captain?.xpts)} xPts</small></div><div><span>Vice-captain</span><strong>{plan?.vice?.name ?? "—"}</strong><small>{number(plan?.vice?.xpts)} xPts</small></div></div></section>
      <section className="surface"><div className="section-heading"><div><span>CAPTAIN EVIDENCE</span><h2>Minutes-gated ranking</h2></div><span className="section-chip">Top 3</span></div><div className="health-list">{decision?.captain_rankings?.map((captain, index) => <article className={captain.eligible ? "good" : "warning"} key={`${captain.name}-${index}`}><ShieldCheck /><div><strong>{index + 1}. {captain.name} · {number(captain.xpts)} xPts</strong><p>Start {number((captain.p_start ?? 0) * 100, 0)}% · {number(captain.expected_minutes, 0)} min · {captain.reason ?? (captain.eligible ? "eligible" : "rejected")}</p></div></article>) ?? <article><CircleAlert /><div><strong>No captain evidence</strong><p>Regenerate the synchronized plan.</p></div></article>}</div></section>
    </div>
    <section className="surface"><div className="section-heading"><div><span>VALIDATION</span><h2>Safety gates before approval</h2></div><span className="section-chip">{validations.filter(([, value]) => value).length}/{validations.length} passed</span></div><div className="validation-grid">{validations.map(([key, value]) => <div key={key} className={value ? "passed" : "failed"}>{value ? <ShieldCheck /> : <CircleAlert />}<span>{key.replaceAll("_", " ")}</span></div>)}</div><p className="execution-note">{plan?.data_note ?? dashboard.engine_note ?? "Official FPL and calibrated statistical V4."}</p></section>
    <section className="surface table-surface"><div className="section-heading"><div><span>MODEL RANKING</span><h2>Top projected players</h2></div><span className="section-chip">Top 20 of {data.predictions?.length ?? 0}</span></div><div className="data-table-wrap"><table className="data-table"><thead><tr><th>#</th><th>Player</th><th>Position</th><th>xPts</th><th>Status</th><th>News</th></tr></thead><tbody>{data.predictions?.slice(0, 20).map((player, index) => <tr key={player.id ?? `${player.name}-${index}`}><td>{index + 1}</td><td><strong>{player.name}</strong></td><td>{player.pos ?? player.position}</td><td>{number(player.xpts)}</td><td><span className={player.status === "a" ? "availability ready" : "availability risk"}>{player.status === "a" ? "Available" : player.status}</span></td><td>{player.news || "—"}</td></tr>)}</tbody></table></div></section>
    <div className="execution-note"><Clock3 /><div><strong>Telegram remains the execution authority</strong><p>The dashboard and Telegram display the same persisted plan ID. Approval still rechecks deadline, account state, prices, injuries and the final saved lineup.</p></div></div>
  </div>;
}

function Disconnected() { return <div className="page-stack"><PageHeader eyebrow="GCP AUTOPILOT" title="V4.1 decision control room" description="The shared Telegram and dashboard plan." /><section className="surface bot-disconnected"><Bot /><h2>Secure bridge not connected</h2><p>The read-only bot plan is temporarily unavailable. Telegram execution remains disabled until a fresh plan is generated.</p></section></div>; }
