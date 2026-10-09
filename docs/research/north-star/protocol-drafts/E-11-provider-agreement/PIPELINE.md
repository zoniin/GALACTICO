# E-11 pipeline specification

Build target for `experiments/preregistered/E-11-provider-agreement/`. The protocol is
`preregistration.md`; every number is in `config.json`; this file is the code contract.
Where this file and the protocol disagree, the protocol wins and the disagreement is a defect.

**Tier rule (binding on every function below).** E-11 is LOCAL_LICENSED end to end.
Nothing that reads StatsBomb is imported by `galactico/api`, `galactico/optimization`,
`galactico/profiles`, `galactico/match_lab`, `galactico/models` or `galactico/features`.
No crosswalk, per-player row, per-match row, identifier or name is written anywhere
except process memory. The only files written are aggregate JSON and Markdown under
`data/licensed/research/E-11-provider-agreement/` (gitignored). Until the root runs the
real execution, every module is exercised on synthetic data only; `preflight` (section 7)
is the only real-data entry point allowed before the protocol commit.

## 0. Files and ownership

| File | New | Owner | Content |
|---|---|---|---|
| `galactico/validation/statsbomb_reader.py` | yes | E-11 A | raw StatsBomb research reader (pass type, shot type, sheets) |
| `galactico/validation/provider_crosswalk.py` | yes | E-11 A | Wyscout sheet reader, match crosswalk, team-sheet crosswalk, wide link, link evaluation |
| `galactico/validation/provider_inputs.py` | yes | E-11 B | harmonised frames, reference surfaces, inputs, event pairing, divergence tables |
| `galactico/validation/provider_agreement.py` | yes | E-11 C | statistics, resampling, decision rule, admission |
| `galactico/validation/provider_agreement_synthetic.py` | yes | E-11 C | planted corpora and the acceptance run |
| `experiments/run_provider_agreement.py` | yes | E-11 C | CLI: `preflight`, `acceptance`, `execute` |
| `scripts/fetch_statsbomb_double_coded.py` | yes | E-11 A | reproducible fetch of the two folders from the match index |
| `tests/test_statsbomb_reader.py`, `tests/test_provider_crosswalk.py` | yes | E-11 A | |
| `tests/test_provider_inputs.py` | yes | E-11 B | |
| `tests/test_provider_agreement.py`, `tests/test_provider_agreement_rule.py`, `tests/test_provider_agreement_runner.py` | yes | E-11 C | |
| `experiments/preregistered/E-11-provider-agreement/{preregistration.md,config.json}` | yes | root commits | from this folder, byte for byte |

Three agents (A, B, C) can build in parallel against the frames fixed in sections 2 to 5.
No existing file is edited. Frozen files are untouched. `StatsBombProvider`, its
`SEASONS` tuple and `MAPPING_AUDIT` are not edited: `competitions()` must keep returning
the four 2015/16 leagues, or Stage 1C's runner would silently pick up two more folders.

**Reused, unchanged:**

| Reuse | From |
|---|---|
| `fit_expected_threat`, `PitchGrid`, `ExpectedThreat` | `galactico/models/xt` (frozen) |
| `normalise_name`, `name_tokens` | `galactico/identity/resolver.py`. `resolve_player` is **not** used: it accepts nobody without a birth date (0 of 2,176) |
| `PROVIDERS`, `DataTier`, `assert_may_host`, `LicenseViolation` | `galactico/providers/base.py` |
| `lf_sha256`, `lf_sha256_text` | `galactico/validation/digests.py` (ASSUMED INTERFACE 1) |
| channel literals 0.21 / 0.37 / 0.63 / 0.79 | copied into config; a test pins them to `features/spec.py::ActionFilter.apply` |
| `check` | `scripts/check_licensing.py`, called by tests on every new file and on both result files |

Engineering: `from __future__ import annotations`; frozen dataclasses; full type hints;
`__all__`; numpy and pandas only (no scipy); ruff clean; paths anchored at
`Path(__file__).resolve().parents[n]`; module docstring states claim and non-claim.

**Licence-guard traps.** Never write, in any committed file, a double-quoted
`possession_team`, `freeze_frame`, `obv_total_net` or `shot_statsbomb_xg`; never a
double-quoted `eventId`, `subEventId`, `matchPeriod` or `tagsList` followed by a colon.
The reader needs none of those fields. Build StatsBomb-shaped and Wyscout-shaped test
payloads with `dict(...)` calls. Result JSON uses none of the keys in
`results_key_denylist`.

## 1. Data flow

```
StatsBomb raw JSON (LOCAL)                      Pappalardo raw JSON + Parquet (PUBLIC)
  read_matches / read_team_sheets                 read_wyscout_matches / _team_sheets / _people
            \                                         /
             crosswalk_matches  ->  match_links (in memory)
             team_sheet_crosswalk -> pairs (in memory) -> evaluate_wide_link -> identity block
  read_events                                     actions.parquet (column list)
  harmonise_statsbomb(variant)                    harmonise_wyscout
  statsbomb_reference_surface(variant)            wyscout_reference_surface
            \                                         /
             player_match_inputs / team_match_inputs   (per provider, variant, valuation)
             build_panel -> match_weights, player_weights -> cell_agreement -> classify
             permuted controls -> admission
             clock_offsets -> pair_events -> divergence_tables
                         results.local.json  +  results.json (tokens only)  +  report_tables.md
```

## 2. `galactico/validation/statsbomb_reader.py`

Claim: reads fields the shipped adapter drops, for research. Non-claim: it is not a
provider adapter, feeds no product path and changes no shipped number.

```python
READER_VERSION = "statsbomb-research-reader-v1"

def read_matches(root: Path, folder: str) -> pd.DataFrame
def read_team_sheets(root: Path, folder: str,
                     game_ids: Collection[int] | None = None, *, cap: int = 90) -> pd.DataFrame
def iter_events(root: Path, folder: str,
                game_ids: Collection[int] | None = None) -> Iterator[tuple[int, list[dict]]]
def read_events(root: Path, folder: str,
                game_ids: Collection[int] | None = None) -> pd.DataFrame
def folder_manifest(root: Path, folder: str) -> dict[str, object]
```

Matches are enumerated from `_matches.json` only, never by listing `events/` (a delisted
file on disk must not become a match). A listed match without its event or lineup file
raises `FileNotFoundError`.

`read_matches` columns: `sb_game_id` int64, `folder` str, `date` str `YYYY-MM-DD`,
`home_sb_team_id`, `away_sb_team_id` int64, `home_team_name`, `away_team_name` str,
`home_goals`, `away_goals` Int64, `stage` str or None, `data_version` str or None.

`read_team_sheets`: one row per player with at least one position spell whose
`from_period` is 1 or 2.

| Column | Rule |
|---|---|
| `sb_game_id`, `sb_team_id`, `sb_player_id` | int64 |
| `player_name`, `player_nickname`, `country` | str; the last two may be None; `country` is `country.name` |
| `started` | any spell with `from_period == 1` and minute field 0 (the shipped rule) |
| `minutes_regulation` | `sum(max(0, end − start))` over regulation spells; `start = min(mm(from), cap)`; `end = min(mm(to), cap)` when `to` exists and `to_period <= 2`, else `cap`; `mm` is the integer before the colon |
| `minute_on`, `minute_off` | smallest `start`, largest `end` |
| `is_goalkeeper` | position of the spell with most regulation minutes equals `statsbomb_goalkeeper_position`; ties go to the earliest spell |
| `cautioned`, `dismissed` | any card; any card whose `card_type` is not `Yellow Card` |

`read_events`: every event of every listed match, **nothing dropped**.

| Column | dtype | Rule |
|---|---|---|
| `sb_game_id` | int64 | |
| `period` | int8 | raw `period` (1 to 5) |
| `period_seconds` | float64 | parsed from `timestamp` (`HH:MM:SS.mmm`), which restarts each period; this is what pairs with Wyscout `seconds` |
| `event_order` | int64 | raw `index` |
| `sb_team_id` | int64 | `team.id` |
| `sb_player_id` | Int64 | `player.id`, NA when absent |
| `kind` | str | `type.name` |
| `start_x`, `start_y` | float64 | `location / (120, 80)`; NaN when absent |
| `end_x`, `end_y` | float64 | `end_location` of the pass, carry or shot detail `/ (120, 80)`; NaN when absent (never a copy of the start) |
| `has_outcome` | bool | the detail object for this `kind` carries an `outcome` |
| `outcome` | str or None | its name |
| `pass_type`, `pass_height`, `body_part` | str or None | `pass.type.name`, `pass.height.name`, `pass.body_part.name` or `shot.body_part.name` |
| `pass_cross`, `shot_assist`, `goal_assist` | bool | `pass.cross`, `pass.shot_assist`, `pass.goal_assist` |
| `shot_type`, `duel_type` | str or None | `shot.type.name`, `duel.type.name` |
| `play_pattern` | str or None | `play_pattern.name` |
| `event_id` | str | raw `id`; in memory only |

`folder_manifest` returns `folder`, `event_files`, `lineup_files`, `bytes`,
`data_versions` (count per distinct `metadata` JSON), and `digest` = sha256 of the lines
`<posix path relative to root>:<sha256 of file bytes>` sorted and joined with `\n`.

`scripts/fetch_statsbomb_double_coded.py`: `DOUBLE_CODED = {"World_Cup_2018": (43, 3),
"La_Liga_2017_18": (11, 1)}`; same layout and base URL as `scripts/fetch_statsbomb.py`;
ids come from the match index; asserts 64 and 36; merges a `double_coded` block into
`MANIFEST.json` without touching `seasons`. Not run by tests.

## 3. `galactico/validation/provider_crosswalk.py`

Claim: identity from team sheets alone. Non-claim: no birth date confirms any link; no
event enters any function here (a test asserts no parameter is an event frame).

```python
CROSSWALK_VERSION = "team-sheet-crosswalk-v1"

def read_wyscout_matches(raw_root: Path, competition: str) -> pd.DataFrame
def read_wyscout_team_sheets(raw_root: Path, competition: str,
                             game_ids: Collection[int], *, cap: int = 90) -> pd.DataFrame
def read_wyscout_people(raw_root: Path) -> pd.DataFrame
def crosswalk_matches(sb_matches: pd.DataFrame, wy_matches: pd.DataFrame,
                      wy_teams: pd.DataFrame, config: Mapping[str, object],
                      *, subset: str) -> tuple[pd.DataFrame, dict[str, int]]
def team_sheet_crosswalk(sb_sheets: pd.DataFrame, wy_sheets: pd.DataFrame,
                         wy_people: pd.DataFrame, match_links: pd.DataFrame,
                         config: Mapping[str, object]) -> tuple[pd.DataFrame, dict[str, object]]
def name_nationality_link(left: pd.DataFrame, right: pd.DataFrame,
                          config: Mapping[str, object], *, tiers: Sequence[str],
                          exclude_right: Mapping[int, int] | None = None) -> pd.DataFrame
def evaluate_wide_link(pairs: pd.DataFrame, sb_people: pd.DataFrame, wy_people: pd.DataFrame,
                       subset_of_player: Mapping[int, frozenset[str]],
                       config: Mapping[str, object]) -> list[dict[str, object]]
def wilson_interval(successes: int, trials: int, z: float) -> tuple[float | None, float | None]
def link_verdict(block: Mapping[str, object], config: Mapping[str, object]) -> str
def permuted_partners(pairs: pd.DataFrame, stratum: pd.Series, seed: int) -> pd.Series
def crosswalk_digest(frame: pd.DataFrame, columns: Sequence[str]) -> str
```

| Frame | Columns |
|---|---|
| `read_wyscout_matches` | `wy_game_id` int64, `date` str (first ten characters of `dateutc`), `home_wy_team_id`, `away_wy_team_id` int64, `home_goals`, `away_goals` Int64 (from `teamsData[*].score`), `duration` str |
| `read_wyscout_team_sheets` | `wy_game_id`, `wy_team_id`, `wy_player_id` int64, `started` bool, `minutes_regulation` int (starter: `min(off_minute or cap, cap)`; used substitute: `max(0, cap − on_minute)`; a non-list `substitutions` is empty, as in the adapter), `minute_on`, `minute_off` int, `cautioned`, `dismissed` bool (`yellowCards`, `redCards` not `"0"`). Unused substitutes have no row |
| `read_wyscout_people` | `wy_player_id` int64, `full_name` (first plus last name, unicode-unescaped exactly as the adapter does), `short_name`, `birth_area`, `passport_area` str or None, `position` (`role.code2`). 3,603 rows |
| `wy_teams` | `teams.parquet`: `team_id`, `team_name` |
| `match_links` | `match_key` int32 (0..M−1, assigned after concatenating subsets in config order, sorted by `wy_game_id`), `subset`, `sb_game_id`, `wy_game_id`, `date`, `swapped` bool, `duration`, `goal_check` in `agree` / `skipped`, `sb_home_team_id`, `sb_away_team_id`, `wy_team_for_sb_home`, `wy_team_for_sb_away` |
| `pairs` | `sb_player_id`, `wy_player_id` int64, `status` in `VERIFIED_BY_TEAM_SHEET` / `ELIMINATION_ONLY` / `STRUCTURE_CONFLICT` / `BIJECTION_CONFLICT`, `sheets_named`, `sheets_together` int, `swap_impossible` bool, `is_goalkeeper` bool |

**`crosswalk_matches`.** Candidates for a StatsBomb match: Wyscout matches of the subset
within `match_date_tolerance_days`. Orientation `straight`: `J(home, home)` and
`J(away, away)` both above `match_team_token_overlap_strictly_above`; `swapped`: the
cross pairs. `J` is Jaccard on `name_tokens`. A candidate qualifies in the orientation
with the larger smaller-side overlap; equal overlaps in both orientations disqualify.
Exactly one qualifying candidate, and that candidate chosen by no other StatsBomb match,
or the match is rejected. Then, when `duration` is in
`match_require_goal_agreement_durations`, goals must agree after orientation.
Rejection reasons counted: `NO_CANDIDATE`, `AMBIGUOUS`, `CLAIMED_TWICE`, `GOALS_DISAGREE`.

**`team_sheet_crosswalk`.** Exactly protocol steps 1 to 4. Name forms: StatsBomb
`player_name`, `player_nickname`; Wyscout `full_name`, `short_name`. Per sheet, loop:
compute for each unpaired row its set of maxima above `sheet_name_overlap_strictly_above`
on the other side; take
every pair that is a singleton maximum in both directions; stop when a pass takes none.
`swap_impossible` is true when, in every sheet the pair shares, the StatsBomb player has
zero overlap with every other Wyscout sheet row and vice versa. The audit dict holds
counts by status, per-subset coverage shares on each side (outfield player-matches with
at least one regulation minute that hold a verified link), `swap_impossible_share`,
and the cautioned table (both / StatsBomb only / Wyscout only). Verified outfield =
verified and Wyscout `position` is not `wyscout_goalkeeper_position`.

**`name_nationality_link`.** `left`: `left_id`, `full_name`, `known_as` (nullable),
`country`. `right`: `right_id`, `full_name`, `countries` (tuple). Returns `left_id`,
`right_id` (Int64, NA when unlinked), `tier`, `outcome` in `LINKED` / `AMBIGUOUS` /
`CLAIMED_TWICE` / `NO_CANDIDATE`. Country comparison: `normalise_name` on both, then
`country_aliases_normalised` on the left. Tier A candidates: a left form (`full_name`
or `known_as`) whose token set equals the right `full_name` token set, at least
`link_tier_a_minimum_tokens` tokens, nationality agrees. One candidate links; several
are `AMBIGUOUS` and do **not** fall through. With none and tier B requested: one token
set strictly contains the other with at least `link_tier_b_minimum_shared_tokens`
shared, nationality agrees; same one-or-ambiguous rule. Finally any `right_id` taken by
two lefts turns all of them into `CLAIMED_TWICE`. `exclude_right` maps a `left_id` to
one `right_id` hidden from that left only.

**`evaluate_wide_link`.** Left = StatsBomb players with a verified link (goalkeepers
included); right = all of `read_wyscout_people`. For each tier set in `link_tier_sets`
and each of `pooled`, `world_cup`, `la_liga`: `verified_players`, `linked`,
`recall` (linked to the verified partner / verified players), `false_link_rate`
(linked to someone else / linked), `no_link_rate`, outcome counts, each with
`wilson_interval`; the same split by nickname present or absent; and
`absent_partner_false_link_rate`: rerun with `exclude_right = {left: verified partner}`,
all other lefts keeping their full-run links for the `CLAIMED_TWICE` rule; rate = linked /
verified players. `link_verdict` applies the protocol table to the `pooled` block.

**`permuted_partners`.** Verified outfield players only. Inside each stratum (sorted
ids), shuffle with `default_rng(SeedSequence([seed_root, 3, seed]))`, then give each
player the Wyscout partner of the next player cyclically. No fixed point when the
stratum has two or more members; singletons are returned unchanged and counted.

## 4. `galactico/validation/provider_inputs.py`

Claim: one definition per quantity, applied to both providers after an explicit family
mapping. Non-claim: equal names do not make the two event streams the same observation.

```python
INPUTS_VERSION = "provider-inputs-v1"
FLAGS: tuple[str, ...]   # the boolean columns below, in this order

def harmonise_statsbomb(events: pd.DataFrame, match_links: pd.DataFrame, pairs: pd.DataFrame,
                        config: Mapping[str, object], *, variant: str) -> pd.DataFrame
def harmonise_wyscout(actions: pd.DataFrame, match_links: pd.DataFrame, pairs: pd.DataFrame,
                      config: Mapping[str, object]) -> pd.DataFrame
def wyscout_reference_surface(actions: pd.DataFrame, excluded_game_ids: Collection[int],
                              config: Mapping[str, object]) -> ExpectedThreat
def statsbomb_reference_surface(root: Path, config: Mapping[str, object],
                                *, variant: str) -> ExpectedThreat
def xt_delta(frame: pd.DataFrame, xt: ExpectedThreat) -> np.ndarray
def goal_angle(x: np.ndarray, y: np.ndarray, config: Mapping[str, object]) -> np.ndarray
def in_penalty_area(x: np.ndarray, y: np.ndarray, config: Mapping[str, object]) -> np.ndarray
def sheet_minutes(sheets: pd.DataFrame, match_links: pd.DataFrame, pairs: pd.DataFrame,
                  *, provider: str) -> pd.DataFrame
def player_match_inputs(frame: pd.DataFrame, minutes: pd.DataFrame, xt: ExpectedThreat,
                        config: Mapping[str, object], *, shot_model: object | None = None
                        ) -> pd.DataFrame
def team_match_inputs(frame: pd.DataFrame, xt: ExpectedThreat,
                      config: Mapping[str, object]) -> pd.DataFrame
def clock_offsets(sb: pd.DataFrame, wy: pd.DataFrame,
                  config: Mapping[str, object]) -> dict[tuple[int, int], float]
def pair_events(sb: pd.DataFrame, wy: pd.DataFrame, family: Mapping[str, object],
                offsets: Mapping[tuple[int, int], float],
                config: Mapping[str, object]) -> pd.DataFrame
def divergence_tables(sb_events: pd.DataFrame, sb: pd.DataFrame, wy: pd.DataFrame,
                      offsets: Mapping[tuple[int, int], float], xt_common: ExpectedThreat,
                      config: Mapping[str, object]) -> dict[str, object]
```

**Harmonised frame** (both functions return exactly these columns; regulation periods only):

| Column | Rule |
|---|---|
| `match_key`, `subset` | from `match_links`; unlinked matches dropped |
| `provider` | `statsbomb` or `wyscout` |
| `period` | 1 or 2 (`1H`→1, `2H`→2) |
| `seconds` | seconds since the period started (`period_seconds`; Wyscout `seconds`) |
| `event_order` | StatsBomb `event_order`; Wyscout row position in the Parquet |
| `team_key` | Wyscout team id (StatsBomb teams mapped through the link) |
| `attributed` | the provider named a player (Wyscout `player_id != 0`) |
| `player_key` | Wyscout player id of the verified link, Int64, NA when unattributed or unverified |
| `start_x`, `start_y`, `end_x`, `end_y` | unit square, acting team's attacking frame, `y = 0` the attacker's left. Wyscout as stored; StatsBomb NaN stays NaN |
| flags | below |

| Flag | Wyscout (neutral Parquet) | StatsBomb `open_play` | StatsBomb `as_shipped` |
|---|---|---|---|
| `open_play_pass` | `type == "pass"` | `kind == "Pass"` and `pass_type` in `statsbomb_open_play_pass_types` | `kind == "Pass"`, location and player present |
| `completed` | `success` is True | `open_play_pass` and not `has_outcome` | same on its own pass set |
| `key_pass` | `completed` and `key_pass` | `completed` and (`shot_assist` or `goal_assist`) | same |
| `key_pass_assist_inclusive` | `completed` and (`key_pass` or `assist`) | as `key_pass` | same |
| `corner`, `free_kick_pass`, `throw_in`, `goal_kick` | `set_piece` subtypes per config | `kind == "Pass"` and `pass_type` in the matching config list | same |
| `open_play_shot` | `type == "shot"` | Shot with `shot_type` in `statsbomb_open_play_shot_types` | every Shot with location and player |
| `free_kick_shot`, `penalty` | `set_piece` subtype `free_kick_shot`, `penalty` | Shot with matching `shot_type` | same |
| `non_penalty_shot` | `open_play_shot` or `free_kick_shot` | Shot and not `penalty` | every Shot with location and player |
| `goal` | shot family and `goal` | Shot and `outcome == "Goal"` | same |
| `clearance` | `touch` with subtype in `wyscout_clearance_subtypes` | `kind == "Clearance"` | same |
| `foul` | `foul` with subtype in `wyscout_foul_subtypes` | `kind == "Foul Committed"` | same |
| `interception` | `interception` column True | `kind == "Interception"` or Pass with `pass_type` in `statsbomb_defensive_pass_types` | same |
| `ground_defending_duel` | `duel` with subtype in `wyscout_defensive_duel_subtypes` | Duel with `duel_type` in `statsbomb_defensive_duel_types`, or `kind == "Dribbled Past"` | same |
| `defensive_action` | `ground_defending_duel` or `interception` or `clearance` or `foul` | `kind` in `statsbomb_defensive_kinds`, or the Duel rule, or the defensive Pass rule | same |
| `turnover` | failed `pass`, or `dangerous_loss` | failed open-play pass, or `kind` in `statsbomb_turnover_kinds` | failed Pass, or the same kinds |

Wyscout frames are read from `competition=World_Cup/actions.parquet` and
`competition=Spain/actions.parquet` with a column list, filtered to linked matches, and
checked for `provider == {"pappalardo"}`. Never `pd.read_parquet` on the directory.

**Surfaces.** Both call `fit_expected_threat(move_start, move_end, shot_start, shot_goal,
turnover_start, grid=PitchGrid(*xt_grid), max_iterations, tolerance)` with moves =
`completed` rows, shots = `open_play_shot` rows (`shot_goal` = `goal`), turnovers =
`turnover` rows; a surface that did not converge or is not finite raises `ValueError`
(the runner maps it to the `XT_SURFACE` gate). `wyscout_reference_surface` uses the Spain
frame minus the linked La Liga matches. `statsbomb_reference_surface` streams
`iter_events(root, xt_statsbomb_reference_folder)` file by file, keeps only the
coordinate arrays, asserts `xt_statsbomb_reference_expected_matches`, and applies the
flag rules of the requested variant. Rows with a NaN coordinate are dropped before the
fit and counted. `xt_delta` returns `values[cells(end)] − values[cells(start)]` and
raises on any NaN coordinate (`PitchGrid.cells` would otherwise send NaN to column 0).

**Geometry.** `X = (1 − x) · pitch_length_m`, `Y = (y − 0.5) · pitch_width_m`,
`g = goal_width_m`. `goal_angle = arctan2(g·X, X² + Y² − (g/2)²)`, plus π where negative.
`in_penalty_area`: `X <= penalty_area_depth_m` and `|Y| <= penalty_area_width_m / 2`.

**`sheet_minutes`** returns `match_key`, `subset`, `player_key`, `team_key`,
`minutes_regulation` for verified outfield players with a sheet row on that provider.

**`player_match_inputs`** returns one row per row of `minutes`: `match_key`, `subset`,
`player_key`, `team_key`, then every key of config `player_match_inputs` as float64,
`0.0` where the player has no qualifying event. `shot_location_value_sum` is NaN in
every row when `shot_model` is None. Unattributed and unverified rows contribute nothing.

**`team_match_inputs`** returns one row per (`match_key`, `team_key`): `match_key`,
`subset`, `team_key`, every count and sum of config `team_match_quantities`, plus the
helper columns `defensive_action_x_sum`, `opponent_build_up_passes`,
`high_defensive_actions`. All rows of the team count, attributed or not.
`opponent_build_up_passes` is taken from the other team of the same match.

**Event pairing (purpose c).** `clock_offsets`: per (`match_key`, `period`), the value in
`arange(lo, hi + step, step)` of `pair_offset_grid_seconds` maximising the number of
StatsBomb `open_play_pass` rows with at least one same-team Wyscout `open_play_pass`
row within `pair_offset_match_window_seconds` of `seconds_sb + offset`; ties to the
smallest absolute value, then the negative. `pair_events` returns `match_key`, `period`,
`sb_row`, `wy_row`, `time_gap`, `start_distance_m`: candidates share match, period and
team, satisfy the family's tolerances, and are taken greedily in ascending
(`|time_gap|`, `start_distance_m`, `sb event_order`, `wy event_order`), each row at
most once. Distances use `pitch_length_m` × `pitch_width_m`. `divergence_tables` returns
the `divergence` block of section 8; the runner strips nothing from it, so it must
already be aggregate.

## 5. `galactico/validation/provider_agreement.py`

Claim: agreement statistics and a frozen rule that maps every outcome to one token.
Non-claim: a token is about two coders of the same matches, not about football.

```python
AGREEMENT_VERSION = "provider-agreement-v1"

@dataclass(frozen=True)
class InputPanel:
    players: np.ndarray            # (P,) player keys ascending; process memory only
    matches: np.ndarray            # (M,) match keys ascending
    subset_of_match: np.ndarray    # (M,) str
    stratum_of_player: np.ndarray  # (P,) team of most regulation minutes
    position_of_player: np.ndarray # (P,) Wyscout role code
    present: np.ndarray            # (P, M) bool: the frozen minimum regulation minutes on BOTH providers
    values: Mapping[str, np.ndarray]   # input key -> (P, M) float64; 0.0 where not present

@dataclass(frozen=True)
class BlandAltman:
    bias: float; sd: float; lower: float; upper: float
    relative_bias: float; scale_ratio: float; slope: float

@dataclass(frozen=True)
class Agreement:
    units: int
    mean_statsbomb: float; mean_wyscout: float; sd_statsbomb: float; sd_wyscout: float
    spearman: float; concordance: float; icc_absolute_single: float
    bland_altman: BlandAltman
    exact_share: float | None

@dataclass(frozen=True)
class CellResult:
    quantity: str; level: str; pool: str; reader: str; valuation: str; exposure_minutes: int | None
    point: Agreement | None
    spearman_interval: tuple[float, float] | None
    concordance_interval: tuple[float, float] | None
    relative_bias_interval: tuple[float, float] | None
    valid_replicates: int
    verdict: str | None            # None for an ungraded sensitivity
    reason: str | None

def build_panel(inputs: pd.DataFrame, players: np.ndarray, matches: np.ndarray,
                subset_of_match: np.ndarray, stratum_of_player: np.ndarray,
                position_of_player: np.ndarray, present: np.ndarray) -> InputPanel
def spearman(x: np.ndarray, y: np.ndarray) -> float
def concordance(x: np.ndarray, y: np.ndarray) -> float
def icc_absolute_single(x: np.ndarray, y: np.ndarray) -> float
def bland_altman(statsbomb: np.ndarray, wyscout: np.ndarray, z: float) -> BlandAltman
def agreement(statsbomb: np.ndarray, wyscout: np.ndarray, *, count_kind: bool, z: float) -> Agreement
def match_weights(subset_of_match: np.ndarray, replicates: int, seed: int) -> np.ndarray
def player_weights(players: int, replicates: int, seed: int) -> np.ndarray
def aggregated_values(panel: InputPanel, quantity: Mapping[str, object],
                      match_weight: np.ndarray, config: Mapping[str, object],
                      *, pool: str, exposure: int) -> tuple[np.ndarray, np.ndarray]
def cell_agreement(statsbomb: InputPanel | pd.DataFrame, wyscout: InputPanel | pd.DataFrame,
                   quantity: Mapping[str, object], config: Mapping[str, object], *,
                   level: str, pool: str, reader: str, valuation: str,
                   match_weight: np.ndarray, player_weight: np.ndarray | None,
                   exposure: int | None, graded: bool,
                   failed_gates: Sequence[str] = ()) -> CellResult
def classify(*, failed_gates: Sequence[str], units: int, minimum_units: int,
             nonzero_both: int, constant: bool, valid_share: float,
             spearman_interval: tuple[float, float] | None,
             concordance_interval: tuple[float, float] | None,
             relative_bias_interval: tuple[float, float] | None,
             config: Mapping[str, object]) -> tuple[str, str | None]
def permuted_link_control(statsbomb: InputPanel, wyscout: InputPanel,
                          quantity: Mapping[str, object], pairs: pd.DataFrame,
                          config: Mapping[str, object], *, pool: str,
                          exposure: int) -> dict[str, object]
def admission(cells: Sequence[CellResult], controls: Mapping[str, object],
              config: Mapping[str, object]) -> dict[str, dict[str, str]]
```

| Function | Exact definition |
|---|---|
| `spearman` | Pearson correlation of average ranks. NaN when fewer than `spearman_minimum_units` units or either side constant |
| `concordance` | `2·s_xy / (s_x² + s_y² + (mean_x − mean_y)²)`, moments with `1/n`. NaN when the denominator is 0 |
| `icc_absolute_single` | two-way random, absolute agreement, single measure, `k = 2`: `(MSR − MSE) / (MSR + (k − 1)·MSE + k·(MSC − MSE)/n)` |
| `bland_altman` | `d = statsbomb − wyscout`; `bias = mean(d)`; `sd` with `ddof = 1`; limits `bias ± z·sd`; `relative_bias = bias / ((mean_sb + mean_wy)/2)`, NaN when that mean is not strictly positive; `scale_ratio = sd_sb / sd_wy`; `slope` = least-squares slope of `d` on `(sb + wy)/2` |
| `agreement` | the above on finite pairs; `exact_share` only when `count_kind` |
| `match_weights` | `(B, M)` int16. `rng = default_rng(SeedSequence([seed, 1]))`; for each subset in config order, `rng.multinomial(m, [1/m]*m, size=B)` written into that subset's columns |
| `player_weights` | `(B, P)` int16 from `default_rng(SeedSequence([seed, 2])).multinomial(P, [1/P]*P, size=B)`; `P` = all verified outfield players, canonical order |
| `aggregated_values` | pool restricts the match axis. `num = values[numerator] @ w`, `den = values[denominator] @ w`, minutes likewise. `defined` requires weighted minutes at or above `exposure` and, for ratio quantities, the frozen minimum denominator; the caller requires `defined` on **both** providers. `value = scale · num / den` |
| `cell_agreement` | point estimate with unit weights; per replicate `b` the units are: aggregated level, defined players repeated `player_weight[b, p]` times; player-match level, present cells repeated `match_weight[b, m] · player_weight[b, p]` times; team level, team-matches repeated `match_weight[b, m]` times. Replicate invalid when units are below `ceil(replicate_minimum_unit_share_of_gate · minimum_units)` or a side is constant. Intervals = `np.quantile` (linear) of valid replicates at `interval_quantiles` for Spearman, concordance and relative bias. `player_weight=None` selects the match-only sensitivity |
| `classify` | protocol decision table, rows 1 to 5 in order. Row 1 reason precedence: `failed_gates[0]`, `UNITS`, `DEGENERATE` (constant side or too few non-zero on both), `REPLICATES`, `UNDEFINED_STATISTIC`. Comparisons are `>=` for lower bounds, `<` for row 4, inclusive for the bias margin. Any NaN bound in row 2 fails row 2 only |
| `permuted_link_control` | for each seed in `permuted_link_seeds`, re-index the Wyscout panel through `permuted_partners` and return the Spearman point value; output `values` (sorted), `point`, `strictly_above_all`, `singleton_players` |
| `admission` | protocol admission table. Keys = `aggregated_player_quantities` keys. Value `{status, reason, pooled_verdict, la_liga_verdict}`, computed for the `open_play` reader only (asked about `as_shipped`, the answer is `EXCLUDED (NOT_PRIMARY_READER)`). Reason precedence: `POSITIVE_CONTROL`, `VERDICT`, `LA_LIGA_SUBSET_CONTRADICTS`, `PERMUTED_LINK_CONTROL`. Adds `e12_preferred: false` on `chance_creation_assist_inclusive` when `chance_creation` is also admitted |

Shared worlds (R12): the runner creates `match_weights` and `player_weights` once and
passes the same arrays to every cell. Replicate `b` is therefore one world for all
quantities, providers, variants, valuations and pools.

## 6. `galactico/validation/provider_agreement_synthetic.py`

```python
def planted_panels(seed: int, *, players: int, matches: Sequence[int],
                   population_spearman: float, wyscout_scale: float
                   ) -> tuple[InputPanel, InputPanel, dict[str, object]]
def run_acceptance(config: Mapping[str, object]) -> dict[str, object]
def synthetic_corpus(root: Path, *, seed: int, matches: Sequence[int] = (6, 4),
                     restarts_per_match: int = 5, noise: bool = False) -> dict[str, object]
```

`planted_panels` (stated so an oracle can be written without reading the code):
matches `M = sum(matches)` in two subsets; nine players in ten belong to the first subset
and appear in `k ~ U{3..7}` of its matches, the rest to the second with `k ~ U{10..M2}`;
90 minutes per appearance. Latent pair `(a, b)` bivariate normal, mean 1.0, sd 0.2,
Pearson `r = 2·sin(π·ρ_s/6)`, so the population Spearman is exactly `ρ_s`
(`ρ_s = 6/π · asin(r/2)`). StatsBomb numerator = `a · minutes/90`, Wyscout numerator =
`wyscout_scale · b · minutes/90`, no match-level noise: a gated player's rate equals his
latent value in every world. Third return value: the quantity mapping
(`planted_rate` = 90 × `planted_numerator` / `minutes_regulation`).

`run_acceptance`: for each scenario in `acceptance_scenarios`, `acceptance_corpora`
corpora (seeds `SeedSequence([acceptance_seed, 4, scenario_index, corpus_index])`), each
graded through the **same** `cell_agreement` and `classify` as the real run at level
`aggregated_player`, pool `pooled`, exposure `exposure_minimum_minutes_primary`,
`acceptance_bootstrap_replicates` replicates. Returns per scenario the token shares and
`passed`; overall `passed` is the conjunction.

| Scenario | Planted | Must hold |
|---|---|---|
| `planted_comparable` | `ρ_s = 0.95`, scale 1 | `COMPARABLE` in at least 95% |
| `planted_order_only` | `ρ_s = 0.95`, scale 1.5 (relative bias −0.40) | `COMPARABLE_IN_RANK_ONLY` in at least 95%; `COMPARABLE` never |
| `planted_null` | independent | `NOT_COMPARABLE` in at least 95%; no admitted token ever |
| `planted_moderate` | `ρ_s = 0.60` | `NOT_COMPARABLE` in at least 90%; no admitted token ever |
| `planted_boundary` | `ρ_s = 0.80` exactly | admitted tokens in at most 10%; `NOT_COMPARABLE` in at most 10% |
| `planted_gate` | 100 players (below the unit gate) | `INCONCLUSIVE` in 100% |

`synthetic_corpus` writes StatsBomb-shaped folders and Pappalardo-shaped raw JSON and
Parquet under a temporary `root` for end-to-end tests: a known truth event list per
match, both providers derived from it. With `noise=False` the Wyscout view is an exact
re-encoding of the StatsBomb view except that `restarts_per_match` set-piece passes are
typed as restarts on both sides (so `as_shipped` over-counts StatsBomb passes by exactly
that number per team-match and `open_play` does not), names appear in different forms,
one team sheet holds two players sharing a surname, one match has swapped orientation,
one player is dismissed, and one match goes to extra time.

## 7. `experiments/run_provider_agreement.py`

```python
def preflight(config: Mapping[str, object]) -> dict[str, object]
def acceptance(config: Mapping[str, object]) -> dict[str, object]
def run(config: Mapping[str, object], *, protocol_commit: str) -> tuple[dict, dict, str]
def main(argv: Sequence[str] | None = None) -> int
```

| Subcommand | Reads | Writes | Allowed before the protocol commit |
|---|---|---|---|
| `preflight` | file presence, JSON key sets, `folder_manifest`, match crosswalk only | stdout counts | yes (structure only) |
| `acceptance` | nothing real | `<local_output_root>/acceptance.json`: scenario shares, `passed`, config hash, source hashes | yes |
| `execute --protocol-commit <sha>` | everything | `results.local.json`, `results.json`, `report_tables.md` in `<local_output_root>` | **no** |
| `execute --protocol-commit <sha> --verify` | everything | `determinism.json` only; exit 1 unless the recomputed `results.local.json` bytes equal the file on disk | no |

`execute` refuses, exit 2 with a one-line reason, unless all hold:

1. `git` is available; `<sha>` is a commit and an ancestor of `HEAD`; `lf_sha256` of the
   working `preregistration.md` and `config.json` equal those of
   `git show <sha>:<path>`. Read-only git only. No git, no run (fail closed).
2. `acceptance.json` exists, `passed` is true, and its config hash and source hashes
   equal the current ones.
3. `local_output_root` resolves under `data/licensed/` and `PROVIDERS["statsbomb"].tier`
   is `LOCAL_LICENSED`. `assert_may_host("pappalardo")` is called before any public read.
4. Without `--verify`, `results.local.json` does not already exist (one execution).

Files are written with `Path.write_text(json.dumps(obj, indent=2, allow_nan=False,
sort_keys=True) + "\n", encoding="utf-8", newline="\n")`; nothing is printed to stdout
except progress on stderr (PowerShell redirection writes UTF-16). After serialising,
the runner asserts: size at most `maximum_results_bytes`; no key in
`results_key_denylist` anywhere; `scripts.check_licensing` fingerprint patterns absent;
in `results.json`, no `float` and no `int` outside `provenance.config` (`bool` is allowed
and is tested before `int`, of which it is a subclass).

Order inside `run`: hashes; StatsBomb matches and sheets; Wyscout matches, sheets,
people, Parquet frames; match crosswalk and gate; team-sheet crosswalk and gate; wide
link; three surfaces; optional shot model; events and harmonised frames for both
variants; inputs for (provider × variant × valuation); panels; weights; cells; controls;
admission; divergence; serialise. Memory: event frames are built per folder and reduced
to harmonised columns before the next is read; peak well under 1.5 GB; no process pool.

**The single command the root runs for the real execution** (repository root, after
the protocol commit `<sha>` and a passing `acceptance`):

```powershell
.venv\Scripts\python.exe -X utf8 experiments/run_provider_agreement.py execute --protocol-commit <sha>
```

Determinism re-run, once, unchanged:

```powershell
.venv\Scripts\python.exe -X utf8 experiments/run_provider_agreement.py execute --protocol-commit <sha> --verify
```

## 8. Result shapes

Both files are aggregate only: no player, team or match identifier, no name, no row per
player or per match. `null`, never NaN.

**`results.local.json`** (LOCAL; never committed):

| Key | Content |
|---|---|
| `provenance` | `experiment`, `protocol_commit`, `protocol_hash`, `config_hash`, `config` (verbatim), `source_hashes`, `source_hash_policy`, `packages` (python, numpy, pandas, pyarrow), `versions` (reader, crosswalk, inputs, agreement), `data` (section 9), `xt` (per surface: `hash`, `matches`, `moves`, `shots`, `turnovers`, `dropped_nan`, `iterations`), `shot_location_model` (`available`, `version`, `hash`), `seeds`, `crosswalk_digests` (`matches`, `players`), `acceptance_hash`, `tier`, `data_license`, `reuse_disclosure` |
| `gates` | `match_crosswalk`, `data`, `identity_coverage`, `xt_surface`, `shot_location_model`: each `{passed, reason}` |
| `coverage` | per subset: `expected_matches`, `crosswalked_matches`, `rejected` by reason, `swapped_orientation`, `goal_checks`, `team_matches`, player-matches per provider, verified coverage share per provider; overall: sheet players per provider, pair counts by status, `verified_outfield`, `swap_impossible_share`, `cautioned`, `unattributed_wyscout_rows`, players per pool along `exposure_curve_minutes` |
| `cells` | list; one object per graded cell: `quantity`, `level`, `pool`, `reader`, `valuation`, `exposure_minutes`, `units`, `mean_statsbomb`, `mean_wyscout`, `sd_statsbomb`, `sd_wyscout`, `spearman`, `spearman_interval`, `concordance`, `concordance_interval`, `icc_absolute_single`, `bias`, `sd_difference`, `limits`, `relative_bias`, `relative_bias_interval`, `scale_ratio`, `slope`, `exact_share`, `valid_replicates`, `verdict`, `reason` |
| `sensitivities` | list; `label` in `exposure_180`, `exposure_450`, `common_valuation`, `match_cluster`, `position_DF`, `position_MD`, `position_FW`; then `quantity`, `level`, `pool`, `reader`, `units`, `spearman`, `spearman_interval`, `concordance`, `relative_bias`. No verdict |
| `subset_differences` | per quantity, level, reader: `spearman_world_cup_minus_la_liga` with interval |
| `controls` | `positive` (the two cells' verdicts, `passed`); `permuted_link` per quantity and pool: `values`, `point`, `strictly_above_all`, `singleton_players` |
| `identity` | list of blocks from `evaluate_wide_link`, each with `tiers`, `pool`, rates, intervals, outcome counts, `verdict` (pooled blocks only) |
| `divergence` | `families` (per family and pool: events per provider, `count_ratio`, interval, per-team-match median / p10 / p90 per provider); `statsbomb_pass_types`, `statsbomb_shot_types` (shares per pool); `pairing` (per family and pool: events, `pairs`, paired share per provider, `player_agreement`, `completion_agreement`, `goal_agreement`, `key_pass_overlap`, start and end displacement median and p90 in metres, `xt_delta_difference` mean and sd); `clock_offsets` (median, p10, p90, count at a grid edge); `one_sided` counts |
| `admission` | per aggregated quantity: `status`, `reason`, `pooled_verdict`, `la_liga_verdict` |
| `uncertainty_limit`, `product_effect` | fixed strings |

Graded cells: 16 player-match inputs + 14 team quantities + 15 aggregated quantities,
times 3 pools, times 2 readers = 270, at the `regime` valuation. Budget about 450 bytes
per cell and 220 per sensitivity row; the runner fails rather than exceed the ceiling.

**`results.json`** (the only machine-readable file that may be committed):

| Key | Content |
|---|---|
| `provenance` | as above **minus** `data`, `xt`, `seeds`, `shot_location_model` and `crosswalk_digests`; hashes, versions and the verbatim config stay (seeds are inside the config echo) |
| `gates` | `passed` and reason codes |
| `verdicts` | list of `{quantity, level, pool, reader, verdict, reason}` |
| `link_verdicts` | list of `{tiers, verdict}` |
| `controls` | `positive_passed`; per quantity `strictly_above_all` |
| `admission` | per quantity `{status, reason}` |
| `local_results_sha256` | sha256 of the `results.local.json` bytes |
| `statistics` | the string `withheld: LOCAL_LICENSED aggregate, see analysis.md` |
| `attribution` | `attribution_statsbomb`, `attribution_pappalardo` |

`report_tables.md`: the aggregate tables of `analysis.md`, generated from
`results.local.json` so no number is retyped.

## 9. Hash discipline

| Object | Hash |
|---|---|
| `preregistration.md`, `config.json` | `lf_sha256` (CRLF→LF, then sha256). The checkout has `core.autocrlf=true`; a raw-byte hash would not reproduce |
| source files | `lf_sha256`, keys as posix paths relative to the repository root: the six E-11 files of section 0, `galactico/validation/digests.py`, `galactico/models/xt/grid.py`, `galactico/models/xt/__init__.py`, `galactico/identity/resolver.py`, `galactico/providers/base.py`, and the shot-model module when used |
| StatsBomb raw JSON | `folder_manifest` digest per folder (`World_Cup_2018`, `La_Liga_2017_18`, `La_Liga`): byte-exact, because these files never pass through git's line-ending conversion |
| Pappalardo raw JSON | byte-exact sha256 of `players.json`, `matches_World_Cup.json`, `matches_Spain.json` |
| Pappalardo Parquet | content hash, never file bytes (the footer embeds the pandas version): sort by `["game_id", "period", "seconds", "event_id"]` (actions), `["game_id"]` (matches), `["game_id", "player_id"]` (lineups); `sha256(pd.util.hash_pandas_object(frame, index=False).values.tobytes())` |
| surfaces | `sha256(xt.values.tobytes())` |
| crosswalks | `crosswalk_digest`: sha256 of sorted `a|b` lines; local file only |
| `protocol_commit` | the CLI argument, verified against git; never a literal in the source |

## 10. Synthetic test suite

No test reads the real corpus except the one marked `slow`, which is structure only.
Oracles import nothing from the module under test and are written from the definitions
with `itertools`, `fractions.Fraction` and hand numbers. Each rule test set must contain
both the interesting outcome and its opposite.

| File | Tests |
|---|---|
| `test_statsbomb_reader.py` | pass type and shot type read from a hand-built match; events without location kept with NaN; `period_seconds` from the timestamp; regulation clipping with an extra-time spell and a spell starting at 90+2; `started`, `cautioned`, `dismissed`; goalkeeper by modal spell; matches come from the index, not the directory (an extra event file is ignored); a listed match without a file raises; the module passes `check_licensing.check`; `StatsBombProvider.competitions()` is unchanged |
| `test_provider_crosswalk.py` | match: straight and swapped orientation; the same two teams twice on different dates; tolerance edge; ambiguous day rejected; goals disagree rejects only `Regular`; bijection. Sheets: mutual unique maximum; shared surname resolved by full name; shared surname unresolvable stays unverified; mononym; elimination marked not verified; `started` conflict; minutes outside tolerance; dismissal waiver; cross-match contradiction drops all pairs; goalkeeper flag; no function parameter is an event frame. Wide link: tier A; tier B; ambiguity at A does not fall to B; claimed twice; country alias; nationality mismatch; absent partner with a planted namesake; a planted 100-person roster returns the planted recall, false-link and absent-partner rates exactly; Wilson against hand numbers; verdict boundaries. Permutation: no fixed point, deterministic, inside strata, singletons counted |
| `test_provider_inputs.py` | every flag row on a hand-built match per provider; `open_play` and `as_shipped` differ by exactly the injected restarts; kick-off counted as an open-play pass on both sides; channel bands equal `ActionFilter.apply` on `y = 0.00..1.00`; surface equals `experiments.run_external_replication.fit_xt` on the same synthetic Wyscout actions; `xt_delta` raises on NaN; `goal_angle` equals `2·atan((g/2)/d)` on the centre line, 0 on the goal line outside the posts, symmetric in `y`; penalty-area edge; final-third boundary and lanes with the attacker's left at `y = 0`; conceded equals the opponent's mirrored value; unverified and unattributed rows absent at player level and present at team level; regulation filter; clock offset recovers a planted +3.5 s; pairing is one-to-one, respects tolerances, is invariant to row order |
| `test_provider_agreement.py` | `spearman` against a brute-force average-rank oracle including ties; constant vector is NaN; `concordance` on hand numbers, 1 for identical vectors, lower under a shift; `icc_absolute_single` against an explicit two-way ANOVA in `Fraction`; both within the cross-check tolerance for `n >= 50`; Bland–Altman hand numbers; weights: shape, per-subset row sums 64 and 36, determinism; a match weight of 2 equals duplicating the match; a player weight of 2 equals duplicating the player; ratio of sums, not mean of ratios; exposure applied to both providers; a hole stays a hole; the same weight arrays reach every quantity and both providers; row-order invariance; planted generator hits its population Spearman within 0.005 at 200,000 draws |
| `test_provider_agreement_rule.py` | each decision row; lower bound exactly at the threshold is admitted; upper bound exactly at the threshold is `NOT_ESTABLISHED`; bias interval touching the margin passes; NaN concordance falls to row 3; NaN Spearman is `INCONCLUSIVE`; each gate gives its reason code; exhaustive grid: exactly one token from the vocabulary for every combination; every admission row; `la_liga` `INCONCLUSIVE` does not veto; positive-control failure excludes all; a tie with a permuted value fails; a reduced acceptance run (20 corpora, 100 replicates) for the comparable and null scenarios |
| `test_provider_agreement_runner.py` | `execute` refuses without a commit, with a protocol that differs from the commit, without or with a stale or failed acceptance stamp, with an output root outside `data/licensed/`, and on a second execution; end to end on `synthetic_corpus(noise=False)`: every graded `open_play` cell `COMPARABLE` with concordance 1, `as_shipped` pass-count bias exactly the injected restarts, crosswalk complete, wide-link counts as planted; two runs byte-identical; `allow_nan=False`; size ceiling; denylist walk; licence-guard patterns; `results.json` holds no number outside the config echo; no product package imports the five research modules; `@pytest.mark.slow` structure check: both real folders list 64 and 36 matches and `read_wyscout_team_sheets` minutes equal `lineups.parquet` minutes clipped at 90 (skips cleanly when either cache is absent) |

**Acceptance before outcomes** (not a unit test; `acceptance` subcommand): the six
scenarios of section 6 at the stated rates, 200 corpora each. `execute` cannot start
without its stamp. A failed scenario is a defect in the code or in the rule; the rule
is not edited to pass it after the protocol commit.

## 11. Pre-outcome code review checklist

The reviewer signs each line before the root runs `execute`.

1. No function in `provider_crosswalk.py` takes or reads an event frame.
2. `match_links`, `pairs`, sheets and people frames are never written to disk, logged,
   or placed in an exception message.
3. Both providers are filtered to regulation periods before any count; minutes are capped.
4. StatsBomb completion uses absence of an outcome; Wyscout uses `success is True`.
5. `open_play` excludes Corner, Free Kick, Goal Kick and Throw-in passes and includes
   Kick Off; penalties are excluded from `non_penalty_shot` on both sides.
6. `y` is not flipped on either side; the left-lane test would fail if it were.
7. Each provider's events are valued on the surface the protocol names; the `common`
   valuation is never graded.
8. Reference surfaces are fitted before the 100 matches are read and exclude them on
   the Wyscout side; a non-converged surface raises.
9. NaN coordinates never reach `PitchGrid.cells`.
10. Per-90 values divide by the same provider's minutes; the exposure gate is applied to
    both providers; ratio quantities are ratios of sums.
11. One weight matrix per axis, created once, passed everywhere; seeds come from config.
12. Replicates recompute gates; invalid replicates are counted, not replaced.
13. `classify` is the only place a token is produced; comparisons match the protocol;
    NaN never passes.
14. Sensitivities carry no token.
15. The permuted control derives from the verified pairs and cannot return a fixed point
    in a stratum of two or more.
16. Result keys: none from the denylist; `results.json` holds no number outside the
    config echo; both files pass `check_licensing.check`.
17. Hashes use `lf_sha256` for protocol, config and code; Parquet uses content hashes.
18. `protocol_commit` is an argument checked against git; no literal commit in source.
19. Nothing under `galactico/api` or any product package imports these modules;
    `StatsBombProvider` is byte-identical to `HEAD`.
20. The acceptance stamp matches the reviewed source hashes.
21. No real cross-provider statistic was printed, logged or inspected during the build
    (the build report says which real-data commands were run; only `preflight` is allowed).

## 12. Attribution and logo

`analysis.md` (and any `docs/research` report citing an E-11 number) starts with:

```markdown
<img src="../../../docs/assets/statsbomb/statsbomb-logo.png" alt="StatsBomb" width="220">

**Data source: StatsBomb.** This analysis is formed from StatsBomb Open Data and is
published under clause 1.4 of the StatsBomb Public Data User Agreement with the StatsBomb
logo. The conclusions are not the opinions or analytical insights of StatsBomb.
Second source: Pappalardo et al. (2019), Scientific Data 6:236, CC BY 4.0.
```

The logo file is the unmodified image from the StatsBomb media pack linked in the
open-data README, stored at `statsbomb_logo_path`. The report is non-commercial, carries
aggregate tables only, and names no player in connection with a StatsBomb-derived value.
A test (added with `analysis.md`) asserts that any file under the E-11 folder that
mentions a StatsBomb-derived statistic contains the logo reference and the sentence.

## 13. Shared-file requests to the root

| File | Request |
|---|---|
| `experiments/preregistered/README.md` | add `E-11 provider agreement` with status `preregistered, not run` |
| `tests/test_research_firewall.py` | append the five `galactico.validation.*` modules of section 0 to the research-pipeline tuple |
| `docs/assets/statsbomb/statsbomb-logo.png` | add the official logo; also add logo and attribution to `docs/research/STAGE-1C-EXTERNAL-REPLICATION.md` and `docs/research/E-01-metronome-fit.md`, which publish StatsBomb-derived analysis without it today |
| `galactico/providers/statsbomb.py` `MAPPING_AUDIT` | after the run, correct two texts that are wrong regardless of outcome: "completed pass" omits that a StatsBomb Pass includes restarts; "shot" omits that a StatsBomb Shot includes penalties. Root decides whether this counts as shipped behaviour |
| `galactico/domain/verdicts.py` | register E-11 tokens for research readers only (ASSUMED INTERFACE 5) |
| `scripts/fetch_statsbomb.py` | none; the new fetch script stands alone |

## ASSUMED INTERFACES

1. **`galactico/validation/digests.py`** (hardening H1): `lf_sha256(path: Path) -> str`,
   `lf_sha256_text(text: str) -> str`. If absent at build time the E-11 C agent stops and
   reports; it does not write a private copy.
2. **E-09** (candidates): keys `shot_volume` (non-penalty shots per 90, direct free kicks
   included, penalties excluded) and `shot_location_value`. Model interface
   `galactico.models.shots.fit_location_model(shots: pd.DataFrame, config: Mapping) ->
   model` with `model.predict(x: np.ndarray, y: np.ndarray) -> np.ndarray` (unit-square
   shot origin in the attacking frame) and `model.version: str`; E-11 fits it on
   Pappalardo five leagues minus the double-coded matches. If the module or signature
   differs, `shot_location_value` is `INCONCLUSIVE (DEPENDENCY_ABSENT)` and
   `shot_goal_angle_per_90` stands as the location input. E-09's defensive-location
   candidate is assumed to be a function of the defensive-action union and start `x`
   defined here; if E-09 fixes a different union, the reconciler replaces the config
   lists **before** the protocol commit.
3. **E-10** (team descriptors): final-third entry = completed open-play pass crossing
   `x = 2/3`; lanes by thirds of `y`; defensive-action height = mean start `x`; the
   pressure-style ratio as defined in the protocol. Same reconciliation rule.
4. **E-12** reads the committed `results.json` (`admission`, `link_verdicts`) and, being
   LOCAL itself, may read `results.local.json` for the measured link rates and the
   per-quantity Spearman as a provider attenuation factor. It must import
   `read_events`, `harmonise_statsbomb(variant="open_play")`, the surface rule of
   `statsbomb_reference_surface` and `name_nationality_link` from the modules above and
   pin their source hashes. Its StatsBomb arm values each league on a surface fitted by
   that same rule.
5. **`galactico/domain/verdicts.py`**: accepts a record of the form
   `(experiment="E-11", subject=<quantity>, scope=<level/pool/reader>, verdict=<token>,
   protocol_hash=<str>, audience="research")`. No product surface renders an E-11 token.
6. **Research firewall test** (hardening H1) exposes one tuple of research modules that
   new experiments append to.

## DISSENT

1. **R7 as written forbids any committed machine-readable E-11 number, yet
   `experiments/external_replication.json` is tracked today and holds StatsBomb-derived
   reliabilities.** The design obeys R7: statistics stay in `results.local.json`, and the
   committed `results.json` carries tokens and hashes only. Cost: the published numbers
   exist only as Markdown tables, which is weaker for reproducibility than E-07/E-08.
   The licence text permits publishing analysis with the logo (preamble, clause 1.4), so
   R7 is stricter than the licence. The root should either relax R7 for aggregate
   research artifacts under `experiments/`, or apply it to the tracked file too.
2. **"Verified identity crosswalk" overstates what team sheets give.** The link is
   name-based inside a closed pool of about fourteen, with name-free corroboration; there
   is still no birth date. It is named `VERIFIED_BY_TEAM_SHEET`, classed `ESTIMATED`,
   and published with its swap-impossible share.
3. **The 100 matches are not one specification.** All 64 World Cup files are StatsBomb
   `data_version` 1.0.2; the 36 La Liga files and the whole 2015/16 corpus are 1.1.0.
   About nine in ten gated players at the aggregated level come from the older
   specification and from national-team football. The design answers with a La Liga veto
   in the admission rule; it cannot make the World Cup evidence into league evidence.
4. **Match-only resampling, as briefed, understates uncertainty at the player levels**
   (players recur across matches and are the units being ordered). The primary interval
   resamples matches and players; the match-only interval is reported beside it.
5. **Admission at 270 double-coded minutes is a gate on a proxy.** E-12 compares season
   aggregates at 900 minutes or more. Agreement at 270 is a lower bound only if coding
   error is independent across matches; the experiment cannot test that.
