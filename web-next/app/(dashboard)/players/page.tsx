import { PlayerExplorer } from "@/components/player-explorer";
import { PageHeader } from "@/components/page-header";
import { getDashboardData } from "@/lib/data";

export default async function PlayersPage() {
  const data = await getDashboardData();
  const upcoming = data.bootstrap.events.find((event) => !event.finished);
  const targetGameweek = upcoming?.id ?? data.gameweek + 1;
  const players = data.bootstrap.elements.map(({ id, web_name, team, element_type, now_cost, ep_next, form, selected_by_percent, status, news }) => ({ id, web_name, team, element_type, now_cost, ep_next, form, selected_by_percent, status, news }));
  const teams = data.bootstrap.teams.map(({ id, short_name }) => ({ id, short_name }));
  return <div className="page-stack"><PageHeader eyebrow={`PLAYER INTELLIGENCE · TARGET GW${targetGameweek}`} title="Player market" description="Search and filter the current FPL player pool before building a transfer scenario." /><PlayerExplorer players={players} teams={teams} targetGameweek={targetGameweek} /></div>;
}
