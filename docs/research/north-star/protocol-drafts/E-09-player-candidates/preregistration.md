# E-09 — four player candidates and a location-only shot conversion model

> **DRAFT. Not frozen, not registered, not run.** Written by one designer during the north-star build and never adversarially reviewed or audited. No outcome named here has been computed. It becomes a protocol only when a reviewed version is committed under `experiments/preregistered/` in a single commit that precedes any run. Section and file references such as ROOT 2.5 point to [ROOT-DECISIONS.md](../../ROOT-DECISIONS.md); see [README](../../README.md) for the working notes it cites.

**Commit this plan and `config.json` before any E-09 outcome is computed. Nothing
below may change once the first result is observed.** This is a prospective
analysis plan on **reused historical data**, not a claim of untouched data
collection; the section "Prior exposure" lists what has already been seen. Every
threshold, seed, grid and gate lives in `config.json`. A statement here that
disagrees with `config.json` is a defect to be fixed before the protocol commit,
never after. Implementation corrections are recorded, not silently adopted.

Destination: `experiments/preregistered/E-09-player-candidates/`.

---

## 1. Claim and unchanged boundaries

Four named statistics and one model are taken through the measurement lifecycle.
The question for each is whether it is repeatable, whether it is more than a
statistic the project already has, and whether that holds in more than one league.

| Subject | What it is | Evidence class | Resolves placeholder |
|---|---|---|---|
| `shot_location_v1` | A location-only shot conversion **model**: P(goal) from shot origin and the provider head-or-body class | PREDICTIVE | instrument only |
| `shot_volume` | Shots per 90, no penalties, no direct free kicks | DERIVED | `shot_profile` |
| `shot_location_value` | Sum of `shot_location_v1` probabilities over those shots, per 90 | PREDICTIVE | `shot_profile` |
| `box_shot_share` | Share of those shots that start inside the provider-drawn penalty area | DERIVED | `shot_profile` |
| `opp_half_defensive_actions` | Ground defending duel records and interception-flagged events starting in the opponent half, per 90 | DERIVED | `defensive_action_profile` |

Not claimed, by any verdict:

- `shot_location_v1` is **not xG supplied by the provider**. The provider supplies
  none. It is not comparable with StatsBomb, Opta or Wyscout xG as if on one scale.
- **Finishing skill is out of scope.** No goals-minus-model quantity is computed,
  for any player or team, as a construct, a control or a diagnostic.
- `shot_volume` and `shot_location_value` do not say a player shoots well, only
  how often and from where.
- `opp_half_defensive_actions` is not pressing, not pressing intensity, not
  ball-winning and not defending ability. The corpus has no pressure, tackle or
  recovery event. A record tagged lost counts the same as a record tagged won.
- Passing the lifecycle earns a **descriptor**. It does not earn an optimiser
  weight with football meaning, a cross-league comparison, persistence across
  seasons or across a club change, or decision utility.

Unchanged: `spec.SPECS`, `CONSTRUCTS`, the five shipped constructs, their
fingerprints, every shipped endpoint and every product evidence gate. No
candidate value reaches Player Lab, Match Lab or the shipped XI Lab from this
experiment. E-07 and E-08 are not reopened.

## 2. Prior exposure of the data

| What | Seen by | Touches E-09 how |
|---|---|---|
| All five Wyscout leagues, full season | Stage 1, 1B, 1C for seven other axes | `shots_per_90` was a baseline column there: its correlation with seven other axes was computed and only the maximum per axis reported. Its own reliability was never computed |
| Shot origin and goal by 16x12 grid cell, per league | every xT fit | A per-cell conversion rate is a component of the shipped xT surface. It was never evaluated out of sample or read as a conversion model |
| Spain and England, March to May rows | E-07, E-08 | Opening-30-minute passing forecasts. No shot or defensive quantity |
| Italy | E-02 | Metronome index only |
| Shot marginals, five leagues | council reconnaissance (`research/xg-and-shots.md`) | Goal rate by league (Spain 11.08%, England 10.82%, Italy 9.69%, Germany 10.83%, France 10.48%), by body-part tag (head-or-body 12.5%, footed 10.2%), by counter-attack and opportunity tags, for penalties and direct free kicks; shot counts by 5 m distance band; shot-count quantiles per player; 4 of the 100 own-half shots are tagged goals |
| Duel, interception and attribution counts | council reconnaissance (`research/event-taxonomy-audit.md`) | Outcome-tag counts by duel sub-type, share of duel records with no player by league and by team-match, team-match volume quantiles |
| Eligibility counts | this design pass (`_work/structure_counts.py`, `_work/structure2.py`) | Outfield players at 900+ minutes per league (319 / 306 / 306 / 270 / 306); reliability-set sizes; players with 30+ shots and 10+ per half (80 / 84 / 88 / 66 / 80); quantiles of the opponent-half defensive-action count among eligible players; shot rows in and out of the model domain; lattice count of penalty-area shots |
| Open-play shot rows before four cutoff dates (9,693 pooled before 2017-10-22; 1,799 in Spain) | reconnaissance critic (`research/_critic.md` R8) | exposure only; it fixes the pooled as-of rule of section 10 |
| Published fits on this corpus | Soccermatics (England, 8,451 shots, in-sample logistic); Mead et al. 2023 (five leagues, random split) | The model family and the expected skill range were chosen with these in view. England is not untouched for this model class |

Not computed by anyone in this project before the protocol commit: any split-half
reliability, confound audit or baseline correlation of a candidate; any fit or
evaluation of a shot conversion model; any relation between a candidate and an
outcome.

One planning figure is derived from the disclosed marginals and stated so that it
cannot later be presented as a surprise: if shot-location mix were identical
across leagues, Italy's observed-over-expected ratio under a model trained on the
other four leagues would be about 0.897 (9.69% against 10.80%). The level
thresholds in section 4.4 were not widened to accommodate it.

## 3. Data, cohorts and exclusions

Public Pappalardo/Wyscout 2017/18 only: Spain, England, Italy, Germany, France.
Neutral Parquet `actions`, `lineups`, `players`; the head-or-body class comes from
the tag sidecar (provider tag 403; it pools headers with chest, knee and other
non-foot contact, so it is named `head_or_body`, never `header`).

| Rule | Value | Note |
|---|---|---|
| Periods | `1H`, `2H` | the leagues contain no other; the filter is asserted to drop zero rows |
| Shot set | neutral `type == "shot"` | provider `Shot` event. Penalties and direct free-kick shots are `set_piece` rows and are excluded by construction. Shots after a set-piece delivery are included. The 26 shots within 6 s of the same team's penalty stay in |
| Model domain | `start_x > 0.50` | 100 shot rows start in the shooter's own half (21 / 11 / 26 / 23 / 19). They are excluded from model fitting, evaluation and `shot_location_value`, and counted. They stay in `shot_volume` and in the denominator of `box_shot_share` |
| Eligible player | 900+ nominal league minutes, broad position DF, MD or FW, `player_id != 0` | goalkeepers excluded. Stage 1B did not exclude them; excluding structural zeros can only lower between-player variance |
| Half floor | 300+ nominal minutes in each half | house value |
| Share floor (`box_shot_share` only) | 30+ shots in the season and 10+ in each half | a share over five shots is noise |
| Unattributed rows | rows with `player_id == 0` are never credited to a player | about one ground defending duel record in ten. Missing stays missing; no reallocation |
| Location sentinels | a row whose start is exactly (0,0) or (1,1) is excluded from any zone test | provider placeholder, not a position |
| No exclusion | on team, age, club strength or league | |

Known and uncorrected, recorded so that it is not later presented as a discovery:
the minutes floor conditions on selection; nominal minutes credit a dismissed
starter with 90 and ignore stoppage time; a mid-season mover is one player with
pooled minutes and is assigned the team of most minutes; the share floor
conditions on shooting.

Structural pins in `config.json` (`expected_*`) are checked before any outcome is
computed. A mismatch stops the run with nothing written; that is a pipeline
defect, not an outcome, and a corrected run is disclosed in `analysis.md`.

## 4. The instrument — frozen

### 4.1 Definition

```
X     = (1 - start_x) * 105          metres from the goal line (convention, not measurement)
C     = |start_y - 0.5| * 68         metres from the centre line
d     = sqrt(X^2 + C^2)              metres to the goal centre
theta = atan2(7.32 * X, X^2 + C^2 - 3.66^2)     visible goal angle, radians, in [0, pi]
H     = 1 if the sidecar body part is head_or_body else 0
```

| Model | Terms | Role |
|---|---|---|
| `M0` | intercept (training goal rate) | reference |
| `MD` | intercept, d | comparator |
| `M1` | intercept, d, theta, H, H*d | default instrument |
| `MFLEX` | `M1` plus hinge terms (d-8)+, (d-16)+, (d-25)+, (theta-0.4)+, (theta-0.9)+, and H*theta | declared challenger |

Family: unpenalised logistic regression, fitted by iteratively reweighted least
squares in NumPy. Label: the `goal` flag on the shot row.

Never a feature: the provider opportunity tag (201; on 99.5% of goals and 67.3% of
non-goals, so it was assigned with the result in view), the accuracy tags, the
blocked tag, the goal-mouth zone tags, the counter-attack tag (a tagger's
judgement), the shooter, the team, the league, the game state, anything after the shot.
There is no shot end location in this corpus.

### 4.2 Leave-one-league-out

Five folds. Fold f fits every model on the other four leagues and predicts league
f. Every league shot therefore has a probability from a model that saw none of its
league, its teams or its players. Candidate values in league f use the fold-f
instrument only. The reference rate for skill is the **training** goal rate.

### 4.3 Frozen selection

The instrument is `M1` unless the pooled relative log-loss gain of `MFLEX` over
`M1`, `(LL_M1 - LL_MFLEX) / LL_M1` on out-of-league predictions, is at least 0.01
**and** the fold gain is at least 0.01 in at least 4 of 5 folds; then the
instrument is `MFLEX`. Nothing else is tried. Selecting between two models on the
same out-of-league predictions that are then judged is mildly optimistic and is
disclosed, not corrected.

### 4.4 Frozen acceptance

All statistics use out-of-league predictions. Intervals are percentile intervals
from 2,000 match-level resamples within each held-out league; coefficients are
held fixed, so training-fold uncertainty is omitted.

| Gate | Statistic | Passes if | Basis |
|---|---|---|---|
| S | sample | each training fold has 20,000+ shots and 2,000+ goals; each held-out league 5,000+ shots and 500+ goals; every fit converged | logistic-basic converges near 6,000 shots (Robberechts & Davis 2020) |
| R1 | Brier skill against the training rate | pooled point at least 0.08 and pooled lower bound at least 0.06; lower bound above 0.03 in 5 of 5 held-out leagues | published 0.10 to 0.13 for this feature set; derived standard error about 0.012 per league |
| R2 | pooled log-loss gain of the instrument over `MD` | lower bound above 0 | angle and head-or-body must earn their parameters |
| R3 | calibration slope (logistic recalibration) | within 0.85 to 1.15 in 5 of 5 | derived standard error about 0.04 |
| R4 | observed over expected, pooled, in five subgroups: footed, head_or_body, d below 10 m, 10 to 20 m, 20 m and beyond | each within 0.85 to 1.15 | derived standard errors 1.6% to 4.3% |
| R5 | pooled AUROC | at most 0.82 | published 0.75 to 0.79; anything higher on this schema is treated as a leak |
| L1 | observed over expected per held-out league | within 0.90 to 1.10 in 5 of 5 | derived standard error about 3.3% |
| L2 | calibration intercept at slope 1 | within 0.12 of zero in 5 of 5 | |
| L3 | expected calibration error, 10 equal-mass bins; maximum bin gap | at most 0.020 and at most 0.07 in 5 of 5 | a perfectly calibrated synthetic model reached 0.0154 and 0.050 in 100 league evaluations |

R gates concern relative value within a league. L gates concern level. The
candidates below are analysed within a league, where a league-constant shift in
level moves no ordering; cross-league use needs level as well.

### 4.5 Instrument verdict

| Outcome | Verdict |
|---|---|
| gate S fails | `INCONCLUSIVE` |
| S passes, any of R1 to R5 fails | `NOT_ESTABLISHED` |
| S and R1 to R5 pass, any of L1 to L3 fails | `ACCEPTED_WITHIN_LEAGUE` |
| every gate passes | `ACCEPTED` |

## 5. Candidate measurements — frozen

Definitions are `CandidateSpec` objects in `galactico/features/candidates.py`,
outside `spec.SPECS`. Their fingerprints are in `config.json`; a run whose
computed fingerprints differ stops before any outcome.

### 5.1 `shot_volume` (`1c6517c2be31`)

- **Definition.** Count of shot rows / minutes x 90.
- **Claim.** How often the player shoots. **Non-claim.** That the shots are good ones.
- **Observable implication.** A player who shoots more in odd matches shoots more
  in even matches, among players of the same broad position.
- **Confounds.** touch volume (context), team (context), broad position (constitutive).
- **Negative control.** Must not be a near-copy of touch volume or of mean field position.
- **Incremental claim.** None. This is the baseline statistic itself, proposed
  under its own name, as pass completion was after E-03. Its own column is
  therefore removed from its battery and from no other.

### 5.2 `shot_location_value` (`9998c7120f99`)

- **Definition.** Sum of the fold instrument's probability over the player's
  in-domain shot rows / minutes x 90.
- **Claim.** Shot volume weighted by where the shots came from. Shot volume is a
  declared component. **Non-claim.** Chance value as the shooter met it: defenders,
  goalkeeper, pressure and shot type are not in the number.
- **Observable implication.** Two players with equal shot volume separate if one
  shoots from closer and more central positions.
- **Confounds.** touch volume (context), team (context), broad position (constitutive).
- **Negative control.** Must not be a near-copy of `shot_volume`. The ceiling is
  the frozen 0.85. Algebra says the sum is about 1.5 times noisier than the count
  and that the count dominates its variance; rejection as redundant is the
  expected outcome and is written here as a prediction.
- **Incremental claim.** The location weighting separates players that counting does not.
- **Dependency.** Evaluated only if the instrument verdict is `ACCEPTED` or
  `ACCEPTED_WITHIN_LEAGUE`.

### 5.3 `box_shot_share` (`af2b2b118e73`)

- **Definition.** Shot rows starting at `start_x >= 0.84` and
  `0.19 <= start_y <= 0.81` / shot rows. The box is the provider's pitch drawing
  in provider coordinates, a frozen convention.
- **Claim.** Where the player's shots originate. **Non-claim.** A preference; the
  share includes deployment and team-mates.
- **Observable implication.** A player whose shots come from inside the area in
  odd matches shows the same in even matches, among players of his position.
- **Confounds.** touch volume (nuisance), shot volume (nuisance), team (context),
  broad position (constitutive).
- **Negative control.** Must not be a near-copy of mean field position or of shot volume.
- **Incremental claim.** None beyond location. It is the model-free location
  descriptor: it needs no instrument, so the location half of `shot_profile` is
  tested even if the instrument is not accepted, and under weakest-class
  composition a counted share outranks a modelled mean. A per-shot mean of the
  instrument is deliberately **not** a candidate and is not computed.

### 5.4 `opp_half_defensive_actions` (`72619cd8130b`)

- **Definition.** Rows that are (`type == "duel"` and
  `subtype == "Ground defending duel"`) or (`interception` flag true), with
  `start_x > 0.50` in the acting player's own frame, / minutes x 90. Any duel
  outcome. The two clauses do not overlap in this corpus (0 rows).
- **Honest reading of the inputs.** Each duel is logged twice, once per
  participant; a player's own record is counted once. The neutral duel `success`
  means not-lost and is **not used**. The sidecar's won / lost / neutral outcome is
  **not used**: the candidate counts engagements, and outcome composition would be
  a different construct needing its own registration. Interception is a tag on the
  intercepting player's next event, not an event.
- **Claim.** How often the player is recorded contesting or cutting out the ball in
  the opponent half. **Non-claim.** See section 1.
- **Observable implication.** Repeatable between halves among players of the same
  position, and not reducible to how much the player is in that half at all.
- **Confounds.** share of the team's ground defending duel records with no player
  (nuisance), touch volume (context), team (context), broad position (constitutive).
- **Negative control.** Must not be a near-copy of defensive-action volume over
  the whole pitch, of on-ball presence in the opponent half, or of mean field position.
- **Incremental claim.** Location of defensive activity, separate from its amount.

## 6. Gauntlet — frozen

Per league and candidate, in this order. Gates in section 8 are evaluated from
counts for **all** leagues before any statistic below is computed.

1. **Value.** Full season on the audit set A (eligible players with a finite
   value), and per half on the reliability set R (eligible, both half floors met,
   position group of at least 8 players in R).
2. **Split.** A match is in half h if the rank of its `game_id` in the league's
   sorted unique ids has parity h. House method.
3. **Reliability.** Within each half subtract the mean over R of the player's
   broad position; Pearson r across R of the two centred vectors is `r_half`;
   `r_sb = 2 r_half / (1 + r_half)`.
4. **Lower bound.** Critical value 1.6448536269514722 in both: the two-sided 90%
   Fisher-z interval, whose lower end is a one-sided 95% bound. `house_low` is that
   lower end for `r_sb` (`AxisReliability.interval`). `half_low` is the
   Spearman-Brown transform of that lower end for `r_half`.
   `reliability_low = min(house_low, half_low)`.
5. **Baseline.** `baseline_r` is the largest absolute Pearson correlation, over A,
   between the raw value and each column of the candidate's declared battery.
   A battery column with no variance is dropped and recorded.
6. **Nuisance.** `nuisance_r2` is the unadjusted R-squared, over A, of the raw
   value on the candidate's nuisance-kind columns only
   (`discriminant_validity`). A candidate with no nuisance column has none.
7. **Status.** `decide(reliability_low, nuisance_r2 or 0.0, baseline_r,
   kind_is_nuisance)` — the frozen Stage 1B rule, imported unchanged from
   `experiments/run_replication.py` (LF sha256 pinned in `config.json`):
   baseline above 0.85 rejects first; then a nuisance R-squared above 0.60; then
   lower bound at least 0.70 `SHIP`, at least 0.50 `SHIP_WITH_BAND`, else reject.

Batteries (exact columns in `config.json`). House nine: `minutes`, `touches`,
`touches_per_90`, `passes_per_90`, `pass_completion`, `mean_x`, `mean_y`,
`mean_pass_length`, and shots per 90, which is `shot_volume` itself.

| Candidate | Battery |
|---|---|
| `shot_volume` | house nine without its own column, plus `opp_half_on_ball_per_90` |
| `shot_location_value` | house nine, plus `opp_half_on_ball_per_90` |
| `box_shot_share` | house nine, plus `opp_half_on_ball_per_90` |
| `opp_half_defensive_actions` | house nine, plus `opp_half_on_ball_per_90`, `defensive_actions_per_90` |

Reported, never gating (as in Stage 1B): joint R-squared on touch count, team
one-hot and position one-hot, unadjusted and adjusted, with its noise floor
k/(n-1); rank correlation between raw and residualised values; top-12 overlap;
the uncentred pooled reliability with the house interval, for comparison with the
shipped five; reliability within each position (20+ players); reliability after
centring on team as well as position; every battery correlation; mean, sd and
zero share; the house replication label from `classify_replication`.

### 6.1 House methods inherited and departed

One principle governs every departure but one: **it can only make survival
harder.** The exception is flagged.

| Trap | Choice | Why |
|---|---|---|
| T8 baseline batteries | **Departs.** One battery function for this experiment: the Stage 1B eight, plus `minutes` (as the Stage 1 report and E-02 list it), plus the declared columns above. Fixed by name in `config.json` | three scripts hold three lists; a candidate's closest baseline must not depend on which script ran it. More columns can only raise `baseline_r` |
| T8 identity column | **Departs.** `shot_volume` is removed from its own battery only | the house battery contains shots per 90; without this the candidate is rejected against itself at r = 1 |
| T9 xT surfaces | **Not applicable by design.** No candidate and no battery column uses an xT surface | the three turnover definitions cannot move these numbers. The only fitted instrument has one definition and one fit per held-out league |
| T11 thin samples | **Departs.** A league needs 40+ players in R and in A or it is `INCONCLUSIVE`; a missing interval is `INCONCLUSIVE`; the point estimate is never used as a bound | the house fallback grades the thinnest sample `NUMBER` |
| T17 interval method | **Departs.** The gate is the smaller of the house bound and the half-r bound. Both are published | the house bound is anti-conservative: at a half correlation of 0.5 it sits about 0.01 above the half-r bound at n = 300 and about 0.04 above it at n = 66, the smallest share set. The house number stays comparable with the shipped five |
| T18 R-squared floor | **Departs.** The gating R-squared uses nuisance columns only (k of 1 or 2, floor at most 2/(n-1)). The joint R-squared is published with its adjusted value and floor | about 20 regressors at n = 66 put the unadjusted floor near 0.31 |
| T20 split | **Inherits** league-wide game-id parity and the 300-minute half floor. Exposure imbalance per half is reported | a per-team alternation would put one match in different halves for its two teams, which is not one partition of matches; comparability with the shipped five |
| T22 shared instrument | **Departs.** Both halves share an instrument that never saw the league | the house halves share a surface fitted on the league itself |
| T23 nuisance rule | **Departs, flagged.** The rule thresholds nuisance-kind variance only, as its own docstring says; the house code thresholded it jointly with team. `house_joint_r2_exceeds_ceiling` is published per league | this is the one departure that can make survival easier than the Stage 1B code path. A candidate that survives only through it is named as such in `analysis.md` |
| T24 degenerate vectors | **Departs.** A value vector with sd below 1e-12 or more than half exact zeros makes the league `INCONCLUSIVE`; a non-finite input to the rule makes the league `INCONCLUSIVE`; `_safe_abs_corr` is never asked about a constant vector | the house helper returns 0.0 for a constant, and the rule passes a NaN baseline |
| Position centring | **Departs.** Reliability is gated on position-centred values | pooled reliability of a shot count is mostly the statement that forwards shoot more than defenders. Centring can only lower r |
| Goalkeepers | **Departs.** Excluded | structural zeros inflate variance |

## 7. Models and baselines, summarised

| Compared | Against | Criterion |
|---|---|---|
| instrument | training goal rate; distance-only model | R1, R2 |
| `M1` | `MFLEX` | 4.3 |
| each candidate | its battery | 0.85 ceiling |
| each candidate | its halves | 0.70 / 0.50 on the lower bound |
| `shot_location_value` | `shot_volume` | the same 0.85 ceiling; no second test |

No hyperparameter search, no feature selection, no per-league tuning, no
sensitivity re-run chooses a result.

## 8. Sample gates

| Gate | Value | Failing it |
|---|---|---|
| players in R, per league and candidate | 40 | league `INCONCLUSIVE` for that candidate |
| players in A, per league and candidate | 40 | same |
| share of the candidate-4 union rows with no player, per league | at most 0.15 | league `INCONCLUSIVE` for `opp_half_defensive_actions` |
| degenerate or non-finite input (T24) | see 6.1 | league `INCONCLUSIVE` |
| evaluable leagues, per candidate | 4 of 5 | candidate `INCONCLUSIVE` |
| instrument gate S | 4.4 | instrument `INCONCLUSIVE` |

If the count gates leave a candidate fewer than 4 leagues, no statistic of that
candidate is computed in any league. If a league only becomes inconclusive through
a degenerate or non-finite input, the other leagues' statistics exist and are
published under the `INCONCLUSIVE` verdict.

## 9. Decision rule — frozen

**League status.** `INCONCLUSIVE`, or the output of `decide()`: `SHIP`,
`SHIP_WITH_BAND`, `REJECT`. A reject carries one reason, read off the frozen rule
by counterfactual calls: `REDUNDANT` if the baseline alone rejects; else
`CONFOUNDED` if the nuisance R-squared alone rejects; else `UNRELIABLE`.

**Candidate verdict.** Let E be the evaluable leagues, s the leagues at `SHIP` or
`SHIP_WITH_BAND`, n the leagues at `SHIP`, j the leagues at `REJECT`.

| # | Condition, first match wins | Verdict | Closure |
|---|---|---|---|
| 1 | candidate depends on the instrument and the instrument is `INCONCLUSIVE` | `INCONCLUSIVE` | — |
| 2 | candidate depends on the instrument and the instrument is `NOT_ESTABLISHED` | `NOT_ESTABLISHED` | `INSTRUMENT` |
| 3 | E < 4 | `INCONCLUSIVE` | — |
| 4 | n >= 4 | `ESTABLISHED_NUMBER` | — |
| 5 | s >= 4 | `ESTABLISHED_BAND` | — |
| 6 | j > E / 2 | `NOT_ESTABLISHED` | the most frequent reject reason; ties resolve `REDUNDANT`, then `CONFOUNDED`, then `UNRELIABLE` |
| 7 | otherwise | `NOT_ESTABLISHED` | `MIXED` |

`INCONCLUSIVE` means a frozen gate failed and nothing was compared at the
candidate level. `NOT_ESTABLISHED` means the comparison ran and the criterion was
not met: a published null, not evidence that the football concept is absent.
Rows 1 to 7 are exhaustive and mutually exclusive by order. There is no other
token and no verdict is assigned by hand.

## 10. Product consequence of each verdict — fixed now

| Verdict | Registry | Copy (frozen; braces are filled from `results.json`) |
|---|---|---|
| `INCONCLUSIVE` | the candidate id replaces its placeholder in `UNTESTED` | none |
| `NOT_ESTABLISHED` / `REDUNDANT` | `REJECTED` | "Too similar to {closest baseline}" |
| `NOT_ESTABLISHED` / `CONFOUNDED` | `REJECTED` | "Mostly explained by {nuisance}" |
| `NOT_ESTABLISHED` / `UNRELIABLE` | `REJECTED` | "Not repeatable between halves of a season within a position" |
| `NOT_ESTABLISHED` / `INSTRUMENT` | `RESEARCH_ONLY` | "Its conversion model was not accepted out of league" |
| `NOT_ESTABLISHED` / `MIXED` | `RESEARCH_ONLY` | "Survived in {s} of {E} leagues; the frozen rule needs four" |
| `ESTABLISHED_*`, external leg not run | `RESEARCH_ONLY` | "Passed the five-league lifecycle; provider and season leg not yet run" |
| `ESTABLISHED_*`, external verdict declared `NOT_COMPARABLE` (`opp_half_defensive_actions`) | `RESEARCH_ONLY` until the registration release of `PIPELINE.md` 11.2 | "Passed the five-league lifecycle; not comparable in the second provider" |
| `ESTABLISHED_*`, external leg run | section 11 | |

In every case the placeholders `shot_profile` and `defensive_action_profile`
leave `UNTESTED`; `carrying_value` stays. Proposed constructs go from 11 to 13.

Fixed regardless of verdict:

- No hosted surface renders `shot_location_value` from this experiment. A
  full-season fit inside a dated decision has seen later shots; fitting out of
  league does not remove that. A positive verdict licenses one follow-up build
  only: an instrument fitted on the shots of **all five leagues** from matches
  strictly before the decision date, with a 6,000-shot minimum-training gate (one
  league alone does not reach it until late in the season), shown to agree with
  the full-season fit. Until then it is UNAVAILABLE.
- A list of players carrying a candidate value is ordered by name or id, never by
  the value.
- Under `ACCEPTED_WITHIN_LEAGUE` the instrument's values carry no goal unit and
  are never compared across leagues.
- `box_shot_share` is a share: never summed over players, never a requirement
  dimension, never scaled by break-even retention.
- Only an `ESTABLISHED_NUMBER` construct with an external verdict of `ROBUST`,
  `ROBUST_WITH_SHIFT` or `NOT_COMPARABLE` may be offered as a user-declared
  requirement dimension, in new endpoints only, with evidence class HEURISTIC (a
  DERIVED or PREDICTIVE rate, composed with the additive historical per-90
  assumption and a declared minimum, takes the weakest). `ESTABLISHED_BAND` is
  offered as inactive research only. Gating a hosted dimension on an external
  label makes a StatsBomb-derived label reach a hosted surface; precedent exists
  for labels only (the five shipped constructs). If the owner's decision on that
  precedent goes the other way, the consequence is the conservative one: not offered.
- A position whose within-position lower bound is below 0.50 in 3 or more
  leagues is written into `invalid_contexts`: "within-position ordering of
  {position} not established (E-09)".
- No verdict changes a shipped evidence gate, endpoint, hash or test.

## 11. External leg — StatsBomb 2015/16, LOCAL tier

Run only for a candidate at `ESTABLISHED_*`, by its own command, after this
experiment's results are committed. Provider and season change together; this leg
cannot attribute a difference to either (E-11 exists for that).

| Candidate | StatsBomb estimator | Equivalence |
|---|---|---|
| `shot_volume` | Shot events whose shot type is Open Play | SEMANTICALLY_EQUIVALENT |
| `shot_location_value` | the same specification **refitted** leave-one-league-out on the four StatsBomb leagues; head_or_body is body part Head or Other | SEMANTICALLY_EQUIVALENT; coefficients are LOCAL |
| `box_shot_share` | same shots, penalty area in metric StatsBomb coordinates (x >= 102, 18 <= y <= 62) | APPROXIMATED (the Wyscout box is a pitch drawing) |
| `opp_half_defensive_actions` | none | **NOT_COMPARABLE**, declared now: Wyscout logs every ground contest from both sides and tags interception on the next event; StatsBomb has tackles, a separate interception event, pressures and recoveries. No faithful estimator exists |

Frozen external rule, same gauntlet, same `decide()`, four leagues, at least 3
evaluable: `ROBUST` if 3+ leagues are at `SHIP` or `SHIP_WITH_BAND` and the mean
over the four common leagues moves by at most 12% relative to Wyscout;
`ROBUST_WITH_SHIFT` if 3+ and it moves by more; `FAILED_EXTERNAL_REPLICATION` if
3+ reject; anything else leaves the construct `RESEARCH_ONLY` with the leg
reported. The 12% boundary is a convention declared here and local to E-09: the house
labelled a 10% shift robust and a 14% shift robust-with-shift, and no code or
prose defines the rule. A house rule written later supersedes it only for later
experiments.
No StatsBomb-derived number, coefficient or identifier enters a committed
machine-readable file or a hosted surface; the leg's aggregate findings appear
only in a research report with attribution.

## 12. Predictions, written before the run

| Subject | Predicted | Reason |
|---|---|---|
| instrument | `ACCEPTED_WITHIN_LEAGUE` | Italy's level |
| `shot_volume` | `ESTABLISHED_NUMBER` | published year-to-year r about 0.66 for strikers |
| `shot_location_value` | `NOT_ESTABLISHED` / `REDUNDANT` | the identity value = volume x mean probability |
| `box_shot_share` | `ESTABLISHED_BAND` | 66 to 88 players per league; no published figure exists |
| `opp_half_defensive_actions` | `ESTABLISHED_NUMBER`, with team explaining a large share | team instruction is context here |

These are predictions, not hypotheses with a test. A miss changes nothing.

## 13. What this experiment cannot show

- Persistence across seasons or clubs: one season, odd/even halves interleaved in time.
- That any candidate is a property of the player rather than of his deployment
  and team. Team is declared context and is reported, not removed.
- Validity against an outcome. No candidate is related to goals, points or
  results here. Reliability is not validity is not decision utility.
- Anything about a single shot, a goalkeeper, a season, tier, sex or provider not evaluated.
- The size of what the instrument omits. The between-player spread of the gap to
  a model with defender positions cannot be estimated from this corpus.
- That the level of the instrument transports to national-team matches; they are not evaluated.
- Cross-provider agreement for any candidate (E-11) or transport across a club change (E-12).

## 14. Interpretation language — frozen

- Redundant: "weighting shots by a location-only conversion model did not
  separate players that counting shots does not, in this corpus." **Not**:
  "shot location does not matter", "xG is useless".
- Instrument not accepted: "this five-parameter location model did not meet its
  frozen out-of-league criteria." **Not**: "conversion cannot be modelled".
- Established: "repeatable within a season among players of the same broad
  position, and not a copy of the declared baselines." **Not**: "measures
  shooting", "measures pressing", "identifies better players".

## 15. Reproducibility and tests

Artifact: protocol, config and code hashes on LF-normalised bytes; protocol commit
verified against git, not typed; content hashes of every input frame; package
versions; candidate fingerprints; seeds; every gate with its count; aggregate
results only. No player or team identifier, no per-player row, nothing over
512 KB. The runner writes the file itself as UTF-8.

Pipelines are developed and tested on synthetic data only. Before any real outcome
is read the runner executes the planted checks of `PIPELINE.md` section 8 at the
rates fixed in `config.json`: over 12 seeded synthetic replicates every planted
candidate effect must be classified established in at least 11, the planted
instrument accepted in all 12 (without scope restriction in at least 10), and no
planted null classified established or accepted in any. A failed self-check stops
the run.

Tests required: hand-computable definition contracts for all four candidates and
their sentences; fingerprints equal `config.json`; zone edges exact at the
lattice; sentinel and unattributed rows never credited; goalkeepers excluded;
`shot_volume` equals the house shots-per-90 column and the plain `ConstructSpec`
form; `decide()` pinned by a truth table written from this document at every
threshold edge; every reject reason and every verdict row reachable; each
departure of 6.1 shown to be no more lenient than the house statistic on the same
data, except T23 which is shown to be flagged; input-order invariance; half
assignment equal to the house split; instrument coefficient recovery, analytic
gradient zero at the fit, leave-one-league-out leakage (changing a held-out
league's labels changes none of its own predictions); every acceptance gate
reachable in both directions; null reporting (`None`, never 0 or NaN);
determinism of the full run under a fixed seed.

---

*Committed before running. Results in `results.json`, interpretation in
`analysis.md`, model card in `MODEL-CARD.md`. If any of them contradicts this
document, this document wins.*

![StatsBomb](../../../../assets/statsbomb/statsbomb-logo.png)

Data source: StatsBomb. The sizes of the two La Liga shifts quoted in section 11
are analysis formed from StatsBomb data, published in
[Stage 1C](../../../STAGE-1C-EXTERNAL-REPLICATION.md). This document carries the
StatsBomb logo as clause 1.4 of the StatsBomb Public Data User Agreement requires.
The conclusions are not the opinions or analytical insights of StatsBomb. No
StatsBomb data is in this repository, and no machine-readable table derived from it
is in the tree. The StatsBomb-side figures printed here are published analysis.
