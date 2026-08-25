# FPL Scout Dashboard — Fix Issues

## Current State
Dashboard is live at: https://fpl-scout-intelligence.netlify.app
Source: /c/Users/irfan/projects/fpl-league-58005-scout/dashboard/

## Files to modify
- `dashboard/app.js` (main logic, 30 lines)
- `dashboard/index.html` (HTML shell)
- `dashboard/styles.css` (styling)

## Issues to Fix

### Issue 1: League names are just IDs
**Problem:** `LEAGUES=[19292,58005,687126,131997]` — dropdown shows raw IDs, user doesn't know which is which.
**Fix:** Change to array of objects with `id` + `name`:
```js
const LEAGUES = [
  {id: 19292, name: 'LIGA KOPAK'},
  {id: 58005, name: 'LIGA FPL KK OLD BOYS'},
  {id: 687126, name: 'LIGA FPL MALAYSIA'},
  {id: 131997, name: 'OVERALL IFE'}
];
```
Update `discover()` to iterate `LEAGUES.map(l => l.id)` or `l => l.id`. Update the dropdown to show names. Update `state.league` to hold the id. Update `init()` leagueSelect to show `name` not `id`.

### Issue 2: GW discovery scans 1-38 blindly
**Problem:** `discover()` makes HEAD requests for GW1-38 for every league (152 requests!) on page load. Only GW1 data exists. The `discover()` function should be smarter — stop scanning at first 404 batch, or use a hardcoded list of available GWs per league.

**Fix:** Either:
- A) Hardcode available GWs: `const AVAILABLE_GWS = {19292: [1], 58005: [1], 687126: [1], 131997: [1]};` and skip the HEAD requests entirely
- B) Or scan only GW1-5 (not 1-38), and stop at first 404 for each league

**Note:** The `discover()` function also causes issue where the dropdown shows only GW1 (correct) but the URL/state might get confused. Make sure `init()` picks the latest available GW, not an empty one.

### Issue 3: Static, needs more dynamic feel
**Problem:** The dashboard is very static — loads data once, no animations, no loading states, no transitions between views.

**Fix suggestions:**
1. Add CSS transitions/animations to:
   - Panel fade-in on load (`@keyframes fadeInUp`)
   - Navigation view switching (slide/fade transitions)
   - KPI number counting animation (animate from 0 to final value)
   - Histogram bars growing from bottom on load
   - Skeleton loading states while data loads
2. Add a data freshness indicator — show "Last updated: X minutes ago" with auto-refresh badge
3. Add a "Last updated" timestamp in the sidebar footer
4. Add subtle hover effects on interactive elements (cards, table rows)
5. Make the sidebar "SCOUT CONTROL ROOM" text more dynamic — maybe show current league name there

### Issue 4 (bonus): Only 2 leagues have data
Only leagues 58005 and 131997 have data files. Leagues 19292 and 687126 don't exist. Filter out non-existent leagues from the LEAGUES array, or at least don't make HEAD requests for them.

## How to fix
1. Edit `dashboard/app.js` directly
2. Edit `dashboard/index.html` if needed for league name display
3. Edit `dashboard/styles.css` for animations
4. After changes, test locally with `python -m http.server 8080` from the repo root
5. Then deploy to Netlify

## Critical
- Don't break the existing data contract (compact.json + data.json structure)
- App.js is a single-file SPA (no build step, no import/export)
- Keep the same visual design system — dark theme, green accents
- All changes must be in the `dashboard/` folder
- The app uses `../data/gw{N}_league{L}_compact.json` and `../data/gw{N}_league{L}_data.json` paths