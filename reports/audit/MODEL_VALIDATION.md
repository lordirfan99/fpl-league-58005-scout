# Model Mathematics and Validation Audit

Audit date: 2026-08-31

## Executive model status

| Lane | Software role | Mathematics verdict | Statistical readiness |
|---|---|---|---|
| `competitive-v4.0` | Production competitive ranking / decision support | Deterministic and bounded, but mixes football estimates with league popularity and does not form a pure forecast | PRODUCTION as the existing champion only; accuracy evidence is insufficient |
| `competitive-v4.2-shadow` | Non-executable challenger | Runtime artifact reports an optimal legal team sheet, but generator/optimizer source is absent here | SHADOW; 0 evaluated GWs and 0 paired rows |
| `projection-v5.0-lab` | Ownership-independent player projection research | Deterministic and bounded, but verified BGW, DGW and clean-sheet defects exist; uncertainty is heuristic | RESEARCH; not a promotion candidate |

## V5 scoring mathematics

### Checks that pass

- Goal and clean-sheet position point constants are explicit.
- Poisson tail helpers are bounded in `[0,1]`.
- Defensive-contribution thresholds are modeled as event probabilities rather than a linear partial award.
- Goalkeeper saves and goals-conceded deductions use expected completed scoring buckets.
- All 623 local player rows have ordered range values and bounded `p_return`/`p_10_plus`.
- Expected minutes, xPts and probability outputs are numerically bounded; unavailable players produce zero minutes.
- Ownership, elite captaincy and league rank are absent from the V5 projection module and response rows.

### Verified mathematical failures

1. **DGW omission (AUD-001).** `fixture_multiplier` returns on the first match. A synthetic two-fixture week produces exactly the same xPts as its first fixture alone.
2. **BGW non-zero output (AUD-002).** A player with no fixture receives a 0.90 fallback and 2.59 synthetic xPts in the audit case.
3. **Reversed clean-sheet difficulty (AUD-015).** For the same 90-minute defender, FDR1 produces a 0.752 clean-sheet component and FDR5 produces 0.917. The result moves in the wrong direction.
4. **Uncalibrated range labels (AUD-003).** `p10=mean-spread`, `p50=mean`, and `p90=mean+spread`, where `spread=max(1.5, 0.65*mean)`. These are not empirical quantiles.
5. **Heuristic event probabilities.** `p_10_plus=clamp((mean-5)/10)` is not a probability fitted to 10+ outcomes. Clean-sheet and 60+ probabilities have no reliability evaluation.
6. **Appearance approximation.** Appearance points infer appearance probability from `expected_minutes/15`, even though the minutes object already separates start and bench-appearance probabilities. This is bounded but not independently validated.

For GW3 local inputs, only 281/623 rows have no quality issue; 342 rows report missing attack evidence. This is transparent but also shows the current catalogue is far from a complete predictive feature set.

## Expected minutes

The implementation combines availability, historical starts/appearances, average minutes when starting and a fixed 22-minute bench appearance. Existing tests prove bounds and zero output for unavailable players. There is no paired pre-deadline expected-minutes versus actual-minutes dataset in the finalized local journal, so minutes MAE, start Brier score and 60+ calibration are **N/A / INSUFFICIENT EVIDENCE**.

Expected minutes are therefore a heuristic input, not a validated submodel.

## Transfer mathematics

The isolated V5 helper correctly subtracts four points when a tested single transfer exceeds free transfers and checks same position, simple bank affordability and the three-per-club limit. It does not implement multi-transfer combinations, selling price, rolling free transfers, Wildcard/Free Hit semantics, multi-GW opportunity value or captain/bench interaction.

The production shortlist explicitly labels its number `next_gameweek_gross; transfer cost and hits excluded`, but it does not check bank or club limits. Current GW1 output includes examples such as Strand Larsen (£6.0m) to Haaland (£15.5m), demonstrating that the shortlist is not a legal or NET-EV transfer optimizer. The browser draft further displays only incoming `ep_next`, not incoming minus outgoing. Q10 answer: **No, the complete surfaced transfer system does not calculate NET EV.**

## Captain mathematics

- V5 `captain_rankings` is a pure football ordering by xPts then `p_10_plus` and is not connected to execution.
- Production `captains` are ordered by the competitive score, which includes elite ownership/captaincy. In the reproduced local packet, Bruno Fernandes (8.5 xPts) ranks above Tarkowski (9.0 xPts) because the score is not xPts-only.
- No walk-forward captain evaluation against simple highest-`ep_next`, highest-V5 and realized-oracle baselines exists.

Q11 answer: captain outperformance is **INSUFFICIENT EVIDENCE**. The competitive ordering is intentional strategy, but the UI/API must not describe it as a calibrated football forecast.

## Lineup and optimizer rules

Snapshot validation correctly checks 2/5/5/3 squad shape, a legal XI formation, exactly one captain and vice, and Bench Boost scoring count. The V5 browser comparison enumerates the eight legal outfield formations and selects one goalkeeper from the existing 15-player live squad. It is a lineup selector, not a transfer optimizer.

No reproducible V4.1/V4.2 optimizer implementation is present, so budget, club, chip, transfer and property-based legality claims for that runtime cannot be independently tested here. Runtime `optimizer_status=Optimal` is evidence of one output, not a proof over all inputs.

## Model scorecard (available evidence only)

| Model | MAE | RMSE | Spearman | Brier | Minutes MAE | n |
|---|---:|---:|---:|---:|---:|---:|
| FPL `ep_next` | N/A | N/A | N/A | N/A | N/A | 0 finalized paired pre-deadline rows |
| Production V4.0 | N/A | N/A | N/A | N/A | N/A | 0 |
| V4.2 | N/A | N/A | N/A | N/A | N/A | 0 |
| V5 | N/A | N/A | N/A | N/A | N/A | 0 |

Position and gameweek breakdowns are N/A because no finalized, deadline-safe paired predictions exist locally. GW1 cannot be reconstructed from the current bootstrap without temporal leakage; GW2 is not yet finalized.

## Reproducible backtest framework

`scripts/audit_model_backtest.py` now pairs only a hash-valid pre-deadline bundle with a hash-valid finalized journal outcome. It rejects capture-at/after-deadline evidence, joins exclusively by official element ID, never imputes a missing player from a newer bootstrap, and reports:

- MAE, RMSE, bias and tie-aware Spearman rank correlation;
- top-K realized mean;
- per-gameweek and per-position breakdowns;
- Brier score and reliability bins for any available start, 60+ and 10+ probabilities;
- an explicit `insufficient_evidence` status when no safe pairs exist.

The public journal currently stores actual outcomes for the personal 15-player squad, so this first framework scope is deliberately named `personal_squad`. Full-universe evaluation requires immutable full event outcomes in the private evidence store.

The 2026-08-31 run found GW1 final outcomes but no GW1 frozen prediction and therefore returned `n=0` and `insufficient_evidence` for both V5 and FPL `ep_next`. That is the correct result. Joining the current catalogue to GW1 would leak future data.

## Step 6 result

The mathematics gate fails. V5 remains isolated and non-executable, limiting immediate production blast radius, but its outputs are not valid for BGWs/DGWs and its clean-sheet term is directionally wrong. Production transfer and captain outputs are competitive research signals rather than proven NET-EV/accuracy winners. Permanent tests and candidate fixes are required before any readiness claim.
