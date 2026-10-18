# E-10 — is where a team concedes a property of the defending team?

> **DRAFT. Not frozen, not registered, not run.** Written by one designer during the north-star build; attacked on 14 October 2026 by three adversarial reviewers (statistics, football data, constitution) and revised the same day; independently audited on 16 October 2026 in four scopes, with every claimed blocker put to a refuter, and revised again the same day ([REVIEW-RECORD.md](REVIEW-RECORD.md) lists every finding of both rounds and its disposition); the root's rulings on that audit (ROOT 2.9, Z1 to Z3) were then applied. As ROOT 2.9 Z4 requires, a second audit read that revision on 16 October 2026 in the same four scopes; its one claimed blocker (the synthetic generator's draw order) was confirmed by a refuter, and every finding was applied, or applied with a stated variant, in a third revision the same day. A third audit read that revision in the same four scopes (dated 16 October 2026); it claimed no blocker, and its majors and minors were applied, or applied with a stated variant, in a fourth revision on 18 October 2026, which also applied ROOT 2.9 Z5, the root's ruling on the second audit's question, so that ROOT 2.9 Z1 to Z3 and Z5 are now applied (REVIEW-RECORD.md, Third audit). That fourth revision has not itself been audited; as with E-11, E-10 is called READY only after an audit of a revision confirms no blocker. No outcome named here has been computed. It becomes a protocol only when an audited version is committed under `experiments/preregistered/` in a single commit that precedes any run (`PIPELINE.md` section 13). Section and file references such as ROOT 2.5 point to [ROOT-DECISIONS.md](../../ROOT-DECISIONS.md); see [README](../../README.md) for the working notes it cites.

**Commit this plan, `config.json`, `PIPELINE.md` and `descriptor_test_vectors.json` before
any E-10 outcome is computed. Nothing in the four may change once the first outcome is
observed.** This is a prospective analysis plan on **reused public data**, not a claim of
untouched data collection. Every threshold, seed, window, list, grid, gate and served sentence
lives in `config.json` and is named here by its key; a number that appears only in this prose
is a defect. Deviations are recorded in `analysis.md`, never silently adopted. The pipeline is
developed and tested on synthetic data only; the root integrator executes the real run once,
plus one determinism re-run.

## Claim and unchanged boundaries

Seven subjects: six descriptors (a primary and five secondaries) and one level subject. For a
descriptor the claim under test is the conjunction of three questions ROOT 2.2 asks:

> On eligible later matches of the season, the defending team's prior history adds
> out-of-sample information about the composition of the declared counts it concedes (or
> records), beyond the attacking team's own history, the total and venue, and for a
> descriptor with mirror pairs including which side; the composition repeats across two
> halves of the team's matches that each hold one meeting with every opponent; and it is more
> than team strength measured by points, goals and pass share.

For the level subject:

> On eligible later matches, the defending team's prior history adds out-of-sample information
> about how many final-third entry passes it concedes per unit of window time, beyond the
> attacking team's own volume and venue, and that volume repeats across two halves of the
> team's matches that each hold one meeting with every opponent. It is not claimed to be more
> than team strength.

Neither claim is persistence in time: the two halves interleave August and May (Reliability
below). How a team-season value carries from the first part of the season to the second is T1,
which is reported and gates nothing.

"Shape" below means the composition of a declared count vector; "level" means how many. They
are separate claims with separate models and separate verdicts. The primary is
`conceded_f3_entries_by_channel`; the experiment's headline is the primary's token with the
level subject's token beside it.

**Not claimed, under any verdict.** That a channel a team concedes through is defended badly:
a team can leave a channel open on purpose, and event data cannot separate that from failing
to close it. That attacking that channel pays. That the composition persists into another
season, another squad or another coach. That a specific pair of teams interacts. Anything
about a player. Anything about shot conversion: the corpus has no expected-goals value and no
shot end coordinate (its goal-zone tags place shots on target, not on the pitch). That a
level difference is a property of the team separate from its strength.

**Unchanged.** No key enters `features/spec.py::SPECS` or `CONSTRUCTS`. No Player Lab,
Match Lab or XI Lab output, endpoint, hash or evidence gate changes. E-07 and E-08 stay
closed at their published results. Passing earns a labelled descriptor in Opponent Lab,
never a requirement, an optimiser weight or an ordering of teams (R1, R4). Registration adds
seven PUBLIC records, token `PENDING`, to `galactico/domain/verdicts.py` (product section).

## Prior knowledge

ROOT 2.5 (4.4) asks for a paragraph built from section 4.4 of the critique, a working note
that is not in this repository (north-star README). What the design relied on, with no
source recorded here beyond the designer's reading: published team-level work finds
repeatable between-team differences in how much a team concedes, which is why the level is a
separate subject; no published study was found that tests where a team concedes against an
attacker-only baseline; the provider reports no positional accuracy and no inter-operator
agreement for its event locations (ADR-0004 cites a published similarity of about one half
for the two providers' action sequences on identical matches), which is why three channels
are used and nothing finer; and team strength is the obvious rival explanation of any
defender term (ROOT 2.2). Nothing in this paragraph was computed on either corpus.

## Prior exposure of the data

| What was already seen | Where | Consequence here |
|---|---|---|
| All five Wyscout leagues, player-level constructs | Stage 1, 1B, 1C; E-02 (Italy primary) | No league is untouched. None of those analyses computed a team-conceded quantity |
| Spain 1 Nov to 28 Feb as development rows; Spain and England 1 Mar to season end as evaluation rows; target = first-30-minute positive completed-pass xT with an `opponent_mean` conceded term in the baseline | E-07, E-08 | 312 of the 917 evaluation matches here (624 of 1,834 team-match rows, 34.0%) carry that exposure: Spain 211 matches (88 as E-08 development, 123 as evaluation), England 101. The 69 Spain November to December matches in this development window were E-07/E-08 development rows. The exposure was to a conceded level of xT, never to a channel composition. A conceded level is the same kind of claim as the level subject's, so the level shares that exposure: its pooled L1 over `unexposed_leagues` is reported beside it (Reported without a verdict), and (Lb), four of the five leagues, cannot hold unless at least two of the three unexposed leagues have L1 below zero |
| The xT surface E-07 and E-08 fitted | E-07 (`xt_training_league` Spain), E-07 and E-08 (`xt_cutoff` 2017-11-01) | A league-level map of where Spain's passes started and ended before 1 November 2017, the expected-threat values of the pitch cells. It is league-level, holds no team and no lateral split by team, and no quantity here reads it |
| StatsBomb 2015/16, player-level constructs | E-01, Stage 1C | The replication corpus is not untouched. No team-conceded quantity was computed on it |
| E-11, registered 14 October 2026, not run | `experiments/preregistered/E-11-provider-agreement/preregistration.md` | Its prior-exposure section prints review-time counts one provider at a time: for Wyscout England 2017/18 the number of non-penalty shots and the number in the provider-drawn box, which is the league-level split behind S3 for one league of this corpus; the same split for one StatsBomb 2015/16 league of the replication arm (not repeated here); that every team-match of Barcelona's double-coded La Liga matches has at least ten final-third entries; and, on the public side of those matches, that 75 of 76 team-matches (122 of 128 at the World Cup) have at least five open-play shots. These are league or club totals, not a composition by team, and the model's league term removes a league's share |
| E-11's pipeline and results | E-11 `PIPELINE.md` section 4 | Built on synthetic data and its acceptance stamp committed (f6f9184); not run; no real value computed. On Barcelona's 36 double-coded La Liga matches, both sides, it computes per team-match final-third entries by left, centre and right, box entry passes, defensive actions by third and `high_zone_defensive_action_share`. Its committed `results.json` will hold tokens only; its `analysis.md` prints agreement statistics and per-provider means and spreads over team-matches, and no team row. E-10 is to be registered before E-11's results are committed; if E-11 runs first, the registration commit says so and states whether its analysis was read, and by whom, and the frozen `reuse_disclosure` names that case |
| Match Lab | every served match, all five leagues | Per team-match recorded actions, completed passes, shots, key passes, interceptions and clearance sub-events are served on the team profiles of every match, and so are each team's `progression` (positive completed-pass xT gain), `progression_per_action` and `chance_creation`, and each team's xT gain in five-minute bins (`threat_flow`). The opponent's `progression` is a per-match conceded level of xT, the kind of exposure the E-07/E-08 row describes, and it is visible for every match of every league, Italy, Germany and France included: "unexposed" below means that no E-07/E-08 analysis scored those leagues, not that no conceded per-match value of them is served. Every one of these is per match, never aggregated by team or season. Also served: each team's wide-channel and half-space pass-origin shares (`width`, completed-pass origins at `y < 0.21` or `y > 0.79`, and `half_space_share`): the opponent's per-match share is a wide-against-the-rest split of what the team conceded, by pass origin over the whole pitch, not by lateral third and not of final-third entries; the start coordinates of every shot of both teams (the shot map), which are S3's raw inputs for each team-match; and the mean pass locations of each player (the passing-network nodes). No conceded split by lateral third, no defensive-action location and no team-season composition is served |
| Sidecar audit counts | `tests/test_sidecar.py` (`AUDIT`), pinned per league | Structure only, league totals. The red-card (tag 1701) and second-yellow (tag 1703) event records against the sheet's red-card entries are Spain 29 + 42 against 71, England 22 + 19 against 39, Italy 46 + 45 against 91, Germany 21 + 22 against 43, France 53 + 33 against 87. Exact in three leagues, which supports the assumption that the sheet's `red_minute` carries a second-yellow dismissal; the England and France differences are why the check before registration is a share, not a zero (Match validity). The same pinned dict holds per league the goal tags (and those on save rows), own goals, the open-play, free-kick and penalty shot totals (S3's league totals, with no inside-the-box split), and the counts of starts and ends at a corner (the rows `wy_location_sentinels` drops), with event, tag, substitution and match counts. None is a team composition |
| Structure only: entry-pass counts per team-match (median 37 to 39.5 by league), state-filter survival (79.0% in Spain with dismissals; about 84% in five leagues from goals alone), share of entries on a lateral-third edge (about 3%), calendars, coach-id counts, mean pass `y` by listed position in 40 StatsBomb files | reconnaissance, critic, this design | Exposure and structure only. No channel split by team, no reliability, no persistence, no loss was computed. Sample gates were set with the entry-pass counts known; they are not expected to bind for the primary and S1. For S2 and S3 no count was looked at, and the events minimum may bind there |
| `synthetic_gate.league_composition` | the gate's generator | Its source is not recorded by the designer and the reviser could not establish it (`league_composition_source`). If it was read from the corpus it discloses a league-level share of conceded entries by lateral third, which the model's league term removes; no team-level split |
| Simulations | the designer's prototype (`_work/prototype.py`, logs `_work/rates_*.log`); the reviewers' and the reviser's scripts of 14 October 2026; the auditors', refuters' and revisers' scripts of the two audits of 16 October 2026 (among them `twotail_sim.py`, `twotail_invariance.py`, `lattice_holm.py`, `check_results_contract.py`, `draw_order_4_1.py`, `estimator_walk.py`, `replication_walk.py`); the third audit's and its reviser's (among them `split_time.py`, `drift_r1.py`, `mod4_check.py`, `draw_order.py`, `pairs.py`, `split_rerun.py`, `split_balance.py`, `two_pass.py`) | Synthetic only; none read `data/`. None of these files is committed |

Italy, Germany and France (535 evaluation matches, 1,070 rows) carry no E-07/E-08 exposure.
They are reported as a separate pooled estimate and enter the decision rule as criterion (f).

## Data, cohorts and exclusions

Corpus: public Pappalardo/Wyscout 2017/18, `leagues`, 1,826 matches, 3,652 team-match rows,
98 teams. Tournaments are excluded: no round-robin. Inputs: the neutral frames `actions` and
`matches`, read through `galactico.storage.public.load_public`; from the tag sidecar
(`galactico.ingestion.sidecar`, ADR-0028) the `events` columns `goal_incident_columns` and
`card`, joined only through `sidecar.attach`, the `matches` score columns and the `squads`
column `red_minute`. A sidecar that is absent, stale, or whose join is not one to one stops
the run before it starts (`PIPELINE.md` section 7.2); it is never a per-match exclusion. No
lineup minutes are read: they are nominal.

**Row.** One row per team per match: the *unit* is the team whose descriptor is read, the
*context* is its opponent. For conceded descriptors the unit defends and the context
attacks. A match yields two rows.

**Prior.** A row dated `t` may use only rows whose calendar date is strictly before `t`: the
date as the provider records it (Wyscout `dateutc`; StatsBomb `match_date`, a local date with
no time or zone), normalised to the day. `gameweek` is never read.

**Development** = rows dated before `evaluation_start`. **Evaluation** = rows on or after it
and before `end`. Evaluation forecasts use an expanding window: every prior row, development
included.

**Match validity** (`validity_reasons`, decided once per match for every window and every
model, `validity_scope`). A match is invalid, with the first reason that applies:
`period_missing` (a period of `regulation_periods` has no row); `clock_invalid` (a
non-finite or negative clock in regulation; it cannot fire on either provider: the adapter
writes a missing Wyscout clock as 0.0, so on this corpus a missing clock is indistinguishable
from the kick-off, and the replication's reader parses each timestamp or raises, which makes
the replication `REPLICATION_INCONCLUSIVE (FAILED_RUN)`; the reason is kept as a guard);
`goals_mismatch` (the full-time goals from events under `goal_incident_rule` differ from the
sheet's score); `dismissals_mismatch` (`dismissal_check`: per team, the players with a
dismissal card in the event record differ in number from the sheet's players with a red-card
minute; an event that has no position is not in the event record, so a card it carried is
missing there, and the check catches it). Invalid matches are counted by reason and never
repaired. One England match is known to lack a scoring event and will be excluded. A
team-match with no row on the sheet stops the run before it starts (`PIPELINE.md` section 7.2).

The dismissal check assumes that the sheet's `red_minute` carries a second-yellow dismissal.
Before registration the root runs a structure-only count on the corpus
(`verified_by_root_before_registration`, ROOT 2.9 Z2); it computes no outcome, and its counts
and share per league are recorded in the registration commit. It tests the assumption: per
league, the share of players with a second-yellow event card whose sheet `red_minute` in that
match is not null. It holds when that share is at least
`dismissal_assumption_minimum_share` in every league: a sheet convention that drops second
yellows gives a share near zero, data gaps give one near one. If it fails,
`dismissal_check_fallback` replaces the rule and the draft is audited again. The residual
mismatches, in either direction, are what `dismissals_mismatch` is built to invalidate; their
counts by league are stated in the registration commit, and only G1 bounds them.

**Goals.** `goal_incident_rule`: a row with the sidecar's own-goal tag is a goal of the other
team; otherwise a row with `goal_on_scoring_event` (the goal tag, not on a save attempt, not
in a shootout) is a goal of the acting team. Own goal first, so no row is credited twice.
This is Match Lab's timeline rule (the goal flag on any row other than a save, own goal
first); the draft's narrower rule (shot and set-piece rows only) was dropped so that one
definition of a goal serves both.

**Results and strength.** Points and goal difference come from the sheet for every match,
valid or not (`strength_tercile_source`, `strength_covariate_sources`); validity governs
event-derived quantities only.

**Eligibility.** A row is eligible when its unit and its context each have at least
`minimum_prior_matches` prior valid matches. Ineligible rows still feed later histories.
No exclusion on team, strength, coach or venue. Promoted clubs and coach changes are not
adjusted for: a team is one unit for the season. The sidecar's match table carries both
coach ids (49 of 98 teams show more than one in the raw sheets, a reconnaissance count whose
reading of the raw value 0 was not recorded); this experiment does not read them beyond
reporting in coverage the number of teams with more than one distinct non-null coach id (the
sidecar writes a raw 0 as null, and a null is never counted as an id) and, separately, the
number of teams with at least one null coach id; no criterion reads either, and a
coach-tenure analysis is in `not_run_in_this_experiment`.

## Measurements — frozen

**Frames.** Every neutral coordinate is in the acting team's attacking frame, `x = 0` its own
goal line. `y = 0` is the acting team's left by each provider's coordinate convention. For
StatsBomb it is checked by the orientation check before any replication loss (`PIPELINE.md`
section 6). For Wyscout the repository already assumes it, without a check on the data: the
registered E-11 frame (`y = 0` the attacker's left, both providers), XI Lab's side pass-origin
rates and Match Lab's pitch all read it so, and the names on this protocol's panels agree with
those shipped labels; it was not checked here because the Wyscout role code does not tell left
from right. No verdict depends on it. Exchanging left and right everywhere exchanges `def_left`
and `def_right` and negates the side-balance coordinate; criteria (a) to (f) are symmetric in
the parts, and (g) reads both tails of every coordinate (Validity against strength), so every
criterion is unchanged and only the names on the panel would be exchanged. The defending
team's left is the acting team's right. That mirror is written once,
in the descriptor definition: part `def_left` reads the opponent's `att_right` column.

**Locations.** A Wyscout start or end at exactly a point of `wy_location_sentinels` is not read
as a location: the sidecar records such raw corners as facts and says nothing of their meaning.
The rule is Wyscout's only; a StatsBomb location at the far corner is a real one. On both
providers a coordinate outside `coordinate_range` or non-finite is not a location. An event set
that reads a location drops such rows and the count dropped is reported per event set. The
adapter writes a missing Wyscout coordinate as 0, which lands on a touchline or goal line and
is caught only when both coordinates sit at a sentinel. The two sentinels lie on one diagonal,
`(0, 0)` and `(1, 1)`, so the location rule, unlike the lateral rule, is not its own mirror
image: in the attacking frame an end at `(1, 1)`, the attacker's far right corner (`att_right`,
the primary's `def_left`), is dropped, while an end at `(1, 0)` is kept as `att_left`, and
likewise for the start of a box entry (S2); an end at `(0, 0)` can never be a final-third
entry. A league-wide offset of this kind is absorbed by `pi`; the drops are reported per event
set and per sentinel point, so a loss that falls on one side is visible.

**Cuts** (`fraction_rule`): a cut the config gives as `[n, d]` is the float64 quotient
`n/d`, compared with float64 coordinates. On the Wyscout lattice `x = 0.84`, `y = 0.19` and
`y = 0.81` are inside the box. On the StatsBomb scale (raw coordinates at the provider's 0.1
resolution divided by `sb_location_scale`) `x = 80/120` is in the attacking third, as an exact
rational also says; no raw `y` falls on a lateral cut, so `y = 26.6/80` is left and
`y = 26.7/80` centre. At every cut, float64 and exact rationals agree on both lattices.

**Measurement window** (`close_11v11`, primary). An event counts when, among incidents with
a strictly earlier `(period, seconds)`, there is no dismissal (`dismissal_cards`, either
team) and the absolute goal difference is at most `max_abs_goal_difference`. Regulation
periods only. The window is "before any dismissal", not "eleven against eleven": a side left
with ten by an injury after its substitutions are used stays in it, and a card recorded on a
bench player closes it; every served phrase says so. `window_seconds` is the measure of that state on each period's `[0, last
event second]`. This conditions on events after kick-off: results describe behaviour in
comparable states and are not forecasts for arbitrary states. `all_states` is a reported
sensitivity only, on the same valid matches.

**Event sets** (acting team's frame; a row is counted once).

| Key | Rows | Location rule | Phrase |
|---|---|---|---|
| `f3_entry_pass` | `type == "pass"` and `success == True` | start `x < 2/3`, end `x >= 2/3`; start and end are locations | completed open-play passes |
| `box_entry_pass` | same | end inside the box (`penalty_box_wy`), start not inside it; start and end are locations | completed open-play passes |
| `open_play_shot` | `type == "shot"` | start is a location | shots not taken directly from a set piece |
| `defensive_action` | ground defending duel record, or any row with the interception flag, or `type == "foul"` with subtype `Foul` | start is a location | recorded defensive actions (ground defending duel records, interception-tagged events and fouls recorded as Foul; each event once) |
| `defensive_action_high` | same | start `x >= 2/5` | same |
| `own_60_pass` | `type == "pass"`, any outcome | start `x <= 3/5` | open-play pass attempts |

`open_play_shot` includes headers and shots after corner and free-kick deliveries; only
shots taken directly from a set piece (direct free kicks, penalties) are out. Lateral thirds:
`y < 1/3` acting team's left, `y > 2/3` its right, otherwise centre (on the Wyscout lattice:
0 to 33, 34 to 66, 67 to 100; the rule is its own mirror image).

**Descriptors.** Each is a composition of counts read from the unit's row. Executable
definitions, sentences and fingerprints are in `galactico/features/team/descriptors.py`;
`descriptor_test_vectors.json` freezes payload, fingerprint, sentence and column names, the
fingerprints are also `descriptor_fingerprints`, and the runner refuses a mismatch.

| Role | Key | Label | Parts (unit's row) |
|---|---|---|---|
| Primary | `conceded_f3_entries_by_channel` | Share of final-third entry passes conceded, by lateral third (defending team's frame) | opponent `f3_entry_pass` by lateral third of the **end**: `def_left`, `def_centre`, `def_right` |
| S1 | `conceded_f3_entries_wide_share` | Share of final-third entry passes conceded in the two outer lateral thirds | `wide` = `def_left + def_right`; `centre` |
| S2 | `conceded_box_entries_by_origin_channel` | Share of penalty-area entry passes conceded, by lateral third of origin (defending team's frame) | opponent `box_entry_pass` by lateral third of the **start** |
| S3 | `conceded_shots_inside_box_share` | Share of conceded shots not taken directly from a set piece that start inside the penalty-area rectangle | opponent `open_play_shot` starting inside the rectangle; outside it |
| S4 | `defensive_actions_by_pitch_third` | Share of recorded defensive actions by pitch third (team's own frame) | own `defensive_action` with start `x < 1/3`; middle; `x >= 2/3` |
| S5 | `high_zone_defensive_action_share` | High-zone defensive actions as a share of those actions plus opponent pass attempts in the opponent's own 60% | own `defensive_action_high`; opponent `own_60_pass` |

The labels follow ROOT 2.5 (H14-H21). S5 is `1 / (1 + passes per action)`, a monotone
transform of opponent passes per recorded high-zone defensive action; it is never labelled
PPDA, because the Wyscout action set differs from every published one, and it keeps E-11's
name for the same `D / (D + P)`. S4 is where recorded actions happened, which follows the
ball; it does not show where the team's defensive line stands. **Level subject**
`conceded_f3_entries_per_90`: the primary's total per `exposure = window_seconds /
exposure_unit_seconds`.

Log-ratio coordinates of a composition `p` with parts in the order above: for three parts
`z1 = sqrt(1/2) ln(p1/p3)`, `z2 = sqrt(2/3) ln(sqrt(p1 p3)/p2)`; for two parts
`z1 = sqrt(1/2) ln(p1/p2)`. For the primary, `z1` is side balance and `z2` is wide versus
centre. Counts are never converted to per-match shares before modelling.

**Not run here** (`not_run_in_this_experiment`): no xT-weighted version, nothing that needs a
possession segmentation, no set-piece or transition quantity, no finer grid, no coach-change
adjustment.

## Models and baselines — frozen

All quantities at date `t` in league `L` use prior valid rows only. `n` is a row's part
vector, `N` its total, `K` the number of parts, `c` a context team, `u` a unit team, `v`
whether the context team is at home.

- League composition `pi = (S + a) / (S_total + a K)`, `a = league_prior_pseudocount_per_part`,
  over all prior league rows; by venue `pi_v` likewise; venue offset `nu_v = ln pi_v - ln pi`.
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
`pi`, `pi_v`, `nu_v`, `A_c`, `A_c^(-u)`, `e`, `O`, `E` and `delta_u`, and the level model's
`lam_v`, `lam`, `rA_c`, `rA_c^(-u)`, `rD_u` and `rD_peers` (the last from the peers' pooled `O`
and `E`), are computed by one estimator on the product side,
`galactico/features/team/estimator.py`, which the research pipeline imports and Opponent Lab's
panel calls; no second implementation exists (ROOT 2.9 Z3; `PIPELINE.md` section 3.8). B5, the
peer grouping and every loss and deviance stay in the research engine. The estimator's source
hash is among the pinned source hashes, so an edit to it after registration is visible.

**Baseline ladder.** A count vector with independent Poisson parts factorises exactly into
a level loss on `N` and a shape loss given `N`. Every rung is a (level, shape) pair. The shape
component is reported for every rung of every descriptor, and the level component for every
rung of the level subject (the primary's total), pooled and by league; S1 to S5 have no level
component.

| Rung | Level of `N` | Shape given `N` | Represents |
|---|---|---|---|
| B0 | league-by-venue rate | `pi_v` | no team information |
| B1 | context-only rate | `A_c exp(nu_v)` | "it is whatever the attacker does" |
| B2 | context and unit rates | `pi_v` | the defender matters for how much, not where |
| B3 | context rate times the pooled ratio of the unit's strength peers | `A_c exp(nu_v + delta_peers)` | "it is just being a stronger or weaker team" |
| **B4** | B2 level | `A_c exp(nu_v)` | **attacker shape times defender level: the decisive null** |
| B5 | unit's last-`raw_persistence_matches` rate, smoothed toward the league rate by `log_ratio_smoothing_per_part` events (`raw_persistence_level_rule`) | that composition, `+ log_ratio_smoothing_per_part` per part | raw persistence: is shrinkage doing the work |
| B6 | B2 level | candidate with the mirror pairs of `delta_u` swapped | mirror placebo |
| B7 | B2 level | candidate with `delta` of a permuted donor, one per `permutation_seeds` | identity-link stress test |
| Candidate | B2 level | `A_c exp(nu_v + delta_u)` | |

Peers: the other teams in the unit's league and strength tercile at `t`. Terciles: teams
with at least one prior match on the sheet, ordered by descending prior points per match,
then descending prior goal difference per match, then ascending team id
(`strength_tercile_key`, from the sheet); tercile = `(strength_tercile_count * position) //
count`, position 0-based. `delta_peers` uses the peers' pooled `O` and `E`.

**Level model.** `y = N`, `e` = exposure. League-by-venue rate `lam_v = sum y / sum e`.
Context ratio `rA_c = (Y_c + kA') / (X_c + kA')` with `X_c = sum_j e_j lam_{v_j}`; unit
ratio `rD_u = (O_u + kD') / (E_u + kD')` with `E_u = sum_j e_j lam_{v_j} rA_{c_j}^(-u)`.
B1 mean `e lam_v rA_c`; B2 mean `e lam_v rA_c rD_u`. B3 mean `e lam_v rA_c rD_peers`, with
`rD_peers = (sum_g O_g + kD') / (sum_g E_g + kD')` over the unit's peers `g` (`peers_level_rule`).
B5 mean `e (Y5 + s) / (X5 + s / lam)`, with `Y5` and `X5` the unit's conceded events and exposure
over its last `raw_persistence_matches` valid rows, `lam` the league rate over both venues and
`s = log_ratio_smoothing_per_part` (`raw_persistence_level_rule`), so a unit with no conceded
event in those rows keeps a positive mean. B4, B6, B7 and the candidate carry the B2 mean.
Under `context_only` (`rD = 1`) the B2 and B3 means are B1's. Loss: Poisson deviance.

**Losses.** Shape: multinomial log loss, `-sum_k n_k ln p_k`, summed over rows and divided
by the number of events (ratio of sums, never a mean of per-match ratios). Level: mean
Poisson deviance per row with positive exposure. Both are strictly proper.

## Frozen selection procedure

Per descriptor, on eligible development rows of all five leagues pooled, by walk-forward
prediction inside the development window (`selection_scope`):

1. `kA` = the value of `shrinkage_grid` with the smallest pooled shape loss of B4.
2. With `kA` fixed, `kD` = the candidate with the smallest pooled shape loss among the
   grid and the boundary `context_only` (`delta = 0`, the candidate **is** B4).

Ties (`selection_tie_rule`): the tie set is every candidate whose pooled loss is at most the
smallest pooled loss plus `selection_tie_tolerance`; `context_only` if it is in the set,
otherwise the largest value in the set (more shrinkage). Grid order cannot decide a tie.
The level constants (`level_selection_rule`): `kA'` on the pooled B1 deviance over the grid;
with `kA'` fixed, `kD'` on the pooled B2 deviance over the grid and `context_only` (`rD = 1`,
B2 **is** B1); the same tie rule. `kA` is frozen for evaluation and for every placebo's own
re-selection of `kD`; `kA`, `kD`, `kA'`, `kD'` are all frozen for the replication. No other
tuning exists: no feature search, no window search, no per-league constants. Selecting among
ten candidates on about a thousand rows can overfit; the evaluation window exists for that
reason.

If `context_only` is selected, the candidate's and the mirror's loss arrays are B4's and every
P1 and M1 difference is exactly zero. Then (a), (b) and (f) are false (pooled P1 has the
p-value 1 by `p_value_rule`, and no estimate is below zero), and so is (d) for a descriptor with
mirror pairs (M1's p-value is 1). Every other criterion is evaluated as defined: (c) compares
the zero with each placebo's own re-selection and can hold; (d) is true for a descriptor
without mirror pairs. The token is `ADDED_INFORMATION_NOT_SHOWN` whatever they return, and
the reasons list what was computed. For the level, `context_only` makes (La) false by its
definition and (Lb) false because every L1 is zero.

## Evaluation and reporting

**Estimands** (per descriptor; all on eligible evaluation rows unless stated).

| Id | Estimand | Definition |
|---|---|---|
| P1 | utility (primary) | shape loss of the candidate minus B4, per event. Negative: defender history helps |
| L1 | level utility | deviance of B2 minus B1, per row (level subject only) |
| M1 | side information | shape loss of the candidate minus B6, per event (descriptors with mirror pairs) |
| P2 | calibration | per coordinate, the event-weighted slope through the origin of the observed log-ratio residual (row composition with `log_ratio_smoothing_per_part` per part, minus B4) on the coordinate of `delta_u` computed without any match against the row's context team, rows with at least `calibration_minimum_events_per_row` events. 0 = no defender shape, 1 = correctly scaled |
| R1 | reliability (gate) | split-half of the team-season descriptor, per coordinate, stepped up by Spearman-Brown |
| T1 | persistence (reported) | per coordinate, correlation over teams of the league-centred development-part value with the league-centred evaluation-part value, each from the team's valid rows dated in that part, teams with at least `minimum_half_matches_per_team` valid rows in each part (`persistence_rule`), no step-up: persistence in time under real squad and coach change |
| V1 | validity against strength | the confound audit of the team-season coordinate on `strength_covariates` |
| I1 | pair interaction (reported, primary only) | correlation between the two meetings of a directed pair of the row's log-ratio coordinates `basis @ ln((n + s) / (N + s K))`, `s = log_ratio_smoothing_per_part`, residualised on an additive context, unit and venue fit within league, meetings with at least `interaction_minimum_events_per_meeting` events |

**Resampling: one shared world** (R12). Every bootstrap interval and bootstrap p-value of
every descriptor, the level subject, every estimand, every subset (a league, the unexposed
leagues) and both windows is computed in one set of worlds. R1's bound is analytic and V1's
permutation reference has its own stream (below); neither is drawn from the world. Clusters are
`world_cluster`, (league, calendar week of the match date), labelled as the house
`paired_week_interval` labels a week, `str(pd.Timestamp(date).to_period(calendar_week_rule))`;
strata are `world_strata`, league × part (`development`, `evaluation`), so an evaluation
estimand always draws each league's own number of evaluation weeks. `world_draw`: one generator, `default_rng(seed + seed_streams.season_world)`, draws
for each stratum of `m` clusters `bootstrap_replicates` vectors of `m` cluster indices,
counted into multiplicities; a match takes its week's multiplicity, and both rows of a match
share a date and so a weight. A replicate's statistic is the ratio of the weighted sums of
the estimand's numerator and denominator over the clusters it touches; a subset is the
restriction of the same replicates to its clusters. A replicate whose denominator is zero is
a hole: it is left out of that estimand and counted. The world's fingerprint (`PIPELINE.md`
section 4.3) is in `results.json`. The interval is the `interval_quantiles` pair of the
replicates by `interval_quantile_method`. The one-sided p-value is `p_value_rule`: `(1 +
number of replicates >= -zero_tolerance) / (replicates kept + 1)`. Intervals condition on the
selected constants and the post-kick-off window; they omit selection uncertainty and
dependence across weeks within a team. The identity-link test, not the interval, is the guard
against that dependence, and the synthetic gate measures the false-positive rate of the
whole rule (DISSENT 1).

**Mirror placebo (B6).** Swapping the left and right components of `delta_u` keeps
wide-versus-centre information and reverses side information. M1 asks whether side
information exists; a strict inequality between two point estimates would pass half the time
under no side information, so M1 is tested with its own p-value.

**Identity-link stress test (B7).** For each of `permutation_seeds`, at each date, teams are
permuted within league and strength tercile (members sorted by team id; generator seeded by
`donor_seed_rule`), each unit receives its donor's `delta`, and `kD` is re-selected on
development rows with `kA` fixed. This breaks the link between a team and its own history
while keeping league and coarse measured strength. It cannot hold latent strength fixed:
terciles estimated from prior points misclassify, and a designer-side synthetic check showed
a shape planted as a function of latent strength passing this test in every season. V1 is
the check for "the shape is strength" (below). B7 is a stress diagnostic, not an
exchangeable permutation test and not a p-value. The share of rows whose donor differs is
reported per seed.

**Reliability (R1).** Units: teams with at least `minimum_half_matches_per_team` valid rows in
each half. The split is `reliability_split`: each half holds one meeting with each opponent. A
team's meetings with an opponent are its rows against it, valid or not, the earlier and the
later by date, then game id; opponents are ordered by the date of the earlier meeting, then
team id; for an opponent at a position (0-based) of 0 or 1 modulo 4 half A takes the earlier
meeting, at 2 or 3 modulo 4 the later; half B takes the other; an invalid meeting is in neither
half and is not replaced. Each half therefore faces the same opponents, holds about half of
each part of the season and is home in about half its matches: on the gate's double round-robin
tables at 18 and 20 teams, mirrored or with the second leg's rounds permuted, each half holds
half (within one) of each leg, and the two halves' home counts differ by at most one. The split
is fixed by the calendar, so an invalid match moves no other opponent. A date-alternating split
puts most of one team's home matches in one half of a mirrored double round-robin, and an
alternation within home and within away matches leaves the halves facing different opponents;
on synthetic seasons the first lowered the mean half correlation under a planted venue effect
and the second lowered it without one (REVIEW-RECORD, R-statistics-16). The draft's next rule,
half A taking the home meeting at even positions and the away meeting at odd ones, kept the
opponents and the venues balanced but not the season: when a team's venues alternate by round,
position parity is venue parity, and on those tables each of its halves was one run of
consecutive rounds against the season's two ends, so a change within the season (49 of 98 teams
show more than one coach id) would lower R1, and a league-wide seasonal shift would survive the
league centring. On 60 synthetic five-league seasons in which half the teams change their
defender shape at a random round (the auditor's script), the mean stepped-up correlation was
0.570 and 0.574 (side, width) under that rule and 0.629 and 0.598 under this one; with static
teams the two rules gave 0.686 and 0.663 against 0.681 and 0.661 (REVIEW-RECORD, Third audit,
2-1). Before registration the root counts, on the real calendars and computing no outcome, the
share of each half dated before `evaluation_start` and its home share, team by team
(`verified_by_root_before_registration`).

A half's value is the log-ratio coordinate of its pooled counts (`log_ratio_smoothing_per_part`
per part); the league mean is removed within each half (`reliability_centring`). With `r` the
correlation over `n` teams in `G` leagues: `R = 2r/(1+r)`; lower bound
`R_lo = SB(tanh(atanh(r) - c / sqrt(n - 3 - (G - 1))))`, `c = reliability_critical_value`, the
one-sided 95% value ROOT 2.5 O5 writes for a protocol with fewer than 100 units, applied to the half-sample correlation
before the step-up, as O5 orders. At `n = 98` a coordinate needs an observed `R` of at least
0.646 for a band (`reliability_band`) and 0.788 for a number (`reliability_number`). The house
interval applies Fisher's transform to the stepped-up value with `n - 3`; it is
`AxisReliability` at `house_reliability_confidence`, whose critical value is
`house_reliability_critical_value` (a test ties the two), reported beside this one (0.616 and
0.776 at `n = 98`), and it gates nothing. A descriptor passes when **every** coordinate has
`R_lo >= reliability_band`. Its render state is "number" when the smallest `R_lo` is at least
`reliability_number`, "band" when at least `reliability_band`, else "insufficient" (ADR-0002).
No per-league reliability is gated: at 20 teams the sample size decides the outcome. (Le)
applies the same split and bound to `ln((sum y + s) / sum e)`, `s =
log_ratio_smoothing_per_part`.

**Validity against strength (V1).** Per coordinate, the team-season value from the pooled
counts of all valid rows, league-centred, and the four `strength_covariates`, league-centred,
from `strength_covariate_sources` (points and goals per match from the sheet over every match;
completed-pass share from valid matches). The confound kind is declared now
(`strength_confound_kind`, `strength_confound_reasoning`, `galactico/validation/lifecycle.py`):

- For every descriptor, strength is a **NUISANCE**: the claim is a property of the defending
  team beyond its measured strength (ROOT 2.2), so variance shared with points, goals and pass
  share is what the claim must exclude. Criterion (g) is the house confound audit,
  `galactico.reliability.confound.discriminant_validity`, on these values with the top `k =
  strength_top_k`, ties `strength_tie_policy`, and three thresholds passed explicitly, never
  its defaults: variance explained at most `strength_variance_explained_ceiling` (the
  lifecycle's line for a damaging nuisance, `ConfoundFinding.damaging`), Spearman correlation
  between raw and residualised values at least `strength_spearman_floor`, and top-`k`
  survival at least `strength_top_k_survival_floor`, pooled over the 98 teams (chance overlap
  at `k = 12` is 1.5 in each tail). A log-ratio coordinate has two leaderboards, and the
  house audit reads only the `k` largest values and the `k`-th largest place, so one call
  would audit one tail, chosen by the arbitrary sign of a basis row or by the frame's
  labelling. For each coordinate the audit is therefore called twice, with the same
  covariates, thresholds, `k` and ties: on the league-centred coordinate and on its negation
  (`strength_survival_tails`). (g) holds when both calls' `ConfoundVerdict.passed` are true
  for every coordinate. Departures from the house audit, stated: the ceiling is the
  lifecycle's 0.25, not the audit's default 0.60, because the claim names strength as a
  nuisance; the survival count is pooled, never per league, where chance overlap exceeds the
  floor's meaning; both tails are read; a tied `k`-th place in either tail leaves that tail's
  count undefined and the check fails by name (ADR-0026); a missing value is a failure.
- For the level subject, strength is **CONTEXT**: how many entries a team concedes is partly
  its strength by construction. V1 is reported for it, with the same two calls on its team
  value `ln((sum y + s) / sum e)` over all of the team's valid rows (`s =
  log_ratio_smoothing_per_part`), league-centred, and gates nothing; its sentence says the two
  are not separated.

Reported beside (g) for every coordinate: once, from the call on the coordinate as computed
(the two calls agree on them up to floating-point rounding), unadjusted `R2`, its noise floor
`q/(n - G)` = 0.043 and `R2_adj = 1 - (1 - R2)(n - G)/(n - G - q)`, with `q` the number of
`strength_covariates` (not `k`, which is `strength_top_k`), a permutation reference
(covariate rows permuted within league, `strength_permutations` draws, a fresh
`default_rng(seed + seed_streams.strength_permutation)` per descriptor, consumed coordinate by
coordinate) and the Spearman correlation; and for each tail, the top-12 survivors or, when
undefined, the tie counts. The draft's rule (adjusted `R2` at most 0.6, no survival check) let
a shape planted as a function of latent strength tercile, at a size of 0.10, pass (e) and (g)
together in a sixth to a quarter of synthetic seasons (the reviewer's and the reviser's
simulations, which differ in split and critical value); the rule above let none through in
200 seasons at any of four planted sizes and three overdispersion values, with one tail read
(REVIEW-RECORD, R-statistics-2) and again with both (REVIEW-RECORD, Audit, A-1-1).

**Secondary family.** S1 to S5 run through the same machinery. Their one-sided p-values for
P1 enter Holm's step-down procedure at `holm_family_alpha_one_sided` with `holm_order_rule`:
`m = holm_family_size` always; p-values in ascending order, `None` and NaN (an `INCONCLUSIVE`
secondary has no p-value) after every number; a `context_only` selection has the p-value 1,
a number, by `p_value_rule`; ties in the order of `secondary_descriptors`; the `i`-th (1-based) is rejected while every earlier
one was rejected and `p_(i) <= alpha / (m - i + 1)`; the first failure stops it; `None` and
NaN never reject. A secondary's criterion (a) is its Holm rejection.

**Reported without a verdict.** Per-league P1 with intervals. The Italy, Germany and France
pooled P1 with its interval. P2, T1 and, for the primary, I1 (I1 permits nothing:
`interaction_reported_only`; its interval is computed in the shared world, a directed pair
weighted by the product of its two meetings' multiplicities). `all_states` P1 and R1 for the
primary: P1 with the `close_11v11` `kA` and `kD`, no re-selection, on the same eligible rows
(eligibility counts valid matches and does not depend on the window) in the shared world, and
R1 with the same split. Loss of every rung. The implied per-match intraclass correlation
`R / (m - (m - 1) R)`, `m` the mean number of valid rows per qualifying team over both halves.
For the level, pooled L1 over `unexposed_leagues` with its interval (Prior exposure). Coverage,
exclusion and dropped-replicate counts, the dropped locations by event set and by sentinel point
(Locations), and the two coach-id counts of Eligibility.
Empty metrics are `null`, never zero.

## Decision rule — frozen

**Sample gates** (every league unless marked pooled).

| Gate | Requirement | Applies to |
|---|---|---|
| G1 | valid matches at least `minimum_valid_match_share_per_league` of matches | shape and level |
| G2 | eligible development rows and weeks at least `minimum_development_rows_per_league`, `minimum_development_weeks_per_league` | shape and level |
| G3 | eligible evaluation rows and weeks at least `minimum_evaluation_rows_per_league`, `minimum_evaluation_weeks_per_league`; the subject's sum of `N` over eligible evaluation rows at least `minimum_evaluation_events_per_league` (`evaluation_events_rule`) | shape and level |
| G4 | at least `minimum_reliability_teams` teams qualify for R1 (pooled) | shape and level |
| G5 | every placebo seed changes the donor on at least `minimum_permutation_changed_share` of eligible evaluation rows (pooled) | shape only |
| G6 | every development selection loss of the shape (B4 over the grid, the candidate over the grid and `context_only`, each placebo's) is finite | shape only |
| LG6 | every development selection deviance of the level (B1 over the grid, B2 over the grid and `context_only`) is finite | level only |

`shape_gates` and `level_gates` list them. G1 to G5 are evaluated on counts before any loss
is computed; G6 and LG6 after development selection and before any evaluation loss is
aggregated. A subject whose own gates fail is `INCONCLUSIVE`, the failed gates are its
reasons, and no evaluation result of it is compared (under G6 or LG6 the development selection
losses were compared, and are not serialised). The level subject is evaluated whenever its own
gates pass, whatever G5 and G6 return for the primary.

**Criteria.** "Below zero" means below `-zero_tolerance`. `alpha = criterion_alpha_one_sided`.
A criterion that cannot be evaluated is `None` and counts as not met.

| | Criterion |
|---|---|
| (a) | Primary: the one-sided p-value of pooled P1 is at most `alpha`. Secondary: Holm rejects |
| (b) | P1 is below zero in at least `minimum_leagues_with_negative_estimate` of the five leagues (`leagues`) |
| (c) | Pooled P1 is strictly smaller than P1 of every placebo of `permutation_seeds`. Ties fail |
| (d) | The one-sided p-value of pooled M1 is at most `alpha`. Only where mirror pairs exist; otherwise true |
| (e) | R1 passes |
| (f) | Pooled P1 over `unexposed_leagues` is below zero |
| (g) | V1 passes (the audit above) |
| (La) | `kD'` is a grid value (not `context_only`) and the one-sided p-value of pooled L1 is at most `alpha` |
| (Lb) | L1 is below zero in at least `level_minimum_leagues_with_negative_estimate` of the five leagues (`leagues`) |
| (Le) | R1 of `ln((sum y + s) / sum e)` passes |

**Verdict of a descriptor** (`verdict_vocabulary.descriptor`, `verdict_precedence`). Exactly
one; the first row that holds decides.

| Order | Condition | Token | Question it answers |
|---|---|---|---|
| 1 | a gate of `shape_gates` failed | `INCONCLUSIVE` | no evaluation result was compared |
| 2 | (a) to (g) all hold | `DEFENDER_SHAPE_SIGNAL` | all three, and side information where it applies |
| 3 | (a), (b), (c) or (f) does not hold | `ADDED_INFORMATION_NOT_SHOWN` | out-of-sample skill not shown |
| 4 | (d) does not hold | `SIDE_NOT_SHOWN` | skill shown; which side not shown |
| 5 | (e) does not hold | `NOT_RELIABLE` | skill shown; not shown to repeat |
| 6 | (g) does not hold | `STRENGTH_NOT_EXCLUDED` | skill shown, repeats; not shown to be more than strength |

**Verdict of the level subject** (`verdict_vocabulary.level`): `INCONCLUSIVE` if a gate of
`level_gates` failed; `LEVEL_ESTABLISHED` if (La), (Lb), (Le) hold;
`ADDED_INFORMATION_NOT_SHOWN` if (La) or (Lb) does not; otherwise `NOT_RELIABLE`.

Each subject's reasons are recorded with its token: the failed gates, or every criterion
that did not hold. A token other than `INCONCLUSIVE`, `DEFENDER_SHAPE_SIGNAL` and
`LEVEL_ESTABLISHED` is a published null, not evidence of absence; each names the first
question that failed and asserts nothing about the questions after it. The lifecycle status
each token earns is `lifecycle_status`: `EXPERIMENTAL` for the two established tokens,
`RESEARCH_ONLY` for every other.

**Replication qualifier** (`replication`). For each descriptor with `DEFENDER_SHAPE_SIGNAL`,
the frozen specification (the definitions of `comparable_descriptors` in unit coordinates,
`kA` and `kD` as selected on the Pappalardo development rows, no selection) is run on
StatsBomb 2015/16, four leagues, every eligible row of the season, in its own world
(`seed_streams.replication_world`, `replication.bootstrap_replicates`; quantiles, quantile
method, p-value rule and `zero_tolerance` as above; strata in the order of
`replication.leagues`; every row is an evaluation row, so the development part has no
stratum). Only P1 and M1 are computed (`replication.estimands`, `estimand_rule`): B4, the
candidate and B6 with the frozen `kA` and `kD`, with no selection, no placebo, and no R1, V1,
P2, T1 or I1. Its sample gates are G1 and G3 only, with the `replication` minima
(`replication.gates`, `gate_rule`); G1's share is valid matches over the matches the folder's
index lists. The provider mapping is frozen in `replication` and `PIPELINE.md` section 6
before any replication outcome is read: the open-play pass types are E-11's
(`sb_open_play_pass_types`, a kick-off is an ordinary pass, as on the Wyscout side), the
sentinel rule does not apply, matches come from the match index only, and a match's
competition is its folder. Status (`status_rule`), the first that holds:

1. `NOT_COMPARABLE`: S4 and S5, declared now (the providers' defensive-event ontologies
   differ).
2. `NOT_RUN`: the descriptor's token is not `run_only_if_descriptor_verdict`.
3. `REPLICATION_INCONCLUSIVE`, with the first reason of `inconclusive_reasons` that holds
   (`inconclusive_reason_rules`): `DATA_MISSING` (any of the four folders, or its match index,
   is absent; checked for existence before any file is read), `VOCABULARY` (a pass type, shot
   type or card name outside `sb_known_pass_types`, `sb_known_shot_types`,
   `sb_known_card_names`), `ORIENTATION` (the orientation check fails), `SAMPLE` (a league
   fails G1 or G3 of `gate_rule`, or a folder's index lists a number of matches other than
   `expected_matches`; a listed match without its files counts as an invalid match),
   `FAILED_RUN` (an exception inside the replication stage, a malformed timestamp included).
4. `REPLICATED`: the p-value of pooled P1 is at most `alpha`, and for a descriptor with
   mirror pairs the p-value of pooled M1 is too.
5. `NOT_REPLICATED`: otherwise.

Entries are keyed by descriptor; the level subject has no replication entry. An exception
inside the replication stage gives `FAILED_RUN` to every descriptor whose status reached step
3; `NOT_COMPARABLE` and `NOT_RUN` stand. The local artifact exists only when a comparable
descriptor reached step 3; it records every descriptor's status and reason, and the
`folder_manifest` digest of each folder whose match index exists, so a later fetch of
re-versioned files can be told apart; it is never committed. The Pappalardo results are written
whatever the replication returns. Ligue 1 has 377 matches in the provider's index. ROOT 2.9 Z5
rules how the arm's result is reported: ROOT 2.5 O1's "a second-provider replication status
sits beside them as a label" is ADR-0018's permission, not a duty; E-10 creates no registry
record for its LOCAL replication arm (`registry_record`); the arm's result, each descriptor's
status and reason and the numbers behind them, is reported in `analysis.md` only, with the logo
and credit of LICENSING.md; and no hosted page carries a label from it (`served_by_product`).
`results.json` therefore holds no replication status, token or number (`results_record`); the
statuses' machine record is the local artifact or, after a replication exception, the
replication failure log, neither ever committed. Product code cannot read a replication status,
and none changes what a panel shows, its opt-in, its interval or its evidence class. A later
protocol may add such a label only through its own LOCAL record.

**No rescue.** No change of grid, window, event set, state filter, lateral rule, split, gate,
threshold or criterion after an outcome is read. A second operationalisation needs a new
preregistration.

**What a null will mean.** DERIVED, not measured: with about 60,000 evaluation events the
paired statistic is `z = 1.5 tau sqrt(R_h n / D)`, `tau` the between-team SD of a channel
share, `R_h` the reliability of the history at hand, `D` the design effect of a row's events.
At `R_h = 0.5` and `D` of 4 to 9, the range this design assumes for real matches, 80% power
needs `tau` of two to three percentage points, a per-match intraclass correlation near 0.05.
Criterion (e) is stricter: a coordinate whose true 38-match reliability is 0.646 passes it
about half the time, and the primary's two coordinates together about a quarter of the time.
The gate's generator sets `D` through `overdispersion_grid`: about 1.1, 3.3 and 6.1 at its
three values (`design_effect`; the gate reports what it realises). On the reviser's synthetic
seasons (`REVIEW-RECORD.md`; not the gate), (e) and (g) together, which bound the detection
rate from above, held for a planted defender SD of 0.15 on both coordinates (about four
percentage points of a channel share) in 200 of 200 seasons at `D` 1.1, 85 of 200 at 3.3 and
none at 6.1, and for an SD of 0.09 in 147 of 200 at 1.1 and none above, with the split above
(the third audit's rerun of the same seasons; the split it replaced gave 87 and 132, and the
first audit's rerun with (g) reading both tails gave those same counts). If real overdispersion
is near the top of the assumed range, this protocol will return `NOT_RELIABLE` or
`ADDED_INFORMATION_NOT_SHOWN` even for an effect of four percentage points. A null therefore
means "smaller than about that, or not separable from match-to-match variation at this sample
size", which is also too small to show as a number from 38 matches. The synthetic gate
publishes the measured detection rate at three smaller planted effects and at every value of
`overdispersion_grid` before the real run.

## Product consequence of each verdict — fixed now

One panel per subject in Opponent Lab: the six descriptors and the level subject. The
prior-date record (counts over the team's prior matches in the same window, matches and events
used) is shown in every state. Product code reads nothing from this experiment but its
registry records (ROOT 3b): seven PUBLIC `VerdictRecord`s in `galactico/domain/verdicts.py`,
built at registration from the config's own entries, token `PENDING`, and given their tokens,
hashes and figures in the results commit (`PIPELINE.md` sections 12 and 13). Every badge,
statement and gate comes from `verdicts.derive` and `verdicts.badge_text`.

| Field | Descriptor records | Level record |
|---|---|---|
| `vocabulary`, `outcomes` | `verdict_vocabulary.descriptor`, `registry_outcomes.descriptor` | `verdict_vocabulary.level`, `registry_outcomes.level` |
| `claim_token` | `registry_descriptor.claim_token` | `registry_level.claim_token` |
| `scope` | `registry_descriptor.scope` | `registry_level.scope` |
| `non_claim` (the fixed panel sentence, printed in every state; before registration the registry has no record and so no `non_claim`, and the panel prints the same sentence from its own constant, which a test ties to `registry_non_claims` and, once registered, to the record) | `registry_non_claims.conceded` for the primary, S1, S2, S3; `registry_non_claims.own_actions` for S4, S5 | `registry_non_claims.level` |
| `not_run_statement` | `registry_common.not_run_statement` | same |
| `figures` (results commit, only under an established token) | `registry_figures.descriptor`: `k_context`, `k_unit`, `reliability_lower_bound`, each with its pointer into `results.json` | `registry_figures.level` |

| Registry state | Badge (`badge_text`) | Shown beyond the record | Evidence class |
|---|---|---|---|
| no record (before registration) | `RECORD ONLY · NOT TESTED` | nothing | counts OBSERVED, shares and rates DERIVED |
| `PENDING` | `E-10 · RECORD ONLY · NOT RUN` | nothing | same |
| `INCONCLUSIVE` | `E-10 · INCONCLUSIVE` | nothing | same |
| a token of status NOT_ESTABLISHED | `E-10 · TESTED · NOT ESTABLISHED` | nothing | same |
| `DEFENDER_SHAPE_SIGNAL` | `E-10 · TESTED · TENDENCY, ONE SEASON` | behind an explicit opt-in, at decision dates on or after `evaluation_start` only: the shrunken composition, its interval and shrink weight (`PIPELINE.md` section 12); the point only when the `reliability_lower_bound` figure is at least `reliability_number` (ADR-0002), otherwise the interval only | EXPERIMENTAL |
| `LEVEL_ESTABLISHED` | `E-10 · TESTED · VOLUME, ONE SEASON` | the same rule: shrunken entries per 90 window minutes, interval and shrink weight | EXPERIMENTAL |

The statement shown is the record's (`registry_outcomes`), verbatim, and names which question
failed; no sentence denies what an earlier criterion found. The established statements say the
verdict was decided on matches of the whole season, which a decision date inside the season
precedes. The volume panel is EXPERIMENTAL, not ESTIMATED: its sentence says the check does
not separate the volume from team strength, and asserts no direction for it, which E-10 does
not measure. Each established statement describes the split-half check as it is run (two
halves of the team's matches that each hold one meeting with every opponent), not as
persistence from the first part of the season to the second. `may_gate` (true only for
an executed, PUBLIC, ESTABLISHED record) is the only thing that unlocks a panel, and only these
PUBLIC tokens set it.

Fixed in every state (`product_rules`):

- Parts are listed in the declared order. No part is highlighted, sorted by size, or called the
  largest. No league-relative adjective. No single number summarises an opponent. Teams are
  never ordered by a descriptor, here or in `analysis.md`.
- The words of `words_never_on_the_page` do not appear on the page.
- The optional requirement proposal stays HEURISTIC under every verdict and needs the user's
  acceptance. Its qualifier follows the cited record's `may_gate` (`proposal_sentence_rule`):
  none when `may_gate` is true; `proposal_sentence_not_tested`, *"based on a record E-10 has
  not tested"*, when the record is not registered, `PENDING` or `INCONCLUSIVE` (unknown is
  never evidence of absence, R11); `proposal_sentence_not_established`, *"based on a record
  that did not pass E-10"*, when its status is NOT_ESTABLISHED. A proposal that cites several
  E-10 records carries one qualifier per cited record whose `may_gate` is false, beside that
  record's label, in the order of `subject_groups`; none is merged or dropped.
- S5's panel shows the share under its label, the tested quantity, with the share's badge
  (`s5_panel_rule`). `s5_ratio_name`, ROOT H14-H21's name for the analogue (*opponent passes
  per recorded high-zone defensive action*), names in prose only the ratio of which the share
  is a monotone transform; no panel shows or labels the ratio.

## Interpretation language — frozen

A null is stated by its token's sentence and, in `analysis.md`, as: *"this procedure did not
meet every frozen criterion for that question"*, naming the question and the criteria that
failed. It is not stated as "teams have no defensive shape" or "opposition analysis does not
work", and a token that names a later question is never stated as the absence of what an
earlier criterion found. A signal is stated as out-of-sample information about a composition,
never as a flaw of the defending team and never as advice to attack a channel. `analysis.md`
names no team and prints no ordered list of teams.

## What this experiment cannot show

- Why a team concedes where it does. Funnelling and failure are observationally the same.
- That a signal is separate from latent team strength in every form. Strength enters through
  league tercile peers (B3, B7) and four measured covariates (V1); a shape that tracks
  strength in a way those miss would pass. The synthetic gate tests the two forms it plants.
- Persistence across seasons: the corpus holds one season per provider, and the two
  providers are two years apart with different ontologies.
- Anything for states outside the window, or for matches not yet kicked off: the window and
  the conditioning on `N` use post-kick-off information.
- Danger. An entry pass is territory, not a chance; no conversion model is used.
- That event locations are precise: the provider reports no positional accuracy and no
  inter-operator agreement, which is why three channels are used and nothing finer.
- Which side is left on the Wyscout pitch, beyond the convention the repository assumes
  (Frames); no verdict depends on it, only the panel's names.
- That a composition persists in time within the season: R1 interleaves the halves; T1, the
  check in time, is reported and gates nothing.
- Stability under a coach or squad change: not adjusted, counted as part of the team.
- Calibrated uncertainty: intervals omit selection uncertainty and week-to-week dependence
  within a team.
- Small effects under high overdispersion (What a null will mean).
- Independence from earlier work: a third of the evaluation rows were previously scored
  for a different conceded target.

## Reproducibility and tests

Artifact (`results.json`, aggregate only, at most `results_maximum_bytes`, no player identifier
or name, no team-level row): the registry contract (`experiment`, `tier`, `verdicts` per
subject with token and reasons, `provenance.protocol_commit`, `provenance.protocol_hash`);
protocol, config, pipeline-document, vectors and source hashes on LF-normalised bytes;
`pipeline_spec_sha256`; content hashes of every input frame and of each team-match table; the
sidecar's `provenance()` per league and the loader version; descriptor fingerprints; package
versions; seeds and the world's fingerprint; the synthetic-gate report hash; coverage and gate
counts; every rung, estimand, criterion and verdict; the frozen strings of `results_strings`,
copied verbatim; and no replication status (ROOT 2.9 Z5, Replication qualifier). Package
versions include the BLAS library numpy reports and the machine, and `real` and its
determinism re-run use the BLAS thread counts of `blas_thread_environment`. No key at any
depth names a provider (`forbidden_result_key_names`); no player identifier or name appears outside the verbatim
config echo (`forbidden_result_substrings_scope`: the echo holds the list of forbidden
substrings itself, and equals the committed config). Replication numbers are written only to
`replication.local_artifact`. The runner refuses a dirty working tree, a fingerprint mismatch
in either dictionary, a pipeline document whose hash differs from `pipeline_spec_sha256`, an
absent or stale sidecar, a team-match with no sheet row, or a missing or failing synthetic
gate.

**One execution.** `real` writes `results.json`, the failure logs, the determinism record and
the local artifact under `output_root`, one directory for both arms' files, which git ignores as
it does E-11's (ROOT 2.9 Z1); nothing under it is committed, and its clean-tree check stays
satisfiable; the results commit copies `results.json` unchanged into the experiment directory.
Every output is written in the last stage, after the checks on the payload. A failed execution
(an exception after the refusal checks, outside the replication stage) appends the exception
type, stage, file and line and source hashes, never the message, to `failed_run_log`, leaves no
other file (one it was writing is removed), and exits; no value from it may be read; the
repair may touch only the failing stage, the gate stamp is regenerated, and the next
execution starts only when the committed `analysis.md` holds the sha256 of the log's bytes
(an `analysis.md` that records only the failures may be committed before the next execution
and completed in the results commit). The determinism re-run (`real --verify`) recomputes
everything and compares the bytes of `results.json` and, when a replication ran, of the local
artifact; it writes only `determinism_record`, and only when every byte is equal, and it is
refused when that record already exists. A difference in any byte, or an exception in the
re-run outside the replication stage, is a failed execution (stage `serialise` for a byte
difference): the first execution's outputs are removed and never committed, no determinism
record is written, the failure goes on the record as any other, and there is no second re-run;
the next step is a new execution.
An exception inside the replication stage is not a failed execution: the Pappalardo results stand, every descriptor whose replication status
reached step 3 is `REPLICATION_INCONCLUSIVE (FAILED_RUN)`, the exception's type, stage, file and
line go to `replication_failure_log`, not to `failed_run_log`, and nothing attempts that
replication again, the determinism re-run included.

**Synthetic gate, before any real outcome** (`synthetic_gate`). Seeded synthetic seasons with
the real double round-robin shape (Berger tables), one league per entry of `leagues`, under
its name and with `expected_teams_per_league` teams (`league_rule`), plant known effects and
known zeros, at each value of `overdispersion_grid` that `requirements` names. A synthetic
season's evaluation reads this protocol's config with exactly two keys replaced, `seed` by the
season's seed and `bootstrap_replicates` by `synthetic_gate.bootstrap_replicates`
(`season_seed_rule`); every subset, gate and criterion therefore reads the same league names
as the real run. The frozen rule must meet every requirement:

- `DEFENDER_SHAPE_SIGNAL` for the primary in at least 90% of seasons with a strong planted
  defender shape (`EFFECT_STRONG`, at the lowest overdispersion);
- `DEFENDER_SHAPE_SIGNAL` in at most 5% of seasons, at the lowest and the highest
  overdispersion, with no defender shape (`NULL_NOTHING`), with a defender level and no shape
  (`NULL_SHAPE_WITH_LEVEL`), with a width-only defender shape (`WIDTH_ONLY`, which has no side
  information, so (d) passes only by chance and (e) fails on the side coordinate), with a
  shape that is a function of latent strength tercile at each of four sizes
  (`STRENGTH_TERCILE_*`, the case that motivated (g)), and with a shape that is a function of
  measured points (`STRENGTH_MEASURED_0_15`);
- any of the five secondaries `DEFENDER_SHAPE_SIGNAL` in at most 5% of seasons with nothing
  planted (`SECONDARY_FAMILY_NULL`, the family-wise rate; Holm's own family-wise rejection
  rate is reported);
- for the level, `LEVEL_ESTABLISHED` in at least 90% of `NULL_SHAPE_WITH_LEVEL` seasons and at
  most 5% of `NULL_NOTHING` seasons; and a token of status NOT_ESTABLISHED for the primary in
  at least 90% of `NULL_NOTHING` seasons.

Detection rates at three smaller planted effects, at every overdispersion value, are
published with the realised design effect, gating nothing.

Tests (synthetic or hand-computed only; `PIPELINE.md` section 9): defender-frame mirror with
the wrong-sign negative control; sentinel, out-of-range and missing coordinates, Wyscout only
for the sentinels; float64 cuts on the Wyscout lattice and on the StatsBomb scale; state
window with goals, own goals (own goal first), a goal flag on a row that is not a shot,
dismissals and same-second ties; dismissals against the sheet; window seconds; count once
under the action union; row-order invariance; table oracle against
`build_match(...).team_profiles`, with a penalty and a direct free-kick shot; descriptor
payloads, fingerprints, sentences and column names against the frozen vectors for both
dictionaries; future and same-day poisoning; own-match exclusion; `context_only` identity
with B4 and with B1; Poisson-multinomial factorisation; ratio of sums; selection ties by the
tie set; development-only selection; permutation determinism, strata and order invariance;
mirror swap; the shared world (both rows of a match in one cluster, one world for every
estimand and subset, its fingerprint); Holm against hand examples with `None`, NaN and ties;
the reliability bound at the stated thresholds; the split's opponent, venue and season balance; the
confound audit as `discriminant_validity` with the frozen thresholds on both tails, including
a tied twelfth place in either tail, and unchanged when a coordinate is negated; a
`context_only` selection against placebos that select grid values; fail-closed validity;
every gate yielding `INCONCLUSIVE` with no loss computed, and the level evaluated when only G5
or G6 fails; a synthetic season that feeds every league subset; the full truth table of both
verdict maps over `{True, False, None}`, token and statement; the replication's status table;
every registry sentence served through the response boundary under `PENDING` and every token;
the runner's refusals, failure log and determinism re-run under an `output_root` in a temporary
directory, no runner test opening a path under the repository's `data/`; strict JSON; no
identifier, no provider-named key and no replication status in `results.json`.

*Committed before running. Results in `results.json`, interpretation in `analysis.md`. If
either contradicts this document, this document wins.*
