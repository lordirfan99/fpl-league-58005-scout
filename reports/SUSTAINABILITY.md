# Sustainability Plan: GW2 → GW38

> How to keep the FPL Scout Dashboard and pipeline running automatically
> every gameweek without manual intervention.

---

## Current State (GW1)

| Component | Status | Manual? |
|:----------|:-------|:--------|
| GW data fetch | ✅ Cron job runs every Fri 20:00 UTC | No |
| Analysis reports | ✅ Generated after fetch | No |
| Git commit + push | ✅ Cron job commits data | No |
| Dashboard deploy | ❌ Manual zip upload to Netlify | **Yes** |
| Data files on dashboard | ❌ Only compact.json deployed | **Yes** |
| Live dashboard URL | ✅ fpl-scout-intelligence.netlify.app | — |

**The bottleneck:** Every GW change, someone has to manually zip and upload to Netlify. The network keeps timing out on 568KB uploads.

---

## The Fix: GitHub → Netlify Auto-Deploy

### How it works

```
Pipeline runs (cron) → Fetches GW data → Generates reports
    → Git commit + push to master
    → GitHub triggers Netlify webhook
    → Netlify builds from repo (no zip upload)
    → Dashboard auto-updates
```

### Step 1: Link Netlify to GitHub (one-time)

1. Go to https://app.netlify.com/sites/fpl-scout-intelligence
2. Settings → Build & Deploy → Continuous Deployment
3. Link to GitHub repo: `lordirfan99/fpl-league-58005-scout`
4. Branch: `master`
5. Build command: `echo "Static site, no build needed"`
6. Publish directory: `/` (repo root)
7. Deploy settings: Auto-publish on every push

Once linked, EVERY push to master auto-deploys to Netlify. No zip uploads, no network timeouts.

### Step 2: Update the cron job to push after each GW

The cron job already runs `fetch_gw_data.py → generate_analysis.py → git commit + push`. We need to ensure:
- The push actually happens (it's already in the pipeline)
- The commit message includes the GW number (already done)
- The push triggers the Netlify webhook

### Step 3: Make the dashboard auto-discover new GWs

The `discover()` function in `app.js` scans for available GW data files. It already works:
- Scans GW1-5 (stops at first 404)
- When GW2 data is pushed, it auto-appears in the dropdown
- No code changes needed for new GWs

---

## What's Already Working

### ✅ Cron job (fpl-gw-scout)
- Runs every Friday 20:00 UTC
- Fetches GW data for all 2,232 managers
- Generates analysis reports
- Commits to GitHub

### ✅ Dashboard auto-discovery
- `discover()` scans for available GWs
- GW dropdown populates automatically
- No manual config needed per GW

### ✅ Data contract
- `data/gw{N}_league{L}_compact.json` and `data/gw{N}_league{L}_data.json`
- Both files generated per league per GW
- Dashboard reads both formats

### ✅ Netlify redirects fixed
- `_redirects`: `/ /index.html 200` (no catch-all)
- `_headers`: Force `Content-Type: application/json` for `/data/*`
- JSON files serve correctly (no more HTML-instead-of-JSON bug)

---

## What Needs To Be Done

### Medium Priority (do before GW2)

| Task | Effort | Impact |
|:-----|:-------|:-------|
| Link Netlify to GitHub | 5 min | Eliminates manual deploys forever |
| Test the cron push after GW2 | 10 min | Confirms auto-deploy works |
| Add `_headers` to the deploy | Already done | Data files serve correctly |

### Low Priority (nice to have)

| Task | Effort | Impact |
|:-----|:-------|:-------|
| GitHub Actions to auto-deploy on push | 30 min | Alternative to Netlify webhook |
| Discord notification when new GW data is live | 20 min | Alerts league members |
| Auto-sync the cron job with FPL deadlines | 15 min | No manual GW number |
| Dashboard shows "GW2 data available" badge | 10 min | Visual indicator |

---

## Resilience Against Failures

### What if the FPL API is down?
- The cron job should retry in 1 hour (up to 3 retries)
- The dashboard remains usable with old GW data
- Users see the freshness badge showing "2d ago" instead of "just now"

### What if the cron job misses a deadline?
- The pipeline has a `--gw` flag to backfill manually
- `python scripts/run_gw_pipeline.py --gw 2` works any time
- Data is committed to git, so nothing is lost

### What if Netlify deploy fails?
- Push to GitHub again (re-triggers deploy)
- Or use Vercel as fallback (vercel.json already in repo)
- Or manually zip upload (slow but works)

### What if the dashboard code has a bug?
- Old version is still deployed (Netlify keeps last good deploy)
- Rollback: Netlify dashboard → Deploys → click previous deploy → Restore
- Or: push a fix to master → auto-deploy

---

## Costs

| Item | Cost | Notes |
|:-----|:-----|:------|
| Netlify (free tier) | $0 | 100 GB bandwidth, 300 build minutes/month |
| GitHub (free) | $0 | Public repo, unlimited collaborators |
| FPL API | $0 | Public, no rate limit issues at 2,232 managers |
| Cron job (local machine) | $0 | Runs on your Windows PC |
| **Total** | **$0/month** | |

If you want cloud-based cron (not dependent on your PC):
- GCP e2-micro ($6-8/month) or Oracle Cloud free tier ($0)
- Telegram bot to monitor and send alerts

---

## Timeline: Before GW2 Deadline

| Day | Action |
|:----|:-------|
| Today | Link Netlify to GitHub (Step 1) |
| Today | Test push triggers auto-deploy |
| Fri (GW2 deadline) | Pipeline runs automatically at 20:00 UTC |
| Fri + 5 min | GitHub receives push |
| Fri + 10 min | Netlify auto-deploys |
| Fri + 12 min | Dashboard shows GW2 data |

---

## Summary

**The system is already 80% sustainable.** The only missing piece is linking Netlify to GitHub for auto-deploy. Once that's done:

1. Cron job runs → fetches GW2 data → generates reports → commits + pushes
2. GitHub → Netlify webhook → auto-deploy
3. Dashboard auto-discovers GW2 → users see new data
4. Repeat for GW3 → GW38 with zero manual steps

**Netlify + GitHub link is the single most impactful change.** Everything else is already automated.