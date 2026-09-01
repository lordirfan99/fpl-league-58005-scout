import { AppShell } from "@/components/app-shell";
import { getAutopilotData } from "@/lib/autopilot";
import { getDashboardData } from "@/lib/data";

export const dynamic = "force-dynamic";

export default async function DashboardLayout({ children }: { children: React.ReactNode }) {
  const [autopilot, dashboard] = await Promise.all([getAutopilotData(), getDashboardData().catch(() => null)]);
  return <AppShell context={{ latestSnapshotGw: dashboard?.gameweek, requestedSnapshotGw: dashboard?.requestedGameweek, snapshotStatus: dashboard?.snapshotStatus, dataSource: dashboard?.dataStatus?.source, dataQuality: dashboard?.dataStatus?.quality, planningGw: autopilot?.plan?.gw ?? autopilot?.dashboard.gw ?? dashboard?.gameweek, deadline: autopilot?.plan?.deadline, status: autopilot?.plan?.status }}>{children}</AppShell>;
}
