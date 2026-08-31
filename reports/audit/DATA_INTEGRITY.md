# Data Integrity Audit

Audit date: 2026-08-31

## Verified evidence

### Final league snapshots

| File family | GW | Rows / declared | Structural quality | Duplicate entry IDs |
|---|---:|---:|---|---:|
| League 58005 full | 1 | 1,218 / 1,218 | valid | 0 |
| League 131997 full | 1 | 1,782 / 1,782 | valid | 0 |

Every full snapshot manager passes the current squad-size, position-shape, XI-formation, captain/vice and hydration checks. Full and compact files contain the same entry-ID sets. The compact rows normalize missing `transfers_made` to zero; their capture timestamps differ from their matching full files by 2–3 seconds.

This structural pass does **not** prove immutability. Git history shows the finalized GW1 league files were replaced repeatedly with very large diffs after the result was final. The current workflow avoids an automatic rerun when all expected files exist, but the collectors and manual override path still overwrite the canonical filename and have no previous-manifest check. This is release-blocking AUD-012.

### Official catalogue and fixtures

- Local bootstrap contains 623 players, 20 teams and 38 events.
- GW1 is `finished=true` and `data_checked=true`; GW2 is current and provisional; GW3 is next.
- Fixture cache contains GW1–GW38 and ten fixtures per ordinary gameweek at the current capture.
- Fixture cache has `fetched_at=2026-08-31T09:44:23.086935+00:00`.
- Bootstrap has no `fetched_at`, source hash or cutoff. Production reproduction returned 626 players, so local and deployed catalogues are not demonstrably the same data revision.

Consequently fixture coverage passes for the current schedule, while bootstrap freshness/provenance is **INSUFFICIENT EVIDENCE**.

### Journal and prediction freezing

| Check | Result |
|---|---|
| GW1 public record SHA-256 recomputation | PASS |
| GW1 index hash equals record hash | PASS |
| GW2 pre-deadline `input_hash` recomputation | PASS |
| GW2 capture precedes deadline | PASS; 2026-08-28 16:08 UTC vs 17:30 UTC |
| GW2 decision target | PASS; GW2 |
| GW2 V5 target/version | PASS; GW2 / `projection-v5.0-lab` |
| Paired V5/FPL rows in GW2 capture | 620 / 620 |
| GW1 deadline evidence | Missing; journal correctly reports `partial` |

The cloud capture path uses GCS generation-match creation and the local path refuses replacement, which protects the pre-deadline input bundle. However, public journal generation currently overwrites `gwNN.json` when rerun, and the horizon updater intentionally mutates old records and replaces their hashes. That conflicts with the UI/documentation claim of immutable records. Read-time API hash verification is also absent. These controls must be corrected before the archive can be called immutable end to end.

### Live/final/stale separation

The API correctly keeps `/v1/live/team` separate from finalized league snapshots, and `/v1/leagues/58005?gw=2` returns an explicit `409 snapshot_not_finalized`. The frontend then weakens this contract: its league loader catches all failures and silently searches backward until a snapshot succeeds. A GW2 request can therefore return GW1 without carrying `requested_gameweek=2` or the reason for fallback. This is release-blocking AUD-013.

## Temporal leakage assessment

- GW2 frozen decision/V5/FPL bundles were captured before the official deadline and their hash is valid.
- GW1 has no frozen prediction bundle, so it cannot be used to assess V5 or production prediction accuracy without leakage risk.
- The repository contains only one finalized journal week. There is no multi-week walk-forward sample.
- Current bootstrap data must not be joined retrospectively to GW1 as if it were GW1 pre-deadline data.

No leakage was found in the one verifiable GW2 capture. Absence of leakage across the season is **INSUFFICIENT EVIDENCE**, not a pass.

## Integrity gate result

| Gate | Result |
|---|---|
| Current full-snapshot structural validity | PASS |
| Full/compact ID consistency | PASS |
| Fixture GW1–GW38 presence | PASS for current ordinary schedule |
| Frozen pre-deadline GW2 hash/cutoff | PASS |
| Frozen GW1 prediction evidence | FAIL / missing |
| Final snapshot immutability | FAIL |
| Public journal immutability enforcement | FAIL |
| Bootstrap freshness and deployed data identity | FAIL / insufficient provenance |
| Explicit frontend stale/mismatch state | FAIL |

Step 5 therefore does not pass as a critical release gate. Production execution remains protected by Telegram authority and safe-hold logic, but historical integrity and frontend freshness controls require permanent fixes and regression tests.

## Post-remediation gate rerun

The initial failures above are retained as audit evidence. After remediation:

| Initial failure | Permanent control and rerun result |
|---|---|
| Final snapshot immutability | Writers refuse overwrite by default; explicit corrections require a reason; five finalized artifacts are CI-manifested — PASS |
| Journal immutability | Identical rerun is idempotent, changed content is rejected, detail/index hashes are verified on read, tamper tests pass — PASS |
| Bootstrap provenance | Official refresh now records source, capture time and content SHA-256; API selects the freshest proven local/GCS reference — PASS after live redeploy verification |
| Frontend mismatch | Only 404/409 can select an archive fallback; requested and returned GWs/reason are visible; browser regression passes — PASS |
| Frozen GW1 prediction | Still missing — INSUFFICIENT EVIDENCE for model scoring, not an engineering publication defect |

The corrected Step 5 engineering integrity gate is **PASS**, while historical model-performance evidence remains insufficient and blocks model promotion.

