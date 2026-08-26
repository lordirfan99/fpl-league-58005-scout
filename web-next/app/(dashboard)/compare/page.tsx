import { LeagueSwitcher, resolveLeague } from "@/components/league-switcher";
import { ManagerCompare } from "@/components/manager-compare";
import { PageHeader } from "@/components/page-header";
import { getLeagueData, MY_TEAM_ID } from "@/lib/data";

export default async function ComparePage({ searchParams }: { searchParams: Promise<{ league?: string }> }) {
  const selected = resolveLeague((await searchParams).league), data = await getLeagueData(selected.id);
  return <div className="page-stack"><PageHeader eyebrow="HEAD TO HEAD" title="Compare managers" description="Inspect squad overlap, unique picks, captaincy, rank gap and each manager’s complete lineup." updated={data.fetchedAt ? new Date(data.fetchedAt).toLocaleString("en-MY", { dateStyle: "medium", timeStyle: "short" }) : undefined} /><LeagueSwitcher selected={selected.id} pathname="/compare" /><section className="surface"><ManagerCompare managers={data.managers} bootstrap={data.bootstrap} gameweek={data.gameweek} myTeamId={MY_TEAM_ID} /></section></div>;
}
