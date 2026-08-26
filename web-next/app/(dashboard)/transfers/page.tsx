import { LeagueSwitcher, resolveLeague } from "@/components/league-switcher";
import { MetricCard } from "@/components/metric-card";
import { PageHeader } from "@/components/page-header";
import { getLeagueData } from "@/lib/data";
import { analyzeElite } from "@/lib/elite";

type Count = { name: string; count: number; percentage: number };

function countRows(values: string[], denominator: number): Count[] {
  const counts = new Map<string, number>();
  values.forEach((value) => counts.set(value, (counts.get(value) ?? 0) + 1));
  return [...counts].map(([name, count]) => ({ name, count, percentage: count / Math.max(1, denominator) * 100 })).sort((a, b) => b.count - a.count);
}

function ActivityList({ rows, empty }: { rows: Count[]; empty: string }) {
  return rows.length ? <div className="ranked-list">{rows.slice(0, 15).map((row, index) => <article key={row.name}><span>{index + 1}</span><strong>{row.name}</strong><b>{row.count}<small>{row.percentage.toFixed(1)}%</small></b></article>)}</div> : <div className="empty-state"><h3>No activity recorded</h3><p>{empty}</p></div>;
}

export default async function TransfersPage({ searchParams }: { searchParams: Promise<{ league?: string }> }) {
  const selected = resolveLeague((await searchParams).league), data = await getLeagueData(selected.id), elite = analyzeElite(data.managers);
  const moves = countRows(data.managers.flatMap((manager) => manager.transfer_details?.map((move) => `${move.out} → ${move.in}`) ?? []), data.managers.length);
  const chips = countRows(data.managers.flatMap((manager) => manager.chips_used?.map((chip) => chip.name ?? chip.chip_name ?? "Unknown") ?? []), data.managers.length);
  const activeManagers = data.managers.filter((manager) => manager.transfers_made > 0).length;
  const eliteActive = elite.elite.filter((manager) => manager.transfers_made > 0).length;
  return <div className="page-stack"><PageHeader eyebrow="MARKET INTELLIGENCE" title="Transfers & chips" description="Track what the complete league and its top-5% cohort actually did in the selected gameweek." updated={data.fetchedAt ? new Date(data.fetchedAt).toLocaleString("en-MY", { dateStyle: "medium", timeStyle: "short" }) : undefined} /><LeagueSwitcher selected={selected.id} pathname="/transfers" />
    <section className="metric-grid"><MetricCard label="League transfers" value={activeManagers.toLocaleString()} detail={`${(activeManagers / data.managers.length * 100).toFixed(1)}% active managers`} /><MetricCard label="Elite transfers" value={eliteActive.toLocaleString()} detail={`${(eliteActive / elite.elite.length * 100).toFixed(1)}% of top 5%`} /><MetricCard label="Top elite move" value={elite.transfers[0]?.name ?? "Hold"} detail={elite.transfers[0] ? `${elite.transfers[0].count} managers` : "No move recorded"} /><MetricCard label="Most-used chip" value={chips[0]?.name ?? "None"} detail={chips[0] ? `${chips[0].count} managers` : "No chip activity"} /></section>
    <div className="content-grid elite-edge-grid"><section className="surface"><div className="section-heading"><div><span>ELITE CONSENSUS</span><h2>Top-5% transfer combinations</h2><p>Moves made by the strongest overall-ranked managers in this league.</p></div><span className="section-chip">{elite.elite.length} managers</span></div><ActivityList rows={elite.transfers} empty="The elite cohort recorded no transfer pairs for this snapshot." /></section><section className="surface"><div className="section-heading"><div><span>WHOLE LEAGUE</span><h2>Popular transfer combinations</h2><p>Use this as herd context, not an automatic recommendation.</p></div><span className="section-chip">{data.managers.length} managers</span></div><ActivityList rows={moves} empty="No league transfer pairs were recorded for this gameweek." /></section></div>
    <div className="content-grid elite-edge-grid"><section className="surface"><div className="section-heading"><div><span>CHIP TRACKER</span><h2>League chip usage</h2></div></div><ActivityList rows={chips} empty="No chips were recorded in this snapshot." /></section><section className="surface"><div className="section-heading"><div><span>ELITE CHIP TIMING</span><h2>Top-5% chip usage</h2></div></div><ActivityList rows={elite.chips} empty="No elite chip usage was recorded." /></section></div>
  </div>;
}
