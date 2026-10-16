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
`galactico/features`. No LOCAL-derived number, interval, coefficient, digest or identifier is
written outside `replication.local_artifact` (ADR-0018).

## 0. Files, owners, order

| WP | Owns (all new unless noted) | Depends on |
|---|---|---|
| A | `galactico/features/team/descriptors.py`, `galactico/features/team/match_table.py`, `galactico/features/team/__init__.py` (exists, empty), `tests/test_team_descriptors.py`, `tests/test_team_match_table.py` | the shipped interfaces of section 1 |
| B | `galactico/validation/conceded_shape.py`, `tests/test_conceded_shape_engine.py`, `tests/test_conceded_shape_rule.py` | row contract (4.1) only |
| C | `galactico/validation/conceded_shape_synthetic.py`, `tests/test_conceded_shape_synthetic.py` | table schema (2.2), row contract (4.1) |
| D | `experiments/run_conceded_shape.py`, `galactico/validation/conceded_shape_sb.py`, `tests/test_conceded_shape_experiment.py`, `tests/test_conceded_shape_sb.py` | A, B, C public names. The LOCAL module is named `_sb` because its path is a key of `source_hashes` in `results.json` (section 7.3) |
| root | `experiments/preregistered/E-10-conceded-shape/{preregistration.md, config.json, PIPELINE.md, descriptor_test_vectors.json}` (registration), `synthetic_gate.json` (own commit), `results.json`, `analysis.md` (results commit); the registry records and the shared files of section 13 | all |

A, B and C can be written in parallel from this document: B and C meet A only through the
table schema of 2.2 and the row contract of 4.1, both frozen here. Research modules
(`galactico/validation/conceded_shape*.py`, `experiments/run_conceded_shape.py`) are never
imported by `galactico/api`, `galactico/models`, `galactico/features`, `galactico/optimization`
or `galactico/profiles`. `galactico/features/team/*` is product-side code and imports nothing
from `galactico.validation` or `experiments`.

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
deep; the runner test of section 9 enforces all three names at every depth on the four files,
with `provenance.config` echoed. None of the source paths of section 7.3 holds any of the three
names.

**Licence-guard traps.** Never write, in any committed file, a double-quoted
`possession_team`, `freeze_frame`, `obv_total_net` or `shot_statsbomb_xg`, nor a double-quoted
`eventId`, `subEventId`, `matchPeriod` or `tagsList` followed by a colon. Every test payload is
generated from a seed with invented ids and coordinates.

**Reused, unchanged** (section 1 gives the calls): `galactico.storage.public.load_public`;
`galactico.ingestion.sidecar` (`load`, `attach`, `verify`, `provenance`,
`SIDECAR_SCHEMA_VERSION`, `TAG_MAPPING_VERSION`); `galactico.validation.digests`;
`galactico.reliability.confound.discriminant_validity`;
`galactico.reliability.core.AxisReliability` (house bound, reported only);
`galactico.domain.verdicts`; `galactico.validation.sb_reader` (LOCAL module only);
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
| I4 | `sidecar.load(league, "matches", columns=["game_id", "home_score", "away_score"])` (`int16` on disk, cast to `int64`) | goals check, points, goal difference | as I2 |
| I5 | `sidecar.load(league, "squads", columns=["game_id", "team_id", "red_minute"])` (`Int16`, null where the sheet has none); `sheet_dismissals` = per `(game_id, team_id)` the count of rows with `red_minute` not null | `dismissals_mismatch` | as I2 |
| I6 | `sidecar.provenance(league)`, `SIDECAR_SCHEMA_VERSION`, `TAG_MAPPING_VERSION` | `results.json` provenance | as I2 |
| I7 | `lf_sha256(path)`, `lf_sha256_text(text)` | every text hash | |
| I8 | `discriminant_validity(y, X, key=..., confound_names=strength_covariates, top_k=strength_top_k, ties=strength_tie_policy, max_variance_explained=strength_variance_explained_ceiling, min_rank_correlation=strength_spearman_floor, min_top_k_survival=strength_top_k_survival_floor)` | criterion (g): `ConfoundVerdict.passed`, never the defaults | |
| I9 | `AxisReliability(key, R, n, 0, season).interval` | the house bound, reported only | |
| I10 | `VerdictRecord`, `Outcome`, `Figure`, `derive`, `badge_text` | registry records (section 12) | constructor rules V1 to V7 |
| I11 | `sb_reader.read_matches(root, folder)`, `read_team_sheets(root, folder, ids, cap=..., regulation_periods=sb_regulation_periods, goalkeeper_position=..., dismissal_card_types_exclude=sb_sheet_card_types_not_dismissal, spell_end_reason_contains=...)`, `read_events(root, folder, ids, scale=sb_location_scale)`, `iter_events(root, folder, ids)`, `folder_vocabulary(root, folder)` | the replication's frames (section 6) | per its docstrings; any exception there is `FAILED_RUN` |
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
                ) -> tuple[pd.DataFrame, pd.DataFrame]: ...
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
dismissed_players` (`int64`, 0 for a team the sheet lists without one). `xt` is `None` or a
surface; it has no default. The neutral `goal` column is not read. Inputs are never mutated.
Output does not depend on input row order. Callers in product code pass the constants of
`descriptors.py` (3.7); research callers pass the config's values.

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
oracle of 2.5 covers it. Counts are 0, not NaN, for a valid match with no qualifying event, and
0 for an invalid match (callers must use `valid`). The table never renames `att_left` to
`def_right`: the mirror lives in the descriptor (3.4), in one place.

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
| `clock_invalid` | a non-finite or negative `seconds` in regulation. The Wyscout adapter writes a missing clock as 0.0, so on that corpus this reason cannot fire and a missing clock places the event at the kick-off; it can fire on the replication's files |
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
`interceptions`, `progression` of `build_match(...)` for the same match: integers exactly,
the xT sum within `1e-9`. `build_match` is an independent code path (per-match, per-row
loops). The synthetic oracle includes a penalty, a direct free-kick shot and an interception
flag on a non-duel row. The real-data oracle (`slow`) requests no descriptor column
(`columns=()`), reads five matches per league, and may run only after the registration commit
(R5): it compares counts Match Lab already serves and computes no descriptor.

## 3. `galactico/features/team/descriptors.py`

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

All use window `close_11v11` (phrase: `first and second half, both teams at eleven, goal
difference at most one`). `TEAM_DESCRIPTORS_SB` holds the first two unchanged and the box pair
rebuilt on `penalty_box_sb` with keys suffixed `_sb` (event set `box_entry_pass_sb`, partition
`start_in_box_sb`). `WINDOWS = {"close_11v11": ..., "all_states": Window("all_states", "first
and second half, every match state", ("1H", "2H"), False, None)}`.

Also exported: `LEVEL_SUBJECTS = {"conceded_f3_entries_per_90": LevelSubject(key, label=
"Final-third entry passes conceded per 90 minutes of window time", descriptor=
"conceded_f3_entries_by_channel", exposure_column="window_seconds", unit_seconds=5400)}`;
`log_ratio_basis(k: int) -> np.ndarray` (rows = coordinates; `k=3`: `[[s, 0, -s], [t, -2t, t]]`
with `s = sqrt(1/2)`, `t = sqrt(1/6)`; `k=2`: `[[s, -s]]`); `required_columns(specs) ->
tuple[Column, ...]`.

### 3.5 Lattice and scale edges (tested)

Bounds are compared as `values <op> float(value)` (`fraction_rule`). On the Wyscout lattice
`j/100.0`: `0.33 -> att_left`, `0.34 -> att_centre`, `0.66 -> att_centre`, `0.67 -> att_right`;
end `x` `0.66` is outside and `0.67` inside the final third; box membership holds at exactly
`x = 0.84`, `y = 0.19`, `y = 0.81`; `0.40` is in `high_zone`; `0.60` is in `own_60`. On the
StatsBomb scale (`sb_location_scale`, values `j/120.0` and `j/80.0`): end `x = 80/120` is in the
final third (an exact rational would say no); start `y = 40/120` is `att_centre`, not
`att_left`; `x = 102/120` and `y = 62/80` are inside `penalty_box_sb`; a location of `(120, 80)`
is a location (no sentinel rule).

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
descriptors` asserts each equals the config. The served panel's constants live in the Opponent
Lab module and are tied the same way (section 12.3).

## 4. `galactico/validation/conceded_shape.py`

Docstring: research pipeline for E-10; frozen walk-forward models, the shared world, the
decision rules; aggregate outputs only; never imported by product code.

### 4.1 Row contract (the only thing B needs from A)

```python
def descriptor_rows(table: pd.DataFrame, spec: TeamDescriptorSpec, *, league: str,
                    exposure_unit_seconds: int) -> pd.DataFrame
```

One row per table row, sorted by `(date, game_id, unit_id)`:

| Column | dtype | Source |
|---|---|---|
| `league` | str | argument |
| `game_id`, `unit_id`, `context_id` | int64 | `game_id`, `team_id`, `opponent_id` |
| `date` | datetime64[ns] | `pd.to_datetime(table.date).dt.normalize()` |
| `context_home` | bool | `~is_home` |
| `valid` | bool | `valid` |
| `exposure` | float64 | `window_seconds / exposure_unit_seconds` |
| `unit_goals`, `context_goals` | int64 | `goals_for`, `goals_against` (the sheet, every match) |
| `unit_passes`, `context_passes` | int64 | `match__completed_passes` of the team and of its opponent |
| `n__<part>` for each part | int64 | `spec.counts(table)` |

### 4.2 Walk-forward state

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
```

Level, with `lam_v = M.sum((0,1))[v] / X.sum((0,1))[v]`, `Xe[c,u,v] = X[c,u,v] lam_v`:

```
rA_c      = (M[c].sum() + kA') / (Xe[c].sum() + kA')
rA_c^(-u) = (M[c].sum() - M[c,u].sum() + kA') / (Xe[c].sum() - Xe[c,u].sum() + kA')
rD_u      = (M[:,u].sum() + kD') / ((Xe[:,u] * rA^(-u)[:,None]).sum() + kD');   1 for context_only
B0 mean = e lam_v;  B1 mean = e lam_v rA_c;  B2 mean = B1 mean * rD_u
deviance(y, mu) = 2 (y ln(y/mu) - (y - mu)),  y ln y = 0 at y = 0;  rows with e == 0 are not scored
```

Rules that must hold in code:

- A row is predicted only if valid and `played_valid[unit] >= m` and `played_valid[context] >=
  m` (`m = minimum_prior_matches`). Invalid rows never update `C` or `X`; they update the sheet
  counters.
- A league date with no prior events (`S.sum() == 0`) predicts nothing.
- For the boundary candidate `context_only` the candidate, mirror, peers and permuted loss
  arrays **are** the B4 array (assigned, not recomputed), so every difference is exactly 0.0;
  likewise the level's B2 array **is** B1's.
- Strength tercile at a date: teams with `played_sheet > 0`, ordered by descending prior points
  per match, then descending prior goal difference per match, then ascending team id;
  `tercile = (strength_tercile_count * position) // count`. Teams with `played_sheet == 0` form
  no tercile and receive no donor.
- Donor map for placebo seed `s`: for each tercile `g`, members sorted by team id,
  `rng = np.random.default_rng(int.from_bytes(sha256(f"{seed}|{s}|{league}|{date:%Y-%m-%d}|{g}"
  .encode()).digest()[:8], "big"))` (`donor_seed_rule`), `donor[members] =
  members[rng.permutation(len(members))]`. A unit's permuted loss uses `delta[donor[unit]]` with
  the unit's own context and venue.
- P2 input: `delta_u` recomputed without the row's context team, i.e. from
  `O_u - C[c,u].sum(0)` and `E_u - sum_v M[c,u,v] e[c,u,v]`.

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

def select_k(loss_by_candidate: np.ndarray, weights: np.ndarray, mask: np.ndarray,
             candidates: Sequence[float | None], *, tolerance: float) -> tuple[int, list[float]]
    # pooled loss_q = loss[q, mask].sum() / weights[mask].sum(); tie set = {q : loss_q <=
    # min loss + tolerance}; None if in the tie set, else the largest k in it; returns the index
    # and every pooled loss. A non-finite pooled loss is returned as is (G6 / LG6 read it)

@dataclass(frozen=True)
class SeasonWorld:
    labels: tuple[str, ...]      # f"{league}|{part}|{week}", sorted within stratum
    strata: tuple[str, ...]      # f"{league}|{part}", in world_strata order
    multiplicity: np.ndarray     # [B, C] int32
    fingerprint: str

def season_world(dates_by_league: Mapping[str, pd.Series], *, evaluation_start: str,
                 week_rule: str, replicates: int, seed: int) -> SeasonWorld
    # clusters: (league, part, W-SUN week of the match date) of every row dated in the season;
    # strata league x part in config league order, development first; rng = default_rng(seed);
    # per stratum of m clusters: idx = rng.integers(0, m, size=(replicates, m)); multiplicity =
    # counts of idx per cluster. fingerprint = sha256(("\n".join(labels)).encode("utf-8") +
    # b"\0" + multiplicity.astype("<i4").tobytes()).hexdigest()

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
    # p = (1 + count(kept >= -zero_tolerance)) / (len(kept) + 1); empty input -> all None

def split_half(rows, parts, *, smoothing, minimum_half_matches, critical_value,
               house_critical_value, band, number) -> dict
def level_split_half(rows, *, smoothing, minimum_half_matches, critical_value,
                     house_critical_value, band, number) -> dict
def persistence(rows, parts, *, evaluation_start, smoothing) -> dict           # T1, no step-up
def strength_validity(rows, parts, sheet, *, covariates, smoothing, top_k, tie_policy,
                      ceiling, spearman_floor, survival_floor, permutations, seed) -> dict
def pair_interaction(rows, parts, world, *, smoothing, minimum_events, quantiles,
                     method) -> dict                                      # reported only
def calibration(forward: ShapeForward, rows, selected: int, world, *, minimum_events,
                quantiles, method, zero_tolerance) -> dict
def holm(p_values: Mapping[str, float | None], order: Sequence[str], *, alpha: float,
         family_size: int) -> dict[str, dict]
def count_pass(rows: pd.DataFrame, settings: ForwardSettings) -> CountPass
    # loss-free walk over the schedule: eligible [R], donor_changed [P, R], prior matches; no model
def sample_gates(rows, counts: CountPass, audit_summary: Mapping, config: dict, *,
                 subject: str) -> dict[str, dict]        # subject "shape" or "level"
def decide_descriptor(*, gates: Mapping[str, bool], criteria: Mapping[str, bool | None]
                      ) -> tuple[str, list[str]]
def decide_level(*, gates: Mapping[str, bool], criteria: Mapping[str, bool | None]
                 ) -> tuple[str, list[str]]
def evaluate_descriptor(rows, spec, config: dict, world: SeasonWorld, *, role: str,
                        frozen: Mapping[str, float | None] | None, sensitivity: bool) -> dict
def evaluate_level(rows, config: dict, world: SeasonWorld, *,
                   frozen: Mapping[str, float | None] | None) -> dict
def evaluate_study(rows_by_descriptor: Mapping[str, pd.DataFrame], config: dict,
                   world: SeasonWorld, *, sensitivity: bool) -> dict
```

Details not already in the protocol:

- `split_half`: per team, the opponents ordered by the date of the first valid meeting, then
  team id; for an opponent at an even position (0-based) half A takes the meeting at which the
  team was at home, for an odd position the away meeting; half B the other; a missing meeting
  is not replaced (`reliability_split`). Team value per half: `basis @ ln((counts + s) /
  (counts.sum() + s K))`. Teams with fewer than `minimum_half_matches` rows in a half are
  dropped and counted. League mean removed per half and coordinate. Returns per coordinate
  `half_r`, `spearman_brown`, `lower_bound` (protocol formula, `critical_value`),
  `house_lower_bound` (`AxisReliability`, `house_critical_value`, reported only), and
  `n_teams`, `teams_dropped`, `minimum_lower_bound`, `implied_per_match_icc`, `render`
  (`"number"` / `"band"` / `"insufficient"` from `minimum_lower_bound` against `number` and
  `band`). Non-finite `r`, `n - 3 - (G - 1) < 1`, or `|r| >= 1` give `lower_bound = None`; then
  `minimum_lower_bound` is `None` and the criterion is not met.
- `strength_validity`: team-season value from the pooled counts of all valid rows, covariates
  from `sheet` (points, goals for and against per match over every match) and from valid rows
  (`sum(unit_passes) / (sum(unit_passes) + sum(context_passes))`). Both league-centred. Per
  coordinate one call of I8; `passed` is `ConfoundVerdict.passed` (never the defaults). Reported
  per coordinate: `r2` (`variance_explained_by_confounds`), `r2_adjusted`, `noise_floor = k /
  (n - G)`, `permutation_p` (covariate rows permuted within league, `permutations` draws,
  `default_rng(seed)`, `(1 + count(R2_perm >= R2)) / (draws + 1)`), `spearman_raw_vs_residual`,
  `top_k_survivors` (`None` when undefined) with `top_k_tied_raw`, `top_k_tied_adjusted`, and
  `failures` (the verdict's words). For the level, the same is computed and gates nothing.
- `pair_interaction` (primary only, reported): rows with `valid` and at least `minimum_events`
  events; per coordinate, least-squares fit on context dummies, unit dummies and `context_home`
  within league; residuals; directed pairs `(context, unit)` with exactly two rows give a pair
  of residuals ordered by date; statistic = Pearson correlation over directed pairs; replicate
  `b` weights a pair by the product of its two meetings' multiplicities in `world` (a pair with
  a zero weight is out of that replicate); returns estimate, interval, `n_directed_pairs`.
  Nothing reads it.
- `calibration`: rows with at least `calibration_minimum_events_per_row`; per coordinate
  `slope = sum(N x y) / sum(N x^2)`; interval by `cluster_ratio(N x y, N x^2, ...)`. `None`
  when `context_only` was selected.
- `holm` (`holm_order_rule`): `m = family_size` always; finite p-values ascending, ties broken by
  `order` (the `secondary_descriptors` list), then every `None` or NaN in `order`; the `i`-th
  (1-based) is rejected while every earlier one was rejected and `p_(i) <= alpha / (m - i + 1)`;
  `None` and NaN are never rejected. Returns per name `p_one_sided`, `order_position`,
  `threshold`, `rejected`.
- `decide_descriptor` (`verdict_precedence.descriptor`): `INCONCLUSIVE` if any gate of
  `shape_gates` is false; else `DEFENDER_SHAPE_SIGNAL` if every criterion in `("a", "b", "c",
  "d", "e", "f", "g")` is `True`; else `FORECAST_NOT_SHOWN` if one of `a, b, c, f` is not `True`;
  else `SIDE_NOT_SHOWN` if `d` is not `True`; else `NOT_RELIABLE` if `e` is not `True`; else
  `STRENGTH_NOT_EXCLUDED`. `None` is not `True`. Reasons: the failed gates, or every criterion
  that is not `True`, in letter order.
- `decide_level` (`verdict_precedence.level`): `INCONCLUSIVE` if any gate of `level_gates` is
  false; else `LEVEL_ESTABLISHED` if `La`, `Lb`, `Le` are all `True`; else `FORECAST_NOT_SHOWN`
  if `La` or `Lb` is not; else `NOT_RELIABLE`.
- `evaluate_descriptor` order of work: `count_pass` and gates G1 to G5 (no loss exists yet)
  -> select `kA` (one forward pass per grid value, development rows only scored) -> one forward
  pass with every `kD` candidate and all placebo seeds -> select `kD` for the real history and,
  separately, for each seed -> G6 (if false, `INCONCLUSIVE`, no evaluation loss is aggregated or
  serialised) -> estimands in `world` -> criteria -> verdict. With `frozen` given (replication)
  no selection happens. A secondary's criterion (a) is filled by `evaluate_study` after `holm`
  over the family. `sensitivity=True` adds the `all_states` P1 and R1 for the primary; the gate
  passes `False`.
- `evaluate_level`: G1 to G4 from the primary's counts (the level's `N` is the primary's
  total), then `kA'` (B1 deviance over the grid), then `kD'` (B2 deviance over the grid and
  `context_only`), LG6, estimands, criteria, verdict. It runs whenever its own gates pass,
  whatever G5 or G6 returned for the primary.
- One `SeasonWorld` per real run (`seed + seed_streams.season_world`, `bootstrap_replicates`)
  and one per synthetic season (the season's seed); every `cluster_ratio`, `calibration` and
  `pair_interaction` of the run reads it. There are no per-estimand or per-descriptor seeds.

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

`synthetic_season`, per league of `T` teams (leagues named `L0..L4`, sizes `team_counts`):

| Quantity | Law (constants in `synthetic_gate`) |
|---|---|
| strength | `s_t ~ N(0, 1)` |
| fixtures | `berger_tables(T)` (`schedule_rule`); round `r` on `first_round_date + days_between_rounds * r`, plus `winter_break_extra_days` for `r >= T - 1`; match `i` of a round one day later when `i` is odd |
| goals | home `~ Poisson(exp(home_intercept + strength_slope (s_h - s_a)))`, away `~ Poisson(exp(away_intercept + strength_slope (s_a - s_h)))` |
| attacker shape | `alpha_t ~ N(0, sd_attacker_shape^2 I_2)` on `(z1, z2)`; plus `home_shape_attacker` when the attacker is at home |
| defender shape | `delta_t = (N(0, sd_side^2), N(0, sd_width^2))`, plus `strength_shape * f * (+1, -1)` by `strength_shape_rules[strength_shape_rule]` (`latent_tercile`: `f` from the latent-strength tercile; `measured_points`: from the finished season's points per match) |
| defender level | `lev_t ~ N(0, sd_level^2)` |
| row composition | `p = ilr^-1(ilr(league_composition) + alpha_att + home term + delta_def + N(0, overdispersion^2 I_2))`, parts ordered `(def_left, def_centre, def_right)` |
| row total | `N ~ Poisson(mean_events_per_row * window_exposure * exp(level_strength_attacker s_att - level_strength_defender s_def + lev_def + home_level [attacker at home] + N(0, sd_match_level^2)))` |
| counts | `Multinomial(N, p)`, written to the `att_right`, `att_centre`, `att_left` columns of `end_lateral_thirds` of `f3_entry_pass` in the defender's `against__` columns |
| secondaries | `secondary_laws`: S1 from the primary's counts; S2 to S5 each with its own `league_composition` and `mean_events_per_row`, the same attacker, home, overdispersion and level laws, and no defender term; S4 and S5 written to the unit's `for__` columns where the descriptor reads them |
| other columns | `window_seconds = exposure_unit_seconds * window_exposure`; `goals_for/against`; `match__completed_passes ~ Poisson(mean_completed_passes * exp(pass_strength_slope * s_t))` |

One `np.random.default_rng(seed)` per season, consumed in the order of the table, leagues in
order, fixtures in schedule order, home row before away row, the primary before the secondaries.
The season's seed (`season_seed_rule`) is also the `seed` of the configuration its evaluation
reads, so its world and its donor maps are its own.

`design_effect(settings, overdispersion)` (`design_effect`): `default_rng(base_seed)` draws
`rows` rows from the generator's row law with no team terms; `w = -ln(q_shifted / q_league)`
per part for `reference_shift`; returns `Var(n . w) / E[N]` at `overdispersion` over the same
at 0. It is reported beside every detection rate. The reviser's implementation gave 1.1, 3.3
and 6.1 at the three grid values.

`synthetic_match_events`: a double round-robin of four teams whose attackers complete entry
passes; the defender of each match receives extra entries on its **left** (attacker's right,
end `y > 2/3`) with odds multiplied by `exp(side_effect)` for team 0 only. Each entry is paired
with a `Ground defending duel` record of the defender at the point-mirrored coordinate
`(1 - x, 1 - y)`. Includes: goals from `shot` rows, a goal flag on a row that is not a shot,
one own goal on a row that also carries the goal flag, one red card, one second yellow, a
`save` row carrying the goal tag (with `goal_on_scoring_event` false), a goal and a pass
sharing one second, one completed pass with a `(1,1)` end, one shot, one penalty and one
direct free-kick shot (for the oracle), one match whose sheet goals disagree with its events,
and one whose sheet lists a dismissal its events do not carry.

## 6. `galactico/validation/conceded_shape_sb.py` (LOCAL tier)

Never imported by product code. Reads only through `sb_reader` (I11), under
`replication.sb_root`, folders `replication.leagues`; matches come from each folder's match index
only (`read_matches`), so a delisted file on disk never becomes a match (KNOWN_LIMITATIONS);
listed matches whose files are absent are counted as invalid. Returns frames that
`build_team_match_table` accepts unchanged.

```python
def load_sb_league(root: Path, folder: str, config: Mapping) -> dict[str, pd.DataFrame]
    # keys: actions (joined shape of I3), matches, match_meta, sheet_dismissals; plus "card_names"
def vocabulary_check(root: Path, folder: str, config: Mapping) -> dict
def orientation_check(root: Path, folder: str, config: Mapping) -> dict
def run_replication(config: dict, frozen: Mapping, *, tables) -> dict
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

`run_replication`: for each descriptor whose token is `run_only_if_descriptor_verdict` and that
is in `comparable_descriptors`, the `_sb` definitions, `kA` and `kD` frozen, every row of the
season (`evaluation_start = season_start` for this arm), its own `SeasonWorld`
(`seed + seed_streams.replication_world`, `replication.bootstrap_replicates`); status by the
protocol's list. It writes `replication.local_artifact` (outside git) with the shape of
`descriptors[key]` restricted to `gates`, `events`, `shape_ladder`, `p1`, `m1` and `status`,
and returns the statuses and reasons only.

## 7. `experiments/run_conceded_shape.py`

### 7.1 Commands

```powershell
# pre-outcome, synthetic only (anyone may run it; root commits the stamp in its own commit)
.venv\Scripts\python.exe -X utf8 experiments\run_conceded_shape.py gate --workers 4
# THE single command of the real execution (root, once)
.venv\Scripts\python.exe -X utf8 experiments\run_conceded_shape.py real
# determinism re-run (root, once): recomputes everything, writes nothing, exits 1 on any byte difference
.venv\Scripts\python.exe -X utf8 experiments\run_conceded_shape.py real --verify
# helper, no data: print fingerprints, source hashes and the pipeline hash
.venv\Scripts\python.exe -X utf8 experiments\run_conceded_shape.py fingerprints
```

`gate` writes `experiments/preregistered/E-10-conceded-shape/synthetic_gate.json`. `real`
writes `.../results.json` and, when a descriptor reaches `DEFENDER_SHAPE_SIGNAL`, runs the
replication and writes `replication.local_artifact`. Files are written by the runner itself:
UTF-8, LF, `json.dumps(obj, indent=1, sort_keys=True, allow_nan=False) + "\n"`. Nothing is
printed to stdout except progress on stderr (a PowerShell redirect would re-encode the
artifact) and, at the end, the sha256 of `results.json`. No timestamp, hostname or path enters
`results.json`.

### 7.2 `real` refuses to start when

| Check | Rule |
|---|---|
| committed protocol | `preregistration.md`, `config.json`, `PIPELINE.md`, `descriptor_test_vectors.json` exist in `HEAD` (`git ls-files --error-unmatch`) and are unchanged since the commit that first added each |
| pipeline hash | `lf_sha256(PIPELINE.md) == pipeline_spec_sha256` |
| clean tree | `git status --porcelain` is empty |
| output absent | `results.json` does not exist (unless `--verify`, which requires it) |
| failed runs on the record | if the failure log exists, the committed `analysis.md` contains the sha256 of its bytes |
| fingerprints | every `TEAM_DESCRIPTORS[key].fingerprint` equals `descriptor_fingerprints[key]`, and every `TEAM_DESCRIPTORS_SB[key].fingerprint` equals `descriptor_fingerprints_sb[key]` |
| synthetic gate | `synthetic_gate.json` exists in `HEAD`, `passed` is true, and its `config_hash`, `protocol_hash`, `pipeline_hash`, `vectors_hash` and `code_hash` equal the current ones |
| licence | `assert_may_host(provider)`; `load_public` refuses any other provider |
| sidecar | for every league, `sidecar.verify` passes and `load` and `attach` do not raise (I2 to I5) |
| leagues | every league has `expected_teams_per_league` teams |

`protocol_commit` is read with `git log --diff-filter=A --format=%H -- <preregistration.md>`;
never a literal. `git` unavailable is a refusal, not a skip.

### 7.3 Hash discipline

| Hash | Over |
|---|---|
| `protocol_hash`, `config_hash`, `pipeline_hash`, `vectors_hash` | `lf_sha256(path)` |
| `source_hashes[posix path]` | `lf_sha256` of: `galactico/validation/conceded_shape.py`, `conceded_shape_synthetic.py`, `conceded_shape_sb.py`, `features/team/{__init__,descriptors,match_table}.py`, this runner, `validation/digests.py`, `validation/sb_reader.py`, `ingestion/sidecar.py`, `storage/public.py`, `reliability/core.py`, `reliability/confound.py` |
| `code_hash` | `lf_sha256_text("\n".join(f"{path} {hash}" for path sorted))` |
| `input_frame_hashes[league][frame]` | `sha256(pd.util.hash_pandas_object(canonical, index=False).values.tobytes())` where `canonical` = the columns the pipeline reads, in the order of section 1, sorted by `event_id` (actions) or `game_id` (matches, sheet frames), index reset; the sidecar's own content hashes are in `provenance.sidecar` |
| `table_hashes[league][window]` | same recipe over the table sorted by `(game_id, team_id)`, columns sorted by name |
| `world.fingerprint` | `SeasonWorld.fingerprint` (4.3) |
| `synthetic_gate_hash` | `lf_sha256(synthetic_gate.json)` |

Parquet file digests are not recorded: they embed the writer's library version and differ
between machines. Content hashes do not.

### 7.4 Structure of `run_real`, and failure

```python
def load_league(league: str, config: dict) -> dict[str, pd.DataFrame]   # I1 to I5, joined
def league_tables(frames, config) -> dict[str, tuple[pd.DataFrame, pd.DataFrame]]   # window -> (table, audit)
def run_real(config: dict) -> dict                            # one league in memory at a time
def run_replication(config: dict, frozen: dict) -> dict       # LOCAL; tokens and reasons returned
def run_gate(config: dict, workers: int) -> dict
def main(argv: Sequence[str] | None = None) -> int
```

Stages (names for the failure log): `refusals`, `load`, `tables`, `world`, `descriptors`,
`level`, `study`, `replication`, `serialise`. Paths are anchored on `Path(__file__)`. No pool in
`real`. `gate` may use a process pool of at most `workers_maximum`; results must not depend on
the worker count (seasons are seeded individually and collected in seed order).

A failed execution (an exception after the refusal checks, in any stage but `replication`)
appends one record to `failed_run_log` (exception type, stage, the file and line of the
innermost frame in the E-10 sources, source hashes; never the message) and exits 3; no
`results.json` is written and nothing from the run may be read. The repair may touch only the
failing stage; the gate stamp is regenerated and recommitted; the next execution starts only
when `analysis.md` (or a commit of its own) records the log's sha256. An exception in
`replication` is caught: the record is appended, every replication status is
`REPLICATION_INCONCLUSIVE` with reason `FAILED_RUN`, `results.json` is written, and the
replication is not attempted again. `real --verify` that finds a byte difference exits 1 and is
a failed execution of stage `serialise`: the results are not committed.

### 7.5 Which code reads which `config.json` key

`test_config_has_every_key_the_pipeline_reads` asserts this table against the code: every key
is read by its consumer, and no consumer reads a number from anywhere else.

| Consumer | Keys |
|---|---|
| `load_league`, coverage | `provider`, `leagues`, `expected_teams_per_league`, `season_start`, `end`, `exposed_leagues`, `unexposed_leagues` |
| table build | `windows`, `window_primary`, `window_sensitivity`, `regulation_periods`, `goal_incident_columns`, `dismissal_cards`, `exposure_unit_seconds`, `wy_location_sentinels`, `coordinate_range` |
| geometry test (product code cannot read an experiment config, so `descriptors.py` holds the values and a test asserts equality) | `fraction_rule`, `final_third_x`, `lateral_left_below_y`, `lateral_right_above_y`, `depth_own_third_below_x`, `depth_opposition_third_from_x`, `penalty_box_wy`, `penalty_box_sb`, `high_zone_x_min`, `own_60_x_max`, `defensive_action_clauses`, `descriptor_schema`, `descriptor_parts`, `descriptor_mirror_pairs`, `descriptor_fingerprints`, `descriptor_fingerprints_sb`, `regulation_periods`, `dismissal_cards`, `goal_incident_columns`, `wy_location_sentinels`, `coordinate_range`, `exposure_unit_seconds` |
| forward passes | `minimum_prior_matches`, `league_prior_pseudocount_per_part`, `log_ratio_smoothing_per_part`, `raw_persistence_matches`, `shrinkage_grid`, `unit_term_boundary_candidate`, `permutation_seeds`, `strength_tercile_count`, `seed` |
| selection | `evaluation_start`, `selection_tie_tolerance` |
| gates | `minimum_valid_match_share_per_league`, `minimum_development_rows_per_league`, `minimum_development_weeks_per_league`, `minimum_evaluation_rows_per_league`, `minimum_evaluation_weeks_per_league`, `minimum_evaluation_events_per_league`, `minimum_reliability_teams`, `minimum_half_matches_per_team`, `minimum_permutation_changed_share`, `shape_gates`, `level_gates` |
| resampling | `bootstrap_replicates`, `interval_quantiles`, `interval_quantile_method`, `seed_streams`, `calendar_week_rule`, `zero_tolerance` |
| criteria | `criterion_alpha_one_sided`, `minimum_leagues_with_negative_estimate`, `level_minimum_leagues_with_negative_estimate`, `holm_family_alpha_one_sided`, `holm_family_size`, `reliability_critical_value`, `reliability_band`, `reliability_number`, `house_reliability_critical_value`, `strength_covariates`, `strength_variance_explained_ceiling`, `strength_spearman_floor`, `strength_top_k`, `strength_top_k_survival_floor`, `strength_tie_policy`, `strength_permutations`, `interaction_minimum_events_per_meeting`, `calibration_minimum_events_per_row` |
| verdicts and registry | `verdict_vocabulary`, `verdict_precedence`, `registry_*`, `lifecycle_status`, `subject_groups` |
| study layout | `primary_descriptor`, `secondary_descriptors`, `level_subject`, `committed_experiment_dir`, `version`, `experiment_id`, `registry_experiment_id`, `tier` |
| runner | `pipeline_spec_sha256`, `failed_run_log`, `results_maximum_bytes`, `forbidden_result_substrings`, `forbidden_result_key_names`, `determinism_reruns` |
| replication | every key of `replication` |
| synthetic gate | every key of `synthetic_gate` |
| served panel test (section 12.3) | `served_panel`, `product_rules` |
| restated rules (strings; the test asserts they are present, code does not branch on them) | `prior_rule`, `state_change_rule`, `goal_incident_rule`, `dismissal_check`, `validity_reasons`, `validity_scope`, `lateral_edge_rule`, `fingerprint_rule`, `shrinkage_grid_unit`, `selection_tie_rule`, `selection_scope`, `level_selection_rule`, `evaluation_events_rule`, `world_cluster`, `world_strata`, `world_draw`, `donor_seed_rule`, `permutation_strata`, `strength_tercile_key`, `strength_tercile_source`, `strength_covariate_sources`, `strength_confound_kind`, `strength_confound_reasoning`, `p_value_rule`, `holm_order_rule`, `reliability_split`, `reliability_centring`, `reliability_interval_method`, `reliability_degrees_of_freedom`, `house_reliability_reported_only`, `interaction_reported_only`, `hash_policy`, `key_naming`, `verified_by_root_before_registration`, `not_run_in_this_experiment`, `season_label` |

## 8. `results.json`

Aggregate only. No player identifier or name, no team-level row, no key that
`banned_key_paths` refuses (`rank`, `score`, `rating`, `index`, `grade`, `total` and the rest of
`BANNED_KEYS`), no key naming a provider at any depth. At most `results_maximum_bytes`. The
first five keys are the registry's contract (`tests/test_verdict_registry.py`).

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
  synthetic_gate_hash, data_license, reuse_disclosure
coverage[league]:
  matches, valid_matches, invalid_by_reason, teams, teams_with_more_than_one_coach_id,
  development {rows, eligible_rows, weeks}, evaluation {rows, eligible_rows, weeks},
  window {events_in_window_share, median_window_seconds}, dropped_location {event_set: n}
gates[subject]: {gate: {passed, detail}}
descriptors[key]:
  role ("primary" | "secondary"), fingerprint, parts, mirror_pairs, gates_passed,
  # everything below is absent when gates_passed is false
  events {development, evaluation, by_league},
  selection {k_context, k_unit, context_losses {k: loss}, unit_losses {k | "context_only": loss}},
  shape_ladder {rung: {pooled, by_league}}            # B0_B2, B1_B4, B3, B5, B6, candidate
  p1 {pooled: ClusterEstimate, by_league {league: ClusterEstimate}, unexposed: ClusterEstimate},
  m1 ClusterEstimate | null,
  identity_stress {placebo_p1 [P], placebo_k_unit [P], donor_changed_share [P],
                   placebos_at_or_below, strictly_below_every_placebo, note},
  calibration {coordinate: {slope, interval}} | null,
  reliability {coordinates {name: {half_r, spearman_brown, lower_bound, house_lower_bound}},
               n_teams, teams_dropped, minimum_lower_bound, implied_per_match_icc, render},
  persistence {coordinate: {r, n_teams}},
  strength_validity {coordinates {name: {r2, r2_adjusted, noise_floor, permutation_p,
                     spearman_raw_vs_residual, top_k_survivors, top_k_tied_raw,
                     top_k_tied_adjusted, failures}}, kind, passed},
  holm {p_one_sided, order_position, threshold, rejected} (secondary only),
  criteria {a, b, c, d, e, f, g}, token, reasons, lifecycle_status,
  # primary only
  interaction {coordinate: {estimate, interval, n_directed_pairs}},
  sensitivity {all_states: {p1, reliability}}
level:
  gates_passed, selection {k_context, k_unit, context_deviances, unit_deviances},
  deviance_ladder, l1 {pooled, by_league}, reliability, strength_validity (kind CONTEXT, reported),
  criteria {La, Lb, Le}, token, reasons, lifecycle_status
replication[key]: {status, reason}                    # tokens only; no number, no digest
interpretation, uncertainty_limit, product_effect     # frozen strings
```

`ClusterEstimate` serialises as `{estimate, interval, p_one_sided, rows, weight, clusters,
holes}`. Coordinate names: three parts `side_balance`, `wide_versus_centre` for the two
conceded-channel descriptors and `first_versus_last`, `ends_versus_middle` otherwise; two parts
`first_versus_second`. A subject whose gates failed has `token` `INCONCLUSIVE` and its failed
gates as reasons. The figures of section 12.2 point into this shape.

`synthetic_gate.json`: `{config_hash, protocol_hash, pipeline_hash, vectors_hash, code_hash,
base_seed, design_effect {value: D}, runs [{scenario, overdispersion, seasons, primary_tokens,
level_tokens, secondary_family_tokens, criterion_pass_counts, selected_k_unit_counts,
median_p1, median_reliability_lower_bound, holm_family_rejections}], requirements [{scenario,
overdispersion, subject, token | status, bound, value, observed, passed}],
frame_negative_control {recovered_sign_with_mirror, recovered_sign_without_mirror, passed},
passed}`.

## 9. Tests (all synthetic or hand-computed; none reads the corpus except the `slow` oracle after registration)

| File | Test | Asserts |
|---|---|---|
| `test_team_descriptors.py` | `test_payloads_match_frozen_vectors` | for `wy` and `sb`: payload, fingerprint, `describe()` and column names equal `descriptor_test_vectors.json`; fingerprints equal `descriptor_fingerprints` and `descriptor_fingerprints_sb` |
| | `test_lattice_and_scale_edges` | every case of 3.5, Wyscout values built as `j / 100.0`, StatsBomb values as `j / 120.0` and `j / 80.0` |
| | `test_remainder_part_and_first_match_wins`, `test_union_counts_each_event_once` | a duel row that also carries the interception flag counts once |
| | `test_changing_a_bound_changes_the_fingerprint`, `test_no_descriptor_reads_duel_success_or_clearance` | |
| | `test_column_names_carry_the_partition_and_never_collide` | two columns with one name and two tokens raise; an anchor outside `needs` raises |
| | `test_window_token_writes_none_only_for_none` | a bound of 0 gives `0`, `None` gives `none` |
| | `test_config_geometry_matches_descriptors` | every value of the geometry row of 7.5 equals the module's constant |
| | `test_log_ratio_basis_is_orthonormal_and_sums_to_zero` | |
| `test_team_match_table.py` | `test_attack_down_attackers_right_lands_on_defenders_left` | synthetic events: entries ending `y = 0.9` are in the defender's `def_left`; the paired defending duels sit at `y = 0.1` in the defender's own frame |
| | `test_without_the_mirror_the_planted_side_has_the_opposite_sign` | negative control (M-01): reading `att_left` as `def_left` flips the recovered sign |
| | `test_sentinels_are_wyscout_only_and_out_of_range_is_dropped` | `(1,1)` Wyscout end is not an entry on the attacker's right; the same point with sentinels `()` is |
| | `test_state_window_goals_own_goals_dismissals`, `test_same_second_incident_does_not_change_that_row`, `test_save_row_goal_tag_is_ignored`, `test_goal_flag_on_a_row_that_is_not_a_shot`, `test_own_goal_takes_precedence` | hand-built timeline |
| | `test_window_seconds_hand_example` | closes at 2-0, reopens at 2-1, closes at a red card |
| | `test_goals_mismatch_and_dismissals_mismatch_invalidate_both_rows_in_every_window` | validity is the same for `close_11v11` and `all_states` |
| | `test_row_order_and_input_immutability` | shuffle rows; frames unchanged |
| | `test_against_columns_are_the_opponents_for_columns` | |
| | `test_oracle_against_build_match_synthetic` | 2.5 on a synthetic match with a penalty, a direct free-kick shot and a flagged non-duel row |
| | `test_oracle_against_build_match_real` (`slow`, after registration) | 2.5 on five matches per league, `columns=()` |
| `test_conceded_shape_engine.py` | `test_hand_computed_two_date_example` | every formula of 4.2 against `fractions.Fraction` arithmetic written in the test |
| | `test_context_only_is_exactly_b4_and_b1`, `test_delta_is_zero_without_history` | |
| | `test_future_and_same_day_rows_cannot_change_a_prediction` | poison rows on or after the date |
| | `test_unit_matches_are_excluded_from_its_expected_composition` | |
| | `test_invalid_rows_never_update_state_but_count_on_the_sheet`, `test_row_order_invariance` | |
| | `test_mirror_swaps_only_the_pair`, `test_poisson_multinomial_factorisation` | |
| | `test_donor_map_is_deterministic_within_strata_and_order_invariant` | |
| | `test_one_world_for_every_estimand_subset_and_window` | per-league and unexposed replicates are restrictions of the pooled ones; both rows of a match share a weight; the fingerprint changes with one multiplicity; a zero-denominator replicate is a hole |
| | `test_cluster_ratio_is_a_ratio_of_sums_with_linear_quantiles_and_the_p_value_rule` | |
| | `test_selection_tie_set`, `test_selection_reads_development_rows_only` | candidates within tolerance of the minimum, not of each other; `context_only` first, then the largest |
| | `test_split_balances_opponents_and_venues` | each half meets every opponent once; home counts differ by at most one; a missing meeting is not replaced |
| | `test_two_part_engine_recovers_a_planted_width_effect` | one seeded season, `sd_width = 0.15`: P1 p-value at most `alpha` for the wide share |
| `test_conceded_shape_rule.py` | `test_verdict_truth_tables` | descriptor: every combination of `{True, False, None}^7` with each gate pattern; level: `{True, False, None}^3` with each level gate pattern; each maps to exactly one token, the protocol's, with its reasons and its `registry_outcomes` statement |
| | `test_any_failed_gate_is_inconclusive_and_computes_no_loss` | loss fields absent; forward pass not called (monkeypatched to raise) |
| | `test_level_runs_when_only_g5_or_g6_fails`, `test_level_inconclusive_on_lg6` | |
| | `test_holm_hand_examples` | `m` fixed at `holm_family_size`; `None` and NaN last and never rejected; a tie ordered by `secondary_descriptors`; the three readings of the review's example give the frozen one |
| | `test_reliability_bound_thresholds` | at `n = 98`, `G = 5`, `c = reliability_critical_value`: `r = 0.4770` gives 0.50009 and `r = 0.4769` 0.49996; `r = 0.6495` gives 0.70001 and `r = 0.6494` less than 0.700; the house bound differs |
| | `test_split_half_known_answer` | 4,000 synthetic units, true plus independent noise: stepped-up value 2/3 within 0.03 |
| | `test_strength_validity_is_the_house_audit_with_frozen_thresholds` | equals `discriminant_validity(...).passed` with the config's thresholds, not the defaults; a shape that is measured strength fails; a tied twelfth place fails by name; NaN fails |
| | `test_pair_interaction_recovers_a_planted_pair_term_and_zero` | |
| | `test_every_registry_sentence_is_served_under_every_token` | the seven records built from the config pass `finalize` under `PENDING` and every token, with figures under the established ones; a planted `line height` in a non-claim is refused |
| `test_conceded_shape_synthetic.py` | `test_berger_tables_shape` | every directed pair once, every unordered pair twice with venues swapped, for 18 and 20 teams; the rule of `schedule_rule` |
| | `test_generator_is_seeded_and_emits_the_table_schema` | with and without the secondaries |
| | `test_design_effect_increases_with_overdispersion` | |
| | `test_small_gate_classifies_planted_effect_and_planted_nothing` | 6 seasons each of `EFFECT_STRONG` and `NULL_NOTHING` at overdispersion 0.1 and 500 replicates: all six `DEFENDER_SHAPE_SIGNAL`; none in the null |
| `test_conceded_shape_experiment.py` | `test_config_has_every_key_the_pipeline_reads`, `test_no_number_is_hard_coded` | AST scan of the three research modules: every numeric literal is in the allowlist `{0, 1, 2, 3, 8}` declared in the test (indices, the deviance factor, Fisher's `n - 3`, the digest slice); every threshold, stride, scale and count is read from `config` |
| | `test_results_shape_is_strict_json_aggregate_and_small` | end to end on two synthetic leagues: `allow_nan=False`, under `results_maximum_bytes`, none of `forbidden_result_substrings`, `banned_key_paths(...) == []`, no key at any depth containing `forbidden_result_key_names` (with `provenance.config` echoed), and the key walker of `tests/test_licensing.py` finds nothing |
| | `test_synthetic_results_pass_the_registry_checks` | a synthetic tree with that `results.json` and the seven records of section 12 passes every checker of `tests/test_verdict_registry.py` |
| | `test_runner_refuses_dirty_tree_missing_gate_hash_and_fingerprint_mismatch` | monkeypatched git; each row of 7.2 |
| | `test_failed_run_writes_no_results_and_no_message`, `test_replication_failure_keeps_the_public_results` | a planted exception whose message holds an invented id is absent from the log |
| | `test_hashes_are_line_ending_invariant`, `test_rerun_is_byte_identical` | |
| | `test_research_modules_are_not_imported_by_product_code` | AST import scan |
| `test_conceded_shape_sb.py` | `test_mapping_on_a_synthetic_event_file` | set-piece passes excluded, kick-off kept; own goal credited to the other team; cards from both details; `(120, 80)` kept; period-relative seconds |
| | `test_vocabulary_and_orientation_failures_are_inconclusive_not_exceptions` | |
| | `test_matches_come_from_the_index_only` | a file on disk the index does not list is not read |
| | `test_sb_module_is_not_imported_by_product_code` | |

## 10. Synthetic gate

`run_gate` runs, for each entry of `requirements` and `reported`, the scenario at each listed
overdispersion value, `seasons_per_gating_scenario` seasons for a scenario of
`gating_scenarios` and `seasons_per_reported_scenario` otherwise, every season with
`synthetic_gate.bootstrap_replicates`, through `evaluate_study` (`SECONDARY_FAMILY_NULL`) or
`evaluate_descriptor` and `evaluate_level` for the primary (every other scenario), with
`sensitivity=False`. Season seeds follow `season_seed_rule`. The frame negative control of
section 9 runs inside the gate. `passed` is the conjunction of every requirement and the
control.

| Scenario | Planted | Requirement (`requirements`) |
|---|---|---|
| `NULL_NOTHING` | no defender shape, no defender level | at overdispersion 0.1 and 0.8: primary `DEFENDER_SHAPE_SIGNAL` at most 5%; `LEVEL_ESTABLISHED` at most 5%; primary token of status NOT_ESTABLISHED at least 90% |
| `NULL_SHAPE_WITH_LEVEL` | defender level only | 0.1 and 0.8: `DEFENDER_SHAPE_SIGNAL` at most 5%; 0.1: `LEVEL_ESTABLISHED` at least 90% |
| `EFFECT_STRONG` | defender shape, SD 0.15 on both coordinates | 0.1: `DEFENDER_SHAPE_SIGNAL` at least 90% |
| `WIDTH_ONLY` | width-only defender shape, SD 0.15 on wide-versus-centre | 0.1 and 0.8: `DEFENDER_SHAPE_SIGNAL` at most 5% (the claim needs side information) |
| `STRENGTH_TERCILE_0_08`, `_0_10`, `_0_12`, `_0_15` | shape = size × latent-strength tercile code × (+1, -1) | 0.1 and 0.8: `DEFENDER_SHAPE_SIGNAL` at most 5% each |
| `STRENGTH_MEASURED_0_15` | shape = 0.15 × standardised finished-season points per match × (+1, -1) | 0.1 and 0.8: `DEFENDER_SHAPE_SIGNAL` at most 5% |
| `SECONDARY_FAMILY_NULL` | nothing, all five secondaries generated | 0.1 and 0.8: any secondary `DEFENDER_SHAPE_SIGNAL` at most 5% (family-wise); Holm's family-wise rejection rate reported |
| `EFFECT_0_09`, `_0_06`, `_0_03` | smaller shapes | detection rate and per-criterion pass rates at 0.1, 0.5 and 0.8; no requirement |
| `EFFECT_STRONG` at 0.5 and 0.8, `NULL_SHAPE_WITH_LEVEL` at 0.5 and 0.8 | as above | reported; no requirement |

Every run reports `design_effect` at its overdispersion. A failed gate is repaired in the code
or reported as a defect of the protocol before registration; after registration a failed gate
blocks the real run and nothing is retuned (a protocol found unsound is superseded by a new
experiment id).

**What the reviser's simulation shows** (14 October 2026; synthetic only; an independent NumPy
implementation of the generator law, 200 seasons per entry; scratch scripts not committed). It
computes (e) (this split, `reliability_critical_value`) and (g) (`discriminant_validity` with the
frozen thresholds) only, so their joint pass rate bounds `DEFENDER_SHAPE_SIGNAL` from above:

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
revised vocabulary those rows read a shape token (`FORECAST_NOT_SHOWN`, `SIDE_NOT_SHOWN`,
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
| 2 | Every number comes from `config.json` | `test_no_number_is_hard_coded`; read the three modules for stray literals and for defaults |
| 3 | Prior means strictly earlier calendar date everywhere, league prior included | read `walk_forward_*`; poison test present |
| 4 | The state array is updated after all rows of a date are predicted | read the loop |
| 5 | `A^(-u)` is used for the unit's expectation and plain `A` for the target row | read 4.2 against code |
| 6 | The mirror exists in exactly one place | grep for `att_right`, `def_left` |
| 7 | Sentinels and out-of-range coordinates cannot reach a zone test; sentinels are Wyscout's only | read `located` and the callers |
| 8 | Ratio of sums, never mean of ratios, for every loss and share | read aggregations |
| 9 | `context_only` arrays are assigned, not recomputed | read; test present |
| 10 | One `SeasonWorld` per run; no estimand draws its own | read every `cluster_ratio` call |
| 11 | Gates run before any loss and return early; the level runs on its own gates | tests present; read |
| 12 | Both verdict maps are the protocol's tables, order included | truth-table tests; read |
| 13 | `results.json` has no identifier, no per-team row, no banned or provider-named key, no timestamp | test; read the serialiser |
| 14 | The StatsBomb module reads through `sb_reader` only, is unreachable from product code, and writes only `replication.local_artifact` | import scan; read paths |
| 15 | Hashes are LF-normalised; the gate stamp hashes the code under review | read 7.3 against code |
| 16 | The synthetic generator shares no helper with the engine beyond `log_ratio_basis` | read imports |
| 17 | Docstrings state claim and non-claim; no word from the banned list labels a quantity | read |
| 18 | (g) calls `discriminant_validity` with the config's thresholds | read; test present |

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
rows dated before `D` in window `close_11v11`, through `build_team_match_table` and the
descriptor's `counts`, and `kA`, `kD` the record's `k_context`, `k_unit` figures:

- **Composition**: `normalise(pi * exp(delta_u))`, with `pi` and `delta_u` exactly as 4.2
  computes them at `D`. **Shrink weight**: `O_total / (O_total + kD)`, `O_total` the team's
  prior events.
- **Volume** (level record): `lam * rD_u` per `exposure_unit_seconds` of window time, `lam` the
  league rate over both venues, `rD_u` as 4.2 with the record's figures. **Shrink weight**:
  `E_u / (E_u + kD')`.
- **Interval**: `league_world_weights(prior league game ids, served_panel.worlds,
  served_panel.world_seed, scheme=served_panel.world_scheme)` (I12): every quantity above is
  recomputed in each world with the world's match weights, and the interval is the
  `served_panel.interval_quantiles` pair by `interval_quantile_method`. A world in which the
  team has no prior event is a hole and is counted.
- **Point**: printed only when the `reliability_lower_bound` figure is at least
  `product_rules.point_needs_reliability_lower_bound_at_least`; otherwise the interval alone.

The Opponent Lab module holds `served_panel` and `product_rules` as constants; a test asserts
they equal the registered config. Evidence class EXPERIMENTAL; the panel prints the record's
statement and non-claim.

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
| Dismissal rule | the structure-only count of `verified_by_root_before_registration`: per league, players with a dismissal card in the event record and a null sheet `red_minute`, and the reverse. Counts only, no outcome. A non-zero count means the rule is revised and the draft re-audited before registration |
| E-11 order | whether E-11's results are committed; if they are, the registration commit says whether its analysis was read |

**The registration commit:**

| File | Change |
|---|---|
| `experiments/preregistered/E-10-conceded-shape/` | the four registered files (section 0); `experiments/preregistered/README.md` row `E-10 conceded shape`, `preregistered, not run` |
| `galactico/domain/verdicts.py` | the seven `PENDING` records of 12.1; the docstring's list of registered experiments |
| `DECISIONS.md` | an ADR recording the registration, as ADR-0029 did for E-11 |
| `tests/test_protocol_drafts.py` | the E-10 twin of its three checks, on the registered directory: `lf_sha256(PIPELINE.md) == pipeline_spec_sha256`; every registry sentence and figure sentence served through `finalize` under `PENDING` and every token, with a planted `line height` refused; no key at any depth of `config.json` or `descriptor_test_vectors.json` names a provider or starts with `SB_`, with a planted negative |
| `tests/test_verdict_registry.py`, `tests/test_lab_runtime.py`, the planning tests and the e2e specs | every assertion that the registry holds E-11's records only: `test_the_shipped_registry_holds_e11_pending_and_answers_not_registered_otherwise`, `test_payload_is_json_ready_and_carries_no_hash_or_pointer` (the exact list `all_payloads()` returns), `test_verdicts_endpoint_serves_the_registry`, and the lists of records in `tests/test_planning_api.py`, `tests/test_planning_render.py`, `tests/test_squad_api.py`, `tests/test_transfer_api.py`, `e2e/squad.spec.js`, `e2e/transfer.spec.js` |
| `galactico/api/planning.py` and the pages that list registered protocols | the wording that names the registered protocols and what has been tested (ADR-0029's rule: the wording follows the evidence, not the commit) |
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

**The run:** `real` once, `real --verify` once; read the coverage block before the verdict
block.

**The results commit:** `results.json` (copied unchanged; its sha256 equals the one `real`
printed), `analysis.md` in the E-08 form (verdict first, protocol and implementation commits,
coverage, ladder, criteria, what it establishes and does not, product consequence,
reproduction, every failed run; no team named, no ordered list of teams), the registry tokens,
hashes and figures (12.2), the attribution of 12.4 and its list entry, the README row, and
`KNOWN_LIMITATIONS.md` entries for anything the run found and could not repair.

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
   dismissal in `red_minute`; the structure-only count before registration decides whether it
   holds.
2. E-11 may run before E-10 is registered. If its `analysis.md` is committed first, should E-10
   be registered without anyone reading it, or registered with a statement of who read it?
3. Should a replication status ever be shown beside a hosted badge? ADR-0018 permits a LOCAL
   label; it would need its own LOCAL registry record in a directory of its own, with the logo,
   credit and link ADR-0027 requires. This protocol does not create one.
