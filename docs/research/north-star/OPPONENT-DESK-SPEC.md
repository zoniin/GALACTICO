# Opponent Lab and Director's desk specification

Build contract for the last two surfaces of ROOT-DECISIONS 2.3: Opponent Lab at `/opponent`
(the prior-date record of what a team did and what was done against it, each descriptor
badged with its E-10 verdict, and an optional HEURISTIC requirement proposal the user must
accept before it changes an XI solve) and the Director's desk at `/desk` (the chain of ROOT 2
end to end, one evidence ledger, and the "not measured here" panel). The binding rules are
ROOT-DECISIONS sections 0, 1 (R1-R13), 2.3, 2.5 (O12, O13, H14-H21), 2.6, 2.9 (Z1-Z5), 2.10,
2.12 (N1-N7), 3b and 4; ADR-0018 to ADR-0030; KNOWN_LIMITATIONS. The E-10 protocol draft
(`protocol-drafts/E-10-conceded-shape/`, READY, not registered) already fixes the product-side
team modules (PIPELINE sections 2 and 3) and the served panel (PIPELINE 12.3); this file reuses
them by name and never redefines them. Where this file and those rules, the E-10 draft or the
shipped code disagree, they win and the disagreement is a defect to report (ROOT 2.6). Points
where this file departs from a ruling's wording are under DISSENT; the points only the root
could settle were ruled in ROOT-DECISIONS 2.12 and are recorded under Root rulings
(ROOT-DECISIONS 2.12).

**Status.** Draft by the Opponent/desk designer, 18 October 2026; revised the same day after
three adversarial reviews (constitution, product, exactness and data). Their 72 findings and
the disposition of each are in the Review record at the end. The root ruled the five questions
the revision left to it (R-1 to R-5), and the order of work, the same day (ROOT-DECISIONS 2.12,
N1 to N7); this file records each ruling under Root rulings (ROOT-DECISIONS 2.12) and follows
it. Not yet audited: under N7 it is audited, with a refuter per claimed blocker, until no scope
has a blocker. Nothing built. Every claim about the shipped code was read from the tree at `52bdc0b`; line numbers refer to
it. The public corpus was not present when this was written (`data/public/` is empty), so no
number below was computed on it, and none may be computed on it for this work before E-10 has
run (1.7).

**What these surfaces are.** The third kind of deliverable ROOT section 0 allows: product
surfaces that render exact computation and the verdicts of preregistered research, and say what
is unmeasured. They add no construct and no empirical claim. Four kinds of number appear, each
with its own class (1.5): counts of recorded events (OBSERVED) and their shares, rates and window
time (DERIVED), which are the record; the E-10 estimate, which exists only where an E-10 record
is ESTABLISHED and only behind an opt-in (EXPERIMENTAL); the minima a requirement proposal sets
(HEURISTIC, the user's declared policy); and the XI solve and its exact additions (exact
computation on the declared model, as XI Lab). The desk composes the replies of the pages that
compute them and computes nothing of its own but the composition. It reads no opponent record
and forms no requirement proposal: those are read, and a proposal accepted, on Opponent Lab
(6.4, DISSENT 5, N3).

**Rulings this file depends on.**

| Ruling | What it fixes here |
|---|---|
| ROOT 2.3 | the two surfaces and the nine items of the desk's "not measured here" panel |
| ROOT 2.5 O12, O13 | declared inputs are not evidence; one mapping to `EvidenceClass` |
| ROOT 2.5 H14-H21 | "share of final-third entries conceded, by lateral third" (never weakness, vulnerability, weak flank); "defensive action distance" (never line height); the PPDA analogue is "opponent passes per recorded high-zone defensive action" |
| ROOT 2.6 D4 | planning surfaces, the desk among them, default to progression alone; the side requirements need `experimental_opt_in` |
| ROOT 2.7 X6 | the same default for XI parts outside XI Lab's main solve |
| ROOT 2.9 Z3 | one estimator, `galactico/features/team/estimator.py`, product side; the panel calls it, never a copy |
| ROOT 2.9 Z5 | no hosted label from E-10's LOCAL replication arm |
| ROOT 2.12 N1-N7 | the rulings on this file's questions (Root rulings): the record gate opens at E-10's results commit (N1) and E-10's product table is aligned to it before registration (N2); the desk reaches the record and the proposal by a link to Opponent Lab (N3); S3, S4 and S5 wait for an E-09 record (N4); ADR-0032 overrides R13 for the nav bytes and pinned tests (N5); E-10's registration commit rewords planning's `shots` item (N6); the order of work (N7, 0.2) |
| ROOT 3b | `galactico/models/opponent/` is the prior-date opponent record; `api/opponent_lab.py`, `api/desk.py`, `web/opponent.html`, `web/desk.html`; the root registers the routers; `verdicts.py` is the only thing product code reads from research |
| E-10 PIPELINE 2.5 and 11 (row 1) | no WP A file is executed on `data/` before E-10's code review, and the only real-data test before the run requests no descriptor column; with R5, the reason the record waits for E-10's run (1.7, DISSENT 1, N1) |
| E-10 PIPELINE 12.3 | when the estimate is shown, how it is computed, the proposal qualifiers, the tests the module carries |
| E-10 PIPELINE 13 (last paragraph) | while `planning_research_sentence` is served, the desk shows no E-10 descriptor or volume (met in every state, 6.4) |
| E-10 preregistration, "Product consequence" | the states of 1.6; this file departs from the READY draft's "shown in every state" before the run (DISSENT 1), and N2 aligns that table to 1.6 before registration |

## 0. Files and ownership

### 0.1 New files

| File | New | Owner | Content |
|---|---|---|---|
| `galactico/features/team/descriptors.py`, `match_table.py`, `estimator.py`, and `tests/test_team_descriptors.py`, `tests/test_team_match_table.py`, `tests/test_team_estimator.py` | yes, if absent | E-10 WP A (PIPELINE section 0) | exactly PIPELINE sections 2 and 3, and the WP A rows of its section 9. This file adds nothing to them, renames nothing and requires no function they do not already specify. `galactico/features/team/__init__.py` exists, empty, and stays as WP A leaves it |
| `galactico/models/opponent/record.py` | yes | OPP-R | the league team-match table loader, the gate, and the prior-date record (sections 1.7 and 2) |
| `galactico/models/opponent/panel.py` | yes | OPP-R | E-10's served computation and the constants PIPELINE 12.3 puts in "the Opponent Lab module" (section 3) |
| `galactico/models/opponent/proposal.py` | yes | OPP-P | the declared proposal policy and its evaluation (section 4). `galactico/models/opponent/__init__.py` exists, empty, and stays empty |
| `galactico/api/opponent_lab.py` | yes | OPP-P | router, request models, gated loaders, envelopes, ledger, copy (section 5) |
| `galactico/api/desk.py` | yes | DESK | router, request model, composition, envelope, copy (section 6) |
| `web/opponent.html`, `web/opponent.js`, `web/opponent.css` | yes | OPP-P | the Opponent Lab page (section 7.2) |
| `web/desk.html`, `web/desk.js`, `web/desk.css` | yes | DESK | the desk page (section 7.3) |
| `tests/opponent_oracle.py` | yes | DESK (it implements neither the record nor the proposal) | an independent recount of the record and the rule evaluation from synthetic event lists, plain loops and `fractions.Fraction`; imports nothing from `galactico` (ROOT 4, M-01; a test asserts it, 8.1). Not collected by pytest |
| `tests/test_opponent_record.py`, `tests/test_opponent_panel.py` | yes | OPP-R | section 8 |
| `tests/test_opponent_proposal.py`, `tests/test_opponent_api.py`, `tests/test_opponent_render.py` | yes | OPP-P | section 8 |
| `tests/test_desk_api.py`, `tests/test_desk_render.py` | yes | DESK | section 8 |
| `tests/test_opponent_desk_pages.py` | yes | DESK | page anatomy of both pages (section 8.3) |
| `e2e/opponent.spec.js`, `e2e/desk.spec.js` | yes | OPP-P, DESK | section 8.4 |
| `docs/research/north-star/OPPONENT-DESK-SPEC.md` | yes | this designer | this file |

Three builders (OPP-R, OPP-P, DESK) work in parallel against the dataclasses of sections 2 to 4
and the envelopes of sections 5 and 6. OPP-P and DESK build against stub records until OPP-R
lands. Nobody here writes WP A: it is built by E-10's WP A owner from PIPELINE sections 2, 3 and
9 and nothing else (0.2).

### 0.2 Order of work

The order is ROOT 2.12 N7's; N2 and N6 fix what E-10's registration carries for this work.

1. This file is audited, with a refuter per claimed blocker, until no scope has a blocker (N7).
   The audit needs nothing of E-10 and may run beside steps 2 and 3; the build waits for it.
2. E-10 is registered (its PIPELINE section 13: the four files, the seven `PENDING` records).
   Before registration its product table is aligned to N1 (the record shown from the results
   commit, withheld with the reason before it, as 1.6 and 1.7 say) and that edit is verified by
   an independent auditor (N2, Z4); the registration commit carries the rewording of planning's
   `shots` item (N6, section 11).
3. E-10's pipeline commit lands WP A to D (PIPELINE section 13, "After registration"). WP A is
   then on disk, frozen with the registered PIPELINE.
4. The build follows that commit (N7). This work is built on WP A, unit-tested on synthetic
   tables only and reviewed against section 10; then the root registers the two routers and the
   two nav entries in one commit with ADR-0032, which carries N5's R13 override (section 11).
5. E-10's code review (PIPELINE 11), gate stamp, run and results commit proceed as PIPELINE 13
   says. The record gate of 1.7 opens at that results commit, when every E-10 record is
   `EXECUTED`, and not before (N1).

Nothing in this work runs a WP A function on the real corpus before step 5's results commit. The
gate is inside the one loader that reads the corpus for a record (1.7), so no route, test, e2e
spec, screenshot or person can reach a descriptor column, a validity decision or a window time
earlier. The pages may ship between steps 4 and 5: the record is then withheld, every badge reads
`E-10 · RECORD ONLY · NOT RUN`, and the page says why (`RECORD_WITHHELD_NOT_RUN`, N1). The XI
solve of Opponent Lab without a proposal, and the whole desk, read no record and work in every
state. This work cannot be built before step 3: it imports WP A's definitions (N7; OPEN
QUESTION 1).

### 0.3 Frozen and not edited

Frozen (ROOT 3b): `galactico/optimization/historical.py`, `galactico/optimization/xi/domain.py`,
`galactico/optimization/xi/solver.py`, `galactico/optimization/xi/tradeoffs.py`,
`galactico/models/xt/grid.py`. Not edited either: `galactico/optimization/squad/kernel.py`,
`galactico/optimization/snapshots.py`, `galactico/optimization/reference.py`,
`galactico/ingestion/sidecar.py`, `galactico/storage/public.py`, `galactico/domain/verdicts.py`
(the E-10 commits edit it, not this work), `galactico/domain/labels.py`,
`galactico/domain/thesis.py`, and every shipped router (`decision_lab.py`, `runtime.py`,
`planning.py`, `squad_lab.py`, `transfer_lab.py`, `xi_extensions.py`). WP A's three modules are
E-10's: after E-10's registration an edit to them is visible against the registered results
(`source_hashes`, PIPELINE 7.3), so this work never edits them; a defect found in them is
reported to the root, never repaired here.

### 0.4 Owned by the root, changed only by request (section 11)

`galactico/api/player_lab.py` (router registration), `galactico/api/shell.py` (two
destinations), `web/labs-shared.js` (no change needed: `Shell.nav` already takes `sr_suffix` per
item, labs-shared.js:62-76), `web/labs-shared.css` (only if the 320 px nav measurement needs it),
the four pages that carry the nav (`web/match.html`, `web/xi.html`, `web/squad.html`,
`web/transfer.html`) and `web/index.html`, the tests that pin the nav, `.github/workflows/ci.yml`,
`galactico/api/runtime.py` (one optional change: the source fingerprint), `galactico/api/planning.py`
wording that the E-10 commits change (section 11), every top-level `*.md`, `ROOT-DECISIONS.md`,
`docs/research/north-star/README.md`.

### 0.5 Reused, unchanged

| Reuse | From | How |
|---|---|---|
| `TEAM_DESCRIPTORS`, `LEVEL_SUBJECTS`, `WINDOWS`, `required_columns`, `REGULATION_PERIODS`, `DISMISSAL_CARDS`, `GOAL_INCIDENT_COLUMNS`, `WY_LOCATION_SENTINELS`, `COORDINATE_RANGE`, `EXPOSURE_UNIT_SECONDS`, `TeamDescriptorSpec.describe`, `.part_names`, `.parts`, `.fingerprint`, `.label`, `LevelSubject.label`, `.descriptor`, `.unit_seconds`, `Window.phrase` | `features/team/descriptors.py` (PIPELINE 3.1-3.7) | every definition, label, sentence, part phrase, window and constant the pages show or the record passes |
| `build_team_match_table`, `TEAM_MATCH_VERSION` | `features/team/match_table.py` (PIPELINE 2.1-2.4) | the league team-match table, window `close_11v11`, `xt=None` |
| `descriptor_rows`, `state_at`, `shape_estimate`, `level_estimate`, `served_composition`, `served_volume`, `LEAGUE_PRIOR_PSEUDOCOUNT_PER_PART` | `features/team/estimator.py` (PIPELINE 3.8) | the record's counts (2.2) and the served panel (3.3); imported as `from galactico.features.team import estimator` and called as `estimator.<name>` |
| `league_world_weights`, `WorldWeights` | `optimization/snapshots.py:183-190, 368-382` | the panel's worlds (PIPELINE I12) and their identity (`namespace`) |
| `load_public`, `TABLES` | `storage/public.py:49, 97-158` | the actions, matches and teams frames |
| `verify`, `load`, `attach`, `provenance`, `SIDECAR_ROOT`, `SidecarMissing`, `SidecarStale`, `SidecarMismatch` | `ingestion/sidecar.py:95, 154-163, 907-1010` | cards, own goals, goals, the sheet's scores and dismissals (PIPELINE I2-I6) |
| `verdict_for`, `figures_for`, `record`, `VERDICTS`, `VerdictBasis`, `as_payload` | `domain/verdicts.py:71-74, 272-536` | badges, gates, figures (`figures_for` returns `Figure` objects; the number is `.value`) |
| `nav_markup`, `NOT_MEASURED`, `not_measured_payload`, `NotMeasured`, `evidence_payload`, `verdict_payload`, `declared_row`, `ledger_row`, `visible_text` | `api/shell.py` | page furniture, badges, ledger rows |
| `Budget`, `lab_errors`, `cache_key`, `RESULTS`, `is_complete`, `finalize`, `respond`, `dumps`, `HOSTED_PROVIDERS`, `match_scenario` | `api/runtime.py` | every rule of a new route (ADR-0024) |
| `_built_once`, `_corpus_files`, `_digest`, `_minimum_text`, `_outward`, `INTEGER_ONLY`, `StrictId`, `League`, `LEAGUE_LABELS`, `FLAGSHIP`, `PlanningInputs`, `resolve_or_404`, `canonical_request`, `corpus_token`, `clubs`, `league_clubs`, `catalogue`, `declared_rows`, `base_ledger`, `verdict_reading`, `not_measured`, `NOT_MEASURED_CLOSING`, `SCOPE_TEMPLATE` | `api/planning.py` | the build gate, the corpus identity of a key, printed minima, the desk's common planning rows and research block. The private ones are pinned by name and signature in the API tests, as OR-XI pinned `_built_once` (OR-XI 0, "Reused") |
| `SCENARIOS`, `decision_inputs`, `DecisionRoute`, `SolveRequest`, `SEED` (via `historical`) | `api/decision_lab.py` | the two decision points, XI Lab's model, the 422 shape |
| `XIDeclarations`, `RequirementId`, `REQUIREMENT_IDS`, `SIDE_REQUIREMENTS`, `MEASURED_REQUIREMENTS`, `MEMBERSHIP_HEADINGS`, `_RULE_TEXTS`, `declare`, `_match_snapshot`, `_exact_sum`, `_lineup_rows`, `OPT_IN_LABEL`, `EXPERIMENTAL_OPT_IN_ERROR`, `UNKNOWN_PLAYER` | `api/xi_extensions.py:154-170, 375-416, 440-447, 580-631` | the decision-point request fields, the opt-in rule applied to XI Lab's model, requirement labels, the five membership headings, the mode labels, the gated match snapshot, exact sums and lineup rows; private names pinned by test |
| the handler functions `squad_snapshot`, `squad_reference`, `squad_depth`, `squad_stress`, `squad_brief` (squad_lab.py:619, 653, 927, 1298, 1482), `transfer_injection` (transfer_lab.py:946), `ceilings_route`, `conflict_route` (xi_extensions.py:1518, 1523), and their request models | `api/squad_lab.py`, `api/transfer_lab.py`, `api/xi_extensions.py` | called in process by the desk (section 6); the names are the module attributes `@router.post` returns, pinned by the desk test. The frontier and risk handlers are not composed by the desk in this release (6.1) |
| `GP.scenarioOptions`, `GP.research`, `GP.tracker`, `GP.notMeasured` | `web/planning.js` | the desk's planning point select (the catalogue's scenarios, then the clubs as served, the shipped helper squad.html:766 calls), research block, request versions (`GP.tracker`, planning.js:571-583) |
| `solve_xi` | `optimization/xi/solver.py:81-97` (frozen) | one call per `/api/opponent/xi` request, with exactly the arguments `decision_lab.solve` passes (decision_lab.py:343-356), its default 15-second time limit included (5.4.3) |
| `declared_minimum`, `load_league_reference`, `PERCENTILE_MENU` | `optimization/reference.py:67, 374-416` | the proposal's minima (4.3) |
| `format_plain` | `domain/precision.py:95` | every number a reader entered, as entered |
| `window.Shell` | `web/labs-shared.js` | badges, ledger cells, errors, not-measured |

### 0.6 Engineering (ROOT section 4)

`from __future__ import annotations`; frozen dataclasses; full type hints; `__all__`; ruff clean at
line length 100 (E, F, I, UP, B, SIM); a module docstring whose first paragraph states the claim
and the non-claim. No module here imports `galactico.validation`, `experiments` or the
licensed-corpus reader `sb_reader` (`tests/test_research_firewall.py:27` already lists `models` and
`features` as product code). The routers read no data at import, and import no solver
(`ortools`), no WP A module (`galactico.features.team`), no opponent model
(`galactico.models.opponent`) and none of `galactico.optimization.snapshots`,
`galactico.optimization.reference`, `galactico.optimization.squad.kernel`,
`galactico.storage.public` or `galactico.ingestion.sidecar` at import: every such import is inside
a function, and a subprocess test asserts it (8.1). They do load pandas and numpy at import, as
every shipped router does through `decision_lab` (decision_lab.py:16 imports
`optimization.historical`; checked in the project venv for `runtime`, `planning`, `decision_lab`,
`xi_extensions`, `squad_lab` and `transfer_lab`), so neither is forbidden, as the OR-XI import test
does not forbid them (`tests/test_xi_extensions_api.py:239-251`). No function takes a default for a
value E-10's config holds (PIPELINE section 0, "Engineering"): those are module constants tied to
the config by test (3.1), and every served sentence that states a config value is a template
filled from those constants. No process over about 1.5 GB; Parquet read with a column list. Tests
skip cleanly without the corpus.

## 1. Shared definitions

### 1.1 Subjects, groups and the one definition

Seven subjects, in `subject_groups` order (config.json:207), are the only quantities Opponent Lab
shows as a record. Each is the object of WP A: its label is `spec.label` (or
`LEVEL_SUBJECTS[...].label`), its definition is `spec.describe()` (byte-equal to
`descriptor_test_vectors.json`, PIPELINE 3.6), its parts and part phrases are `spec.parts`, its
window is `spec.window` (`close_11v11` for every descriptor, PIPELINE 3.4). This file writes none
of them again.

| Group | Subject (registry id) | Kind | Parts, in declared order | ROOT 2.5 name check |
|---|---|---|---|---|
| `conceded` | `conceded_f3_entries_by_channel` (primary) | composition, 3 | `def_left`, `def_centre`, `def_right` | H14-H21: "share of final-third entries conceded, by lateral third", never weakness, vulnerability or weak flank; E-10's label says that, with "passes" and the frame |
| `conceded` | `conceded_f3_entries_wide_share` | composition, 2 | `wide`, `centre` | |
| `conceded` | `conceded_box_entries_by_origin_channel` | composition, 3 | `def_left`, `def_centre`, `def_right` | |
| `conceded` | `conceded_shots_inside_box_share` | composition, 2 | `inside_box`, `outside_box` | H14-H21: "location-only conversion value", never shot quality or provider xG; none is shown here |
| `own_actions` | `defensive_actions_by_pitch_third` | composition, 3 | `own_third`, `middle_third`, `opposition_third` | H14-H21: "defensive action distance", never "line height" (a copy-guard token); E-10 defines no distance, so none is shown (DISSENT 3) |
| `own_actions` | `high_zone_defensive_action_share` | composition, 2 | `high_zone_defensive_actions`, `opponent_own_60_passes` | H14-H21: the PPDA analogue is "opponent passes per recorded high-zone defensive action" (`s5_ratio_name`), named in prose only (PIPELINE 12.3, `s5_panel_rule`) |
| `level` | `conceded_f3_entries_per_90` | level | its count is the primary's three parts added; its exposure is `window_seconds` | |

"What the team did" is the `own_actions` group; "what was done against it" is the `conceded`
group and the level. No other quantity is shown as a record in this release: any other count
would be a definition no protocol registers (OPEN QUESTION 8). The level has no `describe()` and
no payload in WP A (PIPELINE 3.1, `LevelSubject`). Its definition is `LEVEL_DEFINITION_TEMPLATE`
(5.6) filled with WP A's own fields and nothing else: `LEVEL_SUBJECTS[LEVEL].label`,
`.unit_seconds`, and `TEAM_DESCRIPTORS[LEVEL_SUBJECTS[LEVEL].descriptor].describe()`, which
carries the parts and the window phrase. Its identity is the primary's fingerprint, served under
the key `counts_fingerprint` (the level reads the primary's counts), never as a fingerprint of its
own.

### 1.2 Decision date and the prior rule

A decision date `D` is spelled `YYYY-MM-DD` and nothing else (ADR-0021), is a real calendar day,
and lies from `RECORD_FIRST_DATE` = `"2017-07-01"` to `RECORD_LAST_DATE` = `"2018-07-01"`
inclusive (E-10 `season_start` and `end`, tied by test). Matches on calendar dates strictly
before `D` are used; the whole calendar day of `D` is excluded (`prior_rule`
`calendar_date_strictly_before`). The rule has one implementation, `estimator.state_at`, which
normalises `D` and every row's date to the day (PIPELINE 3.8). The record's counts are read from
the state it builds (2.2); the list of matches used is a second view of the same rows and a test
ties it to the state (8.1). A decision point of XI Lab fixes `D` to its scenario's `cutoff`
(`decision_lab.SCENARIOS`, decision_lab.py:44-57: `2018-05-06`, `2018-04-08`), which is the match
day: the match itself is excluded.

### 1.3 One window

The record and the estimate use one window, `close_11v11` (`descriptors.WINDOWS["close_11v11"]`,
E-10's `window_primary`), the window of every `TeamDescriptorSpec` (PIPELINE 3.4) and so of every
definition E-10 registers; its phrase is WP A's. The window is not a request field and is never a
declared row; the page prints its phrase. E-10's `window_sensitivity` (`all_states`) is a
sensitivity analysis inside the protocol, not a registered definition: a record in it would be a
definition no registry record names, whose fingerprint E-10 never froze, which 1.1 excludes. It is
not offered in this release (OPEN QUESTION 11).

### 1.4 Validity and the matches used

Validity is `match_validity`'s, decided once per match and never repaired (PIPELINE 2.4). An
invalid match adds nothing to any count or window time (`estimator.add_rows` selects valid rows,
PIPELINE 3.8) and is listed among the matches used with its first reason, in words (5.6,
`INVALID_*`). Its sheet result is still printed. A team with no valid prior match has no count:
every count, share, the window time and the rate are `null`, never 0, and the record prints
`NO_PRIOR_MATCH`.

### 1.5 Evidence classes (O13)

| Quantity | Class | Why |
|---|---|---|
| a count of recorded events; the number of valid matches | OBSERVED | the provider's events, tags and sheet, counted (`product_rules.evidence_class_of_record.counts`) |
| a share of a descriptor's parts; the level's rate per 90 minutes of window time; window time | DERIVED | a count ratio (`...shares_and_rates`); window time is a mechanical transformation of event times, each half ending at its last recorded event (PIPELINE 2.3), not a count |
| the E-10 estimate (3.3) | EXPERIMENTAL | `product_rules.evidence_class_of_panel` |
| a minimum a proposal sets | HEURISTIC, composed with the requirement's class (progression HEURISTIC; the side requirements EXPERIMENTAL, ADR-0019) and the cited record's class | `product_rules.proposal_class`; a percentile chosen as a minimum is a declared policy (`reference.DeclaredMinimum.evidence_class`) |
| the XI solve, ceilings, conflict | as XI Lab and OR-XI 7.6 compose them | `evidence.from_xi` of each requirement in force, `evidence.SOLVER_CLASS`, eligibility HEURISTIC |

Composition is `weakest()` through `shell.evidence_payload`. `DECLARED` is never a class (O12):
team, date, decision point, rules, thresholds, percentiles, acceptance, minima entered, locks,
exclusions, opt-ins and the slot are declared rows.

### 1.6 Verdict states and their product consequence

Every badge, statement and gate comes from `verdicts.verdict_for("E-10", subject)` through
`shell.verdict_payload`. The record is shown only where 1.7 allows; nothing else is.

| Registry state of the subject | Badge (`badge_text`) | Shown beyond the definition, badge and non-claim | Evidence class |
|---|---|---|---|
| no record (E-10 not registered) | `RECORD ONLY · NOT TESTED` | nothing: the record is withheld (1.7) | (none shown) |
| `PENDING` | `E-10 · RECORD ONLY · NOT RUN` | nothing: the record is withheld (1.7, DISSENT 1, N1) | (none shown) |
| `INCONCLUSIVE` | `E-10 · INCONCLUSIVE` | the record | counts OBSERVED; shares, rates and window time DERIVED |
| `ADDED_INFORMATION_NOT_SHOWN`, `SIDE_NOT_SHOWN`, `NOT_RELIABLE`, `STRENGTH_NOT_EXCLUDED` (NOT_ESTABLISHED) | `E-10 · TESTED · NOT ESTABLISHED` | the record | same |
| `DEFENDER_SHAPE_SIGNAL` (ESTABLISHED, limits) | `E-10 · TESTED · TENDENCY, ONE SEASON` | the record; behind the opt-in, at `D` on or after `PANEL_FROM_DATE`: the estimate of 3.3, the point only when the `reliability_lower_bound` figure is at least the config's bound | EXPERIMENTAL for the estimate; the record keeps its classes |
| `LEVEL_ESTABLISHED` (level, ESTABLISHED, limits) | `E-10 · TESTED · VOLUME, ONE SEASON` | the same rule for the volume | same |

The record of one subject is shown only when all seven records are `EXECUTED` (1.7, N1) and the
subject is not one E-09 still holds back (1.7, N4). The statement printed
beside each badge is the payload's `statement`, verbatim (the registry's `registry_outcomes`
sentence, `not_run_statement`, or "No registered protocol tests this claim."). The group's
non-claim (`registry_non_claims[group]`, config.json:498-502) is printed in every state, before
registration included: the page prints it from the server field `groups[].non_claim`, which
`panel.REGISTRY_NON_CLAIMS` supplies, never from `Shell.verdictLines` (which prints a non-claim
only when ESTABLISHED, labs-shared.js:147-154). Once a record exists, a test asserts its
`non_claim` equals the constant (PIPELINE 12.3). `lifecycle_status` is read by nobody here: a
NOT_ESTABLISHED or INCONCLUSIVE token never removes the record, it only never unlocks the
estimate. No LOCAL replication label exists or is shown (Z5).

### 1.7 The record gate (R5, PIPELINE 11)

Nothing in this work computes a descriptor column, a validity decision or a window time on the
real corpus before E-10 has run: not a route, a test, an e2e spec, a screenshot or a person
looking at a page. Two rules of the E-10 draft fix this.

- R5 and the protocol's prior-exposure table (preregistration.md:80, :86): no conceded split by
  lateral third, no defensive-action location and no team-season composition has been served,
  and criterion (f) rests on three leagues with no such exposure. A served record of every team
  of five leagues at every date is exactly those compositions.
- PIPELINE 11, row 1: E-10's pre-outcome code review, after the pipeline commit and before the
  gate stamp, signs that no file under review (WP A among them) was executed on `data/`; the only
  real-data test before the run is the `slow` oracle, with `columns=()` (PIPELINE 2.5). A record
  served between registration and that review would execute WP A on the corpus and break the
  check. Registration alone is therefore not enough.

ROOT 2.12 N1 accepts this gate (R-1): it opens at E-10's results commit, when all seven E-10
records are `EXECUTED`, and not at registration, and it sits inside the one loader that reads the
corpus for a record. The gate is in code. `record.record_available()` is true when, and only when, for each of the
seven subjects `verdicts.verdict_for("E-10", subject).basis` is `VerdictBasis.EXECUTED` (the
results commit gives every record its token, PIPELINE 12.2; `derive` reads EXECUTED for every
token but `PENDING`, verdicts.py:452-487). Product code may read only the registry from research
(ROOT 3b), and the registry has no state between `PENDING` and `EXECUTED`, so the gate opens at
the results commit, after the review, the gate stamp and the run. The gate sits inside the one
function that reads the corpus for a record: `record.load_league_tables` raises `RecordWithheld`
(a `RuntimeError`, a 500) when it is closed, so no caller, route or test can bypass it. The routes
check the gate first and never call the loader while it is closed.

**E-09 (N4, ruling R-3).** Three subjects are team aggregates of the event sets behind
E-09's unregistered player candidates: S3 (`conceded_shots_inside_box_share`) beside
`box_shot_share` on open-play shots, and S4 (`defensive_actions_by_pitch_third`) and S5
(`high_zone_defensive_action_share`) beside `opp_half_defensive_actions`, ground defending duels
and interception-flagged rows by start x (E-09 draft config.json, the `box_shot_share` and `opp_half_defensive_actions` candidates and `registry_candidate_subjects`). Under N4,
`record.subject_available(subject)` is `record_available()` and, for the three subjects of
`record.E09_ADJACENT`, at least one key of `verdicts.VERDICTS` under `"E-09"`. A subject that is
not available is withheld on its own: its definition, badge and non-claim are shown with
`SUBJECT_WITHHELD_E09` and no count, and its columns are not requested from
`build_team_match_table` (2.1), so they are never computed. N4 accepts this default, so no one is
exposed to the three subjects before E-09 is frozen; the alternative R-3 offered (E-09's
registration commit recording Opponent Lab exposure in its prior-exposure table, and
`E09_ADJACENT` becoming `()`) is not taken.

While `record_available()` is false:

- `POST /api/opponent/record` answers 200 with `record_state` `"WITHHELD"`, the seven
  definitions, their badges, every group's non-claim and `RECORD_WITHHELD_NOT_REGISTERED` or
  `RECORD_WITHHELD_NOT_RUN` (by whether the seven records exist), and no count, no matches block
  and no panel state. Only the match and team tables are read, to name the team (5.2), which is no
  quantity E-10 tests and runs no WP A function.
- `POST /api/opponent/proposal` answers 200 with `proposal_state` `"WITHHELD"` and
  `PROPOSAL_WITHHELD`; `POST /api/opponent/xi` with `accepted_proposal` is a 422
  (`ACCEPT_WHILE_WITHHELD`), and without it solves the XI under the minima entered or the
  defaults, its proposal block `WITHHELD` when rules are declared and `null` when none are.
- the desk reads no record in any state (6.4).

After the results commit the gate is open for good: a registry record is never removed, and an
`EXECUTED` record never returns to `PENDING`.

## 2. The prior-date record: `galactico/models/opponent/record.py`

Module docstring: claim = counts of E-10's declared event sets in a team's league matches before a
date, for and against, in E-10's window, read from the one estimator's state, and their shares,
window time and rate; non-claim = no tendency, no adjustment for opponents or strength, no
statement about how well a team defends, no order of teams.

### 2.1 The league table

```python
RECORD_VERSION = "opponent-record-v2"
LEAGUES: tuple[str, ...] = ("Spain", "England", "Italy", "Germany", "France")  # = config leagues
WINDOW_KEY = "close_11v11"                                       # = config window_primary
ACTION_COLUMNS: tuple[str, ...]  # = PIPELINE I1, verbatim
SIDECAR_EVENT_COLUMNS = ("card", *descriptors.GOAL_INCIDENT_COLUMNS)
E09_ADJACENT: tuple[str, ...] = ("conceded_shots_inside_box_share",
                                 "defensive_actions_by_pitch_third",
                                 "high_zone_defensive_action_share")      # 1.7, N4

class RecordCorpusDefect(RuntimeError): ...   # a corpus that cannot give a table; the router's 503
class RecordWithheld(RuntimeError): ...       # the gate is closed; never reached by a route (500)

@dataclass(frozen=True)
class LeagueTables:
    league: str
    table: pd.DataFrame                  # the table of PIPELINE 2.2, window close_11v11
    subjects: tuple[str, ...]            # the subjects whose columns it holds, in subject order
    team_ids: tuple[int, ...]            # sorted ids of every team with a row
    team_names: Mapping[int, str]
    provenance: Mapping[str, object]     # sidecar.provenance(league), TEAM_MATCH_VERSION,
                                         # descriptor fingerprints, public file identity

def load_league_tables(league: str, subjects: Sequence[str]) -> LeagueTables: ...
def record_available() -> bool: ...      # 1.7
def subject_available(subject: str) -> bool: ...   # 1.7
```

`load_league_tables` first checks the gate: it raises `RecordWithheld` unless
`record_available()` holds and every subject of `subjects` is `subject_available`. It then reads,
in this order and nothing else: `load_public(league, tables=("actions", "matches", "teams"),
action_columns=ACTION_COLUMNS)`; `sidecar.verify(league)`; `sidecar.load(league, "events",
columns=["event_id", *SIDECAR_EVENT_COLUMNS])` and `sidecar.attach(actions, events,
SIDECAR_EVENT_COLUMNS)` (I2, I3); `sidecar.load(league, "matches", columns=["game_id",
"home_score", "away_score"])` cast to `int64` as `match_meta` (I4; coach ids are not read);
`sidecar.load(league, "squads", columns=["game_id", "team_id", "player_id", "red_minute"])` reduced
to `sheet_dismissals` exactly as I5 says. A team-match of `matches` with no `squads` row, a
duplicate `game_id`, or any `ValueError` that `build_team_match_table` raises on these frames is a
property of the corpus, not of a request: the function raises `RecordCorpusDefect` with the
cause, so it is never answered as a 422 (`runtime.lab_errors` turns a `ValueError` into one). Then
`build_team_match_table(actions, matches, columns=required_columns(specs),
window=WINDOWS[WINDOW_KEY], match_meta=..., sheet_dismissals=...,
regulation_periods=REGULATION_PERIODS, dismissal_cards=DISMISSAL_CARDS,
sentinels=WY_LOCATION_SENTINELS, coordinate_range=COORDINATE_RANGE, xt=None)`, with `specs` the
`TEAM_DESCRIPTORS` entries of the descriptor subjects of `subjects` (and the primary when the level
is among them) and the constants of `descriptors.py` (PIPELINE 2.1, "Callers in product code pass
the constants"). No xT surface is fitted: no descriptor reads one, and `match__positive_xt_gain` is
an oracle aid only. The action frame is dropped before return; the table holds one row per team
and match. The audit frame is not kept (OPEN QUESTION 9).

The frame preparation (I1 to I5) restates what E-10's runner does in `load_league` and
`league_tables` (PIPELINE 7.4), which product code may not import (PIPELINE section 0). It is tied
to the runner by a data-free test that feeds both the same synthetic frames and asserts equal
tables (`test_loader_tables_equal_the_runners`, 8.1; tests may import both sides, as the tie of
ROOT 2.10 W3 does), and by that test's `slow` twin on Spain once the gate is open (8.5). A change
the registration makes to I5 (for example `dismissal_check_fallback`, PIPELINE 13) therefore fails
the test until the record follows it.

### 2.2 The record

```python
@dataclass(frozen=True)
class PartRecord:
    part: str; phrase: str
    count: int | None                 # None when the team has no valid prior match
    share: Fraction | None            # None when the subject's events are 0 or None

@dataclass(frozen=True)
class SubjectRecord:
    subject_id: str; group: str; kind: str      # "composition" | "level"
    label: str; definition: str
    fingerprint: str                            # the spec's; the primary's for the level
    state: str                                  # "SHOWN" | "WITHHELD" (E-09, 1.7)
    parts: tuple[PartRecord, ...]               # () for the level and when withheld
    events: int | None                          # the parts' counts added
    window_seconds: Fraction | None             # the team's valid prior window time
    rate_per_90: Fraction | None                # level only

@dataclass(frozen=True)
class MatchUsed:
    game_id: int; date: str; opponent_id: int; opponent_name: str
    is_home: bool; goals_for: int; goals_against: int
    valid: bool; invalid_reason: str; window_seconds: Fraction | None

@dataclass(frozen=True)
class OpponentRecord:
    league: str; team_id: int; team_name: str; date: str
    valid_matches: int; invalid_matches: int
    matches: tuple[MatchUsed, ...]              # by (day, game id)
    subjects: tuple[SubjectRecord, ...]         # subject_groups order

def build_record(tables: LeagueTables, *, team_id: int, date: str) -> OpponentRecord
```

`build_record` reads no file. **Counts.** For each composition subject the table holds: `rows =
estimator.descriptor_rows(tables.table, spec, league=tables.league,
exposure_unit_seconds=EXPOSURE_UNIT_SECONDS)`; `state = estimator.state_at(rows,
team_ids=tables.team_ids, parts=spec.part_names, date=date, weights=np.ones(len(rows)))`; with
`u = tables.team_ids.index(team_id)`, the part counts are `state.counts[:, u, :, :].sum(axis=(0,
1))`, the team's prior events per part. That marginal is the estimator's `O_u`
(`shape_estimate(state, ...).observed[u]`, which does not depend on the constants); a test ties
the two (8.1), so the record holds no second count. There is one `state_at` call per composition
subject the table holds (six at most); the level reads the primary's state and makes no call of
its own. Counts are integers held in `float64` by the state; each is converted with a check that
it is a whole number (a non-integer is a `RuntimeError`, a fault). A `ValueError` raised by an
estimator call (an id outside `team_ids`, a malformed table) is re-raised as `RuntimeError`: it is
a fault of the corpus or of this code, never a refusal of the request. A subject the table does
not hold (withheld, 1.7) gets `state` `"WITHHELD"`, no parts and every number `None`.

**Window time and rate.** `window_seconds` is the exact sum `sum(Fraction(x) for x in ...)` of the
table's `float64` `window_seconds` over the team's valid rows of `matches` (below): exact over the
values the table holds, whatever order they are added in. The state's exposure for the team
(`state.exposure[:, u, :].sum()`, a `float64` sum of the same values divided by
`EXPOSURE_UNIT_SECONDS`) is not the source of a printed number; a test asserts the two agree within
a relative `1e-12` (8.1), so both views read the same rows. The level's `events` is the primary's,
and `rate_per_90 = Fraction(events) * EXPOSURE_UNIT_SECONDS / window_seconds` (window time in
units of 5,400 seconds, 90 minutes), `None` when `window_seconds` is `None` or 0; a team with
window time and no conceded entry has rate 0, which is printed. A share is `Fraction(count,
events)`, `None` when `events` is 0 or `None`. With no valid prior match, every count, `events`,
`window_seconds` and `rate_per_90` is `None`.

**Matches used.** `matches` lists every row of the team's table whose calendar day is before `D`,
valid or not, sorted by (day, `game_id`). `MatchUsed.date` is
`pd.Timestamp(row.date).normalize().date().isoformat()`, the day `state_at` compares (the table's
`date` is the provider's string, a UTC date and time for Wyscout, PIPELINE 2.2 and 4.1); its
`window_seconds` is `Fraction` of the table's value, `None` when invalid. The list restates the
prior rule for display only; `test_matches_used_agree_with_the_state` (8.1) asserts that the
per-part counts added over the listed valid matches equal the state's, for `D` given as a date,
with planted rows on `D`'s day and later and a late-evening UTC match the day before.

### 2.3 Texts

Every text is a pure function of a record, built in the router (5.4), never in the page.

| Text | Rule |
|---|---|
| `count_text` | `"{count} of {events}"`, integers with thousands separators; `null` when `count` is `None` |
| `share_text` | the share as a percentage at one decimal, rounded half-even from the exact `Fraction` (`"38.0%"`); `null` when the share is `None` |
| `events_text` | `"{events} events"`; `null` when `None` |
| `minutes_text` | window time in whole minutes, rounded half-even from the exact `Fraction`, thousands separators (`"2,314"`); `null` when `None` |
| `rate_text` | the rate at two decimals, rounded half-even, then `" per 90 minutes of window time"` (`"0.00 per 90 minutes of window time"` for window time with no event); `null` when `None` |
| `sample_text` | `SAMPLE_TEXT` with events, valid matches and minutes; `null` with no valid prior match |
| `goals_text` | `"{goals_for}–{goals_against}, {venue}"`, the match sheet's full-time result (PIPELINE 2.2), `venue` `VENUE_HOME` or `VENUE_AWAY` |

No text compares a team with its league or with another team, and no part is picked out
(`product_rules`: "No part is highlighted, sorted by size, or called the largest. No
league-relative adjective. No single number summarises an opponent.").

## 3. The served computation: `galactico/models/opponent/panel.py`

Module docstring: claim = E-10's served estimate (PIPELINE 12.3) for an ESTABLISHED record,
computed by the one estimator; non-claim = shown only where E-10 established it, decided on
matches of the whole season, never a statement that a team defends a channel badly.

### 3.1 Constants tied to the config

PIPELINE 3.7 and 12.3 put `served_panel`, `product_rules` and `registry_non_claims` in "the
Opponent Lab module". They live here, because the computation that reads them lives here and a
model module does not import the API layer; `api/opponent_lab.py` reads them from here and holds
no copy.

```python
SERVED_PANEL: Mapping[str, object]        # = config served_panel, verbatim
PRODUCT_RULES: Mapping[str, object]       # = config product_rules, verbatim
REGISTRY_NON_CLAIMS: Mapping[str, str]    # = config registry_non_claims, verbatim
SUBJECT_GROUPS: Mapping[str, tuple[str, ...]]   # = config subject_groups
PANEL_FROM_DATE = "2018-01-01"            # = config evaluation_start (product_rules.panel_from_date)
EXPERIMENT_ID = "E-10"                    # = config registry_experiment_id
PRIMARY = "conceded_f3_entries_by_channel"; LEVEL = "conceded_f3_entries_per_90"
RECORD_FIRST_DATE = "2017-07-01"; RECORD_LAST_DATE = "2018-07-01"   # season_start, end
```

`test_constants_equal_the_config` reads `experiments/preregistered/E-10-conceded-shape/
config.json` when it exists and the draft `docs/research/north-star/protocol-drafts/
E-10-conceded-shape/config.json` otherwise, and asserts each constant equals its key,
`record.LEAGUES == config["leagues"]`, `record.WINDOW_KEY == config["window_primary"]`, and that
every served sentence that states a config value (`PANEL_HEAD_*`, `PANEL_HOLES`,
`PANEL_POINT_WITHHELD`, `PANEL_BEFORE_DATE`, `DATE_RANGE`, `S5_RATIO_NOTE`, 5.6), rendered, contains
the value it states. `PRODUCT_RULES["words_never_on_the_page"]` is in the module and is never served
outside a provenance block: all five words are copy-guard tokens (labels.py:25), so a served copy
would be refused by `finalize`. The estimator's `LEAGUE_PRIOR_PSEUDOCOUNT_PER_PART` is the
estimator's constant (PIPELINE 3.7), not restated here.

### 3.2 When the estimate is offered

`offered(subject, *, date) -> bool` is true when, and only when, all hold: the subject is
available (`record.subject_available`), `verdicts.verdict_for(EXPERIMENT_ID, subject).may_gate` is
true (PUBLIC, EXECUTED, ESTABLISHED; verdicts.py:452-487), and `date >= PANEL_FROM_DATE`. It is
shown when it is offered and the request carries `panel_opt_in: true`
(`product_rules.panel_needs_opt_in`). Nothing else gates it, and a LOCAL label never does
(ADR-0018). For a shown record where it is not offered, the reason is `PANEL_NOT_OFFERED` (not
`may_gate`) or `PANEL_BEFORE_DATE`, in that order; for a withheld record there is no panel state at
all (5.4.2). With today's registry `offered` is false for every subject.

### 3.3 The computation (PIPELINE 12.3, verbatim in substance)

```python
@dataclass(frozen=True)
class PanelEstimate:
    subject_id: str; kind: str
    point: tuple[float, ...] | float | None     # None when the point is withheld (below)
    interval: tuple[tuple[float, float], ...] | tuple[float, float] | None
    shrink_weight: float
    worlds: int; holes: int; world_seed: int; world_scheme: str
    world_namespace: str; world_matches: int    # WorldWeights.namespace, len(WorldWeights.games)
    k_context: float; k_unit: float; reliability_lower_bound: float
    point_shown: bool

def estimate(tables: LeagueTables, *, team_id: int, date: str, subject: str,
             worlds: snapshots.WorldWeights) -> PanelEstimate
def panel_worlds(tables: LeagueTables, *, date: str) -> snapshots.WorldWeights
```

1. Figures: `figures = verdicts.figures_for(EXPERIMENT_ID, subject)` (the level reads the level
   record's three); `kA = figures["k_context"].value`, `kD = figures["k_unit"].value`, `rel =
   figures["reliability_lower_bound"].value`, each checked to be a finite `int` or `float` and not
   a `bool`. A missing or malformed figure is a `RuntimeError`: the results commit gives every
   E-10 record under an established token its three figures (PIPELINE 12.2), so one missing is a
   fault.
2. Rows: `estimator.descriptor_rows(tables.table, spec, ...)`, the primary's for the level.
3. Point state: `estimator.state_at(rows, team_ids=tables.team_ids, parts=spec.part_names,
   date=date, weights=ones)`; `shape_estimate(state, league_pseudocount=
   estimator.LEAGUE_PRIOR_PSEUDOCOUNT_PER_PART, k_context=kA, k_unit=kD)` and
   `served_composition(est, team_id)` for a composition; `level_estimate(state,
   k_context_level=kA, k_unit_level=kD)` and `served_volume(est, team_id)` for the level. The
   first value is the point, the second the shrink weight (`O_total / (O_total + kD)`, or
   `E'_u / (E'_u + kD')`).
4. Worlds: `panel_worlds` takes `game_ids` = the ids of the league's **valid** matches whose
   normalised date is before `pd.Timestamp(date).normalize()` and returns
   `snapshots.league_world_weights(game_ids, SERVED_PANEL["worlds"], SERVED_PANEL["world_seed"],
   scheme=SERVED_PANEL["world_scheme"])`. In world `r`, a row's weight is `w.weights[r, j]` for its
   match at position `j` of `w.games` (sorted ids; the position is found by the row's `game_id`,
   never by row order), and 0 for a row whose match is not in `w.games`. The router calls
   `panel_worlds` once per request and passes the one `WorldWeights` to every subject's
   `estimate`: validity is per match, so `game_ids` is the same for all seven, and the panel's
   subjects share their worlds (R12). The namespace and the number of matches drawn are served in
   each panel's provenance, the same for every subject of one reply (R12: world ids are
   preserved).
5. Per world, step 3's calls with those weights. A world in which the team has no prior event is a
   hole (PIPELINE 12.3, verbatim): the team's `observed` row summed is 0 for a composition, its
   `unit_observed` is 0 (`O'_u`) for the level. Holes are counted and left out. The interval of
   each part (or of the volume) is `np.quantile(values, SERVED_PANEL["interval_quantiles"],
   method=SERVED_PANEL["interval_quantile_method"])` over the other worlds; with every world a hole
   there is no interval.
6. Point rule: `point_shown = rel >= PRODUCT_RULES["point_needs_reliability_lower_bound_at_least"]`;
   when false `point` is `None` and only the interval is served.
7. S5 (`high_zone_defensive_action_share`) is served as its two-part share, under its label, like
   every two-part subject; the ratio `s5_ratio_name` names is never computed, served or labelled
   (`product_rules.s5_panel_rule`); `S5_RATIO_NOTE` names it in prose.

A `ValueError` from an estimator call is re-raised as `RuntimeError` (a fault, never a 422).
Nothing of PIPELINE 4.2 is computed here: `pi`, `A_c^(-u)`, `e`, `delta_u`, `lam`, `rD_u` are the
estimator's (Z3; "there is no second implementation and no parity test"). Texts: a composition's
point and interval ends as percentages at one decimal, rounded half-even from `Fraction(float)`;
the volume at two decimals with `" per 90 minutes of window time"`; the shrink weight at three
decimals. Evidence `EXPERIMENTAL`; the panel prints the record's statement and the group's
non-claim, and `PANEL_HEAD_COMPOSITION` or `PANEL_HEAD_VOLUME` by its kind.

## 4. The requirement proposal: `galactico/models/opponent/proposal.py`

Module docstring: claim = which of the rules a user declared hold on an opponent record, and which
requirement each sets; non-claim = the link from a record to a requirement is the user's
declaration, HEURISTIC under every verdict, and changes no solve until accepted.

### 4.1 The policy: templates, named after what they set

```python
PROPOSAL_POLICY_VERSION = "opponent-proposal-policy-v1"

@dataclass(frozen=True)
class ProposalTemplate:
    template_id: str
    subject_id: str                  # the cited E-10 subject
    part: str | None                 # the cited part; None for the level's rate
    kind: str                        # "share" | "rate"
    requirement_ids: tuple[str, ...] # the measured requirements of decision_inputs it sets

    label -> str                     # template_label(self): built, never written (below)

TEMPLATES: tuple[ProposalTemplate, ...]
```

| `template_id` | Cites | Sets |
|---|---|---|
| `left-origins-from-f3-def-right` | `conceded_f3_entries_by_channel`, `def_right` | `left_pass_origins` |
| `right-origins-from-f3-def-left` | `conceded_f3_entries_by_channel`, `def_left` | `right_pass_origins` |
| `both-origins-from-f3-wide` | `conceded_f3_entries_wide_share`, `wide` | `left_pass_origins`, `right_pass_origins` |
| `left-origins-from-box-def-right` | `conceded_box_entries_by_origin_channel`, `def_right` | `left_pass_origins` |
| `right-origins-from-box-def-left` | `conceded_box_entries_by_origin_channel`, `def_left` | `right_pass_origins` |
| `progression-from-f3-per-90` | `conceded_f3_entries_per_90`, rate | `progression` |

A template's label is built from WP A and XI objects and holds no definition of its own:
`TEMPLATE_LABEL_SHARE` or `TEMPLATE_LABEL_RATE` (5.6) filled with the labels of
`xi_extensions.MEASURED_REQUIREMENTS` for `requirement_ids`, the cited subject's `label` and, for a
share, the cited `PartRef.phrase` of `TEAM_DESCRIPTORS[subject].parts`.

The frame: `def_right` is the defending team's right lateral third, which is the attacking team's
left (PIPELINE 3.4: `def_right <- against att_left`; the mirror lives in the descriptor), and XI
Lab's `left_pass_origins` counts passes with `start_y < 0.21` in the acting team's frame
(historical.py:148), so a rule citing `def_right` sets the attacking XI's left wide-channel
requirement. `test_templates_follow_the_descriptor_mirror` (8.1) reads each cited `PartRef` from
WP A and asserts that its columns are all `att_left` for a template that sets `left_pass_origins`
alone, all `att_right` for `right_pass_origins` alone, and both for `wide`, and pins the six rows
literally, so a swapped row needs a visible edit. No template cites S3, S4 or S5: no requirement
XI Lab measures corresponds to them, and inventing one is out of scope (R4). Templates are fixed in
code and in the GET menu; a template is a structure, not a number. Every number is the user's.

### 4.2 Rules and their evaluation

A rule is `{template_id, threshold, percentile}`, all three declared, none with a default (as O7
gives the frontier no default dimension): `threshold` a share in `[0, 1]` for a share template
and a rate in `[0, 1000]` per 90 minutes of window time for the rate template; `percentile` one of
`reference.PERCENTILE_MENU` (10, 25, 50, 75, 90). Each template at most once per proposal; at most
six rules. Two declared templates that set a common requirement must declare the same percentile
(`PROPOSAL_CONFLICT`, refused at validation, 5.2, whatever the record holds); no merging rule is
invented. Each template's comparison is "at least"; no template compares two parts of one record,
so no rule picks out the larger part (`product_rules`, 1.6).

```python
@dataclass(frozen=True)
class RuleOutcome:
    template: ProposalTemplate; threshold: float; percentile: int
    state: str                       # "HOLDS" | "DOES_NOT_HOLD" | "UNDECIDED"
    value: Fraction | None           # the record's share or rate the rule read

def evaluate(record: OpponentRecord, rules: Sequence[tuple[str, float, int]]) -> tuple[RuleOutcome, ...]
def requirements_set(outcomes: Sequence[RuleOutcome]) -> Mapping[str, tuple[int, tuple[str, ...]]]
```

`evaluate` compares in exact arithmetic: `value >= Fraction(format_plain(threshold))`, so a
threshold entered as `0.4` is `2/5` and a share of exactly `2/5` holds (the float `0.4` is above
`2/5`, and comparing with it would not). `value` is the record's `share` of the cited part (exact)
or the level's `rate_per_90`, which is exact over the table's `float64` window seconds (2.2), so a
rate exactly at the threshold holds. When `value` is `None` (no event, or no window time) the
state is `UNDECIDED`: unknown is never evidence of absence (R11), and an undecided rule sets
nothing. Outcomes come back in `TEMPLATES` order whatever the request's order.
`requirements_set` returns, for each requirement set by at least one rule that holds, its
percentile and the template ids that set it; two holding rules for one requirement carry one
percentile by validation, so a disagreement there is a `RuntimeError` (a fault). The same
percentile from two rules is one minimum citing both.

### 4.3 Minima (in the router)

For a decision point `s` of `decision_lab.SCENARIOS`, the league reference at `s`'s cutoff is
`reference.load_league_reference(competition="Spain", cutoff=s.cutoff, subject_team_id=675,
population="ALL_TEAMS", experimental_opt_in=opt_in)` (675 is Real Madrid, a side of both decision
points' matches; a test asserts it of each `SCENARIOS` match id), behind the build gate (5.3). Each
set requirement's minimum is `reference.declared_minimum(league, requirement_id, percentile)`: its
`value` (the float the solve receives), its `label` (the source sentence) and its
`reference_fingerprint` (provenance). A template that sets a side requirement needs
`experimental_opt_in` (`EXPERIMENTAL_OPT_IN_ERROR`, the sentence of `xi_extensions.declare`).
Units: the reference sums the same per-90 rates of ten outfield starters that the match snapshot's
normaliser is the club median of; `test_reference_club_median_is_the_snapshot_normaliser` (slow,
8.5) asserts `league.distributions[r].subject_club_median == snap.requirement_minima[r]` at both
decision points for the three requirements, and the proposal is not shipped if it fails (OPEN
QUESTION 5).

### 4.4 Qualifiers (PIPELINE 12.3, `proposal_sentence_rule`)

The records a proposal cites are those of its rules that hold. For each cited record whose
`may_gate` is false the proposal carries one qualifier, beside that record's label, in
`SUBJECT_GROUPS` order, none merged or dropped: `proposal_sentence_not_tested` ("based on a
record E-10 has not tested") when the record is not registered, `PENDING` or `INCONCLUSIVE`, and
`proposal_sentence_not_established` ("based on a record that did not pass E-10") when its status
is NOT_ESTABLISHED. A cited record whose `may_gate` is true needs none. Since the record is shown
only once every E-10 record is `EXECUTED` (1.7), a served qualifier is in practice the
`INCONCLUSIVE` or NOT_ESTABLISHED case; the module and its test still cover every state. The
proposal stays HEURISTIC under every verdict (`product_rules.proposal_class`).

### 4.5 Acceptance, and how an accepted proposal enters an XI solve

A proposal is shown and changes nothing until a request that solves the XI carries
`accepted_proposal`, the `fingerprint` the proposal reply served. The fingerprint is
`planning._digest` of `PROPOSAL_POLICY_VERSION`, the canonical rules, the decision point, the
experimental opt-in, `_token("Spain")` (public files, sidecar and registry, 5.3), each rule's
outcome state and each minimum it sets (`repr` of the float): one fingerprint is one proposal as
shown. The XI route recomputes the proposal from the declared rules and refuses with
`PROPOSAL_CHANGED` (422) when its fingerprint differs from the one sent, so a rule edited after the
proposal was read, or a corpus or registry change between the two requests, never applies minima
the reader did not see (ROOT 2.3: the user must accept the proposal, which presupposes seeing it).
Acceptance is a declared row and is in the cache key; no minimum the server served is ever sent
back by the page (R10): the fingerprint is an identity, not a number.

An accepted proposal enters an XI solve through the existing XI declared-requirements path and no
other: its minima join the minima entered as the `minimums` argument of
`decision_lab.decision_inputs(snap, formation, mode, minimums)`, the shipped function
`/api/xi/solve` calls (decision_lab.py:241-332), applied through `xi_extensions.declare` (the
opt-in rule of OR-XI 1.3), and solved by `solve_xi` with the arguments `decision_lab.solve` passes
(5.4.3). The opponent XI reads `in_force`, `locks` and `excludes` of the `Declared` that `declare`
returns and never its `entered` set (which counts every key of `minimums`): the origin of each
minimum in force comes from the request (5.4.3). The reply prints `XI_LAB_MINIMA` with each
minimum written by `format_plain`, so a reader who types those numbers into XI Lab's minimum inputs
sends `/api/xi/solve` the same floats; with the experimental opt-in and the same locks, exclusions
and mode, `test_xi_part_equals_api_xi_solve` (8.1) asserts that the `solve_xi` result equals
`/api/xi/solve`'s with `bootstrap_worlds: 0`. With `accepted_proposal`, a requirement in
`minimums` that any declared template sets is refused (`ENTERED_AND_PROPOSED`, at validation,
whatever the record holds). Squad Lab's declared-requirements path
(`RequirementDeclaration(source="LEAGUE_PERCENTILE")`) is not used for a proposal in this
release: a proposal belongs to one match, and the planning point is the season's end (OPEN
QUESTION 4).

### 4.6 What the proposal and the record cannot say

Printed on the page in every state, as server strings (5.6): `CANNOT_SAY_FUNNEL` (ROOT 2.2, H14:
funnelling and weakness are observationally confounded, so a share conceded on one side is not a
side defended badly and not a place to attack), `CANNOT_SAY_OPPONENTS` (the record is not adjusted
for the opponents met or for strength; where the E-10 estimate is shown it is measured against what
the opponents met produced in their other matches, and is still not adjusted for strength),
`CANNOT_SAY_ORDER`, and the proposal's `PROPOSAL_NON_CLAIM`. The five words of
`words_never_on_the_page` appear nowhere served or rendered (they are copy-guard tokens, so
`finalize` and the render test both enforce it).

## 5. API: `galactico/api/opponent_lab.py`

### 5.1 Routes

| Method | Path | Budget (seconds, local `OPPONENT_BUDGETS`) | Long | Request | Reads the corpus |
|---|---|---|---|---|---|
| GET | `/opponent` | | | | no: `FileResponse(web/opponent.html)`, `include_in_schema=False` |
| GET | `/api/opponent/menu` | | | | no (5.4.1) |
| GET | `/api/opponent/teams` | | | | match and team tables of the leagues present (`planning.clubs()`) and Spain's matches table for the decision points; 503 when none |
| POST | `/api/opponent/record` | `opponent.record`: 30 | no | `RecordRequest` | the league's public tables and sidecar once the gate is open (1.7); the match and team tables before |
| POST | `/api/opponent/proposal` | `opponent.proposal`: 30 | no | `ProposalRequest` | Spain's tables and sidecar once the gate is open, and the league reference |
| POST | `/api/opponent/xi` | `opponent.xi`: 60 | no | `OpponentXIRequest` | the match snapshot; with rules, as the proposal |

The budgets are local to the router, as Squad Lab's `RECORD_BUDGETS` (squad_lab.py:83) and
Transfer Lab's `UNIVERSE_BUDGET_SECONDS` (transfer_lab.py:77) are, so `runtime.BUDGETS` and its
pinned test (`tests/test_lab_runtime.py:115-128`, which asserts no key starts with `opponent` or
`desk`) do not change. No route here enumerates: one XI solve and 40 cheap estimator passes are
not what `LONG_ROUTES` names, so no route takes a long-computation place and none calls
`runtime.long_job` (which would raise `KeyError` for a route outside `BUDGETS`). The budget bounds
the builds; the XI solve keeps XI Lab's own 15-second limit whatever the budget has left (5.4.3),
so a cold XI request can last its budget plus the solve and one build. The budgets are first
numbers, not measurements. The XI route without rules, and the desk, read no record and are
measured on the corpus before the routers are registered; the record and proposal routes cannot
compute before E-10's results commit (1.7), so their cold times and peak memory are measured then
and recorded as a note to ADR-0032 in that commit (section 11), as X5 timed the risk routes; a
budget is raised there if a measurement needs it. The router is
`APIRouter(route_class=decision_lab.DecisionRoute)`; no path collides with another router's
(`tests/test_xi_extensions_api.py:1745-1766` pattern).

### 5.2 Request models

All `ConfigDict(extra="forbid")`; integers, floats and booleans strict; floats
`allow_inf_nan=False`.

```python
TemplateId = Literal["left-origins-from-f3-def-right", "right-origins-from-f3-def-left",
                     "both-origins-from-f3-wide", "left-origins-from-box-def-right",
                     "right-origins-from-box-def-left", "progression-from-f3-per-90"]
Fingerprint = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]

class RecordRequest(BaseModel):
    competition: planning.League
    team_id: planning.StrictId
    decision_date: StrictStr           # format and day checked by the model validator
    panel_opt_in: StrictBool = False

class ProposalRule(BaseModel):
    template_id: TemplateId
    threshold: Annotated[float, Field(strict=True, ge=0, le=1000, allow_inf_nan=False)]
    percentile: Annotated[Literal[10, 25, 50, 75, 90], planning.INTEGER_ONLY]

class ProposalRequest(BaseModel):
    scenario_id: str = "madrid-2018-05-06"          # a key of decision_lab.SCENARIOS, else 404
    experimental_opt_in: StrictBool = False
    rules: list[ProposalRule] = Field(min_length=1, max_length=6)

class OpponentXIRequest(xi_extensions.XIDeclarations):   # scenario_id, formation, locks,
    mode: Literal["BALANCE", "SATISFY"] = "BALANCE"      # excludes, experimental_opt_in
    minimums: dict[xi_extensions.RequirementId, xi_extensions.Minimum] = Field(default_factory=dict)
    rules: list[ProposalRule] = Field(default_factory=list, max_length=6)
    accepted_proposal: Fingerprint | None = None
```

`get_args(TemplateId) == tuple(t.template_id for t in proposal.TEMPLATES)`, by test. Model
validators refuse, each with its fixed sentence and no input value, whatever the corpus holds: a
decision date not spelled `YYYY-MM-DD` (`DATE_FORMAT`; the field is a plain string so this
sentence, not pydantic's pattern error, is served); one that is not a calendar day or lies outside
`RECORD_FIRST_DATE..RECORD_LAST_DATE` (`DATE_RANGE`); a share template's threshold above 1
(`THRESHOLD_SHARE`); a template named twice (`RULE_TWICE`); two declared templates that set a
common requirement at different percentiles (`PROPOSAL_CONFLICT`); `accepted_proposal` with no
rule (`ACCEPT_WITHOUT_RULES`); `accepted_proposal` with a requirement in `minimums` that a declared
template sets (`ENTERED_AND_PROPOSED`). Then, at declaration time, `ValueError` (422): a side
requirement in `minimums`, or a template that sets one, without the opt-in
(`EXPERIMENTAL_OPT_IN_ERROR`); `accepted_proposal` while the record is withheld
(`ACCEPT_WHILE_WITHHELD`); `accepted_proposal` that differs from the recomputed fingerprint
(`PROPOSAL_CHANGED`, 4.5); a lock or exclusion that is not a gated candidate (`UNKNOWN_PLAYER`,
through `xi_extensions.declare`). A team with no league match in the declared league is a 404
(`UNKNOWN_TEAM`), decided from `planning.league_clubs(competition)` before any build; an unknown
decision point is a 404 (`UNKNOWN_DECISION_POINT`).

### 5.3 Handler skeleton, loaders, keys

The ADR-0024 shape, as `squad_lab._answer` (squad_lab.py:256-280):

```
budget = runtime.Budget(OPPONENT_BUDGETS[route])          # at handler entry
resolve: team (404) or decision point (404)
with runtime.lab_errors(), _sidecar_errors():
    key = runtime.cache_key(route, canonical(request), _token(league))
    def compute():
        if not record.record_available(): return runtime.finalize(withheld(...))   # 1.7
        subjects = tuple(s for s in SUBJECTS if record.subject_available(s))       # 1.7
        tables = _league_tables(league, _sidecar_token(league), subjects)          # gated
        ...                                                                          # 5.4
        return runtime.finalize(payload)
    data, hit = runtime.RESULTS.get_or_compute(key, compute, store=runtime.is_complete)
    return runtime.respond(data, cache_hit=hit)
```

- `_league_tables` is `@planning._built_once(maxsize=5, reads=lambda league, sidecar_token,
  subjects: (league,))` around `record.load_league_tables(league, subjects)`: one build per key,
  two builds at once in the process (shared with planning's loaders), 429 after the wait, and the
  public file identity in the build key. The sidecar's identity is the argument `sidecar_token`,
  so a rebuilt sidecar is a new key and is built again: `_files_token` covers only the public
  Parquet tables (planning.py:685-693), which is why the token is passed explicitly. `subjects` is
  in the key, so the table is rebuilt with more columns once E-09's records arrive.
- `_sidecar_token(league)`: `planning._digest` of `[name, size, mtime_ns]` of
  `sidecar.SIDECAR_ROOT/{league}/` `MANIFEST.json`, `events.parquet`, `matches.parquet`,
  `squads.parquet`, an absent file recorded as absent (the build then raises `SidecarMissing`, a
  503). `_token(league)` is `planning._digest` of three parts: `"public"`, the present-file listing
  `planning._corpus_files((league,))` returns, raising `FileNotFoundError` (a 503) when it reports
  an absent file, as `planning.corpus_token` does; `"sidecar"`, `_sidecar_token(league)`; and
  `"registry"`, the seven E-10 verdict payloads and whether an E-09 record exists. The registry is
  in the key because the reply depends on it (1.6, 1.7) and the result cache outlives a test's
  patched registry otherwise.
- `_reference_at(scenario_id, opt_in)` is `@planning._built_once(maxsize=4, reads=lambda
  scenario_id, opt_in: ("Spain",))` around the call of 4.3. The match snapshot is
  `xi_extensions._match_snapshot(scenario_id, 0)` (the gated loader; `decision_lab.snapshot` and
  `runtime.match_snapshot` are not called, OR-XI 7.3).
- `_sidecar_errors()`, the inner context manager, maps `SidecarMissing`, `SidecarStale`,
  `SidecarMismatch` and `record.RecordCorpusDefect` to `HTTPException(503, SIDECAR_UNAVAILABLE)`.
  It sees `SidecarMissing` (a `FileNotFoundError`) before `lab_errors` would answer it with the
  corpus sentence, whose page remedy ("Run the Pappalardo fetch and ingest.", labs-shared.js:207-210)
  is the wrong one for a sidecar. A missing public file is not caught here and stays the corpus
  503.
- `canonical(request)`: `request.model_dump(mode="json")`, locks and exclusions sorted and
  de-duplicated, rules sorted by `template_id` (outcomes are returned in `TEMPLATES` order, so the
  request order changes nothing in the reply). Every default and `accepted_proposal` is in it.
- Storing: `runtime.is_complete`. The record and the proposal carry `completeness` `"EXACT"`. The
  XI reply's budget carries `"EXACT"` for `OPTIMAL` and `INFEASIBLE`, `"TIME_LIMIT"` for `FEASIBLE`
  and `UNKNOWN`, and `"MODEL_INVALID"` for `MODEL_INVALID`; its membership carries `"EXACT"` or
  `"TIME_LIMIT"` (5.4.3) and exists only for `OPTIMAL`. So a solve the clock cut, a refused model
  and a tie analysis the clock cut are never stored.
- `/api/opponent/proposal`, and `/xi` when it declares rules, read the record of the decision
  point's opponent: the opponent is the side of `SCENARIOS[s]["match_id"]` in Spain's `matches`
  table that is not 675, read inside `compute`; `D` is the scenario's cutoff. `/xi` with no rule
  reads no record and does not consult the gate.
- `/api/opponent/teams` returns, beside the clubs, `decision_points`: one entry per scenario of
  `SCENARIOS`, in its order, `{scenario_id, label, cutoff, competition, team_id, team_name,
  record_request}`, with the opponent resolved as above and `record_request` the full
  `RecordRequest` body for it (`decision_date` the cutoff, `panel_opt_in` false), so the page sends
  the body of the entry chosen and joins nothing.

### 5.4 Envelopes

Every POST reply has these keys, `null` where a key does not apply: `tool`, `claim`,
`non_claim`, `statements` (ordered list), `declared`, `ledger`, `evidence`
(`shell.evidence_payload` of the whole reply), `budget` (`budget.report(completeness)`),
`not_measured` (`shell.not_measured_payload(OPPONENT_NOT_MEASURED_EXTRA)`), `cannot_say` (the
three `CANNOT_SAY_*`), `provenance` (`{"providers": ["pappalardo"], "record_version",
"team_match_version", "descriptor_schema", "descriptor_fingerprints" {descriptor: fingerprint}
(the six descriptors), "sidecar": sidecar.provenance(league), "public_files": the token listing,
"registry" {subject: badge}, "panel_worlds" {namespace, matches, worlds, seed} when a panel is
shown, "proposal_policy_version", "reference_fingerprint", "snapshot":
kernel.scrub_lineage(snap.provenance), "solver_warnings": result warnings}` as applies). No key is
`total`, `index`, `score`, `rank` or holds a part of `thesis.BANNED_KEY_PARTS`; `finalize`
refuses otherwise.

#### 5.4.1 `GET /api/opponent/menu` (corpus-free, through `finalize`)

`leagues` `[{competition, label}]` in `LEAGUE_LABELS` order; `date_range` `{first, last}` and
`date_range_text` (`DATE_RANGE` formatted); `window` `{key, phrase}`; `groups` `[{group_id,
heading, non_claim, subjects: [{subject_id, kind, label, definition, part_phrases, verdict}]}]` in
`SUBJECT_GROUPS` order, `heading` from `GROUP_HEADINGS`, each `verdict` the registry payload;
`record_available` (1.7) and `record_withheld_text` (`null` when available); `decision_points`
`[{scenario_id, label, cutoff}]` in `SCENARIOS` order (for the proposal panel; the record path uses
the teams GET's resolved list); `templates` `[{template_id, label, subject_id, part, kind,
requirement_ids, needs_experimental_opt_in, threshold_hint_text}]` in `TEMPLATES` order, the hint
`THRESHOLD_HINT_SHARE` or `THRESHOLD_HINT_RATE`; `percentile_menu` `[{value, text}]` (`text` by
`PERCENTILE_TEXT`); `modes` `[{mode, label}]` with the labels of `xi_extensions._RULE_TEXTS`;
`formations`; `opt_in_label` (`xi_extensions.OPT_IN_LABEL`); `panel_opt_in_label`;
`proposal_claim`, `proposal_non_claim`; `cannot_say`; `s5_ratio_note`; `not_measured`;
`provenance.providers`.

#### 5.4.2 `POST /api/opponent/record`

`tool` `"opponent.record"`; `record_state` `"SHOWN"` | `"WITHHELD"`; `team` `{competition,
competition_label, team_id, team_name}`; `decision_date`; `window` `{key, phrase}`; `scope_text`
(`RECORD_SCOPE`); `prior_rule_text` (`DATE_RULE` formatted); `matches` `{valid_count,
left_out_count, rows: [{date, opponent_name, venue_text, goals_text, minutes_text, valid,
reason_text}]}`; `groups` as the menu's, each subject adding `state` (`"SHOWN"` or
`"WITHHELD"`), `withheld_text` (`SUBJECT_WITHHELD_E09` or `null`), `parts` `[{part, phrase, count,
count_text, share_text}]` (composition) or `count`, `count_text`, `minutes_text`, `rate_text` and
`counts_fingerprint` (level), `events_text`, `sample_text`, `no_event_text` (`NO_EVENT` for a
composition subject with window time and no event, else `null`; never for the level, whose rate is
then 0), `evidence`, `verdict`, `ratio_note` (S5's `S5_RATIO_NOTE`, else `null`), `panel_state`
(`"SHOWN"`, `"OFFERED"` (offered, no opt-in), `"NOT_ESTABLISHED"` or `"BEFORE_DATE"`), `panel_text`
(the matching sentence; `null` for `"SHOWN"`), `panel` (`null` or `{parts: [{part, phrase,
point_text, interval_text}] | point_text, interval_text, shrink_weight_text, holes_text, worlds,
world_seed, statements}`); `panel_opt_in_label`; `claim` `RECORD_CLAIM` or, withheld,
`record_withheld_text`; `non_claim` `RECORD_NON_CLAIM`. When the record is withheld, every count,
share, text built from a count, the matches block, `panel_state`, `panel_text`, `panel` and the
ledger's computed rows are `null` or absent; a withheld subject of a shown record has the same
`null`s.

#### 5.4.3 `POST /api/opponent/proposal` and `POST /api/opponent/xi`

Both: `tool`; `decision_point` `{scenario_id, label, cutoff, opponent_team_id, opponent_name}`;
`record_state` (`null` for an XI request with no rule); `proposal` (`null` for an XI request with
no rule) `{proposal_state ("FORMED" | "NOTHING_SET" | "WITHHELD"), fingerprint (null when
WITHHELD), rules: [{template_id, label, entered_threshold_text, percentile_text, state,
state_text, cited_subject_id, cited_label, cited_value_text}], minimum_rows: [{requirement_id,
label, minimum, minimum_text, source_text, set_by: [template labels], qualifiers: [{subject_id,
label, badge, sentence}]}], minimums: {requirement_id: float}, evidence, accepted, accepted_text,
xi_lab_minima_text}`; `claim` `PROPOSAL_CLAIM`; `non_claim` `PROPOSAL_NON_CLAIM`.
`entered_threshold_text` is the threshold by `format_plain`; `percentile_text` is
`PERCENTILE_TEXT`. `cited_value_text` is the record's share or rate the rule compared
(`share_text` or `rate_text`), `null` when `UNDECIDED`. `minimum_text` is
`planning._minimum_text({"source": "LEAGUE_PERCENTILE", "minimum": value})` (`"≈ "` and four
decimals, a figure read off the record); `source_text` is `REFERENCE_SOURCE` built from
`declared_minimum(...).label` and the distribution's unit counts. `accepted_text` is
`PROPOSAL_NOT_ACCEPTED` without `accepted_proposal`, and with it `PROPOSAL_ACCEPTED` when the
state is `FORMED` and `PROPOSAL_ACCEPTED_NOTHING_SET` when it is `NOTHING_SET`.

`/api/opponent/xi` adds: `scenario`; `formation`, `slots`; `mode` and `mode_text` (`_RULE_TEXTS`);
`minimum_in_force_rows` `[{requirement_id, label, minimum_text, origin_text}]` for every
requirement in force (origin `ORIGIN_DEFAULT`, `ORIGIN_ENTERED` or `ORIGIN_PROPOSAL`; entered
minima printed by `format_plain`, defaults and proposed ones by `_minimum_text`); `model_note`
(`XI_MODEL_NOTE` without the opt-in, else `null`); `omitted_candidates` `[{player_id, name,
position, minutes_text, reason}]` from `snap.omitted` (historical.py:166-177), minutes written by
the server; `xi` `{status, status_text, objective_texts, lineup_rows, requirement_rows: [{label,
minimum_text, sum_text, shortfall_text}], membership, ties_text}`; `claim` `XI_CLAIM`, `non_claim`
`XI_NON_CLAIM`, the proposal's two sentences in `statements` when a proposal exists.

The solve: `problem = xi_extensions.declare(snap, request_with_minima_in_force, mode=mode)`, then
`solve_xi(problem.candidates, problem.requirements, formation=request.formation,
locked=problem.locks, excluded=problem.excludes, mode=mode, seed=historical.SEED,
worlds=snap.worlds, provenance=snap.provenance)`, exactly the call `decision_lab.solve` makes
(decision_lab.py:343-356), its default 15-second time limit and tie analysis included; the
baseline comparison `decision_lab.solve` adds (`what_changed`) is not made (no displaced player,
ROOT 2.6 D3). `status_text`: `OPTIMAL` `XI_STATUS_OPTIMAL`; `INFEASIBLE` under `SATISFY`
`XI_STATUS_INFEASIBLE`; `INFEASIBLE` under `BALANCE` (no XI can be fielded under the locks,
exclusions and eligibility) `XI_STATUS_UNFIELDABLE`; `FEASIBLE` and `UNKNOWN` `XI_NOT_CERTIFIED`;
`MODEL_INVALID` `XI_STATUS_REFUSED`. `lineup_rows` by `xi_extensions._lineup_rows`, in formation
order; `sum_text` the lineup's exact sum (`xi_extensions._exact_sum`) rounded down at four decimals
(`planning._outward(..., up=False)`); `shortfall_text` the solver's `normalized_deficit` at five
decimals rounded half-even, labelled "in club medians"; `objective_texts` the two components of
`objective_vector` the same way, served only for `OPTIMAL`.

`membership` is `null` unless the status is `OPTIMAL` (the solver analyses ties only then,
solver.py:402-426). For `OPTIMAL` it is `{groups: [{heading, rows: [{player_id, name}]}],
completeness}`: every candidate under the heading of its `(possible, necessary)` pair from
`result.equivalent_players[pid]`, with the five headings of `xi_extensions.MEMBERSHIP_HEADINGS`
(xi_extensions.py:406-416, every pair the solver emits, `(None, False)` included) in their order,
empty groups left out, rows in `player_id` order, exactly as `xi_extensions._membership_groups`
groups risk rows (a pair outside the five is a `RuntimeError`); `completeness` `"EXACT"` when
`provenance["tie_analysis_complete"]` and `"TIME_LIMIT"` otherwise. `ties_text` is `XI_TIES` only
when the status is `OPTIMAL` and some candidate is `(True, False)`, else `null`. No
`selection_frequencies`, no CORE/FAVORED/CONTESTED/FRINGE (H10): the solve has no worlds. Solver
warnings stay in provenance (several fail the copy guard, OR-XI 7.7).

### 5.5 The ledger (O12) and evidence (O13)

Declared rows (`shell.declared_row`), a function of the resolved request. Keys are prefixed by
route family so a page can carry them without a collision: `record-team` ("Team", "{team}
({league})"), `record-date` ("Decision date", "{D}. Matches on calendar dates before it are
used."), `record-panel-opt-in` ("E-10 estimate", "Shown where E-10 established it; you opted
in.", only when true); `match-decision-point`, `match-formation` and `match-mode` (always, as XI
Lab's tools always declare the decision point and the template), `match-opt-in` (when true),
`match-lock-{id}`, `match-exclusion-{id}`, `match-minimum-{requirement_id}` (entered,
`format_plain`), `match-rule-{template_id}` ("Rule", "{template label}: at least {threshold by
format_plain}; minimum at the {PERCENTILE_TEXT}."), `match-accept` (only with rules: "Proposal",
"Accepted by you: the proposal shown." or "Not accepted."). No other default is a declared row,
and the window, which nobody declares, is never one.

Computed rows (`shell.ledger_row` with a `stage`, as `planning.ledger_row` adds one; stages here
`OPPONENT`, `PROPOSAL`, `XI`). `value_text` is `None` wherever no number exists, never 0.

| Route | `row_id` | `quantity` | `value_text` | `sample` | `evidence` | `verdict` | `solver` |
|---|---|---|---|---|---|---|---|
| record | `record-matches` | "Valid prior matches of {team}" | "{n} valid; {m} left out" | `prior_rule_text` | OBSERVED | `None` | `TEAM_MATCH_VERSION` |
| record | `record-window-time` | "Window time" | `minutes_text` + " minutes"; `None` with no valid prior match | `WINDOW_TIME_SAMPLE` with the window phrase | DERIVED | `None` | `TEAM_MATCH_VERSION` |
| record | `record-{subject}` | the subject's label | parts as `"{phrase}: {count_text} ({share_text})"` joined by "; ", or the level's `rate_text`; `None` with no valid prior match, with no event for a composition, or when the subject is withheld | `sample_text`, or `SUBJECT_WITHHELD_E09` | DERIVED (counts OBSERVED composed) | the subject's verdict payload | `"descriptor {fingerprint}"`; for the level `"descriptor {primary fingerprint}, parts added, per 90 minutes of window time"` |
| record | `panel-{subject}` (shown only) | "E-10 estimate: {label}" | the interval texts, and the point when shown | `PANEL_HEAD_*` | EXPERIMENTAL | the subject's verdict payload | `"estimator · {worlds} worlds · seed {seed} · draw {namespace}"` from `SERVED_PANEL` and the one `WorldWeights` |
| proposal, xi | `proposal-rule-{template_id}` | the template label | `state_text` and `cited_value_text` | `RULE_*` sentence | the cited record's class | the cited record's payload | `PROPOSAL_POLICY_VERSION` |
| proposal, xi | `proposal-minimum-{requirement_id}` | "{label} minimum, proposed" | `minimum_text` | `source_text` and the qualifiers, in order | HEURISTIC composed with the requirement's and the cited records' classes | `shell.verdict_payload("none", "proposal-{requirement_id}")` (a policy number no protocol tests, the planning precedent for minima) | `PROPOSAL_POLICY_VERSION` |
| xi | `xi-solve` | "Least declared shortfall" | `objective_texts` joined, `None` unless `OPTIMAL` | `XI_CLAIM` | as OR-XI 7.6 composes the requirements in force | `None` (exact computation) | `"{status} · 1/100000"` |
| xi | `xi-minimum-{requirement_id}` | "{label} minimum in force" | `minimum_text` | `origin_text` | the requirement's class (HEURISTIC or EXPERIMENTAL) | `None` | `None` |

Withheld record: no computed row; the kit prints "No computed quantity was sent.".

### 5.6 Copy

Every sentence below is a module constant of `api/opponent_lab.py` (or of the model module that
returns it), served outside provenance, and passes `labels.scan_labels` under every format
argument a test supplies; `tests/test_opponent_api.py` scans each one, and every reply passes
`finalize`. A template's `{...}` fields are filled only by the server, and a sentence is served
only formatted. The sentences of E-10's config (`registry_non_claims`, the qualifiers,
`s5_ratio_name`) are served verbatim from `panel.py`'s constants, and a test asserts they pass the
guard (they do on the draft: checked when this file was first written). The examples below are
filled with invented values.

| Constant | Text |
|---|---|
| `RECORD_CLAIM` | Counts of recorded events in the league matches of {team} dated before {date}, in the window {window phrase}, for each E-10 definition: what opponents did against the team, and where the team's own defensive actions were recorded. Each share is a count divided by the sum of the counts listed beside it. |
| `RECORD_NON_CLAIM` | A record of past matches. It is never itself a tendency: where E-10 established a descriptor, the quantity it tested is the estimate shown behind the opt-in, not these counts. It does not say how well the team defends, and no single number here summarises an opponent. |
| `RECORD_WITHHELD_NOT_REGISTERED` | The record is withheld until E-10 is registered and has run. Computing these counts on the corpus before then would show the quantities E-10 tests before its code has been reviewed and run once. The definitions and their badges are shown. |
| `RECORD_WITHHELD_NOT_RUN` | The record is withheld until E-10 has run. E-10 is registered, and its code is reviewed and run once on the corpus before any of these counts is computed for a page. The definitions and their badges are shown. |
| `SUBJECT_WITHHELD_E09` | This record is withheld until E-09, a protocol that tests nearby player quantities, is registered. Its definition and badge are shown. |
| `RECORD_SCOPE` | LAB · historical · {league label} 2017/18, matches before {date} · counts of recorded events · not modelled: why a side conceded where it did, finishing, defending, goalkeeping, physical profile |
| `GROUP_HEADINGS` | `conceded`: What was done against the team · `own_actions`: Where the team's own defensive actions were recorded · `level`: How many final-third entry passes it conceded |
| `CANNOT_SAY_FUNNEL` | A team can leave a channel open on purpose or fail to close it. Event data cannot tell the two apart, so no share here says where the team defends badly or where to attack. |
| `CANNOT_SAY_OPPONENTS` | A record mixes what this team allowed with what the teams it met tried to do. The record is not adjusted for the opponents met or for team strength. Where the E-10 estimate is shown, it is measured against what the opponents met produced in their other matches, and is still not adjusted for strength. |
| `CANNOT_SAY_ORDER` | Parts are listed in a fixed order. No part is picked out, sorted by size or named the largest, and teams are never listed in order of a share or a rate. |
| `DATE_RULE` / `prior_rule_text` | Matches on calendar dates before {date} are used; matches on that day are not. |
| `LEVEL_DEFINITION_TEMPLATE` | {level label}: every event of the definition below, all parts added, divided by window time in units of {unit_seconds} seconds. {primary describe()} |
| `WINDOW_TIME_SAMPLE` | Time in the window ({window phrase}), from event times; each half ends at its last recorded event. |
| `VENUE_HOME` / `VENUE_AWAY` | home / away |
| `INVALID_PERIOD_MISSING` / `_CLOCK` / `_GOALS` / `_DISMISSALS` | No event in one of the two halves. The match is left out of every record. / An event time is not a valid clock reading. The match is left out of every record. / The goals in the event record differ from the match sheet. The match is left out of every record. / The dismissals in the event record differ from the match sheet. The match is left out of every record. |
| `NO_PRIOR_MATCH` | No valid match of this team is dated before {date}, so no count exists yet. |
| `NO_EVENT` | No such event was recorded in the prior valid matches, so no share exists. It is not zero. |
| `SAMPLE_TEXT` | {events} events in {matches} valid matches, {minutes} minutes of window time. |
| `S5_RATIO_NOTE` | The share is a monotone transform of {ratio name}. That ratio is named here and not shown. |
| `PANEL_OPT_IN_LABEL` | Show the E-10 estimate for each record E-10 established |
| `PANEL_HEAD_COMPOSITION` | Estimate of the one E-10 estimator at {date}: the league composition of matches before that date, moved by this team's own history and drawn toward the league by the pseudo-events E-10 selected. The interval is taken over {worlds} resampled sets of the league's prior matches. |
| `PANEL_HEAD_VOLUME` | Estimate of the one E-10 estimator at {date}: the league rate of matches before that date, per 90 minutes of window time, moved by this team's own history and drawn toward the league by the pseudo-events E-10 selected. The interval is taken over {worlds} resampled sets of the league's prior matches. |
| `PANEL_POINT_WITHHELD` | No point is shown: the reliability bound E-10 recorded for this descriptor is below {bound}, so the interval alone is shown. |
| `PANEL_NOT_OFFERED` / `PANEL_BEFORE_DATE` | E-10 has not established this record, so only the record is shown. / E-10 evaluated matches from {panel date}. Before that date only the record is shown. |
| `PANEL_HOLES` / `PANEL_ALL_HOLES` | {h} of {worlds} resampled sets hold no prior event of this team and are left out of the interval. / Every resampled set holds no prior event of this team, so no interval exists. |
| `SHRINK_TEXT` | Weight of this team's own history in the estimate: {w}. |
| `PROPOSAL_CLAIM` | A requirement proposal formed by the rules you declared. Each rule compares one share or rate of the opponent record with your threshold and, where the record reaches it, sets the minimum or minima its template names at the league percentile you chose. It is your declared policy, HEURISTIC, and it changes no solve until you accept it. |
| `PROPOSAL_NON_CLAIM` | The link from a record to a requirement is your declaration, not something the data shows: the requirement and the record count different events. A record of where a team conceded is not a reason to attack there. |
| `RULE_HOLDS` / `RULE_DOES_NOT_HOLD` / `RULE_UNDECIDED` | The record reaches your threshold, so this rule sets its minimum. / The record is below your threshold, so this rule sets nothing. / The record has no event for this share or rate before the date, so this rule sets nothing. That is not evidence that the share is low. |
| `NO_RULE_HOLDS` | No declared rule sets a minimum, so the minima in force are unchanged. |
| `PROPOSAL_NOT_ACCEPTED` / `PROPOSAL_ACCEPTED` / `PROPOSAL_ACCEPTED_NOTHING_SET` | Shown and not applied: the minima in force are the ones you entered, or the defaults. / Accepted by you: the proposed minima are in force in the solve below. / Accepted by you. No declared rule set a minimum, so the minima in force are unchanged. |
| `ORIGIN_DEFAULT` / `ORIGIN_ENTERED` / `ORIGIN_PROPOSAL` | Shipped default / Entered by you / Your accepted proposal |
| `PROPOSAL_CONFLICT` | Two rules that can set one requirement declare different percentiles. Give them one percentile, or keep one of them. |
| `ENTERED_AND_PROPOSED` | A requirement you entered a minimum for is also set by a declared rule. Accept the proposal without that minimum, or drop the rule. |
| `PROPOSAL_CHANGED` | The proposal changed after it was shown: its rules, or the record or registry it reads, differ. Read it again before accepting it. |
| `PROPOSAL_WITHHELD` / `ACCEPT_WHILE_WITHHELD` | The proposal reads the record, which is withheld until E-10 has run. / There is no proposal to accept while the record is withheld. |
| `ACCEPT_WITHOUT_RULES` | There is no proposal to accept: no rule was declared. |
| `THRESHOLD_HINT_SHARE` / `THRESHOLD_HINT_RATE` | at least a share you declare, from 0 to 1 / at least a rate you declare, per 90 minutes of window time |
| `PERCENTILE_TEXT` | {p}th percentile of league starting-XI sums |
| `RULE_TWICE` / `THRESHOLD_SHARE` | A rule template is declared twice. Declare each at most once. / A share threshold is a number from 0 to 1. |
| `XI_LAB_MINIMA` | To solve the same minima on XI Lab, enter: {label} = {value}; … (each value by `format_plain`). |
| `REFERENCE_SOURCE` | {declared_minimum label} ({n} starting elevens of {t} clubs). |
| `TEMPLATE_LABEL_SHARE` | {requirement labels} {minimum or minima}, from the record “{subject label}”, part: {part phrase} |
| `TEMPLATE_LABEL_RATE` | {requirement label} minimum, from the record “{subject label}” |
| `XI_CLAIM` | The least declared shortfall over the XIs that the eligibility rules, the minutes gate, missing measurements, locks and exclusions allow, solved by XI Lab's solver at this decision point with the requirements and minima in force listed below. Where it certifies an XI, one XI that reaches it is shown. |
| `XI_NON_CLAIM` | Arithmetic on prior per-90 rates under the minima in force. It is not a forecast and says nothing about the result of the match. |
| `XI_TIES` | Other XIs can reach the same shortfall; which one is shown is the solver's choice. |
| `XI_STATUS_OPTIMAL` / `XI_STATUS_INFEASIBLE` / `XI_STATUS_UNFIELDABLE` / `XI_NOT_CERTIFIED` / `XI_STATUS_REFUSED` | Certified in the integer model: no XI reaches a smaller declared shortfall. / No XI meets every minimum under the Satisfy rule, in the integer model. Nothing was relaxed. / No XI can be fielded under these locks, exclusions and eligibility rules, in the integer model. Nothing was relaxed. / The solver did not certify this XI within its time limit. Treat it as incomplete. / The solver refused the model, so no XI is reported. |
| `XI_MODEL_NOTE` | Without the experimental opt-in this solve holds {labels} only. XI Lab's own solve also holds the two side pass-origin requirements, so the two answers can differ for that reason alone. |
| `UNKNOWN_TEAM` / `UNKNOWN_DECISION_POINT` | This team has no league match in the corpus for that league. / unknown decision point |
| `DATE_FORMAT` / `DATE_RANGE` | A decision date is written YYYY-MM-DD. / A decision date lies from {first} to {last}. |
| `SIDECAR_UNAVAILABLE` | The tag sidecar of this league is absent or is not the one its manifest records, so no record can be built. It is built by scripts/build_sidecar.py for this league. |

The membership headings are `xi_extensions.MEMBERSHIP_HEADINGS`, reused (R13), and the mode
labels `xi_extensions._RULE_TEXTS`; this module holds no copy of either.

`OPPONENT_NOT_MEASURED_EXTRA` (appended after the shell's nine, `shell.not_measured_payload`):
`set_pieces` "Set-piece concession" UNMEASURED "No set-piece phase is segmented. Shots taken
directly from a set piece are left out of the shot record."; `transitions` "Transition exposure"
UNMEASURED "No possession segmentation exists, so no record starts at a change of possession.";
`regain` "Where the ball is won back" UNMEASURED "It needs a possession rule that does not exist
here."; `entry_value` "Value of conceded entries" UNMEASURED "Entries are counted, not weighted
by a pass-value surface."; `coach` "Coach changes" UNMEASURED "A record runs across every coach of
the season; no adjustment is made."; `off_ball` "Off-ball movement and pressing" UNAVAILABLE
"Not recorded by this provider's events." (E-10's `not_run_in_this_experiment`, config.json, and
ROOT 2.5 O6). Planning's `NOT_MEASURED_EXTRA` is not used on this page: its "shots" item says no
shot construct is shown, and S3 is one (planning.py:1437-1458).

### 5.7 Failures

404 unknown team or decision point; 422 a refusal of 5.2 with its sentence (no input value);
429 busy (build gate, sixteen places); 503 `SIDECAR_UNAVAILABLE` for a sidecar absent
(`SidecarMissing`), stale, mismatched or a corpus defect (`RecordCorpusDefect`), and the corpus
sentence for a public file absent or damaged (`FileNotFoundError`, Arrow); 500 for a
`BoundaryViolation` or an internal fault (`KeyError`, the non-integer count check, a `ValueError`
of an estimator call re-raised as `RuntimeError`, `RecordWithheld`, which no route reaches). A 200 is
never served for a record built from a sidecar `verify` refused.

### 5.8 What does not change (R13)

Every shipped API route answers byte for byte as before; `decision_lab.snapshot` is neither called
nor cleared; `runtime.router` still serves only `/api/evidence/verdicts`
(`tests/test_lab_runtime.py:783-798`); runtime, squad and transfer still serve exactly 14 API
paths (`tests/test_planning_api.py:1630-1650`); `runtime.BUDGETS` and `LONG_ROUTES` are unchanged.
The HTML of the five shipped pages changes in its nav block only, by the root's edit under the
R13 override ROOT 2.12 N5 rules (R-4), named in ADR-0032 (section 11), as W8 names its overrides.

## 6. API: `galactico/api/desk.py`

### 6.1 What the desk is

One page, one POST, one reply through `finalize`: the chain of ROOT 2, each step the reply of
the page that computes it, composed on the server so `finalize` sees the whole reply, with the
declared inputs apart (O12) and one evidence ledger. The desk computes no number of its own: its
only computations are which parts run, the order of rows, the removal of rows that restate a
common row, the composed evidence class, and the decimal text of an integer a part served
(`str()`, 6.4).

| Stage id | Heading (`DESK_STAGE_HEADINGS`) | Part id | Composed from | Runs when |
|---|---|---|---|---|
| `identity` | Declared identity | `snapshot` | `squad_lab.squad_snapshot(SquadSnapshotRequest)` | always |
| `requirements` | Explicit requirements | `reference` | `squad_lab.squad_reference(SquadReferenceRequest)` | always |
| `audit` | Squad audit | `depth` | `squad_lab.squad_depth(SquadDepthRequest)` | always |
| | | `stress` | `squad_lab.squad_stress(SquadStressRequest(k=stress_k))` | `stress_k` is 1 or 2 (default 1) |
| `brief` | Role brief | `brief` | `squad_lab.squad_brief(SquadBriefRequest(slot_id, include_leagues))` | a slot is declared |
| `search` | Candidate search | `search` | `transfer_lab.transfer_injection(TransferInjectionRequest(slot_id, include_leagues, filters))` | a slot is declared |
| `opponent` | Opponent record and requirement proposal | none: a link to Opponent Lab with `DESK_OPPONENT_STAGE` | | always shown |
| `xi` | XI solve | `match-xi` | `opponent_lab.opponent_xi(OpponentXIRequest(scenario_id, formation, experimental_opt_in, mode))`, no rules, so no record is read | `match` is declared, and the planning point is the flagship |
| `xi-additions` | XI exact additions | `match-ceilings` | `xi_extensions.ceilings_route(CeilingsRequest(scenario_id, formation, experimental_opt_in))` | `match` declared |
| | | `match-conflict` | `xi_extensions.conflict_route(ConflictRequest)` (`explains: "solve"`, the match mode) | `match` declared, mode `SATISFY`, the solve `INFEASIBLE`, and the opt-in (otherwise `DESK_CONFLICT_NEEDS_OPT_IN`) |

The stage list is the fixed constant `DESK_STAGES` (id, heading, part ids), served by the menu
and by every reply; the evidence ledger and the not-measured panel are parts of the reply, not
stages. Every other planning choice (presets, requirement declarations, exclusions, locks, the
opt-in, the formation) is the request's `PlanningInputs`, passed unchanged to every planning part,
so the parts answer one declared problem. A part that does not run is listed with `state`
`"NOT_RUN"` and its sentence (`DESK_NO_SLOT`, `DESK_NO_MATCH`, `DESK_CONFLICT_NEEDS_OPT_IN`,
`DESK_MATCH_OTHER_CLUB`); one the clock stopped is `"NOT_STARTED"`; one whose corpus files are
absent is `"UNAVAILABLE"` (6.3.4). No part is dropped silently. The frontier and the risk modes are
not composed by the desk in this release; they are XI Lab's (KNOWN_LIMITATIONS, section 11).

The per-match chain exists for XI Lab's two decision points, both Real Madrid matches
(decision_lab.py:44-57). It is offered only when the planning point is the flagship
(`madrid-planning-2018-05-21`, ROOT 2.6 Q3); for any other club `match` is a 422
(`DESK_MATCH_OTHER_CLUB`). Any club of the five leagues is a planning point under its own id
(planning.py:276-278); outside Madrid the eligibility rule is `provider-position-broad-v1`,
unreviewed, and the desk prints the eligibility banner every planning reply carries
(`eligibility.banner`, O14).

### 6.2 Route and request

| Method | Path | Budget | Long | Request |
|---|---|---|---|---|
| GET | `/desk` | | | page |
| GET | `/api/desk/menu` | | | corpus-free: `planning.catalogue()` (identity phrases, presets, requirements, minimum sources, percentile menu, leagues, formations, research statement, not measured), the slots of each formation with `recruitable` as Transfer Lab's scenarios GET serves them, `stress_sizes` `[{value, text}]`, the decision points and modes of `/api/opponent/menu`, `DESK_STAGES` with headings, every desk sentence, `provenance.providers` |
| POST | `/api/desk/chain` | `desk.chain`: 180 (local `DESK_BUDGET_SECONDS`) | no | `DeskRequest` |

```python
class DeskMatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenario_id: str = "madrid-2018-05-06"           # a key of decision_lab.SCENARIOS
    mode: Literal["BALANCE", "SATISFY"] = "BALANCE"

class DeskRequest(planning.PlanningInputs):
    slot_id: transfer_lab.SlotId | None = None       # the slot being recruited: brief and search
    include_leagues: list[planning.League] = Field(default_factory=list, max_length=4)
    filters: transfer_lab.TransferFilters = Field(default_factory=transfer_lab.TransferFilters)
    stress_k: Annotated[Literal[1, 2], planning.INTEGER_ONLY] | None = 1
    match: DeskMatch | None = None
```

The formation and the experimental opt-in of `PlanningInputs` are the per-match chain's too. The
per-match chain declares no rule, acceptance, minimum, lock or exclusion: those are declared on
Opponent Lab and XI Lab (6.4, DISSENT 5). A goalkeeper slot is refused before any part runs, with
Transfer Lab's `GOALKEEPER_REASON`. `k = 3` is not offered (it needs Squad Lab's confirmation,
which the desk does not ask). Every field of `DeskRequest` is reached by the API tests (8.1); the
page offers the subset of 7.3, and requirement declarations, exclusions, locks and long-list
filters are declared on Squad and Transfer Lab (KNOWN_LIMITATIONS, section 11).

### 6.3 Composition rules

1. **In process, by the handler.** Each part is the shipped handler function called with its
   request model; the `Response` it returns is read back with `json.loads(response.body)`. So a
   part is the reply its own page receives for the same declarations (equal after removing
   `budget.elapsed_seconds`, or byte for byte on a cache hit), with that route's cache, budget,
   build gate, long-job place and `finalize` (ADR-0024). No HTTP request is made and no build
   function is reached past its handler.
2. **Order.** The order of `DESK_STAGES`, sequentially; never in parallel.
3. **Budget.** The desk starts its own `runtime.Budget(DESK_BUDGET_SECONDS)` at entry. Before a
   part it compares the remaining seconds with that part's own budget ceiling (the route's entry
   in `runtime.BUDGETS`, `squad_lab.RECORD_BUDGETS`, `transfer_lab.UNIVERSE_BUDGET_SECONDS` or
   `opponent_lab.OPPONENT_BUDGETS`); when fewer remain, the part and every later part are
   `NOT_STARTED` (`DESK_NOT_STARTED`) and the reply's completeness is `"DEADLINE"`. A part's own
   budget still bounds it, and no build is interrupted, so a desk request can last its budget
   plus one build for each part that starts cold.
4. **Places and failures.** The desk route is not a long route and never takes a long-computation
   place: the stress and search handlers take theirs inside their own computation, and a desk
   that held one of the two while calling them could wait on itself. A desk request holds its own
   admission place and, while a part computes, that part's (`runtime.admission`, two of sixteen at
   most). A 429 from a part is the desk's 429 (`Retry-After` as served). A 503 from `snapshot` is
   the desk's 503 (nothing can be composed without the declared problem); a 503 from any later
   part makes that part `"UNAVAILABLE"`, its `state_text` the part's own detail sentence, the
   chain `"PARTIAL"` and the reply unstored, and the desk goes on. A 422 from a part is the desk's
   422 with the part's sentence (the declarations are the desk's). The desk catches nothing else.
5. **Consistency.** The planning parts answer one declared problem, so their common rows must be
   equal JSON across parts: the declared rows `planning.declared_rows(problem)` returns (keys
   `declared-scenario`, `declared-template`, `declared-preset-*`, `declared-exclusion-*`,
   `declared-lock-*`, `declared-experimental-opt-in`, `declared-minimum-*`, planning.py:1249-1295)
   and the rows of `planning.base_ledger` (`eligibility-rules`, `gate-minutes`, `rates-*`,
   `minimum-*`). If the corpus files change between two parts they can differ: the desk then
   serves the reply with `chain_state` `"INCONSISTENT"`, completeness `"INCONSISTENT"` (not a
   stored token) and `DESK_INCONSISTENT`. Nothing else is compared: a part's own declared rows
   (the brief's `declared-slot` "Slot the brief is for" and `declared-leagues` "Leagues counted",
   squad_lab.py:1567-1571; the search's `declared-slot` "Slot being recruited",
   `declared-leagues` "Leagues searched" and `declared-filters`, transfer_lab.py:634-649) differ by
   design and are each carried under the part's own prefix (6.4).

### 6.4 The envelope and the one ledger

`tool` `"desk.chain"`; `scenario_id`, `scenario`, `eligibility` (from the snapshot part);
`scope_text` (`planning.SCOPE_TEMPLATE` filled with the scenario, as Squad Lab prints it);
`chain_state` (`"COMPOSED"`, `"PARTIAL"`, `"INCONSISTENT"`); `stages` `[{stage, heading,
statement, parts: [{part_id, route, page_href, page_name, state, state_text, claim, non_claim,
warnings, statements, budget, summary_rows: [{label, value_text}]}]}]` in `DESK_STAGES` order
(`statement` is `DESK_OPPONENT_STAGE` for `opponent`, whose `parts` is empty, and `null`
otherwise); `declared` `[{family, heading, rows}]` and `ledger` (below); `evidence`
(`shell.evidence_payload` over the union of the parts' evidence inputs, de-duplicated by label and
class); `not_measured` (`planning.not_measured()`, the shell's nine of ROOT 2.3 then the six
planning items) and `not_measured_closing`; `research_statement` and `verdicts`
(`planning.verdict_reading()`, the same reading every planning reply carries); `claim`
(`DESK_CLAIM_TEMPLATE` filled with the team, the cutoff and the page names of the parts that ran,
distinct, in stage order); `non_claim` `DESK_NON_CLAIM`; `statements` (`DESK_MATCH_SCOPE` when
`match` is declared, `DESK_NO_DESCRIPTOR` always, `DESK_LINK_NOTE` always); `budget`; `provenance`
`{"providers": ["pappalardo"], "desk_version", "parts": {part_id: that part's provenance}}`.

A part's `summary_rows` are copied from fields its reply serves, never written by the desk; the
one formatting the desk applies is the decimal text of a served integer (`str()`), so the page
prints only strings. snapshot: "Players in the evidence set" from the `gate-minutes` row; depth and
stress: their `claim`; brief: its `claim`, then its `pool.corpus_exit_statement` and
`pool.cross_league_flag` when it serves a `pool` (squad_lab.py:1513-1530); search: the reply's
`deficiency.statement`, its `search_statement` when not `null` (transfer_lab.py:548-586), one row
per outcome group (`outcome_label`, `count`) of the `listings.keys` entry whose `order_key` is
`"name"`, in served order (planning.py:1806-1820, a list), then `screened_count`, then
`selection_statement` when not `null`, then `pool.corpus_exit_statement` (the universe's
visibility statement, ROOT 2.6 Q8) and `pool.cross_league_flag` when not `null` (ROOT 2.3: "not
strength-adjusted"), with no candidate name (the list is on Transfer Lab, and the outcome groups
are counts, R1, H8/H35); match-xi: `xi.status_text`, `objective_texts`, the lineup rows (the one XI
shown, in formation order), `minimum_in_force_rows`; ceilings, conflict: their `claim` and
`statements`.

**Declared.** Two families, served grouped: planning ("Planning declarations") and match
("Per-match declarations"). Planning: the common rows of 6.3.5 once (from `snapshot`), then each
planning part's own rows, in part order, with key `{part_id}-{key}` and `part` set, so the brief's
and the search's slot and league rows both appear. Match: the rows of `match-xi` as served (keys
`match-*`, unique by 5.5); then each XI addition's rows, where a row whose key the explicit map
`MATCH_COMMON_KEYS` (`declared-scenario` to `match-decision-point`, `declared-template` to
`match-formation`, `declared-experimental-opt-in` to `match-opt-in`) names is dropped once the desk
has checked that the mapped `match-xi` row exists (a missing one is a `RuntimeError`), and every
other row (conflict's `declared-arithmetic` and `declared-decision-rule`,
xi_extensions.py:1377-1381) is carried with key `{part_id}-{key}`. The desk builds every
per-match sub-request from the same three fields (scenario, formation, opt-in) and none of them
holds a lock, exclusion or minimum (`DeskMatch` declares none), so a dropped row restates a
`match-xi` row by construction; `test_ledger_composition` asserts it on the sub-requests, not on
row text. Each row keeps its `stage` and gains `part`.

**Computed.** The planning base rows once (from `snapshot`), then each part's other rows in part
order. Each carried row keeps every field its reply served (quantity, value_text, sample,
evidence, verdict, solver, stage) and gains `part`, `page_name` and `page_href`; its `row_id` is
prefixed `"{part_id}-"` (hyphens, so the kit's plain-word rule holds, labs-shared.js:55). Rows of
the XI additions take stage `XI`.

**No E-10 descriptor and no proposal.** The desk reads no opponent record and forms no
requirement proposal, in any state: `DeskMatch` has no rules and no acceptance, and its `match-xi`
part is `/api/opponent/xi` with no rule, which reads no record (5.3). The desk therefore serves no
E-10 descriptor value, share, count, rate or estimate, and nothing from which one could be
recovered: a threshold a rule reached, or a minimum a proposal set, would bound a record's share,
and repeated requests would narrow it (review E6), so neither is on the desk. The record and the
proposal are the `opponent` stage, which links to Opponent Lab (`DESK_OPPONENT_STAGE`), where a
proposal is read beside the record it reads and accepted by the reader who saw it (ROOT 2.3,
4.5). This is stricter than PIPELINE 13's "while it serves this sentence", so that no later
results commit can make a desk reply false (DISSENT 5, N3). `test_desk_shows_no_e10_descriptor` (8.1)
spies `record.load_league_tables`, `record.build_record` and `proposal.evaluate` and asserts that
no desk request calls them, and that no desk reply holds a `proposal`, `rules`,
`cited_value_text` or `minimum_rows` key or a non-null `record_state`.

### 6.5 Copy

As 5.6, every constant scanned and served outside provenance.

| Constant | Text |
|---|---|
| `DESK_CLAIM_TEMPLATE` | The planning chain for {team} before {cutoff}, composed from the replies of {page names} to the declarations above. Every computed row is in one ledger, as the page named beside it served it. |
| `DESK_NON_CLAIM` | Nothing here says whom to keep, sell or sign. Every number is conditional on what you declared, and what is listed as not measured is outside every number. |
| `DESK_MATCH_SCOPE` | The per-match chain runs at Real Madrid's two historical decision points. It is a past decision, not a plan for next season. |
| `DESK_MATCH_OTHER_CLUB` | The per-match chain exists only at Real Madrid's two historical decision points. |
| `DESK_NO_SLOT` | Declare the slot being recruited to see the role brief and the search. |
| `DESK_NO_MATCH` | No per-match chain was declared. |
| `DESK_NOT_STARTED` | Not started: too little of this request's time was left for it. Ask again; parts whose replies were complete are kept by the server. |
| `DESK_NO_DESCRIPTOR` | No E-10 descriptor is shown here, and no requirement proposal is formed here. The opponent record is read, and a proposal formed and accepted, on Opponent Lab. |
| `DESK_OPPONENT_STAGE` | The opponent record and any requirement proposal are on Opponent Lab, beside the record each proposal reads. The XI solve below holds the minima in force without a proposal. |
| `DESK_INCONSISTENT` | The corpus files changed while this chain was composed, so its parts disagree. Ask again. |
| `DESK_CONFLICT_NEEDS_OPT_IN` | A minimal conflicting set for this solve needs the experimental opt-in. Without it, XI Lab's conflict panel explains its own solve. |
| `DESK_LINK_NOTE` | Each part opens on its own page with that page's defaults. Declarations made here are not carried across pages. |
| `DESK_STAGE_HEADINGS` | the headings of 6.1, one per stage id |
| `DESK_FAMILY_HEADINGS` | Planning declarations; Per-match declarations |
| `DESK_PART_COMPOSED` | Composed from the reply of {page name}. |

`DESK_LINK_NOTE` follows the shipped precedent (squad.html: "Transfer Lab opens with its own
defaults. Declarations made here are not carried across pages."): no page reads declarations
from a URL in this release.

### 6.6 Cache key and storing

`runtime.cache_key("desk.chain", body, token)`: `body` is `planning.canonical_request(scenario,
request)`; `token` is `planning._digest` of `planning._corpus_files(leagues)` (present files and
the absent list together, so an absent league is part of the identity instead of an error),
`leagues` the scenario's league, and the five when a slot is declared. Stored when
`runtime.is_complete` holds over the whole reply, so every carried part's own
`budget.completeness` must be `EXACT` or `COMPLETE`; a reply with a `NOT_STARTED`, `UNAVAILABLE`,
`DEADLINE`, `INCONSISTENT` or pool-less part is computed again next time. Each part is also kept
under its own key by its own route, so a second desk request with mostly the same declarations is
mostly cache hits.

## 7. Pages

### 7.1 Shell and nav

Both pages follow the planning page anatomy (squad.html:2-3, 64, 139-142; transfer.html:47, 74-75):
head `labs.css`, `labs-shared.css`, then the page's own sheet (`opponent.css`; `planning.css` and
`desk.css` for the desk); an inline `<style>` that opens with a comment; `<header>` with the
brand, the `lab-tag` "Historical LAB" and the nav byte-equal to `shell.nav_markup("opponent")` or
`nav_markup("desk")`; `<main>` with an eyebrow, an h1, a lede, `#scope-slot`, `#status`
(`role="status"`), `#claim-slot`, `#warnings-slot`, the panels, `#ledger-slot`,
`#not-measured-slot`; the footer with the Pappalardo/Wyscout CC BY 4.0 credit; scripts
`labs-shared.js`, then (desk) `planning.js`, then `opponent.js` or `desk.js`, then a short inline
script that calls `OpponentLab.mount(...)` or `Desk.mount(...)`. Each `*.js` declares one global
(`window.OpponentLab`, `window.Desk`) with two parts, as `xi-extensions.js` (OR-XI 8.1):
`render`, pure functions from payload to markup, every server string through `Shell.esc`, no
element touched, loadable by the node render harness without touching `document`; and
`mount(root)`, the controller, which sends requests through `Shell.api` and discards a reply
whose request version is not the latest.

Nav (a root edit, section 11): `Destination("opponent", "/opponent", "Opponent", "matchday")`
after XI, and `Destination("desk", "/desk", "Desk", "desk")` last, in a group of its own, so the
separators read evidence | matchday | planning | desk. The screen-reader suffix " Lab" becomes a
field of `Destination` (`sr_suffix`, default `" Lab"`; the desk's `" (Director’s desk)"`, written
with U+2019 and no ASCII apostrophe, because `Shell.esc` writes `'` as `&#39;`, labs-shared.js:30,
and the kit and the server must draw byte-identical navs, tests/test_shell_payloads.py:59-79), so
the five shipped links keep their bytes and the desk does not read "Desk Lab". `Shell.nav` already
takes `sr_suffix` per item.

### 7.2 `/opponent`

Eyebrow "Opponent record · prior dates only"; h1 "Where it was conceded.<br>Not why."; lede
"What a team's opponents did against it, and where its own defensive actions were recorded, in
league matches before a date you choose. Each record carries its E-10 badge."

| Panel | Shown when | Request | Renders (server field) | States |
|---|---|---|---|---|
| `#op-form` | always | `GET /api/opponent/menu` on load (corpus-free), then `GET /api/opponent/teams` | league select, team select (served order: league, club name, team id; never by a record value), `input[type=date]` with `min`/`max` from `date_range`, the window phrase as text (`window.phrase`), a decision-point select ("Or use an XI decision point") listing the teams reply's `decision_points` labels, whose choice sends that entry's own `record_request` body, and `#load-record` | teams GET 503: `Shell.errorText` (the decision-point select stays empty: its entries come from that reply); record withheld: `record_withheld_text` from the menu |
| `#scope-slot`, `#claim-slot` | after a record reply | `POST /api/opponent/record` on `#load-record` | `scope_text`, `claim`, `non_claim`, `prior_rule_text` | `WITHHELD`: `claim` (the withheld sentence) as a notice |
| `#record-groups` | after a record reply | | one section per `groups[]` in served order: `heading`, `non_claim` (always, every state), then a card per subject in served order: label, `Shell.verdictBadge(verdict)` and `verdict.statement`, `Shell.evidenceBadge(evidence)`, a parts table (`phrase`, `count_text`, `share_text`, in served order, every row the same classes and computed style), or the level's `count_text`, `minutes_text`, `rate_text`; `sample_text`; `no_event_text`; `ratio_note`; a `<details>` "Definition" holding `definition` | record `WITHHELD`, or subject `state` `WITHHELD`: label, badge, statement, definition and `withheld_text` only; a `null` share prints `—`, never 0 |
| `#panel-optin` | some subject's `panel_state` is `"OFFERED"` or `"SHOWN"` | ticking it sends the record request again with `panel_opt_in: true` | `panel_opt_in_label`; inside each card with `panel` non-null: parts `point_text` (or `PANEL_POINT_WITHHELD` from `panel.statements`), `interval_text`, `shrink_weight_text`, `holes_text`, `worlds` and `world_seed` as served integers, the EXPERIMENTAL badge | `panel_text` beside every card whose estimate is not shown; unchecked on every load |
| `#matches-slot` | record shown | | `<details>` "Matches used": rows date, `opponent_name`, `venue_text`, `goals_text`, `minutes_text`, `reason_text`, in served order | none valid: `NO_PRIOR_MATCH` |
| `.cannot-say` | always | | `Shell.cannotSay(cannot_say)` | |
| `#proposal-panel` | a decision point is chosen | `POST /api/opponent/proposal` on `#form-proposal` | one row per template (served order): an include checkbox, a threshold `input[type=number]` (empty; `min 0`, `max` 1 for a share, 1000 for the rate; `step any`), a percentile select starting on an empty placeholder (options `percentile_menu[].text`, values in the attribute), the template label, `threshold_hint_text`; the experimental opt-in checkbox (`opt_in_label`, unchecked on every load); `#form-proposal` enabled only when every included row has both values; then `proposal_claim`, `proposal_non_claim`, one row per `rules[]` (label, `entered_threshold_text`, `percentile_text`, `cited_value_text`, `state_text`), `minimum_rows` (label, `minimum_text`, `source_text`, `set_by`, each qualifier beside its record's label and badge), `xi_lab_minima_text` | `WITHHELD`: `PROPOSAL_WITHHELD`, form disabled; `NOTHING_SET`: `NO_RULE_HOLDS`; 422: the sentence |
| `#xi-panel` | a decision point is chosen | `#accept-proposal` checkbox (label "I accept this proposal as my declaration"; enabled only while a proposal reply with a `fingerprint` is shown, unchecked on every load and cleared by any new proposal reply or proposal form edit), mode select (`modes`), `#solve-xi`; `POST /api/opponent/xi` with the declarations of the proposal shown, `accepted_proposal` the shown reply's `fingerprint` when the box is ticked and absent otherwise, `minimums` `{}` | `accepted_text`, `minimum_in_force_rows`, `model_note`, `xi.status_text` printed once, as a notice (never through `Shell.infeasible` or `Shell.notCertified`, whose own trailing sentences would repeat the server's), `objective_texts`, a table of `lineup_rows`, `requirement_rows` (label, `minimum_text`, `sum_text`, `shortfall_text`), `membership.groups` in served order, `ties_text`; `omitted_candidates` (name, position, `minutes_text`, reason) | a proposal edit after a solve clears this panel (version rule); 422 `PROPOSAL_CHANGED`: the sentence, and the box cleared |
| `#ledger-slot` | after any POST | | `OpponentLab.render.ledger(prefix, declared, ledger)` for the record (`record`), the proposal (`proposal`) and the XI reply (`xi`), each `Shell.ledger` with its ids rewritten exactly as OR-XI 8.1 rewrites them (whole attribute runs; throw when the kit's markup is not the expected one) | |
| `#not-measured-slot` | after the menu | | `Shell.notMeasured(not_measured)` | |

### 7.3 `/desk`

Eyebrow "Director's desk · the chain end to end"; h1 "One chain.<br>Every row sourced."; lede
"Declare an identity, the requirements it sets and the slot you are recruiting. The desk asks
Squad, Transfer and XI Lab and lays their answers out in one ledger, with what none of them
measures beside it. The opponent record and any proposal stay on Opponent Lab."

| Panel | Shown when | Request | Renders (server field) | States |
|---|---|---|---|---|
| `#desk-form` | always | `GET /api/desk/menu` on load; `GET /api/squad/clubs` for other clubs (the shipped route) | planning point select by `GP.scenarioOptions(catalogue, clubs, current)` (the catalogue's scenarios, then the clubs as served: two served lists in a fixed order, the shipped helper, squad.html:766), formation, the identity table (`identity_policy.phrases`: phrase, state, sentence) and preset checkboxes (`presets`, labels as served; the experimental preset disabled until the opt-in is ticked), the opt-in checkbox, slot select (`recruitable` slots, empty placeholder: no slot), stress select (`stress_sizes[].text` and "no stress"), league checkboxes, and a `<details>` "Per-match chain" (flagship only) with decision point and mode; `#compose` | another club: the per-match `<details>` disabled with `DESK_MATCH_OTHER_CLUB` |
| `#scope-slot`, `#claim-slot`, `#warnings-slot`, banners | after a reply | `POST /api/desk/chain` on `#compose`, versioned by `GP.tracker` (a reply that is not the latest is discarded) | `scope_text`, `eligibility.banner` (the unreviewed banner outside Madrid), `claim`, `non_claim`, `statements`, every part's `warnings` in stage order | `chain_state` `PARTIAL`: each part's `state_text`; `INCONSISTENT`: `DESK_INCONSISTENT` as a notice |
| `#chain` | after a reply | | one section per `stages[]` in served order: heading, `statement` (the `opponent` stage: `DESK_OPPONENT_STAGE` and a link to `/opponent`); per part: `page_name` linked to `page_href`, `state` badge, `state_text`, `claim`, `non_claim`, `summary_rows` as a two-column list | `NOT_RUN` / `NOT_STARTED` / `UNAVAILABLE`: the sentence only |
| `#desk-ledger` | after a reply | | `Desk.render.ledger(declared, ledger)`: one table of declared rows ("Declared by you", one block per served `declared[]` family with its `heading`, origin mark) and one of computed rows with a "Source" column (`page_name`, linked) beside the kit's five, each cell drawn with the kit's own badge functions, rows in served order, `data-label` on every cell for the 650 px stacking; ids `desk-ledger-declared`, `desk-evidence-ledger` | no row: the kit's empty sentences |
| `#research-slot` | after the menu, and after a reply | | `GP.research` of `verdicts` and `research_statement` | |
| `#not-measured-slot` | after the menu | | `Shell.notMeasured(not_measured)` and `not_measured_closing` | |

### 7.4 Rules of the pages

- R10. JS computes no count, share, rate, interval, minimum, threshold comparison, eligibility,
  objective, membership or evidence class. Every number printed is a server string (`*_text`,
  `value_text`, `summary_rows[].value_text`, option `text`) or a server integer on this
  allow-list, printed as is: `worlds` and `world_seed`. Ids and option values appear in
  attributes only. JS never sorts, filters or groups rows, never picks an entry of one list by an
  id from another, and never reorders parts; the one place it joins two served lists is the
  planning point select, by the shipped `GP.scenarioOptions`, in a fixed order. The selections it
  makes are the opt-in's effect on which templates are enabled (by the server's
  `needs_experimental_opt_in`), the flagship test for the per-match details (by the server's
  `scenario_id`), and which reply's `fingerprint` an acceptance carries (the proposal reply shown,
  by the version rule).
- No ranking. No team list is ordered by anything but league, club name and team id; no part is
  highlighted, sorted, enlarged or coloured by size; no candidate list appears on the desk, and the
  one XI shown on either page is in formation order; the membership groups are in their fixed
  order.
- Words. No word of `words_never_on_the_page` and no copy-guard token outside a named denial
  appears in the visible text of either page in any state (`shell.visible_text` over the
  rendered markup, 8.2). The page-written text (headings, labels, eyebrow, h1, lede, figure notes,
  the accept label) is in the render test's scan.
- Defaults. No rule, threshold, percentile, slot, decision point or opt-in is preselected; the
  stress select starts on the server's default; no request that reads the corpus is sent before a
  button is pressed, except `GET /api/opponent/teams` and `GET /api/squad/clubs`, which read the
  match tables only.
- States. Loading (`Shell.loading`), withheld, empty, undecided, 422 (the server's sentence),
  429 (`Retry-After`), 503 (`SIDECAR_UNAVAILABLE` printed verbatim, every other 503 through
  `Shell.errorText`); a `null` is never drawn as 0.
- Mobile. At 390 and 320 px the document has `scrollWidth <= clientWidth`; every table stacks at
  650 px and below by the `td::before{content:attr(data-label)}` pattern; the header nav of seven
  links and three separators fits (labs-shared.css:8-11 lays it out; section 11 asks the root to
  measure it).
- Ids are unique on each page; every `data-*` value written by the page is a plain word.
- Colour: gold (`rgb(201, 162, 39)`) marks no number and no part.

## 8. Tests

Oracles import nothing from the code they check (ROOT 4). Every rule test holds the interesting
outcome and its opposite. Every registry state is planted (`monkeypatch` of `verdicts.VERDICTS`,
with the E-10 records removed for the unregistered state); no test asserts a state by reading the
shipped registry, so neither E-10 commit has to edit these tests. No test reads the corpus except
the `slow` tests of 8.5, which skip without it, and those that reach a record also skip while
`record.record_available()` is false (`pytest.mark.skipif`). CI's corpus job runs every `slow`
test (`pytest -q -m "not research"`, ci.yml; `slow` means only "requires a downloaded corpus",
pyproject.toml:34), so the gate, not the order of commits, keeps them off the corpus before E-10
has run.

### 8.1 Unit tests, data-free

| File | Test | Asserts |
|---|---|---|
| `test_opponent_record.py` | `test_record_equals_the_oracle` | on synthetic events (built in the test with invented ids: two leagues of four teams, eight matches each, a penalty, a direct free-kick shot, an own goal, a red card, entries on every lateral cut of PIPELINE 3.5), with whole-second event clocks so every window time is an integer number of seconds and the `float64` path is exact: every part count, share, window time and rate equals `tests/opponent_oracle.py`'s recount in `Fraction` |
| | `test_record_reads_the_one_state` | `estimator.state_at` monkeypatched to record its arguments: called once per composition subject the table holds and never for the level, with `date` the declared day; a patched `state_at` that adds one event moves the record's count by one (the record has no second count); the counts equal `estimator.shape_estimate(state, ...).observed[u]` |
| | `test_window_time_is_the_tables_and_agrees_with_the_state` | with planted non-integer window seconds (for example 2765.3): `window_seconds` equals the exact `Fraction` sum of the listed valid matches' values, in every addition order; it agrees with `state.exposure[:, u, :].sum() * 5400` within a relative `1e-12`; a level rate exactly at a declared threshold holds (4.2) |
| | `test_matches_used_agree_with_the_state` | the listed valid matches' counts, added, equal the state's for every subject; a planted match on `D`'s day and one after are in neither, with `D` a date; a planted late-evening UTC match the day before `D` is listed under its UTC day and counted; a planted invalid match is listed with its reason text and adds nothing |
| | `test_no_event_is_none_never_zero`, `test_no_prior_match`, `test_level_window_time_without_event` | a team whose prior valid matches hold no S3 event has S3 shares `None` and `NO_EVENT`; a team with no prior valid match has every count, share, window time and rate `None`, `count_text` `null` and the sentence; a team with window time and no conceded entry has level rate 0, `rate_text` "0.00 per 90 minutes of window time" and no `NO_EVENT` |
| | `test_loader_is_gated` | with the gate closed (planted unregistered and planted `PENDING` registries), `load_league_tables` raises `RecordWithheld` before any reader is called; with seven planted `EXECUTED` records it reads; with an E-09 record absent, asking for S3, S4 or S5 raises and the other subjects read, with their columns only |
| | `test_loader_refuses_a_defective_sidecar` | gate planted open; a squads frame missing one team-match, a duplicate `game_id`: `RecordCorpusDefect`, never `ValueError` |
| | `test_loader_reads_only_its_columns` | gate planted open; `load_public` and `sidecar.load` monkeypatched: the column lists of 2.1 exactly; `verify` called before `load`; `xt=None`; `SIDECAR_EVENT_COLUMNS == ("card", *descriptors.GOAL_INCIDENT_COLUMNS)` |
| | `test_loader_tables_equal_the_runners` | gate planted open; one synthetic league (a dismissal, a second yellow, an own goal, a match whose squads hold no `red_minute`) fed to `record.load_league_tables` and to `experiments.run_conceded_shape.load_league` then `league_tables` by monkeypatching the public and sidecar readers each calls: the record's table equals the runner's `close_11v11` table on every column the record holds (`pd.testing.assert_frame_equal`) |
| | `test_estimator_errors_are_faults` | an estimator `ValueError` (a team id missing from `team_ids`) inside `build_record` is a `RuntimeError`, and the route answers 500, not 422 |
| | `test_record_available_follows_the_registry` | on planted registries: false with no E-10 record, false with seven `PENDING`, false with six `EXECUTED` and one `PENDING`, true with seven `EXECUTED` records of any tokens; `subject_available` of S3, S4, S5 also needs a planted E-09 record |
| | `test_oracle_imports_nothing_from_galactico` | the oracle's AST imports no `galactico` module |
| `test_opponent_panel.py` | `test_constants_equal_the_config` | 3.1, against the registered config when present and the draft otherwise, the rendered config-stating sentences included |
| | `test_world_draw_and_state_exclude_invalid_and_same_day_matches` | PIPELINE 12.3: the draw receives exactly the ids of the league's valid matches dated before `D`'s calendar day; a planted invalid match and a planted match on `D`'s day are not among them, and the state built for the point holds neither; both with `D` a date and with `D` a time of day after the planted kick-off (at the module function, which accepts a time) |
| | `test_world_weights_reach_rows_by_game_id` | `snapshots.league_world_weights` monkeypatched to return a planted `WorldWeights` with distinct, unsorted multiplicities over a three-team synthetic league, `game_ids` given out of order: the state built in world `r` equals `estimator.state_at` on the rows physically repeated by their match's weight, and the served interval equals `np.quantile` of the hand-computed per-world `served_composition` values |
| | `test_offered_only_where_established` | `offered` under every registry state of 1.6 (planted: unregistered, `PENDING`, `INCONCLUSIVE`, each NOT_ESTABLISHED token, `DEFENDER_SHAPE_SIGNAL` with figures), dates on either side of `PANEL_FROM_DATE`, and a withheld subject; a LOCAL record never offers (ADR-0018) |
| | `test_estimate_is_the_estimators` | `served_composition`, `served_volume`, `shape_estimate`, `level_estimate` monkeypatched to return marked values: the panel serves exactly those (no formula of 4.2 is held here) |
| | `test_point_needs_the_reliability_bound` | planted `Figure` objects: `reliability_lower_bound` 0.69999 gives no point and the interval; 0.7 gives both; a missing figure or a `bool` value is a `RuntimeError` |
| | `test_holes_are_counted`, `test_quantiles_are_linear_and_shared_worlds` | a team with prior events in few matches has holes counted, for a composition (`O_total == 0`) and for the level (`O'_u == 0`, a world with window time and no event is a hole); quantiles equal `np.quantile(..., method="linear")`; every subject of one request reads one `WorldWeights` (one call), and every panel serves the same namespace and match count |
| | `test_panel_head_follows_the_kind` | a composition panel serves `PANEL_HEAD_COMPOSITION`, the level's `PANEL_HEAD_VOLUME` |
| | `test_s5_ratio_is_never_served` | no served value equals the ratio of the S5 counts and no key or text names it except `S5_RATIO_NOTE` |
| | `test_group_non_claim_in_every_state` | every group's `non_claim` equals `REGISTRY_NON_CLAIMS[group]` under the unregistered registry (where the payload's `non_claim` is `""`), `PENDING` and every token; once a record exists, the record's `non_claim` equals the constant |
| `test_opponent_proposal.py` | `test_exact_threshold_comparison` | a share of exactly 2/5 holds at `0.4`; 0.3999... does not; the rate at its threshold holds |
| | `test_undecided_sets_nothing` | a cited share `None` gives `UNDECIDED` and no minimum |
| | `test_outcomes_follow_template_order` | rules sent in reverse order: the same reply |
| | `test_conflicting_percentiles_are_refused_whatever_the_record`, `test_same_percentile_is_one_minimum` | two templates that set one requirement at different percentiles are a 422 for a record where both hold, one holds and neither holds |
| | `test_qualifiers_follow_may_gate` | PIPELINE 12.3: a proposal citing a `DEFENDER_SHAPE_SIGNAL` record (no qualifier), a `PENDING` one (`proposal_sentence_not_tested`) and a NOT_ESTABLISHED one (`proposal_sentence_not_established`): one qualifier per cited record whose `may_gate` is false, beside its label, in `subject_groups` order, none merged or dropped |
| | `test_templates_follow_the_descriptor_mirror` | 4.1: each template's cited `PartRef` columns are `att_left`, `att_right` or both as its `requirement_ids` say; the six rows pinned literally; each label is built from the cited part's phrase and the requirements' labels |
| | `test_side_templates_need_the_opt_in` | `EXPERIMENTAL_OPT_IN_ERROR` without it |
| | `test_oracle_agrees` | rule states equal `tests/opponent_oracle.py`'s on 200 seeded synthetic records and thresholds, the boundary values included |
| `test_opponent_api.py` | `test_routes_answer_through_finalize` | gate planted open, with synthetic league tables, reference and match snapshot patched into the gated loaders: each route answers 200, the envelope of 5.4 holds every key, and the reply passes `runtime.finalize` (providers, keys with `BANNED_KEY_PARTS`, `scan_labels`) |
| | `test_every_constant_passes_the_copy_guard` | every constant of 5.6 and 6.5 (headings, venue words, origins, percentile text and template labels included) under the format arguments the router uses, and the config sentences `panel.py` serves |
| | `test_words_never_on_the_page_are_never_served` | none of the five words in any served string of any reply in any state, outside provenance |
| | `test_withheld_until_e10_has_run` | planted unregistered and planted seven-`PENDING` registries: record, proposal and XI (no acceptance) answer as 1.7 says, with the matching withheld sentence; `panel_state`, `panel_text` and `panel` are `null`; the league loader patched to raise is never called; the XI with `accepted_proposal` is 422 `ACCEPT_WHILE_WITHHELD` |
| | `test_badges_follow_the_registry` | planted `PENDING`: every badge `E-10 · RECORD ONLY · NOT RUN`; each token in turn: its badge |
| | `test_refusals` | an extra field; `team_id` "675", 675.0, true; a date `2018-5-6` (`DATE_FORMAT`), `2018-02-30` and `2016-01-01` (`DATE_RANGE`); `percentile` 75.0, true, 80; a share threshold 1.5; a template twice; acceptance with no rule; two templates for one requirement at two percentiles; a side template without the opt-in; an entered minimum for a requirement a declared template sets, with acceptance: each 422 with its sentence and no input value, decided before any build; an unknown team and an unknown decision point: 404 |
| | `test_acceptance_is_bound_to_the_proposal_shown` | the fingerprint of a proposal reply accepted unchanged applies its minima; the same fingerprint with an edited threshold, with a planted registry change, and with a changed sidecar token: 422 `PROPOSAL_CHANGED`; `PROPOSAL_ACCEPTED_NOTHING_SET` when no rule held |
| | `test_sidecar_failures_are_503` | `SidecarMissing`, `SidecarStale`, `SidecarMismatch`, `RecordCorpusDefect`: 503 with `SIDECAR_UNAVAILABLE` exactly; a missing public file: 503 with the corpus sentence |
| | `test_cache_key_moves_with_sidecar_and_registry` | a changed sidecar file identity and a planted registry record each change the key; the same request twice is a hit |
| | `test_xi_part_equals_api_xi_solve` | with the opt-in and a synthetic snapshot patched into both `decision_lab.snapshot` and `xi_extensions._match_snapshot`, `solve_xi` spied inside the route: its arguments are those `decision_lab.solve` passes, and its result (`assignments`, `solution_status`, `objective_vector`, each `RequirementAssessment`) equals `/api/xi/solve`'s with `bootstrap_worlds: 0`, for minima entered, a proposal accepted (its minima sent to `/api/xi/solve` as `format_plain` printed them) and a SATISFY infeasible case; without the opt-in `model_note` is served |
| | `test_xi_status_and_membership` | planted solver results: each status gives its sentence, `INFEASIBLE` under `BALANCE` gives `XI_STATUS_UNFIELDABLE`; for `OPTIMAL` every one of the five `(possible, necessary)` pairs lands under its `MEMBERSHIP_HEADINGS` heading, `(None, False)` included; `membership` is `null` and no membership completeness key exists for `INFEASIBLE`, `FEASIBLE`, `UNKNOWN` and `MODEL_INVALID`; `MODEL_INVALID` is not stored; `ties_text` only for `OPTIMAL` with a `(True, False)` row |
| | `test_unaccepted_proposal_changes_no_solve`, `test_xi_without_rules_reads_no_record` | `decision_inputs` spied: the minima it receives exclude the proposal's unless it is accepted; an XI request with no rule never calls the league loader, in every registry state |
| | `test_every_ledger_row_is_a_shell_row` | every terminal state of every route through `shell.ledger_row` and `shell.declared_row`; ids plain words; no `value_text` is `"0"` where no number exists; window time is DERIVED |
| | `test_parts_in_declared_order_and_nothing_picked_out` | parts in `spec.part_names` order in every reply; no key or text says largest, most, least or a rank |
| | `test_literals_equal_their_objects` | `get_args(TemplateId)` equals the `TEMPLATES` ids; the mode labels are `xi_extensions._RULE_TEXTS` |
| | `test_import_reads_nothing` | a subprocess imports `galactico.api.opponent_lab` and `galactico.api.desk`: no module named `ortools` or starting `ortools.`, and none of `galactico.features.team`, `galactico.models.opponent` (or a submodule of either), `galactico.optimization.snapshots`, `galactico.optimization.reference`, `galactico.optimization.squad.kernel`, `galactico.storage.public`, `galactico.ingestion.sidecar` is loaded, and every gated loader's `cache_info().currsize == 0` (pandas and numpy are not checked, 0.6) |
| | `test_private_reuse_is_pinned` | names and signatures of `planning._built_once`, `_corpus_files`, `_digest`, `_minimum_text`, `_outward`, `xi_extensions._match_snapshot`, `_exact_sum`, `_lineup_rows`, `_RULE_TEXTS`, `declare` |
| | `test_paths_are_new_and_unique` | the router serves exactly its six paths; none is served by another router |
| `test_desk_api.py` | `test_each_part_is_its_routes_reply` | with every loader patched to synthetic objects, each carried part's served fields equal the sub-route's reply to the same declarations through the TestClient, as JSON after removing `budget.elapsed_seconds` (the `timeless` helper of `test_xi_extensions_api.py`) |
| | `test_ledger_composition` | base rows once; other rows prefixed and in part order; with a slot declared, the real `squad_brief` and `transfer_injection` handlers on synthetic loaders: a 200 holding both `brief-declared-slot` and `search-declared-slot`; a planted difference in a common declared or base row gives `INCONSISTENT`, not stored; the per-match sub-requests share scenario, formation and opt-in with `match-xi`'s and hold no lock, exclusion or minimum; every key of `MATCH_COMMON_KEYS` maps to a `match-xi` row; conflict's own rows carried under its prefix |
| | `test_desk_shows_no_e10_descriptor` | `record.load_league_tables`, `record.build_record` and `proposal.evaluate` spied: never called by any desk request, gate open or closed; no `proposal`, `rules`, `cited_value_text` or `minimum_rows` key and no non-null `record_state` in any desk reply; `DESK_NO_DESCRIPTOR` and `DESK_OPPONENT_STAGE` present |
| | `test_parts_run_when_declared` | no slot: brief and search `NOT_RUN` with `DESK_NO_SLOT`; another club with `match`: 422; `stress_k` null: no stress part; SATISFY infeasible without the opt-in: conflict `NOT_RUN` with its sentence; every `DeskRequest` field (presets, requirements, exclusions, locks, filters, leagues) reaches its part's request |
| | `test_stages_are_fixed` | `stages` equals `DESK_STAGES` in ids, headings and part ids in every state; the `opponent` stage has no part |
| | `test_claim_names_the_parts_that_ran` | without a slot or a match the claim names Squad Lab only; with both it names each page whose part ran, once, in stage order |
| | `test_not_started_when_time_runs_out` | a patched clock: the first part whose ceiling exceeds the remaining budget and every later one `NOT_STARTED`, completeness `DEADLINE`, not stored |
| | `test_desk_takes_no_long_place` | `runtime.long_job` spied: never called with `desk.chain`; a stress part takes its own place and releases it |
| | `test_busy_and_absent_propagate` | a part's 429 is the desk's 429 with `Retry-After`; the snapshot's 503 is the desk's 503; the search part's 503 (a league absent) makes it `UNAVAILABLE` with its sentence, the chain `PARTIAL`, the planning parts served and the reply not stored |
| | `test_summary_rows_are_served_fields` | every summary row's text is a served string or `str()` of a served integer; the search part carries the deficiency statement, the `name` key's outcome groups, the corpus exit statement and, with leagues opted in, the cross-league flag |
| | `test_research_and_not_measured_are_plannings` | `research_statement` and `verdicts` equal `planning.verdict_reading()`; `not_measured` equals `planning.not_measured()` and begins with the nine of ROOT 2.3 in order |
| | `test_reply_passes_finalize`, `test_every_constant_passes_the_copy_guard` | |

### 8.2 Render tests (node; the harness of `test_shell_render.py`)

`test_opponent_render.py` and `test_desk_render.py` load `labs-shared.js`, `planning.js` (desk)
and the page's script, which touches no `document` when evaluated, and call `render` on replies
built by the real routers on synthetic data in every state (withheld before registration,
withheld before the run, subject withheld for E-09, shown, offered, estimate shown, point
withheld, all holes, proposal formed, nothing set, accepted, accepted with nothing set, proposal
changed, infeasible, unfieldable, not certified; desk composed, partial, not started, unavailable
part, inconsistent, other club). They assert: no `undefined`, `NaN` or `[object`; hostile strings
in every server field escaped; every digit run of the visible text (`shell.visible_text`) lies
inside a server string printed at that place or is the decimal form of an allow-listed integer
(7.4), after removing the kit's badge `aria-label`s (the OR-XI rule); parts, rules, rows, groups
and stages appear in served order; no sentence of the XI panel appears twice; no copy-guard token
and no word of `words_never_on_the_page` in the visible text, page-written text included; every
group's non-claim present in every state; ids unique; the ledger id rewrite throws on a changed
kit markup.

### 8.3 Page shell

`test_opponent_desk_pages.py`: each page's nav equals `shell.nav_markup(dest)` (after the root's
nav edit; until then it is `xfail` with that reason, never skipped silently), links
`labs-shared.css`, carries the footer credit, loads its scripts in the order of 7.1, and its inline
script opens with the header comment the planning pages carry (`test_planning_render.py:954-1021`
pattern). `opponent.css` and `desk.css` use only `op-`- and `desk-`-prefixed classes and ids or
selectors scoped under `#op-root` / `#desk-root` (the OR-XI 8.3 rule, so no shared element is
restyled).

### 8.4 e2e (corpus, CI)

Both specs set `test.setTimeout` per test and explicit response timeouts, as `e2e/squad.spec.js`
and `e2e/transfer.spec.js` do (cold builds exceed the 30-second default, playwright.config.js:25).

`e2e/opponent.spec.js` (CI builds Spain's sidecar only, ci.yml:63): load `/opponent`; the menu and
teams GETs are the only requests before a press; read `record_available` from the menu and each
subject's expected badge from `/api/evidence/verdicts` (a subject absent from it expects
`RECORD ONLY · NOT TESTED`); choose the decision point "Real Madrid · before Barcelona" and load
the record: every badge equals the expected one, every group's non-claim is visible, no page error
and no console error. Then, by `record_available`:

- false: the withheld notice is shown and no count text; the proposal form is disabled with
  `PROPOSAL_WITHHELD`; a POST to `/api/opponent/xi` with an `accepted_proposal` of 64 zeros
  answers 422 `ACCEPT_WHILE_WITHHELD`; a record request for England (no sidecar) answers 200
  `WITHHELD`; solving the XI without a proposal shows eleven lineup rows and the defaults in force.
- true: parts appear in declared order; a record request for England answers 503 with
  `SIDECAR_UNAVAILABLE` printed verbatim; form a proposal with the opt-in and one rule at
  threshold 0 (it holds whenever the cited share exists; the spec asserts the state the reply
  serves), accept it, solve: eleven lineup rows, the accepted text and the minima in force; untick
  accept and solve: the minima in force are the defaults.

The header nav marks `/opponent`; at 390 and 320 px no horizontal overflow.

`e2e/desk.spec.js`: load `/desk`; compose the flagship with defaults: the stages render in the
order of `DESK_STAGES`, brief and search read `DESK_NO_SLOT`, the opponent stage shows its
sentence and a link to `/opponent`, the ledger holds rows from Squad Lab, the not-measured panel
holds the nine of ROOT 2.3 first; declare the centre-forward slot with no deficiency and compose:
the search part shows the deficiency statement and no outcome group (the default flagship has no
declared shortfall, ROOT 3b); add the `exclude-3322` and `progression-league-p90` presets and
compose: when the search part's served deficiency state is `SHORTFALL` it shows outcome groups and
no candidate name, otherwise its deficiency statement; declare the per-match chain at
`madrid-2018-05-06`: the XI solve and ceilings parts render, and no desk reply holds a `proposal`
key; choose another club: the unreviewed banner shows and the per-match details are disabled; 390
and 320 px.

Screenshots: none is added by this work. If the root adds the two pages to
`e2e/screenshots.spec.js`, X14's rule applies: regenerated and inspected only where the corpus is
present, and a record screenshot only after E-10's results commit (1.7).

### 8.5 Slow (corpus)

| Test | Gated by the record gate | Records |
|---|---|---|
| `test_reference_club_median_is_the_snapshot_normaliser` | no: it reads the reference and the match snapshot, no E-10 quantity | 4.3 |
| `test_xi_part_equals_api_xi_solve_real` | no rule: no; an accepted proposal: yes | the parity of 8.1 on the real snapshot at both decision points |
| `test_xi_and_desk_build_time_and_memory` | no | cold time of the XI route without rules and of a desk compose, and peak RSS, without asserting a number, for ADR-0032 before registration (5.1) |
| `test_record_build_time_and_memory` | yes | cold build time of one league's table, the record request time and peak RSS, without asserting a number, for the note to ADR-0032 at E-10's results commit (5.1) |
| `test_loader_tables_equal_the_runners_real` | yes | the parity test of 8.1 on Spain |

No other test of this work compares `match__` columns with `build_match`: PIPELINE 9's
`test_oracle_against_build_match_real` (five matches per league, `columns=()`) is that check, and
the loader's frames are tied to the runner's by the parity tests.

### 8.6 Not changed

Every existing test file passes unchanged except the nav and page tests the root edits (section 11).
A failure in any other is a defect of this work.

## 9. Hashes, fingerprints, provenance

| Object | Rule |
|---|---|
| descriptor fingerprints | `spec.fingerprint` of WP A for the six descriptors, equal to `descriptor_fingerprints` (E-10's test); served under `provenance.descriptor_fingerprints` and printed in the ledger's `solver` cell; the level serves the primary's under `counts_fingerprint` and never a fingerprint of its own |
| table version | `TEAM_MATCH_VERSION` (`team-match-table-v2`) in provenance |
| sidecar | `sidecar.provenance(league)` verbatim (schema version, tag mapping version, content hashes, raw digests, competition) |
| public files | the token listing of 5.3 (names, sizes, modification times), not a content hash; the cache key, not evidence |
| panel worlds | `WorldWeights.namespace` and `len(WorldWeights.games)` with `worlds` and `world_seed`, one value per reply (R12) |
| proposal | `fingerprint` (4.5), the identity an acceptance carries |
| reference | `declared_minimum(...).reference_fingerprint` per proposed minimum |
| snapshot | `kernel.scrub_lineage(snap.provenance)`, as OR-XI 7.5 |
| registry | each subject's badge, so a reply says which registry state it was built under |
| line endings | every hash LF-normalised |
| result store | `runtime.source_fingerprint` hashes `optimization/**/*.py` and `api/*.py` only (runtime.py:331-342), so an edit to `models/opponent` or `features/team` would not move a stored file's key. No result store ships; section 11 asks the root to widen the set before one does |

## 10. Pre-merge review checklist

The reviewer signs each line before the root registers the routers.

1. No frozen file, no root-owned file and none of WP A's three modules is in the diff.
2. No module here holds a definition, zone, part, window, phrase, label or estimator formula of
   E-10: every one is read from WP A (`grep` for the cut values `21/25`, `19/100`, `2/3`, `1/3`,
   `2/5`, `3/5` and for `exp(` in `galactico/models/opponent/` and
   `galactico/api/{opponent_lab,desk}.py` finds none; `tests/opponent_oracle.py` holds them by
   design and imports nothing from `galactico`, by test).
3. The record reads the one state (`estimator.state_at`); the panel calls the one estimator; no
   product module imports `galactico.validation` or `experiments`; the loader's frames are tied to
   E-10's runner by the parity test.
4. The record gate of 1.7 is inside `load_league_tables` and tested; it opens only when every
   E-10 record is `EXECUTED`; every corpus test that reaches a record skips while it is closed; no
   test, spec or screenshot of this work reads the real corpus's descriptors before E-10's results
   commit.
5. Every reply passes `finalize`; `providers` is exactly `["pappalardo"]`; no served string holds
   a word of `words_never_on_the_page`; the list itself is never served.
6. Every badge, statement, gate and figure comes from `verdicts`; the estimate is shown only where
   `may_gate` is true, behind the opt-in, from `PANEL_FROM_DATE`; the point only at a reliability
   bound of at least the config's; S5's ratio is never served.
7. The proposal has no default threshold or percentile, compares in exact arithmetic, never picks
   a part by size, carries the qualifiers of 4.4, stays HEURISTIC, and changes a solve only with
   the `accepted_proposal` fingerprint of the proposal shown, through `decision_inputs`; the parity
   test with `/api/xi/solve` passes.
8. No ranking: no list of teams or players is ordered by a record value or a solver output; the
   desk shows no candidate name, no E-10 descriptor and no proposal.
9. The desk calls handlers in process, sequentially, takes no long place, and serves `NOT_RUN`,
   `NOT_STARTED`, `UNAVAILABLE` and `INCONSISTENT` states with their sentences; nothing is dropped
   silently.
10. JS computes no number and sorts nothing (the render tests pass); both pages pass at 390 and
    320 px.
11. The XI route's and the desk's budgets are measured on the corpus and the numbers are in
    ADR-0032 before the pages are linked from the nav; the record and proposal budgets are
    measured at E-10's results commit (5.1).

## 11. Requests to the root

| File | Change |
|---|---|
| `galactico/api/player_lab.py` | after `app.include_router(xi_extensions_router)` (player_lab.py:61): `from .opponent_lab import router as opponent_router` and `from .desk import router as desk_router` with the other imports, then `app.include_router(opponent_router)` and `app.include_router(desk_router)`. Both import nothing heavy at import (8.1) |
| `galactico/api/shell.py` | `Destination` gains `sr_suffix: str = " Lab"`, and `nav_markup` writes `f'<span class="sr-only">{destination.sr_suffix}</span>'` only when it is non-empty (the five shipped links keep their bytes); `DESTINATIONS` gains `Destination("opponent", "/opponent", "Opponent", "matchday")` after XI and `Destination("desk", "/desk", "Desk", "desk", sr_suffix=" (Director’s desk)")` last, with U+2019 (7.1); the module docstring's "Five destinations ship" becomes seven. In the same commit as the two routers and ADR-0032 (N7), never before (a nav link to a missing page is a 404, shell.py:11-12) |
| `web/match.html`, `web/xi.html`, `web/squad.html`, `web/transfer.html` | the nav block replaced by the new `nav_markup(dest)` bytes, nothing else (under N5's R13 override, R-4) |
| `web/index.html` | two links in its own nav (index.html:189-199), `/opponent` and `/desk` (under N5's R13 override, R-4) |
| `web/labs-shared.css` | only if the 320 px check of seven links and three separators overflows (labs-shared.css:8-11) |
| tests that pin the nav | `tests/test_shell_payloads.py:30-42` (seven hrefs and dests, three separators, the visible text with "Opponent Lab" and "Desk (Director’s desk)", no `opponent`/`desk` exclusion), `:53-56` (parametrise with names that are still not destinations), `:59-79` (items carry `d.sr_suffix`); `tests/test_web_shell.py:19` (`PAGES` gains `opponent` and `desk`); `tests/test_xi_extensions_render.py:843-870` (`SHIPPED_XI_HTML` re-pinned after the nav edit: the five additive edits are unchanged); any e2e assertion that counts nav links. `tests/test_shell_render.py:312-369` builds its own five-item nav literal and is not edited |
| `.github/workflows/ci.yml:69` | add `e2e/opponent.spec.js e2e/desk.spec.js` to the playwright command (both branch on the registry state, 8.4) |
| `galactico/api/runtime.py:331-342` and `tests/test_lab_runtime.py:399-408` (recommended) | `source_fingerprint` also hashes `models/opponent/*.py` and `features/team/*.py`, and the pinned set says so |
| `galactico/api/planning.py` (E-10's registration commit, N6) | E-10's registration commit carries it: N6 rules (R-5) that PIPELINE 13's line for "the wording that names the registered protocols" covers it, and N2's edit names it in that line. The change: the `shots` item of `NOT_MEASURED_EXTRA` (planning.py:1439-1442), whose "No registered protocol tests one" is false once E-10 registers `conceded_shots_inside_box_share`, reworded, for example "No shot construct is shown on a planning page. E-11, registered and not run, compares only whether two providers agree on shot counts; E-10, registered, tests a team-level conceded shot share that no planning page shows." The desk serves `planning.not_measured()` and inherits the edit; its test compares with planning's list, not with the text |
| `DECISIONS.md` | ADR-0032 "Opponent Lab and the Director's desk": Problem (ROOT 2.3's two surfaces unbuilt; KNOWN_LIMITATIONS "not implemented"), Decision (sections 1.7, 2.2, 3, 4.5, 6.3 and 6.4 of this file), the R13 override (ROOT 2.12 N5, ruling R-4: in the form of W8, overriding R13 for exactly the nav bytes of `web/index.html`, `match.html`, `xi.html`, `squad.html` and `transfer.html` and the pinned tests above; `d9bf28f`'s earlier nav edit for Squad and Transfer Lab recorded as the same kind of edit, made without naming R13), Evidence (the oracle, parity and loader tests, the measured times and memory of 8.5), Alternatives rejected (a record before E-10's run; a record in a window E-10 does not register; a second estimator; a proposal with default thresholds; comparing two parts of a record; an acceptance not bound to the proposal shown; client-side composition of the desk; the desk showing descriptors or forming proposals; carrying declarations across pages by URL), Relation to ADR-0018, ADR-0019, ADR-0024; and, at E-10's results commit, a note with the record and proposal routes' measured times |
| `KNOWN_LIMITATIONS.md` | "Product scope" (:418-422): Opponent Lab and the desk are implemented, with what they are; "The tag sidecar holds facts, and nothing has read it yet" (:271-283): Opponent Lab reads cards, own goals, goals and the sheet's dismissals, after `verify`, once E-10 has run; new entries: the record is withheld until E-10 has run (1.7); S3, S4 and S5 are withheld until E-09 is registered (N4); one window, E-10's; a record is not adjusted for opponents or strength and cannot tell funnelling from failing to close (H14); a proposal is a declared HEURISTIC policy; the per-match chain exists at two Madrid decision points only; the desk's per-match chain takes a decision point and a mode, and minima, locks, exclusions, proposals, the frontier and the risk modes are declared on Opponent Lab and XI Lab; the desk page offers presets, the opt-in, the formation, the slot, stress and leagues, and requirement declarations, exclusions, locks and filters are declared on Squad and Transfer Lab; the desk is sequential, can take its budget plus one build per part that starts cold, and holds two of the sixteen places; a league without a built sidecar has no record (CI builds Spain only) |
| `README.md`, `ARCHITECTURE.md` | the three model modules, the two routers and the six web files in the module tables; the two labs in the product list |
| `docs/research/north-star/README.md` | a row for this file: draft, revised after three reviews, its root questions ruled (ROOT 2.12), not audited, nothing built |
| E-10's results commit | nothing extra for this work's tests: they plant registry states, the e2e reads every badge from `/api/evidence/verdicts`, and the record gate opens by itself (PIPELINE 13's list stays sufficient) |

## 12. Reconciliation

**With E-10's PIPELINE.** Sections 2 and 3 are used by name only (0.5). Section 12.3 is
implemented in `models/opponent/panel.py` (3.1 explains why that module is "the Opponent Lab
module" of 12.3); its three listed tests are `test_world_draw_and_state_exclude_invalid_and_
same_day_matches`, `test_constants_equal_the_config` and `test_group_non_claim_in_every_state`,
and its proposal test is `test_qualifiers_follow_may_gate`; its hole rule is used verbatim (3.3
step 5). Section 11's first check holds because no WP A function runs on the corpus here before
the results commit (1.7). Section 13's desk rule is met in every state (6.4). The product
consequence table of the protocol is 1.6, with the record withheld in the "no record" and
`PENDING` rows (DISSENT 1, N1); N2 aligns the protocol's table to that before registration.

**With OR-XI.** The per-match XI part uses `xi_extensions.declare` (the opt-in rule) and its gated
snapshot; the desk composes ceilings and conflict by their handlers, so their claims, ledgers and
refusals are OR-XI's own. The opponent XI is XI Lab's solver, called once, as `/api/xi/solve`
calls it; D5/D6 forbid a loop of solves, not one. Its membership uses OR-XI's five headings.

**With the planning surfaces.** The desk passes `PlanningInputs` unchanged to Squad and Transfer
Lab, carries their `research_statement` reading and their not-measured list, and adds no planning
sentence. D4 holds: progression alone unless the reader opts in.

## DISSENT

1. **The record is withheld until E-10 has run.** The E-10 draft's product consequence
   (preregistration.md:654-676) shows the record "in every state", including the rows "no record
   (before registration)" and `PENDING`. This file withholds it in both (1.7) and shows it from
   the results commit. Evidence: for the unregistered row, R5 ("computing any outcome statistic
   is not [allowed]" during design; E-10 is a prospective plan on reused data) and the protocol's
   prior-exposure table, which states that no conceded split by lateral third and no team-season
   composition has been served (preregistration.md:80) and rests criterion (f) on three leagues
   with no such exposure (:86); for the `PENDING` row, PIPELINE 11 row 1, whose code review signs,
   after the pipeline commit and before the gate stamp, that no file under review (WP A among
   them) was executed on `data/`, and PIPELINE 2.5, which lets the real oracle run after
   registration with no descriptor column. A record computed in the `PENDING` state would run WP A
   on the corpus inside that window, and the registry, the only research state product code may
   read (ROOT 3b), cannot tell the window from the time after the gate stamp. A served record of
   every team of five leagues is the composition E-10 tests, and every person who looks at it
   before the run is exposed. ROOT 2.12 N1 accepts this on that evidence (R-1). N2 aligns E-10's
   product table before registration: its rows "no record (before registration)" and `PENDING`
   print the non-claim and the reason the record is withheld, and the record is shown from the
   results commit. The edit is E-10's, verified by an independent auditor before registration
   (Z4); until it is registered this file departs from the READY draft's wording, and after it
   from nothing.
2. **No default threshold or percentile in a proposal.** ROOT section 3 makes any mapping from an
   adjective to a number a declared, editable HEURISTIC policy, and the planning presets ship a
   default percentile (75, IDENTITY_PHRASES). Here the template is the structure and every number
   is the reader's, as O7 gives the frontier no default dimension, because no default threshold for
   a conceded share exists that is not an invented constant inheriting the record's credibility
   (STAGE-3-QUESTIONS, ROOT section 0). The cost is a form that starts empty. OPEN QUESTION 2.
3. **No "defensive action distance".** ROOT 2.5 names "defensive action distance (never line
   height)". E-10 defines no distance: S4 is a composition by pitch third and S5 a share. The pages
   use E-10's labels verbatim (one object); no distance is shown. "line height" is a copy-guard
   token and cannot appear.
4. **The squad path is not used for a proposal.** The brief asks how an accepted proposal enters an
   XI solve "through the existing XI or squad declared-requirements path". It enters through the
   XI path only (4.5): a proposal is per match and the planning point is the season's end, so a
   squad audit at 21 May has no opponent. OPEN QUESTION 4.
5. **The desk shows the opponent record and the proposal as a link, not as composed parts.** ROOT
   2.3 asks for "the chain end to end", and ROOT 2's chain holds, per match, "opponent record ->
   optional requirement proposal -> XI solve". The desk composes the XI solve and its exact
   additions, and gives the first two steps a stage of their own that links to Opponent Lab (6.1,
   6.4). Evidence: PIPELINE 13 (a planning surface that serves `planning_research_sentence` shows
   no E-10 descriptor or volume, and the desk serves it from E-10's results commit on); a
   proposal's minima and the thresholds its rules reached bound a record's share, and repeated
   requests would narrow it (review E6), so no copy could make the desk "show no descriptor"; and
   ROOT 2.3's acceptance presupposes that the reader saw the proposal, which a desk request
   carrying an acceptance beside unseen rules would not guarantee (review C6). ROOT 2.12 N3
   accepts this (R-2): it meets ROOT 2.3's "chain end to end", because the chain's first two
   steps live on the page that may show them; the desk forms no proposal and shows no descriptor.

## Root rulings (ROOT-DECISIONS 2.12)

The revision put five questions to the root, R-1 to R-5, to be ruled before the routers are
registered. ROOT-DECISIONS 2.12 ruled them on 18 October 2026 (N1 to N6) and fixed the order of
work (N7). Each is recorded here against the question it answers; where this summary and 2.12
differ, 2.12 wins.

- **R-1. When the record gate opens.** The question: this file opens the gate at E-10's results
  commit, when all seven records are `EXECUTED` (1.7, DISSENT 1), departing from the E-10 draft's
  product table for the `PENDING` row; the alternative was records in the `PENDING` state, with
  the gate reading "seven E-10 records exist" and the safety resting on commit order.
  **N1 ACCEPTED.** The gate opens at E-10's results commit, when all seven E-10 records are
  `EXECUTED`, and not at registration, inside the one loader that reads the corpus for a record;
  evidence R5 and E-10 PIPELINE 11 row 1, and the registry cannot tell the window before the gate
  stamp from the time after it. Before the run the pages ship with the record withheld
  (`RECORD_WITHHELD_NOT_RUN`). The `PENDING` alternative is not taken. **N2 RULED** (consequence
  for E-10): E-10's product table is aligned before registration. The prior-date record is shown
  from E-10's results commit; before it the panel prints the non-claim and the reason it
  withholds the record, and the rows "no record (before registration)" and `PENDING` say so. The
  edit is to a READY draft, so an independent auditor verifies it before registration (Z4), with
  `pipeline_spec_sha256` recomputed if PIPELINE.md moves. It is E-10's edit, not this work's (0.2
  step 2).
- **R-2. The desk's per-match chain without the record and the proposal** (DISSENT 5, 6.4): a
  narrower reading of ROOT 2.3's "chain end to end". **N3 ACCEPTED.** The desk composes the XI
  solve and its exact additions and reaches the opponent record and the requirement proposal by
  the `opponent` stage, which links to Opponent Lab. That meets "chain end to end": the chain's
  first two steps live on the page that may show them. The desk forms no proposal and shows no
  descriptor (E-10 PIPELINE 13; the narrowing of review E6).
- **R-3. E-09 adjacency.** S3, S4 and S5 are team aggregates of the event sets behind E-09's
  unregistered candidates (1.7). The default withheld them per subject until a registry record
  under `"E-09"` exists; the alternative had E-09's registration commit record Opponent Lab
  exposure in its prior-exposure table, with `E09_ADJACENT` = `()`. **N4 ACCEPTED the default.** Each of the three is withheld
  until a registry record under `"E-09"` exists (`record.E09_ADJACENT`, 1.7, 2.1), so no one is
  exposed to them before E-09 is frozen. The alternative is not taken.
- **R-4. The nav edit and R13.** Adding two destinations changes the nav bytes of
  `web/index.html`, `match.html`, `xi.html`, `squad.html`, `transfer.html` and re-pins
  `SHIPPED_XI_HTML`, `tests/test_web_shell.py` and `tests/test_shell_payloads.py`. **N5 RULED.**
  ADR-0032 overrides R13 for exactly those nav bytes and the pinned tests section 11 names, in the
  form of W8 ("overriding R13 ... and that commit carries an ADR naming them"). `d9bf28f`'s
  earlier nav edit for Squad and Transfer Lab is recorded there as the same kind of edit, made
  without naming R13 (5.8, section 11's ADR-0032 row).
- **R-5. Planning's `shots` item** (section 11): whether PIPELINE 13's planning wording line
  covers the rewording at E-10's registration. **N6 RULED.** It does: E-10 PIPELINE 13's line for
  "the wording that names the registered protocols" covers rewording planning's `shots` item at
  E-10's registration, and N2's edit names it in that line, so E-10's registration commit carries
  it explicitly (section 11's planning row).
- **Order** (no question was put; ruled with the five). **N7 RULED.** This file is audited, with a
  refuter per claimed blocker, until no scope has a blocker. The build follows E-10's pipeline
  commit, which brings WP A (`galactico/features/team/`). The routers and the nav entries are
  registered in one commit with ADR-0032 (0.2, section 11).

## OPEN QUESTIONS

1. **Ship order.** Ruled by ROOT 2.12 N7 (0.2): this file is audited until no scope has a
   blocker, and the build follows E-10's pipeline commit (WP A), which PIPELINE 13 puts after
   registration; this work imports WP A's definitions, so it cannot be built before WP A exists.
   Whatever the order, the gate of 1.7 is inside the one loader and opens only at E-10's results
   commit (N1), so the record cannot reach the corpus earlier.
2. **Proposal defaults.** Should the 75th percentile, the planning presets' convention, be
   pre-filled for the percentile (never for the threshold)? This file says no (DISSENT 2).
3. Withdrawn in revision: the desk forms no proposal, so it states nothing about a record (6.4,
   DISSENT 5).
4. **A squad-path proposal.** Should a later release let a proposal set a planning minimum through
   `RequirementDeclaration(source="LEAGUE_PERCENTILE")`, and against which opponent at a
   season-end planning point?
5. **Units of the reference at a match cutoff.** 4.3 rests on the reference's club median at
   `2018-05-06` and `2018-04-08` equalling the match snapshot's normaliser. If the slow test fails
   (the two read the corpus by different code paths), the proposal's minima are not in the solve's
   units and the proposal is not shipped until that is reconciled.
6. **Budgets.** 30, 30, 60 and 180 seconds are first numbers. A cold record build runs
   `sidecar.verify` (it hashes three tables) and `build_team_match_table` for one window; whether
   that fits inside 30 seconds, and the peak memory, are measured at E-10's results commit (8.5).
7. **A floor for printing shares.** A share from three prior matches is printed with its sample.
   Should shares print only from `minimum_prior_matches` (8) valid prior matches, as E-10 predicts
   only from eight?
8. **"What the team did" beyond E-10.** Only E-10's own-actions group is shown for it. The team's
   own entries by lateral third would be the same event sets with side `for`; they are not shown
   because no protocol registers them. Should a later protocol register them?
9. **The audit frame.** `build_team_match_table` returns per-match drop counts at sentinels and
   out-of-range locations. Should the record show, per team, how many of its prior entries were
   dropped for a location, as a sample note?
10. Moved to the root as R-3; ruled by ROOT 2.12 N4 (Root rulings).
11. **A second window.** Should a later release show a record in `all_states`, and under which
    identity: a fingerprint E-10 never froze (WP A's payload with that window), or none? Any such
    record is a definition no registry record names (1.3).

## Review record

Three adversarial reviews of the first draft (18 October 2026): constitution (C, 29 findings),
product (P, 24) and exactness and data (E, 19). Each finding was checked against this file, the
E-10 draft and the tree at `52bdc0b` before its disposition. "Accepted" means applied as the
reviewer proposed; "accepted, modified" means the defect is fixed by a different change, named;
"partially accepted" means part of the proposal is applied and the rest is rejected with the
reason given. No finding was found to be false. The dispositions below name R-1 to R-5 as the
questions were put to the root; ROOT 2.12 has since ruled them (N1 to N6, recorded under Root
rulings).

| # | Sev | Finding (short) | Verified by | Disposition and where |
|---|---|---|---|---|
| C1 | blocker | Brief and search both serve `declared-slot`/`declared-leagues` with different values; the desk's one-key-two-values rule makes every slot request a 500 | squad_lab.py:1567-1571, transfer_lab.py:634-649 | Accepted: only `planning.declared_rows` keys and base rows are compared (a difference is INCONSISTENT); part rows carried as `{part_id}-{key}`; slot test with the real handlers (6.3.5, 6.4, 8.1) |
| C2 | blocker | The gate opens at registration, inside the window where PIPELINE 11 forbids running WP A on `data/`; route-only gate bypassed by tests; false self-description of a slow test; OPEN QUESTION 1 false | PIPELINE 2.5, 11, 13; ci.yml corpus job; pyproject `slow` | Accepted: gate inside `load_league_tables`, open only when all seven records are EXECUTED; corpus tests `skipif`; the slow `build_match` test deleted; OQ1 reworded; R-1 asks the root (0.2, 1.7, 8, 8.5, 10.4, DISSENT 1) |
| C3 | major | The import test cannot pass: every shipped router loads pandas and numpy | venv check of six routers; decision_lab.py:16 | Accepted (0.6, `test_import_reads_nothing`) |
| C4 | major | Under `all_states` the close_11v11 definition and fingerprint are served beside other counts | PIPELINE 3.1, 3.4 | Accepted, modified: `all_states` dropped from this release (a definition no record names, 1.1's own rule); OQ 11 (1.3) |
| C5 | major | The desk drops XI additions' declared rows (O12) and passes proposed minima as entered | xi_extensions.py:598-625, 738-770, 1377-1461 | Accepted, modified: the desk forms no proposal and composes no frontier or risk; ceilings' and conflict's own rows carried with prefix; common rows dropped only through `MATCH_COMMON_KEYS`, tested on sub-requests (6.1, 6.2, 6.4, 8.1) |
| C6 | major | The desk can apply a proposal never seen; Opponent Lab acceptance not bound to the proposal shown | spec 4.5, 6.2, 7.2 | Accepted: `fingerprint` and `accepted_proposal`, `PROPOSAL_CHANGED`; desk has no rules or acceptance (4.5, 5.2, 6.2, 6.4, 7.2) |
| C7 | major | Three membership headings drop `(None, False)`; non-OPTIMAL solves tokened TIME_LIMIT | solver.py:402-426; xi_extensions.py:406-416 | Accepted: `MEMBERSHIP_HEADINGS` reused, membership `null` unless OPTIMAL (5.4.3, 8.1) |
| C8 | major | Level hole rule departs from PIPELINE 12.3; PANEL_HOLES and PANEL_HEAD untrue for the level | PIPELINE 12.3, 3.8 | Accepted: `O'_u == 0` verbatim; `PANEL_HEAD_VOLUME` by kind (3.3, 5.6, 8.1) |
| C9 | major | XI_CLAIM, XI_STATUS_INFEASIBLE and XI_TIES untrue in reachable states | xi_extensions.declare; spec 5.4.3 | Accepted: XI_CLAIM reworded, `XI_STATUS_UNFIELDABLE`, `ties_text` only for OPTIMAL with a `(True, False)` row (5.4.3, 5.6) |
| C10 | major | CANNOT_SAY_OPPONENTS false and RECORD_NON_CLAIM overclaims once the estimate is shown | PIPELINE 3.8, 4.2; registry_outcomes | Accepted: both reworded as proposed (4.6, 5.6) |
| C11 | major | PROPOSAL_ACCEPTED with NOTHING_SET, "one minimum" for the wide template, progression non-claim false | spec 4.1, 5.6 | Accepted: `PROPOSAL_ACCEPTED_NOTHING_SET`, PROPOSAL_CLAIM and PROPOSAL_NON_CLAIM reworded (5.4.3, 5.6) |
| C12 | major | A served record exposes team aggregates of E-09's unregistered candidates | E-09 draft config.json (`box_shot_share`, `opp_half_defensive_actions`, `registry_candidate_subjects`) | Accepted: per-subject default withholding of S3, S4, S5 until an E-09 record exists; root ruling R-3 before registration (1.7, 2.1) |
| C13 | major | Tests assume a registry state that will not hold; e2e branches incomplete | spec 0.2, 8.1, 8.4 | Accepted: every state planted; e2e reads badges from `/api/evidence/verdicts`, branches on `record_available`, threshold 0 (8, 8.1, 8.4) |
| C14 | major | Window time and rate come from float64 yet are called exact; the oracle test cannot pass | PIPELINE 3.8, 4.1 | Accepted, modified (E2's fix): exact Fraction sum of the table's values, tied to the state within 1e-12; oracle on whole-second clocks (2.2, 4.2, 8.1) |
| C15 | minor | `figures_for` returns `Figure` objects | verdicts.py:534-536 | Accepted: `.value` with a type check (3.3, 8.1) |
| C16 | minor | PROPOSAL_CONFLICT and ENTERED_AND_PROPOSED depend on the data | spec 4.2, 4.5 | Accepted: both refused at validation (4.2, 4.5, 5.2, 8.1) |
| C17 | minor | Panel texts served when withheld; NO_EVENT untrue for the level; `offered()` unclear | spec 5.4.2, 3.2 | Accepted: `null` when withheld, NO_EVENT for compositions only, `offered` reads `verdict_for` (3.2, 5.4.2) |
| C18 | minor | Page rules contradict the panels (joins, reordering, grouping, player list) | spec 7.2-7.4 | Accepted: teams GET serves `record_request`; `GP.scenarioOptions`; `declared` served grouped; 7.4 reworded (5.3, 6.4, 7.2-7.4) |
| C19 | minor | Served strings with no constant; DATE_RULE unformatted; DATE_FORMAT unreachable | spec 5.4, 5.6 | Accepted: constants added, date checked in the validator, only formatted sentences served (5.2, 5.4, 5.6) |
| C20 | minor | Stage mapping undefined; DESK_CLAIM and DESK_NOT_STARTED untrue | runtime.ResultCache | Accepted: `DESK_STAGES`, claim built from the parts that ran, DESK_NOT_STARTED reworded, DISSENT 5 (6.1, 6.4, 6.5) |
| C21 | minor | Search summary lacks the universe's visibility statement and the cross-league flag | universe.py:123, transfer_lab.py:618-620 | Accepted (6.4, 8.1) |
| C22 | minor | Planning's `shots` item becomes false at E-10's registration | planning.py:1439-1442 | Accepted: request row in section 11 and R-5 |
| C23 | minor | The XI parity test compares fields the reply does not serve | spec 5.4.3 | Accepted: `solve_xi` spied inside the route (4.5, 8.1) |
| C24 | minor | LEVEL_DEFINITION and TEMPLATE_* restate definitions; Literals untied | spec 1.1, 5.6 | Accepted: both built from WP A and XI objects; Literal test (1.1, 4.1, 5.6, 8.1) |
| C25 | minor | Panel does not preserve world identity (R12) | snapshots.py:368-382 | Accepted: namespace and match count served (3.3, 5.4, 9) |
| C26 | minor | Window time classed OBSERVED | PIPELINE 2.3; provenance.py:75-76 | Accepted: DERIVED (1.5, 5.5) |
| C27 | minor | XI status sentences printed twice by the kit | labs-shared.js:213-218 | Accepted: `status_text` printed once, no kit status call; render check (7.2, 8.2) |
| C28 | minor | Desk mechanics: `listings.keys` is a list, ints as text, dead fallback, regret budget | planning.py:1806-1820; transfer_lab.py:827; runtime.py:139 | Accepted: `name` key entry, `str()` rule, fallback replaced by the absent-file token and UNAVAILABLE parts; risk not composed (6.3.4, 6.4, 6.6) |
| C29 | minor | Estimator ValueErrors answered as 422 | runtime.py:524-564 | Accepted: re-raised as RuntimeError (2.2, 3.3, 5.7, 8.1) |
| P1 | blocker | Same as C1 | as C1 | Accepted as C1 |
| P2 | major | XI additions' declared rows not a subset; the risk preference dropped; minima in force unspecified | as C5 | Accepted, modified as C5; frontier and risk not on the desk; no proposed minima reach a sub-route |
| P3 | major | XI status and membership incomplete; MODEL_INVALID tokened TIME_LIMIT | solver.py:402-426 | Accepted: as C7 and C9, and `MODEL_INVALID` its own unstored token (5.3, 5.4.3) |
| P4 | major | Every sidecar failure shows the wrong remedy ("Run the Pappalardo fetch") | labs-shared.js:207-210; sidecar.py:154 | Accepted: `_sidecar_errors` catches `SidecarMissing`; `SIDECAR_UNAVAILABLE` names the build script; the page prints it verbatim (5.3, 5.6, 7.4, 8.1, 8.4) |
| P5 | major | Same as C3 | as C3 | Accepted as C3 |
| P6 | major | The desk's apostrophe breaks byte-equal navs | labs-shared.js:30, 72; test_shell_payloads.py:59-79 | Accepted: U+2019 (7.1, 11) |
| P7 | major | "Every shipped route byte for byte" is false; nav edit needs an explicit R13 override | test_xi_extensions_render.py:843-861; W8 | Accepted: 5.8 limited to API routes; ADR-0032 carries the override; R-4 (5.8, 11) |
| P8 | major | Same as C13 (tests pinned to today's registry) | as C13 | Accepted as C13 |
| P9 | major | Opponent e2e fails in the withheld state; no timeouts | playwright.config.js:25 | Accepted: branched on `record_available`, timeouts as squad.spec.js (8.4) |
| P10 | major | Desk e2e expects outcome groups defaults cannot produce; no timeouts | transfer_lab.py:547-549; ROOT 3b | Accepted: deficiency declared by presets, branched on the served state (8.4) |
| P11 | major | Slow tests have no code gate; one bypasses the route gate | ci.yml; spec 8.5 | Accepted as C2 (8, 8.5) |
| P12 | minor | Stage-to-part mapping undefined | spec 6.1 | Accepted as C20 |
| P13 | minor | Summary rows misread replies (lineup vs 7.4, `listings.keys`, null statement, ints) | planning.py:1806-1820; transfer_lab.py:548-586 | Accepted (6.4, 7.4) |
| P14 | minor | The desk page cannot declare most DeskRequest fields | spec 6.2, 7.3 | Partially accepted: per-match minima, locks, exclusions, rules, acceptance, frontier and risk removed from the request; the planning fields of `PlanningInputs` kept API-only, every one reached by `test_parts_run_when_declared`, and listed in KNOWN_LIMITATIONS. Not removed, because `DeskRequest` is `PlanningInputs`, which the desk passes unchanged so a desk request can state any Squad Lab problem (6.2, 8.1, 11) |
| P15 | minor | Render digit rule fails on percentiles, stress sizes and minutes | spec 7.2-7.4 | Accepted: option texts and `minutes_text` served as strings (5.4, 6.2, 7.4) |
| P16 | minor | Same as C14 | as C14 | Accepted as C14 |
| P17 | minor | Proposal ledger not rendered; decision-point join forbidden by 7.4 | spec 7.2 | Accepted: proposal ledger; resolved decision points with bodies (5.3, 7.2) |
| P18 | minor | Overrun is one build per cold part; DESK_NOT_STARTED untrue | runtime.py docstring; squad_lab `_storable` | Accepted (6.3.3, 6.5, 11) |
| P19 | minor | A cold XI request hands the solver little time and reads not certified | runtime.Budget | Accepted, modified: the solve keeps XI Lab's 15-second limit (exactly `decision_lab.solve`'s call); budget 60, measured (5.1, 5.4.3) |
| P20 | minor | `test_shell_render.py` pins its own nav literal; editing it is needless | test_shell_render.py:312-350 | Accepted: removed from section 11 |
| P21 | minor | DATE_FORMAT unreachable, DATE_RULE unformatted, missing constants | spec 5.2, 5.6 | Accepted as C19 |
| P22 | minor | Same as C22 | as C22 | Accepted as C22 |
| P23 | minor | One missing league takes down the desk; the fallback token is dead | transfer_lab.py:818-830 | Accepted: a later part's 503 is UNAVAILABLE; token records absent files (6.3.4, 6.6) |
| P24 | minor | `figures_for` objects; byte-for-byte part test needs a cache hit | verdicts.py:534-536; runtime.Budget.report | Accepted: `.value`; comparison after removing `elapsed_seconds` (3.3, 6.3.1, 8.1) |
| E1 | major | Same as C4 | as C4 | Accepted, the reviewer's simpler alternative: `all_states` dropped (1.3) |
| E2 | major | Window time and rate not exact; threshold boundary fails | Python check of float sums; PIPELINE 4.1 | Accepted as proposed (2.2, 4.2, 8.1) |
| E3 | major | The loader restates the research runner's frame preparation with no tie | PIPELINE 7.4, 0 | Accepted: data-free parity test and its slow twin; `SIDECAR_EVENT_COLUMNS` from WP A (2.1, 8.1, 8.5) |
| E4 | major | No test could catch a wrong interval mapping | spec 3.3, 8.1 | Accepted: `test_world_weights_reach_rows_by_game_id` (3.3, 8.1) |
| E5 | major | The template-to-requirement mapping is untested against WP A's mirror | PIPELINE 3.4; historical.py:148 | Accepted: `test_templates_follow_the_descriptor_mirror` (4.1, 8.1) |
| E6 | major | The desk serves enough to bound a record's share | spec 6.4 | Accepted: proposals removed from the desk; OQ3 withdrawn; DISSENT 5, R-2 (6.4) |
| E7 | minor | Same as C15 | as C15 | Accepted as C15 |
| E8 | minor | Same as C7 | as C7 | Accepted as C7 |
| E9 | minor | Same as C8 (level holes) | as C8 | Accepted as C8 |
| E10 | minor | LEVEL_DEFINITION is new prose; the level has no fingerprint in WP A | PIPELINE 3.1 | Accepted: template of WP A fields; primary's fingerprint as `counts_fingerprint` (1.1, 5.5, 9) |
| E11 | minor | The record computes `O_u` itself; "once per subject" ambiguous | spec 2.2 | Accepted: tied to `shape_estimate(...).observed[u]`; one call per composition subject (2.2, 8.1) |
| E12 | minor | "No count" yet `count: int` prints "0 of 0" | spec 1.4, 2.2 | Accepted: `count` and `events` `None` with no valid prior match (1.4, 2.2, 2.3) |
| E13 | minor | `MatchUsed.date` format and order unspecified | PIPELINE 2.2, 4.1 | Accepted: the normalised day, sorted by (day, game id), tested (2.2, 8.1) |
| E14 | minor | Copy hard-codes config values | spec 5.6 | Accepted: templates filled from the constants, tested (3.1, 5.6) |
| E15 | minor | Same as C2 for slow tests | as C2 | Accepted as C2 |
| E16 | minor | Same as C5 for the XI additions | as C5 | Accepted as C5 |
| E17 | minor | Same as C26 | as C26 | Accepted as C26 |
| E18 | minor | The cut-value grep would hit the oracle | spec 10.2, 0.1 | Accepted: grep scoped; oracle import test (0.1, 8.1, 10) |
| E19 | minor | Same as C29 | as C29 | Accepted as C29 |

Totals: 3 blockers (3 accepted; P1 shares C1's fix), 28 majors
(28 accepted; 4 by a different fix: C4, C5, C14, P2), 41 minors (40 accepted, 1 partially
accepted: P14; 1 by a different fix: P19). None rejected outright. Duplicates across reviews are
counted once per review.
