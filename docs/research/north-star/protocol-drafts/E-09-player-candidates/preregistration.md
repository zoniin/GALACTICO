# E-09 — four player candidates and a location-only shot conversion model

> **DRAFT. Not frozen, not registered, not run.** Written by one designer during the north-star build; attacked on 14 October 2026 by three adversarial reviewers (statistics, football data, constitution) and revised the same day ([REVIEW-RECORD.md](REVIEW-RECORD.md) lists every finding and its disposition); audited independently in four scopes, every claimed blocker rebuilt by a refuter on synthetic numbers, and revised on 18 October 2026 (REVIEW-RECORD, "Audit"). No scope of that audit was READY. The root then ruled on every question the audit's revision put to it (ROOT 2.10, W1 to W10), and a further revision of the same day applies W1 to W9, among them the open-play shot design (W2) and an explicit, empty promotion set for `product_admissible` (W1). That revision was audited a second time in four scopes on 18 October 2026 (REVIEW-RECORD, "Second audit, 18 October 2026"): scopes 2 and 3 had no blocker, scopes 1 and 4 one each, both confirmed by refuters (the product module of the definitions was to read the experiment's config; ROOT 2.2 still says non-penalty shots for `shot_location_value`), and a revision of the same day applies both blockers and every major and minor that held. No question waits for a root ruling, except the textual amendment of ROOT 2.2's `shot_location_value` parenthesis that the root makes before the registration commit (`PIPELINE.md` section 13). This revision has not been audited, and by W10 it is audited again before E-09 is called READY. No outcome named here has been computed. It becomes a protocol only when an audited version is committed under `experiments/preregistered/` in a single commit that precedes any run (`PIPELINE.md` section 13). Section and file references such as ROOT 2.5 point to [ROOT-DECISIONS.md](../../ROOT-DECISIONS.md); see [README](../../README.md) for the working notes it cites.

**Commit this plan, `config.json` and `PIPELINE.md` before any E-09 outcome is computed.
Nothing in the three may change once the first outcome is observed.** This is a
prospective analysis plan on **reused historical data**, not a claim of untouched data
collection; section 2 lists what has already been seen. Every threshold, seed, grid, gate,
list and served sentence lives in `config.json` and is named here by its key; a number that
appears only in this prose is a defect, except four kinds of figure: planning figures
(`planning_figures`, `power_planning`), which are in `config.json` too with their basis;
counts and rates already seen and disclosed in section 2; figures of the published
literature, cited as such; and constants of shipped code, cited by the name of the code that
holds them. A
statement here that disagrees with `config.json` is a defect to be fixed before the protocol
commit, never after. `PIPELINE.md` is frozen with the protocol through
`pipeline_spec_sha256`. Deviations are recorded in `analysis.md`, never silently adopted.

Destination: `committed_experiment_dir`. Tier: PUBLIC (`tier`); the external leg of section
11 alone is LOCAL_LICENSED and gates nothing.

---

## 1. Claim and unchanged boundaries

Four named statistics and one model are taken through the house measurement lifecycle
(`galactico/validation/lifecycle.py`). The question for each statistic is whether it is
repeatable within a season among players of the same broad position, whether it is more
than a statistic the project already has, and whether both hold in at least four of five
leagues. The model is judged out of league against frozen criteria.

| Subject | What it is | Evidence class | Resolves placeholder |
|---|---|---|---|
| `shot_location_v1` | A location-only shot conversion **model**: the probability that an open-play shot became a goal, from the shot's origin and the provider's head-or-body class | PREDICTIVE | instrument only |
| `shot_volume` | Open-play shots per 90 (no penalties, no direct free kicks) | DERIVED | `shot_profile` |
| `shot_location_value` | Location-only conversion value of those shots from the opponent half per 90: the sum of `shot_location_v1` values over the player's shots in the model domain | PREDICTIVE | `shot_profile` |
| `box_shot_share` | Share of those shots that start inside the provider-drawn penalty area | DERIVED | `shot_profile` |
| `opp_half_defensive_actions` | Ground defending duel records and interception-flagged events starting in the opponent half, per 90 | DERIVED | `defensive_action_profile` |

Display names are the `display_name` entries of `config.json` (ROOT 2.5 H14: "location-only
conversion value", never shot quality, never provider xG). Two candidates import the
registered E-11 definitions unchanged (`e11_subject`, `e11_definition`, `e11_config_sha256`):
`shot_volume` is E-11's open-play shots over regulation minutes, and
`opp_half_defensive_actions` is E-11's ground duel or interception in the opponent half over
regulation minutes. E-11's token for the same subject id therefore applies to them as a
cross-provider label. "Imported unchanged" holds for the row masks (the exhaustive tie of
`PIPELINE.md` section 3) and for the ratio of sums; it does not hold for E-11's unit rule,
which drops a player-match with no regulation minute (a substitute who came on at or after the
90th minute), while E-09's season sum keeps that player-match's rows with no minutes added
(section 3, "Known and uncorrected"). `shot_location_value` and `box_shot_share` are not
graded by E-11.

The three shot candidates count open-play shots, leaving out penalties and direct free kicks.
ROOT 2.10 W2 rules this design: for `shot_volume` by its text, which amends ROOT 2.2's
`shot_volume` parenthesis to match, and for `shot_location_value` by removing
`root_2_2_design`, whose `shot_location_value` weighted non-penalty shots (`PIPELINE.md`
DISSENT 6). W2's text did not amend ROOT 2.2's `shot_location_value` parenthesis, which
still reads non-penalty shots; the root amends it, or records that W2 covers both shot
candidates, before the registration commit, and E-09 is not registered before then
(`root_amendment_before_registration`, `PIPELINE.md` section 13). The non-penalty design once
written beside this one is removed and kept in REVIEW-RECORD as the design not chosen.

Not claimed, by any verdict:

- `shot_location_v1` is **not xG supplied by the provider**. The provider supplies none. It
  is not on one scale with any provider's xG.
- **Finishing skill is out of scope.** No goals-minus-model quantity is computed, for any
  player or team, as a construct, a control or a diagnostic.
- `shot_volume` and `shot_location_value` do not say a player shoots well, only how often
  and from where.
- `opp_half_defensive_actions` is not a record of pressing, of winning the ball or of
  defending ability. The corpus has no pressure, tackle or recovery event, and a duel record
  tagged lost counts the same as one tagged won.
- Passing the lifecycle earns a **descriptor**. It does not earn an optimiser weight with
  football meaning, a cross-league comparison, persistence across seasons or across a club
  change, or decision utility.
- The verdicts are exploratory: the data were seen before this protocol (section 2), and
  England is not untouched for this model class. Every record's non-claim says so, the
  instrument's included (`registry_candidate.non_claim`, `registry_instrument.non_claim`),
  and `results.json` carries `interpretation_limits`.

Unchanged: `spec.SPECS`, `CONSTRUCTS`, the five shipped constructs, their fingerprints,
every product evidence gate, and every XI Lab and Match Lab output. No candidate value
reaches Player Lab, Match Lab, the XI tools or a planning page from this experiment. **ROOT
2.6 ARCH D1 binds:** a candidate that survives is not promoted and is not shown beside
players in this release, and `product_admissible` is false for every E-09 subject under
every token (section 10). E-07 and E-08 are not reopened.

### 1.1 The gates against the lifecycle stages

| Stage (`lifecycle.Stage`) | Gate here | Where |
|---|---|---|
| DEFINITION | fingerprints and hand-computable contracts; the instrument's acceptance | 4, 5 |
| RELIABILITY | position-centred split-half lower bound, number and band thresholds | 6 step 3 |
| CONFOUND_AUDIT | nuisance R-squared above the ceiling rejects (nuisance kinds only); the joint audit is reported | 6 steps 5 and 8 |
| CONSTRUCT_VALIDITY | **not tested.** The observable implications of section 5 are written down and not tested; no outcome criterion exists for these candidates in this corpus | 13 |
| INCREMENTAL_INFORMATION | the baseline ceiling over the declared battery, at the larger of the uncentred and the position-centred correlation | 6 step 4 |
| ROBUSTNESS | four of five leagues; the LOCAL external leg is a label only | 9, 11 |

`ConfoundFinding.damaging` (variance explained by a nuisance kind above the threshold that
`lifecycle.ConfoundFinding.damaging` holds, a constant of shipped code) is reported
per league and does not gate; the gate is the frozen rule's nuisance ceiling
(`nuisance_r2_ceiling`), as in Stage 1B.

## 2. Prior exposure of the data

| What | Seen by | Touches E-09 how |
|---|---|---|
| All five Wyscout leagues, full season | Stage 1, 1B, 1C for seven other axes | `shots_per_90` was a baseline column there: its correlation with other axes was computed and only the maximum per axis reported. Its own reliability was never computed |
| Shot origin and goal by 16x12 grid cell, per league | every xT fit | A per-cell conversion rate is a component of the shipped xT surface. It was never evaluated out of sample or read as a conversion model |
| Spain and England, March to May rows | E-07, E-08 | Opening-30-minute passing forecasts. No shot or defensive quantity |
| Italy | E-02 | Metronome index only |
| Shot marginals, five leagues | council reconnaissance (a working note kept out of the repository; README, "What the drafts cite") | Goal rate by league (Spain 11.08%, England 10.82%, Italy 9.69%, Germany 10.83%, France 10.48%), by body-part tag (head-or-body 12.5%, footed 10.2%), by counter-attack and opportunity tags, for penalties and direct free kicks; shot counts by 5 m distance band; shot-count quantiles per player; 4 of the 100 shot rows recorded at or behind the halfway line are tagged goals |
| Duel, interception and attribution counts | council reconnaissance (working note, not kept) | Outcome-tag counts by duel sub-type, share of duel records with no player by league and by team-match, team-match volume quantiles |
| Eligibility counts | this design pass (structure-only scripts, working notes, not kept) | Outfield players at 900+ nominal minutes per league (319 / 306 / 306 / 270 / 306); reliability-set sizes; players with 30+ shots and 10+ per match set (80 / 84 / 88 / 66 / 80); quantiles of the opponent-half defensive-action count among eligible players; shot rows in and out of the model domain by `start_x` only; lattice count of penalty-area shots. These counts are planning values. The eligibility and share-set sizes set the two sizes of `power_planning` and the share floor's reach, and every sample gate (`minimum_reliability_units`, `minimum_audit_units`) sits below all of them. `degenerate_sd` is the numerical tolerance of the house correlation helper and was not set from any count. `maximum_zero_share` is a round value; the record of this pass does not show what informed it, so it is disclosed as frozen after the opponent-half quantiles were seen, and the zero share is reported per league beside it. Every pinned count of section 3 is recomputed by the root with a committed structure-only script before registration (`counted_by_root_before_registration`) |
| Open-play shot rows before four cutoff dates (9,693 pooled before 2017-10-22; 1,799 in Spain) | reconnaissance critic (working note, not kept) | exposure only; it fixes the pooled as-of rule of section 10 |
| Wyscout England 2017/18: 8,801 non-penalty shots, 5,139 in the provider-drawn box | E-11 prior exposure (registered) | the same box as `box_shot_share`, pooled over players |
| Every shot's start coordinates of both teams, per match; per player-match and per team-match counts of shots (shot events, direct free-kick shots and penalties) and of tagged interceptions, on the served matches | Match Lab, served since its release | match-level records, never a player-season statistic |
| Tag sidecar build: body-part, duel-outcome and goal-zone tag counts per league | ADR-0028 and its audit | structure only; body part is a model input here |
| StatsBomb 2015/16, four leagues | Stage 1C | within-provider reliability, confound share, baselines and level shifts of the five shipped constructs; no shot or defensive quantity of this protocol |
| Published fits on this corpus | Soccermatics (England, 8,451 shots, in-sample logistic); Mead et al. 2023 (five leagues, random split) | The model family and the expected skill range were chosen with these in view. England is not untouched for this model class |

Not computed by anyone in this project before the protocol commit: any split-half
reliability, confound audit or baseline correlation of a candidate; any fit or evaluation of
a shot conversion model; any relation between a candidate and an outcome.

One planning figure is derived from the disclosed marginals and stated so that it cannot
later be presented as a surprise: if shot-location mix were identical across leagues,
Italy's observed-over-expected ratio under a model trained on the other four leagues would
be about 0.897 (`planning_figures.italy_o_e_if_location_mix_identical`, with its basis).
The level thresholds of section 4.4 were not widened to accommodate it.

## 3. Data, cohorts and exclusions

Public Pappalardo/Wyscout 2017/18 only (`leagues`, `season`). The neutral frames named in
`public_tables` are read through `galactico.storage.public.load_public` with the column list
`action_columns`. Body part and the provider's shot family come from the tag sidecar
(`galactico.ingestion.sidecar`, ADR-0028): `verify`, then `load(league, "events",
columns=sidecar_columns)` and `attach`, the only sanctioned join. The head-or-body class is
provider tag 403; it pools headers with chest, knee and other non-foot contact, so it is
named `head_or_body`, never "header" (ROOT 2.5 H14).

| Rule | Key | Note |
|---|---|---|
| Periods | `periods` | the leagues contain no other; the filter is asserted to drop zero rows |
| Shot set | neutral `type == "shot"` | the provider's Shot event, which E-11 calls `open_play_shot`. Penalties and direct free-kick shots are `set_piece` rows and are excluded by construction. Shots after a set-piece delivery are included. The sidecar's `shot_family` is pinned to the neutral type (`shot_family_pins`, `expected_shot_family_disagreements`) |
| Model domain | `model_domain`, `structure_identity` | a shot row starting in zone `opponent_half`: `start_x` strictly above 0.50 and not a location sentinel. Outside it are shot rows at a sentinel start (either pair of `location_sentinels`) and non-sentinel shot rows recorded at or behind the halfway line (`start_x <= 0.50`); the two sets are disjoint, and per league shot rows = in-domain + behind-halfway + sentinel-start, asserted before any outcome. Their recorded location is not trusted. They are excluded from model fitting, evaluation and `shot_location_value`, counted per league (`expected_behind_halfway_shot_rows`, `expected_sentinel_start_shot_rows`), and stay in `shot_volume` and in the denominator of `box_shot_share` |
| Minutes | `minutes_rule`, `regulation_minutes_cap` | per player-match the lineup minutes capped at 90, which is E-11's `minutes_regulation` on this provider, imported unchanged. The house sums nominal lineup minutes, which credit a starter substituted after the 90th minute with more than 90; capping can only lower a player's minutes, so no evidence gate is lowered (R6) |
| Eligible player | `minutes_floor`, `outfield_positions`, `goalkeeper_position` | 900+ league minutes, broad position DF, MD or FW, `player_id != 0`. Goalkeepers excluded (ADR-0025) |
| Match sets | `split`, `split_rule` | two sets of a league's matches by the parity of a match's position among the league's sorted game ids, called match set 0 and match set 1; never "halves", which are the periods |
| Match-set floor | `match_set_minutes_floor` | 300+ minutes in each match set; house value |
| Share floor (`box_shot_share` only) | `share_floor_season_shots`, `share_floor_match_set_shots`, `share_floor_counts` | 30+ shots in the season and 10+ in each match set, counting every shot row of the denominator; a share over a handful of shots is noise (`planning_figures.share_noise_below_shots`) |
| Unattributed rows | | rows with `player_id == 0` are never credited to a player: about one ground defending duel record in ten, as disclosed in section 2 (`planning_figures.unattributed_ground_duel_share_disclosed`). Missing stays missing; no reallocation |
| Location sentinels | `location_sentinels` | a row whose start is exactly (0,0) or (1,1) is excluded from every zone test and from the model domain, and kept in zone-free counts |
| No exclusion | | on team, age, club strength or league |

Known and uncorrected, recorded so that it is not later presented as a discovery: the
minutes floor conditions on selection; lineup minutes ignore stoppage time; a mid-season
mover is one player with pooled minutes and is assigned the team of most minutes
(`player_team_rule`); the share floor conditions on shooting; a substitute who came on at or
after the 90th minute gets no capped minute from the adapter, so a shot or a defensive
action of his in that match enters the season numerator with no minute added to the
denominator, where E-11's `player_match` unit (at least `minimum_regulation_minutes_player_match`
regulation minutes on both sides) drops the row. Those rows are counted per league in
`results.json` (`structure`, `PIPELINE.md` 7.1) and are not removed.

Structural pins in `config.json` (`expected_*`, the shot-family pins, the sidecar manifest's
`actions_event_ids_equal` and versions) are checked before any outcome is computed. A
mismatch stops the run with nothing written; that is a pipeline defect, not an outcome, and
a corrected run is disclosed in `analysis.md` under the failed-execution rule of `PIPELINE.md`
section 7. Every structural pin, the body-part coverage, the clause overlap and the
shot-family disagreements included, is recounted by the root after the audit and before the
registration commit with one committed structure-only script (`counted_by_root_before_registration`).
Counts that parameterise nothing (`counted_by_root_rule`: shot rows, in-domain,
behind-halfway and sentinel-start shot rows, goals, matches, the folder digests) are filled
where null or replaced where they differ, with the difference stated, and those keys are the
only edits to `config.json` after the audit; the file is then registered byte for byte. The
three assumption pins (`counted_by_root_assumption_pins`: body-part coverage on shots, clause
overlap rows, shot-family disagreements) are different: the frozen text depends on their
values (the model refuses a shot with no body part, section 5.4 states that the two clauses
do not overlap, a disagreement stops phase 2), so a count that departs from the draft's value
is never written into the config. Registration stops and the draft returns to a revision that
freezes a rule for those rows, then to an audit (`counted_by_root_assumption_rule`). The pins
carried over from working notes that were not kept are therefore never trusted unchecked. The planning count of shot rows at or behind
the halfway line by `start_x` alone, sentinel rows included, is
`planning_shot_rows_at_or_behind_halfway_by_x_only`.

## 4. The instrument — frozen

### 4.1 Definition

```
X     = (1 - start_x) * 105          metres from the goal line (convention, not measurement)
C     = |start_y - 0.5| * 68         lateral distance from the goal-to-goal axis (convention)
d     = sqrt(X^2 + C^2)              metres to the goal centre
theta = atan2(7.32 * X, X^2 + C^2 - 3.66^2)     visible goal angle, radians, in [0, pi]
H     = 1 if the sidecar body part is head_or_body else 0
```

(`pitch_length_m`, `pitch_width_m`, `goal_width_m`.)

| Model | Terms (`model_terms`) | Role |
|---|---|---|
| `M0` | intercept (the training goal rate; not fitted) | reference |
| `MD` | intercept, d | comparator |
| `M1` | intercept, d, theta, H, H*d | default instrument |
| `MFLEX` | `M1` plus hinge terms (d-8)+, (d-16)+, (d-25)+, (theta-0.4)+, (theta-0.9)+, and H*theta | declared challenger |

Family: unpenalised logistic regression, fitted by iteratively reweighted least squares in
NumPy (`irls_max_iterations`, `irls_tolerance`, `irls_max_halvings`,
`irls_halving_relative_tolerance`; the stop is judged on the full Newton step, `PIPELINE.md`
section 4). Label: the `goal` flag on the shot row.

Never a feature: the provider opportunity tag (201; on 99.5% of goals and 67.3% of
non-goals, so it was assigned with the result in view), the accuracy tags, the blocked tag,
the goal-mouth zone tags, the counter-attack tag (a tagger's judgement), the shooter, the
team, the league, the game state, anything after the shot. There is no shot end location
in this corpus.

### 4.2 Leave-one-league-out

Five folds. Fold f fits every model on the other four leagues and predicts league f, so
every shot of a league has a value from a model that saw none of that league's matches. A
player who moved between two of the five leagues in the 2017/18 winter window has shots in
both the held-out league and a training fold; the model has no player term, so this leaks
nothing about him. Candidate values in league f use the fold-f instrument only. The
reference rate for skill is the **training** goal rate.

### 4.3 Frozen selection

The instrument is `M1` unless the pooled relative log-loss gain of `MFLEX` over `M1`,
`(LL_M1 - LL_MFLEX) / LL_M1` on out-of-league predictions, is at least
`selection_relative_log_loss_gain` **and** the fold gain reaches it in at least
`selection_minimum_folds` of 5 folds **and** `MFLEX` converged in every fold
(`selection_requires_challenger_converged_in_every_fold`); then the instrument is `MFLEX`.
Nothing else is tried. The selected specification is reported as `shot_location_v1/M1` or
`shot_location_v1/MFLEX` in results and on the model card. Selecting between two models on
the same out-of-league predictions that are then judged is mildly optimistic and is
disclosed, not corrected.

### 4.4 Frozen acceptance

All statistics use out-of-league predictions of the selected specification. Intervals are
two-sided 95% percentile intervals (`interval_quantiles`, `interval_quantile_method`) from
`bootstrap_replicates` match-level resamples within each held-out league (`bootstrap_rule`);
coefficients are held fixed, so training-fold uncertainty is omitted. Pooled statistics add
the five leagues' resampled sums.

| Gate | Statistic | Passes if (config keys) | Basis |
|---|---|---|---|
| S-count | sample, before any fit | each training fold and each held-out league meets `gate_s_count` | logistic-basic converges near 6,000 shots (Robberechts & Davis 2020; `planning_figures.literature`) |
| S-fit | convergence, after the fits | every model of `gate_s_fit_models`, and the instrument, converged in every fold (`gate_s_fit_rule`); on the public run a challenger that did not converge in every fold is not selectable and fails nothing, so the rule there equals the earlier one; on the external leg the refitted instrument must converge in every fold | |
| R1 | Brier skill against the training rate | pooled point at least `gate_r1_pooled_brier_skill_minimum`, pooled lower bound at least `gate_r1_pooled_brier_skill_lower_minimum`; lower bound above `gate_r1_league_brier_skill_lower_exclusive_minimum` in `gate_r1_leagues_required` of 5 held-out leagues | published 0.10 to 0.13 for this feature set; planning standard error per league in `planning_figures` |
| R2 | pooled relative log-loss gain of the instrument over `MD` (`gate_r2_gain`) | lower bound above `gate_r2_log_loss_gain_over_comparator_lower_exclusive_minimum` | angle and head-or-body must earn their parameters |
| R3 | calibration slope (logistic recalibration) | within `gate_r3_calibration_slope_range` in `gate_r3_leagues_required` of 5 | planning spread per league about 0.05 (`planning_figures.r3_league_calibration_slope_sd`; the earlier 0.04 understated it) |
| R4 | observed over expected, pooled, in the five subgroups of `gate_r4_subgroups` | each within `gate_r4_subgroup_o_e_range` | spreads simulated on synthetic leagues in `planning_figures.r4_subgroup_o_e_sd_synthetic_planted`; the footed and head-or-body ratios are 1 by construction up to second-order terms (below) |
| R5 | pooled AUROC (`auroc_rule`) | at most `gate_r5_pooled_auroc_maximum` | published 0.75 to 0.79; anything higher on this schema is treated as a leak |
| L1 | observed over expected per held-out league | within `gate_l1_o_e_range` in `gate_l_leagues_required` of 5 | planning standard error in `planning_figures.l1_league_o_e_se` |
| L2 | calibration intercept at slope 1 | absolute value at most `gate_l2_intercept_absolute_maximum` in `gate_l_leagues_required` of 5 | |
| L3 | expected calibration error over `ece_bins` equal-mass bins cut at value boundaries (`ece_binning_rule`, `ece_weighting`); largest bin gap (`mce_rule`) | at most `gate_l3_ece_maximum` and at most `gate_l3_mce_maximum` in `gate_l_leagues_required` of 5 | a bin never splits tied probabilities, so no row order or event id moves either number |

A calibration fit that does not converge gives `None`, and `None` fails its gate in that
league (`calibration_fit_failure`). Any undefined gated statistic fails its gate. When S-count
fails nothing is fitted and every selection, fit and metric field is null; when S-fit fails
the fits and the R and L statistics are reported and their gates are not evaluated; the
failed-gate list and reason follow `instrument_inconclusive_rule`.

**What R4 can see.** Each fold's training score equations set the sums of (y - p) and of
H(y - p) to zero over the four leagues it trains on, so a held-out league's surplus in a
subgroup that is a model term is offset by the four folds in which that league trains.
Pooled over the five held-out leagues, the observed-over-expected ratio of the footed and of
the head-or-body shots is therefore 1 up to second-order terms for any instrument with an
intercept and an H term, which `M1` and `MFLEX` both have, on any data; between-league
differences also cancel in the distance bands. R4 is kept as frozen and checks only a misfit
of functional form that all leagues share, in practice in the distance bands; a misfit that
differs by league is the business of R3 and L1 to L3. This is disclosed, not repaired.

R gates concern relative value within a league. L1 and L2 concern level; L3 (binned
calibration error) concerns level and calibration across value bins, and a league can fail
it with its level right, which is why the `ACCEPTED_WITHIN_LEAGUE` statement names both.
The candidates are analysed within a league, where a league-constant shift in level moves no
ordering; cross-league use needs level as well.

**Multiplicity.** Acceptance is an intersection of gates: every gate must pass, so the
chance of accepting a model that fails one criterion is at most the chance of that one gate
passing wrongly. No adjustment is made, and none is needed for that direction. The two
model specifications are compared once, by the frozen rule of 4.3.

### 4.5 Instrument verdict

| Outcome, first match wins | Token |
|---|---|
| S-count or S-fit fails | `INCONCLUSIVE` |
| S passes, any of R1 to R5 fails | `NOT_ESTABLISHED` |
| S and R1 to R5 pass, any of L1 to L3 fails | `ACCEPTED_WITHIN_LEAGUE` |
| every gate passes | `ACCEPTED` |

The tokens are `verdict_vocabulary.instrument`.

## 5. Candidate measurements — frozen

Definitions are `CandidateSpec` objects in `galactico/features/candidates.py`, outside
`spec.SPECS` (ROOT 2.5 O3); ROOT 2.10 W3 rules that a `ConstructSpec` is generated from one
at promotion, never written beside it. Their fingerprints are in `config.json`; a run whose
computed fingerprints differ stops before any outcome. A fingerprint identifies numerator, measure,
scaling, denominator and instrument; the minutes rule is `minutes_rule`, hashed with the
config. The claim record of each candidate (`AxisSpec`) holds, as constants in
`candidates.py` tied to the config by test (product code cannot read an experiment's config,
`PIPELINE.md` section 3), its construct, observable implication, negative control and
incremental claim, equal to `candidates[*].claim`, and its confounds, equal to the keys of
`confound_kinds`; the zones, sentinels and describe nouns are held and tied the same way. The
Claim, Observable
implication, Negative control and Incremental claim bullets below restate those strings;
where they differ the config wins.

### 5.1 `shot_volume` (`1c6517c2be31`)

- **Definition.** Count of shot rows / minutes x 90, minutes by `minutes_rule`. E-11's
  `shot_volume`, imported unchanged.
- **Claim.** How often the player shoots in open play. **Non-claim.** That the shots are
  good ones.
- **Observable implication.** A player who shoots more in one match set shoots more in the
  other, among players of the same broad position.
- **Confounds.** touch volume (context), team (context), broad position (constitutive).
- **Negative control.** Must not be a near-copy of touch volume or of mean field position.
- **Incremental claim.** None. This is the house baseline column itself, proposed under its
  own name, as pass completion was after E-03. Its own column is therefore removed from its
  battery and from no other.

### 5.2 `shot_location_value` (`537cef62eb4e`)

- **Definition.** Sum of the fold instrument's values over the player's shot rows in the
  model domain / minutes x 90.
- **Claim.** Shot volume weighted by where the shots came from. Shot volume is a declared
  component. **Non-claim.** The opportunity as the shooter met it: defenders, goalkeeper,
  pressure and shot type are not in the number.
- **Observable implication.** Two players with equal shot volume separate if one shoots
  from closer and more central positions.
- **Confounds.** touch volume (context), team (context), broad position (constitutive).
- **Negative control.** Must not be a near-copy of `shot_volume`, at the frozen
  `baseline_ceiling`. (The expected closure as redundant is a prediction of section 12.)
- **Incremental claim.** The location weighting separates players that counting does not.
  ROOT 2.2 requires it to show that or be rejected as redundant: a league rejected as
  redundant closes it as redundant unless it is established (`redundancy_closes_first`,
  section 9).
- **Dependency.** Evaluated only if the instrument token is `ACCEPTED` or
  `ACCEPTED_WITHIN_LEAGUE`; otherwise no statistic of it is computed and its token is
  `INCONCLUSIVE` or `INCONCLUSIVE_INSTRUMENT` (section 9.1).

### 5.3 `box_shot_share` (`af2b2b118e73`)

- **Definition.** Shot rows starting at `start_x >= 0.84` and `0.19 <= start_y <= 0.81`,
  not at a sentinel / shot rows. The box is the provider's pitch drawing in provider
  coordinates, a frozen convention.
- **Claim.** Where the player's shots originate. **Non-claim.** A preference; the share
  includes deployment and team-mates.
- **Observable implication.** A player whose shots come from inside the area in one match
  set shows the same in the other, among players of his position.
- **Confounds.** touch volume (nuisance), shot volume (nuisance), team (context), broad
  position (constitutive).
- **Negative control.** Must not be a near-copy of mean field position or of shot volume.
- **Incremental claim.** None beyond location. It is the model-free location descriptor: it
  needs no instrument, so the location half of `shot_profile` is tested even if the
  instrument is not accepted, and under weakest-class composition a counted share outranks
  a modelled mean. A per-shot mean of the instrument is deliberately **not** a candidate and
  is not computed.

### 5.4 `opp_half_defensive_actions` (`72619cd8130b`)

- **Definition.** Rows that are (`type == "duel"` and `subtype == "Ground defending duel"`) or
  (`interception` flag true), starting in zone `opponent_half` in the acting player's own
  frame, / minutes x 90. Any duel outcome. The two clauses do not overlap in this corpus
  (`expected_clause_overlap_rows`). E-11's `opp_half_defensive_actions`, imported unchanged.
- **Honest reading of the inputs.** Each duel is logged twice, once per participant; a
  player's own record is counted once. The neutral duel `success` means not-lost and is
  **not used**. The sidecar's won / lost / neutral outcome is **not used**: the candidate
  counts engagements, and outcome composition would be a different construct needing its
  own registration. Interception is a tag on the intercepting player's next event, which
  can be a clearance; a flagged clearance counts once, as an interception.
- **Claim.** How often the player is recorded contesting or cutting out the ball in the
  opponent half. **Non-claim.** See section 1.
- **Observable implication.** Repeatable between match sets among players of the same
  position, and not reducible to how much the player is in that half at all.
- **Confounds.** share of the team's ground defending duel records with no player
  (nuisance), touch volume (context), team (context), broad position (constitutive).
- **Negative control.** Must not be a near-copy of ground defending duels and
  interceptions over the whole pitch, of on-ball presence in the opponent half, or of mean
  field position.
- **Incremental claim.** Location of defensive activity, separate from its amount.

## 6. Gauntlet — frozen

Per league and candidate, in this order. The count gates of section 8 are evaluated for
**all** leagues and candidates before any statistic below is computed.

1. **Sets.** A, the audit set: eligible players with a finite full-season value (with the
   share floor where `share_floor`). R, the reliability set: A with both match-set floors
   (and both match-set share floors), keeping only position groups of at least
   `minimum_position_group` players in R. g is the number of position groups kept.
2. **Split.** `split_rule`, the house method.
3. **Reliability.** Within each match set, subtract from each player's value the mean over
   R of his broad position (`centring`). `r_half` is the Pearson correlation across R of the
   two centred vectors (house `split_half_reliability`, called with mappings keyed by
   player); `r_sb = 2 r_half / (1 + r_half)`. The gate is `reliability_low = half_low`
   (`reliability_low_rule`, `half_low_rule`): the Spearman-Brown transform of the lower end
   of the Fisher-z interval for `r_half`, with critical value `interval_z` (the two-sided 90%
   interval, whose lower end is a one-sided 95% bound, ROOT 2.5 O5) and standard error
   `1/sqrt(n - 2 - g)`, since a correlation of within-group centred vectors is a partial
   correlation on g - 1 group indicators. A strongly negative `r_half` therefore gives a
   strongly negative bound, never a missing one, except where `r_half` is so close to -1
   that the transform underflows to NaN in floating point, and the guard of step 6 makes the
   league `INCONCLUSIVE` (practically unreachable; stated, not repaired). The house interval
   (`AxisReliability.interval` on `r_sb`) is reported, never gating (`house_interval_role`);
   it is `None` when `|r_sb| >= 1`.
4. **Baseline.** For each column of the candidate's battery with sd over A at least
   `degenerate_sd` (a column below it is dropped and recorded), the absolute Pearson
   correlation with the value is computed twice over A: on the raw values, and on values and
   column both centred by broad position over A (`position_centring_set`). The column's
   correlation is the larger of the two (`baseline_centring`). `baseline_r` is the largest
   over the battery; every column that attains it is listed (`baseline_tie_rule`).
5. **Nuisance.** `nuisance_r2` is the unadjusted R-squared, over A, of the value on the
   candidate's nuisance-kind columns only, computed raw and position-centred, the larger
   kept (`nuisance_centring`). A candidate with no nuisance column has none.
6. **Guard.** Each vector of `degenerate_vectors` (the full-season values over A, and each
   match set's raw values over R) is tested on its own: sd below `degenerate_sd`, or a share
   of exact zeros above `maximum_zero_share`, makes the league `INCONCLUSIVE` for that
   candidate and names the vector. So does any non-finite input to the rule, or an undefined
   `half_low`. The rule is then not called.
7. **Status.** `decide(reliability_low, nuisance_r2 or 0.0, baseline_r, kind_is_nuisance)`,
   the frozen Stage 1B rule, imported unchanged from `frozen_rule_path`: a baseline above
   `baseline_ceiling` rejects first; then, for a candidate with nuisance columns, a nuisance
   R-squared above `nuisance_r2_ceiling`; then a lower bound of at least `reliability_number`
   is `SHIP`, of at least `reliability_band` is `SHIP_WITH_BAND`, else `REJECT`. The rule is
   pinned by the hash of its source text (`frozen_rule_decide_source_sha256`) and by its
   three module constants (`frozen_rule_constants`); its nuisance threshold is a literal in
   its body (`frozen_rule_nuisance_literal`), held to `nuisance_r2_ceiling` by a truth
   table. The runner's file hash is recorded and does not gate: ADR-0026 and ADR-0027
   changed `run_replication.py` twice after this draft was written, and `decide` did not
   change.
8. **Reported, never gating** (as in Stage 1B): the joint audit
   `discriminant_validity(value, [touches, team one-hot, position one-hot], ties=tie_policy)`
   with its unadjusted and adjusted R-squared and noise floor k/(n-1); the rank correlation
   between raw and residualised values under average ranks; the top-`top_k` survivor count,
   which is `null` when the twelfth value ties the thirteenth (raw or adjusted), reported
   with the two tied counts and the sentence `top_k_tied_statement`; the uncentred pooled
   reliability with the house interval; reliability within each position with at least
   `within_position_report_minimum` players (`within_position_rule`) and the context limits
   (`context_limit_rule`); reliability centred on team as well as position; every battery
   correlation under both centrings; `ConfoundFinding.damaging`; mean, sd and zero share; the
   house replication label from `classify_replication`.

Batteries (exact columns in `config.json`). House nine (`house_battery`): `minutes`,
`touches`, `touches_per_90`, `passes_per_90`, `pass_completion`, `mean_x`, `mean_y`,
`mean_pass_length`, and open-play shots per 90, which is `shot_volume` itself. Declared
additions: `opp_half_on_ball_per_90`, passes and touches without the interception flag
starting in the opponent half, per 90 (`opp_half_on_ball_rule`): it leaves out shot rows and
interception-flagged rows, so it contains no candidate's own rows; and
`duel_or_interception_per_90`, the two clauses of `opp_half_defensive_actions` with the zone
removed (`duel_or_interception_rule`), which contains that candidate by design: it is the
negative control of amount. The house columns `touches`, `touches_per_90`, `mean_x` and
`mean_y` are taken over on-ball rows that include shots and duels, as the house defines them;
they are not redefined.

| Candidate | Battery |
|---|---|
| `shot_volume` | house nine without its own column, plus `opp_half_on_ball_per_90` |
| `shot_location_value` | house nine, plus `opp_half_on_ball_per_90` |
| `box_shot_share` | house nine, plus `opp_half_on_ball_per_90` |
| `opp_half_defensive_actions` | house nine, plus `opp_half_on_ball_per_90`, `duel_or_interception_per_90` |

### 6.1 House methods inherited and departed

No single principle covers the departures. Each is stated with its direction against the
house statistic on the same data: **stricter** (it can only make survival harder),
**lenient** (it can only make survival easier, or easier in every case examined; flagged per
league in `results.json` and named in `analysis.md` for any candidate that survives where it
was active), or **neither** (it can move survival in either direction). Of the "neither"
departures, position centring of reliability is flagged as well
(`position_centred_reliability` in `departures_active`), because its house counterpart, the
uncentred pooled reliability, is computed and reported beside it; T22 and the minutes rule
are not flagged, because no house counterpart of them is computed on these data.

| Trap | Choice | Direction | Why |
|---|---|---|---|
| T8 baseline batteries | **Departs.** One battery function for this experiment: the Stage 1B eight, plus `minutes` (as the Stage 1 report and E-02 list it), plus the declared columns above | stricter: more columns can only raise the maximum | three scripts hold three lists; a candidate's closest baseline must not depend on which script ran it |
| T8 identity column | **Departs.** `shot_volume` is removed from its own battery only | lenient, necessary | the house battery contains shots per 90; without this the candidate is rejected against itself at r = 1 |
| Declared presence column | `opp_half_on_ball_per_90` holds no shot and no interception-flagged row | lenient against a column holding them, necessary | a column that contains a candidate's own rows measures the candidate |
| T9 xT surfaces | **Not applicable by design.** No candidate and no battery column uses an xT surface | — | the three turnover recipes cannot move these numbers |
| T11 thin samples | **Departs.** A league needs `minimum_reliability_units` players in R and `minimum_audit_units` in A or it is `INCONCLUSIVE`; the point estimate is never used as a bound | stricter | the house fallback graded the thinnest sample `NUMBER` |
| T17 interval method | **Departs.** The gate is `half_low` with `n - 2 - g` | stricter in every case examined: on a grid of `r_half` and n the half-r bound was never above the house bound, and the degrees-of-freedom correction lowers it further | the house bound is anti-conservative at small n (about 0.04 above the half-r bound at n = 66 and a half correlation of 0.5); the house number stays reported for comparison with the shipped five |
| T18 R-squared floor | **Departs.** The gating R-squared uses nuisance columns only (k of 1 or 2). The joint R-squared is published with its adjusted value and floor | see T23 | about 20 regressors at n = 66 put the unadjusted floor near 0.31 |
| T20 split | **Inherits** the league-wide split by the parity of a match's position among sorted game ids, and the 300-minute floor per match set. Exposure imbalance per match set is reported | — | a per-team alternation would put one match in different sets for its two teams |
| T22 shared instrument | **Departs.** Both match sets share an instrument that never saw the league | neither | the house match sets share a surface fitted on the league itself |
| T23 nuisance rule | **Departs, flagged.** The rule thresholds nuisance-kind variance only, as its own docstring says; the house code thresholded it jointly with team. `house_joint_r2_exceeds_ceiling` is published per league | lenient | the docstring is the rule's statement |
| T24 degenerate vectors | **Departs.** Step 6 | stricter | the house helper returns 0.0 for a constant, and the rule passes a NaN baseline |
| Position centring of reliability | **Departs.** Reliability is gated on position-centred values | neither: lower when position means are stable between match sets, which the alternating split makes likely; higher when they move (a planted case shows both) | pooled reliability of a shot count is mostly the statement that forwards shoot more than defenders |
| Baseline and nuisance centring | **Departs.** The larger of the raw and the position-centred statistic | stricter than the raw statistic on the same set | a near-copy within every position must not pass because positions dilute the pooled correlation |
| Goalkeepers | **Departs.** Excluded (ADR-0025) | lenient on baseline correlations: goalkeeper rows can extend a line between a candidate and a battery column | goalkeepers are outside every candidate's declared context |
| Minutes | **Departs.** `minutes_rule` (E-11's regulation minutes) | stricter on the floor; neither on the statistics | one definition with E-11 for the two shared subjects |

Required test: each departure's direction is shown on a planted frame and each lenient one
is flagged in `results.json` (`departures_active` per league and candidate).

## 7. Models and baselines, summarised

| Compared | Against | Criterion |
|---|---|---|
| instrument | training goal rate; distance-only model | R1, R2 |
| `M1` | `MFLEX` | 4.3 |
| each candidate | its battery, raw and position-centred | `baseline_ceiling` |
| each candidate | its match sets, position-centred | `reliability_number` / `reliability_band` on `half_low` |
| `shot_location_value` | `shot_volume` | the same ceiling, plus `redundancy_closes_first` |

No hyperparameter search, no feature selection, no per-league tuning, no sensitivity re-run
chooses a result.

## 8. Sample gates

| Gate | Value | Failing it |
|---|---|---|
| players in R, per league and candidate | `minimum_reliability_units` | league `INCONCLUSIVE` for that candidate |
| players in A, per league and candidate | `minimum_audit_units` | same |
| share of the pitch-wide union rows of `opp_half_defensive_actions` with no player, per league | at most `maximum_unattributed_share` | league `INCONCLUSIVE` for `opp_half_defensive_actions` |
| degenerate or non-finite input (6 step 6) | `degenerate_vectors` | league `INCONCLUSIVE` for that candidate |
| instrument gates S-count and S-fit | 4.4 | instrument `INCONCLUSIVE` |

**Evaluable leagues.** E is the set of leagues whose status for the candidate came from
`decide()`: `SHIP`, `SHIP_WITH_BAND` or `REJECT` (`evaluable_statuses`). A league that
failed a count gate or the guard of step 6 is `INCONCLUSIVE`, is outside E, and counts in
neither the surviving nor the rejected leagues. If the count gates leave a candidate fewer
than `minimum_evaluable_leagues` leagues, no statistic of that candidate is computed in any
league, and every league that passed its count gates has status `INCONCLUSIVE` with reason
`league_not_computed_reasons.too_few_evaluable_leagues` (for `shot_location_value` under an
instrument that is not accepted, `league_not_computed_reasons.instrument_not_accepted`, which
is recorded where both apply, as rows 1 and 2 of 9.1 precede row 3:
`league_not_computed_precedence`). A
league that becomes `INCONCLUSIVE` only through the guard keeps whatever it computed before
the guard, reported under its own status.

## 9. Decision rule — frozen

### 9.1 League status and candidate token

**League status.** `INCONCLUSIVE`, or the output of `decide()`: `SHIP`, `SHIP_WITH_BAND`,
`REJECT`. A reject carries one reason, read off the frozen rule by counterfactual calls:
`REDUNDANT` if the baseline alone rejects; else `CONFOUNDED` if the nuisance R-squared
alone rejects; else `UNRELIABLE`.

**Candidate token.** |E| is the number of evaluable leagues, s the leagues in E at `SHIP`
or `SHIP_WITH_BAND`, n those at `SHIP`, j those at `REJECT`.

| # | Condition, first match wins | Token |
|---|---|---|
| 1 | candidate depends on the instrument and the instrument is `INCONCLUSIVE` | `INCONCLUSIVE` |
| 2 | candidate depends on the instrument and the instrument is `NOT_ESTABLISHED` | `INCONCLUSIVE_INSTRUMENT` |
| 3 | \|E\| < `minimum_evaluable_leagues` | `INCONCLUSIVE` |
| 4 | n >= `survival_leagues` | `ESTABLISHED_NUMBER` |
| 5 | s >= `survival_leagues` | `ESTABLISHED_BAND` |
| 6 | the candidate is in `redundancy_closes_first` and at least one league of E is `REJECT` with reason `REDUNDANT` | `NOT_ESTABLISHED_REDUNDANT` |
| 7 | j > \|E\| / 2 | `NOT_ESTABLISHED_` + the most frequent reject reason; ties resolve in `reject_reason_tie_order` |
| 8 | otherwise | `NOT_ESTABLISHED_MIXED` |

`INCONCLUSIVE` and `INCONCLUSIVE_INSTRUMENT` (status INCONCLUSIVE) mean nothing was
compared at the candidate level: a frozen gate failed, or the instrument the candidate
depends on was not judged (row 1) or was judged and not accepted (row 2). Both leave the
candidate untested in the Player Lab counts. `NOT_ESTABLISHED_*` means the comparison ran
and the criterion was not met: a published null, not evidence that the football concept is
absent. The rows are exhaustive and mutually exclusive by order. The tokens are
`verdict_vocabulary.candidate`; there is no other token and none is assigned by hand. Row 6
is ROOT 2.2's requirement that the location-weighted value show incremental information over
shot volume or be rejected as redundant; for the other three candidates a redundant league
is weighed by rows 7 and 8. `NOT_ESTABLISHED_CONFOUNDED` is reachable only for a candidate
with nuisance columns, and rows 1 and 2 only for `shot_location_value`. Rows 4 and 5 come
before row 6, so an established token can carry one league closed as redundant; the
established statements therefore say "in those leagues", and `analysis.md` names such a
league. The reason recorded beside each token is `verdict_reason_codes` (rows 1 to 3).

Required truth-table cases include: five leagues with three `SHIP` and two `INCONCLUSIVE`
(one degenerate, one non-finite) give row 3; four `SHIP` and one degenerate give row 4;
three `SHIP`, one guard `INCONCLUSIVE` and one count-gate failure give row 3; two `REJECT`
and three degenerate give row 3; `shot_location_value` with two `REDUNDANT` and three
`SHIP_WITH_BAND` gives row 6; the same statuses for `box_shot_share` give row 8.

### 9.2 Multiplicity and power

Each candidate is a separate claim; no familywise adjustment is made across the four
candidates or the five leagues. Within a candidate the rule is conjunctive: survival needs
a bound at or above the threshold in four of five leagues, which is stricter than any one
league. The instrument's gates are an intersection (4.4). The two interval levels differ
on purpose and are stated: a two-sided 95% percentile interval for the instrument, a
one-sided 95% Fisher-z bound for reliability.

Power of the four-of-five rule, from the normal approximation to Fisher's z with standard
error `1/sqrt(n - 2 - g)` and g = 3, assuming the same true within-position reliability in
every league and no redundancy (planning figures, `power_planning`): with 300 players in R a
candidate whose true reliability is 0.55 reaches `ESTABLISHED_BAND` or better with
probability 0.011, at 0.65 with 0.948; the reliability it reaches with probability 0.80 is
0.631 for the band and 0.779 for the number. With 66 players in R (the smallest share set)
those two reliabilities are 0.744 and 0.847, and at a true 0.75 the band is reached with
probability 0.846. A null on `box_shot_share` is therefore a weak statement about any
reliability below about 0.74.

## 10. Product consequence of each token — fixed now

**The verdict registry.** The registration commit adds five PUBLIC records to
`galactico/domain/verdicts.py`, token `PENDING`: the four candidates and the instrument,
built from the config's own entries (`registry_candidate_subjects`,
`registry_instrument_subjects`, `registry_common`, `registry_candidate`,
`registry_instrument`, `registry_outcomes`). After the run each record takes its token from
`results.json`. Every outcome statement a record prints is frozen in `registry_outcomes`,
holds no digit and no placeholder, and passes the copy guard; the not-run statement and the
non-claims hold no digit other than the experiment id's, as rule V7 words it, and the scope
names the season; numbers stay in `results.json` and `analysis.md`. No outcome statement
says what holds "in this release", which a later promotion would make false while the
registered statement could not change: the established statements say instead that the
experiment itself promotes nothing. No `ESTABLISHED` outcome moves a construct (rule V6).

| Candidate token | Status | Player Lab registry | `product_admissible` |
|---|---|---|---|
| `ESTABLISHED_NUMBER` | ESTABLISHED | no `registry_move` (rule V6); entered in `TESTED_NOT_PROMOTED` by the declared hand edit `tested_not_promoted_edit` (ARCH D1: tested, not promoted) | false: the registration commit gives it an explicit, empty promotion set (ROOT 2.10 W1) |
| `ESTABLISHED_BAND` | ESTABLISHED, with limits | the same | false, the same |
| `NOT_ESTABLISHED_REDUNDANT`, `_CONFOUNDED`, `_UNRELIABLE` | NOT_ESTABLISHED | `registry_move` `REJECTED` | false |
| `NOT_ESTABLISHED_MIXED` | NOT_ESTABLISHED | `registry_move` `RESEARCH_ONLY` | false |
| `INCONCLUSIVE`, `INCONCLUSIVE_INSTRUMENT` | INCONCLUSIVE | no `registry_move`; the candidate id is added to `UNTESTED` by the declared hand edit `untested_edit` | false |

The instrument's four tokens move no registry entry. Under `ACCEPTED` or
`ACCEPTED_WITHIN_LEAGUE` alone, the results commit adds a note beside the xG / xA row of
`docs/LIVE-DATA-GAP-MATRIX.md` that the free corpus supports a location-only conversion
model and no provider xG (`gap_matrix_edit`); under the other two tokens the matrix is not
edited.

**`product_admissible` stays false.** `verdicts.product_admissible(c)` is true today for any
construct with a PUBLIC, executed, ESTABLISHED E-09 record, which would open the gate the
moment a candidate is established; ARCH D1 says it stays false until a later, separate
promotion. ROOT 2.10 W1 rules the form: the registration commit gives `product_admissible` an
explicit, empty promotion set (`promotion_set_in_this_release`,
`product_admissible_in_this_release`), so a PUBLIC, executed, established E-09 record admits
nothing until a later promotion, which is its own change set with its own ADR; a test covers
every E-09 subject under every token. E-09 is not registered without that change. The instrument subject is never a
construct id and never enters the promotion set. An established E-09 record still derives
`may_gate` true; the same commit amends the `verdicts.py` docstring to say that for E-09 a
panel is unlocked through `product_admissible` only, and adds a test that no route or page
unlocks anything on an E-09 `may_gate` in this release.

**Player Lab registries.** `galactico/profiles/build.py` holds `REJECTED`, `RESEARCH_ONLY`
and `UNTESTED`, which Player Lab serves (`/api/constructs` and its hero counts), and the
results commit adds a fourth, `TESTED_NOT_PROMOTED`, written whatever the tokens (empty when
no candidate is established), so the shape of `/api/constructs` does not depend on the
outcome. After the run, whatever the tokens, `shot_profile` and `defensive_action_profile`
leave `UNTESTED`; `carrying_value` stays (ROOT 2.2 authorises the replacement). Each
candidate enters exactly one of the four lists (`registry_lists_after_run`) with the
headline and detail of `player_lab_text` where the list holds text: digit-free, with a
battery column named through `baseline_prose` by `baseline_fill_rule` and a nuisance set
through `nuisance_prose`. It is served under its config `display_name` (`display_name_edit`,
ROOT 2.5 H14), not a label derived from its id. Under every assignment of tokens the counts
are proposed 13, tested 13 minus the ids in `UNTESTED`, surviving 5
(`player_lab_counts_after_run`). After the run, whatever the tokens, the `shots`
not-measured entry becomes one of the three frozen `planning_after_run` sentences by
`shots_entry_rule` (a shot candidate tested; only the conversion model tested; nothing of
E-09's shot subjects tested), so the registration-time wording is never left standing once it
is false; once any E-09 record's badge reads TESTED, the planning pages' research sentence
becomes `planning_after_run.research_sentence`, and while none does it is not written
(`research_sentence_rule`). No sentence is written after the outcome is known. These edits change
served Player Lab and planning output, which R13 and ADR-0011 pin; ROOT 2.10 W8 makes them,
with the gap-matrix note, the results commit's consequences, overriding R13 and ADR-0011 for
exactly those edits, and the results commit carries an ADR that names them, as ADR-0025 and
ADR-0027 did (`PIPELINE.md` 11.1).

Fixed regardless of token:

- No candidate becomes a requirement dimension, an XI or Squad input, a value beside a
  player or a planning-page number in this release. A later promotion is a separate change
  with its own ADR (`PIPELINE.md` 11.2); it may rest on the PUBLIC E-09 token only. A
  second-provider label may sit beside it, never gating it (ADR-0018, ROOT 2.5 O1), only
  from a LOCAL record: E-11's record for the same definition, or a record a later protocol
  creates for the section 11 leg (ROOT 2.9 Z5); section 11 itself creates none.
- No hosted surface renders `shot_location_value` from this experiment. A full-season fit
  inside a dated decision has seen later shots; fitting out of league does not remove that
  (R9). An instrument token of `ACCEPTED` or `ACCEPTED_WITHIN_LEAGUE` together with a
  `shot_location_value` token of `ESTABLISHED_NUMBER` or `ESTABLISHED_BAND` licenses one
  follow-up build only, in its own protocol: an instrument fitted on the shots of **all five
  leagues** from matches strictly before the decision date, with a
  `followup_as_of_minimum_training_shots` minimum-training gate (one league alone does not
  reach it until late in the season), whose agreement with the full-season fit is judged by
  a criterion that protocol freezes. Until then it is UNAVAILABLE.
- Under `ACCEPTED_WITHIN_LEAGUE` the instrument's values carry no goal unit and are never
  compared across leagues.
- `box_shot_share` is a share: never summed over players, never a requirement dimension,
  never scaled by break-even retention.
- A list of players carrying a candidate value, in any later release, is ordered by name or
  id, never by the value.
- Positions that are context limits of a candidate (`context_limit_rule`) are written to
  `results.json` beside the claim: positions where reliability within the position alone was
  not shown. They do not narrow the claim, which is pooled within-position reliability, so a
  token never carries an empty scope; the record's scope says so. The `invalid_contexts`
  entry of a construct definition waits for a promotion.
- No token changes a shipped evidence gate, a construct definition or its hash, or any XI
  Lab or Match Lab output. The edits named above change the Player Lab registry lists (the
  new `TESTED_NOT_PROMOTED` and `DISPLAY_NAMES` included), the proposed and tested counts,
  the "Why only five?" view's card types, the docs generator's counts and table, the
  planning research sentence and `shots` entry, the gap-matrix note and their tests (`PIPELINE.md` 11.1), and nothing
  else.

## 11. External leg — StatsBomb 2015/16, LOCAL tier

Run only for a candidate in `sb_leg_candidates` whose token is `ESTABLISHED_*`, by its own
command, after this experiment's results are committed. Provider and season change together;
this leg cannot attribute a difference to either (E-11 exists for that). Its token is a
label: it moves no registry entry, opens no gate and parameterises nothing (ADR-0018).

| Candidate | Estimator on the second provider | Equivalence |
|---|---|---|
| `shot_volume` | Shot events whose shot type is in `sb_open_play_shot_types`, per regulation minute (`sb_minutes_rule`) | SEMANTICALLY_EQUIVALENT |
| `shot_location_value` | the selected specification of section 4, **refitted** leave-one-league-out on the four `sb_folders`, no reselection and no fallback to `M1`; head-or-body is a body part mapped to `head_or_body` by `sb_body_part_map`; gates `sb_gate_s_count`, S-fit including the refitted instrument in every fold, and the R and L gates in `sb_gate_leagues_required` of 4 | SEMANTICALLY_EQUIVALENT; coefficients are LOCAL |
| `box_shot_share` | the same shots, the zone `penalty_area_sb` on the unit square (102/120, 18/80 and 62/80 of the provider's drawing, as E-11 freezes it, bounds inclusive), through the leg-only spec `sb_box_spec` with its own fingerprint; `CANDIDATES` keeps its four keys | APPROXIMATED (the Wyscout box is a pitch drawing) |
| `opp_half_defensive_actions` | not in this leg | its cross-provider status is E-11's token for the same subject id, which applies because the definition is imported unchanged |

Frames on the second provider are frozen to the column: rows by `sb_event_row_rule`, the
neutral type by `sb_kind_type_map`, and success, goal, counter-attack, the interception flag
(E-11's family: an Interception event, or a pass of an interception type), body part and
shot family by `sb_frame_columns_rule`; the open-play shot and the interception flag are
computed by E-11's registered code itself, not written again (`sb_flags_rule`); a frame with no pass row is refused
(`sb_frame_refusal`). Positions by `sb_position_groups` and `sb_position_rule`, with each
spell's regulation minutes from the registered reader's own spell rule, never a second
implementation; goalkeepers are the GK group. Periods by `sb_period_labels`, minutes by
`sb_minutes_rule` with the leg's own goalkeeper, card and spell-end keys, the battery by
`sb_battery_rule`. The same gauntlet and the same `decide()`, four leagues, through the
leg's view of the config, written out key by key in `sb_leg_config_rule` (the four folders
replace the five leagues, with their own gates and position indices).

| # | Condition, first match wins | Token (`sb_verdict_vocabulary`) |
|---|---|---|
| 1 | `shot_location_value` and the refitted instrument is `INCONCLUSIVE` or `NOT_ESTABLISHED` | `INSTRUMENT_NOT_ACCEPTED` |
| 2 | fewer than `sb_minimum_evaluable_leagues` evaluable leagues | `INCONCLUSIVE` |
| 3 | at least `sb_survival_leagues` leagues at `SHIP` or `SHIP_WITH_BAND` | `REPLICATED` |
| 4 | at least `sb_rejection_leagues` leagues at `REJECT` | `NOT_REPLICATED` |
| 5 | otherwise | `MIXED` |

Each token's sentence is `sb_statements`; row 1 covers a refit that failed its criteria and
one that a sample or convergence gate left unjudged. The level shift between the two
providers' league means is reported in the LOCAL file only (`sb_level_shift_rule`, from each
league's mean over A wherever its count gates passed) and separates no tokens, so no
boundary for it is chosen here; it is not computed for `shot_location_value`, whose two
values come from two different models.

No StatsBomb-derived number, coefficient or identifier enters a committed machine-readable
file or a hosted surface. The leg writes under `sb_output_root` (gitignored); its aggregate
findings appear only in the research note `sb_report`, with the logo and attribution; the
commit that adds it puts it on `FORMED_FROM_STATSBOMB` in `tests/test_licensing.py`, and an
`analysis.md` that names the provider goes on the list that fits it. No registry record is
created for the leg (`PIPELINE.md` DISSENT 7, ROOT 2.9 Z5, ROOT 2.10 W6); a hosted label from it would
need a LOCAL record that a later protocol creates. The leg's code is built and pinned with
the pipeline, before any public outcome (`PIPELINE.md` section 10).

## 12. Predictions, written before the run

The predictions and their reasons are `predictions` in `config.json`; `results.json` echoes
them with `matched` true when the subject's token equals the predicted token
(`predictions_matched_rule`).

| Subject | Predicted | Reason |
|---|---|---|
| instrument | `ACCEPTED_WITHIN_LEAGUE` | Italy's level (planning figure of section 2) |
| `shot_volume` | `ESTABLISHED_NUMBER` | a published year-to-year correlation of about 0.66 for strikers; the raw correlation with mean pitch position is the likeliest closure if it fails |
| `shot_location_value` | `NOT_ESTABLISHED_REDUNDANT` | the identity value = volume x mean value: the sum is about 1.5 times noisier than the count (`planning_figures.sum_to_count_noise_ratio`) and the count dominates its variance |
| `box_shot_share` | `ESTABLISHED_BAND` | 66 to 88 players per league in the share set; no published figure exists |
| `opp_half_defensive_actions` | `ESTABLISHED_NUMBER` | team instruction is context here; team is expected to explain a large share of its variance in the reported joint audit, which does not gate |

These are predictions, not hypotheses with a test. A miss changes nothing.

## 13. What this experiment cannot show

- Persistence across seasons or clubs: one season, odd and even matches interleaved in time.
- That any candidate is a property of the player rather than of his deployment and team.
  Team is declared context and is reported, not removed.
- Construct validity or validity against an outcome. No candidate is related to goals,
  points or results here. Reliability is not validity is not decision utility.
- Anything about a single shot, a goalkeeper, a season, tier, sex or provider not evaluated.
- The size of what the instrument omits. The between-player spread of the gap to a model
  with defender positions cannot be estimated from this corpus.
- That the level of the instrument transports to national-team matches; they are not evaluated.
- Cross-provider agreement for any candidate (E-11) or transport across a club change (E-12).

## 14. Interpretation language — frozen

The sentences are `interpretation_language` in `config.json`; `analysis.md` uses them.

- Redundant, `shot_location_value` closed with `shot_volume` among the closest baselines of
  a league closed as redundant: "Weighting shots by a location-only conversion model did not
  separate players that counting shots does not, in the leagues where the frozen rule closed
  it, in this corpus." (Row 6 closes it on one such league, so the sentence is limited to
  those leagues, as the other redundant sentence is.) Redundant, every other
  closure (another candidate, or `shot_location_value` closed against another column, such
  as `mean_x`, which row 6 also reads): "The statistic was a near-copy of the named declared
  baseline statistic in the leagues where the frozen rule closed it, in this corpus."
  **Not**: "shot location does not matter", "xG is useless".
- Instrument not accepted, for the token `NOT_ESTABLISHED` only: "This location-only model
  did not meet its frozen out-of-league criteria." **Not**: "conversion cannot be modelled".
  An `INCONCLUSIVE` instrument was not judged, and `analysis.md` uses its registry statement
  instead (`instrument_not_accepted_rule`); the league reason code
  `league_not_computed_reasons.instrument_not_accepted` covers both tokens and is a code, not
  a sentence.
- Established: "Repeatable within a season among players of the same broad position, and,
  in the leagues where it passed, not a copy of the declared baselines." **Not**: "measures
  shooting", "measures pressing", "identifies better players".

## 15. Reproducibility and tests

Artifact: protocol, config, pipeline and code hashes on LF-normalised bytes (the code hashes
a sorted list of path and hash pairs, so no key names a provider); protocol commit (the
commit that first added the three protocol files) verified against git, not typed; the
self-check stamp's hash; content
hashes of every input frame and the sidecar's provenance; package versions; candidate
fingerprints; the selected specification; seeds; every gate with its count; aggregate results
only. `results.json` carries the registry contract at its top level (`experiment` =
`registry_experiment_id`, `version`, `tier`, `verdicts` {subject: {token, reason}}). No player
or team identifier (`results_identifier_key_denylist`), no per-player row, nothing over
`results_maximum_bytes`. The runner writes the file itself as UTF-8, after checking the
whole object in memory, the config echo included and exempted from nothing. An execution
that fails after the refusal checks is recorded and disclosed before any next start
(`PIPELINE.md` section 7, failed executions); a failed execution counts against neither
R5's one real run nor its one determinism re-run, and the disclosure says which phase it
reached.

Pipelines are developed and tested on synthetic data only. Before any real outcome is read
the runner executes the planted checks of `PIPELINE.md` section 8, and a failed check stops
the run; the same checks are first run and committed as a stamp (`selfcheck_stamp`) whose
hashes tie them to the reviewed code and config, and the real run refuses a stamp that does
not match. The predicate is `selfcheck_predicate` over `selfcheck_replicates` seeded replicates:
for each planted world (`synthetic_worlds`) and instrument scenario
(`synthetic_instrument_scenarios`), and each subject it names, at least
`minimum_replicates_matching` replicates give a token in `expected`, and none gives a token
in `never`. The worlds plant a within-position effect in every candidate (`EFFECT`), no
within-position effect (`NULL`, with the assertion that the raw pooled reliability of
`shot_volume` is high while its centred bound is below the band), a nuisance attribution
effect (`NUISANCE`), and a defensive candidate that is a fixed share of all defensive
activity within every position (`REDUNDANT_WITHIN_POSITION`). The reviser's event-level
simulation of this exact generator and rule, before registration, met every predicate with
the margins recorded in `selfcheck_feasibility` (synthetic numbers only, no real row read).
The audit revision lowered the minimums (9 of 12, and 8 of 12 for `PLANTED`'s `ACCEPTED`)
so that all seventeen minimum conditions hold together with probability 0.994 at
conservative miss rates (`joint_minimum_pass_probability`); a failed self-check after
registration supersedes the protocol, and a correct pipeline should not fail it by chance.

Tests required (named in `PIPELINE.md`): hand-computable definition contracts for all four
candidates and their sentences; fingerprints equal `config.json`; the definition constants
of `candidates.py` equal `config.json`, and the module opens no file; zone edges exact at the
lattice; sentinel and unattributed rows never credited; goalkeepers excluded; `shot_volume`
equals `compute_baselines(...)["shots_per_90"]` exactly on the same frame and minutes; the rows of
`shot_volume` and `opp_half_defensive_actions` equal E-11's flags, computed by the imported
`galactico.validation.provider_inputs` (pinned in the source hashes), on every row type,
subtype and flag combination of the public adapter's closed vocabulary (ROOT 2.10 W3);
`decide()` and the correlation helper
pinned by their source hashes, `decide()` also by its constants and a truth table written
from this document at every threshold edge; every reject reason and every token row reachable, including the
cases of 9.1 and `r_half = -0.4` giving `REJECT` with reason `UNRELIABLE`; each departure of
6.1 shown in its stated direction and each lenient one flagged; input-order invariance,
including a tied twelfth place giving a `null` survivor count; match-set assignment equal to
the house split; instrument coefficient recovery, analytic gradient zero at the fit,
leave-one-league-out leakage (changing a held-out league's labels changes none of its own
predictions); every acceptance gate reachable in both directions, S-count and S-fit apart;
calibration bins invariant to row order and event ids; null reporting (`None`, never 0 or
NaN); every registry record built under every token passes `VerdictRecord` and
`runtime.finalize`; the Player Lab counts under all 4,096 assignments of candidate tokens;
no key of the config, of the stamp or of `results.json` in the denylist, refused by
`banned_key_paths` with `BANNED_KEY_PARTS`, or naming a provider; determinism of the full
run under a fixed seed.

---

*Committed before running. Results in `results.json`, interpretation in `analysis.md`,
model card in `MODEL-CARD.md`. If any of them contradicts this document, this document
wins.*

![StatsBomb](../../../../assets/statsbomb/statsbomb-logo.png)

Data source: StatsBomb open data, for the external leg of section 11 only, read locally under
the StatsBomb Public Data User Agreement. This document prints no figure formed from
StatsBomb data; the leg's report will, with this logo and the attribution clause 1.4 of that
agreement requires. No StatsBomb data is in this repository, and no machine-readable table
derived from it is in the tree.
