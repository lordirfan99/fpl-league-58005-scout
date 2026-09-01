# Complete live league snapshots

The Analytics page must never derive formation, captaincy, ownership, or squad
value from partially hydrated data. The collector in `scripts/refresh_live_leagues.py`
is the only process allowed to call an entry's FPL picks endpoint for complete
league analytics.

## Runtime contract

1. Cloud Scheduler starts the collector hourly at `:12` UTC.
2. It fetches official standings and every manager's current picks for leagues
   `58005` and `131997`.
3. A run fails if any manager lacks a valid 15-player squad, 11 starters, one
   captain, or one vice-captain.
4. It writes an immutable run object, then atomically updates a small per-league
   manifest only after validation succeeds.
5. `/v1/leagues/{league_id}/live` reads that manifest and refuses partial data.
   If the latest collection fails, the API continues to serve the previous
   complete snapshot; if none exists it returns `503 live_snapshot_unavailable`.

The job receives the exact same snapshot bucket configured on the Cloud Run API
as `FPL_SNAPSHOT_BUCKET`. Do not point it at a journal-only bucket.
# Scheduling

Production refreshes run as a **Cloud Run Job** triggered hourly by **Cloud
Scheduler**, rather than as a scheduled GitHub Action.  Provision the two
least-privilege service accounts and Scheduler target once:

```powershell
./scripts/provision_live_refresh_infra.ps1
# Deploy the production branch once, then run the command again to create the trigger.
./scripts/provision_live_refresh_infra.ps1
```

The deployment build creates or updates the `fpl-live-league-refresh` job;
after its first successful production deployment, the scheduler may safely run
it. The job writes only fully validated snapshot objects and then atomically
advances the manifest. GitHub Actions remains responsible for CI and deploying
the job image, not for operating the hourly refresh.
