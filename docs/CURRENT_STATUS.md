# FPL Scout Control Centre — current status

**Status date:** 1 September 2026

**Branch:** `master`

**Dashboard revision:** `1cc801fe6e5644c2b51fdeba901c1a5579a3690b`

**API revision:** `bf1da1a56347ada0cafa44ff80d4ea6b1f4dec15`

## Production services

| Service | URL | Verified state |
|---|---|---|
| Dashboard | https://fpl-scout-intelligence.netlify.app | Netlify production deploy is `ready`; compact league UI is live |
| Read API | https://fpl-scout-api-bztsnhv3ea-uc.a.run.app | `/ready` is true and exposes the exact Git revision |
| Autopilot bridge | https://sportmania.duckdns.org/fpl-autopilot/ | Read-only; Telegram remains execution authority |

## Actual official data, finalized history and planning

- Current player, team, event and fixture data is fetched from the official FPL `bootstrap-static` and `fixtures` APIs. The hourly publisher rejects payloads with the wrong shape, fewer than 400 players, anything other than 20 teams/38 events/four positions, fewer than 300 fixtures, invalid team IDs or placeholder difficulty values.
- Each accepted official payload carries its real fetch time, source URL and SHA-256 content identity. A failed validation publishes nothing; the dashboard keeps the previous verified cache.
- Live personal-team state comes from the official FPL API through the server-side `/v1/live/team` reader.
- League research uses only the latest structurally complete, finalized snapshot. If FPL is on GW2 while GW2 league data is incomplete, an unqualified league read returns finalized GW1.
- An explicit incomplete request such as GW2 returns `409 snapshot_not_finalized`; it never silently appears as finalized data.
- Derived xPts and NET-EV are labelled model research, not official results. No placeholder score is substituted for missing official data.
- Finalized league and journal records remain immutable and hash-verified. Hourly refreshes cannot overwrite them.

## Hourly freshness automation

All schedules run every day, including weekends:

| Minute | Workflow | Purpose |
|---:|---|---|
| `:17` hourly | `refresh-fixtures.yml` | Validate official FPL bootstrap/fixtures and publish verified live caches directly to GCS |
| `:23` hourly | `refresh-gameweek.yml` | Detect a newly finished and data-checked GW, then atomically publish league snapshots, journal and model-validation report |
| `:17` hourly | `capture-journal.yml` | Freeze pre-deadline decision/model/optimizer evidence inside the configured deadline window |
| Every 30 minutes | `monitor-production.yml` | Check readiness, compact contracts, payload budgets and bounded p50/p95 latency |

GitHub schedules can start a few minutes late under platform load. The refresh logic is idempotent: incomplete weeks remain provisional and finalized evidence is never reconstructed later.

## Dashboard and API changes now live

- League standings are server-paginated and searchable; only 50 compact rows are sent at a time.
- Manager comparison uses a compact directory and loads only the two selected full squads.
- A single lineup is loaded on demand from the league table.
- Transfers include a read-only `net-ev-multiweek-v1` research table. It evaluates legal 1–3 transfer plans across 2–6 GWs with hit cost, saved-transfer opportunity value, budget, three-per-club, uncertainty and supported chip modes.
- `api-meta-v2` exposes data version/hash, cutoff, feature/model version and code revision.
- External V4.2 bridge artifacts are SHA-256 identified in new captures. The generator source remains external and is labelled honestly.

## Verification evidence

- API tests: **63 passed**, including one valid official-source case and five rejection cases for incomplete/placeholder-like payloads.
- Next.js typecheck, production build and dependency audit: **passed**.
- Browser checks: **19 applicable passed, 1 intentional desktop skip** on both local production build and live Netlify.
- Automated accessibility: no serious/critical WCAG 2 A/AA violations on tested critical pages.
- Frozen-artifact manifest: **5 verified**; recovery drill restored and re-verified all 5 in isolation.
- Production compact summary: **11,620 bytes**, 50 rows, no squads, stable data hash.
- Production dashboard `/league`: **143,624 bytes**, down from approximately 10.3 MB.
- Bounded production smoke: API p95 **1.38 s**; dashboard p95 **4.26 s**; zero errors in the sampled run.
- Python and npm high-severity dependency audits: **no known vulnerabilities found** at verification time.

## Honest remaining limitations

1. Model promotion evidence is still immature. GW1 has no frozen pre-deadline prediction, and at least six paired finalized weeks are required before review eligibility.
2. The external VM V4.2 generator source is not vendored here. Its outputs are immutable/hash-traceable, but independent reproduction still requires that private source.
3. Automated accessibility checks do not replace manual screen-reader and keyboard review across every browser/device combination.

These are evidence or external-source limitations, not open release-breaking engineering defects.
