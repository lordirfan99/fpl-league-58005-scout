"""Deadline-safe, read-only planning artifacts for the next FPL gameweek."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any

from .recommendations import MODEL_VERSION, build_recommendations


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def next_event(bootstrap: dict[str, Any]) -> dict[str, Any] | None:
    return next((event for event in bootstrap.get("events", []) if event.get("is_next")), None)


def packet_status(deadline: datetime, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    if now >= deadline:
        return "locked"
    if now >= deadline - timedelta(hours=2):
        return "final"
    return "candidate"


def build_artifact(
    *, source_snapshot: dict[str, Any], target_event: dict[str, Any], bootstrap: dict[str, Any],
    fixtures: list[dict[str, Any]], league_id: int, team_id: int, now: datetime | None = None,
) -> dict[str, Any]:
    """Build a recommendation for ``target_event`` from the last final snapshot.

    The target GW is intentionally never used as a league-snapshot lookup: its
    public squads are unavailable before deadline and would leak after it.
    """
    now = now or datetime.now(timezone.utc)
    deadline = datetime.fromisoformat(str(target_event["deadline_time"]).replace("Z", "+00:00"))
    managers = source_snapshot.get("competitors", [])
    manager = next((row for row in managers if int(row.get("entry_id") or 0) == team_id), None)
    source_gw = int(source_snapshot.get("gw") or 0)
    if manager is None or source_gw < 1:
        return {
            "schema_version": 1, "league_id": league_id, "team_id": team_id,
            "target_gameweek": int(target_event["id"]), "source_gameweek": source_gw or None,
            "deadline": target_event["deadline_time"], "generated_at": now.isoformat(),
            "packet_status": "insufficient_data", "quality_status": "unknown",
            "quality_issues": ["configured_team_missing_from_source_snapshot"],
            "execution_authority": "manual_fpl", "writes_enabled": False,
        }
    recommendation = build_recommendations(
        manager, managers, bootstrap, fixtures,
        population_size=source_snapshot.get("population_size") or source_snapshot.get("total_entries"),
        gameweek=int(target_event["id"]),
    )
    artifact = {
        "schema_version": 1, "league_id": league_id, "team_id": team_id,
        "target_gameweek": int(target_event["id"]), "source_gameweek": source_gw,
        "deadline": target_event["deadline_time"], "generated_at": now.isoformat(),
        "expires_at": deadline.isoformat(), "packet_status": packet_status(deadline, now),
        "quality_status": "valid", "quality_issues": [], "model_version": MODEL_VERSION,
        "source_snapshot_at": source_snapshot.get("fetched_at"),
        "input_hashes": {
            "source_snapshot": canonical_hash(source_snapshot), "bootstrap": canonical_hash(bootstrap),
            "fixtures": canonical_hash(fixtures),
        },
        "execution_authority": "manual_fpl", "writes_enabled": False,
        **recommendation,
    }
    artifact["artifact_hash"] = canonical_hash(artifact)
    return artifact


def freeze_payload(artifact: dict[str, Any], *, season: str, now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    payload = {
        "schema_version": 3, "season": season, "gameweek": artifact.get("target_gameweek"),
        "captured_at": now.isoformat(), "deadline": artifact.get("deadline"),
        "decision": artifact, "artifact_hashes": {"decision": canonical_hash(artifact)},
        "execution_authority": "manual_fpl", "writes_enabled": False,
    }
    payload["input_hash"] = canonical_hash(payload)
    return payload
