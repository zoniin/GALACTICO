# E-13 — declared-risk selection and selection optimism

> **DRAFT. Not frozen, not registered, not run.** Written by one designer during the north-star build. The root ruled the six reconciliation items between this draft and the built declared-risk solver before its first review (ROOT 2.11, T1 to T8). Attacked on 18 October 2026 by three adversarial reviewers (statistics, football data, constitution: 30, 27 and 29 findings) and revised the same day ([REVIEW-RECORD.md](REVIEW-RECORD.md) lists every finding and its disposition); the revision applies T1 to T7. It has not been audited: by T8, partitioned audits with a refuter per claimed blocker follow, repeated until no scope has a blocker, before E-13 is called READY. No outcome named here has been computed. It becomes a protocol only when an audited version of the three files is committed under `experiments/preregistered/` in a single commit that precedes the pipeline and any run (`PIPELINE.md` section 11). Section and file references such as ROOT 2.5 point to [ROOT-DECISIONS.md](../../ROOT-DECISIONS.md); see [README](../../README.md) for the working notes it cites.

Commit this plan, `config.json` and `PIPELINE.md` before any E-13 outcome is computed: no
frozen-seed simulation cell, no half-split of a Madrid snapshot, no comparison of a risk rule
with BALANCE. The order is the house order: registration with six `PENDING` records, then
the pipeline built and tested on synthetic data, then the planted gate stamped in a commit of
its own, then one run and one determinism re-run. Nothing of the pipeline runs before
registration. This is a **prospective plan on a reused simulation design and reused historical
data**, not an untouched study (see "Prior knowledge"). Every threshold, seed, grid, window,
gate and product sentence is in `config.json`; a number that lives only in this prose is a
defect. Implementation corrections are recorded, never adopted silently; no rule changes
after registration.

Directory: `experiments/preregistered/E-13-declared-risk-selection/`. Tier: PUBLIC.

## Claim and unchanged boundaries

M-05 showed that minimising declared shortfall selects estimation noise: the reported
shortfall of the selected set falls while its true shortfall rises. M-05 named as its next
experiment shrinkage estimated out of sample with temporal training, and selection and
reporting evaluated separately. E-13 does the second part for the declared-risk rules of
ROOT-DECISIONS 2.5 (ruling O8): it evaluates selection and reporting separately, with known
values in a simulation and by held-out halves on real matches. It estimates no shrinkage
(`ORACLE_SHRINKAGE` uses the simulation's known variances) and keeps the temporal split out
of every verdict; out-of-sample shrinkage with temporal training is not done here.

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
  matches. No verdict makes a rule a way to pick a team that plays differently.
- No correction coefficient. Nothing measured here is subtracted from, or added to, a
  product number. M-05's rule stands: no simulation magnitude is transferred to XI Lab.
- BALANCE stays the default. No rule becomes a default; none is offered without the user
  declaring it; every rule stays available under every verdict, because each is an exact
  computation on a declared preference.
- No evidence gate moves (900-minute outfield floor, 1800-minute chance-creation floor).
  E-07 and E-08 stay closed.
- The requirement model is taken as given: additive carry-forward of prior per-90 rates.
  "True shortfall" in Part A is truth inside that model, not on a pitch.
- The tokens label only risk requests inside the token scope ("Product consequence"): the
  three measured requirements in force, which XI Lab holds only behind the experimental
  opt-in. The product's default risk request (progression alone) is outside it and keeps the
  pending payload whatever E-13 finds (ROOT 2.11 T5).

Stated before any number exists. Write `delta_rep` for a rule's point-estimate shortfall
minus BALANCE's on the same trial: it is never negative, because BALANCE minimises that
number. A rule's change in optimism is its change in true shortfall minus `delta_rep`, so the
gap narrows unless the rule's true shortfall rises by at least as much as its report. A
uniformly random selection has no selection optimism at all. The optimism criterion is
therefore necessary and cheap; the criterion that can fail for an interesting reason is the
cost bound on true shortfall. `RANDOM_SET` is carried as a reference arm to keep that
visible. One case is not cheap: where a rule's level set lies inside BALANCE's (a tie-break
among point optima, common where most sets cover the minima), `delta_rep` is zero, and the
optimism criterion then amounts to a strictly lower true shortfall than BALANCE's in that
cell. That is recorded per cell in the artifact; it carries no token of its own.

## Prior knowledge

| Already seen | By whom | Bearing on E-13 |
|---|---|---|
| M-05 table: BALANCE optimism .0131 / .0605 / .1078 and oracle-shrinkage optimism at noise .1 / .3 / .6, seed 20260906 | published | The bridge reproduces it. The design (latent mean 1.8, SD .3, minimum 6.2, eight choose three) is reused knowingly; the E-13 seed is new |
| All five Wyscout leagues, for player constructs (Stage 1, 1B, 1C) | published | Different constructs and estimands; the Spain corpus is not untouched |
| E-07 / E-08: Spain and England March–May rows, opening-30-minute forecast errors | published | Madrid's matches are among those Spain rows. No lineup-selection outcome was computed there |
| XI Lab on both Madrid snapshots: full-prior BALANCE optimum `(0, 0)`; hard-floor query `OPTIMAL`, `OPTIMAL`, `INFEASIBLE` at side-floor multipliers 1, 1.2, 1.3; shared-world selection frequencies; 12-match starter-overlap diagnostic | published, test-pinned | The requirement multipliers are equal steps from the default and every one enters the decision. Their range was set knowing the published query is infeasible near 1.3; that is the one constant here informed by a real-data fact, and it is disclosed |
| Exact computations on the declared model during design: the 12-point requirement-sum frontier, the k-removal table with the players named, 120 equally optimal sets, 5,200 feasible assignments and 480 player sets in 4-3-3 | xi-core and OR reconnaissance (critique 4.4) | Not experimental outcomes. No threshold, grid, gate or tolerance here is derived from them |
| Structure of the snapshots: 34 and 30 prior team matches; 16 gated candidates; outfield candidates in 23–29 (and 20–25) prior matches | this design, structure only | Sets the structural stops and the `GATED_APPEARANCES` counts; the root recounts both, and counts `GATED_MINUTES`, before registration (`counted_by_root_before_registration`) |
| Synthetic solver probes: solve times; growth of the worst-world value and of the largest regret with the number of worlds | OR reconnaissance | Shows a worst-world number is not a parameter. No optimism, no regret against truth, no rule comparison |
| The built risk solver's oracle suite (`risk_solver_oracle_tests`): 120 seeded synthetic instances | ADR-0030, published | Synthetic instances, no football data, no E-13 seed |
| The slow test `test_madrid_worlds_are_the_main_solve_s` (`tests/test_xi_risk.py`): on the 2018-05-06 snapshot at 12 worlds, the risk certificate's world fingerprint and discarded worlds equal the main solve's, and one single-world tail solve equals BALANCE on world 0 | runs only where the corpus is present; asserts, prints nothing on a pass | No selection frequency, no tail value and no comparison of a rule with BALANCE across worlds is printed. Whether and where it has run is recorded by the root in the registration commit |
| `scripts/time_xi_risk.py` (ROOT 2.7 X5): every rule of the menu at 12 and 40 worlds on both scenarios through the router | written to print statuses, completeness, solve counts, times, memory and worlds used and discarded only; no record in this repository that it has run on the corpus | Its printed fields bear on `solver_time_limit` only (`verified_by_root_before_registration`) and are stated in the registration commit. It prints no lineup, loss or frequency |
| XI Lab risk panels and their screenshots (X14) | only where the corpus is present | Whether a risk panel was opened on Madrid, and what it showed, is recorded by the root in the registration commit |
| The first review's synthetic checks (18 October 2026): M-05's unstructured design at seed 777 and seed 99, BALANCE first-index against level-mean optimism and tie shares; one-cell planted arrays; a walk of the token rules | reviewers, scratch scripts not committed | M-05's published estimand; no risk rule, no E-13 seed, no match-noise model of E-13 |
| The revision's synthetic checks (18 October 2026): frozen-shape decision arrays on declared normals; BALANCE and the pseudo-rules on the A1 design at seeds not E-13's (decision tokens, compared-cell counts and the extreme cell mean of each pseudo-rule printed: coin share times BALANCE's regret, M-05's estimand); the structure planted check on an invented Madrid-like structure | reviser, scratch scripts not committed (REVIEW-RECORD) | No declared-risk rule was computed, no world was drawn for a rule, no corpus file was opened |

Not seen by anyone at commit time, as far as this repository records: any optimism,
true-shortfall, regret-against-truth or optimal-selection frequency of a risk rule; any
quantity computed on a half of Madrid's prior matches; any lineup, tail value or regret of a
risk rule on a Madrid snapshot. The root confirms the last item, or states what was seen, in
the registration commit.

## Fixed definitions

Units are the shipped solver's. `Q = quantization`. For value `v`, normaliser `n`, minimum
`m`: coefficient `c = round_half_even(v / n * Q)`, target `t = round_half_even(m / n * Q)`,
deficit `d_r(x) = max(0, t_r - sum of c over the selection x)`, `M(x) = max_r d_r(x)`,
`T(x) = sum_r d_r(x)`, all integers; reported values divide by `Q` ("normalised units").

A **world** is one multinomial count vector over matches, shared by every candidate and every
requirement. **Discard rule** (the shipped bootstrap's, ROOT 2.4 and 2.11 T2;
`solver.py:549-564`, `risk.py` `_discard`): a world is discarded, for every rule, and counted,
when a candidate who is not excluded has no value in it for a requirement in force at a slot he
is eligible for. A candidate has no value in a world when he has no positive minutes in any
match the world draws. E-13 excludes no one. In Part A every candidate is eligible for a pick
of his group and every requirement applies to every pick, so there the rule discards a world
in which any candidate has no exposure; that is a consequence of the rule, not its definition.
In Part B a goalkeeper, at whose slot no requirement applies, never discards a world.

The loss of selection `x` in world `w` is the lexicographic pair `(M^w(x), T^w(x))`. Pairs are
compared through the exact integer encoding `E = BIG * M + T` of ROOT 2.5, with `BIG` from
`encoding_base_rule` (ROOT 2.7 X3: above any sum of `T` over the tier's worlds and above twice
one `T`), so a sum of encodings orders exactly as the pair (sum of `M`, sum of `T`) and a
regret orders as its pair. `E` is a comparison device, never reported or serialised.

| Rule | Selects the feasible selections that minimise | Own statistic (normalised units) |
|---|---|---|
| `BALANCE` | `(M, T)` at the point values | `M / Q` |
| `WORST_WORLD` | the largest `(M^w, T^w)` over the used worlds; this is the tail rule with `k = 1` | `M` of that world `/ Q` |
| `TAIL_10`, `TAIL_25`, `TAIL_50` | the sum of the `k` largest `(M^w, T^w)`; `k` is the integer in `tail_counts` for the tier (the ceiling of 0.10, 0.25, 0.50 of the tier) | mean `M` over those `k` worlds `/ Q` |
| `MINIMAX_REGRET` | `max_w [E^w(x) - E*^w]`, `E*^w` the smallest encoding any feasible selection attains in world `w` (never negative) | none: a regret is not a shortfall |

**Level set.** A rule selects every feasible selection attaining its minimum exactly. No
tie-break is declared, so every per-selection quantity of an arm is the arithmetic mean over
its level set (the expectation under a uniform choice among equal optima). `BALANCE_FIRST`
and `ORACLE_SHRINKAGE_FIRST` (lowest canonical index, M-05's convention) are bridge arms only.
A trial or split direction is **informative for a rule** when its level set differs from
BALANCE's; otherwise their difference is an identity, not evidence.

**Unusable trials** (`unusable_trial_rule`). A trial or direction with fewer used worlds than
`k` is excluded for that rule and for its BALANCE pair, and counted; `k` is never recomputed
on the used worlds.

**Reports.** `reported_point` = `M / Q` of the selection at the point values the user sees.
`reported_own` = the rule's own statistic. `true` (Part A) = `M / Q` at the latent values
through the same quantisation. `held-out` (A2, Part B) = `M / Q` at the other half's values.

**Tiers.** `world_tiers` are computed; verdicts use `decision_tiers` (the world counts the
risk menu holds, ROOT 2.11 T6). The largest tier is reported to show growth with the number of
worlds and enters no verdict. A **component** is one (rule, decision tier) pair.

## Part A1 — synthetic selection with known values

Geometry, counts and levels are in `config.json` (`geometries`). `M05_8C3` is M-05's eight
candidates choose three with two requirements (56 selections). `GROUPED_14C10` is fourteen
candidates in three groups choosing 4 + 3 + 3 with three requirements (200 selections): the
count shape of the Madrid instance, not a model of it. Selections are enumerated; no solver.
Minimum levels follow `minimum_level_rule` (for `GROUPED_14C10`: 18.0, 19.46 and 20.92, the
mean sum of ten picks plus 0, 1 and 2 times 0.8 times the square root of ten thirds); the
normaliser is the `M05` level at every level (changing a minimum leaves the normaliser fixed,
as shipped).

Per trial: latent `theta[i, r] ~ Normal(latent_mean, latent_sd)`, independent. `G =
synthetic_matches`. Candidate `i` plays `n_i` whole matches (`exposure_unit`; the profile's
count vector, assigned to candidates by a per-trial permutation), chosen uniformly without
replacement. Per-match observation, with `sigma_m = noise_sd * sqrt(G)` and `rho` the shared
fraction:

    y[g, i, r] = theta[i, r] + sigma_m * ( sqrt(rho) * c[g, r] + sqrt(1 - rho) * e[g, i, r] )

`c` (one draw per match and requirement, shared by everyone who played) and `e` are
independent standard normals. Point value = mean of `y` over the matches played. World value
= count-weighted mean over the matches played, one count vector per world. `noise_sd` is
therefore the standard error of the value of a candidate who played all `G` matches; a
candidate with `n_i` matches has `noise_sd * sqrt(G / n_i)`. All cells of a geometry share
the same underlying draws (common random numbers); tier `W` uses the first `W` worlds.

**Exposure profiles.** `GATED_MINUTES` copies, for each gated outfield candidate of the
2018-05-06 snapshot, his prior minutes divided by 90 and rounded half to even: the exposure
the shipped minutes-weighted estimator gives him in full-match equivalents. A player with 23
appearances and 1,200 minutes is 13 such matches, and his noise is the larger accordingly.
`GATED_APPEARANCES` copies the same candidates' appearances (matches with positive
reconstructed minutes) and treats each as a whole match; it understates their noise and is a
sensitivity variant only. Both are counted by the root from structure before registration.
`WIDE` spans the range a 900-minute gate admits, from 10 full-match equivalents to `G`.
`M05_8C3` takes eight of a profile's fourteen counts by `exposure_subset_rule` (the order
statistics at positions 0, 2, 4, 6, 7, 9, 11 and 13); a spanning profile is evenly spaced
from 10 to `G`.

What the noise model assumes, and what it does not:

| Assumed (declared, not fitted) | Why this value | Not assumed, not tested |
|---|---|---|
| Gaussian, additive, homoscedastic per-match noise | M-05 continuity | Count-like or zero-inflated rates; noise that scales with the rate |
| A match effect shared by teammates, `base_shared_fraction` of per-match variance (`SHARED_0` removes it) | M-04: teammates share match conditions. The fraction is a declaration | Any estimate of that fraction from football data |
| Whole-match exposure in full-match equivalents of the minutes-weighted estimator (`GATED_MINUTES`), or spanning the admissible range of a 900-minute gate (`WIDE`) | Structure-only facts | Minutes within a match; exposure that depends on form or opponent |
| Exposure independent across candidates: each candidate's matches are drawn on their own | Simplest declaration | Squad rotation and competition for a slot, which make teammates' exposures negatively related, change how often two candidates share a match effect and change world discards. Part B's structure check uses the real minutes |
| Exposure independent of latent value (`WIDE_ALIGNED` instead gives more matches to higher latent means) | Both directions are possible | Which direction football has |
| Latent values constant over the season | Required for "truth" to exist | Drift, role change, opponent effects, injury |
| Independent requirements, no positional structure | M-05 continuity | The structure of the real side requirements: wide-channel pass origins are set by deployment, near zero for a player of the other side, and covered by whichever player of that side is in the XI. The product sentences say the synthetic squads have none |
| `noise_sd` .1 / .2 / .3: implied reliability `latent_sd^2 / (latent_sd^2 + noise_sd^2 * G / n)` of .73–.90 / .40–.69 / .23–.50 over exposures from 10 matches to `G`; .6 (stress only): .07–.20 | A declared grid; the reliabilities are its algebra over the exposures the profiles hold, for no other population | That any real construct has these reliabilities; the product's split-half reliability gate is a league-wide statistic of another kind, at a minutes floor, and is not compared with these |

This is simulation calibration by declaration. It is **not** football calibration, and no
cell is described as "realistic".

Cells (`expand_cells`): **primary** = geometry (2) × `primary_noise_sd` (3) × minimum level
(3) × `primary_exposure_profiles` (2) = `expected_primary_cells_per_tier` per decision tier, at
`base_shared_fraction`. The same cells at the largest tier are **beyond-menu**.
**Sensitivity** = `expected_sensitivity_cells` cells at `sensitivity_worlds`, one declared
variant at a time (`sensitivity_variants`). **Stress** = `expected_stress_cells` cells at
`stress_noise_sd` and `stress_worlds` (geometry × level × primary exposure profile). Only
primary cells enter a verdict.

Arms: the six rules; `BALANCE_FIRST`; `ORACLE_SHRINKAGE` (BALANCE on values shrunk with the
simulation's known mean and variances, M-05's reference, unavailable to the product);
`RANDOM_SET` (level set = every selection). Reference arms earn no verdict.

Per arm and cell, means over trials: `reported_point`, `reported_own`, `true` (M and T),
`optimism_point = true - reported_point`, `optimism_own = true - reported_own`,
disappointment frequency (`true > reported`, both reports), `regret = true M - smallest true
M`, frequency of selecting a truly optimal selection (true lexicographic optimum, exact),
level-set size, share of trials identical to BALANCE. Per rule, paired with BALANCE on the
same trials: `delta_true = true(rule) - true(BALANCE)`, `delta_rep` and `delta_optimism =
optimism_point(rule) - optimism_point(BALANCE)`, and per cell the share of informative trials
with `delta_rep` zero (the tie-break cells of "Claim").

**Precision.** The trial counts are set so that a cell's 95% interval half-width is at most
`precision_target_half_width_fraction` of `true_shortfall_margin` when the per-trial standard
deviation of a paired difference is at most `precision_target_sd` (at the frozen trial count,
1.96 × 0.05 / sqrt(4000) = 0.0015, against one third of the margin, 0.0017). The artifact
reports each cell's realised half-widths.

## Part A2 — synthetic split-sample: does the check track the known values?

Part B has no truth. A held-out shortfall is itself a noisy plug-in of a convex quantity
(biased upward on average for a fixed selection), so "held-out gap" and "true optimism"
differ. Only additive requirement sums are unbiased for a fixed selection. A2 measures both
where truth is known, before Part B is believed.

Cells: geometry (2) × `primary_noise_sd` (3) × minimum level (3) at `split_exposure_profile`
and `base_shared_fraction`: `expected_split_cells_per_tier` per decision tier. Per trial one
uniformly random half/half partition of the `G` matches; both directions; worlds are resamples
of the selecting half only. A trial contributes the mean of its two directions, and is usable
for a rule only when both directions are. A trial is informative for a rule when at least one
of its directions is; the count is reported and gates nothing.

- Per rule: `true_optimism_half = true - reported_point(half)`, `heldout_gap = held-out -
  reported_point(half)`, `heldout_excess = held-out - true`.
- Per rule, paired with BALANCE: the held-out pair (`delta_gap`, `delta_out`) beside the true
  pair (`delta_optimism`, `delta_true`), and their difference `delta_out - delta_true` (the
  rule's held-out excess minus BALANCE's): whether the held-out cost tracks the true cost.
- BALANCE only, on normalised requirement sums averaged over requirements:
  `sum_gap_true = selecting-half sum - true sum`, `sum_gap_heldout = selecting-half sum -
  other-half sum`, and the **recovery ratio** `mean(sum_gap_heldout) / mean(sum_gap_true)`
  with a trial-bootstrap interval.

## Part B — Madrid split-sample diagnostic

**Data and cohort.** Public Pappalardo/Wyscout Spain 2017/18 only. The two shipped
snapshots (`snapshots`): every league match on a calendar date before the decision day;
candidates, eligibility and declared minima exactly as `build_snapshot` and
`decision_inputs` produce them; formation `4-3-3`; the three measured requirements in force
(`expected_active_requirements`); the xT surface fitted once on all prior league events
(`fit_prior_xt`) and held fixed. The later snapshot's prior matches contain all of the earlier
one's: two views of one club-season, never two replicates. The four files of `data_paths` are
read whole, as `load_snapshot` reads them, so that the shipped `dataset_hash` is reproduced
(`data_read_rule`, the named exception to ROOT 4's column lists).

**Exposure.** A candidate's exposure in a match is his reconstructed minutes there, and he has
exposure when they are positive. The minutes are the shipped lineup reconstruction, inherited
as parity requires: no stoppage time, a dismissed player counted to the end of the match, and
a substitute who came on at the 90th minute listed with zero minutes (his events then add to a
numerator without a denominator).

**Exclusions.** Players the snapshot omits stay omitted. No gate is re-applied inside a
half: a half holds roughly half of a gated player's minutes. That is the cohort semantics of
a research diagnostic of the selection rule, not a relaxed certification of any individual;
no half-sample player value is reported. A split direction is **used** when every candidate
eligible at a slot where a requirement in force applies has exposure in both halves (so every
selection has a value on both), and, for an arm that reads worlds, when at least
`minimum_used_world_share` of the tier's worlds survive the discard rule.
`REFERENCE_PRIOR_MINUTES` reads no world, so its used directions are those that meet the
exposure condition, which is the same for both directions of a split. A snapshot whose
structure differs from its `expected_*` counts stops the run.

**Coherent half.** One partition of the team's prior matches, applied to every candidate
and every requirement. A half value is `90 * sum(numerator) / sum(minutes)` over the half's
matches, by the shipped formula and the shipped per-match components. Held fixed across
halves: xT surface, candidate set, eligibility, minima and normalisers. Two of these couple the
halves and are under no test: the xT surface is fitted on all prior league events, the held-out
half's included (for a chronological direction, later events too), and the minima and
normalisers are medians of starting-XI sums over all prior matches. Both are small channels
(Madrid's held-out half is about a twentieth of the league matches in the xT fit), not zero.

**Splits and seeds.** `RANDOM`: `random_splits` seeded balanced partitions per snapshot,
each used in both directions. `ALTERNATING` (odd/even positions by date) and `CHRONOLOGICAL`
(first half/second half) are reported separately and never pooled. The chronological split
mixes selection optimism with change over time. The alternating split may mix it with venue:
a fixture list that alternates home and away puts most home matches in one half. The count of
home matches in each half of both deterministic splits, and its distribution over the random
splits, are reported (structure only). The alternating split is a research family; no product
split is defined here (ROOT 2.11 T7). Worlds are multinomial resamples of the selecting half,
nested by tier.

**Requirement levels.** Each multiplier in `requirement_multipliers` scales all three
minima; normalisers stay at the snapshot minima. Every level enters the decision.

**Selections.** All feasible ordered assignments are enumerated once per snapshot and
reduced to distinct sets of players in requirement-bearing slots (the goalkeeper carries no
requirement in force). Every rule is evaluated by enumeration with level sets, as in Part A.
`REFERENCE_PRIOR_MINUTES` (the feasible selection with the most prior minutes, chosen without
any requirement value) is the fixed-selection control: over the two directions of a split
whose directions are both used its gap sums to exactly zero, so its spread is the
no-selection noise scale.

**Solver audit.** The built declared-risk solver is called through its public function
`declared_risk_selection` (ROOT 2.11 T1) on a frozen subset (`solver_audit_*`: three random
splits and the alternating split, both directions, two levels, 12 worlds, six rules, both
snapshots: `solver_audit_expected_items` solves; BALANCE through `solve_xi`). Its arguments are
E-13's own: the split-half worlds, their count, a world seed by `solver_audit_world_seed_rule`,
the version string `solver_audit_bootstrap_version`, `solver_seed`, a deadline of
`solver_time_limit` seconds, `tail_count` 1 for `WORST_WORLD`, the tier's `k` for a tail rule and
none for the regret, and no tie analysis (`solver_audit_analyze_ties`). An item is certified when
its status is `CERTIFIED` with completeness `EXACT` (BALANCE: `OPTIMAL`). A certified item must
return an XI whose requirement-bearing players form a selection of the enumerated level set,
per-world `(M, T)` pairs (`world_losses`) equal to the enumerated pairs in every used world,
used and discarded world ids equal to the enumeration's, the rule's optimum equal to the
enumerated one, and for the regret each world's least pair equal to the enumerated one. A world
discarded by the one discard rule is compared, never skipped. A direction that is not used
is not audited, and is counted. Fewer certified items than
`solver_audit_minimum_certified_share` of the audited items, no audited item, or any mismatch
stops the run and nothing is written. The solver is imported only after its oracle tests pass
on POSIX with the counts in `risk_solver_oracle_expected` (`risk_solver_oracle_tests`).

**Measurements.** Per snapshot, family, level, decision tier and rule: directions, used,
informative; means of `reported_point`, `reported_own`, held-out `M`, `gap = held-out -
reported_point`; `split_quantiles` of the gap over used directions; per rule, paired with
BALANCE on the same direction: `delta_gap`, `delta_out`, their means over every used direction
with a zero where the level sets are identical (`split_mean_denominator`, as A1), and the
shares of informative used directions below and above zero; per requirement, the mean
normalised sum on the selecting half and on the other half.

## Frozen procedure

No fitting, tuning or selection of any parameter. One command, in this order: (1) hashes;
protocol commit derived from git; refusal if any of `protocol_files` or a listed source file
differs from its committed blob; (2) M-05 bridge: the engine's bridge arms on M-05's exact
draws must match `experiments/run_optimizer_curse.py` within `bridge_tolerance` on all six
columns (`bridge_columns`); (3) Part A1; (4) Part A2; (5) both snapshots loaded through the one
loader that demands the committed protocol hash, with the structural stops (the real numerators
are read here and enter no selection or gap before step 8); (6) the risk solver's oracle gate;
(7) the planted structure check: planted effect, planted cost and planted identity on synthetic
values laid over both snapshots' real structure together (real minutes, real eligibility, no
real numerator), which the frozen split rule must classify as `planted_split_arms` says;
(8) the solver audit; (9) Part B; (10) decisions; (11) write.

Execution failures are not verdicts: a failed bridge, a structure mismatch, a failed or
skipped oracle test, an audit mismatch or a certified share below its minimum, a failed planted
check, a hash that differs from the commit, or an artifact above `results_maximum_bytes` stops
the run with a non-zero exit and writes nothing. The repair is disclosed in `analysis.md` and
may not touch a rule; a rule that a planted check shows to be unsound is not repaired, and E-13
is then superseded by a new experiment id with its own preregistration.

## Evaluation and reporting

Part A intervals: percentile interval (`interval_quantiles`, `interval_quantile_method`) of
the mean paired difference (or of the ratio of means) over `bootstrap_replicates` resamples of
whole trials (`bootstrap_seed`); one resampling matrix per geometry, shared by all cells and
rules, restricted to a rule's usable trials (`unusable_trial_rule`). The standard error of a
cell mean is `standard_error_rule`. These are Monte Carlo intervals for the declared
simulation. They are not intervals about football.

The positive criteria are intersections (every compared cell must pass), so their size needs
no adjustment. The cost criterion is a union (any valid cell may show a cost), so it is
adjusted: `cost_multiplicity_rule` (Bonferroni at `cost_family_alpha` over the valid primary
cells of the subject, with a normal bound on the bootstrap standard error). Under every
configuration in which no cell's true cost exceeds the margin, a subject's cost token fires
with probability at most `cost_family_alpha`, up to the normal approximation; common random
numbers correlate the cells and make it smaller.

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
A valid cell **shows a cost** for a rule when its cost bound, `mean(delta_true) - z_m * SE`,
exceeds `margin`, with `z_m` and `m` from `cost_multiplicity_rule`. A measured cost is never
hidden behind a gate that failed in another cell or component: the selection verdict, both
aggregations and the token table read a cost first. (The split verdict's cost is a statement
about every block, so its gate is read first.)

**Component selection verdict** (A1, the tier's primary cells). First row that applies:

| # | Condition | Verdict |
|---|---|---|
| 1 | some valid primary cell shows a cost | `COSTS_TRUE_SHORTFALL` |
| 2 | a primary cell is invalid, or fewer than `minimum_compared_cell_fraction` of them are compared | `INCONCLUSIVE` |
| 3 | every compared cell has `delta_true` high `<= margin` and `delta_optimism` high `< 0` | `LESS_OPTIMISTIC_COST_BOUNDED` |
| 4 | otherwise | `NOT_ESTABLISHED` |

**Component reporting verdict** (A1, the tier's primary cells). A valid cell is
**reporting-compared** when at least `reporting_minimum_nonzero_trials` of its usable trials
have a non-zero own statistic or a non-zero true shortfall. First row that applies:

| # | Condition | Verdict |
|---|---|---|
| 1 | the rule is `MINIMAX_REGRET` | `NOT_APPLICABLE` |
| 2 | a primary cell is invalid, or fewer than `reporting_minimum_compared_cell_fraction` of them are reporting-compared | `INCONCLUSIVE` |
| 3 | every reporting-compared cell has mean `optimism_own` high `<= 0` | `OWN_STATISTIC_NOT_OPTIMISTIC` |
| 4 | otherwise | `NOT_ESTABLISHED` |

**Component diagnostic validity** (A2, the tier's split cells; a yes/no input to the split
verdict). Give each interval a sign: `+` if low `> 0`, `-` if high `< 0`, else `0`. A cell
`CONTRADICTS` if `delta_gap` and `delta_optimism` have opposite non-zero signs, or
`delta_out` and `delta_true` do. It `AGREES` if it does not contradict and `delta_gap` and
`delta_optimism` have the same non-zero sign. With `tol = diagnostic_cost_tolerance`, the cost
of a cell `TRACKS` when the interval of `delta_out - delta_true` lies inside the closed
interval `[-tol, tol]`, and `DIVERGES` when it lies wholly outside it (low `> tol` or high
`< -tol`). Valid iff no cell contradicts, no cell's cost diverges, at least
`diagnostic_minimum_agreeing_fraction` of the cells agree and at least
`diagnostic_minimum_tracking_fraction` of them track. The optimism pair alone is pushed the
same way by `delta_rep`; the tracking condition is what lets the held-out cost stand for the
true cost in Part B.

**Component split verdict** (Part B, `RANDOM` family; the blocks are the two snapshots ×
every level in `requirement_multipliers`, `split_expected_blocks` of them). Means are over used
directions with zeros where identical; shares are over informative used directions. First row
that applies:

| # | Condition | Verdict |
|---|---|---|
| 1 | fewer than `split_expected_blocks` blocks, or some block has fewer than `minimum_used_directions` used or fewer than `minimum_informative_directions` informative directions | `INCONCLUSIVE` |
| 2 | the diagnostic is not valid for this component | `DIAGNOSTIC_UNVALIDATED` |
| 3 | every block has mean `delta_out > margin_B` and at least `minimum_direction_share` of `delta_out` above zero | `HELD_OUT_SHORTFALL_LARGER` |
| 4 | every block has mean `delta_gap < 0`, at least `minimum_direction_share` of `delta_gap` below zero, and mean `delta_out <= margin_B` | `HELD_OUT_GAP_SMALLER` |
| 5 | otherwise | `NOT_ESTABLISHED` |

**Subjects.** The registry holds six claims (`registry_subjects`, `subject_arms`):
`risk_rule:WORST_WORLD`, `risk_rule:TAIL`, `risk_rule:MINIMAX_REGRET`,
`risk_report:WORST_WORLD`, `risk_report:TAIL` and `split_sample_diagnostic`. A subject's
components are its rules × `decision_tiers`. There is no `risk_report` claim for
MINIMAX_REGRET: a regret is not a shortfall.

**`risk_rule:*` token.** Aggregate the components first, a cost first: selection `S` =
`COSTS` if any component is `COSTS_TRUE_SHORTFALL`; else `INCONCLUSIVE` if any component is;
else `POSITIVE` if all are `LESS_OPTIMISTIC_COST_BOUNDED`; else `NOT_ESTABLISHED`. Split `P` =
`LARGER` if any component is `HELD_OUT_SHORTFALL_LARGER`; else `INCONCLUSIVE` if any is; else
`UNVALIDATED` if any is `DIAGNOSTIC_UNVALIDATED`; else `SMALLER` if all are
`HELD_OUT_GAP_SMALLER`; else `NOT_ESTABLISHED`. Then, first row that applies:

| # | `S` | `P` | Token |
|---|---|---|---|
| 1 | `COSTS` | any | `COSTS_SHORTFALL` |
| 2 | any | `LARGER` | `COSTS_SHORTFALL` |
| 3 | `INCONCLUSIVE` | any other | `INCONCLUSIVE` |
| 4 | `POSITIVE` | `SMALLER` | `LESS_OPTIMISTIC_COST_BOUNDED_SYNTHETIC_AND_SPLIT` |
| 5 | `POSITIVE` | `INCONCLUSIVE`, `UNVALIDATED` or `NOT_ESTABLISHED` | `LESS_OPTIMISTIC_COST_BOUNDED_SYNTHETIC` |
| 6 | `NOT_ESTABLISHED` | any other | `NOT_ESTABLISHED` |

The cost comes first because a cost measured in one component is evidence about the rule,
whatever a gate did in another; a positive token is published only when no component of
either part measured a cost.

**`risk_report:*` token.** `INCONCLUSIVE` if any component is; else
`OWN_STATISTIC_NOT_OPTIMISTIC` if all are; else `NOT_ESTABLISHED`.

**`split_sample_diagnostic` token** (A2, BALANCE, the split cells of the first decision tier;
BALANCE uses no worlds, so one tier suffices). A cell is **resolved** when `sum_gap_true` low
`> 0`. A resolved cell **recovers** when every bootstrap replicate's denominator is positive and
the interval of the recovery ratio lies inside the closed interval `[1 -
diagnostic_recovery_tolerance, 1 + diagnostic_recovery_tolerance]`. First row that applies:

| # | Condition | Token |
|---|---|---|
| 1 | fewer than `diagnostic_minimum_resolved_fraction` of the cells are resolved | `INCONCLUSIVE` |
| 2 | every resolved cell recovers | `RECOVERS_SUM_GAP` |
| 3 | otherwise | `NOT_ESTABLISHED` |

**Experiment verdict** (one token for the register, from `experiment_verdict_vocabulary`):
`INCONCLUSIVE` if all three `risk_rule` tokens are; else `LABEL_EARNED` if some `risk_rule`
token is a `LESS_OPTIMISTIC_*` token; else `NOT_ESTABLISHED`.

`INCONCLUSIVE` always means a frozen sample gate failed, no cost was measured, and the
subject's criterion was not evaluated. `NOT_ESTABLISHED` always means the comparison ran and
the criterion was not met: a published null, not evidence that a rule is useless or harmful.
Component tokens are published beside every subject token, so an inconclusive subject cannot
hide a component. Whether a rule's true shortfall was strictly lower than BALANCE's in every
compared cell is recorded as a boolean and carries **no** token: a lower synthetic shortfall
would be read as a football claim. The sensitivity and stress cells reach no decision; for
each rule the artifact counts its valid cells there that show a cost (`m` = those cells).

`margin` is one half of one percent of the declared normaliser: a declared tolerance,
smaller than the smallest optimism M-05 published. It is not a football-meaningful
difference, and nobody has identified one. The recovery and cost-tracking tolerances are
likewise declared.

## Product consequence of each verdict, fixed now

Product code reads tokens and sentences from `galactico/domain/verdicts.py` and nothing
else. The registration commit adds six `PENDING` records built from `config.json`
(`registry_experiment_id`, `experiment_directory`, `registry_subjects`, `verdict_vocabulary`,
`registry_common`, the three `registry_*` family entries and `registry_outcomes`): each record's
scope, badge word (`claim_token`), non-claim, not-run statement and the status, limit flag and
statement of every token are those values, verbatim. Every one passes the response boundary
(`runtime.finalize`) and the copy guard under every token, `PENDING` included. While a record is
`PENDING` it prints its not-run statement: "No E-13 result applies here: E-13 has not run, or
the request lies outside what it tests." It stays true when the router serves the pending form
of an executed record to a request outside the token scope.

| Claim | Token | Status (limits) | Statement the product prints |
|---|---|---|---|
| `risk_rule:*` | `INCONCLUSIVE` | INCONCLUSIVE | "A declared risk preference over resamples of the same prior matches. A sample gate of E-13 failed for this rule and no cost was measured, so it was not compared with Balance." |
| | `NOT_ESTABLISHED` | NOT_ESTABLISHED | "A declared risk preference over resamples of the same prior matches. On synthetic squads with known values, E-13 did not establish that choosing by this rule narrows the gap between reported and true shortfall while keeping its true shortfall within 0.005 normalised units of Balance's on average." |
| | `COSTS_SHORTFALL` | NOT_ESTABLISHED | "A declared risk preference over resamples of the same prior matches. In E-13 this rule's selections had a larger average largest normalised shortfall than Balance's, by more than 0.005, against known values on synthetic squads or on held-out halves of Real Madrid's prior matches; the research note says which." |
| | `LESS_OPTIMISTIC_COST_BOUNDED_SYNTHETIC` | ESTABLISHED (with limits) | "On synthetic squads with known values and no positional structure, averaged over trials in each compared cell, the true largest shortfall of this rule's selection exceeded its point-estimate shortfall by less than Balance's did, and was not larger than Balance's by more than 0.005 normalised units. A rule that does not minimise the reported shortfall reports at least Balance's, so the gap narrows unless its true shortfall rises as much; the tested part is the cost bound. Declared Gaussian match noise, not these players." |
| | `LESS_OPTIMISTIC_COST_BOUNDED_SYNTHETIC_AND_SPLIT` | ESTABLISHED (with limits) | the two sentences above before "Declared Gaussian match noise", then "On random half-splits of Real Madrid's prior matches the gap between chosen-on and held-out shortfall was also smaller than Balance's, without a held-out shortfall larger than Balance's by more than 0.005 normalised units on average: one club, two overlapping snapshots, no interval." |
| `risk_report:*` | `OWN_STATISTIC_NOT_OPTIMISTIC` | ESTABLISHED (with limits) | "On synthetic squads with known values, in each compared cell, this tail value was on average not below the selected XI's true largest shortfall at 12 and at 40 worlds. It is a tail statistic of resampling, the mean over the tail worlds and not their sum, and it grows with the number of worlds." |
| | `NOT_ESTABLISHED` | NOT_ESTABLISHED | "A tail statistic of resampling. E-13 compared it with the true largest shortfall on synthetic squads and did not establish that it is at or above it on average. It grows with the number of worlds." |
| | `INCONCLUSIVE` | INCONCLUSIVE | "A tail statistic of resampling. A sample gate of E-13 failed for this value, so it was not compared with the true shortfall. It grows with the number of worlds." |
| `split_sample_diagnostic` | `RECOVERS_SUM_GAP` | ESTABLISHED (with limits) | "On synthetic squads with known values, E-13's split-sample check recovered the true selection gap of the requirement sums within 25 percent. The shortfall line is different: a held-out shortfall is a noisy reading of a convex quantity and on average overstates the shortfall of a fixed XI." |
| | `NOT_ESTABLISHED` | NOT_ESTABLISHED | "On synthetic squads with known values, E-13's split-sample check did not recover the selection gap of the requirement sums within 25 percent. Its Madrid differences are read as the spread of one club-season's splits and nothing more." |
| | `INCONCLUSIVE` | INCONCLUSIVE | "The synthetic calibration of E-13's split-sample check did not reach its sample gate. Its Madrid differences are read as the spread of one club-season's splits and nothing more." |

Scope of each record (`registry_risk_rule`, `registry_risk_report`,
`registry_split_sample_diagnostic`):

- `risk_rule:*`: "Selections of eleven by this declared risk rule set against Balance, on
  synthetic squads with known values (eight candidates choosing three, and fourteen in three
  groups choosing ten; Gaussian match noise; no positional structure) and on Real Madrid's
  2017/18 league matches before 8 April and before 6 May 2018 in the public Wyscout data
  (Pappalardo et al. 2019): formation 4-3-3, 12 or 40 resampled worlds, the menu's tail counts,
  the three measured requirements in force (left and right wide-channel pass origins and
  progression), declared minima equal to the snapshot's own times 1.0, 1.15, 1.3 or 1.45, and no
  lock or exclusion."
- `risk_report:*`: "The tail value of this declared risk rule (the largest shortfall of its
  worst world, or the mean largest shortfall over its k tail worlds, in normalised units) read
  as a report about the selected XI, on synthetic squads with known values, at 12 and at 40
  resampled worlds and the menu's tail counts."
- `split_sample_diagnostic`: "E-13's research split-sample check under Balance (select on one
  half of the matches, read the fixed selection on the other half), calibrated on synthetic
  squads with known values and exchangeable matches; it labels no product computation."

Badge words: "LESS OPTIMISTIC, COST BOUNDED" (`risk_rule`), "NOT OPTIMISTIC ON AVERAGE"
(`risk_report`), "RECOVERS THE SUM GAP" (`split_sample_diagnostic`). Non-claim printed with
every `risk_rule` and `risk_report` statement: "Stability against resampling of the historical
matches; not robustness to opponents, absences or form, and not a forecast." With
`split_sample_diagnostic`: "A research check of one experiment. Not a prediction of any XI, and
not a correction to any number."

**Token scope** (`token_scope`, ROOT 2.11 T5). A `risk_rule` token speaks only to a risk
request with formation `formation`, a world count in `decision_tiers`, a tail count of
`tail_counts` for that world count (`WORST_WORLD` at 1), a scenario among
`snapshots[*].scenario_id`, the requirement set in force equal to
`expected_active_requirements`, declared minima that are the snapshot's own times one of
`requirement_multipliers` (`declared_minima_rule`, compared in the solver's integer units), and
no lock or exclusion. A request outside any of these carries the subject's pending payload and
`RISK_OUTSIDE_E13`, whatever the token. That includes the product's default risk request,
which holds progression alone: E-13's tokens never label it. The router's `E13_SCOPE` holds the
first five today and is equal to this config by test; the minima, lock and exclusion conditions
are a registration-commit request to the root (`PIPELINE.md` section 11). The scope sentence of
every `risk_rule` record states the same list.

**`risk_report`** (ROOT 2.11 T4; `risk_report_after_run`). E-13's statistic is the largest
shortfall `M` of the worst world and the mean `M` over the `k` tail worlds; the product serves
the tail sum of `M`, which is `k` times it. Before the results commit the product serves no
`risk_report` payload and prints no figure note, and `verdicts.risk_report` stays `null` on
every reply. If E-13 runs, its results commit may add the mean (the tail sum divided by `k`) as
an exact server text that carries the `risk_report` payload and its statement, under an ADR
naming that edit, as ROOT 2.10 W8 rules for E-09. The statement is never set beside the tail
sum itself.

**`split_sample_diagnostic`** (ROOT 2.11 T7; `split_sample_after_run`). The split-sample check
is E-13's own research code. No product tool exists or is specified here; the record labels no
product computation and is served on the verdicts endpoint only. A later product tool is
specified in a change set of its own after registration, and only a verdict whose `may_gate`
is true may unlock a number it shows.

What no outcome changes: the default rule; the need for a declared risk preference; the
availability of every rule; the world count, tail count, seed, world fingerprint and
discarded-world count beside every risk result; the absence of any corrected or "expected"
shortfall; the point-estimate requirement ledger shown for every rule; the order of rules in
the interface (fixed, never by token).

## What this experiment cannot show

- That any rule selects a team that plays differently. Nothing here observes a match outcome.
- That the additive carry-forward model is right. Truth in Part A is truth inside it.
- The size of selection optimism in football. Part A magnitudes belong to a declared
  Gaussian simulation without positional structure; Part B has one club, 34 and 30 nested
  matches, and no interval.
- Robustness to opponents, absences, form or role change: the worlds resample past matches.
- Anything about a world count, a tail count, a formation, a requirement set, a set of
  declared minima, a lock, an exclusion or a club that was not run. On Madrid only common
  multipliers of the three minima were run. A worst-world value is the largest of `W` draws
  and is not a parameter.
- Anything about the product's default progression-only risk request.
- That a held-out half is truth. A2 measures that gap in the simulation only, and the
  recovery of sums holds there by exchangeable matches, which a season is not. In Part B the
  halves share the xT surface and the declared minima, and the alternating split may mix
  selection with venue.
- A null here does not show the rules are useless; a positive token does not make a rule's
  selection correct. Repeated use of these snapshots is reuse, not validation.

## Reproducibility and tests

Artifact (`results.json`, aggregate only, under `results_maximum_bytes`): LF-normalised
SHA-256 of the three `protocol_files` and of every path in `source_paths`; the raw digests of
`manifest_path` as the data pin, with the Parquet file hashes recorded beside them; the protocol
commit derived from git; package versions; per snapshot the shipped `dataset_hash`, xT version,
feature fingerprints and structural counts; the oracle gate's counts and file hashes; every
seed; every table named above; every component token and every subject token with a
one-sentence reason. No player identifier, no player name, no per-player value, no selected
XI, no encoding `E`, no corpus identifier other than `results_allowed_identifiers`, no
wall-clock field.

Built and tested after registration, before the run (`PIPELINE.md` lists them): an
independent `itertools`/`Fraction` oracle for all six rules including level sets, discarded
worlds and the single-world invariant; rounding parity with the shipped solver; the M-05
bridge; row-order, candidate-order and world-order invariance; shared-world coherence;
snapshot parity of full-sample values and shipped worlds against `build_snapshot`; parity of
the Part B world discard with `world_losses`; antisymmetry of the fixed-selection gap;
exhaustive truth tables for every decision function (each input maps to exactly one token);
and the **planted gate** on seeds from `planted_seed_rule`, which evaluates BALANCE, the
reference arms and pseudo-rules only, never a declared-risk rule on a frozen cell:

- A1 on both geometries and both decision tiers: a planted benefit (`TRUTH_MIX`) classified
  `LESS_OPTIMISTIC_COST_BOUNDED`, a planted cost (`RANDOM_MIX`) classified
  `COSTS_TRUE_SHORTFALL`, an identical selection classified `INCONCLUSIVE`, each in
  `planted_minimum_correct` of `planted_seeds` seeds; the planted target of `TRUTH_MIX` is an
  identity of the arm (coin share times BALANCE's regret) and is checked as one, to
  `planted_identity_tolerance`; an own statistic set above the truth by
  `planted_reporting_shift_margin_multiple` margins classified `OWN_STATISTIC_NOT_OPTIMISTIC`,
  one set below it `NOT_ESTABLISHED`, and an identically zero one `INCONCLUSIVE`.
- A2: a planted sum gap recovered (`RECOVERS_SUM_GAP`), leaky halves caught
  (`NOT_ESTABLISHED`), and a held-out shortfall shifted by
  `planted_heldout_shift_margin_multiple` margins for one pseudo-rule making the diagnostic
  invalid.
- The split rule on `planted_split_corpora` synthetic corpora, as the structure check of the
  frozen run applies it (`planted_split_arms`).
- Decision arrays at the frozen shape (`planted_arrays`; `planted_array_subject_cells` cells,
  `planted_array_trials` trials, `planted_array_seeds` seeds): a true cost at the margin in
  every cell gives the cost token in at most the declared count; one cell at the margin gives
  the positive token in at most the declared count; zero cost and an optimism reduction of
  `planted_array_effect_standard_errors` standard errors in every cell give the positive token
  in at least the declared count; one cell at the margin plus that many standard errors gives
  the cost token in at least the declared count; and the percentile interval covers a planted
  mean in at least `planted_coverage_minimum` seeds.

The planted gate runs after registration and is stamped in a commit of its own before the
run; a failed requirement blocks the run and no constant moves. The frozen seed is used once,
by the root, plus one determinism re-run.

Committed before running. Results in `results.json`, interpretation in `analysis.md`. If
either contradicts this document, this document wins.
