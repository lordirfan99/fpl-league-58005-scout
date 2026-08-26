"""Read-only bridge from the GCP FPL Autopilot to the web control centre.

This service intentionally exposes no execution route. Telegram remains the only
approval surface and the existing executor remains the only FPL write authority.
"""
from __future__ import annotations

import hmac
import json
import os
import threading
import time
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException

from webapp.server import build_dashboard


BASE = Path(__file__).resolve().parents[1]
PROCESSED = BASE / "data" / "processed"
PLAN_FILE = PROCESSED / "pending_plan.json"
ENGINE_FILE = PROCESSED / "engine_state.json"
AUTO_FILE = PROCESSED / "auto_state.json"
HEARTBEAT_FILE = PROCESSED / "bot_heartbeat.txt"

app = FastAPI(title="FPL Autopilot Dashboard Bridge", version="1.1.0")
_cache: dict[str, Any] = {"expires_at": 0.0, "payload": None}
_cache_lock = threading.Lock()


def require_service_token(authorization: str | None = Header(default=None)) -> None:
    expected = os.getenv("DASHBOARD_READ_TOKEN", "").strip()
    supplied = authorization.removeprefix("Bearer ").strip() if authorization else ""
    if not expected or not supplied or not hmac.compare_digest(expected, supplied):
        raise HTTPException(status_code=401, detail="Invalid dashboard service token")


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def player(player: dict[str, Any]) -> dict[str, Any]:
    return {
        key: player.get(key)
        for key in ("id", "name", "position", "pos", "club", "cost", "xpts", "xpts_horizon", "status", "cop", "news")
        if key in player
    }


def safe_plan(raw: dict[str, Any]) -> dict[str, Any] | None:
    if not raw:
        return None
    return {
        "team_id": raw.get("team_id"),
        "gw": raw.get("gw"),
        "generated_at": raw.get("generated_at"),
        "deadline": raw.get("deadline"),
        "status": raw.get("status"),
        "model_version": raw.get("model_version"),
        "engine_display": raw.get("engine_display"),
        "engine_note": raw.get("engine_note"),
        "transfers": [
            {key: move.get(key) for key in ("element_in", "element_out", "in_name", "out_name", "in_pos", "out_pos", "gain", "gain_gw1", "hit")}
            for move in raw.get("transfers", [])
        ],
        "target_starters": [player(item) for item in raw.get("target_starters", [])],
        "bench": [player(item) for item in raw.get("bench", [])],
        "captain": player(raw.get("captain", {})),
        "vice": player(raw.get("vice", {})),
        "current_xpts": raw.get("current_xpts"),
        "target_xpts": raw.get("target_xpts"),
        "target_xi_xpts": raw.get("target_xi_xpts"),
        "captain_bonus_xpts": raw.get("captain_bonus_xpts"),
        "target_scoring_xpts": raw.get("target_scoring_xpts"),
        "target_net_scoring_xpts": raw.get("target_net_scoring_xpts"),
        "horizon_gain": raw.get("horizon_gain"),
        "validation": raw.get("validation", {}),
        "chip_suggestion": raw.get("chip_suggestion"),
        "odds_note": raw.get("odds_note"),
        "bonus_note": raw.get("bonus_note"),
        "paid_transfer_note": raw.get("paid_transfer_note"),
        "league_intelligence": raw.get("league_intelligence", {}),
        "v3_shadow_progress": raw.get("v3_shadow_progress"),
    }


def prediction_rows(gw: int) -> list[dict[str, Any]]:
    raw = read_json(PROCESSED / f"predictions_gw{gw}.json")
    rows = [player(item) for item in raw.get("players", [])]
    return sorted(rows, key=lambda item: float(item.get("xpts") or 0), reverse=True)[:100]


def shadow_player(raw: dict[str, Any]) -> dict[str, Any]:
    """Return projection evidence only; never expose executor or approval state."""
    return {
        key: raw.get(key)
        for key in (
            "id", "name", "position", "club", "cost", "xpts", "xpts_floor",
            "xpts_upside", "xpts_variance", "p_start", "expected_minutes",
            "xpts_horizon", "xpts_by_gw", "variance_by_gw", "components",
        )
        if key in raw
    }


def shadow_action(raw: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    return {
        key: raw.get(key)
        for key in ("out_name", "in_name", "position", "out_pos", "in_pos")
        if key in raw
    }


def shadow_week(raw: dict[str, Any]) -> dict[str, Any]:
    captain = raw.get("captain")
    vice = raw.get("vice")
    return {
        "gw_offset": raw.get("gw_offset"),
        "formation": raw.get("formation"),
        "transfers": [shadow_action(item) for item in raw.get("transfers", []) if isinstance(item, dict)],
        "transfer_count": raw.get("transfer_count"),
        "hits": raw.get("hits"),
        "free_transfers_before": raw.get("free_transfers_before"),
        "bank_after": raw.get("bank_after"),
        "mean_points_with_captain": raw.get("mean_points_with_captain"),
        "captain": captain.get("name") if isinstance(captain, dict) else captain,
        "vice": vice.get("name") if isinstance(vice, dict) else vice,
    }


def shadow_plan(raw: dict[str, Any]) -> dict[str, Any]:
    weeks = [shadow_week(item) for item in raw.get("weeks", []) if isinstance(item, dict)]
    first_action = shadow_action(raw.get("first_action"))
    if first_action is None and weeks and weeks[0].get("transfers"):
        first_action = weeks[0]["transfers"][0]
    return {
        key: raw.get(key)
        for key in (
            "planner", "planner_version", "mode", "scenario", "status", "horizon",
            "objective", "risk_penalty", "bench_weight", "flexibility_weight",
            "max_transfers_per_gw", "candidate_pool_size", "weights",
        )
        if key in raw
    } | {
        "first_action": first_action,
        "weeks": weeks,
    }


def latest_shadow() -> dict[str, Any] | None:
    candidates: list[tuple[int, Path]] = []
    for path in PROCESSED.glob("v3_shadow_gw*.json"):
        try:
            candidates.append((int(path.stem.removeprefix("v3_shadow_gw")), path))
        except ValueError:
            continue
    if not candidates:
        return None
    raw = read_json(max(candidates, key=lambda item: item[0])[1])
    if not raw:
        return None
    scenarios = raw.get("planner_scenarios", {})
    raw_captain = raw.get("captain", {})
    captain_id = raw_captain.get("id") if isinstance(raw_captain, dict) else None
    detailed_captain = next(
        (item for item in raw.get("top_candidates", []) if isinstance(item, dict) and item.get("id") == captain_id),
        raw_captain,
    )
    return {
        "model": raw.get("model"),
        "projection_version": raw.get("projection_version"),
        "planner_mode": raw.get("planner_mode"),
        "planner_version": raw.get("planner_version"),
        "gw": raw.get("gw"),
        "generated_at": raw.get("generated_at"),
        "deadline": raw.get("deadline"),
        "calibration": raw.get("calibration", {}),
        "captain": shadow_player(detailed_captain if isinstance(detailed_captain, dict) else {}),
        "multigw_plan": shadow_plan(raw.get("multigw_plan", {})),
        "scenarios": {
            name: shadow_plan(value)
            for name, value in scenarios.items()
            if isinstance(name, str) and isinstance(value, dict)
        } if isinstance(scenarios, dict) else {},
        "planner_errors": raw.get("planner_errors", []),
        "squad": [shadow_player(item) for item in raw.get("squad", []) if isinstance(item, dict)],
        "top_candidates": [shadow_player(item) for item in raw.get("top_candidates", []) if isinstance(item, dict)][:30],
    }


def build_control_centre() -> dict[str, Any]:
    with _cache_lock:
        if _cache["payload"] is not None and float(_cache["expires_at"]) > time.time():
            return _cache["payload"]
        dashboard = build_dashboard()
        plan = safe_plan(read_json(PLAN_FILE))
        gw = int((plan or {}).get("gw") or dashboard.get("gw") or 1)
        heartbeat = None
        heartbeat_mtime = None
        try:
            heartbeat = HEARTBEAT_FILE.read_text(encoding="utf-8").strip()
            heartbeat_mtime = HEARTBEAT_FILE.stat().st_mtime
        except OSError:
            pass
        payload = {
            "bridge_version": app.version,
            "execution_authority": "telegram",
            "writes_enabled": False,
            "dashboard": dashboard,
            "plan": plan,
            "predictions": prediction_rows(gw),
            "engine": read_json(ENGINE_FILE),
            "shadow_v3": latest_shadow(),
            "automation": read_json(AUTO_FILE),
            "heartbeat": {"value": heartbeat, "modified_unix": heartbeat_mtime},
        }
        _cache.update(expires_at=time.time() + 60, payload=payload)
        return payload


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "service": "fpl-autopilot-dashboard-bridge", "read_only": True}


@app.get("/v1/control-centre", dependencies=[Depends(require_service_token)])
def control_centre() -> dict[str, Any]:
    return build_control_centre()
