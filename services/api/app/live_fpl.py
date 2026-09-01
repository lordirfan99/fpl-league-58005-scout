from __future__ import annotations

from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
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


def team(entry_id: int, gameweek: int, league_id: int | None = None) -> dict[str, Any]:
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
    live_points = history_row.get("event_total")
    if live_points is None:
        # During a live Gameweek FPL does not always publish the history row
        # yet. The official player event totals and the saved pick
        # multipliers still provide the manager's current provisional score.
        live_points = sum(pick["points"] * pick["multiplier"] for pick in picks)
    classic_leagues = entry.get("leagues", {}).get("classic", [])
    league = next((row for row in classic_leagues if int(row.get("id") or 0) == league_id), None)
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
        "league": ({
            "id": int(league.get("id") or 0),
            "name": league.get("name", ""),
            "entry_rank": int(league.get("entry_rank") or 0),
            "entry_last_rank": int(league.get("entry_last_rank") or 0),
            "rank_count": int(league.get("rank_count") or 0),
        } if league else None),
        "picks": picks,
        "points": int(live_points),
        "points_source": "history" if history_row.get("event_total") is not None else "official-live-picks",
        "provisional": not bool((next((e for e in bootstrap.get("events", []) if int(e.get("id") or 0) == gameweek), {}) or {}).get("finished")),
    }


def league_standings(league_id: int) -> dict[str, Any]:
    """Read the current classic-league standings directly from FPL.

    FPL publishes event totals and ranks while a gameweek is live, before our
    immutable research snapshot is finalized. Keep this read model separate
    from snapshot collection so provisional values can never overwrite history.
    """
    rows: list[dict[str, Any]] = []
    page = 1
    while True:
        payload = _get(
            f"leagues-classic/{league_id}/standings/?page_standings={page}&page_new_entries=1",
            ttl=60,
        )
        batch = payload.get("standings", {}).get("results", [])
        rows.extend(batch)
        if not payload.get("standings", {}).get("has_next") or not batch:
            break
        page += 1
        # The dashboard's live cohort only needs the top 200 managers. Full
        # league history remains available from finalized snapshots.
        if page >= 4:
            break
    return {
        "source": "official-fpl-live",
        "status": "live",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "league_id": league_id,
        "count": len(rows),
        "managers": rows,
    }


def hydrate_manager_squads(rows: list[dict[str, Any]], gameweek: int, limit: int) -> int:
    """Hydrate the top cohort's squads from official FPL picks in parallel."""
    bootstrap = _get("bootstrap-static/", ttl=30)
    players = {int(row["id"]): row for row in bootstrap.get("elements", [])}
    teams = {int(row["id"]): row.get("name", "—") for row in bootstrap.get("teams", [])}
    targets = rows[:limit]

    def hydrate(row: dict[str, Any]) -> tuple[int, list[dict[str, Any]], str]:
        try:
            payload = _get(f"entry/{int(row['entry'])}/event/{gameweek}/picks/", ttl=30)
            picks = []
            captain = ""
            for pick in payload.get("picks", []):
                player = players.get(int(pick.get("element") or 0), {})
                element_type = int(player.get("element_type") or 3)
                position = "GKP" if element_type == 1 else "DEF" if element_type == 2 else "MID" if element_type == 3 else "FWD"
                name = player.get("web_name", "Unknown")
                if pick.get("is_captain"):
                    captain = name
                picks.append({"element": int(pick.get("element") or 0), "name": name, "position": position, "team": teams.get(int(player.get("team") or 0), "—"), "cost": int(player.get("now_cost") or 0) / 10, "multiplier": int(pick.get("multiplier") or 0), "is_captain": bool(pick.get("is_captain")), "is_vice_captain": bool(pick.get("is_vice_captain")), "selected_by": float(player.get("selected_by_percent") or 0)})
            return int(row["entry"]), picks, captain
        except Exception:
            return int(row["entry"]), [], ""

    hydrated = 0
    with ThreadPoolExecutor(max_workers=16) as pool:
        futures = [pool.submit(hydrate, row) for row in targets]
        results = [future.result() for future in as_completed(futures)]
    by_id = {entry_id: (picks, captain) for entry_id, picks, captain in results}
    for row in rows:
        entry_id = int(row.get("entry") or 0)
        if entry_id in by_id and by_id[entry_id][0]:
            row["_live_squad"] = by_id[entry_id][0]
            row["_live_captain"] = by_id[entry_id][1]
            hydrated += 1
    return hydrated
