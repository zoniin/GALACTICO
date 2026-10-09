# E-13 — declared-risk selection and selection optimism

> **DRAFT. Not frozen, not registered, not run.** Written by one designer during the north-star build and never adversarially reviewed or audited. No outcome named here has been computed. It becomes a protocol only when a reviewed version is committed under `experiments/preregistered/` in a single commit that precedes any run. Section and file references such as ROOT 2.5 point to [ROOT-DECISIONS.md](../../ROOT-DECISIONS.md); see [README](../../README.md) for the working notes it cites.

Commit this plan and `config.json` before any E-13 outcome is computed: no frozen-seed
simulation cell, no half-split of a Madrid snapshot, no comparison of a risk rule with
BALANCE. This is a **prospective plan on a reused simulation design and reused historical
data**, not an untouched study (see "Prior knowledge"). Every threshold, seed, grid, window,
gate and product sentence is in `config.json`; a number that lives only in this prose is a
defect. Implementation corrections are recorded, never adopted silently; no rule changes
after the first outcome.

Directory: `experiments/preregistered/E-13-declared-risk-selection/`. Tier: PUBLIC.

## Claim and unchanged boundaries

M-05 showed that minimising declared shortfall selects estimation noise: the reported
shortfall of the selected set falls while its true shortfall rises. M-05 named the next
experiment: selection and reporting evaluated separately, out of sample. E-13 is that
experiment for the declared-risk rules of ROOT-DECISIONS 2.5 (ruling O8).

Three questions, kept apart:

1. **Selection.** Under one common report (the point-estimate shortfall of whatever was
   selected), is a rule's "true minus reported" gap smaller than BALANCE's, and what does
   that cost in true shortfall?
2. **Reporting.** Is a rule's own tail value, read as a report about the selected set, at or
   above that set's true shortfall on average?
3. **The check itself.** Does "chosen on one half, read on the other" recover the selection
   gap when the truth is known?

Part A answers all three on synthetic matches with known values (exhaustive enumeration, no
solver). Part B repeats question 1 on the two shipped Madrid snapshots without truth: select
on one coherent half of the prior matches, evaluate the fixed selection on the other half,
both directions, over repeated coherent splits.

Not estimated, and not changed by any outcome:

- No football claim. A rule is a declared preference over resamples of the same prior
  matches. No verdict makes a rule a better way to pick a team.
- No correction coefficient. Nothing measured here is subtracted from, or added to, a
  product number. M-05's rule stands: no simulation magnitude is transferred to XI Lab.
- BALANCE stays the default. No rule becomes a default; none is offered without the user
  declaring it; every rule stays available under every verdict, because each is an exact
  computation on a declared preference.
- No evidence gate moves (900-minute outfield floor, 1800-minute chance-creation floor).
  E-07 and E-08 stay closed.
- The requirement model is taken as given: additive carry-forward of prior per-90 rates.
  "True shortfall" in Part A is truth inside that model, not on a pitch.

Stated before any number exists: under a common point report, **any rule that does not
minimise the reported number reports a larger one**, so its gap narrows mechanically; a
uniformly random selection has no selection optimism at all. The optimism criterion is
necessary and cheap. The criterion that can fail for an interesting reason is the cost bound
on true shortfall. `RANDOM_SET` is carried as a reference arm to keep that visible.

## Prior knowledge

| Already seen | By whom | Bearing on E-13 |
|---|---|---|
| M-05 table: BALANCE optimism .0131 / .0605 / .1078 and oracle-shrinkage optimism at noise .1 / .3 / .6, seed 20260906 | published | The bridge reproduces it. The design (latent mean 1.8, SD .3, minimum 6.2, eight choose three) is reused knowingly; the E-13 seed is new |
| All five Wyscout leagues, for player constructs (Stage 1, 1B, 1C) | published | Different constructs and estimands; the Spain corpus is not untouched |
| E-07 / E-08: Spain and England March–May rows, opening-30-minute forecast errors | published | Madrid's matches are among those Spain rows. No lineup-selection outcome was computed there |
| XI Lab on both Madrid snapshots: full-prior BALANCE optimum `(0, 0)`; hard-floor query `OPTIMAL`, `OPTIMAL`, `INFEASIBLE` at side-floor multipliers 1, 1.2, 1.3; shared-world selection frequencies; 12-match starter-overlap diagnostic | published, test-pinned | The requirement multipliers are equal steps from the default and every one enters the decision. Their range was set knowing the published query is infeasible near 1.3; that is the one constant here informed by a real-data fact, and it is disclosed |
| Exact computations on the declared model during design: the 12-point requirement-sum frontier, the k-removal table with the players named, 120 equally optimal sets, 5,200 feasible assignments and 480 player sets in 4-3-3 | xi-core and OR reconnaissance (critique 4.4) | Not experimental outcomes. No threshold, grid, gate or tolerance here is derived from them |
| Structure of the snapshots: 34 and 30 prior team matches; 16 gated candidates; outfield candidates appear in 23–29 (and 20–25) prior matches | this design, structure only | Sets the structural stops and the `GATED_SQUAD` exposure counts |
| Synthetic solver probes: solve times; growth of the worst-world value and of the largest regret with the number of worlds | OR reconnaissance | Shows a worst-world number is not a parameter. No optimism, no regret against truth, no rule comparison |

Not seen by anyone at commit time: any optimism, true-shortfall, regret-against-truth or
optimal-selection frequency of a risk rule; any quantity computed on a half of Madrid's
prior matches.

## Fixed definitions

Units are the shipped solver's. `Q = quantization`. For value `v`, normaliser `n`, minimum
`m`: coefficient `c = round_half_even(v / n * Q)`, target `t = round_half_even(m / n * Q)`,
deficit `d_r(x) = max(0, t_r - sum of c over the selection x)`, `M(x) = max_r d_r(x)`,
`T(x) = sum_r d_r(x)`, all integers; reported values divide by `Q` ("normalised units").

A **world** is one multinomial count vector over matches, shared by every candidate and every
requirement. A world in which any candidate has zero exposure is discarded for every rule
and counted. The loss of selection `x` in world `w` is the lexicographic pair
`(M^w(x), T^w(x))`. Pairs are compared through the exact integer encoding
`E = BIG * M + T` of ROOT 2.5; `E` is a comparison device, never reported or serialised.
E-13 takes `BIG` larger than the largest possible **sum over all worlds** of `T`, so that a
sum of encodings orders exactly as the pair (sum of `M`, sum of `T`).

| Rule | Selects the feasible selections that minimise | Own statistic (normalised units) |
|---|---|---|
| `BALANCE` | `(M, T)` at the point values | `M / Q` |
| `WORST_WORLD` | the largest `(M^w, T^w)` over the used worlds; this is the tail rule with `k = 1` | `M` of that world `/ Q` |
| `TAIL_10`, `TAIL_25`, `TAIL_50` | the sum of the `k` largest `(M^w, T^w)`; `k` is the integer in `tail_counts` for the tier (the ceiling of 0.10, 0.25, 0.50 of the tier) | mean `M` over those `k` worlds `/ Q` |
| `MINIMAX_REGRET` | `max_w [E^w(x) - E*^w]`, `E*^w` the smallest encoding any feasible selection attains in world `w` (never negative) | none: a regret is not a shortfall |

**Level set.** A rule selects every feasible selection attaining its minimum exactly. No
tie-break is declared, so every per-selection quantity of an arm is the arithmetic mean over
its level set (the expectation under a uniform choice among equal optima). `BALANCE_FIRST`
(lowest canonical index, M-05's convention) is a bridge arm only. A trial or split direction
is **informative for a rule** when its level set differs from BALANCE's; otherwise their
difference is an identity, not evidence. A trial or direction with fewer used worlds than
`k` is excluded for that rule and counted.

**Reports.** `reported_point` = `M / Q` of the selection at the point values the user sees.
`reported_own` = the rule's own statistic. `true` (Part A) = `M / Q` at the latent values
through the same quantisation. `held-out` (A2, Part B) = `M / Q` at the other half's values.

**Tiers.** `world_tiers` are computed; verdicts use `decision_tiers` (the world counts the
product offers). The largest tier is reported to show growth with the number of worlds and
enters no verdict. A **component** is one (rule, decision tier) pair.

## Part A1 — synthetic selection with known values

Geometry, counts and levels are in `config.json` (`geometries`). `M05_8C3` is M-05's eight
candidates choose three with two requirements (56 selections). `GROUPED_14C10` is fourteen
candidates in three groups choosing 4 + 3 + 3 with three requirements (200 selections): the
count shape of the Madrid instance, not a model of it. Selections are enumerated; no solver.

Per trial: latent `theta[i, r] ~ Normal(latent_mean, latent_sd)`, independent. `G =
synthetic_matches`. Candidate `i` plays `n_i` whole matches (the profile's count vector,
assigned to candidates by a per-trial permutation), chosen uniformly without replacement.
Per-match observation, with `sigma_m = noise_sd * sqrt(G)` and `rho` the shared fraction:

    y[g, i, r] = theta[i, r] + sigma_m * ( sqrt(rho) * c[g, r] + sqrt(1 - rho) * e[g, i, r] )

`c` (one draw per match and requirement, shared by everyone who played) and `e` are
independent standard normals. Point value = mean of `y` over the matches played. World value
= count-weighted mean over the matches played, one count vector per world. `noise_sd` is
therefore the standard error of the value of a candidate who played all `G` matches; a
candidate with `n_i` matches has `noise_sd * sqrt(G / n_i)`. All cells of a geometry share
the same underlying draws (common random numbers); tier `W` uses the first `W` worlds.

What the noise model assumes, and what it does not:

| Assumed (declared, not fitted) | Why this value | Not assumed, not tested |
|---|---|---|
| Gaussian, additive, homoscedastic per-match noise | M-05 continuity | Count-like or zero-inflated rates; noise that scales with the rate |
| A match effect shared by teammates, `base_shared_fraction` of per-match variance (`SHARED_0` removes it) | M-04: teammates share match conditions. The fraction is a declaration | Any estimate of that fraction from football data |
| Whole-match exposure; counts copied from the structure of the 2018-05-06 snapshot (`GATED_SQUAD`: 23–29 of 34) or spanning the admissible range of a 900-minute gate (`WIDE`: 10–34) | Structure-only facts | Minutes within a match; exposure that depends on form or opponent |
| Exposure independent of latent value (`WIDE_ALIGNED` instead gives more matches to higher latent means) | Both directions are possible | Which direction football has |
| Latent values constant over the season | Required for "truth" to exist | Drift, role change, opponent effects, injury |
| Independent requirements, no position structure | M-05 continuity | Side descriptors that are structured by position and by each other |
| `noise_sd` .1 / .2 / .3 = implied reliability .90 / .69 / .50 for a 34-match candidate (algebra: `latent_sd^2 / (latent_sd^2 + noise_sd^2)`); .6 = .20, below every shipped gate, stress only | Brackets the reliability band the product admits (.50 and .70) | That any real construct has these reliabilities |

This is simulation calibration by declaration. It is **not** football calibration, and no
cell is described as "realistic".

Cells (`expand_cells`): **primary** = geometry (2) × `primary_noise_sd` (3) × minimum level
(3) × `primary_exposure_profiles` (2) = 36 per decision tier, at `base_shared_fraction`.
The same 36 at the largest tier are **beyond-menu**. **Sensitivity** = 72 cells at
`sensitivity_worlds`, one declared variant at a time (`sensitivity_variants`). **Stress** =
12 cells at `stress_noise_sd`. Only primary cells enter a verdict. The normaliser is the
geometry's `M05`-level minimum at every level (changing a minimum leaves the normaliser
fixed, as shipped).

Arms: the six rules; `BALANCE_FIRST`; `ORACLE_SHRINKAGE` (BALANCE on values shrunk with the
simulation's known mean and variances, M-05's reference, unavailable to the product);
`RANDOM_SET` (level set = every selection). Reference arms earn no verdict.

Per arm and cell, means over trials: `reported_point`, `reported_own`, `true` (M and T),
`optimism_point = true - reported_point`, `optimism_own = true - reported_own`,
disappointment frequency (`true > reported`, both reports), `regret = true M - smallest true
M`, frequency of selecting a truly optimal selection (true lexicographic optimum, exact),
level-set size, share of trials identical to BALANCE. Per rule, paired with BALANCE on the
same trials: `delta_true = true(rule) - true(BALANCE)` and `delta_optimism =
optimism_point(rule) - optimism_point(BALANCE)`.

## Part A2 — synthetic split-sample: does the check track the known values?

Part B has no truth. A held-out shortfall is itself a noisy plug-in of a convex quantity
(biased upward for a fixed selection), so "held-out gap" and "true optimism" differ. Only
additive requirement sums are unbiased for a fixed selection. A2 measures both where truth
is known, before Part B is believed and before the product's split-sample check is labelled.

Cells: geometry (2) × `primary_noise_sd` (3) × minimum level (3) at `split_exposure_profile`
and `base_shared_fraction`: 18 per decision tier. Per trial one uniformly random half/half
partition of the `G` matches; both directions; worlds are resamples of the selecting half
only. A trial contributes the mean of its two directions.

- Per rule: `true_optimism_half = true - reported_point(half)`, `heldout_gap = held-out -
  reported_point(half)`, `heldout_excess = held-out - true`.
- Per rule, paired with BALANCE: the held-out pair (`delta_gap`, `delta_out`) beside the true
  pair (`delta_optimism`, `delta_true`).
- BALANCE only, on normalised requirement sums averaged over requirements:
  `sum_gap_true = selecting-half sum - true sum`, `sum_gap_heldout = selecting-half sum -
  other-half sum` (the quantity the product's check prints), and the **recovery ratio**
  `mean(sum_gap_heldout) / mean(sum_gap_true)` with a trial-bootstrap interval.

## Part B — Madrid split-sample diagnostic

**Data and cohort.** Public Pappalardo/Wyscout Spain 2017/18 only. The two shipped
snapshots (`snapshots`): every league match on a calendar date before the decision day;
candidates, eligibility and declared minima exactly as `build_snapshot` and
`decision_inputs` produce them; formation `4-3-3`; the xT surface fitted once on all prior
league events (`fit_prior_xt`) and held fixed. The later snapshot's prior matches contain
all of the earlier one's: two views of one club-season, never two replicates.

**Exclusions.** Players the snapshot omits stay omitted. No gate is re-applied inside a
half: a half holds roughly half of a gated player's minutes. That is the cohort semantics of
a research diagnostic of the selection rule, not a relaxed certification of any individual;
no half-sample player value is reported. A split direction is unused if any candidate has no
exposure in either half or if fewer than `minimum_used_world_share` of a tier's worlds
survive. A snapshot whose structure differs from the `expected_*` counts stops the run.

**Coherent half.** One partition of the team's prior matches, applied to every candidate
and every requirement. A half value is `90 * sum(numerator) / sum(minutes)` over the half's
matches, by the shipped formula. Held fixed across halves: xT surface, candidate set,
eligibility, minima and normalisers (the declared minima were computed from all prior
matches; they are inputs, not estimates under test).

**Splits and seeds.** `RANDOM`: `random_splits` seeded balanced partitions per snapshot,
each used in both directions. `ALTERNATING` (odd/even by date; also the one split the
product's check uses, `product_split_rule`) and `CHRONOLOGICAL` (first half/second half) are
reported separately and never pooled: the chronological split mixes selection optimism with
change over time. Worlds are multinomial resamples of the selecting half, nested by tier.

**Requirement levels.** Each multiplier in `requirement_multipliers` scales all three
minima; normalisers stay at the snapshot minima. Every level enters the decision.

**Selections.** All feasible ordered assignments are enumerated once per snapshot and
reduced to distinct sets of players in requirement-bearing slots (the goalkeeper carries no
active requirement). Every rule is evaluated by enumeration with level sets, as in Part A.
`REFERENCE_PRIOR_MINUTES` (the feasible selection with the most prior minutes, chosen without
any requirement value) is the fixed-selection control: over the two directions of a split
its gap sums to exactly zero, so its spread is the no-selection noise scale.

**Solver audit.** The declared-risk solver is called through its public API on a frozen
subset (`solver_audit_*`: three random splits and the alternating split, both directions,
two levels, 12 worlds, six rules, both snapshots: 192 solves). Each certified solve must
return an XI inside the enumerated level set and per-world `(M, T)` pairs equal to the
enumerated ones. A mismatch stops the run and nothing is written. Uncertified solves and
items with a discarded world are counted and compared with nothing. The solver is imported
only after its own oracle tests pass (`risk_solver_oracle_tests`).

**Measurements.** Per snapshot, family, level, decision tier and rule: directions, used,
informative; means of `reported_point`, `reported_own`, held-out `M`, `gap = held-out -
reported_point`; `split_quantiles` of the gap over directions; per rule, paired with BALANCE
on the same direction: `delta_gap`, `delta_out`, their means and the shares of informative
directions below and above zero; per requirement, the mean normalised sum on the selecting
half and on the other half.

## Frozen procedure

No fitting, tuning or selection of any parameter. One command, in this order: (1) hashes;
protocol commit derived from git; refusal if the protocol, the config or a listed source
file differs from its committed blob; (2) M-05 bridge: the engine's `BALANCE_FIRST` arm on
M-05's exact draws must match `experiments/run_optimizer_curse.py` within `bridge_tolerance`
on all six columns; (3) Part A1; (4) Part A2; (5) solver oracle tests, then the solver
audit; (6) planted effect and planted null on synthetic values laid over each snapshot's
real structure (real minutes, real eligibility, no real numerator): the frozen split rule
must classify both correctly; (7) Part B, whose real numerators are reachable only through
one accessor that demands the committed protocol hash; (8) decisions; (9) write.

Execution failures are not verdicts: a failed bridge, a structure mismatch, a failed oracle
test, an audit mismatch, a failed planted check, a hash that differs from the commit, or an
artifact above `results_maximum_bytes` stops the run with a non-zero exit and writes
nothing. The repair is disclosed in `analysis.md` and may not touch a rule.

## Evaluation and reporting

Part A intervals: percentile interval (`interval_quantiles`) of the mean paired difference
(or of the ratio of means) over `bootstrap_replicates` resamples of whole trials
(`bootstrap_seed`); one resampling matrix per geometry, shared by all cells and rules. They
are Monte Carlo intervals for the declared simulation. They are not intervals about football.

Part B has no valid interval. Directions of one split, splits of one match set, and two
nested snapshots are dependent. The split distribution is reported as a distribution of
splits, with quantiles named as such. The thresholds below are descriptive consistency
thresholds, not significance.

Everything is reported: every arm, every cell, every level, every tier, both snapshots, the
reference arms, the audit counts, every gate count. Unavailable is `null`, never zero.

## Decision rule — frozen

"Low" and "high" are interval bounds. `margin = true_shortfall_margin`; `margin_B =
heldout_shortfall_margin`. A cell is **valid** when at most
`maximum_discarded_world_trial_share` of its trials lost a world. A valid cell is
**compared** for a rule when it has at least `minimum_informative_trials` informative trials.

**Component selection verdict** (A1, the tier's 36 primary cells). First row that applies:

| # | Condition | Verdict |
|---|---|---|
| 1 | a primary cell is invalid, or fewer than `minimum_compared_cell_fraction` of them are compared | `INCONCLUSIVE` |
| 2 | some compared cell has `delta_true` low `> margin` | `COSTS_TRUE_SHORTFALL` |
| 3 | every compared cell has `delta_true` high `<= margin` and `delta_optimism` high `< 0` | `LESS_OPTIMISTIC_NOT_WORSE` |
| 4 | otherwise | `NOT_ESTABLISHED` |

**Component reporting verdict** (A1, the tier's 36 primary cells). First row that applies:

| # | Condition | Verdict |
|---|---|---|
| 1 | the rule is `MINIMAX_REGRET` | `NOT_APPLICABLE` |
| 2 | a primary cell is invalid | `INCONCLUSIVE` |
| 3 | every cell has mean `optimism_own` high `<= 0` | `OWN_STATISTIC_NOT_OPTIMISTIC` |
| 4 | otherwise | `NOT_ESTABLISHED` |

**Component diagnostic validity** (A2, the tier's 18 cells; a yes/no input to the split
verdict). Give each interval a sign: `+` if low `> 0`, `-` if high `< 0`, else `0`. A cell
`CONTRADICTS` if `delta_gap` and `delta_optimism` have opposite non-zero signs, or
`delta_out` and `delta_true` do. It `AGREES` if it does not contradict and `delta_gap` and
`delta_optimism` have the same non-zero sign. Valid iff no cell contradicts and at least
`diagnostic_minimum_agreeing_fraction` of the cells agree.

**Component split verdict** (Part B, `RANDOM` family; the blocks are the two snapshots ×
every level in `requirement_multipliers`). Shares are over informative directions. First row
that applies:

| # | Condition | Verdict |
|---|---|---|
| 1 | some block has fewer than `minimum_used_directions` used or fewer than `minimum_informative_directions` informative directions | `INCONCLUSIVE` |
| 2 | the diagnostic is not valid for this component | `DIAGNOSTIC_UNVALIDATED` |
| 3 | every block has mean `delta_out > margin_B` and at least `minimum_direction_share` of `delta_out` above zero | `HELD_OUT_SHORTFALL_LARGER` |
| 4 | every block has mean `delta_gap < 0`, at least `minimum_direction_share` of `delta_gap` below zero, and mean `delta_out <= margin_B` | `HELD_OUT_GAP_SMALLER` |
| 5 | otherwise | `NOT_ESTABLISHED` |

**Subjects.** The registry holds six claims (`subject_arms`): `risk_rule:WORST_WORLD`,
`risk_rule:TAIL`, `risk_rule:MINIMAX_REGRET`, `risk_report:WORST_WORLD`, `risk_report:TAIL`
and `split_sample_diagnostic`. A subject's components are its rules × `decision_tiers`.
There is no `risk_report` claim for MINIMAX_REGRET: a regret is not a shortfall, and the
rule's own claim text says so.

**`risk_rule:*` token.** Aggregate the components first: selection `S` = `INCONCLUSIVE` if
any component is; else `COSTS` if any component is `COSTS_TRUE_SHORTFALL`; else `POSITIVE`
if all are `LESS_OPTIMISTIC_NOT_WORSE`; else `NOT_ESTABLISHED`. Split `P` = `INCONCLUSIVE`
if any component is; else `UNVALIDATED` if any is `DIAGNOSTIC_UNVALIDATED`; else `LARGER` if
any is `HELD_OUT_SHORTFALL_LARGER`; else `SMALLER` if all are `HELD_OUT_GAP_SMALLER`; else
`NOT_ESTABLISHED`. Then, first row that applies:

| # | `S` | `P` | Token |
|---|---|---|---|
| 1 | `INCONCLUSIVE` | any | `INCONCLUSIVE` |
| 2 | `COSTS` | any | `COSTS_SHORTFALL` |
| 2 | any other | `LARGER` | `COSTS_SHORTFALL` |
| 3 | `POSITIVE` | `SMALLER` | `LESS_OPTIMISTIC_NOT_WORSE_SYNTHETIC_AND_SPLIT` |
| 4 | `POSITIVE` | any other | `LESS_OPTIMISTIC_NOT_WORSE_SYNTHETIC` |
| 5 | `NOT_ESTABLISHED` | any other | `NOT_ESTABLISHED` |

**`risk_report:*` token.** `INCONCLUSIVE` if any component is; else
`OWN_STATISTIC_NOT_OPTIMISTIC` if all are; else `NOT_ESTABLISHED`.

**`split_sample_diagnostic` token** (A2, BALANCE, the 18 cells; BALANCE uses no worlds, so
one tier suffices). A cell is **resolved** when `sum_gap_true` low `> 0`. First row that
applies:

| # | Condition | Token |
|---|---|---|
| 1 | fewer than `diagnostic_minimum_resolved_fraction` of the cells are resolved | `INCONCLUSIVE` |
| 2 | in every resolved cell the interval of the recovery ratio lies inside `1 ± diagnostic_recovery_tolerance` | `RECOVERS_SUM_GAP` |
| 3 | otherwise | `NOT_ESTABLISHED` |

**Experiment verdict** (one token for the register): `INCONCLUSIVE` if all three
`risk_rule` tokens are; else `LABEL_EARNED` if some `risk_rule` token is a
`LESS_OPTIMISTIC_*` token; else `NOT_ESTABLISHED`.

`INCONCLUSIVE` always means a frozen sample gate failed and the subject's criterion was not
evaluated. `NOT_ESTABLISHED` always means the comparison ran and the criterion was not met:
a published null, not evidence that a rule is useless or harmful. Component tokens are
published beside every subject token, so an inconclusive subject cannot hide a component.
Whether a rule's true shortfall was strictly lower than BALANCE's in every compared cell is
recorded as a boolean and carries **no** token: a lower synthetic shortfall would be read as
a football claim.

`margin` is one half of one percent of the declared normaliser: a declared tolerance,
smaller than the smallest optimism M-05 published. It is not a football-meaningful
difference, and nobody has identified one. The recovery tolerance is likewise declared.

## Product consequence of each verdict, fixed now

Product code reads tokens and sentences from `galactico/domain/verdicts.py` and nothing
else; the sentences below are `consequence_sentences` in `config.json`, verbatim. Display
status follows `display_status`; the badge word after "TESTED" follows `claim_tokens`.
Before the run every claim is pending: "Registered, not run. No tested claim exists for
this quantity."

| Claim | Token | Display status | Sentence the product prints |
|---|---|---|---|
| `risk_rule:*` | `INCONCLUSIVE` | INCONCLUSIVE | "A declared risk preference over resamples of the same prior matches. E-13's sample gate failed for this rule, so it was not compared with Balance." |
| | `NOT_ESTABLISHED` | NOT_ESTABLISHED | "A declared risk preference over resamples of the same prior matches. On synthetic squads with known values, E-13 did not establish that choosing by this rule narrows the gap between reported and true shortfall without adding true shortfall." |
| | `COSTS_SHORTFALL` | NOT_ESTABLISHED | "A declared risk preference over resamples of the same prior matches. In E-13 the selections of this rule carried a larger declared shortfall than Balance's, on synthetic squads with known values or on held-out halves of Real Madrid's prior matches; the research note says which." |
| | `LESS_OPTIMISTIC_NOT_WORSE_SYNTHETIC` | ESTABLISHED | "On synthetic squads with known values, the true shortfall of this rule's selection exceeded its point-estimate shortfall by less than Balance's did, and was not larger than Balance's by more than 0.005 normalised units. Any rule that does not minimise the reported number narrows that gap; the tested part is the cost bound. Declared Gaussian match noise, not these players." |
| | `LESS_OPTIMISTIC_NOT_WORSE_SYNTHETIC_AND_SPLIT` | ESTABLISHED | the sentence above with its last sentence replaced by "On random half-splits of Real Madrid's prior matches the gap between chosen-on and held-out shortfall was also smaller than Balance's, without a larger held-out shortfall: one club, two overlapping snapshots, no interval." |
| `risk_report:*` | `OWN_STATISTIC_NOT_OPTIMISTIC` | ESTABLISHED | "On synthetic squads with known values this tail value was, on average, not below the selected set's true shortfall at 12 and at 40 worlds. It is a tail statistic of resampling and grows with the number of worlds." |
| | `NOT_ESTABLISHED`, `INCONCLUSIVE` | as the token | "A tail statistic of resampling. E-13 did not establish that it is at or above the true shortfall on average. It grows with the number of worlds." |
| `split_sample_diagnostic` | `RECOVERS_SUM_GAP` | ESTABLISHED | "On synthetic squads with known values, the difference between chosen-on and other-half requirement sums recovered the true selection gap of those sums within 25 percent. The shortfall line is different: a held-out shortfall is a noisy reading of a convex quantity and overstates shortfall for a fixed XI." |
| | `NOT_ESTABLISHED` | NOT_ESTABLISHED | "On synthetic squads with known values, this check did not recover the selection gap of the requirement sums within 25 percent. Read the differences as one split of one season and nothing more." |
| | `INCONCLUSIVE` | INCONCLUSIVE | "The synthetic calibration of this check did not reach its sample gate. Read the differences as one split of one season and nothing more." |

Non-claim printed with every `risk_rule` and `risk_report` sentence: "Stability against
resampling of the historical matches; not robustness to opponents, absences or form, and
not a forecast." With `split_sample_diagnostic`: "One split of one club's season. Not a
prediction of any XI, and not a correction to any number."

Scope of every token: the product's menu only (`decision_tiers`, the tail counts in
`tail_counts`). A request outside it (another world count, another tail count, another
formation or club) carries the pending sentence, whatever the tokens say.

What no outcome changes: the default rule; the need for a declared risk preference; the
availability of every rule; the world count, tail count, seed, world fingerprint and
discarded-world count beside every risk result; the absence of any corrected or "expected"
shortfall; the point-estimate requirement ledger shown for every rule; the order of rules in
the interface (fixed, never by token). The product's split-sample check stays withheld on
the real snapshots until this protocol has been executed once; afterwards it shows its own
numbers for the user's query under whichever sentence its token selects.

## What this experiment cannot show

- That any rule selects a team that plays better. Nothing here observes a match outcome.
- That the additive carry-forward model is right. Truth in Part A is truth inside it.
- The size of selection optimism in football. Part A magnitudes belong to a declared
  Gaussian simulation; Part B has one club, 34 and 30 nested matches, and no interval.
- Robustness to opponents, absences, form or role change: the worlds resample past matches.
- Anything about a world count, a tail count, a formation, a requirement set or a club that
  was not run. A worst-world value is the largest of `W` draws and is not a parameter.
- That a held-out half is truth. A2 measures that gap in the simulation only, and the
  recovery of sums holds there by exchangeable matches, which a season is not.
- A null here does not show the rules are useless; a positive token does not make a rule's
  selection correct. Repeated use of these snapshots is reuse, not validation.

## Reproducibility and tests

Artifact (`results.json`, aggregate only, under `results_maximum_bytes`): LF-normalised
SHA-256 of this protocol, of `config.json` and of every path in `source_paths`; the raw
digests of `manifest_path` as the data pin, with the Parquet file hashes recorded beside
them; the protocol commit derived from git; package versions; per snapshot the shipped
`dataset_hash`, xT version, feature fingerprints and structural counts; every seed; every
table named above; every component token and every subject token with a one-sentence reason.
No player identifier, no player name, no per-player value, no selected XI, no encoding `E`.

Must exist and pass before the frozen run (`PIPELINE.md` lists them): an independent
`itertools`/`Fraction` oracle for all six rules including level sets, discarded worlds and
the single-world invariant; rounding parity with the shipped solver; the M-05 bridge;
row-order, candidate-order and world-order invariance; shared-world coherence; snapshot
parity of full-sample values and shipped worlds against `build_snapshot`; antisymmetry of
the fixed-selection gap; exhaustive truth tables for every decision function (each input
maps to exactly one token); and the planted checks on rehearsal seeds: a planted effect of
known size must be recovered in magnitude and classified `LESS_OPTIMISTIC_NOT_WORSE`, a
planted cost must be classified `COSTS_TRUE_SHORTFALL`, an identical selection must be
`INCONCLUSIVE`, a planted sum gap must be recovered by the split check, and a zero-mean
difference must earn the positive verdict in at most `planted_array_maximum_false_positive`
of `planted_array_seeds` runs, at the rates in `config.json`. The frozen seed is used once,
by the root, plus one determinism re-run.

Committed before running. Results in `results.json`, interpretation in `analysis.md`. If
either contradicts this document, this document wins.
