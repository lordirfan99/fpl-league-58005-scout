from __future__ import annotations

from app.journal import build_gameweek_journal, build_index
from app.main import app
from fastapi.testclient import TestClient


client = TestClient(app)


def test_public_journal_api_and_export() -> None:
    index = client.get("/v1/journal?season=2026-27")
    assert index.status_code == 200
    assert index.json()["gameweeks"][0]["gameweek"] == 1
    entry = client.get("/v1/journal/2026-27/gw/1")
    assert entry.status_code == 200
    assert entry.json()["quality"]["issues"] == ["predeadline_evidence_missing"]
    exported = client.get("/v1/journal/2026-27/export?filename=gameweeks.csv")
    assert exported.status_code == 200
    assert "gw_points" in exported.text


def test_journal_rejects_path_traversal_and_unknown_gw() -> None:
    assert client.get("/v1/journal?season=../../private").status_code == 400
    assert client.get("/v1/journal/2026-27/gw/39").status_code == 400


def test_journal_builder_is_deterministic_and_private_notes_are_not_inputs() -> None:
    snapshot = {"fetched_at": "2026-08-25T00:00:00Z", "total_entries": 1, "competitors": [{
        "entry_id": 1, "gw_points": 10, "total_points": 10, "overall_rank": 99, "league_rank": 1,
        "captain": "A", "squad": [{"element": 7, "name": "A", "team": "Club", "position": "MID",
        "multiplier": 2, "is_captain": True, "is_vice_captain": False}],
    }]}
    analysis = {"generated_at": "2026-08-25T00:00:00Z", "total_competitors": 1,
                "squad_ownership": {"avg_gw_points": 8}}
    live = {"elements": [{"id": 7, "stats": {"total_points": 5, "minutes": 90}}]}
    first = build_gameweek_journal(season="2026-27", gameweek=1, team_id=1, league_id=2,
                                   snapshot=snapshot, analysis=analysis, live=live)
    second = build_gameweek_journal(season="2026-27", gameweek=1, team_id=1, league_id=2,
                                    snapshot=snapshot, analysis=analysis, live=live)
    assert first == second
    assert first["summary"]["captain_points"] == 5
    assert "private" not in str(first).lower()
    assert build_index([first], "2026-27")["totals"]["completed"] == 1
