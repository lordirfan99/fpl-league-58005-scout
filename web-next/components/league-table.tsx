"use client";

import { Search, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Pitch } from "@/components/pitch";
import type { Bootstrap, Manager } from "@/lib/types";

const PAGE_SIZE = 50;

export function LeagueTable({ managers, myTeamId, bootstrap, gameweek }: { managers: Manager[]; myTeamId: number; bootstrap: Bootstrap; gameweek: number }) {
  const [query, setQuery] = useState(""), [page, setPage] = useState(1), [selected, setSelected] = useState<Manager | null>(null);
  useEffect(() => {
    if (!selected) return;
    const close = (event: KeyboardEvent) => { if (event.key === "Escape") setSelected(null); };
    document.addEventListener("keydown", close);
    document.body.classList.add("modal-open");
    return () => { document.removeEventListener("keydown", close); document.body.classList.remove("modal-open"); };
  }, [selected]);
  const filtered = useMemo(() => {
    const term = query.trim().toLocaleLowerCase();
    return term ? managers.filter((manager) => `${manager.entry_name} ${manager.player_name} ${manager.entry_id}`.toLocaleLowerCase().includes(term)) : managers;
  }, [managers, query]);
  const pages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE)), safePage = Math.min(page, pages), visible = filtered.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);
  return <><div className="table-toolbar"><label><Search size={15} /><input value={query} onChange={(event) => { setQuery(event.target.value); setPage(1); }} placeholder="Search manager, team or FPL ID" /></label><span>{filtered.length.toLocaleString()} managers · select a row to inspect lineup</span></div><div className="data-table-wrap"><table className="data-table"><thead><tr><th>Rank</th><th>Team</th><th>Manager</th><th>GW</th><th>Total</th><th>Overall</th><th>Captain</th><th>Value</th></tr></thead><tbody>{visible.map((entry) => <tr key={entry.entry_id} className={`manager-row ${entry.entry_id === myTeamId ? "my-row" : ""}`} tabIndex={0} aria-label={`Open ${entry.entry_name} lineup`} onClick={() => setSelected(entry)} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); setSelected(entry); } }}><td>#{entry.league_rank}</td><td><strong>{entry.entry_name}</strong><small>View lineup</small></td><td>{entry.player_name}</td><td>{entry.gw_points}</td><td>{entry.total_points}</td><td>{entry.overall_rank.toLocaleString()}</td><td>{entry.captain}</td><td>£{entry.squad_cost.toFixed(1)}m</td></tr>)}</tbody></table></div><div className="table-pagination"><button disabled={safePage === 1} onClick={() => setPage((value) => Math.max(1, value - 1))}>Previous</button><span>Page {safePage} of {pages}</span><button disabled={safePage === pages} onClick={() => setPage((value) => Math.min(pages, value + 1))}>Next</button></div>{selected && <ManagerLineup manager={selected} bootstrap={bootstrap} gameweek={gameweek} onClose={() => setSelected(null)} />}</>;
}

function ManagerLineup({ manager, bootstrap, gameweek, onClose }: { manager: Manager; bootstrap: Bootstrap; gameweek: number; onClose: () => void }) {
  const starters = manager.squad.slice(0, 11);
  const formation = ["DEF", "MID", "FWD"].map((position) => starters.filter((pick) => pick.position === position).length).join("-");
  return <div className="manager-dialog-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}><section className="manager-dialog" role="dialog" aria-modal="true" aria-labelledby="manager-dialog-title"><header><div><span>MANAGER DETAIL · GW{gameweek}</span><h2 id="manager-dialog-title">{manager.entry_name}</h2><p>{manager.player_name} · League rank #{manager.league_rank.toLocaleString()} · FPL ID {manager.entry_id}</p></div><button type="button" onClick={onClose} aria-label="Close lineup"><X size={18} /></button></header><div className="manager-dialog-metrics"><article><span>GW points</span><strong>{manager.gw_points}</strong></article><article><span>Total</span><strong>{manager.total_points}</strong></article><article><span>Overall rank</span><strong>{manager.overall_rank.toLocaleString()}</strong></article><article><span>Squad value</span><strong>£{manager.squad_cost.toFixed(1)}m</strong></article></div><div className="manager-lineup-heading"><div><span>STARTING XI</span><strong>{formation}</strong></div><small>11 on field · 4 substitutes · Captain: {manager.captain}</small></div><Pitch squad={manager.squad} bootstrap={bootstrap} /></section></div>;
}
