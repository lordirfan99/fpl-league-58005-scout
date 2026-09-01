# Complete live league snapshots

The Analytics page must never derive formation, captaincy, ownership, or squad
value from partially hydrated data. The collector in `scripts/refresh_live_leagues.py`
is the only process allowed to call an entry's FPL picks endpoint for complete
league analytics.

## Runtime contract

1. `refresh-live-leagues.yml` runs hourly at `:12` UTC.
2. It fetches official standings and every manager's current picks for leagues
   `58005` and `131997`.
3. A run fails if any manager lacks a valid 15-player squad, 11 starters, one
   captain, or one vice-captain.
4. It writes an immutable run object, then atomically updates a small per-league
   manifest only after validation succeeds.
5. `/v1/leagues/{league_id}/live` reads that manifest and refuses partial data.
   If the latest collection fails, the API continues to serve the previous
   complete snapshot; if none exists it returns `503 live_snapshot_unavailable`.

Set repository variable `FPL_SNAPSHOT_BUCKET` to the exact bucket supplied to
the Cloud Run API as `FPL_SNAPSHOT_BUCKET`. Do not point it at the journal-only
bucket unless that is also the API's snapshot bucket.

## Manual bootstrap

Run the `Refresh complete live league snapshots` workflow once after deploying
this change. Verify both manifests contain matching `expected_count` and
`hydrated_count`, then visit `/analytics`.

## Future scheduler migration

The collector is deliberately independent of GitHub Actions. It can move to a
Cloud Run Job without changing its payload or API contract; use the same bucket
and invoke `python scripts/refresh_live_leagues.py`. Keep the job idempotent and
retain the manifest publication precondition.
