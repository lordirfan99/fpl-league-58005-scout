# Failure and Risk Register

Audit opened: 2026-08-31

Status meanings: `OPEN` is verified and unresolved; `GAP` is a missing control/evidence gate; `FIXED` requires a permanent regression test; `ACCEPTED` is documented residual risk. P0/P1 defects block release.

| ID | Severity | Layer | Problem | Evidence | Impact | Root cause | Required fix / evidence | Status |
|---|---:|---|---|---|---|---|---|---|
| AUD-001 | P1 | V5 projection | A double gameweek was reduced to the first matching fixture. | Synthetic DGW equaled its first fixture. | Wrong V5 xPts and missing critical fixtures for DGWs. | Projection contract modeled a player-week as one fixture. | Every fixture is now scored and summed; DGW appearance aggregation regression added. | FIXED |
| AUD-002 | P1 | V5 projection | A blank gameweek received a fallback and non-zero xPts/range. | Synthetic BGW returned 2.59 xPts. | Wrong V5 xPts in BGWs. | Missing fixture and blank fixture were conflated. | No-fixture rows now return zero mean/range and `blank_gameweek:no_fixture`; regression added. | FIXED |
| AUD-003 | P1 | V5 uncertainty/UI | Heuristic bounds were shown as probabilistic quantiles. | Fixed deterministic spread; UI used P10/Median/P90. | Users could interpret bounds as measured probabilities. | No fitted distribution/calibration store exists. | API adds `heuristic_not_calibrated`; UI says Low range/Estimate/High range and explains limitation. | FIXED |
| AUD-004 | P1 | Transfer decisions | Production shortlist did not enforce affordability/club limits and browser showed incoming xPts rather than change. | GW1 surfaced £6.0m → £15.5m; browser assigned only incoming `ep_next`. | Research could be mistaken for a legal/value-positive move. | Candidate generation omitted legal context and display omitted opportunity cost. | Snapshot-price bank/club checks added; browser shows gross incoming-minus-outgoing and all surfaces say hits/horizon excluded. | FIXED |
| AUD-005 | P1 | Release QA | No frontend functional or automated E2E suite existed. | CI ran only typecheck/build. | Critical navigation, stale-state and interaction regressions could ship green. | Frontend testing was never added to release workflow. | Playwright desktop/mobile critical flows, week routing, artwork and console gates now run in CI. | FIXED |
| AUD-006 | P1 | Historical integrity | Journal records had hashes but no read-time/index/CI tamper enforcement. | Repository returned JSON without verifying it. | Frozen prediction/history corruption could remain undetected. | Hash generation and verification were not paired. | Immutable writer, detail/index verification, tamper tests and CI frozen-manifest verification added. | FIXED |
| AUD-007 | P2 | Model validation | Statistical evidence remains too small for model promotion. | GW1 has no frozen prediction; GW2 is frozen but not final. | Accuracy/calibration promotion claims cannot be supported yet. | Prediction freezing began after GW1. | Reproducible scorer now returns insufficient evidence; continue accumulating shadow pairs. | ACCEPTED — V5 remains RESEARCH |
| AUD-008 | P2 | Performance | League and compare pages transfer approximately 10.3 MB; league API transfers 7.39 MB for GW1. | Production HTTP reproduction on 2026-08-31. | Slow mobile navigation, higher memory use and timeout risk. | Full hydrated manager squads are embedded/fetched for overview routes. | Add summary/pagination contracts and measure p50/p95 before/after. | OPEN |
| AUD-009 | P2 | Observability | `/health` is shallow and production does not expose a commit/revision identifier. | Health reports static service/model flags only. | Operators cannot prove which code/data revision is serving or distinguish dependency failure. | Build provenance and readiness checks are absent. | Add non-secret revision/data metadata and dependency readiness, then test deployment. | OPEN |
| AUD-010 | P2 | Model governance | V4.2 generator/optimizer implementation and V4.1 horizon optimizer are not reproducible from this repository. | Only the bridge serializer/runtime artifact is present. | Shadow evidence cannot be independently rebuilt from source. | Implementation lives on the VM outside version control. | Import versioned source/config or document immutable external artifact hash. | OPEN |
| AUD-011 | P2 | Metadata | Model outputs omit consistent feature version, data version/hash and cutoff fields. | Registry audit across V4.0, V4.2 and V5 contracts. | Recommendation origin is not fully reconstructable. | Metadata contracts evolved independently. | Introduce a shared provenance envelope without rewriting frozen artifacts. | OPEN |
| AUD-012 | P1 | Historical data | Finalized GW1 league snapshots had been rewritten repeatedly after finalization. | Git history records at least ten large rewrites. | Historical league review could drift. | Collectors overwrote canonical final filenames without a manifest gate. | Default overwrite refusal, explicit correction flag/reason, five-artifact SHA-256 manifest and CI verification added. | FIXED |
| AUD-013 | P1 | Frontend data | League loading caught every API failure and silently walked backward. | Broad `catch` loop could hide 500/auth/outage states. | Old data could look current. | Fallback was implicit rather than modeled. | Fallback is restricted to 404/409; requested/returned GW and reason are visible; unknown failures propagate; week-routing E2E added. | FIXED |
| AUD-014 | P2 | Source freshness | Bootstrap lacked capture/hash provenance. | Local/deployed player counts differed and cutoff was unknown. | Current data identity could not be reconstructed. | Raw cache lacked a source envelope. | Official refresh now stores capture time/content SHA-256; catalog/V5 expose honest freshness/quality metadata. | FIXED |
| AUD-015 | P1 | V5 clean sheets | Harder fixtures produced a larger clean-sheet component. | Synthetic FDR1/FDR5 returned 0.752/0.917. | Defender/GKP ranking could invert. | Difficulty sign was reversed. | Monotonic heuristic corrected and regression added; calibration remains explicitly unproven. | FIXED |
| AUD-016 | P2 | Frontend media | Some official portraits returned upstream 403 through Next Image. | Production-server E2E logs. | Broken portraits/noisy server errors. | Constructed image URLs are not guaranteed. | Direct unoptimized retrieval activates shirt/badge/initial fallback; artwork E2E passes without optimizer 403 logs. | FIXED |
| AUD-017 | P2 | Decision research | A complete multi-transfer, multi-GW NET-EV optimizer is not present in this repository. | V5 helper is single-transfer; competitive API is explicitly gross. | Research cannot answer full transfer optimization. | Optimizer source is external/incomplete and statistical horizon evidence is immature. | Keep surfaces honest and non-executable; implement only after frozen multi-GW evidence exists. | ACCEPTED LIMITATION |

## Release-blocking count at register creation

- P0: 0 known
- P1: 0 open (nine fixed)
- P2: 6 open/accepted limitations; two additional P2s fixed
- P3: 0

No P1 is considered closed merely because V5 is isolated from execution. Isolation limits production blast radius; it does not make the wrong research result valid.

## Why the original tests missed the P1 defects

| IDs | Missing test mechanism now added |
|---|---|
| AUD-001, AUD-002, AUD-015 | Projection tests covered bounds only, not BGW/DGW shape or monotonic direction. Synthetic fixture-shape regressions now pin all three. |
| AUD-003 | Contract tests checked separation/row count, not uncertainty semantics. API metadata and browser copy are now asserted through contract/E2E gates. |
| AUD-004 | The original transfer test covered the isolated single-transfer helper, not surfaced competitive/browser candidates. API legality and UI gross-change behavior are now gated. |
| AUD-005, AUD-013 | Typecheck/build cannot exercise route state or navigation. Real desktop/mobile production-server E2E now checks explicit GW fallback and purpose-based week links. |
| AUD-006, AUD-012 | Tests generated hashes but never attempted replacement/tampering or checked Git artifacts. Immutable-write, tamper, index mismatch, writer refusal and manifest gates now fail permanently. |
