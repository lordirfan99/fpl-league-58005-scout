# Architecture and Current-State Inventory

Audit timestamp: 2026-08-31 (Asia/Kuala_Lumpur)  
Repository branch: `master`  
Commit inspected at inventory start: `b86797a2273b141516315c28da4b8614b6a4927f`

## System map

```text
Official FPL public API
  |-- live team polling (15-30 second server cache)
  |-- bootstrap and fixture refresh
  |-- completed-GW league collectors
  v
Collectors and VM autopilot
  |-- provisional/live read model
  |-- validated completed-GW JSON snapshots
  |-- pre-deadline frozen journal evidence
  |-- production plan + V4.2 non-executable shadow artifacts
  v
GCS snapshot store + immutable repository journal/data
  v
Cloud Run FastAPI read API
  |-- snapshot-backed league/elite/recommendation routes
  |-- official-FPL live personal-team route
  |-- read-only VM bridge proxy
  |-- isolated V5 lab projections
  v
Netlify Next.js dashboard
  |-- live My Team
  |-- finalized league/elite/analytics views
  |-- decision, planner, model comparison and journal views
  v
Human approval via Telegram (only write authority)
```

## Repository inventory

| Area | Responsibility | Main inputs | Main outputs | Important consumers | Primary failure modes | Existing verification |
|---|---|---|---|---|---|---|
| `.github/workflows` | CI, API deployment, fixture refresh, completed-GW collection, pre-deadline capture | Git commits, schedules, GitHub OIDC | Cloud Run revisions, refreshed fixture/snapshot commits, journal evidence | Production services | Required gates currently omit lint and frontend tests; scheduled upstream failures | Workflow runs and post-deploy API assertions |
| `scripts/` | FPL collectors, analysis, fixture horizon, journal build/export | Official FPL API, snapshot files | JSON/CSV/Markdown reports and journals | API repository, research | API throttling, partial managers, hard-coded helper scripts, duplicated collectors | Selected scripts compiled; collector validation exists but coverage is uneven |
| `data/` | Versioned bootstrap, fixtures, league snapshots and journal | Collectors and workflow commits | Packaged fail-soft API data and immutable GW journal | Cloud Run API, analysis scripts | Large 20-32 MB full snapshots, provisional/final mismatch, accidental mutation | Snapshot quality functions; only GW1 finalized locally |
| `services/api/app` | Versioned read API, live FPL proxy, projections and recommendations | GCS/repository snapshots, FPL live API, VM bridge | Typed JSON endpoints | Next.js dashboard, deployment smoke checks | Contract drift, incomplete snapshot response validation, upstream failure, stale cache | 32 pytest tests at inventory time |
| `integration/gcp-bot` | Read-only VM bridge serializer and sync service | VM plan/shadow artifacts | Sanitized control-centre payload | Cloud Run API/autopilot UI | External generator not reproducible here, stale file artifacts, bridge availability | Python compile plus health check; no direct unit suite found |
| `web-next` | Next.js 16 production dashboard | Cloud Run API | User-facing pages | End user | No frontend unit/component/E2E suite, multi-MB SSR payloads, silent fetch fallback, provenance gaps | Typecheck and build only in CI |
| `dashboard/` | Legacy/static dashboard assets | Snapshot files | Legacy UI | Unknown/legacy | Duplicate logic and stale UX | No active dependency proof yet |
| `docs/` | Architecture, deployment and V5 blueprint | Repository/runtime observations | Operational documentation | Maintainers | Documentation drift | Manual review |
| `reports/` | GW analysis and audit evidence | Snapshots/model outputs | Markdown/JSON research | Maintainers and journal | Generated-file churn, unverified provenance | Generation scripts; audit folder created by this cycle |

## API and frontend boundaries

FastAPI route groups found:

- health and snapshot ingestion;
- identity and live personal team;
- snapshot-backed personal team, league, elite and recommendations;
- catalog, fixtures and V5 projections;
- journal index, entry and exports;
- integration/autopilot status and read-only control centre;
- canonical read-only decision packet.

Next.js critical routes found:

- `/`, `/my-team`, `/league`, `/elite`, `/players`, `/transfers`, `/planner`, `/analytics`;
- `/model-compare`, `/v5-lab`, `/journal`, `/journal/[season]/gw/[gameweek]`;
- `/assistant`, `/settings`, `/autopilot`, `/compare`, `/shadow-v3`.

## Schemas and time layers

| Data layer | Mutability | Intended freshness | Current representation | Required UI label |
|---|---|---|---|---|
| Personal live team | Mutable | 15-30 seconds cache | `/v1/live/team` | LIVE / PROVISIONAL |
| Official player catalog | Mutable | short cache / refresh | `/v1/catalog`, bootstrap cache | LIVE or freshness timestamp |
| Fixtures | Mutable until played | hours | fixture cache and `/v1/fixtures` | source + captured time |
| League snapshot | Immutable only after finalization | one completed GW | GCS/repository `gw*_league*_data.json` | FINAL; otherwise INVALID/PROVISIONAL |
| Pre-deadline prediction | Immutable after deadline | frozen | journal raw evidence / VM artifacts | model + cutoff + target GW |
| Journal | Immutable | permanent | `data/journal/<season>/gwNN.json` | FINAL |
| V5 projection | Mutable research output | request time | `/v1/projections/current` | LAB / PROJECTED |

## Confirmed hard-coded and duplicate-risk areas

- Default league `58005`, team ID `2797967`, season `2026-27` and some default GW1 values exist in configuration/code. Some are intended defaults, but season rollover is not fully centralized.
- Multiple collectors exist (`fetch_gw_data.py`, `fetch_gw_data_fixed.py`, GW1 fast/full scripts), creating drift risk.
- Legacy `dashboard/` and active `web-next/` coexist; dependency ownership is not documented.
- V3, V4.2 and V5 read surfaces coexist; model registry metadata is not centralized in executable configuration.
- Frontend server adapters frequently catch errors and return null/fallbacks. This improves availability but can hide which upstream failed unless provenance is displayed.

## Current architecture verdict

The production safety boundary is strong: the dashboard and API are read-only, Telegram is the execution authority, V4.2 is non-executable, and V5 is isolated from league popularity. The architecture is not yet fully reproducible because the production horizon optimizer and V4.2 generator live outside this repository, frontend QA is build-only, and model/data version metadata are incomplete.

