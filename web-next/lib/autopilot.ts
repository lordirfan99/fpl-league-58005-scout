import "server-only";

const API_BASE = process.env.FPL_API_BASE_URL?.replace(/\/$/, "") ?? "http://127.0.0.1:8080";

export interface AutopilotPlayer { id?: number; name?: string; position?: string; pos?: string; club?: number | string; xpts?: number; xpts_horizon?: number; status?: string; news?: string }
export interface ShadowPlayer extends AutopilotPlayer { xpts_floor?: number; xpts_upside?: number; xpts_variance?: number; p_start?: number; expected_minutes?: number; xpts_by_gw?: number[]; variance_by_gw?: number[]; components?: Record<string, number> }
export interface ShadowTransfer { out_name?: string; in_name?: string; position?: string; out_pos?: string; in_pos?: string }
export interface ShadowWeek { gw_offset?: number; formation?: string; transfers?: ShadowTransfer[]; transfer_count?: number; hits?: number; free_transfers_before?: number; bank_after?: number; mean_points_with_captain?: number; captain?: string; vice?: string }
export interface ShadowPlan { planner?: string; planner_version?: string; mode?: string; scenario?: string; status?: string; horizon?: number; objective?: number; risk_penalty?: number; bench_weight?: number; flexibility_weight?: number; max_transfers_per_gw?: number; candidate_pool_size?: number; weights?: number[]; first_action?: ShadowTransfer | null; weeks?: ShadowWeek[] }
export interface ShadowV3 { model?: string; projection_version?: string; planner_mode?: string; planner_version?: string; gw?: number; generated_at?: string; deadline?: string; calibration?: { n?: number; mae?: number | null; rmse?: number | null; bias?: number | null }; captain?: ShadowPlayer; multigw_plan?: ShadowPlan; scenarios?: Record<string, ShadowPlan>; planner_errors?: unknown[]; squad?: ShadowPlayer[]; top_candidates?: ShadowPlayer[] }
export interface AutopilotPlan {
  gw?: number; generated_at?: string; deadline?: string; status?: string; model_version?: string; engine_display?: string; engine_note?: string;
  transfers?: Array<{ in_name?: string; out_name?: string; out_pos?: string; gain?: number; gain_gw1?: number; hit?: boolean }>;
  target_starters?: AutopilotPlayer[]; bench?: AutopilotPlayer[]; captain?: AutopilotPlayer; vice?: AutopilotPlayer;
  current_xpts?: number; target_xpts?: number; target_xi_xpts?: number; target_scoring_xpts?: number; target_net_scoring_xpts?: number; horizon_gain?: number;
  validation?: Record<string, boolean | number>; odds_note?: string; paid_transfer_note?: string; v3_shadow_progress?: string;
  league_intelligence?: { applied?: boolean; mode?: string; reason?: string };
}
export interface AutopilotData {
  bridge_version: string; execution_authority: string; writes_enabled: boolean;
  dashboard: { gw?: number; formation?: string; projected_xpts?: number; base_xpts?: number; model_version?: string; engine_note?: string; projection_generated_at?: string; team_value?: number; bank?: number; deadline?: { deadline?: string; hours?: number }; players?: AutopilotPlayer[] };
  plan?: AutopilotPlan | null; predictions?: AutopilotPlayer[];
  engine?: { promoted?: boolean; shadow_evaluated_gws?: number; promotion_candidate?: boolean; promotion_status?: string; report?: { evaluated_gws?: number[]; min_gws_required?: number; gate_met?: boolean; passed?: boolean; reason?: string; promotion_policy?: string } };
  shadow_v3?: ShadowV3 | null;
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
