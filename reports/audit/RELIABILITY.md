# Reliability Audit

Audit date: 2026-08-31

## Controls verified

- Final league writers refuse replacement by default. An intentional correction requires an explicit flag and reason.
- The five existing finalized artifacts are protected by a canonical SHA-256 manifest verified in CI. Canonical newline hashing gives the same identity on Windows and Linux runners.
- Journal creation is idempotent for identical content, refuses changed content, and verifies detail and index hashes at read time.
- Pre-deadline evidence remains separate from final outcomes and carries capture time/input hashes.
- Provisional league data is rejected explicitly. The UI falls back only for expected 404/409 archive states and labels the mismatch.
- The decision layer fails safe: dashboard writes are disabled and Telegram remains the only execution authority.
- Refresh workflows, CI and Cloud Run smoke checks make failure visible rather than silently publishing malformed snapshots.

## Failure behavior

| Failure | Behavior |
|---|---|
| Official/live upstream unavailable | Availability may degrade; unknown failures are not presented as a current finalized week |
| Requested GW not finalized | API returns 409; dashboard may show the latest archive with an explicit notice |
| Frozen file changed or missing | CI manifest gate fails |
| Journal record/index tampered | API rejects it with 409 |
| Unsafe/incomplete decision evidence | Non-executable safe hold; no dashboard write path |
| Repeated finalization attempt | Writer refuses overwrite unless recorded as a correction |

## Gaps

- There are no published SLOs, alert thresholds, p50/p95 monitoring or synthetic uptime monitor.
- Public health is liveness-oriented, not a full readiness/provenance endpoint.
- Disaster recovery and restore drills are not demonstrated by repository evidence.
- External VM optimizer source and immutable build identity are not captured here.

## Verdict

Release-critical data and decision failure modes are guarded. Reliability is **GREEN for this engineering release**, with production observability and recovery maturity at P2.
