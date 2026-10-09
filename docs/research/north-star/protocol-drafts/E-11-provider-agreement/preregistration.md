# E-11 — provider agreement on the 100 double-coded matches

> **DRAFT. Not frozen, not registered, not run.** Written by one designer during the north-star build and never adversarially reviewed or audited. No outcome named here has been computed. It becomes a protocol only when a reviewed version is committed under `experiments/preregistered/` in a single commit that precedes any run. Section and file references such as ROOT 2.5 point to [ROOT-DECISIONS.md](../../ROOT-DECISIONS.md); see [README](../../README.md) for the working notes it cites.

**Commit this plan and `config.json` before any cross-provider statistic is computed.
Nothing below may change once the first agreement value is observed.** This is a
prospective analysis plan on **previously inspected public data and newly cached licensed
data**, not a claim of untouched data collection. Every threshold, seed, list and gate
lives in `config.json`; a number that appears only in this prose is a defect. Deviations
are recorded in `analysis.md`, never silently adopted.

**Tier: LOCAL_LICENSED end to end.** Any quantity that touches StatsBomb inherits the
StatsBomb tier. No crosswalk file, no per-player row, no per-match row and no
StatsBomb-derived number enters Git in machine-readable form or reaches a hosted surface.
The published output is one aggregate research report with the StatsBomb logo.

## Claim and unchanged boundaries

StatsBomb and Pappalardo/Wyscout each coded the same 100 matches independently: World Cup
2018 (64) and Barcelona's La Liga 2017/18 matches (36, both Clásicos included). For each
quantity in `config.json` the claim under test is:

> Computed independently from each provider on the same matches, the two estimators of
> the same named quantity order the same players (or teams) alike; and, as a stronger
> claim, return the same values to within a frozen margin.

One verdict per quantity, level, pool and reader variant. Three purposes, kept separate:

| | Purpose | Output |
|---|---|---|
| (a) | Grade cross-provider comparability of every surviving construct and every E-09/E-10 candidate input | a verdict token per cell; the E-12 admission list |
| (b) | Build an identity crosswalk from shared team sheets, then measure how well a name-plus-nationality link reproduces it | a link verdict per tier set, with error rates |
| (c) | Quantify event-level definitional divergence | descriptive tables; **no verdict** |

**Not claimed.** That either provider is correct. Validity, reliability or decision utility
of any quantity (R4: agreement between two coders of one match is none of these). That
agreement on these 100 matches holds for StatsBomb 2015/16, for other competitions, or
for a later Wyscout specification. Anything about a named player or team. Anything about
transport across a club change (E-12).

**Unchanged.** No product code, `SPECS`, `CONSTRUCTS`, evidence gate, Parquet file,
`StatsBombProvider` or hosted endpoint changes under any outcome. E-07 and E-08 stay
closed. `"cross-provider pooling of raw values"` stays a registered invalid context
unless a later ADR, citing this experiment, says otherwise.

## Prior exposure, stated before the run

| Data | What has already been seen |
|---|---|
| Pappalardo five leagues 2017/18 | Inspected for every shipped construct (Stage 1, 1B, 1C, Player Lab, Match Lab, XI Lab). E-07 and E-08 used Spain and England rows, including March to May outcomes. The 36 Barcelona matches are ordinary Spain rows inside all of that |
| Pappalardo World Cup 2018 | Ingested; counts, periods and lineup minutes inspected. No construct value has been published from it |
| StatsBomb 2015/16 (four leagues) | Stage 1C computed within-provider reliability, confound share, baselines and La Liga level shifts (progression −32%, chance_creation +110%, provider and season confounded) |
| StatsBomb World Cup 2018 and La Liga 2017/18 | Cached 2026-10-09. Read for structure only: match list, lineup field names, team-sheet sizes (1,790 and 1,002 player-matches with a position spell), `metadata` version fields. **No event file in either folder was opened during design** |
| Design-time planning values | From a 40-match StatsBomb La Liga 2015/16 sample (not a double-coded match): 10.9% of Pass events are set-piece restarts; 3.8% of Shot events are free kicks and 0.95% penalties. ADR-0004 cites a published ~0.53 action-sequence similarity for the two providers on identical matches |

No same-match cross-provider statistic, no cross-provider player link rate and no event
pairing has been computed by anyone on this project. The open-play reader below was
chosen from the planning values in the last row, before outcomes.

## Data, cohorts and exclusions

| Subset | StatsBomb (LOCAL) | Pappalardo (PUBLIC) | Matches | StatsBomb `data_version` |
|---|---|---|---:|---|
| `world_cup` | `World_Cup_2018/` | `competition=World_Cup` | 64 | 1.0.2 (all 64) |
| `la_liga` | `La_Liga_2017_18/` | `competition=Spain`, Barcelona's matches | 36 | 1.1.0 (all 36; 7 lack the `xy_fidelity_version` field the other 29 carry). The E-12 corpus is 1.1.0 |

Structural expectations from the public side (counts only): 904 distinct players; 247 with
at least 270 double-coded minutes (219 outfield), 412 with at least 180; La Liga alone 94
with at least 180 and 23 with at least 270; 200 team-matches; about 2,790 player-matches.

Rules, all frozen:

1. **Regulation only.** Wyscout periods `1H`, `2H`; StatsBomb periods 1, 2. Extra time and
   shootouts (5 World Cup matches) are dropped on both sides, events and minutes.
2. **Minutes.** Each provider's own regulation minutes, capped at 90 per player-match.
   Wyscout: the shipped `lineups.minutes` rule, clipped to 90. StatsBomb: position spells
   with both ends clipped to 90, spells in periods above 2 dropped. A per-90 quantity
   divides by the same provider's minutes; minutes are themselves a compared quantity.
3. **Outfield only at the two player levels** (Wyscout role code is not `GK`). Team level
   keeps every row, including rows with no attributed player.
4. **Whole-match exclusions:** a match missing from either side, failing the match
   crosswalk, or missing an event or lineup file is dropped and counted by reason. No
   match is dropped for any reason that uses event content.
5. **Whole-player exclusions:** a player without a `VERIFIED_BY_TEAM_SHEET` link is absent
   from both player levels and counted. Missing is missing: never zero, never imputed.
6. No exclusion on team, position (beyond rule 3), age, minutes above the gate, or
   competition stage. No outlier removal.

## Identity: match, team and player

No event content enters any crosswalk. Linking on event agreement and then measuring
event agreement would be circular.

**Match crosswalk.** Within a subset, a StatsBomb match and a Wyscout match are linked iff
their calendar dates differ by at most `match_date_tolerance_days`, each side's two team
names pair off with token overlap above `match_team_token_overlap_strictly_above`
(`name_tokens` Jaccard, either orientation;
swapped home/away is recorded, not rejected), the candidate is unique in both directions,
and for `Regular`-duration matches the goals of each side agree. Team identity inside a
linked match follows from the same pairing. Gate: `minimum_crosswalked_matches` per
subset, else every cell is `INCONCLUSIVE (MATCH_CROSSWALK)`.

**Player crosswalk, `VERIFIED_BY_TEAM_SHEET`.** For each linked team-match the two sheets
list the same people. Pair them by name inside that closed pool only:

1. Name overlap = largest token Jaccard over name forms (StatsBomb legal name, nickname;
   Wyscout first plus last name, short name). A pair is taken when each is the other's
   unique maximum above `sheet_name_overlap_strictly_above`. Remove taken pairs and repeat
   until nothing changes.
2. A single leftover on each side with equal `started` flags is paired **by elimination**
   and marked so; elimination pairs are not verified.
3. Structural corroboration without names, per sheet: `started` flags equal; regulation
   minutes within `sheet_minutes_tolerance` (waived when StatsBomb records a dismissal:
   StatsBomb closes the spell, Wyscout does not); goalkeeper flags equal.
4. Across all matches the pairs must form a partial bijection. A player with two
   different partners loses every pair.

A link is verified iff it was name-paired in at least one sheet, never contradicted, and
passed step 3 in every sheet it appears in. Its evidence class is `ESTIMATED`
(`NAME_AND_CONTEXT`): there is still no birth date on the StatsBomb side. Reported
beside it: the share of verified links for which no team-mate shares any name token (a
swap is then impossible under this rule), and agreement of the two sheets on who was
cautioned. Gate: verified links must cover at least
`minimum_verified_player_match_coverage` of outfield player-matches on each side in each
subset, else both player levels are `INCONCLUSIVE (IDENTITY_COVERAGE)`.

**Wide link under test (the E-12 rule).** For every StatsBomb player holding a verified
link, link against **all** Pappalardo player records with no match, team or club context:

| Tier | Rule |
|---|---|
| A | identical full-name token set of at least `link_tier_a_minimum_tokens` tokens, and nationality agrees |
| B | one full-name token set contains the other with at least `link_tier_b_minimum_shared_tokens` shared tokens, and nationality agrees |

Nationality agrees when the normalised StatsBomb country equals the normalised Wyscout
birth area or passport area after `country_aliases_normalised`. A link needs a unique
candidate in both directions over the whole run. Tier sets evaluated: `[A]`, `[A, B]`.

## Measurements

**Reader variants (StatsBomb side).**

| Variant | Open-play pass | Shots | Role |
|---|---|---|---|
| `open_play` | Pass whose `pass.type` is absent, Recovery, Interception or Kick Off | by `shot.type` | **primary**; mirrors Wyscout, where restarts are a separate type and a kick-off is an ordinary pass |
| `as_shipped` | every Pass with a location and a player | every Shot | what `StatsBombProvider.actions` and Stage 1C computed; graded to price the uncorrected reader |

StatsBomb completion: no recorded outcome. Wyscout completion: `success` is true.

**Event families.** Wyscout rule on the neutral Parquet; StatsBomb rule on the research frame.

| Family | Wyscout | StatsBomb |
|---|---|---|
| open-play pass | `type` pass | variant rule above |
| corner / free-kick pass / throw-in / goal kick | `set_piece` subtypes `corner` / `free_kick`, `free_kick_cross` / `throw_in` / `goal_kick` | Pass with `pass.type` Corner / Free Kick / Throw-in / Goal Kick |
| open-play shot | `type` shot | Shot with `shot.type` Open Play |
| free-kick shot / penalty | `set_piece` subtype `free_kick_shot` / `penalty` | Shot with `shot.type` Free Kick / Penalty |
| non-penalty shot | open-play shot or free-kick shot | Shot whose type is not Penalty |
| key pass, shipped flag | tag 302 (`key_pass`) on a completed open-play pass | shot assist or goal assist on a completed open-play pass |
| key pass, assist-inclusive | `key_pass` or `assist` | same as above |
| defensive action | ground defending duel, or any row carrying the interception tag, or Clearance, or a foul in `wyscout_foul_subtypes`; each row once | Interception, Clearance, Foul Committed, Dribbled Past, Duel of type Tackle, or Pass of type Interception; each row once |

Block is left out of the StatsBomb defensive union: Wyscout records a block on the
attacker's event and names no blocker. Carries, pressures and receipts enter nothing.

**xT surfaces.** One fit rule on both sides (`fit_expected_threat`, 16×12, moves =
completed open-play passes, shots = open-play shots, turnovers = failed open-play pass
plus `dangerous_loss` / Miscontrol and Dispossessed).

| Surface | Fitted on | Why |
|---|---|---|
| `wyscout_reference` | Pappalardo Spain 2017/18 minus the 36 double-coded matches | league football of the lab season; the units being compared do not fit their own instrument |
| `statsbomb_reference` | StatsBomb La Liga 2015/16, 380 matches, same reader variant as the events it values | the surface the StatsBomb arm of E-12 uses for La Liga; 36 Barcelona matches cannot fit a league surface |

`regime` valuation (graded): each provider's events on its own reference. This is the
estimator pair E-12 runs. `common` valuation (reported, not graded): both providers'
events on `wyscout_reference`; the gap between the two valuations attributes
disagreement to the surface or to the event stream. Both surfaces are retrospective; no
temporal claim is made (this is not a decision at a date).

**Quantities.** Keys and formulas are `player_match_inputs`,
`aggregated_player_quantities` and `team_match_quantities` in `config.json`. Definitions:

| Input (per player-match; summed for teams) | Definition, identical on both sides after the family mapping |
|---|---|
| `open_play_passes_attempted`, `_completed` | counts |
| `positive_xt_gain_completed_passes` | sum of `max(0, xT(end) − xT(start))` over completed open-play passes |
| `xt_delta_key_passes` (and assist-inclusive) | sum of `xT(end) − xT(start)` over completed open-play passes carrying the flag |
| `completed_passes_from_half_space`, `_from_wide` | completed open-play passes whose start `y` lies in `half_space_bands`; below `wide_below` or above `wide_above` |
| `non_penalty_shots`, `open_play_shots` | counts |
| `shot_goal_angle_sum` | sum over non-penalty shots of the angle (radians) the goal mouth subtends at the shot location on a 105 × 68 m pitch |
| `shot_location_value_sum` | sum over non-penalty shots of the E-09 location-only conversion model, fitted on public data only; `INCONCLUSIVE (DEPENDENCY_ABSENT)` if that model is not in the tree |
| `defensive_actions`, `_opponent_half`, `defensive_action_x_sum` | count; count with start `x` at or above `opponent_half_x_minimum`; sum of start `x`, all in the acting team's attacking frame |
| team only: `final_third_entries` (+ left / centre / right) | completed open-play passes starting short of `final_third_x_fraction` and ending at or beyond it; lane by end `y` against `lane_y_edge_fractions`, `y = 0` the attacker's left |
| team only: `shots_in_penalty_area` | non-penalty shots inside the geometric penalty area |
| team only: `opponent_build_up_passes_per_high_defensive_action` | opponent open-play pass attempts starting at or short of `build_up_x_maximum` (their frame), divided by the team's defensive actions at or beyond `high_defensive_action_x_minimum` (own frame) |

A quantity conceded by a team is the opponent's quantity mirrored, so it is not graded twice.

**Levels.**

| Level | Unit | Value compared |
|---|---|---|
| `player_match` | verified outfield player in one match, at least `minimum_regulation_minutes_player_match` regulation minute on both sides | raw inputs (counts and sums), zeros included |
| `team_match` | team in one match | team sums and ratios |
| `aggregated_player` | verified outfield player over all his double-coded matches in the pool | per-90 rates and ratios of sums, under the exposure gate |

Exposure gate at the aggregated level: at least `exposure_minimum_minutes_primary`
regulation minutes **on each provider**; for the `la_liga` pool
`exposure_minimum_minutes_la_liga_subset`. Ratio quantities also need the frozen minimum
denominator on each side. A player below a gate is a hole for that quantity, not a zero.

## Models and baselines

No model is fitted to an outcome. The xT surfaces and the optional shot model are
instruments fitted on disjoint or public data and then held fixed. Controls:

| Control | Definition | Use |
|---|---|---|
| Positive | `open_play_passes_completed` at `team_match`, `pooled`, `open_play`; and `completed_passes_per_90` at `aggregated_player` | if either is not `COMPARABLE` or `COMPARABLE_IN_RANK_ONLY`, the crosswalk or the reader is suspect: every token is still reported and every E-12 admission is `EXCLUDED (POSITIVE_CONTROL)` |
| Permuted link | 20 fixed seeds; within each team, verified Wyscout partners are permuted with no fixed point (singleton teams unchanged and counted); computed at `aggregated_player`, `pooled`, `open_play` | an admitted quantity must have a Spearman point estimate strictly above all 20 permuted values; ties fail. An identity-link stress test, not a p-value |
| Reader contrast | `as_shipped` beside `open_play` | prices the uncorrected reader; never substitutes for the primary |
| Surface contrast | `common` beside `regime` | attribution only |

## Frozen selection and tuning procedure

None. No parameter is tuned and no quantity, level, pool, exposure, variant or threshold
is chosen after outcomes. Two data-dependent steps exist and are frozen: the two xT fits
(inputs above), and, for purpose (c) only, one clock offset per match-period, taken as
the grid value in `pair_offset_grid_seconds` that maximises the number of StatsBomb
open-play passes with a same-team Wyscout open-play pass within
`pair_offset_match_window_seconds`; ties go to the smallest absolute offset, then the
negative one. If a step fails (a surface does not converge), the affected cells are
`INCONCLUSIVE`; nothing is substituted.

## Evaluation and reporting

Differences are StatsBomb minus Wyscout. For every cell report, with `null` for anything
undefined:

- units; means and standard deviations per provider;
- Spearman correlation on average ranks (the order statistic);
- Lin's concordance correlation `2·s_xy / (s_x² + s_y² + (mean_x − mean_y)²)` with `1/n`
  moments (the level statistic), and ICC(2,1) absolute agreement as a cross-check; a gap
  above `ccc_icc_cross_check_tolerance` is flagged as a suspected code defect and does
  not alter a verdict;
- Bland–Altman bias, standard deviation of differences, limits `bias ± 1.96·sd`, relative
  bias `bias / ((mean_sb + mean_wy)/2)`, scale ratio `sd_sb / sd_wy`, slope of difference
  on pair mean;
- for count inputs at `player_match`: share of exactly equal pairs.

**Resampling.** `bootstrap_replicates` replicates, fixed `seed`, percentile intervals at
`interval_quantiles`. Matches are resampled with replacement inside each subset (64 and 36
draws), so both teams and all players of a match stay together and the subset mix is fixed.
At the two player levels each replicate also draws an independent multinomial weight per
player (match × player "pigeonhole" resampling), because players recur across matches and
are the units whose ordering is at issue. One replicate id is one match-weight vector
and one player-weight vector, shared by every quantity, both providers, both variants and
every pool. Aggregates, exposure gates and denominators are recomputed inside each
replicate; a player who falls below a gate there is a hole there. A replicate with fewer
than `replicate_minimum_unit_share_of_gate` of the unit gate, or a constant vector, is
invalid and counted. The match-only scheme is reported beside it as a sensitivity.
These are intervals of this resampling scheme, conditional on the 100 matches, the
crosswalk and the fixed surfaces; they are not universal confidence statements.

**Pools.** `pooled` (primary), `world_cup`, `la_liga`. The two subsets differ in football
(national teams against one club's league season), in team mix (32 teams against one team
and its 19 opponents) and in StatsBomb specification version, so both are always shown
and their difference with its interval is reported; it is not tested.

**Descriptive only, never a verdict:** exposure sensitivities at
`exposure_sensitivity_minutes`; unit counts along `exposure_curve_minutes`; the `common`
valuation; the match-only bootstrap; agreement by Wyscout broad position; every table of
purpose (c).

**Purpose (c), event level.** Per family: events per team-match on each side, the pooled
count ratio with a match-cluster interval, and StatsBomb Pass and Shot events by type.
For `pair_families`: one-to-one greedy pairing of same-team events within the family's
time tolerance after the clock offset and (where set) its distance tolerance in metres,
by ascending time gap, then distance, then event order. Report paired share of each
side, player agreement among pairs (verified links only), completion and goal agreement,
key-pass flag overlap, median and 90th percentile start and end displacement, and the
xT delta difference on paired completed passes under the common surface. Families that
exist on one side only are counted, not paired.

**Purpose (b).** Per tier set and subset, on StatsBomb players holding a verified link:
recall (the wide link returns the verified partner), false-link rate (a returned link
differs from the verified partner), no-link rate, and the **absent-partner false-link
rate** (the verified partner is removed from the pool; any link returned is false by
construction). Wilson 95% intervals. Also by presence of a StatsBomb nickname.

## Decision rule

**Per cell** (quantity × level × pool × reader variant, `regime` valuation, primary
exposure). `L` and `U` are the interval bounds. Evaluate in order; the first match wins.

| # | Condition | Verdict |
|---|---|---|
| 1 | An experiment gate failed (match crosswalk, missing data, identity coverage at player levels, surface for xT quantities, absent dependency), or units are below `minimum_units`, or fewer than `minimum_units_nonzero_on_both_providers` units are non-zero on both sides, or either side is constant, or valid replicates are below `minimum_valid_replicate_share`, or Spearman or its interval is undefined | `INCONCLUSIVE` with one reason code; nothing was compared |
| 2 | `L(Spearman) ≥ spearman_lower_bound_minimum` and `L(CCC) ≥ ccc_lower_bound_minimum` and the whole relative-bias interval lies within `± relative_bias_margin` | `COMPARABLE` |
| 3 | `L(Spearman) ≥ spearman_lower_bound_minimum` | `COMPARABLE_IN_RANK_ONLY` |
| 4 | `U(Spearman) < spearman_lower_bound_minimum` | `NOT_COMPARABLE`: the data exclude the required agreement |
| 5 | otherwise | `NOT_ESTABLISHED`: compared; criterion not met; the interval contains the threshold |

An undefined CCC or relative bias fails row 2 and falls through to row 3. NaN is never a pass.

**Wide link, per tier set.**

| Condition | Verdict |
|---|---|
| fewer than `link_minimum_verified_players` verified players | `INCONCLUSIVE` |
| upper bound of false-link rate ≤ `link_false_link_rate_upper_maximum` and upper bound of absent-partner false-link rate ≤ `link_absent_partner_false_link_rate_upper_maximum` and lower bound of recall ≥ `link_recall_lower_minimum` | `LINK_USABLE` |
| otherwise | `LINK_NOT_ESTABLISHED` |

**Why these numbers, written before any outcome.**

- *0.80 on the lower bound of the order statistic.* Two measurements of the same matches
  correlate at `ρ_AB = sqrt(rel_A · rel_B)`; a cross-provider, cross-season correlation
  is the true persistence times that factor. A true two-season persistence of 0.75
  gives an observed 0.60 at `ρ_AB = 0.80` and 0.45 at `ρ_AB = 0.60`. The transfer-design
  planning table (Fisher algebra on census counts, no outcome data) puts E-12's smallest
  detectable retention ratio at about 0.73 for a stayer persistence of 0.60 and about
  0.57 for 0.45. Below 0.80 the provider change alone leaves E-12 able to detect little
  short of collapse. The house `NUMBER` grade asks 0.70 of split-half reliability across
  *different* matches; two coders of the *same* events must clear more. Koo and Li (2016) place
  0.75 to 0.90 in their "good" band, judged on the interval (REPORTED; not re-read for
  this protocol).
- *The bound, not the point.* With about 219 gated outfield players a Fisher interval
  puts the lower bound above 0.80 for a true value near 0.85 or more (planning algebra;
  the resampling scheme used here is wider).
- *Exposure 270.* Coding error that is independent across matches averages out, so
  agreement at 270 minutes understates agreement at E-12's 900. The gate is therefore
  conservative for E-12; per-player systematic coder differences do not average and are
  what remains.
- *±10% relative bias.* Stage 1C called `width` (+10%) ROBUST and `half_space_share`
  (−14%) ROBUST_WITH_SHIFT without writing the boundary down. It is written down here.
- *Link rates.* A false-link share `e` multiplies an arm's correlation by `(1 − e)` and
  false links fall in the mover arm; 2% biases E-12's retention ratio by about −0.02,
  an order below its margin. If a quarter of StatsBomb 2015/16 players are absent from
  the 2017/18 roster and 60% are linked (census planning values), an absent-partner
  false-link rate of 5% yields `0.25 × 0.05 / 0.60 ≈ 2%` false links.
- *Unit gates* sit at roughly 70 to 90% of the structural counts above, so a failed
  crosswalk trips them and the design does not.

Under a calibrated interval a cell exactly at the threshold is admitted about 2.5% of the
time; the planted boundary scenario must bound that at 10% before the run. Error is not
controlled across cells and no cell borrows from another.

## Consequence of each verdict, fixed now

**E-12 admission, per quantity,** from the `aggregated_player` level, `open_play` reader,
`regime` valuation:

| `pooled` verdict | `la_liga` verdict (exposure 180) | Controls | E-12 |
|---|---|---|---|
| `COMPARABLE` | anything but `NOT_COMPARABLE` | positive control holds; strictly above all 20 permuted links | `ADMITTED_LEVEL_AND_ORDER`: may enter the confirmatory family; raw cross-provider contrasts may be reported as secondary |
| `COMPARABLE_IN_RANK_ONLY` | anything but `NOT_COMPARABLE` | same | `ADMITTED_ORDER_ONLY`: within provider × league × role rank-normal values only; no raw contrast and no level-shift estimand |
| either of the above | `NOT_COMPARABLE` | — | `EXCLUDED (LA_LIGA_SUBSET_CONTRADICTS)`: league football under the E-12 specification version disagrees |
| either of the above | any | a control fails | `EXCLUDED (PERMUTED_LINK_CONTROL or POSITIVE_CONTROL)` |
| `NOT_ESTABLISHED`, `NOT_COMPARABLE`, `INCONCLUSIVE` | any | — | `EXCLUDED (VERDICT)`: not computed in E-12 at all, not as a secondary, not as a description |

E-12 must read StatsBomb through the reader, the surface rule and the wide-link function
graded here, unchanged and hash-pinned. A quantity admitted under `open_play` is not
admitted under the unfiltered adapter. If `chance_creation` and its assist-inclusive
variant are both admitted, E-12 uses `chance_creation`.

**Wide link.** E-12 uses the widest tier set graded `LINK_USABLE` and cites its measured
rates. If none is, E-12's cross-provider arm needs an independent confirmation of every
mover link or reports `INCONCLUSIVE`.

**Everything else.**

| Outcome | Consequence |
|---|---|
| any | No hosted surface, endpoint, gate or shipped number changes. No StatsBomb-derived number is served or committed as data |
| `COMPARABLE` at all three levels in both subsets | The quantity is *eligible* for a new ADR proposing to widen `comparable_across` (ADR-0004's reversal clause). Nothing widens automatically |
| `COMPARABLE_IN_RANK_ONLY` | Permitted sentence: "orders players consistently across the two providers on double-coded matches". Raw pooling stays invalid |
| `NOT_COMPARABLE` on a shipped construct | A dated caveat is requested on its Stage 1C external label: within-provider validity replicated; same-match agreement did not. The label itself is not edited |
| `NOT_ESTABLISHED`, `INCONCLUSIVE` | No registry or wording change. Published as such |
| E-09 candidate or E-10 descriptor not admitted | It may still pass its own Wyscout lifecycle; its external status reads "untested across providers" and it stays out of any cross-provider study |
| team-level quantity | Gates any future cross-provider team study by the same table, read at `team_match` |

A verdict here promotes nothing. It decides only what a later cross-provider study may use.

## What this experiment cannot show

- That a quantity means what its name implies. Two providers can agree on a number that
  measures something else.
- Agreement for StatsBomb 2015/16. E-12 uses a different season; only the 36 La Liga
  matches share its specification version, and they are one team's matches.
- League football at the aggregated level: about nine in ten gated players come from the
  World Cup. The La Liga check can veto; it cannot confirm.
- That the crosswalk is error-free. It is name-based inside a closed pool with
  structural corroboration and no birth date.
- The false-link rate of E-12's link on its own population. The players here are all
  present in the Wyscout roster; the absent-partner stress approximates the missing case
  and does not reproduce E-12's name-form mix.
- Any xT surface pair other than the La Liga pair.
- Anything about carries, pressures or receipts, which only one provider records.
- Anything about a role-specific provider effect beyond the descriptive table.

## Reproducibility and tests

Local artifact `results.local.json` (aggregate only): protocol, config and source hashes on
LF-normalised bytes; raw data file digests; content hashes of the frames used; surface
hashes; package versions; seeds; digests of the match and player crosswalks (digests and
counts only, rebuilt deterministically at run time); every statistic above. Committed:
this protocol, `config.json`, `analysis.md` with the StatsBomb logo and attribution, and
a `results.json` holding provenance and verdict tokens with **no** statistic. Every
artifact stays under 512 KB; none holds a player, team or match identifier or name.

The pipeline is written and tested on synthetic data only. Before any real outcome is
read, the frozen decision rule must classify planted corpora at the rates in
`acceptance_scenarios` (planted agreement, planted order-only agreement, planted null,
planted moderate agreement, a planted boundary case that bounds the false-admission
rate, and a planted sample-gate failure), and the runner refuses to execute without that
stamp and without a commit that contains this protocol and config unchanged.

Tests must cover: match crosswalk (swapped orientation, a pair of teams meeting twice,
date tolerance, goal disagreement); team-sheet crosswalk (shared surnames, mononyms,
elimination, minutes conflict, dismissal waiver, cross-match contradiction); the wide
link (tiers, nationality aliases, ambiguity, absent partner); regulation clipping;
reader variants against a hand-built match; the family mapping; channel bands equal to
`features/spec.py`; surface parity with the shipped fit rule; each statistic against an
independent closed-form or brute-force oracle; ties and constant vectors; shared weights
across quantities and providers; holes that stay holes; row-order invariance; the
decision rule on every boundary; fail-closed on NaN; aggregate-only output keys, size
and licence-guard patterns; refusal to run before the protocol commit.

---

*Committed before running. Local results in `results.local.json`, interpretation in
`analysis.md`. If either contradicts this document, this document wins.*
