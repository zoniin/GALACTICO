# E-12 — do player rates survive a club change? Movers against stayers

> **DRAFT. Not frozen, not registered, not run.** Written by one designer during the north-star build; first adversarial review (a statistician, a reader of the football data and a reader for the constitution) and its revision on 18 October 2026, which applied ROOT 2.8 Y1 to Y4 ([REVIEW-RECORD](REVIEW-RECORD.md)); not yet audited. No outcome named here has been computed. It becomes a protocol only when an audited version is committed under `experiments/preregistered/` in a single commit that precedes any run. Section and file references such as ROOT 2.5 point to [ROOT-DECISIONS.md](../../ROOT-DECISIONS.md); see [README](../../README.md) for the working notes it cites.

<img src="../../../../assets/statsbomb/statsbomb-logo.png" alt="StatsBomb" width="170">

Data source: **StatsBomb** open data, read locally under the StatsBomb Public Data User
Agreement. This analysis is formed from StatsBomb data (the structural counts below are
formed from its lineups) and carries the StatsBomb logo as clause 1.4 of that agreement
requires. It is not the opinion or analytical insight of StatsBomb. No StatsBomb data is in
this repository, and no machine-readable table derived from it is in the tree. The
StatsBomb-side figures printed here are published analysis. Second source: Pappalardo et al.
(2019), *A public data set of spatio-temporal match events in soccer competitions*,
Scientific Data 6:236, CC BY 4.0; figshare collection 4415000, articles Events
(doi:10.6084/m9.figshare.7770599), Matches (doi:10.6084/m9.figshare.7770428), Players and
Teams.

**Commit this plan, `config.json` and `PIPELINE.md` before any persistence, reliability or
forecast-error value is computed for any cohort defined below. Nothing in the three may
change once the first such value is observed.** Stage 1's full-season split-half
reliabilities of every gated player of the public 2017/18 corpus were computed long before
this plan and are disclosed under Prior exposure; no before-and-after, cross-season or
half-against-half value of any cohort defined here has been. This is a prospective analysis
plan on **previously inspected historical data**, not a claim of untouched data collection.
Every threshold, seed, window, list, grid and gate lives in `config.json` and is named here
by its key; a number that appears only in this prose is a defect. Deviations are recorded in
`analysis.md`, never silently adopted.

**Order (ROOT 2.8 Y4).** E-12 may be registered before E-11 runs, and that is preferred: its
design is then frozen before E-11's results can shape it. E-11's execution binds E-12's run,
not its registration: the runner refuses to start while any E-11 record it reads is
`PENDING`, and the constructs it admits are a function, frozen here, of E-11's registry
tokens and admission statuses read at run time.

**Two arms, two tiers, two directories.** `cross_corpus` (StatsBomb 2015/16 to Pappalardo
2017/18) is LOCAL_LICENSED end to end: no number, interval, count, coefficient or identifier
from it enters Git in machine-readable form or reaches a hosted surface; its verdict tokens
may be shown as labels. Its results are committed under `committed_experiment_dir` as tokens
only. `public_winter` (Pappalardo 2017/18 only) is PUBLIC and is the only arm that may put a
number on a hosted page; its results are committed under `public_experiment_dir`, which holds
byte-identical copies of the three protocol files, so that each `results.json` carries one
tier (PIPELINE.md section 0; DISSENT 6 asks the root to confirm this layout).

## Claim and unchanged boundaries

Claim under test, one verdict per construct and contrast:

> Among players who are used at their next club and whose broad position is the same under
> the two providers' labels, the ordering of players on the construct persists across a
> change of club to within a frozen margin of its persistence among players of the same
> prior standing who did not change club over the same interval, and movers' standing does
> not shift against those stayers by more than a frozen margin.

Stayers cross the same provider change, the same unobserved 2016/17 season and the same two
years of ageing, so the stayer persistence is the yardstick and the estimand is a
mover-to-stayer contrast, never an absolute persistence figure. Stayers are weighted to the
movers' mix of position and prior percentile before the comparison (Estimands), so that a
difference in the spread of prior standing between the two groups cannot pass for a
difference in persistence. "Persists" is a non-inferiority claim on the ordering ratio with a
margin, joined to an equivalence claim with a margin on the standing shift; failing to find a
difference is not it.

Primary endpoint: `progression` (per 90), contrast `within_league` (ROOT 2.5 K15).
`progression_per_action`, `chance_creation`, `half_space_share` and `width` are secondary:
each gets its own verdict, and a verdict on one says nothing about another. Being primary
affects reporting order and the headline of `analysis.md` only
(`primary_designation_effect`).

**The estimator.** E-12's `progression` is E-11's harmonised estimator of the shipped Player
Lab construct (ROOT 2.5 O2), not the number Transfer Lab injects. They differ in four ways:
the recipe (Transfer Lab values on `historical.fit_prior_xt`, whose turnovers are failed
passes only; E-11's recipe adds dangerous losses, `xt_turnover_rule`); the surface (Transfer
Lab uses the destination league's pre-cutoff surface; E-12 uses one fixed surface per
provider for every league, `surface_rule`); the club (Transfer Lab takes the club of the
latest appearance; E-12 takes the main club, most regulation minutes); and the minutes
(shipped lineup minutes against E-11's regulation minutes capped at `regulation_minutes_cap`
of E-11's config). A winter mover with more minutes at his first club than at his second is
valued at the second by Transfer Lab and at the first by E-12. A verdict here is about the
ordering of E-11's harmonised progression. Whether it governs the injected rate is a reading
of K15 that DISSENT 7 asks the root to rule; until it does, every product sentence names the
estimator (`product_copy.estimator_note`).

**Not claimed.** Transfer success, selection or playing time. A causal effect of the
destination club or of moving. League strength. A forecast for any individual. The fraction
of a rate one player keeps. Performance of an unplayed XI. Anything for a player who was not
used at the destination: every estimate is conditional on clearing the destination minutes
floor, which selects movers who succeeded (attrition table below). Anything for a player whose
broad position differs between the two providers' labels: the verdict is conditional on a
variable observed after the move, and movers redeployed to another broad position, whose
ordering is the most likely to break, are outside it (ROOT 2.8 Y2; the ROLE_CHANGED share of
each arm is printed beside every verdict so that a difference between the arms is visible).
Anything about a named player or club.

**Unchanged.** No `SPECS`, `CONSTRUCTS`, evidence gate (900 minutes outfield; 1,800 minutes
for Wyscout `chance_creation`), Parquet file, provider adapter or shipped number changes
under any outcome. No transport function, shrinkage coefficient or context coefficient enters
the product under any outcome: Transfer Lab keeps injecting the candidate's historical rate
and states the break-even carry-over fraction. E-07 and E-08 stay closed;
`galactico/validation/transport.py` (E-07, lineup-sum forecast) is a different study, and
E-12's tokens, claim token and module name avoid its word. The registration commit changes
product code in exactly the places `PIPELINE.md` section 13 lists, under an ADR in the form of
ROOT 2.10 W8: the Transfer Lab's candidate rows look up E-12's governing subject, and stale
docstrings are corrected. No verdict changes an injected number, a grouping or an order.

## Prior exposure, stated before the run

| Data | What has already been seen |
|---|---|
| Pappalardo five leagues 2017/18 | Inspected for every shipped construct: Stage 1 and 1B (split-half reliability by alternating matches, confound audits, baselines, all five leagues), Stage 1C (estimator v2, four leagues), Player Lab, Match Lab and XI Lab (Spain). E-02 used Italy, with England, Germany and France as secondary. E-07 and E-08 used Spain and England team-opening rows, including March-to-May outcomes. Squad Lab and Transfer Lab compute per-player 2017/18 rates of the gated players of all five leagues, on the shipped decision recipe, at end-of-season cutoffs: the quantity Transfer Lab injects, on the destination side of this study |
| StatsBomb 2015/16, four leagues | E-01 (exploratory). Stage 1C: within-provider reliability, confound share, baselines, La Liga level shifts (`progression` -32%, `chance_creation` +110%, provider and season confounded), the `chance_creation` minutes curve |
| The wide-link rule (quoted from E-11's registered protocol) | "The mover census ran name-plus-nationality tiers, with eleven of the twelve aliases, on all 2,176 StatsBomb 2015/16 players against the same 3,603 Wyscout records: its tier A (legal name; the census also used the Wyscout middle name) linked 1,272 (58.5%); link, ambiguity and unresolved shares, the split by nickname, and position, goalkeeper-flag and implied-age agreement per tier were read." The position agreement read there is, in substance, the ROLE_SAME share that now decides which units are confirmatory (ROOT 2.8 Y2) |
| E-11 | Registered 14 October 2026; its sixteen records were `PENDING` when this revision was written (18 October 2026), and no E-11 statistic has been computed. If E-11 has run before E-12's registration commit, that commit adds a row here naming everyone who read E-11's `analysis.md`, `report_tables.md` or `results.local.json` before it (ROOT 2.8 Y4; the E-10 precedent). E-12 conditions on E-11's verdicts by design, and no E-12 constant depends on them |
| Structure, counted for this protocol | Lineups, rosters and match lists only (`mover-census.md`; design script `count_cohorts.py`): arm sizes under the rules below, club overlap, position mix, the age gap between movers and stayers (about 1.4 years at the median), minutes distributions, the 124 in-season movers and their appearance dates, and the counts of units whose two position labels differ |
| Planning values | One blog source reports year-to-year VAEP persistence of about 0.77 for same-club players against 0.69 for same-league movers (numbers read from charts; unverified; one season, one provider). All power figures below are algebra or synthetic simulation |

No player has ever been linked across the two corpora for an outcome statistic. No
cross-season or cross-provider player-level association, no before/after-date persistence
within a season, no mover-against-stayer contrast and no half-against-half correlation
inside any cohort defined here has been computed by anyone on this project. Gates were set
from the algebra in "Why these numbers" with the structural counts in view; that is
disclosed, and the counts are printed beside the gates.

## Data, identity, cohorts and exclusions

### Corpora and the E-11 dependency

Origin: StatsBomb open data 2015/16, La Liga, Premier League, Serie A, Ligue 1
(`origin_expected_matches`). Destination: Pappalardo 2017/18, Spain, England, Italy, France,
Germany (`destination_expected_matches`; Germany can only be a destination). Both sides are
read through E-11's registered readers, its `open_play` variant, its xT fit rule and its two
reference surfaces, imported unchanged from `galactico.validation.sb_reader`,
`provider_crosswalk` and `provider_inputs` and pinned by `dependency_source_sha256`; E-11's
registered config is read and pinned by `dependency_config_sha256`. E-12 reads no event and
no minute differently from E-11. The one thing it reads that E-11's readers do not return is
the position name of each StatsBomb lineup spell, which it takes through the pinned module's
own spell rule (`sb_modal_broad_position_rule`; `PIPELINE.md` section 2).

Three of the four origin folders were never checked by E-11. Before any event is harmonised,
the runner compares the category names of event kind, pass type, shot type and duel type in
each folder of `sb_vocabulary_checked_folders` with E-11's four `sb_known_*` lists (E-11
`PIPELINE.md` section 14, item 7): "a name outside a list stops E-12 before any statistic".
Here that stop is a gate: every `cross_corpus` subject of an admitted construct is
`INCONCLUSIVE (UNKNOWN_VOCABULARY)` and the public arm is unaffected. The four folder digests
are pinned in `sb_folder_digests`; the root computes the three that are null before
registration, and a null value refuses the run.

**Admission (ROOT 2.8 Y4; E-11 section 14, item 3).** Per construct, E-12 reads two values
at run time: the token of the registry record `E-11/<construct>` in
`galactico/domain/verdicts.py`, and E-11's committed `results.json`
`admission[<construct>]` (`status`, `reason`, `pooled_verdict`, `la_liga_verdict`). The
registry token must equal E-11's `results.json` `verdicts[<construct>].token`, or the
runner refuses. A construct is admitted iff its registry token is in
`dependency_agreeing_tokens` **and** its admission status is one of the four
`dependency_admitting_statuses` (`admission_rule`). The conjunction is needed because the two
can disagree: "A quantity can be admitted while its registry token is `INCONCLUSIVE` ...
and can keep an agreeing registry token while it is `EXCLUDED` (the declared variant;
`LA_LIGA_SUBSET_UNTESTED`)" (E-11's protocol). DISSENT 8 asks the root to confirm it.

| E-11 registry token | E-11 admission status | `cross_corpus` arm | `public_winter` arm |
|---|---|---|---|
| `COMPARABLE` or `COMPARABLE_IN_RANK_ONLY` | `ADMITTED_LEVEL_AND_ORDER` or `ADMITTED_ORDER_ONLY` | Enters. Analysed on within-cell normal scores only: no raw cross-provider value is formed or reported under any admission. The standing shift `D` is a difference of within-provider, within-league, within-position normal scores, which is what both admissions permit ("on within-provider × league × role rank-normal values only") | unaffected (one provider) |
| agreeing, as above | `ADMITTED_LEVEL_AND_ORDER_LEAGUE_UNCONFIRMED` or `ADMITTED_ORDER_ONLY_LEAGUE_UNCONFIRMED` | Enters, same analysis. The suffix and both E-11 tokens are printed beside every result for the construct, and its registry token carries the suffix (`registry_token_rule`) | unaffected |
| `NOT_ESTABLISHED`, `NOT_COMPARABLE` or `INCONCLUSIVE` | any | `NOT_ADMITTED` with reason `E11_TOKEN_<token>` (`not_admitted_reason_map`). No outcome statistic is computed for it in this arm, not as a secondary, not as a stratifier, not as a description | unaffected |
| agreeing | `EXCLUDED` for `DECLARED_VARIANT`, `POSITIVE_CONTROL`, `VERDICT`, `LA_LIGA_SUBSET_CONTRADICTS`, `LA_LIGA_SUBSET_UNTESTED` or `PERMUTED_LINK_CONTROL` | `NOT_ADMITTED` with reason `E11_<reason>`, same rule | unaffected |
| any E-11 record read (`dependency_registry_subjects`, `dependency_link_subject`) is `PENDING`, or E-11's results are absent, stale, hash-mismatched or disagree with the registry | - | the runner refuses to start (exit 2); no verdict is written | not run either: one command, one protocol |

The reason of a `NOT_ADMITTED` is the first of `not_admitted_reasons` that holds: the
registry token's, then E-11's exclusion reason. Both E-11 values are printed beside it.
E-12's five constructs include no declared variant of E-11; the assist-inclusive variant of
`chance_creation` never enters.

### The identity link: a declared research link, not an identification

StatsBomb lineups carry no birth date, so `resolve_player` accepts nobody on this pairing
(0 of 2,176). The link below is declared, tiered, measured on E-11's double-coded matches
and stress-tested. Its evidence class is `ESTIMATED` in both tiers, so every cross-corpus
statistic is `ESTIMATED` at most. The word *verified* is not used for any link.

| Tier | Rule | Error evidence |
|---|---|---|
| P | The StatsBomb player holds a `PAIRED_BY_TEAM_SHEET` pair (`dependency_paired_status`, read from E-11's `paired_status`) in E-11's team-sheet crosswalk, rebuilt in memory by E-11's own calls (`PIPELINE.md` section 6). StatsBomb ids are one id space, so the pair links his 2015/16 rows | E-11's coverage, swap-impossible share and cautioned-agreement table; no false-pair rate is measured |
| A | E-11's wide link with tier set `[A]`, used only when the registry token of `E-11/wide_link_tier_a` is `LINK_USABLE` (E-11 section 14, item 2), and called exactly as E-11 fixes it: `name_nationality_link(left, right, e11_config, tiers=["A"], exclude_right=None, unique_right=True)`. The StatsBomb legal name token set equals the Wyscout first-plus-last-name token set, both on `name_tokens` of `galactico/identity/resolver.py`, at least E-11's `link_tier_a_minimum_tokens` tokens, nationality agrees. No nickname. A left with several candidates is `AMBIGUOUS` and claims nothing; a right record reached by two or more lefts makes every one of them `CLAIMED_TWICE` | E-11's `false_link_rate.upper` and `absent_partner_bound` of the `identity` block with `tiers` `["A"]` and `pool` `pooled` |
| excluded | Everything else (`link_excluded`) | - |

The left side is every StatsBomb player with a regulation minute in a 2015/16 match of the
four folders, with the legal name, nickname and country of his row in his last such match by
date, then match id; players whose rows disagree are counted (`link_left_row_rule`; E-11
section 14, item 9). The right side is every Wyscout record, built as E-11's
`evaluate_wide_link` builds it (`link_right_rule`). Tier P wins. A StatsBomb player whose two
tiers name different partners, or a Wyscout player linked from two StatsBomb players, loses
every link and is counted (`tier_conflict`, `claimed_twice`). If the link token is not
`LINK_USABLE`, the arm runs on tier P alone (`link_fallback_when_wide_link_not_usable`); the
structural upper bound of that tier (143 stayers and 66 within-league movers, all roles) is
below the gates, so every `cross_corpus` subject is then expected `INCONCLUSIVE`. Tier N and
tier B never enter, whatever E-11 says about them.

**Measured error and its use.** With `e_fl` and `e_ap` E-11's two bounds above, `N0` the
StatsBomb outfield players at the origin floor, `NP` and `NA` those linked by tier P and by
tier A only (`false_link_rule`):

    F = e_fl * NA + e_ap * max(0, N0 - NP - NA * (1 - e_fl))
    e(contrast) = F / n_M(contrast)

`n_M` is the analysed mover count of the contrast (Sample gates). A false link pairs unrelated
players, who almost never share a club, so it is counted as a mover and multiplies the mover
correlation by `(1 - e)`. All of `F` is assumed to fall in the mover arm being judged. That
biases toward loss, so the loss verdict must survive division by `(1 - e)`; the survival
verdict is not adjusted, because the bias runs against it. The loss verdict is evaluable only
when the wide link was used and `e` is at most `false_link_share_cap`: in `paired_only` mode
no false-pair rate exists, and above the cap the correction is too large to trust, so in both
cases the loss row cannot fire and a loss-shaped result is `NOT_ESTABLISHED
(LOSS_NOT_ROBUST_TO_CORRECTIONS)`. A false link inside the stayer arm would bias toward
survival; it needs a different person with the same full name and nationality at the same
club two years on, and the `paired_links_only` sensitivity is the check. E-11 measured its
rates on the players of the double-coded team sheets; applying them to the 2015/16 rosters is
an extrapolation ("What this experiment cannot show").

**Stress test, in the manner of E-08.** For each of `identity_placebo_seeds`, permute the
whole destination side (values, halves) among analysed units inside `identity_placebo_pool`
(cohort, destination league, position), with the seed of `placebo_seed_rule`, units sorted
and no dependence on row order; singleton pools and unchanged units are counted. The real
correlation of each arm must be strictly above all 20 permuted values of that arm; ties fail,
and a missing result fails (`identity_placebo_none_fails`). This is an identity-link stress
test, not an exchangeable permutation test and not a p-value. A planted-contamination curve
(`contamination_fractions`, `contamination_draws`, `contamination_count_rule`) is reported
beside the algebraic adjustment.

**No crosswalk is persisted.** Links, pairs and every row that holds a provider player id
exist in process memory only and are rebuilt deterministically on each run. Nothing that
holds a StatsBomb id, a linked pair or a per-player linked value is written to any file,
tracked or not. Only digests and counts of the crosswalk reach the local artifact.

### Club crosswalk

Club key = `normalise_name(team name)`, then `club_aliases` (12 entries: the two providers
spell 12 of the 66 shared clubs differently), then the league. The names are those of
`club_name_sources`: StatsBomb `read_matches` home and away team names; Wyscout
`teams.parquet` `team_name`, as E-11's crosswalk reads it, whose content hash is pinned. No
provider team id enters the key. Before any action is read the runner asserts
`club_crosswalk_expected_shared` (66 shared keys: Spain 17, England 17, Italy 16, France 16),
`club_crosswalk_expected_origin_only` (14), 14 destination-only in the four overlap leagues,
18 in Germany, and a one-to-one mapping; a mismatch is a failed run (exit 3, no verdict). Five
shared clubs spent 2016/17 in the second tier (`second_tier_2016_17_clubs`); "same club" for
their players spans a relegation and a promotion.

### Cross-corpus cohorts

Unit: a linked outfield player (`outfield_rule`). Main club in a season = the club with most
of his regulation minutes; a tie excludes him. Every value uses his main-club matches only.
An appearance is a sheet row with at least `minimum_regulation_minutes_appearance` regulation
minute. Origin floor: 900 minutes at the origin main club. Destination floor: the registered
Wyscout floor of the construct at the destination main club (900; 1,800 for
`chance_creation`). Cohorts are therefore construct-specific.

| Cohort | Definition | Role |
|---|---|---|
| `S` stayer | same club key in both seasons and exactly one club in each season | control |
| `M_w` within-league mover | different club, same league | primary mover arm (`within_league`) |
| `M_x` league-changer | different league, destination in the four overlap leagues | secondary (`league_change`) |
| `M_b` Bundesliga destination | destination league is Germany | secondary (`bundesliga_destination`); expected `INCONCLUSIVE` |
| second club within a season, same main club | same main club in both seasons but a second club in either | excluded from every contrast; counted |
| second club within a season, mover | a mover with a second club in either season | kept, main-club values; dropped in `single_club_movers` |

**Role continuity (ROOT 2.8 Y1 to Y3).** A linked unit is `ROLE_SAME` when its StatsBomb modal
broad class equals its Wyscout role code under `wy_position_map`, `ROLE_CHANGED` otherwise
(`role_same_rule`). The StatsBomb class is the broad class with most regulation minutes over
his main-club spells of the season, ties to the class of the earliest spell, unmapped names
counted (`sb_modal_broad_position_rule`); the same rule places every player of the reference
population. An E-11 admission covers an origin cell only for a `ROLE_SAME` unit (Y1).
**Every verdict-bearing statistic of the `cross_corpus` arm is computed on `ROLE_SAME` units
only (Y2):** the two correlations, the reliabilities, the matched weights, `D`, the placebos,
the gates, the false-link share, the rule comparison and every sensitivity. The reference
population of a cell is unchanged. `ROLE_CHANGED` units are reported beside each contrast as
a descriptive stratum labelled outside the ordering E-11 graded (`role_changed_rule`); they
never reach a verdict, and `analysis.md` prints `role_changed_sentence` beside them. The
`ROLE_CHANGED` share of the linked units of each arm is printed beside every contrast in
`results.local.json` and `analysis.md` (Y3; E-11 section 14, item 10). The flag mixes
redeployment with provider labelling and cannot separate them.

Position for strata, matching and reporting is the Wyscout role (one public label per
player). Further declared flags: origin club absent from the 2017/18 corpus; destination club
absent from the 2015/16 corpus; stayer at a second-tier-2016/17 club; link tier; age band on
`age_reference_date` (Wyscout birth date) and destination minutes band, both under
`band_closure`, with `band_missing_value` where a birth date is missing.

Structural counts under the draft's rules (tier A alone, shipped lineup minutes, the draft's
modal position name; counts only; no outcome was read; realised counts will differ by a few
because E-11's reader caps regulation minutes, tier P adds links, and the modal rule is now by
class minutes):

| Origin / destination floor | `S` | `M_w` | `M_x` | `M_b` | excluded, same main club | origin clubs `S` / `M_w` / `M_x` |
|---|---:|---:|---:|---:|---:|---|
| 900 / 900 | 337 | 193 | 72 | 12 | 17 | 66 / 72 / 44 |
| 900 / 1,800 (`chance_creation`) | 237 | 118 | 32 | <5 | 5 | 63 / 63 / 26 |
| 900 / 900, players also present in the double-coded competitions (upper bound on tier P) | 143 | 66 | 36 | <5 | 5 | 37 / 36 / 29 |

At 900 / 900: position mix `S` 148 DF, 133 MF, 56 FW; `M_w` 74, 74, 45; `M_x` 31, 26, 15.
42 movers have a second club within a season; 54 left a club absent from the 2017/18
corpus; 43 `M_w` or `M_x` movers joined a club absent from 2015/16; 11 stayers are at
second-tier-2016/17 clubs. **24 stayers and 23 movers are `ROLE_CHANGED`**, so the
confirmatory stayer arm at 900 / 900 has 313 units; how the 23 movers divide among `M_w`,
`M_x` and `M_b` was not recorded. In proportion to the cohort sizes they leave about 177, 66
and 11. The root recounts every cohort for `ROLE_SAME` under the revised modal rule before
registration (`counted_by_root_before_registration`), with the distinct origin and
destination clubs among those units, and prints the counts in the registration commit. Of
1,228 StatsBomb outfield players at the origin floor, 864 hold a tier A link, 822 of those
appear in 2017/18 lineups and 631 clear the 900-minute destination floor.

### Public arm cohorts (Pappalardo 2017/18 only; provider-declared ids)

| Cohort | Definition |
|---|---|
| `P_M` winter mover | appearances (`public_appearance_rule`) for exactly two clubs in the five leagues; last appearance for the first club after `public_winter_last_old_club_appearance_after`; first appearance for the second on or after `public_winter_first_new_club_appearance_from`; every first-club appearance earlier than every second-club appearance (the three loan-and-recall players are excluded, `public_exclude_interleaved_spells`); outfield; side floor met on both sides. Before = first-club matches, after = second-club matches. The move is bracketed by two observed appearances, not by a transfer date the data does not hold |
| `P_S` same club | appearances for exactly one club; before = matches dated earlier than `public_same_club_split_date`, after = the rest; outfield; side floor met on both sides |

Side floor = `public_side_floor_minutes` (half the construct's registered Wyscout floor: 450;
900 for `chance_creation`), so the two sides together meet the registered floor. This is a
research cohort with different semantics, not a relaxed individual gate, and it certifies no
individual. A mover's split is his own move, which falls between the first day of
`public_winter_first_new_club_appearance_from` and his first second-club appearance; a
stayer's split is the fixed date, two weeks into the window. The two splits differ by a few
weeks at most and that is not corrected. Exact structural counts (`public_structural_counts`):
124 two-club players; 29 `P_M` at 450 on each side (20 within a league, 9 across; 8 DF, 12 MF,
9 FW), 51 at 270, 7 at 900; 1,097 `P_S` at 450, 592 at 900. **The mover comparison in this arm
cannot meet its gate (29 against a requirement of 62 for the four constructs at 450 minutes a
side, and 7 against 65 for `chance_creation`) and is expected to return `INCONCLUSIVE` for all
five constructs. That is known now and is the registered outcome, not a disappointment to be
repaired by lowering a floor.** The arm is registered so that the gate, not judgement after
the fact, is what withholds the number.

### Exclusions

Goalkeepers; players below a floor (a hole, never a zero); main-club ties; units in a
standardisation cell with fewer than `minimum_cell_units` units; units with an undefined value
(a zero denominator, or one below the construct's `minimum_denominator`); `ROLE_CHANGED` units
from every verdict-bearing statistic. No exclusion on team, age, nationality, league or club
strength, and no outlier removal. Every exclusion is counted by reason, and the passage from
cohort to analysed units is printed per construct and contrast.

## Measurements

**Inputs.** Per player-match sums from E-11's `player_match_inputs` (`input_columns`):
regulation minutes, completed open-play passes, positive xT gain over completed open-play
passes, xT delta over key passes, completed passes from the half-space bands and from wide.
StatsBomb through `open_play` (set-piece restarts excluded), never the unfiltered adapter.
Player-matches with fewer than `minimum_regulation_minutes_appearance` minute are dropped.

**Constructs.** Each of the five is E-11's `aggregated_player_quantities` entry of the same
key, numerator, denominator, scale and `minimum_denominator` included, asserted equal at run
time (`construct_definition_rule`); a token of E-11 applies to the definition it hashes.

**Surfaces.** The xT recipe is the shipped Player Lab recipe as frozen in E-11 (`xt_recipe`).
Exactly three surfaces are used (`surface_rule`). `sb_reference_open_play` (La Liga 2015/16)
values all four origin leagues and `wy_reference` (Spain 2017/18 without E-11's linked La
Liga matches) all five destination leagues of the `cross_corpus` arm; both are hash-equal to
E-11's (`provenance.xt.sb_reference_open_play.hash`, `provenance.xt.wy_reference.hash`), the
only pair whose cross-provider agreement E-11 graded. `wy_reference` excludes matches chosen
by the match crosswalk "and so reads StatsBomb: a PUBLIC arm may not use it" (E-11 section 14,
item 5). The public arm is valued on `wy_public_spain`: E-11's fit rule on every Spain 2017/18
match, no match excluded, built before any licensed path is opened from Pappalardo files
alone, with its own hash. The public arm has one provider and needs no graded pair. One fixed
surface per provider is the E-07 / E-08 device. All three are retrospective; no decision at a
date is claimed.

**Value.** `scale * sum(numerator) / sum(denominator)` over the unit's matches for the club
in question (`constructs`). A denominator of zero or below `minimum_denominator` gives a
missing value.

**Standardisation.** Cell = provider-season x league x broad position (StatsBomb modal class
on the origin side, Wyscout role on the destination side). The reference population of a
cross-corpus cell is every outfield player of that corpus-league at the floor, linked or not.
Within a cell: average ranks `r` of finite values, `u = (r - normal_score_offset) / n` (the
unit's prior percentile on the origin side), `z` = standard normal quantile of `u`. Level
shifts between providers and between league surfaces are removed by construction; raw values
are never compared across cells. Public arm cells: league x Wyscout role x side, with the
reference population of `public_reference_population_rule`.

**Halves.** A unit's matches for the club, sorted by date then match id, alternate A, B
(`half_assignment`). Half values are standardised within the same cells among units with at
least the half floor in that half (`half_floor_minutes_by_side_floor`: one third of the floor
of that side, so 300 minutes at a 900-minute floor, 600 at 1,800, 150 at the public 450 and
300 at the public 900). A unit short of it is a hole for reliability only.

**Club levels.** `level_origin` = minutes-weighted mean origin `z` of the other
floor-eligible outfield players at the unit's origin club (leave-one-out, at least
`club_level_minimum_other_players` others). `level_destination_prior` = the same mean over
all floor-eligible outfield players at the destination club in the origin season; missing
when that club is not in the origin corpus. `own_deviation = z_pre - level_origin`.

## Models and baselines

**Estimands, per construct and contrast (`g` = arm; all on normal scores; `cross_corpus` on
`ROLE_SAME` units).**

| Symbol | Definition |
|---|---|
| matched stayer weights | Cell = Wyscout position x bin of the origin percentile `u_pre` (`prior_percentile_bin_edges`, `prior_bin_closure`). A stayer's weight is (movers' weight in his cell) / (stayers' weight in his cell); a mover in a cell with no stayer is dropped and counted (`prior_matching_rule`). Recomputed inside each world |
| `rho_M`, `rho_S` | Pearson correlation of `(z_pre, z_post)` over the movers, and over the stayers under the matched weights (a rank-based statistic: both are within-cell normal scores). The Spearman coefficient of the same `(z_pre, z_post)` pairs is reported beside each point value |
| `tau` | `rho_M / rho_S`, the ordering ratio. **The decision statistic.** The ratio with unit stayer weights is reported beside it as `unmatched_ratio` and decides nothing |
| `dz` | `atanh(rho_S) - atanh(rho_M)`, reported with its resampling interval and with the analytic check `1.6449 * sqrt(1/(n_S - 3) + 1/(n_M - 3))` |
| `rel_g,s` | Spearman-Brown `2r / (1 + r)` of the half-A / half-B correlation, inside arm `g` (stayers under the matched weights), season `s`, on the same units |
| `rho*_g`, `tau*` | `rho_g / sqrt(rel_g,pre * rel_g,post)` and `rho*_M / rho*_S`. Reported **beside** the raw value, never instead of it; missing unless each stepped-up reliability exceeds `attenuation_minimum` and each half correlation exceeds -1 (`attenuation_rule`) |
| `D` | Standing shift: mean of `z_post - z_pre` over movers minus the mean over stayers in the same matched cells. Movers selected on a high prior value regress whether or not anything failed to persist, and so do stayers of the same prior standing |

The ratio, not the Fisher-z difference, carries the decision because the margin has to mean
the same thing at every stayer level: a fixed `dz` of 0.25 is `tau` 0.90 when `rho_S` is
0.85 and 0.69 when it is 0.60 (algebra).

**Why the stayers are matched.** A correlation falls when the spread of the prior falls, with
no change in persistence. Movers are not a random draw from the prior distribution, and nor
are stayers who keep their place. On synthetic panels with complete persistence (ratio 1) and
movers drawn from the top half of the prior, the unmatched ratio averaged 0.755 and survival
was returned in 0.03 of panels; with stayers drawn from the top 60% and a ratio of 0.80 at the
margin, the draft's unmatched rule returned survival in 0.14 of panels, above the 0.10 it
allows itself. Matching the stayers to the movers' position and prior bin, and dropping movers
in cells without stayers, gave 0.97 and 0.005 (PIPELINE.md section 7 and REVIEW-RECORD). The
estimand is therefore defined on the movers' prior distribution.

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

**What is fitted on whom.** `a`, `alpha`, `beta` are one weighted least-squares fit of
stayers' `z_post` on `[1, own_deviation, level_origin]`, with the matched stayer weights.
Nothing is fitted on movers. Stayers are the only units for whom "how much of an own
deviation and of a team level persists across this provider change and these two years, with
no club change" is observed; movers are the only units for whom the three rules disagree. So
every rule is an out-of-sample forecast for every mover, no cross-fitting or tuning is needed,
and the comparison among `R1`, `R2`, `R3` isolates which component travels. Stated limit:
applying `beta` to the destination level assumes a mover absorbs it as an incumbent does; that
is the hypothesis `R3` tests, not an assumption of the report. All rules are scored on
identical rows (movers with every term defined); the rest are counted. No hyperparameter, no
feature search, no other covariate.

**Controls.**

| Control | Definition | Use |
|---|---|---|
| Stayer yardstick | `rho_S` | denominator of `tau`; its floor decides whether a ratio means anything |
| Regression to the mean | `D` above | enters the survival verdict |
| Identity placebos | 20 permuted-link values per arm | enter the survival verdict |
| False-link adjustment | `e` | enters the loss verdict |
| Pseudo-movers | `pseudo_mover_draws` draws of `n_M` stayers, drawn with probability proportional to their matching weights, against the rest, through the same estimator (`pseudo_mover_rule`) | a pipeline self-check: when 1 lies outside the `pseudo_mover_check_quantiles` of the draws, the contrast is `NOT_ESTABLISHED (PIPELINE_SELF_CHECK_FAILED)`; centre and quantiles reported |
| Composition match | stayers reweighted to the movers' mix of position x age band x destination-minutes band | reported: `tau` under those weights (`composition_matched`) |

## Frozen selection and tuning procedure

None. No parameter is tuned and no cohort, floor, cell, construct, contrast, surface, margin
or threshold is chosen after outcomes. The only data-dependent fits are E-11's two surfaces
(inherited, hash-pinned), the public surface (one fixed rule) and the three stayer
coefficients above. If a step fails, the affected verdict follows the decision table; nothing
is substituted. A failed execution follows E-11's policy, adopted word for word (`PIPELINE.md`
section 6): "No value from a failed run may be printed, logged or read. The repair may touch
only the failing stage", the calibration stamp is regenerated and recommitted, and every
failed run is listed in `analysis.md`. "A gate that fails is not an exception: it is a
verdict."

## Evaluation and reporting

**Resampling.** `bootstrap_replicates` worlds, fixed `seed` and `seed_streams`. One world is
one multinomial weight vector over origin club keys (public arm: the club key of the before
side), shared by every construct, contrast, statistic and sensitivity of the arm
(`world_rule`); a unit's weight is its club's weight, so team-mates and both arms of a club
move together. Matched weights, reliabilities and the stayer coefficients are recomputed
inside each world; cells and normal scores are not (intervals are conditional on the
reference populations, the links, the surfaces and this resampling scheme, and are not
universal confidence statements). A world in which an arm's weight is below
`replicate_minimum_arm_weight` or a variance is zero is invalid for that statistic and
counted. Intervals are `np.quantile` (`interval_quantile_method`) of valid worlds: the
decision uses `decision_quantiles`, so each bound is a one-sided 5% bound;
`reported_quantiles` are printed beside them. No Fisher-z interval on a stepped-up
correlation is used anywhere; the step-up happens inside each world.

**Declared departures, for root rulings.** *R12:* a world is a club-weight vector, not "one
coherent match-weight vector": units are players across two seasons and two providers, no
match is common to both sides, and the dependence the scheme must respect is by club.
Movers' destination values also share their destination club, which origin-club worlds do
not resample. On synthetic panels with a destination-club shock of a fifth of the
destination variance, origin-club worlds kept each directional verdict at the margin to 0.04
and 0.035 and covered the planted ratio in 0.90 of panels; product weights over origin and
destination clubs (a two-way scheme) doubled the interval widths. Destination-club worlds are
reported as a sensitivity, and the calibration plants the shock (`planted_null_destination_shock`).
DISSENT 4. *O5:* the persistence correlation is not a half-sample correlation, and two
contrasts (`league_change`, `bundesliga_destination`) and the public mover arm have fewer
than 100 analysed units; the percentile interval of the ratio, with the half correlations
stepped up inside each world, is used for all of them. DISSENT 5 asks the root to rule, as for
E-11, that O5 does not apply.

**Attrition table (always reported; the selection the estimand conditions on).** From the
StatsBomb outfield players at the origin floor: linked by tier, unlinked by E-11 outcome,
origin club shared or absent; among the linked: `ROLE_SAME` or `ROLE_CHANGED`; absent from
2017/18 lineups, by cohort, and by destination minutes at each of
`attrition_destination_minutes_steps`; the share of each cohort clearing the destination
floor. Counts are structure. The z-contrast of `attrition_contrast_rule` (mean origin `z` of
those who cleared the floor minus those who did not, among `ROLE_SAME` linked units with a
2017/18 appearance) is computed only for an admitted construct and a contrast that passed
rows 1 and 2. Public arm: the same counts from the 124 two-club players.

**Descriptive outputs are gated (`descriptive_outputs_rule`).** The `ROLE_CHANGED` stratum,
the sensitivities, the contamination curve, the rule comparison and the attrition
z-contrasts are computed only for a construct admitted by E-11 and a contrast that passed
decision rows 1 and 2; none reaches `decide`. A construct that is `NOT_ADMITTED` gets no
cross-provider statistic of any kind, and a contrast behind a failed gate gets none.

**Sensitivities (the `within_league` contrast of each construct that passed rows 1 and 2;
never a verdict;** `sensitivities`, `sensitivity_definitions`, each needing
`sensitivity_minimum_movers` movers and `minimum_stayers` stayers, else skipped and counted):
`single_club_movers`; `origin_club_survived`; `stayers_top_flight_throughout`;
`paired_links_only`; `all_movers_pooled`; `composition_matched`; `unmatched_ratio`;
`destination_club_worlds`; `player_bootstrap`; floor pairs in `sensitivity_floor_pairs` with
cells rebuilt.

**Where numbers go.** `results.local.json` (gitignored, under `local_output_root`): every
cross-corpus statistic, with the verbatim config. The `cross_corpus` `results.json`
(committed under `committed_experiment_dir`): provenance hashes, E-11's admission values,
gate booleans and reason codes, verdict tokens and flags; no number, no config echo. The
public `results.json` (committed under `public_experiment_dir`, written by the public stage,
which reads no StatsBomb file): tokens, the public arm's counts and aggregates, and nothing
from the `cross_corpus` arm. `analysis.md`: the aggregate research report, with the StatsBomb
logo and credit; counts below `small_count_suppression_below` are printed as "<5"; no
statistic on fewer than `minimum_units_for_any_statistic` units. E-11's registry token,
admission status, pooled and La Liga tokens and suffix are printed beside every result for a
construct (`admission_rule.printed_beside_every_result`).

**Same-club split persistence (public, descriptive, own gate).** `rho` over `P_S`, raw and
disattenuated, with its interval. Status `REPORTED` when `P_S` has at least
`same_club_split_minimum_units` units and `minimum_clubs_per_arm` clubs and the decision
interval is available, else `INCONCLUSIVE` with the first of `same_club_split_reasons`. It is
not a transport estimate and is reported whatever the mover gate says. A hosted page prints
the decision interval (`public_interval_printed`), never another.

## Sample gates and decision rule

**Analysed units (`analysed_unit_rule`).** `n_S` and `n_M` count, per construct and contrast,
the units of the arm (`cross_corpus`: `ROLE_SAME` only) with finite `z_pre` and `z_post`, and
for movers in a matched cell holding at least one such stayer. Counting finite values is
structure, not an outcome. The same `n` enters every gate, the false-link share and
`required_movers`, and the clubs gate counts the distinct origin club keys among those units.
The passage from cohort to analysed units is printed by reason.

**Gates, per construct and contrast (all must hold), in this order.**

| Gate | Rule | Reason code |
|---|---|---|
| vocabulary (`cross_corpus` only) | every name in the four origin folders is in E-11's lists | `UNKNOWN_VOCABULARY` |
| stayers | `n_S >= minimum_stayers` | `MIN_STAYERS` |
| movers | `n_M >= minimum_movers` | `MIN_MOVERS` |
| planning precision | `1/(n_S - 3) + 1/(n_M - 3) <= maximum_inverse_n_sum`, evaluated only when both counts exceed `inverse_n_sum_requires_counts_above` | `INVERSE_N_SUM` |
| clubs | distinct origin clubs in each arm `>= minimum_clubs_per_arm` | `MIN_STAYER_CLUBS`, `MIN_MOVER_CLUBS` |

`required_movers` (`required_movers_rule`) is `max(minimum_movers, ceil(3 + 1 /
(maximum_inverse_n_sum - 1/(n_S - 3))))`, null when `n_S` is at most 3 or the denominator is
not positive: 72 at `n_S` 313, 62 at 1,097 and 65 at 592.

**Decision table.** `L(.)`, `U(.)` are the decision quantiles; `m` =
`transport_ratio_margin`; `sm` = `standing_shift_margin`; `e` the false-link share of the
contrast (0 in the public arm). Comparisons follow `comparison_rule`. Evaluate in order; the
first match wins. A NaN or None never passes a row.

| # | Condition | Verdict (reason) |
|---|---|---|
| 1 | `cross_corpus` and the construct is not admitted | `NOT_ADMITTED` (first of `not_admitted_reasons`) |
| 2 | a gate fails | `INCONCLUSIVE` (first failing gate). Nothing was compared: no outcome statistic is computed for this construct and contrast |
| 3 | valid worlds for `rho_S` or `tau` below `minimum_valid_replicate_share` | `NOT_ESTABLISHED` (`INTERVAL_UNAVAILABLE`) |
| 4 | `L(rho_S) < stayer_correlation_floor` | `NOT_ESTABLISHED` (`STAYER_PERSISTENCE_BELOW_FLOOR`): the provider change and the two years leave nothing to transport |
| 5 | the interval of `tau*` is unavailable | `NOT_ESTABLISHED` (`CORRECTION_UNAVAILABLE`) |
| 6 | the pseudo-mover self-check fails | `NOT_ESTABLISHED` (`PIPELINE_SELF_CHECK_FAILED`) |
| 7 | the loss is evaluable (`false_link_rule`; always in the public arm) and `max(U(tau), U(tau*)) / (1 - e) < m` | `ORDER_REDUCED_BEYOND_MARGIN` |
| 8 | `min(L(tau), L(tau*)) >= m`, the interval of `D` is available, `-sm <= L(D)`, `U(D) <= sm`, and the placebo condition holds in both arms | `ORDER_PERSISTS_WITHIN_MARGIN` |
| 9 | `min(L(tau), L(tau*)) >= m` and the interval of `D` is unavailable | `NOT_ESTABLISHED` (`STANDING_SHIFT_UNAVAILABLE`) |
| 10 | `min(L(tau), L(tau*)) >= m` and the `D` condition fails | `NOT_ESTABLISHED` (`STANDING_SHIFT_OUTSIDE_MARGIN`) |
| 11 | `min(L(tau), L(tau*)) >= m` (the placebo condition did not hold: false or missing) | `NOT_ESTABLISHED` (`IDENTITY_STRESS_NOT_PASSED`) |
| 12 | `max(U(tau), U(tau*)) < m` | `NOT_ESTABLISHED` (`LOSS_NOT_ROBUST_TO_CORRECTIONS`): both bounds lie below the margin, and the false-link correction removes the loss or cannot be made |
| 13 | `max(L(tau), L(tau*)) >= m` or `min(U(tau), U(tau*)) < m` | `NOT_ESTABLISHED` (`RAW_AND_DISATTENUATED_DISAGREE`) |
| 14 | otherwise | `NOT_ESTABLISHED` (`INTERVAL_SPANS_MARGIN`) |

Decision vocabulary, exhaustive (`decision_vocabulary`): `NOT_ADMITTED`, `INCONCLUSIVE` (a
frozen gate failed and nothing was compared), `ORDER_PERSISTS_WITHIN_MARGIN`,
`ORDER_REDUCED_BEYOND_MARGIN`, `NOT_ESTABLISHED` (compared; neither conclusion met; a
published null, not evidence of absence). Rows 7 and 8 cannot both hold, since a lower bound
never exceeds its upper bound. Every reachable state maps to exactly one token and one reason.
When `L(tau)` exceeds `ratio_flag_lower_bound_above`, the flag `RATIO_ABOVE_ONE` is printed
beside the verdict (movers' ordering persisted more than stayers', beyond the interval, which
no planning value anticipates; the stayer arm is examined in `analysis.md`); it changes no
token. The public arm skips row 1 and the vocabulary gate.

**Registry token (`registry_token_rule`).** For the `cross_corpus` arm the registry token is
the decision token, with `_LEAGUE_UNCONFIRMED` appended to `ORDER_PERSISTS_WITHIN_MARGIN`,
`ORDER_REDUCED_BEYOND_MARGIN` and `NOT_ESTABLISHED` when E-11's admission status of the
construct carries that suffix; so the suffix reaches every label of the construct, as E-11
requires. The public arm's registry token is its decision token (`verdict_vocabulary`).

**Transport-rule verdict (secondary; own vocabulary; no product effect).** Computed only when
the contrast was compared and at least `transport_rule_minimum_movers` movers have every term;
otherwise `RULES_NOT_EVALUATED`. If any of the three difference intervals `d(R2, R1)`,
`d(R3, R1)`, `d(R3, R2)` is unavailable: `RULES_INTERVAL_UNAVAILABLE`. With `d(a, b)` the
paired mean squared-error difference `loss(a) - loss(b)` over movers: `R2` beats `R1` iff
`U(d(R2, R1)) < 0`; likewise `R3`. Neither: `NO_RULE_PREFERRED_OVER_CARRY_FORWARD`. Only `R2`:
`OWN_DEVIATION_PREFERRED`. Only `R3`: `DESTINATION_LEVEL_PREFERRED`. Both: `U(d(R3, R2)) < 0`
gives `DESTINATION_LEVEL_PREFERRED`, `L(d(R3, R2)) > 0` gives `OWN_DEVIATION_PREFERRED`, else
`CONTEXT_RULES_NOT_SEPARATED`. `R0` and `R1_raw` are reported, never selected. The verdict
chains up to three one-sided 5% comparisons with no correction, so under a global null its
family-wise error can reach about 0.14; that is printed beside it.

**Why these numbers, written before any outcome.**

- *Margin 0.80 on `tau`.* The one published stayer-against-mover contrast is a ratio near
  0.90 (unverified). A margin of 0.80 lets an effect of that size pass given enough data and
  refuses "half is lost". It is the lower bound, not the point, that must clear it.
- *Floor 0.30 on `L(rho_S)`.* Below it the denominator of `tau` is within a few resampling
  standard errors of zero at these sizes and a ratio is not an estimate of anything.
- *Standing-shift margin 0.25.* A quarter of a cell standard deviation; at the cell median
  that is ten percentile points. For `league_change`, `D` compares a player's standing among
  the players of his new league with his standing among those of his old one: a move to a
  league where his rate places him lower shows a negative `D` for reasons of league as well as
  of the player, and E-12 cannot separate them. A `league_change` survival therefore needs
  both an unbroken ordering and no such shift, the stricter reading; a shift alone returns
  `NOT_ESTABLISHED (STANDING_SHIFT_OUTSIDE_MARGIN)`.
- *The precision gate.* Under a normal approximation, `SE(tau) = tau * sqrt(v * ((1 -
  rho^2)/rho)^2 * (1/(n_S - 3) + 1/(n_M - 3)))` with `v = planning_variance_allowance`. The
  raw-ratio lower bound alone has planning power `planning_power` at `tau = 1` and `rho_S =
  planning_stayer_correlation` iff `SE(tau) <= (1 - m) / (1.6449 + 0.8416)`, which is
  `maximum_inverse_n_sum` (0.0179). That is all the gate guarantees (`planning_basis`). The
  survival row also needs the disattenuated bound, the `D` interval and the placebos, under
  club-cluster worlds: at the gate boundary (313 stayers, 72 movers) its simulated power at
  `tau = 1` is 0.56 at an observed stayer correlation of 0.75, 0.22 at 0.62 and 0.10 at 0.48
  (table below). No basis is recorded for 0.75 as an observed cross-provider, two-season
  stayer correlation: the blog value 0.77 is one season and one provider, and E-11's own
  planning puts an observed cross-provider correlation of a true 0.75 persistence at 0.45 to
  0.60. No basis is recorded for the allowance 1.06.
- *The gates on the `ROLE_SAME` counts (ROOT 2.8 Y3).* The draft stated the gates on all
  linked units; they are restated here on the confirmatory units. With the 24 `ROLE_CHANGED`
  stayers removed, `n_S` is 313 at 900 / 900 and `required_movers` is 72. `within_league`
  (about 177 movers if the 23 `ROLE_CHANGED` movers fall in proportion; inverse sum 0.0090)
  clears for the four constructs at 900 / 900, and for `chance_creation` (about 220 stayers
  and 108 movers; 0.0141) if no more than 37 stayers at 900 / 1,800 are `ROLE_CHANGED`.
  `league_change` had 72 linked movers of all roles and needs 72 `ROLE_SAME` ones: it clears
  only if no `ROLE_CHANGED` mover is a league-changer, and with about 66 it **is expected to
  return `INCONCLUSIVE (INVERSE_N_SUM)` for every construct**; it fails for `chance_creation`
  (32). `bundesliga_destination` fails (12); the public mover arm fails (29 against 62; 7
  against 65). The root's recount before registration settles these expectations; no gate
  moves with it.
- *One-sided 5% bounds.* The ordering ratio is tested for non-inferiority (one bound against
  the margin) and the standing shift for equivalence (two one-sided bounds); the same
  convention as the house lower-bound rule for reliability.
- *Multiplicity.* One primary endpoint. Each secondary verdict governs only its own label.
  Error is not controlled across constructs; nobody may count verdicts.
- *Constants with no recorded basis.* `minimum_clubs_per_arm` (40), `same_club_split_minimum_units`
  (200), `replicate_minimum_arm_weight` (20), `sensitivity_minimum_movers` (40),
  `attenuation_minimum` (0.05), `false_link_share_cap` (0.5), `age_band_edges_years` and
  `destination_minutes_band_edges`: no basis is recorded for these values.
  `minimum_valid_replicate_share` (0.95) is E-11's value, and `transport_rule_minimum_movers`
  equals `minimum_movers`.

**What the rule can and cannot detect (synthetic simulation of the revised rule, 200 panels
per cell and 400 origin-club worlds, at the `ROLE_SAME` planning sizes 313 stayers and 177
movers, equal reliability 0.88, a team share of 0.2, no false links, stayers matched; not
football data; the reviser's prototype, PIPELINE.md section 7).** Share of panels returning
the directional verdict:

| Observed stayer correlation | `tau` = 1.0, persists | `tau` = 0.9, persists | `tau` = 0.7, reduced | `tau` = 0.6, reduced | `tau` = 0.5, reduced |
|---:|---:|---:|---:|---:|---:|
| 0.75 | 0.93 | 0.48 | 0.32 | 0.82 | 0.99 |
| 0.62 | 0.65 | 0.24 | 0.19 | 0.50 | 0.82 |
| 0.48 | 0.30 | 0.09 | 0.08 | 0.24 | 0.54 |

At the margin itself (`tau` = 0.80, 400 panels) the two directional verdicts appear in 0.04
and 0.03 of panels. With `e` = 0.15 the loss verdict falls to 0.63 at `tau` = 0.5 and 0.22 at
0.6: an unverifiable link is paid for in the ability to call a loss. At `chance_creation`
sizes (220 / 108) survival at `tau` = 1 is 0.72, 0.34 and 0.11 at the three stayer
correlations; at the `league_change` gate boundary (313 / 72) it is 0.56, 0.22 and 0.10.
**The experiment can show persistence when it is close to complete and stayers persist at
about 0.6 or more, and can show a loss of about 40% or more. A true ratio near 0.9, the only
published figure, most often returns `NOT_ESTABLISHED`, and so does almost everything at the
stayer correlation E-11's planning makes likely. That is stated now so that a null is not
later read as a finding or repaired.**

## Consequence of each verdict, fixed now

**Records.** The `cross_corpus` verdicts become registry records under the E-11 precedent:
fifteen LOCAL records `E-12/<contrast>:<construct>` (`registry_records`), added with token
`PENDING` in the registration commit, labels on hosted pages and never gates, carrying no
figure and no digit. The `public_winter` verdicts become five PUBLIC records
`E-12/public_winter:<construct>` in `public_experiment_dir`, whose figures are those of
`registry_figures`, each with its own pointer and sentence. Each record's scope, claim token
(`ORDER PERSISTS`), non-claim, not-run statement and outcome statements are in config
(`registry_cross_corpus`, `registry_public_winter`, `registry_common`, `registry_outcomes`),
with `{construct}` filled from `construct_display_names`; every one passes the registry's
rules and the response boundary under `PENDING` and every token. Status mapping: a
persistence token is `ESTABLISHED` with limits; a reduction and `NOT_ESTABLISHED` are
`NOT_ESTABLISHED`; `INCONCLUSIVE` and `NOT_ADMITTED` are `INCONCLUSIVE`. A page may show less
than this allows, never more.

**Governing verdict for a Transfer Lab candidate (`product_governing_rule`).** Keyed on the
candidate's league (origin) and the squad's league (destination), in this order: origin
Germany, no E-12 subject (the fixed label `NO_ORIGIN_SEASON`: the corpus has no season with a
Bundesliga origin); destination Germany from an overlap league, `bundesliga_destination`;
the same league, `within_league`; otherwise `league_change` (two different overlap leagues).
The subject is `E-12/<contrast>:<construct>` for the five constructs. Before the run every
label is `PENDING`. Labels and addenda are `product_copy`, copied into product code verbatim
with a test tying them to this config; every hosted `cross_corpus` label carries the StatsBomb
logo, the data-source sentence and a link to the research note before any token other than
`PENDING` is served (ADR-0027 item 4; `PIPELINE.md` section 13).

| Registry token | Label (`product_copy.label`) | Carried-forward value | Sentence added after the break-even lead (`carry_over_addendum`) |
|---|---|---|---|
| `ORDER_PERSISTS_WITHIN_MARGIN` | "tested, movers' ordering persisted within margin" | `HEURISTIC`, unchanged | ordering is not level; the finding says nothing about the fraction |
| `ORDER_REDUCED_BEYOND_MARGIN` | "tested, movers' ordering persisted less than stayers' beyond margin" | `HEURISTIC`, unchanged | ordering is not level; nothing measured says how much of a rate persists |
| `NOT_ESTABLISHED` | "tested, not established" | `HEURISTIC`, unchanged | "Nothing measured here says how much persists." |
| `INCONCLUSIVE` | "not tested (sample gate)" | `HEURISTIC`, unchanged | same, naming the gate |
| `NOT_ADMITTED` | "not tested (provider agreement not established)" | `HEURISTIC`, unchanged | same, naming the experiment |
| any `_LEAGUE_UNCONFIRMED` token | the base label with `label_suffix_league_unconfirmed` | `HEURISTIC`, unchanged | as the base token |

Fixed under every verdict:

- The carried-forward value stays `HEURISTIC` with the sentence `product_copy.carried_value`,
  and every E-12 label is followed by `product_copy.estimator_note`. No verdict upgrades the
  value, applies a shrinkage, changes an injected number, or changes how candidates are
  grouped or ordered.
- A `cross_corpus` verdict is at most a label that links to the research note with the
  StatsBomb credit. It never unlocks a number-bearing panel and never parameterises a served
  computation. No `cross_corpus` number, interval, count or coefficient is served or
  committed in machine-readable form, and no sentence attached to it contains a number.
- The break-even carry-over fraction keeps its fixed lead: it predicts nothing and states how
  much would have to persist. It is never compared with an E-12 ratio (an ordering ratio
  across a population is not the fraction of a rate one player keeps), never coloured or
  worded as safe or unsafe, and never accompanied by "likely", "expected" or "projected". No
  E-12 sentence reads a verdict as evidence about how much of a rate carries over or says
  that an assumption is argued against (`product_forbidden`); only a PUBLIC experiment could
  support a carry-over statement beside the break-even (ADR-0023), and this one supports
  none. E-12 supplies no reference value for that display under any verdict: no tick, no band.
- **May the public arm ever show a number?** Three cases, fixed now. (1) Structural counts:
  always, as the figures `winter_movers_at_floor`, `winter_movers_required` and
  `side_floor_minutes`. (2) Same-club split persistence: when its status is `REPORTED`, as
  the figures `same_club_split_units`, `same_club_split_correlation`, `same_club_split_lower`
  and `same_club_split_upper`, whose sentences say these players did not change club. (3) A
  mover ratio: only under a public-arm verdict other than `INCONCLUSIVE`, which the exact
  count (29) rules out under this registration. A larger public same-provider mover sample
  needs its own registration; this gate is not re-floored.
- The planning page's row of a squad's own rates and Squad Lab's carry-over row keep their
  present lookups, which answer `NOT_REGISTERED` ("No registered protocol tests this
  claim."): E-12 tests the ordering of movers on five constructs, not a squad's own rates and
  not how much of a rate carries over, so that sentence stays true.
- The transport-rule verdict changes nothing in the product. It decides what a later,
  separately registered study would test.

## What this experiment cannot show

- That a quantity means what its name implies, or that a move works. Persistence of ordering
  is neither validity nor decision utility.
- Anything for players who were not used at the destination, left the five leagues, or could
  not be linked. About half of the 2015/16 regulars (597 of 1,228) are not linked and back at
  the floor in 2017/18; the estimate is conditional on surviving.
- Anything for players whose broad position differs between the two providers' labels. The
  confirmatory sample is selected on a label observed after the move; if redeployed movers
  lose their ordering more often, the verdict overstates persistence for movers in general.
  The `ROLE_CHANGED` shares of the two arms are printed beside each verdict, and their
  descriptive stratum is outside the graded ordering.
- The injected rate itself. The verdict is about E-11's harmonised estimator, which differs
  from Transfer Lab's in recipe, surface, club rule and minutes (Claim).
- A provider effect that differs between movers and stayers. Stayers absorb the provider
  change only if it does not interact with moving or with role mix; E-11 tests part of that,
  on other matches.
- What happened in 2016/17, how long a mover had been at the new club, whether a "stayer"
  was loaned out in between, or whether the manager changed.
- A redeployment inside a broad position. Wyscout has no per-match position.
- League strength. League-changers are compared on within-league standings; a shift there
  mixes transport with the two leagues' populations.
- The identity error on its own population. E-11 measures the link on players of the
  double-coded team sheets; its rates are applied to the 2015/16 rosters as an extrapolation,
  and the absent-partner rate approximates the rest.
- A within-provider, within-season mover effect at any usable precision (public arm), or a
  public split that coincides with each mover's own move.
- Any surface other than the three named; any estimator other than completed open-play
  passes; carries, duels, shots and defending.
- A ratio near 0.9 from a ratio of 1.0 (power table).
- Dependence through the destination club beyond the planted shock the calibration covers.

## Reproducibility and tests

Artifacts: protocol, config, pipeline and source hashes on LF-normalised bytes; E-11's
protocol, config and pipeline hashes, its results hashes, surface hashes and crosswalk digest
asserted equal to E-11's; the four origin folder digests; raw data digests and frame content
hashes (`teams.parquet` included); package versions and the machine, asserted equal to E-11's
(`dependency_machine_rule`); seeds; the calibration stamp; every statistic above, in the file
its tier allows. Aggregate only: no player, club or match identifier or name, no row per
player; every committed file under `maximum_results_bytes`.

The pipeline is written and tested on synthetic data only. Before any real outcome is
read, the frozen decision rule must classify planted panels at the rates in
`calibration_scenarios`: planted equivalence, a planted null at the margin, a planted loss, a
planted reliability artefact, planted false links with and without the adjustment (so the
guard is shown to act), absent stayer persistence, a planted gate failure in which no
statistic may be computed, a planted standing shift and a planted null standing shift at the
margin, a planted identity stress, movers and stayers selected on prior standing, a
destination-club shock with a coverage requirement, and three planted transport-rule worlds;
and it must recover the planted ratio within its tolerance. Structural requirements and
non-vacuity minimums are never relaxed by the reduced test (`calibration_tolerance_exempt`).
The calibration stamp is committed beside the protocol before `execute`. The runner refuses to
execute without that stamp, while any E-11 record it reads is `PENDING`, without E-11's
results, on another machine than E-11's, with a null folder digest, or without the commit that
first added this protocol, its config and its pipeline specification, unchanged since.

Tests must cover: club keys and the crosswalk assertion; the modal broad class and its ties;
`ROLE_SAME` and its exclusion from every verdict-bearing statistic; tier precedence and
conflicts; main club, ties and second-club cases; every cohort boundary; floors and minimum
denominators per construct; cells and normal scores (ties, minimum cell, holes); halves and
half floors; leave-one-out levels (own value excluded); matched weights; each statistic
against an independent brute-force oracle; shared worlds across constructs and contrasts;
row-order invariance; placebo pools, counts and seed derivation; the false-link formula and
the loss-evaluable rule; stayer-only fitting (changing any mover outcome leaves every
coefficient unchanged); identical rows across rules; every decision-table row and boundary;
fail-closed on NaN and None; the admission function over E-11's whole vocabulary; no statistic
computed behind a failed gate or for a construct that is not admitted, descriptive outputs
included; the governing-contrast mapping over all 25 league pairs; the public stage running
with no StatsBomb path present and its surface hash unchanged; aggregate-only keys, size and
licence-guard patterns; no number in the `cross_corpus` `results.json`; nothing written
outside the declared output files; refusal to run before the protocol commit, while E-11 is
`PENDING`, or twice.

---

*Committed before running. Local results in `results.local.json`, tokens in the
`cross_corpus` `results.json`, the public arm in its own `results.json`, interpretation in
`analysis.md`. If any of them contradicts this document, this document wins.*
