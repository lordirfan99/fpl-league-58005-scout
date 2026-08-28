"use client";

import Link from "next/link";
import { useState } from "react";
import { AlertTriangle, ArrowUpRight, CheckCircle2 } from "lucide-react";
import type { JournalIndexRow } from "@/lib/journal";

export function JournalTimeline({ season, rows }: { season: string; rows: JournalIndexRow[] }) {
  const [quality, setQuality] = useState<"all" | "valid" | "partial">("all");
  const visible = quality === "all" ? rows : rows.filter((row) => row.quality.status === quality);
  return <section className="surface journal-timeline-surface">
    <div className="section-heading"><div><span>SEASON TIMELINE</span><h2>Every decision leaves evidence</h2></div><div className="journal-filter" role="group" aria-label="Filter journal quality">{(["all", "valid", "partial"] as const).map((item) => <button key={item} type="button" aria-pressed={quality === item} className={quality === item ? "active" : ""} onClick={() => setQuality(item)}>{item}</button>)}</div></div>
    <div className="journal-timeline">
      {visible.map((row) => <Link href={`/journal/${season}/gw/${row.gameweek}`} className="journal-week" key={row.gameweek}>
        <span className="journal-node">GW{row.gameweek}</span>
        <article><header><div><span>{row.summary.phase ?? "SEASON START"}</span><h3>{row.summary.gw_points} points</h3></div>{row.quality.status === "valid" ? <CheckCircle2 /> : <AlertTriangle />}</header>
          <div className="journal-week-stats"><span><b>{row.summary.total_points}</b>Total</span><span><b>#{row.summary.league_rank.toLocaleString()}</b>League</span><span><b className={row.summary.points_vs_reference >= 0 ? "positive-text" : "negative-text"}>{row.summary.points_vs_reference > 0 ? "+" : ""}{row.summary.points_vs_reference}</b>vs reference</span></div>
          <footer><span>{row.summary.captain ?? "No captain"} · {row.summary.captain_points ?? "—"} pts</span><b>Open review <ArrowUpRight size={13} /></b></footer>
        </article>
      </Link>)}
    </div>
    {visible.length === 0 ? <div className="empty-state"><h3>No matching journal entries</h3><p>Choose another quality filter.</p></div> : null}
  </section>;
}
