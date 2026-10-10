# E-11 — provider agreement on the 100 double-coded matches

> **DRAFT. Not frozen, not registered, not run.** Written by one designer during the north-star build, attacked once by three reviewers (statistics, football data, constitution), revised, audited branch by branch (found not ready), revised again, audited a second time (found not ready, but close) and revised a third time under root rulings of 9 October 2026. This third revision was audited on 9 October 2026 and found not ready: three blockers, not yet applied (see the README two folders up). No outcome named here has been computed. It becomes a protocol only when the root commits a reviewed version under `experiments/preregistered/` in a single commit that precedes any run. References such as ROOT 2.5 point to [ROOT-DECISIONS.md](../../ROOT-DECISIONS.md); see [README](../../README.md) for the working notes it cites.

<img src="../../../../assets/statsbomb/statsbomb-logo.png" alt="StatsBomb" width="170">

Data source: **StatsBomb** open data, read locally under the StatsBomb Public Data User
Agreement. This analysis is formed from StatsBomb data and carries the StatsBomb logo as
clause 1.4 of that agreement requires. It is not the opinion or analytical insight of
StatsBomb. No StatsBomb data, no identifier and no row for a player, a team or a match is in
this repository; the figures below are aggregates. Second source: Pappalardo et al. (2019),
*A public data set of spatio-temporal match events in soccer competitions*, Scientific Data
6:236, CC BY 4.0; figshare collection 4415000, articles Events
(doi:10.6084/m9.figshare.7770599), Matches (doi:10.6084/m9.figshare.7770428), Players and
Teams.

**Commit this plan, `config.json` and `PIPELINE.md` before any cross-provider statistic is
computed. Nothing in the three may change once the first agreement value is observed.**
This is a prospective analysis plan on **previously inspected public data and licensed data
that this project has already parsed** (next section), not a claim of untouched data. Every
threshold, seed, list and gate lives in `config.json` and is named here by its key; a number
that appears only in this prose is a defect. Deviations are recorded in `analysis.md`,
never silently adopted.

**Tier: LOCAL_LICENSED end to end.** Any quantity that touches StatsBomb inherits the
StatsBomb tier. No crosswalk file, per-player row, per-match row or StatsBomb-derived number
enters Git in machine-readable form or reaches a hosted surface. A sha256 digest of a
provider's files is not data and not a table derived from data: it discloses nothing, it is
what pins the inputs of a preregistered experiment, and the three folder digests of
`sb_folder_digests` are therefore committed in `config.json` (root ruling, 9 October 2026).

## Claim and unchanged boundaries

StatsBomb and Pappalardo/Wyscout each coded the same matches independently: World Cup 2018
and Barcelona's La Liga 2017/18 matches (`subsets[*].expected_matches`). For each quantity
in `config.json` the claim under test is:

> Computed independently from each provider on the same matches, the two estimators of the
> same named quantity order the same units alike, players being compared with players of the
> same role; and, as a stronger claim, they agree in level on average: mean relative bias
> inside `± relative_bias_margin` of the mean of the two provider means, and concordance at
> or above `ccc_lower_bound_minimum`.

The stronger claim bounds the average level and the scatter relative to the between-unit
spread. It does not bound the difference for any one player or team, and concordance is
computed across roles, so differences in level between roles raise it.

One verdict per quantity, level, pool and reader variant. Three purposes, kept separate:

| | Purpose | Output |
|---|---|---|
| (a) | Grade cross-provider comparability of every shipped construct and of the candidate inputs defined in `config.json` | a verdict token per cell; the E-12 admission list |
| (b) | Pair players from shared team sheets, then measure how well a name-plus-nationality link reproduces the pairing | a link verdict per tier set, with error rates |
| (c) | Quantify event-level definitional divergence | descriptive tables; **no verdict** |

**Not claimed.** That either provider is correct. Any ordering of the two providers: no
sentence says one is more accurate, more complete or closer to the truth; differences are
reported signed, with the direction named. Validity, reliability or decision utility of any
quantity (R4). That agreement on these matches holds for StatsBomb 2015/16, for other
competitions, or for a later Wyscout specification. Anything about a named player or team.
Anything about transport across a club change (E-12).

**Unchanged.** No number, gate, computation, `SPECS`, `CONSTRUCTS`, Parquet file or
`StatsBombProvider` changes under any outcome. No entry of
`MetricDefinition.comparable_across` or of `ConstructSpec.invalid_contexts` changes. E-07
and E-08 stay closed. Registration adds one E-11 record per subject in
`registry_cell_subjects` and `registry_link_subjects` to `galactico/domain/verdicts.py`.
They are served as labels by `/api/evidence/verdicts` and listed on the planning pages, as
ADR-0018 permits; `may_gate` is false for every one under every token.

**Definitions belong to this file.** A token of this experiment applies to the definition
hashed in this config. It is a token for an E-09 candidate or an E-10 descriptor only if
that protocol, when registered, imports the definition unchanged; otherwise that
candidate's cross-provider status is "not graded". `shot_location_value` is not graded
here: its model is E-09's, and E-09 is not registered.

## Prior exposure, stated before the run

| Data | What has already been seen |
|---|---|
| Pappalardo five leagues 2017/18 | Inspected for every shipped construct (Stage 1, 1B, 1C, Player Lab, Match Lab, XI Lab). E-07 and E-08 used Spain and England rows, including March to May outcomes. Barcelona's matches are ordinary Spain rows inside all of that |
| Pappalardo World Cup 2018 | Ingested; counts, periods and lineup minutes inspected. No construct value has been published from it |
| StatsBomb 2015/16 (four leagues) | Stage 1C computed within-provider reliability, confound share, baselines and La Liga level shifts (progression −32%, chance_creation +110%, provider and season confounded) |
| StatsBomb World Cup 2018 and La Liga 2017/18 | Fetched 2026-10-09 by a script that was not committed. Both folders were then ingested through the shipped adapter: `data/licensed/parquet/statsbomb/` holds an action frame and a lineup frame for each, so every event file in both folders has been parsed by this project through the `as_shipped` reader. No statistic computed from those action frames is recorded in the repository or the working notes. The match index was read (match list, dates, team names, `metadata` versions) and the lineup files and frames were read for field names, team-sheet sizes, spell structure, player ids, names and countries. For `sb_folder_digests` the files of both folders and of the reference folder were hashed as bytes; the match indexes were read for match ids only. The category names of event kind, pass type, shot type and duel type in those three folders were compared with the four frozen lists, names only, no counts: none lies outside a list. `scripts/fetch_statsbomb_double_coded.py`, written for this protocol and committed with it, reproduces that fetch; on these folders it has been run in `--check` mode only, which downloaded nothing and hashed the same files as bytes again (its fetch mode was exercised on invented files in a temporary directory, with the network disabled). The pipeline never opens `sb_forbidden_roots` |
| Which Barcelona matches are double-coded | Pappalardo holds 38 Barcelona league matches and StatsBomb 36. The first public-side counts written for this protocol were stated for 36 matches; the step that picked them out of 38 was not saved and its method is not recorded. The counts below come from the saved script, which takes all 38 |
| The wide-link rule | The mover census ran name-plus-nationality tiers, with eleven of the twelve aliases, on all 2,176 StatsBomb 2015/16 players against the same 3,603 Wyscout records: its tier A (legal name; the census also used the Wyscout middle name) linked 1,272 (58.5%); link, ambiguity and unresolved shares, the split by nickname, and position, goalkeeper-flag and implied-age agreement per tier were read. No two records on either roster share a full-name token set. The E-12 design then counted how many StatsBomb players present in both the double-coded lineups and 2015/16 obtain a tier A link; the count is in the working notes and was read again during this revision. `link_recall_lower_minimum` and the tier definitions were set with these in view. The twelfth alias (Iran) was added for this protocol; its source is not recorded. No team-sheet pairing existed, so no recall against a paired partner, no false-link rate and no absent-partner rate has been seen |
| Design-time planning values | From a 40-match StatsBomb La Liga 2015/16 sample: 10.9% of Pass events are set-piece restarts; 3.8% of Shot events are free kicks and 0.95% penalties. ADR-0004 cites a published ~0.53 action-sequence similarity for the two providers on identical matches |
| Review-time counts, one provider at a time | Penalty-area definitions on leagues that are not double-coded: Wyscout England 2017/18, 8,801 non-penalty shots, 5,139 in the provider-drawn box against 4,990 in a 16.5 m box on a 105 × 68 m mapping; StatsBomb Premier League 2015/16, 9,908 shots, 5,848 against 6,123. StatsBomb lineups of the double-coded folders: 213 outfield players at 270 minutes or more, 57 of them at exactly 270; 79 La Liga outfield players at 180 or more, 57 at exactly 180; the nickname is null on 1,554 of 2,886 World Cup and 256 of 1,296 La Liga lineup entries; spell structure in extra time, stoppage time and after dismissals; team-sheet field names, card types and periods, spell start and end reasons, starters per team under the `started` rule, rows with zero regulation minutes and competition stages. Pappalardo World Cup alone: match durations, lineup sizes, substitutions per team-match, dismissals, role codes, missing birth and passport areas, event subtypes in the shootout period; team names of both competitions. The category names of event kind, pass type, shot type and duel type in the frozen lists were listed from the 2015/16 La Liga folder, without counts. The audit read the shipped Pappalardo adapter's set-piece subtype map and the public event-name table against the `wy_*` lists. The public-side counts of units that clear each ratio's minimum denominator are in the paragraph below. The matches of the public Spain frame were counted for `xt_wy_reference_expected_matches` |

Structural expectations from the public side alone (saved script, all 38 Barcelona
matches, an upper bound for the 36): 852 distinct outfield players; 218 with at least 270
minutes (DF 100, MD 78, FW 40), 62 of them at exactly 270; World Cup alone 198 (94, 70,
34); La Liga alone 86 with at least 180 (46, 27, 13), 64 of them at exactly 180, and 22
with at least 270; 204 team-matches; 2,599 outfield player-matches of at least one minute.
Minimum denominators, same script and side, players at their pool's gate: at least 30
completed open-play passes, all 218 pooled, all 198 World Cup, 79 of the 86 La Liga (83
with 30 attempted); at least ten open-play shots, 35 pooled, 24 World Cup, 11 La Liga.
Team-matches with at least five open-play shots: 197 of 204 (122 of 128 World Cup, 75 of
76 La Liga); every team-match has at least ten final-third entries. A share of open-play
shots per player over a denominator of ten cannot reach `minimum_units` in any pool, and
it is not an aggregated quantity of this experiment (see "What this experiment cannot
show").

No agreement value for any quantity, no event pairing, no team-sheet pairing and no
false-link rate has been computed on the double-coded matches. A link count of the rule
under test has been, as the table says: **the recall criterion of the link verdict is not
blind; its false-link criteria are.** The alias list is frozen as it stands; a country it
misses is a no-link, never a new alias. The open-play reader below was chosen from the
planning values, before outcomes.

## Data, cohorts and exclusions

| Subset | StatsBomb (LOCAL) | Pappalardo (PUBLIC) | StatsBomb `data_version` |
|---|---|---|---|
| `world_cup` | `World_Cup_2018/` | `competition=World_Cup` | 1.0.2 (all files) |
| `la_liga` | `La_Liga_2017_18/` | `competition=Spain`, the matches that pass the match crosswalk | 1.1.0 (all files; 7 lack the `xy_fidelity_version` field the others carry). The E-12 corpus is 1.1.0 |

Rules, all frozen:

1. **Regulation only.** `wy_regulation_periods`, `sb_regulation_periods`. Extra time and
   shootouts are dropped on both sides, events and minutes.
2. **Minutes.** Each provider's own regulation minutes; a player-match is never credited
   more than `regulation_minutes_cap`. Wyscout: the shipped `lineups.minutes` rule, clipped.
   StatsBomb: position spells with both ends clipped, spells in later periods dropped.
   StatsBomb minutes exclude recorded off-pitch gaps (Player Off, Player On); Wyscout
   minutes do not. A per-90 quantity divides by the same provider's minutes; minutes are
   themselves a compared quantity.
3. **Outfield only at the two player levels** (Wyscout role code is not
   `wy_goalkeeper_position`). Team level keeps every row, including rows with no
   attributed player.
4. **Whole-match exclusions.** A listed match whose event or lineup file is absent on
   either side, or that fails the match crosswalk, is dropped and counted by reason. No
   match is dropped for a reason that uses event content.
5. **Closed vocabulary.** Three StatsBomb folders are read: the two of the table above and
   the reference folder `xt_sb_reference_folder`. If any of the three holds an event kind,
   a pass type among Pass events, a shot type among Shot events or a duel type among Duel
   events (a missing type is null) outside `sb_known_event_kinds`, `sb_known_pass_types`,
   `sb_known_shot_types`, `sb_known_duel_types`, the run stops before any statistic: every
   cell and every link verdict is `INCONCLUSIVE (UNKNOWN_VOCABULARY)`. `preflight` prints
   the names seen, without counts, one provider at a time, and may be run before the commit.
6. **Whole-player exclusions.** A player without a `PAIRED_BY_TEAM_SHEET` link is absent
   from both player levels and counted. Missing is missing: never zero, never imputed.
7. **Locations.** The two unit squares are different pitch drawings; every location
   threshold is applied to each provider's own drawing and no registration between them is
   attempted. A Wyscout row whose start is in `wy_location_sentinels` is excluded from
   every location quantity; one whose end is a sentinel has no end location and is excluded
   from xT sums, final-third and box entries, lanes and end displacement. A StatsBomb row
   without a start location is excluded from every location quantity. Such rows stay in
   plain counts and are counted by reason.
8. No exclusion on team, position (beyond rule 3), age, minutes above the gate, or
   competition stage. No outlier removal.

## Identity: match, team and player

No event content enters any crosswalk. Linking on event agreement and then measuring event
agreement would be circular.

**Match crosswalk.** Within a subset, a StatsBomb match and a Wyscout match are linked iff
their calendar dates differ by at most `match_date_tolerance_days`, each side's two team
names pair off with `name_tokens` Jaccard overlap above
`match_team_token_overlap_strictly_above` (either orientation; swapped home and away is
recorded, not rejected), the candidate is unique in both directions, and for durations in
`match_require_goal_agreement_durations` the goals of each side agree. Team identity inside
a linked match follows from the same pairing. It runs on real data only inside `execute`.
Gates, per subset: fewer than `minimum_crosswalked_matches` listed matches with all files
present gives `INCONCLUSIVE (DATA_MISSING)` for every cell and every link verdict; fewer
than that number linked gives `INCONCLUSIVE (MATCH_CROSSWALK)`, likewise.

**Order of the gates.** `DATA_MISSING`, `UNKNOWN_VOCABULARY` (rule 5) and
`MATCH_CROSSWALK` are evaluated in that order, the order of
`inconclusive_reason_precedence`: each of the three is evaluated only if every gate before
it in `inconclusive_reason_precedence` passed, and the first that fails stops the run. No
crosswalk is built on missing files or an unknown vocabulary, and every cell and every
link verdict takes that reason. `IDENTITY_COVERAGE` and `XT_SURFACE` are evaluated only if
those three passed, each whatever the other returns, and neither stops the run: the first
applies to the two player levels and to every link verdict, the second to the xT
quantities at every level, and a cell to which both apply takes the first. A gate that
fails in either subset fails for every pool.

**Player crosswalk, `PAIRED_BY_TEAM_SHEET`.** For each linked team-match the two sheets
list the same people. Rows with zero regulation minutes under rule 2 are removed on each
sheet first, each provider by its own minutes, and counted. Pairing is by name inside that
closed pool only:

1. Name overlap = largest token Jaccard over name forms (StatsBomb legal name, nickname;
   Wyscout first plus last name, short name). A pair is taken when each is the other's
   unique maximum above `sheet_name_overlap_strictly_above`; taken pairs are removed and
   the step repeats until nothing changes. A taken pair is *name-paired* only if the two
   rows share at least one token that no other row of either sheet, as filtered above,
   contains in any name form (`sheet_require_distinguishing_token`); otherwise it is `NAME_WEAK`.
2. A single leftover on each side with equal `started` flags is paired by elimination
   (`ELIMINATION_ONLY`).
3. Structural corroboration without names, per sheet: `started` flags equal; the absolute
   difference of the two regulation minutes is at most `sheet_minutes_tolerance` (a
   difference exactly at the tolerance passes), waived under `sheet_minutes_waiver` (either
   provider records a dismissal, or StatsBomb ends a spell with a permanent player-off
   reason); goalkeeper flags equal.
4. Across all matches the pairs of every kind must form a partial bijection. A player
   with two different partners loses every pair (`BIJECTION_CONFLICT`).

A link is `PAIRED_BY_TEAM_SHEET` iff it was name-paired in at least one sheet, never
contradicted (step 4), and passed step 3 in at least `sheet_structure_pass_share_minimum`
of the sheets it appears in (below that share: `STRUCTURE_CONFLICT`). The sheets a link
appears in are all the linked team-matches in which both of its players hold a sheet row,
as filtered above; step 3 is evaluated on every one of them, whether or not steps 1 and 2
paired the two there. A sheet in which a
paired link fails step 3 removes that one player-match, and nothing else of the player
(`sheet_structure_conflict_scope`), from both player levels, and it is counted; the link
stands. Evidence class `ESTIMATED` (`NAME_AND_CONTEXT`): there is no birth date on
the StatsBomb side, and the word *verified* is not used for any link in `analysis.md`.
Reported beside it: the share of paired links for which no team-mate shares any name token,
and agreement of the two sheets on who was cautioned. Gate: in each subset, paired links
must cover at least `minimum_paired_player_match_coverage` of outfield player-matches with
regulation minutes on each side (StatsBomb side by its own goalkeeper flag, Wyscout side by
role code), else both player levels and every link verdict are
`INCONCLUSIVE (IDENTITY_COVERAGE)`. A player-match removed under step 3 is not covered.

**Wide link under test.** Every StatsBomb sheet player with regulation minutes in a linked
match, goalkeeper or not, paired or not (the *evaluated players*), is linked against
**all** Pappalardo player records with no match, team or club context. Tiers are tried in
the order of the tier set; a tier is tried only when the previous one returned no
candidate; several candidates at one tier are `AMBIGUOUS` and do not fall through.

| Tier | Rule |
|---|---|
| A | the StatsBomb legal name token set equals the Wyscout first-plus-last-name token set, at least `link_tier_a_minimum_tokens` tokens, nationality agrees |
| N | the same test with the StatsBomb nickname, when present, in place of the legal name (`link_tier_n_minimum_tokens`) |
| B | one of the two token sets of tier A strictly contains the other with at least `link_tier_b_minimum_shared_tokens` shared tokens, nationality agrees |

The Wyscout short name is never used. Nationality agrees when the normalised StatsBomb
country, after `country_aliases_normalised`, equals the normalised Wyscout birth area or
passport area. A Wyscout record returned for two evaluated players unlinks both. Tier sets
evaluated: `link_tier_sets`.

## Measurements

**Reader variants (StatsBomb side).**

| Variant | Open-play pass | Shots | Role |
|---|---|---|---|
| `open_play` | Pass whose `pass.type` is in `sb_open_play_pass_types` | by `shot.type` | **primary**; mirrors Wyscout, where restarts are a separate type and a kick-off is an ordinary pass |
| `as_shipped` | every Pass with a location and a player | every Shot with a location and a player | what `StatsBombProvider.actions` and Stage 1C computed; graded to price the uncorrected reader |

StatsBomb completion: no recorded outcome. Wyscout completion: `success` is true.

**Event families.** Wyscout rule on the neutral Parquet; StatsBomb rule on the research
frame. Lists are the `sb_*` and `wy_*` keys of `config.json`.

| Family | Wyscout | StatsBomb |
|---|---|---|
| open-play pass | `type` pass | variant rule above |
| corner / free-kick pass / throw-in / goal kick | `set_piece` with subtype in `wy_corner_subtypes`, `wy_free_kick_pass_subtypes`, `wy_throw_in_subtypes`, `wy_goal_kick_subtypes` | Pass with `pass.type` in `sb_corner_pass_types`, `sb_free_kick_pass_types`, `sb_throw_in_pass_types`, `sb_goal_kick_pass_types` |
| open-play shot | `type` shot | Shot with `shot.type` in `sb_open_play_shot_types` |
| free-kick shot / penalty | `set_piece` with subtype in `wy_free_kick_shot_subtypes`, `wy_penalty_subtypes` | Shot with `shot.type` in `sb_free_kick_shot_types`, `sb_penalty_shot_types` |
| non-penalty shot | open-play shot or free-kick shot | Shot with `shot.type` in `sb_non_penalty_shot_types`; `sb_one_sided_shot_types` are counted as one-sided |
| key pass, shipped flag | `key_pass` tag on a completed open-play pass | shot assist or goal assist on a completed open-play pass |
| key pass, assist-inclusive | `key_pass` or `assist` | same as above |
| ground duel | `wy_ground_duel_subtypes` | Duel with type in `sb_ground_duel_types`, or a kind in `sb_ground_duel_kinds` |
| interception | any row carrying the interception flag | a kind in `sb_interception_kinds`, or Pass with type in `sb_interception_pass_types` |
| foul | foul with subtype in `wy_foul_subtypes` | a kind in `sb_foul_kinds` |
| duel or interception | ground duel or interception; each row once | same |
| defensive action | ground duel, interception or foul; each row once | same |

Clearances and blocks are in neither union: Wyscout records a block on the attacker's
event and names no blocker; clearances enter purpose (c) only. Carries, pressures and
receipts enter nothing.

**xT surfaces.** One fit rule on both sides (`xt_recipe`, `xt_grid`; moves = completed
open-play passes, shots = open-play shots, turnovers = `xt_turnover_rule`).

| Surface | Fitted on | Why |
|---|---|---|
| `wy_reference` | Pappalardo Spain 2017/18 minus the linked double-coded matches | league football of the lab season; the units being compared do not fit their own instrument |
| `sb_reference` | StatsBomb La Liga 2015/16 (`xt_sb_reference_expected_matches`), same reader variant as the events it values | the surface the StatsBomb arm of E-12 uses; one club's matches cannot fit a league surface |

`regime` valuation (graded): each provider's events on its own reference. This is the
estimator pair E-12 runs. `common` valuation (reported, not graded): both providers'
events on `wy_reference`. Both surfaces are retrospective; no decision at a date is
claimed. A surface that does not converge, is not finite, or whose corpus does not hold
its expected matches (`xt_sb_reference_expected_matches` for `sb_reference`;
`xt_wy_reference_expected_matches` in the Spain frame, before the linked matches are taken
out, for `wy_reference`) gives `INCONCLUSIVE (XT_SURFACE)` for every xT quantity.

**Quantities.** Keys and formulas are `player_match_inputs`,
`aggregated_player_quantities` and `team_match_quantities`. A ratio's `minimum_denominator`
applies to its own `denominator`, on each provider.

| Input (per player-match; summed for teams) | Definition, identical on both sides after the family mapping |
|---|---|
| `minutes_regulation` | the provider's own regulation minutes under rule 2 |
| `open_play_passes_attempted`, `_completed` | counts |
| `positive_xt_gain_completed_passes` | sum of `max(0, xT(end) − xT(start))` over completed open-play passes |
| `xt_delta_key_passes` (and assist-inclusive) | sum of `xT(end) − xT(start)` over completed open-play passes carrying the flag |
| `key_passes` | count of completed open-play passes carrying the shipped key-pass flag (not the assist-inclusive one) |
| `completed_passes_from_half_space`, `_from_wide` | completed open-play passes whose start `y` lies inside `half_space_bands`, bounds inclusive; strictly below `wide_below` or strictly above `wide_above` |
| `non_penalty_shots`, `open_play_shots` | counts |
| `open_play_shots_in_penalty_area` | open-play shots whose start lies in the provider-drawn penalty area: `penalty_area_wy`, `penalty_area_sb`, bounds inclusive |
| `shot_goal_angle_sum` | sum over non-penalty shots of the angle (radians) the goal mouth subtends at the shot location under `pitch_length_m` × `pitch_width_m`, `goal_width_m`: a convention, not a measurement |
| `defensive_actions` | count of the defensive-action family |
| `opp_half_duel_or_interception` | duel-or-interception rows with start `x` strictly above `opponent_half_x_minimum_exclusive`, acting team's frame |
| team only: `final_third_entries` (+ left / centre / right) | completed open-play passes starting short of `final_third_x_fraction` and ending at or beyond it; left: end `y` below the first of `lane_y_edge_fractions`; right: above the second; centre otherwise; `y = 0` is the attacker's left |
| team only: `box_entry_passes` | completed open-play passes ending inside the provider-drawn penalty area and not starting inside it |
| team only: `defensive_actions_own_third`, `_opposition_third`, `_middle_third` | defensive actions with start `x` below the first of `pitch_third_x_fractions` (own); at or beyond the second (opposition); the remainder (middle) |
| team only: `high_zone_defensive_action_share` | `D / (D + P)`: `D` = the team's defensive actions starting at or beyond `high_defensive_action_x_minimum`; `P` = the opponent's open-play pass attempts starting at or short of `build_up_x_maximum` in the opponent's frame |

A quantity conceded by a team is the opponent's quantity mirrored, so it is not graded twice.

**Levels.**

| Level | Unit | Value compared |
|---|---|---|
| `player_match` | paired outfield player in one match, at least `minimum_regulation_minutes_player_match` regulation minutes on both sides | raw inputs (counts and sums), zeros included |
| `team_match` | team in one match | team sums and ratios |
| `aggregated_player` | paired outfield player over his `player_match` units in the pool: the same player-matches on both providers | per-90 rates and ratios of sums, under the exposure gate |

A player-match that is not a `player_match` unit (under the minimum on either provider,
or removed under step 3 of the player crosswalk) enters no aggregate on either side,
minutes included. Exposure gate at the aggregated level: `exposure_minimum_minutes` for
the pool, in regulation minutes **on each provider**, each provider's own minutes summed
over those units, evaluated once on the real minutes. A player below a gate or a minimum
denominator is a hole for that quantity, not a zero.

## Models and baselines

No model is fitted to an outcome. The xT surfaces are instruments fitted on disjoint data
and then held fixed. Controls:

| Control | Definition | Use |
|---|---|---|
| Positive | the cells in `positive_controls` | if either token is outside `positive_control_passing_tokens`, the crosswalk or the reader is suspect: every token is still reported and every admission is `EXCLUDED (POSITIVE_CONTROL)`, except the declared variant, which keeps `EXCLUDED (DECLARED_VARIANT)` under `exclusion_reason_precedence`. Registry tokens: row a of the registry rule |
| Permuted link | for every seed in `permuted_link_seeds`, inside each `permuted_link_stratum`, the Wyscout partners of paired players are permuted with no fixed point (singleton strata unchanged and counted); computed at `permuted_link_level`, `permuted_link_pool`, `open_play` | an admitted quantity must have an order-statistic point estimate strictly above every permuted value; ties fail. An identity-link stress test, not a p-value. Registry tokens: row a of the registry rule |
| Reader contrast | `as_shipped` beside `open_play` | prices the uncorrected reader; never substitutes for the primary |
| Surface contrast | `common` beside `regime` | attribution only |

## Frozen selection and tuning procedure

None. No parameter is tuned and no quantity, level, pool, exposure, variant or threshold is
chosen after outcomes. Two data-dependent steps exist and are frozen: the two xT fits, and,
for purpose (c) only, one clock offset per match-period, taken as the grid value in
`pair_offset_grid_seconds` that maximises the number of StatsBomb open-play passes with a
same-team Wyscout open-play pass within `pair_offset_match_window_seconds`; ties go to the
smallest absolute offset, then the negative one. If a step fails, the affected cells are
`INCONCLUSIVE`; nothing is substituted.

## Evaluation and reporting

Differences are StatsBomb minus Wyscout. For every cell that passes row 1 of the decision
rule report, with `null` for anything undefined:

- units; means and standard deviations per provider;
- **the order statistic, a stratified rank correlation.** Inside each rank stratum, each
  provider separately, among units defined on both providers, average ranks give
  `u = (rank − fractional_rank_offset) / n`; the statistic is the Pearson correlation of
  the pairs `(u_sb, u_wy)` pooled over strata. Strata (`rank_strata`): the Wyscout role
  codes `rank_strata_roles` at the two player levels; at `team_match` in the `la_liga`
  pool, the rows of the team with most crosswalked matches and the rows of its opponents;
  one stratum elsewhere, where the statistic is Spearman's coefficient. A stratum with
  fewer than `minimum_units_per_rank_stratum` units is dropped and counted. The
  unstratified Spearman coefficient is reported beside it, ungraded;
- Lin's concordance correlation `2·s_xy / (s_x² + s_y² + (mean_x − mean_y)²)` with `1/n`
  moments over all units (the level statistic), and ICC(2,1) absolute agreement as a
  cross-check; an absolute gap strictly above `ccc_icc_cross_check_tolerance` is recorded
  as the boolean `concordance_cross_check_gap` of the cell in `results.local.json` and
  listed in `analysis.md` as a suspected code defect. It is not a cell flag, enters no
  committed JSON and does not alter a verdict;
- Bland–Altman bias, standard deviation of differences, limits `bias ± bland_altman_z·sd`,
  relative bias `bias / ((mean_sb + mean_wy)/2)`, scale ratio `sd_sb / sd_wy`, slope of
  difference on pair mean;
- for count inputs at `player_match`: share of exactly equal pairs.

**Resampling.** `bootstrap_replicates` replicates, fixed `seed` and `seed_streams`,
percentile intervals at `interval_quantiles` (`interval_quantile_method`) for the order
statistic, concordance and relative bias. Ranks are recomputed inside each replicate; a
retained stratum whose units all carry zero weight in a replicate contributes no unit to
it.

| Level | Scheme (`bootstrap_scheme`) | What a replicate draws |
|---|---|---|
| `team_match` | `match_cluster` | matches with replacement inside each subset, one draw per crosswalked match; both teams of a match stay together |
| `player_match` | `pigeonhole_match_by_player` | the match weights above times an independent multinomial weight per paired outfield player |
| `aggregated_player` | `team_cluster_fixed_cohort` | exposure and denominator gates and every player's aggregate are computed once on unweighted data and held fixed; teams are drawn with replacement inside each subset block and a player carries the weight of `bootstrap_cluster_aggregated_player` |

One replicate id is one match-weight vector, one player-weight vector and one team-weight
vector, shared by every quantity, both providers, both readers, both valuations and every
pool. **Declared departure from R12, accepted by the root** (ruling recorded in
`PIPELINE.md`, DISSENT 5): at the aggregated level the shared world is a
team-weight vector, not a match-weight vector. Resampling matches inside an aggregate
re-weights three-match aggregates and re-applies the gate to players who sit exactly on it
(62 of 218 on the public side), and three reviewers' simulations showed its percentile
interval is then not centred on the estimate. That scheme is reported at the aggregated
level as `bootstrap_sensitivity_scheme` and decides nothing. A replicate in which the
statistic is undefined is invalid and counted. For every cell `replicate mean − point` is
reported. **ROOT 2.5 O5 does not apply** (root ruling recorded in `PIPELINE.md`, DISSENT
6): it prescribes an interval on a half-sample correlation for split-half protocols, and
here no half-sample correlation is formed and nothing is transformed. Every interval,
including those of the `la_liga` pool, is the two-sided percentile interval; for cells
with fewer than 100 units that interval, whose lower bound gates admission, is accepted by
the same ruling.
These are intervals of this resampling scheme, conditional on the 100 matches, the
crosswalk and the fixed surfaces; they are not universal confidence statements.

**Pools.** `pooled` (primary), `world_cup`, `la_liga`. The two subsets differ in football,
in team mix and in StatsBomb specification version, so both are always shown and their
difference with its interval is reported; it is not tested.

**Descriptive only, never a verdict:** exposure sensitivities at
`exposure_sensitivity_minutes` and agreement by Wyscout role, in `sensitivity_pools` only
(above its gate the `la_liga` pool is one club's players, so neither is computed there);
unit counts along `exposure_curve_minutes`; the `common` valuation; the sensitivity
bootstrap schemes; the `as_shipped` cell of each shipped construct beside its headline
cell; every table of purpose (c); and the **difference decomposition**: for each
aggregated quantity whose denominator is minutes, over player-matches with at least
`difference_decomposition_minimum_minutes` on both providers of players with at least
`difference_decomposition_minimum_matches` such matches, a one-way random-effects
decomposition of the per-90 provider difference, reporting the between-player share of its
variance with a team-cluster interval. It says whether coding differences are systematic
per player or average out over matches.

**Purpose (c), event level.** The StatsBomb side of every table and of the pairing is read
through `divergence_reader_variant`; the table of StatsBomb Pass and Shot events by type
counts every event of the two kinds. Per family: events per team-match on each side, the pooled
count ratio with a match-cluster interval, and StatsBomb Pass and Shot events by type. For
`pair_families`: one-to-one greedy pairing of same-team events within the family's time
tolerance after the clock offset and (where set) its distance tolerance in metres, by
ascending time gap, then distance, then event order. Report paired share of each side,
player agreement among pairs (paired players only), completion and goal agreement, key-pass
flag overlap, median and 90th percentile start and end displacement, and the xT delta
difference on paired completed passes under the common surface. `count_only_families` are
counted, not paired.

**Purpose (b).** Per tier set and pool. Each evaluated player with a returned link is
`CORRECT` (he is paired and the link is his partner), `FALSE` (he is paired and the link is
someone else, or he is not paired and the returned record is on none of his linked
team-match sheets), or `UNVERIFIABLE` (he is not paired and the returned record is on one of
his sheets). Rates, with Wilson intervals at `wilson_z`:

- **recall** = `CORRECT` / (evaluated players − `UNVERIFIABLE`); an unpaired player with no
  link or a false link counts as a miss;
- **false-link rate** = `FALSE` / (`CORRECT` + `FALSE`);
- **absent-partner stress rate** = paired players for whom a link is still returned when
  their partner is hidden from the pool / paired players;
- **namesake collision rate**, Pappalardo alone: each Wyscout record's own first-plus-last
  name and birth area as the left, every other record as the right; records returning a
  single candidate / all records.

The absent-partner bound is `link_absent_partner_bound`. The same rates on paired players
only, and by presence of a StatsBomb nickname, are reported beside these and decide nothing.

## Decision rule

**Per cell** (quantity × level × pool × reader variant, `regime` valuation, the pool's
exposure gate). `L`, `U` and `P` are the interval bounds and the point estimate; `T` is
`order_statistic_lower_bound_minimum`. Evaluate in order; the first match wins.

| # | Condition | Verdict |
|---|---|---|
| 1 | The first reason in `inconclusive_reason_precedence` that holds: an experiment gate failed (`DATA_MISSING`, `UNKNOWN_VOCABULARY`, `MATCH_CROSSWALK`; `IDENTITY_COVERAGE` at player levels; `XT_SURFACE` for xT quantities); units below `minimum_units`, or fewer than `minimum_rank_strata` strata left where strata are defined (`UNITS`); the quantity is zero on every unit of exactly one provider and non-zero on at least `minimum_units_nonzero_on_both_providers` units of the other (`ONE_SIDED`); either side constant over all units of the cell, or fewer than `minimum_units_nonzero_on_both_providers` units non-zero on both (`DEGENERATE`); valid replicates below `minimum_valid_replicate_share` (`REPLICATES`); the order statistic or its interval undefined (`UNDEFINED_STATISTIC`) | `INCONCLUSIVE` with that reason code; no agreement was graded. `analysis.md` names every `ONE_SIDED` quantity as not recorded by one provider |
| 2 | `L(order) ≥ T` and `P(order) ≥ T` and `L(CCC) ≥ ccc_lower_bound_minimum` and the whole relative-bias interval lies within `± relative_bias_margin`, bounds inclusive | `COMPARABLE` |
| 3 | `L(order) ≥ T` and `P(order) ≥ T` | `COMPARABLE_IN_RANK_ONLY` |
| 4 | `U(order) < T` and `P(order) < T` | `NOT_COMPARABLE`: the data exclude the required agreement |
| 5 | otherwise | `NOT_ESTABLISHED`: compared; criterion not met and not excluded |

An undefined CCC or relative bias fails row 2 and falls through to row 3. NaN is never a
pass. A cell whose order-statistic point estimate lies outside its own interval carries
the flag `POINT_OUTSIDE_INTERVAL`. The flag changes no token.

**Wide link, per tier set,** on the `link_verdict_pool` block. Evaluate in order.

| Condition | Verdict |
|---|---|
| a data, vocabulary, match-crosswalk or identity-coverage gate failed in any subset, or fewer than `link_minimum_evaluated_players` evaluated players | `INCONCLUSIVE`, with the first reason of `link_inconclusive_reasons` that holds |
| upper bound of the false-link rate ≤ `link_false_link_rate_upper_maximum` and the absent-partner bound ≤ `link_absent_partner_false_link_rate_upper_maximum` and lower bound of recall ≥ `link_recall_lower_minimum` | `LINK_USABLE` |
| otherwise | `LINK_NOT_ESTABLISHED` |

An undefined bound fails the `LINK_USABLE` row. None is never a pass.

**Why these numbers, written before any outcome.**

- *The order threshold* (config: `order_statistic_lower_bound_minimum`). Two measurements
  of the same matches correlate at `ρ_AB = sqrt(rel_A · rel_B)`; a cross-provider,
  cross-season correlation is the true persistence times that factor. A true two-season
  persistence of 0.75 gives an observed 0.60 at `ρ_AB = 0.80` and 0.45 at 0.60. The
  transfer-design planning table (Fisher algebra on census counts, no outcome data) puts
  E-12's smallest detectable retention ratio at about 0.73 for a stayer persistence of 0.60
  and about 0.57 for 0.45: below the threshold the provider change alone leaves E-12 able
  to detect little short of collapse. The house `NUMBER` grade asks 0.70 of split-half
  reliability across *different* matches; two coders of the *same* events must clear more.
- *Within role.* E-12 analyses normal scores inside provider-season × league × broad
  position, so the ordering it depends on is within role. Position is truth both providers
  share trivially; a correlation pooled over roles measures agreement about position mix.
- *Stratum minima* (config: `minimum_units_per_rank_stratum`). Set from the public-side
  role counts above: the La Liga pool holds at most 13 forwards at its gate, so a larger
  minimum would drop its forward stratum by design and leave the cell graded on two roles.
- *Exposure* (config: `exposure_minimum_minutes`). Agreement at 270 same-match minutes is
  neither an upper nor a lower bound on agreement at E-12's 900 minutes in different
  seasons: coding error independent across matches makes it too low; match-to-match
  football variation is shared by both coders of the same matches and makes it too high
  when coders differ systematically per player. The difference decomposition says which
  dominates.
- *Relative bias margin* (config: `relative_bias_margin`; unit:
  `relative_bias_margin_unit`). Stage 1C called `width` (+10%) ROBUST and
  `half_space_share` (−14%) ROBUST_WITH_SHIFT without writing the boundary down. It is
  written down here. The same relative margin is applied to rates and to shares.
- *Link rates* (config: `link_false_link_rate_upper_maximum`,
  `link_absent_partner_false_link_rate_upper_maximum`). A false-link bound `e_fl` and an
  absent-partner bound `e_ap` enter E-12 as
  `F = e_fl·NA + e_ap·max(0, N0 − NV − NA·(1 − e_fl))` and
  `e_worst = min(F / n_movers, cap)`, with `N0` the StatsBomb outfield players at E-12's
  origin floor, `NV` those it links through a team-sheet pair, `NA` those it links by tier
  A only, and `cap` E-12's own ceiling of 0.5. At the two maxima and E-12's planning
  counts (`N0` 1,228; 864 tier A links, of which none to 164 become team-sheet pairs, so
  `NA` 864 to 700 and `NV` 0 to 164; 193 within-league movers) `e_worst` is 0.083 to 0.075
  for the within-league arm; E-12's own simulation has its loss verdict largely gone at
  0.15. The false-link bound passes with one false link in 600 linked players and fails
  with two. The absent-partner bound passes with eight absent-partner links in 849 paired
  players and with nine in 850; nine in 849 fail.
- *Unit gates* sit at roughly 70 to 90% of the structural counts above, so for counts,
  sums and per-90 rates a failed crosswalk trips them and the design does not. A ratio
  also loses every unit under its minimum denominator. On the public side that leaves 79
  of 86 La Liga players for the ratios over completed passes and 75 of 76 La Liga
  team-matches for the box share of shots: above their `minimum_units`, with less room
  than the counts have. A short ratio cell is `INCONCLUSIVE (UNITS)` and is not evidence
  about the crosswalk.
- *Level threshold* (config: `ccc_lower_bound_minimum`). It equals the order threshold. No
  separate basis is recorded: it was chosen before any agreement value was computed and
  is not calibrated.
- *Match and coverage gates* (config: `minimum_crosswalked_matches`,
  `minimum_paired_player_match_coverage`). About nine in ten of each subset's matches and
  of each side's outfield player-matches. At exactly the two match minima the `team_match`
  values of `minimum_units` are still met in all three pools, two of them with nothing to
  spare. The nine-in-ten level has no further basis: chosen before any crosswalk was
  built, not calibrated.
- *Sheet structure* (config: `sheet_minutes_tolerance`,
  `sheet_structure_pass_share_minimum`). The two minute rules differ by construction (rule
  2), so equal minutes cannot be required; the size of the tolerance has no further basis.
  The pass share was added at the first review so that one failing sheet in five keeps a
  link; a player on four or fewer sheets still loses his link on one failure. Both values
  were chosen before any sheet was paired and are not calibrated.
- *Evaluated players* (config: `link_minimum_evaluated_players`). No basis is recorded for
  the value: it was chosen before any link was evaluated and is not calibrated. It is not
  the binding sample requirement: with no false link at all, the false-link criterion
  cannot pass on fewer than 381 returned links.
- *Valid replicates and non-zero units* (config: `minimum_valid_replicate_share`,
  `minimum_units_nonzero_on_both_providers`). Neither has a recorded basis: both were
  chosen before any agreement value was computed and are not calibrated. The second is
  also the floor under which no statistic of a cell or descriptive row is printed.

**Operating characteristics, simulated on synthetic corpora before the run** (the
`acceptance_generator`: squads, substitutions, team and match effects, three coder-error
structures; about 200 gated units; `acceptance_bootstrap_replicates` replicates; two
independent implementations of the generator and the rule, the designer's and the
auditor's, 600 corpora per entry each, so one share has a standard error of at most
0.02). Share of corpora receiving an admitted token (`acceptance_admitted_tokens`) at the
pooled aggregated level, range over the three structures and both implementations:

| True within-role agreement | 0.78 | 0.80 | 0.85 | 0.90 | 0.95 |
|---|---|---|---|---|---|
| admitted | 0 to 0.02 | 0.005 to 0.055 | 0.19 to 0.25 | 0.74 to 0.95 | 0.99 to 1.00 |

**A true agreement near 0.85 most often returns `NOT_ESTABLISHED`.** That is stated now so
that it is not later read as a finding or repaired. `acceptance_scenarios` holds these as
requirements the frozen code must meet before the run, with margins for the noise of 200
corpora. With one admission cell per aggregated quantity other than the declared variant
(twelve), up to about 0.7 false admissions are expected if every quantity sat exactly at
the threshold. Error is not controlled across cells, no cell borrows from another, and
nobody may count admissions.

## Consequence of each verdict, fixed now

**Admission, per quantity** (`admission_rule`): from the `aggregated_player` level,
`open_play` reader, `regime` valuation. The first reason in
`exclusion_reason_precedence` that holds decides an exclusion.

| `pooled` token | `la_liga` token | Controls | Admission |
|---|---|---|---|
| any | any | any | a quantity in `admission_rule.declared_variants_never_admitted`: `EXCLUDED (DECLARED_VARIANT)`. It is graded for the record and admits nothing |
| any | any | positive control fails | `EXCLUDED (POSITIVE_CONTROL)` |
| `NOT_ESTABLISHED`, `NOT_COMPARABLE`, `INCONCLUSIVE` | any | — | `EXCLUDED (VERDICT)`: a later study computes nothing for it across providers, not as a secondary, not as a description |
| admitted token | `NOT_COMPARABLE` | — | `EXCLUDED (LA_LIGA_SUBSET_CONTRADICTS)` |
| admitted token | `INCONCLUSIVE` | — | `EXCLUDED (LA_LIGA_SUBSET_UNTESTED)` |
| admitted token | any other | permuted-link control fails | `EXCLUDED (PERMUTED_LINK_CONTROL)` |
| `COMPARABLE` | `COMPARABLE`, `COMPARABLE_IN_RANK_ONLY` | hold | `ADMITTED_LEVEL_AND_ORDER` |
| `COMPARABLE_IN_RANK_ONLY` | `COMPARABLE`, `COMPARABLE_IN_RANK_ONLY` | hold | `ADMITTED_ORDER_ONLY` |
| `COMPARABLE` | `NOT_ESTABLISHED` | hold | `ADMITTED_LEVEL_AND_ORDER_LEAGUE_UNCONFIRMED` |
| `COMPARABLE_IN_RANK_ONLY` | `NOT_ESTABLISHED` | hold | `ADMITTED_ORDER_ONLY_LEAGUE_UNCONFIRMED` |

Every admission of either kind permits the same thing: the quantity may enter a later
cross-provider study on within-provider × league × role rank-normal values only. Level
agreement is recorded as a finding and licenses no raw cross-provider value, contrast or
level-shift estimand. An admission means the `la_liga` cell did not contradict the pooled
one; `_LEAGUE_UNCONFIRMED` means it did not confirm it either, and a study must print that
suffix, and both tokens, beside every result for the quantity. A later study must read
StatsBomb through the reader, the surface rule and the wide-link function graded here,
unchanged and hash-pinned. A quantity admitted under `open_play` is not admitted under the
unfiltered adapter.

**Wide link.** `LINK_USABLE` for a tier set permits a later LOCAL study to use that tier
set, called through `name_nationality_link` unchanged and hash-pinned, and obliges it to
cite the measured rates. It obliges no study to use it. `LINK_NOT_ESTABLISHED` or
`INCONCLUSIVE` means no later study may use that tier set. What a study does without it is
fixed in its own protocol; no outside identity source is implied.

**Registry token, per cell subject** (`registry_token_rule`). A label on a hosted page must
never be more favourable than the whole experiment supports, so the token recorded for a
subject of `registry_cell_subjects` is not always the token of its headline cell. `H` is
the token of the subject's headline cell (`registry_headline_cell`); `S` is the token of
the `la_liga` cell of the same quantity, level, reader and valuation; the *agreeing
tokens* are `registry_token_rule.agreeing_tokens`. Evaluate in order; the first row that
holds decides.

| # | Condition | Registry token | Reason | Second reason |
|---|---|---|---|---|
| a | a control failed: the positive control (either of its cells outside `positive_control_passing_tokens`), or the permuted-link control (for at least one cell subject whose `H` is an agreeing token, the order-statistic point estimate is not strictly above every permuted value) | `INCONCLUSIVE`, for every cell subject | the first failed control in `registry_token_rule.row_a_control_failed.reason_precedence`: `POSITIVE_CONTROL`, then `PERMUTED_LINK_CONTROL` | none |
| b | `H` is an agreeing token and `S` is `NOT_COMPARABLE` | `NOT_ESTABLISHED` | `LA_LIGA_SUBSET_CONTRADICTS` | none |
| c | otherwise | `H` | the reason code of the headline cell (none unless `H` is `INCONCLUSIVE`) | `LA_LIGA_SUBSET_DID_NOT_CONFIRM` when `H` is an agreeing token and `S` is `NOT_ESTABLISHED` or `INCONCLUSIVE`; none otherwise |

Every combination of the two controls, `H` and `S` falls in exactly one row. The registry
token is `H`, `NOT_ESTABLISHED` or `INCONCLUSIVE`; it is an agreeing token only when `H`
is one, no control failed and `S` is not `NOT_COMPARABLE`. A gate that leaves a
positive-control cell `INCONCLUSIVE` fails that control, so row a then applies with
`POSITIVE_CONTROL`; the gate's own code stays in `gates` and on every cell. Row a also
replaces a `NOT_ESTABLISHED` or `NOT_COMPARABLE` headline: when a control of the pipeline
has failed, its negative results are no better founded than its positive ones. Under
every row the headline cell keeps its own token, reason and flags in `cells`, and
`analysis.md` prints the registry token and both reasons beside `H` for every cell
subject. A link subject takes the link verdict and reason of its tier set. The codes this
rule adds are `registry_reason_vocabulary`. When no cell subject has an agreeing `H`, the
permuted-link control has tested nothing: it is recorded as not evaluated, never as
passed. The admission table is not changed by this rule and is read separately. A
quantity can be admitted while its registry token is `INCONCLUSIVE` (the permuted-link
control failed on another quantity), and can keep an agreeing registry token while it is
`EXCLUDED` (the declared variant; `LA_LIGA_SUBSET_UNTESTED`).

**Everything else.** Where a row names a registry token, it is the token of the rule
above, not `H`.

| Outcome | Consequence |
|---|---|
| any | Nothing listed under **Unchanged** changes. No StatsBomb-derived number is served or committed as data |
| registry token of a shipped construct is `COMPARABLE_IN_RANK_ONLY`, `NOT_ESTABLISHED` or `NOT_COMPARABLE` while `MetricDefinition.comparable_across` for that key contains both providers | The contradiction is stated in `analysis.md` and entered in `KNOWN_LIMITATIONS.md`. The registry, `external_replication`, Player Lab and the Stage 1C report are not edited by this experiment; narrowing `comparable_across` is a separate ADR |
| registry token `COMPARABLE` | Recorded. It widens nothing and makes nothing eligible for widening: ADR-0004's reversal clause asks for a validated harmonisation, and this experiment claims agreement, not validity. In `analysis.md` and in any research note that carries the logo, the limits of agreement are printed beside the token. On a hosted page the token is a label that links to that report and carries no number |
| registry token `COMPARABLE_IN_RANK_ONLY` | Permitted sentence: "orders players of the same role consistently across the two providers on double-coded matches". Raw pooling stays invalid |
| registry token `NOT_ESTABLISHED`, `INCONCLUSIVE` | No wording change. Published as such |
| quantity graded here and not admitted | Its cross-provider status is its registry token with its reason codes. "Not graded across providers" is used only for a quantity absent from this config |
| team-level quantity | Its `team_match` tokens are reported. No admission is computed and none is implied; a cross-provider team study states its own admission rule in its own protocol |

A verdict here promotes nothing. It decides only what a later cross-provider study may use.

## What is written where

- `results.local.json`, `determinism.json`, `report_tables.md`, `failed_runs.json`: under
  `local_output_root`, never committed.
- `results.json` (committed): tokens, reason codes from the frozen vocabularies, booleans
  and hashes; no number. A registry cell subject takes the token and reasons of the
  registry rule in the previous section.
- `analysis.md` (committed, with the logo and credit block): for graded cells that pass
  row 1, units, per-provider means and standard deviations, the order statistic,
  concordance and relative bias with intervals, bias and limits of agreement; for every
  cell subject its registry token and reasons beside its headline token; link rates
  with intervals; coverage counts; the divergence tables by family and pool; every failed
  run.
- Neither committed nor printed: any identifier or name of a player, team or match,
  including in deviation notes; any statistic of a cell or descriptive row with fewer than
  `minimum_units_nonzero_on_both_providers` units (its unit count only); crosswalk digests;
  any value of a StatsBomb-fitted surface.

## What this experiment cannot show

- That a quantity means what its name implies. Two providers can agree on a number that
  measures something else.
- Agreement for StatsBomb 2015/16. E-12 uses a different season; only the La Liga matches
  share its specification version, and they are one team's matches.
- League football at the aggregated level: about nine in ten gated players come from the
  World Cup. The La Liga cell vetoes reliably only far below the threshold and confirms
  less than half the time even when agreement is high. Simulated share of corpora in which
  it returns `NOT_COMPARABLE`, by its true agreement (range over three coder-error
  structures and the two implementations above, 600 corpora each): 0.60, 0.48 to 0.94;
  0.70, 0.16 to 0.59; 0.75, 0.07 to 0.30; 0.90, none. At a true 0.90 it returns an
  admitted token in 0.33 to 0.43 of corpora, so most admissions will carry
  `_LEAGUE_UNCONFIRMED`. These figures are for a larger cohort than can occur: the
  generator's club block yields about 88 gated players with about 18 forwards (fewest
  seen in 600 corpora: 73 and 9), while the structural counts above cap the real cell at
  79 players on the StatsBomb side and 13 forwards on the public side. The real cell has
  less power than printed, to veto and to confirm, and its forward stratum sits near
  `minimum_units_per_rank_stratum`; if it falls below, the order statistic is computed on
  the two remaining roles and the dropped stratum is counted.
- A share of open-play shots per player (the box share of shots at the aggregated level).
  On the public side 35 of the 218 gated players have ten open-play shots (24 of 198 in
  the World Cup pool, 11 of 86 in the La Liga pool), fewer than `minimum_units` in every
  pool, so the cell could only have returned `INCONCLUSIVE (UNITS)`. It is not graded and
  not registered, and its cross-provider status at that level is "not graded". The E-09
  candidate `box_shot_share` therefore has no E-11 token at the player level. The box
  share of shots is graded per team-match, and the count of open-play shots in the area
  per player-match.
- That the pairing is error-free. It is name-based inside a closed pool with structural
  corroboration and no birth date.
- The false-link rate of a link on another population. Every player here is on a Wyscout
  team sheet. For tier set `[A]` the absent-partner criterion adds nothing: no two Wyscout
  records share a full-name token set, so the namesake count is zero, and with his partner
  hidden a paired player still receives a tier A link only if his link was to another
  record all along. The stress count is therefore the number of paired players whose tier
  A link is a wrong record: it is not known in advance, and the false-link criterion
  already counts every one of them. Both estimates are live for the wider tier sets only.
  The chance that a StatsBomb player who left the five leagues has a namesake of his
  nationality who arrived is not estimable from either roster.
- Any xT surface pair other than the La Liga pair.
- Anything about carries, pressures or receipts, which only one provider records.
- Anything about a role-specific provider effect beyond the descriptive table.
- The shipped adapter's own documentation. `MAPPING_AUDIT` rates "completed pass" and
  "shot" `SEMANTICALLY_EQUIVALENT` without saying that a StatsBomb Pass includes restarts
  and a StatsBomb Shot includes penalties. That defect was known before this experiment
  (design-time planning values); it belongs in `KNOWN_LIMITATIONS.md` and is not edited
  here.

## Reproducibility and tests

Local artifact `results.local.json` (aggregate only): protocol, config, pipeline and source
hashes on LF-normalised bytes; raw data digests, which must equal `sb_folder_digests`;
content hashes of the frames used; surface hashes; package versions; seeds; digests and
counts of the match and player crosswalks, rebuilt deterministically at run time; every
statistic above. Committed files are listed in the previous section. Every committed
artifact stays under `maximum_results_bytes`; every local artifact under
`maximum_local_results_bytes`.

The pipeline is written and tested on synthetic data only; every test payload is generated
from a seed with invented names, ids and coordinates. Before any real outcome is read, the
frozen decision rule must classify planted corpora as `acceptance_scenarios` requires, and
the resulting `acceptance.json` (synthetic only) is committed beside the protocol. The
runner refuses to execute without that stamp, with a config whose `pipeline_spec_sha256` or
`sb_folder_digests` is null or does not match, or without the commit that first added this
protocol, its config and its pipeline specification, unchanged since. One execution: a
failed execution appends to `failed_runs.json` (exception type and message, stage, source
hashes; no statistic), no value from it may be printed, logged or read, the repair may
touch only the failing stage, the acceptance stamp is regenerated, and `analysis.md` lists
every failed run.

The required tests are listed in `PIPELINE.md` section 10. They must exercise every
branch of every rule in this document on synthetic data, each statistic against an oracle
that shares no code with it, fail-closed behaviour on NaN and None, the keys, strings and
size of every committed output, and refusal to run before the protocol commit.

---

*Committed before running. Local results in `results.local.json`, interpretation in
`analysis.md`. If either contradicts this document, this document wins.*
