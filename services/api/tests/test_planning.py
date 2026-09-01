from datetime import datetime, timedelta, timezone

from app.planning import build_artifact, packet_status


def _source() -> dict:
    return {"gw": 2, "fetched_at": "2026-09-01T00:00:00Z", "total_entries": 1, "competitors": [{
        "entry_id": 2797967, "total_points": 100, "gw_points": 50, "gw_bank": 10,
        "squad": [{"element": 1, "name": "One", "position": "MID", "team": "A", "cost": 5.0, "multiplier": 1}],
    }]}


def _bootstrap() -> dict:
    return {"elements": [{"id": 1, "web_name": "One", "team": 1, "ep_next": "5.0", "form": "5", "points_per_game": "5", "status": "a"}], "teams": []}


def test_predeadline_plan_uses_finalized_source_not_future_snapshot() -> None:
    now = datetime(2026, 9, 1, tzinfo=timezone.utc)
    artifact = build_artifact(
        source_snapshot=_source(), target_event={"id": 3, "deadline_time": (now + timedelta(days=2)).isoformat()},
        bootstrap=_bootstrap(), fixtures=[], league_id=58005, team_id=2797967, now=now,
    )
    assert artifact["target_gameweek"] == 3
    assert artifact["source_gameweek"] == 2
    assert artifact["packet_status"] == "candidate"
    assert artifact["writes_enabled"] is False


def test_deadline_status_boundaries() -> None:
    deadline = datetime(2026, 9, 4, 17, 30, tzinfo=timezone.utc)
    assert packet_status(deadline, deadline - timedelta(hours=3)) == "candidate"
    assert packet_status(deadline, deadline - timedelta(minutes=30)) == "final"
    assert packet_status(deadline, deadline) == "locked"
