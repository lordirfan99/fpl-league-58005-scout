import { PageHeader } from "@/components/page-header";
import { getPlannerData } from "@/lib/data";
import { buildRecommendations } from "@/lib/model";
import type { Fixture, Pick } from "@/lib/types";

export default async function PlannerPage() {
  const data = await getPlannerData(), plan = buildRecommendations(data.manager, data.managers, data.bootstrap, data.fixture);
  const gameweeks = Array.from({ length: data.toGameweek - data.fromGameweek + 1 }, (_, index) => data.fromGameweek + index);
  const playerIndex = new Map(data.bootstrap.elements.map((player) => [player.id, player]));
  const starters = data.manager.squad.slice(0, 11);
  const weekly = gameweeks.map((gameweek) => summarizeWeek(gameweek, starters, data.fixtureHorizon[String(gameweek)] ?? [], playerIndex));
  return <div className="page-stack"><PageHeader eyebrow="TRANSFER PLANNER" title="Plan the next five gameweeks" description={`Official FPL fixtures and difficulty for GW${data.fromGameweek}–GW${data.toGameweek}, layered over your current squad and elite transfer signals.`} />
    <section className="surface"><div className="section-heading"><div><span>FIXTURE HORIZON</span><h2>Five-week squad outlook</h2></div><span className="section-chip">Official FPL FDR</span></div><div className="horizon-cards">{weekly.map((week, index) => <article className={index === 0 ? "active" : ""} key={week.gameweek}><div><span>GW{week.gameweek}</span><b className={`fdr-${Math.round(week.averageFdr)}`}>{week.averageFdr.toFixed(1)} avg FDR</b></div><strong>{week.easy} favourable · {week.hard} difficult</strong><small>Captain fixture: {week.captain}</small></article>)}</div></section>
    <section className="surface fixture-matrix-surface"><div className="section-heading"><div><span>YOUR SQUAD</span><h2>Player-by-player fixture run</h2></div><span className="section-chip">11 starters + 4 bench</span></div><div className="fixture-matrix-wrap"><table className="fixture-matrix"><thead><tr><th>Player</th>{gameweeks.map((gameweek) => <th key={gameweek}>GW{gameweek}</th>)}</tr></thead><tbody>{data.manager.squad.map((pick, index) => <tr className={index === 11 ? "bench-start" : ""} key={pick.element}><td><strong>{pick.name}</strong><small>{index < 11 ? "XI" : "Bench"} · {pick.position}</small></td>{gameweeks.map((gameweek) => <td key={gameweek}><FixtureCell pick={pick} fixtures={data.fixtureHorizon[String(gameweek)] ?? []} /></td>)}</tr>)}</tbody></table></div></section>
    <section className="surface"><div className="section-heading"><div><span>GW{data.fromGameweek} SHORTLIST</span><h2>Current transfer candidates</h2></div><span className="section-chip">Elite + model</span></div>{plan.transfers.length ? <div className="planner-grid">{plan.transfers.map((move) => <article key={`${move.outgoing.element}-${move.incoming.element}`}><span>{move.outgoing.name}</span><strong>→ {move.incoming.name}</strong><small>{move.incoming.position} · {move.incoming.team} · {move.incoming.fixture}</small><div><b>{move.xptsGain >= 0 ? "+" : ""}{move.xptsGain.toFixed(1)} xPts</b><em>{move.incoming.eliteOwnership.toFixed(1)}% elite</em></div></article>)}</div> : <div className="empty-state"><h3>No forced transfer</h3><p>The current model does not see a sufficiently strong same-position upgrade for GW{data.fromGameweek}.</p></div>}</section>
    <section className="surface planner-note"><span>HOW TO USE THIS</span><h2>Look beyond one gameweek</h2><p>Prioritise players with several green fixtures, not a single easy match. FDR is schedule context—not a points guarantee—so confirm injuries, minutes and late team news before approving a move through Telegram.</p></section>
  </div>;
}

function fixturesFor(team: string, fixtures: Fixture[]) {
  return fixtures.filter((fixture) => fixture.team_h === team || fixture.team_a === team).map((fixture) => fixture.team_h === team
    ? { label: `${shortTeam(fixture.team_a)} (H)`, fdr: fixture.team_h_difficulty }
    : { label: `${shortTeam(fixture.team_h)} (A)`, fdr: fixture.team_a_difficulty });
}

function FixtureCell({ pick, fixtures }: { pick: Pick; fixtures: Fixture[] }) {
  const matches = fixturesFor(pick.team, fixtures);
  if (!matches.length) return <span className="fixture-chip blank">TBC</span>;
  return <div className="fixture-cell">{matches.map((match, index) => <span className={`fixture-chip fdr-${match.fdr}`} key={`${match.label}-${index}`}>{match.label}<b>{match.fdr}</b></span>)}</div>;
}

function summarizeWeek(gameweek: number, starters: Pick[], fixtures: Fixture[], playerIndex: Map<number, { form: string }>) {
  const schedule = starters.flatMap((pick) => fixturesFor(pick.team, fixtures).map((match) => ({ ...match, pick })));
  const averageFdr = schedule.reduce((sum, item) => sum + item.fdr, 0) / Math.max(1, schedule.length);
  const captain = [...schedule].sort((a, b) => (a.fdr - b.fdr) || (Number(playerIndex.get(b.pick.element)?.form ?? 0) - Number(playerIndex.get(a.pick.element)?.form ?? 0)))[0];
  return { gameweek, averageFdr, easy: schedule.filter((item) => item.fdr <= 2).length, hard: schedule.filter((item) => item.fdr >= 4).length, captain: captain ? `${captain.pick.name} · ${captain.label}` : "TBC" };
}

function shortTeam(team: string) {
  const aliases: Record<string, string> = { "Manchester City": "MCI", "Manchester United": "MUN", "Nott'm Forest": "NFO", "Crystal Palace": "CRY", "Newcastle United": "NEW", "Ipswich Town": "IPS", "Coventry City": "COV", "Hull City": "HUL", "Aston Villa": "AVL", "Wolverhampton Wanderers": "WOL" };
  return aliases[team] ?? team.slice(0, 3).toUpperCase();
}
