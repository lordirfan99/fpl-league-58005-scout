# Production Reproduction Evidence

Observed 2026-08-31 from the production Netlify and Cloud Run URLs. These measurements are single-request smoke observations, not load-test percentiles.

## Dashboard route reproduction

All discovered critical routes returned HTTP 200:

| Route group | Result | Observed concern |
|---|---|---|
| `/`, `/my-team`, `/players`, `/transfers`, `/planner`, `/analytics` | 200 | Server response times ranged roughly 1.1-5.3 seconds in this run |
| `/model-compare`, `/v5-lab`, `/journal`, `/journal/2026-27/gw/1` | 200 | V5 response was approximately 447 KB |
| `/assistant`, `/settings`, `/autopilot`, `/shadow-v3` | 200 | No HTTP-level failure |
| `/league`, `/compare` | 200 | Each HTML response was approximately 10.26 MB; the full league dataset is being serialized into the page |
| `/elite` | 200 | HTML response was approximately 2.46 MB |

HTTP 200 does not establish absence of console, hydration, accessibility or interaction failures. Those remain frontend/E2E audit items.

## API reproduction

| Endpoint | Result | Observed size/time | Interpretation |
|---|---:|---:|---|
| `/health` | 200 | 188 B / 405 ms | Process and model identity available; no dependency readiness or commit SHA |
| `/v1/me` | 200 | 66 B / 314 ms | Configured identity available |
| `/v1/live/team` | 200 | 2.5 KB / 698 ms | GW2, 15-player official-FPL live team, provisional |
| `/v1/catalog` | 200 | 1.65 MB / 1.8 s | Full bootstrap payload is large |
| `/v1/fixtures?from_gw=2&to_gw=6` | 200 | 6.9 KB / 461 ms | Horizon available |
| `/v1/leagues/58005?gw=1` | 200 | 7.39 MB / 3.1 s | Latest finalized league available but response is very large |
| `/v1/leagues/58005?gw=2` | 409 | 149 B / 295 ms | Correct explicit `snapshot_not_finalized`; no HTTP 500 |
| `/v1/elite/1?league_id=58005` | 200 | 384 KB / 1.2 s | Final GW1 cohort available |
| `/v1/recommendations/current?league_id=58005&gw=1` | 200 | 25 KB / 478 ms | Production competitive model output available |
| `/v1/projections/current` | 200 | 333 KB / 1.2 s | 626-player V5 lab output for GW3 |
| `/v1/journal?season=2026-27` | 200 | 558 B / 305 ms | GW1 final archive and season index available |
| `/v1/decision/current?league_id=58005&gw=2` | 200 | 19 KB / 473 ms | Non-executable safe-hold decision packet |
| `/v1/autopilot/control-centre` | 200 | 31 KB / 377 ms | Read-only plan/shadow bridge available |

## Provenance and deployment identity

- Runtime model identities are exposed.
- Runtime commit SHA/image digest is not exposed by `/health` or a version endpoint, so production cannot be proven to serve a particular Git commit using the public contract alone.
- `/health` does not report latest final GW, data age, model registry or dependency readiness.
- Netlify route responses prove availability, not the exact deployed SHA.

## Reproduction verdict

Production is reproducible at the HTTP contract level and the live/final mismatch is explicit. Exact build provenance, browser runtime correctness, load behaviour and dependency readiness are not yet proven.

## Post-deployment smoke addendum

The deployed hardening revision was rechecked after the initial baseline:

- Cloud Run workflow smoke passed with `competitive-v4.0`, valid recommendation quality, Telegram authority and dashboard writes disabled.
- Live V5 rows expose `heuristic_not_calibrated` and range labels; the production endpoint retains 626 current players because the GCS catalogue was newer in roster membership but lacked provenance.
- That GCS/local selection issue was reproduced and fixed so reference caches select the newest timestamped, proven source; a regression test covers proven-local versus newer-proven-remote selection.
- The real Netlify suite first passed 16 flows with one intentional desktop skip and exposed the injected badge/early-hydration mobile issue. After the permanent fix, the final deployed mobile rerun passed; all 17 applicable production flows therefore have passing evidence.

