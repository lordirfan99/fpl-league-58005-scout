from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


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
    assert payload["competitive"]["phase"] in {"CATCH", "MATCH", "ATTACK"}
    assert 0 <= payload["competitive"]["alignment"] <= 100
    assert payload["competitive"]["target_alignment"] == 82
    assert payload["competitive"]["weights"] == {
        "elite_consensus": 0.45,
        "projection": 0.45,
        "current_season_evidence": 0.10,
    }


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
