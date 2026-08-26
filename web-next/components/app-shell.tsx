"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ArrowLeftRight, BarChart3, Bot, BrainCircuit, Cpu, LayoutDashboard, ListChecks, RefreshCcw, Shield, Trophy, Users } from "lucide-react";

const navigation = [
  { href: "/my-team", label: "My Team", icon: LayoutDashboard },
  { href: "/assistant", label: "Assistant", icon: Bot },
  { href: "/autopilot", label: "GCP Autopilot", icon: Cpu },
  { href: "/shadow-v3", label: "Shadow V3", icon: BrainCircuit },
  { href: "/planner", label: "Planner", icon: ListChecks },
  { href: "/league", label: "League Explorer", icon: Users },
  { href: "/elite", label: "Elite 5%", icon: Trophy },
  { href: "/compare", label: "Compare", icon: ArrowLeftRight },
  { href: "/transfers", label: "Transfers & Chips", icon: RefreshCcw },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/players", label: "Players", icon: BarChart3 },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
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
        <div className="sidebar-status"><span className="status-dot" /><div><strong>2026/27 live</strong><small>GW snapshots connected</small></div></div>
      </aside>
      <div className="app-content">
        <header className="mobile-header"><Link href="/my-team" className="brand"><span className="brand-mark"><Shield size={18} /></span><strong>Fantasy Scout</strong></Link><span className="live-chip"><span className="status-dot" />Live</span></header>
        <main>{children}</main>
        <nav className="mobile-nav" aria-label="Mobile navigation">
          {navigation.map(({ href, label, icon: Icon }) => <Link key={href} href={href} className={pathname === href ? "active" : ""}><Icon size={19} /><span>{label}</span></Link>)}
        </nav>
      </div>
    </div>
  );
}
