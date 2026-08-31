# Security Audit

Audit date: 2026-08-31

## Verified posture

- The public dashboard uses read-only API contracts; `dashboard_writes_enabled=false` and execution authority is Telegram.
- Cloud Run deployment uses GitHub OIDC/workload identity rather than a repository service-account key.
- Snapshot publishing uses authenticated request verification and bounded/path-controlled artifact handling.
- CORS and exposed HTTP methods are constrained to the read use case.
- The fresh frontend dependency installation reported 34 packages audited and zero known npm vulnerabilities.
- No credential was intentionally added to the audit changes or reports.

## Threat and control summary

| Risk | Current control | Residual assessment |
|---|---|---|
| Dashboard triggers an FPL action | No dashboard write path; Telegram-only authority | LOW |
| Historical artifact substitution | Manifest, immutable writer and read-time hash verification | LOW for tracked artifacts |
| Untrusted/malformed FPL payload | Pydantic/schema and squad integrity validation before serialization | MEDIUM; upstream availability remains external |
| Secret exposure in deployment | OIDC and GitHub environment variables | LOW from repository evidence |
| Oversized public payload abuse | Read-only endpoints but large responses | MEDIUM; rate/edge controls were not evidenced |
| Dependency vulnerability | npm audit clean at test time | MEDIUM; Python SCA and continuous scanning were not demonstrated |

## Limitations

This was a repository and public-contract review, not a penetration test. IAM bindings, Cloud Run/Netlify account configuration, WAF/rate limits, secret rotation, SAST and Python dependency CVE scanning require platform-level evidence not present in the repository.

## Verdict

No release-blocking secret or write-authority defect was found. Security is **PASS with P2 hardening work** for platform controls and continuous dependency scanning.
