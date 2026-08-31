# Release Readiness

Audit date: 2026-08-31

## Classification

| Scope | Status | Confidence | Decision |
|---|---|---|---|
| Engineering hardening | GREEN | HIGH | Deployed; CI and live verification passed |
| Production `competitive-v4.0` operations | PRODUCTION | LOW for predictive accuracy; HIGH for identity/isolation | Keep champion; no accuracy claim |
| `competitive-v4.2-shadow` | SHADOW / non-executable | LOW | Continue collecting evidence; do not promote |
| `projection-v5.0-lab` | RESEARCH | LOW | Do not use as execution authority |

P0 open: **0**. P1 open: **0**. Six P2 risks/accepted limitations remain in the bug register.

## Critical questions

1. **Can stale data silently mislead?** Known 404/409 archive fallback is now explicit; unknown errors propagate. Upstream source accuracy remains an external risk.
2. **Can provisional data contaminate history?** Final publication requires checked/final data; pre-deadline evidence is separate and hashes are enforced. No path was found under the tested workflow.
3. **Is there future leakage?** The backtester refuses missing cutoff/frozen pairs. GW1 is not scored because it lacks a frozen prediction. Full-season absence of leakage remains insufficient evidence.
4. **Are expected minutes validated out of sample?** No.
5. **Are V5 ranges calibrated quantiles?** No; they are explicitly labeled heuristic ranges.
6. **Is clean-sheet probability calibrated?** No; only the prior directional defect is fixed and monotonicity tested.
7. **Does V5 beat FPL `ep_next`?** Insufficient evidence; zero finalized paired weeks.
8. **Does V5 beat the production model?** Insufficient evidence.
9. **Which positions are strongest?** Insufficient evidence.
10. **Is a complete NET-EV transfer optimizer present?** No. Current research surfaces gross single-transfer change and exclude hit/horizon value.
11. **Does captain selection outperform baselines?** Insufficient evidence.
12. **Do BGW/DGW schedules break V5?** The reproduced BGW/DGW defects are fixed and regression-tested; future unusual schedules remain a monitoring risk.
13. **Do chips break lineup logic?** Bench-boost behavior is covered; the complete lifecycle of every chip/edge case is not yet proven.
14. **Can the frontend silently show the wrong week?** The broad fallback defect is fixed; requested and returned weeks are visible.
15. **Can upstream API failure corrupt data?** Validation blocks malformed final snapshots. Availability can still degrade, but unknown errors are not converted into apparently current data.
16. **Can model changes contaminate shadow evidence?** Frozen namespaces/hashes prevent it in the tested local path. External VM build provenance remains incomplete.
17. **Does popularity contaminate forecasts?** Competitive-v4.0 uses league behavior by design; V5 projections remain a separate lab family.
18. **Which features add measurable value?** Insufficient ablation evidence.
19. **Which features hurt?** The reversed clean-sheet difficulty heuristic hurt directional validity and is fixed; broader ablation evidence is insufficient.
20. **What blocks season-long trust?** Out-of-sample accuracy/calibration, expected-minutes validation, full chip coverage, external optimizer reproducibility, payload performance and operational observability.

## Release rule

The pushed application passed GitHub CI, Cloud Run deployment smoke and the live Netlify critical-flow test. The engineering release is **GREEN and deployed**. Model readiness remains separate: no V5/V4.2 promotion is authorized by this audit.
