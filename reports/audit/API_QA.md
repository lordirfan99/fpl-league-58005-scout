# API QA

Audit date: 2026-08-31

## Automated result

The clean audit environment and the post-fix local rerun both completed **50/50 API tests**. Coverage includes the endpoint contract matrix, schema validation, journal tamper detection, frozen artifacts, BGW/DGW projection shapes, expected minutes, 2026 scoring, transfer constraints, backtest refusal rules and 1,000 randomized squad mutations.

## Contract matrix

| Contract | Expected behavior | Result |
|---|---|---|
| Health and identity | Read service and configured manager are available | PASS |
| Current catalog/fixtures | Official cache exposed with freshness and quality metadata | PASS |
| Final league GW | Structurally valid final snapshot is returned | PASS |
| Provisional league GW | HTTP 409 `snapshot_not_finalized`, never malformed data or HTTP 500 | PASS |
| Live team | Explicitly provisional official-FPL live view | PASS |
| V5 projection | Lab namespace, target GW, input freshness and uncalibrated uncertainty status | PASS |
| Recommendation/decision | Production model identity preserved; decision remains non-executable/read-only | PASS |
| Journal detail/index | Content and index hashes verified on read; corruption returns HTTP 409 | PASS |
| Autopilot bridge | Telegram authority and dashboard writes disabled | PASS |

## Residual API risks

- `/health` does not expose runtime Git revision, dependency readiness or full data-age diagnostics (AUD-009).
- The league response is approximately 7.39 MB for GW1; summary/pagination contracts are needed (AUD-008).
- The API cannot independently reproduce the external V4.1/V4.2 optimizer implementation from this repository (AUD-010).
- A shared cutoff/data/feature provenance envelope is not yet present on every model family (AUD-011).

## Verdict

No known P0/P1 API defect remains. Contract correctness is **PASS**; observability, payload size and external optimizer reproducibility remain P2.
