import { AlertTriangle, ArrowRight, BrainCircuit, Check, FlaskConical, LockKeyhole, ShieldCheck, TimerReset } from "lucide-react";
import { MetricCard } from "@/components/metric-card";
import { PageHeader } from "@/components/page-header";
import { getAutopilotData, type ShadowPlan, type ShadowPlayer } from "@/lib/autopilot";

const n = (value?: number | null, digits = 1) => typeof value === "number" ? value.toFixed(digits) : "—";
const pct = (value?: number | null) => typeof value === "number" ? `${Math.round(value * 100)}%` : "—";
const label = (value: string) => value.replaceAll("_", " ").replace(/\b\w/g, letter => letter.toUpperCase());

export default async function ShadowV3Page() {
  const data = await getAutopilotData();
  const shadow = data?.shadow_v3;
  if (!data || !shadow) return <Unavailable />;

  const engine = data.engine;
  const evaluated = engine?.shadow_evaluated_gws ?? engine?.report?.evaluated_gws?.length ?? 0;
  const required = engine?.report?.min_gws_required ?? 3;
  const progress = Math.min(100, Math.round((evaluated / required) * 100));
  const plan = shadow.multigw_plan;
  const calibration = shadow.calibration;
  const scenarioRows = Object.entries(shadow.scenarios ?? {});
  const candidates = shadow.top_candidates ?? [];
  const squad = shadow.squad ?? [];

  return <div className="page-stack shadow-page">
    <PageHeader eyebrow="GCP MODEL LAB" title="Shadow V3 intelligence" description="A detailed, read-only view of the next projection and multi-gameweek planning engine." updated={shadow.generated_at ? new Date(shadow.generated_at).toLocaleString("en-MY", { dateStyle: "medium", timeStyle: "short" }) : undefined} />

    <section className="shadow-hero">
      <div>
        <span className="hero-kicker"><FlaskConical size={14} /> SHADOW ONLY · GW{shadow.gw}</span>
        <h2>Testing the next engine without risking your team</h2>
        <p>V3 observes the same decision cycle as the live bot, but it cannot create approvals, send Telegram actions, or write to FPL. Promotion remains manual.</p>
      </div>
      <div className="shadow-progress" aria-label={`${evaluated} of ${required} shadow gameweeks evaluated`}>
        <div style={{ "--progress": `${progress * 3.6}deg` } as React.CSSProperties}><strong>{evaluated}/{required}</strong><span>GWs</span></div>
        <small>{engine?.promotion_status?.replaceAll("_", " ") ?? "collecting data"}</small>
      </div>
    </section>

    <section className="metric-grid">
      <MetricCard label="Projection engine" value={shadow.projection_version ?? shadow.model ?? "V3"} detail="Component-level expected points" />
      <MetricCard label="Planner" value={shadow.planner_version ?? plan?.planner_version ?? "—"} detail={`${plan?.horizon ?? 0}-GW robust horizon`} />
      <MetricCard label="Objective score" value={n(plan?.objective, 2)} detail={`${plan?.candidate_pool_size ?? 0} candidates assessed`} tone="positive" />
      <MetricCard label="Calibration sample" value={`${calibration?.n ?? 0} players`} detail={calibration?.mae == null ? "Awaiting completed-GW outcomes" : `${n(calibration.mae)} MAE`} tone={calibration?.n ? undefined : "warning"} />
    </section>

    <div className="content-grid shadow-overview-grid">
      <section className="surface">
        <div className="section-heading"><div><span>CAPTAIN FORECAST</span><h2>{shadow.captain?.name ?? "No captain projection"}</h2></div><span className="section-chip">V3 distribution</span></div>
        <div className="captain-range">
          <RangeStat label="Floor" value={shadow.captain?.xpts_floor} tone="floor" />
          <RangeStat label="Expected" value={shadow.captain?.xpts} tone="mean" />
          <RangeStat label="Upside" value={shadow.captain?.xpts_upside} tone="upside" />
        </div>
        <div className="captain-meta"><span><strong>{pct(shadow.captain?.p_start)}</strong> start probability</span><span><strong>{n(shadow.captain?.expected_minutes, 0)}</strong> expected minutes</span><span><strong>{n(shadow.captain?.xpts_variance, 2)}</strong> variance</span></div>
        <ComponentBars player={shadow.captain} />
      </section>

      <section className="surface">
        <div className="section-heading"><div><span>PROMOTION CONTROL</span><h2>Evidence gates</h2></div><span className="section-chip">Manual policy</span></div>
        <div className="gate-list">
          <Gate done={evaluated >= required} title={`${required} completed shadow GWs`} detail={`${evaluated} evaluated so far`} />
          <Gate done={calibration?.mae != null} title="Accuracy not materially worse" detail={calibration?.mae == null ? "MAE, rank correlation and bias pending" : `MAE ${n(calibration.mae)} · RMSE ${n(calibration.rmse)}`} />
          <Gate done={Boolean(engine?.report?.gate_met)} title="Decision metric improves" detail="Captain score or top-15 squad score must improve" />
          <Gate done={Boolean(engine?.promoted)} title="Owner approves promotion" detail="Never promoted automatically" />
        </div>
        <p className="gate-reason"><LockKeyhole size={14} /> {engine?.report?.reason ?? "Promotion evidence has not been evaluated yet."}</p>
      </section>
    </div>

    <section className="surface">
      <div className="section-heading"><div><span>ROBUST MULTI-GW PLAN</span><h2>What V3 would do next</h2><p>Forward plan for observation only. It does not replace the approved live plan.</p></div><span className="section-chip">{plan?.status ?? "unknown"}</span></div>
      <div className="shadow-timeline">
        {(plan?.weeks ?? []).map((week, index) => <article key={`${week.gw_offset}-${index}`}>
          <header><span>GW{(shadow.gw ?? 0) + (week.gw_offset ?? index)}</span><b>{week.formation ?? "—"}</b></header>
          <strong>{n(week.mean_points_with_captain)} <small>projected pts</small></strong>
          <div className="timeline-actions">{week.transfers?.length ? week.transfers.map((move, moveIndex) => <div key={`${move.out_name}-${move.in_name}-${moveIndex}`}><span>{move.out_name}</span><ArrowRight size={12} /><b>{move.in_name}</b></div>) : <div><ShieldCheck size={13} /><b>Roll transfer</b></div>}</div>
          <footer><span>FT {week.free_transfers_before ?? "—"}</span><span>Hit {week.hits ?? 0}</span><span>Bank £{n(week.bank_after)}m</span></footer>
          <small>C {week.captain ?? "—"} · VC {week.vice ?? "—"}</small>
        </article>)}
      </div>
      <div className="model-settings"><span>Risk penalty <b>{n(plan?.risk_penalty, 2)}</b></span><span>Bench weight <b>{n(plan?.bench_weight, 2)}</b></span><span>Flexibility <b>{n(plan?.flexibility_weight, 2)}</b></span><span>GW weights <b>{plan?.weights?.join(" · ") ?? "—"}</b></span></div>
    </section>

    <section className="surface table-surface">
      <div className="section-heading"><div><span>SCENARIO LAB</span><h2>Strategy comparison</h2><p>See how constraints alter the transfer path, not only the final score.</p></div><span className="section-chip">{scenarioRows.length} scenarios</span></div>
      <div className="data-table-wrap"><table className="data-table"><thead><tr><th>Scenario</th><th>Status</th><th>Objective</th><th>Horizon</th><th>First move out</th><th>First move in</th></tr></thead><tbody>{scenarioRows.map(([name, scenario]) => <tr key={name}><td><strong>{label(name)}</strong></td><td>{scenario.status ?? "—"}</td><td>{n(scenario.objective, 2)}</td><td>{scenario.horizon ?? "—"} GWs</td><td>{scenario.first_action?.out_name ?? "Hold"}</td><td>{scenario.first_action?.in_name ?? "—"}</td></tr>)}</tbody></table></div>
    </section>

    <PlayerProjectionTable title="V3 candidate ranking" eyebrow="PLAYER LAB" players={candidates.slice(0, 20)} note={`Top 20 of ${candidates.length}`} />
    <PlayerProjectionTable title="Your squad under V3" eyebrow="SQUAD DIAGNOSTIC" players={squad} note={`${squad.length} players`} />

    <section className="surface shadow-safety">
      <div><BrainCircuit /><span><strong>How V3 reasons</strong><small>Fixtures → minutes model → component xPts → uncertainty → robust multi-GW planner → chip strategy.</small></span></div>
      <div><LockKeyhole /><span><strong>What V3 cannot do</strong><small>No pending-plan writes, Telegram approvals, transfers, captain changes or chip execution.</small></span></div>
      <div><TimerReset /><span><strong>How it becomes trusted</strong><small>Completed-GW calibration, V2/V3 comparison, safety tests, then your explicit manual promotion.</small></span></div>
    </section>
  </div>;
}

function RangeStat({ label: text, value, tone }: { label: string; value?: number; tone: string }) { return <div className={`range-stat ${tone}`}><span>{text}</span><strong>{n(value)}</strong><small>xPts</small></div>; }

function Gate({ done, title, detail }: { done: boolean; title: string; detail: string }) { return <article className={done ? "done" : "pending"}><span>{done ? <Check size={14} /> : <TimerReset size={14} />}</span><div><strong>{title}</strong><small>{detail}</small></div><b>{done ? "Passed" : "Pending"}</b></article>; }

function ComponentBars({ player }: { player?: ShadowPlayer }) {
  const rows = Object.entries(player?.components ?? {}).filter(([, value]) => typeof value === "number" && value > 0).sort((a, b) => b[1] - a[1]).slice(0, 6);
  const max = Math.max(...rows.map(([, value]) => value), 1);
  return <div className="component-bars">{rows.map(([name, value]) => <div key={name}><span>{label(name)}</span><i><b style={{ width: `${Math.max(4, (value / max) * 100)}%` }} /></i><strong>{n(value, 2)}</strong></div>)}</div>;
}

function PlayerProjectionTable({ title, eyebrow, players, note }: { title: string; eyebrow: string; players: ShadowPlayer[]; note: string }) {
  return <section className="surface table-surface"><div className="section-heading"><div><span>{eyebrow}</span><h2>{title}</h2></div><span className="section-chip">{note}</span></div><div className="data-table-wrap"><table className="data-table shadow-player-table"><thead><tr><th>#</th><th>Player</th><th>Pos</th><th>Expected</th><th>Floor</th><th>Upside</th><th>Horizon</th><th>P(start)</th><th>Minutes</th></tr></thead><tbody>{players.map((player, index) => <tr key={player.id ?? `${player.name}-${index}`}><td>{index + 1}</td><td><strong>{player.name ?? "—"}</strong><small>{String(player.club ?? "")}</small></td><td>{player.position ?? player.pos ?? "—"}</td><td><b>{n(player.xpts)}</b></td><td>{n(player.xpts_floor)}</td><td className="positive-text">{n(player.xpts_upside)}</td><td>{n(player.xpts_horizon)}</td><td>{pct(player.p_start)}</td><td>{n(player.expected_minutes, 0)}</td></tr>)}</tbody></table></div></section>;
}

function Unavailable() { return <div className="page-stack"><PageHeader eyebrow="GCP MODEL LAB" title="Shadow V3 intelligence" description="Detailed read-only observability for the next model engine." /><section className="surface bot-disconnected"><AlertTriangle /><h2>Shadow artifact not available</h2><p>The dashboard bridge is connected, but no sanitized V3 shadow artifact was returned. The live bot remains unaffected.</p></section></div>; }
