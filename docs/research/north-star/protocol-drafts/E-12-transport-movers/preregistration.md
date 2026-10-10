# E-12 — do player rates survive a club change? Movers against stayers

> **DRAFT. Not frozen, not registered, not run.** Written by one designer during the north-star build and never adversarially reviewed or audited. No outcome named here has been computed. It becomes a protocol only when a reviewed version is committed under `experiments/preregistered/` in a single commit that precedes any run. Section and file references such as ROOT 2.5 point to [ROOT-DECISIONS.md](../../ROOT-DECISIONS.md); see [README](../../README.md) for the working notes it cites.

**Commit this plan and `config.json` before any persistence, reliability or forecast-error
value is computed for any cohort below. Nothing may change once the first such value is
observed.** This is a prospective analysis plan on **previously inspected historical data**,
not a claim of untouched data collection. Every threshold, seed, window, list, grid and gate
lives in `config.json`; a number that appears only in this prose is a defect. Deviations are
recorded in `analysis.md`, never silently adopted. E-11 must be registered and executed first.

**Two arms, two tiers.** `cross_corpus` (StatsBomb 2015/16 to Pappalardo 2017/18) is
LOCAL_LICENSED end to end: no number, interval, count, coefficient or identifier from it
enters Git in machine-readable form or reaches a hosted surface; its verdict tokens may be
shown as labels. `public_winter` (Pappalardo 2017/18 only) is PUBLIC and is the only arm
that may ever put a number on a hosted page.

## Claim and unchanged boundaries

Claim under test, one verdict per construct and contrast:

> Among players who are used at their next club, the ordering of players on the construct
> persists across a change of club to within a frozen margin of its persistence among
> players who did not change club over the same interval, and movers' standing does not
> shift against stayers of the same prior standing by more than a frozen margin.

Stayers cross the same provider change, the same unobserved 2016/17 season and the same
two years of ageing, so the stayer persistence is the yardstick and the estimand is a
mover-to-stayer contrast, never an absolute persistence figure. "Survives" is an
equivalence claim with a margin; failing to find a difference is not it.

Primary endpoint: `progression` (per 90), contrast `within_league`. That is the quantity
Transfer Lab injects. `progression_per_action`, `chance_creation`, `half_space_share` and
`width` are secondary: each gets its own verdict, and a verdict on one says nothing about
another.

**Not claimed.** Transfer success, selection or playing time. A causal effect of the
destination club. League strength. A forecast for any individual. The fraction of a rate one
player keeps. Performance of an unplayed XI. Anything for a player who was not used at the
destination: every estimate is conditional on clearing the destination minutes floor, which
selects movers who succeeded (attrition table below). Anything about a named player or club.

**Unchanged.** No product code, `SPECS`, `CONSTRUCTS`, evidence gate (900 minutes outfield;
1,800 minutes for Wyscout `chance_creation`), Parquet file, provider adapter or shipped
number changes under any outcome. No transport function, shrinkage coefficient or context
coefficient enters the product under any outcome: Transfer Lab keeps injecting the
candidate's historical rate and states the break-even carry-over fraction. E-07 and E-08
stay closed. `galactico/validation/transport.py` (E-07, lineup-sum forecast) is a different
study; verdict tokens here avoid its word.

## Prior exposure, stated before the run

| Data | What has already been seen |
|---|---|
| Pappalardo five leagues 2017/18 | Inspected for every shipped construct: Stage 1 and 1B (split-half reliability by alternating matches, confound audits, baselines, all five leagues), Stage 1C (estimator v2, four leagues), Player Lab, Match Lab and XI Lab (Spain). E-02 used Italy, with England, Germany and France as secondary. E-07 and E-08 used Spain and England team-opening rows, including March-to-May outcomes |
| StatsBomb 2015/16, four leagues | E-01 (exploratory). Stage 1C: within-provider reliability, confound share, baselines, La Liga level shifts (`progression` -32%, `chance_creation` +110%, provider and season confounded), the `chance_creation` minutes curve |
| E-11 | Its verdicts, link rates and surfaces will be known before E-12 runs. By design: E-12 conditions on them and no E-12 constant depends on them |
| Structure, counted for this protocol | Lineups, rosters and match lists only (`mover-census.md`; design script `count_cohorts.py`): arm sizes under the rules below, club overlap, position mix, the age gap between movers and stayers (about 1.4 years at the median), minutes distributions, the 124 in-season movers and their appearance dates |
| Planning values | One blog source reports year-to-year VAEP persistence of about 0.77 for same-club players against 0.69 for same-league movers (numbers read from charts; unverified). All power figures below are algebra or synthetic simulation |

No player has ever been linked across the two corpora for an outcome statistic. No
cross-season or cross-provider player-level association, no before/after-date persistence
within a season, no mover-against-stayer contrast and no half-against-half correlation
inside any cohort defined here has been computed by anyone on this project. Gates were set
from the algebra in "Why these numbers" with the structural counts in view; that is
disclosed, and the counts are printed beside the gates.

## Data, identity, cohorts and exclusions

### Corpora and the E-11 dependency

Origin: StatsBomb open data 2015/16, La Liga, Premier League, Serie A, Ligue 1 (380, 380,
380, 377 matches). Destination: Pappalardo 2017/18, Spain, England, Italy, France, Germany
(Germany can only be a destination). Both sides are read through the reader variant, the
xT fit rule and the two reference surfaces that E-11 graded, imported unchanged and
hash-pinned (`dependency_*` keys). E-12 implements no second reader.

Admission per construct is read from E-11 (`aggregated_player` level, `pooled`, `open_play`
reader, `regime` valuation). What E-12 does under each E-11 outcome:

| E-11 admission | Underlying E-11 verdicts | `cross_corpus` arm | `public_winter` arm |
|---|---|---|---|
| `ADMITTED_LEVEL_AND_ORDER` | pooled `COMPARABLE`, La Liga not `NOT_COMPARABLE`, controls hold | Enters. Analysed on within-cell normal scores only, exactly as the next row: no raw cross-provider value is formed or reported by E-12 under any admission | unaffected (one provider) |
| `ADMITTED_ORDER_ONLY` | pooled `COMPARABLE_IN_RANK_ONLY`, same conditions | Enters, same analysis. The standing shift `D` below is a difference of within-cell normal scores, not a raw level shift, so it is inside what order-only admission permits | unaffected |
| `EXCLUDED (VERDICT)` | pooled `NOT_ESTABLISHED`, `NOT_COMPARABLE` or `INCONCLUSIVE` | `NOT_ADMITTED`. No outcome statistic is computed for it in this arm, not as a secondary, not as a stratifier, not as a description | unaffected |
| `EXCLUDED (LA_LIGA_SUBSET_CONTRADICTS, PERMUTED_LINK_CONTROL, POSITIVE_CONTROL)` | as named | `NOT_ADMITTED`, same rule | unaffected |
| E-11 results absent, stale or hash-mismatched | - | the runner refuses to start; no verdict is written | not run either: one command, one protocol |

If `chance_creation` and its assist-inclusive variant are both admitted, E-12 uses
`chance_creation`; the variant never enters.

### The identity link: a declared research link, not an identification

StatsBomb lineups carry no birth date, so `resolve_player` accepts nobody on this pairing
(0 of 2,176). The link below is declared, tiered, measured on E-11's double-coded matches
and stress-tested. Its evidence class is `ESTIMATED` in both tiers, so every cross-corpus
statistic is `ESTIMATED` at most.

| Tier | Rule | Error evidence |
|---|---|---|
| V | The StatsBomb player holds a `VERIFIED_BY_TEAM_SHEET` pair in E-11's crosswalk (same match, same team sheet, name-paired, structurally corroborated, never contradicted). StatsBomb ids are one id space, so the pair links his 2015/16 rows | E-11's coverage, swap-impossible share and cautioned-agreement table |
| A | E-11's wide link, tier set `[A]`, called exactly as E-11 calls it: identical full-name token set of at least two tokens, nationality agrees (StatsBomb country against Wyscout birth or passport area), one candidate in each direction over all StatsBomb 2015/16 players with a position spell and all 3,603 Wyscout player records | E-11's measured false-link rate, absent-partner false-link rate and recall for `[A]`, with Wilson bounds |
| excluded | Everything else: tier B containment, name fragments, club context, any link without nationality agreement, any ambiguous or twice-claimed candidate | - |

Tier V wins. A StatsBomb player whose tier V and tier A partners differ, or a Wyscout
player claimed by two StatsBomb players, loses every link and is counted (`tier_conflict`).
If E-11 does not grade `[A]` as `LINK_USABLE`, the arm runs on tier V alone and the sample
gates decide (`link_fallback_when_wide_link_not_usable`); tier B never enters, whatever
E-11 says about `[A, B]`.

**Measured error and its use.** With `e_fl` and `e_ap` the upper Wilson bounds of E-11's
false-link and absent-partner false-link rates for `[A]` (pooled), `N0` the StatsBomb
outfield players at the origin floor, `NV` and `NA` those linked by tier V and by tier A
only:

    F = e_fl * NA + e_ap * max(0, N0 - NV - NA * (1 - e_fl))
    e_worst(contrast) = min(F / n_movers(contrast), false_link_share_cap)

A false link pairs unrelated players, who almost never share a club, so it is counted as a
mover and multiplies the mover correlation by `(1 - e)`. All of `F` is assumed to fall in
the mover arm being judged. That biases toward loss, so the loss verdict must survive
division by `(1 - e_worst)`; the survival verdict is not adjusted, because the bias runs
against it. A false link inside the stayer arm would bias toward survival; it needs a
different person with the same full name and nationality at the same club two years on,
and the `verified_links_only` sensitivity is the check.

**Stress test, in the manner of E-08.** For each of `identity_placebo_seeds`, permute the
whole destination side (values, halves) among linked players inside
`identity_placebo_pool` (cohort, destination league, position), with a SHA-256-derived
seed per pool, sorted ids and no dependence on row order; singleton pools and unchanged
players are counted. The real correlation must be strictly above all 20 permuted values in
both arms of a contrast; ties fail. This is an identity-link stress test, not an
exchangeable permutation test and not a p-value. A planted-contamination curve
(`contamination_fractions`: that share of mover links replaced by another eligible player
of the same destination cell, `contamination_draws` draws) is reported beside the
algebraic adjustment.

**No crosswalk is persisted.** Links, pairs and every row that holds a provider player id
exist in process memory only and are rebuilt deterministically on each run. Nothing that
holds a StatsBomb id, a linked pair or a per-player linked value is written to any file,
tracked or not. Only digests and counts of the crosswalk reach the local artifact.

### Club crosswalk

Club key = `normalise_name(provider team name)`, then `club_aliases` (12 entries: the two
providers spell 12 of the 66 shared clubs differently), then the league. No provider team
id enters the key. Before any action is read the runner asserts 66 shared keys (Spain 17,
England 17, Italy 16, France 16), 14 origin-only, 14 destination-only in the four overlap
leagues, 18 in Germany, and a one-to-one mapping; a mismatch aborts with exit code 3 and
no verdict. Five shared clubs spent 2016/17 in the second tier
(`second_tier_2016_17_clubs`); "same club" for their players spans a relegation and a
promotion.

### Cross-corpus cohorts

Unit: a linked outfield player (not a goalkeeper under either provider's position).
Main club in a season = the club with most of his regulation minutes; a tie excludes him.
Every value uses his main-club matches only. Origin floor: 900 minutes at the origin main
club. Destination floor: the registered Wyscout floor of the construct at the destination
main club (900; 1,800 for `chance_creation`). Cohorts are therefore construct-specific.

| Cohort | Definition | Role |
|---|---|---|
| `S` stayer | same club key in both seasons and exactly one club in each season | control |
| `M_w` within-league mover | different club, same league | primary mover arm (`within_league`) |
| `M_x` league-changer | different league, destination in the four overlap leagues | secondary (`league_change`) |
| `M_b` Bundesliga destination | destination league is Germany | secondary (`bundesliga_destination`); expected `INCONCLUSIVE` |
| second club within a season, same main club | same main club in both seasons but a second club in either | excluded from every contrast; counted |
| second club within a season, mover | a mover with a second club in either season | kept, main-club values; dropped in `single_club_movers` |

Role-continuity strata, declared before outcomes: `ROLE_SAME` when the StatsBomb modal
broad position (by spell minutes, `statsbomb_broad_position_rule`) equals the Wyscout role
code; `ROLE_CHANGED` otherwise. That flag mixes redeployment with provider labelling and
cannot separate them. The primary analysis keeps both; `role_same` is a sensitivity.
Position for strata, matching and reporting is the Wyscout role (one public label per
player). Further declared flags: origin club absent from the 2017/18 corpus; destination
club absent from the 2015/16 corpus; stayer at a second-tier-2016/17 club; link tier; age
band on `age_reference_date` (Wyscout birth date); destination minutes band.

Structural counts under these rules, tier A alone, shipped lineup minutes (counts only; no
outcome was read; realised counts will differ by a few because the E-11 reader caps
regulation minutes at 90 and tier V adds links):

| Origin / destination floor | `S` | `M_w` | `M_x` | `M_b` | excluded, same main club | origin clubs `S` / `M_w` / `M_x` |
|---|---:|---:|---:|---:|---:|---|
| 900 / 900 | 337 | 193 | 72 | 12 | 17 | 66 / 72 / 44 |
| 900 / 1,800 (`chance_creation`) | 237 | 118 | 32 | <5 | 5 | 63 / 63 / 26 |
| 900 / 900, players also present in the double-coded competitions (upper bound on tier V) | 143 | 66 | 36 | <5 | 5 | 37 / 36 / 29 |

At 900 / 900: position mix `S` 148 DF, 133 MF, 56 FW; `M_w` 74, 74, 45; `M_x` 31, 26, 15.
42 movers have a second club within a season; 54 left a club absent from the 2017/18
corpus; 43 `M_w` or `M_x` movers joined a club absent from 2015/16; 24 stayers and 23
movers are `ROLE_CHANGED`; 11 stayers are at second-tier-2016/17 clubs. Of 1,228 StatsBomb
outfield players at the origin floor, 864 hold a tier A link, 822 of those appear in
2017/18 lineups and 631 clear the 900-minute destination floor.

### Public arm cohorts (Pappalardo 2017/18 only; provider-declared ids)

| Cohort | Definition |
|---|---|
| `P_M` winter mover | lineup rows for exactly two clubs in the five leagues; last appearance for the first club after `public_winter_last_old_club_appearance_after`; first appearance for the second on or after `public_winter_first_new_club_appearance_from`; every first-club match earlier than every second-club match (the three loan-and-recall players are excluded); outfield; side floor met on both sides. Before = first-club matches, after = second-club matches. The move is bracketed by two observed appearances, not by a transfer date the data does not hold |
| `P_S` same club | exactly one club; before = matches dated earlier than `public_same_club_split_date`, after = the rest; outfield; side floor met on both sides |

Side floor = half the construct's registered Wyscout floor (450; 900 for
`chance_creation`), so the two sides together meet the registered floor. This is a research
cohort with different semantics, not a relaxed individual gate, and it certifies no
individual. Exact structural counts: 124 two-club players; 29 `P_M` at 450 on each side
(20 within a league, 9 across; 8 DF, 12 MF, 9 FW), 51 at 270, 7 at 900; 1,097 `P_S` at 450,
592 at 900. **The mover comparison in this arm cannot meet its gate (29 against a
requirement of 62 at this control size) and is expected to return `INCONCLUSIVE` for all
five constructs. That is known now and is the registered outcome, not a disappointment to
be repaired by lowering a floor.** The arm is registered so that the gate, not judgement
after the fact, is what withholds the number.

### Exclusions

Goalkeepers; players below a floor (a hole, never a zero); main-club ties; units in a
standardisation cell with fewer than `minimum_cell_units` units; units with an undefined
value (no denominator events). No exclusion on team, age, nationality, league or club
strength, and no outlier removal. Every exclusion is counted by reason.

## Measurements

**Inputs.** Per player-match sums from E-11's reader (`input_columns`): regulation minutes,
completed open-play passes, positive xT gain over completed open-play passes, xT delta
over key passes, completed passes from the half-space bands and from wide. StatsBomb
through `open_play` (set-piece restarts excluded), never the unfiltered adapter.

**Surfaces.** The xT recipe is the shipped Player Lab recipe (`xt_recipe`: completed
open-play passes as moves, open-play shots, failed passes and dangerous losses as
turnovers), as frozen in E-11. Exactly two
surfaces are used, hash-equal to E-11's: `statsbomb_reference` (La Liga 2015/16) for all
four origin leagues and `wyscout_reference` (Spain 2017/18 without the 36 double-coded
matches) for all five destination leagues and for the public arm. These are the only
instruments whose cross-provider agreement E-11 graded; one fixed surface per provider is
the E-07 / E-08 device. Both are retrospective; no decision at a date is claimed.

**Value.** `scale * sum(numerator) / sum(denominator)` over the unit's matches for the club
in question (`constructs`). A zero denominator gives a missing value.

**Standardisation.** Cell = provider-season x league x broad position (StatsBomb modal
position on the origin side, Wyscout role on the destination side). The reference
population of a cell is every outfield player of that corpus-league at the floor, linked or
not. Within a cell: average ranks `r` of finite values, `u = (r - normal_score_offset) / n`
(the unit's prior percentile on the origin side), `z` = standard normal quantile of `u`.
Level shifts between providers and between league surfaces are removed by construction;
raw values are never compared across cells. Public arm cells: league x position x side.

**Halves.** A unit's matches for the club, sorted by date then match id, alternate A, B.
Half values are standardised within the same cells among units with at least
`half_floor_fraction_of_floor` of the floor in that half. A unit short of it is a hole for
reliability only.

**Club levels.** `level_origin` = minutes-weighted mean origin `z` of the other
floor-eligible outfield players at the unit's origin club (leave-one-out, at least
`club_level_minimum_other_players` others). `level_destination_prior` = the same mean over
all floor-eligible outfield players at the destination club in the origin season; missing
when that club is not in the origin corpus. `own_deviation = z_pre - level_origin`.

## Models and baselines

**Estimands, per construct and contrast (`g` = arm; all on normal scores).**

| Symbol | Definition |
|---|---|
| `rho_g` | Pearson correlation of `(z_pre, z_post)` over units of arm `g` (a rank-based statistic: both are within-cell normal scores). Plain Spearman is reported beside the point value |
| `tau` | `rho_M / rho_S`, the ordering-transport ratio. **The decision statistic** |
| `dz` | `atanh(rho_S) - atanh(rho_M)`, reported with its resampling interval and with the analytic check `1.6449 * sqrt(1/(n_S - 3) + 1/(n_M - 3))` |
| `rel_g,s` | Spearman-Brown `2r / (1 + r)` of the half-A / half-B correlation, inside arm `g`, season `s`, on the same players |
| `rho*_g`, `tau*` | `rho_g / sqrt(rel_g,pre * rel_g,post)` and `rho*_M / rho*_S`. Reported **beside** the raw value, never instead of it; missing when the root is not above `attenuation_minimum` |
| `D` | Standing shift: mean of `z_post - z_pre` over movers minus the mean over stayers reweighted to the movers' mix of position x prior-percentile bin (`prior_percentile_bin_edges`). This is the regression-to-the-mean control: movers selected on a high prior value regress whether or not anything failed to transport, and so do stayers of the same prior standing. Movers in a cell with no stayer are dropped and counted |

The ratio, not the Fisher-z difference, carries the decision because the margin has to mean
the same thing at every stayer level: a fixed `dz` of 0.25 is `tau` 0.90 when `rho_S` is
0.85 and 0.69 when it is 0.60 (algebra).

Two artefacts are the size of the effect sought and both push `tau` down: unequal
reliability (movers have fewer minutes) and false links. Hence the asymmetric rule below:
a survival verdict needs raw and disattenuated lower bounds to agree, and a loss verdict
needs raw and disattenuated upper bounds to agree after the false-link adjustment.

**Transport rules for movers (a forecast comparison in normal-score units).**

| Rule | Forecast of a mover's `z_post` | Reading |
|---|---|---|
| `R0` | 0 | his history carries nothing |
| `R1_raw` | `z_pre` | literal carry-forward of the standardised rate (what an injection assumes) |
| `R1` | `a + alpha * own_deviation + beta * level_origin` | carry-forward with stayer persistence: own part and origin-team part both persist |
| `R2` | `a + alpha * own_deviation` | own deviation from the origin team only; the team level stays behind |
| `R3` | `a + alpha * own_deviation + beta * level_destination_prior` | own deviation plus the destination team's prior level |

**What is fitted on whom.** `a`, `alpha`, `beta` are one ordinary least-squares fit of
stayers' `z_post` on `[1, own_deviation, level_origin]`. Nothing is fitted on movers. Stayers
are the only units for whom "how much of an own deviation and of a team level persists
across this provider change and these two years, with no club change" is observed; movers
are the only units for whom the three rules disagree. So every rule is an out-of-sample
forecast for every mover, no cross-fitting or tuning is needed, and the comparison among
`R1`, `R2`, `R3` isolates which component travels. Stated limit: applying `beta` to the
destination level assumes a mover absorbs it as an incumbent does; that is the hypothesis
`R3` tests, not an assumption of the report. All rules are scored on identical rows
(movers with every term defined); the rest are counted. No hyperparameter, no feature
search, no other covariate.

**Controls.**

| Control | Definition | Use |
|---|---|---|
| Stayer yardstick | `rho_S` | denominator of `tau`; its floor decides whether a ratio means anything |
| Regression to the mean | `D` above | enters the survival verdict |
| Identity placebos | 20 permuted-link values per arm | enters the survival verdict |
| False-link adjustment | `e_worst` | enters the loss verdict |
| Pseudo-movers | `pseudo_mover_draws` random relabellings of stayers as movers of the mover arm's size | reported: the centre and the 0.05 / 0.95 quantiles of `tau`; a centre away from 1 indicts the pipeline |
| Composition match | stayers reweighted to the movers' mix of position x age band x destination-minutes band | reported: `tau` under those weights |

## Frozen selection and tuning procedure

None. No parameter is tuned and no cohort, floor, cell, construct, contrast, surface, margin
or threshold is chosen after outcomes. The only data-dependent fits are E-11's two surfaces
(inherited, hash-pinned) and the three stayer coefficients above. If a step fails, the
affected verdict follows the decision table; nothing is substituted.

## Evaluation and reporting

**Resampling.** `bootstrap_replicates` worlds, fixed `seed`. One world is one multinomial
weight vector over origin clubs (public arm: the club on the before side), shared by every
construct, contrast, statistic and sensitivity; a unit's weight is its club's weight, so
team-mates and both arms of a club move together. Reliabilities, matched weights and the
stayer coefficients are recomputed inside each world; cells and normal scores are not
(intervals are conditional on the reference populations, the links, the two surfaces and
this resampling scheme, and are not universal confidence statements). A world in which an
arm's weight is below `replicate_minimum_arm_weight` or a variance is zero is invalid for
that statistic and counted. Intervals are `np.quantile` (linear) of valid worlds: the
decision uses `decision_quantiles` (0.05 and 0.95, so each bound is a one-sided 5% bound);
`reported_quantiles` are printed beside them. No Fisher-z interval on a stepped-up
correlation is used anywhere; the step-up happens inside each world.

**Attrition table (always reported; the selection the estimand conditions on).** From the
StatsBomb outfield players at the origin floor: linked by tier, unlinked by E-11 outcome,
origin club shared or absent; among the linked: absent from 2017/18 lineups, by cohort,
and by destination minutes at each of `attrition_destination_minutes_steps`; the share of
each cohort clearing the destination floor; and, per admitted construct and cohort, the
mean origin `z` of those who cleared the floor minus those who did not, with its interval.
Public arm: the same from the 124 two-club players.

**Sensitivities (reported for the primary contrast, never a verdict;** `sensitivities`,
each needing `sensitivity_minimum_movers`): `role_same`; `single_club_movers`;
`origin_club_survived`; `stayers_top_flight_throughout`; `verified_links_only`;
`all_movers_pooled`; `composition_matched`; `player_bootstrap` (units resampled within arm
and position instead of clubs); floor pairs in `sensitivity_floor_pairs` with cells rebuilt.

**Where numbers go.** `results.local.json` (gitignored, under `local_output_root`): every
cross-corpus statistic. `results.json` (committed): provenance, admissions, gate booleans
and verdict tokens for both arms, plus one block `public_winter` (providers
`["pappalardo"]`, computed by a stage that reads no StatsBomb file) holding the public
arm's aggregates. Outside that block and the config echo `results.json` holds no number.
`analysis.md`: the aggregate research report, with the
StatsBomb logo and attribution; counts below `small_count_suppression_below` are printed
as "<5"; no statistic on fewer than `minimum_units_for_any_statistic` units.

**Same-club split persistence (public, descriptive, own gate).** `rho` over `P_S`, raw and
disattenuated, with its interval. Status `REPORTED` when `P_S` has at least
`same_club_split_minimum_units` units and `minimum_clubs_per_arm` clubs, else
`INCONCLUSIVE`. It is not a transport estimate and is reported whatever the mover gate says.

## Sample gates and decision rule

**Gates, per construct and contrast (all must hold).**

| Gate | Rule | Reason code |
|---|---|---|
| stayers | `n_S >= minimum_stayers` | `MIN_STAYERS` |
| movers | `n_M >= minimum_movers` | `MIN_MOVERS` |
| planning power | `1/(n_S - 3) + 1/(n_M - 3) <= maximum_inverse_n_sum` | `INVERSE_N_SUM` |
| clubs | distinct clusters in each arm `>= minimum_clubs_per_arm` | `MIN_STAYER_CLUBS`, `MIN_MOVER_CLUBS` |

**Decision table.** `L(.)`, `U(.)` are the 0.05 and 0.95 quantiles; `m` =
`transport_ratio_margin`; `e` = `e_worst` (0 in the public arm). Evaluate in order; the
first match wins. A NaN never passes a row.

| # | Condition | Verdict (reason) |
|---|---|---|
| 1 | `cross_corpus` and the construct is not admitted by E-11 | `NOT_ADMITTED` (E-11's reason) |
| 2 | a gate fails | `INCONCLUSIVE` (first failing gate). Nothing was compared: no outcome statistic is computed for this construct and contrast |
| 3 | valid worlds for `rho_S` or `tau` below `minimum_valid_replicate_share` | `NOT_ESTABLISHED` (`INTERVAL_UNAVAILABLE`) |
| 4 | `L(rho_S) < stayer_correlation_floor` | `NOT_ESTABLISHED` (`STAYER_PERSISTENCE_BELOW_FLOOR`): the provider change and the two years leave nothing to transport |
| 5 | the interval of `tau*` or of `D` is unavailable | `NOT_ESTABLISHED` (`CORRECTION_UNAVAILABLE`) |
| 6 | `max(U(tau), U(tau*)) / (1 - e) < m` | `REDUCED_BEYOND_MARGIN` |
| 7 | `min(L(tau), L(tau*)) >= m` and `-standing_shift_margin <= L(D)` and `U(D) <= standing_shift_margin` and both arms strictly above all identity placebos | `TRANSPORTS_WITHIN_MARGIN` |
| 8 | `min(L(tau), L(tau*)) >= m` and the `D` condition fails | `NOT_ESTABLISHED` (`STANDING_SHIFT_OUTSIDE_MARGIN`) |
| 9 | `min(L(tau), L(tau*)) >= m` and the placebo condition fails | `NOT_ESTABLISHED` (`IDENTITY_STRESS_NOT_PASSED`) |
| 10 | `min(U(tau), U(tau*)) < m` | `NOT_ESTABLISHED` (`LOSS_NOT_ROBUST_TO_CORRECTIONS`) |
| 11 | `max(L(tau), L(tau*)) >= m` | `NOT_ESTABLISHED` (`RAW_AND_DISATTENUATED_DISAGREE`) |
| 12 | otherwise | `NOT_ESTABLISHED` (`INTERVAL_SPANS_MARGIN`) |

Vocabulary, exhaustive: `NOT_ADMITTED`, `INCONCLUSIVE` (a frozen sample gate failed and
nothing was compared), `TRANSPORTS_WITHIN_MARGIN`, `REDUCED_BEYOND_MARGIN`,
`NOT_ESTABLISHED` (compared; neither criterion met; a published null, not evidence of
absence). Rows 6 and 7 cannot both hold. Every reachable state maps to exactly one token.
The positive token says "transports" because E-09 already uses "survives" for its own
claim; in prose both words mean the sentence in "Claim" and nothing wider.

**Transport-rule verdict (secondary; own vocabulary; no product effect).** Computed only
when the contrast was compared and at least `transport_rule_minimum_movers` movers have
every term; otherwise `RULES_NOT_EVALUATED`. With `d(a, b)` the paired mean squared-error
difference `loss(a) - loss(b)` over movers: `R2` beats `R1` iff `U(d(R2, R1)) < 0`;
likewise `R3`. Neither: `NO_RULE_PREFERRED_OVER_CARRY_FORWARD`. Only `R2`:
`OWN_DEVIATION_PREFERRED`. Only `R3`: `DESTINATION_LEVEL_PREFERRED`. Both: `U(d(R3, R2)) < 0`
gives `DESTINATION_LEVEL_PREFERRED`, `L(d(R3, R2)) > 0` gives `OWN_DEVIATION_PREFERRED`,
else `CONTEXT_RULES_NOT_SEPARATED`. `R0` and `R1_raw` are reported, never selected.

**Why these numbers, written before any outcome.**

- *Margin 0.80 on `tau`.* The one published stayer-against-mover contrast is a ratio near
  0.90 (unverified). A margin of 0.80 lets an effect of that size pass given enough data and
  refuses "half is lost". It is the lower bound, not the point, that must clear it.
- *Floor 0.30 on `L(rho_S)`.* Below it the denominator of `tau` is within a few resampling
  standard errors of zero at these sizes and a ratio is not an estimate of anything.
- *Standing-shift margin 0.25.* A quarter of a cell standard deviation; at the cell median
  that is ten percentile points.
- *Gates.* Under a normal approximation, `SE(tau) = tau * sqrt(v * ((1 - rho^2)/rho)^2 *
  (1/(n_S - 3) + 1/(n_M - 3)))` with `v = planning_variance_allowance`. The survival row has
  planning power `planning_power` at `tau = 1` and `rho_S = planning_stayer_correlation` iff
  `SE(tau) <= (1 - m) / (1.6449 + 0.8416)`, which is `maximum_inverse_n_sum` (0.0179). The
  two minimum counts keep either arm from carrying the other. Against the structural counts:
  `within_league` clears for all five constructs; `league_change` sits on its gate (72
  against a requirement of 71 at `n_S` = 337) and fails for `chance_creation` (32);
  `bundesliga_destination` fails (12); the public mover arm fails (29 against 62).
- *One-sided 5% bounds.* Two one-sided tests; the same convention as the house lower-bound
  rule for reliability.
- *Multiplicity.* One primary endpoint. Each secondary verdict governs only its own label.
  Error is not controlled across constructs; nobody may count verdicts.

**What the rule can and cannot detect (synthetic simulation of this rule, 400 panels per
cell, planning sizes 340 stayers and 190 movers, equal reliability 0.88, no false links;
not football data).** Share of panels returning the directional verdict:

| Observed stayer correlation | `tau` = 1.0, survives | `tau` = 0.9, survives | `tau` = 0.7, reduced | `tau` = 0.6, reduced | `tau` = 0.5, reduced |
|---:|---:|---:|---:|---:|---:|
| 0.75 | 0.96 | 0.45 | 0.39 | 0.85 | 0.98 |
| 0.62 | 0.68 | 0.26 | 0.24 | 0.59 | - |
| 0.48 | 0.38 | 0.16 | 0.18 | 0.36 | - |

At the margin itself (`tau` = 0.80) each directional verdict appears in about 0.05 of
panels. With `e_worst` = 0.15 the loss verdict falls to 0.72 at `tau` = 0.5 and 0.24 at 0.6:
an unverifiable link is paid for in the ability to call a loss. At `chance_creation` sizes
(240 / 120) survival at `tau` = 1 is 0.81; at league-changer sizes (340 / 70) it is 0.53.
**The experiment can show survival when transport is close to complete and stayers persist
at about 0.6 or more, and can show a loss of about 40% or more. A true ratio near 0.9, the
only published figure, most often returns `NOT_ESTABLISHED`. That is stated now so that a
null is not later read as a finding or repaired.**

## Consequence of each verdict, fixed now

Governing verdict for a Transfer Lab candidate and requirement: the construct's
`within_league` verdict for a same-league candidate; its `league_change` verdict for a
cross-league candidate whose origin league is one of the four overlap leagues (beside the
existing "not strength-adjusted" label); for a candidate whose origin league is Germany the
fixed label `NO_ORIGIN_SEASON` (the corpus has no season with a Bundesliga origin). Before
the run every label is `PENDING`. Exact copy is `product_copy` in `config.json`. Registry
mapping (`product_outcomes`): `TRANSPORTS_WITHIN_MARGIN` is `ESTABLISHED` with limits;
`REDUCED_BEYOND_MARGIN` and `NOT_ESTABLISHED` are `NOT_ESTABLISHED`; `INCONCLUSIVE` and
`NOT_ADMITTED` are `INCONCLUSIVE`. One record per construct and contrast; the three
`cross_corpus` contrasts are LOCAL records (labels, never gates, no figure), `public_winter`
is a PUBLIC record. A page may show less than this table allows, never more.

| Verdict | Label and banner | Carried-forward value | Break-even carry-over fraction: sentence added after the fixed lead |
|---|---|---|---|
| `TRANSPORTS_WITHIN_MARGIN` | "tested, ordering persists within margin"; banner states an aggregate finding about ordering, two seasons, two providers, not a forecast for this player | `HEURISTIC`, unchanged | "Ordering is not level: that finding does not say this fraction will be kept." |
| `REDUCED_BEYOND_MARGIN` | "tested, reduced beyond margin"; banner states that carrying the rate forward unchanged is an assumption the result argues against | `HEURISTIC`, unchanged | "A conclusion that needs nearly all of his rate to carry over rests on an assumption that finding argues against." |
| `NOT_ESTABLISHED` | "tested, not established" | `HEURISTIC`, unchanged | "Nothing measured here says how much persists." |
| `INCONCLUSIVE` | "not tested (sample gate)" | `HEURISTIC`, unchanged | same, naming the gate |
| `NOT_ADMITTED` | "not tested (providers not comparable)" | `HEURISTIC`, unchanged | same, naming E-11 |

Fixed under every verdict:

- The carried-forward value stays `HEURISTIC` with the sentence `product_copy.carried_value`.
  No verdict upgrades it, applies a shrinkage, changes an injected number, or changes how
  candidates are grouped or ordered.
- A `cross_corpus` verdict is at most a label that links to the research note with the
  StatsBomb attribution. It never unlocks a number-bearing panel and never parameterises a
  served computation. No `cross_corpus` number, interval, count or coefficient is served or
  committed in machine-readable form, and no sentence attached to it contains a number.
- The break-even carry-over fraction keeps its fixed lead: it predicts nothing and states
  how much would have to persist. It is never compared with an E-12 ratio (an ordering
  ratio across a population is not the fraction of a rate one player keeps), never coloured
  or worded as safe or unsafe, and never accompanied by "likely", "expected" or "projected".
  E-12 supplies no reference value for that display under any verdict: no tick, no band.
- **May the public arm ever show a number?** Three cases, fixed now. (1) Structural counts:
  always, with `product_copy.public_movers_inconclusive`. (2) Same-club split persistence:
  when its status is `REPORTED`, with `product_copy.public_same_club_split`, which says
  these players did not change club. (3) A mover ratio: only under a public-arm verdict
  other than `INCONCLUSIVE`, which the exact count (29) rules out under this registration.
  A larger public same-provider mover sample needs its own registration; this gate is not
  re-floored.
- The transport-rule verdict changes nothing in the product. It decides what a later,
  separately registered study would test.

## What this experiment cannot show

- That a quantity means what its name implies, or that a move works. Persistence of
  ordering is neither validity nor decision utility.
- Anything for players who were not used at the destination, left the five leagues, or
  could not be linked. About 46% of 2015/16 regulars are not linked and back at the floor
  in 2017/18; the estimate is conditional on surviving.
- A provider effect that differs between movers and stayers. Stayers absorb the provider
  change only if it does not interact with moving or with role mix; E-11 tests part of
  that, on other matches.
- What happened in 2016/17, how long a mover had been at the new club, whether a "stayer"
  was loaned out in between, or whether the manager changed.
- A redeployment inside a broad position. Wyscout has no per-match position.
- League strength. League-changers are compared on within-league standings; a shift there
  mixes transport with the two leagues' populations.
- The identity error on its own population. E-11 measures the link on players who appear
  in double-coded matches; the absent-partner rate approximates the rest.
- A within-provider, within-season mover effect at any usable precision (public arm).
- Any surface pair other than E-11's two; any estimator other than completed open-play
  passes; carries, duels, shots and defending.
- A ratio near 0.9 from a ratio of 1.0 (power table).

## Reproducibility and tests

Artifacts: protocol, config and source hashes on LF-normalised bytes; E-11 result hashes,
surface hashes and crosswalk digests asserted equal to E-11's; raw data digests and frame
content hashes; package versions; seeds; the calibration stamp; every statistic above, in
the file its tier allows. Aggregate only: no player, club or match identifier or name, no
row per player; every file under 512 KB.

The pipeline is written and tested on synthetic data only. Before any real outcome is
read, the frozen decision rule must classify planted panels at the rates in
`calibration_scenarios`: planted equivalence (survival at least 0.85), a planted null at
the margin (each directional verdict at most 0.10), a planted loss (reduction at least
0.90), a planted reliability artefact and planted false links (reduction at most 0.02, and
at least 0.04 when the adjustment is switched off, so the guard is shown to act), absent
stayer persistence, a planted gate failure in which no statistic may be computed, a planted
standing shift, and three planted transport-rule worlds; and it must recover the planted
ratio within `calibration_recovery_tolerance`. The runner refuses to execute without that
stamp, without E-11's results, or without a commit that holds this protocol and config
unchanged.

Tests must cover: club keys and the crosswalk assertion; tier precedence and conflicts;
main club, ties and second-club cases; every cohort boundary; floors per construct; cells
and normal scores (ties, minimum cell, holes); halves; leave-one-out levels (own value
excluded); each statistic against an independent brute-force oracle; shared worlds across
constructs and contrasts; row-order invariance; placebo pools, counts and seed derivation;
the false-link formula; matched weights; stayer-only fitting (changing any mover outcome
leaves every coefficient unchanged); identical rows across rules; every decision-table row
and boundary; fail-closed on NaN; no statistic computed behind a failed gate or for a
construct that is not admitted; the public stage running with no StatsBomb path present;
aggregate-only keys, size and licence-guard patterns; no number outside the config echo in
`results.json`; nothing written outside the declared output files; refusal to run before
the protocol commit or twice.

---

*Committed before running. Local results in `results.local.json`, tokens and the public
arm in `results.json`, interpretation in `analysis.md`. If any of them contradicts this
document, this document wins.*

![StatsBomb](../../../../assets/statsbomb/statsbomb-logo.png)

Data source: StatsBomb. The structural counts above are formed from StatsBomb Open Data
(lineups only) and from Pappalardo et al. (2019), Scientific Data 6:236, CC BY 4.0. This
document is published with the StatsBomb logo (`docs/assets/statsbomb/statsbomb-logo.png`)
under clause 1.4 of the StatsBomb Public Data User Agreement. The conclusions are not the
opinions or analytical insights of StatsBomb.
