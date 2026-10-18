# Opponent Lab and Director's desk specification

Build contract for the last two surfaces of ROOT-DECISIONS 2.3: Opponent Lab at `/opponent`
(the prior-date record of what a team did and what was done against it, each descriptor
badged with its E-10 verdict, and an optional HEURISTIC requirement proposal the user must
accept before it changes an XI solve) and the Director's desk at `/desk` (the chain of ROOT 2
end to end, one evidence ledger, and the "not measured here" panel). The binding rules are
ROOT-DECISIONS sections 0, 1 (R1-R13), 2.3, 2.5 (O12, O13, H14-H21), 2.6, 2.9 (Z1-Z5), 2.10, 3b
and 4; ADR-0018 to ADR-0030; KNOWN_LIMITATIONS. The E-10 protocol draft
(`protocol-drafts/E-10-conceded-shape/`, READY, not registered) already fixes the product-side
team modules (PIPELINE sections 2 and 3) and the served panel (PIPELINE 12.3); this file reuses
them by name and never redefines them. Where this file and those rules, the E-10 draft or the
shipped code disagree, they win and the disagreement is a defect to report (ROOT 2.6). Points
where this file departs from a ruling's wording are under DISSENT.

**Status.** Draft by the Opponent/desk designer, 18 October 2026. Not yet attacked or audited.
Nothing built. Every claim about the shipped code was read from the tree at `c74c676`; line
numbers refer to it. The public corpus was not present when this was written (`data/public/` is
empty), so no number below was computed on it, and none may be computed on it for this work
before E-10 is registered (1.7).

**What these surfaces are.** The third kind of deliverable ROOT section 0 allows: product
surfaces that render exact computation and the verdicts of preregistered research, and say what
is unmeasured. They add no construct and no empirical claim. Four kinds of number appear, each
with its own class (1.5): counts of recorded events (OBSERVED) and their shares and rates
(DERIVED), which are the record; the E-10 estimate, which exists only where an E-10 record is
ESTABLISHED and only behind an opt-in (EXPERIMENTAL); the minima a requirement proposal sets
(HEURISTIC, the user's declared policy); and the XI solve and its exact additions (exact
computation on the declared model, as XI Lab). The desk composes the replies of the pages that
compute them and computes nothing of its own but the composition.

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
| ROOT 3b | `galactico/models/opponent/` is the prior-date opponent record; `api/opponent_lab.py`, `api/desk.py`, `web/opponent.html`, `web/desk.html`; the root registers the routers |
| E-10 PIPELINE 12.3 | when the estimate is shown, how it is computed, the proposal qualifiers, the tests the module carries |
| E-10 PIPELINE 13 (last paragraph) | while `planning_research_sentence` is served, the desk shows no E-10 descriptor or volume |

## 0. Files and ownership

### 0.1 New files

| File | New | Owner | Content |
|---|---|---|---|
| `galactico/features/team/descriptors.py`, `match_table.py`, `estimator.py`, and `tests/test_team_descriptors.py`, `tests/test_team_match_table.py`, `tests/test_team_estimator.py` | yes, if absent | E-10 WP A (PIPELINE section 0) | exactly PIPELINE sections 2 and 3, and the WP A rows of its section 9. This file adds nothing to them, renames nothing and requires no function they do not already specify. `galactico/features/team/__init__.py` exists, empty, and stays as WP A leaves it |
| `galactico/models/opponent/record.py` | yes | OPP-R | the league team-match tables loader and the prior-date record (section 2) |
| `galactico/models/opponent/panel.py` | yes | OPP-R | E-10's served computation and the constants PIPELINE 12.3 puts in "the Opponent Lab module" (section 3) |
| `galactico/models/opponent/proposal.py` | yes | OPP-P | the declared proposal policy and its evaluation (section 4). `galactico/models/opponent/__init__.py` exists, empty, and stays empty |
| `galactico/api/opponent_lab.py` | yes | OPP-P | router, request models, gated loaders, envelopes, ledger, copy (section 5) |
| `galactico/api/desk.py` | yes | DESK | router, request model, composition, envelope, copy (section 6) |
| `web/opponent.html`, `web/opponent.js`, `web/opponent.css` | yes | OPP-P | the Opponent Lab page (section 7.2) |
| `web/desk.html`, `web/desk.js`, `web/desk.css` | yes | DESK | the desk page (section 7.3) |
| `tests/opponent_oracle.py` | yes | DESK (it implements neither the record nor the proposal) | an independent recount of the record and the rule evaluation from synthetic event lists, plain loops and `fractions.Fraction`; imports nothing from `galactico` (ROOT 4, M-01). Not collected by pytest |
| `tests/test_opponent_record.py`, `tests/test_opponent_panel.py` | yes | OPP-R | section 8 |
| `tests/test_opponent_proposal.py`, `tests/test_opponent_api.py`, `tests/test_opponent_render.py` | yes | OPP-P | section 8 |
| `tests/test_desk_api.py`, `tests/test_desk_render.py` | yes | DESK | section 8 |
| `tests/test_opponent_desk_pages.py` | yes | DESK | page anatomy of both pages (section 8.3) |
| `e2e/opponent.spec.js`, `e2e/desk.spec.js` | yes | OPP-P, DESK | section 8.4 |
| `docs/research/north-star/OPPONENT-DESK-SPEC.md` | yes | this designer | this file |

Three builders (OPP-R, OPP-P, DESK) work in parallel against the dataclasses of sections 2 to 4
and the envelopes of sections 5 and 6. OPP-P and DESK build against stub records until OPP-R
lands. Nobody here writes WP A: if WP A is absent when this work starts, it is built by E-10's
WP A owner from PIPELINE sections 2, 3 and 9 and nothing else (0.2).

### 0.2 Order of work

1. E-10 is registered (its PIPELINE section 13: the four files, the seven `PENDING` records).
2. E-10's pipeline commit lands WP A to D (PIPELINE section 13, "After registration"). WP A is
   then on disk, frozen with the registered PIPELINE.
3. This work is built on WP A, unit-tested on synthetic tables only, reviewed against section 10,
   and the root registers the two routers and the two nav entries in one commit (section 11).

Step 3 never runs a record on the real corpus before step 1 (1.7). The pages may ship before
E-10 has run: every badge then reads `E-10 · RECORD ONLY · NOT RUN`, which is the state the
registry gives, and the page says so (1.6). A different order (WP A or this work before E-10's
registration) needs a root ruling; OPEN QUESTION 1 states the case and the code gate of 1.7
keeps it safe either way.

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
`galactico/api/runtime.py` (one optional change: the source fingerprint), every top-level `*.md`,
`ROOT-DECISIONS.md`, `docs/research/north-star/README.md`.

### 0.5 Reused, unchanged

| Reuse | From | How |
|---|---|---|
| `TEAM_DESCRIPTORS`, `LEVEL_SUBJECTS`, `WINDOWS`, `required_columns`, `REGULATION_PERIODS`, `DISMISSAL_CARDS`, `GOAL_INCIDENT_COLUMNS`, `WY_LOCATION_SENTINELS`, `COORDINATE_RANGE`, `EXPOSURE_UNIT_SECONDS`, `TeamDescriptorSpec.describe`, `.part_names`, `.parts`, `.fingerprint`, `.label`, `Window.phrase` | `features/team/descriptors.py` (PIPELINE 3.1-3.7) | every definition, label, sentence, part phrase, window and constant the pages show or the record passes |
| `build_team_match_table`, `TEAM_MATCH_VERSION` | `features/team/match_table.py` (PIPELINE 2.1-2.4) | the league team-match tables, `xt=None` |
| `descriptor_rows`, `state_at`, `shape_estimate`, `level_estimate`, `served_composition`, `served_volume`, `LEAGUE_PRIOR_PSEUDOCOUNT_PER_PART` | `features/team/estimator.py` (PIPELINE 3.8) | the record's counts (2.2) and the served panel (3.3); imported as `from galactico.features.team import estimator` and called as `estimator.<name>` |
| `league_world_weights` | `optimization/snapshots.py:368-382` | the panel's worlds (PIPELINE I12) |
| `load_public`, `TABLES` | `storage/public.py:49, 97-158` | the actions, matches and teams frames |
| `verify`, `load`, `attach`, `provenance`, `SIDECAR_ROOT`, `SidecarMissing`, `SidecarStale`, `SidecarMismatch` | `ingestion/sidecar.py:95, 158-163, 907-1010` | cards, own goals, goals, the sheet's scores and dismissals (PIPELINE I2-I6) |
| `verdict_for`, `figures_for`, `record`, `VERDICTS`, `as_payload` | `domain/verdicts.py:272-536` | badges, gates, figures |
| `nav_markup`, `NOT_MEASURED`, `not_measured_payload`, `NotMeasured`, `evidence_payload`, `verdict_payload`, `declared_row`, `ledger_row`, `visible_text` | `api/shell.py` | page furniture, badges, ledger rows |
| `Budget`, `lab_errors`, `cache_key`, `RESULTS`, `is_complete`, `finalize`, `respond`, `dumps`, `HOSTED_PROVIDERS`, `match_scenario` | `api/runtime.py` | every rule of a new route (ADR-0024) |
| `_built_once`, `_corpus_files`, `_digest`, `_minimum_text`, `_outward`, `INTEGER_ONLY`, `StrictId`, `League`, `LEAGUE_LABELS`, `FLAGSHIP`, `PlanningInputs`, `resolve_or_404`, `canonical_request`, `corpus_token`, `clubs`, `league_clubs`, `catalogue`, `verdict_reading`, `not_measured`, `NOT_MEASURED_CLOSING`, `SCOPE_TEMPLATE` | `api/planning.py` | the build gate, the corpus identity of a key, printed minima, the desk's planning declarations and research block. The private ones are pinned by name and signature in the API tests, as OR-XI pinned `_built_once` (OR-XI 0, "Reused") |
| `SCENARIOS`, `decision_inputs`, `DecisionRoute`, `SolveRequest`, `SEED` (via `historical`) | `api/decision_lab.py` | the two decision points, XI Lab's model, the 422 shape |
| `XIDeclarations`, `RequirementId`, `SIDE_REQUIREMENTS`, `declare`, `_match_snapshot`, `_exact_sum`, `_lineup_rows`, `OPT_IN_LABEL`, `EXPERIMENTAL_OPT_IN_ERROR`, `UNKNOWN_PLAYER` | `api/xi_extensions.py:154-195, 375-384, 440-447, 540-640` | the decision-point request fields, the opt-in rule applied to XI Lab's model, the gated match snapshot, exact sums and lineup rows; private names pinned by test |
| the handler functions `squad_snapshot`, `squad_reference`, `squad_depth`, `squad_stress`, `squad_brief`, `transfer_injection`, `ceilings_route`, `conflict_route`, `frontier_route`, `risk_tail_route`, `risk_regret_route` and their request models | `api/squad_lab.py`, `api/transfer_lab.py`, `api/xi_extensions.py` | called in process by the desk (section 6); the names are the module attributes `@router.post` returns. The builder confirms each name against the tree and the desk test pins them |
| `solve_xi` | `optimization/xi/solver.py:81-97` (frozen) | one call per `/api/opponent/xi` request, with the arguments `decision_lab.solve` passes (5.4.3) |
| `declared_minimum`, `load_league_reference`, `PERCENTILE_MENU` | `optimization/reference.py:67, 374-416` | the proposal's minima (4.3) |
| `format_plain` | `domain/precision.py:95` | every number a reader entered, as entered |
| `window.Shell`, `window.GP` | `web/labs-shared.js`, `web/planning.js` | badges, ledger cells, errors, not-measured, research block |

### 0.6 Engineering (ROOT section 4)

`from __future__ import annotations`; frozen dataclasses; full type hints; `__all__`; ruff clean at
line length 100 (E, F, I, UP, B, SIM); a module docstring whose first paragraph states the claim
and the non-claim. No module here imports `galactico.validation`, `experiments` or the
licensed-corpus reader `sb_reader` (`tests/test_research_firewall.py:27` already lists `models` and
`features` as product code). The routers read no data and import no solver, pandas, numpy or WP A
module at import: every such import is inside a function, and a subprocess test asserts it (8.1).
No function takes a default for a value E-10's config holds (PIPELINE section 0, "Engineering"):
those are module constants tied to the config by test (3.1). No process over about 1.5 GB; Parquet
read with a column list. Tests skip cleanly without the corpus.

## 1. Shared definitions

### 1.1 Subjects, groups and the one definition

Seven subjects, in `subject_groups` order (config.json:207), are the only quantities Opponent Lab
shows as a record. Each is the object of WP A: its label is `spec.label` (or
`LEVEL_SUBJECTS[...].label`), its definition is `spec.describe()` (byte-equal to
`descriptor_test_vectors.json`, PIPELINE 3.6), its parts and part phrases are `spec.parts`, its
window is `spec.window`. This file writes none of them again.

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
would be a definition no protocol registers (OPEN QUESTION 8). The level has no `describe()`;
its definition is the constant `LEVEL_DEFINITION` (5.6), which names the primary's label and the
window phrase and adds nothing to them.

### 1.2 Decision date and the prior rule

A decision date `D` is spelled `YYYY-MM-DD` and nothing else (ADR-0021), is a real calendar day,
and lies from `RECORD_FIRST_DATE` = `"2017-07-01"` to `RECORD_LAST_DATE` = `"2018-07-01"`
inclusive (E-10 `season_start` and `end`, tied by test). Matches on calendar dates strictly
before `D` are used; the whole calendar day of `D` is excluded (`prior_rule`
`calendar_date_strictly_before`). The rule has one implementation, `estimator.state_at`, which
normalises `D` and every row's date to the day (PIPELINE 3.8, 559-564). The record's counts are
read from the state it builds (2.2); the list of matches used is a second view of the same rows
and a test ties it to the state (8.1). A decision point of XI Lab fixes `D` to its scenario's
`cutoff` (`decision_lab.SCENARIOS`, decision_lab.py:44-57: `2018-05-06`, `2018-04-08`), which is
the match day: the match itself is excluded.

### 1.3 Windows

`close_11v11` (default; E-10's `window_primary`) and `all_states` (E-10's `window_sensitivity`),
both `descriptors.WINDOWS`, phrases as WP A writes them. E-10 registers its definitions in
`close_11v11` only (the window token is in every fingerprint payload, PIPELINE 3.6), so under
`all_states` a subject is a different definition: its badge is the unregistered one,
`verdict_for("none", f"{subject}-all-states")` (`RECORD ONLY · NOT TESTED`, "No registered
protocol tests this claim."), the record prints `ALL_STATES_NOTE`, and no estimate is offered.
The experiment id `"none"` is the planning precedent for a quantity no protocol names
(planning.py `_NO_PROTOCOL`).

### 1.4 Validity and the matches used

Validity is `match_validity`'s, decided once per match and never repaired (PIPELINE 2.4). An
invalid match adds nothing to any count or window time (`estimator.add_rows` selects valid rows,
PIPELINE 3.8) and is listed among the matches used with its first reason, in words (5.6,
`INVALID_*`). Its sheet result is still printed. A team with no valid prior match has no count:
every share and the rate are `null`, never 0, and the record prints `NO_PRIOR_MATCH`.

### 1.5 Evidence classes (O13)

| Quantity | Class | Why |
|---|---|---|
| a count of recorded events, valid matches, window time | OBSERVED | the provider's events, tags and sheet, counted (`product_rules.evidence_class_of_record.counts`) |
| a share of a descriptor's parts; the level's rate per 90 minutes of window time | DERIVED | a count ratio (`...shares_and_rates`) |
| the E-10 estimate (3.3) | EXPERIMENTAL | `product_rules.evidence_class_of_panel` |
| a minimum a proposal sets | HEURISTIC, composed with the requirement's class (progression HEURISTIC; the side requirements EXPERIMENTAL, ADR-0019) and the cited record's class | `product_rules.proposal_class`; a percentile chosen as a minimum is a declared policy (`reference.DeclaredMinimum.evidence_class`) |
| the XI solve, ceilings, conflict, frontier, risk | as XI Lab and OR-XI 7.6 compose them | `evidence.from_xi` of each requirement in force, `evidence.SOLVER_CLASS`, eligibility HEURISTIC |

Composition is `weakest()` through `shell.evidence_payload`. `DECLARED` is never a class (O12):
team, date, window, decision point, rules, thresholds, percentiles, acceptance, minima entered,
locks, exclusions, opt-ins and the slot are declared rows.

### 1.6 Verdict states and their product consequence (fixed by the E-10 draft)

Every badge, statement and gate comes from `verdicts.verdict_for("E-10", subject)` through
`shell.verdict_payload`. The record is shown in every state that 1.7 allows; nothing else is.

| Registry state of the subject (window `close_11v11`) | Badge (`badge_text`) | Shown beyond the record | Evidence class |
|---|---|---|---|
| no record (E-10 not registered) | `RECORD ONLY · NOT TESTED` | nothing; the record itself is withheld (1.7) | (none shown) |
| `PENDING` | `E-10 · RECORD ONLY · NOT RUN` | nothing | counts OBSERVED, shares and rates DERIVED |
| `INCONCLUSIVE` | `E-10 · INCONCLUSIVE` | nothing | same |
| `ADDED_INFORMATION_NOT_SHOWN`, `SIDE_NOT_SHOWN`, `NOT_RELIABLE`, `STRENGTH_NOT_EXCLUDED` (NOT_ESTABLISHED) | `E-10 · TESTED · NOT ESTABLISHED` | nothing | same |
| `DEFENDER_SHAPE_SIGNAL` (ESTABLISHED, limits) | `E-10 · TESTED · TENDENCY, ONE SEASON` | behind the opt-in, at `D` on or after `2018-01-01`, window `close_11v11`: the estimate of 3.3, the point only when the `reliability_lower_bound` figure is at least 0.70 | EXPERIMENTAL for the estimate; the record keeps its classes |
| `LEVEL_ESTABLISHED` (level, ESTABLISHED, limits) | `E-10 · TESTED · VOLUME, ONE SEASON` | the same rule for the volume | same |

The statement printed beside each badge is the payload's `statement`, verbatim (the registry's
`registry_outcomes` sentence, `not_run_statement`, or "No registered protocol tests this
claim."). The group's non-claim (`registry_non_claims[group]`, config.json:498-502) is printed
in every state, before registration included: the page prints it from the server field
`groups[].non_claim`, which `panel.REGISTRY_NON_CLAIMS` supplies, never from `Shell.verdictLines`
(which prints a non-claim only when ESTABLISHED, labs-shared.js:147-154). Once a record exists, a
test asserts its `non_claim` equals the constant (PIPELINE 12.3). `lifecycle_status` is read by
nobody here: a NOT_ESTABLISHED or INCONCLUSIVE token never removes the record, it only never
unlocks the estimate. No LOCAL replication label exists or is shown (Z5).

### 1.7 The registration gate (R5)

Before E-10's registration commit, nothing in this work computes a descriptor column on the real
corpus: not a route, a test, an e2e spec, a screenshot or a person looking at a page. The reason
is R5: E-10 is a prospective plan on reused data, its prior-exposure table states that no
conceded split by lateral third, no defensive-action location and no team-season composition has
been served (preregistration.md:80), its criterion (f) rests on three leagues that carry no such
exposure, and its own real-data oracle may run only after registration and computes no
descriptor (PIPELINE 2.5, 278-279). A served record of every team of five leagues at every date
is exactly those compositions.

The gate is in code, not only in the order of 0.2. `record.record_available()` is true when, and
only when, `verdicts.VERDICTS` holds a record for each of the seven subjects under
`registry_experiment_id` `"E-10"`. While it is false:

- `POST /api/opponent/record` answers 200 with `record_state` `"WITHHELD"`, the seven
  definitions and their badges (`RECORD ONLY · NOT TESTED`), every group's non-claim and
  `RECORD_WITHHELD`, and no count. It computes no descriptor column: the league tables loader is
  never called (a test patches it to raise). Only the match and team tables are read, to name the
  team (5.2), which is no quantity E-10 tests.
- `POST /api/opponent/proposal` answers 200 with `proposal_state` `"WITHHELD"` and
  `PROPOSAL_WITHHELD`; `POST /api/opponent/xi` with `accept: true` is a 422
  (`ACCEPT_WHILE_WITHHELD`), and with `accept: false` solves the XI under the minima entered or
  the defaults, its proposal block `WITHHELD`.
- the desk's per-match chain runs as the line above says.

After registration the gate is open for good (a registry record is never removed). The gate reads
only the registry, the one thing product code may read from research.

## 2. The prior-date record: `galactico/models/opponent/record.py`

Module docstring: claim = counts of E-10's declared event sets in a team's league matches before a
date, for and against, in a declared window, read from the one estimator's state, and their
shares and rate; non-claim = no tendency, no adjustment for opponents or strength, no statement
about how well a team defends, no order of teams.

### 2.1 The league tables

```python
RECORD_VERSION = "opponent-record-v1"
LEAGUES: tuple[str, ...] = ("Spain", "England", "Italy", "Germany", "France")  # = config leagues
ACTION_COLUMNS: tuple[str, ...]  # = PIPELINE I1, verbatim
SIDECAR_EVENT_COLUMNS = ("card", "own_goal", "goal_on_scoring_event")

class RecordCorpusDefect(RuntimeError): ...   # a corpus that cannot give a table; the router's 503

@dataclass(frozen=True)
class LeagueTables:
    league: str
    tables: Mapping[str, pd.DataFrame]   # window key -> the table of PIPELINE 2.2
    team_ids: tuple[int, ...]            # sorted ids of every team with a row
    team_names: Mapping[int, str]
    provenance: Mapping[str, object]     # sidecar.provenance(league), TEAM_MATCH_VERSION,
                                         # descriptor fingerprints, public file identity

def load_league_tables(league: str) -> LeagueTables: ...
def record_available() -> bool: ...      # 1.7
```

`load_league_tables` reads, in this order and nothing else: `load_public(league, tables=("actions",
"matches", "teams"), action_columns=ACTION_COLUMNS)`; `sidecar.verify(league)`;
`sidecar.load(league, "events", columns=["event_id", *SIDECAR_EVENT_COLUMNS])` and
`sidecar.attach(actions, events, SIDECAR_EVENT_COLUMNS)` (I2, I3); `sidecar.load(league, "matches",
columns=["game_id", "home_score", "away_score"])` cast to `int64` as `match_meta` (I4; coach ids
are not read); `sidecar.load(league, "squads", columns=["game_id", "team_id", "player_id",
"red_minute"])` reduced to `sheet_dismissals` exactly as I5 says. A team-match of `matches` with no
`squads` row, a duplicate `game_id`, or any `ValueError` that `build_team_match_table` raises on
these frames is a property of the corpus, not of a request: the function raises
`RecordCorpusDefect` with the cause, so it is never answered as a 422 (`runtime.lab_errors` turns a
`ValueError` into one). Then, for each window of `descriptors.WINDOWS`,
`build_team_match_table(actions, matches, columns=required_columns(TEAM_DESCRIPTORS.values()),
window=WINDOWS[key], match_meta=..., sheet_dismissals=..., regulation_periods=REGULATION_PERIODS,
dismissal_cards=DISMISSAL_CARDS, sentinels=WY_LOCATION_SENTINELS,
coordinate_range=COORDINATE_RANGE, xt=None)`, the constants of `descriptors.py` (PIPELINE 2.1,
"Callers in product code pass the constants"). No xT surface is fitted: no descriptor reads one,
and `match__positive_xt_gain` is an oracle aid only. The action frame is dropped before return; the
tables hold one row per team and match. The audit frame is not kept (OPEN QUESTION 9).

### 2.2 The record

```python
@dataclass(frozen=True)
class PartRecord:
    part: str; phrase: str
    count: int
    share: Fraction | None            # None when the subject's events are 0

@dataclass(frozen=True)
class SubjectRecord:
    subject_id: str; group: str; kind: str      # "composition" | "level"
    label: str; definition: str; fingerprint: str
    parts: tuple[PartRecord, ...]               # () for the level
    events: int                                 # the parts' counts added
    window_seconds: Fraction                    # the team's valid prior window time
    rate_per_90: Fraction | None                # level only; None with no window time

@dataclass(frozen=True)
class MatchUsed:
    game_id: int; date: str; opponent_id: int; opponent_name: str
    is_home: bool; goals_for: int; goals_against: int
    valid: bool; invalid_reason: str; window_seconds: Fraction | None

@dataclass(frozen=True)
class OpponentRecord:
    league: str; team_id: int; team_name: str; date: str; window: str
    valid_matches: int; invalid_matches: int
    matches: tuple[MatchUsed, ...]              # date order, then game id
    subjects: tuple[SubjectRecord, ...]         # subject_groups order

def build_record(tables: LeagueTables, *, team_id: int, date: str, window: str) -> OpponentRecord
```

`build_record` reads no file. For each composition subject: `rows =
estimator.descriptor_rows(tables.tables[window], spec, league=tables.league,
exposure_unit_seconds=EXPOSURE_UNIT_SECONDS)`; `state = estimator.state_at(rows,
team_ids=tables.team_ids, parts=spec.part_names, date=date, weights=np.ones(len(rows)))`; with
`u` the team's index, the part counts are `state.counts[:, u, :, :].sum(axis=(0, 1))` (the
estimator's `O_u`, PIPELINE 4.2) and the exposure is `state.exposure[:, u, :].sum()`. Counts are
integers held in `float64` by the state; each is converted with a check that it is a whole number
(a non-integer is a `RuntimeError`, a fault). The level uses the primary's rows: its count is the
primary's `events`, its rate `events / exposure` with exposure in units of
`EXPOSURE_UNIT_SECONDS` (5,400 seconds, 90 minutes), `None` when the exposure is 0.
`window_seconds = Fraction(exposure) * EXPOSURE_UNIT_SECONDS`. A share is
`Fraction(count, events)`. No quantity of 4.2 is computed here: the record is the state's
marginal for one team, so the record and the panel read one state built by one function.

`matches` lists every row of the team's table with a normalised date before `D`, valid or not.
Its date rule restates the prior rule for display only; `test_matches_used_agree_with_the_state`
(8.1) asserts that the per-part counts added over the listed valid matches equal the state's, for
`D` given as a date and planted rows on `D`'s day and later.

### 2.3 Texts

Every text is a pure function of a record, built in the router (5.4), never in the page.

| Text | Rule |
|---|---|
| `count_text` | `"{count} of {events}"`, integers with thousands separators |
| `share_text` | the share as a percentage at one decimal, rounded half-even from the exact `Fraction` (`"38.0%"`); `null` when the share is `None` |
| `events_text` | `"{events} events"` |
| `minutes_text` | window time in whole minutes, rounded half-even from the exact `Fraction`, thousands separators (`"2,314"`) |
| `rate_text` | the rate at two decimals, rounded half-even, then `" per 90 minutes of window time"`; `null` when `None` |
| `sample_text` | `SAMPLE_TEXT` with events, valid matches and minutes |
| `goals_text` | `"{goals_for}–{goals_against}"`, the match sheet's full-time result (PIPELINE 2.2), with the venue word |

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

`test_opponent_constants_equal_the_config` reads `experiments/preregistered/E-10-conceded-shape/
config.json` when it exists and the draft `docs/research/north-star/protocol-drafts/
E-10-conceded-shape/config.json` otherwise, and asserts each constant equals its key, and
`record.LEAGUES == config["leagues"]`. `PRODUCT_RULES["words_never_on_the_page"]` is in the module
and is never served outside a provenance block: all five words are copy-guard tokens
(labels.py:25), so a served copy would be refused by `finalize`. The estimator's
`LEAGUE_PRIOR_PSEUDOCOUNT_PER_PART` is the estimator's constant (PIPELINE 3.7), not restated here.

### 3.2 When the estimate is offered

`offered(subject, *, window, date) -> bool` is true when, and only when, all hold: the subject's
verdict has `may_gate` true (PUBLIC, EXECUTED, ESTABLISHED; verdicts.py:452-487), `window ==
"close_11v11"`, and `date >= PANEL_FROM_DATE`. It is shown when it is offered and the request
carries `panel_opt_in: true` (`product_rules.panel_needs_opt_in`). Nothing else gates it, and a
LOCAL label never does (ADR-0018). In every other case the record is shown with
`PANEL_NOT_OFFERED`, `PANEL_BEFORE_DATE` or `PANEL_WINDOW_ONLY` as its reason, chosen in that
order of the three conditions. With today's registry `offered` is false for every subject.

### 3.3 The computation (PIPELINE 12.3, verbatim in substance)

```python
@dataclass(frozen=True)
class PanelEstimate:
    subject_id: str; kind: str
    point: tuple[float, ...] | float | None     # None when the point is withheld (below)
    interval: tuple[tuple[float, float], ...] | tuple[float, float] | None
    shrink_weight: float
    worlds: int; holes: int; world_seed: int; world_scheme: str
    k_context: float; k_unit: float; reliability_lower_bound: float
    point_shown: bool

def estimate(tables: LeagueTables, *, team_id: int, date: str, subject: str) -> PanelEstimate
```

1. Figures: `figures = verdicts.figures_for(EXPERIMENT_ID, subject)`; `kA = figures["k_context"]`,
   `kD = figures["k_unit"]`, `rel = figures["reliability_lower_bound"]` (the level reads the level
   record's three). A missing figure is a `RuntimeError`: the results commit gives every E-10
   record under an established token its three figures (PIPELINE 12.2), so one missing is a fault.
2. Rows: `estimator.descriptor_rows(tables.tables["close_11v11"], spec, ...)`, the primary's for
   the level.
3. Point state: `estimator.state_at(rows, team_ids=tables.team_ids, parts=spec.part_names,
   date=date, weights=ones)`; `shape_estimate(state, league_pseudocount=
   estimator.LEAGUE_PRIOR_PSEUDOCOUNT_PER_PART, k_context=kA, k_unit=kD)` and
   `served_composition(est, team_id)` for a composition; `level_estimate(state,
   k_context_level=kA, k_unit_level=kD)` and `served_volume(est, team_id)` for the level. The
   first value is the point, the second the shrink weight (`O_total / (O_total + kD)`, or
   `E'_u / (E'_u + kD')`).
4. Worlds: `game_ids` = the ids of the league's **valid** matches whose normalised date is before
   `pd.Timestamp(date).normalize()`; `w = snapshots.league_world_weights(game_ids,
   SERVED_PANEL["worlds"], SERVED_PANEL["world_seed"], scheme=SERVED_PANEL["world_scheme"])`. In
   world `r`, a row's weight is `w.weights[r, j]` for its match at position `j` of `w.games`, and
   0 for a row whose match is not in `w.games`. One draw serves every subject of one request
   (validity is per match, so `game_ids` is the same for all seven): the panel's subjects share
   their worlds (R12).
5. Per world, step 3's calls with those weights. A world in which the team has no prior event
   (`O_total == 0`, or `E'_u == 0` for the level) is a hole: it is counted and left out. The
   interval of each part (or of the volume) is `np.quantile(values, SERVED_PANEL
   ["interval_quantiles"], method=SERVED_PANEL["interval_quantile_method"])` over the other
   worlds; with every world a hole there is no interval.
6. Point rule: `point_shown = rel >= PRODUCT_RULES["point_needs_reliability_lower_bound_at_least"]`;
   when false `point` is `None` and only the interval is served.
7. S5 (`high_zone_defensive_action_share`) is served as its two-part share, under its label, like
   every two-part subject; the ratio `s5_ratio_name` names is never computed, served or labelled
   (`product_rules.s5_panel_rule`); `S5_RATIO_NOTE` names it in prose.

Nothing of PIPELINE 4.2 is computed here: `pi`, `A_c^(-u)`, `e`, `delta_u`, `lam`, `rD_u` are the
estimator's (Z3; "there is no second implementation and no parity test"). Texts: a composition's
point and interval ends as percentages at one decimal, rounded half-even from `Fraction(float)`;
the volume at two decimals with `" per 90 minutes of window time"`; the shrink weight at three
decimals. Evidence `EXPERIMENTAL`; the panel prints the record's statement and the group's
non-claim.

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
    label: str                       # 5.6 TEMPLATE_*
    subject_id: str                  # the cited E-10 subject
    part: str | None                 # the cited part; None for the level's rate
    kind: str                        # "share" | "rate"
    requirement_ids: tuple[str, ...] # the measured requirements of decision_inputs it sets

TEMPLATES: tuple[ProposalTemplate, ...]
```

| `template_id` | Cites | Sets | Label (5.6) |
|---|---|---|---|
| `left-origins-from-f3-def-right` | `conceded_f3_entries_by_channel`, `def_right` | `left_pass_origins` | `TEMPLATE_LEFT_F3` |
| `right-origins-from-f3-def-left` | `conceded_f3_entries_by_channel`, `def_left` | `right_pass_origins` | `TEMPLATE_RIGHT_F3` |
| `both-origins-from-f3-wide` | `conceded_f3_entries_wide_share`, `wide` | `left_pass_origins`, `right_pass_origins` | `TEMPLATE_WIDE` |
| `left-origins-from-box-def-right` | `conceded_box_entries_by_origin_channel`, `def_right` | `left_pass_origins` | `TEMPLATE_LEFT_BOX` |
| `right-origins-from-box-def-left` | `conceded_box_entries_by_origin_channel`, `def_left` | `right_pass_origins` | `TEMPLATE_RIGHT_BOX` |
| `progression-from-f3-per-90` | `conceded_f3_entries_per_90`, rate | `progression` | `TEMPLATE_PROGRESSION` |

The frame: `def_right` is the defending team's right lateral third, which is the attacking team's
left (PIPELINE 3.4, the mirror lives in the descriptor), so a rule citing it sets the attacking
XI's left wide-channel requirement. No template cites S3, S4 or S5: no requirement XI Lab measures
corresponds to them, and inventing one is out of scope (R4). Templates are fixed in code and in the
GET menu; a template is a structure, not a number. Every number is the user's.

### 4.2 Rules and their evaluation

A rule is `{template_id, threshold, percentile}`, all three declared, none with a default (as O7
gives the frontier no default dimension): `threshold` a share in `[0, 1]` for a share template
and a rate in `[0, 1000]` per 90 minutes of window time for the rate template; `percentile` one of
`reference.PERCENTILE_MENU` (10, 25, 50, 75, 90). Each template at most once per proposal; at most
six rules. Each template's comparison is "at least"; no template compares two parts of one record,
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
`2/5`, and comparing with it would not). `value` is the record's `share` of the cited part or the
level's `rate_per_90`; when it is `None` (no event, or no window time) the state is `UNDECIDED`:
unknown is never evidence of absence (R11), and an undecided rule sets nothing. Outcomes come
back in `TEMPLATES` order whatever the request's order. `requirements_set` returns, for each
requirement set by at least one rule that holds, its percentile and the template ids that set it;
two holding rules that set one requirement at different percentiles are a `ValueError`
(`PROPOSAL_CONFLICT`): no merging rule is invented. The same percentile from two rules is one
minimum citing both.

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
is NOT_ESTABLISHED. A cited record whose `may_gate` is true needs none. Under `all_states` every
cited record is the unregistered one (1.3), so every qualifier is the first sentence. The
proposal stays HEURISTIC under every verdict (`product_rules.proposal_class`).

### 4.5 Acceptance, and how an accepted proposal enters an XI solve

A proposal is shown and changes nothing until the request that solves the XI carries
`accept: true`. Acceptance is a declaration: it is a declared row, it is in the cache key, and
the server recomputes the proposal from the declared rules on every request; no minimum the
server served is ever sent back by the page (R10). An accepted proposal enters an XI solve
through the existing XI declared-requirements path and no other: its minima are the `minimums`
argument of `decision_lab.decision_inputs(snap, formation, mode, minimums)`, the shipped function
`/api/xi/solve` calls (decision_lab.py:241-332), applied through `xi_extensions.declare` (the
opt-in rule of OR-XI 1.3), and solved by `solve_xi` with the arguments `decision_lab.solve` passes
(5.4.3). The reply prints `XI_LAB_MINIMA` with each minimum written by `format_plain`, so a reader
who types those numbers into XI Lab's minimum inputs sends `/api/xi/solve` the same floats; with
the experimental opt-in and the same locks, exclusions and mode, `test_xi_part_equals_api_xi_solve`
(8.1) asserts the lineup, status, objective and requirement assessments equal `/api/xi/solve`'s
with `bootstrap_worlds: 0`. Squad Lab's declared-requirements path
(`RequirementDeclaration(source="LEAGUE_PERCENTILE")`) is not used for a proposal in this
release: a proposal belongs to one match, and the planning point is the season's end (OPEN
QUESTION 4). A minimum the reader entered and an accepted proposed minimum for one requirement
are refused together (`ENTERED_AND_PROPOSED`).

### 4.6 What the proposal and the record cannot say

Printed on the page in every state, as server strings (5.6): `CANNOT_SAY_FUNNEL` (ROOT 2.2, H14:
funnelling and weakness are observationally confounded, so a share conceded on one side is not a
side defended badly and not a place to attack), `CANNOT_SAY_OPPONENTS` (a raw record is not
adjusted for the opponents met or for strength; E-10 tests whether the defender's own history adds
anything beyond the attacker's, and its badge says whether that was tested), `CANNOT_SAY_ORDER`,
and the proposal's `PROPOSAL_NON_CLAIM`. The five words of `words_never_on_the_page` appear
nowhere served or rendered (they are copy-guard tokens, so `finalize` and the render test both
enforce it).

## 5. API: `galactico/api/opponent_lab.py`

### 5.1 Routes

| Method | Path | Budget (seconds, local `OPPONENT_BUDGETS`) | Long | Request | Reads the corpus |
|---|---|---|---|---|---|
| GET | `/opponent` | | | | no: `FileResponse(web/opponent.html)`, `include_in_schema=False` |
| GET | `/api/opponent/menu` | | | | no (5.4.1) |
| GET | `/api/opponent/teams` | | | | match and team tables of the leagues present (`planning.clubs()`); 503 when none |
| POST | `/api/opponent/record` | `opponent.record`: 30 | no | `RecordRequest` | the league's public tables and sidecar, unless withheld (1.7) |
| POST | `/api/opponent/proposal` | `opponent.proposal`: 30 | no | `ProposalRequest` | Spain's tables and sidecar, and the league reference |
| POST | `/api/opponent/xi` | `opponent.xi`: 45 | no | `OpponentXIRequest` | as the proposal, and the match snapshot |

The budgets are local to the router, as Squad Lab's `RECORD_BUDGETS` (squad_lab.py:83) and
Transfer Lab's `UNIVERSE_BUDGET_SECONDS` (transfer_lab.py:77) are, so `runtime.BUDGETS` and its
pinned test (`tests/test_lab_runtime.py:115-128`, which asserts no key starts with `opponent` or
`desk`) do not change. No route here enumerates: one XI solve and 40 cheap estimator passes are
not what `LONG_ROUTES` names, so no route takes a long-computation place and none calls
`runtime.long_job` (which would raise `KeyError` for a route outside `BUDGETS`). The budgets are
first numbers, not measurements: the cold times and peak memory of the three POSTs are measured on
the corpus after E-10's registration and recorded in the ADR (section 11), as X5 timed the risk
routes; a budget is raised there if a measurement needs it. The router is
`APIRouter(route_class=decision_lab.DecisionRoute)`; no path collides with another router's
(`tests/test_xi_extensions_api.py:1745-1766` pattern).

### 5.2 Request models

All `ConfigDict(extra="forbid")`; integers, floats and booleans strict; floats
`allow_inf_nan=False`.

```python
WindowKey = Literal["close_11v11", "all_states"]
TemplateId = Literal["left-origins-from-f3-def-right", "right-origins-from-f3-def-left",
                     "both-origins-from-f3-wide", "left-origins-from-box-def-right",
                     "right-origins-from-box-def-left", "progression-from-f3-per-90"]
IsoDay = Annotated[str, Field(pattern=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")]

class RecordRequest(BaseModel):
    competition: planning.League
    team_id: planning.StrictId
    decision_date: IsoDay
    window: WindowKey = "close_11v11"
    panel_opt_in: StrictBool = False

class ProposalRule(BaseModel):
    template_id: TemplateId
    threshold: Annotated[float, Field(strict=True, ge=0, le=1000, allow_inf_nan=False)]
    percentile: Annotated[Literal[10, 25, 50, 75, 90], planning.INTEGER_ONLY]

class ProposalRequest(BaseModel):
    scenario_id: str = "madrid-2018-05-06"          # a key of decision_lab.SCENARIOS, else 404
    window: WindowKey = "close_11v11"
    experimental_opt_in: StrictBool = False
    rules: list[ProposalRule] = Field(min_length=1, max_length=6)

class OpponentXIRequest(xi_extensions.XIDeclarations):   # scenario_id, formation, locks,
    mode: Literal["BALANCE", "SATISFY"] = "BALANCE"      # excludes, experimental_opt_in
    window: WindowKey = "close_11v11"
    minimums: dict[xi_extensions.RequirementId, xi_extensions.Minimum] = Field(default_factory=dict)
    rules: list[ProposalRule] = Field(default_factory=list, max_length=6)
    accept: StrictBool = False
```

Model validators refuse, each with its fixed sentence and no input value: a decision date that is
not a calendar day or lies outside `RECORD_FIRST_DATE..RECORD_LAST_DATE` (`DATE_RANGE`); a share
template's threshold above 1 (`THRESHOLD_SHARE`); a template named twice (`RULE_TWICE`);
`accept: true` with no rule (`ACCEPT_WITHOUT_RULES`). Then, at declaration time, `ValueError`
(422): a side requirement in `minimums`, or a template that sets one, without the opt-in
(`EXPERIMENTAL_OPT_IN_ERROR`); `PROPOSAL_CONFLICT`; `ENTERED_AND_PROPOSED` (accepted only);
`ACCEPT_WHILE_WITHHELD`; a lock or exclusion that is not a gated candidate (`UNKNOWN_PLAYER`,
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
        tables = _league_tables(league, _sidecar_token(league))                    # gated
        ...                                                                          # 5.4
        return runtime.finalize(payload)
    data, hit = runtime.RESULTS.get_or_compute(key, compute, store=runtime.is_complete)
    return runtime.respond(data, cache_hit=hit)
```

- `_league_tables` is `@planning._built_once(maxsize=5, reads=lambda league, sidecar_token:
  (league,))` around `record.load_league_tables(league)`: one build per key, two builds at once in
  the process (shared with planning's loaders), 429 after the wait, and the public file identity
  in the build key. The sidecar's identity is the argument `sidecar_token`, so a rebuilt sidecar
  is a new key and is built again: `_files_token` covers only the public Parquet tables
  (planning.py:685-693), which is why the token is passed explicitly.
- `_sidecar_token(league)`: `planning._digest` of `[name, size, mtime_ns]` of
  `sidecar.SIDECAR_ROOT/{league}/` `MANIFEST.json`, `events.parquet`, `matches.parquet`,
  `squads.parquet`, an absent file recorded as absent (the build then raises `SidecarMissing`, a
  503). `_token(league)` is `planning._digest` of three parts: `"public"`, the present-file listing
  `planning._corpus_files((league,))` returns, raising `FileNotFoundError` (a 503) when it reports
  an absent file, as `planning.corpus_token` does; `"sidecar"`, `_sidecar_token(league)`; and
  `"registry"`, the seven E-10 verdict payloads. The registry is in the key because the reply
  depends on it (1.6, 1.7) and the result cache outlives a test's patched registry otherwise.
- `_reference_at(scenario_id, opt_in)` is `@planning._built_once(maxsize=4, reads=lambda
  scenario_id, opt_in: ("Spain",))` around the call of 4.3. The match snapshot is
  `xi_extensions._match_snapshot(scenario_id, 0)` (the gated loader; `decision_lab.snapshot` and
  `runtime.match_snapshot` are not called, OR-XI 7.3).
- `_sidecar_errors()` maps `SidecarStale`, `SidecarMismatch` and `record.RecordCorpusDefect` (all
  `RuntimeError`, which `lab_errors` would leave as a 500) to `HTTPException(503,
  SIDECAR_UNAVAILABLE)`; `SidecarMissing` is a `FileNotFoundError` and `lab_errors` already makes
  it a 503.
- `canonical(request)`: `request.model_dump(mode="json")`, locks and exclusions sorted and
  de-duplicated, rules sorted by `template_id` (outcomes are returned in `TEMPLATES` order, so the
  request order changes nothing in the reply). Every default is in it.
- Storing: `runtime.is_complete`. The record and the proposal carry `completeness` `"EXACT"`; the
  XI part carries `"EXACT"` for `OPTIMAL` and `INFEASIBLE`, and `"TIME_LIMIT"` otherwise, so a
  solve the clock cut is never stored.
- `/api/opponent/proposal` and `/xi` read the record of the decision point's opponent: the
  opponent is the side of `SCENARIOS[s]["match_id"]` in Spain's `matches` table that is not
  675, read inside `compute`; `D` is the scenario's cutoff. `/api/opponent/teams` returns, beside
  the clubs, each decision point with its opponent resolved the same way, so the page can send a
  `RecordRequest` for it.

### 5.4 Envelopes

Every POST reply has these keys, `null` where a key does not apply: `tool`, `claim`,
`non_claim`, `statements` (ordered list), `declared`, `ledger`, `evidence`
(`shell.evidence_payload` of the whole reply), `budget` (`budget.report(completeness)`),
`not_measured` (`shell.not_measured_payload(OPPONENT_NOT_MEASURED_EXTRA)`), `cannot_say` (the
three `CANNOT_SAY_*`), `provenance` (`{"providers": ["pappalardo"], "record_version", 
"team_match_version", "descriptor_schema", "descriptor_fingerprints" {subject: fingerprint},
"sidecar": sidecar.provenance(league), "public_files": the token listing, "registry" {subject:
badge}, "proposal_policy_version", "reference_fingerprint", "snapshot":
kernel.scrub_lineage(snap.provenance), "solver_warnings": result warnings}` as applies). No key is
`total`, `index`, `score`, `rank` or holds a part of `thesis.BANNED_KEY_PARTS`; `finalize`
refuses otherwise.

#### 5.4.1 `GET /api/opponent/menu` (corpus-free, through `finalize`)

`leagues` `[{competition, label}]` in `LEAGUE_LABELS` order; `date_range` `{first, last}` and
`date_rule_text` (`PRIOR_RULE_TEMPLATE` unformatted is not served; `DATE_RULE`); `windows` `[{key,
phrase, default}]`; `groups` `[{group_id, heading, non_claim, subjects: [{subject_id, kind, label,
definition, part_phrases, verdict}]}]` in `SUBJECT_GROUPS` order with each `verdict` the registry
payload for `close_11v11`; `record_available` (1.7) and `record_withheld_text`; `decision_points`
`[{scenario_id, label, cutoff}]` in `SCENARIOS` order (the opponent is resolved by the teams GET);
`templates` `[{template_id, label, subject_id, part, kind, requirement_ids,
needs_experimental_opt_in, threshold_text}]` in `TEMPLATES` order; `percentile_menu`; `modes`
`[{mode, label}]`; `formations`; `opt_in_label` (`xi_extensions.OPT_IN_LABEL`);
`panel_opt_in_label`; `proposal_claim`, `proposal_non_claim`; `cannot_say`; `s5_ratio_note`;
`not_measured`; `provenance.providers`. A template's `threshold_text` is `THRESHOLD_TEXT_SHARE` or
`THRESHOLD_TEXT_RATE` (5.6).

#### 5.4.2 `POST /api/opponent/record`

`tool` `"opponent.record"`; `record_state` `"SHOWN"` | `"WITHHELD"`; `team` `{competition,
competition_label, team_id, team_name}`; `decision_date`; `window` `{key, phrase}`; `scope_text`
(`RECORD_SCOPE`); `prior_rule_text`; `matches` `{valid_count, left_out_count, rows: [{date,
opponent_name, venue_text, goals_text, minutes_text, valid, reason_text}]}` (`null` when
withheld); `groups` as the menu's, each subject adding `parts` `[{part, phrase, count,
count_text, share_text}]` (composition) or `count`, `count_text`, `minutes_text`, `rate_text`
(level), `events_text`, `sample_text`, `no_event_text` (`NO_EVENT` or `null`), `evidence`,
`verdict`, `verdict_note` (`ALL_STATES_NOTE` under `all_states`, else `null`), `ratio_note`
(S5's `S5_RATIO_NOTE`, else `null`), `panel_state` (`"SHOWN"`, `"OFFERED"` (offered, no
opt-in), or the reason token `"NOT_ESTABLISHED"`, `"BEFORE_DATE"`, `"WINDOW"`), `panel_text`
(the matching sentence), `panel` (`null` or `{parts: [{part, phrase, point_text,
interval_text}] | point_text, interval_text, shrink_weight_text, holes_text, worlds, world_seed,
statements}`); `panel_opt_in_label`; `claim` `RECORD_CLAIM` or, withheld, `RECORD_WITHHELD`;
`non_claim` `RECORD_NON_CLAIM`. When withheld every count, share, text built from a count, the
matches block and the ledger's computed rows are absent or `null`.

#### 5.4.3 `POST /api/opponent/proposal` and `POST /api/opponent/xi`

Both: `tool`; `decision_point` `{scenario_id, label, cutoff, opponent_team_id, opponent_name}`;
`window`; `record_state`; `proposal` `{proposal_state ("FORMED" | "NOTHING_SET" | "WITHHELD"),
rules: [{template_id, label, threshold_text, percentile_text, state, state_text,
cited_subject_id, cited_label, cited_value_text}], minimum_rows: [{requirement_id, label,
minimum, minimum_text, source_text, set_by: [template labels], qualifiers: [{subject_id, label,
badge, sentence}]}], minimums: {requirement_id: float}, evidence, accepted, accepted_text,
xi_lab_minima_text}`; `claim` `PROPOSAL_CLAIM`; `non_claim` `PROPOSAL_NON_CLAIM`.
`cited_value_text` is the record's share or rate the rule compared (`share_text` or `rate_text`),
`null` when `UNDECIDED`. `minimum_text` is `planning._minimum_text({"source":
"LEAGUE_PERCENTILE", "minimum": value})` (`"≈ "` and four decimals, a figure read off the record);
`source_text` is `REFERENCE_SOURCE` built from `declared_minimum(...).label` and the
distribution's unit counts.

`/api/opponent/xi` adds: `scenario`; `formation`, `slots`; `mode` and `mode_text`;
`minimum_in_force_rows` `[{requirement_id, label, minimum_text, origin_text}]` for every
requirement in force (origin "Shipped default", "Entered by you" or "Your accepted proposal";
entered minima printed by `format_plain`, defaults and proposed ones by `_minimum_text`);
`model_note` (`XI_MODEL_NOTE` without the opt-in, else `null`); `omitted_candidates`
(`snap.omitted`, as `/api/xi/solve` serves them); `xi` `{status, status_text, objective_texts,
lineup_rows, requirement_rows: [{label, minimum_text, sum_text, shortfall_text}],
membership: {groups: [{heading, rows: [{player_id, name}]}], completeness}, ties_text}`; `claim`
`XI_CLAIM`, `non_claim` `XI_NON_CLAIM`, the proposal's two sentences in `statements`.

The solve: `problem = xi_extensions.declare(snap, request_with_minima_in_force, mode=mode)`, then
`solve_xi(problem.candidates, problem.requirements, formation=request.formation,
locked=problem.locks, excluded=problem.excludes, mode=mode, seed=historical.SEED,
worlds=snap.worlds, provenance=snap.provenance, time_limit=min(15.0, budget.remaining()))`, the
call `decision_lab.solve` makes (decision_lab.py:343-356) with the clock bound added; the baseline
comparison `decision_lab.solve` adds (`what_changed`) is not made (no displaced player, ROOT 2.6
D3). `status_text`: `XI_STATUS_OPTIMAL`, `XI_STATUS_INFEASIBLE` (SATISFY), `XI_NOT_CERTIFIED`
(`FEASIBLE`, `UNKNOWN`), `XI_STATUS_REFUSED` (`MODEL_INVALID`). `lineup_rows` by
`xi_extensions._lineup_rows`; `sum_text` the lineup's exact sum (`xi_extensions._exact_sum`)
rounded down at four decimals (`planning._outward(..., up=False)`); `shortfall_text` the solver's
`normalized_deficit` at five decimals rounded half-even, labelled "in club medians";
`objective_texts` the two components of `objective_vector` the same way. `membership` reads
`result.equivalent_players[pid]["possible"]` and `["necessary"]` (solver.py:419-422) into three
fixed headings (5.6 `MEMBERSHIP_*`), rows in `player_id` order, players with `possible` false not
listed; its `completeness` is `"EXACT"` when `provenance["tie_analysis_complete"]` and
`"TIME_LIMIT"` otherwise. No `selection_frequencies`, no CORE/FAVORED/CONTESTED/FRINGE (H10): the
solve has no worlds. Solver warnings stay in provenance (several fail the copy guard, OR-XI 7.7).

### 5.5 The ledger (O12) and evidence (O13)

Declared rows (`shell.declared_row`), a function of the resolved request. Keys are prefixed by
route family so the desk can carry them without a collision (6.4): `record-team` ("Team",
"{team} ({league})"), `record-date` ("Decision date", "{D}. Matches on calendar dates before it
are used."), `record-window` ("Window", phrase), `record-panel-opt-in` ("E-10 estimate", "Shown
where E-10 established it; you opted in.", only when true); `match-decision-point`,
`match-formation`, `match-mode`, `match-opt-in` (when true), `match-lock-{id}`,
`match-exclusion-{id}`, `match-minimum-{requirement_id}` (entered, `format_plain`),
`match-window`, `match-rule-{template_id}` ("Rule", "{template label}: at least {threshold};
minimum at the {p}th percentile of league starting-XI sums."), `match-accept` ("Proposal",
"Accepted by you." or "Not accepted."). A default is never a declared row.

Computed rows (`shell.ledger_row` with a `stage`, as `planning.ledger_row` adds one; stages here
`OPPONENT`, `PROPOSAL`, `XI`). `value_text` is `None` wherever no number exists, never 0.

| Route | `row_id` | `quantity` | `value_text` | `sample` | `evidence` | `verdict` | `solver` |
|---|---|---|---|---|---|---|---|
| record | `record-matches` | "Valid prior matches of {team}" | "{n} valid; {m} left out" | `prior_rule_text` | OBSERVED | `None` | `TEAM_MATCH_VERSION` |
| record | `record-window-time` | "Window time" | `minutes_text` + " minutes" | window phrase | OBSERVED | `None` | `TEAM_MATCH_VERSION` |
| record | `record-{subject}` | the subject's label | parts as `"{phrase}: {count_text} ({share_text})"` joined by "; ", or the level's `rate_text`; `None` with no event | `sample_text` | DERIVED (counts OBSERVED composed) | the subject's verdict payload | `"descriptor {fingerprint}"` |
| record | `panel-{subject}` (shown only) | "E-10 estimate: {label}" | the interval texts, and the point when shown | `PANEL_HEAD` | EXPERIMENTAL | the subject's verdict payload | `"estimator · 40 worlds · seed 20261009"` from `SERVED_PANEL` |
| proposal, xi | `proposal-rule-{template_id}` | the template label | `state_text` and `cited_value_text` | `RULE_*` sentence | the cited record's class | the cited record's payload | `PROPOSAL_POLICY_VERSION` |
| proposal, xi | `proposal-minimum-{requirement_id}` | "{label} minimum, proposed" | `minimum_text` | `source_text` and the qualifiers, in order | HEURISTIC composed with the requirement's and the cited records' classes | `shell.verdict_payload("none", "proposal-{requirement_id}")` (a policy number no protocol tests, the planning precedent for minima) | `PROPOSAL_POLICY_VERSION` |
| xi | `xi-solve` | "Least declared shortfall" | `objective_texts` joined, `None` unless `OPTIMAL` | `XI_CLAIM` | as OR-XI 7.6 composes the requirements in force | `None` (exact computation) | `"{status} · 1/100000"` |
| xi | `xi-minimum-{requirement_id}` | "{label} minimum in force" | `minimum_text` | `origin_text` | the requirement's class (HEURISTIC or EXPERIMENTAL) | `None` | `None` |

Withheld: no computed row; the kit prints "No computed quantity was sent.".

### 5.6 Copy

Every sentence below is a module constant of `api/opponent_lab.py` (or of the model module that
returns it), served outside provenance, and passes `labels.scan_labels` under every format
argument a test supplies; `tests/test_opponent_api.py` scans each one, and every reply passes
`finalize`. The sentences of E-10's config (`registry_non_claims`, the qualifiers,
`s5_ratio_name`) are served verbatim from `panel.py`'s constants, and a test asserts they pass the
guard (they do on the draft: checked when this file was written). The examples below are filled
with invented values.

| Constant | Text |
|---|---|
| `RECORD_CLAIM` | Counts of recorded events in the league matches of {team} dated before {date}, in the window you declared, for each E-10 definition: what opponents did against the team, and where the team's own defensive actions were recorded. Each share is a count divided by the sum of the counts listed beside it. |
| `RECORD_NON_CLAIM` | A record of past matches. It is not a tendency unless the badge beside it says E-10 tested it and established it, it does not say how well the team defends, and no single number here summarises an opponent. |
| `RECORD_WITHHELD` | The record is withheld until E-10 is registered. Computing these counts on the corpus before its protocol is frozen would show the quantities E-10 tests to the people who still decide it. The definitions and their badges are shown. |
| `RECORD_SCOPE` | LAB · historical · {league label} 2017/18, matches before {date} · counts of recorded events · not modelled: why a side conceded where it did, finishing, defending, goalkeeping, physical profile |
| `CANNOT_SAY_FUNNEL` | A team can leave a channel open on purpose or fail to close it. Event data cannot tell the two apart, so no share here says where the team defends badly or where to attack. |
| `CANNOT_SAY_OPPONENTS` | A record mixes what this team allowed with what the teams it met tried to do. Nothing here is adjusted for the opponents met or for team strength. |
| `CANNOT_SAY_ORDER` | Parts are listed in a fixed order. No part is picked out, sorted by size or named the largest, and teams are never listed in order of a share or a rate. |
| `DATE_RULE` / `prior_rule_text` | Matches on calendar dates before {date} are used; matches on that day are not. |
| `LEVEL_DEFINITION` | Final-third entry passes conceded per 90 minutes of window time: the three parts of the share of final-third entry passes conceded, added together, divided by the window time in units of 90 minutes. Window: {window phrase}. |
| `INVALID_PERIOD_MISSING` / `_CLOCK` / `_GOALS` / `_DISMISSALS` | No event in one of the two halves. The match is left out of every record. / An event time is not a valid clock reading. The match is left out of every record. / The goals in the event record differ from the match sheet. The match is left out of every record. / The dismissals in the event record differ from the match sheet. The match is left out of every record. |
| `NO_PRIOR_MATCH` | No valid match of this team is dated before {date}, so no count exists yet. |
| `NO_EVENT` | No such event was recorded in the prior valid matches, so no share exists. It is not zero. |
| `SAMPLE_TEXT` | {events} events in {matches} valid matches, {minutes} minutes of window time. |
| `S5_RATIO_NOTE` | The share is a monotone transform of opponent passes per recorded high-zone defensive action. That ratio is named here and not shown. |
| `ALL_STATES_NOTE` | E-10 registers its definitions in the window before any dismissal and within one goal. In every match state the definition is a different one, so no E-10 record covers it and no E-10 badge is shown for it. |
| `PANEL_OPT_IN_LABEL` | Show the E-10 estimate for each record E-10 established |
| `PANEL_HEAD` | Estimate of the one E-10 estimator at {date}: the league composition of matches before that date, moved by this team's own history and drawn toward the league by the pseudo-events E-10 selected. The interval is taken over 40 resampled sets of the league's prior matches. |
| `PANEL_POINT_WITHHELD` | No point is shown: the reliability bound E-10 recorded for this descriptor is below 0.70, so the interval alone is shown. |
| `PANEL_NOT_OFFERED` / `PANEL_BEFORE_DATE` / `PANEL_WINDOW_ONLY` | E-10 has not established this record, so only the record is shown. / E-10 evaluated matches from 2018-01-01. Before that date only the record is shown. / The estimate exists for the window before any dismissal and within one goal only. |
| `PANEL_HOLES` / `PANEL_ALL_HOLES` | {h} of 40 resampled sets hold no prior event of this team and are left out of the interval. / Every resampled set holds no prior event of this team, so no interval exists. |
| `SHRINK_TEXT` | Weight of this team's own history in the estimate: {w}. |
| `PROPOSAL_CLAIM` | A requirement proposal formed by the rules you declared. Each rule compares one share or rate of the opponent record with your threshold and, where the record reaches it, sets one minimum at the league percentile you chose. It is your declared policy, HEURISTIC, and it changes no solve until you accept it. |
| `PROPOSAL_NON_CLAIM` | The link from a record to a requirement is your declaration, not something the data shows. The requirement counts where your players' passes started; the record counts where opponents' entries ended or started. A record of where a team conceded is not a reason to attack there. |
| `RULE_HOLDS` / `RULE_DOES_NOT_HOLD` / `RULE_UNDECIDED` | The record reaches your threshold, so this rule sets its minimum. / The record is below your threshold, so this rule sets nothing. / The record has no event for this share or rate before the date, so this rule sets nothing. That is not evidence that the share is low. |
| `NO_RULE_HOLDS` | No declared rule sets a minimum, so the minima in force are unchanged. |
| `PROPOSAL_NOT_ACCEPTED` / `PROPOSAL_ACCEPTED` | Shown and not applied: the minima in force are the ones you entered, or the defaults. / Accepted by you: the proposed minima are in force in the solve below. |
| `PROPOSAL_CONFLICT` | Two rules that hold set one requirement at different percentiles. Keep one of them. |
| `ENTERED_AND_PROPOSED` | One requirement has a minimum you entered and an accepted proposed minimum. Keep one of them. |
| `PROPOSAL_WITHHELD` / `ACCEPT_WHILE_WITHHELD` | The proposal reads the record, which is withheld until E-10 is registered. / There is no proposal to accept while the record is withheld. |
| `ACCEPT_WITHOUT_RULES` | There is no proposal to accept: no rule was declared. |
| `THRESHOLD_TEXT_SHARE` / `THRESHOLD_TEXT_RATE` | at least a share you declare, from 0 to 1 / at least a rate you declare, per 90 minutes of window time |
| `RULE_TWICE` / `THRESHOLD_SHARE` | A rule template is declared twice. Declare each at most once. / A share threshold is a number from 0 to 1. |
| `XI_LAB_MINIMA` | To solve the same minima on XI Lab, enter: {label} = {value}; … (each value by `format_plain`). |
| `REFERENCE_SOURCE` | {declared_minimum label} ({n} starting elevens of {t} clubs). |
| `TEMPLATE_LEFT_F3` | Left wide-channel pass origins minimum, from the share of final-third entry passes conceded in the defending team's right lateral third |
| `TEMPLATE_RIGHT_F3` | Right wide-channel pass origins minimum, from the share of final-third entry passes conceded in the defending team's left lateral third |
| `TEMPLATE_WIDE` | Both wide-channel pass origin minima, from the share of final-third entry passes conceded in the two outer lateral thirds |
| `TEMPLATE_LEFT_BOX` | Left wide-channel pass origins minimum, from the share of penalty-area entry passes conceded that started in the defending team's right lateral third |
| `TEMPLATE_RIGHT_BOX` | Right wide-channel pass origins minimum, from the share of penalty-area entry passes conceded that started in the defending team's left lateral third |
| `TEMPLATE_PROGRESSION` | Positive completed-pass xT per 90 minimum, from final-third entry passes conceded per 90 minutes of window time |
| `XI_CLAIM` | The least declared shortfall over the XIs that the eligibility rules, the minutes gate, missing measurements, locks and exclusions allow, solved by XI Lab's solver on XI Lab's model at this decision point with the minima in force. One XI that reaches it is shown. |
| `XI_NON_CLAIM` | Arithmetic on prior per-90 rates under the minima in force. It is not a forecast and says nothing about the result of the match. |
| `XI_TIES` | Other XIs can reach the same shortfall; which one is shown is the solver's choice. |
| `XI_STATUS_OPTIMAL` / `XI_STATUS_INFEASIBLE` / `XI_NOT_CERTIFIED` / `XI_STATUS_REFUSED` | Certified in the integer model: no XI reaches a smaller declared shortfall. / No XI meets every minimum under the Satisfy rule, in the integer model. Nothing was relaxed. / The solver did not certify this XI within its time limit. Treat it as incomplete. / The solver refused the model, so no XI is reported. |
| `XI_MODEL_NOTE` | Without the experimental opt-in this solve holds {labels} only. XI Lab's own solve also holds the two side pass-origin requirements, so the two answers can differ for that reason alone. |
| `MEMBERSHIP_EVERY` / `_SOME` / `_UNDECIDED` | In every XI that reaches this shortfall / In some XIs that reach it, not in all / Whether in every XI that reaches it was not decided |
| `UNKNOWN_TEAM` / `UNKNOWN_DECISION_POINT` | This team has no league match in the corpus for that league. / unknown decision point |
| `DATE_FORMAT` / `DATE_RANGE` | A decision date is written YYYY-MM-DD. / A decision date lies from 2017-07-01 to 2018-07-01. |
| `SIDECAR_UNAVAILABLE` | the tag sidecar of this league is absent or is not the one its manifest records |

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
429 busy (build gate, sixteen places); 503 corpus, sidecar or match table absent or damaged
(`SidecarMissing`, `_sidecar_errors`, `FileNotFoundError`, Arrow); 500 for a `BoundaryViolation`
or an internal fault (`KeyError`, the non-integer count check). A 200 is never served for a
record built from a sidecar `verify` refused.

### 5.8 What does not change (R13)

Every shipped route answers byte for byte as before; `decision_lab.snapshot` is neither called
nor cleared; `runtime.router` still serves only `/api/evidence/verdicts`
(`tests/test_lab_runtime.py:783-798`); runtime, squad and transfer still serve exactly 14 API
paths (`tests/test_planning_api.py:1630-1650`); `runtime.BUDGETS` and `LONG_ROUTES` are unchanged.

## 6. API: `galactico/api/desk.py`

### 6.1 What the desk is

One page, one POST, one reply through `finalize`: the chain of ROOT 2, each step the reply of
the page that computes it, composed on the server so `finalize` sees the whole reply (the
preference stated for this work), with the declared inputs apart (O12) and one evidence ledger.
The desk computes no number of its own: its only computations are which parts run, the order of
rows, the removal of repeated rows, and the composed evidence class.

| Stage (ROOT 2) | Part id | Composed from | Runs when |
|---|---|---|---|
| declared identity | `snapshot` | `squad_lab.squad_snapshot(SquadSnapshotRequest)` | always |
| explicit requirements | `reference` | `squad_lab.squad_reference(SquadReferenceRequest)` | always |
| squad audit | `depth` | `squad_lab.squad_depth(SquadDepthRequest)` | always |
| squad audit | `stress` | `squad_lab.squad_stress(SquadStressRequest(k))` | `stress_k` is 1 or 2 (default 1) |
| role brief | `brief` | `squad_lab.squad_brief(SquadBriefRequest(slot_id, include_leagues))` | a slot is declared |
| candidate search | `search` | `transfer_lab.transfer_injection(TransferInjectionRequest(slot_id, include_leagues, filters))` | a slot is declared |
| per match: opponent record, proposal, XI solve | `match-xi` | `opponent_lab.opponent_xi(OpponentXIRequest)` | `match` is declared, and the planning point is the flagship |
| per match: XI exact additions | `match-ceilings` | `xi_extensions.ceilings_route(CeilingsRequest)`, minima in force | `match` declared |
| | `match-conflict` | `xi_extensions.conflict_route(ConflictRequest)` (`explains: "solve"`, the match mode, minima in force) | `match` declared, mode `SATISFY`, the solve `INFEASIBLE`, and the opt-in (otherwise `DESK_CONFLICT_NEEDS_OPT_IN`) |
| | `match-frontier` | `xi_extensions.frontier_route(FrontierRequest)` | `match.frontier_dimensions` declared (two or three; the opt-in is then needed, OR-XI 7.2) |
| | `match-risk` | `xi_extensions.risk_tail_route` or `risk_regret_route`, 12 worlds | `match.risk_rule` declared |
| evidence ledger | | the parts' ledgers, composed (6.4) | always |

Every other planning choice (presets, requirement declarations, exclusions, locks, the opt-in, the
formation) is the request's `PlanningInputs`, passed unchanged to every planning part, so the
parts answer one declared problem. The per-match parts share one set of match declarations. A
part that does not run is listed with `state` `"NOT_RUN"` and its sentence (`DESK_NO_SLOT`,
`DESK_NO_MATCH`, `DESK_CONFLICT_NEEDS_OPT_IN`, `DESK_MATCH_OTHER_CLUB`); it is never dropped
silently.

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
| GET | `/api/desk/menu` | | | corpus-free: `planning.catalogue()` (identity phrases, presets, requirements, minimum sources, percentile menu, leagues, formations, research statement, not measured), the slots of each formation with `recruitable` as Transfer Lab's scenarios GET serves them, `stress_sizes` `[1, 2]`, the decision points and templates of `/api/opponent/menu`, the stage list with headings, every desk sentence, `provenance.providers` |
| POST | `/api/desk/chain` | `desk.chain`: 180 (local `DESK_BUDGET_SECONDS`) | no | `DeskRequest` |

```python
class DeskMatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenario_id: str = "madrid-2018-05-06"           # a key of decision_lab.SCENARIOS
    window: opponent_lab.WindowKey = "close_11v11"
    mode: Literal["BALANCE", "SATISFY"] = "BALANCE"
    locks: list[StrictInt] = Field(default_factory=list, max_length=11)
    excludes: list[StrictInt] = Field(default_factory=list, max_length=30)
    minimums: dict[xi_extensions.RequirementId, Minimum] = Field(default_factory=dict)
    rules: list[opponent_lab.ProposalRule] = Field(default_factory=list, max_length=6)
    accept: StrictBool = False
    frontier_dimensions: list[xi_extensions.RequirementId] | None = Field(default=None,
                                                                         min_length=2, max_length=3)
    risk_rule: Literal["WORST_WORLD", "TAIL", "MINIMAX_REGRET"] | None = None
    risk_tail_count: StrictInt | None = None

class DeskRequest(planning.PlanningInputs):
    slot_id: transfer_lab.SlotId | None = None       # the slot being recruited: brief and search
    include_leagues: list[planning.League] = Field(default_factory=list, max_length=4)
    filters: transfer_lab.TransferFilters = Field(default_factory=transfer_lab.TransferFilters)
    stress_k: Annotated[Literal[1, 2], planning.INTEGER_ONLY] | None = 1
    match: DeskMatch | None = None
```

The formation and the experimental opt-in of `PlanningInputs` are the per-match chain's too. A
goalkeeper slot is refused before any part runs, with Transfer Lab's `GOALKEEPER_REASON`. The
risk fields follow `RiskTailRequest`'s validators (OR-XI 7.2), restated by calling them: the desk
builds the sub-request and a `ValidationError` from it is a 422 through `lab_errors`. `k = 3` is
not offered (it needs Squad Lab's confirmation, which the desk does not ask).

### 6.3 Composition rules

1. **In process, by the handler.** Each part is the shipped handler function called with its
   request model; the `Response` it returns is read back with `json.loads(response.body)`. So a
   part is byte for byte the reply its own page receives for the same declarations, with that
   route's cache, budget, build gate, long-job place and `finalize` (ADR-0024). No HTTP request
   is made and no build function is reached past its handler.
2. **Order.** The table order of 6.1, sequentially; never in parallel.
3. **Budget.** The desk starts its own `runtime.Budget(DESK_BUDGET_SECONDS)` at entry. Before a
   part it compares the remaining seconds with that part's own budget ceiling (the route's entry
   in `runtime.BUDGETS`, `squad_lab.RECORD_BUDGETS`, `transfer_lab.UNIVERSE_BUDGET_SECONDS` or
   `opponent_lab.OPPONENT_BUDGETS`); when fewer remain, the part and every later part are
   `NOT_STARTED` (`DESK_NOT_STARTED`) and the reply's completeness is `"DEADLINE"`. A part's own
   budget still bounds it.
4. **Places.** The desk route is not a long route and never takes a long-computation place: the
   stress, search and risk handlers take theirs inside their own computation, and a desk that held
   one of the two while calling them could wait on itself. A desk request holds its own admission
   place and, while a part computes, that part's (`runtime.admission`, two of sixteen at most).
   A 429 from a part is the desk's 429 (`Retry-After` as served); a 503 is the desk's 503; a 422
   from a part is the desk's 422 with the part's sentence (the declarations are the desk's). The
   desk catches nothing else.
5. **Consistency.** The planning parts answer one declared problem, so their common rows
   (`planning.declared_rows` and `planning.base_ledger`: `eligibility-rules`, `gate-minutes`,
   `rates-*`, `minimum-*`) must be equal JSON across parts. If the corpus files change between two
   parts, they can differ: the desk then serves the reply with `chain_state` `"INCONSISTENT"`,
   completeness `"INCONSISTENT"` (not a stored token) and `DESK_INCONSISTENT`. A declared row with
   one key and two values inside one family is a fault of the desk (`RuntimeError`, a 500).

### 6.4 The envelope and the one ledger

`tool` `"desk.chain"`; `scenario_id`, `scenario`, `eligibility` (from the snapshot part);
`scope_text` (`planning.SCOPE_TEMPLATE` filled with the scenario, as Squad Lab prints it);
`chain_state` (`"COMPOSED"`, `"PARTIAL"`, `"INCONSISTENT"`); `stages` `[{stage, heading,
parts: [{part_id, route, page_href, page_name, state, state_text, claim, non_claim, warnings,
statements, budget, summary_rows: [{label, value_text}]}]}]` in chain order; `declared` and
`ledger` (below); `evidence` (`shell.evidence_payload` over the union of the parts' evidence
inputs, de-duplicated by label and class); `not_measured` (`planning.not_measured()`, the
shell's nine of ROOT 2.3 then the six planning items) and `not_measured_closing`;
`research_statement` and `verdicts` (`planning.verdict_reading()`, the same reading every planning
reply carries); `claim` `DESK_CLAIM`, `non_claim` `DESK_NON_CLAIM`; `statements`
(`DESK_MATCH_SCOPE` when `match` is declared, `DESK_NO_DESCRIPTOR` always, `DESK_LINK_NOTE`
always); `budget`; `provenance` `{"providers": ["pappalardo"], "desk_version", "parts":
{part_id: that part's provenance}}`.

A part's `summary_rows` are copied from fields its reply serves, never written by the desk:
snapshot: "Players in the evidence set" from the `gate-minutes` row; depth and stress: their
`claim`; brief: its `claim`; search: `search_statement`, then one row per outcome group of
`listings.keys[name].groups` (`outcome_label`, `count`) in served order, then `screened_count` and
`selection_statement` (no candidate name: the list is on Transfer Lab, and the outcome groups are
counts, R1, H8/H35); match-xi: `xi.status_text`, `objective_texts`, the lineup rows,
`minimum_in_force_rows`, and the proposal's `minimum_rows` with their `set_by` labels and
qualifiers; ceilings, conflict, frontier, risk: their `claim` and `statements`.

**Declared.** Rows of two families, planning and match. Planning: the declared rows of every
planning part, in part order, a row whose key has been seen dropped when equal (6.3.5). Match:
the declared rows of `match-xi` only (they hold every match declaration: decision point,
formation, mode, opt-in, locks, exclusions, entered minima, window, rules, acceptance); the XI
additions' declared rows are not carried, because the desk builds their requests from the same
match fields and a test asserts each is a subset of `match-xi`'s declarations. Each row keeps its
`stage` and gains `part`.

**Computed.** The planning base rows once (from `snapshot`), then each part's other rows in part
order. Each carried row keeps every field its reply served (quantity, value_text, sample,
evidence, verdict, solver, stage) and gains `part`, `page_name` and `page_href`; its `row_id` is
prefixed `"{part_id}-"` (hyphens, so the kit's plain-word rule holds, labs-shared.js:55). Rows of
the XI additions take stage `XI`. From `match-xi` the desk carries the rows `xi-*` and
`proposal-minimum-*` and never `proposal-rule-*`.

**No E-10 descriptor.** The desk shows no E-10 descriptor value, share, count, rate or estimate,
in any state (stricter than PIPELINE 13's "while it serves this sentence", so that no later
results commit can make a desk reply false): it carries no `record` reply, no `proposal.rules`, no
`cited_value_text` and no `proposal-rule-*` row. It names cited records only by label and badge
beside a proposed minimum (the qualifiers PIPELINE 12.3 requires) and prints
`DESK_NO_DESCRIPTOR`. `test_desk_shows_no_e10_descriptor` (8.1) plants a record with known texts
and asserts none of them, and none of those keys, is in any desk reply. What remains: a minimum
the proposal set states that some declared rule held, that is, that the record reached the
threshold the reader declared (OPEN QUESTION 3).

### 6.5 Copy

As 5.6, every constant scanned and served outside provenance.

| Constant | Text |
|---|---|
| `DESK_CLAIM` | The planning chain for {team} before {cutoff}, composed from the Squad, Transfer, XI and Opponent Lab replies to the declarations above. Every computed row is in one ledger, as the page named beside it served it. |
| `DESK_NON_CLAIM` | Nothing here says whom to keep, sell or sign. Every number is conditional on what you declared, and what is listed as not measured is outside every number. |
| `DESK_MATCH_SCOPE` | The per-match chain runs at Real Madrid's two historical decision points. It is a past decision, not a plan for next season. |
| `DESK_MATCH_OTHER_CLUB` | The per-match chain exists only at Real Madrid's two historical decision points. |
| `DESK_NO_SLOT` | Declare the slot being recruited to see the role brief and the search. |
| `DESK_NO_MATCH` | No per-match chain was declared. |
| `DESK_NOT_STARTED` | Not started: too little of this request's time was left for it. Ask again; parts already computed are kept by the server. |
| `DESK_NO_DESCRIPTOR` | No E-10 descriptor is shown here. A proposal's minima are listed with the records they cite; the records themselves are on Opponent Lab. |
| `DESK_INCONSISTENT` | The corpus files changed while this chain was composed, so its parts disagree. Ask again. |
| `DESK_CONFLICT_NEEDS_OPT_IN` | A minimal conflicting set for this solve needs the experimental opt-in. Without it, XI Lab's conflict panel explains its own solve. |
| `DESK_LINK_NOTE` | Each part opens on its own page with that page's defaults. Declarations made here are not carried across pages. |
| `DESK_STAGE_HEADINGS` | Declared identity; Explicit requirements; Squad audit; Role brief; Candidate search; Opponent record; Requirement proposal; XI solve; Evidence ledger; Not measured here |
| `DESK_PART_COMPOSED` | Composed from the reply of {page name}. |

`DESK_LINK_NOTE` follows the shipped precedent (squad.html: "Transfer Lab opens with its own
defaults. Declarations made here are not carried across pages."): no page reads declarations
from a URL in this release.

### 6.6 Cache key and storing

`runtime.cache_key("desk.chain", body, token)`: `body` is `planning.canonical_request(scenario,
request)` with the match part's locks, exclusions and rules canonicalised as 5.3; `token` is
`planning._digest` of `planning.corpus_token(scenario, all five leagues if a slot is declared
else ())` (falling back to the scenario's league alone when another league's files are absent, as
`squad_lab._corpus_token` does, and then not stored) and, when `match` is declared,
`opponent_lab._token("Spain")`. Stored when `runtime.is_complete` holds over the whole reply, so
every carried part's own `budget.completeness` must be `EXACT` or `COMPLETE`; a `NOT_STARTED`,
`DEADLINE`, `INCONSISTENT` or pool-less reply is computed again next time. Each part is also kept
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
separators read evidence | matchday | planning | desk. The screen-reader suffix " Lab" is a field
of `Destination` (`sr_suffix`, default `" Lab"`; the desk's `" (Director's desk)"`), so the five
shipped links keep their bytes and the desk does not read "Desk Lab". `Shell.nav` already takes
`sr_suffix` per item.

### 7.2 `/opponent`

Eyebrow "Opponent record · prior dates only"; h1 "Where it was conceded.<br>Not why."; lede
"What a team's opponents did against it, and where its own defensive actions were recorded, in
league matches before a date you choose. Each record carries its E-10 badge."

| Panel | Shown when | Request | Renders (server field) | States |
|---|---|---|---|---|
| `#op-form` | always | `GET /api/opponent/menu` on load (corpus-free), then `GET /api/opponent/teams` | league select, team select (served order: league, club name, team id; never by a record value), `input[type=date]` with `min`/`max` from `date_range`, window select (`windows`, default marked by the server), a decision-point select ("Or use an XI decision point", `decision_points` labels) that fills league, team and date from the teams reply's resolved points, and `#load-record` | teams GET 503: `Shell.errorText` and the decision-point path still offered; record unavailable state from `record_available` |
| `#scope-slot`, `#claim-slot` | after a record reply | `POST /api/opponent/record` on `#load-record` | `scope_text`, `claim`, `non_claim`, `prior_rule_text` | `WITHHELD`: `claim` (`RECORD_WITHHELD`) as a notice |
| `#record-groups` | after a record reply | | one section per `groups[]` in served order: `heading`, `non_claim` (always, every state), then a card per subject in served order: label, `Shell.verdictBadge(verdict)` and `verdict.statement`, `verdict_note`, `Shell.evidenceBadge(evidence)`, a parts table (`phrase`, `count_text`, `share_text`, in served order, every row the same classes and computed style), or the level's `count_text`, `minutes_text`, `rate_text`; `sample_text`; `no_event_text`; `ratio_note`; a `<details>` "Definition" holding `definition` | `WITHHELD`: label, badge, statement and definition only; a `null` share prints `—` and `no_event_text`, never 0 |
| `#panel-optin` | some subject's `panel_state` is `"OFFERED"` or `"SHOWN"` | ticking it sends the record request again with `panel_opt_in: true` | `panel_opt_in_label`; inside each card with `panel` non-null: parts `point_text` (or `PANEL_POINT_WITHHELD` from `panel.statements`), `interval_text`, `shrink_weight_text`, `holes_text`, `worlds` and `world_seed` as served integers, the EXPERIMENTAL badge | `panel_text` beside every card whose estimate is not shown; unchecked on every load |
| `#matches-slot` | record shown | | `<details>` "Matches used": rows date, `opponent_name`, `venue_text`, `goals_text`, `minutes_text`, `reason_text`, in served order | none valid: `NO_PRIOR_MATCH` |
| `.cannot-say` | always | | `Shell.cannotSay(cannot_say)` | |
| `#proposal-panel` | a decision point is chosen | `POST /api/opponent/proposal` on `#form-proposal` | one row per template (served order): an include checkbox, a threshold `input[type=number]` (empty; `min 0`, `max` 1 for a share, 1000 for the rate; `step any`), a percentile select starting on an empty placeholder, the template label, `threshold_text`; the experimental opt-in checkbox (`opt_in_label`, unchecked on every load); `#form-proposal` enabled only when every included row has both values; then `proposal_claim`, `proposal_non_claim`, one row per `rules[]` (label, `threshold_text`, `percentile_text`, `cited_value_text`, `state_text`), `minimum_rows` (label, `minimum_text`, `source_text`, `set_by`, each qualifier beside its record's label and badge), `xi_lab_minima_text` | `WITHHELD`: `PROPOSAL_WITHHELD`, form disabled; `NOTHING_SET`: `NO_RULE_HOLDS`; 422: the sentence |
| `#xi-panel` | a proposal reply is shown | `#accept-proposal` checkbox (unchecked on every load, label "I accept this proposal as my declaration"), mode select (`modes`), `#solve-xi`; `POST /api/opponent/xi` with the same declarations, `accept` from the checkbox, `minimums` `{}` | `accepted_text`, `minimum_in_force_rows`, `model_note`, `xi.status_text`, `objective_texts`, a table of `lineup_rows`, `requirement_rows` (label, `minimum_text`, `sum_text`, `shortfall_text`), `membership.groups` in served order, `ties_text`; `omitted_candidates` | `INFEASIBLE`: `Shell.infeasible`; not certified: `Shell.notCertified`; a proposal edit after a solve clears this panel (version rule) |
| `#ledger-slot` | after any POST | | `OpponentLab.render.ledger(prefix, declared, ledger)` for the record (`record`) and the XI reply (`xi`), each `Shell.ledger` with its ids rewritten exactly as OR-XI 8.1 rewrites them (whole attribute runs; throw when the kit's markup is not the expected one) | |
| `#not-measured-slot` | after the menu | | `Shell.notMeasured(not_measured)` | |

### 7.3 `/desk`

Eyebrow "Director's desk · the chain end to end"; h1 "One chain.<br>Every row sourced."; lede
"Declare an identity, the requirements it sets and the slot you are recruiting. The desk asks
Squad, Transfer, XI and Opponent Lab and lays their answers out in one ledger, with what none of
them measures beside it."

| Panel | Shown when | Request | Renders (server field) | States |
|---|---|---|---|---|
| `#desk-form` | always | `GET /api/desk/menu` on load; `GET /api/squad/clubs` for other clubs (the shipped route) | planning point select (flagship first, then clubs as served), formation, the identity table (`identity_policy.phrases`: phrase, state, sentence) and preset checkboxes (`presets`, labels as served; the experimental preset disabled until the opt-in is ticked), the opt-in checkbox, slot select (`recruitable` slots, empty placeholder: no slot), stress select (`stress_sizes` and "no stress"), league checkboxes, and a `<details>` "Per-match chain" (flagship only) with decision point, window, mode, the proposal templates as on `/opponent`, the accept checkbox; `#compose` | another club: the per-match `<details>` disabled with `DESK_MATCH_OTHER_CLUB` |
| `#scope-slot`, `#claim-slot`, `#warnings-slot`, banners | after a reply | `POST /api/desk/chain` on `#compose`, through `GP.tracker` for the status line | `scope_text`, `eligibility.banner` (the unreviewed banner outside Madrid), `claim`, `non_claim`, `statements`, every part's `warnings` in stage order | `chain_state` `PARTIAL`: each part's `state_text`; `INCONSISTENT`: `DESK_INCONSISTENT` as a notice |
| `#chain` | after a reply | | one section per `stages[]` in served order: heading; per part: `page_name` linked to `page_href`, `state` badge, `state_text`, `claim`, `non_claim`, `summary_rows` as a two-column list | `NOT_RUN` / `NOT_STARTED`: the sentence only |
| `#desk-ledger` | after a reply | | `Desk.render.ledger(declared, ledger)`: one table of declared rows ("Declared by you", grouped by family, origin mark) and one of computed rows with a "Source" column (`page_name`, linked) beside the kit's five, each cell drawn with the kit's own badge functions, rows in served order, `data-label` on every cell for the 650 px stacking; ids `desk-ledger-declared`, `desk-evidence-ledger` | no row: the kit's empty sentences |
| `#research-slot` | after the menu, and after a reply | | `GP.research` of `verdicts` and `research_statement` | |
| `#not-measured-slot` | after the menu | | `Shell.notMeasured(not_measured)` and `not_measured_closing` | |

### 7.4 Rules of the pages

- R10. JS computes no count, share, rate, interval, minimum, threshold comparison, eligibility,
  objective, membership or evidence class. Every number printed is a server string (`*_text`,
  `value_text`, `summary_rows[].value_text`) or a server integer on this allow-list, printed as
  is: `worlds` and `world_seed`; ids appear in attributes only. An outcome group's count reaches
  the desk page as the server's `value_text`. JS never sorts, filters or groups rows, never picks an entry of one list by
  an id from another, and never reorders parts. The two selections it makes are the opt-in's
  effect on which templates are enabled (by the server's `needs_experimental_opt_in`) and the
  flagship test for the per-match details (by the server's `scenario_id`).
- No ranking. No team list is ordered by anything but league, club name and team id; no part is
  highlighted, sorted, enlarged or coloured by size; no player list appears on the desk; the XI
  lineup is in formation order and the membership groups in their fixed order.
- Words. No word of `words_never_on_the_page` and no copy-guard token outside a named denial
  appears in the visible text of either page in any state (`shell.visible_text` over the
  rendered markup, 8.2). The page-written text (headings, labels, eyebrow, h1, lede, figure notes,
  the accept label) is in the render test's scan.
- Defaults. No rule, threshold, percentile, slot, decision point or opt-in is preselected; the
  window select and the stress select start on the server's default; no request that reads the
  corpus is sent before a button is pressed, except `GET /api/opponent/teams` and
  `GET /api/squad/clubs`, which read the match tables only.
- States. Loading (`Shell.loading`), withheld, empty, undecided, 422 (the server's sentence),
  429 (`Retry-After`), 503 (`Shell.errorText`); a `null` is never drawn as 0.
- Mobile. At 390 and 320 px the document has `scrollWidth <= clientWidth`; every table stacks at
  650 px and below by the `td::before{content:attr(data-label)}` pattern; the header nav of seven
  links and three separators fits (labs-shared.css:8-11 lays it out; section 11 asks the root to
  measure it).
- Ids are unique on each page; every `data-*` value written by the page is a plain word.
- Colour: gold (`rgb(201, 162, 39)`) marks no number and no part.

## 8. Tests

Oracles import nothing from the code they check (ROOT 4). Every rule test holds the interesting
outcome and its opposite. No test reads the corpus except the `slow` tests of 8.5, which skip
without it and run only after E-10's registration.

### 8.1 Unit tests, data-free

| File | Test | Asserts |
|---|---|---|
| `test_opponent_record.py` | `test_record_equals_the_oracle` | on synthetic events (built in the test with invented ids: two leagues of four teams, eight matches each, a penalty, a direct free-kick shot, an own goal, a red card, entries on every lateral cut of PIPELINE 3.5), every part count, share, window time and rate equals `tests/opponent_oracle.py`'s recount in `Fraction` |
| | `test_record_reads_the_one_state` | `estimator.state_at` monkeypatched to record its arguments: called once per subject per record, with `date` the declared day; a patched `state_at` that adds one event moves the record's count by one (the record has no second count) |
| | `test_matches_used_agree_with_the_state` | the listed valid matches' counts, added, equal the state's for every subject; a planted match on `D`'s day and one after are in neither, with `D` a date; a planted invalid match is listed with its reason text and adds nothing |
| | `test_no_event_is_none_never_zero`, `test_no_prior_match` | a team whose prior valid matches hold no S3 event has S3 shares `None`; a team with no prior valid match has every share and the rate `None` and the sentence |
| | `test_all_states_reads_its_own_table` | under `all_states` the counts come from `tables["all_states"]` and differ from `close_11v11` on the planted 2-0 match |
| | `test_loader_refuses_a_defective_sidecar` | a squads frame missing one team-match, a duplicate `game_id`: `RecordCorpusDefect`, never `ValueError` |
| | `test_loader_reads_only_its_columns` | `load_public` and `sidecar.load` monkeypatched: the column lists of 2.1 exactly; `verify` called before `load`; `xt=None` |
| | `test_record_available_follows_the_registry` | false on the shipped registry; true with seven planted `PENDING` records; false with six |
| `test_opponent_panel.py` | `test_constants_equal_the_config` | 3.1, against the registered config when present and the draft otherwise |
| | `test_world_draw_and_state_exclude_invalid_and_same_day_matches` | PIPELINE 12.3: the draw receives exactly the ids of the league's valid matches dated before `D`'s calendar day; a planted invalid match and a planted match on `D`'s day are not among them, and the state built for the point holds neither; both with `D` a date and with `D` a time of day after the planted kick-off (at the module function, which accepts a time) |
| | `test_offered_only_where_established` | `offered` under every registry state of 1.6 (planted records: unregistered, `PENDING`, `INCONCLUSIVE`, each NOT_ESTABLISHED token, `DEFENDER_SHAPE_SIGNAL` with figures), every window and dates on either side of `2018-01-01`; a LOCAL record never offers (ADR-0018) |
| | `test_estimate_is_the_estimators` | `served_composition`, `served_volume`, `shape_estimate`, `level_estimate` monkeypatched to return marked values: the panel serves exactly those (no formula of 4.2 is held here) |
| | `test_point_needs_the_reliability_bound` | `reliability_lower_bound` 0.69999 gives no point and the interval; 0.7 gives both |
| | `test_holes_are_counted`, `test_quantiles_are_linear_and_shared_worlds` | a team with prior events in few matches has holes counted; quantiles equal `np.quantile(..., method="linear")`; every subject of one request reads one `WorldWeights` (one call) |
| | `test_s5_ratio_is_never_served` | no served value equals the ratio of the S5 counts and no key or text names it except `S5_RATIO_NOTE` |
| | `test_group_non_claim_in_every_state` | every group's `non_claim` equals `REGISTRY_NON_CLAIMS[group]` under the unregistered registry (where the payload's `non_claim` is `""`), `PENDING` and every token; once a record exists, the record's `non_claim` equals the constant |
| `test_opponent_proposal.py` | `test_exact_threshold_comparison` | a share of exactly 2/5 holds at `0.4`; 0.3999... does not; the rate at its threshold holds |
| | `test_undecided_sets_nothing` | a cited share `None` gives `UNDECIDED` and no minimum |
| | `test_outcomes_follow_template_order` | rules sent in reverse order: the same reply |
| | `test_conflicting_percentiles_are_refused`, `test_same_percentile_is_one_minimum` | |
| | `test_qualifiers_follow_may_gate` | PIPELINE 12.3: a proposal citing a `DEFENDER_SHAPE_SIGNAL` record (no qualifier), a `PENDING` one (`proposal_sentence_not_tested`) and a NOT_ESTABLISHED one (`proposal_sentence_not_established`): one qualifier per cited record whose `may_gate` is false, beside its label, in `subject_groups` order, none merged or dropped; under `all_states` every qualifier is the first sentence |
| | `test_side_templates_need_the_opt_in` | `EXPERIMENTAL_OPT_IN_ERROR` without it |
| | `test_oracle_agrees` | rule states equal `tests/opponent_oracle.py`'s on 200 seeded synthetic records and thresholds, the boundary values included |
| `test_opponent_api.py` | `test_routes_answer_through_finalize` | with synthetic league tables, reference and match snapshot patched into the gated loaders: each route answers 200, the envelope of 5.4 holds every key, and the reply passes `runtime.finalize` (providers, keys with `BANNED_KEY_PARTS`, `scan_labels`) |
| | `test_every_constant_passes_the_copy_guard` | every constant of 5.6 and 6.5 under the format arguments the router uses, and the config sentences `panel.py` serves |
| | `test_words_never_on_the_page_are_never_served` | none of the five words in any served string of any reply in any state, outside provenance |
| | `test_withheld_before_registration` | shipped registry: record, proposal and XI (accept false) answer as 1.7 says, the league loader patched to raise is never called, and the XI with `accept: true` is 422 `ACCEPT_WHILE_WITHHELD` |
| | `test_badges_follow_the_registry` | planted `PENDING`: every badge `E-10 · RECORD ONLY · NOT RUN`; each token in turn: its badge; under `all_states`: `RECORD ONLY · NOT TESTED` |
| | `test_refusals` | an extra field; `team_id` "675", 675.0, true; a date `2018-5-6`, `2018-02-30`, `2016-01-01`; `percentile` 75.0, true, 80; a share threshold 1.5; a template twice; accept with no rule; a side template without the opt-in; entered and accepted proposed minima for one requirement: each 422 with its sentence and no input value; an unknown team and an unknown decision point: 404 |
| | `test_sidecar_failures_are_503` | `SidecarMissing`, `SidecarStale`, `SidecarMismatch`, `RecordCorpusDefect`: 503 `SIDECAR_UNAVAILABLE` (or the corpus sentence) |
| | `test_cache_key_moves_with_sidecar_and_registry` | a changed sidecar file identity and a planted registry record each change the key; the same request twice is a hit |
| | `test_xi_part_equals_api_xi_solve` | with the opt-in and a synthetic snapshot patched into both `decision_lab.snapshot` and `xi_extensions._match_snapshot`: `assignments`, `solution_status`, `objective_vector` and each `RequirementAssessment` equal `/api/xi/solve`'s with `bootstrap_worlds: 0`, for minima entered, a proposal accepted (its minima sent to `/api/xi/solve` as `format_plain` printed them) and a SATISFY infeasible case; without the opt-in `model_note` is served |
| | `test_unaccepted_proposal_changes_no_solve` | `decision_inputs` spied: the minima it receives exclude the proposal's unless `accept` is true |
| | `test_every_ledger_row_is_a_shell_row` | every terminal state of every route through `shell.ledger_row` and `shell.declared_row`; ids plain words; no `value_text` is `"0"` where no number exists |
| | `test_parts_in_declared_order_and_nothing_picked_out` | parts in `spec.part_names` order in every reply; no key or text says largest, most, least or a rank |
| | `test_import_reads_nothing` | a subprocess imports `galactico.api.opponent_lab` and `galactico.api.desk`: no `pandas`, `numpy`, `ortools`, `galactico.features.team`, `galactico.models.opponent`, `galactico.optimization.snapshots` module is loaded, and every gated loader's `cache_info().currsize == 0` |
| | `test_private_reuse_is_pinned` | names and signatures of `planning._built_once`, `_corpus_files`, `_digest`, `_minimum_text`, `_outward`, `xi_extensions._match_snapshot`, `_exact_sum`, `_lineup_rows`, `declare` |
| | `test_paths_are_new_and_unique` | the router serves exactly its six paths; none is served by another router |
| `test_desk_api.py` | `test_each_part_is_its_routes_reply` | with every loader patched to synthetic objects, each carried part's served fields equal the sub-route's reply to the same declarations through the TestClient, byte for byte as JSON |
| | `test_ledger_composition` | base rows once; other rows prefixed and in part order; declared rows de-duplicated within a family; XI additions' declarations are a subset of `match-xi`'s; a planted base-row difference gives `INCONSISTENT`, not stored; a planted declared-row clash is a 500 |
| | `test_desk_shows_no_e10_descriptor` | a planted record with distinctive share and count texts: none of its texts, no `cited_value_text`, no `rules`, no `proposal-rule-*` row in any desk reply; `DESK_NO_DESCRIPTOR` present |
| | `test_parts_run_when_declared` | no slot: brief and search `NOT_RUN` with `DESK_NO_SLOT`; another club with `match`: 422; `stress_k` null: no stress part; SATISFY infeasible without the opt-in: conflict `NOT_RUN` with its sentence |
| | `test_not_started_when_time_runs_out` | a patched clock: the first part whose ceiling exceeds the remaining budget and every later one `NOT_STARTED`, completeness `DEADLINE`, not stored |
| | `test_desk_takes_no_long_place` | `runtime.long_job` spied: never called with `desk.chain`; a stress part takes its own place and releases it |
| | `test_busy_and_absent_propagate` | a part's 429 is the desk's 429 with `Retry-After`; a part's 503 the desk's 503 |
| | `test_research_and_not_measured_are_plannings` | `research_statement` and `verdicts` equal `planning.verdict_reading()`; `not_measured` equals `planning.not_measured()` and begins with the nine of ROOT 2.3 in order |
| | `test_reply_passes_finalize`, `test_every_constant_passes_the_copy_guard` | |

### 8.2 Render tests (node; the harness of `test_shell_render.py`)

`test_opponent_render.py` and `test_desk_render.py` load `labs-shared.js`, `planning.js` (desk)
and the page's script, which touches no `document` when evaluated, and call `render` on replies
built by the real routers on synthetic data in every state (withheld, shown, offered, estimate
shown, point withheld, all holes, proposal formed, nothing set, accepted, infeasible, not
certified; desk composed, partial, not started, inconsistent, other club). They assert: no
`undefined`, `NaN` or `[object`; hostile strings in every server field escaped; every digit run of
the visible text (`shell.visible_text`) lies inside a server string printed at that place or is the
decimal form of an allow-listed integer (7.4), after removing the kit's badge `aria-label`s (the
OR-XI rule); parts, rules, rows, groups and stages appear in served order; no copy-guard token and
no word of `words_never_on_the_page` in the visible text, page-written text included; every
group's non-claim present in every state; ids unique; the ledger id rewrite throws on a changed kit
markup.

### 8.3 Page shell

`test_opponent_desk_pages.py`: each page's nav equals `shell.nav_markup(dest)` (after the root's
nav edit; until then it is `xfail` with that reason, never skipped silently), links
`labs-shared.css`, carries the footer credit, loads its scripts in the order of 7.1, and its inline
script opens with the header comment the planning pages carry (`test_planning_render.py:954-1021`
pattern). `opponent.css` and `desk.css` use only `op-`- and `desk-`-prefixed classes and ids or
selectors scoped under `#op-root` / `#desk-root` (the OR-XI 8.3 rule, so no shared element is
restyled).

### 8.4 e2e (corpus, CI)

`e2e/opponent.spec.js` (CI builds Spain's sidecar only, ci.yml:63): load `/opponent`; the menu
and teams GETs are the only requests before a press; choose the decision point "Real Madrid ·
before Barcelona" and load the record: every badge reads `E-10 · RECORD ONLY · NOT RUN` (or the
withheld state, by the registry state the spec reads from `/api/evidence/verdicts`), every group's
non-claim is visible, parts appear in declared order, no page error and no console error; choose
`all_states`: every badge reads `RECORD ONLY · NOT TESTED`; a league without a sidecar answers the
503 sentence; form a proposal with the opt-in and one rule, accept it, solve: eleven lineup rows,
the accepted text and the minima in force; untick accept and solve: the minima in force are the
defaults; the header nav marks `/opponent`; at 390 and 320 px no horizontal overflow.

`e2e/desk.spec.js`: load `/desk`; compose the flagship with defaults: the stages render in order,
search and brief read `DESK_NO_SLOT`, the ledger holds rows from Squad Lab, the not-measured panel
holds the nine of ROOT 2.3 first; declare a slot and compose again: the search part shows outcome
groups and no candidate name; declare the per-match chain at `madrid-2018-05-06`: the XI solve and
ceilings parts render, and no share text the `/api/opponent/record` reply of the same opponent
serves appears on the page (the spec fetches it and compares); choose another club: the
unreviewed banner shows and the per-match details are disabled; 390 and 320 px.

Screenshots: none is added by this work. If the root adds the two pages to
`e2e/screenshots.spec.js`, X14's rule applies: regenerated and inspected only where the corpus is
present, and only after E-10's registration (1.7).

### 8.5 Slow (corpus; after E-10's registration)

`test_reference_club_median_is_the_snapshot_normaliser` (4.3); `test_xi_part_equals_api_xi_solve`
on the real snapshot at both decision points; `test_record_build_time_and_memory` records, without
asserting a number, the cold build time of one league's tables, the record request time and the
process's peak RSS, for the ADR (5.1); `test_record_counts_against_build_match` compares the
`match__` columns of the cached table with `build_match(...).team_profiles` for five Spain matches
(E-10's own real oracle, PIPELINE 2.5, run here on the product loader's frames; it computes no
descriptor).

### 8.6 Not changed

Every existing test file passes unchanged except the nav and page tests the root edits (section 11).
A failure in any other is a defect of this work.

## 9. Hashes, fingerprints, provenance

| Object | Rule |
|---|---|
| descriptor fingerprints | `spec.fingerprint` of WP A, equal to `descriptor_fingerprints` (E-10's test); served under `provenance.descriptor_fingerprints` and printed in the ledger's `solver` cell |
| table version | `TEAM_MATCH_VERSION` (`team-match-table-v2`) in provenance |
| sidecar | `sidecar.provenance(league)` verbatim (schema version, tag mapping version, content hashes, raw digests, competition) |
| public files | the token listing of 5.3 (names, sizes, modification times), not a content hash; the cache key, not evidence |
| reference | `declared_minimum(...).reference_fingerprint` per proposed minimum |
| snapshot | `kernel.scrub_lineage(snap.provenance)`, as OR-XI 7.5 |
| registry | each subject's badge, so a reply says which registry state it was built under |
| line endings | every hash LF-normalised |
| result store | `runtime.source_fingerprint` hashes `optimization/**/*.py` and `api/*.py` only (runtime.py:330-342), so an edit to `models/opponent` or `features/team` would not move a stored file's key. No result store ships; section 11 asks the root to widen the set before one does |

## 10. Pre-merge review checklist

The reviewer signs each line before the root registers the routers.

1. No frozen file, no root-owned file and none of WP A's three modules is in the diff.
2. No module here holds a definition, zone, part, window, phrase, label or estimator formula of
   E-10: every one is read from WP A (`grep` for the cut values `21/25`, `19/100`, `2/3`, `1/3`,
   `2/5`, `3/5` and for `exp(` in the new modules finds none).
3. The record reads the one state (`estimator.state_at`); the panel calls the one estimator; no
   product module imports `galactico.validation` or `experiments`.
4. The registration gate of 1.7 is in code and tested; no test, spec or screenshot of this work
   reads the real corpus's descriptors before E-10's registration.
5. Every reply passes `finalize`; `providers` is exactly `["pappalardo"]`; no served string holds
   a word of `words_never_on_the_page`; the list itself is never served.
6. Every badge, statement, gate and figure comes from `verdicts`; the estimate is shown only where
   `may_gate` is true, behind the opt-in, from `2018-01-01`, in `close_11v11`; the point only at a
   reliability bound of at least 0.70; S5's ratio is never served.
7. The proposal has no default threshold or percentile, compares in exact arithmetic, never picks
   a part by size, carries the qualifiers of 4.4, stays HEURISTIC, and changes a solve only with
   `accept: true`, through `decision_inputs`; the parity test with `/api/xi/solve` passes.
8. No ranking: no list of teams or players is ordered by a record value or a solver output; the
   desk shows no candidate name and no E-10 descriptor.
9. The desk calls handlers in process, sequentially, takes no long place, and serves `NOT_RUN`,
   `NOT_STARTED` and `INCONSISTENT` states with their sentences; nothing is dropped silently.
10. JS computes no number and sorts nothing (the render tests pass); both pages pass at 390 and
    320 px.
11. The budgets of 5.1 and 6.2 are measured on the corpus after registration and the numbers are
    in the ADR before the pages are linked from the nav.

## 11. Requests to the root

| File | Change |
|---|---|
| `galactico/api/player_lab.py` | after `app.include_router(xi_extensions_router)` (player_lab.py:61): `from .opponent_lab import router as opponent_router` and `from .desk import router as desk_router` with the other imports, then `app.include_router(opponent_router)` and `app.include_router(desk_router)`. Both import nothing heavy at import (8.1) |
| `galactico/api/shell.py` | `Destination` gains `sr_suffix: str = " Lab"`, and `nav_markup` writes `f'<span class="sr-only">{destination.sr_suffix}</span>'` only when it is non-empty (the five shipped links keep their bytes); `DESTINATIONS` gains `Destination("opponent", "/opponent", "Opponent", "matchday")` after XI and `Destination("desk", "/desk", "Desk", "desk", sr_suffix=" (Director's desk)")` last; the module docstring's "Five destinations ship" becomes seven. In the same commit as the two routers, never before (a nav link to a missing page is a 404, shell.py:11-12) |
| `web/match.html`, `web/xi.html`, `web/squad.html`, `web/transfer.html` | the nav block replaced by the new `nav_markup(dest)` bytes, nothing else |
| `web/index.html` | two links in its own nav (index.html:189-199), `/opponent` and `/desk` |
| `web/labs-shared.css` | only if the 320 px check of seven links and three separators overflows (labs-shared.css:8-11) |
| tests that pin the nav | `tests/test_shell_payloads.py:30-42` (seven hrefs and dests, three separators, the visible text with "Opponent Lab" and "Desk (Director's desk)", no `opponent`/`desk` exclusion), `:53-56` (parametrise with names that are still not destinations), `:59-79` (items carry `d.sr_suffix`); `tests/test_web_shell.py:19` (`PAGES` gains `opponent` and `desk`); `tests/test_shell_render.py:312-369` (eight header anchors); `tests/test_xi_extensions_render.py:843-870` (`SHIPPED_XI_HTML` re-pinned after the nav edit: the five additive edits are unchanged); any e2e assertion that counts nav links |
| `.github/workflows/ci.yml:69` | add `e2e/opponent.spec.js e2e/desk.spec.js` to the playwright command |
| `galactico/api/runtime.py:330-342` and `tests/test_lab_runtime.py:399-408` (recommended) | `source_fingerprint` also hashes `models/opponent/*.py` and `features/team/*.py`, and the pinned set says so |
| `DECISIONS.md` | ADR-0031 "Opponent Lab and the Director's desk": Problem (ROOT 2.3's two surfaces unbuilt; KNOWN_LIMITATIONS "not implemented"), Decision (sections 1.7, 2.2, 3, 4, 6.3 and 6.4 of this file), Evidence (the oracle and parity tests, the measured times and memory of 8.5), Alternatives rejected (a record before E-10's registration; a second estimator; a proposal with default thresholds; comparing two parts of a record; client-side composition of the desk; the desk showing descriptors; carrying declarations across pages by URL), Relation to ADR-0018, ADR-0019, ADR-0024 |
| `KNOWN_LIMITATIONS.md` | "Product scope" (:418-422): Opponent Lab and the desk are implemented, with what they are; "The tag sidecar holds facts, and nothing has read it yet" (:271-283): Opponent Lab reads cards, own goals, goals and the sheet's dismissals, after `verify`; new entries: a record is not adjusted for opponents or strength and cannot tell funnelling from failing to close (H14); a proposal is a declared HEURISTIC policy; the per-match chain exists at two Madrid decision points only; the desk is sequential, can take its budget plus one build, and holds two of the sixteen places; a league without a built sidecar has no record (CI builds Spain only) |
| `README.md`, `ARCHITECTURE.md` | the three model modules, the two routers and the six web files in the module tables; the two labs in the product list |
| `docs/research/north-star/README.md` | a row for this file: draft, not attacked, nothing built |
| E-10's registration and results commits | nothing extra: the tests of this work read the badge from the registry and assert explicit states only on planted records, so neither commit needs to edit them (PIPELINE 13's list stays sufficient) |

## 12. Reconciliation

**With E-10's PIPELINE.** Sections 2 and 3 are used by name only (0.5). Section 12.3 is
implemented in `models/opponent/panel.py` (3.1 explains why that module is "the Opponent Lab
module" of 12.3); its three listed tests are `test_world_draw_and_state_exclude_invalid_and_
same_day_matches`, `test_constants_equal_the_config` and `test_group_non_claim_in_every_state`,
and its proposal test is `test_qualifiers_follow_may_gate`. Section 13's desk rule is met more
strictly (6.4). The product consequence table of the protocol is 1.6, with the "no record" row's
counts withheld (DISSENT 1).

**With OR-XI.** The per-match XI part uses `xi_extensions.declare` (the opt-in rule) and its gated
snapshot; the desk composes the four exact additions by their handlers, so their claims, ledgers
and refusals are OR-XI's own. The opponent XI is XI Lab's solver, called once, as
`/api/xi/solve` calls it; D5/D6 forbid a loop of solves, not one.

**With the planning surfaces.** The desk passes `PlanningInputs` unchanged to Squad and Transfer
Lab, carries their `research_statement` reading and their not-measured list, and adds no planning
sentence. D4 holds: progression alone unless the reader opts in.

## DISSENT

1. **The record is withheld before E-10's registration.** The E-10 draft's product table has a
   row "no record (before registration) · RECORD ONLY · NOT TESTED · nothing · counts OBSERVED,
   shares and rates DERIVED" (preregistration.md, "Product consequence"), which reads as a record
   shown before registration. This file withholds it (1.7). Evidence: R5 ("computing any outcome
   statistic is not [allowed]" during design; E-10 is a prospective plan on reused data); the
   protocol's own prior-exposure table, which states that no conceded split by lateral third and
   no team-season composition has been served (preregistration.md:80) and rests criterion (f) on
   three leagues with no such exposure (:86); PIPELINE 2.5, which lets E-10's real oracle run only
   after registration and compute no descriptor. A served record of every team of five leagues is
   the composition E-10 tests, and every person who looks at it before the freeze is exposed. If
   the root rules otherwise, the record ships from the merge and the E-10 registration commit adds
   an Opponent Lab row to the prior-exposure table naming who saw what; the gate's code is then
   `record_available() -> True` and nothing else changes.
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

## OPEN QUESTIONS

1. **Ship order.** 0.2 assumes E-10 registration, then its pipeline commit (WP A), then this work.
   If the root wants the pages earlier, WP A must be built before registration (PIPELINE 13 puts
   it after) or this work cannot import its definitions. The gate of 1.7 keeps either order safe;
   which order is the root's.
2. **Proposal defaults.** Should the 75th percentile, the planning presets' convention, be
   pre-filled for the percentile (never for the threshold)? This file says no (DISSENT 2).
3. **The desk's one-bit statement about a record.** A minimum the proposal set says that some
   declared rule held, that is, that the record reached the reader's threshold. No record value is
   shown. Does that satisfy PIPELINE 13's "no quantity on this page is an E-10 descriptor" while
   `planning_research_sentence` is served, or should the desk then show the minima in force with
   origin "Your accepted proposal" and nothing about which rules set them?
4. **A squad-path proposal.** Should a later release let a proposal set a planning minimum through
   `RequirementDeclaration(source="LEAGUE_PERCENTILE")`, and against which opponent at a
   season-end planning point?
5. **Units of the reference at a match cutoff.** 4.3 rests on the reference's club median at
   `2018-05-06` and `2018-04-08` equalling the match snapshot's normaliser. If the slow test fails
   (the two read the corpus by different code paths), the proposal's minima are not in the solve's
   units and the proposal is not shipped until that is reconciled.
6. **Budgets.** 30, 30, 45 and 180 seconds are first numbers. A cold record build runs
   `sidecar.verify` (it hashes three tables) and `build_team_match_table` for two windows; whether
   that fits inside 30 seconds, and the peak memory, are measured after registration (8.5).
7. **A floor for printing shares.** A share from three prior matches is printed with its sample.
   Should shares print only from `minimum_prior_matches` (8) valid prior matches, as E-10 predicts
   only from eight?
8. **"What the team did" beyond E-10.** Only E-10's own-actions group is shown for it. The team's
   own entries by lateral third would be the same event sets with side `for`; they are not shown
   because no protocol registers them. Should a later protocol register them?
9. **The audit frame.** `build_team_match_table` returns per-match drop counts at sentinels and
   out-of-range locations. Should the record show, per team, how many of its prior entries were
   dropped for a location, as a sample note?
10. **E-09's exposure.** The record serves team-level defensive-action locations and conceded shot
    locations, near E-09's `opp_half_defensive_actions` and shot candidates. Should the gate of 1.7
    also wait for E-09's registration, or should E-09's registration commit state whether anyone
    saw an Opponent Lab record?
