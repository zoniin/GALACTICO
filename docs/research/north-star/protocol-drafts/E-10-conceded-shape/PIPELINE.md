# E-10 pipeline: what to build, exactly

Companion to `preregistration.md` (the protocol), `config.json` (every number) and
`descriptor_test_vectors.json` (the frozen definitions). This file fixes module paths,
signatures, column names, artifact shapes, hashes, tests, the synthetic gate, the registry
records and the commands. **It is frozen with them:** it is registered byte for byte as it
stands, its `lf_sha256` is `pipeline_spec_sha256` in the config, and the runner refuses a
mismatch. Where this file and the protocol disagree, the protocol wins and the disagreement is
a defect to report.

Claim of the pipeline: it computes the frozen estimands of E-10 from the neutral frames and
the tag sidecar, deterministically, with no number entering from prose. Non-claim: nothing here
decides football; a green suite says the code matches the protocol on synthetic seasons, not
that the protocol is right about real ones.

**Tier rule.** E-10 is PUBLIC; its replication arm is LOCAL_LICENSED. Only
`galactico/validation/conceded_shape_sb.py` reads StatsBomb files, and only through
`galactico.validation.sb_reader`. Nothing that reads StatsBomb is imported by `galactico/api`,
`galactico/optimization`, `galactico/profiles`, `galactico/match_lab`, `galactico/models` or
`galactico/features`. No code writes a LOCAL-derived number, interval, coefficient, digest or
identifier anywhere but `replication.local_artifact`, which is never committed (ADR-0018);
`analysis.md` prints the replication's numbers, with the credit, only as section 12.4 allows.

## 0. Files, owners, order

| WP | Owns (all new unless noted) | Depends on |
|---|---|---|
| A | `galactico/features/team/descriptors.py`, `galactico/features/team/match_table.py`, `galactico/features/team/estimator.py`, `galactico/features/team/__init__.py` (exists, empty), `tests/test_team_descriptors.py`, `tests/test_team_match_table.py`, `tests/test_team_estimator.py` | the shipped interfaces of section 1 |
| B | `galactico/validation/conceded_shape.py`, `tests/test_conceded_shape_engine.py`, `tests/test_conceded_shape_rule.py` | the estimator's signatures (3.8) and the row contract (4.1) only |
| C | `galactico/validation/conceded_shape_synthetic.py`, `tests/test_conceded_shape_synthetic.py` | table schema (2.2), row contract (4.1) |
| D | `experiments/run_conceded_shape.py`, `galactico/validation/conceded_shape_sb.py`, `tests/test_conceded_shape_experiment.py`, `tests/test_conceded_shape_sb.py` | A, B, C public names. The LOCAL module is named `_sb` because its path is a key of `source_hashes` in `results.json` (section 7.3) |
| root | `experiments/preregistered/E-10-conceded-shape/{preregistration.md, config.json, PIPELINE.md, descriptor_test_vectors.json}` (registration), `synthetic_gate.json` (own commit), `results.json` (copied unchanged from `output_results`), `analysis.md` (results commit); the registry records and the shared files of section 13 | all |

A, B and C can be written in parallel from this document: B and C meet A only through the
table schema of 2.2, the row contract of 4.1 and, for B, the estimator's signatures of 3.8, all
frozen here. Research modules
(`galactico/validation/conceded_shape*.py`, `experiments/run_conceded_shape.py`) are never
imported by `galactico/api`, `galactico/models`, `galactico/features`, `galactico/optimization`
or `galactico/profiles`. `galactico/features/team/*` is product-side code and imports nothing
from `galactico.validation` or `experiments`. The import runs one way only (ROOT 2.9 Z3): the
research pipeline imports `galactico.features.team` (the descriptors, the match table and the
estimator), and no product module imports the research pipeline. The estimator of E-10's
descriptors is one object, `galactico/features/team/estimator.py` (3.8): the engine (B) and
Opponent Lab's panel (12.3) both call it, and neither holds a second implementation of it.

**Registration-time edits** (section 13). `config.json`, `PIPELINE.md` and
`descriptor_test_vectors.json` are registered byte for byte. `preregistration.md` is registered
after one edit and no other: the DRAFT banner (the one-line block quote under the title, which
holds the only relative links) is replaced by the one line
`> References such as ROOT 2.5 or R12 point to [ROOT-DECISIONS.md](../../../docs/research/north-star/ROOT-DECISIONS.md); the working notes they cite are described in the [README](../../../docs/research/north-star/README.md) beside it.`
The protocol draws no logo: it prints no figure formed from StatsBomb data. The only E-10
document that draws one is `analysis.md`, from
`experiments/preregistered/E-10-conceded-shape/`, by the path
`../../../docs/assets/statsbomb/statsbomb-logo.png` (section 12.4). `REVIEW-RECORD.md` stays in
the draft folder as the record of review; the four protocol files there become one-line
pointers to the registered directory.

**Engineering.** `from __future__ import annotations`; frozen dataclasses; full type hints;
`__all__`; numpy and pandas only (no scipy); ruff clean; paths anchored at
`Path(__file__).resolve().parents[n]`; module docstrings state claim and non-claim. **No
function takes a default for a value that is in config** (a threshold, a list, a seed, a rule
switch): product-side modules hold such values as module constants that a test ties to the
config (7.5), and research modules receive them from the config. Config keys that restate a
rule as a sentence are read by assertions, not branches.

**Key names.** No key at any depth of `config.json`, `descriptor_test_vectors.json`,
`synthetic_gate.json` or `results.json` contains `statsbomb`, `pappalardo` or `wyscout` in any
letter case (`forbidden_result_key_names`) or starts with `SB_`; a key that concerns one
provider has `sb` or `wy` as one `_`-separated part (`key_naming`). `tests/test_licensing.py`
enforces the first name and the prefix on every JSON file under `experiments/`, three levels
deep; the runner test of section 9 enforces all three key names at every depth on the four
files, with `provenance.config` echoed (a key-name check; the substring scan of section 8 is a
different check and reads the payload without the echo). None of the source paths of section
7.3 holds any of the three names.

**Licence-guard traps.** Never write, in any committed file, a double-quoted
`possession_team`, `freeze_frame`, `obv_total_net` or `shot_statsbomb_xg`, nor a double-quoted
`eventId`, `subEventId`, `matchPeriod` or `tagsList` followed by a colon. Every test payload is
generated from a seed with invented ids and coordinates.

**Reused, unchanged** (section 1 gives the calls): `galactico.storage.public.load_public`;
`galactico.ingestion.sidecar` (`load`, `attach`, `verify`, `provenance`,
`SIDECAR_SCHEMA_VERSION`, `TAG_MAPPING_VERSION`); `galactico.validation.digests`;
`galactico.reliability.confound.discriminant_validity`;
`galactico.reliability.core.AxisReliability` (house bound, reported only);
`galactico.domain.verdicts`; `galactico.domain.thesis.banned_key_paths` (the runner's key
check); `galactico.validation.sb_reader` (LOCAL module only);
`galactico.optimization.snapshots.league_world_weights` (served panel only);
`galactico.match_lab.model.build_match` and `galactico.models.xt.grid` (oracle only);
`galactico.providers.base.assert_may_host`. Not reused, and why:
`forecast_evaluation.paired_week_interval` weights rows equally, has no strata and its file is
hash-pinned in E-07/E-08; `partial_history._permutation_maps` is private and keyed on player
strata.

## 1. Shipped interfaces (verified against the code on 14 October 2026)

| # | Call | Used for | When it raises |
|---|---|---|---|
| I1 | `load_public(league, tables=("actions", "matches"), action_columns=ACTION_COLUMNS)` with `ACTION_COLUMNS = ("game_id", "period", "seconds", "team_id", "player_id", "type", "subtype", "start_x", "start_y", "end_x", "end_y", "success", "key_pass", "interception", "event_id")`; `matches` gives `game_id, competition, date, home_team_id, away_team_id` | every event and the calendar | `LicenseViolation`, `FileNotFoundError`: refusal before the run |
| I2 | `sidecar.verify(league)`, then `sidecar.load(league, "events", columns=["event_id", "card", "own_goal", "goal_on_scoring_event"])`. The table is dense: one row per event that has a position, the `event_id` set of `actions.parquet` (ADR-0028) | cards, own goals, goals | `SidecarMissing`, `SidecarStale`, `SidecarMismatch`: refusal before the run |
| I3 | `sidecar.attach(actions, events, ["card", "own_goal", "goal_on_scoring_event"])`, the only sanctioned join | the joined frame | `SidecarMismatch` (an action row without a sidecar row, or a repeated id): refusal before the run; there is no per-match "sidecar missing" reason |
| I4 | `sidecar.load(league, "matches", columns=["game_id", "home_score", "away_score", "home_coach_id", "away_coach_id"])` (scores `int16` on disk, cast to `int64`; coach ids `Int64`, null where the raw value is 0) | goals check, points, goal difference; the coach ids for the coverage count only | as I2 |
| I5 | `sidecar.load(league, "squads", columns=["game_id", "team_id", "player_id", "red_minute"])` (`Int16`, null where the sheet has none); `sheet_dismissals` = one row per `(game_id, team_id)` of `matches`, the count of its rows with `red_minute` not null (0 when it has rows and none is set). A team-match with no `squads` row is a refusal before the run (7.2) | `dismissals_mismatch` | as I2 |
| I6 | `sidecar.provenance(league)`, `SIDECAR_SCHEMA_VERSION`, `TAG_MAPPING_VERSION` | `results.json` provenance | as I2 |
| I7 | `lf_sha256(path)`, `lf_sha256_text(text)` | every text hash | |
| I8 | `discriminant_validity(y, X, key=..., confound_names=strength_covariates, top_k=strength_top_k, ties=strength_tie_policy, max_variance_explained=strength_variance_explained_ceiling, min_rank_correlation=strength_spearman_floor, min_top_k_survival=strength_top_k_survival_floor)`, called twice per coordinate (`strength_survival_tails`): `upper` on `y`, `lower` on `-y`, the same `X` | criterion (g): `upper.passed and lower.passed` for every coordinate, never the defaults. The audit counts survivors among the `k` largest values only (`np.argsort(...)[-k:]`) and checks a tie at the `k`-th largest place only, so the second call is what reads the other tail | |
| I9 | `AxisReliability(key, R, n, 0, season_label, confidence=house_reliability_confidence).interval` | the house bound, reported only. A test asserts `galactico.reliability.core._CRITICAL_VALUES[house_reliability_confidence] == house_reliability_critical_value` (a private member read by the test only, the form of ROOT 2.7 X9) | |
| I10 | `VerdictRecord`, `Outcome`, `Figure`, `derive`, `badge_text` | registry records (section 12) | constructor rules V1 to V7 |
| I11 | `sb_reader.read_matches(root, folder)`, `read_team_sheets(root, folder, ids, cap=..., regulation_periods=sb_regulation_periods, goalkeeper_position=..., dismissal_card_types_exclude=sb_sheet_card_types_not_dismissal, spell_end_reason_contains=...)`, `read_events(root, folder, ids, scale=sb_location_scale)`, `iter_events(root, folder, ids)`, `folder_vocabulary(root, folder)`, `folder_manifest(root, folder)` | the replication's frames (section 6); the folder digests the local artifact records | per its docstrings (`read_events` raises `ValueError` on a timestamp that is not `HH:MM:SS.mmm`); any exception there is `FAILED_RUN` |
| I12 | `league_world_weights(game_ids, worlds, seed, scheme="LEAGUE_MATCHES")` | the served panel's interval (section 12.3) | |
| I13 | `build_match(...).team_profiles` | the oracle (2.5) | |
| I14 | `tests/test_research_firewall.py::RESEARCH_PIPELINES` | firewall | root appends `conceded_shape`, `conceded_shape_synthetic`, `conceded_shape_sb` in the pipeline commit, not before (`test_the_lists_name_modules_that_exist`) |

`read_team_sheets` needs a minutes cap, a goalkeeper position and a spell-end string that
E-10 never uses beyond the `dismissed` column; the module passes
`replication.sb_team_sheet_arguments`, which holds E-11's frozen values for them, and
`replication.sb_sheet_card_types_not_dismissal` (E-11's `sb_dismissal_card_types_exclude`).
No keyword has a default. **Cross-reference to E-11.** E-11 grades
`final_third_entries` (+ left, centre, right) with the same cuts. E-10 does not import E-11's
definitions, so by E-11's own rule ("Definitions belong to this file") an E-11 token is not a
token for an E-10 descriptor; E-10's replication is a within-provider rerun of its own frozen
rule.

## 2. `galactico/features/team/match_table.py`

Module docstring: claim = counts of declared event sets per team and match, for and against,
in a declared match state, with the defending-frame mirror applied by the descriptor that reads
the column; non-claim = no rate, no share, no opinion about defending.

### 2.1 Signatures

```python
TEAM_MATCH_VERSION = "team-match-table-v2"

def location_valid(x: pd.Series, y: pd.Series, *, sentinels: Sequence[tuple[float, float]],
                   coordinate_range: tuple[float, float]) -> np.ndarray: ...
def match_validity(actions: pd.DataFrame, matches: pd.DataFrame, match_meta: pd.DataFrame,
                   sheet_dismissals: pd.DataFrame, *, regulation_periods: Sequence[str],
                   dismissal_cards: Sequence[str]) -> pd.DataFrame: ...
def match_state(actions: pd.DataFrame, matches: pd.DataFrame, *,
                regulation_periods: Sequence[str], dismissal_cards: Sequence[str],
                ) -> tuple[pd.DataFrame, pd.DataFrame]: ...   # (state, incidents)
def period_ends(actions: pd.DataFrame, *, regulation_periods: Sequence[str]) -> pd.DataFrame: ...
def window_mask(actions: pd.DataFrame, state: pd.DataFrame, window: Window) -> np.ndarray: ...
def window_seconds(incidents: pd.DataFrame, period_ends: pd.DataFrame,
                   window: Window) -> pd.Series: ...
def build_team_match_table(actions: pd.DataFrame, matches: pd.DataFrame, *,
                           columns: Sequence[Column], window: Window,
                           match_meta: pd.DataFrame, sheet_dismissals: pd.DataFrame,
                           regulation_periods: Sequence[str], dismissal_cards: Sequence[str],
                           sentinels: Sequence[tuple[float, float]],
                           coordinate_range: tuple[float, float],
                           xt) -> tuple[pd.DataFrame, pd.DataFrame]: ...
```

`actions` is the joined frame of I3: the columns of `ACTION_COLUMNS` plus `card`, `own_goal`,
`goal_on_scoring_event`. `event_id` is `int64` for Wyscout and `str` for StatsBomb, one type per
call. `matches` needs `game_id, competition, date, home_team_id, away_team_id`; `match_meta`
needs `game_id, home_score, away_score` (`int64`); `sheet_dismissals` needs `game_id, team_id,
dismissed_players` (`int64`, 0 for a team the sheet lists without one), one row for each team
of each match of `matches`; a team-match without a row raises `ValueError` (the runner refuses
such a sidecar before the run, 7.2, so the raise is a guard). `xt` is `None` or a surface; it
has no default. The neutral `goal` column is not read. Inputs are never mutated. Output does
not depend on input row order. Callers in product code pass the constants of `descriptors.py`
(3.7); research callers pass the config's values.

`match_state` returns `state`, aligned to the index of `actions` (`game_id`, `time_key`,
`home_goals_before`, `away_goals_before`, `dismissals_before`, all `int64`), and `incidents`, one
row per goal or dismissal incident in a regulation period (`game_id`, `period`, `seconds`,
`time_key`, and the `int64` indicators `home_goal`, `away_goal`, `dismissal`, exactly one of them
1). `period_ends` returns one row per `(game_id, period)` of `regulation_periods` that has a row:
`game_id`, `period`, `last_second` (the largest `seconds` of the period's rows). `window_seconds`
returns a `float64` series indexed by `game_id`.

### 2.2 Output schema (frozen: WP B, C and Opponent Lab rely on it)

`table`, one row per `(game_id, team_id)`, sorted by `(date, game_id, team_id)`:

| Column | dtype | Meaning |
|---|---|---|
| `game_id`, `team_id`, `opponent_id` | int64 | |
| `competition` | str | from `matches` |
| `date` | str | as in `matches` (callers normalise to the day) |
| `is_home` | bool | |
| `window` | str | `Window.key` |
| `valid` | bool | match validity (2.4); identical for both rows and for every window |
| `invalid_reason` | str | `""` when valid; the first failing reason otherwise |
| `window_seconds` | float64 | time in the window state; NaN when invalid |
| `goals_for`, `goals_against` | int64 | the sheet's full-time score (`match_meta`), for every match, valid or not |
| `match__recorded_actions` | int64 | the team's rows in every period except `P` |
| `match__completed_passes` | int64 | rows with `type == "pass"` and `success == True`, every period except `P` (the `progression` numerator filter Match Lab counts) |
| `match__shots` | int64 | rows with `type == "shot"` or `subtype` in (`free_kick_shot`, `penalty`), every period except `P` (Match Lab's rule; set-piece shots included) |
| `match__key_passes` | int64 | the completed passes above with `key_pass` true |
| `match__interception_flags` | int64 | rows of any type with `interception` true |
| `match__positive_xt_gain` | float64 | only when `xt` is not `None`; sum of `max(0, xT(end) - xT(start))` over the completed passes above with **no** location filter, exactly as Match Lab computes it. An oracle aid, never a descriptor input |
| `for__<event_set>` and `for__<event_set>__<partition>__<part>` | int64 | the team's own events in the window, one column per requested `Column` (3.1 `Column.name`) |
| `against__...` | int64 | the opponent's `for__` column of the same match, **part names unchanged** (acting team's frame) |

`match__completed_passes` is also the input of the V1 covariate `completed_pass_share`, so the
oracle of 2.5 covers it. The `match__` columns are computed for every match, valid or not, as
`goals_for` is (the oracle reads arbitrary matches). The `for__` and `against__` counts are 0,
not NaN, for a valid match with no qualifying event, and 0 for an invalid match (callers must
use `valid`). The table never renames `att_left` to `def_right`: the mirror lives in the
descriptor (3.4), in one place.

`audit`, one row per `game_id`: `valid, invalid_reason, home_goals_events, away_goals_events,
home_goals_meta, away_goals_meta, home_dismissed_events, away_dismissed_events,
home_dismissed_sheet, away_dismissed_sheet, goal_incidents, dismissal_incidents,
first_dismissal_period, first_dismissal_seconds, period_seconds_1H, period_seconds_2H,
events_in_window, events_all_states`, and one `dropped_location__<event_set>` per event set
(rows that matched the clauses and the window but whose needed location failed
`location_valid`).

### 2.3 State and window

- Time key of a row: `(1 + position of period in regulation_periods) * 100000 + seconds`. Rows
  in other periods are in no window and enter only `match__` columns (never period `P`).
- Goal incidents (`goal_incident_rule`): a row with `own_goal` true is a goal of the other team
  of the match; otherwise a row with `goal_on_scoring_event` true is a goal of the acting team.
  Own goal first, so a row is credited once. This is Match Lab's timeline rule (`goal` on any
  row other than a save, own goal first); `goal_on_scoring_event` already excludes save
  attempts and the shootout.
- Dismissal incidents: rows whose `card` is in `dismissal_cards`.
- State of a row: counts of incidents with a **strictly smaller** key (`np.searchsorted(...,
  side="left")` on the sorted incident keys of the match). Same-second rows are in the earlier
  state; the result cannot depend on row order.
- `window_mask`: regulation period, and `dismissals_before == 0` if `eleven_v_eleven`, and
  `abs(home_goals_before - away_goals_before) <= max_abs_goal_difference` if it is not `None`.
- `window_seconds`: per period, breakpoints `0`, the incident seconds of that period, and the
  period's last event second; on each interval `(a, b]` the state is that of incidents with
  key `<= a`; sum `b - a` where the window state holds. A loop over matches is acceptable here
  (a match has few incidents); every per-event computation is vectorised.

### 2.4 Validity (once per match, fail closed, never repaired)

`match_validity` decides each match once, for every window and every model
(`validity_scope`); `build_team_match_table` calls it and copies the result to both rows under
every window. Reasons in the order of `validity_reasons`, the first that applies recorded:

| Reason | Rule |
|---|---|
| `period_missing` | no row in one of `regulation_periods` |
| `clock_invalid` | a non-finite or negative `seconds` in regulation. It cannot fire on either provider and is kept as a guard: the Wyscout adapter writes a missing clock as 0.0, so a missing clock places the event at the kick-off; `sb_reader` parses each timestamp or raises, and a raise in the replication is `FAILED_RUN` (I11) |
| `goals_mismatch` | full-time goals under `goal_incident_rule`, regulation only, differ from `match_meta` |
| `dismissals_mismatch` | `dismissal_check`: for either team, the number of distinct `player_id` with a regulation row whose `card` is in `dismissal_cards` differs from `sheet_dismissals.dismissed_players` |

A card on a raw event without a position never reaches the frames (the adapter and the sidecar
both leave such events out), which is what `dismissals_mismatch` catches. Duplicate `game_id`
in `matches` or `match_meta`, a `team_id` that is neither side of its match, or a match with
no `match_meta` row raise `ValueError`; so does a window that needs state when `own_goal`,
`goal_on_scoring_event` or `card` is absent from `actions`. Results of invalid matches still
count on the sheet (`goals_for`, `goals_against`).

### 2.5 Oracle

`match__recorded_actions`, `match__completed_passes`, `match__shots`, `match__key_passes`,
`match__interception_flags` and (with `xt`) `match__positive_xt_gain` must equal the
`team_profiles` metrics `recorded_actions`, `completed_passes`, `shots`, `key_passes`,
`interceptions`, `progression` of `build_match(...)` for the same match: integers exactly, the
xT sum within `1e-9`. `build_match` is an independent code path (per-match, per-row loops). It
needs more than the table does: the action column `provider`, the `lineups`, `players`
(`player_id`, `name`, `position`) and `teams` (`team_id`, `team_name`) frames, a `match` dict
with `game_id`, `home_team_id`, `away_team_id` and a `label` (any string; not compared), and
`provenance={"provider": ...}`. The synthetic oracle builds them; the real one reads them
through `load_public(league, tables=("actions", "matches", "lineups", "players", "teams"))` with
every action column. The synthetic oracle includes a penalty, a direct free-kick shot and an
interception flag on a non-duel row. The real-data oracle (`slow`) requests no descriptor column
(`columns=()`), reads five matches per league, and may run only after the registration commit
(R5): it compares counts Match Lab already serves and computes no descriptor.

## 3. `galactico/features/team/descriptors.py` and `estimator.py`

One object yields the number, the sentence and the fingerprint. Nothing here is added to
`spec.SPECS` or `CONSTRUCTS`.

### 3.1 Dataclasses (all frozen)

```python
DESCRIPTOR_SCHEMA = "team-descriptor-v1"

class Bound:      axis: str            # "x" | "y", acting team's frame, unit square
                  op: str              # "<" | "<=" | ">" | ">="
                  value: Fraction
                  token -> f"{axis}{op}{value.numerator}/{value.denominator}"
                  mask(values: np.ndarray) -> np.ndarray    # values <op> float(value): fraction_rule

class Zone:       key: str; phrase: str; bounds: tuple[Bound, ...]     # AND; phrase holds {poss}
                  token -> f"{key}({'&'.join(b.token for b in bounds)})"

class Clause:     types: tuple[str, ...]; subtypes: tuple[str, ...]
                  completed: bool | None; flags: tuple[str, ...]
                  token -> f"{','.join(types) or '*'}:{','.join(subtypes) or '*'}:"
                           f"{'completed'|'failed'|'any'}:{','.join(flags) or '-'}"

class EventSet:   key: str; phrase: str; clauses: tuple[Clause, ...]    # OR, row counted once
                  start_in: Zone | None; start_not_in: Zone | None
                  end_in: Zone | None; needs: tuple[str, ...]          # of "start", "end"
                  token -> f"{key}[{'+'.join(c.token)}|start_in={z}|start_not_in={z}|end_in={z}"
                           f"|needs={','.join(needs) or '-'}]"          # z = zone.token or "-"
                  mask(actions) -> np.ndarray          # clauses, zones; NOT location validity
                  located(actions, *, sentinels, coordinate_range) -> np.ndarray
                  sentence(side) -> str

class Part:       name: str; phrase: str; bounds: tuple[Bound, ...]     # () = remainder, last
class Partition:  key: str; anchor: str ("start"|"end"); parts: tuple[Part, ...]
                  token -> f"{key}@{anchor}[{';'.join(name=('&'.join(b.token) or 'otherwise'))}]"
                  assign(actions) -> np.ndarray of part names   # first matching part wins

class Column:     side: str ("for"|"against"); event_set: EventSet
                  partition: Partition | None; part: str | None
                  __post_init__: partition.anchor must be in event_set.needs, else ValueError
                  name  -> f"{side}__{event_set.key}" + (f"__{partition.key}__{part}" if part else "")
                  token -> f"{side}/{event_set.token}" + (f"/{partition.token}:{part}" if part else "")
                  sentence() -> str

class Window:     key: str; phrase: str; periods: tuple[str, ...]
                  eleven_v_eleven: bool; max_abs_goal_difference: int | None
                  token -> f"{key}(periods={','.join(periods)};eleven_v_eleven={bool};"
                           f"max_abs_goal_difference={'none' if n is None else n})"

class PartRef:    name: str; phrase: str; columns: tuple[Column, ...]   # summed

class TeamDescriptorSpec:
                  key: str; label: str; parts: tuple[PartRef, ...]; window: Window
                  mirror_pairs: tuple[tuple[str, str], ...]; kind: str  # "composition"
                  part_names -> tuple[str, ...]
                  columns -> tuple[Column, ...]   # deduplicated by name, sorted by name; two
                                                  # columns with one name and two tokens: ValueError
                  counts(table: pd.DataFrame) -> np.ndarray     # [rows, K] int64
                  describe() -> str
                  payload -> str; fingerprint -> str       # sha256(payload utf-8).hexdigest()[:16]

class LevelSubject:
                  key: str; label: str
                  descriptor: str          # the key of the TeamDescriptorSpec whose total is N
                  exposure_column: str     # a column of the table of 2.2
                  unit_seconds: int        # EXPOSURE_UNIT_SECONDS
```

Sentences. With `actor` = `"the team"` for side `for` and `"the opponent"` for `against`, and
`poss` = `actor + "'s"`: `EventSet.sentence(side)` = `f"{phrase} by {actor}"`, then, after one
space and joined by `" and "`, each of `f"starting in {start_in.phrase}"`,
`f"starting outside {start_not_in.phrase}"`, `f"ending in {end_in.phrase}"` that applies,
with `{poss}` filled. `Column.sentence()` = the event-set sentence plus
`f", {partition.anchor} location {part.phrase}"` (with `{poss}` filled) when a part is set.
`describe()` = `f"{label}: " + "; ".join(f"{partref.phrase} = " + " plus ".join(column
sentences)) + f". Each part is a share of the {two|three}-part total. Window: {window.phrase}."`

`payload` = `f"{DESCRIPTOR_SCHEMA}|{key}|{kind}|window={window.token}|parts=" +
";".join(f"{p.name}<-" + "+".join(c.token for c in p.columns)) + "|mirror=" +
(",".join(f"{a}<>{b}") or "-")`. No phrase, label or column name enters a payload.

### 3.2 Zones, clauses, event sets

| Zone key | Bounds | Phrase |
|---|---|---|
| `final_third` | `x>=2/3` | `{poss} attacking third` |
| `penalty_box` | `x>=21/25 & y>=19/100 & y<=81/100` | `the penalty-area rectangle at {poss} attacking end` |
| `penalty_box_sb` | `x>=17/20 & y>=9/40 & y<=31/40` | same |
| `high_zone` | `x>=2/5` | `the zone at least 40% of the pitch length from {poss} own goal line` |
| `own_60` | `x<=3/5` | `{poss} own 60% of the pitch length` |

| Event set | Clauses | Zones | `needs` | Phrase |
|---|---|---|---|---|
| `f3_entry_pass` | `pass:*:completed:-` | start not in `final_third`; end in `final_third` | start, end | completed open-play passes |
| `box_entry_pass` (`_sb` with `penalty_box_sb`) | same | start not in the box; end in the box | start, end | completed open-play passes |
| `open_play_shot` | `shot:*:any:-` | | start | shots not taken directly from a set piece |
| `defensive_action` | `duel:Ground defending duel:any:-` + `*:*:any:interception` + `foul:Foul:any:-` | | start | recorded defensive actions (ground defending duel records, interception-tagged events and fouls recorded as Foul; each event once) |
| `defensive_action_high` | same three | start in `high_zone` | start | same phrase |
| `own_60_pass` | `pass:*:any:-` | start in `own_60` | start | open-play pass attempts |

`completed` reads `success == True`; it is never read on duels (the neutral duel `success`
means "not lost"). The `clearance` column is never read (always false in this corpus). A
flagged clearance is an interception in the union, as in E-11.

### 3.3 Partitions

| Key | Anchor | Parts in order (name: bounds: phrase) |
|---|---|---|
| `end_lateral_thirds` | end | `att_left`: `y<1/3`: `in {poss} left lateral third` · `att_right`: `y>2/3`: `in {poss} right lateral third` · `att_centre`: remainder: `in the central lateral third` |
| `start_lateral_thirds` | start | same three |
| `start_in_box` (`start_in_box_sb` with the `_sb` bounds) | start | `inside`: the box bounds: `inside the penalty-area rectangle at {poss} attacking end` · `outside`: remainder: `outside that rectangle` |
| `start_depth_thirds` | start | `own_third`: `x<1/3`: `in {poss} own third` · `opposition_third`: `x>=2/3`: `in {poss} attacking third` · `middle_third`: remainder: `in the middle third` |

### 3.4 Descriptors (`TEAM_DESCRIPTORS`, in this order)

| Key | Label | Parts: name (phrase) <- columns | Mirror pairs |
|---|---|---|---|
| `conceded_f3_entries_by_channel` | Share of final-third entry passes conceded, by lateral third (defending team's frame) | `def_left` (defending team's left) <- against `f3_entry_pass` `end_lateral_thirds` `att_right`; `def_centre` (centre) <- `att_centre`; `def_right` (defending team's right) <- `att_left` | `def_left<>def_right` |
| `conceded_f3_entries_wide_share` | Share of final-third entry passes conceded in the two outer lateral thirds | `wide` (wide (both outer lateral thirds)) <- against `att_left` + `att_right`; `centre` (centre) <- `att_centre` | |
| `conceded_box_entries_by_origin_channel` | Share of penalty-area entry passes conceded, by lateral third of origin (defending team's frame) | as the primary on `box_entry_pass` and `start_lateral_thirds` | `def_left<>def_right` |
| `conceded_shots_inside_box_share` | Share of conceded shots not taken directly from a set piece that start inside the penalty-area rectangle | `inside_box` (inside the rectangle) <- against `open_play_shot` `start_in_box` `inside`; `outside_box` (outside it) <- `outside` | |
| `defensive_actions_by_pitch_third` | Share of recorded defensive actions by pitch third (team's own frame) | `own_third` (own third), `middle_third` (middle third), `opposition_third` (attacking third) <- for `defensive_action` `start_depth_thirds`, same-named part | |
| `high_zone_defensive_action_share` | High-zone defensive actions as a share of those actions plus opponent pass attempts in the opponent's own 60% | `high_zone_defensive_actions` (high-zone defensive actions) <- for `defensive_action_high`; `opponent_own_60_passes` (opponent pass attempts in its own 60%) <- against `own_60_pass` | |

All use window `close_11v11` (phrase: `first and second half, before any dismissal, goal
difference at most one`; the key and the token keep `11v11` and `eleven_v_eleven`, which are in
the payloads, while the phrase says what the window measures: a side left with ten by an
injury stays in it). `TEAM_DESCRIPTORS_SB` holds the first two unchanged and the box pair
rebuilt on `penalty_box_sb` with keys suffixed `_sb` (event set `box_entry_pass_sb`, partition
`start_in_box_sb`). `WINDOWS = {"close_11v11": ..., "all_states": Window("all_states", "first
and second half, every match state", ("1H", "2H"), False, None)}`.

Also exported: `LEVEL_SUBJECTS = {"conceded_f3_entries_per_90": LevelSubject(key, label=
"Final-third entry passes conceded per 90 minutes of window time", descriptor=
"conceded_f3_entries_by_channel", exposure_column="window_seconds",
unit_seconds=EXPOSURE_UNIT_SECONDS)}`;
`log_ratio_basis(k: int) -> np.ndarray` (rows = coordinates; `k=3`: `[[s, 0, -s], [t, -2t, t]]`
with `s = sqrt(1/2)`, `t = sqrt(1/6)`; `k=2`: `[[s, -s]]`); `required_columns(specs) ->
tuple[Column, ...]`.

### 3.5 Lattice and scale edges (tested)

Bounds are compared as `values <op> float(value)` (`fraction_rule`). On the Wyscout lattice
`j/100.0`: `0.33 -> att_left`, `0.34 -> att_centre`, `0.66 -> att_centre`, `0.67 -> att_right`;
end `x` `0.66` is outside and `0.67` inside the final third; box membership holds at exactly
`x = 0.84`, `y = 0.19`, `y = 0.81`; `0.40` is in `high_zone`; `0.60` is in `own_60`. On the
StatsBomb scale (`sb_location_scale`; raw coordinates at the provider's 0.1 resolution, so
values `(j / 10) / 120.0` and `(j / 10) / 80.0`): end `x = 80/120` is in the final third, as an
exact rational also says (`80/120 = 2/3`); no raw `y` lies on a lateral cut (`80/3` and `160/3`
are not multiples of 0.1), so start `y = 26.6/80` is `att_left`, `26.7/80` is `att_centre`,
`53.3/80` is `att_centre` and `53.4/80` is `att_right`; `x = 102/120` and `y = 62/80` are inside
`penalty_box_sb`; a location of `(120, 80)` is a location (no sentinel rule). On both lattices
float64 and exact rationals agree at every cut of 3.2 and 3.3.

### 3.6 Frozen payloads and fingerprints

`descriptor_test_vectors.json` (beside this file) holds, under `wy` and `sb`, for every
descriptor of both dictionaries (six and four), the exact `payload`, `fingerprint`,
`describe()` string (`sentence`) and column names (`columns`), generated by an independent
script from the tables above. `tests/test_team_descriptors.py` asserts byte equality. The
fingerprints are also `descriptor_fingerprints` and `descriptor_fingerprints_sb`. An
implementation whose payload differs is not the preregistered definition: fix the
implementation, never the vector.

| Key | Fingerprint |
|---|---|
| `conceded_f3_entries_by_channel` | `2be74ac2872fc2cd` |
| `conceded_f3_entries_wide_share` | `d251a8b6ea11589a` |
| `conceded_box_entries_by_origin_channel` | `1520182357343ffa` |
| `conceded_shots_inside_box_share` | `7b51b3b307b4148b` |
| `defensive_actions_by_pitch_third` | `5ecfbefcb7634b29` |
| `high_zone_defensive_action_share` | `0d2ee50169a05af9` |
| `conceded_box_entries_by_origin_channel_sb` | `11161bb6ef93404e` |
| `conceded_shots_inside_box_share_sb` | `b54d37b794ed388e` |

### 3.7 Constants product code holds

Product code cannot read an experiment's config, so `descriptors.py` holds, as module
constants, every value of the config that a product caller passes: `REGULATION_PERIODS`,
`DISMISSAL_CARDS`, `GOAL_INCIDENT_COLUMNS`, `WY_LOCATION_SENTINELS`, `COORDINATE_RANGE`,
`EXPOSURE_UNIT_SECONDS`, and the fractions of 3.2 and 3.3. `test_config_geometry_matches_
descriptors` asserts each equals the config. `estimator.py` holds
`LEAGUE_PRIOR_PSEUDOCOUNT_PER_PART` (`league_prior_pseudocount_per_part`, which `pi` needs),
tied the same way by `test_estimator_constant_matches_the_config` (3.8). The served panel's
constants (`served_panel`, `product_rules`) live in the Opponent Lab module and are tied the
same way (section 12.3).

### 3.8 `galactico/features/team/estimator.py`: the one estimator (ROOT 2.9 Z3)

Module docstring: claim = the walk-forward state of 4.2 (the cumulative arrays of a league's
strictly prior valid rows) and every quantity of 4.2 that is a function of it, in closed form,
NumPy only; non-claim = no loss, no selection, no verdict, and no statement that a composition
persists or is a property of the team (that is what E-10 tests). It is product-side code beside
`match_table.py` and `descriptors.py`, imports nothing but `descriptors.py`, the standard
library, NumPy and pandas, and so nothing from `galactico.validation` or `experiments`
(`tests/test_research_firewall.py`). The research engine
(4.3) imports it and Opponent Lab's panel (12.3) calls it; there is no second implementation and
no parity test. Its `lf_sha256` is in `source_hashes` (7.3), so an edit after registration is
visible against the registered results. The formulas are those of 4.2, which stay normative;
this section fixes where they live and how they are called.

```python
LEAGUE_PRIOR_PSEUDOCOUNT_PER_PART: float   # = league_prior_pseudocount_per_part (a test ties it)

def descriptor_rows(table: pd.DataFrame, spec: TeamDescriptorSpec, *, league: str,
                    exposure_unit_seconds: int) -> pd.DataFrame          # the row contract, 4.1

@dataclass(frozen=True)
class PriorState:                     # the walk-forward state of 4.2, one league
    team_ids: tuple[int, ...]         # sorted; index t is team team_ids[t]
    parts: tuple[str, ...]            # the descriptor's part names, in its order
    counts: np.ndarray                # C [T, T, 2, K] float64: (context, unit, context_home, part)
    exposure: np.ndarray              # X [T, T, 2] float64

def empty_state(team_ids: Sequence[int], parts: Sequence[str]) -> PriorState
def add_rows(state: PriorState, rows: pd.DataFrame, *, weights: np.ndarray) -> PriorState
def state_at(rows: pd.DataFrame, *, team_ids: Sequence[int], parts: Sequence[str], date: str,
             weights: np.ndarray) -> PriorState

@dataclass(frozen=True)
class ShapeEstimate:
    team_ids: tuple[int, ...]         # the state's; index t is team team_ids[t]
    k_context: float; k_unit: float | None; league_pseudocount: float
    events: float                     # S.sum(); 0 means the league has no prior event
    pi: np.ndarray                    # [K]
    pi_venue: np.ndarray; nu: np.ndarray            # [2, K], index v = context_home
    context: np.ndarray               # A_c [T, K]
    context_without_unit: np.ndarray  # A_c^(-u) [T, T, K], index (c, u)
    expected_share: np.ndarray        # e[c, u, v] [T, T, 2, K]
    observed: np.ndarray              # O_u [T, K]
    expected: np.ndarray              # E_u [T, K]
    delta: np.ndarray                 # delta_u [T, K]

@dataclass(frozen=True)
class LevelEstimate:
    team_ids: tuple[int, ...]         # the state's; index t is team team_ids[t]
    k_context_level: float; k_unit_level: float | None
    rate_venue: np.ndarray            # lam_v [2]
    rate: float                       # lam, both venues
    context_ratio: np.ndarray         # rA_c [T]
    context_ratio_without_unit: np.ndarray          # rA_c^(-u) [T, T], index (c, u)
    unit_observed: np.ndarray         # O'_u [T]
    unit_expected: np.ndarray         # E'_u [T]
    unit_ratio: np.ndarray            # rD_u [T]

def shape_estimate(state: PriorState, *, league_pseudocount: float, k_context: float,
                   k_unit: float | None) -> ShapeEstimate
def level_estimate(state: PriorState, *, k_context_level: float,
                   k_unit_level: float | None) -> LevelEstimate
def unit_deviation(observed: np.ndarray, expected: np.ndarray, *,
                   k_unit: float | None) -> np.ndarray
def unit_level_ratio(observed: np.ndarray, expected: np.ndarray, *,
                     k_unit_level: float | None) -> np.ndarray
def predicted_shape(estimate: ShapeEstimate, context: np.ndarray, context_home: np.ndarray,
                    delta: np.ndarray) -> np.ndarray
def predicted_level(estimate: LevelEstimate, context: np.ndarray, context_home: np.ndarray,
                    exposure: np.ndarray, unit_ratio: np.ndarray) -> np.ndarray
def served_composition(estimate: ShapeEstimate, team_id: int) -> tuple[np.ndarray, float]
def served_volume(estimate: LevelEstimate, team_id: int) -> tuple[float, float]
```

- `descriptor_rows` is the row contract of 4.1, defined here so that the engine and the panel
  build the same rows; the engine imports it.
- `add_rows` adds `weights[i]` times the row's `n__<part>` counts and `exposure` at
  `[context, unit, context_home]` for every row with `valid` true; an invalid row adds nothing;
  a unit or context id outside `team_ids` raises `ValueError`; inputs are never mutated and the
  result does not depend on row order. `weights` is required and aligned to `rows`: the engine
  passes ones; the panel passes ones for its point and each world's match weights for its
  interval (12.3), so an integer weight `w` is the row counted `w` times and a weight of 0 is the
  row absent. A listed team with no row changes no quantity of another team.
- `state_at` = `add_rows(empty_state(team_ids, parts), r, weights=w)` over the rows `r` (and
  their weights `w`) whose normalised calendar date is strictly before `date` (`prior_rule`).
- `shape_estimate` computes `pi`, `pi_v`, `nu_v`, `A_c`, `A_c^(-u)`, `e`, `O_u`, `E_u` and
  `delta_u` by the formulas of 4.2, with `a = league_pseudocount`; `delta` is
  `unit_deviation(observed, expected, k_unit=k_unit)`. `level_estimate` computes `lam_v`, `lam`,
  `rA_c`, `rA_c^(-u)`, `O'_u`, `E'_u` and `rD_u` by 4.2's level formulas; `unit_ratio` is
  `unit_level_ratio(unit_observed, unit_expected, k_unit_level=k_unit_level)`.
- `unit_deviation` is 4.2's `delta` from an `(O, E)` pair (rows `[..., K]`), 0 where
  `O.sum() == 0` and everywhere when `k_unit` is `None` (`context_only`); `unit_level_ratio` is
  `(O' + kD') / (E' + kD')`, 1 when `k_unit_level` is `None`. The unit's `delta_u`, the peers'
  pooled `delta`, P2's pair-excluded `delta`, `rD_u` and `rD_peers` are these two functions on
  different inputs; the engine forms those inputs (4.2) and never the formulas.
- Both estimates carry the state's `team_ids`. In `predicted_shape` and `predicted_level`,
  `context` is an `int64` array `[R]` of 0-based indices into `team_ids` (never team ids) and
  `context_home` a `bool` array `[R]`; `served_composition` and `served_volume` take a team id
  and map it to its index through `team_ids`, raising `ValueError` for an id not in it.
- `predicted_shape` is `normalise(A_c exp(nu_v + delta))` per row (`delta` `[R, K]`): B1 and B4
  with zeros, the candidate, mirror, peers and permuted rungs with the engine's `delta` rows.
  `predicted_level` is `e lam_v rA_c unit_ratio` per row: B1 with ones, B2 with `rD_u`, B3 with
  `rD_peers`. B0's shape and B2's shape are `pi_v`, read from the shape estimate's `pi_venue`,
  not from `predicted_shape`.
- `served_composition` returns `(normalise(pi exp(delta_u)), O_total / (O_total + kD))` for the
  team, `O_total` its prior events; `served_volume` returns `(lam rD_u, E'_u / (E'_u + kD'))`, the
  volume per `exposure_unit_seconds` of window time. Both raise `ValueError` when the estimate's
  unit constant is `None`: an established token never carries `context_only`.
- No function has a default for any argument. Research callers pass the config's
  `league_prior_pseudocount_per_part` and their selected constants; product callers pass
  `LEAGUE_PRIOR_PSEUDOCOUNT_PER_PART` and the record's `k_context` and `k_unit` figures (12.3).

The tests of `tests/test_team_estimator.py` (WP A) are listed in section 9.

## 4. `galactico/validation/conceded_shape.py`

Docstring: research pipeline for E-10; frozen walk-forward models, the shared world, the
decision rules; aggregate outputs only; never imported by product code.

### 4.1 Row contract (what B needs from A, with the estimator of 3.8)

```python
def descriptor_rows(table: pd.DataFrame, spec: TeamDescriptorSpec, *, league: str,
                    exposure_unit_seconds: int) -> pd.DataFrame
```

Defined in `galactico/features/team/estimator.py` (3.8), product side, so that the engine and
the served panel read the same rows; this module imports it.

One row per table row, sorted by `(date, game_id, unit_id)`:

| Column | dtype | Source |
|---|---|---|
| `league` | str | argument |
| `game_id`, `unit_id`, `context_id` | int64 | `game_id`, `team_id`, `opponent_id` |
| `date` | datetime64[ns] | `pd.to_datetime(table.date).dt.normalize()`: the date as the provider records it (Wyscout `dateutc`, a UTC time; StatsBomb `match_date`, a local calendar date with no time or zone), normalised to the day |
| `context_home` | bool | `~is_home` |
| `valid` | bool | `valid` |
| `exposure` | float64 | `window_seconds / exposure_unit_seconds` |
| `unit_goals`, `context_goals` | int64 | `goals_for`, `goals_against` (the sheet, every match) |
| `unit_passes`, `context_passes` | int64 | `match__completed_passes` of the team and of its opponent |
| `n__<part>` for each part | int64 | `spec.counts(table)` |

### 4.2 Walk-forward state

The state and every quantity below that is a function of it are computed by the estimator of
3.8, product side, which this module imports (ROOT 2.9 Z3): the arrays `C` and `X` are its
`PriorState`, `pi` to `delta_u` its `ShapeEstimate`, `lam_v` to `rD_u` its `LevelEstimate`,
`delta` and `rD` of any `(O, E)` pair its `unit_deviation` and `unit_level_ratio`, the shape
means of B1, B3, B4, B6, B7 and the candidate its `predicted_shape`, and the level means of B1,
B2 and B3 its `predicted_level`. B0 and B2 read their shape `pi_v` from the shape estimate
(`pi_venue`), and B0 reads its level rate `lam_v` from the level estimate (`rate_venue`); B4,
B6, B7 and the candidate carry B2's level mean. This module computes none of them itself. It
keeps what is research only: the walk over dates, eligibility, the sheet counters, strength
terciles and peers, donor maps, the mirror swap, the inputs of P2, the raw five rung (B5),
losses and deviances. The formulas are written once, here, and are normative for the
estimator.

Per league, teams indexed `0..T-1` by sorted id. One cumulative array of strictly prior valid
rows, updated only after every row of a date has been predicted:

- `C[c, u, v, k]`: events of part `k` in rows with context `c`, unit `u`, `v = context_home`.
- `X[c, u, v]`: exposure, same indexing. `played_valid[team]` from valid rows;
  `played_sheet[team]`, `points[team]`, `goal_diff[team]` from every row (3/1/0 from
  `unit_goals` versus `context_goals`, counted once per team and match).

Everything in the protocol's model section is a sum over axes of `C`:
`S = C.sum((0,1))` (by venue, part); `F_c = C.sum((1,2))`; rows against `u`: `C[c,u].sum(0)`;
`M[c,u,v] = C.sum(3)`; `O_u = C.sum((0,2))`. Formulas (normative, identical to the protocol):

```
pi    = (S.sum(0) + a) / (S.sum() + a K)                       a = league_prior_pseudocount_per_part
pi_v  = (S[v] + a) / (S[v].sum() + a K);   nu_v = ln pi_v - ln pi
A_c       = (F_c + kA pi) / (F_c.sum() + kA)
A_c^(-u)  = (F_c - C[c,u].sum(0) + kA pi) / (F_c.sum() - C[c,u].sum() + kA)
e[c,u,v]  = normalise(A_c^(-u) * exp(nu_v))
E_u   = sum_{c,v} M[c,u,v] * e[c,u,v];     ebar_u = E_u / O_u.sum()
delta_u = ln((O_u + kD ebar_u) / (O_u.sum() + kD)) - ln(ebar_u);   0 if O_u.sum() == 0
B4 shape   = normalise(A_c * exp(nu_v))
candidate  = normalise(A_c * exp(nu_v + delta_u))
mirror     = candidate with delta_u's mirror-pair components swapped
peers      = delta from (sum of O_g, sum of E_g) over g in the unit's league-tercile, g != u
raw five   = (c5 + s) / (c5.sum() + s K), c5 = pooled counts of the unit's last raw_persistence_matches valid rows, s = log_ratio_smoothing_per_part
shape loss of a row = -sum_k n_k ln p_k
log-ratio coordinates of a composition p = basis @ ln p          basis = log_ratio_basis(K)
```

Level, with `lam_v = M.sum((0,1))[v] / X.sum((0,1))[v]`, `Xe[c,u,v] = X[c,u,v] lam_v`:

```
rA_c      = (M[c].sum() + kA') / (Xe[c].sum() + kA')
rA_c^(-u) = (M[c].sum() - M[c,u].sum() + kA') / (Xe[c].sum() - Xe[c,u].sum() + kA')
rD_u      = (M[:,u].sum() + kD') / ((Xe[:,u] * rA^(-u)[:,None]).sum() + kD');   1 for context_only
O'_g = M[:,g].sum();  E'_g = (Xe[:,g] * rA^(-g)[:,None]).sum()
rD_peers  = (sum_g O'_g + kD') / (sum_g E'_g + kD'), g in the unit's league-tercile, g != u
            (1 for context_only)
lam       = M.sum() / X.sum()                                     (both venues)
B0 mean = e lam_v;  B1 mean = e lam_v rA_c;  B2 mean = B1 mean * rD_u
B3 mean = B1 mean * rD_peers                                      (peers_level_rule)
B5 mean = e (Y5 + s) / (X5 + s / lam)                            (raw_persistence_level_rule)
          Y5, X5 = the unit's conceded events and exposure over its last raw_persistence_matches valid rows
deviance(y, mu) = 2 (y ln(y/mu) - (y - mu)),  y ln y = 0 at y = 0;  rows with e == 0 are not scored
```

The level ladder exists for the level subject only; S1 to S5 report shape rungs only.

Rules that must hold in code:

- A row is predicted only if valid and `played_valid[unit] >= m` and `played_valid[context] >=
  m` (`m = minimum_prior_matches`). Invalid rows never update `C` or `X`; they update the sheet
  counters.
- A league date with no prior events (`S.sum() == 0`) predicts nothing.
- For the boundary candidate `context_only` the candidate, mirror, peers and permuted loss
  arrays **are** the B4 array (assigned, not recomputed), so every difference is exactly 0.0;
  likewise the level's B2 and B3 arrays **are** B1's. The consequences for the criteria are
  the protocol's (Frozen selection procedure): (a), (b), (f), and (d) where mirror pairs exist,
  are false by computation (p-value 1, no estimate below zero); (c) and every other criterion
  are evaluated as defined.
- Strength tercile at a date: teams with `played_sheet > 0`, ordered by descending prior points
  per match, then descending prior goal difference per match, then ascending team id;
  `tercile = (strength_tercile_count * position) // count`. Teams with `played_sheet == 0` form
  no tercile and receive no donor.
- Donor map for placebo seed `s`: for each tercile `g`, members sorted by team id,
  `rng = np.random.default_rng(int.from_bytes(sha256(f'{seed}|{placebo_seed}|{league}|{date:%Y-%m-%d}|{tercile}'.encode('utf-8')).digest()[:8], 'big'))`
  (`donor_seed_rule`, the same text: `date` the normalised pandas `Timestamp` of the decision
  date, `tercile` the 0-based `int`), `donor[members] =
  members[rng.permutation(len(members))]`. A unit's permuted loss uses `delta[donor[unit]]` with
  the unit's own context and venue.
- P2 input: `delta_u` recomputed without the row's context team, i.e. `estimator.unit_deviation`
  of `O_u - C[c,u].sum(0)` and `E_u - sum_v M[c,u,v] e[c,u,v]`.

### 4.3 Functions

```python
@dataclass(frozen=True)
class ForwardSettings:          # every field from config; no field has a default
    parts: tuple[str, ...]; mirror_pairs: tuple[tuple[str, str], ...]
    k_context: float; k_unit_candidates: tuple[float | None, ...]      # None = context_only
    minimum_prior_matches: int; league_pseudocount: float
    raw_matches: int; smoothing: float
    permutation_seeds: tuple[int, ...]; seed: int; tercile_count: int

@dataclass(frozen=True)
class ShapeForward:            # arrays aligned to the input rows
    eligible: np.ndarray       # [R] bool
    events: np.ndarray         # [R] int64
    loss_league_venue: np.ndarray; loss_context: np.ndarray; loss_raw_five: np.ndarray   # [R]
    loss_candidate: np.ndarray; loss_mirror: np.ndarray; loss_peers: np.ndarray          # [Q, R]
    loss_permuted: np.ndarray  # [P, Q, R]
    donor_changed: np.ndarray  # [P, R] bool
    residual_coordinates: np.ndarray        # [R, K-1]   observed minus B4, smoothed
    delta_coordinates_pair_excluded: np.ndarray   # [Q, R, K-1]

def walk_forward_shape(rows: pd.DataFrame, settings: ForwardSettings) -> ShapeForward
def walk_forward_level(rows: pd.DataFrame, settings: ForwardSettings) -> LevelForward
    # LevelForward: eligible, scored (e > 0), deviance_league_venue, deviance_context,
    # deviance_raw_five [R]; deviance_unit, deviance_peers [Q, R] (Q over None and the grid)
    # Both hold one estimator.PriorState per league (3.8). At each date the shape walk calls
    # shape_estimate(state, league_pseudocount=settings.league_pseudocount,
    # k_context=settings.k_context, k_unit=None) and unit_deviation per k_unit candidate; the
    # level walk calls level_estimate(state, k_context_level=settings.k_context,
    # k_unit_level=None) and unit_level_ratio per candidate; each predicts that date's rows,
    # then add_rows(state, those rows, weights=ones). This module defines no state_at; the
    # state at a date is estimator.state_at's (3.8)

def select_k(loss_by_candidate: np.ndarray, weights: np.ndarray, mask: np.ndarray,
             candidates: Sequence[float | None], *, tolerance: float
             ) -> tuple[int | None, list[float]]
    # pooled loss_q = loss[q, mask].sum() / weights[mask].sum(); tie set = {q : loss_q <=
    # min loss + tolerance}; the selected candidate is context_only (the candidate None) if it
    # is in the tie set, else the largest k in it. Returns (q, every pooled loss), q the int
    # position of the selected candidate in `candidates`: when context_only is selected, q is
    # the position of None, an int, and the selection is valid (G6 and LG6 stay true). The
    # first element is None only when a pooled loss is non-finite: no selection, and the
    # caller sets G6 (LG6) false and runs no further forward pass

@dataclass(frozen=True)
class SeasonWorld:
    labels: tuple[str, ...]      # f"{league}|{part}|{week}", sorted within stratum
    strata: tuple[str, ...]      # f"{league}|{part}", in world_strata order
    multiplicity: np.ndarray     # [B, C] int32
    fingerprint: str

def season_world(dates_by_league: Mapping[str, pd.Series], *, leagues: Sequence[str],
                 evaluation_start: str, week_rule: str, replicates: int, seed: int) -> SeasonWorld
    # asserts set(dates_by_league) == set(leagues); clusters: (league, part, week) of every row
    # dated in the season, week = str(pd.Timestamp(date).to_period(week_rule)) (the house
    # paired_week_interval's label), part "development" (date < evaluation_start) or
    # "evaluation"; strata league x part in the order of `leagues`, development first; a part
    # with no rows has no stratum; rng = default_rng(seed); per stratum of m clusters, in
    # stratum order: idx = rng.integers(0, m, size=(replicates, m)); multiplicity = counts of
    # idx per cluster. fingerprint = sha256(("\n".join(labels)).encode("utf-8") + b"\0" +
    # multiplicity.astype("<i4").tobytes()).hexdigest()

@dataclass(frozen=True)
class ClusterEstimate:
    estimate: float | None; interval: tuple[float, float] | None; p_one_sided: float | None
    rows: int; weight: float; clusters: int; holes: int

def cluster_ratio(numerator: np.ndarray, denominator: np.ndarray, labels: np.ndarray,
                  world: SeasonWorld, *, quantiles: tuple[float, float], method: str,
                  zero_tolerance: float) -> ClusterEstimate
    # rows are summed into their cluster labels; replicate b: sum_c W[b,c] num_c / sum_c W[b,c]
    # den_c over the clusters present; a replicate with zero denominator is a hole (left out,
    # counted); interval = np.quantile(kept, quantiles, method=method);
    # p = (1 + count(kept >= -zero_tolerance)) / (len(kept) + 1); empty input -> all None.
    # An all-zero numerator (a context_only selection) gives every kept replicate 0.0 and p = 1

def split_half(rows, parts, *, smoothing, minimum_half_matches, critical_value,
               house_confidence, period: str, band, number) -> dict
def level_split_half(rows, *, smoothing, minimum_half_matches, critical_value,
                     house_confidence, period: str, band, number) -> dict
    # period: config["season_label"], AxisReliability's period (I9) for the house bound
def persistence(rows, parts, *, evaluation_start, smoothing, minimum_part_matches) -> dict
    # T1 (persistence_rule), no step-up
def strength_validity(rows, parts, *, covariates, smoothing, top_k, tie_policy, ceiling,
                      spearman_floor, survival_floor, permutations, seed) -> dict
def level_strength_validity(rows, *, covariates, smoothing, top_k, tie_policy, ceiling,
                            spearman_floor, survival_floor, permutations, seed) -> dict
    # the level's V1: team value ln((sum y + s) / sum e), reported only (kind CONTEXT)
def pair_interaction(rows, parts, world, *, smoothing, minimum_events, quantiles,
                     method) -> dict                                      # reported only
def calibration(forward: ShapeForward, rows, selected: int, world, *,
                k_unit: float | None, minimum_events, quantiles, method,
                zero_tolerance) -> dict | None
    # selected: select_k's index q; k_unit: candidates[q], the selected value (None is
    # context_only, for which calibration returns None)
def holm(p_values: Mapping[str, float | None], order: Sequence[str], *, alpha: float,
         family_size: int) -> dict[str, dict]
def count_pass(rows: pd.DataFrame, settings: ForwardSettings) -> CountPass
    # loss-free walk over the schedule: eligible [R], donor_changed [P, R], prior matches; no model
def sample_gates(rows, counts: CountPass, audit_summary: Mapping, config: dict, *,
                 subject: str) -> dict[str, dict]   # subject "shape", "level" or "replication"
def decide_descriptor(*, gates: Mapping[str, bool], criteria: Mapping[str, bool | None]
                      ) -> tuple[str, list[str]]
def decide_level(*, gates: Mapping[str, bool], criteria: Mapping[str, bool | None]
                 ) -> tuple[str, list[str]]
def replication_status(descriptor: str, token: str, config: dict, *,
                       inconclusive: str | None, p1: float | None, m1: float | None
                       ) -> tuple[str, str | None]
def evaluate_descriptor(rows, spec, config: dict, world: SeasonWorld, *, role: str,
                        sensitivity_rows: pd.DataFrame | None) -> dict
def evaluate_replication(rows, spec, config: dict, world: SeasonWorld, *,
                         frozen: Mapping[str, float],
                         listed_matches: Mapping[str, int]) -> dict
    # listed_matches: per league of replication.leagues, the matches its index lists
def evaluate_level(rows, config: dict, world: SeasonWorld) -> dict
def evaluate_study(rows_by_descriptor: Mapping[str, pd.DataFrame], config: dict,
                   world: SeasonWorld, *, sensitivity_rows: pd.DataFrame | None) -> dict
```

Details not already in the protocol:

- Leagues. Every per-league subset, G1 to G3, (b), (Lb) and the world's strata iterate the
  `leagues` the caller passes (`config["leagues"]` for the real run and the gate,
  `config["replication"]["leagues"]` for the replication); (f) and `p1.unexposed` read
  `unexposed_leagues`. A listed league with no rows fails its gates; it is never skipped.
- `split_half`: per team, the opponents ordered by the date of the first valid meeting, then
  team id; for an opponent at an even position (0-based) half A takes the meeting at which the
  team was at home, for an odd position the away meeting; half B the other; a missing meeting
  is not replaced (`reliability_split`). Team value per half: `basis @ ln((counts + s) /
  (counts.sum() + s K))`. Teams with fewer than `minimum_half_matches` rows in a half are
  dropped and counted. League mean removed per half and coordinate. Returns `coordinates`, per
  coordinate `half_r`, `spearman_brown`, `lower_bound` (protocol formula, `critical_value`),
  `house_lower_bound` (`AxisReliability` at `confidence=house_confidence`, reported only), and
  `n_teams`, `teams_dropped`, `minimum_lower_bound`, `implied_per_match_icc` (per coordinate,
  `R / (m - (m - 1) R)` with `m` the mean number of valid rows per qualifying team over both
  halves), `render` (`"number"` / `"band"` / `"insufficient"` from `minimum_lower_bound`
  against `number` and `band`). Non-finite `r`, `n - 3 - (G - 1) < 1`, or `|r| >= 1` give
  `lower_bound = None`; then `minimum_lower_bound` is `None` and the criterion is not met.
  `level_split_half` returns the same shape with the one coordinate `log_rate`
  (`ln((sum y + s) / sum e)` per half), so `minimum_lower_bound` is that coordinate's bound.
- `persistence` (`persistence_rule`): per coordinate, the team value of each part
  (development, evaluation) from the pooled counts of the team's valid rows dated in it,
  smoothed as in `split_half`, league-centred within each part; teams with at least
  `minimum_part_matches` (= `minimum_half_matches_per_team`) valid rows in each part; Pearson
  correlation over teams; returns per coordinate `r` and `n_teams`.
- `strength_validity`: team-season value from the pooled counts of all valid rows; covariates
  derived from `rows` (no other frame): points per match and goals for and against per match
  from `unit_goals` and `context_goals` over every row of the team, valid or not (the sheet),
  and `sum(unit_passes) / (sum(unit_passes) + sum(context_passes))` over valid rows. Both
  league-centred. Per coordinate two calls of I8 with the same covariates
  (`strength_survival_tails`): `upper` on the coordinate, `lower` on its negation; `passed` is
  `upper.passed and lower.passed` (never the defaults). Reported per coordinate: from `upper`
  only, `r2` (`variance_explained_by_confounds`), `r2_adjusted = 1 - (1 - r2)(n - G) / (n - G -
  q)`, `noise_floor = q / (n - G)`, with `q = len(covariates)` (`top_k` enters neither),
  `permutation_p` (covariate rows permuted within league, `permutations` draws,
  `(1 + count(R2_perm >= R2)) / (draws + 1)`) and `spearman_raw_vs_residual` (the two calls
  agree on these up to floating-point rounding); from each call, `top_k_survivors`,
  `top_k_tied_raw`, `top_k_tied_adjusted` (`upper`) and `top_k_survivors_lower`,
  `top_k_tied_raw_lower`, `top_k_tied_adjusted_lower` (`lower`), survivors `None` when
  undefined; `failures`, the verdicts' words each prefixed `"upper: "` or `"lower: "` (the
  words alone do not say which tail they describe); `passed`. The permutation generator is a
  fresh `default_rng(seed)` per call, `seed = config seed + seed_streams.strength_permutation`,
  consumed coordinate by coordinate, so every descriptor's first coordinate meets the same
  permutations.
- `level_strength_validity`: the level's V1, reported with kind CONTEXT and gating nothing. The
  team value is `ln((sum y + s) / sum e)` over all of the team's valid rows, `y` the row's `N`
  (the primary's total), `e` its exposure and `s = smoothing` (`log_ratio_smoothing_per_part`),
  league-centred; the covariates, the two calls, the reported fields and the permutation
  generator (a fresh `default_rng(seed)` for the level) are those of `strength_validity`, with
  the one coordinate `log_rate`.
- `pair_interaction` (primary only, reported): rows with `valid` and at least `minimum_events`
  events; per coordinate, the row's log-ratio coordinate `basis @ ln((n + s) / (N + s K))`,
  least-squares fit on context dummies, unit dummies and `context_home` within league;
  residuals; directed pairs `(context, unit)` with exactly two rows give a pair of residuals
  ordered by date; statistic = Pearson correlation over directed pairs; replicate `b` weights a
  pair by the product of its two meetings' multiplicities in `world` (a pair with a zero weight
  is out of that replicate); returns estimate, interval, `n_directed_pairs`. Nothing reads it.
- `calibration`: rows with at least `calibration_minimum_events_per_row`; per coordinate
  `slope = sum(N x y) / sum(N x^2)`, `x` read from `delta_coordinates_pair_excluded[selected]`;
  interval by `cluster_ratio(N x y, N x^2, ...)`. `None` when `k_unit` is `None` (`context_only`
  was selected).
- `holm` (`holm_order_rule`): `m = family_size` always; finite p-values ascending, ties broken by
  `order` (the `secondary_descriptors` list), then every `None` or NaN in `order`; the `i`-th
  (1-based) is rejected while every earlier one was rejected and `p_(i) <= alpha / (m - i + 1)`;
  `None` and NaN are never rejected. A `context_only` selection enters with its computed
  p-value, 1.0. Returns per name `p_one_sided`, `order_position`, `threshold`, `rejected`.
- `decide_descriptor` (`verdict_precedence.descriptor`): `INCONCLUSIVE` if any gate of
  `shape_gates` is false; else `DEFENDER_SHAPE_SIGNAL` if every criterion in `("a", "b", "c",
  "d", "e", "f", "g")` is `True`; else `ADDED_INFORMATION_NOT_SHOWN` if one of `a, b, c, f` is
  not `True`; else `SIDE_NOT_SHOWN` if `d` is not `True`; else `NOT_RELIABLE` if `e` is not
  `True`; else `STRENGTH_NOT_EXCLUDED`. `None` is not `True`. Reasons: the failed gates, or
  every criterion that is not `True`, in letter order.
- `decide_level` (`verdict_precedence.level`): `INCONCLUSIVE` if any gate of `level_gates` is
  false; else `LEVEL_ESTABLISHED` if `La`, `Lb`, `Le` are all `True`; else
  `ADDED_INFORMATION_NOT_SHOWN` if `La` or `Lb` is not; else `NOT_RELIABLE`.
- `evaluate_descriptor` order of work: `count_pass` and gates G1 to G5 (no loss exists yet)
  -> select `kA` (one forward pass per grid value, development rows only scored) -> one forward
  pass with every `kD` candidate and all placebo seeds -> select `kD` for the real history and,
  separately, for each seed -> G6 (false when a selection loss is non-finite, `select_k`
  returning `None` as its index; then `INCONCLUSIVE`, no evaluation loss is aggregated or
  serialised; a `context_only` selection is an int index and leaves G6 true) ->
  estimands in `world` -> criteria -> verdict. A secondary's criterion (a) is filled by
  `evaluate_study` after `holm` over the family. `sensitivity_rows` is the primary's
  `all_states` rows or `None` (the gate and every secondary pass `None`). When given, it adds
  the `all_states` P1: one forward pass on those rows with the selected `kA` and `kD` as the
  only candidate and no placebo, no re-selection, on the same eligible rows (eligibility
  counts valid matches and does not depend on the window; the function asserts the two
  eligible masks are equal), in the shared `world`; and the `all_states` R1, `split_half` on
  those rows with the same split.
- `evaluate_replication` (the replication's frozen path; no selection happens anywhere in
  it): gates `sample_gates(..., subject="replication")`, which are G1 and G3 only
  (`replication.gates`, `replication.gate_rule`), with the `replication` block's minima and G1's
  share over the matches the index lists: `audit_summary` carries `listed_matches`, and G1 is
  the league's valid matches among `rows` divided by `listed_matches[league]`, so a listed
  match whose files are absent counts as invalid although it has no row; a failed gate is the
  reason `SAMPLE`. Then one
  forward pass with `k_context = frozen["k_context"]`, `k_unit_candidates =
  (frozen["k_unit"],)` and `permutation_seeds = ()`, and the estimands P1 and M1 (pooled and
  by league) in the replication's `world` (`replication.estimand_rule`): B4, the candidate and
  B6 only. No placebo, no R1, V1, P2, T1 or I1, and no G2, G4, G5 or G6. Returns `gates`,
  `events`, `shape_ladder` (B4, candidate, B6), `p1`, `m1`.
- `replication_status` (`replication.status_rule`): `NOT_COMPARABLE` if `descriptor` is in
  `not_comparable_descriptors`; else `NOT_RUN` if `token` is not
  `run_only_if_descriptor_verdict`; else `REPLICATION_INCONCLUSIVE` with `inconclusive` (the
  first reason of `inconclusive_reasons` that holds, `inconclusive_reason_rules`) when it is
  not `None`; else `REPLICATED` if `p1 <= alpha` and, for a descriptor of
  `descriptor_mirror_pairs`, `m1 <= alpha`; else `NOT_REPLICATED`. The reason is `None` except
  under `REPLICATION_INCONCLUSIVE`. A `None` p-value is not at most `alpha`.
- `evaluate_level`: G1 to G4 from the primary's counts (the level's `N` is the primary's
  total), then `kA'` (B1 deviance over the grid), then `kD'` (B2 deviance over the grid and
  `context_only`), LG6 (false when `select_k` returns `None` as its index, never for a
  `context_only` selection), estimands, criteria, verdict. It
  runs whenever its own gates pass, whatever G5 or G6 returned for the primary. It has no
  replication entry.
- Worlds. One `SeasonWorld` per real run (`seed + seed_streams.season_world`,
  `bootstrap_replicates`, `leagues`), one per synthetic season (the same formula, with the
  season's seed as `seed`, section 5), and one for the replication (`seed +
  seed_streams.replication_world`, `replication.bootstrap_replicates`, `replication.leagues`,
  `replication.evaluation_start`, so its strata are evaluation parts only). Every
  `cluster_ratio`, `calibration` and `pair_interaction` of a run reads its world. There are no
  per-estimand or per-descriptor seeds.

## 5. `galactico/validation/conceded_shape_synthetic.py`

Written from football and the schedule, not from the engine's equations: effects live on
log-ratio coordinates and on a log rate; the engine shrinks counts.

```python
def berger_tables(n_teams: int) -> list[list[tuple[int, int]]]
    # schedule_rule; 2 (n - 1) rounds; second half = first half with venues swapped
def synthetic_season(seed: int, scenario: Mapping[str, object], overdispersion: float,
                     settings: Mapping) -> dict[str, dict[str, pd.DataFrame]]
    # league name -> {descriptor key: frame in the TABLE SCHEMA of 2.2 (that descriptor's
    # columns only), valid = True}; the secondaries only when scenario["secondaries"]
def synthetic_match_events(seed: int, *, teams: int, side_effect: float) -> dict[str, pd.DataFrame]
    # keys: actions (joined, I3 shape), matches, match_meta, sheet_dismissals; tiny, for table tests
def design_effect(settings: Mapping, overdispersion: float) -> float
def run_gate(config: dict, *, workers: int) -> dict
```

`settings` is the season configuration of `season_seed_rule` (below): `config.json` with
`seed` and `bootstrap_replicates` replaced. `synthetic_season` reads from it `leagues`,
`expected_teams_per_league`, `exposure_unit_seconds`, `secondary_descriptors`,
`strength_tercile_count` and `synthetic_gate`, and nothing else; `design_effect` reads
`synthetic_gate` from the same mapping.

`synthetic_season` builds one league per entry of `leagues`, in that order and under that name,
league `l` with `T = expected_teams_per_league[l]` teams (`synthetic_gate.league_rule`); its
keys equal `leagues`, in order, so every league subset, gate and criterion of the evaluation
reads the names the real run reads. Per league:

| Quantity | Law (constants in `synthetic_gate`) |
|---|---|
| strength | `s_t ~ N(0, 1)` |
| fixtures | `berger_tables(T)` (`schedule_rule`); round `r` on `first_round_date + days_between_rounds * r`, plus `winter_break_extra_days` for `r >= T - 1`; match `i` of a round one day later when `i` is odd |
| goals | home `~ Poisson(exp(home_intercept + strength_slope (s_h - s_a)))`, away `~ Poisson(exp(away_intercept + strength_slope (s_a - s_h)))` |
| attacker shape | `alpha_t ~ N(0, sd_attacker_shape^2 I_2)` on `(z1, z2)`; plus `home_shape_attacker` when the attacker is at home |
| defender shape | `delta_t = (N(0, sd_side^2), N(0, sd_width^2))`, plus `strength_shape * f * (+1, -1)` by `strength_shape_rules[strength_shape_rule]` (`latent_tercile`: `f` from the latent-strength tercile; `measured_points`: from the points per match of the season's goals, drawn before the team terms) |
| defender level | `lev_t ~ N(0, sd_level^2)` |
| row composition | `p = ilr^-1(ilr(league_composition) + alpha_att + home term + delta_def + N(0, overdispersion^2 I_2))`, parts ordered `(def_left, def_centre, def_right)` |
| row total | `N ~ Poisson(mean_events_per_row * window_exposure * exp(level_strength_attacker s_att - level_strength_defender s_def + lev_def + home_level [attacker at home] + N(0, sd_match_level^2)))` |
| counts | `Multinomial(N, p)`, written to the `att_right`, `att_centre`, `att_left` columns of `end_lateral_thirds` of `f3_entry_pass` in the defender's `against__` columns |
| secondaries | `secondary_laws`: S1 from the primary's counts; S2 to S5 each with its own `league_composition` and `mean_events_per_row`, the same attacker, home, overdispersion and level laws (its own draws), and no defender term; for a two-part secondary (S3, S5) every two-dimensional term is a one-dimensional draw with the same standard deviation and the home term is the first component of `home_shape_attacker` (`secondary_laws.rule`); every secondary's counts written where its descriptor reads them: S2 and S3 in the defender's `against__` columns, S4 in the unit's `for__` columns, and S5's first part in the unit's `for__defensive_action_high` and its second in `against__own_60_pass` |
| other columns | `window_seconds = exposure_unit_seconds * window_exposure`; `goals_for/against`; `match__completed_passes ~ Poisson(mean_completed_passes * exp(pass_strength_slope * s_t))` |

One `np.random.default_rng(seed)` per season, consumed league by league in the order of
`leagues`, in the same order in every scenario. Within a league: first the strength, a vector
over teams in team order. Then the goals of every fixture in schedule order, each match's home
goals then its away goals. Then the other team draws, each a vector over teams in team order,
per subject (the primary, then each generated secondary in the order of
`secondary_descriptors`; S1 draws nothing): its attacker shape and, for the primary only, the
defender shape and the defender level. The defender shape draws only its two normal
components. Its `strength_shape` term is added without a draw, with `f` read from the latent
strength (`latent_tercile`) or from the points per match of the goals already drawn
(`measured_points`; three points for a win, one for a draw). Then, fixture by fixture in
schedule order, the home row and the away row, each drawing per subject in the same order its
shape noise, its level noise, `N` and the counts, and last the row's
`match__completed_passes`. The `goals_for` and `goals_against` columns are the goals drawn
above.

The season's seed (`season_seed_rule`) is the `seed` of the configuration its evaluation
reads. That configuration is `config.json` with exactly two keys replaced, `seed` by the
season's seed and `bootstrap_replicates` by `synthetic_gate.bootstrap_replicates`; every other
key, `leagues`, `exposed_leagues`, `unexposed_leagues`, `expected_teams_per_league`,
`world_strata`'s order and every gate minimum included, is read unchanged, and `run_gate`
asserts that the two configurations differ in those two keys only. So the season's world is
`default_rng(season seed + seed_streams.season_world)`, as in 4.3, and its donor maps hash the
season seed; `seed_stride_per_season` exceeds every value of `seed_streams`, so no season's
generator or engine stream is another season's.

`design_effect(settings, overdispersion)` (`design_effect`): `default_rng(design_effect.seed)` draws
`rows` rows from the generator's row law with no team terms; `w = -ln(q_shifted / q_league)`
per part for `reference_shift`; returns `Var(n . w) / E[N]` at `overdispersion` over the same
at 0. It is reported beside every detection rate. The reviser's implementation gave 1.1, 3.3
and 6.1 at the three grid values.

`synthetic_match_events`: a double round-robin of `teams` teams (four in every test and in the
gate's frame control) whose attackers complete entry passes; the defender of each match receives
extra entries on its **left** (attacker's right, end `y > 2/3`) with odds multiplied by
`exp(side_effect)` for team 0 only. Each entry is paired with a `Ground defending duel` record
of the defender at the point-mirrored coordinate `(1 - x, 1 - y)`. Includes: goals from `shot`
rows, a goal flag on a row that is not a shot, one own goal on a row that also carries the goal
flag, one red card, one second yellow, a `save` row carrying the goal tag (with
`goal_on_scoring_event` false), a goal and a pass sharing one second, one completed pass with a
`(1,1)` end, one shot, one penalty and one direct free-kick shot (for the oracle), one match
whose sheet goals disagree with its events, and one whose sheet lists a dismissal its events do
not carry. Its event layout (coordinates, clock values, which match carries which incident) is
written in the function, which `test_no_number_is_hard_coded` exempts by name; `seed`, `teams`
and `side_effect` are its arguments, and the gate reads them from
`synthetic_gate.frame_negative_control` (section 10).

## 6. `galactico/validation/conceded_shape_sb.py` (LOCAL tier)

Never imported by product code. Reads only through `sb_reader` (I11), under
`replication.sb_root`, folders `replication.leagues`; matches come from each folder's match index
only (`read_matches`), so a delisted file on disk never becomes a match (KNOWN_LIMITATIONS);
listed matches whose files are absent are counted as invalid: they are not rows of the table,
and G1's denominator is the listed count (`listed_matches` below). Returns frames that
`build_team_match_table` accepts unchanged. Before any file is read, `run_replication` checks
that every folder of `replication.leagues` and its match index exist; an absent one is
`DATA_MISSING` for every comparable descriptor (`replication.inconclusive_reason_rules`), not
an exception.

Memory (ROOT section 4, no process over about 1.5 GB): one folder is read at a time.
`read_events` builds one Python dict per event before its frame, so `load_sb_league` calls it in
batches of `replication.sb_events_batch_matches` listed match ids, ascending, keeps only the
columns the mapping below needs for I3, concatenates the batches in order and frees each
batch's frame before the next; card names are read through `iter_events`, one file at a time.
The frames do not depend on the batch size (a test).

```python
def load_sb_league(root: Path, folder: str, config: Mapping) -> dict[str, pd.DataFrame]
    # keys: actions (joined shape of I3), matches, match_meta, sheet_dismissals; plus
    # "card_names" and "listed_matches", an int: the number of matches the folder's index
    # lists, len(frame) + len(missing ids) of read_matches
def vocabulary_check(root: Path, folder: str, config: Mapping) -> dict
def orientation_check(root: Path, folder: str, config: Mapping) -> dict

@dataclass(frozen=True)
class ReplicationRun:
    statuses: dict[str, dict]      # every descriptor of descriptor_parts: {status, reason}
    artifact: dict | None          # the local artifact's payload; None when no comparable
                                   # descriptor reached step 3 of status_rule

def run_replication(config: dict, tokens: Mapping[str, str],
                    frozen: Mapping[str, Mapping[str, float]]) -> ReplicationRun
    # tokens: the Pappalardo token of each descriptor; frozen: per descriptor its k_context,
    # k_unit. It writes no file: the runner writes or compares the artifact (7.4)
```

Frozen mapping (keys read with single-quoted strings; no schema key in double quotes):

| Neutral field | StatsBomb source |
|---|---|
| `game_id`, `team_id`, `player_id` | `sb_game_id`, `sb_team_id`, `sb_player_id` of `read_events` |
| `period` | `1 -> "1H"`, `2 -> "2H"` (`sb_regulation_periods`); other periods kept as their number string and never in a window |
| `seconds` | `period_seconds` of `read_events` |
| `type`, `subtype` | `Pass` with `pass_type` in `sb_open_play_pass_types` (the missing type, Recovery, Interception, Kick Off) -> `pass` / `"Pass"`; other `Pass` -> `set_piece` / its type; `Shot` with `shot_type` in `sb_open_play_shot_types` -> `shot`; other `Shot` -> `set_piece` / its type; every other kind -> `other` / the kind |
| `success` | `pass`: `True` when `has_outcome` is false, else `False`; others `None` |
| `start_x, start_y`, `end_x, end_y` | `read_events` with `scale = sb_location_scale` (an absent location is NaN; an end only from the pass, carry or shot detail); for a row without an end, the start |
| `key_pass`, `interception` | `False` (S4 and S5 are `NOT_COMPARABLE`; the oracle columns are not used) |
| `event_id` | the event id string (`str`; on the Wyscout side `int64`) |
| `own_goal` | kind `== sb_own_goal_kind` (the conceding team's record; a goal of the other team, as in Wyscout) |
| `goal_on_scoring_event` | `Shot` whose `outcome == sb_goal_shot_outcome`, any shot type |
| `card` | the card name in the event's `foul_committed` or `bad_behaviour` detail (`sb_card_detail_keys`, read through `iter_events`): `"Red Card" -> "red_card"`, `"Second Yellow" -> "second_yellow"`, `"Yellow Card" -> "yellow_card"` |
| `matches.date`, home and away ids; `match_meta` goals | `read_matches`: `date`, `home_sb_team_id`, `away_sb_team_id`, `home_goals`, `away_goals` |
| `matches.competition` | the folder name, a member of `replication.leagues` |
| `sheet_dismissals` | per team and match, the players `read_team_sheets` marks `dismissed`, with `dismissal_card_types_exclude = sb_sheet_card_types_not_dismissal` |

No sentinel rule applies (`wy_location_sentinels` is Wyscout's); `coordinate_range` and the
finiteness rule do. `vocabulary_check` (before any replication loss): the pass and shot types
of `folder_vocabulary` and the card names seen are compared with `sb_known_pass_types`,
`sb_known_shot_types`, `sb_known_card_names`, names only; a name outside a list gives
`REPLICATION_INCONCLUSIVE (VOCABULARY)` for every comparable descriptor. `orientation_check`
(structure, before any replication loss): over at least `orientation_check_minimum_matches`
matches, the mean `start_y` of `pass` rows whose event `position.name` (read through
`iter_events`) is `orientation_positions.left` is below `orientation_threshold`, and that of
`orientation_positions.right` above it; otherwise `REPLICATION_INCONCLUSIVE (ORIENTATION)`.
Neither raises. Known differences, stated in `analysis.md`: StatsBomb coordinates are
continuous, so few rows sit on a cut; the box rectangle is each provider's own; StatsBomb
pass types Recovery and Interception are open-play passes, and on the Wyscout side a pass after
a recovery or an interception is an ordinary pass too; both providers' open-play passes include
head passes.

`run_replication` is the only replication entry point; the runner calls it with the Pappalardo
tokens and each descriptor's selected `k_context` and `k_unit`. For every descriptor of
`descriptor_parts` it returns `{status, reason}` from `replication_status` (4.3); the level
subject has no entry. For each descriptor whose token is `run_only_if_descriptor_verdict` and
that is in `comparable_descriptors`, the checks run in this order and stop at the first that
fails, which is therefore the first reason that holds in `inconclusive_reasons` order: the
existence check above (`DATA_MISSING`, before any file is opened); `vocabulary_check`
(`VOCABULARY`); `orientation_check` (`ORIENTATION`); a folder whose index lists a number of
matches other than `expected_matches` (`SAMPLE`). Then the `_sb` definitions through
`build_team_match_table`; `evaluate_replication` (4.3) with `kA` and `kD` frozen and
`listed_matches` the listed count of each folder, every row of the season (`evaluation_start =
season_start` for this arm), in its own `SeasonWorld` (`seed + seed_streams.replication_world`,
`replication.bootstrap_replicates`, strata in the order of `replication.leagues`), a failed G1
or G3 being `SAMPLE`. When at least one comparable descriptor reached step 3 of `status_rule`
(its token is `run_only_if_descriptor_verdict`), it returns as `artifact` the payload of
`replication.local_artifact`: per such descriptor the shape of `descriptors[key]` restricted to
`gates`, `events`, `shape_ladder`, `p1`, `m1` (those it computed) and `status`, plus
`folder_digests`, the `folder_manifest` digest of each folder of `replication.leagues` whose
match index exists, and `null` for one whose folder or index is absent
(`replication.local_artifact_records`; ADR-0027 allows a digest of a provider's files, and this
one is never committed). Otherwise `artifact` is `None` and no local artifact exists. It writes
no file and returns the statuses and the artifact; the runner writes or compares the artifact
under `output_root` (7.4). An exception inside it is handled by the runner (7.4).

## 7. `experiments/run_conceded_shape.py`

### 7.1 Commands

```powershell
# pre-outcome, synthetic only (anyone may run it; root commits the stamp in its own commit)
.venv\Scripts\python.exe -X utf8 experiments\run_conceded_shape.py gate --workers 4
# THE single command of the real execution (root, once)
.venv\Scripts\python.exe -X utf8 experiments\run_conceded_shape.py real
# determinism re-run (root, once): recomputes, compares, writes only the determinism record
.venv\Scripts\python.exe -X utf8 experiments\run_conceded_shape.py real --verify
# helper, no data: print fingerprints, source hashes and the pipeline hash
.venv\Scripts\python.exe -X utf8 experiments\run_conceded_shape.py fingerprints
```

| Subcommand | Writes |
|---|---|
| `gate` | `experiments/preregistered/E-10-conceded-shape/synthetic_gate.json` (root commits it in its own commit, so the tree is clean again before `real`) |
| `real` | under `output_root` only (ROOT 2.9 Z1: one directory for both arms' files, which git ignores, `data/licensed/`, as E-11's; nothing under it is committed), all in stage `serialise`: `output_results`; when a comparable descriptor (`replication.comparable_descriptors`) reaches `DEFENDER_SHAPE_SIGNAL`, `replication.local_artifact` (`ReplicationRun.artifact`, section 6); on a replication exception, `replication_failure_log`. On a failed execution: a record appended to `failed_run_log` and nothing else |
| `real --verify` | `determinism_record` only; on a byte difference or an exception, the removal and the failed-run record of 7.4 |

The results commit copies `output_results` unchanged into `committed_experiment_dir` (its
sha256 equals the one `real` printed). Files are written by the runner itself: UTF-8, LF,
`json.dumps(obj, indent=1, sort_keys=True, allow_nan=False) + "\n"`. Nothing is printed to
stdout except progress on stderr (a PowerShell redirect would re-encode the artifact) and, at
the end, the sha256 of `results.json`. No timestamp, hostname or absolute machine path enters
`results.json` (the config echo and `source_hashes` hold repository-relative paths only).

### 7.2 `real` refuses to start when

Exit 2 with a one-line reason; nothing is written.

| Check | Rule |
|---|---|
| committed protocol | `preregistration.md`, `config.json`, `PIPELINE.md`, `descriptor_test_vectors.json` exist in `HEAD` (`git ls-files --error-unmatch`) and are unchanged since the commit that first added each |
| pipeline hash | `lf_sha256(PIPELINE.md) == pipeline_spec_sha256` |
| output root | `output_root` resolves under `data/licensed/`, `git check-ignore` reports it ignored, and `output_results`, `failed_run_log`, `replication_failure_log`, `determinism_record` and `replication.local_artifact` all resolve under it |
| clean tree | `git status --porcelain` is empty (untracked files included: an untracked module or `sitecustomize.py` refuses; the outputs under `output_root` are ignored and so never refuse) |
| output absent | without `--verify`: neither `output_results` nor `committed_experiment_dir/results.json` exists (one execution). With `--verify`: `output_results` exists |
| failed runs on the record | if `failed_run_log` exists, the committed `analysis.md` at `HEAD` contains the sha256 of its bytes. The same rule is stated in 7.4 and in the protocol; an `analysis.md` that records only the failures may be committed for this, and is completed in the results commit |
| fingerprints | every `TEAM_DESCRIPTORS[key].fingerprint` equals `descriptor_fingerprints[key]`, and every `TEAM_DESCRIPTORS_SB[key].fingerprint` equals `descriptor_fingerprints_sb[key]` |
| synthetic gate | `synthetic_gate.json` exists in `HEAD`, `passed` is true, and its `config_hash`, `protocol_hash`, `pipeline_hash`, `vectors_hash` and `code_hash` equal the current ones |
| licence | `assert_may_host(provider)`; `load_public` refuses any other provider |
| sidecar | for every league, `sidecar.verify` passes and `load` and `attach` do not raise (I2 to I5), and every team of every match of `matches` has at least one `squads` row (structure only) |
| leagues | every league has `expected_teams_per_league` teams; `exposed_leagues` and `unexposed_leagues` are disjoint and their union is `leagues` |

`protocol_commit` is read with `git log --diff-filter=A --format=%H -- <preregistration.md>`;
never a literal. `git` unavailable is a refusal, not a skip.

### 7.3 Hash discipline

| Hash | Over |
|---|---|
| `protocol_hash`, `config_hash`, `pipeline_hash`, `vectors_hash` | `lf_sha256(path)` |
| `source_hashes[posix path]` | `lf_sha256` of: `galactico/validation/conceded_shape.py`, `conceded_shape_synthetic.py`, `conceded_shape_sb.py`, `features/team/{__init__,descriptors,estimator,match_table}.py` (the estimator of 3.8 among them, ROOT 2.9 Z3), this runner, `validation/digests.py`, `validation/sb_reader.py`, `ingestion/sidecar.py`, `storage/public.py`, `reliability/core.py`, `reliability/confound.py`, `domain/precision.py` (its `format_plain` writes the audit's `failures` words), `domain/thesis.py` (the runner's key check) |
| `code_hash` | `lf_sha256_text("\n".join(f"{path} {hash}" for path sorted))` |
| `input_frame_hashes[league][frame]` | `sha256(pd.util.hash_pandas_object(canonical, index=False).values.tobytes())` where `canonical` = the columns the pipeline reads, in the order of section 1, index reset, sorted stably by every one of those columns in that order, nulls last (`event_id` alone orders `actions` and `game_id` alone `matches` and the sidecar `matches`, both unique; `squads` rows that tie on every read column are identical, so the order among them cannot change the bytes); the sidecar's own content hashes are in `provenance.sidecar` |
| `table_hashes[league][window]` | same recipe over the table sorted by `(game_id, team_id)`, columns sorted by name |
| `world.fingerprint` | `SeasonWorld.fingerprint` (4.3) |
| `synthetic_gate_hash` | `lf_sha256(synthetic_gate.json)` |

Parquet file digests are not recorded: they embed the writer's library version and differ
between machines. Content hashes do not.

### 7.4 Structure of `run_real`, and failure

```python
def load_league(league: str, config: dict) -> dict[str, pd.DataFrame]   # I1 to I5, joined
def league_tables(frames, config) -> dict[str, tuple[pd.DataFrame, pd.DataFrame]]   # window -> (table, audit)
def run_real(config: dict, *, verify: bool) -> dict           # one league in memory at a time
def run_gate(config: dict, workers: int) -> dict
def main(argv: Sequence[str] | None = None) -> int
```

The replication is `conceded_shape_sb.run_replication` (section 6); the runner has no function
of its own for it. Stages (names for the failure logs): `refusals`, `load`, `tables`, `world`,
`descriptors`, `level`, `study`, `replication`, `serialise`. Paths are anchored on
`Path(__file__)`. No pool in `real`. `gate` may use a process pool of at most
`workers_maximum`; results must not depend on the worker count (seasons are seeded
individually and collected in seed order).

**Writing.** No stage before `serialise` writes a file: `run_replication` returns its statuses
and its artifact payload (section 6), and a replication exception is held in memory as its
record. In stage `serialise`, after the checks of "Before writing" below, `real` writes
`output_results`, then `replication.local_artifact` when `ReplicationRun.artifact` is not
`None` (the same `json.dumps` form as 7.1), then `replication_failure_log` when the
replication raised.

**A failed execution** is an exception after the refusal checks in any stage but
`replication`. It appends one record to `failed_run_log` (exception type, stage, the file and
line of the innermost frame in the E-10 sources, source hashes; never the message) and exits
3; nothing else is written and nothing from the run may be read. An exception while files are
being written removes every file this execution wrote under `output_root` (`output_results`,
the local artifact and the replication failure log included) before the record is appended,
so a failed execution leaves no output but its record. The repair may touch only the failing
stage; the gate stamp is regenerated and recommitted; the next execution starts only when the
committed `analysis.md` at `HEAD` contains the sha256 of the log's bytes (the refusal check of
7.2, the same words).

**An exception in `replication`** is not a failed execution. It is caught; its type, stage,
file and line and the source hashes (never the message) form the record written to
`replication_failure_log`, not to `failed_run_log`; every descriptor whose replication status
reached step 3 of `replication.status_rule` is `REPLICATION_INCONCLUSIVE` with reason
`FAILED_RUN` (`NOT_COMPARABLE` and `NOT_RUN` stand); no local artifact is written;
`output_results` is written; the replication is not attempted again. `failed_run_log`
therefore holds the records of exit-3 executions and of `--verify` failures (below), none of
which leaves an `output_results`, and a replication exception never blocks the determinism
re-run of an execution that succeeded.

**`real --verify`** recomputes everything except a replication whose first-run status is
`FAILED_RUN`, which it takes unchanged from `output_results` without attempting it. It writes
no output file: it reads the bytes of `output_results` and, when it exists,
`replication.local_artifact` before it recomputes, and compares them in memory with the
recomputed bytes (the local artifact's existence included). It writes only
`determinism_record` (`{results_sha256, recomputed_sha256, local_artifact_equal, equal}`, no
number from the run). On any byte difference, or on an exception in any stage of the re-run
other than a replication exception (which sets `FAILED_RUN` as above, writes no log under
`--verify`, and then shows as a byte difference), it removes `output_results` and `replication.local_artifact` (they are never
committed, and nothing from them may be read), appends one failed-run record (stage
`serialise` for a byte difference, the raising stage for an exception) and exits 1. There is
no second determinism re-run (`determinism_reruns`): the next execution is a new `real` under
the failed-execution rule above, followed by its own `real --verify`.

**Before writing**, in stage `serialise`, the runner asserts on the in-memory payload:
`allow_nan=False` serialises it; its size, echo included, is at most `results_maximum_bytes`;
the substring scan of section 8 finds none of `forbidden_result_substrings`;
`banned_key_paths(payload) == []`; no key at any depth contains a name of
`forbidden_result_key_names`; `interpretation`, `uncertainty_limit`, `product_effect`,
`provenance.data_license` and `provenance.reuse_disclosure` are present and equal their
`results_strings` entries; and every `identity_stress.note` that exists equals
`results_strings.identity_stress_note`, with no requirement that one exists (a descriptor whose
gates failed has no `identity_stress`, section 8). A failure is a failed execution of stage
`serialise`.

### 7.5 Which code reads which `config.json` key

`test_config_has_every_key_the_pipeline_reads` asserts this table against the code: every key
is read by its consumer, and no consumer reads a number from anywhere else.

| Consumer | Keys |
|---|---|
| `load_league`, coverage | `provider`, `leagues`, `expected_teams_per_league`, `season_start`, `end`, `exposed_leagues` (coverage only, and the 7.2 assertion that it and `unexposed_leagues` partition `leagues`; no criterion reads it), `unexposed_leagues` |
| table build | `windows`, `window_primary`, `window_sensitivity`, `regulation_periods`, `goal_incident_columns`, `dismissal_cards`, `exposure_unit_seconds`, `wy_location_sentinels`, `coordinate_range` |
| geometry test (product code cannot read an experiment config, so `descriptors.py` holds the values and a test asserts equality) | `fraction_rule`, `final_third_x`, `lateral_left_below_y`, `lateral_right_above_y`, `depth_own_third_below_x`, `depth_opposition_third_from_x`, `penalty_box_wy`, `penalty_box_sb`, `high_zone_x_min`, `own_60_x_max`, `defensive_action_clauses`, `descriptor_schema`, `descriptor_parts`, `descriptor_mirror_pairs`, `descriptor_fingerprints`, `descriptor_fingerprints_sb`, `regulation_periods`, `dismissal_cards`, `goal_incident_columns`, `wy_location_sentinels`, `coordinate_range`, `exposure_unit_seconds` |
| forward passes (the pseudocount passed to the estimator of 3.8 as `league_pseudocount`) | `minimum_prior_matches`, `league_prior_pseudocount_per_part`, `log_ratio_smoothing_per_part`, `raw_persistence_matches`, `shrinkage_grid`, `unit_term_boundary_candidate`, `permutation_seeds`, `strength_tercile_count`, `seed` |
| selection | `evaluation_start`, `selection_tie_tolerance` |
| gates | `minimum_valid_match_share_per_league`, `minimum_development_rows_per_league`, `minimum_development_weeks_per_league`, `minimum_evaluation_rows_per_league`, `minimum_evaluation_weeks_per_league`, `minimum_evaluation_events_per_league`, `minimum_reliability_teams`, `minimum_half_matches_per_team`, `minimum_permutation_changed_share`, `shape_gates`, `level_gates` |
| resampling | `leagues` (strata order), `bootstrap_replicates`, `interval_quantiles`, `interval_quantile_method`, `seed_streams`, `calendar_week_rule`, `zero_tolerance` |
| criteria | `leagues` ((b), (Lb), the per-league subsets), `unexposed_leagues` ((f), `p1.unexposed`), `criterion_alpha_one_sided`, `minimum_leagues_with_negative_estimate`, `level_minimum_leagues_with_negative_estimate`, `holm_family_alpha_one_sided`, `holm_family_size`, `reliability_critical_value`, `reliability_band`, `reliability_number`, `house_reliability_critical_value`, `house_reliability_confidence`, `season_label` (the house bound's period, passed to `split_half` and `level_split_half` as `period`), `strength_covariates`, `strength_variance_explained_ceiling`, `strength_spearman_floor`, `strength_top_k`, `strength_top_k_survival_floor`, `strength_tie_policy`, `strength_permutations`, `interaction_minimum_events_per_meeting`, `calibration_minimum_events_per_row` |
| verdicts and registry | `verdict_vocabulary`, `verdict_precedence`, `registry_*`, `lifecycle_status`, `subject_groups` |
| study layout | `primary_descriptor`, `secondary_descriptors`, `level_subject`, `committed_experiment_dir`, `version`, `experiment_id`, `registry_experiment_id`, `tier` |
| runner | `pipeline_spec_sha256`, `output_root`, `output_results`, `failed_run_log`, `replication_failure_log`, `determinism_record`, `results_maximum_bytes`, `results_strings` (copied verbatim, asserted), `forbidden_result_substrings`, `forbidden_result_substrings_scope` (the scan of section 8 follows it; the runner applies it before writing, 7.4), `forbidden_result_key_names`, `determinism_reruns` |
| replication | every key of `replication` |
| synthetic gate | every key of `synthetic_gate` |
| estimator constant test (3.8; product code cannot read an experiment config, so `estimator.py` holds the value and a test asserts equality) | `league_prior_pseudocount_per_part` |
| served panel test (section 12.3) | `served_panel`, `product_rules`, `registry_non_claims` |
| root's checks before registration (no pipeline code reads them; the test asserts they are present) | `verified_by_root_before_registration`, `dismissal_assumption_minimum_share`, `dismissal_check_fallback` |
| restated rules (strings; the test asserts they are present, code does not branch on them) | `prior_rule`, `state_change_rule`, `goal_incident_rule`, `dismissal_check`, `validity_reasons`, `validity_scope`, `lateral_edge_rule`, `fingerprint_rule`, `shrinkage_grid_unit`, `selection_tie_rule`, `selection_scope`, `level_selection_rule`, `evaluation_events_rule`, `world_cluster`, `world_strata`, `world_draw`, `donor_seed_rule`, `permutation_strata`, `strength_tercile_key`, `strength_tercile_source`, `strength_covariate_sources`, `strength_confound_kind`, `strength_confound_reasoning`, `p_value_rule`, `holm_order_rule`, `reliability_split`, `reliability_centring`, `persistence_rule`, `peers_level_rule`, `raw_persistence_level_rule`, `strength_survival_tails`, `reliability_interval_method`, `reliability_degrees_of_freedom`, `house_reliability_reported_only`, `interaction_reported_only`, `hash_policy`, `key_naming`, `not_run_in_this_experiment` |

## 8. `results.json`

Aggregate only. No player identifier or name, no team-level row, no key that
`banned_key_paths` refuses (`rank`, `score`, `rating`, `index`, `grade`, `total` and the rest of
`BANNED_KEYS`), no key naming a provider at any depth. At most `results_maximum_bytes`, echo
included. The registry reads `experiment`, `tier`, `verdicts` and
`provenance.protocol_commit` and `provenance.protocol_hash` (`tests/test_verdict_registry.py`);
files are written with sorted keys, so no key order is a contract.

The substring scan (`forbidden_result_substrings_scope`) reads the exact text that will be
written, `json.dumps(payload_without_echo, indent=1, sort_keys=True, allow_nan=False)`, where
`payload_without_echo` is the payload with the single key `provenance.config` removed. The
echo is exempt because it equals the committed `config.json` (`tests/test_digests.py` asserts
that), and the config holds the list of forbidden substrings itself. The key-name rules and
`banned_key_paths` still read the whole payload, echo included. The runner applies all of
them before writing (7.4).

```
experiment: "E-10"
tier: "PUBLIC"
verdicts: {subject: {token, reasons}}          # the seven subjects of subject_groups
headline: {primary: token, level: token}
provenance:
  protocol_commit, protocol_hash, config_hash, pipeline_hash, vectors_hash,
  pipeline_spec_sha256, config (verbatim), source_hashes, code_hash, hash_policy,
  packages {numpy, pandas, pyarrow}, team_match_version, loader_version,
  descriptor_schema, descriptor_fingerprints, descriptor_fingerprints_sb,
  sidecar {league: sidecar.provenance(league)}, sidecar_schema_version, tag_mapping_version,
  input_frame_hashes, table_hashes, world {fingerprint, replicates, clusters, strata},
  synthetic_gate_hash, data_license, reuse_disclosure    # the two: results_strings, verbatim
coverage[league]:
  matches, valid_matches, invalid_by_reason, teams, teams_with_more_than_one_coach_id,
  development {rows, eligible_rows, weeks}, evaluation {rows, eligible_rows, weeks},
  window {events_in_window_share, median_window_seconds}, dropped_location {event_set: n}
gates[subject]: {gate: {passed, detail}}
descriptors[key]:
  role ("primary" | "secondary"), fingerprint, parts, mirror_pairs, gates_passed,
  # when gates_passed is false, of the keys below only token, reasons and lifecycle_status
  # are present (G6 included: a non-finite selection loss is never serialised)
  events {development, evaluation, by_league},
  selection {k_context, k_unit, context_losses {k: loss}, unit_losses {k | "context_only": loss}},
  shape_ladder {rung: {pooled, by_league}}            # B0_B2, B1_B4, B3, B5, B6, candidate
  p1 {pooled: ClusterEstimate, by_league {league: ClusterEstimate}, unexposed: ClusterEstimate},
  m1 ClusterEstimate | null,
  identity_stress {placebo_p1 [P], placebo_k_unit [P], donor_changed_share [P],
                   placebos_at_or_below, strictly_below_every_placebo,
                   note},                           # note: results_strings.identity_stress_note
  calibration {coordinate: {slope, interval}} | null,
  reliability {coordinates {name: {half_r, spearman_brown, lower_bound, house_lower_bound,
                                   implied_per_match_icc}},
               n_teams, teams_dropped, minimum_lower_bound, render},
  persistence {coordinate: {r, n_teams}},
  strength_validity {coordinates {name: {r2, r2_adjusted, noise_floor, permutation_p,
                     spearman_raw_vs_residual,                      # from the upper call
                     top_k_survivors, top_k_tied_raw, top_k_tied_adjusted,       # upper tail
                     top_k_survivors_lower, top_k_tied_raw_lower,
                     top_k_tied_adjusted_lower,                                  # lower tail
                     failures, passed}}, kind, passed},    # failures prefixed by tail
  holm {p_one_sided, order_position, threshold, rejected} (secondary only),
  criteria {a, b, c, d, e, f, g}, token, reasons, lifecycle_status,
  # primary only
  interaction {coordinate: {estimate, interval, n_directed_pairs}},
  sensitivity {all_states: {p1, reliability}}
level:
  gates_passed,
  # when gates_passed is false, of the keys below only token, reasons and lifecycle_status
  # are present (LG6 included: a non-finite selection deviance is never serialised)
  selection {k_context, k_unit, context_deviances, unit_deviances},
  deviance_ladder {rung: {pooled, by_league}},       # B0, B1, B2, B3, B5
  l1 {pooled, by_league, unexposed},                 # unexposed: over unexposed_leagues, in
                                                     # the shared world, reported only
  reliability {coordinates {log_rate: {half_r, spearman_brown, lower_bound, house_lower_bound,
                                       implied_per_match_icc}},
               n_teams, teams_dropped, minimum_lower_bound, render},
  strength_validity (level_strength_validity: the descriptors' shape, coordinate log_rate;
                     kind CONTEXT, reported),
  criteria {La, Lb, Le}, token, reasons, lifecycle_status
replication[key]: {status, reason}   # every descriptor key, none for the level; tokens only
interpretation, uncertainty_limit, product_effect     # results_strings, verbatim
```

`ClusterEstimate` serialises as `{estimate, interval, p_one_sided, rows, weight, clusters,
holes}`. Coordinate names: three parts `side_balance`, `wide_versus_centre` for the two
conceded-channel descriptors and `first_versus_last`, `ends_versus_middle` otherwise; two parts
`first_versus_second`. A subject whose gates failed has `token` `INCONCLUSIVE` and its failed
gates as reasons. The figures of section 12.2 point into this shape.

`synthetic_gate.json`: `{config_hash, protocol_hash, pipeline_hash, vectors_hash, code_hash,
base_seed, design_effect {str(overdispersion): D} (one entry per value of
`overdispersion_grid`), runs [{scenario, overdispersion, design_effect, seasons,
primary_tokens, level_tokens, secondary_family_tokens, criterion_pass_counts,
selected_k_unit_counts, median_p1, median_reliability_lower_bound, holm_family_rejections}]
(each run's `design_effect` is the entry of its overdispersion), requirements [{scenario,
overdispersion, subject, token | status, bound, value, observed, passed}],
frame_negative_control {statistic_with_mirror, statistic_without_mirror,
recovered_sign_with_mirror, recovered_sign_without_mirror, passed}, passed}`.

## 9. Tests (all synthetic or hand-computed; none reads the corpus except the `slow` oracle after registration)

| File | Test | Asserts |
|---|---|---|
| `test_team_descriptors.py` | `test_payloads_match_frozen_vectors` | for `wy` and `sb`: payload, fingerprint, `describe()` and column names equal `descriptor_test_vectors.json`; fingerprints equal `descriptor_fingerprints` and `descriptor_fingerprints_sb` |
| | `test_lattice_and_scale_edges` | every case of 3.5, Wyscout values built as `j / 100.0`, StatsBomb values as `(j / 10) / 120.0` and `(j / 10) / 80.0`; and on both lattices, at every cut of 3.2 and 3.3, the float64 comparison equals the `fractions.Fraction` comparison |
| | `test_remainder_part_and_first_match_wins`, `test_union_counts_each_event_once` | a duel row that also carries the interception flag counts once |
| | `test_changing_a_bound_changes_the_fingerprint`, `test_no_descriptor_reads_duel_success_or_clearance` | |
| | `test_column_names_carry_the_partition_and_never_collide` | two columns with one name and two tokens raise; an anchor outside `needs` raises |
| | `test_window_token_writes_none_only_for_none` | a bound of 0 gives `0`, `None` gives `none` |
| | `test_config_geometry_matches_descriptors` | every value of the geometry row of 7.5 equals the module's constant |
| | `test_log_ratio_basis_is_orthonormal_and_sums_to_zero` | |
| `test_team_match_table.py` | `test_attack_down_attackers_right_lands_on_defenders_left` | synthetic events: entries ending `y = 0.9` are in the defender's `def_left`; the paired defending duels sit at `y = 0.1` in the defender's own frame |
| | `test_without_the_mirror_the_planted_side_has_the_opposite_sign` | negative control (M-01): reading `att_left` as `def_left` flips the recovered sign of the statistic of `synthetic_gate.frame_negative_control` |
| | `test_sentinels_are_wyscout_only_and_out_of_range_is_dropped` | `(1,1)` Wyscout end is not an entry on the attacker's right; the same point with sentinels `()` is |
| | `test_state_window_goals_own_goals_dismissals`, `test_same_second_incident_does_not_change_that_row`, `test_save_row_goal_tag_is_ignored`, `test_goal_flag_on_a_row_that_is_not_a_shot`, `test_own_goal_takes_precedence` | hand-built timeline; `state` and `incidents` carry the columns of 2.1 |
| | `test_window_seconds_hand_example` | closes at 2-0, reopens at 2-1, closes at a red card; `period_ends` holds each period's last second |
| | `test_goals_mismatch_and_dismissals_mismatch_invalidate_both_rows_in_every_window` | validity is the same for `close_11v11` and `all_states`; the `match__` columns of an invalid match equal Match Lab's, its `for__` and `against__` counts are 0 |
| | `test_a_team_match_without_a_sheet_row_raises` | `sheet_dismissals` missing one team of one match raises `ValueError` |
| | `test_row_order_and_input_immutability` | shuffle rows; frames unchanged |
| | `test_against_columns_are_the_opponents_for_columns` | |
| | `test_oracle_against_build_match_synthetic` | 2.5 on a synthetic match with a penalty, a direct free-kick shot and a flagged non-duel row, `build_match` given the extra inputs 2.5 lists |
| | `test_oracle_against_build_match_real` (`slow`, after registration) | 2.5 on five matches per league, `columns=()` |
| `test_team_estimator.py` | `test_hand_computed_two_date_example` | every state quantity of 4.2 (`pi`, `pi_v`, `nu_v`, `A_c`, `A_c^(-u)`, `e`, `O_u`, `E_u`, `delta_u`, `lam_v`, `lam`, `rA_c`, `rA_c^(-u)`, `O'_u`, `E'_u`, `rD_u`), `predicted_shape`, `predicted_level`, `served_composition` and `served_volume` through `state_at`, `shape_estimate` and `level_estimate`, against `fractions.Fraction` arithmetic written in the test; the team ids of the example are not `0..T-1` (for example 11, 23, 37), so the id-to-index mapping is exercised, and an id outside `team_ids` raises `ValueError` |
| | `test_estimator_constant_matches_the_config` | `LEAGUE_PRIOR_PSEUDOCOUNT_PER_PART == league_prior_pseudocount_per_part` |
| | `test_unit_matches_are_excluded_from_its_expected_composition` | (moved from the engine's tests; the exclusion is the estimator's) |
| | `test_rows_on_or_after_the_date_and_invalid_rows_are_not_added` | `state_at` ignores poison rows dated on or after `date` and every invalid row |
| | `test_weights_count_rows_and_zero_removes_them` | an integer weight `w` gives the state of the row repeated `w` times; a weight of 0 the state without it; row order does not matter; inputs unchanged |
| | `test_context_only_gives_zero_delta_and_unit_ratio_one`, `test_served_functions_refuse_context_only` | `k_unit=None` gives `delta` 0 and `k_unit_level=None` `rD` 1; `served_composition` and `served_volume` raise `ValueError` on them |
| | `test_no_argument_has_a_default` | no parameter of a public function of the module has a default |
| `test_conceded_shape_engine.py` | `test_hand_computed_two_date_example` | the rung assembly of 4.2 on the estimator's example (B0 to B7 and the candidate, the B3 and B5 level means included, the mirror swap, the peers' pooled `(O, E)`, the P2 inputs), against `fractions.Fraction` arithmetic written in the test |
| | `test_engine_reads_the_one_estimator` | AST: `conceded_shape.py` imports `galactico.features.team.estimator`, and none of the three research modules defines a function or class named in the estimator's `__all__`; `conceded_shape_synthetic.py` imports from the estimator at most `descriptor_rows`, and only `run_gate` calls it (the generator of section 5 reads none of the estimator). Behaviour, on the estimator's two-date example. Every perturbation moves a composition or a rate; a constant added to every part of `delta` would not, since it cancels in the normalisation and in `basis @ delta`, whose rows sum to zero. With `b = log_ratio_basis(K)[0]`, each monkeypatch is applied alone, and the engine's pooled quantity named beside it must change by more than `1e-6` in absolute value: `estimator.unit_deviation` adding `b` to every row of its result (the candidate loss and the P2 inputs); `estimator.unit_level_ratio` multiplying its result by 2 (the B2 deviance); `estimator.shape_estimate` returning its estimate with one field replaced, in turn `context` by `normalise(context * exp(b))` (the B1 and B4 losses), `nu` by `nu + b` (the B1 loss), `expected` by `expected * exp(b)` (the candidate loss) and `expected_share` by `normalise(expected_share * exp(b))` (the P2 inputs); `estimator.level_estimate` returning its estimate with `rate_venue` (the B0 deviance), `context_ratio` (B1) or `unit_expected` (B2) multiplied by 2. So an engine that holds a copy of any formula of 4.2 under another name, the level ratios included, fails |
| | `test_context_only_is_exactly_b4_and_b1`, `test_delta_is_zero_without_history` | under `context_only` the candidate, mirror, peers and permuted arrays are the B4 array, and the level's B2 and B3 arrays are B1's |
| | `test_context_only_selection_against_grid_selecting_placebos` | a planted history where the real `kD` is `context_only` and every placebo selects a grid value with positive evaluation P1: (a), (b), (f) are `False`; (d) is `False` for a mirror descriptor and `True` otherwise; (c) is `True`; the pooled P1 `p_one_sided` is exactly 1.0; the token is `ADDED_INFORMATION_NOT_SHOWN` and the reasons are exactly the criteria that are not `True` |
| | `test_raw_five_level_is_positive_with_no_recent_event` | a unit with no conceded event in its last `raw_persistence_matches` rows has a finite deviance |
| | `test_future_and_same_day_rows_cannot_change_a_prediction` | poison rows on or after the date |
| | `test_invalid_rows_never_update_state_but_count_on_the_sheet`, `test_row_order_invariance` | |
| | `test_mirror_swaps_only_the_pair`, `test_poisson_multinomial_factorisation` | |
| | `test_donor_map_is_deterministic_within_strata_and_order_invariant` | the seed string is `donor_seed_rule`'s, byte for byte, on a hand example |
| | `test_one_world_for_every_estimand_subset_and_window` | per-league and unexposed replicates are restrictions of the pooled ones; both rows of a match share a weight; the fingerprint changes with one multiplicity; a zero-denominator replicate is a hole |
| | `test_world_labels_strata_and_leagues` | labels are `f"{league}\|{part}\|{week}"` with the house week label and `part` in `development`, `evaluation`; strata follow the `leagues` argument; a league set other than `leagues` raises; a part with no rows has no stratum |
| | `test_cluster_ratio_is_a_ratio_of_sums_with_linear_quantiles_and_the_p_value_rule` | an all-zero numerator gives p = 1 |
| | `test_selection_tie_set`, `test_selection_reads_development_rows_only` | candidates within tolerance of the minimum, not of each other; `context_only` first, then the largest; with candidates `(None, 25, 50, 100)` and pooled losses `(1.0, 1.0 + 1e-13, 1.2, 1.3)`, `select_k` returns `(0, losses)`, an int index, and G6 and LG6 stay true |
| | `test_select_k_returns_none_on_a_non_finite_loss` | `(None, losses)`; G6 (LG6) false, `INCONCLUSIVE`, no further forward pass (monkeypatched to raise) |
| | `test_sensitivity_uses_the_selected_constants_and_the_same_eligible_rows` | the `all_states` P1 reads one forward pass with the selected `kA`, `kD`, no placebo, the same eligible mask and the shared world |
| | `test_split_balances_opponents_and_venues` | each half meets every opponent once; home counts differ by at most one; a missing meeting is not replaced |
| | `test_persistence_follows_its_rule` | league-centred part values, the minimum per part, no step-up, on a hand example |
| | `test_two_part_engine_recovers_a_planted_width_effect` | one seeded season, `sd_width = 0.15`: P1 p-value at most `alpha` for the wide share |
| | `test_replication_path_computes_p1_and_m1_only` | `evaluate_replication` on synthetic rows with no development part: gates G1 and G3 only, from the `replication` minima; no selection, placebo, R1, V1, P2, T1 or I1 is computed (each monkeypatched to raise); a planted effect gives `REPLICATED` and a planted nothing `NOT_REPLICATED` |
| `test_conceded_shape_rule.py` | `test_verdict_truth_tables` | descriptor: every combination of `{True, False, None}^7` with each gate pattern; level: `{True, False, None}^3` with each level gate pattern; each maps to exactly one token, the protocol's, with its reasons and its `registry_outcomes` statement |
| | `test_replication_status_truth_table` | every comparable and not comparable descriptor; every token; `inconclusive` `None` and each of `inconclusive_reasons`; P1 and M1 p-values below, at and above `alpha` and `None`: exactly the protocol's status and reason, including a mirror descriptor with P1 at most `alpha` and M1 above it giving `NOT_REPLICATED`, and `FAILED_RUN` never replacing `NOT_COMPARABLE` or `NOT_RUN` |
| | `test_any_failed_gate_is_inconclusive_and_computes_no_loss` | loss fields absent; forward pass not called (monkeypatched to raise) |
| | `test_level_runs_when_only_g5_or_g6_fails`, `test_level_inconclusive_on_lg6` | |
| | `test_holm_hand_examples` | `m` fixed at `holm_family_size`, `alpha = holm_family_alpha_one_sided`, `order = secondary_descriptors` (S1 to S5). Example 1, p = (S1 0.004, S2 0.007, S3 None, S4 NaN, S5 0.007): positions S1 1, S2 2, S5 3 (the tie in list order), S3 4, S4 5; thresholds 0.005, 0.00625, 0.0083333, 0.0125, 0.025; rejected S1 only (S5 is under its threshold but follows a failure). The wrong readings it excludes: `m` shrinking to the three numbers rejects S1, S2 and S5; `None` ranked first rejects nothing. Example 2, p = (0.0049, 0.0062, None, NaN, 0.0062): rejected S1, S2, S5 at the same positions and thresholds. A p-value of 1.0 (a `context_only` selection) is a number and is ranked |
| | `test_reliability_bound_thresholds` | at `n = 98`, `G = 5`, `c = reliability_critical_value`: `r = 0.4770` gives 0.50009 and `r = 0.4769` 0.49996; `r = 0.6495` gives 0.70001 and `r = 0.6494` less than 0.700; the house bound differs |
| | `test_house_bound_confidence_matches_the_critical_value` | `galactico.reliability.core._CRITICAL_VALUES[house_reliability_confidence] == house_reliability_critical_value` |
| | `test_split_half_known_answer` | 4,000 synthetic units, true plus independent noise: stepped-up value 2/3 within 0.03 |
| | `test_strength_validity_is_the_house_audit_with_frozen_thresholds` | `passed` equals `discriminant_validity(y, ...).passed and discriminant_validity(-y, ...).passed` with the config's thresholds, not the defaults; a shape that is measured strength fails; a tied twelfth place in either tail fails by name, its failure prefixed by its tail; NaN fails |
| | `test_strength_validity_is_invariant_to_negating_a_coordinate` | negating any coordinate (and, for the primary's side balance, exchanging `def_left` and `def_right` in the counts) leaves `passed` and the token unchanged and swaps the per-tail counts. Two 98-value vectors (coordinate and four covariates, five leagues of 20, 20, 20, 18 and 20) are written out in the test, and the test first asserts the properties they were built for: (a) unadjusted `R2` below `strength_variance_explained_ceiling`, Spearman at least `strength_spearman_floor`, 6 of 12 survivors in the upper tail and 5 in the lower, so the one-tail rule passes and this rule fails; (b) the upper tail has no tie and the lower tail a tied twelfth raw place, so this rule fails by name. Hand-built vectors, never draws of a scratch generator |
| | `test_pair_interaction_recovers_a_planted_pair_term_and_zero` | |
| | `test_every_registry_sentence_is_served_under_every_token` | the seven records built from the config pass `finalize` under `PENDING` and every token, with figures under the established ones; a planted `line height` in a non-claim is refused; the proposal sentences, `planning_research_sentence` and `s5_ratio_name` pass the copy guard |
| `test_conceded_shape_synthetic.py` | `test_berger_tables_shape` | every directed pair once, every unordered pair twice with venues swapped, for 18 and 20 teams; the rule of `schedule_rule` |
| | `test_generator_is_seeded_and_emits_the_table_schema` | with and without the secondaries; a two-part secondary draws one-dimensional terms |
| | `test_synthetic_season_feeds_every_league_subset` | one seeded `EFFECT_STRONG` season at overdispersion 0.1: its keys equal `leagues`, in order, each with `expected_teams_per_league` teams; every per-league subset of P1 and L1 has rows; the `unexposed` estimate has rows and a non-`None` estimate; criteria (b), (f) and (Lb) are not `None`; G1 to G3 read non-empty league counts; the world's strata follow `leagues` |
| | `test_season_configuration_differs_in_two_keys_only` | the configuration a season's evaluation reads differs from `config.json` in `seed` and `bootstrap_replicates` only |
| | `test_season_seeds_and_streams_never_collide` | over every scenario, overdispersion and season of the gate, the season seeds and their `seed + seed_streams` values are distinct, and neither `design_effect.seed` nor `frame_negative_control.seed` is among them |
| | `test_design_effect_increases_with_overdispersion` | |
| | `test_small_gate_classifies_planted_effect_and_planted_nothing` | 6 seasons each of `EFFECT_STRONG` and `NULL_NOTHING`, five leagues named by `leagues`, at overdispersion 0.1 and 500 replicates: all six `DEFENDER_SHAPE_SIGNAL`; none in the null |
| `test_conceded_shape_experiment.py` | `test_config_has_every_key_the_pipeline_reads`, `test_no_number_is_hard_coded` | AST scan of the three research modules: every numeric literal is in the allowlist `{0, 1, 2, 3, 8}` declared in the test (indices, the deviance factor, Fisher's `n - 3`, the digest slice), except inside `synthetic_match_events`, which the test exempts by name (its event layout); every threshold, stride, scale, seed and count is read from `config` |
| | `test_results_shape_is_strict_json_aggregate_and_small` | end to end on one five-league synthetic season (`synthetic_season`, leagues named by `leagues`, with the secondaries), through `run_real`'s stages below the refusal checks. The injection, written in the test: the refusal checks are monkeypatched to pass; `load_league` returns, per league, a stub of its frame dict built from the season's tables: `matches` (`game_id`, `competition`, `date`, `home_team_id`, `away_team_id`), `match_meta` (`game_id`, the scores from `goals_for` and `goals_against`, both coach ids null), and empty `actions` and `sheet_dismissals` frames with the columns of I3 and I5; `league_tables` returns for each window of `windows` one table, the league's descriptor frames merged on `(game_id, team_id)` (the same table for `all_states`), and an `audit` built from it (each match valid with reason `""`, the goal columns from `goals_for` and `goals_against`, no dismissal, the period seconds half of `window_seconds` each, `events_in_window` and `events_all_states` the primary's total of the match, every `dropped_location__<event_set>` 0); `sidecar.provenance` is monkeypatched to return a fixed dict written in the test; `provenance.input_frame_hashes` hash the stub frames and `table_hashes` the merged tables, by the recipe of 7.3. The test config differs from the frozen one only in `bootstrap_replicates` and `strength_permutations` (the test lists them and asserts no other key differs). Asserted: `allow_nan=False`, under `results_maximum_bytes`, none of `forbidden_result_substrings` in the payload with `provenance.config` removed, `banned_key_paths(...) == []` and no key at any depth containing `forbidden_result_key_names`, both with `provenance.config` echoed, and the key walker of `tests/test_licensing.py` finds nothing. Two further cases: the full serialised payload, echo included, does contain `player_id` (the exemption is needed); a payload with `player_id` planted outside the echo, in a reason string, is refused by the runner's check |
| | `test_results_strings_are_copied_verbatim` | `interpretation`, `uncertainty_limit`, `product_effect`, `provenance.data_license` and `provenance.reuse_disclosure` are present and equal `results_strings`; every `identity_stress.note` present equals `identity_stress_note` |
| | `test_every_subject_inconclusive_still_writes_results` | the injection of the test above, with `valid` set false (and `invalid_reason` `goals_mismatch`) on enough of one league's matches to put its valid share below `minimum_valid_match_share_per_league`, so G1 fails for every subject: `real` writes `output_results` and exits 0; every token is `INCONCLUSIVE` with its failed gates; no descriptor has `identity_stress` and the level block has no `selection`; the five always-present strings are there; `allow_nan=False` holds |
| | `test_synthetic_results_pass_the_registry_checks` | a synthetic tree with that `results.json` and the seven records of section 12, executed under every token including `DEFENDER_SHAPE_SIGNAL` and `LEVEL_ESTABLISHED` with their figures, passes every checker of `tests/test_verdict_registry.py`; every figure pointer, `/level/reliability/minimum_lower_bound` included, resolves to a value of the figure's JSON type |
| | `test_runner_refuses_dirty_tree_missing_gate_hash_and_fingerprint_mismatch` | monkeypatched git; each row of 7.2; an untracked file outside `output_root` refuses; outputs present under `output_root` do not trip the clean-tree row |
| | `test_verify_passes_after_a_clean_real` | `real`, then `real --verify`, outputs under `output_root`: exit 0, only `determinism_record` written |
| | `test_failed_run_writes_no_results_and_no_message` | a planted exception whose message holds an invented id is absent from the log; no `output_results` |
| | `test_failed_run_on_the_record_lets_the_next_real_start` | a planted exception in a stage other than `replication`; once a committed `analysis.md` holds the log's sha256 the next `real` starts, and before that it is refused |
| | `test_replication_failure_keeps_the_public_results` | a planted exception in `replication`: `output_results` written, `FAILED_RUN` only for descriptors past step 2, `replication_failure_log` written, `failed_run_log` untouched; `real --verify` then passes and does not call `run_replication` (monkeypatched to raise) |
| | `test_verify_mismatch_is_one_serialise_failure` | a planted byte difference: exit 1, exactly one record of stage `serialise` appended, `output_results` and the local artifact removed |
| | `test_verify_exception_is_one_failed_run_and_writes_no_output` | a planted exception in stage `descriptors` of `real --verify`: exit 1, one record of that stage appended, `output_results` and the local artifact removed, no other file written; `run_replication` writes no file in either mode (the local artifact's bytes are compared in memory) |
| | `test_a_serialise_failure_leaves_no_output` | with a replication that returned an artifact and one that raised: a planted failure of a "Before writing" check, and a planted exception while writing the local artifact, each leave under `output_root` only the appended `failed_run_log` record |
| | `test_hashes_are_line_ending_invariant`, `test_rerun_is_byte_identical` | |
| | `test_research_modules_are_not_imported_by_product_code` | AST import scan; `galactico/features/team/estimator.py` imports nothing from `galactico.validation` or `experiments` (the firewall's one direction, ROOT 2.9 Z3) |
| `test_conceded_shape_sb.py` | `test_mapping_on_a_synthetic_event_file` | set-piece passes excluded, kick-off kept; own goal credited to the other team; cards from both details; `(120, 80)` kept; period-relative seconds; `competition` is the folder name |
| | `test_vocabulary_and_orientation_failures_are_inconclusive_not_exceptions` | |
| | `test_data_missing_before_any_read_and_reasons_in_their_order` | an absent folder or index is `DATA_MISSING` with no file opened; an index listing other than `expected_matches` matches is `SAMPLE`; a folder with both an unknown pass type and a wrong listed count is `VOCABULARY`, the first in `inconclusive_reasons` order |
| | `test_absent_files_count_against_g1` | synthetic folders, an index of 380 with 12 matches' files absent and 8 present matches invalid: G1 reads 360 / 380 and fails at `minimum_valid_match_share_per_league`, so the status is `REPLICATION_INCONCLUSIVE (SAMPLE)` (360 / 368 would have passed) |
| | `test_events_do_not_depend_on_the_batch_size` | the frames of `load_sb_league` on synthetic files are equal with `sb_events_batch_matches` 1 and with its config value |
| | `test_local_artifact_only_past_step_two_and_digests_of_existing_folders` | no comparable descriptor at `run_only_if_descriptor_verdict` (only S4 or S5 at it included): `artifact` is `None`; one absent folder with a comparable descriptor at it: `DATA_MISSING`, no exception, `folder_digests` `null` for the absent folder and the `folder_manifest` digest for the others |
| | `test_a_malformed_timestamp_is_failed_run` | `read_events` raises; the runner records `FAILED_RUN` as in 7.4 |
| | `test_local_artifact_records_folder_digests` | the artifact holds `folder_digests` equal to `folder_manifest`'s; `results.json` holds no digest |
| | `test_matches_come_from_the_index_only` | a file on disk the index does not list is not read |
| | `test_sb_module_is_not_imported_by_product_code` | |

## 10. Synthetic gate

`run_gate` runs, for each entry of `requirements` and `reported`, the scenario at each listed
overdispersion value, `seasons_per_gating_scenario` seasons for a scenario of `gating_scenarios`
and `seasons_per_reported_scenario` otherwise, every season with
`synthetic_gate.bootstrap_replicates`, through `evaluate_study` (`SECONDARY_FAMILY_NULL`) or
`evaluate_descriptor` and `evaluate_level` for the primary (every other scenario), with
`sensitivity_rows=None`. Every season is the five-league season of section 5, its leagues named
by `leagues`, and its evaluation reads the configuration of `season_seed_rule` (the config with
`seed` and `bootstrap_replicates` replaced, nothing else); `run_gate` asserts that two-key
difference before the first season. The frame negative control runs inside the gate with the
settings of `synthetic_gate.frame_negative_control`: `synthetic_match_events(seed, teams=teams,
side_effect=side_effect)` through `build_team_match_table` and the primary's `counts`; the
statistic is team 0's side-balance coordinate (the first basis row, Python index 0 of
`log_ratio_basis(3)`, `[s, 0, -s]`, which changes sign when `def_left` and `def_right` are
exchanged; the second row, wide versus centre, does not), `log_ratio_smoothing_per_part` per
part, pooled counts of its valid rows as defender) minus the mean of the other teams' same
coordinate, computed once through the descriptor (`def_left` reads `att_right`) and once with
`att_left` read as `def_left`; the control passes when the first is above zero and the second
below. `passed` is the conjunction of every requirement and the control.

| Scenario | Planted | Requirement (`requirements`) |
|---|---|---|
| `NULL_NOTHING` | no defender shape, no defender level | at overdispersion 0.1 and 0.8: primary `DEFENDER_SHAPE_SIGNAL` at most 5%; `LEVEL_ESTABLISHED` at most 5%; primary token of status NOT_ESTABLISHED at least 90% |
| `NULL_SHAPE_WITH_LEVEL` | defender level only | 0.1 and 0.8: `DEFENDER_SHAPE_SIGNAL` at most 5%; 0.1: `LEVEL_ESTABLISHED` at least 90% |
| `EFFECT_STRONG` | defender shape, SD 0.15 on both coordinates | 0.1: `DEFENDER_SHAPE_SIGNAL` at least 90% |
| `WIDTH_ONLY` | width-only defender shape, SD 0.15 on wide-versus-centre | 0.1 and 0.8: `DEFENDER_SHAPE_SIGNAL` at most 5% (the claim needs side information; (d) passes only by chance, and (e) fails on the side coordinate) |
| `STRENGTH_TERCILE_0_08`, `_0_10`, `_0_12`, `_0_15` | shape = size × latent-strength tercile code × (+1, -1) | 0.1 and 0.8: `DEFENDER_SHAPE_SIGNAL` at most 5% each |
| `STRENGTH_MEASURED_0_15` | shape = 0.15 × standardised finished-season points per match × (+1, -1) | 0.1 and 0.8: `DEFENDER_SHAPE_SIGNAL` at most 5% |
| `SECONDARY_FAMILY_NULL` | nothing, all five secondaries generated | 0.1 and 0.8: any secondary `DEFENDER_SHAPE_SIGNAL` at most 5% (family-wise); Holm's family-wise rejection rate reported |
| `EFFECT_0_09`, `_0_06`, `_0_03` | smaller shapes | detection rate and per-criterion pass rates at 0.1, 0.5 and 0.8; no requirement |
| `EFFECT_STRONG` at 0.5 and 0.8, `NULL_SHAPE_WITH_LEVEL` at 0.5 and 0.8 | as above | reported; no requirement |

Every run reports `design_effect` at its overdispersion (section 8). The gate runs only after
registration (section 13), so a failed gate blocks the real run, and nothing is retuned. The
code may be corrected where it departs from the frozen text, after which the code review of
section 11 is repeated for the changed files and the stamp is regenerated; no constant,
scenario, requirement, threshold or rule may change. A rule the gate shows to be unsound is not
repaired: E-10 is superseded by a new experiment id with its own preregistration.

**What the reviser's simulation shows** (14 October 2026; synthetic only; an independent NumPy
implementation of the generator law, 200 seasons per entry; scratch scripts not committed). It
computes (e) (this split, `reliability_critical_value`) and (g) (`discriminant_validity` with the
frozen thresholds) only, so their joint pass rate bounds `DEFENDER_SHAPE_SIGNAL` from above. The
audit of 16 October 2026 reran the same seasons with (g) reading both tails
(`strength_survival_tails`): every entry of the table is unchanged (REVIEW-RECORD, Audit,
A-1-1), so the gate's `EFFECT_STRONG` requirement is not made harder to meet. The table
describes the generator law, not the frozen random stream of section 5: the draw order fixed
on 16 October 2026 (second audit, 4-1) gives other season realisations than these scripts drew,
and the gate run of the implementers' code is the binding check:

| Scenario | (e) and (g) at overdispersion 0.1 / 0.5 / 0.8 |
|---|---|
| `STRENGTH_TERCILE` at 0.08, 0.10, 0.12, 0.15 | 0 / 0 / 0 at every size |
| `STRENGTH_MEASURED_0_15` | 0 / 0 / 0 |
| `WIDTH_ONLY` | 0 / 0 / 0 ((e) fails on the side coordinate) |
| `EFFECT_STRONG` | 200 / 87 / 0 |
| `EFFECT_0_09` | 132 / 0 / 0 |
| `EFFECT_0_06`, `NULL_NOTHING` | 0 / 0 / 0 |

Under the draft's (g) (adjusted `R2` at most 0.6, no survival check) the latent-tercile plant at
0.10 passed (e) and (g) together in 33 of 200 seasons (with `reliability_critical_value` and an
alternation within home and within away matches), and the reviewer's own simulation found 27 of
100 with the draft's split and critical value.

**The designer's prototype** (independent NumPy code, synthetic only, 50 seasons per scenario,
1,000 bootstrap replicates; `_work/prototype.py`, logs `_work/rates_*.log`, neither committed)
ran the draft's rule, before criterion (g) existed for most rows:

| Scenario | Verdicts in 50 seasons | Criteria passed (of 50) |
|---|---|---|
| `NULL_NOTHING` | 50 `NOT_ESTABLISHED` | (a) 0, (c) 1, (e) 0, (g) 50 |
| `NULL_SHAPE_WITH_LEVEL` | 50 `LEVEL_ONLY` | (a) 0, (c) 1, (e) 0 |
| `EFFECT_STRONG` | 50 `DEFENDER_SHAPE_SIGNAL` | all 50 |
| `WIDTH_ONLY` (width-only defender shape) | 0 signal, 50 `LEVEL_ONLY` | (a) 50, (d) 0, (e) 0 |
| measured-strength shape | 0 signal, 50 `LEVEL_ONLY` | (a) to (f) 50, (g) 0 |
| `EFFECT_0_09` | 31 signal, 19 `LEVEL_ONLY` | (a) 50, (e) 31 |
| `EFFECT_0_06` | 0 signal | (a) 46, (e) 0 |
| `EFFECT_0_03` | 0 signal | (a) 7, (e) 0 |

`LEVEL_ONLY` was the draft's token for a shape verdict with an established level; under the
revised vocabulary those rows read a shape token (`ADDED_INFORMATION_NOT_SHOWN`, `SIDE_NOT_SHOWN`,
`NOT_RELIABLE` or `STRENGTH_NOT_EXCLUDED`) beside `LEVEL_ESTABLISHED`. The rows where (a) passed
and the draft printed "did not find that it adds out-of-sample information" are the reason the
vocabulary names the failing question. Criterion (c) passes about once in 21 null seasons, as
exchangeability predicts. A shape planted as a function of **latent** strength tercile was
called a signal in 50 of 50 seasons before (g) existed: terciles estimated from prior points
misclassify, so a team's own history beats its permuted peers'. These runs are not the gate:
the gate is the implementers' code at 200 seasons.

## 11. Pre-outcome code review (a second agent, after the pipeline commit and before the gate stamp)

| # | Check | How |
|---|---|---|
| 1 | No file under review was executed on `data/` | shell history / agent reports; the only real-data test is the `slow` oracle, after registration, with `columns=()` |
| 2 | Every number comes from `config.json` | `test_no_number_is_hard_coded`; read the three research modules and `estimator.py` (one constant, tied to the config by a test) for stray literals and for defaults |
| 3 | Prior means strictly earlier calendar date everywhere, league prior included | read `walk_forward_*`; poison test present |
| 4 | The state array is updated after all rows of a date are predicted | read the loop |
| 5 | `A^(-u)` is used for the unit's expectation and plain `A` for the target row | read 4.2 against `estimator.py` |
| 6 | The mirror exists in exactly one place | grep for `att_right`, `def_left` |
| 7 | Sentinels and out-of-range coordinates cannot reach a zone test; sentinels are Wyscout's only | read `located` and the callers |
| 8 | Ratio of sums, never mean of ratios, for every loss and share | read aggregations |
| 9 | `context_only` arrays are assigned, not recomputed | read; test present |
| 10 | One `SeasonWorld` per run; no estimand draws its own | read every `cluster_ratio` call |
| 11 | Gates run before any loss and return early; the level runs on its own gates | tests present; read |
| 12 | Both verdict maps are the protocol's tables, order included | truth-table tests; read |
| 13 | `results.json` has no identifier, no per-team row, no banned or provider-named key, no timestamp | test; read the serialiser |
| 14 | The StatsBomb module reads through `sb_reader` only, in batches, one folder at a time, is unreachable from product code, and writes no file; the runner writes its artifact to `replication.local_artifact` only | import scan; read paths |
| 15 | Hashes are LF-normalised; the gate stamp hashes the code under review | read 7.3 against code |
| 16 | The synthetic generator shares no helper with the engine or the estimator (3.8) beyond `log_ratio_basis` | read imports |
| 17 | Docstrings state claim and non-claim; no word from the banned list labels a quantity | read |
| 18 | (g) calls `discriminant_validity` with the config's thresholds on both signs of every coordinate, and `passed` is the AND of the two | read; tests present (house audit, negation invariance) |
| 19 | Every file `real` writes is under `output_root`; the substring scan removes `provenance.config` and nothing else | read the writers and the scan; runner tests present |
| 20 | A synthetic season's evaluation reads the config with `seed` and `bootstrap_replicates` replaced and nothing else; its leagues are `leagues` | read `run_gate` and `synthetic_season`; tests present |
| 21 | One estimator (ROOT 2.9 Z3): the engine computes no quantity of 4.2's state itself and reads them from `galactico/features/team/estimator.py`; no product module imports a research module | read the engine's imports and loop; `test_engine_reads_the_one_estimator` and the firewall test present |

## 12. Registry records, figures, served computation, attribution

### 12.1 Records at registration

`galactico/domain/verdicts.py` receives seven PUBLIC records in the registration commit, token
`PENDING`, built from the config verbatim (as E-11's sixteen were): for each subject of
`subject_groups`, `experiment_id = registry_experiment_id`, `directory =
committed_experiment_dir`, `tier = Tier.PUBLIC`, `vocabulary` and `outcomes` of its kind
(`descriptor` for the six descriptors, `level` for the level subject) from
`verdict_vocabulary` and `registry_outcomes` (`Outcome(VerdictStatus[status], limits,
statement)`), `claim_token` and `scope` from `registry_descriptor` or `registry_level`,
`non_claim` from `registry_non_claims` of its group, `not_run_statement` from `registry_common`,
`protocol_hash` and `config_hash` of the registered files. Each reads `E-10 · RECORD ONLY · NOT
RUN`.

### 12.2 The results commit

Each record receives its token from `results.json["verdicts"]`, `protocol_commit`,
`results_hash`, and, only when its token is in `registry_figures.on_tokens`, the figures of
`registry_figures` for its kind: `Figure(key, value, unit, sentence, pointer)` with the pointer's
`{subject}` filled and the value the one at that pointer, of the same JSON type. No other figure
exists. `tests/test_verdict_registry.py` ties every token, hash and figure to the committed
files.

### 12.3 The served computation (Opponent Lab)

Shown only for a record whose `may_gate` is true, behind an explicit opt-in, at a decision date
`D` on or after `evaluation_start` (`product_rules.panel_from_date`). With the league's valid
rows dated before `D` in window `close_11v11`, through `build_team_match_table`, the
descriptor's `counts` and `estimator.descriptor_rows`, and `kA`, `kD` the record's `k_context`,
`k_unit` figures, every quantity below comes from the estimator of 3.8: `estimator.state_at(rows,
team_ids=the league's teams, parts=spec.part_names, date=D, weights=...)`, then
`shape_estimate(state, league_pseudocount=LEAGUE_PRIOR_PSEUDOCOUNT_PER_PART, k_context=kA,
k_unit=kD)` or, for the level record, `level_estimate(state, k_context_level=kA',
k_unit_level=kD')` on the primary's rows (the level's `N` is the primary's total) with the level
record's figures:

- **Composition**: `served_composition(estimate, team)`, which is `normalise(pi * exp(delta_u))`
  with `pi` and `delta_u` of 4.2 at `D`. **Shrink weight**: its second value,
  `O_total / (O_total + kD)`, `O_total` the team's prior events.
- **Volume** (level record): `served_volume(estimate, team)`, which is `lam * rD_u` per
  `exposure_unit_seconds` of window time, `lam` the league rate over both venues, `rD_u` as 4.2
  with the record's figures. **Shrink weight**: its second value, `E'_u / (E'_u + kD')`.
- **Interval**: `league_world_weights(game ids, served_panel.worlds,
  served_panel.world_seed, scheme=served_panel.world_scheme)` (I12), the game ids being those
  of the league's valid matches dated before `D` (an invalid match adds nothing to the state,
  3.8, and takes no draw): every quantity above is
  recomputed in each world by the same calls, with `weights` the world's match weight of each
  row's match (ones for the point), and the interval is the
  `served_panel.interval_quantiles` pair by `interval_quantile_method`. A world in which the
  team has no prior event is a hole and is counted.
- **Point**: printed only when the `reliability_lower_bound` figure is at least
  `product_rules.point_needs_reliability_lower_bound_at_least`; otherwise the interval alone.
- **S5** is shown as the share under its label, with the share's badge
  (`product_rules.s5_panel_rule`); `s5_ratio_name` names the ratio in prose only, and no panel
  computes, shows or labels the ratio.
- **Proposal qualifier**: the requirement proposal's sentence follows the cited record's
  `may_gate` (`product_rules.proposal_sentence_rule`): none when true;
  `proposal_sentence_not_tested` for a record not registered, `PENDING` or `INCONCLUSIVE`;
  `proposal_sentence_not_established` for a NOT_ESTABLISHED status. A proposal that cites
  several E-10 records carries one qualifier per cited record whose `may_gate` is false, each
  beside that record's label, in the order of `subject_groups`; no qualifier is merged or
  dropped. The panel test covers a proposal citing a `DEFENDER_SHAPE_SIGNAL` record, a
  `PENDING` one and a NOT_ESTABLISHED one.

The Opponent Lab module holds `served_panel`, `product_rules` and `registry_non_claims` as
constants; a test asserts they equal the registered config and that the panel's world draw
receives exactly the ids of the league's valid matches dated before `D` (an invalid match and
a match on `D` planted in the input are not among them). The non-claim of its group is printed
in every state, before registration included, when `verdict_for` returns no record and so no
`non_claim` (`verdicts._unregistered` gives `""`); once a record exists, the test also asserts
that the record's `non_claim` equals the constant. `LEAGUE_PRIOR_PSEUDOCOUNT_PER_PART` is the estimator's
constant (3.7, 3.8), not the panel's. The panel computes none of 4.2 itself: the served `pi`,
`A_c^(-u)`, `e`, `delta_u`, `lam` and `rD_u` are the values of the one estimator the research
engine imports (ROOT 2.9 Z3), so there is no second implementation and no parity test. Product
code imports `galactico.features.team.estimator`, never `galactico.validation` (section 0), and
the estimator's source hash is in `source_hashes` (7.3), so an edit to it after registration is
visible against the registered results. Evidence class EXPERIMENTAL; the panel prints the
record's statement and non-claim.

### 12.4 Attribution

`analysis.md` prints replication numbers only when a replication ran. Then it starts with the
block E-11's PIPELINE section 12 gives, with the image path
`../../../docs/assets/statsbomb/statsbomb-logo.png`, and goes on `FORMED_FROM_STATSBOMB` in
`tests/test_licensing.py` in the commit that adds it. If no replication ran and it mentions
StatsBomb only as a plan, it goes on `NO_FIGURE_FORMED_FROM_STATSBOMB` instead.

## 13. Order of operations and shared-file requests

One order, the one the north-star README gives: audit, registration with `PENDING` records, the
pipeline, the gate stamp in a commit of its own, the run, the results.

**Before registration** (each is a check the root repeats):

| Step | Detail |
|---|---|
| Audit | an independent audit that walks every branch of both verdict rules |
| Pipeline hash | `pipeline_spec_sha256` is `lf_sha256` of this file as it stands; an edit to this file before registration means recomputing it |
| Fingerprints | recomputed from the vectors' payloads |
| Dismissal rule (ROOT 2.9 Z2) | the structure-only counts of `verified_by_root_before_registration`, run by the root on the corpus before registration; counts only, they compute no outcome. The assumption test: per league, the share of players with a `second_yellow` event card whose sheet `red_minute` in that match is not null, its counts and share per league recorded in the registration commit; if it is below `dismissal_assumption_minimum_share` in any league, `dismissal_check_fallback` replaces `dismissal_check` and the draft is audited again before registration. The residuals: per league, players with a dismissal card in the event record and a null sheet `red_minute`, and the reverse, stated in the registration commit; they are the matches `dismissals_mismatch` is built to invalidate, bounded by G1 only, and they never stop registration. The audit counts pinned in `tests/test_sidecar.py` (red and second-yellow tags against sheet red-card entries) are already disclosed in the protocol's prior-exposure table |
| E-11 order | whether E-11 has run and whether its results are committed; if it has run, the registration commit says so (the `reuse_disclosure` string of `results_strings` names that case) and whether its analysis was read, and by whom |
| Replication label (OPEN QUESTION 3) | ROOT 2.5 O1 says a second-provider replication status "sits beside" a hosted panel as a label; this protocol creates no registry record for one and serves none. A root ruling that O1 is read as ADR-0018's permission, which E-10 does not use, or a LOCAL record of its own, is recorded before registration; until it is, the registration commit states the question open |

**The registration commit:**

| File | Change |
|---|---|
| `experiments/preregistered/E-10-conceded-shape/` | the four registered files (section 0); `experiments/preregistered/README.md` row `E-10 conceded shape`, `preregistered, not run` |
| `galactico/domain/verdicts.py` | the seven `PENDING` records of 12.1; the docstring's list of registered experiments |
| `DECISIONS.md` | an ADR recording the registration, as ADR-0029 did for E-11 |
| `tests/test_protocol_drafts.py` | the E-10 twin of its three checks, on the registered directory: `lf_sha256(PIPELINE.md) == pipeline_spec_sha256`; every registry sentence and figure sentence served through `finalize` under `PENDING` and every token, with a planted `line height` refused; no key at any depth of `config.json` or `descriptor_test_vectors.json` names a provider or starts with `SB_`, with a planted negative |
| `tests/test_verdict_registry.py`, `tests/test_lab_runtime.py`, `tests/test_shell_payloads.py`, the planning tests and the e2e specs | every assertion that the registry holds E-11's records only, or that an E-10 subject is unregistered: `test_the_shipped_registry_holds_e11_pending_and_answers_not_registered_otherwise`, `test_verdicts_endpoint_serves_the_registry`, `tests/test_shell_payloads.py::test_verdict_payload_is_the_registry_payload` (it asks for `("E-10", "conceded_f3_entries_per_90")`, the level subject's id, and expects `RECORD ONLY · NOT TESTED` and `NOT_REGISTERED`: it is pointed at a subject no protocol registers, or asserts `E-10 · RECORD ONLY · NOT RUN` and `REGISTERED_NOT_RUN`), and the lists of records in `tests/test_planning_api.py`, `tests/test_planning_render.py`, `tests/test_squad_api.py`, `tests/test_transfer_api.py`, `e2e/squad.spec.js`, `e2e/transfer.spec.js`. `test_payload_is_json_ready_and_carries_no_hash_or_pointer` replaces `VERDICTS` with its own records and needs no change |
| `galactico/api/planning.py` and the pages that list registered protocols | the wording that names the registered protocols (ADR-0029's rule: the wording follows the evidence, not the commit). Nothing is tested at registration: `REGISTERED_NOT_TESTED_STATEMENT` stays, since every E-10 record is `PENDING` |
| `tests/test_preregistration_order.py` | add `"descriptor_test_vectors.json"` to `PROTOCOL`, and in the same edit add it as `"frozen"` to the `E-91-in-order` entry of the first `SCRATCH_HISTORY` commit, as E-11 did for `PIPELINE.md` |
| `tests/test_licensing.py` | add the registered `preregistration.md` and `PIPELINE.md` to `NO_FIGURE_FORMED_FROM_STATSBOMB` (they print no figure formed from StatsBomb data); remove the draft `preregistration.md` and `PIPELINE.md`, which become one-line pointers; `REVIEW-RECORD.md` stays on its list |
| prose that describes E-10 as an unreviewed draft or the sidecar as unread by any draft | `docs/research/north-star/README.md`, `KNOWN_LIMITATIONS.md` (the sidecar entry and "Registered or drafted, not run"), ROOT-DECISIONS 2.6's registry sentence, ADR-0018's registry paragraph |
| draft folder | the four protocol files become one-line pointers to the registered directory |

**After registration, before the run:**

| Step | Detail |
|---|---|
| The pipeline commit | the source and test files of section 0. In that commit, and not before, `tests/test_research_firewall.py` gains `conceded_shape`, `conceded_shape_synthetic` and `conceded_shape_sb` in `RESEARCH_PIPELINES` |
| Code review | section 11 |
| Gate stamp | `gate`; `synthetic_gate.json` in a commit of its own, hashing the registered bytes; `tests/test_preregistration_order.py` does not read it |

**The run:** `real` once, `real --verify` once, every output under `output_root`; read the
coverage block before the verdict block.

**The results commit:** `results.json` (copied unchanged from `output_results`; its sha256
equals the one `real` printed; the licence, size and key checks run on it as if at its committed
path, since `scripts/check_licensing.py` refuses paths under `data/licensed/`), `analysis.md` in
the E-08 form (verdict first, protocol and implementation commits, coverage, ladder, criteria,
what it establishes and does not, product consequence, reproduction, every failed run; no team
named, no ordered list of teams), the registry tokens, hashes and figures (12.2), the
attribution of 12.4 and its list entry, the README row, and `KNOWN_LIMITATIONS.md` entries for
anything the run found and could not repair.

The planning research sentence goes in the same commit. Every E-10 token but `INCONCLUSIVE`
has status ESTABLISHED or NOT_ESTABLISHED, so once one E-10 record reads TESTED,
`planning.verdict_reading()` returns `None` for the sentence (its docstring: the commit that
records that result writes the sentence that replaces it). That commit therefore also edits
`galactico/api/planning.py`: the sentence that replaces `REGISTERED_NOT_TESTED_STATEMENT` (or,
if an earlier results commit already replaced it, the sentence that commit wrote, which this
one follows with its own) is, for E-10, `product_rules.planning_research_sentence`: "E-10
tested whether a defending team's own history adds information about where and how many
final-third entry passes it concedes. That is not validity or decision use, and no quantity on
this page is an E-10 descriptor." It passes the copy guard and `finalize`, and a planning test
asserts that the served sentence contains it verbatim. The tests that assert the old sentence or that every record is
`PENDING` are updated in that commit: `tests/test_planning_api.py`, `tests/test_squad_api.py`,
`tests/test_transfer_api.py`, `tests/test_planning_render.py` and the e2e specs that read the
research statement. If every E-10 token is `INCONCLUSIVE`, no record reads TESTED and the
sentence is unchanged.

## DISSENT

1. **Calendar-week clusters understate the uncertainty of P1.** Loss differences for the same
   defender are positively dependent across weeks, because one noisy `delta_u` is reused all
   season. The house method is kept as instructed, now in one shared world (R12); criteria (b),
   (c), (f) and the synthetic gate bound the false-positive rate of the whole rule (in the
   designer's prototype no signal in 150 synthetic seasons: 100 with no defender shape and 50
   with a width-only defender shape). The published interval should still not be read as
   calibrated. A team-level block bootstrap would be the better interval; it is not adopted
   because it would change the house method inside one experiment.
2. **The research note's secondary family was not kept.** Its xT-weighted target needs a
   prior-date surface and one of three live turnover recipes; its regain height needs a
   possession rule that does not exist. They are replaced by quantities the root decision names
   (shots, defensive-action location, a passes-per-action analogue) that need neither.
3. **The mirror criterion was strengthened.** As written in the research note (point estimate
   smaller than the placebo's) it passes half the time under no side information.
4. **The level is not tested against strength.** ROOT 2.2 asks whether descriptors are more than
   team strength; for conceded volume strength is partly constitutive, so the level's V1 is
   reported as CONTEXT and its sentence says the two are not separated. A volume claim beyond
   strength would need a strength-adjusted baseline this design does not have.

## OPEN QUESTIONS

1. The dismissal rule is frozen on the assumption that the sheet records a second-yellow
   dismissal in `red_minute`. The pinned audit counts support it in three leagues; the
   structure-only share before registration decides it, with `dismissal_check_fallback`
   declared now for the case where it fails. ROOT 2.9 Z2 accepted this check and its fallback;
   the root runs the count and records it in the registration commit (section 13).
2. E-11 may run before E-10 is registered. If its `analysis.md` is committed first, should E-10
   be registered without anyone reading it, or registered with a statement of who read it?
   Either way the frozen `reuse_disclosure` stays true: it names the case where E-11 ran first,
   and the registration commit states which case holds (section 13).
3. Should a replication status ever be shown beside a hosted badge? ADR-0018 permits a LOCAL
   label; it would need its own LOCAL registry record in a directory of its own, with the logo,
   credit and link ADR-0027 requires. This protocol does not create one. ROOT 2.5 O1 says such
   a status "sits beside" a hosted panel as a label, and ROOT 2.9 does not rule this question,
   so it needs a root ruling before registration, or is stated open in the registration commit
   (section 13).
