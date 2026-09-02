import { PageHeader } from "@/components/page-header";
import { TransferDraft } from "@/components/transfer-draft";
import { getPlannerData } from "@/lib/data";

export default async function BuilderPage() {
  const data = await getPlannerData();
  const players = data.bootstrap.elements.map(({ id, web_name, element_type, now_cost, ep_next, team, status }) => ({ id, web_name, element_type, now_cost, ep_next, team, status }));
  const teams = data.bootstrap.teams.map(({ id, short_name }) => ({ id, short_name }));
  return <div className="page-stack"><PageHeader eyebrow={`SQUAD BUILDER · GW${data.fromGameweek}`} title="Build a legal manual draft" description="Test normal transfers now. Wildcard and Free Hit full-squad recommendations are read-only and never sent to FPL." /><section className="execution-note"><span className="status-dot" /><div><strong>FPL execution is manual</strong><p>This workspace saves only your advisory draft. You remain in control of every official FPL change.</p></div></section><TransferDraft squad={data.manager.squad} players={players} teams={teams} gameweek={data.fromGameweek} /><section className="surface"><div className="section-heading"><div><span>CHIP MODE</span><h2>Wildcard-safe optimiser</h2><p>The API now excludes unavailable players by default and validates a complete legal 15-player squad before presenting a chip plan.</p></div></div><a className="workspace-cta" href={`/transfers?league=${data.leagueId}`}>Review chip research</a></section></div>;
}
