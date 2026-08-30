"use client";

import { ArrowRight, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { ManagerLineup } from "@/components/manager-lineup";
import type { Bootstrap, Manager, Pick } from "@/lib/types";

export function ManagerCompare({ managers, bootstrap, gameweek, myTeamId }: { managers: Manager[]; bootstrap: Bootstrap; gameweek: number; myTeamId: number }) {
  const sorted = useMemo(() => [...managers].sort((a, b) => a.league_rank - b.league_rank), [managers]);
  const defaultA = sorted.find((manager) => manager.entry_id === myTeamId)?.entry_id ?? sorted[0]?.entry_id;
  const [leftId, setLeftId] = useState(defaultA), [rightId, setRightId] = useState(sorted.find((manager) => manager.entry_id !== defaultA)?.entry_id ?? defaultA), [open, setOpen] = useState<Manager | null>(null);
  useEffect(() => { if (!open) return; const close = (event: KeyboardEvent) => { if (event.key === "Escape") setOpen(null); }; document.addEventListener("keydown", close); document.body.classList.add("modal-open"); return () => { document.removeEventListener("keydown", close); document.body.classList.remove("modal-open"); }; }, [open]);
  const left = sorted.find((manager) => manager.entry_id === leftId) ?? sorted[0], right = sorted.find((manager) => manager.entry_id === rightId) ?? sorted[1] ?? sorted[0];
  const leftMap = new Map(left.squad.map((pick) => [pick.element, pick])), rightMap = new Map(right.squad.map((pick) => [pick.element, pick]));
  const shared = left.squad.filter((pick) => rightMap.has(pick.element)), leftOnly = left.squad.filter((pick) => !rightMap.has(pick.element)), rightOnly = right.squad.filter((pick) => !leftMap.has(pick.element));
  return <><div className="compare-selectors"><ManagerPicker label="Manager A" managers={sorted} selectedId={leftId} onSelect={setLeftId} /><span className="compare-vs">VS</span><ManagerPicker label="Manager B" managers={sorted} selectedId={rightId} onSelect={setRightId} /></div>
    <div className="compare-kpis"><article><span>Squad overlap</span><strong>{shared.length}/15</strong></article><article><span>GW gap</span><strong>{Math.abs(left.gw_points - right.gw_points)}</strong></article><article><span>Rank gap</span><strong>{Math.abs(left.overall_rank - right.overall_rank).toLocaleString()}</strong></article><article><span>Value gap</span><strong>£{Math.abs(left.squad_cost - right.squad_cost).toFixed(1)}m</strong></article></div>
    <div className="compare-squads"><SquadColumn manager={left} picks={leftOnly} onOpen={() => setOpen(left)} /><SquadColumn manager={right} picks={rightOnly} onOpen={() => setOpen(right)} /><section className="compare-shared"><span>SHARED CORE</span><h3>{shared.length} players</h3><div>{shared.map((pick) => <PlayerChip key={pick.element} pick={pick} />)}</div></section></div>
    {open ? <ManagerLineup manager={open} bootstrap={bootstrap} gameweek={gameweek} onClose={() => setOpen(null)} /> : null}
  </>;
}

function ManagerPicker({ label, managers, selectedId, onSelect }: { label: string; managers: Manager[]; selectedId: number; onSelect: (id: number) => void }) {
  const selected = managers.find((manager) => manager.entry_id === selectedId) ?? managers[0];
  const [query, setQuery] = useState("");
  const matches = useMemo(() => { const term = query.trim().toLowerCase(); if (!term) return managers.slice(0, 6); return managers.filter((manager) => `${manager.entry_name} ${manager.player_name} ${manager.entry_id} ${manager.league_rank}`.toLowerCase().includes(term)).slice(0, 8); }, [managers, query]);
  return <div className="manager-picker"><span>{label}</span><label><Search size={14} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={`Find ${label.toLowerCase()}`} aria-label={`Find ${label.toLowerCase()}`} /></label><strong>#{selected.league_rank} · {selected.entry_name}</strong><div className="manager-picker-results" role="listbox" aria-label={`${label} matches`}>{matches.map((manager) => <button type="button" role="option" aria-selected={manager.entry_id === selectedId} key={manager.entry_id} className={manager.entry_id === selectedId ? "active" : ""} onClick={() => { onSelect(manager.entry_id); setQuery(""); }}><b>#{manager.league_rank}</b><span>{manager.entry_name}<small>{manager.player_name}</small></span></button>)}</div></div>;
}

function SquadColumn({ manager, picks, onOpen }: { manager: Manager; picks: Pick[]; onOpen: () => void }) { return <section className="compare-manager"><header><div><span>#{manager.league_rank}</span><h3>{manager.entry_name}</h3><small>{manager.player_name} · {manager.gw_points} pts</small></div><button type="button" onClick={onOpen}>Full squad <ArrowRight size={13} /></button></header><div>{picks.map((pick) => <PlayerChip key={pick.element} pick={pick} />)}</div></section>; }
function PlayerChip({ pick }: { pick: Pick }) { return <span className="compare-player-chip"><strong>{pick.name}</strong><small>{pick.position} · {pick.team}{pick.is_captain ? " · C" : pick.is_vice_captain ? " · V" : ""}</small></span>; }
