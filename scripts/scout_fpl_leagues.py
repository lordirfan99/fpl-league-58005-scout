"""Pre-season FPL league scouting from the public Fantasy Premier League API.

The FPL standings list is empty before GW1, so this collector reads both
``standings.results`` and ``new_entries.results``.  It then fetches each unique
entry's public profile and historical season finishes and creates a transparent
pre-season scouting score.

Run:
    python jobs/scout_fpl_leagues.py --league 19292 58005 687126 131997
"""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import json
import math
import os
import statistics
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict


BASE_URL = "https://fantasy.premierleague.com/api"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUTPUT = os.path.join(ROOT, "data", "research", "fpl_league_scout_2026-08-20.json")
USER_AGENT = "FPL-Manager-Research/1.0"


def get_json(path: str, retries: int = 5) -> dict:
    url = f"{BASE_URL}/{path.lstrip('/')}"
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.load(response)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
            last_error = exc
            if attempt == retries - 1:
                break
            time.sleep(0.75 * (2**attempt))
    raise RuntimeError(f"Failed after {retries} attempts: {url}: {last_error}")


def fetch_league(league_id: int) -> tuple[dict, list[dict]]:
    page = 1
    members: dict[int, dict] = {}
    league_meta: dict = {}
    while True:
        payload = get_json(
            f"leagues-classic/{league_id}/standings/"
            f"?page_new_entries={page}&page_standings={page}"
        )
        league_meta = payload.get("league", league_meta)
        new_entries = payload.get("new_entries", {})
        standings = payload.get("standings", {})
        for row in new_entries.get("results", []) or []:
            members[int(row["entry"])] = {
                "entry": int(row["entry"]),
                "entry_name": row.get("entry_name"),
                "player_name": " ".join(
                    p for p in [row.get("player_first_name"), row.get("player_last_name")] if p
                ),
                "joined_time": row.get("joined_time"),
                "current_league_rank": None,
                "current_points": None,
                "membership_source": "new_entries",
            }
        for row in standings.get("results", []) or []:
            existing = members.get(int(row["entry"]), {})
            existing.update(
                {
                    "entry": int(row["entry"]),
                    "entry_name": row.get("entry_name") or existing.get("entry_name"),
                    "player_name": row.get("player_name") or existing.get("player_name"),
                    "joined_time": existing.get("joined_time"),
                    "current_league_rank": row.get("rank"),
                    "current_points": row.get("total"),
                    "membership_source": "standings",
                }
            )
            members[int(row["entry"])] = existing
        has_next = bool(new_entries.get("has_next")) or bool(standings.get("has_next"))
        if not has_next:
            break
        page += 1
        if page > 1000:
            raise RuntimeError(f"Pagination safety limit reached for league {league_id}")
    return league_meta, list(members.values())


def percentile_score(percent: float | None) -> float:
    """Convert an overall-rank percentile (lower is better) to a 0-100 score."""
    if percent is None:
        return 20.0
    value = max(0.0, min(100.0, float(percent)))
    return max(0.0, min(100.0, 100.0 * (1.0 - math.sqrt(value / 100.0))))


def recent_weighted(values_oldest_first: list[float]) -> float | None:
    if not values_oldest_first:
        return None
    newest = list(reversed(values_oldest_first))
    preset = [0.40, 0.25, 0.15, 0.10, 0.06, 0.04]
    weights = preset[: len(newest)]
    if len(newest) > len(preset):
        weights.extend([0.02] * (len(newest) - len(preset)))
    total_weight = sum(weights)
    return sum(v * w for v, w in zip(newest, weights)) / total_weight


def trend_label(percentiles: list[float]) -> tuple[str, float | None]:
    if len(percentiles) < 4:
        return "Insufficient history", None
    recent = statistics.mean(percentiles[-2:])
    prior = statistics.mean(percentiles[-4:-2])
    delta = prior - recent  # positive means improvement (lower percentile)
    threshold = max(1.5, prior * 0.25)
    if delta > threshold:
        return "Improving", round(delta, 2)
    if delta < -threshold:
        return "Declining", round(delta, 2)
    return "Stable", round(delta, 2)


def classify_manager(metrics: dict) -> tuple[str, str]:
    seasons = metrics["seasons_played"]
    weighted = metrics.get("weighted_percentile")
    best = metrics.get("best_percentile")
    top_100k = metrics["top_100k_finishes"]
    top_1 = metrics["top_1pct_finishes"]
    trend = metrics["trend"]
    volatility = metrics.get("rank_volatility")

    if seasons == 0:
        return "Unproven newcomer", "D"
    if seasons <= 2:
        tier = "A" if (best is not None and best <= 1) else "C"
        return "Limited sample / high uncertainty", tier
    if (weighted is not None and weighted <= 1.5 and top_100k >= 2) or top_1 >= 3:
        return "Elite proven finisher", "S"
    if trend == "Improving" and weighted is not None and weighted <= 10:
        return "Improving contender", "A"
    if best is not None and best <= 1 and (weighted is None or weighted > 10):
        return "High ceiling, volatile", "B"
    if weighted is not None and weighted <= 5:
        return "Strong veteran", "A"
    if seasons >= 5 and weighted is not None and weighted <= 15 and (volatility or 0) <= 0.75:
        return "Steady experienced manager", "B"
    if trend == "Declining":
        return "Experienced but declining", "C"
    if weighted is not None and weighted <= 20:
        return "Competitive mid-tier", "B"
    return "Casual / inconsistent", "C"


def build_scout(entry_id: int, profile: dict, history: dict) -> dict:
    past = history.get("past", []) or []
    past = sorted(past, key=lambda row: row.get("season_name", ""))
    percentiles = [float(row["rank_percentage"]) for row in past if row.get("rank_percentage") not in (None, "")]
    ranks = [int(row["rank"]) for row in past if row.get("rank")]
    recent_pct = percentiles[-1] if percentiles else None
    weighted_pct = recent_weighted(percentiles)
    best_pct = min(percentiles) if percentiles else None
    median_pct = statistics.median(percentiles) if percentiles else None
    recent3_pct = statistics.mean(percentiles[-3:]) if percentiles else None
    log_ranks = [math.log10(rank) for rank in ranks if rank > 0]
    volatility = statistics.pstdev(log_ranks) if len(log_ranks) >= 2 else None
    trend, trend_delta = trend_label(percentiles)

    metrics = {
        "seasons_played": len(past),
        "recent_rank": ranks[-1] if ranks else None,
        "recent_percentile": round(recent_pct, 2) if recent_pct is not None else None,
        "recent3_avg_percentile": round(recent3_pct, 2) if recent3_pct is not None else None,
        "weighted_percentile": round(weighted_pct, 2) if weighted_pct is not None else None,
        "best_rank": min(ranks) if ranks else None,
        "best_percentile": round(best_pct, 2) if best_pct is not None else None,
        "median_rank": round(statistics.median(ranks)) if ranks else None,
        "median_percentile": round(median_pct, 2) if median_pct is not None else None,
        "top_100k_finishes": sum(rank <= 100_000 for rank in ranks),
        "top_10k_finishes": sum(rank <= 10_000 for rank in ranks),
        "top_10pct_finishes": sum(pct <= 10 for pct in percentiles),
        "top_1pct_finishes": sum(pct <= 1 for pct in percentiles),
        "rank_volatility": round(volatility, 3) if volatility is not None else None,
        "trend": trend,
        "trend_delta_pct_points": trend_delta,
    }

    weighted_component = percentile_score(weighted_pct)
    best_component = percentile_score(best_pct)
    consistency_component = (
        100.0 * metrics["top_10pct_finishes"] / len(past) if past else 0.0
    )
    experience_component = min(100.0, len(past) / 8.0 * 100.0)
    momentum_component = 50.0
    if trend_delta is not None:
        momentum_component = max(0.0, min(100.0, 50.0 + trend_delta * 3.0))
    scout_score = (
        0.40 * weighted_component
        + 0.25 * best_component
        + 0.20 * consistency_component
        + 0.10 * experience_component
        + 0.05 * momentum_component
    )
    metrics["score_components"] = {
        "weighted_form_40": round(weighted_component, 1),
        "best_finish_25": round(best_component, 1),
        "top10_consistency_20": round(consistency_component, 1),
        "experience_10": round(experience_component, 1),
        "momentum_5": round(momentum_component, 1),
    }
    metrics["scout_score"] = round(scout_score, 1)
    archetype, threat_tier = classify_manager(metrics)
    metrics["archetype"] = archetype
    metrics["threat_tier"] = threat_tier
    metrics["confidence"] = "High" if len(past) >= 5 else "Medium" if len(past) >= 3 else "Low"

    return {
        "entry_id": entry_id,
        "team_name": profile.get("name"),
        "manager_name": " ".join(
            p for p in [profile.get("player_first_name"), profile.get("player_last_name")] if p
        ),
        "region": profile.get("player_region_name"),
        "favourite_team_id": profile.get("favourite_team"),
        "years_active_api": profile.get("years_active"),
        "joined_time": profile.get("joined_time"),
        "metrics": metrics,
        "past_seasons": past,
        "sources": {
            "profile": f"{BASE_URL}/entry/{entry_id}/",
            "history": f"{BASE_URL}/entry/{entry_id}/history/",
        },
    }


def fetch_entry(entry_id: int) -> tuple[int, dict | None, str | None]:
    try:
        profile = get_json(f"entry/{entry_id}/")
        history = get_json(f"entry/{entry_id}/history/")
        return entry_id, build_scout(entry_id, profile, history), None
    except Exception as exc:  # keep the full league dataset even if one entry fails
        return entry_id, None, str(exc)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--league", nargs="+", type=int, required=True)
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    league_rows: list[dict] = []
    league_meta_rows: list[dict] = []
    for league_id in args.league:
        meta, members = fetch_league(league_id)
        league_meta_rows.append(
            {
                "league_id": league_id,
                "league_name": meta.get("name"),
                "created": meta.get("created"),
                "start_event": meta.get("start_event"),
                "member_count": len(members),
                "source": f"{BASE_URL}/leagues-classic/{league_id}/standings/",
            }
        )
        for member in members:
            member["league_id"] = league_id
            member["league_name"] = meta.get("name")
            league_rows.append(member)
        print(f"League {league_id} {meta.get('name')}: {len(members)} entries", flush=True)

    memberships: dict[int, list[dict]] = defaultdict(list)
    for row in league_rows:
        memberships[int(row["entry"])].append(row)
    entry_ids = sorted(memberships)
    print(f"Unique entries: {len(entry_ids)}; memberships: {len(league_rows)}", flush=True)

    scouts: dict[int, dict] = {}
    errors: dict[int, str] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(fetch_entry, entry_id): entry_id for entry_id in entry_ids}
        for index, future in enumerate(concurrent.futures.as_completed(futures), start=1):
            entry_id, scout, error = future.result()
            if scout is not None:
                scout["memberships"] = memberships[entry_id]
                scouts[entry_id] = scout
            else:
                errors[entry_id] = error or "Unknown error"
            if index % 100 == 0 or index == len(entry_ids):
                print(f"Profiles completed: {index}/{len(entry_ids)}; errors: {len(errors)}", flush=True)

    tier_counts = Counter(s["metrics"]["threat_tier"] for s in scouts.values())
    output = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "season_state": "Pre-GW1: current standings and current-season histories are empty",
        "methodology": {
            "scout_score": "40% recent-weighted historical percentile + 25% best finish + 20% top-10% consistency + 10% experience + 5% momentum",
            "recent_weights_newest_first": [0.40, 0.25, 0.15, 0.10, 0.06, 0.04, "0.02 each older season"],
            "percentile_transform": "100 * (1 - sqrt(rank_percentile / 100)); lower historical percentile is better",
            "limitations": [
                "Pre-season scouting uses only public historical finishes; no 2026/27 picks or transfer behaviour is visible before the GW1 deadline.",
                "Threat tiers and archetypes are analytical labels, not facts supplied by FPL.",
                "Managers can join or leave leagues after this snapshot.",
            ],
        },
        "leagues": league_meta_rows,
        "memberships": league_rows,
        "unique_entries": len(entry_ids),
        "successful_profiles": len(scouts),
        "errors": errors,
        "tier_counts": dict(tier_counts),
        "scouts": sorted(scouts.values(), key=lambda s: (-s["metrics"]["scout_score"], s["entry_id"])),
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(output, handle, ensure_ascii=False, indent=2)
    print(f"Saved {args.output}", flush=True)


if __name__ == "__main__":
    main()
