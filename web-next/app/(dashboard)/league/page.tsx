import { LeagueTable } from "@/components/league-table";
import { LeagueSwitcher, resolveLeague } from "@/components/league-switcher";
import { MetricCard } from "@/components/metric-card";
import { PageHeader } from "@/components/page-header";
import { getLeagueData, MY_TEAM_ID } from "@/lib/data";

export default async function LeaguePage({ searchParams }: { searchParams: Promise<{ league?: string }> }) {
  const selected = resolveLeague((await searchParams).league), data = await getLeagueData(selected.id), rows = [...data.managers].sort((a, b) => a.league_rank - b.league_rank);
  const average = rows.reduce((sum, entry) => sum + entry.gw_points, 0) / rows.length, myTeam = data.manager;
  return <div className="page-stack"><PageHeader eyebrow="LEAGUE INTELLIGENCE" title={selected.name} description={`${rows.length.toLocaleString()} managers · complete searchable standings`} updated={data.fetchedAt ? new Date(data.fetchedAt).toLocaleString("en-MY", { dateStyle: "medium", timeStyle: "short" }) : undefined} /><LeagueSwitcher selected={selected.id} pathname="/league" /><section className="metric-grid"><MetricCard label="Managers" value={rows.length.toLocaleString()} detail={`League ${selected.id}`} /><MetricCard label="Average GW" value={average.toFixed(1)} /><MetricCard label="Your rank" value={myTeam ? `#${myTeam.league_rank}` : "—"} detail={myTeam ? `${myTeam.gw_points} points` : "Your team is not in this league"} tone={myTeam ? (myTeam.gw_points >= average ? "positive" : "warning") : undefined} /><MetricCard label="Leader" value={`${rows[0]?.gw_points ?? 0} pts`} detail={rows[0]?.entry_name} /></section><section className="surface table-surface"><div className="section-heading"><div><span>STANDINGS</span><h2>League table</h2></div><span className="section-chip">GW{data.gameweek}</span></div><LeagueTable managers={rows} myTeamId={MY_TEAM_ID} bootstrap={data.bootstrap} gameweek={data.gameweek} /></section></div>;
}
