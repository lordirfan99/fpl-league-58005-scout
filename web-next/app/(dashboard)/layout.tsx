import { AppShell } from "@/components/app-shell";
import { getDashboardData } from "@/lib/data";

export const dynamic = "force-dynamic";

export default async function DashboardLayout({ children }: { children: React.ReactNode }) {
  const dashboard = await getDashboardData().catch(() => null);
  return <AppShell context={{
    latestSnapshotGw: dashboard?.gameweek,
    requestedSnapshotGw: dashboard?.requestedGameweek,
    snapshotStatus: dashboard?.snapshotStatus,
    dataSource: dashboard?.dataStatus?.source,
    dataQuality: dashboard?.dataStatus?.quality,
    planningGw: dashboard?.gameweek,
  }}>{children}</AppShell>;
}
