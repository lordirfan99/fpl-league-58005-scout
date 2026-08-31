"""Refresh the full FPL fixture horizon used by the dashboard planner."""

from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
FPL_BASE = "https://fantasy.premierleague.com/api"
HEADERS = {"User-Agent": "FantasyScoutControlCentre/1.0"}


def get_json(path: str):
    request = Request(f"{FPL_BASE}/{path}", headers=HEADERS)
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def main() -> None:
    bootstrap = get_json("bootstrap-static/")
    fixtures = get_json("fixtures/")
    fetched_at = datetime.now(timezone.utc).isoformat()
    bootstrap_hash = hashlib.sha256(
        json.dumps(bootstrap, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    bootstrap["_meta"] = {
        "fetched_at": fetched_at,
        "source": "official-fpl-api/bootstrap-static",
        "content_sha256": bootstrap_hash,
    }
    teams = {team["id"]: team["name"] for team in bootstrap["teams"]}
    gameweeks: dict[str, list[dict]] = {str(gw): [] for gw in range(1, 39)}

    for fixture in fixtures:
        event = fixture.get("event")
        if not event:
            continue
        gameweeks[str(event)].append(
            {
                "event": event,
                "team_h": teams[fixture["team_h"]],
                "team_a": teams[fixture["team_a"]],
                "team_h_difficulty": fixture.get("team_h_difficulty", 0),
                "team_a_difficulty": fixture.get("team_a_difficulty", 0),
                "kickoff_time": fixture.get("kickoff_time"),
            }
        )

    payload = {
        "fetched_at": fetched_at,
        "source": "official-fpl-api",
        "gameweeks": gameweeks,
    }
    target = DATA_DIR / "fixtures_cache.json"
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (DATA_DIR / "bootstrap_cache.json").write_text(
        json.dumps(bootstrap, separators=(",", ":"), ensure_ascii=False), encoding="utf-8"
    )
    populated = sum(bool(items) for items in gameweeks.values())
    print(f"Saved {len(fixtures)} fixtures across {populated} gameweeks and refreshed bootstrap provenance")


if __name__ == "__main__":
    main()
