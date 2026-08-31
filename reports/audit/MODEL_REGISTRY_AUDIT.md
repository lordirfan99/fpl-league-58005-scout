# Model Registry Audit

Audit timestamp: 2026-08-31 (Asia/Kuala_Lumpur)  
Repository commit inspected: `b86797a2273b141516315c28da4b8614b6a4927f`  
Runtime targets: Netlify dashboard, Cloud Run read API, Compute Engine autopilot bridge

## Verified model lanes

| Lane | Model identity | Purpose | Status | Source of truth | Promotion eligibility |
|---|---|---|---|---|---|
| Production competitive decision support | `competitive-v4.0` | Combines FPL `ep_next`, fixture difficulty, current form/PPG and elite cohort signals into transfer, captain and competitive-context outputs | PRODUCTION | `services/api/app/recommendations.py`; `services/api/app/main.py` | Already production; execution still requires Telegram authority |
| Production horizon optimizer | V4.1, identity not returned by the read API | Multi-GW planning inside the external VM autopilot | PRODUCTION SUPPORT, NOT REPRODUCIBLE FROM THIS REPOSITORY | Runtime plan/bridge payload and project documentation only | N/A; implementation source is not present in this repository |
| Active immutable shadow | `competitive-v4.2-shadow` | Non-executable challenger team sheet, projections and optimizer evidence | SHADOW | Runtime VM artifact exposed read-only by `integration/gcp-bot/dashboard_bridge.py` | Yes in principle, but runtime reports `awaiting_eligibility`, 0 evaluated GWs and 0 paired rows |
| Research player projection | `projection-v5.0-lab` | Ownership-independent full-player football projection laboratory | RESEARCH | `services/api/app/projections.py`, `projection_types.py`, `scoring.py`, `transfer_optimizer.py` | No; must not replace V4.2 or production |
| Legacy read surface | V3 shadow artifacts (`v3_shadow_gw*.json`) | Older experimental projections/plans exposed by the bridge | LEGACY/RESEARCH | `integration/gcp-bot/dashboard_bridge.py`; `/shadow-v3` UI | No verified promotion path |

## Runtime verification

Production API evidence collected from `https://fpl-scout-api-bztsnhv3ea-uc.a.run.app`:

- `/health`: `competitive_model=competitive-v4.0`, writes disabled.
- `/v1/autopilot/control-centre`: bridge `2.1.0`, production dashboard and plan model `competitive-v4.0`, Telegram execution authority, dashboard writes disabled.
- The current plan targets GW3 but is `rejected`; it is not executable.
- `model_candidate.version=competitive-v4.2-shadow`, status `awaiting_eligibility`, evaluated GWs `[]`, paired rows `0`, owner approval false.
- `shadow_v42.artifact_type=non_executable_shadow`, GW2, champion `competitive-v4.0`, generated before the recorded GW2 deadline.
- `/v1/projections/current`: `projection-v5.0-lab`, target GW3, 626 player rows.
- `/v1/decision/current?league_id=58005&gw=2`: `competitive-v4.0`, `safe_hold`, non-executable.

## Model definitions and features

### `competitive-v4.0`

- Source: `services/api/app/recommendations.py`.
- Target: competitive decision ranking, not a pure football outcome target.
- Inputs: official FPL `ep_next`, FDR-derived fixture component, form, points per game, elite ownership/captaincy, availability and league state.
- Gameweek-dependent weights:
  - GW1-2: elite 0.45, projection 0.45, current evidence 0.10.
  - GW3-4: elite 0.40, projection 0.45, current evidence 0.15.
  - GW5-8: elite 0.30, projection 0.45, current evidence 0.25.
  - GW9+: elite 0.25, projection 0.45, current evidence 0.30.
- Competitive phases: CATCH, MATCH, ATTACK, CHASE. CHASE begins no earlier than GW28 and requires a leader gap of at least `max(40, remaining_gameweeks * 5)`.
- Known limitation: the returned `captains` list is ranked by the mixed competitive score. The pure-football and strategic captain questions are therefore not fully separated in this production response.
- Calibration/training data: no fitted training dataset is present; weights are deterministic policy constants tested for application, not statistically calibrated model parameters.

### `competitive-v4.2-shadow`

- Repository contains only the bridge serializer, not the generator/optimizer implementation.
- Runtime artifact contains component xPts, expected minutes, start probability, floor/upside/variance, horizon projections, optimizer status and legal lineup output.
- Runtime evaluation state reports no finalized paired evidence despite an artifact containing `history_rows=610`; these are not equivalent measures and must not be conflated.
- Feature version, data version and immutable artifact hash are not exposed by the bridge.

## Post-fix governance verification (2026-08-31)

- Existing champion remains `competitive-v4.0`; its current GW3 plan is rejected/read-only, not silently executable.
- V4.2 remains `competitive-v4.2-shadow` with `artifact_type=non_executable_shadow`, champion reference `competitive-v4.0`, GW2, and optimizer status `Optimal`.
- V4.2 was generated at 2026-08-28 16:05 UTC, before the recorded 17:30 UTC deadline.
- Bridge 2.1.0 still reports `execution_authority=telegram` and `writes_enabled=false`.
- No file under `integration/` and no frozen GW1 snapshot/journal artifact changed in this audit.
- Five frozen artifacts verify against the new SHA-256 manifest.
- V5 code changed only inside the existing `projection-v5.0-lab` lane. Its API/UI explicitly says heuristic uncertainty and LAB/RESEARCH; no promotion flag, Telegram route or production model constant changed.

The audit therefore preserves champion/shadow/lab separation. V4.2 remains SHADOW and V5 remains RESEARCH because statistical promotion evidence is insufficient.
- Promotion is blocked by live-GW, rows, coverage, minutes-Brier, bias, rank, decision-MAE and policy-safety gates.

### `projection-v5.0-lab`

- Source: `services/api/app/projections.py` and scoring primitives.
- Prediction target: expected FPL points for the full official player catalogue.
- Football features: expected minutes heuristic, xG/90, xA/90, FDR-derived fixture multiplier, xGC/90, saves/90, defensive contribution, historical bonus/minute and availability.
- Explicitly excludes league ownership, captaincy, rank and mini-league state.
- Expected-minutes model: deterministic start-rate heuristic based on starts, appearances and minutes; sparse-data fallback 0.82 for available players.
- Clean-sheet model: heuristic formula, not empirically calibrated.
- `p10/p50/p90`: deterministic mean plus/minus a fixed spread; these are not validated probabilistic quantiles.
- `p_10_plus`: linear heuristic, not calibrated probability.
- Fixture model: first matching fixture only; this does not correctly aggregate DGWs and treats missing fixtures with a 0.90 fallback rather than a true BGW zero-fixture projection.
- Calibration/training data: none in repository.
- Promotion status: RESEARCH. Statistical promotion evidence is insufficient.

## Required prediction metadata audit

The master specification requires every frozen prediction to carry model version, prediction timestamp, target GW, data cutoff, feature version and data version.

| Field | V4 production plan | V4.2 bridge artifact | V5 API |
|---|---|---|---|
| model version | Present | Present | Present at response level |
| prediction timestamp | `generated_at` present | `generated_at` present | Response generation time only |
| target Gameweek | Present | Present | Present |
| data cutoff | Not consistently explicit | Deadline present, cutoff not explicit | Missing |
| feature version | Missing | Missing | Missing |
| data version/hash | Partial source manifest only | Missing | Missing |

Governance verdict: **AMBER**. Lane identities are separated and V5 has no execution authority, but metadata completeness and reproducibility are insufficient, and the active V4.2 generator is outside the audited repository.
