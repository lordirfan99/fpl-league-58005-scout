from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_public_read_contract_matrix_has_no_unexpected_server_errors() -> None:
    cases = {
        "/health": 200,
        "/v1/me": 200,
        "/v1/catalog": 200,
        "/v1/fixtures?from_gw=1&to_gw=10": 200,
        "/v1/leagues/58005?gw=1": 200,
        "/v1/me/team?league_id=58005&gw=1": 200,
        "/v1/elite/1?league_id=58005": 200,
        "/v1/recommendations/current?league_id=58005&gw=1": 200,
        "/v1/projections/current?gw=1": 200,
        "/v1/journal?season=2026-27": 200,
        "/v1/journal/2026-27/gw/1": 200,
        "/v1/fixtures?from_gw=10&to_gw=1": 400,
        "/v1/leagues/58005?gw=38": 404,
    }
    for path, expected in cases.items():
        response = client.get(path)
        assert response.status_code == expected, (path, response.status_code, response.text[:300])


def test_all_gameweek_fixture_contracts_preserve_the_requested_week() -> None:
    for gameweek in range(1, 39):
        payload = client.get(f"/v1/fixtures?from_gw={gameweek}&to_gw={gameweek}").json()
        assert payload["from_gameweek"] == payload["to_gameweek"] == gameweek
        assert str(gameweek) in payload["gameweeks"]

