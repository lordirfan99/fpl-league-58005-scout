# Performance Audit

Audit date: 2026-08-31

These are single-request production observations, not a load test and not p50/p95 percentiles.

## Observed baseline

| Surface | Approximate transfer/time | Assessment |
|---|---:|---|
| `/health` | 188 B / 405 ms | Acceptable smoke response |
| `/v1/catalog` | 1.65 MB / 1.8 s | Large but usable |
| `/v1/leagues/58005?gw=1` | 7.39 MB / 3.1 s | High payload and latency risk |
| `/v1/projections/current` | 333 KB / 1.2 s | Moderate |
| `/league` and `/compare` HTML | about 10.3 MB / up to about 5.3 s in the route sweep | Material mobile and memory risk |
| `/elite` HTML | about 2.46 MB | Large |

## Root cause and remediation

Overview pages serialize or fetch complete hydrated manager/player datasets. The functional release is not blocked, but this will scale poorly across slower devices and networks.

Recommended sequence:

1. Add league-summary and paginated manager endpoints.
2. Keep full squad hydration behind drill-down routes.
3. Add compression/cache evidence and server-timing fields.
4. Establish p50/p95 payload, TTFB and route-transition budgets in CI/monitoring.
5. Compare the same production dataset before and after the contract change.

## Verdict

No crash or correctness blocker was reproduced, but performance is **AMBER / P2**. The 10 MB route payload is the highest-priority engineering follow-up after this release.
