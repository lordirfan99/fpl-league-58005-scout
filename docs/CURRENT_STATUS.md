# FPL Scout Control Centre — current status

**Status date:** 30 August 2026  
**Branch:** `master`  
**Latest commit:** `6d75594 feat: add live FPL team polling with snapshot fallback`

## Production URLs

| Service | URL | Current verification |
|---|---|---|
| Dashboard | https://fpl-scout-intelligence.netlify.app | Live Netlify production deployment; `/my-team`, `/journal` and `/settings` return HTTP 200 |
| Read API | https://fpl-scout-api-bztsnhv3ea-uc.a.run.app | Cloud Run health returns HTTP 200 and `version=4.0.0` |
| Autopilot bridge | https://sportmania.duckdns.org/fpl-autopilot/ | Read-only bridge used for plan context; execution remains Telegram-only |

## What is live now

The dashboard uses a hybrid data model:

1. **Live FPL feed** — the API server polls the official FPL API for the configured team. Results are cached for 15–30 seconds and exposed through `GET /v1/live/team`.
2. **League snapshots** — completed-gameweek league standings, competitor squads and analysis remain snapshot-backed. This prevents mutable live data from rewriting research history.
3. **Journal archive** — a Gameweek is archived only after FPL reports `finished=true` and `data_checked=true`. Journal records include provenance, quality checks, prediction evidence and a content hash.
4. **Fallback** — if FPL is unavailable, the dashboard uses the newest valid captured snapshot and labels it as historical/stale instead of pretending it is live.

The live endpoint currently reports:

- source: `official-fpl-live`
- status: `live`
- current Gameweek: `GW2`
- squad rows: `15`
- provisional: `true` until FPL finalises the Gameweek

## Current data state

- **GW1:** captured and available as the completed league/journal baseline.
- **GW2:** the personal 15-player team is available from the live FPL feed.
- **GW2 league snapshot:** not yet available in the read API, so league rank, elite behaviour and completed-GW comparisons correctly remain on the last captured snapshot until the collector runs after lock.
- **Next planning target:** derived from the latest completed review and the next FPL deadline; it must not be confused with a completed-GW result.

## Dashboard behaviour

- **My Team** prefers the live team feed and displays provisional points/rank language while GW2 is in progress.
- **League, Elite, Transfers and Analytics** use a selected, captured Gameweek so comparisons remain internally consistent.
- **Journal** shows all 38 Gameweeks, with completed, live and upcoming states separated.
- **Settings** stores local display preferences (league, timezone, landing page, reminders and compact tables).
- **Season weeks** navigation links directly to the journal review for any GW1–GW38.

## Automation and deployment

- Netlify deploys `web-next` from `master`.
- GitHub Actions workflow `deploy-api.yml` builds and deploys the read API to Cloud Run.
- GitHub Actions workflow `refresh-gameweek.yml` checks every four hours for a newly finished/data-checked Gameweek, collects both tracked leagues, validates the payload and commits snapshots atomically.
- The live FPL reader is server-side only; the browser never calls the official FPL API directly.
- No dashboard endpoint can write transfers, captains or lineups. Telegram remains the execution authority.

## Verification performed for commit `6d75594`

- API test suite: **25 passed**.
- Next.js typecheck: **passed**.
- Next.js production build: **passed**.
- Cloud Run deployment workflow: **passed**, including production API verification.
- `GET /health`: HTTP 200.
- `GET /v1/live/team`: HTTP 200 with 15 live picks for GW2.
- `GET /v1/leagues/58005?gw=1`: HTTP 200.
- `GET /v1/leagues/58005?gw=2`: currently unavailable because the GW2 league snapshot has not been collected yet; this is expected during the live/provisional phase.

## Known limitations and next operational steps

1. The live endpoint currently covers the configured personal team. Live league-wide polling is intentionally not enabled because it would require paginating the league and fetching hundreds of manager squads, creating avoidable load and inconsistent mid-gameweek comparisons.
2. After GW2 is locked and data-checked, run or allow `refresh-gameweek.yml` to publish the GW2 snapshots and journal record.
3. Confirm the next refresh with `/v1/leagues/58005?gw=2`, `/v1/journal?season=2026-27` and the dashboard's Journal page.
4. Keep the live layer for current decisions and the snapshot layer for auditability; do not merge provisional live rows into the historical journal.

