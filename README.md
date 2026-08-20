# FPL Four-League Manager Scout — 2026/27

Pre-season competitive intelligence for FPL leagues **19292, 58005, 687126 and 131997**, collected from the public Fantasy Premier League API on 20 August 2026.

## Snapshot

- 3,362 memberships
- 2,887 unique managers
- 2,691 managers with history
- 17,206 historical season records
- 385 tier S/A threats
- zero failed profiles

## Core finding

**Na Fantasy League has the strongest historical field**, while **Mapei Quick Step — Faris Zain** leads the combined scout ranking with a score of **93.9**.

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
