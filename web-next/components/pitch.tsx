import type { Bootstrap, Pick, Position } from "@/lib/types";
import { PlayerCard } from "./player-card";

const order: Position[] = ["GKP", "DEF", "MID", "FWD"];

export function Pitch({ squad, bootstrap, showEventPoints = false }: { squad: Pick[]; bootstrap: Bootstrap; showEventPoints?: boolean }) {
  const starters = squad.slice(0, 11), bench = squad.slice(11, 15);
  const meta = (pick: Pick) => { const player = bootstrap.elements.find((item) => item.id === pick.element); return showEventPoints ? `${player?.event_points ?? 0} pts` : "Snapshot squad"; };
  return <div className="squad-view"><section className="pitch" aria-label="Starting eleven football pitch">{order.map((position) => <div className={`pitch-row ${position.toLowerCase()}`} key={position}>{starters.filter((player) => player.position === position).map((player) => <PlayerCard key={player.element} pick={player} bootstrap={bootstrap} meta={meta(player)} />)}</div>)}</section><div className="bench"><div className="bench-heading"><span>Bench</span><small>{bench.length} substitutes</small></div><div className="bench-grid">{bench.map((player) => <PlayerCard key={player.element} pick={player} bootstrap={bootstrap} meta={meta(player)} />)}</div></div></div>;
}
