# E-11 pipeline specification

Build target for `experiments/preregistered/E-11-provider-agreement/`. The protocol is
`preregistration.md`; every number is in `config.json`; this file is the code contract.
**It is frozen with them:** it is committed in the registration commit byte for byte as it
stands here, its `lf_sha256` is `pipeline_spec_sha256` in the config, and `execute` refuses
a mismatch. Where this file and
the protocol disagree, the protocol wins and the disagreement is a defect.

**Tier rule (binding on every function below).** E-11 is LOCAL_LICENSED end to end.
Nothing that reads StatsBomb is imported by `galactico/api`, `galactico/optimization`,
`galactico/profiles`, `galactico/match_lab`, `galactico/models` or `galactico/features`.
No crosswalk, per-player row, per-match row, identifier or name is written anywhere except
process memory. The only files the pipeline writes are aggregate JSON and Markdown under
`local_output_root` (gitignored); the fetch script writes the provider's own files and its
manifest under `sb_root` (gitignored), nowhere else. Until the root runs the real
execution, every module is exercised on synthetic data only. `preflight` (section 7) and
`scripts/fetch_statsbomb_double_coded.py` (section 2) are the only real-data entry points
allowed before the protocol commit. Neither joins anything across providers, and the
script reads no event: it writes and hashes files as bytes.

## 0. Files and ownership

| File | New | Owner | Content |
|---|---|---|---|
| `galactico/validation/sb_reader.py` | yes | E-11 A | raw StatsBomb research reader (pass type, shot type, sheets, vocabulary, folder digest). The file is named `sb_` because its path is a key of `source_hashes` in two committed JSON files |
| `galactico/validation/provider_crosswalk.py` | yes | E-11 A | Wyscout sheet reader, match crosswalk, team-sheet crosswalk, wide link, link evaluation |
| `galactico/validation/provider_inputs.py` | yes | E-11 B | harmonised frames, reference surfaces, inputs, event pairing, divergence tables |
| `galactico/validation/provider_agreement.py` | yes | E-11 C | statistics, resampling, decision rule, admission |
| `galactico/validation/provider_agreement_synthetic.py` | yes | E-11 C | planted corpora and the acceptance run |
| `experiments/run_provider_agreement.py` | yes | E-11 C | CLI: `preflight`, `acceptance`, `execute` |
| `scripts/fetch_statsbomb_double_coded.py` | yes | written before registration; root commits it with the registration | reproducible fetch of the two folders from the match index, and a `--check` mode that recomputes the folder digests with no network (section 2) |
| `tests/test_sb_reader.py`, `tests/test_provider_crosswalk.py` | yes | E-11 A | |
| `tests/test_provider_inputs.py` | yes | E-11 B | |
| `tests/test_provider_agreement.py`, `tests/test_provider_agreement_rule.py`, `tests/test_provider_agreement_runner.py` | yes | E-11 C | |
| `experiments/preregistered/E-11-provider-agreement/{preregistration.md,config.json,PIPELINE.md}` | yes | root commits | registered from this folder. `config.json` and `PIPELINE.md` are registered byte for byte. `preregistration.md` is registered after two edits and no other: the DRAFT banner (the one-line block quote under the title, which holds the only relative links) is replaced by the one line `> References such as ROOT 2.5 or R12 point to [ROOT-DECISIONS.md](../../../docs/research/north-star/ROOT-DECISIONS.md); the working notes they cite are described in the [README](../../../docs/research/north-star/README.md) beside it.`, and the logo path becomes `../../../docs/assets/statsbomb/statsbomb-logo.png`. The two values named in `verified_by_root_before_registration` are already in the config: before registering, the root recomputes `lf_sha256` of this file and the three folder digests of section 2 (`scripts/fetch_statsbomb_double_coded.py --check`) and stops if one differs. The registered hashes are of the registered bytes. In the same commit the three files of this draft folder are replaced by one line pointing at the registered directory |
| `experiments/preregistered/E-11-provider-agreement/acceptance.json` | yes | root commits, before `execute` | the synthetic acceptance stamp, committed after the pipeline is built (section 13); no key contains a provider's full name |

Three agents (A, B, C) can build in parallel against the frames fixed in sections 2 to 5.
No existing file is edited by them. Frozen files are untouched. `StatsBombProvider`, its
`SEASONS` tuple and `MAPPING_AUDIT` are not edited: `competitions()` must keep returning
the four 2015/16 leagues, or Stage 1C's runner would silently pick up two more folders.

**Reused, unchanged:**

| Reuse | From |
|---|---|
| `fit_expected_threat`, `PitchGrid`, `ExpectedThreat` | `galactico/models/xt` (frozen) |
| `normalise_name`, `name_tokens` | `galactico/identity/resolver.py`. `resolve_player` is **not** used: it accepts nobody without a birth date |
| `PROVIDERS`, `DataTier`, `assert_may_host`, `LicenseViolation` | `galactico/providers/base.py` |
| `lf_sha256`, `lf_sha256_text` | `galactico/validation/digests.py` |
| `banned_key_paths` | `galactico/domain/thesis.py` |
| channel literals of `half_space_bands`, `wide_below`, `wide_above` | copied into config; a test pins them to `features/spec.py::ActionFilter.apply` |
| `check` | `scripts/check_licensing.py`, called by tests on every new file and on both result files |

Engineering: `from __future__ import annotations`; frozen dataclasses; full type hints;
`__all__`; numpy and pandas only (no scipy); ruff clean; paths anchored at
`Path(__file__).resolve().parents[n]`; module docstring states claim and non-claim. No
function takes a default for a value that is in config (the cap, a threshold, a seed, a
rule switch).
Config keys that restate a protocol rule as a boolean or a sentence (for example
`outfield_only_at_player_levels`, `link_recall_denominator`) are read by assertions, not
by branches: the pipeline asserts the frozen value and implements only that value.

**Licence-guard traps.** Never write, in any committed file, a double-quoted
`possession_team`, `freeze_frame`, `obv_total_net` or `shot_statsbomb_xg`; never a
double-quoted `eventId`, `subEventId`, `matchPeriod` or `tagsList` followed by a colon. The
reader needs none of those fields. No key of `config.json`, `acceptance.json` or
`results.json` contains the substring `statsbomb` in any letter case or starts with `SB_`
(`tests/test_licensing.py` reads the keys of every JSON file under `experiments/`, three
levels deep); hence the `sb_` and `wy_` prefixes and the reader's file name: the keys of
`source_hashes` are source paths, and none of the twelve paths of section 9 holds that
substring. Every test payload is generated by `synthetic_corpus` from a
seed with invented names, ids and coordinates. No literal name, id, event or lineup row
copied from either provider appears in a committed file.

## 1. Data flow

```
StatsBomb raw JSON (LOCAL)                      Pappalardo raw JSON + Parquet (PUBLIC)
  read_matches / read_team_sheets                 read_wyscout_matches / _team_sheets / _people
  folder_vocabulary -> gate                       namesake_collision (Pappalardo alone)
            \                                         /
             crosswalk_matches  ->  match_links (in memory)        [inside execute only]
             team_sheet_crosswalk -> pairs (in memory) -> evaluate_wide_link -> identity block
  read_events                                     actions.parquet (column list)
  harmonise_statsbomb(variant)                    harmonise_wyscout
  statsbomb_reference_surface(variant)            wyscout_reference_surface
            \                                         /
             player_match_inputs / team_match_inputs   (per provider, variant, valuation)
             build_panel -> match, player and team weights -> cell_agreement -> classify
             permuted controls -> admission -> registry verdicts
             difference_decomposition; clock_offsets -> pair_events -> divergence_tables
                         results.local.json  +  results.json (tokens only)  +  report_tables.md
```

## 2. `galactico/validation/sb_reader.py`

Claim: reads fields the shipped adapter drops, for research. Non-claim: it is not a
provider adapter, feeds no product path and changes no shipped number.

```python
READER_VERSION = "statsbomb-research-reader-v2"

def read_matches(root: Path, folder: str) -> tuple[pd.DataFrame, list[int]]
def read_team_sheets(root: Path, folder: str, game_ids: Collection[int], *, cap: int,
                     regulation_periods: Collection[int]) -> pd.DataFrame
def iter_events(root: Path, folder: str,
                game_ids: Collection[int]) -> Iterator[tuple[int, list[dict]]]
def read_events(root: Path, folder: str, game_ids: Collection[int]) -> pd.DataFrame
def folder_vocabulary(root: Path, folder: str) -> dict[str, list[str | None]]
def folder_manifest(root: Path, folder: str) -> dict[str, object]
```

Matches are enumerated from `_matches.json` only, never by listing `events/` (a delisted
file on disk must not become a match). `read_matches` returns the frame of listed matches
whose event and lineup files both exist and the list of listed ids for which one is
absent; nothing raises. The runner drops and counts the absent ones. No function opens a
path under `sb_forbidden_roots`; the runner asserts it.

`read_matches` columns: `sb_game_id` int64, `folder` str, `date` str `YYYY-MM-DD`,
`home_sb_team_id`, `away_sb_team_id` int64, `home_team_name`, `away_team_name` str,
`home_goals`, `away_goals` Int64, `stage` str or None, `data_version` str or None.

`read_team_sheets`: one row per player with at least one position spell whose
`from_period` is a regulation period.

| Column | Rule |
|---|---|
| `sb_game_id`, `sb_team_id`, `sb_player_id` | int64 |
| `player_name`, `player_nickname`, `country` | str; the last two may be None; `country` is `country.name` |
| `started` | any spell with `from_period == 1` and minute field 0 (the shipped rule) |
| `minutes_regulation` | `min(cap, sum(max(0, end − start)))` over regulation spells; `start = min(mm(from), cap)`; `end = min(mm(to), cap)` when `to` exists and `to_period` is a regulation period, else `cap`; `mm` is the integer before the colon. A recorded off-pitch gap is simply the absence of a spell |
| `minute_on`, `minute_off` | smallest `start`, largest `end` |
| `is_goalkeeper` | position of the spell with most regulation minutes equals `sb_goalkeeper_position`; ties go to the earliest spell |
| `cautioned`, `dismissed` | any card; any card whose `card_type` is not in `sheet_minutes_waiver.sb_dismissal_card_types_exclude` |
| `permanent_off` | any spell whose end reason contains `sheet_minutes_waiver.sb_spell_end_reason_contains` |

`read_events`: every event of every requested match, **nothing dropped**.

| Column | dtype | Rule |
|---|---|---|
| `sb_game_id` | int64 | |
| `period` | int8 | raw `period` |
| `period_seconds` | float64 | parsed from `timestamp` (`HH:MM:SS.mmm`), which restarts each period; this is what pairs with Wyscout `seconds` |
| `event_order` | int64 | raw `index` |
| `sb_team_id` | int64 | `team.id` |
| `sb_player_id` | Int64 | `player.id`, NA when absent |
| `kind` | str | `type.name` |
| `start_x`, `start_y` | float64 | `location / (120, 80)`; NaN when absent |
| `end_x`, `end_y` | float64 | `end_location` of the pass, carry or shot detail `/ (120, 80)`; NaN when absent (never a copy of the start) |
| `has_outcome` | bool | the detail object for this `kind` carries an `outcome` |
| `outcome` | str or None | its name |
| `pass_type`, `pass_height` | str or None | `pass.type.name`, `pass.height.name` |
| `pass_cross`, `shot_assist`, `goal_assist` | bool | `pass.cross`, `pass.shot_assist`, `pass.goal_assist` |
| `shot_type`, `duel_type` | str or None | `shot.type.name`, `duel.type.name` |
| `play_pattern` | str or None | `play_pattern.name` |
| `event_id` | str | raw `id`; in memory only |

`folder_vocabulary` returns, with no counts, the sorted distinct names in a folder of
`kind` among all events, of `pass_type` among Pass events, of `shot_type` among Shot
events and of `duel_type` among Duel events; a missing type is None. The runner compares
them with the four `sb_known_*` lists for the two double-coded folders and for
`xt_sb_reference_folder`; a name outside a list in any of the three folders fails the
`UNKNOWN_VOCABULARY` gate.

`folder_manifest` returns `folder`, `event_files`, `lineup_files`, `bytes`,
`data_versions` (count per distinct `metadata` JSON), and `digest`. The digest is fixed to
the byte: one line `<path>:<hash>` for the match index `<folder>/_matches.json` and, for
every match id listed in the index, for `<folder>/events/<id>.json` and
`<folder>/_lineups/<id>.json`, where `<path>` is the posix path relative to `root` (it
starts with the folder name) and `<hash>` is the lower-case hex sha256 of the file's
bytes; a listed file that is absent contributes no line; the lines are sorted as strings
(code-point order), joined with `\n` with no trailing newline and encoded as UTF-8, and
`digest` is the lower-case hex sha256 of those bytes. The three values of
`sb_folder_digests` were computed by this rule from the files on disk before
registration; an implementation that returns anything else for an unchanged folder is
wrong. A sha256 digest of a provider's files is not data and not a table derived from
data: it discloses nothing, it is what pins the inputs of a preregistered experiment, and
the three folder digests of `sb_folder_digests` are therefore committed in `config.json`
(root ruling, 9 October 2026).

`scripts/fetch_statsbomb_double_coded.py` (written before registration, committed with
it): `DOUBLE_CODED = {"World_Cup_2018": (43, 3), "La_Liga_2017_18": (11, 1)}`; same layout
and base URL as `scripts/fetch_statsbomb.py`; ids come from the match index; a folder
whose index does not list `subsets[*].expected_matches` is refused and the exit code is
non-zero; a file already on disk, the index included, is never fetched again and never
rewritten; it merges a `double_coded` block into `MANIFEST.json` without touching
`seasons`. `--check` opens no connection: it recomputes the digest above for every folder
of `sb_folder_digests`, compares the listed matches with `subsets[*].expected_matches`
and `xt_sb_reference_expected_matches`, and exits non-zero on any difference. `--config`
names the config while it is not yet at `committed_experiment_dir`. The script reads no
event and computes no statistic. Not run by tests.

## 3. `galactico/validation/provider_crosswalk.py`

Claim: identity from team sheets alone. Non-claim: no birth date confirms any link; no
event enters any function here (a test asserts no parameter is an event frame).

```python
CROSSWALK_VERSION = "team-sheet-crosswalk-v2"

def read_wyscout_matches(raw_root: Path, competition: str) -> pd.DataFrame
def read_wyscout_team_sheets(raw_root: Path, competition: str,
                             game_ids: Collection[int], *, cap: int) -> pd.DataFrame
def read_wyscout_people(raw_root: Path) -> pd.DataFrame
def crosswalk_matches(sb_matches: pd.DataFrame, wy_matches: pd.DataFrame,
                      wy_teams: pd.DataFrame, config: Mapping[str, object],
                      *, subset: str) -> tuple[pd.DataFrame, dict[str, int]]
def team_sheet_crosswalk(sb_sheets: pd.DataFrame, wy_sheets: pd.DataFrame,
                         wy_people: pd.DataFrame, match_links: pd.DataFrame,
                         config: Mapping[str, object]
                         ) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]
def name_nationality_link(left: pd.DataFrame, right: pd.DataFrame,
                          config: Mapping[str, object], *, tiers: Sequence[str],
                          exclude_right: Mapping[int, int] | None,
                          unique_right: bool) -> pd.DataFrame
def evaluate_wide_link(pairs: pd.DataFrame, sb_people: pd.DataFrame, wy_people: pd.DataFrame,
                       sheet_ids_of_player: Mapping[int, frozenset[int]],
                       subset_of_player: Mapping[int, frozenset[str]],
                       config: Mapping[str, object]) -> list[dict[str, object]]
def namesake_collision(wy_people: pd.DataFrame, config: Mapping[str, object],
                       *, tiers: Sequence[str]) -> dict[str, object]
def wilson_interval(successes: int, trials: int, z: float) -> tuple[float | None, float | None]
def link_verdict(block: Mapping[str, object], failed_gates: Sequence[str],
                 config: Mapping[str, object]) -> tuple[str, str | None]
def permuted_partners(pairs: pd.DataFrame, stratum: pd.Series, config: Mapping[str, object],
                      *, seed: int) -> pd.Series
def crosswalk_digest(frame: pd.DataFrame, columns: Sequence[str]) -> str
```

| Frame | Columns |
|---|---|
| `read_wyscout_matches` | `wy_game_id` int64, `date` str (first ten characters of `dateutc`), `home_wy_team_id`, `away_wy_team_id` int64, `home_goals`, `away_goals` Int64 (from `teamsData[*].score`), `duration` str |
| `read_wyscout_team_sheets` | `wy_game_id`, `wy_team_id`, `wy_player_id` int64, `started` bool, `minutes_regulation` int (starter: `min(off_minute or cap, cap)`; used substitute: `max(0, cap − on_minute)`; a non-list `substitutions` is empty, as in the adapter), `minute_on`, `minute_off` int, `cautioned`, `dismissed` bool (`yellowCards`; `redCards` not equal to `sheet_minutes_waiver.wy_red_cards_not_equal`). Unused substitutes have no row |
| `read_wyscout_people` | `wy_player_id` int64, `full_name` (first plus last name, unicode-unescaped exactly as the adapter does), `short_name`, `birth_area`, `passport_area` str or None, `position` (`role.code2`) |
| `wy_teams` | `teams.parquet`: `team_id`, `team_name` |
| `match_links` | `match_key` int32 (0..M−1, assigned after concatenating subsets in config order, sorted by `wy_game_id`), `subset`, `sb_game_id`, `wy_game_id`, `date`, `swapped` bool, `duration`, `goal_check` in `agree` / `skipped`, `sb_home_team_id`, `sb_away_team_id`, `wy_team_for_sb_home`, `wy_team_for_sb_away` |
| `pairs` | `sb_player_id`, `wy_player_id` int64, `status` in `pair_status_vocabulary`, `sheets_named`, `sheets_together`, `sheets_structure_passed` int, `swap_impossible` bool, `is_goalkeeper` bool |
| `dropped_player_matches` (second return of `team_sheet_crosswalk`) | `match_key`, `sb_player_id`: sheets in which a paired link failed step 3 |

**`crosswalk_matches`.** Candidates for a StatsBomb match: Wyscout matches of the subset
within `match_date_tolerance_days`. Orientation `straight`: `J(home, home)` and
`J(away, away)` both above `match_team_token_overlap_strictly_above`; `swapped`: the cross
pairs. `J` is Jaccard on `name_tokens`. A candidate qualifies in the orientation with the
larger smaller-side overlap; equal overlaps in both orientations disqualify. Exactly one
qualifying candidate, and that candidate chosen by no other StatsBomb match, or the match
is rejected. Then, when `duration` is in `match_require_goal_agreement_durations`, goals
must agree after orientation. Rejection reasons counted: `NO_CANDIDATE`, `AMBIGUOUS`,
`CLAIMED_TWICE`, `GOALS_DISAGREE`. **It runs on real data only inside `execute`.**

**`team_sheet_crosswalk`.** Exactly the protocol's steps. Rows with zero
`minutes_regulation` are filtered here, each sheet by its own minutes (both readers still
return them), and counted. Name
forms: StatsBomb `player_name`, `player_nickname`; Wyscout `full_name`, `short_name`. Per
sheet, loop: compute for each unpaired row its set of maxima above
`sheet_name_overlap_strictly_above` on the other side; take every pair that is a singleton
maximum in both directions; stop when a pass takes none. A taken pair is name-paired iff
the two rows share a token found in no name form of any other row of either filtered
sheet; otherwise that sheet's pair is weak. Link status, first that holds:
`BIJECTION_CONFLICT` (either player appears in pairs of any kind with two partners);
`STRUCTURE_CONFLICT` (`sheets_structure_passed / sheets_together` below
`sheet_structure_pass_share_minimum`); `PAIRED_BY_TEAM_SHEET` (name-paired in at least one
sheet); `NAME_WEAK`; `ELIMINATION_ONLY`. `sheets_together` is the number of linked
team-matches in which both players of the link hold a filtered sheet row, whether or not
the loop or the elimination step paired the two there; step 3 is evaluated on every one of
them, and `sheets_structure_passed` is the number that pass. Step 3 passes in a sheet iff the two `started`
values are equal, the two goalkeeper flags are equal (StatsBomb `is_goalkeeper`; Wyscout
`position` equal to `wy_goalkeeper_position`), and
`abs(minutes_sb − minutes_wy) <= sheet_minutes_tolerance` on the two
`minutes_regulation` values: a difference exactly at the tolerance passes. The minutes
check alone is waived in a sheet when either sheet row has `dismissed` or the StatsBomb
row has `permanent_off`. A sheet in which a paired link fails step 3 goes to
`dropped_player_matches` and drops that one player-match and nothing else of the player
(`sheet_structure_conflict_scope`).
`swap_impossible` is true when, in every sheet the pair shares, the StatsBomb player has
zero overlap with every other Wyscout sheet row and vice versa. The audit dict holds
counts by status, zero-minute rows dropped, player-matches dropped, per-subset coverage
shares on each side (outfield player-matches with regulation minutes that hold a paired
link and were not dropped; outfield per `coverage_outfield_rule`), `swap_impossible_share`,
and the cautioned table (both / StatsBomb only / Wyscout only). Paired outfield = paired
and Wyscout `position` is not `wy_goalkeeper_position`.

**`name_nationality_link`.** `left`: `left_id`, `full_name`, `known_as` (nullable),
`country`. `right`: `right_id`, `full_name`, `countries` (tuple). Returns `left_id`,
`right_id` (Int64, NA when unlinked), `tier`, `outcome` in `LINKED` / `AMBIGUOUS` /
`CLAIMED_TWICE` / `NO_CANDIDATE`. Country comparison: `normalise_name` on both, then
`country_aliases_normalised` on the left; a missing country never agrees. Tiers are tried
in the order given. Tier A candidates: the left `full_name` token set equals the right
`full_name` token set, at least `link_tier_a_minimum_tokens` tokens, nationality agrees.
Tier N: the same with the left `known_as` token set (skipped when `known_as` is null), at
least `link_tier_n_minimum_tokens`. Tier B: one of the left and right `full_name` token
sets strictly contains the other with at least `link_tier_b_minimum_shared_tokens` shared,
nationality agrees. At each tier one candidate links; several are `AMBIGUOUS` and do
**not** fall through; none moves to the next requested tier. `exclude_right` and
`unique_right` are required keywords with no default. With `unique_right` true, any
`right_id` taken by two lefts turns all of them into `CLAIMED_TWICE`;
`evaluate_wide_link` asserts `link_requires_unique_both_directions` and passes true, and
`namesake_collision` passes false, the only call that does. `exclude_right` maps
a `left_id` to one `right_id` hidden from that left only. `short_name` is never read.

**`evaluate_wide_link`.** Left = every StatsBomb sheet player with regulation minutes in a
linked match (goalkeepers included, paired or not); right = all of `read_wyscout_people`.
`sheet_ids_of_player` maps a StatsBomb player to the Wyscout ids on his linked team-match
sheets. For each tier set in `link_tier_sets` and each pool: the class of every left per
the protocol (`link_outcome_classes`); `evaluated`, `paired`, counts by class and by
link outcome; `recall`, `false_link_rate`, `no_link_rate` with `wilson_interval`; the same
on paired players only and split by nickname present or absent; and
`absent_partner_stress_rate`: rerun with `exclude_right = {left: partner}` for paired
lefts (the full run passes `exclude_right=None`), all other lefts keeping their full-run links for the `CLAIMED_TWICE` rule; rate =
still linked / paired. **`namesake_collision`**: left = each Wyscout record with its own
`full_name`, `known_as` null and `country` = its `link_namesake_left_country`; right = all
records, `exclude_right = {id: id}`, `unique_right=False`; `K` = lefts with outcome
`LINKED`, `N` = all records; rate and interval. `link_verdict` applies the protocol table
to the `link_verdict_pool` block with the larger of the two upper bounds; a `None` bound
fails the `LINK_USABLE` row; the reason of an `INCONCLUSIVE` is the first of
`link_inconclusive_reasons` that holds: a gate named in `failed_gates` (data, vocabulary,
match crosswalk, identity coverage), then `EVALUATED_PLAYERS`. When a gate stopped the run
before the link was evaluated, the block is empty and the verdict and reason are still
returned.

**`permuted_partners`.** Paired outfield players only. Inside each stratum (sorted ids),
shuffle with `default_rng(SeedSequence([config["seed"],
config["seed_streams"]["permuted_link"], seed]))`, then give each player the Wyscout
partner of the next player cyclically. No fixed point when the stratum has two or more
members; singletons are returned unchanged and counted.

## 4. `galactico/validation/provider_inputs.py`

Claim: one definition per quantity, applied to both providers after an explicit family
mapping. Non-claim: equal names do not make the two event streams the same observation.

```python
INPUTS_VERSION = "provider-inputs-v2"
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
def in_penalty_area(x: np.ndarray, y: np.ndarray, box: Mapping[str, float]) -> np.ndarray
def sheet_minutes(sheets: pd.DataFrame, match_links: pd.DataFrame, pairs: pd.DataFrame,
                  dropped: pd.DataFrame, *, provider: str) -> pd.DataFrame
def player_match_inputs(frame: pd.DataFrame, minutes: pd.DataFrame, xt: ExpectedThreat,
                        config: Mapping[str, object]) -> pd.DataFrame
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
| `player_key` | Wyscout player id of the paired link, Int64, NA when unattributed or unpaired |
| `start_x`, `start_y`, `end_x`, `end_y` | unit square of the provider's own drawing, acting team's attacking frame, `y = 0` the attacker's left. StatsBomb NaN stays NaN. A Wyscout start in `wy_location_sentinels` sets all four to NaN; a Wyscout end in it sets the two end columns to NaN |
| flags | below |

| Flag | Wyscout (neutral Parquet) | StatsBomb `open_play` | StatsBomb `as_shipped` |
|---|---|---|---|
| `open_play_pass` | `type == "pass"` | `kind == "Pass"` and `pass_type` in `sb_open_play_pass_types` | `kind == "Pass"`, location and player present |
| `completed` | `open_play_pass` and `success` is True | `open_play_pass` and not `has_outcome` | same on its own pass set |
| `key_pass` | `completed` and `key_pass` | `completed` and (`shot_assist` or `goal_assist`) | same |
| `key_pass_assist_inclusive` | `completed` and (`key_pass` or `assist`) | as `key_pass` | same |
| `corner`, `free_kick_pass`, `throw_in`, `goal_kick` | `type == "set_piece"` and `subtype` in `wy_corner_subtypes`, `wy_free_kick_pass_subtypes`, `wy_throw_in_subtypes`, `wy_goal_kick_subtypes` | `kind == "Pass"` and `pass_type` in `sb_corner_pass_types`, `sb_free_kick_pass_types`, `sb_throw_in_pass_types`, `sb_goal_kick_pass_types` | same |
| `open_play_shot` | `type == "shot"` | Shot with `shot_type` in `sb_open_play_shot_types` | every Shot with location and player |
| `free_kick_shot`, `penalty` | `type == "set_piece"` and `subtype` in `wy_free_kick_shot_subtypes`, `wy_penalty_subtypes` | Shot with `shot_type` in `sb_free_kick_shot_types`, `sb_penalty_shot_types` | same |
| `non_penalty_shot` | `open_play_shot` or `free_kick_shot` | Shot with `shot_type` in `sb_non_penalty_shot_types` | every Shot with location and player |
| `goal` | shot family and `goal` | Shot and `outcome == "Goal"` | same |
| `ground_duel` | `duel` with subtype in `wy_ground_duel_subtypes` | Duel with `duel_type` in `sb_ground_duel_types`, or `kind` in `sb_ground_duel_kinds` | same |
| `interception` | `interception` column True | `kind` in `sb_interception_kinds`, or Pass with `pass_type` in `sb_interception_pass_types` | same |
| `foul` | `foul` with subtype in `wy_foul_subtypes` | `kind` in `sb_foul_kinds` | same |
| `duel_or_interception` | `ground_duel` or `interception` | same | same |
| `defensive_action` | `duel_or_interception` or `foul` | same | same |
| `clearance` (purpose c only) | `touch` with subtype in `wy_clearance_subtypes` | `kind` in `sb_clearance_kinds` | same |
| `turnover` | failed `pass`, or `dangerous_loss` | failed open-play pass, or `kind` in `sb_turnover_kinds` | failed Pass, or the same kinds |

Wyscout frames are read from `competition=World_Cup/actions.parquet` and
`competition=Spain/actions.parquet` with a column list, filtered to linked matches, and
checked for `provider == {"pappalardo"}`. Never `pd.read_parquet` on the directory.

**Surfaces.** Both call `fit_expected_threat(move_start, move_end, shot_start, shot_goal,
turnover_start, grid=PitchGrid(*xt_grid), max_iterations=xt_max_iterations,
tolerance=xt_tolerance)` with moves =
`completed` rows, shots = `open_play_shot` rows (`shot_goal` = `goal`), turnovers =
`turnover` rows; a surface that did not converge or is not finite raises `ValueError` (the
runner maps it to the `XT_SURFACE` gate). `wyscout_reference_surface` raises unless the
Spain frame holds `xt_wy_reference_expected_matches` distinct matches, then uses that
frame minus the linked La Liga matches. `statsbomb_reference_surface` streams
`iter_events(root, xt_sb_reference_folder, ...)` file by file, keeps only the coordinate
arrays, raises unless `xt_sb_reference_expected_matches` matches are present, and applies
the flag rules of the requested variant. A row is dropped from one fit input, and counted,
only when a coordinate that input reads is NaN: a move reads start and end, a shot and a
turnover read the start only. A missing or sentinel end never removes a turnover.
`xt_delta` returns `values[cells(end)] − values[cells(start)]` and is NaN
where a coordinate is NaN; such rows are excluded from xT sums and counted
(`PitchGrid.cells` never receives NaN).

**Geometry.** `X = (1 − x) · pitch_length_m`, `Y = (y − 0.5) · pitch_width_m`,
`g = goal_width_m`. `goal_angle = arctan2(g·X, X² + Y² − (g/2)²)`, plus π where negative.
`in_penalty_area(x, y, box)`: `x >= box.min_x` and `box.min_y <= y <= box.max_y`, with
`penalty_area_wy` for Wyscout rows and `penalty_area_sb` for StatsBomb rows; NaN is
outside. Half-space: `lo <= y <= hi` for a band of `half_space_bands`; wide:
`y < wide_below` or `y > wide_above`. Lanes: left `y < 1/3`, right `y > 2/3`, centre
otherwise (exact fractions of `lane_y_edge_fractions`). Thirds of the pitch: own
`x < 1/3`, opposition `x >= 2/3`, middle otherwise. Opponent half:
`x > opponent_half_x_minimum_exclusive`. A NaN coordinate is in no band, lane, third, half
or area: such a row is excluded before the test, never sent to an "otherwise" branch.

**`sheet_minutes`** returns `match_key`, `subset`, `player_key`, `team_key`,
`minutes_regulation` for paired outfield players with a sheet row on that provider, minus
the `dropped` player-matches.

**`player_match_inputs`** returns one row per row of `minutes`: `match_key`, `subset`,
`player_key`, `team_key`, then every key of config `player_match_inputs` as float64, `0.0`
where the player has no qualifying event. Unattributed and unpaired rows contribute
nothing. A row without the location a quantity needs is left out of that quantity only.
The fifteen keys, each a count of rows or a sum over rows of the harmonised frame:

| Input key | Rows | Value |
|---|---|---|
| `minutes_regulation` | none | copied from `minutes` |
| `open_play_passes_attempted` | `open_play_pass` | count |
| `open_play_passes_completed` | `completed` | count |
| `positive_xt_gain_completed_passes` | `completed`, finite `xt_delta` | sum of `max(0, xt_delta)` |
| `xt_delta_key_passes` | `key_pass`, finite `xt_delta` | sum of `xt_delta` |
| `xt_delta_key_passes_assist_inclusive` | `key_pass_assist_inclusive`, finite `xt_delta` | sum of `xt_delta` |
| `key_passes` | `key_pass` | count; never `key_pass_assist_inclusive` |
| `completed_passes_from_half_space` | `completed`, finite start `y` inside a band of `half_space_bands` | count |
| `completed_passes_from_wide` | `completed`, finite start `y` below `wide_below` or above `wide_above` | count |
| `non_penalty_shots` | `non_penalty_shot` | count |
| `open_play_shots` | `open_play_shot` | count |
| `open_play_shots_in_penalty_area` | `open_play_shot` with a start inside the provider's own penalty area | count |
| `shot_goal_angle_sum` | `non_penalty_shot`, finite start | sum of `goal_angle` |
| `defensive_actions` | `defensive_action` | count |
| `opp_half_duel_or_interception` | `duel_or_interception`, finite start `x` above `opponent_half_x_minimum_exclusive` | count |

**`team_match_inputs`** returns one row per (`match_key`, `team_key`): `match_key`,
`subset`, `team_key`, every count and sum of config `team_match_quantities` (a key it
shares with `player_match_inputs` has the rows and value of the table above;
`final_third_entries` with its three lanes and `box_entry_passes` count `completed` rows
with a finite start and end; the three `defensive_actions_*_third` keys count
`defensive_action` rows with a finite start), plus the
helper columns `final_third_entries_wide` (left plus right), `high_defensive_actions` and
`high_defensive_actions_plus_opponent_build_up_passes`. All rows of the team count,
attributed or not. Opponent build-up passes are taken from the other team of the same
match.

**Event pairing (purpose c).** The frame `sb` passed to `clock_offsets`, `pair_events` and
`divergence_tables` is the harmonised StatsBomb frame of `divergence_reader_variant`;
`sb_events` is the raw event frame, from which Pass and Shot events are counted by type.
`clock_offsets`: per (`match_key`, `period`), the value in
`arange(lo, hi + step, step)` of `pair_offset_grid_seconds` maximising the number of
StatsBomb `open_play_pass` rows with at least one same-team Wyscout `open_play_pass` row
within `pair_offset_match_window_seconds` of `seconds_sb + offset`; ties to the smallest
absolute value, then the negative. `pair_events` returns `match_key`, `period`, `sb_row`,
`wy_row`, `time_gap`, `start_distance_m`: candidates share match, period and team, satisfy
the family's tolerances, and are taken greedily in ascending (`|time_gap|`,
`start_distance_m`, `sb event_order`, `wy event_order`), each row at most once. Distances
use `pitch_length_m` × `pitch_width_m`. `divergence_tables` returns the `divergence` block
of section 8; the runner strips nothing from it, so it must already be aggregate.

## 5. `galactico/validation/provider_agreement.py`

Claim: agreement statistics and a frozen rule that maps every outcome to one token.
Non-claim: a token is about two coders of the same matches, not about football.

```python
AGREEMENT_VERSION = "provider-agreement-v2"

@dataclass(frozen=True)
class InputPanel:
    players: np.ndarray            # (P,) player keys ascending; process memory only
    matches: np.ndarray            # (M,) match keys ascending
    subset_of_match: np.ndarray    # (M,) str
    team_of_player_match: np.ndarray   # (P, M) Wyscout team id, 0 where absent
    role_of_player: np.ndarray     # (P,) Wyscout role code
    present: np.ndarray            # (P, M) bool: a sheet_minutes row with the frozen minimum regulation minutes on BOTH providers
    values: Mapping[str, np.ndarray]   # input key -> (P, M) float64; 0.0 where not present, minutes_regulation included

@dataclass(frozen=True)
class BlandAltman:
    bias: float; sd: float; lower: float; upper: float
    relative_bias: float; scale_ratio: float; slope: float

@dataclass(frozen=True)
class Agreement:
    units: int
    strata_retained: tuple[str, ...]; strata_dropped: tuple[str, ...]
    mean_statsbomb: float; mean_wyscout: float; sd_statsbomb: float; sd_wyscout: float
    order: float; spearman_unstratified: float
    concordance: float; icc_absolute_single: float
    bland_altman: BlandAltman
    exact_share: float | None

@dataclass(frozen=True)
class CellResult:
    quantity: str; level: str; pool: str; reader: str; valuation: str; exposure_minutes: int | None
    point: Agreement | None
    order_interval: tuple[float, float] | None
    concordance_interval: tuple[float, float] | None
    relative_bias_interval: tuple[float, float] | None
    replicate_mean_minus_point: float | None
    concordance_cross_check_gap: bool | None   # results.local.json only; not a flag
    valid_replicates: int
    verdict: str | None            # None for an ungraded sensitivity
    reason: str | None
    flags: tuple[str, ...]

def build_panel(...) -> InputPanel
def cluster_of_player(panel: InputPanel, minutes_wyscout: np.ndarray, *, pool: str) -> np.ndarray
def stratified_rank_correlation(x: np.ndarray, y: np.ndarray, strata: np.ndarray,
                                weights: np.ndarray | None, config: Mapping[str, object],
                                *, minimum_stratum_units: int | None
                                ) -> tuple[float, tuple[str, ...], tuple[str, ...]]
def concordance(x: np.ndarray, y: np.ndarray, weights: np.ndarray | None = None) -> float
def icc_absolute_single(x: np.ndarray, y: np.ndarray) -> float
def bland_altman(statsbomb: np.ndarray, wyscout: np.ndarray, z: float) -> BlandAltman
def match_weights(subset_of_match: np.ndarray, config: Mapping[str, object]) -> np.ndarray
def player_weights(players: int, config: Mapping[str, object]) -> np.ndarray
def team_weights(teams: np.ndarray, subset_of_team: np.ndarray,
                 config: Mapping[str, object]) -> np.ndarray
def aggregated_values(panel: InputPanel, quantity: Mapping[str, object],
                      config: Mapping[str, object], *, pool: str, exposure: int,
                      match_weight: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]
def cell_agreement(statsbomb, wyscout, quantity: Mapping[str, object],
                   config: Mapping[str, object], *, level: str, pool: str, reader: str,
                   valuation: str, scheme: str, weights: Mapping[str, np.ndarray],
                   exposure: int | None, graded: bool,
                   failed_gates: Sequence[str] = ()) -> CellResult
def classify(*, failed_gates: Sequence[str], units: int, minimum_units: int,
             strata_defined: bool, strata_retained: int,
             nonzero_statsbomb: int, nonzero_wyscout: int, nonzero_both: int,
             constant_statsbomb: bool, constant_wyscout: bool, valid_share: float,
             order_point: float, order_interval: tuple[float, float] | None,
             concordance_interval: tuple[float, float] | None,
             relative_bias_interval: tuple[float, float] | None,
             config: Mapping[str, object]) -> tuple[str, str | None, tuple[str, ...]]
def permuted_link_control(statsbomb: InputPanel, wyscout: InputPanel,
                          quantity: Mapping[str, object], pairs: pd.DataFrame,
                          config: Mapping[str, object]) -> dict[str, object]
def difference_decomposition(statsbomb: InputPanel, wyscout: InputPanel,
                             quantity: Mapping[str, object], team_weight: np.ndarray,
                             config: Mapping[str, object], *, pool: str) -> dict[str, object]
def admission(cells: Sequence[CellResult], controls: Mapping[str, object],
              config: Mapping[str, object]) -> dict[str, dict[str, str | None]]
def registry_verdicts(cells: Sequence[CellResult], controls: Mapping[str, object],
                      link_blocks: Sequence[Mapping[str, object]],
                      config: Mapping[str, object]) -> dict[str, dict[str, str | None]]
```

| Function | Exact definition |
|---|---|
| `cluster_of_player` | the team with most Wyscout regulation minutes over the pool's matches; ties to the smallest Wyscout team id. A team's subset block is the subset whose matches it plays |
| `stratified_rank_correlation` | among finite pairs: strata with fewer than `minimum_stratum_units` units are dropped (never when `strata` is constant or the minimum is None); inside each retained stratum, per side, weighted average ranks (`rank_i = Σ w_j[x_j < x_i] + (Σ w_j[x_j = x_i] + 1)/2`, unit weights when `weights` is None) give `u = (rank − fractional_rank_offset) / Σw`; result = weighted Pearson correlation of `(u_x, u_y)` over retained strata. NaN when fewer than `order_statistic_minimum_units` units, when either pooled `u` vector is constant, or when strata are defined and fewer than `minimum_rank_strata` remain. With one stratum and unit weights it equals Spearman on average ranks |
| `concordance` | `2·s_xy / (s_x² + s_y² + (mean_x − mean_y)²)`, moments with `1/n` (weighted when given). NaN when the denominator is 0 |
| `icc_absolute_single` | two-way random, absolute agreement, single measure, `k = 2`: `(MSR − MSE) / (MSR + (k − 1)·MSE + k·(MSC − MSE)/n)` |
| `bland_altman` | `d = statsbomb − wyscout`; `bias = mean(d)`; `sd` with `ddof = 1`; limits `bias ± z·sd`; `relative_bias = bias / ((mean_sb + mean_wy)/2)`, NaN when that mean is not strictly positive; `scale_ratio = sd_sb / sd_wy`; `slope` = least-squares slope of `d` on `(sb + wy)/2` |
| `match_weights` | `(B, M)` int16, `B = bootstrap_replicates`. `rng = default_rng(SeedSequence([seed, seed_streams.match_weights]))`; for each subset in config order, `rng.multinomial(m, [1/m]*m, size=B)` written into that subset's columns, `m` = its crosswalked matches |
| `player_weights` | `(B, P)` int16 from `default_rng(SeedSequence([seed, seed_streams.player_weights])).multinomial(P, [1/P]*P, size=B)`; `P` = all paired outfield players, canonical order |
| `team_weights` | `(B, T)` int16 from `default_rng(SeedSequence([seed, seed_streams.team_weights]))`; teams in ascending Wyscout id; for each subset block in config order, `rng.multinomial(t, [1/t]*t, size=B)` written into that block's columns |
| `aggregated_values` | pool restricts the match axis. A player is aggregated over his present cells only, the same player-matches on both providers, minutes included, as the protocol's level table says. `num = values[numerator] @ w`, `den = values[denominator] @ w`, minutes likewise, `w` all ones unless `match_weight` is given (the sensitivity scheme only). `defined` requires minutes at or above `exposure` and, when the quantity has one, `den >= minimum_denominator`; the caller requires `defined` on **both** providers. `value = scale · num / den` |
| `cell_agreement` | point estimate with unit weights. Replicate `b` by `scheme`: `team_cluster_fixed_cohort` (aggregated primary): units and values as in the point estimate, unit weight `team_weight[b, cluster_of_player]`; `pigeonhole_match_by_player`: at `player_match`, present cells weighted `match_weight[b, m] · player_weight[b, p]`; at the aggregated level (sensitivity), `aggregated_values` with `match_weight[b]`, gates recomputed, weight `player_weight[b, p]`; `match_cluster`: team-matches (or present cells, sensitivity) weighted `match_weight[b, m]`. Ranks, strata totals and moments are recomputed with the weights; the set of retained strata is fixed by the point estimate. A retained stratum with zero total weight in a replicate contributes no unit; the replicate is valid if the statistic is defined on the rest (`minimum_rank_strata`, like the retained set, is a rule of the point estimate and is not applied again inside a replicate). A replicate is invalid when the order statistic is NaN in it. Intervals = `np.quantile(method=interval_quantile_method)` of valid replicates at `interval_quantiles` for the order statistic, concordance and relative bias; `replicate_mean_minus_point` for the order statistic. `concordance_cross_check_gap` is `abs(concordance − icc_absolute_single) > ccc_icc_cross_check_tolerance` at the point estimate, `None` when either is NaN; it is written to `results.local.json` only. Level statistics use all units; the order statistic uses the retained strata. Strata per `rank_strata`; minimum per `minimum_units_per_rank_stratum[level][pool]`, which is null exactly where `rank_strata` defines no strata |
| `classify` | protocol decision table, rows 1 to 5 in order. Row 1 returns the first reason of `inconclusive_reason_precedence` that holds, gates from `failed_gates`. The runner passes a cell only the failed gates that apply to it: a gate that stopped the run to every cell, `IDENTITY_COVERAGE` to the two player levels, `XT_SURFACE` to inputs of kind `xt_sum` and to aggregated quantities whose numerator is one. `ONE_SIDED`: exactly one side has no non-zero unit while the other has at least `minimum_units_nonzero_on_both_providers` non-zero units. `DEGENERATE`: otherwise, a side that is constant over all units of the cell (a side that is constant and non-zero included), or `nonzero_both` below that minimum. Comparisons: `>=` for lower bounds and the point in rows 2 and 3, `<` for both in row 4, inclusive for the bias margin. Any NaN bound in row 2 fails row 2 only. Flag `POINT_OUTSIDE_INTERVAL` when the order-statistic point is outside its interval (`point < L` or `point > U`); the flag is set after the token is chosen and changes no token |
| `permuted_link_control` | for each seed in `permuted_link_seeds`, re-index the Wyscout panel through `permuted_partners` (stratum = `cluster_of_player` × role, pool `permuted_link_pool`) and return the order-statistic point value; output `values` (sorted), `point`, `strictly_above_all`, `singleton_players` |
| `difference_decomposition` | quantities whose denominator is `minutes_regulation`. Rows: present cells with at least `difference_decomposition_minimum_minutes` on both providers, of players with at least `difference_decomposition_minimum_matches` such rows; `d = scale·(num_sb/min_sb − num_wy/min_wy)`. One-way random effects, unbalanced: `n0 = (N − Σn_i²/N)/(k − 1)`, `var_between = max(0, (MSB − MSW)/n0)`, `share = var_between / (var_between + MSW)`; interval from the team weights. No verdict |
| `admission` | protocol admission table from `admission_rule`, for every key of `aggregated_player_quantities`. Value `{status, reason, pooled_verdict, la_liga_verdict}`; `reason` is the first of `exclusion_reason_precedence` that holds, else null |
| `registry_verdicts` | `{subject: {token, reason, second_reason}}`. A cell subject follows the protocol's registry rule (`registry_token_rule`), rows a to c in order, first match wins, with `H` the verdict of its `registry_headline_cell` and `S` the verdict of the cell of the same quantity, level, reader and valuation in `la_liga_pool`. Row a: when `controls.positive_passed` is false or `controls.permuted_link_passed` is false, every cell subject takes `row_a_control_failed.token`, the first code of its `reason_precedence` whose control failed, and a null `second_reason`. Row b: `H` in `agreeing_tokens` and `S` in `row_b_la_liga_contradicts.la_liga_tokens` gives that row's `token` and `reason`, `second_reason` null. Row c: `token` is `H`, `reason` is the headline cell's reason, and `second_reason` is `row_c_headline_token.second_reason` when `H` is in `agreeing_tokens` and `S` is in its `second_reason_la_liga_tokens`, else null. `positive_passed` is false iff a cell of `positive_controls` has a verdict outside `positive_control_passing_tokens`, which a run stopped by a gate always gives. `permuted_link_passed` is null when no subject of `registry_cell_subjects` has `H` in `agreeing_tokens`: the control then tested nothing, a control that tested nothing is not recorded as passed, and no agreeing registry token exists for it to protect. Otherwise it is false iff `strictly_above_all` is not true for at least one such subject, and true when it is true for every one. Null does not trigger row a. A link subject takes the verdict and reason of `link_verdict` for its tier set, with a null `second_reason`; no control enters it. Every `reason` and `second_reason` written is null or a code of `registry_reason_vocabulary`, of `inconclusive_reason_precedence` (row c of a cell subject) or of `link_inconclusive_reasons` (a link subject), and the function asserts it. This function is the only place a registry token is produced |

Shared worlds: the runner creates the three weight arrays once and passes the same arrays
to every cell. Replicate `b` is one world for all quantities, providers, variants,
valuations and pools. The departure from R12 at the aggregated level is declared in the
protocol and accepted by the root (DISSENT 5).

## 6. `galactico/validation/provider_agreement_synthetic.py`

```python
def planted_corpus(seed: Sequence[int], scenario: Mapping[str, object], coder_error: str,
                   config: Mapping[str, object]) -> tuple[InputPanel, InputPanel, dict[str, object]]
def population_value(scenario: Mapping[str, object], coder_error: str,
                     config: Mapping[str, object]) -> float
def run_acceptance(config: Mapping[str, object]) -> dict[str, object]
def synthetic_corpus(root: Path, *, seed: int, matches: Sequence[int] = (6, 4),
                     restarts_per_match: int = 5, noise: bool = False) -> dict[str, object]
```

`planted_corpus` (`acceptance_generator`; a scenario key overrides the generator key of the
same name). Stated so an oracle can be written without reading the code:

1. **Teams.** Tournament block: `tournament_groups × tournament_teams_per_group` teams.
   Club block (unless the scenario sets `club_block` false): one common team and
   `club_block_opponents` opponents. Each team has `squad_outfield_by_role` players; its
   first ten are the first `first_ten_by_role` of each role.
2. **Schedule.** Each group plays a single round robin. Two teams per group, drawn
   uniformly and independently of every value, advance; they are shuffled and play single
   elimination with a uniformly drawn winner, plus a third-place match between the losing
   semi-finalists. The common team meets every opponent twice, except
   `club_block_opponents_met_once` uniformly drawn opponents, whom it meets once. With the
   default keys this is `subsets[*].expected_matches`.
3. **Minutes, per team-match, equal on both providers.** For each first-ten slot, with
   probability `rotation_probability`, a uniformly drawn unselected reserve of the same
   role starts instead (the regular starts if none is left). Starters get 90.
   `substitutions_per_team_match` distinct starters, drawn uniformly, are each replaced at
   an integer minute uniform on `substitution_minute_range` inclusive by a uniformly drawn
   unselected squad player of the same role, or of any role if none is left; the replaced
   player gets that minute and the entrant 90 minus it. This gives players exactly on the
   gate, players below it and unused players.
4. **Truth.** Per-90 rate of a player in a team-match = `role_means_per_90[role]` +
   ability `N(0, sd_ability)` per player + `N(0, sd_team)` per team + `N(0, sd_team_match)`
   per team-match + `N(0, sd_player_match_at_90 · sqrt(90/minutes))` per player-match.
5. **Coder error,** drawn independently for each provider. `independent`:
   `N(0, coder_sd · sqrt(90/minutes))` per player-match. `systematic`: `N(0, coder_sd)`
   per player, the same in all his matches. `team_match`: `N(0, coder_sd)` per team-match,
   shared by the team's players.
6. **Numerators.** StatsBomb `(rate + error_sb) · minutes/90`; Wyscout
   `wy_scale · (rate + error_wy) · minutes/90` (`wy_scale` 1 unless the scenario sets it).
   With `independent_truths`, the Wyscout side uses a second, independent draw of step 4.
7. **Count family** (`count_family` true): role means are
   `acceptance_generator.count_family.role_means_per_90` and each of the four standard
   deviations is multiplied by its `sd_scale`; no coder error of step 5; true count
   `N ~ Poisson(max(rate, 0) · minutes/90)`; StatsBomb records `N`; Wyscout records
   `Binomial(N, 1 − miss_probability) + Poisson(miss_probability · max(rate, 0) ·
   minutes/90)`.
8. The quantity is `planted_rate` = 90 × numerator / minutes, graded at
   `aggregated_player` in the scenario's `pool` (`la_liga` = the club block) under that
   pool's `exposure_minimum_minutes`, `minimum_units` and stratum minimum, with a
   player's team as his cluster.

`population_value`: the stratified rank correlation on the union of the gated units of
`acceptance_population_corpora` corpora, ranks within role over the union. It is recorded
in `acceptance.json` and must lie within `acceptance_population_tolerance` of the
scenario's `target` unless the scenario sets `population_check` false.

`run_acceptance`: for each scenario and each coder-error structure it names (the keys of
`coder_sd`; the count family has one), `acceptance_corpora` corpora (seeds
`SeedSequence([acceptance_seed, seed_streams.acceptance, scenario_index, structure_index,
corpus_index])`), each graded through the **same** `cell_agreement` and `classify` as the
real run with `acceptance_bootstrap_replicates` replicates. Per scenario and structure it
records the token shares, the share of corpora whose point estimate lies inside its
interval, the mean of `replicate_mean_minus_point`, the mean unit count, the population
value, and `passed`. A share requirement is a number, or a map by structure where the
structures differ. Requirements: `required_tokens` together reach `minimum_share`;
`forbidden_tokens` never occur; `limited_tokens` together stay at or below
`maximum_share` (likewise `second_*`); `point_inside_interval_minimum_share`;
`report_only` scenarios require only the population check. Overall `passed` is the
conjunction.

| Scenario | Planted | Must hold |
|---|---|---|
| `planted_comparable` | agreement 0.95, three structures | `COMPARABLE`; point inside its interval |
| `planted_power_090`, `planted_power_085` | 0.90 and 0.85, three structures | an admitted token at the stated share at 0.90; 0.85 reported |
| `planted_boundary`, `planted_below_boundary` | exactly at and just below the threshold, three structures | admitted tokens and `NOT_COMPARABLE` bounded |
| `planted_moderate`, `planted_null` | 0.60; unrelated truths | `NOT_COMPARABLE`; no admitted token ever |
| `planted_order_only`, `planted_level_boundary` | 0.95 with a level shift; relative bias exactly on the margin | rank-only; `COMPARABLE` bounded |
| `planted_position_mix` | within-role 0.60, role means two within-role standard deviations apart | no admitted token ever |
| `planted_count_boundary`, `planted_count_power_090` | zero-inflated counts with ties | admitted tokens bounded; reported |
| `planted_gate` | a two-group tournament, no club block | `INCONCLUSIVE` always |
| `la_liga_veto_*`, `la_liga_false_veto_090` | the club block alone at 0.60, 0.70, 0.75; at 0.90. The generated block holds about 88 gated players and 18 forwards, more than the real cell can (the protocol's structural counts) | veto power reported; false veto bounded, never `INCONCLUSIVE` |

`synthetic_corpus` writes StatsBomb-shaped folders and Pappalardo-shaped raw JSON and
Parquet under a temporary `root` for end-to-end tests: a known truth event list per match,
both providers derived from it, all names, ids and coordinates invented. With
`noise=False` the Wyscout view is an exact re-encoding of the StatsBomb view except that
`restarts_per_match` set-piece passes are typed as restarts on both sides (so `as_shipped`
over-counts StatsBomb passes by exactly that number per team-match and `open_play` does
not), names appear in different forms, one team sheet holds two players sharing a surname,
one holds two players sharing only a given name, one match has swapped orientation, one
player is dismissed, one has a zero-minute sheet row, and one match goes to extra time.

## 7. `experiments/run_provider_agreement.py`

```python
def preflight(config: Mapping[str, object]) -> dict[str, object]
def acceptance(config: Mapping[str, object]) -> dict[str, object]
def run(config: Mapping[str, object], *, protocol_commit: str) -> tuple[dict, dict, str]
def main(argv: Sequence[str] | None = None) -> int
```

| Subcommand | Reads | Writes | Allowed before the protocol commit |
|---|---|---|---|
| `preflight` | per provider, in separate function calls: file presence, JSON key sets, `folder_manifest`, `folder_vocabulary`, per-provider match and sheet counts. Nothing is joined across providers; the match crosswalk is not run | stdout: counts, the three folder digests, vocabulary names without counts | yes |
| `acceptance` | nothing real | `<local_output_root>/acceptance.json`: per scenario and structure the record of section 6, `passed`, config hash, pipeline hash, source hashes | yes |
| `execute --protocol-commit <sha>` | everything | `results.local.json`, `results.json`, `report_tables.md` in `<local_output_root>` | **no** |
| `execute --protocol-commit <sha> --verify` | everything | `determinism.json` only; exit 1 unless the recomputed `results.local.json` bytes equal the file on disk | no |

`execute` refuses, exit 2 with a one-line reason, unless all hold:

1. `git` is available; `<sha>` is a commit and an ancestor of `HEAD`; for each of
   `preregistration.md`, `config.json` and `PIPELINE.md` under `committed_experiment_dir`,
   `<sha>` is the last line of `git log --diff-filter=A --format=%H -- <path>`,
   `git log <sha>..HEAD -- <path>` is empty, and `lf_sha256` of the working file equals
   that of `git show <sha>:<path>`. Read-only git only. No git, no run (fail closed).
2. `pipeline_spec_sha256` equals `lf_sha256` of the registered `PIPELINE.md`, and every
   value of `sb_folder_digests` equals the `folder_manifest` digest of that folder. A null
   value refuses.
3. The committed `acceptance.json` exists and equals the local one under `lf_sha256`,
   `passed` is true, and its config, pipeline and source hashes equal the current ones.
4. `local_output_root` resolves under `data/licensed/` and `PROVIDERS["statsbomb"].tier` is
   `LOCAL_LICENSED`. `assert_may_host("pappalardo")` is called before any public read.
5. No path under `sb_forbidden_roots` is opened.
6. Without `--verify`, `results.local.json` does not exist (one execution). If
   `failed_runs.json` exists, the committed `analysis.md` must contain the sha256 of its
   bytes: every failure is on the record before the next start.

**A failed execution.** Any exception after the refusal checks appends one record to
`<local_output_root>/failed_runs.json` (exception type and message, stage name, source
hashes; no statistic and no identifier) and exits 3. No value from a failed run may be
printed, logged or read. The repair may touch only the failing stage; the acceptance stamp
is regenerated and recommitted. A gate that fails is not an exception: it is a verdict.

Files are written with `Path.write_text(json.dumps(obj, indent=2, allow_nan=False,
sort_keys=True) + "\n", encoding="utf-8", newline="\n")`; nothing is printed to stdout
except progress on stderr (PowerShell redirection writes UTF-16) and, at the end, the
sha256 of `results.json`. All serialisation checks run on in-memory objects before any
file is written: size at most `maximum_results_bytes` for `results.json` and
`acceptance.json`, at most `maximum_local_results_bytes` for the other files under
`local_output_root`; no key in
`results_identifier_key_denylist` and `banned_key_paths(obj) == []`;
`scripts.check_licensing` fingerprint patterns absent; and for `results.json` the rules of
section 8.

Order inside `run` (stage names for `failed_runs.json`): `hashes`; `sheets` (StatsBomb
matches and sheets; Wyscout matches, sheets, people; the data gate); `vocabulary` (the
vocabulary gate); `match_crosswalk` (its gate); `player_crosswalk` (the coverage gate);
`wide_link`; `surfaces` (both references, after the match crosswalk, which names the
matches the Wyscout reference leaves out, and before any double-coded event is read; the
surface gate); `frames` (events and harmonised frames for both variants); `inputs`;
`panels`; `weights`; `cells`; `controls`; `admission`; `divergence`; `serialise`.

Gates follow the protocol's "Order of the gates". The data, vocabulary and match-crosswalk
gates are evaluated in that order, each only if the one before passed. The first that
fails stops the run at its stage: no later stage runs, every graded cell is
`INCONCLUSIVE` with that reason, every link verdict is `INCONCLUSIVE` with that reason,
every admission is `EXCLUDED` by the admission table, and the files of section 8 are
written with their statistic blocks empty. The coverage and surface gates are evaluated
only if those three passed, each whatever the other returns, and do not stop the run. A
gate that was not evaluated has `passed` null in `gates`. A gate that fails in one
subset fails for every pool.

Memory: event frames are built per folder and reduced to harmonised columns before the next is
read; peak well under 1.5 GB; no process pool.

**The single command the root runs for the real execution** (repository root, after the
protocol commit `<sha>` and a committed, passing `acceptance.json`):

```powershell
.venv\Scripts\python.exe -X utf8 experiments/run_provider_agreement.py execute --protocol-commit <sha>
```

Determinism re-run, once, unchanged:

```powershell
.venv\Scripts\python.exe -X utf8 experiments/run_provider_agreement.py execute --protocol-commit <sha> --verify
```

The root copies `results.json` to `committed_experiment_dir` unchanged; the results commit
is refused unless its sha256 equals the one `execute` printed.

## 8. Result shapes

Both files are aggregate only: no player, team or match identifier, no name, no row per
player or per match. `null`, never NaN.

**`results.local.json`** (LOCAL; never committed):

| Key | Content |
|---|---|
| `provenance` | `experiment`, `protocol_commit`, `protocol_hash`, `config_hash`, `pipeline_hash`, `config` (verbatim), `source_hashes`, `packages` (python, numpy, pandas, pyarrow), `versions` (reader, crosswalk, inputs, agreement), `data` (section 9), `xt` (per surface: `hash`, `matches`, `moves`, `shots`, `turnovers`, `dropped_nan`, `iterations`), `seeds`, `crosswalk_digests` (`matches`, `players`), `acceptance_hash`, `tier`, `providers` |
| `gates` | `data`, `vocabulary`, `match_crosswalk`, `identity_coverage`, `xt_surface`: each `{passed, reason}`; `passed` is true, false, or null when the gate was not evaluated; `reason` is the gate's code when it failed (`DATA_MISSING`, `UNKNOWN_VOCABULARY`, `MATCH_CROSSWALK`, `IDENTITY_COVERAGE`, `XT_SURFACE`, in the order of the gates), else null |
| `coverage` | per subset: `expected_matches`, `listed_with_files`, `crosswalked_matches`, `rejected` by reason, `swapped_orientation`, `goal_checks`, `team_matches`, player-matches per provider, paired coverage share per provider; overall: sheet players per provider, zero-minute rows dropped, pair counts by status, player-matches dropped, `paired_outfield`, `swap_impossible_share`, `cautioned`, location exclusions by reason, players per pool along `exposure_curve_minutes` |
| `cells` | list; one object per graded cell: `quantity`, `level`, `pool`, `reader`, `valuation`, `exposure_minutes`, `units`, `strata_retained`, `strata_dropped`, `mean_statsbomb`, `mean_wyscout`, `sd_statsbomb`, `sd_wyscout`, `order`, `order_interval`, `replicate_mean_minus_point`, `spearman_unstratified`, `concordance`, `concordance_interval`, `icc_absolute_single`, `bias`, `sd_difference`, `limits`, `relative_bias`, `relative_bias_interval`, `scale_ratio`, `slope`, `exact_share`, `concordance_cross_check_gap`, `valid_replicates`, `verdict`, `reason`, `flags`. A cell that is `INCONCLUSIVE` holds `units`, `verdict` and `reason` only |
| `sensitivities` | list; `label` in `exposure_<minutes>`, `common_valuation`, `sensitivity_scheme`, `role_<code>`, `as_shipped_headline`; then `quantity`, `level`, `pool`, `reader`, `units`, `order`, `order_interval`, `concordance`, `relative_bias`. Pools per `sensitivity_pools`. No verdict. A row with fewer than `minimum_units_nonzero_on_both_providers` units holds `units` only |
| `difference_decomposition` | per quantity and pool: rows, players, `between_player_share`, interval |
| `subset_differences` | per quantity, level, reader: order statistic `world_cup` minus `la_liga` with interval |
| `controls` | `positive` (the two cells' verdicts, `passed`); `permuted_link` per aggregated quantity: `values`, `point`, `strictly_above_all`, `singleton_players`; `permuted_link_passed` (section 5, `registry_verdicts`) |
| `identity` | list of blocks from `evaluate_wide_link`, each with `tiers`, `pool`, counts, rates, intervals; `namesake_collision` per tier set; `verdict` and `reason` (verdict-pool blocks only) |
| `divergence` | `families` (per family and pool: events per provider, `count_ratio`, interval, per-team-match median / p10 / p90 per provider); StatsBomb pass and shot types (shares per pool); `pairing` (per family and pool: events, `pairs`, paired share per provider, `player_agreement`, `completion_agreement`, `goal_agreement`, `key_pass_overlap`, start and end displacement median and p90 in metres, `xt_delta_difference` mean and sd); `clock_offsets` (median, p10, p90, count at a grid edge); `one_sided` counts |
| `admission`, `verdicts` | as in `results.json` |

Graded cells: (`player_match_inputs` + `team_match_quantities` +
`aggregated_player_quantities`) × `pools` × `reader_variants`, at the `regime` valuation.
The runner fails rather than exceed either ceiling.

**`results.json`** (the only machine-readable file that may be committed). It holds no
`int` and no `float` anywhere (`bool` is allowed and is tested before `int`), and every
string outside `experiment`, `version` and `provenance` is a token, reason code, flag or
key name frozen in `config.json`; the runner asserts both.

| Key | Content |
|---|---|
| `experiment`, `version`, `tier` | `registry_experiment_id`, `version`, `tier` |
| `provenance` | `protocol_commit`, `protocol_hash`, `config_hash`, `pipeline_hash`, `source_hashes`, `packages`, `versions`, `acceptance_hash`, `local_results_sha256`, `providers`. No config echo |
| `verdicts` | `{subject: {token, reason, second_reason}}` for `registry_cell_subjects` and `registry_link_subjects`, from `registry_verdicts` |
| `cells` | list of `{quantity, level, pool, reader, verdict, reason, flags}` for every graded cell |
| `gates` | per gate `{passed, reason}`, as in the local file |
| `controls` | `positive_passed`; `permuted_link_passed` (true, false, or null when it tested nothing); per aggregated quantity `strictly_above_all` |
| `admission` | per aggregated quantity `{status, reason, pooled_verdict, la_liga_verdict}` |

`report_tables.md`: the aggregate tables of `analysis.md`, generated from
`results.local.json` under the protocol's "What is written where", so no number is retyped.
It stays local; the analyst copies tables from it.

**Registry records** (root adds them, `PENDING`, in the registration commit; one per
subject). Common: `experiment_id = registry_experiment_id`, `tier = Tier.LOCAL`,
`directory = committed_experiment_dir`, `non_claim` and `not_run_statement` from
`registry_common`, `protocol_hash` and `config_hash` = `lf_sha256` of the registered files.
Cell records: `scope` and `claim_token` from `registry_cell`, `vocabulary =
verdict_vocabulary.cell`, `outcomes = registry_outcomes.cell`. Link records: the same from
`registry_link`, `verdict_vocabulary.link`, `registry_outcomes.link`. After the run each
record takes its `token` from `verdicts[subject].token` in `results.json`,
`protocol_commit`, and `results_hash = lf_sha256(results.json)`. No sentence holds a digit other than the experiment id's.

## 9. Hash discipline

| Object | Hash |
|---|---|
| `preregistration.md`, `config.json`, `PIPELINE.md` | `lf_sha256` (CRLF→LF, then sha256). The checkout has `core.autocrlf=true`; a raw-byte hash would not reproduce |
| source files | `source_hashes`: `lf_sha256`, keys as posix paths relative to the repository root, twelve of them: the six E-11 source files of section 0 (`galactico/validation/sb_reader.py`, `provider_crosswalk.py`, `provider_inputs.py`, `provider_agreement.py`, `provider_agreement_synthetic.py` and `experiments/run_provider_agreement.py`), `galactico/validation/digests.py`, `galactico/models/xt/grid.py`, `galactico/models/xt/__init__.py`, `galactico/identity/resolver.py`, `galactico/providers/base.py`, `galactico/domain/thesis.py` |
| StatsBomb raw JSON | `folder_manifest` digest per folder, byte-exact (these files never pass through git's line-ending conversion); must equal `sb_folder_digests` |
| Pappalardo raw JSON | byte-exact sha256 of `players.json`, `matches_World_Cup.json`, `matches_Spain.json` |
| Pappalardo Parquet | content hash, never file bytes (the footer embeds the pandas version): sort by `["game_id", "period", "seconds", "event_id"]` (actions), `["game_id"]` (matches), `["game_id", "player_id"]` (lineups); `sha256(pd.util.hash_pandas_object(frame, index=False).values.tobytes())` |
| surfaces | `sha256(xt.values.tobytes())` |
| crosswalks | `crosswalk_digest`: sha256 of sorted `a|b` lines; local file only |
| `protocol_commit` | the CLI argument, verified against git; never a literal in the source |

## 10. Synthetic test suite

No test reads the real corpus except the one marked `slow`, which is structure only and
reads one provider per test. Oracles import nothing from the module under test and are
written from the definitions with `itertools`, `fractions.Fraction` and hand numbers. Each
rule test set must contain both the interesting outcome and its opposite.

| File | Tests |
|---|---|
| `test_sb_reader.py` | pass type and shot type read from a hand-built match; events without location kept with NaN; `period_seconds` from the timestamp; regulation clipping with an extra-time spell and a spell starting at 90+2; a spell ending at 47:00 in period 1 followed by a spell from 45:00 in period 2 gives the cap; an off-pitch gap lowers minutes; `started`, `cautioned`, `dismissed`, `permanent_off`; goalkeeper by modal spell; matches come from the index, not the directory; a listed match without a file is returned as missing, not raised; `folder_vocabulary` returns names and no counts, reads each type among the events of its own kind only (an event of another kind adds no None) and returns None for a Shot without a shot type; `folder_manifest` on a hand-built folder returns the digest of section 2 computed by hand with `hashlib`, ignores a file on disk that the index does not list, writes no line for a listed file that is absent, and changes when one byte of one file changes; the module passes `check_licensing.check`; `StatsBombProvider.competitions()` is unchanged |
| `test_provider_crosswalk.py` | match: straight and swapped orientation; the same two teams twice on different dates; tolerance edge; ambiguous day rejected; goals disagree rejects only listed durations; bijection. Sheets: zero-minute rows removed on each side by that side's own minutes; mutual unique maximum; shared surname resolved by full name; two leftovers sharing only a given name that a removed team-mate also carries stay `NAME_WEAK`; mononym; elimination marked not paired; `started` conflict; a minutes difference exactly at the tolerance passes and one minute more fails; minutes outside tolerance in one sheet of five keeps the link and drops that player-match; in one sheet of three gives `STRUCTURE_CONFLICT`; a dropped player-match is not covered; `sheets_together` counts a sheet in which the two hold rows and were paired by elimination, and step 3 is evaluated there; both waivers; cross-match contradiction drops all pairs; goalkeeper flag; no function parameter is an event frame. Wide link: tier A on the legal name only; tier N tried only after A finds nothing and only with a nickname; tier B; ambiguity does not fall through; claimed twice; country alias; a country outside the alias list is a no-link; the three outcome classes including an unpaired player linked off his sheets and on them; absent partner with a planted namesake; namesake collision on a planted roster; a planted 100-person roster returns the planted recall, false-link, stress and collision rates exactly; Wilson against hand numbers; zero trials give None and None fails the verdict; each of the four gates and too few evaluated players gives `INCONCLUSIVE` with its own reason, in the order of `link_inconclusive_reasons`; verdict boundaries; `name_nationality_link` has no default for `unique_right` or `exclude_right`. Permutation: no fixed point, deterministic, inside strata, singletons counted |
| `test_provider_inputs.py` | every flag row on a hand-built match per provider; a successful Wyscout duel, touch or set piece is not `completed`; a Miscontrol row with no end location and a failed Wyscout pass with a sentinel end are both turnovers in their surface; a Spain frame without `xt_wy_reference_expected_matches` matches raises; each of the fifteen player inputs against the table of section 4 on a hand-built match, where `key_passes` counts the shipped flag and differs from the assist-inclusive count; every Wyscout set-piece subtype of the adapter falls in exactly one `wy_*_subtypes` list; the closed vocabulary stops on an unknown name; a Corner-type shot is one-sided, not a non-penalty shot; clearances are in no union; `open_play` and `as_shipped` differ by exactly the injected restarts; kick-off counted as an open-play pass on both sides; channel bands equal `ActionFilter.apply` on `y = 0.00..1.00`; surface equals `experiments.run_external_replication.fit_xt` on the same synthetic Wyscout actions; sentinel starts and ends excluded from location quantities and kept in counts; `xt_delta` is NaN on NaN and the row is excluded; `goal_angle` equals `2·atan((g/2)/d)` on the centre line, 0 on the goal line outside the posts, symmetric in `y`; each provider's penalty-area edges, inclusive; opponent half strict at the halfway line; final-third boundary, lanes with the attacker's left at `y = 0`, pitch thirds; conceded equals the opponent's mirrored value; unpaired and unattributed rows absent at player level and present at team level; regulation filter; clock offset recovers a planted +3.5 s; pairing is one-to-one, respects tolerances, is invariant to row order |
| `test_provider_agreement.py` | `stratified_rank_correlation` against a brute-force oracle including ties and weights; equals Spearman with one stratum; unchanged when a constant is added to one stratum on both sides; a stratum below its minimum is dropped; fewer than the minimum strata is NaN; a replicate in which a retained stratum has zero total weight is valid and equals the statistic on the other strata; constant vector is NaN; integer weights equal duplicated units; `concordance` on hand numbers, 1 for identical vectors, lower under a shift; `icc_absolute_single` against an explicit two-way ANOVA in `Fraction`; Bland–Altman hand numbers; weights: shapes, per-block row sums, determinism, seed streams distinct; `team_cluster_fixed_cohort` never changes the gated set or an aggregate; the sensitivity scheme recomputes gates; ratio of sums, not mean of ratios; exposure and minimum denominator applied to both providers; a player-match present on one provider only enters no aggregate and no exposure sum on either; a hole stays a hole; `concordance_cross_check_gap` is true strictly above the tolerance, false at it and None on NaN; the same weight arrays reach every quantity and both providers; row-order invariance; `difference_decomposition` recovers planted variance shares; `planted_corpus` structure (match counts, minutes sum per team-match, players exactly on the gate exist) and its population values within tolerance |
| `test_provider_agreement_rule.py` | each decision row; lower bound and point exactly at the threshold are admitted; lower bound at the threshold with the point below is `NOT_ESTABLISHED` and flagged; a point below its interval with both at or above the threshold keeps its row 2 or row 3 token and is flagged; a point above its interval with both below the threshold stays `NOT_COMPARABLE` and is flagged; a point inside its interval is not flagged; upper bound exactly at the threshold is `NOT_ESTABLISHED`; bias interval touching the margin passes; NaN concordance falls to row 3; NaN order statistic is `INCONCLUSIVE`; each gate gives its reason code in precedence order, and each of the ten reason codes is returned by at least one case in which no earlier reason holds; missing files with too few matches left to link return `DATA_MISSING`, not `MATCH_CROSSWALK`; `IDENTITY_COVERAGE` reaches player-level cells only and `XT_SURFACE` xT quantities only; `ONE_SIDED` against `DEGENERATE`, where a side that is constant and non-zero while the other varies is `DEGENERATE` and a side with no non-zero unit against a constant non-zero side is `ONE_SIDED`; exhaustive grid: exactly one token from the vocabulary for every combination; every admission row and every reason in precedence order; `la_liga` `INCONCLUSIVE` excludes; `la_liga` `NOT_ESTABLISHED` gives the suffix; the declared variant is never admitted; positive-control failure excludes all; a tie with a permuted value fails; `registry_verdicts`: every combination of the two control states, the five headline tokens and the five `la_liga` tokens returns exactly one token of the vocabulary, equal to the headline token or to `NOT_ESTABLISHED` or `INCONCLUSIVE`; a failed positive control gives every cell subject `INCONCLUSIVE` with `POSITIVE_CONTROL`, a permuted-link failure on one subject with an agreeing headline gives every cell subject `INCONCLUSIVE` with `PERMUTED_LINK_CONTROL`, and both failing gives `POSITIVE_CONTROL`; a permuted value at or above the point of a subject whose headline token is not agreeing fails nothing; `permuted_link_passed` is null, not true, when no subject has an agreeing headline, and row a does not then apply on its account; every reason and second reason written is null or in its frozen vocabulary; an agreeing headline with `la_liga` `NOT_COMPARABLE` gives `NOT_ESTABLISHED` with `LA_LIGA_SUBSET_CONTRADICTS`; with `la_liga` `NOT_ESTABLISHED` or `INCONCLUSIVE` it keeps the headline token and carries `LA_LIGA_SUBSET_DID_NOT_CONFIRM`; with `la_liga` agreeing it carries no second reason; a headline that is not agreeing keeps its token and reason under every `la_liga` token; a run stopped by a gate gives every cell subject `INCONCLUSIVE` with `POSITIVE_CONTROL`; link subjects are unchanged by any control; `admission` is unchanged by the registry rule: with a permuted-link failure on one subject, another quantity whose own cells and control hold is still admitted while its registry token is `INCONCLUSIVE`; a reduced acceptance run for the comparable, boundary and null scenarios |
| `test_provider_agreement_runner.py` | `execute` refuses without a commit, with a commit that is not the first to add each file, with a later commit touching one, with a protocol, config or pipeline that differs, with a null or wrong digest, without or with a stale or failed acceptance stamp (a committed stamp that differs from the local one in line endings only is accepted), with an output root outside `data/licensed/`, on a second execution, and after a failed run not listed in the analysis; a planted exception writes `failed_runs.json` with no statistic; a synthetic corpus with files missing, with an unknown vocabulary name and with too few linkable matches each stops at its stage, runs no later stage, and returns its own reason for every cell and every link verdict, with later gates null; no path under `sb_forbidden_roots` is opened; `preflight` calls no function with frames of both providers; end to end on `synthetic_corpus(noise=False)`: every graded `open_play` cell `COMPARABLE` with concordance 1, `as_shipped` pass-count bias exactly the injected restarts, crosswalk complete, wide-link counts as planted; the divergence tables and the pairing receive the `divergence_reader_variant` frame; two runs byte-identical; `allow_nan=False`; both size ceilings, a local file between the two being accepted and a committed one refused; denylist and `banned_key_paths`; licence-guard patterns; `results.json` holds no number and only frozen strings, and a synthetic tree built from it with the registry records of section 8 passes every checker of `tests/test_verdict_registry.py`; no key of the config or the result files contains a provider's full name, and the key walker of `tests/test_licensing.py`, copied into the test, finds nothing in a `results.json` and an `acceptance.json` built with the twelve real source paths of section 9; no product package imports the five research modules; `@pytest.mark.slow` structure checks, one provider each: both real folders list the expected matches, and `read_wyscout_team_sheets` minutes equal `lineups.parquet` minutes clipped at the cap (skip cleanly when a cache is absent) |

**Acceptance before outcomes** (not a unit test; `acceptance` subcommand): the scenarios of
section 6. `execute` cannot start without the committed stamp. A failed scenario is a
defect in the code or in the rule; the rule is not edited to pass it after the protocol
commit.

## 11. Pre-outcome code review checklist

The reviewer signs each line before the root runs `execute`.

1. No function in `provider_crosswalk.py` takes or reads an event frame.
2. `match_links`, `pairs`, sheets and people frames are never written to disk, logged, or
   placed in an exception message or in `failed_runs.json`.
3. Both providers are filtered to regulation periods before any count; minutes are capped
   after summing spells.
4. StatsBomb completion uses absence of an outcome; Wyscout uses `success is True`; both
   on open-play passes only.
5. `open_play` excludes Corner, Free Kick, Goal Kick and Throw-in passes and includes Kick
   Off; penalties, and StatsBomb shots typed Corner or Kick Off, are outside
   `non_penalty_shot`; the vocabulary gate runs before any event is counted.
6. `y` is not flipped on either side; the left-lane test would fail if it were. Each
   provider's penalty area is its own; sentinels never reach a location test.
7. Each provider's events are valued on the surface the protocol names; the `common`
   valuation is never graded.
8. Reference surfaces are fitted before the double-coded events are read and exclude them
   on the Wyscout side; a non-converged surface raises.
9. NaN coordinates never reach `PitchGrid.cells`.
10. Per-90 values divide by the same provider's minutes; the exposure gate and minimum
    denominators are applied to both providers; ratio quantities are ratios of sums.
11. One weight matrix per axis (match, player, team), created once, passed everywhere;
    seeds and streams come from config.
12. At the aggregated level the primary scheme never recomputes a gate or an aggregate;
    ranks are recomputed in every replicate; invalid replicates are counted, not replaced.
13. `classify` is the only place a cell token is produced and `registry_verdicts` the only
    place a registry token is; comparisons match the protocol; NaN and None never pass.
14. Sensitivities and the decomposition carry no token.
15. The permuted control derives from the paired links and cannot return a fixed point in
    a stratum of two or more.
16. `results.json` holds no number and only frozen strings; both files pass
    `check_licensing.check`, the denylist and `banned_key_paths`.
17. Hashes use `lf_sha256` for protocol, config, pipeline and code; Parquet uses content
    hashes.
18. `protocol_commit` is an argument checked against git; no literal commit in source.
19. Nothing under `galactico/api` or any product package imports these modules;
    `StatsBombProvider` is byte-identical to `HEAD`.
20. The committed acceptance stamp matches the reviewed source hashes.
21. No agreement value, pairing or link rate beyond those listed in the protocol's
    prior-exposure table was printed, logged or inspected during the build. The build
    report says which real-data commands were run; only `preflight` and the fetch script
    of section 2 are allowed, and neither joins anything across providers.

## 12. Attribution and logo

`analysis.md` (and any `docs/research` report citing an E-11 number) starts with the block
at the head of the protocol, with the image path relative to the file that carries it:

```markdown
<img src="../../../docs/assets/statsbomb/statsbomb-logo.png" alt="StatsBomb" width="170">

Data source: **StatsBomb** open data, read locally under the StatsBomb Public Data User
Agreement. This analysis is formed from StatsBomb data and carries the StatsBomb logo as
clause 1.4 of that agreement requires. It is not the opinion or analytical insight of
StatsBomb. No StatsBomb data, no identifier and no row for a player, a team or a match is in
this repository; the tables below are aggregates.
```

followed by the Pappalardo citation as in the protocol. The logo is the existing file at
`source_logo_path`, unchanged (it is hash-pinned by `tests/test_licensing.py`). The report
is non-commercial, carries aggregate tables only, and names no player, team or match.

## 13. Shared-file requests to the root

One order, the one the north-star README gives: registration, then the pipeline, then the
acceptance stamp, then the run.

**Before registration** (nothing below is an outcome; each was done for these three files
and the root repeats it as a check):

| Step | Detail |
|---|---|
| Folder digests | `sb_folder_digests` holds the three digests of section 2, computed from the files on disk. `scripts/fetch_statsbomb_double_coded.py --check` recomputes them by that rule with no network; the root runs it and stops if it exits non-zero. `preflight` prints them again once the pipeline exists |
| Vocabulary | the names in the two double-coded folders and in `xt_sb_reference_folder` were compared with the four `sb_known_*` lists, names only: none is outside a list |
| Pipeline hash | `pipeline_spec_sha256` is `lf_sha256` of this file as it stands. An edit to this file before registration means recomputing it; after registration neither changes |

**The registration commit** changes hosted output, and says so:

| File | Change |
|---|---|
| `experiments/preregistered/E-11-provider-agreement/` | the three registered files (section 0); `experiments/preregistered/README.md` row `E-11 provider agreement`, `preregistered, not run` |
| `galactico/domain/verdicts.py` | the `PENDING` records of section 8; the docstring's "ships EMPTY" paragraph |
| `galactico/api/planning.py` | the wording `verdict_reading` returns once the registry is non-empty. It must keep a true sentence that no planning quantity has been tested by a registered experiment. The `shots` entry of `NOT_MEASURED_EXTRA` reads "No shot construct is shown. No protocol covers one.": the second sentence is false once E-11's shot subjects are registered, and the first must be checked against what the page then lists. A root product decision, not E-11's |
| tests and specs that assert the empty registry | every one; search for `VERDICTS == {}`, `all_payloads`, `"verdicts"`, `NOT_TESTED_STATEMENT` and "registry is empty". At least: `tests/test_verdict_registry.py` (`test_the_shipped_registry_is_empty_and_answers_not_registered`, and `test_payload_is_json_ready_and_carries_no_hash_or_pointer`, which asserts the exact list `all_payloads()` returns), `tests/test_lab_runtime.py` (`test_verdicts_endpoint_serves_the_registry`, which asserts an empty `verdicts` list), `tests/test_planning_api.py`, `tests/test_planning_render.py`, `tests/test_squad_api.py`, `tests/test_transfer_api.py`, `e2e/squad.spec.js`, `e2e/transfer.spec.js` |
| prose that says the registry is empty | ADR-0018, `docs/research/north-star/README.md`, ROOT-DECISIONS 2.6, `KNOWN_LIMITATIONS.md`, `ROADMAP.md`, the module docstring of `galactico/api/transfer_lab.py` |
| `tests/test_preregistration_order.py` | add `"PIPELINE.md"` to `PROTOCOL`, and in the same edit add `"PIPELINE.md": "frozen"` to the `E-91-in-order` entry of the first `SCRATCH_HISTORY` commit; without the second, `test_protocol_then_results_is_accepted_and_a_rerun_does_not_reset_it` fails |
| `tests/test_licensing.py` | add the registered `preregistration.md` to `FORMED_FROM_STATSBOMB` now and `analysis.md` in the results commit |
| `scripts/fetch_statsbomb_double_coded.py` | committed as written (section 2) |
| `LICENSING.md` | the sentence of section 2 on folder digests, as the root ruled |
| a data-free test, new or in an existing test file | `lf_sha256` of the registered `PIPELINE.md` equals `pipeline_spec_sha256`: until the pipeline exists nothing else ties the two (M-06) |
| `docs/assets/statsbomb/statsbomb-logo.png` | the existing file, unchanged |
| `galactico/providers/base.py` | add the Players and Teams figshare articles to the Pappalardo attribution if the root wants their identifiers cited; the protocol names them by title |

**After registration, before `execute`:**

| Step | Detail |
|---|---|
| The commit that adds the pipeline | the six source files and the test files of section 0. In that commit, and not before, `tests/test_research_firewall.py` gains the five `galactico.validation` modules of section 0 in `RESEARCH_PIPELINES` (`sb_reader`, `provider_crosswalk`, `provider_inputs`, `provider_agreement`, `provider_agreement_synthetic`): `test_the_lists_name_modules_that_exist` requires each listed file to exist |
| Run and commit `acceptance` | `acceptance.json` beside the protocol, in a commit of its own after the pipeline and before the results. It is not one of the three protocol files and `tests/test_preregistration_order.py` does not read it |

**After the run:** the results commit (`results.json`, `analysis.md`, the registry tokens
and hashes); `KNOWN_LIMITATIONS.md` entries for any contradiction with
`comparable_across` and for the `MAPPING_AUDIT` wording. `MAPPING_AUDIT` itself is not
edited by this work package.

## 14. Reconciliation of E-12 with this protocol, before E-12 is frozen

This protocol does not wait for it. E-12's protocol must repeat these, word for word where
a rule is quoted, before it is frozen:

1. Pair status `PAIRED_BY_TEAM_SHEET` (was `VERIFIED_BY_TEAM_SHEET`).
2. Tier A: the StatsBomb legal name token set equals the Wyscout first-plus-last-name
   token set. No nickname. E-12 uses tier set `[A]` only; `[A, N]` and `[A, N, B]` are
   graded for the record.
3. Admission statuses: four statuses admit, and the two `_LEAGUE_UNCONFIRMED` ones must be
   printed; reasons `LA_LIGA_SUBSET_UNTESTED` and `DECLARED_VARIANT` exclude. A share of
   open-play shots per player is not graded here and so is not admitted.
4. `e_fl` = the upper bound of the false-link rate; `e_ap` = `link_absent_partner_bound`.
5. E-12 reads the committed `results.json` (`admission`, `verdicts`) and, being LOCAL
   itself, may read `results.local.json` for the measured link rates. The per-quantity
   order statistic is not a provider attenuation factor: it is an upper-biased one when
   the between-player share of the difference decomposition is large. E-12 imports
   `read_events`, `harmonise_statsbomb(variant="open_play")`, the surface rule of
   `statsbomb_reference_surface` and `name_nationality_link` from the modules above
   (`galactico.validation.sb_reader`, `provider_inputs`, `provider_crosswalk`) and pins
   their source hashes.
6. Config keys were renamed (`sb_*`, `wy_*`); E-12's own config has the same exposure to
   the key check of `tests/test_licensing.py`.

## DISSENT

1. **R7 as written forbids any committed machine-readable E-11 number.** The design obeys
   it: statistics stay in `results.local.json`, and the committed `results.json` carries
   tokens and hashes only. Cost: the published numbers exist only as Markdown tables,
   which is weaker for reproducibility than E-07 and E-08. The licence text permits
   publishing analysis with the logo, so R7 is stricter than the licence.
2. **The 100 matches are not one specification.** About nine in ten gated players at the
   aggregated level come from the older specification and from national-team football.
   By the protocol's own simulation the La Liga cell excludes a quantity reliably only
   when its agreement is near 0.60, and under one error structure in about half of the
   corpora even there; most admissions will read `_LEAGUE_UNCONFIRMED`. The simulated
   club block is larger than the real one, so the real cell does less.
3. **The interval is conservative at high agreement.** In both simulations the replicate
   distribution sits slightly below the point estimate (about 0.01; nearer 0.02 in the La
   Liga pool), which lowers the admission rate at a true 0.85 to between a fifth and a
   quarter. A bias-corrected interval would raise it; it was not adopted because its
   behaviour at the boundary was not simulated under all three error structures.
4. **The absent-partner criterion adds nothing for tier set `[A]`.** Its namesake count
   is known to be zero on this roster, and its stress count is the number of paired
   players whose tier A link is a wrong record, each of which the false-link criterion
   already counts. The protocol says so; nothing in the two corpora can measure the risk it
   stands for.
5. **R12 at the aggregated level.** R12 asks that every resample be one coherent
   match-weight vector shared by all players and constructs. At the aggregated level the
   shared world of this protocol is one team-weight vector per replicate, shared by every
   quantity, reader and pool, with the cohort and every aggregate held fixed (section 5,
   `team_cluster_fixed_cohort`). **Root ruling, 9 October 2026: ACCEPTED.** R12 exists to
   keep one coherent world across players and constructs; a shared team-weight vector
   keeps that, and the reviewers' simulations showed that re-weighting matches inside an
   aggregate and re-applying the gates miscalibrates the admission rule.
6. **ROOT 2.5 O5 below 100 units.** O5 asks a protocol with fewer than 100 units to
   compute its interval on the half-sample correlation and transform it. The cells of the
   `la_liga` pool at the `aggregated_player` and `team_match` levels have fewer than 100
   units and use the two-sided percentile interval, whose lower bound gates admission.
   **Root ruling, 9 October 2026: O5 does not apply to E-11.** It prescribes an interval
   on a half-sample correlation for split-half protocols, and E-11 forms none. The
   two-sided percentile interval is ACCEPTED for cells with fewer than 100 units.
