import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException

from app import main
from app.main import app
from app.recommendations import _phase, calibration_weights
from app.validation import validate_manager_squad


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["competitive_model"] == "competitive-v4.0"
    assert response.json()["execution_authority"] == "telegram"
    assert response.json()["dashboard_writes_enabled"] is False


def test_my_team_has_valid_squad() -> None:
    response = client.get("/v1/me/team?league_id=58005&gw=1")
    assert response.status_code == 200
    payload = response.json()
    assert payload["manager"]["entry_id"] == 2797967
    assert len(payload["manager"]["squad"]) == 15
    assert sum(1 for pick in payload["manager"]["squad"] if pick["multiplier"] > 0) == 11


def test_current_gameweek_is_discovered() -> None:
    identity = client.get("/v1/me").json()
    response = client.get("/v1/me/team?league_id=58005")
    assert response.status_code == 200
    assert response.json()["gameweek"] == identity["current_gameweek"]


def test_elite_and_recommendation_contracts() -> None:
    league = client.get("/v1/leagues/58005?gw=1")
    elite = client.get("/v1/elite/1?league_id=58005")
    recommendations = client.get("/v1/recommendations/current?league_id=58005&gw=1")
    assert elite.status_code == 200
    assert league.json()["hydration_percent"] == 100.0
    expected_count = max(1, (league.json()["count"] * 5 + 99) // 100)
    assert elite.json()["count"] == expected_count
    assert elite.json()["ownership"]
    assert recommendations.status_code == 200
    payload = recommendations.json()
    assert payload["elite_count"] == expected_count
    assert payload["captains"]
    assert payload["competitive"]["model_version"] == "competitive-v4.0"
    assert payload["competitive"]["phase"] in {"CATCH", "MATCH", "ATTACK", "CHASE"}
    assert 0 <= payload["competitive"]["alignment"] <= 100
    assert payload["competitive"]["target_alignment"] == 82
    assert payload["competitive"]["weights"] == {
        "elite_consensus": 0.45,
        "projection": 0.45,
        "current_season_evidence": 0.10,
    }
    assert payload["competitive"]["writes_enabled"] is False
    assert payload["competitive"]["execution_authority"] == "telegram"
    assert payload["meta"]["quality_status"] == "valid"

    # V4 must apply the published weights, not merely return them as metadata.
    candidate = next(player for player in payload["captains"] if not player["risk"])
    components = candidate["components"]
    weights = payload["competitive"]["weights"]
    calculated = 100 * sum(weights[name] * components[name] for name in weights)
    assert candidate["score"] == pytest.approx(calculated, abs=0.02)


def test_bench_boost_validation_is_chip_aware() -> None:
    payload = client.get("/v1/me/team?league_id=58005&gw=1").json()["manager"]
    payload["active_chip"] = "bboost"
    for pick in payload["squad"]:
        pick["multiplier"] = max(1, pick["multiplier"])
    assert validate_manager_squad(payload) == []


def test_canonical_decision_packet_contract() -> None:
    response = client.get("/v1/decision/current?league_id=58005&gw=1")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["decision_id"]) == 64
    assert payload["model_version"] == "competitive-v4.0"
    assert payload["competitive"]["model_version"] == "competitive-v4.0"
    assert payload["execution_authority"] == "telegram"
    assert payload["writes_enabled"] is False


def test_bridge_plan_is_canonical_before_current_snapshot(monkeypatch) -> None:
    plan = {
        "gw": 2, "status": "pending", "model_version": "competitive-v4.0",
        "plan_id": "plan-1", "input_fp": "input-1",
        "generated_at": "2026-08-26T08:00:00+00:00",
    }

    class Bridge:
        configured = True

        @staticmethod
        def control_centre():
            return {"plan": plan}

    monkeypatch.setattr(main, "autopilot", Bridge())
    monkeypatch.setattr(
        main, "recommendations",
        lambda **_: (_ for _ in ()).throw(HTTPException(status_code=404)),
    )
    response = client.get("/v1/decision/current?league_id=58005&gw=2")
    payload = response.json()
    assert response.status_code == 200
    assert payload["packet_status"] == "valid"
    assert payload["executable"] is True
    assert payload["meta"]["source"] == "autopilot_bridge"
    assert payload["plan"] == plan


def test_v4_calibration_and_chase_are_deterministic() -> None:
    for gameweek in (1, 3, 6, 12):
        assert sum(calibration_weights(gameweek).values()) == pytest.approx(1.0)
    manager = {"total_points": 1800}
    phase, _, inputs = _phase(manager, [{"total_points": 1900}], 30, alignment=90, target=72)
    assert phase == "CHASE"
    assert inputs["leader_gap"] == 100
    assert inputs["chase_trigger"] == 40


def test_catalog_exposes_official_fpl_entities() -> None:
    response = client.get("/v1/catalog")
    assert response.status_code == 200
    assert response.json()["players"]
    assert response.json()["teams"]


def test_fixture_horizon_is_populated() -> None:
    response = client.get("/v1/fixtures?from_gw=2&to_gw=6")
    assert response.status_code == 200
    payload = response.json()["gameweeks"]
    assert set(payload) == {"2", "3", "4", "5", "6"}
    assert all(payload[str(gw)] for gw in range(2, 7))


def test_missing_snapshot_is_404() -> None:
    response = client.get("/v1/leagues/58005?gw=38")
    assert response.status_code == 404


def test_telegram_is_honestly_disconnected() -> None:
    response = client.get("/v1/integration/status")
    assert response.status_code == 200
    assert response.json()["approvals_enabled"] is False
