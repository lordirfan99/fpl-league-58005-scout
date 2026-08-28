import "server-only";

const API_BASE = process.env.FPL_API_BASE_URL?.replace(/\/$/, "") ?? "http://127.0.0.1:8080";

export interface AutopilotPlayer { id?: number; name?: string; position?: string; pos?: string; club?: number | string; cost?: number; xpts?: number; xpts_horizon?: number; status?: string; news?: string; starter?: boolean; role?: string }
export interface ShadowPlayer extends AutopilotPlayer { xpts_floor?: number; xpts_upside?: number; xpts_variance?: number; p_start?: number; expected_minutes?: number; xpts_by_gw?: number[]; variance_by_gw?: number[]; components?: Record<string, number> }
export interface ShadowTransfer { out_name?: string; in_name?: string; position?: string; out_pos?: string; in_pos?: string }
export interface ShadowWeek { gw_offset?: number; formation?: string; transfers?: ShadowTransfer[]; transfer_count?: number; hits?: number; free_transfers_before?: number; bank_after?: number; mean_points_with_captain?: number; captain?: string; vice?: string }
export interface ShadowPlan { planner?: string; planner_version?: string; mode?: string; scenario?: string; status?: string; horizon?: number; objective?: number; risk_penalty?: number; bench_weight?: number; flexibility_weight?: number; max_transfers_per_gw?: number; candidate_pool_size?: number; weights?: number[]; first_action?: ShadowTransfer | null; weeks?: ShadowWeek[] }
export interface ShadowV3 { model?: string; projection_version?: string; planner_mode?: string; planner_version?: string; gw?: number; generated_at?: string; deadline?: string; calibration?: { n?: number; mae?: number | null; rmse?: number | null; bias?: number | null }; captain?: ShadowPlayer; multigw_plan?: ShadowPlan; scenarios?: Record<string, ShadowPlan>; planner_errors?: unknown[]; squad?: ShadowPlayer[]; top_candidates?: ShadowPlayer[] }
export interface ShadowV42 { model_version?: string; champion_version?: string; artifact_type?: string; gw?: number; generated_at?: string; deadline?: string; history_rows?: number; formation?: string; captain_id?: number; lineup?: ShadowPlayer[]; bench?: ShadowPlayer[]; transfers?: ShadowTransfer[]; mean_points_with_captain?: number; robust_points_with_captain?: number; optimizer_status?: string; optimizer_error?: string | null }
export interface DecisionRoute { moves?: Array<{ out?: string; in?: string; hit?: boolean }>; horizon_gain?: number; net_after_hit?: number; projection_starts_gw?: number }
export interface DecisionSummary {
  schema_version?: number; run_id?: string; plan_id?: string;
  optimizer?: { name?: string; version?: string; status?: string; objective?: number; candidate_pool_size?: number };
  recommended_action?: string; reason?: string; approval_scope?: string; template_candidate_gate_applied?: boolean;
  formation?: { selected?: string; template?: string; explanation?: string };
  horizon?: { metric?: string; current_weighted?: number; proposed_weighted?: number; rows?: Array<{ gw?: number; weight?: number; current?: number; proposed?: number; gain?: number }> };
  roadmap?: Array<{ gw?: number; action?: string; status?: string; route?: DecisionRoute | null; formation?: string; bank_after?: number; free_transfers_before?: number; free_transfers_after?: number; mean_points_with_captain?: number; robust_points_with_captain?: number }>;
  captain_rankings?: Array<{ name?: string; xpts?: number; p_start?: number; expected_minutes?: number; eligible?: boolean; reason?: string }>;
  team_diff?: { started?: string[]; benched?: string[]; captain_from?: string; captain_to?: string; vice_from?: string; vice_to?: string; write_required?: boolean; approval_action?: string };
  source_manifest?: { status?: string; run_id?: string; official_fpl?: { status?: string; fetched_at?: string }; account?: { status?: string; fetched_at?: string; squad_count?: number; free_transfers?: number }; league?: { status?: string; run_id?: string; snapshot_at?: string; freshness_hours?: number }; refresh_failures?: string[] };
  alternatives?: { best_paid_transfer?: DecisionRoute | null; paid_transfer_allowed?: boolean };
  uncertainty?: { mean_with_captain?: number; outcome_low?: number; outcome_high?: number; label?: string; calibration?: { n?: number; mae?: number; rmse?: number; bias?: number } };
  template_comparison?: { formation?: string; owned?: Array<{ name?: string }>; missing?: Array<{ name?: string; position?: string; elite_percentage?: number; cash_affordable_with_one_move?: boolean | null }>; outside?: Array<{ name?: string; position?: string }> };
  data_health?: { account_squad_synced?: boolean; free_transfers_synced?: boolean; free_transfers?: number; league_snapshot_age_hours?: number | null; league_context_ready?: boolean; deadline_safety?: string; minutes_to_deadline?: number };
}
export interface AutopilotPlan {
  schema_version?: number; run_id?: string; optimizer_version?: string; projection_version?: string; plan_id?: string;
  gw?: number; generated_at?: string; deadline?: string; status?: string; model_version?: string; engine_display?: string; engine_note?: string;
  transfers?: Array<{ in_name?: string; out_name?: string; out_pos?: string; gain?: number; gain_gw1?: number; hit?: boolean }>;
  target_starters?: AutopilotPlayer[]; bench?: AutopilotPlayer[]; captain?: AutopilotPlayer; vice?: AutopilotPlayer;
  current_xpts?: number; target_xpts?: number; target_xi_xpts?: number; target_scoring_xpts?: number; target_net_scoring_xpts?: number; horizon_gain?: number;
  validation?: Record<string, boolean | number>; data_note?: string; paid_transfer_note?: string;
  league_intelligence?: { applied?: boolean; mode?: string; reason?: string };
  competitive?: Record<string, unknown>;
  model_candidate?: { version?: string; status?: string; evaluated_gws?: number[]; rows?: number; eligible_for_owner_approval?: boolean; checks?: Record<string, boolean> };
  decision_summary?: DecisionSummary;
}
export interface AutopilotData {
  bridge_version: string; execution_authority: string; writes_enabled: boolean;
  dashboard: { gw?: number; formation?: string; projected_xpts?: number; base_xpts?: number; model_version?: string; engine_note?: string; projection_generated_at?: string; team_value?: number; bank?: number; deadline?: { deadline?: string; hours?: number }; players?: AutopilotPlayer[] };
  plan?: AutopilotPlan | null; predictions?: AutopilotPlayer[];
  engine?: { promoted?: boolean; shadow_evaluated_gws?: number; promotion_candidate?: boolean; promotion_status?: string; report?: { evaluated_gws?: number[]; min_gws_required?: number; gate_met?: boolean; passed?: boolean; reason?: string; promotion_policy?: string } };
  shadow_v3?: ShadowV3 | null;
  shadow_v42?: ShadowV42 | null;
  automation?: Record<string, unknown>; heartbeat?: { value?: string; modified_unix?: number };
}

export async function getAutopilotData(): Promise<AutopilotData | null> {
  try {
    const response = await fetch(`${API_BASE}/v1/autopilot/control-centre`, { cache: "no-store" });
    if (!response.ok) return null;
    return response.json() as Promise<AutopilotData>;
  } catch {
    return null;
  }
}
