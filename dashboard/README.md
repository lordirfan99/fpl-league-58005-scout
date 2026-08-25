# FPL Scout Intelligence Dashboard

A lightweight zero-backend dashboard for the repository's weekly FPL scouting snapshots.

## Features

- Overview KPIs, points distribution, top performers and captaincy meta
- Rank movement indicators using current vs previous league rank
- Template XI derived from league ownership
- League Explorer with sorting, search and manager drill-down
- Player Intelligence with ownership, captaincy and differential classification
- Manager Explorer with squad detail
- Manager-vs-manager comparison with squad overlap and unique picks
- Transfer Intelligence for common moves
- Chip usage tracker
- My Team vs League view with strongest differentials and most similar managers
- Automatic discovery of available GW1-GW38 snapshots
- Support for leagues 19292, 58005, 687126 and 131997

## Data contract

Fast navigation reads:

`data/gw{GW}_league{LEAGUE}_compact.json`

Deep scouting views lazily load:

`data/gw{GW}_league{LEAGUE}_data.json`

The dashboard therefore stays responsive while preserving access to full squad, transfer and chip information.

## Run locally

Serve the repository root through any static HTTP server. Example:

```bash
python -m http.server 8080
```

Then open `/dashboard/`.

Do not open `index.html` directly through `file://`, because the browser must fetch the JSON snapshots over HTTP.

## Deployment

The repository includes `vercel.json` so the root URL rewrites to the dashboard while `/data/*` remains available to the browser.

No database or application server is required. When the GW pipeline commits a new snapshot, a normal Vercel deployment will expose it automatically.
