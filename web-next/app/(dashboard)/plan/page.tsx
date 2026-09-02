import { PageHeader } from "@/components/page-header";
import { OwnerControl } from "@/components/owner-control";
import { getCompetitiveRecommendation } from "@/lib/competitive";
import { getDashboardData } from "@/lib/data";
import { deriveSeasonContext } from "@/lib/season";

export const dynamic = "force-dynamic";

export default async function PlanPage() {
  const dashboard = await getDashboardData().catch(() => null);
  const season = dashboard ? deriveSeasonContext(dashboard.bootstrap.events, { finalizedGw: dashboard.gameweek }) : null;
  const target = season?.nextDeadlineGw ?? 0;
  const recommendation = dashboard && target ? await getCompetitiveRecommendation(dashboard.leagueId, target).catch(() => null) : null;
  const captain = recommendation?.captains[0];
  return <div className="page-stack"><PageHeader eyebrow="PLAN · OWNER CONTROL" title="Approve the next FPL move" description="Create a time-limited Telegram approval only after reviewing the official-data recommendation." />
    <OwnerControl clientId={process.env.FPL_GOOGLE_OAUTH_CLIENT_ID ?? ""} targetGameweek={target} captain={captain ? { name: captain.name, element: captain.element } : undefined} />
    <section className="surface"><div className="section-heading"><div><span>RECOMMENDATION</span><h2>{captain ? `Captain ${captain.name}` : "Plan still preparing"}</h2><p>{recommendation?.competitive.phaseReason ?? "The next official FPL deadline has not produced a valid plan yet."}</p></div></div><p className="plan-safety">No action is submitted from this page. A separately configured private session executor receives only an approved, unexpired action after Telegram confirmation.</p></section>
  </div>;
}
