# Manual FPL operation migration plan

## Decision and target state

The owner will make every FPL transfer, captain, lineup and chip change manually
in the official FPL website/app. The Scout system remains a **read-only research
and decision-support product**: retain official FPL reads, the hourly Cloud Run
snapshot collector, Analytics, Planner, projections, recommendations and the
season journal; remove Telegram, the Autopilot bridge and all execution claims.

Do not replace Telegram with another execution integration. The resulting
dashboard must never write to FPL.

## Important local paths for the implementation agent

Repository root:

`C:\Users\irfan\Documents\ChatGPT\FPL MANAGER\fpl-league-58005-scout`

Primary deployment configuration:

`C:\Users\irfan\Documents\ChatGPT\FPL MANAGER\fpl-league-58005-scout\cloudbuild.api.yaml`

Keep this Cloud Run/Scheduler provisioning script: it powers read-only live
snapshots and is unrelated to Telegram:

`C:\Users\irfan\Documents\ChatGPT\FPL MANAGER\fpl-league-58005-scout\scripts\provision_live_refresh_infra.ps1`

The legacy bridge is documented as running on the external Compute Engine VM at
`/opt/fpl-autopilot/`. The repository-side bridge adapter is:

`C:\Users\irfan\Documents\ChatGPT\FPL MANAGER\fpl-league-58005-scout\integration\gcp-bot\dashboard_bridge.py`

## Implementation order

### 1. Inventory before deleting

Search for `telegram`, `autopilot`, `sportmania`, `FPL_AUTOPILOT`, and
`fpl-dashboard-read-token`. Classify every result as retained read-only
research, removable bridge/UI integration, or historical documentation that
needs relabelling. Export any private reflections the owner wants to retain.
Do not delete GCS live snapshots or journal evidence.

### 2. Decouple the API

Remove `app.autopilot`, its settings, bridge authentication helper,
`/v1/autopilot/*` endpoints and all bridge fallback paths. Replace dependent
decision responses with locally derived read-only recommendations using existing
official catalog, snapshot and model data. Responses must have
`writes_enabled: false` and `execution_authority: "manual_fpl"` (or omit the
latter).

In `cloudbuild.api.yaml`, remove only:

- `FPL_AUTOPILOT_BASE_URL`
- `FPL_AUTOPILOT_TOKEN`
- Secret Manager reference `fpl-dashboard-read-token`

Do not remove `FPL_SNAPSHOT_BUCKET`, the Cloud Run live-refresh Job, its service
account or Cloud Scheduler.

### 3. Simplify the dashboard

Remove or redesign the GCP Autopilot route/navigation. Pages currently using
`getAutopilotData` (`assistant`, `my-team`, `planner`, `players`,
`model-compare`, dashboard layout) must use local read-only data or show a
plainly labelled recommendation. Replace “approve through Telegram”,
“execution authority”, and “canonical Telegram plan” with “review and apply
manually in FPL”. Remove Telegram-only journal reflection copy.

### 4. Retire runtime and secrets only after deployment

After production is verified without bridge calls:

1. Disable the Telegram webhook/bot in its external runtime.
2. Stop, then delete the Compute Engine Autopilot VM after an owner-agreed
   rollback window.
3. Delete `fpl-dashboard-read-token` only once no deployed revision references
   it.
4. Remove unused Telegram environment variables/service accounts after checking
   IAM usage.

Verify exact resource names before deletion; do not use wildcard cleanup.

### 5. Tests and documentation

Update `README.md`, `DEPLOYMENT.md`, `docs/CURRENT_STATUS.md` and runbooks.
Label past Telegram references as historical rather than silently rewriting
history. Add tests that the API starts without bridge/Telegram settings, pages
render without the bridge, no response exposes writes, and the live-snapshot
Analytics path remains complete. Run API pytest, TypeScript, Next build and
Playwright. Confirm no browser request reaches `sportmania.duckdns.org`.

## Acceptance checklist

- [ ] No deployed environment variable or secret points at the Autopilot bridge.
- [ ] No dashboard copy tells the owner to use Telegram.
- [ ] API has no Autopilot/Telegram endpoint or bridge fallback.
- [ ] All FPL-facing functionality is demonstrably read-only.
- [ ] Cloud Run live refresh and Analytics still show complete snapshots.
- [ ] VM, webhook and secret retirement are documented and done only after
      production verification.

## Explicit non-goals

Do not remove FPL analytics, projections, models, the live snapshot collector,
Cloud Scheduler, Cloud Run API, browser dashboard or immutable journal evidence.
Do not automate FPL actions by another channel.
