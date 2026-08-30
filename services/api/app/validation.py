from __future__ import annotations

from collections import Counter
from typing import Any


BENCH_BOOST_NAMES = {"bboost", "bench_boost", "benchboost", "bench boost"}
SQUAD_SHAPE = {"GKP": 2, "DEF": 5, "MID": 5, "FWD": 3}


def validate_manager_squad(manager: dict[str, Any]) -> list[str]:
    """Return chip-aware structural issues without mutating snapshot data."""
    squad = manager.get("squad") or []
    issues: list[str] = []
    if len(squad) != 15:
        issues.append(f"squad_size:{len(squad)}")
        return issues

    shape = Counter(str(pick.get("position")) for pick in squad)
    if dict(shape) != SQUAD_SHAPE:
        issues.append(f"squad_shape:{dict(shape)}")

    active_chip = str(
        manager.get("active_chip") or (manager.get("picks") or {}).get("active_chip") or ""
    ).strip().lower()
    bench_boost = active_chip in BENCH_BOOST_NAMES
    scoring_count = sum(1 for pick in squad if int(pick.get("multiplier") or 0) > 0)
    expected_scoring = 15 if bench_boost else 11
    if scoring_count != expected_scoring:
        issues.append(f"scoring_players:{scoring_count};expected:{expected_scoring};chip:{active_chip or 'none'}")

    # The FPL picks payload is ordered XI first, then bench. Validate the legal XI
    # independently of Bench Boost, where all fifteen multipliers are positive.
    lineup = squad[:11]
    lineup_shape = Counter(str(pick.get("position")) for pick in lineup)
    if lineup_shape["GKP"] != 1:
        issues.append(f"starting_goalkeepers:{lineup_shape['GKP']}")
    if not 3 <= lineup_shape["DEF"] <= 5:
        issues.append(f"starting_defenders:{lineup_shape['DEF']}")
    if not 2 <= lineup_shape["MID"] <= 5:
        issues.append(f"starting_midfielders:{lineup_shape['MID']}")
    if not 1 <= lineup_shape["FWD"] <= 3:
        issues.append(f"starting_forwards:{lineup_shape['FWD']}")

    if sum(1 for pick in squad if pick.get("is_captain")) != 1:
        issues.append("captain_count")
    if sum(1 for pick in squad if pick.get("is_vice_captain")) != 1:
        issues.append("vice_captain_count")
    return issues


def snapshot_quality(snapshot: dict[str, Any]) -> tuple[str, list[str]]:
    issues: list[str] = []
    managers = snapshot.get("competitors") or []
    declared = int(snapshot.get("total_entries") or len(managers))
    if len(managers) != declared:
        issues.append(f"hydration:{len(managers)}/{declared}")
    if snapshot.get("errors"):
        issues.append(f"collector_errors:{len(snapshot['errors'])}")
    for manager in managers:
        for issue in validate_manager_squad(manager):
            issues.append(f"entry:{manager.get('entry_id', 'unknown')}:{issue}")
            if len(issues) >= 25:
                issues.append("additional_issues_truncated")
                return "invalid", issues
    return ("valid" if not issues else "invalid"), issues
