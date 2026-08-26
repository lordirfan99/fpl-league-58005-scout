# GCP Autopilot dashboard integration

## Runtime architecture

```text
FPL Autopilot VM
  model + authenticated FPL client + executor
                |
                | sanitized, read-only state
                v
dashboard_bridge.py (localhost:8787)
                |
                | HTTPS + bearer service token
                v
Fantasy Scout FastAPI BFF
                |
                | no bot token or FPL credentials
                v
Next.js GCP Autopilot / Assistant views

Telegram bot -> approve/reject -> existing hardened executor
```

The browser never receives `DASHBOARD_READ_TOKEN`, the Telegram token, FPL session cookies, or FPL credentials. The bridge has no write endpoint.

## Live GCP installation

- Service: `fpl-dashboard-bridge.service`
- Local listener: `127.0.0.1:8787`
- Public read path: `https://sportmania.duckdns.org/fpl-autopilot/`
- Secret Manager secret: `fpl-dashboard-read-token`
- Caddy rollback file: `/etc/caddy/Caddyfile.backup-20260825T1425Z`

The bridge payload includes sanitized Shadow V3 evidence: projection ranges,
component xPts, candidate and squad rankings, multi-GW plans, scenario comparisons and
promotion state. It never exposes credentials, session data or an execution route.

## Automatic bridge delivery

`fpl-dashboard-bridge-sync.timer` checks the reviewed GitHub `master` version every five
minutes. A changed bridge must compile and pass the local health check. A failed restart
automatically restores `dashboard_bridge.py.auto-rollback`.

Install the timer once using the three files in this directory. After that, bridge-only
changes no longer require SSH or a manual service restart.

## Health checks

```bash
systemctl is-active fpl-bot.service
systemctl is-active fpl-dashboard-bridge.service
curl https://sportmania.duckdns.org/fpl-autopilot/health
```

`/v1/control-centre` must return `401` without a valid service token. A successful payload must always report `writes_enabled: false` and `execution_authority: telegram`.

## Recommended operating model

- Website: large analysis surface, rankings, model diagnostics, elite context and audit history.
- Telegram: deadline alerts and explicit approve/reject actions.
- Executor: validates plan ID, deadline, price, availability and final FPL state before mutation.
- Model: remains authoritative; elite ownership is supporting evidence and a risk-control signal, not a blind copy rule.

## Next production hardening

1. Put user authentication in front of the Next.js control centre before exposing personal model detail publicly.
2. Add a structured append-only decision audit containing model input fingerprint, proposal, approval identity, execution result and post-gameweek score.
3. Alert if the bridge, bot heartbeat, projection snapshot or odds feed is stale.
4. Rotate the read token periodically and after any suspected disclosure.
