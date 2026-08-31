# Executive Summary

Audit date: 2026-08-31

## Outcome

The repository is engineering-ready for a guarded read-only release once the final pushed revision passes CI and live smoke verification. Nine P1 defects were reproduced and permanently fixed, including V5 BGW/DGW math, reversed clean-sheet difficulty, misleading uncertainty labels, illegal transfer suggestions, silent gameweek fallback and mutable historical records. No open P0/P1 defect remains.

This is not a model-performance endorsement. There are no finalized out-of-sample paired weeks available for V5 accuracy or calibration scoring. V5 remains **RESEARCH**, V4.2 remains **non-executable SHADOW**, and `competitive-v4.0` remains the production champion without a new accuracy claim.

## Scorecard

Scores reflect evidence available in this audit, not product ambition.

| Dimension | Score / 100 | Evidence-based assessment |
|---|---:|---|
| Data integrity | 82 | Structural checks, immutable writers and hashes pass; season sample is still one finalized week |
| API reliability | 82 | 50 tests and explicit provisional/corruption contracts; large payload and shallow readiness remain |
| Frontend reliability | 84 | Production build and desktop/mobile critical E2E pass; full accessibility depth remains |
| Prediction accuracy | 25 | Scorer exists, but zero finalized paired V5 weeks |
| Prediction calibration | 20 | Heuristic ranges and clean-sheet estimate are explicitly uncalibrated |
| Expected minutes | 30 | Deterministic logic is tested; out-of-sample validation is absent |
| Decision engine | 58 | Legal/gross constraints and fail-safe authority are clear; complete multi-GW NET EV is absent |
| Competitive engine | 55 | Operational champion is isolated, but comparative performance evidence is insufficient |
| Testing | 88 | 50 API tests, randomized validation, build/typecheck and 17 browser flows run in CI |
| Observability | 55 | Workflow/smoke visibility exists; revision, readiness, SLOs and alerts are incomplete |
| Deployment | 82 | Automated Cloud Run verification and Netlify delivery; exact public revision evidence is limited |
| Maintainability | 68 | Contracts/reports improved; external optimizer source and duplicated large data contracts remain |

## Decision

- **Engineering:** GREEN only after the recorded final CI and production smoke pass.
- **Models:** keep current separation; do not promote V5 or V4.2.
- **Next priorities:** reduce league payloads, expose runtime/data revision readiness, capture every pre-deadline prediction, then report walk-forward MAE/RMSE/bias/rank/calibration by GW and position.

The detailed evidence is in the audit report set alongside this summary.
