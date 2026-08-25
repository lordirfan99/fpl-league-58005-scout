#!/usr/bin/env python3
"""Corrected multi-league GW fetcher.

Fixes two issues in the original fetcher:
1. Managers appearing in more than one tracked league are retained in every league.
2. Transfers are fetched from /entry/{id}/transfers/ and filtered by gameweek.

The expensive per-manager API calls are cached in-memory, so overlapping managers are
only fetched once and then projected into each league's standings context.
"""

import argparse
import copy
import json
import os
import sys
import time

import fetch_gw_data as base

DATA_DIR = base.DATA_DIR


def get_entry_transfers_fixed(entry_id, gw):
    data = base.api_get(f"entry/{entry_id}/transfers/")
    if not data:
        return {"transfers": []}
    if isinstance(data, list):
        return {"transfers": [t for t in data if t.get("event") == gw]}
    transfers = data.get("transfers", []) if isinstance(data, dict) else []
    return {"transfers": [t for t in transfers if t.get("event") == gw]}


# Patch the helper used inside base.fetch_competitor_data.
base.get_entry_transfers = get_entry_transfers_fixed


def write_outputs(gw, league_id, competitors, errors):
    full_path = os.path.join(DATA_DIR, f"gw{gw}_league{league_id}_data.json")
    payload = {
        "gw": gw,
        "league_id": league_id,
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_entries": len(competitors),
        "errors": errors,
        "competitors": competitors,
    }
    with open(full_path, "w") as f:
        json.dump(payload, f, indent=2)

    compact_path = os.path.join(DATA_DIR, f"gw{gw}_league{league_id}_compact.json")
    compact = {
        "gw": gw,
        "league_id": league_id,
        "fetched_at": payload["fetched_at"],
        "total_entries": len(competitors),
        "competitors": [
            {
                "entry_id": c["entry_id"],
                "entry_name": c.get("entry_name", ""),
                "player_name": c.get("player_name", ""),
                "league_rank": c.get("league_rank", 0),
                "gw_points": c.get("gw_points", 0),
                "total_points": c.get("total_points", 0),
                "rank": c.get("rank", 0),
                "squad_cost": c.get("squad_cost", 0),
                "captain": c.get("captain", "N/A"),
                "vice_captain": c.get("vice_captain", "N/A"),
                "transfers_made": c.get("transfers_made", 0),
                "injured_count": c.get("injured_count", 0),
                "active_players_count": c.get("active_players_count", 0),
                "squad_composition": c.get("squad_composition", {}),
                "squad_teams": c.get("squad_teams", {}),
            }
            for c in competitors
        ],
    }
    with open(compact_path, "w") as f:
        json.dump(compact, f, indent=2)

    print(f"League {league_id}: {len(competitors)} competitors -> {full_path}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Corrected FPL multi-league GW fetcher")
    parser.add_argument("--gw", type=int, required=True)
    parser.add_argument("--league", type=int, nargs="+", default=[58005, 131997])
    parser.add_argument("--max", type=int, default=3000)
    args = parser.parse_args()

    os.makedirs(DATA_DIR, exist_ok=True)
    bootstrap = base.load_bootstrap()
    if not bootstrap:
        print("Failed to load FPL bootstrap-static", file=sys.stderr)
        return 1
    player_map = base.build_player_map(bootstrap)

    standings_by_league = {}
    all_entry_ids = set()
    for league_id in args.league:
        standings = base.get_league_standings(league_id, args.gw)
        if not standings:
            fallback = base.load_entry_ids_from_scout_data([league_id]).get(league_id, [])
            standings = [
                {
                    "entry_id": e["entry_id"],
                    "entry_name": e.get("entry_name", ""),
                    "player_name": e.get("player_name", ""),
                    "rank": i + 1,
                    "total_points": 0,
                    "last_rank": 0,
                }
                for i, e in enumerate(fallback)
            ]
        standings = standings[: args.max]
        standings_by_league[league_id] = standings
        all_entry_ids.update(s["entry_id"] for s in standings if s.get("entry_id"))
        print(f"League {league_id}: {len(standings)} standings entries", file=sys.stderr)

    # Fetch each unique manager once.
    cache = {}
    errors = 0
    ids = sorted(all_entry_ids)
    for i, entry_id in enumerate(ids, 1):
        try:
            cache[entry_id] = base.fetch_competitor_data(entry_id, args.gw, player_map)
        except Exception as exc:
            errors += 1
            print(f"Failed entry {entry_id}: {exc}", file=sys.stderr)
            cache[entry_id] = {"entry_id": entry_id, "gw": args.gw, "fetch_error": str(exc)}
        if i % 50 == 0:
            print(f"Fetched {i}/{len(ids)} unique managers (errors={errors})", file=sys.stderr)
        time.sleep(0.15)

    # Project the cached manager snapshot into EVERY league membership.
    for league_id, standings in standings_by_league.items():
        competitors = []
        for standing in standings:
            entry_id = standing.get("entry_id")
            if not entry_id:
                continue
            c = copy.deepcopy(cache[entry_id])
            c["league_id"] = league_id
            c["league_rank"] = standing.get("rank", 0)
            c["entry_name"] = standing.get("entry_name", "")
            c["player_name"] = standing.get("player_name", "")
            c["league_total"] = standing.get("total_points", 0)
            c["league_last_rank"] = standing.get("last_rank", 0)
            competitors.append(c)
        write_outputs(args.gw, league_id, competitors, errors)

    print(f"Done: {len(ids)} unique managers across {len(args.league)} leagues; errors={errors}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
