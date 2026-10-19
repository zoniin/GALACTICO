# E-12 pipeline specification

Build target for `experiments/preregistered/E-12-transport-movers/` and its public twin
`experiments/preregistered/E-12-transport-movers-public/`. The protocol is
`preregistration.md`; every number is in `config.json`; this file is the code contract.
**It is frozen with them:** it is committed in the registration commit byte for byte as it
stands here, its `lf_sha256` is `pipeline_spec_sha256` in the config, and `execute` refuses a
mismatch. Where this file and the protocol disagree, the protocol wins and the disagreement
is a defect. Revised on 18 October 2026 after the first adversarial review (REVIEW-RECORD);
not yet audited.

**Tier rule (binding on every function below).** The `cross_corpus` arm is LOCAL_LICENSED.
Nothing here is imported by `galactico/api`, `galactico/optimization`, `galactico/profiles`,
`galactico/match_lab`, `galactico/models` or `galactico/features`. No link, pair, per-player
row, provider id or name is written anywhere except process memory. The only files written
are aggregate JSON and Markdown under `local_output_root` and `public_output_root`
(gitignored); the root copies the committed ones. Until the root runs the real execution,
every module is exercised on synthetic data only. No agent runs `execute`. The public stage
opens no path under `sb_root`, reads no E-11 result and runs before the licensed stage.

## 0. Files and ownership

| File | New | Owner | Content |
|---|---|---|---|
| `galactico/validation/club_change.py` | yes | E-12 A (sections 2, 3), E-12 B (sections 4, 5, 7) | pure functions: frames in, results out; no IO except `sb_spell_positions` (section 2), no provider import |
| `experiments/run_club_change.py` | yes | E-12 C | CLI `calibrate`, `execute`; all other IO; the only place E-11 modules and `PappalardoProvider` are imported |
| `tests/test_club_change_structure.py` | yes | E-12 A | club keys, positions, links, cohorts, values, cells, levels |
| `tests/test_club_change_statistics.py` | yes | E-12 B | statistics against independent oracles; shared worlds; matched weights |
| `tests/test_club_change_rule.py` | yes | E-12 B | decision table, admission, registry token, rule verdict, gates, governing mapping, calibration (reduced) |
| `tests/test_club_change_runner.py` | yes | E-12 C | refusals, output shapes, tier separation, determinism on a synthetic corpus |
| `experiments/preregistered/E-12-transport-movers/{preregistration.md,config.json,PIPELINE.md}` | yes | root commits | registered from this folder. `config.json` and `PIPELINE.md` byte for byte. `preregistration.md` after two edits and no other: the DRAFT banner (the block quote under the title, which holds the only relative links besides the logo) is replaced by the one line `> References such as ROOT 2.5 or R12 point to [ROOT-DECISIONS.md](../../../docs/research/north-star/ROOT-DECISIONS.md); the working notes they cite are described in the [README](../../../docs/research/north-star/README.md) beside it.`, and the logo path becomes `registration_logo_relative_path`. The registered hashes are of the registered bytes |
| `experiments/preregistered/E-12-transport-movers-public/{preregistration.md,config.json,PIPELINE.md}` | yes | root commits | byte-identical copies of the three registered files above, so that the five PUBLIC records point at a directory whose `results.json` is PUBLIC (DISSENT 6); a test asserts the copies equal the originals |
| `experiments/preregistered/E-12-transport-movers/calibration.json` | yes | root commits, before `execute` | the synthetic calibration stamp, in a commit of its own after the pipeline (section 13) |

Three agents (A, B, C) can build in parallel against the frames fixed in sections 2 to 5.
No existing file is edited by them. Frozen files are untouched.

Naming. The module is `club_change` (ARCH-SPEC 8.2, a working note not in the tree, used the
same name; the assignment's `transport_movers` is not used, so that no module of E-12 carries
E-07's word beside `galactico/validation/transport.py`). The directory slug stays
`E-12-transport-movers`.

**Reused, unchanged.** Every name below was imported and its signature read on 18 October
2026.

| Reuse | From |
|---|---|
| `normalise_name` | `galactico/identity/resolver.py`. `resolve_player` is not used (it accepts nobody without a birth date) |
| `read_matches`, `read_team_sheets`, `read_events`, `folder_vocabulary`, `folder_manifest`; `_requested`, `_file`, `LINEUPS`, `_spell` (the spell rule `read_team_sheets` applies, for `sb_spell_positions`) | `galactico/validation/sb_reader.py` (E-11) |
| `read_wyscout_matches`, `read_wyscout_team_sheets`, `read_wyscout_people`, `crosswalk_matches`, `assign_match_keys`, `team_sheet_crosswalk`, `name_nationality_link`, `crosswalk_digest`; `_right` (the right side `evaluate_wide_link` builds) | `galactico/validation/provider_crosswalk.py` (E-11) |
| `read_wyscout_actions`, `harmonise_statsbomb(variant="open_play")`, `harmonise_wyscout`, `statsbomb_reference_surface`, `wyscout_reference_surface`, `sheet_minutes`, `player_match_inputs`, `SurfaceUnfit` | `galactico/validation/provider_inputs.py` (E-11) |
| `PappalardoProvider(...).players()` (`birth_date` only) | `galactico/providers/pappalardo.py` |
| `lf_sha256`, `lf_sha256_text` | `galactico/validation/digests.py` |
| `PROVIDERS`, `assert_may_host`, `LicenseViolation` | `galactico/providers/base.py` |
| `verdict_for` (to read E-11's registry tokens) | `galactico/domain/verdicts.py` |
| `banned_key_paths`, `BANNED_KEY_PARTS` | `galactico/domain/thesis.py` |
| `check` | `scripts/check_licensing.py`, called by tests on every new file and on both `results.json` and `calibration.json` as if at their committed paths, never at paths under `data/licensed/` |
| channel bands, xT grid and recipe | inherited through E-11's functions and config; E-12 defines none |
| house precedents | `experiments/run_provider_agreement.py` (refusals, failed-run log, serialisation checks), `galactico/validation/partial_history.py::_permutation_maps` (SHA-256-derived placebo seeds; pattern only, not imported), `galactico/profiles/uncertainty.py::shared_match_weights` (one multinomial matrix shared by all measurements; pattern only: E-12's unit is the club) |

Not reused, on purpose: `experiments/run_external_replication.evaluate` (unfiltered
StatsBomb reader, per-league surfaces, league-wide parity halves), `features.spec.evaluate`
(hard-codes `player_id` and the unfiltered adapter),
`galactico/profiles/uncertainty.py::bootstrap_players` (resamples matches; E-12's estimand is
across players and its dependence is by club).

Engineering: `from __future__ import annotations`; frozen dataclasses; full type hints;
`__all__`; numpy and pandas only (no scipy; the normal quantile is
`statistics.NormalDist().inv_cdf`); ruff clean (line length 100); paths anchored at
`Path(__file__).resolve().parents[n]`; module docstring states claim and non-claim. No
function takes a default for a value that is in config. Config keys that restate a rule as a
sentence are read by assertions, not by branches. JSON keys never come from
`results_key_denylist`. **Key names:** no key, at any depth, of `config.json`,
`calibration.json`, either `results.json` or `results.local.json` contains `statsbomb`,
`pappalardo` or `wyscout` in any letter case or starts with `SB_` (`key_naming`); a key that
concerns one provider has `sb` or `wy` as one of its parts; no key has a part in
`BANNED_KEY_PARTS`. No double-quoted provider schema key followed by a colon in any committed
file (provider-shaped test payloads are built with `dict(...)`).

## 1. Data flow

```
PUBLIC STAGE (opens no path under sb_root; reads no E-11 result)
  Spain actions -> wyscout_reference_surface(actions, [], e11_config) = wy_public_spain
  wyscout season inputs (5 leagues, wy_public_spain) -> public_cohorts -> unit_values
  -> normal_scores (league x role x side) -> panel P -> same_club_split, evaluate_contrast(public_winter)
  -> public results.json + its tables
DEPENDENCY (read_dependency)
  verdicts.py E-11 records -> refusal if PENDING; E-11 results.json + results.local.json
  -> admission per construct, link token, e_fl / e_ap, surface hashes, crosswalk digests, packages
LICENSED STAGE (only when at least one construct is admitted)
  folder digests and vocabulary of the four 2015/16 folders (vocabulary gate)
  E-11 double-coded folders -> crosswalk_matches -> WY_ROWS_ABSENT -> assign_match_keys
     -> team_sheet_crosswalk -> PAIRED pairs (memory); digests asserted equal to E-11's
  surfaces sb_reference_open_play, wy_reference; hashes asserted equal to E-11's
  StatsBomb 2015/16 people x Wyscout people -> name_nationality_link(tiers=["A"]) (memory)
  combine_links -> club_keys / assert_club_crosswalk
  statsbomb season inputs (4 leagues) + wyscout season inputs (5 leagues) + sb_spell_positions
  -> season_summary -> modal_broad_class -> cross_corpus_cohorts (per floor pair) -> unit_values
  -> normal_scores -> club_levels -> build_panel
  -> evaluate_contrast x {within_league, league_change, bundesliga_destination} on ROLE_SAME
  -> (gated) role_changed stratum, sensitivities, attrition
assemble -> results.local.json (LOCAL) + cross_corpus results.json (tokens) + report_tables.md
```

## 2. Structure functions (`club_change.py`; no outcome is touched)

```python
VERSION = "club-change-v2"

def club_keys(team_names: pd.Series, league: pd.Series,
              aliases: Mapping[str, Sequence[str]]) -> pd.Series
def assert_club_crosswalk(origin_keys: Iterable[str], destination_keys: Iterable[str],
                          config: Mapping[str, object]) -> dict[str, int]
def combine_links(paired: pd.DataFrame, wide: pd.DataFrame | None
                  ) -> tuple[pd.DataFrame, dict[str, int]]
def sb_spell_positions(root: Path, folder: str, game_ids: Collection[int], *, cap: int,
                       regulation_periods: Collection[int]) -> pd.DataFrame
def modal_broad_class(spells: pd.DataFrame, main_club_games: pd.DataFrame,
                      rule: Sequence[Sequence[str]]) -> pd.DataFrame
def season_summary(appearances: pd.DataFrame) -> pd.DataFrame
def cross_corpus_cohorts(links: pd.DataFrame, origin: pd.DataFrame, destination: pd.DataFrame,
                         shared_clubs: Collection[str], config: Mapping[str, object],
                         *, origin_floor: int, destination_floor: int) -> pd.DataFrame
def public_cohorts(appearances: pd.DataFrame, position: pd.Series,
                   config: Mapping[str, object], *, side_floor: int) -> pd.DataFrame
def false_link_share(*, origin_floor_players: int, paired: int, wide_only: int,
                     false_link_upper: float | None, absent_partner_upper: float | None,
                     movers: int, cap: float) -> tuple[float | None, bool]
def sample_gate(*, stayers: int, movers: int, stayer_clubs: int, mover_clubs: int,
                vocabulary_passed: bool, config: Mapping[str, object]) -> Gate
def required_movers(stayers: int, config: Mapping[str, object]) -> int | None
```

| Function | Exact behaviour |
|---|---|
| `club_keys` | `key = normalise_name(name)`; if `key` is one of the spellings in `aliases`, replace by the canonical; return `key + "\|" + league`. No provider team id enters. Names from `club_name_sources` |
| `assert_club_crosswalk` | shared = intersection. Raises `StructureError` (a failed run, exit 3) unless shared per league equals `club_crosswalk_expected_shared`, origin-only count equals `club_crosswalk_expected_origin_only`, destination-only count in the overlap leagues and in `destination_only_league` equal their expected values, and every key occurs once per corpus. Returns the counts |
| `combine_links` | `paired`: `origin_id`, `destination_id` (E-11 pairs with status `dependency_paired_status`). `wide`: `origin_id`, `destination_id` for outcome `LINKED`, or `None` in `paired_only` mode. Result: `origin_id`, `destination_id`, `tier` (`P`, else `A`). Tier P wins. An `origin_id` whose two tiers name different partners, and every link into a `destination_id` reached from two `origin_id`s, is dropped; counts `tier_p`, `tier_a`, `tier_conflict`, `claimed_twice` |
| `sb_spell_positions` | the one StatsBomb read E-11 does not provide (E-11 section 14, item 9). For each requested match (`sb_reader._requested`), the lineup file (`sb_reader._file(root, folder, LINEUPS, id)`), every team and player, every spell whose `from_period` is in `regulation_periods`, through `sb_reader._spell(spell, place, cap, set(regulation_periods))`: one row per spell, `sb_game_id`, `sb_team_id`, `sb_player_id` int64, `from_period` int8, `from_minute` int (`_spell(...).order[1]`), `place` int, `position` str or None, `minutes` int (`_spell(...).minutes`). It reads lineup files only. A parity test: per player-match, `min(cap, sum(minutes))` equals `read_team_sheets`' `minutes_regulation`, and the position of the spell with most minutes, ties to the earliest, gives its `is_goalkeeper` |
| `modal_broad_class` | `sb_modal_broad_position_rule`: spells restricted to the player's main-club matches (`main_club_games`: `sb_player_id`, `sb_game_id`, `date`); each spell's class is the first matching lower-case substring of `sb_broad_position_rule` in order (none: unmapped, counted); minutes summed per class; the largest wins; a tie goes to the tied class of the earliest spell by (`date`, `sb_game_id`, `from_period`, `from_minute`, `place`). Output per player: `broad_class` (`GK`, `DF`, `MF`, `FW` or missing), `tie_broken` bool, `unmapped_minutes`. "Right Wing Back" is DF |
| `season_summary` | input: one corpus, columns `player_id`, `club`, `league`, `game_id`, `date`, `minutes_regulation`, rows with at least `minimum_regulation_minutes_appearance` minute only. Output index `player_id`: `main_club`, `main_league`, `main_minutes` (minutes for the main club only), `clubs` (count with an appearance), `tie` (two clubs share the maximum). Rows with `tie` are excluded downstream and counted |
| `cross_corpus_cohorts` | one row per link with both summaries present, outfield on both sides (`outfield_rule`), no tie, `main_minutes >= floor` on each side: `cohort` by the protocol table (`S`, `M_w`, `M_x`, `M_b`, `EXCLUDED_SAME_MAIN_SECOND_CLUB`), `tier`, `role_same` (`role_same_rule`), `second_club`, `origin_club_shared`, `destination_club_shared`, `second_tier_stayer`, `age_band`, `minutes_band` (`band_closure`, `band_missing_value`). Also returns, in `attrs["attrition"]`, the count of links lost at each step by reason, with `ROLE_SAME` and `ROLE_CHANGED` counts per cohort |
| `public_cohorts` | from the five-league appearances (`public_appearance_rule`): per player the clubs with an appearance and their first and last appearance dates. `P_M` and `P_S` by the protocol table. Output per unit: `cohort`, `before_club`, `after_club`, `before_league`, `after_league`, `before_games`, `after_games` (tuples of game ids, memory only), `minutes_before`, `minutes_after`. `attrs["attrition"]`: two-club players, by window, interleaved, goalkeepers, below each side floor |
| `false_link_share` | `F = false_link_upper * wide_only + absent_partner_upper * max(0.0, origin_floor_players - paired - wide_only * (1.0 - false_link_upper))`; returns `(F / movers, F / movers <= cap)`, and `(None, False)` when either bound is `None` (`paired_only` mode). The second value is "loss evaluable" |
| `sample_gate` | failed codes in the order of `inconclusive_reasons`: `UNKNOWN_VOCABULARY` (`cross_corpus` only), `MIN_STAYERS`, `MIN_MOVERS`, `INVERSE_N_SUM` (evaluated only when both counts exceed `inverse_n_sum_requires_counts_above`; otherwise recorded as not evaluated), `MIN_STAYER_CLUBS`, `MIN_MOVER_CLUBS`; `passed = not failed`. Counts are the analysed counts (`analysed_unit_rule`) |
| `required_movers` | `required_movers_rule`: `max(minimum_movers, ceil(3 + 1 / (maximum_inverse_n_sum - 1 / (n_S - 3))))`; `None` when `n_S <= 3` or the denominator is not positive. 72 at 313, 62 at 1,097, 65 at 592 (tested) |

```python
class StructureError(RuntimeError): ...

@dataclass(frozen=True)
class Gate:
    passed: bool
    failed: tuple[str, ...]
    stayers: int
    movers: int
    stayer_clubs: int
    mover_clubs: int
    required_movers: int | None
```

## 3. Measurement functions

```python
def unit_values(inputs: pd.DataFrame, games: pd.DataFrame,
                construct: Mapping[str, object], half_floor: int) -> pd.DataFrame
def normal_scores(values: pd.Series, cells: pd.Series, *, minimum_cell: int,
                  offset: float) -> pd.DataFrame
def club_levels(z: pd.Series, minutes: pd.Series, club: pd.Series, *, leave_one_out: bool,
                minimum_others: int) -> pd.Series
def build_panel(cohorts: pd.DataFrame, origin_scores: pd.DataFrame,
                destination_scores: pd.DataFrame, levels: pd.DataFrame,
                config: Mapping[str, object]) -> tuple[pd.DataFrame, pd.DataFrame]
```

3.1 **Season inputs** (built by the runner, section 6): one frame per corpus-league with
`input_key_columns` and `input_columns` from `player_match_inputs`, mapped back through the
season adapter's identity links to `game_id`, `date`, `team_id` and `player_id`, plus `league`
and `club` (club key). One row per player-match with at least
`minimum_regulation_minutes_appearance` regulation minute; `0.0` where the player has no
qualifying event.

3.2 **`unit_values`**. `games`: `unit_key`, `game_id` (which matches count for the unit:
main-club matches; in the public arm the matches of one side). Sort a unit's games by
`(date, game_id)`; index parity gives half A (even) and B (odd). Output per `unit_key`:
`minutes`, `value`, `minutes_a`, `value_a`, `minutes_b`, `value_b`, each value
`scale * sum(numerator) / sum(denominator)`; a denominator of zero, or below the construct's
`minimum_denominator` when it is not null, gives NaN for that value (whole unit or half);
`value_a` and `value_b` are NaN when that half's minutes are below `half_floor`
(`half_floor_minutes_by_side_floor[side floor]`).

3.3 **`normal_scores`**. Within each cell, over finite values only: average ranks `r`
(ties averaged), `u = (r - offset) / n`, `z = NormalDist().inv_cdf(u)`. Cells with fewer
than `minimum_cell` finite values give NaN for every member and are counted. Output
columns `z`, `u`, `cell_units`. The function receives the whole reference population of the
cell (cross-corpus: every outfield player of the corpus-league at the floor; public:
`public_reference_population_rule`), not only analysed units. Half values are scored by a
separate call over the finite half values.

3.4 **`club_levels`**. Minutes-weighted mean of `z` over the club's rows; with
`leave_one_out` the row's own contribution is removed from numerator and denominator.
NaN when fewer than `minimum_others` other finite rows remain (or, without leave-one-out,
fewer than `minimum_others` rows).

3.5 **Cells.** Origin: (`origin_league`, StatsBomb `broad_class` of `modal_broad_class`).
Destination: (`destination_league`, Wyscout role under `wy_position_map`). Public arm: (league
of the side, Wyscout role, side).

3.6 **Panel schema** (the boundary between structure and statistics; one frame per
construct and floor pair; canonical order = sort by `cohort`, `cluster`, then the provider
ids, after which the ids are dropped):

| Column | dtype | Meaning |
|---|---|---|
| `unit` | int32 | running index in canonical order; never a provider id |
| `cohort` | str | `S`, `M_w`, `M_x`, `M_b`; public arm `P_S`, `P_M` |
| `tier` | str | `P`, `A`; `D` (provider-declared id) in the public arm |
| `cluster` | str | origin club key (public arm: before-side club key) |
| `destination_cluster` | str | destination club key (public arm: after-side club key); for the `destination_club_worlds` sensitivity |
| `origin_league`, `destination_league`, `position` | str | `position` is the Wyscout role under `wy_position_map` |
| `role_same` | bool | `role_same_rule` (public arm: True) |
| `second_club`, `origin_club_shared`, `destination_club_shared`, `second_tier_stayer` | bool | protocol flags (public arm: all False except `second_club` for `P_M`) |
| `age_band`, `minutes_band` | int8 | 0, 1, 2 under `band_closure`; `band_missing_value` (-1) when undefined; -1 in the public arm |
| `z_pre`, `z_post`, `u_pre` | float64 | section 3.3 |
| `z_pre_a`, `z_pre_b`, `z_post_a`, `z_post_b` | float64 | half scores; NaN is a hole |
| `level_origin`, `level_destination_prior` | float64 | section 3.4; NaN when undefined |

`build_panel` also returns `reference_post`: `destination_league`, `position`, `z_post`,
`z_post_a`, `z_post_b` for every floor-eligible destination unit, linked or not, without ids
(donor pool for the contamination curve).

## 4. Statistics

```python
@dataclass(frozen=True)
class Worlds:
    clusters: tuple[str, ...]      # sorted
    weights: np.ndarray            # (B, C) int16
    namespace: str                 # sha256 of version, seed, stream, B and the cluster keys, first 16 hex

@dataclass(frozen=True)
class Estimate:
    point: float | None
    decision: tuple[float, float] | None    # decision_quantiles
    reported: tuple[float, float] | None    # reported_quantiles
    valid_share: float

@dataclass(frozen=True)
class ContrastStatistics:
    stayers: int
    movers: int
    dropped_movers: int                       # in matched cells without a stayer (point sample)
    effective_stayers: float                  # Kish size of the point matched weights
    rho_stayers: Estimate                     # matched
    rho_movers: Estimate
    ratio: Estimate                           # tau, matched: the decision statistic
    ratio_unmatched: Estimate                 # reported only
    fisher_difference: Estimate
    fisher_analytic_half_width: float
    spearman_stayers: float | None
    spearman_movers: float | None
    reliability: Mapping[str, Estimate]       # stayers_pre, stayers_post (matched), movers_pre, movers_post
    rho_star_stayers: Estimate
    rho_star_movers: Estimate
    ratio_star: Estimate
    standing_shift: Estimate

def cluster_worlds(clusters: Iterable[str], *, replicates: int, seed: int,
                   stream: int) -> Worlds
def weighted_correlation(weights: np.ndarray, x: np.ndarray, y: np.ndarray,
                         *, minimum_weight: float) -> np.ndarray
def matched_weights(unit_weights: np.ndarray, stayers: np.ndarray, movers: np.ndarray,
                    cell: np.ndarray) -> tuple[np.ndarray, np.ndarray]
def contrast_statistics(panel: pd.DataFrame, stayers: np.ndarray, movers: np.ndarray,
                        worlds: Worlds, config: Mapping[str, object],
                        *, stayer_weights: np.ndarray | None,
                        cluster_column: str) -> ContrastStatistics
def identity_placebos(panel: pd.DataFrame, stayers: np.ndarray, movers: np.ndarray,
                      config: Mapping[str, object]) -> dict[str, object]
def contamination_curve(panel: pd.DataFrame, reference_post: pd.DataFrame, stayers: np.ndarray,
                        movers: np.ndarray, config: Mapping[str, object]) -> list[dict]
def pseudo_movers(panel: pd.DataFrame, stayers: np.ndarray, movers: int,
                  config: Mapping[str, object]) -> dict[str, object]
def rule_comparison(panel: pd.DataFrame, stayers: np.ndarray, movers: np.ndarray,
                    worlds: Worlds, config: Mapping[str, object]) -> RuleComparison | None
def composition_weights(panel: pd.DataFrame, stayers: np.ndarray, movers: np.ndarray
                        ) -> np.ndarray
def attrition_contrast(z_pre: np.ndarray, cleared: np.ndarray, cluster: np.ndarray,
                       worlds: Worlds, config: Mapping[str, object]) -> Estimate
```

| Function | Exact behaviour |
|---|---|
| `cluster_worlds` | `clusters` = every club key of the arm's corpus (cross_corpus: origin corpus; public: every before-side club), sorted. `world_rule`: `rng = np.random.default_rng(np.random.SeedSequence([seed, stream]))`; `weights = rng.multinomial(C, np.full(C, 1 / C), size=B)`. Created once per arm by the runner with `seed_streams.worlds` and passed to every construct, contrast and sensitivity; the `destination_club_worlds` sensitivity builds a second object over destination club keys with `seed_streams.destination_worlds` (R12: declared departure, DISSENT 4) |
| `weighted_correlation` | rows of `weights` are `(B, n)` unit weights. `sw = sum w`; means, `cxy`, `vx`, `vy` with `1/sw` moments; `r = cxy / sqrt(vx * vy)`. NaN where `sw < minimum_weight` (`replicate_minimum_arm_weight`), a variance is not positive, or the result is not finite. Pairs with a NaN in `x` or `y` are removed before the call |
| point estimates | unit weights (one row of ones) through the same code path |
| `matched_weights` | `prior_matching_rule`, per row of `unit_weights`: cell = `position` x bin of `u_pre` (`prior_percentile_bin_edges`, `prior_bin_closure`: right-open, last bin closed); `m_c` mover weight and `s_c` stayer weight per cell; a stayer's matched weight `w * m_c / s_c`; a mover in a cell with `s_c = 0` gets weight 0. Returns the matched stayer weights and the kept mover weights |
| `contrast_statistics` | on the analysed units only (`analysed_unit_rule`). `rho_movers` on (`z_pre`, `z_post`) with kept mover weights; `rho_stayers` with matched stayer weights (times `stayer_weights` when given: composition match); `ratio = rho_M / rho_S`; `ratio_unmatched` with unit stayer weights; `fisher_difference = atanh(rho_S) - atanh(rho_M)`; `fisher_analytic_half_width = 1.6449 * sqrt(1/(n_S - 3) + 1/(n_M - 3))`. Reliability per arm and side: `r` of (`z_*_a`, `z_*_b`) over units with both halves finite, under the same weights, stepped up `2r / (1 + r)` inside each world. `rho_star_g = rho_g / sqrt(rel_pre * rel_post)`, NaN unless each stepped-up reliability exceeds `attenuation_minimum` and each `r > -1` (`attenuation_rule`); `ratio_star = rho_star_M / rho_star_S`. `Estimate.decision` and `.reported` = `np.quantile(..., method=interval_quantile_method)` over finite worlds, `None` when the finite share is below `minimum_valid_replicate_share` |
| standing shift | `d = z_post - z_pre`; the matched cells. Per world: for each cell with positive stayer weight, mover mass `m_c`, weighted stayer mean `s_c`; `D = (sum over those cells of [sum of w*d over movers in c] - m_c * s_c) / sum m_c` |
| `identity_placebos` | for each seed in `identity_placebo_seeds`: inside each pool of `identity_placebo_pool` among analysed units, sorted by `unit`, permute the destination columns (`z_post`, `z_post_a`, `z_post_b`) with `default_rng(<placebo_seed_rule>)`; recompute each arm's point correlation through the same estimator (matched for stayers). Return per arm the sorted permuted values, `point`, `strictly_above_all` (ties fail), `singleton_units`, mean `unchanged_units`. `placebos_passed` = True iff both arms are `strictly_above_all`; None when either is undefined, and None fails (`identity_placebo_none_fails`) |
| `contamination_curve` | for each fraction `f`: `floor(f * n_M + 0.5)` movers (`contamination_count_rule`) chosen without replacement; each gets the destination columns of a uniformly drawn row of `reference_post` in his (`destination_league`, `position`); `contamination_draws` draws from `default_rng(SeedSequence([contamination_seed, index of f]))`; report mean and the decision quantiles of the point `ratio` and the algebraic `(1 - f) * ratio` |
| `pseudo_movers` | `pseudo_mover_rule`: `pseudo_mover_draws` draws from `default_rng(SeedSequence([pseudo_mover_seed, draw]))`; `movers` stayers drawn without replacement with probability proportional to their point matched weight; point `ratio` of the drawn against the rest through `contrast_statistics`' point path; report centre and `pseudo_mover_check_quantiles`; `self_check_passed` = 1 inside those quantiles, bounds inclusive |
| `rule_comparison` | rows: stayers with finite `z_pre`, `z_post`, `level_origin`; movers with those and finite `level_destination_prior`. `None` when movers on those rows are below `transport_rule_minimum_movers`. Per world: weighted least squares of stayers' `z_post` on `[1, z_pre - level_origin, level_origin]` with matched stayer weights (normal equations; a singular world is invalid). Forecasts for movers by `transport_rules`; loss = weighted mean squared error; differences `R1 - R0`, `R1_raw - R0`, `R2 - R1`, `R3 - R1`, `R3 - R2` as `Estimate`s. Coefficients are a function of stayer rows only |
| `composition_weights` | stayer weight = (movers' share of the cell) / (stayers' share of the cell), cell = `position` x `age_band` x `minutes_band` (a `-1` band is its own level); 0 where no mover; movers in cells without stayers are counted |
| `attrition_contrast` | `attrition_contrast_rule`: weighted mean `z_pre` of units that cleared the destination floor minus those that did not, as an `Estimate` |

```python
@dataclass(frozen=True)
class RuleComparison:
    stayer_rows: int
    mover_rows: int
    dropped_movers: int
    coefficients: tuple[float, float, float]     # a, alpha, beta (point)
    losses: Mapping[str, float]                  # R0, R1_raw, R1, R2, R3 (point)
    differences: Mapping[str, Estimate]
```

## 5. Decision

```python
@dataclass(frozen=True)
class Verdict:
    token: str              # decision_vocabulary
    reason: str | None
    flags: tuple[str, ...]

def admission(e11_registry_token: str, e11_admission: Mapping[str, object],
              config: Mapping[str, object]) -> tuple[bool, str | None]
def decide(*, arm: str, admitted: bool, admission_reason: str | None, gate: Gate,
           statistics: ContrastStatistics | None, false_link_share: float | None,
           loss_evaluable: bool, self_check_passed: bool | None,
           placebos_passed: bool | None, config: Mapping[str, object]) -> Verdict
def registry_token(verdict: Verdict, arm: str, e11_admission_status: str | None,
                   config: Mapping[str, object]) -> str
def decide_rules(comparison: RuleComparison | None, compared: bool,
                 config: Mapping[str, object]) -> str
def governing_contrast(origin_league: str, destination_league: str,
                       config: Mapping[str, object]) -> str
def evaluate_contrast(panel: pd.DataFrame, reference_post: pd.DataFrame, *, arm: str,
                      contrast: str, stayer_cohort: str, mover_cohorts: Sequence[str],
                      admitted: bool, admission_reason: str | None,
                      e11_admission_status: str | None, vocabulary_passed: bool,
                      link_bounds: tuple[float | None, float | None, int, int, int],
                      worlds: Worlds, config: Mapping[str, object]) -> dict[str, object]
def same_club_split(panel: pd.DataFrame, worlds: Worlds, config: Mapping[str, object]
                    ) -> dict[str, object]
```

`admission` is `admission_rule`: admitted iff `e11_registry_token` is in
`dependency_agreeing_tokens` and `e11_admission["status"]` in `dependency_admitting_statuses`;
otherwise the reason `not_admitted_reason_map[token]` when the token is not agreeing, else
`not_admitted_reason_map[e11_admission["reason"]]`. A status or reason outside E-11's
`admission_vocabulary` and `exclusion_reason_precedence` raises (a failed run).

`decide` is the protocol's decision table, rows 1 to 14 in order, written as one `if` ladder
with no other entry point. Comparisons: `comparison_rule` (`>=` for lower bounds against the
margin and the floor, `<` for upper bounds, inclusive at both ends of the standing-shift
margin). Any `None` or NaN bound fails the row that needs it (rows 3, 5 and 9 name those
cases); `placebos_passed` that is not `True` fails the placebo condition (row 11); a
`self_check_passed` of `False` is row 6 and `None` (not computed) fails it too. Row 7 is
skipped unless `loss_evaluable`. `arm == "public_winter"` skips row 1 and the vocabulary gate
and calls with `false_link_share = 0.0`, `loss_evaluable = True`. The flag `RATIO_ABOVE_ONE`
is set when `ratio.decision[0] > ratio_flag_lower_bound_above`, under any token.

`registry_token` is `registry_token_rule`. `governing_contrast` is `product_governing_rule`
in its order, returning `NO_ORIGIN_SEASON`, `bundesliga_destination`, `within_league` or
`league_change`; a test covers all 25 pairs of the five leagues.

`evaluate_contrast` enforces the order that makes `INCONCLUSIVE` true to its definition:

1. not admitted: return `{verdict: NOT_ADMITTED, ...}`; **no panel column is read**.
2. the analysed masks (`role_same` for `cross_corpus`, finite `z_pre` and `z_post`, matched
   cells holding a stayer: counting finite values reads no outcome relation), then
   `sample_gate`; failed: return `{verdict: INCONCLUSIVE, gate: ...}`; **neither
   `contrast_statistics` nor any function of section 4 is called** (a test replaces each with
   a function that raises).
3. statistics, pseudo-movers, placebos (both arms), `decide`, `registry_token`; then the
   descriptive outputs of `descriptive_outputs_rule`: `rule_comparison` and `decide_rules`,
   the `ROLE_CHANGED` stratum (`role_changed_rule`: `contrast_statistics` on the
   `ROLE_CHANGED` masks of each arm when each holds `minimum_units_for_any_statistic`; never
   `decide`), and (cross-corpus only) the contamination curve.

Contrasts: `within_league` = `S` against `M_w`; `league_change` = `S` against `M_x`;
`bundesliga_destination` = `S` against `M_b`; `public_winter` = `P_S` against `P_M`.

`same_club_split`: `P_S` rows only; status `REPORTED` iff units reach
`same_club_split_minimum_units`, clusters reach `minimum_clubs_per_arm` and the decision
interval of `rho` is available; else `INCONCLUSIVE` with the first of
`same_club_split_reasons`; then `rho`, its reliabilities and `rho_star` as `Estimate`s.

Sensitivities (`descriptive_outputs_rule`: the `within_league` contrast of each admitted
construct that passed rows 1 and 2; each skipped and counted below
`sensitivity_minimum_movers` movers or `minimum_stayers` stayers): a list of `(label, stayer
mask, mover mask, stayer_weights, worlds)` passed to `contrast_statistics` by
`sensitivity_definitions`; `player_bootstrap` replaces `worlds` by unit-level multinomial
weights within arm x position (`player_bootstrap_sensitivity_seed`); `destination_club_worlds`
passes the destination `Worlds` and `cluster_column="destination_cluster"`; `floors_450`,
`floors_1350` rebuild cohorts, cells and the panel at those floors. No sensitivity reaches
`decide`. The attrition z-contrasts follow the same gate.

## 6. Runner `experiments/run_club_change.py`

```python
def read_dependency(config: Mapping[str, object]) -> Dependency
def e11_config(config: Mapping[str, object]) -> dict
def paired_pairs(e11: Mapping[str, object], dependency: Dependency
                 ) -> tuple[pd.DataFrame, frozenset[int]]
def wide_link(e11: Mapping[str, object], config: Mapping[str, object]) -> pd.DataFrame
def sb_season(folder: str, surface, e11, config) -> tuple[pd.DataFrame, pd.DataFrame]
def wy_season(competition: str, surface, e11, config) -> tuple[pd.DataFrame, pd.DataFrame]
def outcome_inputs(protocol_hash: str, stamp: Mapping[str, object], *, stage: str) -> dict
def public_stage(config, stamp, protocol_hash) -> dict
def licensed_stage(config, dependency, stamp, protocol_hash) -> tuple[dict, dict]
def calibrate(config, *, out: Path | None = None) -> dict
def execute(config, *, verify: bool = False) -> int
def main(argv: Sequence[str] | None = None) -> int
```

| Piece | Rule |
|---|---|
| `e11_config` | E-11's committed `config.json`, refused unless its `lf_sha256` equals `dependency_config_sha256`; asserts `paired_status == dependency_paired_status` and every construct's definition equal to E-11's `aggregated_player_quantities` entry (`construct_definition_rule`; a missing `minimum_denominator` is null) |
| `Dependency` | frozen dataclass: `registry_tokens: Mapping[str, str]` (from `verdict_for("E-11", subject)` for `dependency_registry_subjects` and `dependency_link_subject`), `admission: Mapping[str, Mapping[str, object]]` (E-11 `results.json` `admission[<construct>]`: `status`, `reason`, `pooled_verdict`, `la_liga_verdict`), `link_usable: bool` (registry token of `dependency_link_subject` equals `dependency_link_usable_token`), `false_link_upper`, `absent_partner_upper` (E-11 `results.local.json` `identity` block with `tiers` == `dependency_identity_block.tiers` and `pool` == its `pool`: `false_link_rate.upper` and `absent_partner_bound`; `None` in `paired_only` mode), `surface_hashes` (`provenance.xt.sb_reference_open_play.hash`, `provenance.xt.wy_reference.hash`), `crosswalk_digests` (`provenance.crosswalk_digests`), `packages` (`provenance.packages`), `committed_hash`, `local_sha256`. Raises unless the local file's sha256 equals `provenance.local_results_sha256` of the committed file and every registry token equals E-11's `results.json` `verdicts[<subject>].token` |
| `paired_pairs` | E-11's crosswalk, reproduced call for call (E-11 PIPELINE sections 3 and 7): for each entry of E-11's `subsets` in order, `read_matches(sb_root, sb_folder)` (absent files dropped); `read_wyscout_matches(wy_raw_root, wy_competition)`; `teams = pd.read_parquet(wy_parquet_root/teams.parquet, columns=["team_id", "team_name"])`; `crosswalk_matches(sb, wy, teams, e11, subset=key)`; the linked matches with no row in that competition's `actions.parquet` or none in its `lineups.parquet` (column `game_id`) removed (`WY_ROWS_ABSENT`); `assign_match_keys(kept, e11)`; `read_team_sheets(sb_root, folder, ids, cap=e11.regulation_minutes_cap, regulation_periods=e11.sb_regulation_periods, goalkeeper_position=e11.sb_goalkeeper_position, dismissal_card_types_exclude=e11.sheet_minutes_waiver.sb_dismissal_card_types_exclude, spell_end_reason_contains=e11.sheet_minutes_waiver.sb_spell_end_reason_contains)` per subset; `read_wyscout_team_sheets(wy_raw_root, competition, ids, cap=e11.regulation_minutes_cap, red_cards_not_equal=e11.sheet_minutes_waiver.wy_red_cards_not_equal)`; `read_wyscout_people(wy_raw_root)`; `team_sheet_crosswalk(sb_sheets, wy_sheets, wy_people, match_links, e11)`. Keeps the pairs with status `dependency_paired_status`. Asserts `crosswalk_digest(match_links, ["sb_game_id", "wy_game_id"])` and `crosswalk_digest(paired, ["sb_player_id", "wy_player_id"])` equal E-11's (else a failed run, exit 3). Returns the pairs (memory) and the Wyscout game ids of the `la_liga` subset's linked matches |
| surfaces | `statsbomb_reference_surface(sb_root, e11, variant="open_play")`, `wyscout_reference_surface(spain_actions, <la_liga ids>, e11)`; `sha256(xt.values.tobytes())` must equal E-11's recorded hashes (else a failed run, exit 3; the machine condition of `dependency_machine_rule` is checked before, as a refusal). `wy_public_spain` = `wyscout_reference_surface(spain_actions, [], e11)` in the public stage, its hash recorded in the public provenance. A `SurfaceUnfit` is a failed run |
| `wide_link` | `link_left_row_rule`: per origin folder, `read_matches` and `read_team_sheets` with E-11's keywords over every listed match; rows with at least `minimum_regulation_minutes_appearance` minute; per `sb_player_id` the row of his last match by (`date`, `sb_game_id`) gives `left_id`, `full_name` (`player_name`), `known_as` (`player_nickname`), `country`; `sb_people_disagreeing` counted. `right = provider_crosswalk._right(read_wyscout_people(wy_raw_root))`. Then `name_nationality_link(left, right, e11, tiers=["A"], exclude_right=None, unique_right=True)`; links = rows with `outcome == "LINKED"`. Called only when `Dependency.link_usable` |
| `sb_season` | E-11's readers have no season entry point, so the runner feeds them identity links. For one folder: `read_matches` (asserts `origin_expected_matches` and no absent file); `read_team_sheets` with E-11's keywords; `sb_spell_positions(sb_root, folder, ids, cap=e11.regulation_minutes_cap, regulation_periods=e11.sb_regulation_periods)`. `match_links` in E-11's schema: `match_key` 0..M-1 by `sb_game_id`, `subset` = folder, `sb_game_id`, `wy_game_id` = `sb_game_id`, `date`, `swapped` False, `duration` "Regular", `goal_check` "skipped", `sb_home_team_id`, `sb_away_team_id`, `wy_team_for_sb_home` / `_away` = the StatsBomb team ids. `pairs`: one row per sheet player, `sb_player_id` = `wy_player_id` = his id, `status` = `dependency_paired_status`, `sheets_named` = `sheets_together` = `sheets_structure_passed` = 0, `swap_impossible` False, `is_goalkeeper` False (outfield is decided downstream by `outfield_rule`, one rule for units and adapter alike). `dropped` = an empty frame (`match_key`, `sb_player_id`). Then, in chunks of `season_reader_chunk_matches` matches by `sb_game_id`: `harmonise_statsbomb(read_events(sb_root, folder, chunk, scale=e11.sb_location_scale), links_chunk, pairs, e11, variant="open_play")`, `sheet_minutes(sheets_chunk, links_chunk, pairs, dropped, provider="statsbomb")`, `player_match_inputs(frame, minutes, surface, e11)`; keep `input_key_columns` and `input_columns`; drop rows below `minimum_regulation_minutes_appearance`; map `match_key` to `sb_game_id` and `date`, `player_key` and `team_key` to the ids (identity). Returns the inputs and the people frame (`sb_player_id`, names, country, and the spells). Peak memory stays under 1.5 GB |
| `wy_season` | the same with `read_wyscout_matches` (asserts `destination_expected_matches`), `read_wyscout_actions(wy_parquet_root, competition)` (column list; `provider == {"pappalardo"}` asserted by it), `read_wyscout_team_sheets` with E-11's keywords, identity links on Wyscout ids (`sb_game_id` = `wy_game_id`, `sb_home_team_id` = `wy_team_for_sb_home` = the home team), `harmonise_wyscout(actions, links, pairs, e11)`, `sheet_minutes(..., provider="wyscout")`. People from `read_wyscout_people` (role code) and `PappalardoProvider(wy_raw_root).players()` (`birth_date` only) |
| `outcome_inputs` | the only function that opens an event or action file of a real season. Raises `RuntimeError` unless `protocol_hash` equals `lf_sha256` of the committed protocol and `stamp` is the committed calibration stamp for the current config, pipeline and source hashes. `stage="public"` never touches `sb_root` |
| writing | `Path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8", newline="\n")`. Never shell redirection. No timestamp in any payload. All serialisation checks (size, `results_key_denylist`, `banned_key_paths(..., parts=BANNED_KEY_PARTS)`, provider-named keys, licence-guard patterns, and for the `cross_corpus` `results.json` no `int` and no `float`) run on in-memory objects before any file is written; `results.local.json` is written last |

CLI.

| Command | Reads | Writes | Real outcome data |
|---|---|---|---|
| `calibrate [--out PATH]` | config only | `calibration.json` under `local_output_root` | no (synthetic) |
| `execute` | everything | public `results.json` and tables under `public_output_root`; `results.local.json`, `cross_corpus` `results.json`, `report_tables.md` under `local_output_root` | **yes; root only, once** |
| `execute --verify` | everything | `determinism.json` | yes; root only, once |

`execute` refuses (exit 2, one-line reason naming the failed condition) unless all hold:

1. git is available and the work tree is clean for the protocol files and every file in
   `source_hashes`.
2. For each of `protocol_files` under `committed_experiment_dir`, `protocol_commit = git log
   --diff-filter=A --format=%H -- <path>` (last line) is non-empty and the same for the
   three, `git log <protocol_commit>..HEAD -- <path>` is empty, and the working file's
   `lf_sha256` equals that of `git show <protocol_commit>:<path>`; the copies under
   `public_experiment_dir` are byte-equal to them. `pipeline_spec_sha256` equals `lf_sha256`
   of the registered `PIPELINE.md`. The commit is derived, never typed.
3. `calibration.json` under `committed_experiment_dir` is tracked at `HEAD`; `lf_sha256` of
   the working file, of `git show HEAD:<path>` and of the local stamp are equal; `passed` is
   true; its config, pipeline and source hashes equal the current ones.
4. No E-11 record read (`dependency_registry_subjects`, `dependency_link_subject`) is
   `PENDING` in `galactico/domain/verdicts.py` (ROOT 2.8 Y4); E-11's committed `results.json`
   and local `results.local.json` exist and agree (`read_dependency`); E-11's protocol commit
   is an ancestor of `HEAD`; E-11's protocol, config and pipeline hashes equal
   `dependency_protocol_sha256`, `dependency_config_sha256` and `dependency_pipeline_sha256`;
   the three E-11 modules equal `dependency_source_sha256`.
5. The machine and packages equal E-11's `provenance.packages` (`dependency_machine_rule`).
6. Every value of `sb_folder_digests` is non-null and equals the `folder_manifest` digest of
   that folder; no path under `sb_forbidden_roots` is opened.
7. `local_output_root` resolves under `data/licensed/` and `public_output_root` under
   `data/public/`; `PROVIDERS["statsbomb"].tier` is `LOCAL_LICENSED`;
   `assert_may_host("pappalardo")` is called before any public read; every Pappalardo file
   of section 9 exists.
8. Without `--verify`: `results.local.json` does not exist (one execution), and if
   `failed_runs.json` exists the committed `analysis.md` contains the sha256 of its bytes.
   With `--verify`: it exists.

**The vocabulary gate (E-11 section 14, item 7).** After the refusals and before any event is
harmonised, `folder_vocabulary(sb_root, folder)` for every folder of
`sb_vocabulary_checked_folders` is compared with E-11's `sb_known_event_kinds`,
`sb_known_pass_types`, `sb_known_shot_types` and `sb_known_duel_types`. A name outside a list
fails the `UNKNOWN_VOCABULARY` gate: no StatsBomb event is harmonised, every `cross_corpus`
subject of an admitted construct is `INCONCLUSIVE (UNKNOWN_VOCABULARY)`, and the run completes
with its files. The public stage is unaffected.

**A failed execution (E-11's policy, word for word where quoted).** "Any exception after the
refusal checks appends one record to `<local_output_root>/failed_runs.json` (exception type,
stage name, the file and line of the innermost frame in the" E-12 "source files, and source
hashes; never the exception message, which can hold a count or an identifier) and exits 3. No
value from a failed run may be printed, logged or read. The repair may touch only the failing
stage; the" calibration "stamp is regenerated and recommitted. A gate that fails is not an
exception: it is a verdict." An exception while files are being written removes every file
this execution wrote, then appends to `failed_runs.json`. `StructureError`, a digest or
surface-hash mismatch and `SurfaceUnfit` are such failures. Stage names: `hashes`,
`dependency`, `public`, `vocabulary`, `crosswalk`, `surfaces`, `wide_link`, `seasons`,
`cohorts`, `panels`, `contrasts`, `descriptive`, `serialise`.

Exit codes: `exit_codes`. `--verify` recomputes every payload, compares bytes with the files
on disk, writes `determinism.json` (`equal`, the sha256 values) and exits 4 on any difference.

**The single command the root runs for the real execution** (after the protocol commit,
after the calibration stamp's commit, and after E-11's results commit):

```powershell
.venv\Scripts\python.exe -X utf8 experiments/run_club_change.py execute
```

then once `... execute --verify`, then copy the `cross_corpus` `results.json` into
`committed_experiment_dir` and the public `results.json` into `public_experiment_dir`,
unchanged. Expected wall time: about ten minutes, dominated by reading 1,517 StatsBomb event
files once.

## 7. Synthetic generator and calibration

```python
def synthetic_panel(rng: np.random.Generator, scenario: Mapping[str, object],
                    config: Mapping[str, object]) -> tuple[pd.DataFrame, pd.DataFrame]
def run_calibration(config: Mapping[str, object], *, panels: int | None = None,
                    replicates: int | None = None) -> dict[str, object]
```

Generator, fully specified (the draft's reference to a design prototype outside the tree is
withdrawn). Parameters default to `calibration_defaults` (a design grid, not formed from any
corpus count: `calibration_defaults_basis`), overridden per scenario.

1. Reference population: `clubs` x `players_per_club` origin players
   (`calibration_reference_population`), each at a club `c` and a position drawn uniformly
   from three labels (used as cells and placebo pools). Team effect `T_c ~ N(0, g)`, own
   part `o_i ~ N(0, 1 - g)`, `g = team_variance_share`; `t_pre = T + o`.
2. Prior observation: half reliability `q = rel / (2 - rel)` with `rel =
   reliability_stayers` (movers re-drawn with `reliability_movers` once chosen); each half
   `sqrt(q) * t + sqrt(1 - q) * noise`; full = mean of halves; normal scores within position
   over the whole population, per side and half.
3. Draw `stayers` linked players without replacement by `stayer_selection`, then `movers`
   from the rest by `mover_selection` (`calibration_selection_rules`, on the observed prior
   percentile `u_pre`). A mover's destination club is a different club chosen uniformly.
4. True destination value, with `s = stability`: stayers `s * t_pre + sqrt(1 - s^2) * e`.
   Movers by `mode`: `scale` gives `s * ratio * t_pre + sqrt(1 - (s * ratio)^2) * e`;
   `team_stays_behind` gives `s * o + sqrt(1 - s^2) * e`; `destination` gives
   `s * (o + T_dest) + sqrt(1 - s^2) * e`. With `h = destination_shock_share` > 0, every
   unit's value becomes `sqrt(1 - h) * value + sqrt(h) * U_d`, `U_d ~ N(0, 1)` one draw per
   destination club, shared by the stayers and the movers there. Add `standing_shift` to
   movers.
5. Destination observation as in step 2 with each arm's reliability.
6. `false_link_share` of movers (`floor(f * n + 0.5)`) receive the destination values of a
   random other player of the population.
7. Normal scores over the whole population per side and half; `level_origin` leave-one-out
   over the origin club; `level_destination_prior` over the destination club's origin
   values. Placebo pools: `cohort_position` (cohort x position, one league), or
   `singleton_movers` (every mover in a pool of his own, so every permuted mover value equals
   the real one).
8. `assumed_false_link_share` is passed to `decide` as `false_link_share` with
   `loss_evaluable` True. Every panel is `ROLE_SAME`.

`run_calibration`: for each scenario, `calibration_panels` panels (or the scenario's own
`panels`), `calibration_bootstrap_replicates` worlds, seed
`SeedSequence([calibration_seed, scenario index])`; each panel goes through
`evaluate_contrast` exactly as a real one. Output per scenario: shares by verdict token, by
reason, by rule verdict; mean point `ratio`, `ratio_unmatched` and `ratio_star`; the share of
panels whose decision interval of `ratio` covers the planted ratio; each requirement with
`required`, `observed`, `passed`. `passed` overall iff every requirement of every scenario
holds. `calibration.json` = that dict plus `config_hash`, `pipeline_hash`, `source_hashes`
and `version`; no key names a provider.

Requirements (frozen in `calibration_scenarios`). The prototype column is the reviser's
scratch prototype of this generator and the revised rule (400 panels, 400 origin-club worlds;
not in the tree; REVIEW-RECORD gives its numbers in full), shown so that a failing port can
be told from a failing design. The three rule scenarios were not prototyped in this revision;
their figures are the draft's, from a prototype that is not in the tree and cannot be
reproduced from it.

| Scenario | Plants | Requirement | Prototype |
|---|---|---|---|
| `planted_equivalence` | ratio 1.0 | `ORDER_PERSISTS_WITHIN_MARGIN` >= 0.85; `ORDER_REDUCED_BEYOND_MARGIN` <= 0.01; mean ratio within `calibration_recovery_tolerance` of 1.0 | 0.90; 0.00; 1.002 |
| `planted_null_at_margin` | ratio 0.80 | each directional verdict <= 0.10; mean ratio within tolerance of 0.80 | 0.048 and 0.035; 0.800 |
| `planted_loss` | ratio 0.5 | reduction >= 0.90; persistence <= 0.01; mean ratio within tolerance of 0.5 | 0.968; 0.00; 0.502 |
| `reliability_artefact` | reliability 0.89 stayers, 0.80 movers | reduction <= 0.02; mean raw ratio in [0.86, 0.94]; mean disattenuated ratio in [0.95, 1.05] | 0.00; 0.911; 1.008 |
| `false_links_adjusted` | 25% false mover links, bound 0.25 | reduction <= 0.02 | 0.00 |
| `false_links_unadjusted` | same, bound 0 | reduction >= 0.04 (non-vacuity: the guard acts; exempt from the test tolerance) | 0.105 |
| `no_stayer_persistence` | stability 0.1 | reason `STAYER_PERSISTENCE_BELOW_FLOOR` >= 0.95; each directional verdict <= 0.01 | 1.00; 0.00 |
| `planted_gate_failure` | 1,097 stayers, 29 movers | `INCONCLUSIVE` = 1.0 and no function of section 4 called (structural; exempt) | 1.00 |
| `planted_standing_shift` | movers shifted by -0.5 | reason `STANDING_SHIFT_OUTSIDE_MARGIN` >= 0.85; persistence <= 0.02 | 0.968; 0.00 |
| `planted_null_standing_shift` | movers shifted by -0.25 (the margin) | persistence <= 0.10 | 0.075 |
| `planted_identity_stress` | `singleton_movers` pools | persistence = 0 (structural; exempt); reason `IDENTITY_STRESS_NOT_PASSED` >= 0.80 | 0.00; 0.902 |
| `planted_movers_selected_on_prior` | ratio 1.0, movers from the top half of the prior | persistence >= 0.20; reduction <= 0.02; mean ratio within `calibration_selection_recovery_tolerance` of 1.0; mean unmatched ratio <= 0.80 (non-vacuity: the restriction is planted; exempt) | 0.305; 0.00; 0.970; 0.755 |
| `planted_null_stayers_selected_on_prior` | ratio 0.80, stayers from the top 60% of the prior | each directional verdict <= 0.10 | 0.005 and 0.085 (the draft's unmatched rule: persistence 0.142) |
| `planted_null_destination_shock` | ratio 0.80, destination shock 0.2 | each directional verdict <= 0.10; coverage of the planted ratio >= `calibration_coverage_minimum` | 0.04 and 0.035; 0.90 |
| `rules_team_level_stays` | movers keep own deviation only | `OWN_DEVIATION_PREFERRED` >= 0.75 | 0.90 (draft) |
| `rules_everything_travels` | movers keep everything | `NO_RULE_PREFERRED_OVER_CARRY_FORWARD` >= 0.90 | 1.00 (draft) |
| `rules_destination_level` | movers take the destination level | `DESTINATION_LEVEL_PREFERRED` >= 0.80 | 0.91 (draft) |

`tests/test_club_change_rule.py` runs the same scenarios at `calibration_test_panels` panels
with each bound relaxed by `calibration_test_tolerance`, except the requirements of
`calibration_tolerance_exempt` and those marked `tolerance_exempt`, which are tested as frozen
(it must stay under a minute in the data-free CI job); the full run is the `calibrate`
command.

## 8. Result shapes

All files are aggregate only: no player, club or match identifier, no name, no row per
player. `null`, never NaN. Committed files under `maximum_results_bytes`, local ones under
`maximum_local_results_bytes`. No key names a provider.

**`results.local.json`** (LOCAL; never committed).

| Key | Content |
|---|---|
| `experiment`, `version`, `tier` | `E-12`, config `version`, `LOCAL_LICENSED` |
| `provenance` | section 9 in full, with the verbatim config, `packages` (python, numpy, pandas, pyarrow, the BLAS library and version numpy reports, `platform.platform()`, `platform.processor()`) |
| `dependency` | per construct: E-11 registry token, `status`, `reason`, `pooled_verdict`, `la_liga_verdict`, `admitted`, E-12's not-admitted reason; the link token; `identity_mode` (`wide` or `paired_only`); the two bounds; `surface_hashes_equal`, `crosswalk_digests_equal` |
| `structure` | club crosswalk counts; link counts by tier and by loss reason; `sb_people_disagreeing`; modal-rule ties and unmapped minutes; per floor pair: cohort counts with `ROLE_SAME` and `ROLE_CHANGED` counts, flags' counts, position mix, distinct origin and destination clubs per cohort, cells (count, smallest, excluded), cohort-to-analysed attrition by reason per construct and contrast |
| `attrition` | the protocol's attrition table, with the gated z-contrasts |
| `identity` | `false_link_share` and `loss_evaluable` per contrast |
| `contrasts` | list; one object per construct x contrast: `construct`, `contrast`, `role`, E-11's four values and suffix, `verdict` (decision token), `registry_token`, `reason`, `flags`, `gate` (with `required_movers`), `role_changed_share` (stayers, movers), `statistics` (every field of `ContrastStatistics`, `null` when not compared), `pseudo_movers`, `placebos` (per arm: sorted values, `point`, `strictly_above_all`, `singleton_units`), `contamination`, `rule_comparison`, `rule_verdict`, `role_changed` (the stratum, or `null`) |
| `sensitivities` | list; `label`, `construct`, `stayers`, `movers`, `rho_stayers`, `rho_movers`, `ratio` with both intervals, `ratio_star`. No verdict |
| `uncertainty_limit`, `product_effect`, `attribution` | fixed strings from the protocol and config |

**`cross_corpus` `results.json`** (committed under `committed_experiment_dir`). It holds no
`int` and no `float` anywhere (`bool` is allowed and is tested before `int`), and every string
outside `experiment`, `version` and `provenance` is a token, reason code, flag, key name or
value frozen in `config.json` or in E-11's vocabularies; the runner asserts both (the
registry test of LOCAL directories reads the same).

| Key | Content |
|---|---|
| `experiment`, `version`, `tier` | `registry_experiment_id`, `version`, `LOCAL_LICENSED` |
| `provenance` | `protocol_commit`, `protocol_hash`, `config_hash`, `pipeline_hash`, `source_hashes`, `packages`, `versions`, `calibration_hash`, `local_results_sha256`, `providers` (`results` of both), `dependency` (E-11's protocol, config, pipeline and results hashes). No config echo |
| `admission` | per construct `{registry_token, status, reason, pooled_verdict, la_liga_verdict, admitted, not_admitted_reason}` |
| `identity_mode` | `wide` or `paired_only` |
| `gates` | per subject `{passed, failed}` (booleans and codes) |
| `rule_verdicts` | per subject |
| `verdicts` | `{"<contrast>:<construct>": {token, reason, decision_token, flags}}` for the three contrasts x five constructs; `token` is the registry token |
| `attribution`, `uncertainty_limit`, `product_effect` | fixed strings |

**Public `results.json`** (committed under `public_experiment_dir`; written by the public
stage, which reads no StatsBomb file).

| Key | Content |
|---|---|
| `experiment`, `version`, `tier` | `E-12`, config `version`, `PUBLIC` |
| `provenance` | `protocol_commit`, `protocol_hash`, `config_hash`, `pipeline_hash`, `source_hashes`, `packages`, `calibration_hash`, `providers` (`public_block_providers`), `surface` (`wy_public_spain` hash and match count), the Pappalardo data hashes. No config echo |
| `cohort`, `attrition` | the public counts |
| `same_club_split` | per construct: `status`, `reason`, `units`, `clubs`, `floor_minutes`, `correlation`, `disattenuated`, `reliability_before`, `reliability_after`, each `{point, decision, reported}` |
| `movers` | per construct: `gate` (`passed`, `failed`, `movers`, `stayers`, `stayer_clubs`, `mover_clubs`, `required_movers`, `side_floor_minutes`), `statistics` or `null` |
| `verdicts` | `{"public_winter:<construct>": {token, reason, flags}}` |
| `attribution` | the Pappalardo citation |

`report_tables.md` is generated from `results.local.json` and the public payload so no number
in `analysis.md` is retyped; it prints counts below `small_count_suppression_below` as `<5`.

**Registry records** (root adds them, `PENDING`, in the registration commit; section 13).
Common: `experiment_id = registry_experiment_id`, `non_claim` from `registry_common`,
`not_run_statement` = `registry_common.not_run_statement` with `{construct}` replaced by
`construct_display_names[construct]`, `protocol_hash` and `config_hash` = `lf_sha256` of the
registered files. Cross-corpus records (15): `subject_id` = `<contrast>:<construct>`,
`tier = Tier.LOCAL`, `directory = committed_experiment_dir`, `scope` and `claim_token` from
`registry_cross_corpus`, `vocabulary = verdict_vocabulary.cross_corpus`, outcomes from
`registry_outcomes.cross_corpus` (status, limits, statement with `{construct}` filled). Public
records (5): `subject_id` = `public_winter:<construct>`, `tier = Tier.PUBLIC`, `directory =
public_experiment_dir`, `registry_public_winter`, `verdict_vocabulary.public_winter`,
`registry_outcomes.public_winter`. After the run each record takes its `token` from
`verdicts[subject].token` of its directory's `results.json`, `protocol_commit` and
`results_hash`; a public record takes, as `Figure`s, the entries of
`registry_figures.public_winter` whose `when` holds, each `value` read at its `pointer` with
`{construct}` filled, each with its own sentence. No sentence V7 reads holds a digit other than
`E-12`. The config holds no `product_outcomes` key: the registry test's vocabulary check reads
`verdict_vocabulary` as a map of the two vocabularies.

## 9. Hash discipline

| Object | Hash |
|---|---|
| `preregistration.md`, `config.json`, `PIPELINE.md` | `lf_sha256` (CRLF to LF, then sha256). The checkout has `core.autocrlf=true`; a raw-byte hash does not reproduce |
| source files | `lf_sha256`, keys as posix paths relative to the repository root: `galactico/validation/club_change.py`, `experiments/run_club_change.py`, every file in `dependency_source_files`, `galactico/validation/digests.py`, `galactico/models/xt/grid.py`, `galactico/models/xt/__init__.py`, `galactico/identity/resolver.py`, `galactico/providers/base.py`, `galactico/providers/pappalardo.py`, `galactico/domain/verdicts.py`, `galactico/domain/thesis.py`. No path holds a provider's name |
| E-11 | `lf_sha256` of its committed protocol, config, pipeline and `results.json`, asserted against the `dependency_*_sha256` keys; sha256 of its `results.local.json` bytes, asserted against its committed `local_results_sha256` |
| StatsBomb raw JSON | `folder_manifest` digest per folder used (the four 2015/16 folders against `sb_folder_digests`; the two double-coded folders against E-11's `sb_folder_digests`): byte-exact; these files never pass through git |
| Pappalardo raw JSON | byte-exact sha256 of `players.json`, `teams.json` and the five `matches_<League>.json` |
| Pappalardo Parquet | content hash, never file bytes (the footer embeds the pandas version), of the whole file as `pd.read_parquet(<file>)` returns it: sort by `["game_id", "period", "seconds", "event_id"]` (actions), `["game_id"]` (matches), `["game_id", "player_id"]` (lineups), `["team_id"]` (`teams.parquet`, whose names feed the club keys); `sha256(pd.util.hash_pandas_object(frame, index=False).values.tobytes())` |
| season input frames | the same content hash after sorting by `["game_id", "player_id"]`, per corpus-league; local file only |
| surfaces | `sha256(xt.values.tobytes())`; the two `cross_corpus` surfaces asserted equal to E-11's on E-11's machine; `wy_public_spain` recorded |
| crosswalk | E-11's `crosswalk_digest` of the match links and of the paired pairs, asserted equal to E-11's; the combined link table gets a digest and counts in the local file only |
| panels | content hash per construct and floor pair, local file only |
| `protocol_commit` | derived from git by the runner |
| determinism | sha256 of the bytes of every result file, first run and verify run |

## 10. Synthetic test suite (data-free unless marked)

| File | Tests |
|---|---|
| `test_club_change_structure.py` | `club_keys` on the 12 aliases, on accents and on a name that is a substring of another; `assert_club_crosswalk` passes on a synthetic 66 / 14 / 14 / 18 layout and raises on a missing alias, a duplicate and a miscount; `combine_links` precedence, conflict, twice-claimed, `paired_only`, and a synthetic E-11 pair frame with status `PAIRED_BY_TEAM_SHEET` gives a non-empty tier P (a `VERIFIED_BY_TEAM_SHEET` row gives none); `sb_spell_positions` against `read_team_sheets` on synthetic lineup files (minutes parity, `is_goalkeeper` parity); `modal_broad_class` on every StatsBomb position name, "Right Wing Back" is DF, the review's instance (400 minutes Right Midfield, 300 Right Wing, 300 Left Wing: class FW), ties to the earliest spell, unmapped names counted; `role_same` against `wy_position_map`; `season_summary` tie, second club, minutes at the main club only, zero-minute rows dropped; every cohort of the protocol table from hand-built lineups, including same main club with a second club, a Bundesliga destination, a mover whose origin club is absent; floors per construct (900 / 1,800); `public_cohorts` winter rule, summer mover rejected, interleaved rejected, split-date boundary (a match on the split date is "after"), goalkeeper rejected, a 0-minute row is no appearance; `unit_values` halves by own match order, zero and below-minimum denominators are NaN not zero, half floors, row-order invariance; `normal_scores` ties, minimum cell, NaN in and out, symmetric around zero, `u` in (0, 1); `club_levels` excludes the unit's own value and respects the minimum; `false_link_share` against a hand calculation, `None` bounds and the cap; `sample_gate` every code, the vocabulary code first, the boundary `0.0179`, counts at 3; `required_movers` at 313, 1,097, 592 and a non-positive denominator |
| `test_club_change_statistics.py` | `weighted_correlation` equals `np.corrcoef` on rows repeated by integer weights (oracle uses repetition, not weights); point estimate equals the unit-weight world; `matched_weights` against an explicit loop, movers in cells without stayers dropped, bins right-open with the last closed; the matched ratio removes a planted restriction of the prior (synthetic, oracle on a large panel); standing shift equals an explicit double loop written from the protocol sentence; Spearman-Brown inside the world, not after; disattenuated value missing below `attenuation_minimum` and when both stepped-up reliabilities are negative; `rule_comparison` coefficients equal `np.linalg.lstsq` on stayer rows repeated by weight and are unchanged when every mover's `z_post` is replaced; all rules scored on identical rows; `cluster_worlds` deterministic, sorted, shared: two constructs given the same `Worlds` see identical weights; row-order invariance of every statistic; placebos: pools respected, counts preserved, the seed derivation fixed (a pinned vector), singletons unchanged and counted, permuted correlation near zero on a planted strong panel; contamination curve close to `(1 - f)` times the clean ratio; pseudo-movers centred near 1 on an exchangeable panel and `self_check_passed` False on a planted biased estimator; invalid worlds counted and an interval withheld below the valid share; non-vacuity: at least one test panel yields each of a finite and a missing interval |
| `test_club_change_rule.py` | the decision table as a truth table written by hand from the protocol (it imports only `decide`): every row, every boundary (`L == m` passes row 8, `U == m` fails row 7, `D` bound equal to the margin passes), NaN and None in each position, `placebos_passed` None reaching row 11, a missing `D` interval reaching row 9, the review's case (L(tau) 0.82, U 1.0, L(tau*) 0.5, U(tau*) 0.75) reaching row 13, `loss_evaluable` False moving a case from row 7 to row 12, the self-check row, public arm skipping row 1; exhaustiveness: a grid over the bounds returns exactly one token and one reason each time and every token and reason is produced at least once; `admission` over every E-11 registry token and every admission status and reason, including an agreeing token with `EXCLUDED (LA_LIGA_SUBSET_UNTESTED)` and `INCONCLUSIVE` with an admitting status; `registry_token` with and without the suffix; `decide_rules` every branch including `RULES_INTERVAL_UNAVAILABLE`; `governing_contrast` over all 25 league pairs; `evaluate_contrast` computes nothing for a construct that is not admitted and nothing behind a failed gate, descriptive outputs included (each section 4 function patched to raise); the reduced calibration (section 7) |
| `test_club_change_runner.py` | `execute` refuses: without git, on a dirty tree, with a protocol differing from its commit or a public copy differing from it, with a pipeline hash mismatch, without or with a stale, uncommitted or failed calibration stamp, while a synthetic E-11 record is `PENDING`, with a registry token differing from E-11's `results.json`, without E-11 results, with a local file whose sha256 differs from E-11's committed record, on a machine or package mismatch, with a null folder digest, with an output root outside `data/licensed/` or `data/public/`, on a second execution, and after a failed run not recorded in `analysis.md`; the vocabulary gate turns every admitted `cross_corpus` subject `INCONCLUSIVE (UNKNOWN_VOCABULARY)`; end to end on a synthetic corpus written to `tmp_path` (provider-shaped files built with `dict(...)`): planted full persistence returns `ORDER_PERSISTS_WITHIN_MARGIN` for the primary subject and the public arm returns `INCONCLUSIVE` with statistics `null`; two runs byte-identical; `allow_nan=False`; size ceilings; denylist, banned-part and provider-name key walks on every file and on the config; `scripts/check_licensing.check` passes on both `results.json` and `calibration.json`; no `int` or `float` in the `cross_corpus` `results.json`; the public stage completes with `sb_root` pointing at a missing directory, its surface hash is unchanged by that, and its block is byte-identical to the block from a full run; no file is created outside the two output roots (directory snapshot before and after); no payload string equals any synthetic player or club name; `import galactico.api` leaves `galactico.validation.club_change` out of `sys.modules`; a failed stage appends a record without its message and exits 3; `@pytest.mark.slow` structure check on the real caches (skips cleanly when absent): the club crosswalk assertion holds and the public structural counts equal `public_structural_counts`. It reads lineups and match lists only |

Oracles are written from the protocol text with plain loops, `itertools` and
`np.corrcoef` / `np.linalg.lstsq`, and import no helper from the module under test.

## 11. Pre-outcome code review checklist

Run by a reviewer who did not write the code, on synthetic data, before `execute`.

1. The protocol files in both experiment directories are byte-equal (LF) to this folder's,
   save the two registration edits of the protocol, and `pipeline_spec_sha256` matches.
2. Every numeric literal in `club_change.py` and the runner is `0`, `1`, `2`, `3` (the
   `n - 3` of the gate), `0.5` or `1.6449`, or comes from config. Grep for others.
3. Every key of `config.json` is read by code or echoed in the local provenance; none is
   unused.
4. E-11 functions are imported, not copied; their source hashes are in provenance; the
   runner contains no pass-type, shot-type or channel literal; the private names imported
   (`_spell`, `_requested`, `_file`, `_right`) are exactly those of section 0.
5. The machine check, the E-11 hashes, the registry tokens and the `PENDING` refusal precede
   any read of a season; the surface hashes and crosswalk digests are asserted before any
   season is valued.
6. `outcome_inputs` is the only call site that opens a season's events or actions; it is
   reached only after the refusals of section 6; the public stage opens nothing under
   `sb_root`.
7. Links and pairs never reach `to_parquet`, `to_csv`, `to_json`, `pickle`, `print` or a
   log call. Grep the runner for those names.
8. Provider ids are dropped in `build_panel`; no function after it has an id column.
9. Cells use the whole reference population; cohort membership never changes a `z`.
10. Halves alternate by the unit's own match order, not by league-wide parity.
11. `level_origin` is leave-one-out; `level_destination_prior` uses origin-season values only.
12. Stayer coefficients are computed from stayer rows only, inside each world.
13. One `Worlds` object per arm; no function draws its own resampling weights except the
    declared sensitivities.
14. `decide` matches the protocol table row for row; no other code assigns a verdict token.
15. A failed gate or a non-admitted construct returns before any outcome column is read, and
    no descriptive output is computed for it.
16. `ROLE_CHANGED` units enter no verdict-bearing statistic; their stratum never reaches
    `decide`.
17. `false_link_share` enters row 7 only; it never touches row 8.
18. Disattenuated values are reported beside raw values everywhere; nothing prints one
    without the other.
19. The `cross_corpus` `results.json` holds no number; the public one holds nothing from the
    `cross_corpus` arm; no denylisted, banned or provider-named key; under the size ceiling.
20. `calibration.json` passed with the committed config and the reviewed sources and is
    committed.
21. Protocol files are committed; `git log` shows that commit before any results file.
22. The attribution strings and the logo path are present in `analysis.md`'s template and
    in the protocol.

## 12. StatsBomb attribution requirement

Clause 1.4 applies to every publication of analysis formed from StatsBomb data, nulls and
verdict labels included.

| Where | Requirement |
|---|---|
| `preregistration.md` (it prints structural counts formed from StatsBomb lineups) | the logo image and the credit block at its head, ending with the sentence on what is true of the tree; at registration the image path becomes `registration_logo_relative_path` (section 0). The logo is the existing file at `source_logo_path`, unchanged (it is hash-pinned by `tests/test_licensing.py`) |
| `analysis.md`, `report_tables.md` | the logo image and both attribution strings above the first table; the sentence that the conclusions are not StatsBomb's; the sentence on what is true of the tree |
| `cross_corpus` `results.json` | `attribution` with both strings |
| any hosted label derived from a `cross_corpus` verdict | the logo (the `web/assets` copy), `attribution_sb`, and a link to `research_note_path` beside it; no number (ADR-0027 item 4) |
| `results.local.json` | both strings; never leaves the machine |
| tests | the runner test asserts the strings in both payloads and in the report template |

## 13. Shared-file requests to the root

One order: audit; registration (with E-11 `PENDING` or run); the pipeline; the calibration
stamp in a commit of its own; the run, after E-11's results commit.

**Before registration** (nothing below is an outcome): the items of
`verified_by_root_before_registration` and the structure count of
`counted_by_root_before_registration`, each printed in the registration commit; if E-11 has
run, the prior-exposure row of ROOT 2.8 Y4.

**The registration commit** changes hosted output and product code, and says so, under an ADR
that names exactly these edits and overrides R13 and ADR-0011 for them (the form of ROOT 2.10
W8 and 2.12 N5; DISSENT 9):

| File | Change |
|---|---|
| `experiments/preregistered/E-12-transport-movers/` and `-public/` | the registered files (section 0); `experiments/preregistered/README.md` rows for both |
| this draft folder | its files replaced by one line pointing at the registered directory |
| `galactico/domain/verdicts.py` | the 20 `PENDING` records of section 8 (15 LOCAL, 5 PUBLIC); the module docstring's sentence that E-12 is a draft |
| `galactico/api/transfer_lab.py` | the candidate rate row's verdict for the five constructs becomes `verdict_payload("E-12", f"{governing_contrast(origin, destination)}:{metric}")`, origin the candidate's league and destination the scenario's; a German origin keeps the unregistered lookup and prints `product_copy.label.NO_ORIGIN_SEASON`; the E-12 labels, `label_suffix_league_unconfirmed`, `estimator_note` and the carry-over addenda are copied verbatim with a test tying them to this config; the module docstring's "E-12 ... is not registered" |
| `galactico/api/planning.py`, `galactico/api/squad_lab.py` | unchanged lookups (`E-12/<metric>`, `E-12/carry_over`), which still answer `NOT_REGISTERED` truthfully; a comment says why |
| tests that read the registry or E-12 lookups | `tests/test_verdict_registry.py` (registry contents), `tests/test_planning_render.py`, `tests/test_transfer_api.py`, `tests/test_lab_runtime.py`, and the e2e specs that assert the Transfer Lab ledger |
| `tests/test_preregistration_order.py` | both directories under its rule |
| `tests/test_licensing.py` | add the registered `preregistration.md` (both copies) to `FORMED_FROM_STATSBOMB` and the registered `PIPELINE.md` and `REVIEW-RECORD.md` to `NO_FIGURE_FORMED_FROM_STATSBOMB`; remove the draft entries; add `analysis.md` in the commit that first adds it |
| `tests/test_protocol_drafts.py` | an E-12 guard (ROOT 2.10 W9 form): the pipeline hash; every registry sentence and figure sentence through the response boundary under `PENDING` and every token of each arm; the served texts through the copy guard; key walks for provider names, `SB_`, banned parts and the denylist over the config and the result shapes; the public copies equal the originals. Its checks were run on this revision from a scratch script (REVIEW-RECORD) |
| `docs/assets/statsbomb/statsbomb-logo.png` | the existing file, unchanged (in the tree since 9 October 2026) |
| `VALIDATION.md` Phase 5 | replace "rank successful fits above failed ones better than market value does" by a pointer to E-12's claim; that test is not runnable on this corpus |

**After registration, before `execute`:** the pipeline commit (the six files of section 0;
`tests/test_research_firewall.py` gains `club_change` in `RESEARCH_PIPELINES` in that commit);
then `calibration.json`, committed.

**Before any E-12 `cross_corpus` token other than `PENDING` is served:** the Transfer Lab view
that prints it shows the StatsBomb logo, `attribution_sb` and a link to the research note
beside it, and `tests/test_served_credit.py` asserts it on a reply holding an executed E-12
record (ADR-0027 item 4).

**After the run:** the results commit (both `results.json`, `analysis.md`, both
`report_tables.md` extracts as the analyst chooses, the registry tokens, hashes and public
figures).

## 14. Interfaces resolved

Nothing is assumed at registration (the ROOT 2.11 T1 form). The draft's nine assumed
interfaces are settled as follows.

1. **E-11 modules and frames.** The built signatures of section 0, read on 18 October 2026:
   `read_team_sheets(root, folder, game_ids, *, cap, regulation_periods,
   goalkeeper_position, dismissal_card_types_exclude, spell_end_reason_contains)`;
   `read_events(root, folder, game_ids, *, scale)`; `crosswalk_matches(sb_matches,
   wy_matches, wy_teams, config, *, subset)`; `assign_match_keys(links, config)`;
   `team_sheet_crosswalk(sb_sheets, wy_sheets, wy_people, match_links, config)` returning
   `(pairs, dropped, audit)`; `name_nationality_link(left, right, config, *, tiers,
   exclude_right, unique_right)`, neither keyword with a default;
   `harmonise_statsbomb(events, match_links, pairs, config, *, variant)`;
   `harmonise_wyscout(actions, match_links, pairs, config)`; `sheet_minutes(sheets,
   match_links, pairs, dropped, *, provider)`; `player_match_inputs(frame, minutes, xt,
   config)` returning `match_key`, `subset`, `player_key`, `team_key` and the input keys;
   `wyscout_reference_surface(actions, excluded_game_ids, config)`;
   `statsbomb_reference_surface(root, config, *, variant)`. E-11's committed `results.json`:
   `admission[<quantity>] = {status, reason, pooled_verdict, la_liga_verdict}`,
   `verdicts[<subject>] = {token, reason, second_reason}` (the link token at
   `verdicts.wide_link_tier_a.token`), `provenance.local_results_sha256`;
   `results.local.json`: `identity` blocks with `tiers`, `pool`, `false_link_rate.upper`,
   `absent_partner_bound`; `provenance.xt.sb_reference_open_play.hash`,
   `provenance.xt.wy_reference.hash`; `provenance.crosswalk_digests.matches` and `.players`;
   `provenance.packages`. There is no `link_verdicts` key and no season entry point; the
   identity-link adapter of section 6 stays.
2. **Tier A as graded.** No nickname: tier A uses the legal name only (E-11 section 14,
   item 2). The draft's interface 2 was false and is withdrawn.
3. **The tier set.** `[A]` only, and only when `verdicts.wide_link_tier_a.token` is
   `LINK_USABLE`; `[A, N]` and `[A, N, B]` are E-11's record, not E-12's choice.
4. **`D` under order-only admission.** E-11: "Every admission of either kind permits the same
   thing: the quantity may enter a later cross-provider study on within-provider × league ×
   role rank-normal values only." `D` is a difference of such values and enters the verdict
   under both admissions.
5. **Surfaces.** E-11's two reference surfaces for the `cross_corpus` arm, a public surface of
   its own for the public arm (protocol, Surfaces).
6. **`galactico/validation/digests.py`**: `lf_sha256(path)`, `lf_sha256_text(text)`.
7. **ARCH-SPEC.** Module name `club_change`; results contract met with one tier per
   `results.json`; `protocol_commit` derived from git; `VerdictRecord` rules V1 to V7 met by
   records built from this config (REVIEW-RECORD).
8. **PRODUCT-PLANNING 1.9.** E-12 never supplies `figures["retention_reference"]`: no E-12
   estimand is the fraction of a rate. The cross-corpus arm is a ledger label only.
9. **Transfer Lab** reads the governing subject by `product_governing_rule` (section 13).

## 15. Reconciliation with E-11's section 14

E-11's registered `PIPELINE.md` section 14 lists what E-12 must repeat. Each item, quoted,
and the E-12 rule that meets it:

1. "Pair status `PAIRED_BY_TEAM_SHEET` (was `VERIFIED_BY_TEAM_SHEET`)." `dependency_paired_status`;
   tier P; `paired_links_only`; a test that the old status gives an empty tier.
2. "Tier A: the StatsBomb legal name token set equals the Wyscout first-plus-last-name token
   set, both on `name_tokens` ... No nickname. E-12 may use tier set `[A]` only, and only when
   `results.json` `verdicts.wide_link_tier_a.token` is `LINK_USABLE`." Protocol identity table;
   `Dependency.link_usable`, read from the registry and cross-checked with that key.
3. "Admission statuses: four statuses admit, and the two `_LEAGUE_UNCONFIRMED` ones must be
   printed; reasons `LA_LIGA_SUBSET_UNTESTED` and `DECLARED_VARIANT` exclude."
   `dependency_admitting_statuses`, `not_admitted_reasons`, `admission_rule`,
   `registry_token_rule`.
4. "`e_fl` = `false_link_rate.upper` and `e_ap` = `absent_partner_bound` of the
   `results.local.json` `identity` block with `tiers` `["A"]` and `pool` `pooled`."
   `dependency_identity_block`, `dependency_false_link_bound_field`,
   `dependency_absent_partner_bound_field`.
5. "E-12 reads the committed `results.json` (`admission`, `verdicts`) and, being LOCAL itself,
   may read `results.local.json` for the measured link rates. The per-quantity order statistic
   is not a provider attenuation factor ... E-12 imports `read_events` (with `scale =
   sb_location_scale`), `harmonise_statsbomb(variant="open_play")`, the surface rule of
   `statsbomb_reference_surface` ... (the Wyscout one is `xt.wy_reference.hash`, which excludes
   matches chosen by the match crosswalk and so reads StatsBomb: a PUBLIC arm may not use it)
   and `name_nationality_link`, called as `name_nationality_link(left, right, config,
   tiers=["A"], exclude_right=None, unique_right=True)`." Section 6 (`sb_season`, surfaces,
   `wide_link`); `wy_public_spain`; E-12 uses no order statistic of E-11 as a factor.
6. "Config keys were renamed (`sb_*`, `wy_*`); E-12's own config has the same exposure to the
   key check of `tests/test_licensing.py`." `key_naming`; no key names a provider.
7. "Before any event is harmonised it runs `folder_vocabulary` on each of its 2015/16 folders
   and compares the names with `sb_known_event_kinds`, `sb_known_pass_types`,
   `sb_known_shot_types` and `sb_known_duel_types`; a name outside a list stops E-12 before any
   statistic." The vocabulary gate (section 6), and the root's names-only check before
   registration.
8. "E-12 refits on the machine E-11 ran on, under the package versions recorded in E-11's
   `provenance.packages`, and a mismatch is cleared only by running there, never by
   loosening the comparison." `dependency_machine_rule`; refusal 5.
9. "For a season E-12 states its own row rule ... counts the players whose rows disagree, and
   states how it reads StatsBomb position names, which `read_team_sheets` does not return."
   `link_left_row_rule`; `sb_spell_positions`; `sb_modal_broad_position_rule`.
10. "E-12 states that the ordering of its origin percentiles for players whose two labels
    differ was not graded here, and reports beside each contrast the share of linked units
    whose StatsBomb position and Wyscout role differ." ROOT 2.8 Y1 to Y3; `role_changed_rule`,
    `role_changed_sentence`, `role_changed_share` per contrast.

## DISSENT

1. **The cross-corpus arm is unlikely to settle its question.** Synthetic simulation of the
   revised rule at the `ROLE_SAME` planning sizes (313 / 177): a true ratio of 0.9, the only
   published figure, returns `NOT_ESTABLISHED` in about half the panels at an observed stayer
   correlation of 0.75 and three quarters at 0.62; at 0.48, which E-11's own planning makes
   plausible, complete persistence is shown in 0.30 of panels. With the false-link share at
   0.15 a 40% loss is called in 0.22 of panels. `league_change` is expected `INCONCLUSIVE`
   for every construct once Y2 applies. The design satisfies the root decision and says
   this in the protocol: a test that can detect near-complete persistence or a large loss,
   with `NOT_ESTABLISHED` the modal outcome.
2. **ROOT 2.2 counts 31 public movers at 450 minutes on each side.** Under rules that can be
   frozen (outfield, winter window, non-interleaved spells) the count is 29 (one goalkeeper
   and one non-winter case fall out). The gate needs 62. The protocol uses 29.
3. **O1 read strictly also covers some of this protocol's machine-readable constants.** The
   calibration sizes are now a design grid (300 / 160), not rounded local counts. Two kinds of
   number formed in part from StatsBomb files remain in `config.json`: the club crosswalk
   expectations (counts of the provider index's teams joined with the public team list) and
   the La Liga folder digest (already committed by E-11 under the root's ruling of 9 October
   2026). The structural tables are in Markdown with the credit. If the root reads O1 as
   barring the crosswalk expectations, they move to a local file whose digest is pinned.
   **Root ruling requested.**
4. **R12: club-weight worlds.** A world is one multinomial vector over origin club keys,
   shared by every construct, contrast and statistic, not a match-weight vector: the units are
   players across two seasons and two providers, no match is common to both sides, and the
   dependence is by club. Destination dependence is not resampled; on synthetic panels with
   a destination-club shock of a fifth of the variance, the origin-club scheme kept each
   directional verdict at the margin to 0.04 and 0.035 with coverage 0.90, while two-way
   product weights doubled the interval widths and would cost most of the power.
   Destination-club worlds are a reported sensitivity and the shock is a calibration
   scenario. **Root ruling requested** (E-11's DISSENT 5 was accepted for E-11 only).
5. **ROOT 2.5 O5 below 100 units.** `league_change`, `bundesliga_destination` and the public
   mover arm have fewer than 100 analysed units. O5 prescribes an interval on a half-sample
   correlation; E-12's decision statistic is a ratio of persistence correlations, its
   half-sample correlations are reliabilities stepped up inside each world, and its interval is
   the percentile interval of the ratio. **Root ruling requested** that O5 does not apply, as
   for E-11 (its DISSENT 6).
6. **One tier per `results.json`.** The registry tests require that a directory holding a
   LOCAL record commit no number and that each record's tier equal its `results.json` tier.
   The public arm's five PUBLIC records therefore point at a second directory holding
   byte-identical copies of the protocol files and the public `results.json`. The alternative
   is a ruled change to the registry tests (a `tiers` map and a numbered `public_winter` block
   inside one `results.json`), which would let numbers into a LOCAL directory's committed file.
   **Root ruling requested** between the two; this draft is written for the first.
7. **K15's reading.** The primary endpoint is "the quantity Transfer Lab injects" by name;
   the estimator E-12 grades is E-11's harmonised one (ROOT 2.5 O2), which differs from the
   injected one in recipe, surface, club rule and minutes (protocol, Claim). The labels say
   so (`estimator_note`). **Root ruling requested** that a verdict on the research estimator's
   ordering may label the injected rate with that note, or that it may not label it at all.
8. **The admission conjunction.** Y4 says the admitted set is "a function of E-11's registry
   tokens". A registry token can agree while E-11's admission is `EXCLUDED`
   (`LA_LIGA_SUBSET_UNTESTED`, the declared variant), and a token-only rule would admit a
   quantity E-11 says "enters no later cross-provider study". E-12 requires both, reading
   the token from `verdicts.py` and the status from E-11's committed `results.json`.
   **Root confirmation requested.**
9. **Product edits at registration.** Registering E-12 subjects as `<contrast>:<construct>`
   leaves the Transfer Lab's present lookups (`E-12/<metric>`) answering `NOT_REGISTERED` for
   a subject E-12 tests, the defect ADR-0029 repaired for E-11. The registration commit
   therefore edits `transfer_lab.py` under an ADR (section 13). **Root ruling requested** on
   that ADR, in the form of W8 and N5.
