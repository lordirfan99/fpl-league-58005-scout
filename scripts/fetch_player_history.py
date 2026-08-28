"""Fetch deadline-safe official FPL per-player history into the V5 LAB namespace."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "v5_lab"
BASE = "https://fantasy.premierleague.com/api"


def read_json(path: str) -> dict:
    with urlopen(Request(f"{BASE}/{path}", headers={"User-Agent": "FPLScoutV5/1.0"}), timeout=30) as response:
        return json.load(response)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--player", type=int, action="append", required=True)
    args = parser.parse_args()
    DATA.mkdir(parents=True, exist_ok=True)
    for player_id in args.player:
        payload = read_json(f"element-summary/{player_id}/")
        artifact = {"schema_version": 1, "projection_version": "projection-v5.0-lab",
                    "fetched_at": datetime.now(timezone.utc).isoformat(), "source": "official-fpl-api",
                    "player_id": player_id, "history": payload.get("history", []),
                    "history_past": payload.get("history_past", [])}
        (DATA / f"player_{player_id}_history.json").write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
