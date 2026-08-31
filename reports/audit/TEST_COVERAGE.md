# Test Coverage Audit

Audit date: 2026-08-31

## Existing gates reproduced

| Gate | Command / environment | Result |
|---|---|---|
| Frontend dependency install | `npm ci`, Node/npm lockfile | PASS; 30 packages installed, 0 reported vulnerabilities |
| Frontend static types | `npm run typecheck` | PASS |
| Frontend production build | `npm run build`, Next.js 16.3.2 | PASS; all 18 application routes compiled |
| API clean install | Python 3.12 isolated virtual environment; `pip install -r services/api/requirements.txt` | PASS |
| API regression suite | `python -m pytest services/api/tests`, pinned dependencies | PASS; 32 tests in 1.92 s |
| Operational Python syntax | CI `py_compile` list for bridge and six pipeline/journal scripts | PASS |

The Pytest run emitted one cache warning because the parent workspace blocks creation of `.pytest_cache`; it did not affect collection or execution.

## Coverage map at audit start

| Surface | Existing evidence | Important missing evidence |
|---|---|---|
| API routes/contracts | FastAPI TestClient coverage for core routes, malformed snapshots and journal paths | Contract matrix for every public endpoint, response status/schema invariants, upstream outage behaviour |
| FPL rule validation | Squad shape, XI formation, captain/vice, Bench Boost cases | Property tests over many legal/illegal combinations; Triple Captain, Free Hit and Wildcard lifecycle cases |
| V5 scoring | 2026 scoring primitives and basic expected-minutes cases | DGW aggregation, BGW zero-fixture behaviour, probability calibration and numerical property tests |
| Transfer evaluator | One legal single-transfer scenario, hit subtraction, position mismatch | Multiple transfers, rolling free transfers, selling value, squad budget, chip semantics and multi-GW NET EV |
| Journal | Build/index/export happy paths and missing pre-deadline evidence | Frozen-record tamper detection, repeated-run idempotency and pre-/post-deadline leakage checks |
| Frontend | TypeScript compilation and production build only | Unit/component tests, accessibility checks, browser console checks and automated critical E2E flows |
| Deployment | Workflow build and limited post-deploy API assertions | Immutable build provenance, frontend smoke automation and dependency/readiness checks |
| Models | No historical evaluation test suite at audit start | Walk-forward scorer, strong baselines, MAE/RMSE/rank/calibration, position/GW breakdowns and promotion gates |

## Initial conclusion

The existing suite is green but is not sufficient for an engineering-ready release under the master audit criteria. In particular, a successful build is not a frontend functional test, and a one-gameweek journal entry without a frozen V5 prediction cannot establish forecasting validity.

## QA added during this audit

| New gate | Scope | Latest result |
|---|---|---|
| Artifact integrity | Full/compact IDs and shape, journal/index hashes, optional private cutoff bundle, GW1–GW38 fixture identity | PASS |
| Contract matrix | Core public API status contracts plus every single-GW fixture request from 1 through 38 | PASS |
| Rule property tests | All eight legal formations with/without Bench Boost and 1,000 seeded critical-rule mutations | PASS |
| Desktop browser E2E | My Team, Assistant, Planner, Journal, Settings, frozen GW1 drill-down, CSS and console checks | PASS |
| Mobile browser E2E | Same critical routes, frozen drill-down, primary/overflow navigation | PASS |
| Backtest mathematics | Exact error/rank/calibration cases, missing-row non-imputation, insufficient-evidence behavior | PASS |

After adding these gates and the backtest framework, the API suite is 43 tests and the Playwright suite is 13 passed / 1 intentionally skipped desktop copy of a mobile-only assertion. Chromium executes against a real Next production server. The first browser run found a device-specific selector mismatch and repeated official player-image 403s; the selector was corrected and the media reliability issue remains tracked as AUD-016.

CI now installs Chromium and runs Playwright after the production build. The new tests do not establish model accuracy; that remains the responsibility of the backtest and frozen-evidence gates.
