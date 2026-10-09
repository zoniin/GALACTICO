# E-10 — is where a team concedes a property of the defending team?

> **DRAFT. Not frozen, not registered, not run.** Written by one designer during the north-star build and never adversarially reviewed or audited. No outcome named here has been computed. It becomes a protocol only when a reviewed version is committed under `experiments/preregistered/` in a single commit that precedes any run. Section and file references such as ROOT 2.5 point to [ROOT-DECISIONS.md](../../ROOT-DECISIONS.md); see [README](../../README.md) for the working notes it cites.

**Commit this plan, `config.json` and `PIPELINE.md` before any E-10 outcome is computed.
Nothing below may change once the first outcome is observed.** This is a prospective
analysis plan on **reused public data**, not a claim of untouched data collection. Every
threshold, seed, window, list, grid and gate lives in `config.json`; a number that appears
only in this prose is a defect. Deviations are recorded in `analysis.md`, never silently
adopted. The pipeline is developed and tested on synthetic data only; the root integrator
executes the real run once, plus one determinism re-run.

## Claim and unchanged boundaries

> After accounting for the attacking team's own tendencies, the total conceded and venue,
> the defending team's prior history adds out-of-sample information about the channel
> composition of the final-third entry passes it concedes.

"Shape" below means the composition of a declared count vector. "Level" means how many.
They are separate claims with separate models. Published reliability evidence exists only
for level; no published study was found that tests shape against an attacker-only baseline.

**Not claimed, under any verdict.** That a channel a team concedes through is defended
badly: a team can leave a channel open on purpose, and event data cannot separate that from
failing to close it. That attacking that channel pays. That the composition persists into
another season, another squad or another coach. That a specific pair of teams interacts.
Anything about a player. Anything about shot conversion: the corpus has no expected-goals
value and no shot end location.

**Unchanged.** No key enters `features/spec.py::SPECS` or `CONSTRUCTS`. No Player Lab,
Match Lab or XI Lab output, endpoint, hash or evidence gate changes. E-07 and E-08 stay
closed at their published results. Passing earns a labelled descriptor in Opponent Lab,
never a requirement, an optimiser weight or an ordering of teams (R1, R4).

## Prior exposure of the data

| What was already seen | Where | Consequence here |
|---|---|---|
| All five Wyscout leagues, player-level constructs | Stage 1, 1B, 1C; E-02 (Italy primary) | No league is untouched. None of those analyses computed a team-conceded quantity |
| Spain 1 Nov to 28 Feb as development rows; Spain and England 1 Mar to season end as evaluation rows; target = first-30-minute positive completed-pass xT with an `opponent_mean` conceded term in the baseline | E-07, E-08 | 312 of the 917 evaluation matches here (624 of 1,834 team-match rows, 34.0%) carry that exposure: Spain 211 matches (88 as E-08 development, 123 as evaluation), England 101. The 69 Spain November to December matches in this development window were E-07/E-08 development rows. The exposure was to a conceded level of xT, never to a channel composition |
| StatsBomb 2015/16, player-level constructs | E-01, Stage 1C | The replication corpus is not untouched. No team-conceded quantity was computed on it |
| Structure only: entry-pass counts per team-match (median 37 to 39.5 by league), state-filter survival (79.0% in Spain with dismissals; about 84% in five leagues from goals alone), share of entries on a lateral-third edge (about 3%), calendars, coach-id counts, mean pass `y` by listed position in 40 StatsBomb files | reconnaissance, critic, this design | Exposure and structure only. No channel split by team, no reliability, no persistence, no loss was computed. Sample gates were set with these counts known; they are not expected to bind and exist to catch a broken data path |

Italy, Germany and France (535 evaluation matches, 1,070 rows) carry no E-07/E-08 exposure.
They are reported as a separate pooled estimate and enter the decision rule as criterion (f).
A designer-side prototype was run on **synthetic** seasons only, to confirm the rule is
satisfiable before freezing; it never read `data/`.

## Data, cohorts and exclusions

Corpus: public Pappalardo/Wyscout 2017/18, `config.leagues`, 1,826 matches, 3,652
team-match rows, 98 teams. Tournaments are excluded: no round-robin. Inputs are the neutral
Parquet frames plus the event sidecar (cards, own goals) and the match sidecar (full-time
goals). No lineup minutes are read: they are nominal.

**Row.** One row per team per match: the *unit* is the team whose descriptor is read, the
*context* is its opponent. For conceded descriptors the unit defends and the context
attacks. A match yields two rows.

**Prior.** A row dated `t` may use only rows whose calendar date (UTC, normalised to the
day) is strictly before `t`. `gameweek` is never read.

**Development** = rows dated before `config.evaluation_start`. **Evaluation** = rows on or
after it and before `config.end`. Evaluation forecasts use an expanding window: every prior
row, development included.

**Match validity.** A match is invalid, for both rows and all models alike, when: a period
in `windows[...].periods` is absent; an event clock is non-finite or negative; sidecar rows
are missing for the match; or the full-time goals reconstructed from events (goal-flagged
`shot` and `set_piece` rows credited to the acting team, own-goal rows credited to the
other team) differ from the match sidecar. Invalid matches are counted by reason and never
repaired. One England match is known to lack a scoring event and will be excluded.

**Eligibility.** A row is eligible when its unit and its context each have at least
`minimum_prior_matches` prior valid matches. Ineligible rows still feed later histories.
No exclusion on team, strength, coach or venue. Promoted clubs and coach changes are not
adjusted for: a team is one unit for the season (coach ids exist upstream, 49 of 98 teams
show more than one; the sidecar does not carry them).

## Measurements — frozen

**Frames.** Every neutral coordinate is in the acting team's attacking frame: `x = 0` its
own goal line, `y = 0` its left touchline (verified on both providers). The defending
team's left is the acting team's right. That mirror is written once, in the descriptor
definition: part `def_left` reads the opponent's `att_right` column.

**Placeholders.** A start or end at exactly `(0,0)` or `(1,1)` is a provider placeholder
that encodes home/away, not a location. An event set that reads a location drops such rows
and any row with a coordinate outside `[0,1]` or non-finite; the count dropped is reported
per event set.

**Measurement window** (`close_11v11`, primary). An event counts when, among incidents with
a strictly earlier `(period, seconds)`, there is no dismissal (red card or second yellow,
either team) and the absolute goal difference is at most one. Regulation periods only.
`window_seconds` is the measure of that state on each period's `[0, last event second]`.
This conditions on events after kick-off: results describe behaviour in comparable states
and are not forecasts for arbitrary states. `all_states` is a reported sensitivity only.

**Event sets** (acting team's frame; bounds are exact fractions; a row is counted once).

| Key | Rows | Location rule |
|---|---|---|
| `f3_entry_pass` | `type == "pass"` and `success == True` | start `x < 2/3`, end `x >= 2/3`; real start and end |
| `box_entry_pass` | same | end inside the rectangle `x >= 21/25`, `19/100 <= y <= 81/100`; start not inside it; real start and end |
| `open_play_shot` | `type == "shot"` | real start |
| `defensive_action` | ground defending duel record, or any row with the interception flag, or `type == "foul"` with subtype `Foul` | real start |
| `defensive_action_high` | same | start `x >= 2/5` |
| `own_60_pass` | `type == "pass"`, any outcome | start `x <= 3/5` |

Lateral thirds: `y < 1/3` acting team's left, `y > 2/3` its right, otherwise centre (on the
Wyscout lattice: 0 to 33, 34 to 66, 67 to 100; the rule is its own mirror image).

**Descriptors.** Each is a composition of counts read from the unit's row. Executable
definitions, sentences and fingerprints are in `galactico/features/team/descriptors.py`;
the fingerprints are frozen in `config.descriptor_fingerprints` and the runner refuses a
mismatch.

| Role | Key | Parts (unit's row) |
|---|---|---|
| Primary | `conceded_f3_entries_by_channel` | opponent `f3_entry_pass` by lateral third of the **end**, in the defending frame: `def_left`, `def_centre`, `def_right` |
| S1 | `conceded_f3_entries_wide_share` | `wide` = `def_left + def_right`; `centre` |
| S2 | `conceded_box_entries_by_origin_channel` | opponent `box_entry_pass` by lateral third of the **start**, defending frame |
| S3 | `conceded_shots_inside_box_share` | opponent `open_play_shot` starting inside the rectangle; outside it |
| S4 | `defensive_actions_by_pitch_third` | own `defensive_action` with start `x < 1/3`; middle; `x >= 2/3` |
| S5 | `high_zone_defensive_action_share` | own `defensive_action_high`; opponent `own_60_pass` |

S5 is `1 / (1 + passes per action)`: a monotone transform of opponent passes per recorded
high-zone defensive action. It is never labelled PPDA: the Wyscout action set differs from
every published one. S4 is where recorded actions happened, which follows the ball; it is
not a line height. **Level subject** `conceded_f3_entries_per_90`: the primary's total per
`exposure = window_seconds / 5400`.

Log-ratio coordinates of a composition `p` with parts in the order above: for three parts
`z1 = sqrt(1/2) ln(p1/p3)`, `z2 = sqrt(2/3) ln(sqrt(p1 p3)/p2)`; for two parts
`z1 = sqrt(1/2) ln(p1/p2)`. For the primary, `z1` is side balance and `z2` is wide versus
centre. Counts are never converted to per-match shares before modelling.

**Not run here** (`config.not_run_in_this_experiment`): no xT-weighted version, nothing
that needs a possession segmentation, no set-piece or transition quantity, no finer grid.

## Models and baselines — frozen

All quantities at date `t` in league `L` use prior valid rows only. `n` is a row's part
vector, `N` its total, `K` the number of parts, `c` a context team, `u` a unit team, `v`
whether the context team is at home.

- League composition `pi = (S + 1) / (S_total + K)` over all prior league rows; by venue
  `pi_v` likewise; venue offset `nu_v = ln pi_v - ln pi`.
- Context composition `A_c = (F_c + kA pi) / (F_c_total + kA)`, `F_c` the pooled counts of
  rows in which `c` was the context. `A_c^(-u)` is the same with rows against `u` removed.
- Expected composition of a history row `j` of unit `u`:
  `e_j proportional to A_{c_j}^(-u) exp(nu_{v_j})`.
- Unit deviation: `O = sum_j n_j`, `E = sum_j N_j e_j`, `ebar = E / O_total`,
  `delta_u = ln((O + kD ebar) / (O_total + kD)) - ln(ebar)`; `delta_u = 0` when the unit
  has no prior events. Excluding `u`'s own matches from `A` prevents a team's history from
  explaining itself.
- **Candidate**: `p proportional to A_c exp(nu_v + delta_u)`.

`kA`, `kD` are prior strengths in pseudo-events. Closed form, NumPy only, no iterative fit.

**Baseline ladder.** A count vector with independent Poisson parts factorises exactly into
a level loss on `N` and a shape loss given `N`. Every rung is a (level, shape) pair; both
components are reported for every rung, pooled and by league.

| Rung | Level of `N` | Shape given `N` | Represents |
|---|---|---|---|
| B0 | league-by-venue rate | `pi_v` | no team information |
| B1 | context-only rate | `A_c exp(nu_v)` | "it is whatever the attacker does" |
| B2 | context and unit rates | `pi_v` | the defender matters for how much, not where |
| B3 | context rate times the pooled ratio of the unit's strength peers | `A_c exp(nu_v + delta_peers)` | "it is just being a stronger or weaker team" |
| **B4** | B2 level | `A_c exp(nu_v)` | **attacker shape times defender level: the decisive null** |
| B5 | unit's unshrunken last-five rate | unit's unshrunken last-five composition, `+0.5` per part | raw persistence: is shrinkage doing the work |
| B6 | B2 level | candidate with the mirror pairs of `delta_u` swapped | mirror placebo |
| B7 | B2 level | candidate with `delta` of a permuted donor, 20 seeds | identity-link stress test |
| Candidate | B2 level | `A_c exp(nu_v + delta_u)` | |

Peers: the other teams in the unit's league and strength tercile at `t` (prior points per
match, ties by prior goal difference per match, then team id; terciles by descending
order, `floor(3 i / T)`). `delta_peers` uses the peers' pooled `O` and `E`.

**Level model.** `y = N`, `e` = exposure. League-by-venue rate `lam_v = sum y / sum e`.
Context ratio `rA_c = (Y_c + kA') / (X_c + kA')` with `X_c = sum_j e_j lam_{v_j}`; unit
ratio `rD_u = (O_u + kD') / (E_u + kD')` with `E_u = sum_j e_j lam_{v_j} rA_{c_j}^(-u)`.
B1 mean `e lam_v rA_c`; B2 mean `e lam_v rA_c rD_u`. Loss: Poisson deviance.

**Losses.** Shape: multinomial log loss, `-sum_k n_k ln p_k`, summed over rows and divided
by the number of events (ratio of sums, never a mean of per-match ratios). Level: mean
Poisson deviance per row with positive exposure. Both are strictly proper.

## Frozen selection procedure

Per descriptor, on eligible development rows of all five leagues pooled, by walk-forward
prediction inside the development window:

1. `kA` = the grid value with the smallest pooled shape loss of B4.
2. With `kA` fixed, `kD` = the candidate with the smallest pooled shape loss among the
   grid and the boundary `context_only` (`delta = 0`, the candidate **is** B4).

Ties within `selection_tie_tolerance`: `context_only` first, then the larger value (more
shrinkage). Grid order cannot decide a tie. The level constants `kA'`, `kD'` are selected
the same way with the deviance. `kA` is frozen for evaluation and for every placebo's own
re-selection of `kD`; `kA` and `kD` are both frozen for the replication. No other tuning exists: no
feature search, no window search, no per-league constants. Selecting among ten candidates
on about a thousand rows can overfit; the evaluation window exists for that reason.

If `context_only` is selected the candidate's loss array is B4's, the difference is exactly
zero, and criteria (a), (b), (c), (d) and (f) are false by definition.

## Evaluation and reporting

**Estimands** (per descriptor; all on eligible evaluation rows unless stated).

| Id | Estimand | Definition |
|---|---|---|
| P1 | utility (primary) | shape loss of the candidate minus B4, per event. Negative: defender history helps |
| L1 | level utility | deviance of B2 minus B1, per row (level subject only) |
| M1 | side information | shape loss of the candidate minus B6, per event (descriptors with mirror pairs) |
| P2 | calibration | per coordinate, the event-weighted slope through the origin of the observed log-ratio residual (row composition with `+0.5` per part, minus B4) on the coordinate of `delta_u` computed without any match against the row's context team. 0 = no defender shape, 1 = correctly scaled |
| R1 | reliability (gate) | alternating split-half of the team-season descriptor, per coordinate, stepped up by Spearman-Brown |
| T1 | persistence (reported) | correlation of the development-window value with the evaluation-window value, no step-up: persistence under real squad and coach change |
| V1 | validity against strength | variance of the team-season coordinate explained by `strength_covariates` |
| I1 | pair interaction | correlation between the two meetings of a directed pair of the residual coordinates after an additive context, unit and venue fit within league |

**Resampling.** Paired differences are resampled by calendar week (`W-SUN`) within league:
clusters are (league, week), strata are leagues, `bootstrap_replicates` draws, statistic =
ratio of resampled sums. Both rows of a match share a date and therefore a cluster. The
interval is the percentile interval at `interval_quantiles`. The one-sided p-value is
`(1 + number of replicates >= 0) / (replicates + 1)`. Intervals condition on the selected
constants and the post-kick-off window; they omit selection uncertainty and dependence
across weeks within a team. The identity-link test, not the interval, is the guard against
that dependence, and the synthetic gate measures the false-positive rate of the whole rule.

**Mirror placebo (B6).** Swapping the left and right components of `delta_u` keeps
wide-versus-centre information and reverses side information. M1 asks whether side
information exists; a strict inequality between two point estimates would pass half the
time under no side information, so M1 is tested with its own interval.

**Identity-link stress test (B7).** For each of `permutation_seeds`, at each date, teams are
permuted within league and strength tercile (sorted ids; generator seeded from SHA-256 of
`seed | placebo seed | league | date | tercile`), each unit receives its donor's `delta`,
and `kD` is re-selected on development rows. This breaks the link between a team and its
own history while keeping league and coarse measured strength. It cannot hold latent
strength fixed: terciles estimated from prior points misclassify, and a designer-side
synthetic check showed a shape planted as a function of latent strength passing this test
in every season. V1 is the check for "the shape is strength", and only up to its ceiling.
B7 is a stress diagnostic, not an exchangeable permutation test and not a p-value. The
share of rows whose donor differs is reported per seed.

**Reliability (R1).** Units: teams with at least `minimum_half_matches_per_team` valid rows
in each half. Each team's valid rows over the whole season are ordered by date and
alternated. A half's value is the log-ratio coordinate of its pooled counts (`+0.5` per
part); the league mean is removed within each half. With `r` the correlation over `n`
teams in `G` leagues: `R = 2r/(1+r)`; lower bound
`R_lo = SB(tanh(atanh(r) - c / sqrt(n - 3 - (G - 1))))`, `c = reliability_critical_value`
(two-sided 95%, so a one-sided 97.5% bound). The house interval applies Fisher's transform
to the stepped-up value, which is anti-conservative at team-level `n`; it is reported
beside this one and gates nothing. At `n = 98` this gate needs an observed `R` of at least
0.669 for a band and 0.801 for a number (house method: 0.616 and 0.776). A descriptor
passes when **every** coordinate has `R_lo >= reliability_band`. No per-league reliability
is gated: at 20 teams the sample size decides the outcome.

**Validity against strength (V1).** Per coordinate, league-centred, ordinary least squares
of the team-season value on the league-centred `strength_covariates` (`k = 4`,
`n = 98`, `G = 5`). Reported: unadjusted `R2`, its noise floor `k/(n - G)` = 0.043,
`R2_adj = 1 - (1 - R2)(n - G)/(n - G - k)`, a permutation reference (covariate rows
permuted within league), the Spearman correlation between raw and residualised values, and
the overlap of the twelve largest values before and after (chance expectation 1.5 of 12;
reported, gating nothing; never computed per league, where chance exceeds the house floor).
Passes when every coordinate has `R2_adj <= strength_adjusted_r2_ceiling` and Spearman
correlation `>= strength_rank_correlation_floor`. A missing value is a failure.

**Secondary family.** S1 to S5 run through the same machinery. Their one-sided p-values for
P1 enter Holm's step-down procedure at `holm_family_alpha_one_sided`: ordered ascending,
the `i`-th is rejected while `p_(i) <= alpha / (5 - i + 1)`; the first failure stops it.

**Reported without a verdict.** Per-league P1 with intervals. The Italy, Germany and
France pooled P1 with its interval. `all_states` P1 and R1 for the primary. Loss of every
rung. The implied per-match intraclass correlation `R / (m - (m - 1) R)` at the mean
number of matches `m`. Coverage, exclusion and placeholder counts. Empty metrics are
`null`, never zero.

## Decision rule — frozen

**Sample gates.** G1 to G5 are evaluated on counts only, before any loss is computed; G6
after development selection and before any evaluation loss is aggregated. If any fails for
a descriptor, its verdict is `INCONCLUSIVE`, the reason is recorded, and nothing is compared.

| Gate | Requirement, every league |
|---|---|
| G1 | valid matches at least `minimum_valid_match_share_per_league` of matches |
| G2 | eligible development rows and weeks at least the configured minima |
| G3 | eligible evaluation rows, weeks and events at least the configured minima |
| G4 | at least `minimum_reliability_teams` teams qualify for R1 (pooled) |
| G5 | every placebo seed changes the donor on at least `minimum_permutation_changed_share` of eligible evaluation rows (pooled) |
| G6 | every development selection loss is finite |

**Criteria.** "Below zero" means below `-zero_tolerance`.

| | Criterion |
|---|---|
| (a) | Upper bound of the pooled interval of P1 is below zero. Secondary descriptors: Holm rejects instead |
| (b) | P1 is below zero in at least `minimum_leagues_with_negative_estimate` of five leagues |
| (c) | Pooled P1 is strictly smaller than P1 of every one of the 20 permuted placebos. Ties fail |
| (d) | Upper bound of the pooled interval of M1 is below zero. Applies only where mirror pairs exist; otherwise true |
| (e) | R1 passes |
| (f) | Pooled P1 over Italy, Germany and France is below zero |
| (g) | V1 passes |
| (La) | A finite `kD'` was selected and the upper bound of the pooled interval of L1 is below zero |
| (Lb) | L1 is below zero in at least four of five leagues |
| (Le) | R1 of `ln((sum y + 0.5) / sum e)` passes |

**Verdict.** Exactly one, in this order:

| Order | Condition | Verdict |
|---|---|---|
| 1 | a sample gate failed | `INCONCLUSIVE` |
| 2 | (a) to (g) all hold | `DEFENDER_SHAPE_SIGNAL` |
| 3 | primary descriptor only: (La), (Lb), (Le) all hold | `LEVEL_ONLY` |
| 4 | otherwise | `NOT_ESTABLISHED` |

`INCONCLUSIVE` = a frozen sample gate failed and nothing was compared. `NOT_ESTABLISHED` =
compared, criterion not met: a published null, not evidence of absence. `LEVEL_ONLY` = the
team concedes more or fewer entries than the attacker alone predicts; where they arrive is
not shown to be its own property. The level component status (`LEVEL_ESTABLISHED` when
(La), (Lb), (Le) hold, else `NOT_ESTABLISHED`, or `INCONCLUSIVE`) is recorded under every
primary verdict. The experiment's headline verdict is the primary descriptor's.

**Replication qualifier.** For each descriptor with `DEFENDER_SHAPE_SIGNAL`, the frozen
specification (same definitions in unit coordinates, same selected constants, no selection)
is run on StatsBomb 2015/16, four leagues, every eligible row of the season.
`REPLICATED`: pooled P1 upper bound below zero. `NOT_REPLICATED`: evaluated, not met.
`REPLICATION_INCONCLUSIVE`: fewer than the configured rows, weeks or valid-match share in
any league. `NOT_COMPARABLE`: S4 and S5, declared now (the providers' defensive-event
ontologies differ). `NOT_RUN`: every other case. The provider mapping is frozen in
`config.replication` and in `PIPELINE.md` before any replication outcome is read. Ligue 1
has 377 matches. Replication numbers stay in the local tier and in `analysis.md`.

**Matchup features.** Permitted only if the lower `interaction_lower_quantile` bound of I1
exceeds `interaction_floor` on at least one coordinate of the primary descriptor. Each
directed pair meets twice, about half a season apart; smaller interaction cannot be
claimed from one season.

**No rescue.** No change of grid, window, event set, state filter, lateral rule, gate or
criterion after an outcome is read. A second operationalisation needs a new preregistration.

**What a null will mean.** DERIVED, not measured: with about 60,000 evaluation events the
paired statistic is `z = 1.5 tau sqrt(R_h n / D)`, `tau` the between-team SD of a channel
share, `R_h` the reliability of the history at hand, `D` the design effect. At `R_h = 0.5`
and `D` of 4 to 9, 80% power needs `tau` of two to three percentage points, a per-match
intraclass correlation near 0.05. Criterion (e) is stricter: a descriptor whose true
38-match reliability is 0.67 passes it about half the time. A null therefore means "smaller
than about that", which is also too small to show as a number from 38 matches. The synthetic
gate publishes the measured detection rate at four planted effect sizes before the real run.

## Product consequence of each verdict — fixed now

One panel per subject in Opponent Lab: the six descriptors and the level subject. The
prior-date record (counts over the team's prior matches in the same window, matches and
events used) is shown in every state.

| Subject | State | Shown beyond the record | Badge (verbatim) | Evidence class |
|---|---|---|---|---|
| any | not yet run, or `INCONCLUSIVE` | nothing | `RECORD · NOT TESTED` | counts OBSERVED, shares and rates DERIVED |
| descriptor | `NOT_ESTABLISHED`; primary under `LEVEL_ONLY` | nothing | `RECORD · NOT SHOWN TO PERSIST` | same |
| descriptor | `DEFENDER_SHAPE_SIGNAL` | behind an explicit opt-in: the shrunken composition `pi exp(delta_u)` normalised, its interval and shrink weight. R1 lower bound at least `reliability_number`: point and interval; otherwise interval only | `TESTED TENDENCY · ONE SEASON, ONE PROVIDER` | EXPERIMENTAL |
| descriptor | the same with `REPLICATED`, and only if an ADR permits a StatsBomb-derived label on a hosted surface | the same, without opt-in | `TESTED TENDENCY · REPLICATED` | PREDICTIVE |
| level | `LEVEL_ESTABLISHED` (always so under `LEVEL_ONLY`) | shrunken entries per 90 window minutes, interval, shrink weight | `VOLUME TESTED · ONE SEASON` | ESTIMATED |
| level | `NOT_ESTABLISHED` | nothing | `RECORD · NOT SHOWN TO PERSIST` | DERIVED |

Until that ADR exists the hosted panel depends on the Pappalardo verdict only and the
replication qualifier appears only in `analysis.md` with the required attribution. The
volume estimate is classed ESTIMATED, not EXPERIMENTAL: persistence of conceded volume is
the part the literature already supports, and the panel states a rate for this team in
this window, not a forecast.

Fixed in every state:

- Parts are listed in the declared order. No part is highlighted, sorted by size, or
  called the largest. No league-relative adjective. No single number summarises an
  opponent. Teams are never ordered by a descriptor.
- The words weak, weakness, vulnerable, vulnerability and exploit do not appear on the
  page.
- Under every conceded panel (primary, S1, S2, S3, level): *"This is where the opponent's
  actions were recorded. A team can leave a channel open on purpose. Event data cannot
  tell that apart from failing to close it, so this panel does not say the team defends
  that channel badly."*
- Under S4 and S5: *"This is where the team's defensive actions were recorded. Actions
  happen where the ball is, so this follows the opponent's play as well as the team's
  choices. It is not a line height and does not say how well the team defends."*
- `NOT_ESTABLISHED`: *"E-10 compared this team-specific split with what the opposing
  team's own history predicts and did not find that it adds out-of-sample information.
  Read it as a record of past matches, not as a tendency."*
- `INCONCLUSIVE`: *"E-10 could not test this descriptor: a frozen sample gate failed.
  Nothing was compared."*
- `LEVEL_ESTABLISHED`, volume panel: *"E-10 found that how many entries this team concedes
  carries information beyond the attacking team's own volume."* Under `LEVEL_ONLY` it
  continues: *"Where they arrive was not shown to be the team's own property."*
- `DEFENDER_SHAPE_SIGNAL`: *"E-10 found that this team-specific split adds out-of-sample
  information beyond what the opposing team's own history predicts, in one season from one
  provider. The
  estimate is shrunken toward the league composition and describes matches at eleven
  against eleven within one goal."*
- V1 failed (possible only without `DEFENDER_SHAPE_SIGNAL`), appended: *"Most of the
  between-team variation in this descriptor is explained by points, goals and pass share."*
- The optional requirement proposal stays HEURISTIC under every verdict and needs the
  user's acceptance. When it cites a descriptor without `DEFENDER_SHAPE_SIGNAL` its text
  must contain *"based on a record not shown to persist"*.
- S5 may be displayed as opponent passes per recorded high-zone defensive action; the
  tested quantity and the badge are those of the share.

`galactico/domain/verdicts.py` receives one row per descriptor and one for the level
subject: status = the verdict token; product state `PASSED_WITH_LIMITS` for
`DEFENDER_SHAPE_SIGNAL` and `LEVEL_ESTABLISHED`, `FAILED` for `NOT_ESTABLISHED` and for the
channel row under `LEVEL_ONLY`, `INCONCLUSIVE` for `INCONCLUSIVE`; hostable true. Product
code reads nothing else from this experiment.

## Interpretation language — frozen

A null is stated as: *"this procedure did not find that the defending team's history adds
information about where it concedes beyond the attacking team's own habits"*. It is not
stated as "teams have no defensive shape" or "opposition analysis does not work". A signal
is stated as predictive information about a composition, never as a flaw of the defending
team and never as advice to attack a channel.

## What this experiment cannot show

- Why a team concedes where it does. Funnelling and failure are observationally the same.
- That a signal is separate from latent team strength. Strength enters through league
  tercile peers (B3, B7) and four measured covariates (V1); a shape that tracks strength
  in a way those miss would pass.
- Persistence across seasons: the corpus holds one season per provider, and the two
  providers are two years apart with different ontologies.
- Anything for states outside the window, or for matches not yet kicked off: the window and
  the conditioning on `N` use post-kick-off information.
- Danger. An entry pass is territory, not a chance; no conversion model is used.
- That event locations are precise: the provider reports no positional accuracy and no
  inter-operator agreement, which is why three channels are used and nothing finer.
- Stability under a coach or squad change: not adjusted, counted as part of the team.
- Calibrated uncertainty: intervals omit selection uncertainty and week-to-week dependence
  within a team.
- Independence from earlier work: a third of the evaluation rows were previously scored
  for a different conceded target.

## Reproducibility and tests

Artifact (`results.json`, aggregate only, under 512 KB, no player identifier or name):
protocol, config, pipeline-document and source hashes on LF-normalised bytes; content
hashes of every input frame and of each team-match table; sidecar and table versions;
descriptor fingerprints; package versions; seeds; the protocol commit read from git; the
synthetic-gate report hash; coverage and gate counts; every rung, estimand, criterion and
verdict. Replication numbers are written only under `data/licensed/`. The runner refuses a
dirty working tree, a fingerprint mismatch, or a missing or failing synthetic gate.

**Synthetic gate, before any real outcome.** Seeded synthetic seasons with the real double
round-robin shape plant a known defender effect and a known zero. The frozen rule must
return `DEFENDER_SHAPE_SIGNAL` in at least 90% of seasons with a strong planted effect, at
most 5% with no defender shape (alone, with a level effect, with a wide-only effect, or
with a shape that is a function of strength tercile), `LEVEL_ONLY` in at least 90% with a
planted level effect and no shape, and `NOT_ESTABLISHED` in at least 90% with nothing
planted. Detection rates at three smaller effects are published, gating nothing.

Tests (synthetic or hand-computed only): defender-frame mirror with the wrong-sign negative
control; placeholder and out-of-range coordinates; lateral and box edges on the lattice;
state window with goals, own goals, dismissals and same-second ties; window seconds; count
once under the action union; row-order invariance; table oracle against
`build_match(...).team_profiles`; descriptor payloads and fingerprints against the frozen
vectors; future and same-day poisoning; own-match exclusion; `context_only` identity with
B4; Poisson-multinomial factorisation; ratio of sums; selection ties; development-only
selection; permutation determinism, strata and order invariance; mirror swap; both rows of
a match in one cluster; Holm against a hand example; the reliability bound at the stated
thresholds; fail-closed validity; every gate yielding `INCONCLUSIVE` with no loss computed;
the full truth table of the verdict map; strict JSON; no identifier in the artifact.

*Committed before running. Results in `results.json`, interpretation in `analysis.md`. If
either contradicts this document, this document wins.*
