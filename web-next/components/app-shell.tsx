"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { ArrowLeftRight, BarChart3, Beaker, BookOpenText, Bot, Cpu, Layers3, LayoutDashboard, ListChecks, Menu, RefreshCcw, Settings, Shield, Trophy, Users, X } from "lucide-react";

const navigation = [
  { href: "/my-team", label: "My Team", icon: LayoutDashboard },
  { href: "/assistant", label: "Assistant", icon: Bot },
  { href: "/autopilot", label: "GCP Autopilot", icon: Cpu },
  { href: "/v5-lab", label: "V5 Lab", icon: Beaker },
  { href: "/model-compare", label: "Model XIs", icon: Layers3 },
  { href: "/journal", label: "Journal", icon: BookOpenText },
  { href: "/planner", label: "Planner", icon: ListChecks },
  { href: "/league", label: "League Explorer", icon: Users },
  { href: "/elite", label: "Elite 5%", icon: Trophy },
  { href: "/compare", label: "Compare", icon: ArrowLeftRight },
  { href: "/transfers", label: "Transfers & Chips", icon: RefreshCcw },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/players", label: "Players", icon: BarChart3 },
  { href: "/settings", label: "Settings", icon: Settings },
];

type PlanningContext = { latestSnapshotGw?: number; planningGw?: number; deadline?: string; status?: string };

const mobilePrimary = ["/my-team", "/assistant", "/planner", "/journal"];

export function AppShell({ children, context }: { children: React.ReactNode; context?: PlanningContext }) {
  const pathname = usePathname();
  const [moreOpen, setMoreOpen] = useState(false);
  const planningLabel = context?.planningGw ? `Planning GW${context.planningGw}` : "Planning context loading";
  return (
    <div className="app-frame">
      <aside className="sidebar">
        <Link href="/my-team" className="brand" aria-label="Fantasy Scout home">
          <span className="brand-mark"><Shield size={20} strokeWidth={2.4} /></span>
          <span><strong>Fantasy Scout</strong><small>Control Centre</small></span>
        </Link>
        <nav aria-label="Primary navigation">
          {navigation.map(({ href, label, icon: Icon }) => (
            <Link key={href} href={href} className={pathname === href ? "nav-link active" : "nav-link"}>
              <Icon size={18} /><span>{label}</span>
            </Link>
          ))}
        </nav>
        <div className="sidebar-status"><span className={context?.status === "rejected" ? "status-dot warning" : "status-dot"} /><div><strong>{planningLabel}</strong><small>{context?.latestSnapshotGw ? `Latest team snapshot: GW${context.latestSnapshotGw}` : "Snapshots connected"}</small></div></div>
      </aside>
      <div className="app-content">
        <header className="mobile-header"><Link href="/my-team" className="brand"><span className="brand-mark"><Shield size={18} /></span><strong>Fantasy Scout</strong></Link><span className="live-chip"><span className={context?.status === "rejected" ? "status-dot warning" : "status-dot"} />GW{context?.planningGw ?? "—"}</span></header>
        <div className="planning-context" role="status"><span>Decision target</span><strong>{planningLabel}</strong>{context?.latestSnapshotGw && context.latestSnapshotGw !== context.planningGw ? <small>Team and league review data currently ends at GW{context.latestSnapshotGw}.</small> : <small>Team, research and decision data are aligned.</small>}<details className="week-rail"><summary>Season weeks</summary><div>{Array.from({ length: 38 }, (_, index) => index + 1).map((gw) => <Link key={gw} href={`/journal?gw=${gw}`} className={gw === context?.latestSnapshotGw ? "archived" : gw === context?.planningGw ? "planning" : ""}>{gw === context?.latestSnapshotGw ? "✓ " : ""}GW{gw}</Link>)}</div></details></div>
        <main>{children}</main>
        <nav className="mobile-nav" aria-label="Mobile navigation">
          {navigation.filter((item) => mobilePrimary.includes(item.href)).map(({ href, label, icon: Icon }) => <Link key={href} href={href} className={pathname === href ? "active" : ""}><Icon size={19} /><span>{label}</span></Link>)}
          <button type="button" className={moreOpen ? "active" : ""} onClick={() => setMoreOpen((open) => !open)} aria-expanded={moreOpen} aria-controls="mobile-more-menu">{moreOpen ? <X size={19} /> : <Menu size={19} />}<span>More</span></button>
        </nav>
        {moreOpen ? <div className="mobile-more-menu" id="mobile-more-menu"><div><strong>Research & tools</strong><button type="button" aria-label="Close more navigation" onClick={() => setMoreOpen(false)}><X size={16} /></button></div>{navigation.filter((item) => !mobilePrimary.includes(item.href)).map(({ href, label, icon: Icon }) => <Link key={href} href={href} onClick={() => setMoreOpen(false)} className={pathname === href ? "active" : ""}><Icon size={17} /><span>{label}</span></Link>)}</div> : null}
      </div>
    </div>
  );
}
