# E-10 pipeline: what to build, exactly

Companion to `preregistration.md` (the protocol) and `config.json` (every number). This file
fixes module paths, signatures, column names, artifact shape, hashes, tests, the synthetic
gate and the commands. It is hashed into `results.json` with the other two. Where this file
and the protocol disagree, the protocol wins and the disagreement is a defect to report.

Claim of the pipeline: it computes the frozen estimands of E-10 from the neutral frames and
the sidecar, deterministically, with no number entering from prose. Non-claim: nothing here
decides football; a green suite says the code matches the protocol on synthetic seasons, not
that the protocol is right about real ones.

## 0. Files, owners, order

| WP | Owns (all new unless noted) | Depends on |
|---|---|---|
| A | `galactico/features/team/descriptors.py`, `galactico/features/team/match_table.py`, `galactico/features/team/__init__.py` (exists, empty), `tests/test_team_descriptors.py`, `tests/test_team_match_table.py` | sidecar column names (section 1) |
| B | `galactico/validation/conceded_shape.py`, `tests/test_conceded_shape_engine.py`, `tests/test_conceded_shape_rule.py` | row contract (4.1) only |
| C | `galactico/validation/conceded_shape_synthetic.py`, `tests/test_conceded_shape_synthetic.py` | table schema (2.2), row contract (4.1) |
| D | `experiments/run_conceded_shape.py`, `galactico/validation/conceded_shape_statsbomb.py`, `tests/test_conceded_shape_experiment.py`, `tests/test_conceded_shape_statsbomb.py` | A, B, C public names |
| root | `experiments/preregistered/E-10-conceded-shape/{preregistration.md, config.json, PIPELINE.md, descriptor_test_vectors.json, synthetic_gate.json, results.json, analysis.md}`, README table row, firewall tuple, `domain/verdicts.py` rows | all |

A, B and C can be written in parallel from this document: B and C meet A only through the
table schema of 2.2 and the row contract of 4.1, both frozen here. Research modules
(`galactico/validation/conceded_shape*.py`, `experiments/run_conceded_shape.py`) are never
imported by `galactico/api`, `galactico/models`, `galactico/features`, `galactico/optimization`
or `galactico/profiles`. `galactico/features/team/*` is product-side code and imports nothing
from `galactico.validation` or `experiments`.

Reused, unchanged: `galactico.validation.digests.lf_sha256`, `lf_sha256_text`;
`galactico.reliability.core.spearman_brown`, `AxisReliability` (house bound, reported only);
`galactico.reliability.confound.discriminant_validity` (unadjusted R2, Spearman, top-k);
`galactico.providers.base.assert_may_host`; `galactico.ingestion.sidecar` loaders;
`galactico.match_lab.model.build_match` and `galactico.models.xt.grid` (oracle test only).
Not reused, and why: `forecast_evaluation.paired_week_interval` weights rows equally and has
no strata, and its file is hash-pinned in E-07/E-08; `partial_history._permutation_maps` is
private and keyed on player strata.

## 1. ASSUMED INTERFACES

| # | Interface assumed | Used for | If it differs |
|---|---|---|---|
| A1 | `galactico.ingestion.sidecar.load_event_sidecar(competition: str) -> pd.DataFrame` with one row per `event_id` of that competition's `actions.parquet` (same id set) and at least: `event_id` int64 unique, `card` object in {`None`, `"yellow_card"`, `"second_yellow"`, `"red_card"`}, `own_goal` bool | dismissals, own goals | only `load_league` in the runner changes. If the sidecar is sparse (rows only for tagged events), `match_state` must be told so explicitly: a missing row then means "no tag" and gate "sidecar rows missing" cannot be evaluated; say so in the audit |
| A2 | `galactico.ingestion.sidecar.load_match_sidecar(competition: str) -> pd.DataFrame` with `game_id` int64 unique, `home_score` int64, `away_score` int64 (full-time, from provider match metadata) | full-time goals check, points | same |
| A3 | `galactico.ingestion.sidecar.SIDECAR_VERSION: str` and a content hash helper, or none | provenance | the runner hashes the frames itself (7.3) |
| A4 | `galactico.validation.digests.lf_sha256(path) -> str`, `lf_sha256_text(text) -> str` (H1) | all text hashes | implement locally with the same rule: `sha256(bytes.replace(b"\r\n", b"\n"))` |
| A5 | `galactico.domain.verdicts` holds rows `{experiment_id, subject, status, product_state, hostable, summary, report}`; `product_state` in {`NOT_RUN`, `PASSED`, `PASSED_WITH_LIMITS`, `FAILED`, `INCONCLUSIVE`} | product gating | `results.json["product_verdicts"]` (section 8) carries everything needed to fill any shape |
| A6 | Opponent Lab computes its prior-date record with `build_team_match_table` and `TEAM_DESCRIPTORS` in window `close_11v11`, reads the selected `k_context`, `k_unit` from the verdict row only for a descriptor with `DEFENDER_SHAPE_SIGNAL`, and draws intervals from shared match worlds (R12) | product consequence table | the table in the protocol still fixes what may be shown |
| A7 | `tests/test_research_firewall.py` has one tuple of research-pipeline module names (H1) | firewall | root appends `conceded_shape`, `conceded_shape_synthetic`, `conceded_shape_statsbomb` |
| A8 | `galactico.reliability.confound._spearman` returns NaN for a constant vector and handles ties (H2) | V1 | V1 treats NaN as failed regardless |
| A9 | E-11 grades `final_third_entries` (+ left/centre/right) with the same bounds: start `x < 2/3`, end `x >= 2/3`, lanes at `1/3` and `2/3`, `y = 0` the attacker's left | cross-provider status of the primary input | E-10 does not wait for E-11; its own replication is a within-provider rerun of the frozen rule |

## 2. `galactico/features/team/match_table.py`

Module docstring must state: claim = counts of declared event sets per team and match, for
and against, in a declared match state, with the defending-frame mirror applied by the
descriptor that reads the column; non-claim = no rate, no share, no opinion about defending.

### 2.1 Signatures

```python
TEAM_MATCH_VERSION = "team-match-table-v1"
REGULATION = {"1H": 1, "2H": 2}

def location_valid(x: pd.Series, y: pd.Series) -> np.ndarray: ...
def match_state(actions: pd.DataFrame, matches: pd.DataFrame, event_sidecar: pd.DataFrame,
                match_meta: pd.DataFrame, *, goal_event_types: tuple[str, ...] = ("shot", "set_piece"),
                dismissal_cards: tuple[str, ...] = ("red_card", "second_yellow"),
                ) -> tuple[pd.DataFrame, pd.DataFrame]: ...
def window_mask(actions: pd.DataFrame, state: pd.DataFrame, window: Window) -> np.ndarray: ...
def window_seconds(incidents: pd.DataFrame, period_ends: pd.DataFrame, window: Window) -> pd.Series: ...
def build_team_match_table(actions: pd.DataFrame, matches: pd.DataFrame, *,
                           columns: Sequence[Column], window: Window,
                           event_sidecar: pd.DataFrame | None = None,
                           match_meta: pd.DataFrame | None = None,
                           xt=None) -> tuple[pd.DataFrame, pd.DataFrame]: ...
```

`actions` needs `game_id, period, seconds, team_id, type, subtype, start_x, start_y, end_x,
end_y, success, goal, interception, key_pass, event_id`; `matches` needs `game_id,
competition, date, home_team_id, away_team_id`. Inputs are never mutated. Output does not
depend on input row order.

### 2.2 Output schema (frozen: WP B, C and Opponent Lab rely on it)

`table`, one row per `(game_id, team_id)`, sorted by `(date, game_id, team_id)`:

| Column | dtype | Meaning |
|---|---|---|
| `game_id`, `team_id`, `opponent_id` | int64 | |
| `competition` | str | from `matches` |
| `date` | str | as in `matches` (callers normalise to the day) |
| `is_home` | bool | |
| `window` | str | `Window.key` |
| `valid` | bool | match validity (2.4); identical for both rows of a match |
| `invalid_reason` | str | `""` when valid; first failing reason otherwise |
| `window_seconds` | float64 | time in the window state; NaN when invalid |
| `goals_for`, `goals_against` | Int64 | from `match_meta`; `<NA>` when not supplied |
| `match__recorded_actions`, `match__completed_passes`, `match__shots`, `match__key_passes`, `match__interception_flags` | int64 | whole match, every state, periods other than `P`; the oracle columns |
| `match__positive_xt_gain` | float64 | only when `xt` is passed; sum of `max(0, xT(end) - xT(start))` over completed passes with **no** location filter, exactly as Match Lab computes it. An oracle aid, never a descriptor input |
| `for__<event_set>` and `for__<event_set>__<part>` | int64 | the team's own events in the window, one column per requested `Column` |
| `against__<event_set>[__<part>]` | int64 | the opponent's `for__` column of the same match, **part names unchanged** (acting team's frame) |

Counts are 0, not NaN, for a valid match with no qualifying event, and 0 for an invalid match
(callers must use `valid`). The table never renames `att_left` to `def_right`: the mirror
lives in the descriptor (3.4), in one place.

`audit`, one row per `game_id`: `valid, invalid_reason, home_goals_events, away_goals_events,
home_goals_meta, away_goals_meta, goal_incidents, dismissal_incidents, first_dismissal_period,
first_dismissal_seconds, period_seconds_1H, period_seconds_2H, events_in_window, events_total`,
and one `dropped_location__<event_set>` per event set (rows that matched the clauses and the
window but had a placeholder, out-of-range or non-finite coordinate).

### 2.3 State and window

- Time key of a row: `REGULATION[period] * 100000 + seconds`. Rows in other periods are in no
  window and enter only `match__` columns (never period `P`).
- Goal incidents: rows with `goal == True` and `type in goal_event_types`, credited to the
  acting team; rows with sidecar `own_goal == True`, credited to the other team of the match.
  `save` rows carry the goal flag too and are ignored.
- Dismissal incidents: rows whose sidecar `card` is in `dismissal_cards`.
- State of a row: counts of incidents with a **strictly smaller** key (`np.searchsorted(...,
  side="left")` on the sorted incident keys of the match). Same-second rows are in the earlier
  state; the result cannot depend on row order.
- `window_mask`: regulation period, and `dismissals_before == 0` if `eleven_v_eleven`, and
  `abs(home_goals_before - away_goals_before) <= max_abs_goal_difference` if set.
- `window_seconds`: per period, breakpoints `0`, the incident seconds of that period, and the
  period's last event second; on each interval `(a, b]` the state is that of incidents with
  key `<= a`; sum `b - a` where the window state holds. A loop over matches is acceptable here
  (a match has few incidents); every per-event computation is vectorised.

### 2.4 Validity (fail closed, never repaired)

A match is invalid with the first applicable reason: `period_missing` (no row in `1H` or in
`2H`), `clock_invalid` (non-finite or negative `seconds` in regulation), `sidecar_missing`
(window needs state and the match has no sidecar or no meta row), `goals_mismatch`
(event-derived full-time goals differ from `match_meta`). With `window.eleven_v_eleven` false
and no goal bound, the sidecar is optional and `sidecar_missing`/`goals_mismatch` cannot occur.
A window that needs state with `event_sidecar is None` raises `ValueError`. Duplicate
`game_id` in `matches`, duplicate `event_id` in the sidecar, or a `team_id` that is neither
side of its match raise `ValueError`.

### 2.5 Oracle

`match__recorded_actions`, `match__completed_passes`, `match__shots`, `match__key_passes`,
`match__interception_flags` and (with `xt`) `match__positive_xt_gain` must equal the
`team_profiles` metrics `recorded_actions`, `completed_passes`, `shots`, `key_passes`,
`interceptions`, `progression` of `build_match(...)` for the same match: integers exactly,
the xT sum within `1e-9`. `build_match` is an independent code path (per-match, per-row
loops). The clearance metric is excluded: its definition is being repaired elsewhere.

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
                  mask(values: np.ndarray) -> np.ndarray    # compares with float(value)

class Zone:       key: str; phrase: str; bounds: tuple[Bound, ...]     # AND
                  token -> f"{key}({'&'.join(b.token for b in bounds)})"

class Clause:     types: tuple[str, ...] = (); subtypes: tuple[str, ...] = ()
                  completed: bool | None = None; flags: tuple[str, ...] = ()
                  token -> f"{','.join(types) or '*'}:{','.join(subtypes) or '*'}:"
                           f"{'completed'|'failed'|'any'}:{','.join(flags) or '-'}"

class EventSet:   key: str; phrase: str; clauses: tuple[Clause, ...]    # OR, row counted once
                  start_in: Zone | None = None; start_not_in: Zone | None = None
                  end_in: Zone | None = None; needs: tuple[str, ...] = ()   # of "start", "end"
                  token -> f"{key}[{'+'.join(c.token)}|start_in={z}|start_not_in={z}|end_in={z}"
                           f"|needs={','.join(needs) or '-'}]"          # z = zone.token or "-"
                  mask(actions) -> np.ndarray          # clauses, zones; NOT location validity
                  located(actions) -> np.ndarray       # location_valid for every name in needs
                  sentence(side) -> str

class Part:       name: str; phrase: str; bounds: tuple[Bound, ...]     # () = remainder, last
class Partition:  key: str; anchor: str ("start"|"end"); parts: tuple[Part, ...]
                  token -> f"{key}@{anchor}[{';'.join(name=bounds-or-'otherwise')}]"
                  assign(actions) -> np.ndarray of part names   # first matching part wins

class Column:     side: str ("for"|"against"); event_set: EventSet
                  partition: Partition | None = None; part: str | None = None
                  name  -> f"{side}__{event_set.key}" + (f"__{part}" if part else "")
                  token -> f"{side}/{event_set.token}" + (f"/{partition.token}:{part}" if part else "")

class Window:     key: str; phrase: str; periods: tuple[str, ...]
                  eleven_v_eleven: bool; max_abs_goal_difference: int | None
                  token -> f"{key}(periods={','.join(periods)};eleven_v_eleven={bool};"
                           f"max_abs_goal_difference={n or 'none'})"

class PartRef:    name: str; columns: tuple[Column, ...]                # summed

class TeamDescriptorSpec:
                  key: str; label: str; parts: tuple[PartRef, ...]; window: Window
                  mirror_pairs: tuple[tuple[str, str], ...] = (); kind: str = "composition"
                  part_names -> tuple[str, ...]
                  columns -> tuple[Column, ...]            # deduplicated, sorted by name
                  counts(table: pd.DataFrame) -> np.ndarray     # [rows, K] int64
                  describe() -> str
                  payload -> str; fingerprint -> str       # sha256(payload utf-8).hexdigest()[:16]
```

`EventSet.sentence(side)`: `f"{phrase} {'by the team' if side == 'for' else 'by the opponent'}"`
then, joined by `" and "` after one space, any of `f"starting in {start_in.phrase}"`,
`f"starting outside {start_not_in.phrase}"`, `f"ending in {end_in.phrase}"`.
`Column` sentence: the event-set sentence, plus `f", {partition.anchor} location {part.phrase}"`
when a part is set. `describe()`:
`f"{label}: " + "; ".join(f"{name with '_' as ' '} = " + " plus ".join(column sentences)) +
f". Each part is a share of the {two|three}-part total. Window: {window.phrase}."`

`payload`: `f"{DESCRIPTOR_SCHEMA}|{key}|{kind}|window={window.token}|parts=" +
";".join(f"{p.name}<-" + "+".join(c.token for c in p.columns)) + f"|mirror=" +
(",".join(f"{a}<>{b}") or "-")`.

### 3.2 Zones, clauses, event sets

| Zone key | Bounds | Phrase |
|---|---|---|
| `final_third` | `x>=2/3` | the final third |
| `penalty_box` | `x>=21/25 & y>=19/100 & y<=81/100` | the penalty-area rectangle |
| `penalty_box_sb` | `x>=17/20 & y>=9/40 & y<=31/40` | the penalty-area rectangle |
| `high_zone` | `x>=2/5` | the zone at least 40% of the pitch length from the acting team's own goal line |
| `own_60` | `x<=3/5` | the passing team's own 60% of the pitch length |

| Event set | Clauses | Zones | `needs` | Phrase |
|---|---|---|---|---|
| `f3_entry_pass` | `pass:*:completed:-` | start not in `final_third`; end in `final_third` | start, end | completed open-play passes |
| `box_entry_pass` (`_sb` with `penalty_box_sb`) | same | start not in box; end in box | start, end | completed open-play passes |
| `open_play_shot` | `shot:*:any:-` | | start | open-play shots |
| `defensive_action` | `duel:Ground defending duel:any:-` + `*:*:any:interception` + `foul:Foul:any:-` | | start | recorded defensive actions (ground defending duel records, interception-tagged events, fouls committed; each event once) |
| `defensive_action_high` | same three | start in `high_zone` | start | same phrase |
| `own_60_pass` | `pass:*:any:-` | start in `own_60` | start | open-play pass attempts |

`completed` reads `success == True`; it is never read on duels (the neutral duel `success` means
"not lost"). The `clearance` column is never read (always false in this corpus).

### 3.3 Partitions

| Key | Anchor | Parts in order (name: bounds: phrase) |
|---|---|---|
| `end_lateral_thirds` | end | `att_left`: `y<1/3`: in the acting team's left lateral third · `att_right`: `y>2/3`: in the acting team's right lateral third · `att_centre`: remainder: in the central lateral third |
| `start_lateral_thirds` | start | same three |
| `start_in_box` (`_sb`) | start | `inside`: the box bounds: inside the penalty-area rectangle · `outside`: remainder: outside the penalty-area rectangle |
| `start_depth_thirds` | start | `own_third`: `x<1/3`: in the acting team's own third · `opposition_third`: `x>=2/3`: in the opposition third · `middle_third`: remainder: in the middle third |

### 3.4 Descriptors (`TEAM_DESCRIPTORS`, in this order)

| Key | Label | Parts: name <- columns | Mirror pairs |
|---|---|---|---|
| `conceded_f3_entries_by_channel` | Conceded final-third entry passes, share by channel (defending team's frame) | `def_left` <- against `f3_entry_pass` `att_right`; `def_centre` <- `att_centre`; `def_right` <- `att_left` | `def_left<>def_right` |
| `conceded_f3_entries_wide_share` | Conceded final-third entry passes, wide share | `wide` <- against `att_left` + `att_right`; `centre` <- `att_centre` | |
| `conceded_box_entries_by_origin_channel` | Conceded penalty-area entry passes, share by origin channel (defending team's frame) | `def_left` <- against `box_entry_pass` (start) `att_right`; `def_centre` <- `att_centre`; `def_right` <- `att_left` | `def_left<>def_right` |
| `conceded_shots_inside_box_share` | Conceded open-play shots, share from inside the penalty-area rectangle | `inside_box` <- against `open_play_shot` `inside`; `outside_box` <- `outside` | |
| `defensive_actions_by_pitch_third` | Recorded defensive actions, share by pitch third (team's own frame) | `own_third`, `middle_third`, `opposition_third` <- for `defensive_action` same-named part | |
| `high_zone_defensive_action_share` | High-zone defensive actions as a share of those actions plus opponent pass attempts started in the opponent's own 60% | `high_zone_defensive_actions` <- for `defensive_action_high`; `opponent_own_60_passes` <- against `own_60_pass` | |

All use window `close_11v11` (phrase: `first and second half, both teams at eleven, goal
difference at most one`). `TEAM_DESCRIPTORS_STATSBOMB` holds the first two unchanged and the
box pair rebuilt on `penalty_box_sb` with keys suffixed `_sb` (event set `box_entry_pass_sb`,
partition `start_in_box_sb`). `WINDOWS = {"close_11v11": ..., "all_states": Window("all_states",
"first and second half, every match state", ("1H", "2H"), False, None)}`.

Also exported: `LEVEL_SUBJECTS = {"conceded_f3_entries_per_90": LevelSubject(key, label=
"Conceded final-third entry passes per 90 minutes of window time", descriptor=
"conceded_f3_entries_by_channel", exposure_column="window_seconds", unit_seconds=5400)}`;
`log_ratio_basis(k: int) -> np.ndarray` (rows = coordinates; `k=3`:
`[[s, 0, -s], [t, -2t, t]]` with `s = sqrt(1/2)`, `t = sqrt(1/6)`; `k=2`: `[[s, -s]]`);
`required_columns(specs) -> tuple[Column, ...]`.

### 3.5 Lattice edges (tested)

Bounds are compared as `values <op> float(value)`. On the Wyscout lattice `j/100.0`:
`0.33 -> att_left`, `0.34 -> att_centre`, `0.66 -> att_centre`, `0.67 -> att_right`;
end `x` `0.66` is outside and `0.67` inside the final third; box membership holds at exactly
`x = 0.84`, `y = 0.19`, `y = 0.81`; `0.40` is in `high_zone`; `0.60` is in `own_60`.

### 3.6 Frozen payloads and fingerprints

`descriptor_test_vectors.json` (beside this file) holds, for every descriptor of both
dictionaries, the exact `payload`, `fingerprint` and `describe()` string, generated by an
independent designer-side script from the tables above. `tests/test_team_descriptors.py`
loads it and asserts byte equality. The fingerprints are also in
`config.descriptor_fingerprints[_statsbomb]`. An implementation whose payload differs is not
the preregistered definition: fix the implementation, never the vector.

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

## 4. `galactico/validation/conceded_shape.py`

Docstring: research pipeline for E-10; frozen walk-forward models, resampling and decision
rule; aggregate outputs only; never imported by product code.

### 4.1 Row contract (the only thing B needs from A)

```python
def descriptor_rows(table: pd.DataFrame, spec: TeamDescriptorSpec, *, league: str) -> pd.DataFrame
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
| `unit_goals`, `context_goals` | Int64 | `goals_for`, `goals_against` |
| `unit_passes`, `context_passes` | int64 | `match__completed_passes` of the team and of its opponent |
| `n__<part>` for each part | int64 | `spec.counts(table)` |

### 4.2 Walk-forward state

Per league, teams indexed `0..T-1` by sorted id. One cumulative array of strictly prior valid
rows, updated only after every row of a date has been predicted:

- `C[c, u, v, k]`: events of part `k` in rows with context `c`, unit `u`, `v = context_home`.
- `X[c, u, v]`: exposure, same indexing. `played[team]`, `points[team]`, `goal_diff[team]`
  from valid rows (3/1/0 from `unit_goals` versus `context_goals`, counted once per match).

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

Level (primary only), with `lam_v = M.sum((0,1))[v] / X.sum((0,1))[v]`, `Xe[c,u,v] = X[c,u,v] lam_v`:

```
rA_c      = (M[c].sum() + kA') / (Xe[c].sum() + kA')
rA_c^(-u) = (M[c].sum() - M[c,u].sum() + kA') / (Xe[c].sum() - Xe[c,u].sum() + kA')
rD_u      = (M[:,u].sum() + kD') / ((Xe[:,u] * rA^(-u)[:,None]).sum() + kD')
B0 mean = e lam_v;  B1 mean = e lam_v rA_c;  B2 mean = B1 mean * rD_u
deviance(y, mu) = 2 (y ln(y/mu) - (y - mu)),  y ln y = 0 at y = 0;  rows with e == 0 are not scored
```

Rules that must hold in code:

- A row is predicted only if valid and `played[unit] >= m` and `played[context] >= m`
  (`m = minimum_prior_matches`). Invalid rows never update the state.
- A league date with no prior events (`S.sum() == 0`) predicts nothing.
- For the boundary candidate `context_only` the candidate, mirror, peers and permuted loss
  arrays **are** the B4 array (assigned, not recomputed), so every difference is exactly 0.0.
- Strength tercile at a date: order teams with `played > 0` by descending prior points per
  match, then descending prior goal difference per match, then ascending team id;
  `tercile = (3 * position) // count`. Teams with `played == 0` form no tercile and receive
  no donor.
- Donor map for placebo seed `s`: for each tercile `g`, members sorted by team id,
  `rng = np.random.default_rng(int.from_bytes(sha256(f"{seed}|{s}|{league}|{date:%Y-%m-%d}|{g}"
  .encode()).digest()[:8], "big"))`, `donor[members] = members[rng.permutation(len(members))]`.
  A unit's permuted loss uses `delta[donor[unit]]` with the unit's own context and venue.
- P2 input: `delta_u` recomputed without the row's context team, i.e. from
  `O_u - C[c,u].sum(0)` and `E_u - sum_v M[c,u,v] e[c,u,v]`.

### 4.3 Functions

```python
@dataclass(frozen=True)
class ForwardSettings:
    parts: tuple[str, ...]; mirror_pairs: tuple[tuple[str, str], ...]
    k_context: float; k_unit_candidates: tuple[float | None, ...]      # None = context_only
    minimum_prior_matches: int; league_pseudocount: float
    raw_matches: int; smoothing: float
    permutation_seeds: tuple[int, ...]; seed: int; tercile_count: int = 3

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
def walk_forward_level(rows, *, parts, k_context, k_unit_candidates, minimum_prior_matches,
                       raw_matches, smoothing, permutation_seeds, seed) -> LevelForward
    # LevelForward: eligible, scored (e > 0), deviance_league_venue, deviance_context,
    # deviance_raw_five [R]; deviance_unit, deviance_peers [Q, R]; deviance_permuted [P, Q, R]

def select_k(loss_by_candidate: np.ndarray, weights: np.ndarray, mask: np.ndarray,
             candidates: Sequence[float | None], *, tolerance: float) -> tuple[int, list[float]]
    # pooled loss = loss[mask].sum() / weights[mask].sum(); returns the chosen index and every pooled loss
    # tie order: None first, then descending k

@dataclass(frozen=True)
class ClusterEstimate:
    estimate: float | None; interval: tuple[float, float] | None; p_one_sided: float | None
    rows: int; weight: float; clusters: int

def cluster_ratio(numerator, denominator, clusters, strata, *, replicates: int, seed: int,
                  quantiles: tuple[float, float]) -> ClusterEstimate
    # strata in sorted order; clusters sorted within stratum; rng = default_rng(seed);
    # per stratum: idx = rng.integers(0, m, size=(replicates, m)); statistic = sum(num)/sum(den)
    # p_one_sided = (1 + count(replicates >= 0)) / (replicates + 1); empty input -> all None

def week_clusters(rows: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]
    # clusters = league + "|" + date.dt.to_period("W-SUN").astype(str); strata = league

def split_half(rows, parts, *, smoothing, minimum_half_matches, critical_value) -> dict
def level_split_half(rows, parts, *, smoothing, minimum_half_matches, critical_value) -> dict
def persistence(rows, parts, *, evaluation_start, smoothing) -> dict           # T1, no step-up
def strength_validity(rows, parts, *, covariates, smoothing, ceiling, rho_floor, top_k,
                      permutations, seed) -> dict
def pair_interaction(rows, parts, *, smoothing, minimum_events, replicates, seed,
                     lower_quantile) -> dict
def calibration(forward: ShapeForward, rows, selected: int, *, minimum_events, replicates,
                seed, quantiles) -> dict
def holm(p_values: Mapping[str, float | None], alpha: float) -> dict[str, bool]   # None never rejects
def count_pass(rows: pd.DataFrame, settings: ForwardSettings) -> CountPass
    # loss-free walk over the schedule: eligible [R], donor_changed [P, R], prior matches; no model
def sample_gates(rows: pd.DataFrame, counts: CountPass, audit_summary: Mapping, config: dict) -> dict[str, dict]
def decide(*, gates_passed: bool, criteria: Mapping[str, bool | None],
           level: Mapping[str, bool | None] | None) -> str
def evaluate_descriptor(rows: pd.DataFrame, spec, config: dict, *, role: str,
                        frozen: Mapping[str, float | None] | None = None,
                        evaluation_start: str | None = None) -> dict
def evaluate_study(rows_by_descriptor: Mapping[str, pd.DataFrame], config: dict) -> dict
```

Details not already in the protocol:

- `split_half`: per team, valid rows ordered by `(date, game_id)`; even positions (0-based) are
  half A, odd half B. Team value per half: `basis @ ln((counts + s) / (counts.sum() + s K))`.
  Teams with fewer than `minimum_half_matches` rows in a half are dropped and counted. League
  mean removed per half and coordinate. Returns per coordinate `half_r`, `spearman_brown`,
  `lower_bound` (protocol formula), `house_lower_bound_90` (from `AxisReliability(key, R, n, 0,
  season).interval`, reported only), `n_teams`, `implied_per_match_icc`, and `render`
  (`"number"` / `"band"` / `"insufficient"` from the minimum lower bound over coordinates).
  Non-finite `r`, `n - 3 - (G - 1) < 1`, or `|r| >= 1` give `lower_bound = None` and fail.
- `strength_validity`: team-season value from pooled counts of all valid rows; covariates per
  team from the same rows: points per match, goals for and against per match,
  `sum(unit_passes) / (sum(unit_passes) + sum(context_passes))`. All league-centred. OLS by
  `np.linalg.lstsq`; `R2`, `R2_adj` (protocol formula), `noise_floor = k / (n - G)`,
  `permutation_p` (covariate rows permuted within league, `strength_permutations` draws,
  `(1 + count(R2_perm >= R2)) / (draws + 1)`), `spearman_raw_vs_residual`, `top_k_overlap`
  with `top_k_chance = top_k ** 2 / n`. `passed` per protocol; any NaN fails.
- `pair_interaction` (primary only): rows with `valid` and at least `minimum_events` events;
  per coordinate, least-squares fit on context dummies, unit dummies and `context_home` within
  league; residuals; directed pairs `(context, unit)` with exactly two rows give a pair of
  residuals ordered by date; statistic = Pearson correlation over directed pairs; bootstrap over
  **unordered** pairs within league; returns estimate, lower bound at `lower_quantile`,
  `n_directed_pairs`, `n_unordered_pairs`, and `matchup_features_permitted`.
- `calibration`: rows with at least `calibration_minimum_events_per_row`; per coordinate
  `slope = sum(N x y) / sum(N x^2)`; interval by `cluster_ratio(N x y, N x^2, ...)`. `None` when
  `context_only` was selected.
- `decide`: `"INCONCLUSIVE"` if not `gates_passed`; else `"DEFENDER_SHAPE_SIGNAL"` if every
  criterion in `("a","b","c","d","e","f","g")` is `True`; else `"LEVEL_ONLY"` if `level` is not
  `None` and `level["La"] and level["Lb"] and level["Le"]`; else `"NOT_ESTABLISHED"`. A `None`
  criterion counts as not met. When gates fail, `evaluate_descriptor` returns before any loss
  is computed and the loss fields are absent.
- `evaluate_descriptor` order of work: `count_pass` and gates G1 to G5 (no loss exists yet)
  -> select `kA` (one forward pass per grid value, development rows only scored) -> one forward
  pass with every `kD` candidate and all placebo seeds -> select `kD` for the real history and,
  separately, for each seed -> gate G6 (every development selection loss finite; if not,
  `INCONCLUSIVE` and no evaluation loss is aggregated or serialised) -> estimands -> criteria
  -> verdict. With `frozen` given (replication) no selection happens.
  The secondary criterion (a) is filled by `evaluate_study` after `holm` over the family.
- Seeds: `config.seed + seed_stride_per_descriptor * i + seed_offsets[name]`, `i` the
  descriptor's position in `[primary] + secondary_descriptors`. Per-league estimates add the
  league's position in `config.leagues` to the `per_league` offset.

## 5. `galactico/validation/conceded_shape_synthetic.py`

Written from football and the schedule, not from the engine's equations: effects live on
log-ratio coordinates and on a log rate; the engine shrinks counts. Two generators.

```python
def double_round_robin(n_teams: int) -> list[list[tuple[int, int]]]
    # circle method; 2 (n - 1) rounds; second half = first half with venues swapped
def synthetic_season(seed: int, scenario: Mapping[str, float], settings: Mapping) -> dict[str, pd.DataFrame]
    # league name -> a frame in the TABLE SCHEMA of 2.2 (primary columns only), valid = True
def synthetic_match_events(seed: int, *, teams: int = 4, side_effect: float = 1.0) -> dict[str, pd.DataFrame]
    # keys: actions, matches, event_sidecar, match_meta - neutral schema, tiny, for table tests
def run_gate(config: dict, *, workers: int = 1) -> dict
```

`synthetic_season`, per league of `T` teams (leagues named `L0..L4`, sizes `team_counts`):

| Quantity | Law (constants in `config.synthetic_gate`) |
|---|---|
| strength | `s_t ~ N(0, 1)` |
| fixtures | `double_round_robin(T)`; round `r` on `first_round_date + days_between_rounds * r`, plus `winter_break_extra_days` for `r >= T - 1`; match `i` of a round one day later when `i` is odd |
| goals | home `~ Poisson(exp(home_intercept + slope (s_h - s_a)))`, away `~ Poisson(exp(away_intercept + slope (s_a - s_h)))` |
| attacker shape | `alpha_t ~ N(0, sd_attacker_shape^2 I_2)` on `(z1, z2)` |
| defender shape | `delta_t = (N(0, sd_side^2), N(0, sd_width^2))`, plus `strength_shape * z(points per match of the finished season, within league) * (+1, -1)` |
| defender level | `lev_t ~ N(0, sd_level^2)` |
| row composition | `p = ilr^-1(ilr(league_composition) + alpha_att + delta_def + N(0, sd_match_shape^2 I_2))`, parts ordered `(def_left, def_centre, def_right)` |
| row total | `N ~ Poisson(mean_events_per_row * window_exposure * exp(level_strength_attacker s_att - level_strength_defender s_def + lev_def + home_level [attacker at home] + N(0, sd_match_level^2)))` |
| counts | `Multinomial(N, p)`, written to `against__f3_entry_pass__att_right`, `__att_centre`, `__att_left` of the defender's row |
| other columns | `window_seconds = 5400 * window_exposure`; `goals_for/against`; `match__completed_passes ~ Poisson(mean_completed_passes * exp(pass_strength_slope * s_t))` |

One `np.random.default_rng(seed)` per season, consumed in the order of the table, leagues in
order, fixtures in schedule order, home row before away row.

`synthetic_match_events`: a double round-robin of four teams whose attackers complete entry
passes; the defender of each match receives extra entries on its **left** (attacker's right,
end `y > 2/3`) with odds multiplied by `exp(side_effect)` for team 0 only. Each entry is paired
with a `Ground defending duel` record of the defender at the point-mirrored coordinate
`(1 - x, 1 - y)`. Includes: goals from `shot` rows, one own goal, one red card, one
second yellow, a `save` row carrying the goal flag, a goal and a pass sharing one second, one
completed pass with a `(1,1)` end, one shot (placeholder end by construction), one match
whose meta goals disagree with its events.

## 6. `galactico/validation/conceded_shape_statsbomb.py` (LOCAL tier)

Never imported by `galactico/api`. Reads `data/licensed/statsbomb/<league>/` one match at a
time. Returns frames that `build_team_match_table` accepts unchanged.

```python
def load_statsbomb_league(root: Path, competition: str) -> dict[str, pd.DataFrame]
    # keys: actions, matches, event_sidecar, match_meta
def orientation_check(root: Path, competition: str, *, minimum_matches: int) -> dict
```

Frozen mapping (keys read with single-quoted strings; no schema key in double quotes):

| Neutral field | StatsBomb source |
|---|---|
| `game_id`, `team_id` | `match_id`; `team.id` |
| `period` | `1 -> "1H"`, `2 -> "2H"`; other periods kept as their number string and never in a window |
| `seconds` | period-relative seconds parsed from `timestamp` (`HH:MM:SS.mmm`) |
| `type`, `subtype` | `Pass` with `pass.type.name` absent or not in `set_piece_pass_types` -> `pass` / `"Pass"`; `Pass` otherwise -> `set_piece` / the type name; `Shot` with `shot.type.name == open_play_shot_type` -> `shot`; other `Shot` -> `set_piece` / `"shot"`; every other event -> `other` / the event type name |
| `success` | `pass`: `True` when `pass.outcome` is absent, else `False`; others `None` |
| `start_x, start_y` | `location / (120, 80)`; NaN when absent |
| `end_x, end_y` | `pass.end_location / (120, 80)`; for other events the start |
| `goal` | `Shot` with `shot.outcome.name == "Goal"` |
| `interception`, `key_pass` | `False` (S4 and S5 are `NOT_COMPARABLE`; oracle columns are not used) |
| `event_id` | the event `id` string |
| sidecar `own_goal` | event type name `== own_goal_event_type` (the conceding team's record; credited to the other team, as in Wyscout) |
| sidecar `card` | `foul_committed.card.name` or `bad_behaviour.card.name`: `"Red Card" -> "red_card"`, `"Second Yellow" -> "second_yellow"`, `"Yellow Card" -> "yellow_card"` |
| `matches.date`, home and away ids | `match_date`, `home_team.home_team_id`, `away_team.away_team_id` |
| `match_meta` goals | `home_score`, `away_score` |

`orientation_check` (structure, run before any replication loss): over at least
`orientation_check_minimum_matches` matches, the mean `start_y` of `pass` rows by players whose
first listed position is `Left Back` is below 0.5 and that of `Right Back` above 0.5;
otherwise raise. Known differences, stated in the report: StatsBomb passes include headers and
recoveries as open play; StatsBomb coordinates are continuous, so no row sits on a lattice
edge; the box rectangle is each provider's own.

## 7. `experiments/run_conceded_shape.py`

### 7.1 Commands

```powershell
# pre-outcome, synthetic only (anyone may run it; root commits the report with the code)
.venv\Scripts\python.exe -X utf8 experiments\run_conceded_shape.py gate --workers 4
# THE single command of the real execution (root, once)
.venv\Scripts\python.exe -X utf8 experiments\run_conceded_shape.py real
# determinism re-run (root, once): recomputes everything, writes nothing, exits 1 on any byte difference
.venv\Scripts\python.exe -X utf8 experiments\run_conceded_shape.py real --verify
# helper, no data: print fingerprints and source hashes
.venv\Scripts\python.exe -X utf8 experiments\run_conceded_shape.py fingerprints
```

`gate` writes `experiments/preregistered/E-10-conceded-shape/synthetic_gate.json`. `real`
writes `.../results.json` and, when a descriptor reaches `DEFENDER_SHAPE_SIGNAL` and the
licensed cache is present, runs the replication and writes `config.replication.local_artifact`
(outside git). Files are written by the runner itself: UTF-8, LF, `json.dumps(obj, indent=1,
sort_keys=True, allow_nan=False) + "\n"`. Nothing is printed to stdout except progress on
stderr (a PowerShell redirect would re-encode the artifact). No timestamp, hostname or path
enters `results.json`.

### 7.2 `real` refuses to start when

| Check | Rule |
|---|---|
| committed protocol | `preregistration.md`, `config.json`, `PIPELINE.md`, `descriptor_test_vectors.json` exist in `HEAD` (`git ls-files --error-unmatch`) |
| clean tree | `git status --porcelain` is empty |
| output absent | `results.json` does not exist (unless `--verify`, which requires it) |
| fingerprints | every `TEAM_DESCRIPTORS[key].fingerprint` equals `config.descriptor_fingerprints[key]` |
| synthetic gate | `synthetic_gate.json` exists in `HEAD`, `passed` is true, and its `config_hash`, `protocol_hash`, `pipeline_hash` and `code_hash` equal the current ones |
| licence | `assert_may_host(config.provider)`; `actions.provider` values are exactly `{"pappalardo"}` |
| leagues | every league has `expected_teams_per_league` teams and both sidecar frames |

`protocol_commit` is read with `git log -1 --format=%H -- <preregistration.md>`; never a
literal. `git` unavailable is a refusal, not a skip.

### 7.3 Hash discipline

| Hash | Over |
|---|---|
| `protocol_hash`, `config_hash`, `pipeline_hash`, `vectors_hash` | `lf_sha256(path)` |
| `source_hashes[posix path]` | `lf_sha256` of: the three `conceded_shape*.py` modules, `features/team/{__init__,descriptors,match_table}.py`, this runner, `validation/digests.py`, `ingestion/sidecar.py`, `reliability/core.py`, `reliability/confound.py` |
| `code_hash` | `lf_sha256_text("\n".join(f"{path} {hash}" for path sorted))` |
| `input_frame_hashes[league][frame]` | `sha256(pd.util.hash_pandas_object(canonical, index=False).values.tobytes())` where `canonical` = the columns the pipeline reads, in the order listed in 2.1 or section 1, sorted by `event_id` (actions, event sidecar) or `game_id` (matches, match sidecar), index reset |
| `table_hashes[league][window]` | same recipe over the table sorted by `(game_id, team_id)`, columns sorted by name |
| `synthetic_gate_hash` | `lf_sha256(synthetic_gate.json)` |

Parquet file digests are not recorded: they embed the writer's library version and differ
between machines. Content hashes do not.

### 7.4 Structure of `run_real`

```python
def load_league(league: str) -> dict[str, pd.DataFrame]      # column-limited parquet reads + sidecars
def league_tables(frames, config) -> dict[str, tuple[pd.DataFrame, pd.DataFrame]]   # window -> (table, audit)
def run_real(config: dict) -> dict                            # one league in memory at a time
def run_replication(config: dict, frozen: dict) -> dict       # LOCAL; aggregate only
def run_gate(config: dict, workers: int) -> dict
def main(argv: Sequence[str] | None = None) -> int
```

Paths are anchored on `Path(__file__)`. No pool in `real`. `gate` may use a process pool of at
most `synthetic_gate.workers_maximum`; results must not depend on the worker count (seasons
are seeded individually and collected in seed order).

### 7.5 Which code reads which `config.json` key

`test_config_has_every_key_the_pipeline_reads` asserts this table against the code: every key
is read by its consumer, and no consumer reads a number from anywhere else.

| Consumer | Keys |
|---|---|
| `load_league`, coverage | `provider`, `leagues`, `expected_teams_per_league`, `season_start`, `end`, `exposed_leagues`, `unexposed_leagues` |
| table build | `windows`, `window_primary`, `window_sensitivity`, `goal_event_types`, `dismissal_cards`, `exposure_unit_seconds` |
| geometry test (product code cannot read an experiment config, so `descriptors.py` holds the fractions and a test asserts equality) | `sentinel_coordinates`, `coordinate_range`, `final_third_x`, `lateral_left_below_y`, `lateral_right_above_y`, `depth_own_third_below_x`, `depth_opposition_third_from_x`, `penalty_box_wyscout`, `penalty_box_statsbomb`, `high_zone_x_min`, `own_60_x_max`, `defensive_action_clauses`, `descriptor_schema`, `descriptor_parts`, `descriptor_mirror_pairs`, `descriptor_fingerprints`, `descriptor_fingerprints_statsbomb` |
| forward passes | `minimum_prior_matches`, `league_prior_pseudocount_per_part`, `log_ratio_smoothing_per_part`, `raw_persistence_matches`, `shrinkage_grid`, `unit_term_boundary_candidate`, `permutation_seeds`, `strength_tercile_count`, `seed` |
| selection | `evaluation_start`, `selection_tie_tolerance` |
| gates | `minimum_valid_match_share_per_league`, `minimum_development_rows_per_league`, `minimum_development_weeks_per_league`, `minimum_evaluation_rows_per_league`, `minimum_evaluation_weeks_per_league`, `minimum_evaluation_events_per_league`, `minimum_reliability_teams`, `minimum_half_matches_per_team`, `minimum_permutation_changed_share` |
| resampling | `bootstrap_replicates`, `interval_quantiles`, `seed_offsets`, `seed_stride_per_descriptor`, `calendar_week_rule` |
| criteria | `zero_tolerance`, `minimum_leagues_with_negative_estimate`, `holm_family_alpha_one_sided`, `holm_family_size`, `reliability_critical_value`, `reliability_band`, `reliability_number`, `house_reliability_critical_value`, `strength_covariates`, `strength_adjusted_r2_ceiling`, `strength_rank_correlation_floor`, `strength_top_k_reported_only`, `strength_permutations`, `interaction_minimum_events_per_meeting`, `interaction_lower_quantile`, `interaction_floor`, `calibration_minimum_events_per_row` |
| study layout | `primary_descriptor`, `secondary_descriptors`, `level_subject`, `experiment_directory`, `version`, `experiment_id` |
| replication | every key of `replication` |
| synthetic gate | every key of `synthetic_gate` |
| artifact | `results_maximum_bytes`, `forbidden_result_substrings`, `determinism_reruns` |
| restated rules (strings; the test asserts they are present, code does not branch on them) | `prior_rule`, `state_change_rule`, `lateral_edge_rule`, `fingerprint_rule`, `shrinkage_grid_unit`, `selection_tie_rule`, `selection_scope`, `permutation_strata`, `strength_tercile_key`, `reliability_split`, `reliability_centring`, `reliability_interval_method`, `reliability_degrees_of_freedom`, `house_reliability_reported_only`, `hash_policy`, `not_run_in_this_experiment`, `season_label` |

## 8. `results.json`

Aggregate only. No player identifier or name, no team-level row, no key named `rank`, `score`,
`rating`, `index`, `grade` or `total`. Below 512 KB (expected under 150 KB).

```
provenance:
  experiment, protocol_commit, config (verbatim), protocol_hash, config_hash, pipeline_hash,
  vectors_hash, source_hashes, code_hash, hash_policy, packages {numpy, pandas, pyarrow},
  team_match_version, descriptor_schema, descriptor_fingerprints, sidecar_version,
  input_frame_hashes, table_hashes, synthetic_gate_hash, data_license, reuse_disclosure
coverage[league]:
  matches, valid_matches, invalid_by_reason, teams,
  development {rows, eligible_rows, weeks}, evaluation {rows, eligible_rows, weeks},
  window {events_in_window_share, median_window_seconds}, dropped_location {event_set: n}
descriptors[key]:
  role ("primary" | "secondary"), fingerprint, parts, mirror_pairs,
  gates {G1..G6: {passed, detail}}, gates_passed,
  # everything below is absent when gates_passed is false
  events {development, evaluation, by_league},
  selection {k_context, k_unit, context_losses {k: loss}, unit_losses {k | "context_only": loss}},
  shape_ladder {rung: {pooled, by_league}}            # B0_B2, B1_B4, B3, B5, B6, candidate
  p1 {pooled: ClusterEstimate, by_league {league: ClusterEstimate}, unexposed: ClusterEstimate},
  m1 ClusterEstimate | null,
  identity_stress {placebo_p1 [20], placebo_k_unit [20], donor_changed_share [20],
                   placebos_at_or_below, strictly_below_every_placebo, note},
  calibration {coordinate: {slope, interval}} | null,
  reliability {coordinates {name: {half_r, spearman_brown, lower_bound, house_lower_bound_90}},
               n_teams, teams_dropped, implied_per_match_icc, render},
  persistence {coordinate: {r, n_teams}},
  strength_validity {coordinates {name: {r2, r2_adjusted, noise_floor, permutation_p,
                     spearman_raw_vs_residual, top_k_overlap, top_k_chance}}, passed},
  holm {p_one_sided, order_position, threshold, rejected} (secondary only),
  criteria {a, b, c, d, e, f, g}, verdict,
  # primary only
  level {selection, deviance_ladder, l1 {pooled, by_league}, reliability, strength_validity,
         criteria {La, Lb, Le}, status},
  interaction {coordinate: {estimate, lower_bound, n_directed_pairs, n_unordered_pairs}},
  matchup_features_permitted,
  sensitivity {all_states: {p1, reliability}}
replication[key]: {status, local_artifact_sha256 | null}     # no StatsBomb-derived number
product_verdicts: [{experiment_id: "E-10", subject, fingerprint, status, product_state,
                    hostable: true, replication_status, reliability_render, strength_passed,
                    k_context, k_unit, badge, evidence_class, summary}]
verdict, interpretation, uncertainty_limit, product_effect
```

`ClusterEstimate` serialises as `{estimate, interval, p_one_sided, rows, weight, clusters}`.
Coordinate names: three parts `side_balance`, `wide_versus_centre` for the two conceded-channel
descriptors and `first_versus_last`, `ends_versus_middle` otherwise; two parts `first_versus_second`.
`summary` is the frozen sentence of the protocol for that status. The local replication artifact
has the `descriptors[key]` shape restricted to `gates, events, shape_ladder, p1` and `status`.

`synthetic_gate.json`: `{config_hash, protocol_hash, pipeline_hash, code_hash, base_seed,
scenarios {name: {seasons, verdict_counts, criterion_pass_counts, selected_k_unit_counts,
median_p1, median_reliability_lower_bound}}, requirements {name: {rule, observed, passed}},
frame_negative_control {recovered_sign_with_mirror, recovered_sign_without_mirror, passed}, passed}`.

## 9. Tests (all synthetic or hand-computed; none reads the corpus except two marked `slow`)

| File | Test | Asserts |
|---|---|---|
| `test_team_descriptors.py` | `test_payloads_match_frozen_vectors` | payload, fingerprint, `describe()` equal `descriptor_test_vectors.json`; fingerprints equal `config.json` |
| | `test_lattice_edges` | every case of 3.5, values built as `j / 100.0` |
| | `test_remainder_part_and_first_match_wins`, `test_union_counts_each_event_once` | a duel row that also carries the interception flag counts once |
| | `test_changing_a_bound_changes_the_fingerprint`, `test_no_descriptor_reads_duel_success_or_clearance` | |
| | `test_config_geometry_matches_descriptors` | every fraction, clause, part list and mirror pair in `config.json` equals the one in `descriptors.py` |
| | `test_log_ratio_basis_is_orthonormal_and_sums_to_zero` | |
| `test_team_match_table.py` | `test_attack_down_attackers_right_lands_on_defenders_left` | synthetic events: entries ending `y = 0.9` are in the defender's `def_left`; the paired defending duels sit at `y = 0.1` in the defender's own frame |
| | `test_without_the_mirror_the_planted_side_has_the_opposite_sign` | negative control (M-01): reading `att_left` as `def_left` flips the recovered sign |
| | `test_placeholder_and_out_of_range_locations_are_dropped_and_counted` | `(1,1)` end is not an entry on the attacker's right |
| | `test_state_window_goals_own_goals_dismissals`, `test_same_second_incident_does_not_change_that_row`, `test_save_row_goal_flag_is_ignored` | hand-built timeline |
| | `test_window_seconds_hand_example` | closes at 2-0, reopens at 2-1, closes at a red card |
| | `test_goals_mismatch_invalidates_both_rows`, `test_missing_sidecar_raises_when_state_is_needed` | |
| | `test_row_order_and_input_immutability` | shuffle rows; frames unchanged |
| | `test_against_columns_are_the_opponents_for_columns` | |
| | `test_oracle_against_build_match_synthetic` | 2.5 on a synthetic match |
| | `test_oracle_against_build_match_real` (`slow`) | 2.5 on five matches per league |
| `test_conceded_shape_engine.py` | `test_hand_computed_two_date_example` | every formula of 4.2 against `fractions.Fraction` arithmetic written in the test |
| | `test_context_only_is_exactly_b4`, `test_delta_is_zero_without_history` | |
| | `test_future_and_same_day_rows_cannot_change_a_prediction` | poison rows on or after the date |
| | `test_unit_matches_are_excluded_from_its_expected_composition` | changing a context team's counts against `u` alone leaves `E_u`'s other cells unchanged and changes `delta_u` only through `O_u` |
| | `test_invalid_rows_never_update_state`, `test_row_order_invariance` | |
| | `test_mirror_swaps_only_the_pair`, `test_poisson_multinomial_factorisation` | joint Poisson log-likelihood equals level plus shape |
| | `test_donor_map_is_deterministic_within_strata_and_order_invariant` | |
| | `test_cluster_ratio_keeps_both_rows_of_a_match_together_and_is_a_ratio_of_sums` | |
| | `test_selection_ties_prefer_context_only_then_more_shrinkage`, `test_selection_reads_development_rows_only` | |
| | `test_two_part_engine_recovers_a_planted_width_effect` | one seeded season, `sd_width = 0.15`: P1 upper bound below zero for the wide share |
| `test_conceded_shape_rule.py` | `test_verdict_truth_table` | all `2^7 x 2^3 x 2` combinations map to exactly one of four tokens, and to the protocol's token |
| | `test_any_failed_gate_is_inconclusive_and_computes_no_loss` | loss fields absent; forward pass not called (monkeypatched to raise) |
| | `test_holm_hand_example`, `test_none_p_value_never_rejects` | |
| | `test_reliability_bound_thresholds` | at `n = 98`, `G = 5`: `r = 0.5020` gives a lower bound of 0.500 within `1e-3`, `r = 0.6682` gives 0.700; the house bound differs |
| | `test_split_half_known_answer` | 4,000 synthetic units, true plus independent noise: stepped-up value 2/3 within 0.03 |
| | `test_strength_validity_flags_a_shape_that_is_measured_strength`, `test_strength_validity_nan_fails` | |
| | `test_pair_interaction_recovers_a_planted_pair_term_and_zero` | |
| `test_conceded_shape_synthetic.py` | `test_double_round_robin_shape` | every directed pair once, every unordered pair twice with venues swapped, for 18 and 20 teams |
| | `test_generator_is_seeded_and_emits_the_table_schema` | |
| | `test_small_gate_classifies_planted_effect_and_planted_nothing` | 6 seasons each of `EFFECT_STRONG` and `NULL_NOTHING` at 500 replicates: all six `DEFENDER_SHAPE_SIGNAL`; none in the null |
| `test_conceded_shape_experiment.py` | `test_config_has_every_key_the_pipeline_reads`, `test_no_number_is_hard_coded` | AST scan of the three research modules: every numeric literal is in the allowlist `{0, 1, 2, 3, 8}` declared in the test (indices, the deviance factor, the digest slice); every threshold is read from `config` |
| | `test_results_shape_is_strict_json_aggregate_and_small` | end-to-end on two synthetic leagues: `allow_nan=False`, under 512 KB, none of `forbidden_result_substrings`, no banned key |
| | `test_runner_refuses_dirty_tree_missing_gate_and_fingerprint_mismatch` | monkeypatched git |
| | `test_hashes_are_line_ending_invariant`, `test_rerun_is_byte_identical` | |
| | `test_research_modules_are_not_imported_by_product_code` | AST import scan |
| `test_conceded_shape_statsbomb.py` | `test_mapping_on_a_synthetic_event_file` | set-piece passes excluded; own goal credited to the other team; cards; period-relative seconds |
| | `test_statsbomb_reader_is_not_imported_by_api` | |

## 10. Synthetic gate

Runs `evaluate_descriptor(..., role="primary")` (shape and level) on `synthetic_season`
output; no secondary family, so no Holm step. Seed of season `j` of scenario `i` (order of `config.synthetic_gate.scenarios`):
`base_seed + 1000 * i + j`. Gating scenarios use `seasons_per_gating_scenario`, reported ones
`seasons_per_reported_scenario`; every season uses `synthetic_gate.bootstrap_replicates`.

| Scenario | Planted | Requirement on the frozen rule |
|---|---|---|
| `NULL_NOTHING` | no defender shape, no defender level | `DEFENDER_SHAPE_SIGNAL` in at most 5%; `LEVEL_ONLY` in at most 5%; `NOT_ESTABLISHED` in at least 90% |
| `NULL_SHAPE_WITH_LEVEL` | defender level only | `DEFENDER_SHAPE_SIGNAL` in at most 5%; `LEVEL_ONLY` in at least 90% |
| `EFFECT_STRONG` | defender shape, SD 0.15 on both coordinates | `DEFENDER_SHAPE_SIGNAL` in at least 90% |
| `WIDTH_ONLY` | SD 0.15 on wide-versus-centre only | `DEFENDER_SHAPE_SIGNAL` in at most 5% (the three-channel claim needs side information) |
| `STRENGTH_ONLY` | shape = exact function of measured strength | `DEFENDER_SHAPE_SIGNAL` in at most 5% |
| `EFFECT_0_09`, `_0_06`, `_0_03` | smaller shapes | detection rate and per-criterion pass rates published; no requirement |

Plus the frame negative control of section 9 run inside the gate. `passed` is the conjunction.
A failed gate is repaired in the code or reported as a defect of the protocol **before** the
protocol commit; after it, a failed gate blocks the real run and nothing is retuned.

Designer-side prototype (independent NumPy code, synthetic only, 50 seasons per scenario, 1,000
bootstrap replicates; `_work/prototype.py`, logs `_work/rates_*.log`):

| Scenario | Verdicts in 50 seasons | Criteria passed (of 50) |
|---|---|---|
| `NULL_NOTHING` | 50 `NOT_ESTABLISHED` | (a) 0, (c) 1, (e) 0, (g) 50 |
| `NULL_SHAPE_WITH_LEVEL` | 50 `LEVEL_ONLY` | (a) 0, (c) 1, (e) 0 |
| `EFFECT_STRONG` | 50 `DEFENDER_SHAPE_SIGNAL` | all 50 |
| `WIDTH_ONLY` | 0 signal, 50 `LEVEL_ONLY` | (a) 50, (d) 0, (e) 0 |
| `STRENGTH_ONLY` | 0 signal, 50 `LEVEL_ONLY` | (a) to (f) 50, (g) 0 |
| `EFFECT_0_09` | 31 signal, 19 `LEVEL_ONLY` | (a) 50, (e) 31 |
| `EFFECT_0_06` | 0 signal | (a) 46, (e) 0 |
| `EFFECT_0_03` | 0 signal | (a) 7, (e) 0 |

Criterion (c) passes about once in 21 null seasons, as exchangeability predicts. The table
shows the thresholds are satisfiable and that the reliability criterion, not the forecast
criterion, sets the detection limit (about three percentage points of between-team SD in a
channel share). `NULL_SHAPE_WITH_LEVEL`, `WIDTH_ONLY` and the three smaller effects were run
before criterion (g) existed; their plants are independent of strength, and (g) passed 50 of
50 where it was run on such a plant (`NULL_NOTHING`, `EFFECT_STRONG`). The prototype omits
criterion (Le) and the pass-share covariate. These runs are not the gate: the gate is the
implementers' code at 200 seasons.

One finding changed the design. A shape planted as a function of **latent** strength tercile
was called `DEFENDER_SHAPE_SIGNAL` in 50 of 50 seasons before criterion (g) existed: terciles
estimated from prior points misclassify, so a team's own history beats its permuted peers'.
The identity-link test controls league and coarse measured strength, not latent strength.
`STRENGTH_ONLY` therefore plants a shape that is a function of *measured* strength, which
criterion (g) must reject, and the protocol states the limit.

## 11. Pre-outcome code review (a second agent, before the protocol commit is followed by a run)

| # | Check | How |
|---|---|---|
| 1 | No file under review was executed on `data/` | shell history / agent reports; the only real-data test is the `slow` oracle, which reads counts that Match Lab already serves |
| 2 | Every number comes from `config.json` | `test_no_number_is_hard_coded`; read the three modules for stray literals |
| 3 | Prior means strictly earlier calendar date everywhere, league prior included | read `walk_forward_*`; poison test present |
| 4 | The state array is updated after all rows of a date are predicted | read the loop |
| 5 | `A^(-u)` is used for the unit's expectation and plain `A` for the target row | read 4.2 against code |
| 6 | The mirror exists in exactly one place | grep for `att_right`, `def_left` |
| 7 | Placeholder coordinates cannot reach a zone test | read `located` use in the table builder |
| 8 | Ratio of sums, never mean of ratios, for every loss and share | read aggregations |
| 9 | `context_only` arrays are assigned, not recomputed | read; test present |
| 10 | Bootstrap strata, cluster order and seed offsets follow 4.3 | read `cluster_ratio` |
| 11 | Gates run before any loss and return early | test present; read |
| 12 | Verdict map is the protocol's table, order included | truth-table test; read |
| 13 | `results.json` has no identifier, no per-team row, no banned key, no timestamp | test; read the serialiser |
| 14 | The StatsBomb reader is unreachable from `galactico/api` and writes only under `data/licensed/` | import scan; read paths |
| 15 | Hashes are LF-normalised; the gate report hash covers the code under review | read 7.3 against code |
| 16 | Synthetic generator shares no helper with the engine beyond `log_ratio_basis` | read imports |
| 17 | Docstrings state claim and non-claim; no word from the banned list labels a quantity | read |

## 12. Order of operations for the root

1. Implement A-D on synthetic data; `pytest -q`; `ruff check`.
2. `gate`; read `synthetic_gate.json`; code review (section 11).
3. Commit protocol, config, this file, vectors, code, tests and `synthetic_gate.json`. Record the hash.
4. `real` once. `real --verify` once. Read the coverage block before the verdict block.
5. Write `analysis.md` in the E-08 form (verdict first, protocol and implementation commits,
   coverage, ladder, criteria, what it establishes and does not, product consequence,
   reproduction). Replication numbers appear there only, with the StatsBomb attribution.
6. Commit `results.json`, `analysis.md`, the README row and the `verdicts.py` rows.

## SHARED-FILE REQUESTS

| File | Edit |
|---|---|
| `experiments/preregistered/README.md` | add the E-10 row |
| `tests/test_research_firewall.py` | append the three research module names (A7) |
| `galactico/domain/verdicts.py` | seven rows from `results.json["product_verdicts"]` (six descriptors, one level subject); `NOT_RUN` until then |
| `Makefile` / CI | no new job; the synthetic tests run in `check`; the `slow` oracle runs where the corpus is present |

## DISSENT

1. **Calendar-week clusters understate the uncertainty of P1.** Loss differences for the same
   defender are positively dependent across weeks, because one noisy `delta_u` is reused all
   season. The house method is kept as instructed; criteria (b), (c), (f) and the synthetic
   gate bound the false-positive rate of the whole rule (no signal in 150 synthetic seasons
   with no defender shape in the prototype). The published interval should still not be read as calibrated. A team-level
   block bootstrap would be the better interval; it is not adopted because it would change
   the house method inside one experiment.
2. **`REPLICATED` cannot gate a hosted panel today** (R7, critic O1/H2). The research design
   made the shipped evidence class depend on it. This protocol fixes both branches and
   defaults to the Pappalardo verdict only; the decision belongs in an ADR.
3. **The research note's secondary family was not kept.** Its xT-weighted target needs a
   prior-date surface and one of three live turnover recipes; its regain height needs a
   possession rule that does not exist. They are replaced by quantities the root decision
   names (shots, defensive-action location, a passes-per-action analogue) that need neither.
4. **The mirror criterion was strengthened.** As written in the research note (point estimate
   smaller than the placebo's) it passes half the time under no side information.

## OPEN QUESTIONS

1. Is the event sidecar dense (one row per event) or sparse? A1 assumes dense.
2. May a StatsBomb-derived categorical label appear on a hosted page (ADR-0018)?
3. Should the sidecar carry `coachId`, so a later, separately registered study can test
   persistence within a coach's tenure?
4. H3 may change the Match Lab clearance metric; the oracle deliberately does not use it.
