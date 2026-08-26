# Fantasy Scout Control Centre

Production FPL decision and league-intelligence system for the 2026/27 season.

- Dashboard: https://fpl-scout-intelligence.netlify.app
- Personal FPL entry: `2797967`
- Tracked leagues: `58005` (KK Old Boys) and `131997` (Overall IFE)
- Production API: `https://fpl-scout-api-bztsnhv3ea-uc.a.run.app`

## What is live

The current dashboard is the Next.js application in `web-next/`. The older files in
`dashboard/` are retained only as a rollback reference and are not the production UI.

Current views:

- My Team: official FPL-style 11-player pitch, four-player bench, GW points and fixtures
- Assistant: weekly captain, transfer, risk and elite-context decision board
- GCP Autopilot: live model plan, safety validation, heartbeat and Telegram handoff
- Shadow V3: uncertainty ranges, component xPts, multi-GW scenarios and promotion gates
- Planner: GW2-GW6 fixture horizon and squad planning
- League: searchable standings and manager lineup inspection for both tracked leagues
- Elite 5%: template XI, bench, ownership edges, captaincy and manager detail
- Players: official player, availability, price, form and fixture data

## Production architecture

```text
Official FPL API ───────┐
                       ├─> completed-GW snapshots ─> Cloud Run read API
Two tracked leagues ───┘                               │
                                                      v
GCP FPL Autopilot VM ─> read-only bridge ─────────> Next.js on Netlify
        │                                             │
        └─ Telegram approval ─> hardened executor     └─ analysis only
```

Safety boundary:

- The website and Cloud Run API have no FPL write endpoint.
- The browser never receives the bridge bearer token, Telegram token or FPL cookies.
- Telegram remains the only approve/reject surface.
- Shadow V3 is read-only and cannot mutate the pending plan or live team.

## Shadow V3 lifecycle

1. Inside the 26-hour pre-deadline window, the VM generates `v3_shadow_gwN.json`.
2. The dashboard shows its captain distribution, candidate ranking and four-GW plan.
3. After FPL marks the gameweek finished and data-checked, the evaluation job compares
   projected and actual outcomes.
4. Promotion requires at least three evaluated GWs, acceptable calibration, an improved
   decision metric and explicit manual approval.
5. A completed GW artifact is historical evidence, not the current recommendation.

## Automatic season pipeline

| Trigger | Automation | Result |
|---|---|---|
| Every 2 hours on the VM | `fpl-auto-runner.timer` | Live V2 plan, Shadow V3 snapshot, post-GW review and promotion evaluation |
| Every 4 hours on GitHub | `refresh-gameweek.yml` | Detect latest finished/data-checked GW, collect both leagues, validate and commit snapshots |
| Daily on GitHub | `refresh-fixtures.yml` | Refresh official GW2-GW6 fixture horizon |
| Push affecting `web-next` | Netlify Git integration | TypeScript/Next.js production deployment |
| Push affecting API or snapshots | `deploy-api.yml` | Cloud Build image and Cloud Run deployment |
| Every 5 minutes on the VM | `fpl-dashboard-bridge-sync.timer` | Fetch reviewed bridge code, compile, install, health-check and rollback on failure |

This keeps the system moving through GW38 without a weekly human deployment. Human action
is still intentionally required for an actual FPL transfer, captain or chip approval.

## Local development

```powershell
cd web-next
npm ci
$env:FPL_API_BASE_URL='https://fpl-scout-api-bztsnhv3ea-uc.a.run.app'
npm run dev
```

Validation:

```powershell
cd web-next
npm run typecheck
npm run build

cd ..\services\api
python -m pip install -r requirements.txt
$env:PYTHONPATH='.'
python -m pytest tests
```

## Repository map

```text
web-next/                 Next.js production dashboard
services/api/             FastAPI read API deployed to Cloud Run
integration/gcp-bot/      Read-only VM bridge and auto-update units
scripts/                  League collector, reports and fixture jobs
data/                     Versioned completed-GW snapshots
reports/                  Generated league and elite analysis
.github/workflows/        CI, data refresh and GCP deployment
cloudbuild.api.yaml       Cloud Run image/build definition
netlify.toml              Git-connected frontend build definition
DEPLOYMENT.md             One-time setup, operations and rollback
```

## Data quality gates

A completed-GW snapshot is committed only when:

- FPL reports the gameweek as both `finished` and `data_checked`;
- both configured leagues are present;
- every manager has 15 players and exactly 11 scoring starters;
- no manager fetch failed;
- full and compact manager counts match.

Failed validation leaves the previous production snapshot untouched.

## Ownership

Owner: `lordirfan99`
Data source: Fantasy Premier League public API
