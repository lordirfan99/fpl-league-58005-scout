# FPL Scout V5 — Player Intelligence & Competitive Decision Engine
## Full audit, research findings, implementation specification, examples, tests, rollout gates, and agent handoff

**Repository audited:** `lordirfan99/fpl-league-58005-scout`  
**Audit branch:** `master`  
**Repository tree observed:** `9a2db4609b6848e1480f34963ca0a6108304c5f2`  
**Research date:** 28 August 2026  
**Target season:** Fantasy Premier League 2026/27  
**Recommended new projection model name:** `projection-v5.0-lab`  
**Existing competitive production model:** keep `competitive-v4.0` active until promotion gates are passed.

**Existing active shadow candidate:** preserve the currently running **V4.2** experiment exactly as-is.  
**V5 governance rule:** V5 must begin as `projection-v5.0-lab`, not as another promotion-eligible shadow candidate.

> **Critical revision:** The repository already has an active V4.2 shadow-model lifecycle. V5 must not overwrite, reset, rename, merge into, or contaminate V4.2's live-shadow history, paired rows, calibration metrics, promotion gates, or registry state. V4.2 remains the only active promotion-eligible challenger until its current lifecycle reaches a pass/fail decision.

---

# 0. Purpose of this document

This document is the implementation brief for upgrading the existing FPL Scout system from a strong **league-intelligence / competitive-alignment product** into a stronger **player forecasting + decision system**.

The main objective is **not** to replace the good parts of the repository.

The correct direction is:

```text
KEEP:
- league intelligence
- elite-manager monitoring
- CATCH / MATCH / ATTACK / CHASE strategy
- read-only dashboard
- Cloud Run API
- GCP Autopilot bridge
- Telegram approval/execution boundary
- freshness / quality checks
- shadow-model promotion controls

IMPROVE:
- player projection quality
- expected-minutes modelling
- opponent modelling
- previous-season priors
- current-season underlying-performance modelling
- defensive-contribution modelling
- clean-sheet / goalkeeper modelling
- uncertainty / probability distributions
- captain ranking
- transfer valuation
- candidate-player universe
- early-season elite-cohort definition
- model validation and backtesting
```

The most important architectural rule is:

> **Prediction and competitive strategy must be separated.**

A player's football projection must answer:

> "How many FPL points do we expect this player to score, and with what uncertainty?"

Only after that should the competitive layer ask:

> "Given elite ownership, our league position, captaincy exposure and risk posture, should we align with this player or deliberately deviate?"

Do **not** mix popularity into the mathematical football forecast.

---

# 1. Executive assessment

## 1.0 Existing V4.2 shadow must be preserved

The repository already has three distinct model roles and they must remain separate:

| Lane | Model | Purpose | Promotion eligible now? |
|---|---|---|---|
| Production | `competitive-v4.0` + V4.1 horizon optimizer | Real decision support | Already production |
| Active shadow | **V4.2** | Existing controlled challenger | **Yes** |
| Research / laboratory | `projection-v5.0-lab` | Build and evaluate the new player-intelligence architecture | **No** |

The correct model-governance structure is:

```text
PRODUCTION
competitive-v4.0
      │
      ├── V4.1 horizon optimizer
      └── real recommendations / Telegram approval

ACTIVE SHADOW
V4.2
      │
      ├── keep existing shadow-GW history
      ├── keep paired-row count
      ├── keep calibration / policy gates
      └── remain promotion eligible

RESEARCH / LAB
projection-v5.0-lab
      │
      ├── independent player xPts
      ├── expected minutes
      ├── underlying xG/xA
      ├── opponent model
      ├── previous-season prior
      ├── 2026/27 DC / GK / CS model
      ├── uncertainty
      └── multi-GW transfer EV
```

### Hard governance rule

> **Do not modify V4.2's formula halfway through its shadow run.**

If V4.2 has already collected live evidence, changing its behaviour materially would make the six-GW shadow record statistically inconsistent.

Bad:

```text
V4.2 GW2 = old formula
V4.2 GW3 = old formula
V4.2 GW4 = new V5 xG/minutes/opponent engine
V4.2 GW5 = new formula
```

This is no longer one model.

Correct:

```text
V4.2
= frozen active-shadow candidate

projection-v5.0-lab
= separate research challenger
```

### V5 may still collect live comparisons immediately

V5 does not need to wait to be useful.

For each target GW, store a parallel comparison:

```text
FPL ep_next
competitive-v4.0
V4.2 active shadow
projection-v5.0-lab
actual FPL points
```

Example:

```text
GW2 Player X

FPL ep_next         6.0
V4.0                6.2
V4.2                6.7
V5 Lab              7.1
Actual              8
```

V5's laboratory data are valuable for research and benchmarking, but they must not be counted as V4.2 shadow evidence and must not inherit V4.2's promotion status.

### What happens when V4.2 completes its current shadow lifecycle?

If V4.2 passes:

```text
production:
    promote V4.2 only after existing gates + explicit owner approval

research:
    keep projection-v5.0-lab
```

Then V5 may become the **next formal shadow candidate** against the newly approved production baseline.

If V4.2 fails:

```text
production:
    keep current approved production model

v4.2:
    mark rejected / retired candidate

v5:
    may become the next formal shadow candidate
```

V5 must not be auto-promoted in either scenario.


## 1.1 What the current system already does well

The existing repository has a much stronger operational architecture than a normal hobby FPL script.

It already has:

- a FastAPI read API;
- validated completed-gameweek snapshots;
- league hydration and freshness checks;
- multiple tracked leagues;
- elite ownership and captaincy analysis;
- a Next.js control centre;
- a separate Autopilot bridge;
- a Telegram execution boundary;
- shadow-model concepts;
- explicit model versions;
- promotion gates;
- multi-gameweek fixture plumbing;
- CI tests;
- documentation for handoff.

These should remain.

The repository README also already states the right strategic principle:

```text
Align where elite consensus and our model agree.
Deviate only where the model gives us a defensible reason.
```

That principle is good.

The current weakness is that **"our model" is not yet independent or deep enough**.

---

# 2. Current implementation: what is actually happening

The important production logic is currently in:

```text
services/api/app/recommendations.py
```

At the time of this audit the player signal is approximately:

```python
elite_component =
    0.80 * elite_ownership
  + 0.20 * elite_captaincy

projection_component =
    0.85 * normalized(FPL ep_next)
  + 0.15 * normalized(FDR)

current_component =
    0.65 * normalized(FPL form)
  + 0.35 * normalized(points_per_game)
```

Then:

```text
competitive_score =
    elite_weight * elite_component
  + projection_weight * projection_component
  + current_weight * current_component
```

Current early-season weights are:

| Period | Elite | Projection | Current season |
|---|---:|---:|---:|
| GW1–2 | 45% | 45% | 10% |
| GW3–4 | 40% | 45% | 15% |
| GW5–8 | 30% | 45% | 25% |
| GW9+ | 25% | 45% | 30% |

This is a sensible **competitive heuristic**, but it is not yet a strong independent football projection model.

The system is mostly combining:

1. what elite managers already own;
2. what FPL's own `ep_next` says;
3. FPL FDR;
4. recent FPL points.

That can help stay near the template, but it limits the amount of new predictive edge the system can create.

---

# 3. Priority findings — what I would complain about or change

Priority definitions:

```text
P0 = fix before calling V5 a serious player-intelligence engine
P1 = important for stronger decision quality
P2 = useful later; do not delay the core model
```

---

## P0-1 — Prediction and strategy are mixed together

### Current problem

Elite ownership and previous elite captaincy contribute directly to the same score used for:

- transfer ranking;
- captain ranking;
- player support classification.

This creates a circular effect:

```text
popular with elite managers
        ↓
higher score
        ↓
system says player is better
        ↓
system aligns with elite managers
```

Popularity can be strategically important, but it is not evidence that a player has a higher underlying probability of scoring.

### Required change

Create two distinct concepts:

```text
A. football_projection
   - expected FPL points
   - expected minutes
   - scoring probabilities
   - uncertainty
   - opponent context

B. competitive_strategy
   - elite ownership
   - elite exposure
   - league gap
   - phase
   - template alignment
   - leverage
```

Recommended contract:

```text
football xPts = independent of ownership

competitive decision =
    football xPts
    + squad constraints
    + transfer horizon
    + elite exposure
    + league strategy
```

Do not alter `xpts_mean` because a player is popular.

---

## P0-2 — `ep_next` currently does most of the projection work

In the current code:

```text
projection component =
85% FPL ep_next
15% FDR
```

That makes the system heavily dependent on an FPL-provided derived metric.

`ep_next` is useful and should be retained as a **baseline and fallback**, but it should not be the primary source of proprietary model strength.

### Required change

V5 should generate its own point estimate from components:

```text
xPts =
    appearance
  + goals
  + assists
  + clean sheet
  + goalkeeper saves
  + defensive contributions
  + bonus
  + penalty saves
  - goals-conceded deductions
  - card expectation
  - own-goal expectation
  - penalty-miss expectation
```

Then compare V5 against `ep_next` every week.

`ep_next` becomes:

```text
baseline_model = FPL ep_next
candidate_model = V5 xPts
```

This makes improvement measurable.

---

## P0-3 — FPL `form` and PPG are outcome-heavy signals

Current-season evidence is:

```text
65% form
35% points_per_game
```

FPL form is based on recent **actual fantasy points**, and PPG is also based on actual output.

Both are useful display metrics but can chase variance.

### Example

Player A:

```text
GW points: 10
xG:       0.15
xA:       0.02
minutes:  90
```

Player B:

```text
GW points: 2
xG:       0.85
xA:       0.20
minutes:  90
```

If their roles and future fixtures are comparable, the predictive engine should often prefer B despite A's larger previous score.

### Required change

Move `form` and `PPG` to:

```text
display / diagnostics / optional weak feature
```

Make underlying rates the main evidence:

```text
xG / 90
xA / 90
xGI / 90
defensive contributions / 90
saves / 90
minutes / starts
set-piece role
penalty role
clean-sheet environment
```

If richer licensed data are later available, add:

```text
non-penalty xG
shots
shots in box
big chances
key passes
touches in box
```

But V5 must **not depend on an unlicensed scraper** to work.

---

## P0-4 — The collector discards useful fields already available to it

Current:

```text
scripts/fetch_gw_data.py
```

`build_player_map()` stores:

- name
- team
- position
- price
- form
- total points
- PPG
- ownership
- status
- chance of playing
- news

It does not currently preserve many useful projection fields.

The current FPL data ecosystem exposes fields such as:

```text
minutes
starts
expected_goals
expected_goals_per_90
expected_assists
expected_assists_per_90
expected_goal_involvements
expected_goal_involvements_per_90
expected_goals_conceded
expected_goals_conceded_per_90
clean_sheets
saves
saves_per_90
bonus
bps
defensive_contribution
defensive_contribution_per_90
clearances_blocks_interceptions
tackles
recoveries
penalties_order
direct_freekicks_order
corners_and_indirect_freekicks_order
```

### Required change

Extend the data contract before changing the model.

Do **not** build V5 on fields that are not persisted and validated.

---

## P0-5 — Candidate universe is restricted by tracked-manager ownership

This is a major structural limitation.

Current `recommendations.py` builds `known_picks` from the union of players owned by tracked managers:

```python
known_picks = {}

for entry in managers:
    for pick in entry["squad"]:
        known_picks[pick["element"]] = pick
```

The model then generates signals only from those known picks.

### Why this matters

A player who is:

- newly starting;
- newly promoted into a role;
- returning from injury;
- low-owned;
- genuinely overlooked by the tracked league,

may never enter the recommendation universe if nobody in the tracked manager set owns him.

That is exactly the type of player a good independent engine should be capable of discovering.

### Required change

The candidate universe must be:

```text
ALL valid FPL players from bootstrap/catalog
```

not:

```text
all players currently owned by tracked managers
```

Elite ownership should be attached afterward:

```text
elite_ownership = 0.0
```

if the player is not owned by the cohort.

### New flow

```text
bootstrap all players
       ↓
projection for every player
       ↓
legal-position / budget filtering
       ↓
elite ownership enrichment
       ↓
competitive classification
       ↓
transfer optimizer
```

---

## P0-6 — Transfer recommendations can be strategically or legally incomplete

Current transfer generation essentially:

1. finds a missing player;
2. compares him with the weakest player of the same position;
3. recommends the move if signal gain > 5.

The current output explicitly says:

```text
next_gameweek_gross;
transfer cost and hits excluded
```

### Missing constraints

A valid transfer engine must consider:

- actual bank;
- purchase price;
- selling price;
- same-position replacement rule;
- maximum three players per Premier League club;
- free transfers available;
- banked free transfers;
- maximum of five banked free transfers in 2026/27;
- four-point cost for each additional transfer beyond free transfers;
- multi-transfer combinations;
- injury/status;
- future fixtures;
- squad structure;
- chip state;
- opportunity cost of spending a free transfer now.

### Required change

Replace single-GW gross gain with multi-GW **net transfer value**.

Recommended first implementation:

```text
NetTransferGain(H) =
    Σ[h=1..H] discount[h] ×
        (xPts_in[h] - xPts_out[h])
    - hit_cost
    - transfer_opportunity_cost
    + optional_structure_value
```

Use a 4–6 GW planning horizon.

Do not let price or ownership alter raw player xPts.

---

## P0-7 — Captain selection is currently based on competitive score

Current captain candidates are sorted by the same mixed competitive score.

That means an elite-popular player can be promoted partly because he was popular.

### Required change

Captain projection should begin with football probabilities:

```text
captain_xPts
P(5+)
P(10+)
P(15+)
floor / median / ceiling
expected minutes
```

Then competitive strategy may choose between:

```text
SAFE captain
MAX-EV captain
CONTROLLED-LEVERAGE captain
```

depending on phase.

The default should be **max expected points**, not "most popular".

---

## P0-8 — Previous elite captaincy is fixture-specific and should not predict the next fixture directly

The API currently loads a completed-GW league snapshot and then evaluates the following fixture.

Elite ownership from the prior GW is a useful exposure prior.

But a captain choice is highly fixture-specific.

Example:

```text
GW1 elite captained Player X because he had an easy home fixture.
GW2 Player X has a difficult away fixture.
```

Using GW1 captaincy as a direct player-quality input for GW2 is not logically clean.

### Required change

Treat historical elite captaincy as:

```text
retrospective manager behaviour
```

not:

```text
forward player projection
```

For the next GW:

- use V5 captain probabilities;
- use current ownership as an exposure baseline;
- label actual upcoming elite captaincy as unknown before deadline.

After the deadline, calculate realized effective ownership for review.

---

## P0-9 — Early-season "elite = current top 5%" can be noisy

Current `elite_managers()` sorts the tracked population by current overall rank and takes the top 5%.

In GW1–GW3, current overall rank is heavily influenced by one or two outcomes.

The repository already has richer manager-history work in:

```text
scripts/generate_analysis.py
data/scout_report.csv
data/season_history.csv
```

`generate_analysis.py` explicitly loads historical information such as:

```text
scout_score
threat_tier
best_rank
seasons_played
recent_rank
weighted_percentile
```

But the production competitive recommendation path does not currently use that manager prior.

### Required change

Maintain two separate cohorts:

```text
VALIDATED_ELITE
= managers selected from historical multi-season quality

CURRENT_LEADERS
= current top X% by current overall rank
```

Early season:

```text
validated elite should dominate strategic reference
```

Later season:

```text
blend current high-performing managers more heavily
```

Do not erase the current top-5% view; just stop treating it as the only definition of manager quality.

---

## P0-10 — Expected minutes are not a proper model component

Availability is currently handled mainly as:

```text
risk = status not active
or chance_of_playing < threshold

if risk:
    score -= 35
```

A fixed 35-point competitive penalty is a heuristic.

FPL points depend massively on expected minutes.

### Required change

Model minutes explicitly:

```text
p_start
p_bench_appearance
minutes_if_start
minutes_if_bench
p_60_plus
expected_minutes
```

Core equation:

```text
E[minutes] =
    P(start) × E[minutes | start]
  + P(bench appearance) × E[minutes | bench appearance]
```

A fit player who usually gets 65 minutes is not equivalent to a nailed 90-minute player.

A 70%-likely starter is not equivalent to a player who is definitely unavailable.

---

## P0-11 — 2026/27 defensive-contribution scoring is missing from the model

Official 2026/27 FPL scoring awards:

```text
DEF:
2 points after reaching 10
clearances + blocks + interceptions + tackles

MID/FWD:
2 points after reaching 12
clearances + blocks + interceptions + tackles + recoveries
```

This is now a meaningful repeatable source of points.

### Required change

Model threshold probability, not a linear score.

If a defender has an expected 9.5 eligible actions in a match:

```text
P(actions >= 10 | Poisson λ=9.5) ≈ 47.8%

expected DC points ≈
2 × 0.478
= 0.96 points
```

Do **not** calculate:

```text
9.5 / 10 × 2 = 1.90
```

because FPL awards either 0 or 2 at the threshold.

Poisson is a reasonable V1 approximation.

Backtest variance. If action counts are materially overdispersed, use a negative-binomial distribution.

---

## P0-12 — Opponent quality is compressed into FDR

FDR is useful but intentionally compressed to 1–5.

Official FPL explains that FDR uses an algorithm based on Opta variables and home/away form.

That means FDR already contains team-strength information.

### Required change

V5 should create separate opponent components:

```text
opponent defensive strength
opponent attacking strength
home/away effect
recent team form
longer-term team prior
```

Use FDR as:

```text
fallback
or small residual/context feature
```

once a richer opponent model is available.

Do not heavily use both:

```text
FDR + derived opponent xGA
```

without calibration, because that can double-count the same concept.

---

# 4. P1 improvements

## P1-1 — Add probability distributions, not only a point estimate

A mean of 6.5 can describe very different players.

Example:

```text
Player A:
mean 6.5
P10  4
P50  6
P90  10

Player B:
mean 6.5
P10  1
P50  4
P90  15
```

Player A is safer.

Player B has a larger ceiling.

That distinction matters for captaincy and late-season chasing.

### Required outputs

Every player projection should eventually include:

```text
xpts_mean
xpts_p10
xpts_p50
xpts_p90
p_60_plus
p_return
p_10_plus
p_15_plus
```

---

## P1-2 — Add Bayesian / sample-size shrinkage for early season

Do not solve early-season noise only with manually stepped GW weights.

Use the previous season as a **prior**, then let current evidence replace it as minutes accumulate.

For a per-90 metric:

```text
posterior_rate =
    (prior_equivalent_minutes × prior_rate
     + current_minutes × current_rate)
    /
    (prior_equivalent_minutes + current_minutes)
```

Example only:

```text
previous-season xG/90 = 0.60
current-season xG/90  = 1.10
current minutes       = 180
prior equivalent      = 900

posterior xG/90 =
(900×0.60 + 180×1.10) / 1080
≈ 0.68
```

After 1,000+ current minutes, current-season evidence naturally dominates.

### Important

`prior_equivalent_minutes` is a **tuneable hyperparameter**, not a truth.

Tune it by rolling-origin backtests.

Do not hard-code 900 permanently just because it works in an example.

---

## P1-3 — Add recency decay without forgetting sample size

A player's old season data should matter less than recent current data, but a single hot match should not dominate.

Recommended form:

```text
match_weight =
exp(-ln(2) × age_in_matches / half_life)
```

Start testing half-lives such as:

```text
4
6
8
10 matches
```

Choose by out-of-sample performance.

Then combine with the prior/shrinkage system.

---

## P1-4 — Model role changes explicitly

Past performance can become misleading after:

- a transfer to another club;
- a new manager;
- a change in position;
- losing penalties;
- gaining penalties;
- moving onto/off corners;
- becoming a regular starter;
- a major teammate injury changing role.

### Required metadata

Projection diagnostics should include:

```text
role_change_detected
penalty_order
corner_order
direct_fk_order
club_changed
minutes_role_changed
manual_override_reason
```

Manual overrides must be:

- explicit;
- timestamped;
- attributable;
- visible in diagnostics;
- never silent.

---

## P1-5 — Improve team-context / new-club handling

If a player changes club, do not blindly transfer his old team's clean-sheet environment or attacking multiplier.

Split:

```text
player skill prior
team environment prior
```

Example:

```text
Player attacking rate:
mostly follows player, with shrinkage.

Clean-sheet rate:
mostly follows new team.

Expected minutes:
must be recalculated for the new depth chart.
```

For promoted teams, do not directly equate lower-division xG with Premier League xG unless a proper league-strength adjustment exists.

Fallback to:

- FPL team strength/FDR;
- conservative league-average shrinkage;
- current Premier League evidence as it accumulates.

---

## P1-6 — Model FPL assists separately from pure xA

FPL assists are not identical to standard Opta expected assists.

Official FPL can award assists for:

- certain rebounds;
- forced own goals;
- winning a penalty/free kick that is scored;
- some deflected passes under defined conditions.

Therefore:

```text
xA != exact expected FPL assists
```

### Required change

Use xA as the central creative signal, then calibrate:

```text
expected_FPL_assists =
calibrated_function(
    xA,
    historical FPL assists,
    minutes,
    player/position context
)
```

Do not claim that:

```text
1.0 xA = exactly 1.0 expected FPL assists
```

without calibration.

---

## P1-7 — Improve goalkeeper projection

Goalkeepers need separate modelling.

Core components:

```text
expected minutes
clean-sheet probability
expected goals conceded
save distribution
penalty-save probability
bonus expectation
cards
```

### Save points

FPL awards one point for every complete three saves.

Do not simply use:

```text
expected_saves / 3
```

because:

```text
2.9 saves = usually 0 save points
3.1 saves = often 1 save point
```

Instead estimate a save-count distribution and calculate:

```text
E[floor(saves / 3)]
```

A Poisson approximation is acceptable for V1, then verify empirically.

---

## P1-8 — Improve clean-sheet modelling

Use a team-goal model.

If the opponent's expected scoring parameter is `λ`:

```text
P(clean sheet) = exp(-λ)
```

Then player clean-sheet expectation also depends on playing long enough.

For a defender/GK:

```text
expected_CS_points ≈
4 × P(team clean sheet AND player reaches 60)
```

For a midfielder:

```text
expected_CS_points ≈
1 × P(team clean sheet AND player reaches 60)
```

This is a simplification because a substituted player can lock a clean sheet after 60 minutes even if the team later concedes.

The simulation engine should eventually model:

```text
player exit minute
goal timing
```

V1 can use the simplified probability; V2 can improve event timing.

---

## P1-9 — Estimate bonus without pretending it is independent

Bonus is relative to every player in the match.

A player's bonus probability depends on:

- goals/assists;
- clean sheet;
- BPS actions;
- teammate/opponent performances.

2026/27 also changed the BPS rules.

### V1 recommendation

Use historical empirical modelling:

```text
expected_bonus =
f(
    position,
    xG,
    xA,
    CS probability,
    expected saves,
    defensive actions,
    historical BPS / 90,
    expected minutes
)
```

### V2 recommendation

Simulate all players' BPS within the fixture.

Do not attempt an exact BPS simulation until the full 2026/27 BPS event model has been verified.

---

## P1-10 — Historical player-v-opponent record should be tiny and shrunk

This addresses the Haaland-v-Palace question directly.

Historical head-to-head is not worthless, but it has:

- tiny sample sizes;
- changing managers;
- changing defenders;
- changing tactical systems;
- changing player roles.

### Correct implementation

Use it as a capped context modifier.

For example:

```text
h2h_reliability =
n_matches / (n_matches + k)
```

where `k` is a shrinkage constant tuned by backtest.

Then:

```text
raw_h2h_effect
    ↓
shrink toward zero
    ↓
hard cap
```

Recommended maximum V1 impact:

```text
±3% of base xPts
```

or an equivalent small absolute cap.

This cap is an engineering policy, not a proven universal constant. Backtest it.

### Example

Base Haaland projection:

```text
7.20 xPts
```

Historical matchup is strongly positive.

Maximum +3% modifier:

```text
7.20 × 1.03 = 7.416
```

Rounded:

```text
7.42 xPts
```

The historical record adds confidence.

It does **not** turn a 7.2 projection into 10 points just because he scored many times against the opponent previously.

---

# 5. P2 improvements

These are valuable but should come after a reliable V5 projection engine.

## P2-1 — Chip expected-value engine

2026/27 has two sets of:

- Wildcard;
- Free Hit;
- Triple Captain;
- Bench Boost,

one set for each half of the season.

Later build:

```text
Triple Captain:
compare captain distribution across future GWs

Bench Boost:
expected bench points by GW

Free Hit:
best one-week squad EV minus normal-squad EV

Wildcard:
multi-week squad EV after rebuild
minus value of preserving wildcard
```

Do not start here before the player projection model is validated.

---

## P2-2 — Price change as a separate squad-management signal

2026/27 includes an official FPL Price Change Predictor.

Use price information as:

```text
squad-structure / timing context
```

not:

```text
player football ability
```

Example:

```text
Move has +5.2 projected points over 5 GWs.
Target may rise £0.1m before deadline.
```

The UI may flag timing pressure, but late team news and information value must still be considered.

---

# 6. Official 2026/27 FPL scoring that V5 must implement

The 2026/27 scoring engine must reflect the current official rules.

## Appearance

```text
up to 60 minutes: 1 point
60+ minutes:      2 points
```

## Goals

```text
GKP: 10
DEF: 6
MID: 5
FWD: 4
```

## Assists

```text
3 points
```

## Clean sheets

```text
GKP: 4
DEF: 4
MID: 1
FWD: 0
```

## Goalkeeper saves

```text
1 point for every 3 saves
```

## Penalty saved

```text
5 points
```

## Defensive contributions

```text
DEF:
2 points for 10 CBIT
(clearances + blocks + interceptions + tackles)

MID/FWD:
2 points for 12 CBIRT
(CBIT + recoveries)
```

## Negative events

```text
penalty miss:              -2
every 2 goals conceded
by GKP/DEF:                -1
yellow card:               -1
red card:                  -3
own goal:                  -2
```

## Bonus

```text
1–3 points according to BPS ranking
```

Do not copy a previous-season scoring implementation without explicit 2026/27 tests.

---

# 7. 2026/27 BPS implications

The current season changed BPS.

Relevant changes include:

- being tackled no longer gives the old negative BPS deduction;
- clearances, blocks and interceptions now earn 1 BPS per three CBI rather than the previous per-two treatment;
- goalkeeper save BPS was changed;
- big-chance saves now receive an extra BPS component;
- penalty-save BPS was adjusted in connection with that change.

### Engineering implication

Do not hard-code an old BPS table into V5.

For the first release:

```text
bonus = empirical expectation
```

rather than:

```text
pretend exact BPS reconstruction
```

Only implement full BPS simulation after every 2026/27 BPS rule is represented and tested.

---

# 8. Target architecture

Recommended final architecture:

```text
                         ┌─────────────────────────┐
                         │ Official FPL data       │
                         │ + optional provider     │
                         └───────────┬─────────────┘
                                     │
                                     ▼
                         ┌─────────────────────────┐
                         │ Feature Builder         │
                         │ deadline-safe data only │
                         └───────────┬─────────────┘
                                     │
                                     ▼
                    ┌────────────────────────────────┐
                    │ V5 Player Projection Engine    │
                    │                                │
                    │ expected minutes               │
                    │ attacking rates                │
                    │ opponent model                 │
                    │ CS / saves / DC                │
                    │ bonus / negatives              │
                    │ uncertainty                    │
                    └──────────────┬─────────────────┘
                                   │
                          xPts distributions
                                   │
                                   ▼
                    ┌────────────────────────────────┐
                    │ Squad / Transfer Optimizer     │
                    │ legal constraints + horizon    │
                    └──────────────┬─────────────────┘
                                   │
                                   ▼
                    ┌────────────────────────────────┐
                    │ Competitive Strategy V4/V5     │
                    │ elite cohort / alignment / gap │
                    │ CATCH MATCH ATTACK CHASE       │
                    └──────────────┬─────────────────┘
                                   │
                                   ▼
                       Dashboard / Autopilot
                                   │
                                   ▼
                         Telegram approval only
```

Important:

```text
browser remains read-only
Cloud Run remains read-oriented
Telegram remains execution authority
```

Do not weaken this safety boundary for convenience.

---

# 9. Recommended repository changes

## 9.1 New backend modules

Create:

```text
services/api/app/scoring.py
services/api/app/projections.py
services/api/app/projection_types.py
services/api/app/opponent_model.py
services/api/app/transfer_optimizer.py
```

Suggested responsibilities:

### `scoring.py`

Contains only verified 2026/27 FPL scoring rules.

No league strategy.

### `projections.py`

Contains football projection logic:

```text
expected minutes
attacking rates
clean sheets
saves
DC
bonus expectation
negative events
simulation/distribution
```

No elite ownership.

### `projection_types.py`

Typed internal contracts.

### `opponent_model.py`

Team attack/defence and home-away context.

### `transfer_optimizer.py`

Legal squad constraints and multi-GW move valuation.

---

## 9.2 Refactor `recommendations.py`

Do not delete the existing competitive logic.

Change its responsibility from:

```text
calculate quasi-projection + strategy together
```

to:

```text
consume V5 projection
+
add elite/league strategy
```

Conceptually:

```python
projection = projection_index[player_id]

role = classify_competitive_role(
    projection=projection,
    elite_ownership=elite_owned,
    phase=phase,
    ...
)
```

`model_support` should come from projection evidence, for example:

```text
projection quality valid
expected minutes sufficient
horizon xPts competitive
```

not from elite ownership.

---

## 9.3 Extend `repository.py`

Current `SnapshotRepository` already provides:

```text
league()
bootstrap()
fixtures()
fixture_horizon()
```

Add:

```python
def projections(self, gameweek: int) -> dict:
    return self.read(f"projection_gw{gameweek}.json")

def player_history(self) -> dict:
    return self.read("player_history_cache.json")

def team_model(self) -> dict:
    return self.read("team_model_cache.json")
```

Prefer the same local/GCS read mechanism already in the repository.

Do not create a second storage architecture unless needed.

---

## 9.4 Extend `schemas.py`

Add typed output.

Example:

```python
class ProjectionComponents(BaseModel):
    appearance: float
    goals: float
    assists: float
    clean_sheet: float
    saves: float
    penalty_saves: float
    defensive_contribution: float
    bonus: float
    goals_conceded: float
    cards: float
    own_goals: float
    penalty_misses: float

class PlayerProjection(BaseModel):
    player_id: int
    gameweek: int
    fixture_id: int | None

    expected_minutes: float
    p_start: float
    p_60_plus: float

    xpts_mean: float
    xpts_p10: float
    xpts_p50: float
    xpts_p90: float

    p_return: float
    p_10_plus: float
    p_15_plus: float

    components: ProjectionComponents
    data_quality: str
    diagnostics: dict
```

Keep public response types explicit.

Avoid unbounded `dict[str, Any]` for the final V5 projection surface where a stable schema is practical.

---

# 10. Data collection implementation

## 10.1 Extend bootstrap extraction

Update:

```text
scripts/fetch_gw_data.py
```

and/or create a dedicated:

```text
scripts/fetch_player_features.py
```

Persist at least:

```text
id
code
web_name
team_id
team_name
element_type
now_cost

minutes
starts

expected_goals
expected_goals_per_90
expected_assists
expected_assists_per_90
expected_goal_involvements
expected_goal_involvements_per_90
expected_goals_conceded
expected_goals_conceded_per_90

clean_sheets
goals_conceded
saves
saves_per_90
penalties_saved

bonus
bps

defensive_contribution
defensive_contribution_per_90
clearances_blocks_interceptions
tackles
recoveries

penalties_order
direct_freekicks_order
corners_and_indirect_freekicks_order

status
chance_of_playing_next_round
news

ep_next
form
points_per_game
selected_by_percent
```

### Rule

At refresh time, validate field existence and type.

The public FPL API is widely used but not presented as a versioned developer contract.

Therefore:

```text
missing field != silently zero
```

Use:

```text
missing field
→ quality warning
→ documented fallback
```

---

## 10.2 Add per-player match history

Create:

```text
scripts/fetch_player_history.py
```

Recommended input:

```text
bootstrap player IDs
```

Recommended output:

```text
data/model/player_history_current.json
```

Per player-match/GW row:

```text
player_id
fixture_id
gameweek
kickoff_time
team_id
opponent_team_id
was_home

minutes
starts
total_points
goals_scored
assists

expected_goals
expected_assists
expected_goal_involvements
expected_goals_conceded

clean_sheets
goals_conceded
saves
penalties_saved
penalties_missed

bonus
bps

defensive_contribution
clearances_blocks_interceptions
tackles
recoveries

yellow_cards
red_cards
own_goals

value
```

Potential sources:

```text
/element-summary/{player_id}/
/event/{gw}/live/
```

For efficiency, `event/{gw}/live` is attractive for completed-GW bulk collection.

Use `element-summary` for:

- player-specific history;
- previous-season summaries;
- future fixtures;

but cache aggressively rather than making hundreds of calls unnecessarily.

---

## 10.3 Build team match rows

Create:

```text
scripts/build_team_history.py
```

Aggregate player-level xG/xA by fixture/team.

Example:

```text
team_xG =
sum(player expected_goals in fixture for team)

team_xA =
sum(player expected_assists in fixture for team)
```

Create:

```text
team_id
fixture_id
gameweek
home
opponent
goals_for
goals_against
xG_for
xG_against
```

If source completeness is questionable:

```text
quality_status = partial
```

and use FDR/team-strength fallback.

---

# 11. Data-source policy

## Tier 1 — default production source

Use the FPL data already powering the project.

Benefits:

- no new vendor dependency;
- consistent player IDs;
- current xG/xA/xGC;
- defensive contribution data;
- BPS;
- ownership;
- set-piece order;
- FDR;
- status.

This should be sufficient to build a meaningful V5 baseline.

---

## Tier 2 — offline historical bootstrap

For previous seasons, a public historical FPL archive such as the `vaastav/Fantasy-Premier-League` dataset can be useful for research/backtesting.

Use it for:

```text
historical model development
rolling-origin backtests
previous-season priors
```

Do not assume a third-party archive is a guaranteed production SLA.

Cache the exact version used and record provenance.

---

## Tier 3 — optional richer licensed provider

If later adding richer match-event features:

```text
non-penalty xG
shot locations
big chances
key passes
xGOT
team xG models
```

implement a provider interface.

Example:

```python
class FootballDataProvider(Protocol):
    def player_match_features(...): ...
    def team_match_features(...): ...
```

Then adapters can include:

```text
FPLProvider
LicensedProvider
```

Do not hard-code the whole projection model to one commercial vendor.

Do not make an unlicensed scraper a critical production dependency.

---

# 12. Feature model

Create a canonical feature row for each player and target GW.

Example:

```json
{
  "player_id": 123,
  "target_gw": 2,

  "expected_minutes": 84.0,
  "p_start": 0.94,
  "p_60_plus": 0.88,

  "posterior_xg90": 0.62,
  "posterior_xa90": 0.18,
  "posterior_dc90": 5.2,
  "posterior_saves90": 0.0,

  "penalty_order": 1,
  "set_piece_role": "primary_penalties",

  "opponent_attack_multiplier": 0.91,
  "opponent_defence_multiplier": 1.13,
  "home_multiplier": 1.05,

  "fdr": 2,

  "h2h_modifier": 1.01,

  "data_quality": "valid"
}
```

Every feature must be calculated from information available **before the target GW deadline**.

---

# 13. Expected-minutes model

Expected minutes are the most important missing foundation.

## 13.1 Required probabilities

For every player:

```text
P(start)
P(bench appearance | not start)
E(minutes | start)
E(minutes | bench appearance)
P(60+)
```

## 13.2 Starting baseline

A simple V1 can use:

```text
recent starts
recent minutes
season start rate
availability
team rotation pattern
fixture congestion
```

Example concept:

```text
P(start) =
weighted recent start rate
× availability adjustment
× rotation adjustment
```

Do not use arbitrary manual team-news guesses unless stored as explicit overrides.

---

## 13.3 Availability mapping

Do not convert every status to a single fixed penalty.

Use status to influence:

```text
P(start)
P(bench)
```

Example logic:

```text
confirmed unavailable:
P(start)=0
P(bench)=0

fully available nailed player:
high P(start)

doubt:
reduce P(start), but do not automatically make xPts zero
```

---

# 14. Player attacking projection

## 14.1 Primary official-data version

If only FPL xG/xA are available:

```text
expected_goals =
posterior_xG90
× expected_minutes / 90
× opponent_defence_multiplier
× role_multiplier

expected_assists =
calibrated_xA90
× expected_minutes / 90
× opponent_defence_multiplier
```

### Important

Do not double-count:

```text
xG
+
goals scored
+
form
```

as equal-strength independent predictors.

Actual goals can help estimate finishing ability over large samples, but short-term goals are noisy.

Start with a parsimonious model.

---

## 14.2 Penalties

If the data source cannot separate non-penalty xG from penalty xG:

```text
do not invent a precise penalty split
```

V1:

- use FPL xG as observed;
- use penalty order as a role diagnostic / modest prior adjustment.

V2 with an appropriate event/provider dataset:

```text
non-penalty xG
+
expected penalty opportunities × penalty conversion model
```

This is more correct because a change in penalty taker can meaningfully alter future xG.

---

# 15. Opponent model

## 15.1 Separate attack and defence

For target fixture:

```text
opponent_defence_strength
→ affects player's goal/assist expectation

opponent_attack_strength
→ affects clean-sheet / GK expectation
```

Do not use one generic difficulty number for everything.

---

## 15.2 Team prior + recent form

Recommended structure:

```text
team_strength =
shrunken long-term prior
+
recency-weighted current-season evidence
+
home/away adjustment
```

Early season:

```text
previous-season prior matters strongly
```

Later:

```text
current-season evidence dominates naturally
```

---

## 15.3 FDR role

When the richer team model is valid:

```text
FDR = secondary diagnostic / fallback
```

When the richer model is unavailable:

```text
FDR = primary fixture-strength fallback
```

Always expose:

```text
opponent_source
```

Example:

```text
opponent_source = "team-xg-model"
```

or:

```text
opponent_source = "fpl-fdr-fallback"
```

---

# 16. Clean-sheet and goals-conceded engine

Let the expected opponent goal rate be:

```text
λ_opp
```

Basic Poisson clean-sheet probability:

```text
P(0 goals) = exp(-λ_opp)
```

Use this as a V1 team-level probability.

For GK/DEF:

```text
CS_points =
4 × P(clean sheet while eligible)
```

For MID:

```text
CS_points =
1 × P(clean sheet while eligible)
```

For GKP/DEF conceded-goal deductions, calculate from a goal distribution rather than a single mean where possible.

Simplified:

```text
expected deduction =
Σ P(goals_conceded = g) × floor(g / 2) × -1
```

Eventually incorporate player on-pitch time.

---

# 17. Defensive-contribution engine

## 17.1 Player rate

Estimate per-90 eligible actions:

For DEF:

```text
CBIT90 =
(clearances + blocks + interceptions + tackles)
/ minutes × 90
```

For MID/FWD:

```text
CBIRT90 =
(CBIT + recoveries)
/ minutes × 90
```

Use sample-size shrinkage.

---

## 17.2 Match expectation

Convert posterior rate to target expected actions using minutes/opponent.

Then:

```text
DEF:
DC_xPts = 2 × P(actions >= 10)

MID/FWD:
DC_xPts = 2 × P(actions >= 12)
```

### Example

Defender expected actions:

```text
λ = 9.5
```

Poisson probability:

```text
P(X >= 10) ≈ 0.478
```

Expected DC points:

```text
≈ 0.956
```

This is much better than treating DC as a linear rate.

---

# 18. Goalkeeper save engine

Estimate target saves using:

```text
player save rate
opponent shot/goal threat
team defensive environment
expected minutes
```

Then model integer saves.

For a save-count distribution `S`:

```text
save_points =
floor(S / 3)
```

Expected points:

```text
E[save_points] =
Σ P(S=s) × floor(s/3)
```

Do not use:

```text
E[S] / 3
```

as the final answer.

---

# 19. Bonus engine

## V5.0

Use an empirical expected-bonus model.

Features can include:

```text
position
expected minutes
xG
xA
clean-sheet probability
expected saves
DC actions
historical BPS/90
```

Output:

```text
expected_bonus
```

## V5.x later

Build full fixture-level BPS simulation after the 2026/27 scoring inputs are validated.

Until then, label:

```text
bonus_model = "empirical"
```

not:

```text
bonus_model = "exact"
```

---

# 20. Negative points

Include low-frequency negative expectations.

Potential components:

```text
yellow card
red card
own goal
penalty miss
goals conceded
```

Use strongly shrunk historical rates.

Do not overfit rare events to a small individual sample.

Position-level or league-level priors should dominate unless the player has a large history.

---

# 21. Full xPts decomposition

Every projection should be explainable.

Example output:

```text
Player: Example MID
Fixture: Home vs Opponent

Expected minutes        84.0

Appearance              1.86
Goals                   2.15
Assists                  0.88
Clean sheet              0.36
Defensive contribution   0.41
Bonus                    0.46
Cards                   -0.10
Other negatives         -0.03
--------------------------------
xPts mean                5.99
```

This is significantly better than showing only:

```text
score = 76.4
```

The user should be able to see **why** the model likes the player.

---

# 22. Projection distribution

## Recommended implementation

Precompute projections offline rather than running heavy simulation for every dashboard request.

For each player/fixture:

```text
simulate 5,000–20,000 match outcomes
```

A default such as 10,000 is reasonable for development; benchmark runtime and sampling stability before fixing it.

Use a deterministic seed derived from:

```text
model_version
gameweek
fixture_id
player_id
```

This guarantees reproducible tests.

### Output

```text
mean
P10
median
P90
P(return)
P(10+)
P(15+)
```

---

# 23. Why historical "vs team" must remain small

Historical matchup data can be stored as a diagnostic:

```text
matches
minutes
goals
assists
xG
xA
FPL points
```

But it should not become a primary model feature.

### Reliability rule

```text
if matches < minimum:
    h2h_modifier = 1.0
```

Then shrink larger samples toward zero effect.

### Strong rule

```text
H2H must never rescue a bad base projection.
```

Example:

```text
base xPts 4.0
historical H2H excellent
max +3%
final ≈ 4.12
```

Not:

```text
base 4.0 → final 7.0
```

---

# 24. Elite-manager intelligence upgrade

The competitive system should track two things independently.

## 24.1 Validated manager skill

Use multi-season history.

Possible manager score inputs:

```text
number of prior seasons
best rank
recent ranks
multi-season weighted percentile
consistency
```

The repository already contains historical scout work.

Create:

```text
data/model/manager_quality.json
```

Example:

```json
{
  "entry_id": 123,
  "manager_quality_score": 91.4,
  "tier": "ELITE",
  "evidence_seasons": 5
}
```

---

## 24.2 Current-season leaders

Keep:

```text
current top 5%
```

but label it:

```text
CURRENT_LEADERS
```

not automatically:

```text
VALIDATED_ELITE
```

---

## 24.3 Early-season blend

Conceptually:

```text
GW1–4:
historical quality dominates cohort selection

GW5+:
current performance gets more weight

later season:
current rank becomes increasingly informative
```

Tune the schedule using historical manager data.

Do not define the exact blend only from intuition if backtest data are available.

---

# 25. Effective ownership and captaincy

Pre-deadline:

```text
known:
previous squad ownership
historical behaviour

unknown:
actual next-GW transfers
actual next-GW captain
```

Do not pretend upcoming elite captaincy is known.

Post-deadline:

calculate realized cohort exposure:

```text
EO =
sum(player multiplier across cohort)
/
number of managers
× 100
```

This can exceed 100% due to captain multipliers.

Use post-deadline EO for:

- performance attribution;
- risk analysis;
- "why rank moved";
- calibration of strategic exposure.

---

# 26. Transfer optimizer design

## 26.1 Legal constraints

Every proposed move must pass:

```text
15-player squad
correct position counts
budget
selling price
purchase price
max 3 from a club
free-transfer count
hit cost
availability
```

For 2026/27:

```text
one new free transfer each GW
unused transfers can roll
maximum bank = five
extra transfer = -4 FPL points
```

---

## 26.2 Horizon

Default comparison:

```text
GW+1 through GW+5
```

with configurable horizon.

Example:

```text
Player Out → Player In

GW2   +1.2
GW3   +0.9
GW4   -0.4
GW5   +1.5
GW6   +0.8
----------------
gross +4.0
```

If it consumes a free transfer:

```text
hit = 0
```

but there is still an opportunity cost.

If it requires an extra transfer:

```text
subtract 4
```

So:

```text
gross +4.0
hit   -4.0
net    0.0
```

Usually not compelling unless structure/risk considerations add value.

---

## 26.3 Opportunity cost

A free transfer is not literally free in strategic terms.

Spending it prevents:

- rolling it;
- reacting to future injuries;
- making two coordinated moves later.

Start with a configurable small opportunity-cost parameter and test whether it improves historical transfer decisions.

Do not hide the parameter.

Expose:

```text
transfer_opportunity_cost
```

in diagnostics.

---

## 26.4 Multi-transfer optimization

Later, use a small combinatorial search.

For example:

```text
0 transfers
1 transfer
2 transfers
3 transfers
```

Subject to:

```text
free transfers
hit cost
budget
club limit
position structure
```

Do not brute-force every possible squad combination if a pruned search can provide the same practical result.

---

# 27. Captain engine

Return at least:

```text
MAX_EV
SAFE
LEVERAGE
VICE
```

Example:

| Player | xPts | P10 | P90 | P(10+) | Strategy |
|---|---:|---:|---:|---:|---|
| A | 7.8 | 2 | 16 | 36% | Max EV |
| B | 7.4 | 3 | 13 | 29% | Safer |
| C | 7.1 | 1 | 17 | 34% | Leverage |

Then the competitive phase decides whether a deviation is justified.

### Critical rule

```text
Captain model first.
League strategy second.
```

---

# 28. Wildcard / chip handling in transfer logic

The transfer optimizer must know chip state.

Examples:

```text
Wildcard:
transfer hits do not apply;
permanent squad rebuild.

Free Hit:
one-GW temporary squad;
normal squad returns after the GW.

Bench Boost:
all 15 projected scores matter.

Triple Captain:
captain multiplier becomes 3.
```

Do not use ordinary transfer-horizon logic unchanged during these chips.

---

# 29. API design

Recommended new endpoint:

```text
GET /v1/projections/current?gw=2
```

Response:

```json
{
  "meta": {
    "projection_version": "projection-v5.0-lab",
    "generated_at": "...",
    "quality_status": "valid",
    "stale": false
  },
  "gameweek": 2,
  "players": [...]
}
```

Recommended existing endpoint behaviour:

```text
/v1/recommendations/current
```

continues to return competitive advice, but the player `xpts` now comes from V5 when:

```text
V5 shadow source is valid
AND endpoint explicitly requests shadow
```

Production should not silently replace V4.

---

# 30. Projection metadata and provenance

Every generated projection file should include:

```text
schema_version
projection_version
generated_at
target_gameweek
input_snapshot_ids
input_deadline_cutoff
data_provider
quality_status
quality_issues
random_seed_scheme
git_commit
```

This makes every recommendation reproducible.

---

# 31. Fail-safe / fallback behaviour

If V5 data are:

- missing;
- stale;
- invalid;
- incomplete,

do not fabricate values.

Fallback order:

```text
1. valid V5 projection
2. valid existing production projection
3. FPL ep_next fallback
4. unavailable
```

Expose:

```text
projection_source
```

Examples:

```text
projection_source = "projection-v5.0-shadow"
projection_source = "competitive-v4-fpl-ep-next"
projection_source = "fpl-ep-next-fallback"
```

A fallback must be visible in the dashboard.

---


# 31A. Required experiment namespaces

Keep model outputs physically and logically separate.

Recommended layout:

```text
artifacts/model-evaluation/
    production-v4.0/
    shadow-v4.2/
    v5-lab/
```

or equivalent GCS keys:

```text
snapshots/model-evaluation/production-v4.0/
snapshots/model-evaluation/shadow-v4.2/
snapshots/model-evaluation/v5-lab/
```

V5 must never write into the V4.2 directory/key prefix.

Recommended registry shape:

```yaml
production:
  competitive_model: competitive-v4.0
  optimizer: horizon-v4.1

active_shadow:
  model: v4.2
  frozen_candidate_definition: true
  promotion_eligible: true

research:
  - model: projection-v5.0-lab
    promotion_eligible: false
    writes_enabled: false
    can_influence_production: false
```

Add tests proving that the research model cannot replace or mutate `active_shadow`.

---

# 32. Keep heavy modelling out of the live API

Current API dependencies are intentionally small:

```text
FastAPI
httpx
Pydantic
pytest
uvicorn
google-cloud-storage
```

That is good for production reliability.

Do not immediately add an enormous ML stack to the Cloud Run request path.

Recommended split:

```text
services/api/requirements.txt
→ lightweight runtime

requirements-research.txt
→ pandas
→ numpy
→ scipy
→ scikit-learn
→ optional modelling packages
```

Projection generation can run:

```text
scheduled job / VM / GitHub Action
```

and publish JSON results.

The API only reads the projection artifact.

---

# 33. Proposed new scripts

Create:

```text
scripts/fetch_player_history.py
scripts/build_team_history.py
scripts/build_model_features.py
scripts/build_projections.py
scripts/backtest_projections.py
scripts/evaluate_projection_calibration.py
```

## Responsibilities

### `fetch_player_history.py`

Collect raw deadline-safe player/match data.

### `build_team_history.py`

Aggregate team attack/defence history.

### `build_model_features.py`

Create prior + current-season + fixture features.

### `build_projections.py`

Generate player xPts and distributions.

### `backtest_projections.py`

Walk historical GWs chronologically.

### `evaluate_projection_calibration.py`

Produce:

```text
MAE
RMSE
rank correlation
Brier scores
calibration tables
captain regret
transfer-horizon results
```

---

# 34. Workflow integration

Current repository already has a scheduled fixture refresh.

Add a separate V5 laboratory workflow:

```text
.github/workflows/refresh-projections-v5-lab.yml
```

Do **not** reuse or overwrite the existing V4.2 shadow workflow/state.

Recommended sequence:

```text
1. checkout
2. setup Python
3. fetch current bootstrap
4. fetch fixture horizon
5. fetch/update player history
6. validate inputs
7. build features
8. build V5 shadow projections
9. validate projection artifact
10. publish projection artifact
11. run contract tests
12. update shadow evaluation
```

Do not auto-promote the model.

---

# 35. No future-data leakage

This is non-negotiable.

For a projection targeting GW10:

```text
allowed:
everything known before GW10 deadline

forbidden:
GW10 result
GW10 final xG
GW10 minutes
later injury outcome
future price change
GW11 information
```

### Backtest method

Use rolling-origin evaluation:

```text
train / calculate priors using past
predict next GW
record error
move forward one GW
repeat
```

Do not randomly shuffle player-GW rows into ordinary train/test sets.

Random splitting can allow future information to influence a prediction of the past.

---

# 36. Backtesting plan

## Baselines

Every V5 evaluation must include:

```text
Baseline A: FPL ep_next
Baseline B: current V4 ranking
Candidate: V5
```

Do not evaluate V5 in isolation.

---

## Point metrics

Use:

```text
MAE
RMSE
```

Actual FPL points are very noisy, so do not use only point error.

---

## Ranking metrics

Use:

```text
Spearman rank correlation
top-10 hit rate
top-N recall by position
```

The real decision problem often cares more about ranking useful players than predicting 5.7 vs 5.9 exactly.

---

## Probability calibration

For:

```text
P(60+)
P(return)
P(10+)
P(clean sheet)
P(DC threshold)
```

use:

```text
Brier score
reliability/calibration diagrams
```

Example:

If the model labels 100 events as:

```text
70% clean-sheet probability
```

approximately 70 should occur over a well-calibrated sample.

---

## Captain evaluation

Track:

```text
chosen captain xPts
actual captain points
best candidate actual points
captain regret
top-2 captain containment
```

Do not overreact to one-week captain outcomes.

---

## Transfer evaluation

At recommendation time save:

```text
out player
in player
expected horizon gain
hit
horizon
```

Then after the horizon finishes calculate realized points.

Evaluate both:

```text
forecast accuracy
decision outcome
```

A good forecast can still lose over five GWs due to variance.

---

# 37. Promotion gates

Keep the existing philosophy:

```text
shadow first
production later
owner approval required
```

The README already requires:

```text
at least 6 completed live shadow GWs
at least 500 paired player rows
accuracy / calibration / policy gates
explicit owner approval
```

Keep those as minimum live-shadow safeguards.

For V5 add:

```text
1. no data leakage found
2. all scoring-rule tests pass
3. all legal-transfer tests pass
4. API contract tests pass
5. read-only / Telegram boundaries unchanged
6. V5 is not materially worse than ep_next baseline on primary point metrics
7. V5 probability calibration is acceptable
8. V5 ranking performance is at least competitive with baseline
9. missing-data fallback tested
10. owner explicitly approves promotion
```

### Better than arbitrary thresholds

Do not invent a permanent rule such as:

```text
V5 must improve MAE by exactly 7%
```

before seeing historical variance.

Use:

```text
relative baseline performance
+
confidence intervals
+
minimum sample size
```

Then lock thresholds once backtest distributions are known.

---

# 38. Tests that should be added

Create:

```text
services/api/tests/test_scoring_2026.py
services/api/tests/test_expected_minutes.py
services/api/tests/test_projection_math.py
services/api/tests/test_opponent_model.py
services/api/tests/test_transfer_optimizer.py
services/api/tests/test_projection_api.py
services/api/tests/test_no_leakage.py
services/api/tests/test_model_fallback.py
```

---

## 38.1 Scoring tests

Test exactly:

```text
appearance 1 / 2
goal points by position
assist = 3
CS by position
save points every complete 3
penalty save
DC thresholds
penalty miss
goals conceded
cards
own goal
```

---

## 38.2 DC tests

Examples:

```text
DEF 9 actions  -> 0 realized DC
DEF 10 actions -> 2 realized DC

MID 11 actions -> 0
MID 12 actions -> 2

FWD 11 actions -> 0
FWD 12 actions -> 2
```

For expected value:

```text
Poisson tail probability is calculated correctly.
```

---

## 38.3 Candidate-universe test

Create a player who:

```text
exists in bootstrap
is owned by nobody in tracked league
has a strong projection
```

Assert:

```text
player is still eligible for V5 candidate ranking
```

This prevents a regression to the current ownership-limited universe.

---

## 38.4 Prediction / strategy separation test

Change elite ownership from:

```text
5% → 95%
```

Assert:

```text
football xPts does not change
```

Only competitive classification may change.

This should be a hard invariant.

---

## 38.5 Captain test

Change elite captaincy.

Assert:

```text
base xPts unchanged
```

A strategic captain label may change only in the competitive layer.

---

## 38.6 Transfer legality tests

Test:

```text
insufficient bank
club limit exceeded
position mismatch
hit cost
one free transfer
five banked transfers
sell price vs purchase price
multi-transfer combination
```

Illegal moves must never be returned as actionable recommendations.

---

## 38.7 Missing-data tests

Remove:

```text
expected_goals
defensive_contribution
fixture strength
```

one at a time.

Assert:

```text
quality warning
documented fallback
no silent zero unless zero is genuinely observed
```

---

## 38.8 Deterministic simulation

Given the same:

```text
model version
inputs
seed
```

assert identical projection output.

---


## 38.9 V4.2 experiment-isolation tests

Add hard tests such as:

```python
def test_v4_2_remains_active_shadow():
    assert registry.active_shadow.model == "v4.2"
    assert registry.active_shadow.promotion_eligible is True

def test_v5_lab_cannot_replace_active_shadow():
    assert registry.research["projection-v5.0-lab"].promotion_eligible is False

def test_v5_lab_cannot_execute():
    assert v5_lab.writes_enabled is False

def test_v5_outputs_use_separate_namespace():
    assert v5_lab.artifact_prefix != v4_2_shadow.artifact_prefix
```

If V4.2's candidate definition changes materially, require a new version identity.

---

# 39. Dashboard changes

Do not redesign the whole dashboard.

Use the existing pages and expose stronger information.

---

## Assistant page

Show:

```text
Football xPts
Competitive role
Expected minutes
Fixture
Uncertainty
Elite ownership
Reason
```

Example:

```text
Player A
xPts: 6.8
Exp mins: 87
P10–P90: 2–14
Elite own: 78%
Role: ALIGN

Why:
high xG prior + favourable opponent + nailed minutes
```

---

## Player page

Add:

```text
V5 xPts
FPL ep_next
difference
posterior xG/90
posterior xA/90
expected minutes
DC probability
CS probability
opponent strength
H2H modifier
projection source
data quality
```

---

## Shadow page

Show:

```text
projection-v5.0-shadow

live GWs
paired rows
MAE
RMSE
rank correlation
P(return) Brier
P(10+) Brier
calibration
baseline comparison
promotion gates
```

---

## Transfers page

Replace single-GW gross score with:

```text
5-GW gross gain
hit cost
net gain
free-transfer count
bank
legality
risk
```

---

# 40. Frontend implementation rule

Current `web-next/lib/competitive.ts` correctly behaves as a server-side API adapter instead of rebuilding the Python formula.

Keep that principle.

Add fields to TypeScript types, but do not independently implement projection math in React/TypeScript.

Correct:

```text
Python calculates
API returns
Next.js displays
```

Incorrect:

```text
Python calculates one version
browser recalculates another version
```

---

# 41. Recommended response contract

A competitive player could eventually look like:

```json
{
  "element": 123,
  "name": "Example",
  "position": "MID",
  "team": "Example FC",

  "projection": {
    "version": "projection-v5.0-lab",
    "source": "v5",
    "expected_minutes": 84.0,
    "xpts_mean": 6.21,
    "xpts_p10": 2.0,
    "xpts_p50": 5.0,
    "xpts_p90": 13.0,
    "p_return": 0.58,
    "p_10_plus": 0.24
  },

  "competitive": {
    "elite_ownership": 62.4,
    "role": "ALIGN"
  }
}
```

This makes the distinction obvious.

---

# 42. Example: Player A vs Player B after GW1

Suppose:

```text
Player A:
GW1 points 10
90 minutes
xG 0.15
xA 0.02
next fixture average

Player B:
GW1 points 2
90 minutes
xG 0.85
xA 0.20
next fixture favourable
```

Current form/PPG logic can over-reward A.

V5 should do:

```text
previous-season prior
+
GW1 underlying evidence
+
expected minutes
+
next opponent
```

It may still choose A if:

- A has a far stronger long-term prior;
- B's role was temporary;
- B is a rotation risk.

But the decision will be based on predictive evidence rather than simply last week's FPL points.

---

# 43. Example: Haaland vs Palace

Historical record:

```text
strong
```

V5 process:

```text
1. expected minutes
2. current + prior xG rate
3. City attack
4. Palace defence
5. venue
6. penalty role
7. distribution
8. tiny H2H modifier
9. competitive exposure
```

Example:

```text
base xPts                 7.20
H2H modifier             +2.0%
post-H2H xPts             7.34
elite ownership           high
role                      ALIGN
captain classification    strong
```

The historical matchup is confirmation, not the engine.

---

# 44. Example: Defender DC

Defender posterior:

```text
expected eligible actions = 9.5
```

Threshold:

```text
10
```

Poisson V1:

```text
P(10+) ≈ 47.8%
```

Expected DC:

```text
2 × 47.8%
≈ 0.96 xPts
```

That is the correct type of threshold model.

---

# 45. Example: Transfer

Current squad player:

```text
Out
GW2 4.3
GW3 3.8
GW4 4.7
GW5 3.9
GW6 4.0
total 20.7
```

Target:

```text
In
GW2 5.5
GW3 4.7
GW4 4.3
GW5 5.4
GW6 4.8
total 24.7
```

Gross gain:

```text
+4.0
```

Scenario A:

```text
free transfer available
hit = 0
```

Candidate move.

Scenario B:

```text
requires extra transfer
hit = -4
```

Pure points gain becomes approximately zero before opportunity/structure adjustments.

The system should not describe both scenarios as equally good.

---

# 46. Example: captain strategy

Player A:

```text
xPts 8.0
P10 2
P90 16
elite exposure very high
```

Player B:

```text
xPts 7.6
P10 1
P90 18
elite exposure moderate
```

During `CATCH`:

```text
A may be preferable because:
- highest EV
- high elite exposure
- reduces unnecessary downside
```

During late `CHASE`:

```text
B may be considered
only if the xPts gap is small enough
and the league deficit justifies variance.
```

The projection numbers remain unchanged.

Only decision utility changes.

---

# 47. Model configuration

Do not scatter magic numbers in functions.

Create a versioned config:

```text
services/api/app/model_config.py
```

or JSON/YAML.

Example:

```python
ProjectionConfig(
    prior_minutes_xg=...,
    prior_minutes_xa=...,
    recency_half_life=...,
    h2h_max_multiplier=...,
    simulation_count=...,
    horizon=5,
)
```

Every projection artifact stores the config version.

---

# 48. Feature ablation

Many FPL statistics are correlated.

Examples:

```text
xGI
xG + xA
form
PPG
total points
ep_next
ICT
```

Do not include every available number simply because it exists.

For each feature family:

```text
train/evaluate base
add feature
measure out-of-sample change
```

If the feature does not improve performance or calibration, remove it.

Simpler models are easier to trust.

---

# 49. Suggested modelling progression

## V5.0 — deterministic/probabilistic transparent model

Use:

```text
Bayesian/shrunken rates
expected minutes
Poisson-style event probabilities
opponent strength
2026/27 scoring rules
simulation
```

Advantages:

- explainable;
- easy to test;
- works with current amount of data;
- avoids overfitting GW1–GW3.

---

## V5.1 — fitted calibration models

After enough historical rows:

```text
calibrate assist rates
calibrate bonus
calibrate p_start
calibrate clean sheet
calibrate DC probability
```

---

## V5.2 — optional ML challenger

Only after V5.0 is a strong baseline, test:

```text
regularized regression
gradient boosting
other tabular models
```

Use rolling-origin validation.

The ML model must beat the transparent baseline.

Do not promote ML just because it is more complex.

---

# 50. Implementation phases

## Phase 0 — freeze production contracts

Before changes:

```text
run tests
record current API samples
record current health response
record current V4 output
tag/commit baseline
```

Do not break V4.

---

## Phase 1 — data completeness

Deliver:

```text
full useful bootstrap fields
per-player current history
team history
provenance
quality validation
```

Acceptance:

```text
all active FPL players represented
no candidate-universe restriction
missing fields explicitly reported
```

---

## Phase 2 — scoring and expected minutes

Deliver:

```text
2026/27 scoring module
expected-minutes model
unit tests
```

Acceptance:

```text
all official scoring tests pass
minutes outputs bounded 0–90
probabilities bounded 0–1
```

---

## Phase 3 — attacking / opponent / prior model

Deliver:

```text
posterior xG/xA
team attack/defence
home/away
FDR fallback
```

Acceptance:

```text
GW1 current data cannot overwhelm prior
current data naturally gains weight with minutes
```

---

## Phase 4 — CS / GK / DC / bonus

Deliver component projections.

Acceptance:

```text
full xPts decomposition adds to total
DC threshold model tested
save bucket model tested
```

---

## Phase 5 — distributions

Deliver:

```text
P10/P50/P90
P(return)
P(10+)
```

Acceptance:

```text
deterministic seed
distribution sanity checks
```

---

## Phase 6 — transfer and captain integration

Deliver:

```text
legal multi-GW transfer value
dedicated captain engine
```

Acceptance:

```text
no illegal transfer
hits/free transfers correct
captain does not depend on ownership in raw projection
```

---

## Phase 7 — competitive integration

Deliver:

```text
VALIDATED_ELITE
CURRENT_LEADERS
V5 xPts + V4 strategic phase
```

Acceptance:

```text
changing elite ownership cannot alter base xPts
```

---

## Phase 8 — dashboard LAB comparison view

Display V5 without execution authority and without replacing the existing V4.2 shadow surface.

The dashboard should clearly label:

```text
Production: competitive-v4.0
Active shadow: V4.2
Research: projection-v5.0-lab
```

---

## Phase 9 — V4.2 completes its existing formal shadow lifecycle

Do not reset V4.2.

Keep its existing safeguards, including the repository's current minimum live-shadow requirements:

```text
6 completed live shadow GWs
500+ paired rows
accuracy / calibration / policy gates
explicit owner approval
```

V5 continues collecting **separate laboratory comparisons** during this period.

---

## Phase 10 — choose the next formal baseline

If V4.2 passes:

```text
promote V4.2 only through the existing approval process
```

If V4.2 fails:

```text
keep the current approved production model
retire/reject V4.2 as a candidate
```

Neither result automatically promotes V5.

---

## Phase 11 — V5 becomes the next formal shadow candidate

Only after the V4.2 lifecycle is closed should V5 be allowed to move from:

```text
projection-v5.0-lab
```

to a formal promotion-eligible shadow identity, for example:

```text
projection-v5.0-shadow
```

At that point V5 starts its **own** formal shadow counter and promotion record.

Historical lab comparisons remain useful evidence, but must not be relabelled as V4.2 shadow rows or silently backfilled into the formal V5 shadow counter.

---

## Phase 12 — explicit V5 promotion decision

No automatic promotion.

Owner approves V5 only after its own formal gates pass.

---

# 51. Exact agent implementation instructions

The following block can be handed directly to an implementation agent.

---

## AGENT TASK: IMPLEMENT `projection-v5.0-lab` WITHOUT DISTURBING THE EXISTING V4.2 SHADOW

### Objective

Build a new **laboratory** player-intelligence engine for the existing FPL Scout repository.

The repository already has an active V4.2 shadow experiment. Preserve it exactly.

Do not replace `competitive-v4.0`.

Do not modify the FPL execution boundary.

Telegram remains the only execution authority.

The dashboard remains read-only.

### Mandatory first step

Read and understand:

```text
README.md
DEPLOYMENT.md
services/api/app/recommendations.py
services/api/app/main.py
services/api/app/repository.py
services/api/app/schemas.py
services/api/app/validation.py
services/api/tests/test_api.py
scripts/fetch_gw_data.py
scripts/fetch_fixture_horizon.py
scripts/generate_analysis.py
web-next/lib/competitive.ts
web-next/lib/autopilot.ts
```

Run existing tests before editing.

### Hard invariants

0. The existing V4.2 shadow candidate remains frozen and promotion-eligible under its current lifecycle.
1. V5 must begin as `projection-v5.0-lab`, not as the active formal shadow candidate.
2. V5 must not overwrite V4.2 model-candidate state, paired rows, shadow-GW count, calibration metrics, policy gates, registry entry, or historical prediction artifacts.
3. V5 may consume the same deadline-safe input snapshots, but must write to a separate artifact namespace.
4. A materially changed V4.2 formula must receive a new version identity rather than silently continuing the same shadow run.
1. `competitive-v4.0` remains the production model.
2. V5 starts as `projection-v5.0-lab`.
3. No browser writes to FPL.
4. No FPL credential/token moves to frontend.
5. Telegram execution boundary remains unchanged.
6. Existing API contracts remain backward compatible unless a versioned endpoint is added.
7. V5 raw xPts must not depend on elite ownership.
8. V5 raw xPts must not depend on league rank.
9. V5 candidate universe must include every valid FPL player.
10. No future data may enter a historical prediction.

### Implement

Create:

```text
services/api/app/scoring.py
services/api/app/projections.py
services/api/app/projection_types.py
services/api/app/opponent_model.py
services/api/app/transfer_optimizer.py

scripts/fetch_player_history.py
scripts/build_team_history.py
scripts/build_model_features.py
scripts/build_projections.py
scripts/backtest_projections.py
scripts/evaluate_projection_calibration.py

services/api/tests/test_scoring_2026.py
services/api/tests/test_expected_minutes.py
services/api/tests/test_projection_math.py
services/api/tests/test_transfer_optimizer.py
services/api/tests/test_projection_api.py
services/api/tests/test_no_leakage.py
services/api/tests/test_model_fallback.py
```

### Extend

```text
scripts/fetch_gw_data.py
services/api/app/repository.py
services/api/app/schemas.py
services/api/app/main.py
services/api/app/recommendations.py
web-next/lib/types.ts
web-next/lib/competitive.ts
```

### Projection inputs

At minimum:

```text
minutes
starts
xG
xA
xGI
xGC
DC
CBI
tackles
recoveries
saves
BPS
bonus
set-piece orders
player status
fixtures
FDR
team/opponent history
previous-season history
```

### Projection outputs

At minimum:

```text
expected minutes
P(start)
P(60+)

xPts mean
P10
P50
P90

P(return)
P(10+)

component breakdown
data quality
projection source
diagnostics
```

### Football-model rules

- use previous-season data as a shrinkage prior;
- use current-season data with sample-size-aware updating;
- model expected minutes explicitly;
- create independent opponent attack and defence strength;
- model clean-sheet probability;
- model goalkeeper saves by integer buckets;
- model DC by threshold probability;
- use an empirical bonus model first;
- add only a small shrunk/capped H2H modifier;
- keep `ep_next` as baseline/fallback, not as the core candidate model.

### Transfer rules

Respect:

```text
budget
selling price
purchase price
same-position transfer
3-per-club maximum
free transfers
maximum five banked free transfers
-4 points for additional transfers
chip state
```

Use 4–6 GW horizon.

### Competitive integration

Maintain:

```text
CATCH
MATCH
ATTACK
CHASE
```

But use V5 football projections as independent evidence.

Separate:

```text
VALIDATED_ELITE
CURRENT_LEADERS
```

Do not use previous-GW elite captaincy as a direct next-GW player projection feature.

### Validation

Run:

```text
existing tests
new unit tests
API contract tests
backtests
no-leakage tests
```

Compare:

```text
V5 vs FPL ep_next
V5 vs current V4 ranking
```

### Shadow promotion

Do not promote automatically.

Require:

```text
minimum live-shadow sample
predictive metrics
calibration metrics
no policy regressions
no API regressions
explicit owner approval
```

### Documentation

Update README with:

```text
what V5 is
what remains production
data sources
formula/component overview
how to run refresh
how to run backtest
how to read shadow metrics
fallback behavior
promotion gates
zero-knowledge operator instructions
```

---

# 52. Definition of done

- [ ] Existing V4.2 shadow state is unchanged and still promotion-eligible under its original rules.
- [ ] V4.2 paired rows, completed shadow GWs, calibration results and promotion gates were not reset.
- [ ] V5 is registered as `projection-v5.0-lab`, not as the active shadow candidate.
- [ ] V5 artifacts are stored separately from V4.2 artifacts.
- [ ] V5 cannot influence production recommendations or Telegram execution while in LAB mode.

V5 shadow is complete only if all statements below are true.

- [ ] Every FPL player can be projected even if zero tracked managers own him.
- [ ] Raw xPts is independent of elite ownership.
- [ ] Raw xPts is independent of league rank.
- [ ] Previous-season information is incorporated through a documented prior.
- [ ] Current-season underlying performance updates that prior.
- [ ] Expected minutes are explicit.
- [ ] Opponent attack and defence are separate.
- [ ] FDR fallback is available.
- [ ] 2026/27 scoring rules are tested.
- [ ] Defensive contribution is modelled probabilistically.
- [ ] Goalkeeper save buckets are represented.
- [ ] Clean-sheet probability is represented.
- [ ] Bonus is represented and labelled by model type.
- [ ] H2H impact is shrunk and capped.
- [ ] Projection uncertainty is available.
- [ ] Captain ranking uses projection distribution first.
- [ ] Transfer recommendations use a multi-GW horizon.
- [ ] Transfer recommendations are legal.
- [ ] Hit costs and banked free transfers are included.
- [ ] `ep_next` baseline is stored for comparison.
- [ ] Backtest uses chronological/rolling-origin splits.
- [ ] Probability calibration is measured.
- [ ] Existing V4 production remains functional.
- [ ] Dashboard remains read-only.
- [ ] Telegram remains execution authority.
- [ ] V5 remains shadow until formal promotion.

---

# 53. What not to do

Do **not**:

```text
1. replace V4 immediately;
2. use one GW of form as proof of ability;
3. use raw FPL points as the main performance predictor;
4. make H2H a major feature;
5. classify low ownership itself as an edge;
6. let popularity change raw xPts;
7. use last GW captaincy as if it predicts next GW captaincy;
8. limit candidate players to those already owned by competitors;
9. suggest transfers without budget / club / hit checks;
10. random-shuffle time-series rows for model validation;
11. silently use future data in a backtest;
12. silently replace missing values with zero;
13. run an unvalidated model directly through Telegram execution;
14. duplicate projection formulas in the frontend;
15. add a complex ML model before a transparent baseline is working.
```

---

# 54. Research basis

## Official Premier League / FPL — primary sources

### 2026/27 scoring rules

Premier League — **FPL basics explained: Scoring points**  
Published 20 July 2026  
https://www.premierleague.com/en/news/2174909

Used for:

- appearance points;
- goal points by position;
- assists;
- clean sheets;
- goalkeeper saves;
- penalty saves;
- defensive contribution thresholds;
- negative scoring;
- bonus.

### 2026/27 BPS changes

Premier League — **What's new in 2026/27 Fantasy: Changes to Bonus Points System**  
Published 20 July 2026  
https://www.premierleague.com/en/news/4679946/whats-new-in-202627-fantasy-changes-to-bonus-points-system

Used for:

- 2026/27 BPS changes;
- goalkeeper-save BPS;
- CBI BPS change;
- removal of tackled deduction.

### Transfer rules

Premier League — **FPL basics explained: How to make transfers**  
Published 20 July 2026  
https://www.premierleague.com/en/news/2174907/fpl-basics-explained-how-to-make-transfers

Used for:

- one free transfer per GW;
- rolling transfers;
- maximum five banked free transfers;
- four-point additional-transfer cost;
- same-position replacement;
- budget;
- three-player club limit;
- selling-price mechanics.

### FDR

Fantasy Premier League — **Fixture Difficulty Rating**  
https://fantasy.premierleague.com/fixtures/fdr

Premier League — **How the Fixture Difficulty Ratings help FPL managers**  
https://www.premierleague.com/en/news/68553

Used for:

- FDR is a compressed 1–5 difficulty measure;
- it uses team performance data;
- it uses home/away form;
- it is reviewed as the season progresses.

### 2026/27 chips

Premier League — **What's happening with FPL chips in 2026/27**  
https://www.premierleague.com/en/news/4679879/whats-happening-with-fpl-chips-in-202627

Used for:

- two chip sets in 2026/27;
- Wildcard, Free Hit, Triple Captain, Bench Boost.

---

## Historical / API field reference — secondary sources

### Vaastav FPL historical data dictionary

https://github.com/vaastav/Fantasy-Premier-League/blob/master/DATA_DICTIONARY.md

Useful for confirming historical FPL dataset fields such as:

```text
xG
xA
xGI
xGC
per-90 values
defensive contribution
set-piece orders
player history
```

Treat this as a community-maintained data source/reference, not an official FPL API guarantee.

### Community FPL endpoint documentation

Example reference:

https://github.com/atsilverman/fpl-explorer/blob/main/docs/FPL_API_COMPLETE_REFERENCE.md

Useful for endpoint/data-shape research around:

```text
/event/{gw}/live
/element-summary/{player_id}/
/fixtures/
```

Again: community documentation, so runtime schema validation remains mandatory.

---

## Forecast-validation research

### Hyndman & Athanasopoulos — Forecasting: Principles and Practice

Time-series cross-validation / rolling forecasting origin:  
https://otexts.com/fpp3/tscv.html

Used for:

```text
train on past
test on future
roll forward
avoid future leakage
```

### scikit-learn — TimeSeriesSplit

https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html

Used as implementation guidance for ordered validation.

### scikit-learn — Probability calibration

https://scikit-learn.org/stable/modules/calibration.html

Used for:

```text
calibration curves
reliability diagrams
probabilistic interpretation
Brier-score evaluation
```

---

# 55. Final recommendation

Do not rebuild the whole project.

The strongest next move is:

```text
preserve V4.2 active shadow unchanged
+
build V5 in an isolated LAB lane
+
current strong infrastructure
+
independent V5 player projection
+
proper expected minutes
+
underlying statistics
+
opponent model
+
previous-season prior
+
2026/27 scoring components
+
probability distributions
+
legal multi-GW transfer optimizer
+
existing elite strategy
```

In short:

```text
FIRST:
predict football/FPL output properly

THEN:
decide how to fight the league
```

The existing competitive engine should become the **strategy layer above the projection engine**, not the projection engine itself.

That is the clearest path from a system that mostly follows strong managers to a system that can:

```text
1. match elite managers when they are correct;
2. identify when the model independently agrees;
3. discover players before the tracked cohort owns them;
4. take controlled deviations only when the statistical case is strong.
```

---

# 56. Final model-lifecycle rule

V5 must follow this lifecycle:

```text
projection-v5.0-lab
        ↓
historical backtest
        ↓
parallel live lab comparisons
        ↓
V4.2 lifecycle closes
        ↓
formal decision to admit V5 as next shadow
        ↓
projection-v5.0-shadow
        ↓
its own formal shadow counter / paired rows / gates
        ↓
explicit owner approval
        ↓
production promotion, if justified
```

Never use:

```text
V4.2 shadow history
```

as if it were:

```text
V5 shadow history
```

and never modify V4.2 halfway through its experiment merely to incorporate V5 features.
