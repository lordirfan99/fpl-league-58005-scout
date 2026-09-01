# Weekly refresh — reliability model

How the dashboard's data stays fresh from now through GW38, what can break it,
and how a failure is surfaced.

## The moving parts

| Workflow | Schedule | Job | Failure surface |
|---|---|---|---|
| `refresh-fixtures.yml` | hourly `:17` | Fetch official bootstrap + fixtures, publish verified caches to `gs://$FPL_JOURNAL_BUCKET/snapshots/` | Telegram alert on failure |
| `refresh-gameweek.yml` | hourly `:23` | When a GW is `finished` + `data_checked` and not yet saved: fetch both leagues, build reports + journal + model backtest, **publish snapshots to GCS**, then commit + push | Telegram alert on failure; push is rebase + retry |
| `capture-journal.yml` | hourly `:17` | Freeze pre-deadline decision evidence inside the deadline window | Telegram alert on failure |
| `freshness-watchdog.yml` | `:05` / `:35` | From outside the pipeline, assert the **live API** is serving data as fresh as its guarantee for this point in the GW cycle | Telegram alert when tripped |
| `monitor-production.yml` | every 30 min | Site + API up, contract shapes, latency budgets | workflow status only |
| `deploy-api.yml` | on push to `data/**`, `services/api/**` | Rebuild + redeploy Cloud Run, verify `/health` + `/ready` | workflow status only |

The `competitive-v4.0` model, the MILP optimizer and the Telegram approval bot
run separately on the GCP VM (`fpl-autopilot`, systemd timers). They publish the
read-only pending plan the dashboard shows via `/v1/autopilot/control-centre`.

## The post-deadline gap is expected

Between a GW's deadline (Fri) and FPL marking it `data_checked` (Sun–Mon), no
finalized league snapshot exists for that GW. During that window:

* `/v1/leagues/58005?gw=<current>` returns `409 snapshot_not_finalized`
* the dashboard falls back to `/v1/leagues/58005/live`
* recommendations stay pinned to the previous finalized GW

This is deliberate historical integrity, **not** a failed refresh. The watchdog
tolerates it and only escalates to an alert once a GW has been finished +
data-checked for more than `FINALIZE_GRACE_HOURS` (48h) without a snapshot.

## What now updates the live API without a redeploy

`refresh-gameweek.yml` copies the finalized `gw<N>_league<id>_data.json` files
(plus `bootstrap_cache.json` / `fixtures_cache.json`) to the GCS snapshots
bucket **before** committing. `repository._read_remote()` reads that bucket
first, so the running Cloud Run service serves the new snapshot within its
short remote cache TTL. The git commit + `deploy-api.yml` rebuild still happen,
but they are no longer on the critical path for freshness.

## Alerting

Alerts are optional and fail-soft. Set two repository secrets to turn them on:

| Secret | Value |
|---|---|
| `TELEGRAM_BOT_TOKEN` | the approval bot's token (same bot is fine) |
| `TELEGRAM_ALERT_CHAT_ID` | chat / channel id to receive alerts |

If either is unset, the notify step logs a notice and the workflow still
succeeds — nothing else changes.

## Manual checks

```bash
# Is the API serving data as fresh as it should be?
python scripts/check_freshness.py

# Force a finalized-GW refresh (bypass the "is it finished yet" gate)
gh workflow run refresh-gameweek.yml -f gameweek=<N>
```

## Follow-ups not in this change

* Cache `/v1/leagues/{id}/live` (currently ~6 s, 25 FPL page fetches, ~30 s
  in-process TTL) in GCS keyed by `(league_id, gw)` + `Cache-Control` /
  `stale-while-revalidate` headers on the heavy read endpoints.
* `web-next` still calls full `/v1/catalog` (1.6 MB) where `/v1/catalog/compact`
  (76 KB) would do.
* Frontend could use the new `/v1/me` `live_gameweek` / `snapshot_lag_gameweeks`
  fields to label the post-deadline gap explicitly instead of inferring it.
