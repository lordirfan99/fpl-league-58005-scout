# FPL Scout Intelligence Dashboard

> **Live at:** https://fpl-scout-intelligence.netlify.app
> **Part of:** https://github.com/lordirfan99/fpl-league-58005-scout

A lightweight, zero-backend dashboard for FPL league scouting. No build step, no database — just HTML, CSS, and JavaScript that reads JSON data files.

---

## Features

### 9 Dashboard Views

| View | Description |
|:-----|:------------|
| **Overview** | KPIs, top 10 performers, captaincy bar chart, points distribution, template XI, rank movers |
| **League Explorer** | Full standings table, searchable, sortable by any column |
| **Player Intelligence** | Every player's ownership %, captaincy %, differential classification |
| **Manager Explorer** | Card grid of all managers — click to see full squad, captain, vice, value |
| **Compare Managers** | Pick 2 managers → see squad overlap, unique picks, shared players |
| **Transfers & Chips** | Most common transfers, chip usage tracker with pie chart |
| **My Team vs League** | Your differentials (lowest-owned players) and most similar managers |
| **Elite Tracker** | Top 5% managers by overall rank — elite picks, lineup grid, transfers, chips |
| **Analytics** | Squad cost distribution, formation trends, ownership saturation |

### Features
- **League selector** — Switch between 4 leagues (names shown, not IDs)
- **GW selector** — Browse any available gameweek data
- **Dark theme** — Premium dark green/black design
- **Mobile responsive** — Bottom nav bar, scrollable tables, compact for Poco X8 Pro Max (1280×2772)
- **Animations** — Fade-in, grow bars, hover effects, freshness badge
- **Data freshness** — Shows "just now" / "45m ago" / "2h ago" next to data timestamp

---

## Files

| File | Purpose |
|:-----|:--------|
| `index.html` | Main HTML page (dark theme, sidebar navigation, 9 view sections) |
| `app.js` | Single-file JavaScript app (30KB, all logic in one file) |
| `styles.css` | Styling: base + animations + elite tracker + charts + mobile responsive |

---

## Data Contract

The dashboard reads two JSON files per league per gameweek:

### Compact JSON (fast overview)
```
data/gw{N}_league{L}_compact.json
```
Used for: Overview, League Explorer, Manager Explorer, all KPIs.

### Full Data JSON (deep scouting)
```
data/gw{N}_league{L}_data.json
```
Used for: Player Intelligence, Compare, Transfers, My Team, Elite Tracker, Analytics.
Lazy-loaded only when the user opens those views.

### Supported Leagues

| ID | Name |
|:---|:-----|
| 19292 | LIGA KOPAK |
| 58005 | LIGA FPL KK OLD BOYS |
| 687126 | LIGA FPL MALAYSIA |
| 131997 | OVERALL IFE |

---

## How to Modify

### Adding a new view
1. Add a nav button in `index.html` inside `<nav id="nav">`
2. Add a `<section id="yourview" class="view">` element in index.html
3. Add a render function in `app.js` (e.g., `renderYourView()`)
4. Wire it up in the nav click handler and `load()` function
5. Add CSS in `styles.css`

### Changing styles
- **Desktop:** Lines 1-84 of `styles.css` (base CSS)
- **Mobile:** Lines 86+ of `styles.css` (inside `@media(max-width:1000px)` and `@media(max-width:500px)`)

### Adding leagues
1. Edit `LEAGUES` array in `app.js` (line 1-6)
2. Ensure data files exist: `data/gw{N}_league{ID}_compact.json` and `data/gw{N}_league{ID}_data.json`

---

## Deployment

### Netlify (current)
Deployed via manual zip upload using Netlify API. Requires:
- `index.html`, `app.js`, `styles.css`
- `data/gw1_league*.json` (GW data)
- `_redirects` — must contain ONLY `/ /index.html 200` (NOT `/* /index.html 200`)
- `_headers` — forces `Content-Type: application/json` for `/data/*`

### Vercel (alternative)
`vercel.json` in repo root rewrites `/` → `/dashboard/index.html`. Not currently deployed.

### Run Locally
```bash
python -m http.server 8080
# Open http://localhost:8080/dashboard/
```

---

## Known Issues

- **Leagues 19292 and 687126** have no data files yet — they'll show as unavailable
- **Elite Grid** shows 20×20 matrix — scroll horizontally on mobile
- **Data files must be deployed together** with the dashboard HTML/JS/CSS
- **Do NOT use `/* /index.html 200` in `_redirects`** — it breaks JSON file serving

---

## Recent Changes (25 Aug 2026)

- Fixed: JSON files returning HTML instead of JSON (`_redirects` catch-all removed)
- Added: Elite Tracker (top 5% managers, lineup grid, elite picks vs league)
- Added: Analytics (squad cost histogram, formation distribution, ownership)
- Added: Chip pie chart visual
- Added: Mobile responsive design (bottom nav, scrollable tables, compact)
- Added: League names instead of IDs
- Added: Animations, freshness badge, scroll-to-top button
- Fixed: GW discovery scanning 1-38 → 1-5 (stops at first 404)