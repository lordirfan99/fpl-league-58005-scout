from __future__ import annotations

from datetime import datetime, timezone
from time import monotonic
from typing import Any

import httpx


FPL_BASE = "https://fantasy.premierleague.com/api"
_cache: dict[str, tuple[float, Any]] = {}


def _get(path: str, ttl: int = 30) -> Any:
    now = monotonic()
    cached = _cache.get(path)
    if cached and cached[0] > now:
        return cached[1]
    response = httpx.get(
        f"{FPL_BASE}/{path.lstrip('/')}",
        headers={"User-Agent": "FPLScoutLive/1.0", "Accept": "application/json"},
        timeout=20,
        follow_redirects=True,
    )
    response.raise_for_status()
    value = response.json()
    _cache[path] = (now + ttl, value)
    return value


def current_gameweek() -> int:
    payload = _get("bootstrap-static/", ttl=30)
    current = next((event for event in payload.get("events", []) if event.get("is_current")), None)
    return int((current or {}).get("id") or 1)


def team(entry_id: int, gameweek: int) -> dict[str, Any]:
    """Read the public, mutable FPL team state for one entry.

    This is intentionally a live read model. It is never used to rewrite the
    journal or any completed-gameweek snapshot.
    """
    bootstrap = _get("bootstrap-static/", ttl=30)
    players = {int(row["id"]): row for row in bootstrap.get("elements", [])}
    entry = _get(f"entry/{entry_id}/", ttl=30)
    picks_payload = _get(f"entry/{entry_id}/event/{gameweek}/picks/", ttl=15)
    history = _get(f"entry/{entry_id}/history/", ttl=30)
    history_row = next((row for row in history.get("current", []) if int(row.get("event") or 0) == gameweek), {})
    picks: list[dict[str, Any]] = []
    for pick in picks_payload.get("picks", []):
        player = players.get(int(pick.get("element") or 0), {})
        picks.append({
            "element": int(pick.get("element") or 0),
            "position": int(pick.get("position") or 0),
            "multiplier": int(pick.get("multiplier") or 0),
            "is_captain": bool(pick.get("is_captain")),
            "is_vice_captain": bool(pick.get("is_vice_captain")),
            "web_name": player.get("web_name", "Unknown"),
            "team": int(player.get("team") or 0),
            "points": int(player.get("event_points") or 0),
            "now_cost": int(player.get("now_cost") or 0),
        })
    return {
        "source": "official-fpl-live",
        "status": "live",
        "gameweek": gameweek,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "entry": {
            "id": int(entry_id),
            "entry_name": entry.get("name", ""),
            "player_name": entry.get("player_first_name", "") + " " + entry.get("player_last_name", ""),
            "overall_rank": history_row.get("overall_rank") or entry.get("summary_overall_rank") or 0,
            "total_points": history_row.get("total_points") or entry.get("summary_overall_points") or 0,
            "value": entry.get("last_deadline_value") or entry.get("value") or 0,
            "bank": entry.get("last_deadline_bank") or entry.get("bank") or 0,
            "transfers_made": history_row.get("event_transfers") or 0,
            "transfers_cost": history_row.get("event_transfers_cost") or 0,
        },
        "picks": picks,
        "points": history_row.get("event_total"),
        "provisional": not bool((next((e for e in bootstrap.get("events", []) if int(e.get("id") or 0) == gameweek), {}) or {}).get("finished")),
    }
