# FPL Scout Intelligence Dashboard

A zero-backend navigable dashboard for the repository's gameweek snapshots.

## What it reads

The app automatically probes for:

- `data/gw{n}_league{league}_compact.json`
- `data/gw{n}_league{league}_data.json`

Tracked leagues: `19292`, `58005`, `687126`, `131997`.

Compact files drive the fast overview, leaderboard and manager search. Full files are loaded only when player intelligence or an individual squad is opened.

## Views

- **Overview** — manager count, average/median GW score, top score, top captain, captaincy meta and points distribution.
- **League Explorer** — searchable/sortable league table.
- **Player Intelligence** — league-specific ownership and captaincy derived from every manager squad.
- **Manager Explorer** — manager cards and squad drill-down.

## Local preview

Run a static server from the repository root so the dashboard can access `../data/`:

```bash
python -m http.server 8000
```

Then open `http://localhost:8000/dashboard/`.

Do not open `dashboard/index.html` directly with `file://`; browser fetch security will block JSON loading.

## Vercel

`vercel.json` rewrites `/` to the dashboard entry. Deploy the repository root as a static project. The repository `data/` directory remains addressable by the dashboard.

## Data lifecycle

No dashboard code change is required for later gameweeks. When the pipeline commits new `gw{n}_league{league}_compact.json` and full JSON snapshots, the dashboard discovers the new gameweek automatically.
