from __future__ import annotations

from collections import Counter
from typing import Any


def elite_managers(
    managers: list[dict[str, Any]],
    percentile: int = 5,
    population_size: int | None = None,
) -> list[dict[str, Any]]:
    population = population_size or len(managers)
    count = min(len(managers), max(1, (population * percentile + 99) // 100))
    return sorted(managers, key=lambda item: item.get("overall_rank") or 10**12)[:count]


def cohort_summary(elite: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    owned: Counter[tuple[int, str, str, str]] = Counter()
    captained: Counter[tuple[int, str, str, str]] = Counter()
    for manager in elite:
        for pick in manager.get("squad", []):
            key = (pick["element"], pick["name"], pick["position"], pick["team"])
            owned[key] += 1
            if pick.get("is_captain"):
                captained[key] += 1
    denominator = max(1, len(elite))

    def rows(counter: Counter[tuple[int, str, str, str]]) -> list[dict[str, Any]]:
        return [
            {
                "element": key[0],
                "name": key[1],
                "position": key[2],
                "team": key[3],
                "count": count,
                "percentage": round(count / denominator * 100, 1),
            }
            for key, count in counter.most_common()
        ]

    return rows(owned), rows(captained)


def _calibration_weights(gameweek: int) -> dict[str, float]:
    if gameweek <= 2:
        return {"elite_consensus": 0.45, "projection": 0.45, "current_season_evidence": 0.10}
    if gameweek <= 4:
        return {"elite_consensus": 0.40, "projection": 0.45, "current_season_evidence": 0.15}
    if gameweek <= 8:
        return {"elite_consensus": 0.30, "projection": 0.45, "current_season_evidence": 0.25}
    return {"elite_consensus": 0.25, "projection": 0.45, "current_season_evidence": 0.30}


def _role(elite_owned: float, model_support: bool, risk: bool) -> str:
    if risk:
        return "AVOID"
    if elite_owned >= 60 and model_support:
        return "ALIGN"
    if elite_owned < 35 and model_support:
        return "CONTROLLED_EDGE"
    if elite_owned >= 60 and not model_support:
        return "INVESTIGATE"
    if elite_owned < 20 and not model_support:
        return "AVOID"
    return "NEUTRAL"


def build_recommendations(
    manager: dict[str, Any],
    managers: list[dict[str, Any]],
    bootstrap: dict[str, Any],
    fixtures: list[dict[str, Any]],
    population_size: int | None = None,
    gameweek: int = 1,
) -> dict[str, Any]:
    elite = elite_managers(managers, population_size=population_size)
    ownership, captaincy = cohort_summary(elite)
    ownership_by_id = {row["element"]: row["percentage"] for row in ownership}
    captaincy_by_id = {row["element"]: row["percentage"] for row in captaincy}
    player_index = {player["id"]: player for player in bootstrap.get("elements", [])}
    fixture_by_team: dict[str, tuple[str, int]] = {}
    for fixture in fixtures:
        home, away = fixture.get("team_h"), fixture.get("team_a")
        if home and away:
            fixture_by_team[home] = (f"{away} (H)", fixture.get("team_h_difficulty", 0))
            fixture_by_team[away] = (f"{home} (A)", fixture.get("team_a_difficulty", 0))

    known_picks: dict[int, dict[str, Any]] = {}
    for entry in managers:
        for pick in entry.get("squad", []):
            known_picks[pick["element"]] = pick

    def signal(pick: dict[str, Any]) -> dict[str, Any]:
        player = player_index.get(pick["element"], {})
        fixture, fdr = fixture_by_team.get(pick["team"], ("Fixture TBC", None))
        xpts = _number(player.get("ep_next"))
        form = _number(player.get("form"))
        elite_owned = ownership_by_id.get(pick["element"], 0.0)
        elite_captained = captaincy_by_id.get(pick["element"], 0.0)
        chance = player.get("chance_of_playing_next_round")
        risk = player.get("status", "a") != "a" or (chance is not None and chance < 75)
        fixture_boost = (6 - fdr) * 0.35 if fdr else 0
        model_support = not risk and (xpts >= 4.5 or (xpts >= 3.8 and form >= 4.0))
        score = xpts * 0.62 + form * 0.12 + elite_owned * 0.045 + elite_captained * 0.10 + fixture_boost - (6 if risk else 0)
        return {
            **pick,
            "xpts": round(xpts, 2),
            "form": round(form, 2),
            "elite_ownership": elite_owned,
            "elite_captaincy": elite_captained,
            "fixture": fixture,
            "fdr": fdr,
            "risk": risk,
            "news": player.get("news", ""),
            "model_support": model_support,
            "elite_core": elite_owned >= 60,
            "role": _role(elite_owned, model_support, risk),
            "score": round(score, 2),
        }

    signals = [signal(pick) for pick in known_picks.values()]
    by_id = {item["element"]: item for item in signals}
    squad = [by_id[pick["element"]] for pick in manager.get("squad", []) if pick["element"] in by_id]
    owned_ids = {pick["element"] for pick in squad}
    starters = [pick for pick in squad if pick.get("multiplier", 0) > 0]
    missing = sorted(
        (pick for pick in signals if pick["element"] not in owned_ids and pick["elite_ownership"] >= 20 and not pick["risk"]),
        key=lambda pick: pick["score"],
        reverse=True,
    )
    weakest: dict[str, dict[str, Any]] = {}
    for pick in squad:
        current = weakest.get(pick["position"])
        if current is None or pick["score"] < current["score"]:
            weakest[pick["position"]] = pick
    transfers = []
    for incoming in missing:
        outgoing = weakest.get(incoming["position"])
        if not outgoing:
            continue
        signal_gain = incoming["score"] - outgoing["score"]
        if signal_gain > 0.5:
            transfers.append({
                "incoming": incoming,
                "outgoing": outgoing,
                "xpts_gain": round(incoming["xpts"] - outgoing["xpts"], 2),
                "signal_gain": round(signal_gain, 2),
            })
    transfers.sort(key=lambda item: item["signal_gain"], reverse=True)

    core = [pick for pick in signals if pick["elite_core"] and not pick["risk"]]
    core_owned = sum(1 for pick in core if pick["element"] in owned_ids)
    alignment = round(core_owned / max(1, len(core)) * 100, 1) if core else 100.0
    target_alignment = 82 if gameweek <= 4 else 78 if gameweek <= 8 else 72
    if gameweek <= 4 and alignment < target_alignment:
        phase = "CATCH"
        phase_reason = "Under-aligned with the validated elite core: converge before taking unnecessary variance."
    elif alignment >= target_alignment:
        phase = "MATCH"
        phase_reason = "Core structure is competitive: preserve the baseline and use only model-supported deviations."
    else:
        phase = "ATTACK"
        phase_reason = "Alignment is below target outside the early catch window: use selective leverage rather than blind convergence."

    competitive = {
        "phase": phase,
        "phase_reason": phase_reason,
        "alignment": alignment,
        "target_alignment": target_alignment,
        "core_owned": core_owned,
        "core_size": len(core),
        "critical_missing": sorted(
            (pick for pick in core if pick["element"] not in owned_ids and pick["model_support"]),
            key=lambda pick: pick["elite_ownership"],
            reverse=True,
        )[:6],
        "model_edges": sorted(
            (pick for pick in signals if pick["element"] not in owned_ids and pick["role"] == "CONTROLLED_EDGE"),
            key=lambda pick: pick["score"],
            reverse=True,
        )[:6],
        "disagreements": sorted(
            (pick for pick in signals if pick["role"] == "INVESTIGATE"),
            key=lambda pick: pick["elite_ownership"],
            reverse=True,
        )[:6],
        "weights": _calibration_weights(gameweek),
    }

    return {
        "elite_count": len(elite),
        "elite_overlap": sum(1 for pick in squad if ownership_by_id.get(pick["element"], 0) > 0),
        "elite_average_points": round(sum(item.get("gw_points", 0) for item in elite) / max(1, len(elite)), 1),
        "transfers": transfers[:5],
        "captains": sorted(starters, key=lambda pick: pick["score"], reverse=True)[:4],
        "risks": [pick for pick in squad if pick["risk"]],
        "missing_elite_players": missing[:6],
        "competitive": competitive,
    }


def _number(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0
