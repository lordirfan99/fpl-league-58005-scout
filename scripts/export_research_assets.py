"""Export the four-league FPL scout snapshot into repository assets."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


def md(value) -> str:
    return str(value if value is not None else "—").replace("|", "\\|").replace("\n", " ")


def pct(value, digits=1) -> str:
    return f"{100 * value:.{digits}f}%"


def rank_value(value) -> str:
    return f"{int(value):,}" if value not in (None, "") else "—"


def manager_row(rank: int, scout: dict) -> str:
    metrics = scout["metrics"]
    return (
        f"| {rank} | {md(scout['team_name'])} | {md(scout['manager_name'])} | "
        f"{metrics['seasons_played']} | {rank_value(metrics['best_rank'])} | "
        f"{rank_value(metrics['recent_rank'])} | {metrics['weighted_percentile'] if metrics['weighted_percentile'] is not None else '—'} | "
        f"{metrics['scout_score']:.1f} | {metrics['threat_tier']} | {md(metrics['archetype'])} |"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    repo = args.repo.resolve()
    data_dir = repo / "data"
    reports_dir = repo / "reports"
    data_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    data = json.loads(args.source.read_text(encoding="utf-8"))
    scouts = data["scouts"]
    scout_by_id = {int(s["entry_id"]): s for s in scouts}

    # Canonical JSON exports.
    (data_dir / "full_scout_data.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    membership_payload = {
        "generated_at": data["generated_at"],
        "season_state": data["season_state"],
        "leagues": data["leagues"],
        "memberships": data["memberships"],
    }
    (data_dir / "league_entries.json").write_text(
        json.dumps(membership_payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    scout_fields = [
        "scout_rank", "entry_id", "team_name", "manager_name", "region", "league_count", "league_ids",
        "seasons_played", "years_active_api", "recent_rank", "recent_percentile", "recent3_avg_percentile",
        "weighted_percentile", "best_rank", "best_percentile", "median_rank", "median_percentile",
        "top_100k_finishes", "top_10k_finishes", "top_10pct_finishes", "top_1pct_finishes",
        "rank_volatility", "trend", "trend_delta_pct_points", "scout_score", "threat_tier", "archetype",
        "confidence", "profile_source", "history_source",
    ]
    with (data_dir / "scout_report.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=scout_fields)
        writer.writeheader()
        for rank, scout in enumerate(scouts, start=1):
            metrics = scout["metrics"]
            writer.writerow({
                "scout_rank": rank,
                "entry_id": scout["entry_id"],
                "team_name": scout["team_name"],
                "manager_name": scout["manager_name"],
                "region": scout["region"],
                "league_count": len(scout["memberships"]),
                "league_ids": ",".join(str(m["league_id"]) for m in scout["memberships"]),
                "seasons_played": metrics["seasons_played"],
                "years_active_api": scout["years_active_api"],
                "recent_rank": metrics["recent_rank"],
                "recent_percentile": metrics["recent_percentile"],
                "recent3_avg_percentile": metrics["recent3_avg_percentile"],
                "weighted_percentile": metrics["weighted_percentile"],
                "best_rank": metrics["best_rank"],
                "best_percentile": metrics["best_percentile"],
                "median_rank": metrics["median_rank"],
                "median_percentile": metrics["median_percentile"],
                "top_100k_finishes": metrics["top_100k_finishes"],
                "top_10k_finishes": metrics["top_10k_finishes"],
                "top_10pct_finishes": metrics["top_10pct_finishes"],
                "top_1pct_finishes": metrics["top_1pct_finishes"],
                "rank_volatility": metrics["rank_volatility"],
                "trend": metrics["trend"],
                "trend_delta_pct_points": metrics["trend_delta_pct_points"],
                "scout_score": metrics["scout_score"],
                "threat_tier": metrics["threat_tier"],
                "archetype": metrics["archetype"],
                "confidence": metrics["confidence"],
                "profile_source": scout["sources"]["profile"],
                "history_source": scout["sources"]["history"],
            })

    history_fields = ["entry_id", "team_name", "manager_name", "season", "total_points", "overall_rank", "rank_percentile", "history_source"]
    with (data_dir / "season_history.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=history_fields)
        writer.writeheader()
        for scout in sorted(scouts, key=lambda s: int(s["entry_id"])):
            for season in scout["past_seasons"]:
                writer.writerow({
                    "entry_id": scout["entry_id"],
                    "team_name": scout["team_name"],
                    "manager_name": scout["manager_name"],
                    "season": season["season_name"],
                    "total_points": season["total_points"],
                    "overall_rank": season["rank"],
                    "rank_percentile": season["rank_percentage"],
                    "history_source": scout["sources"]["history"],
                })

    league_stats = []
    for league in data["leagues"]:
        members = [m for m in data["memberships"] if int(m["league_id"]) == int(league["league_id"])]
        league_scouts = [scout_by_id[int(m["entry"])] for m in members]
        tiers = Counter(s["metrics"]["threat_tier"] for s in league_scouts)
        scores = sorted(s["metrics"]["scout_score"] for s in league_scouts)
        midpoint = len(scores) // 2
        median = scores[midpoint] if len(scores) % 2 else (scores[midpoint - 1] + scores[midpoint]) / 2
        top = max(league_scouts, key=lambda s: s["metrics"]["scout_score"])
        league_stats.append({
            **league,
            "tiers": tiers,
            "average": sum(scores) / len(scores),
            "median": median,
            "coverage": sum(s["metrics"]["seasons_played"] > 0 for s in league_scouts) / len(league_scouts),
            "top": top,
        })

    overlap = Counter(len(s["memberships"]) for s in scouts)
    kokdiang_rank = next(i for i, s in enumerate(scouts, start=1) if int(s["entry_id"]) == 2797967)
    kokdiang = scout_by_id[2797967]
    sa_count = sum(s["metrics"]["threat_tier"] in {"S", "A"} for s in scouts)
    history_count = sum(s["metrics"]["seasons_played"] > 0 for s in scouts)

    league_table = [
        "| League | Members | S | A | B | C | D | Avg | Median | History | Top manager |",
        "|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|:--|",
    ]
    for stat in league_stats:
        tier = stat["tiers"]
        top = stat["top"]
        league_table.append(
            f"| {md(stat['league_name'])} (`{stat['league_id']}`) | {stat['member_count']:,} | {tier['S']} | {tier['A']} | {tier['B']} | {tier['C']} | {tier['D']} | "
            f"{stat['average']:.1f} | {stat['median']:.1f} | {pct(stat['coverage'])} | {md(top['team_name'])} — {md(top['manager_name'])} ({top['metrics']['scout_score']:.1f}) |"
        )

    top_header = [
        "| # | Team | Manager | Seasons | Best rank | Recent rank | Weighted % | Score | Tier | Archetype |",
        "|--:|:--|:--|--:|--:|--:|--:|--:|:--:|:--|",
    ]
    top25 = top_header + [manager_row(i, s) for i, s in enumerate(scouts[:25], start=1)]

    findings = f"""# Four-League FPL Scout Findings

Snapshot: **20 August 2026, pre-GW1**. Public FPL API data only.

## Dataset

- **{len(data['memberships']):,}** league memberships
- **{len(scouts):,}** unique managers after cross-league deduplication
- **{history_count:,}** managers with historical records ({history_count / len(scouts):.1%})
- **{sum(len(s['past_seasons']) for s in scouts):,}** historical season rows
- **{sa_count:,}** S/A threats ({sa_count / len(scouts):.1%})
- **{len(data['errors'])}** profile/history API failures

## League comparison

{chr(10).join(league_table)}

**Na Fantasy League is the strongest field by historical profile**: average score {league_stats[2]['average']:.1f}, median {league_stats[2]['median']:.1f}, with {league_stats[2]['tiers']['S'] + league_stats[2]['tiers']['A']} S/A managers among {league_stats[2]['member_count']} members.

## Top 25 historical threats

{chr(10).join(top25)}

## Cross-league overlap

| Membership count | Unique managers |
|--:|--:|
| 1 league | {overlap[1]:,} |
| 2 leagues | {overlap[2]:,} |
| 3 leagues | {overlap[3]:,} |
| 4 leagues | {overlap[4]:,} |

**KOKDIANG FC — Muhd Irfan (entry `2797967`) is the only manager in all four leagues.**

## KOKDIANG FC baseline

| Metric | Value |
|:--|--:|
| Historical scout rank | {kokdiang_rank:,} / {len(scouts):,} |
| Score / tier | {kokdiang['metrics']['scout_score']:.1f} / {kokdiang['metrics']['threat_tier']} |
| Confidence | {kokdiang['metrics']['confidence']} |
| Historical seasons | {kokdiang['metrics']['seasons_played']} |
| Best overall rank | {kokdiang['metrics']['best_rank']:,} |
| Recent overall rank | {kokdiang['metrics']['recent_rank']:,} |
| Recent percentile | {kokdiang['metrics']['recent_percentile']:.1f}% |

This is a baseline, not a prediction of 2026/27 performance. Only two historical seasons are available, so uncertainty is high.

## Methodology

Scout score is **40% recent-weighted historical percentile + 25% best finish + 20% top-10% consistency + 10% experience + 5% momentum**.

Historical percentile is transformed as `100 × (1 − sqrt(rank percentile ÷ 100))`. Recent seasons receive more weight. Tiers and archetypes are analytical labels generated by this project, not official FPL classifications.

## Pre-GW1 limitation

The four league endpoints returned members in `new_entries`; current standings are empty until scoring begins. Current-season picks, captaincy, transfer-hit behaviour and team-value growth therefore cannot yet be used. Re-run after each deadline to replace preseason priors with live evidence.
"""
    (reports_dir / "FINDINGS.md").write_text(findings, encoding="utf-8")

    tier_lines = [
        "# Threat Tier Breakdown", "", "## All unique managers", "",
        "| Tier | Managers | Share |", "|:--:|--:|--:|",
    ]
    total_tiers = Counter(s["metrics"]["threat_tier"] for s in scouts)
    for tier in ["S", "A", "B", "C", "D"]:
        tier_lines.append(f"| {tier} | {total_tiers[tier]:,} | {total_tiers[tier] / len(scouts):.1%} |")
    tier_lines += ["", "## By league", "", *league_table, "", "See `FINDINGS.md` and the workbook for methodology and row-level evidence."]
    (reports_dir / "TIER_BREAKDOWN.md").write_text("\n".join(tier_lines) + "\n", encoding="utf-8")

    for filename, tier, title in [
        ("ELITE_MANAGERS.md", "S", "Tier S Managers"),
        ("SHARP_MANAGERS.md", "A", "Tier A Managers"),
    ]:
        selected = [s for s in scouts if s["metrics"]["threat_tier"] == tier]
        lines = [f"# {title}", "", f"**{len(selected)} managers** in the four-league deduplicated snapshot.", "", *top_header]
        for scout in selected:
            lines.append(manager_row(scouts.index(scout) + 1, scout))
        lines += ["", "Scores are pre-GW1 historical priors; see `FINDINGS.md` for methodology and limitations."]
        (reports_dir / filename).write_text("\n".join(lines) + "\n", encoding="utf-8")

    strategy = f"""# Competitive Strategy — 2026/27

## What the research changes

1. **Na Fantasy League deserves the tightest monitoring.** Its median historical score ({league_stats[2]['median']:.1f}) is the highest of the four leagues.
2. **Track the shared threats first.** {overlap[2] + overlap[3] + overlap[4]} managers appear in at least two target leagues, so one monitoring pipeline covers multiple competitions.
3. **Do not overreact to peak rank alone.** The scoring model separates ceiling, recent weighted form, consistency, experience and momentum.
4. **Pre-GW1 classifications are priors.** Upgrade them with actual captain, transfers, hits, squad value and GW-rank consistency after deadlines.

## Priority watchlist

{chr(10).join(top25[:12])}

## KOKDIANG FC plan

- Historical baseline: rank **{kokdiang_rank:,}/{len(scouts):,}**, score **{kokdiang['metrics']['scout_score']:.1f}**, tier **{kokdiang['metrics']['threat_tier']}**, low confidence.
- The low-confidence label matters: two seasons are not enough to establish the manager's true ceiling.
- First target: outperform the C-tier median through disciplined captaincy and avoiding unnecessary hits.
- Reassess after GW4, when live evidence begins to outweigh the historical prior.
- Monitor the top shared threats weekly; compare captain, transfers, hits and rank movement only after each deadline.

## Monitoring cadence

- **Post-deadline:** capture revealed squads, captain and transfers.
- **During GW:** monitor live points and rank movement.
- **Post-GW:** calculate transfer gain/loss, hit efficiency, captain contribution and value capture.
- **GW4 onward:** blend live sharpness with this historical score.
"""
    (reports_dir / "COMPETITIVE_STRATEGY.md").write_text(strategy, encoding="utf-8")

    readme = f"""# FPL Four-League Manager Scout — 2026/27

Pre-season competitive intelligence for FPL leagues **19292, 58005, 687126 and 131997**, collected from the public Fantasy Premier League API on 20 August 2026.

## Snapshot

- {len(data['memberships']):,} memberships
- {len(scouts):,} unique managers
- {history_count:,} managers with history
- {sum(len(s['past_seasons']) for s in scouts):,} historical season records
- {sa_count:,} tier S/A threats
- zero failed profiles

## Core finding

**Na Fantasy League has the strongest historical field**, while **Mapei Quick Step — Faris Zain** leads the combined scout ranking with a score of **{scouts[0]['metrics']['scout_score']:.1f}**.

## Repository contents

| Path | Purpose |
|:--|:--|
| `artifacts/FPL_League_Manager_Scout_2026-08-20.xlsx` | Filterable workbook with dashboard, rankings, memberships, 17k season rows and methodology |
| `data/full_scout_data.json` | Complete canonical API-derived research dataset |
| `data/league_entries.json` | League metadata and all membership rows |
| `data/scout_report.csv` | One row per unique manager |
| `data/season_history.csv` | One row per manager-season |
| `reports/FINDINGS.md` | Full cross-league findings and methodology |
| `reports/TIER_BREAKDOWN.md` | Tier distribution overall and by league |
| `reports/ELITE_MANAGERS.md` | Complete tier S list |
| `reports/SHARP_MANAGERS.md` | Complete tier A list |
| `reports/COMPETITIVE_STRATEGY.md` | Actionable monitoring strategy |
| `scripts/scout_fpl_leagues.py` | Re-runnable public FPL API collector |

## Scoring

`40% recent-weighted percentile + 25% best finish + 20% top-10% consistency + 10% experience + 5% momentum`

See [`reports/FINDINGS.md`](reports/FINDINGS.md) for definitions, top threats and limitations.

## Important limitation

This is a **pre-GW1** snapshot. Current standings, picks, captaincy and transfer behaviour were unavailable. Re-run the collector after deadlines and blend live evidence into the preseason prior.
"""
    (repo / "README.md").write_text(readme, encoding="utf-8")


if __name__ == "__main__":
    main()
