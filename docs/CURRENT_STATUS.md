# FPL Scout Control Centre — current status

**Status date:** 1 September 2026

**Branch:** `master`

**Frontend code revision:** `017dd0c333a5381881383628b46e12a6535f25f0`

**API revision:** `ea65bfa33a7b41d898a1e6910d756ff6a7e3ca4e`

## Production services

| Service | URL | Verified state |
|---|---|---|
| Dashboard | https://fpl-scout-intelligence.netlify.app | Netlify serves the `017dd0c` UI; all 17 dashboard routes were rechecked on desktop and a 393 px phone viewport |
| Read API | https://fpl-scout-api-bztsnhv3ea-uc.a.run.app | `/ready` is true and exposes the exact Git revision |
| Autopilot bridge | https://sportmania.duckdns.org/fpl-autopilot/ | Read-only; Telegram remains execution authority |

## Actual official data, finalized history and planning

- Current player, team, event and fixture data is fetched from the official FPL `bootstrap-static` and `fixtures` APIs. The hourly publisher rejects payloads with the wrong shape, fewer than 400 players, anything other than 20 teams/38 events/four positions, fewer than 300 fixtures, invalid team IDs or placeholder difficulty values.
- Each accepted official payload carries its real fetch time, source URL and SHA-256 content identity. A failed validation publishes nothing; the dashboard keeps the previous verified cache.
- Live personal-team state comes from the official FPL API through the server-side `/v1/live/team` reader. The response includes the current 15 picks, calculated provisional GW points from official event totals and multipliers, official total points/overall rank, and the selected classic-league rank.
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

- My Team prioritizes the official live feed over the older Autopilot artifact for squad, score, total, overall rank, league rank and update timestamp. In-progress values are labelled provisional; they are no longer hidden behind `Pending` placeholders.
- Public league `131997` no longer fails on Transfers when the configured personal team is not a member. League transfer/chip/elite evidence remains available, while only the personalized NET-EV optimizer becomes unavailable with an explanatory link back to league `58005`.
- Internal chip identifiers are translated for users (`bboost` → `Bench Boost`, `3xc` → `Triple Captain`, `freehit` → `Free Hit`). Counts remain those captured in the finalized league snapshot.
- Mobile decision evidence uses compact Plan/Run fields, readable uncertainty copy and `LINEUP SAFE` instead of the overflowing `LINEUP_ONLY_SAFE` identifier.
- Netlify's injected badge is hidden below 720 px so it cannot cover the five-item mobile navigation.
- League standings are server-paginated and searchable; only 50 compact rows are sent at a time.
- Manager comparison uses a compact directory and loads only the two selected full squads.
- A single lineup is loaded on demand from the league table.
- Transfers include a read-only `net-ev-multiweek-v1` research table. It evaluates legal 1–3 transfer plans across 2–6 GWs with hit cost, saved-transfer opportunity value, budget, three-per-club, uncertainty and supported chip modes.
- `api-meta-v2` exposes data version/hash, cutoff, feature/model version and code revision.
- External V4.2 bridge artifacts are SHA-256 identified in new captures. The generator source remains external and is labelled honestly.

## Data meaning by dashboard area

| Area | Freshness/source | Expected behavior |
|---|---|---|
| My Team | Official mutable FPL entry/picks feed, read on page request | Shows the current live GW squad and provisional numeric score/ranks. Values may change until FPL finalises the event. |
| Assistant / Autopilot / Planner | Latest persisted decision artifact plus current official deadline/catalog | Targets the next deadline. A source gate can place the plan in safe/read-only mode; the UI must not invent a transfer. |
| League / Elite / Transfers / Analytics | Latest complete immutable league snapshot | Remains on GW1 while GW2 is unfinished or not data-checked. This is deliberate historical integrity, not a failed refresh. |
| Players / V5 Lab | Hourly verified official bootstrap/fixture cache plus clearly labelled derived projections | Official identity, price, availability and fixtures; model xPts/ranges remain research rather than official outcomes. |
| Journal | Immutable completed-GW records plus frozen pre-deadline evidence | A week is archived only after final data is available; future weeks remain planned/pending without fabricated results. |
| Model Compare | Persisted production/shadow/lab artifacts only | A lane says unavailable when its real artifact does not exist. No placeholder XI is synthesized. |

## Verification evidence

- API tests: **64 passed**, including live-score/league-rank derivation, one valid official-source case and five rejection cases for incomplete/placeholder-like payloads.
- Next.js typecheck, production build and dependency audit: **passed**.
- Local browser checks: **26 passed, 2 intentional project-specific skips** across desktop and Pixel-sized projects. The suite includes every dashboard tab, My Team live-value assertions, public-league Transfers fallback, navigation, artwork and accessibility.
- Production route audit: **17/17 routes passed** at desktop and 393 px widths, with no route error and no page-level horizontal overflow. A clean production tab recorded no console errors.
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

## Release trail

| Commit | Deployment | Evidence |
|---|---|---|
| `ea65bfa` | Cloud Run API and initial Netlify UI | Official live score/rank contract, optional public-league optimizer, responsive evidence blocks; Cloud Run `/health` reports the exact SHA. |
| `017dd0c` | Final Netlify UI | Human-readable chip names and hidden mobile Netlify badge; final GitHub validation run `33472272135` succeeded. |
