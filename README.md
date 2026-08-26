# Fantasy Scout Control Centre

Production FPL decision, league-intelligence and competitive-alignment system for the 2026/27 season.

- Dashboard: https://fpl-scout-intelligence.netlify.app
- Personal FPL entry: `2797967`
- Tracked leagues: `58005` (KK Old Boys) and `131997` (Overall IFE)
- Production API: `https://fpl-scout-api-bztsnhv3ea-uc.a.run.app`
- Repository owner: `lordirfan99`

## Operational status

| Item | Current contract |
|---|---|
| Competitive intelligence | `competitive-v4.0` — read-only API authority |
| Optimizer laboratory | Shadow V3 — separate model, unchanged and non-executing |
| Maximum snapshot age | 12 hours; older or unknown data is stale |
| Real FPL execution authority | Telegram approval flow only |
| Dashboard writes | Disabled |
| Last manual documentation verification | 2026-08-26 UTC |

After deployment, `/health` must report `competitive-v4.0`. A green service alone is insufficient: also confirm the expected GW, snapshot timestamp and `quality_status=valid`. The absence of an alert is not proof that an automated refresh succeeded.

---

# 1. Read this first — zero-knowledge handoff

This section is written for a person who has never used this project before.

You do **not** need to understand Python, Next.js, Google Cloud or the FPL API to operate the system normally. The production system is designed to refresh data, deploy the dashboard and generate model output automatically.

The most important rule is:

> **The website is an analysis and monitoring surface. Telegram remains the approval/execution authority for real FPL actions. Never treat a website suggestion as proof that a transfer, captain change or chip has already been executed.**

For normal weekly operation, your job is mainly to:

1. Open the dashboard.
2. Confirm that the data is current.
3. Read the Assistant competitive phase and alignment score.
4. Read the GCP Autopilot recommendation.
5. Compare it with the competitive-alignment evidence.
6. Review risks, captaincy and transfer rationale.
7. Use Telegram for any action that requires approval/execution.
8. After the GW, allow the automated pipeline to collect and evaluate the result.

Do not manually edit generated JSON data unless you are recovering from a documented failure.

---

# 2. What this system is trying to do

The project is not simply a player-points predictor.

It has two related jobs:

1. **FPL decision quality** — identify strong captain, transfer and squad decisions using projections, fixtures, availability and multi-GW planning.
2. **Competitive positioning** — understand what strong managers own and decide when our team should align with them and when a model-supported deviation is justified.

Competitive V4 uses four phases:

| Phase | Meaning | Normal behaviour |
|---|---|---|
| `CATCH` | Squad is materially under-aligned with the validated elite core | Repair important structural gaps; avoid unnecessary differentials |
| `MATCH` | Squad is close to the strong baseline | Maintain the core; preserve transfers and flexibility |
| `ATTACK` | Outside the early catch window, alignment remains below target | Use selective leverage to improve structure; do not blindly copy or punt |
| `CHASE` | Later-season deficit requires more variance | Increase calculated leverage; still avoid unsupported punts |

Early in the season the system is deliberately conservative. GW1/GW2 evidence is noisy and is not allowed to dominate established signals.

Current early-season competitive weighting:

```text
Elite consensus       45%
Projection evidence   45%
Current-season data   10%
```

The current-season component increases as more gameweeks provide evidence:

| Gameweeks | Elite | Projection | Current season |
|---|---:|---:|---:|
| GW1–2 | 45% | 45% | 10% |
| GW3–4 | 40% | 45% | 15% |
| GW5–8 | 30% | 45% | 25% |
| GW9+ | 25% | 45% | 30% |

Unlike the previous implementation, V4 applies these weights directly to a normalized `0–100` competitive score:

- elite component: elite ownership plus elite captaincy;
- projection component: FPL `ep_next` plus fixture difficulty;
- current-season component: form plus points per game;
- availability risk: explicit score penalty and no model-support classification.

The API in `services/api/app/recommendations.py` is the single calculation authority. The Next.js application consumes that response and must not independently reproduce the formula. These remain operational weights rather than permanent truths; backtest and recalibrate them before promotion to any execution path.

> **Namespace warning:** Competitive V4 `CATCH/MATCH/ATTACK/CHASE` describes league-alignment posture. It is separate from any Autopilot captain-variance or execution mode with a similar name. Competitive V4 cannot create or execute an FPL action.

`CHASE` activates only from GW28 when the gap to the tracked league leader is at least `max(40, remaining gameweeks × 5)` points. This deterministic threshold prevents an undocumented switch to high variance.

---

# 3. How to read the competitive layer

## Elite alignment

`Elite alignment` measures how much of the high-consensus elite core is already covered by our squad.

The current core threshold is approximately `60%` elite ownership within the selected elite cohort. The system then compares our squad against that core.

Alignment is **not** a command to blindly copy elite managers.

A missing elite player becomes more important when elite consensus and the projection model agree.

## Player classifications

The competitive model can classify signals approximately as:

| Classification | Interpretation | Operator response |
|---|---|---|
| `ALIGN` | Elite consensus and model support the player | Strong candidate for the common/core structure |
| `CONTROLLED_EDGE` | Model likes the player but elite ownership is lower | Potential calculated differential |
| `INVESTIGATE` | Elite managers like the player but model support is weaker | Do not copy automatically; investigate why signals disagree |
| `AVOID` | Neither evidence source provides enough support | Usually not a priority |
| `NEUTRAL` | No strong strategic instruction | Treat normally |

The key operating principle is:

> **Align where elite consensus and our model agree. Deviate only where the model gives us a defensible reason.**

## Critical core gaps

A `critical core gap` is more important than an ordinary missing elite player. It indicates that our squad is missing a high-consensus asset and the model also supports the asset.

During `CATCH`, repair these before intentionally creating new low-ownership punts unless there is a compelling multi-GW reason not to.

## Controlled edges

A controlled edge is not simply a low-owned player. It must have enough model support to justify being different.

Never interpret `low ownership` by itself as an advantage.

---

# 4. What is live

The production dashboard is the Next.js application in `web-next/`.

The older files in `dashboard/` are retained only as rollback/reference material and are **not** the production UI.

Current views:

- **My Team** — official FPL-style starting XI, bench, GW points and fixtures.
- **Assistant** — primary weekly decision board, competitive phase, alignment, transfer/captain context and elite evidence.
- **GCP Autopilot** — live model plan, safety validation, heartbeat and Telegram handoff.
- **Shadow V3** — uncertainty ranges, component xPts, multi-GW scenarios and promotion gates.
- **Planner** — forward fixture horizon and squad planning.
- **League Explorer** — searchable standings and manager lineup inspection for both tracked leagues.
- **Elite 5%** — each league's top-5% cohort, consensus XI and bench, squad matrix, ownership edges, captaincy, distributions and every elite lineup.
- **Compare** — head-to-head squad overlap, unique picks, captaincy, rank gap and full lineups.
- **Transfers & Chips** — complete-league and elite-cohort transfer consensus plus chip timing.
- **Analytics** — formation, points, squad-value, captaincy and elite ownership distributions.
- **Players** — official player status, availability, price, form and fixture data.

If you only have time to inspect three pages before a deadline, use:

1. Assistant
2. GCP Autopilot
3. Shadow V3 / My Team for supporting evidence

---

# 5. Production architecture in plain English

```text
Official FPL API ───────┐
                       ├─> completed-GW snapshots ─> Cloud Run read API
Tracked FPL leagues ────┘                               │
                                                      v
GCP FPL Autopilot VM ─> read-only bridge ─────────> Next.js on Netlify
        │                                             │
        └─ Telegram approval ─> hardened executor     └─ analysis only
```

In simple terms:

- The **FPL API** supplies official public game/player/league information.
- **GitHub automation** stores validated completed-GW snapshots.
- **Cloud Run** exposes read-only data to the application.
- The **GCP VM** runs the Autopilot/model process.
- The **bridge** lets the dashboard read the model plan without giving the browser execution authority.
- **Netlify** hosts the dashboard.
- **Telegram** is intentionally kept as the approval/execution boundary.

---

# 6. Safety boundary — do not bypass this

The architecture deliberately separates analysis from execution.

- The website and Cloud Run API have no FPL write endpoint.
- The browser must never receive the bridge bearer token, Telegram token or FPL cookies.
- Telegram remains the approve/reject surface.
- Shadow V3 is read-only.
- Competitive alignment is advisory evidence, not execution authority.
- A generated recommendation must not silently mutate the live FPL team.

If a future developer proposes putting FPL credentials directly in the frontend, reject that change.

If the dashboard and Telegram disagree about whether an action was executed, verify the live FPL team rather than assuming the dashboard is authoritative.

---

# 7. Normal weekly operator workflow

## A. After a gameweek finishes

Normally you do nothing immediately.

GitHub automation checks whether FPL marks the GW as both:

```text
finished = true
data_checked = true
```

Only then should the completed-GW snapshot become trusted historical data.

The automated collection validates both tracked leagues before committing the new snapshot.

After collection, check the dashboard and make sure the previous GW information is visible and sensible.

Do not panic if the snapshot does not update immediately after the final whistle. FPL must finish processing the gameweek first.

## B. Early in the new decision cycle

Open **Assistant**.

Record mentally or externally:

- competitive phase;
- elite alignment percentage;
- elite-core coverage;
- critical core gaps;
- controlled edges;
- current GW points versus elite reference;
- major squad availability risks.

During early-season `CATCH`, the first question is:

> Are we structurally weaker than the strong baseline?

Do not immediately ask:

> Which differential can rescue the points lost last week?

One GW of bad variance is not enough evidence to abandon a good structure.

## C. Review the Autopilot plan

Open **GCP Autopilot**.

Check:

- recommended transfer;
- captain;
- expected gain;
- whether a hit is involved;
- status/heartbeat;
- engine version;
- whether the recommendation is current rather than an old artifact.

Always read the gain basis. Competitive V4 transfer `xpts_gain` is **next-GW gross projection difference against the named same-position outgoing player**. It excludes hits, free-transfer opportunity cost, price changes and multi-GW transfer-path cost. The GCP Autopilot horizon/net fields are separate and must state whether hits are already deducted.

A recommendation with a large headline gain should still be checked against:

- player availability;
- next-GW projection;
- multi-GW projection;
- elite/core exposure;
- future transfer consequences;
- whether it requires a hit;
- whether it destroys captaincy or chip structure.

## D. Compare Autopilot with competitive evidence

Typical interpretation:

### Autopilot + elite/model consensus agree

This is the cleanest decision class.

Example conceptually:

```text
Autopilot: BUY Player A
Elite core: Player A 78%
Projection: strong
Classification: ALIGN
```

This is a strong structural candidate.

### Autopilot likes a low-elite player

Check whether it is labelled a controlled/model-supported edge.

Do not reject it just because elite ownership is low, but do not accept it merely because it is different.

### Elite consensus likes a player but model does not

Treat as `INVESTIGATE`.

Possible reasons include:

- model weakness;
- elite managers planning multiple weeks ahead;
- captaincy access;
- price structure;
- stale projection data;
- genuine herd behaviour.

Do not automatically copy.

## E. Captain review

Captaincy can create more weekly variance than an ordinary squad difference.

Before approval, check:

- Autopilot captain;
- projected points;
- availability/minutes risk;
- elite captaincy concentration;
- whether deviating is intentional or accidental.

During `CATCH`, unnecessary captain punts are generally undesirable. A differential captain should have a genuine projection/strategic justification.

## F. Transfer review

Before approving any transfer, ask:

1. Is the outgoing player actually a problem?
2. Does the incoming player improve next GW?
3. Does the move improve the multi-GW horizon?
4. Is this repairing a critical structural gap?
5. Are we chasing last week's points?
6. Can the transfer be rolled instead?
7. Is a hit required?
8. Does the move block a likely next transfer?
9. Does it damage team value/formation flexibility?
10. Is the recommendation based on current data?

## G. Final deadline check

Close to the deadline:

- confirm player availability/news;
- confirm the model/bridge heartbeat is current;
- confirm the intended captain;
- confirm the intended transfer and hit cost;
- confirm chip status;
- use Telegram for approval/execution;
- verify the live FPL team if execution status is uncertain.

Never rely on memory for a high-impact action near deadline.

---

# 8. Wildcard operating rule

Do **not** Wildcard solely because our previous GW score was below elite managers.

The Wildcard becomes more defensible when multiple signals show structural damage, for example:

- low elite alignment;
- several critical core gaps;
- weak multi-GW projection;
- injuries/minutes problems;
- poor team structure that cannot be repaired efficiently with free transfers;
- substantially better projected squad after Wildcard.

Compare at least these three paths conceptually:

```text
A. Keep / roll
B. Use free transfer(s)
C. Wildcard
```

Evaluate the squad after the move, not only the immediate incoming player.

The system should eventually quantify these paths more deeply; until then, Wildcard remains a deliberate human-reviewed decision.

---

# 9. Shadow V3 lifecycle

Shadow V3 exists so experimental modelling can be tested without silently taking control.

1. Inside the pre-deadline window, the VM generates `v3_shadow_gwN.json`.
2. The dashboard shows captain distribution, candidate ranking and multi-GW planning evidence.
3. After FPL marks the GW finished and data-checked, evaluation compares projections with actual outcomes.
4. Promotion requires enough evaluated GWs, acceptable calibration, improved decision metrics and explicit approval.
5. A completed-GW artifact is historical evidence, not a current recommendation.

Do not promote a model because it happened to pick one player who hauled.

The correct question is whether the model improves decision quality across a meaningful sample.

---

# 10. Automatic season pipeline

| Trigger | Automation | Result |
|---|---|---|
| Every 2 hours on VM | `fpl-auto-runner.timer` | Live plan, Shadow V3 snapshot, post-GW review and promotion evaluation |
| Every 4 hours on GitHub | `refresh-gameweek.yml` | Detect finished/data-checked GW, collect both leagues, validate and commit snapshots |
| Daily on GitHub | `refresh-fixtures.yml` | Refresh forward official fixtures |
| Push affecting `web-next` | Netlify Git integration | Build/deploy production frontend |
| Push affecting API/snapshots | `deploy-api.yml` | Build and deploy Cloud Run read API |
| Every 5 minutes on VM | `fpl-dashboard-bridge-sync.timer` | Pull reviewed bridge code, compile, install, health-check and rollback on failure |

The system is intended to progress through the season without a manual deployment every GW.

Human approval is still intentionally required for real FPL actions.

---

# 11. Quick health check for a non-technical operator

Before trusting recommendations, check:

- Dashboard loads.
- Correct GW is displayed.
- My Team contains the expected 15 players.
- Assistant shows a competitive phase and alignment data.
- Autopilot is connected/current.
- No obvious stale-data warning is visible.
- Player availability looks plausible.

If all of these are true, normal analysis can continue.

If something looks wrong, **do not compensate by manually guessing data into the repository**. Use the troubleshooting section below.

---

# 12. Technical health checks

Public API:

```powershell
Invoke-RestMethod https://fpl-scout-api-bztsnhv3ea-uc.a.run.app/health
```

Bridge:

```powershell
Invoke-RestMethod https://sportmania.duckdns.org/fpl-autopilot/health
```

On the VM:

```bash
systemctl is-active fpl-bot.service
systemctl is-active fpl-dashboard-bridge.service
systemctl is-active fpl-dashboard-bridge-sync.timer
systemctl list-timers --all | grep fpl
journalctl -u fpl-dashboard-bridge-sync.service -n 50 --no-pager
```

The control-centre payload should retain the safety properties:

```text
writes_enabled: false
execution_authority: telegram
```

If those properties unexpectedly change, investigate before using the system for decisions.

---

# 13. Troubleshooting decision tree

## Dashboard does not load

1. Check whether Netlify deployment is healthy.
2. Check the latest GitHub Actions validation result.
3. If the frontend deployment failed after a new commit, inspect the build error.
4. Roll back to the previous known-good deploy if necessary.

## Dashboard loads but data looks old

1. Confirm which GW FPL currently considers finished/data-checked.
2. Check `refresh-gameweek.yml`.
3. Check whether the latest snapshot exists under `data/`.
4. Check Cloud Run health.
5. Remember that a just-finished GW may not yet be data-checked.

## Assistant has no competitive information

1. Confirm the correct league snapshot is available.
2. Confirm managers have complete 15-player squads.
3. Confirm the frontend is on the latest `master` deployment.
4. Run frontend typecheck/build if a recent code change touched the model.

## Autopilot shows offline/unavailable

1. Do not substitute a website elite heuristic as an executable recommendation.
2. Check bridge health.
3. Check `fpl-bot.service`.
4. Check `fpl-dashboard-bridge.service`.
5. Check bridge-sync timer/logs.
6. Restore the last known-good bridge if the new bridge is unhealthy.

## Recommendation looks absurd

Do not execute first and debug later.

Check:

- data timestamp;
- player status;
- fixture mapping;
- xPts/projection inputs;
- whether a completed historical artifact is being mistaken for the current plan;
- whether the player is classified `INVESTIGATE` because elite/model signals disagree;
- whether the recommendation violates budget/position/team constraints.

## GitHub workflow fails

Open the failed workflow and identify which stage failed.

Typical categories:

- dependency/install failure;
- TypeScript/build failure;
- Python test failure;
- snapshot validation failure;
- Google Cloud authentication/deployment failure.

Fix the underlying cause rather than disabling the validation gate.

---

# 14. Local development from a fresh computer

These instructions are for a developer or technical maintainer.

Required software:

- Git
- Node.js/npm compatible with the project lockfile
- Python 3
- GitHub access to the repository

Clone and enter the repository:

```powershell
git clone https://github.com/lordirfan99/fpl-league-58005-scout.git
cd fpl-league-58005-scout
```

Install and start the frontend:

```powershell
cd web-next
npm ci
npm run dev
```

Open the local URL printed by Next.js, normally `http://localhost:3000`.

The production read API is the built-in default. Set `FPL_API_BASE_URL` only when testing another API deployment.

Validate frontend changes before pushing:

```powershell
npm run typecheck
npm run build
```

Validate the API:

```powershell
cd ..\services\api
python -m pip install -r requirements.txt
$env:PYTHONPATH='.'
python -m pytest tests
```

Do not push a known failing build to `master`.

---

# 15. Production deployment

Normal production deployment is automatic.

## Frontend

Netlify is connected to the repository's `master` branch. A reviewed push affecting the frontend triggers a production build/deployment.

Required production environment variable:

```text
FPL_API_BASE_URL=https://fpl-scout-api-bztsnhv3ea-uc.a.run.app
```

## API

GitHub Actions deploys the read API to Cloud Run through Google Workload Identity Federation and Cloud Build.

Do not introduce long-lived Google service-account JSON keys into the repository.

## VM bridge

The VM sync timer checks reviewed bridge code and automatically performs compile/install/health-check/rollback behaviour.

For the complete one-time infrastructure setup and rollback commands, read `DEPLOYMENT.md`.

---

# 16. Repository map

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
DEPLOYMENT.md             Infrastructure setup, operations and rollback
README.md                 Main zero-knowledge operator/developer handoff
```

When taking over the project, start with `README.md`, then use `DEPLOYMENT.md` only when infrastructure or deployment work is required.

---

# 17. Data quality gates

A completed-GW snapshot is committed only when:

- FPL reports the GW as both `finished` and `data_checked`;
- both configured leagues are present;
- every manager has 15 players;
- every manager has a legal 11-player starting lineup in the first 11 FPL pick positions;
- multiplier validation is chip-aware: normally 11 players score, while Bench Boost permits all 15;
- captain, vice-captain and positional squad/lineup structure are valid;
- no manager fetch failed;
- full and compact manager counts match.

Failed validation should leave the previous production snapshot untouched.

Never weaken these checks simply to force a broken data refresh through production.

---

# 18. Rules for future developers and AI agents

Preserve these invariants unless the owner explicitly redesigns the architecture:

1. **Read and understand the existing architecture before modifying it.**
2. **Do not put FPL credentials, Telegram secrets or bridge bearer tokens in browser code.**
3. **Do not turn Shadow V3 into an execution engine without the promotion process.**
4. **Do not replace Autopilot authority with a frontend heuristic.**
5. **Do not interpret elite ownership as proof a player should be bought.**
6. **Do not interpret low ownership as proof of an edge.**
7. **Preserve Competitive V4 Catch/Match/Attack/Chase semantics when modifying competitive logic.**
8. **Keep early-GW evidence conservative until calibration supports increasing it.**
9. **Run tests/typecheck/build after meaningful changes.**
10. **Keep production data validation fail-closed.**
11. **Prefer additive/backward-compatible API changes where practical.**
12. **Document any operational behaviour that a future zero-knowledge operator must know.**

When changing model weights, thresholds or promotion criteria, document **why** they changed and what evidence supports the change.

---

# 19. Handoff checklist

A new operator should be able to answer all of these before taking sole control:

- [ ] I know the dashboard URL.
- [ ] I know which FPL entry is being managed.
- [ ] I know the two tracked league IDs.
- [ ] I understand that the website is read-only/analysis-oriented.
- [ ] I understand that Telegram is the execution approval surface.
- [ ] I know what `CATCH`, `MATCH`, `ATTACK` and `CHASE` mean.
- [ ] I know what elite alignment measures.
- [ ] I understand `ALIGN`, `CONTROLLED_EDGE`, `INVESTIGATE`, `AVOID` and `NEUTRAL`.
- [ ] I know not to chase one-GW points blindly.
- [ ] I know how to check API and bridge health.
- [ ] I know where to look when data is stale.
- [ ] I know that completed-GW data must pass validation.
- [ ] I know that Shadow V3 requires evaluation/promotion before authority changes.
- [ ] I know where `DEPLOYMENT.md` is.
- [ ] I know how to roll back instead of improvising on production.

If a new operator cannot answer these, they should continue using the system in observation mode until they can.

---

# 20. Recommended improvement roadmap

The competitive layer is intentionally incremental. High-value future work includes:

1. Replace current-rank-heavy elite selection with **historically weighted proven-elite consensus**.
2. Add richer effective-ownership/captaincy exposure.
3. Add opponent-relative value and threat/shield/sword analysis.
4. Add Monte Carlo comparison against the relevant elite cohort.
5. Add transfer-path optimisation across several GWs rather than isolated moves.
6. Add Wildcard/chip scenario comparison.
7. Backtest and recalibrate Competitive V4 weights, component normalization and phase thresholds.
8. Add decision attribution so good process is separated from lucky/unlucky outcomes.

Do not rush these components into execution authority. Introduce major predictive changes in shadow/read-only form first, collect evidence, then promote deliberately.

---

# 21. Ownership and source

Owner: `lordirfan99`

Primary public data source: Fantasy Premier League public API.

This repository is an independent FPL analysis/decision-support project. Always verify consequential deadline actions against the live FPL team and current player information.
