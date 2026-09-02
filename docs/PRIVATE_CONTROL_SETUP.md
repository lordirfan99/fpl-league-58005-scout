# Private control setup

The new Plan screen and `/v3/control/*` API are deliberately fail-closed until
the owner configures identity and the new Telegram bot. No legacy token or FPL
password is accepted by this service.

## Required configuration

1. Run `scripts/provision_control_api_identity.ps1` once in the project GCP
   account.
2. Create a Google OAuth web client for the Cloud Run dashboard domain. Set:
   `FPL_GOOGLE_OAUTH_CLIENT_ID` and `FPL_OWNER_EMAIL`.
3. Rotate the legacy Telegram token, create the new notification/approval bot,
   and add: `FPL_TELEGRAM_BOT_TOKEN`, `FPL_TELEGRAM_CHAT_ID`, and a random
   `FPL_TELEGRAM_WEBHOOK_SECRET`.
4. Deploy a private FPL session executor separately. It is the only process
   allowed to contain encrypted FPL session data. Configure its private URL and
   shared token as `FPL_EXECUTION_WEBHOOK_URL` and
   `FPL_EXECUTION_WEBHOOK_TOKEN`.
5. Bind only `fpl-control-api` to the six named Secret Manager secrets, then
   inject them into `fpl-scout-api` as environment variables. Do not put any
   of these values in the dashboard build or browser environment.

## Executor contract

The private executor receives a JSON POST with `action_id`, `plan_hash`, and
`request`, plus `x-fpl-executor-token`. It must validate the exact FPL deadline,
current squad, player availability, price, and idempotency before it submits a
change. It returns `{ "ok": true, "reference": "..." }` on one successful
submission, or `{ "ok": false, "code": "..." }` otherwise.

The API has no FPL credentials and cannot submit an action while the executor
is absent. This is intentional.
