# E-12 pipeline specification

Build target for `experiments/preregistered/E-12-transport-movers/`. The protocol is
`preregistration.md`; every number is in `config.json`; this file is the code contract.
Where this file and the protocol disagree, the protocol wins and the disagreement is a defect.

**Tier rule (binding on every function below).** The `cross_corpus` arm is LOCAL_LICENSED.
Nothing here is imported by `galactico/api`, `galactico/optimization`, `galactico/profiles`,
`galactico/match_lab`, `galactico/models` or `galactico/features`. No link, pair, per-player
row, provider id or name is written anywhere except process memory. The only files written
are aggregate JSON and Markdown under `data/licensed/research/E-12-transport-movers/`
(gitignored); the root copies the committed ones. Until the root runs the real execution,
every module is exercised on synthetic data only. No agent runs `execute`.

## 0. Files and ownership

| File | Owner | Content |
|---|---|---|
| `galactico/validation/transport_movers.py` | E-12 A (sections 2, 3), E-12 B (sections 4, 5, 7) | pure functions: frames in, results out; no IO, no provider import, no E-11 import |
| `experiments/run_transport_movers.py` | E-12 C | CLI `calibrate`, `execute`; all IO; the only place E-11 modules are imported |
| `tests/test_transport_movers_structure.py` | E-12 A | club keys, links, cohorts, values, cells, levels |
| `tests/test_transport_movers_statistics.py` | E-12 B | statistics against independent oracles; shared worlds |
| `tests/test_transport_movers_rule.py` | E-12 B | decision table, rule verdict, gates, calibration (reduced) |
| `tests/test_transport_movers_runner.py` | E-12 C | refusals, output shapes, tier separation, determinism on a synthetic corpus |
| `experiments/preregistered/E-12-transport-movers/{preregistration.md,config.json}` | root commits | from this folder, byte for byte |

A and B build against the panel schema of section 3.6; C builds against sections 2 to 6.
No existing file is edited. Frozen files are untouched.

Naming. The assignment fixed `transport_movers.py` and `run_transport_movers.py`. ARCH-SPEC
8.2 names the same package `club_change.py` / `run_club_change.py` / `test_club_change.py`.
One must be chosen before the build; the rename is mechanical (module, runner, tests,
firewall tuple, `version` in config, directory slug). Nothing else depends on the name.
`galactico/validation/transport.py` (E-07) is a different study and is not imported.

**Reused, unchanged.**

| Reuse | From |
|---|---|
| `normalise_name` | `galactico/identity/resolver.py`. `resolve_player` is not used (it accepts nobody without a birth date) |
| `read_matches`, `read_team_sheets`, `iter_events` / `read_events`, `folder_manifest` | `galactico/validation/statsbomb_reader.py` (E-11) |
| `read_wyscout_matches`, `read_wyscout_team_sheets`, `read_wyscout_people`, `crosswalk_matches`, `team_sheet_crosswalk`, `name_nationality_link`, `crosswalk_digest` | `galactico/validation/provider_crosswalk.py` (E-11) |
| `harmonise_statsbomb(variant="open_play")`, `harmonise_wyscout`, `statsbomb_reference_surface`, `wyscout_reference_surface`, `sheet_minutes`, `player_match_inputs` | `galactico/validation/provider_inputs.py` (E-11) |
| `lf_sha256`, `lf_sha256_text` | `galactico/validation/digests.py` (hardening H1) |
| `PROVIDERS`, `assert_may_host`, `LicenseViolation` | `galactico/providers/base.py` |
| `check` | `scripts/check_licensing.py`, called by tests on every new file and on `results.json` |
| channel bands, xT grid and recipe | inherited through E-11's functions and config; E-12 defines none |
| house precedents | `experiments/run_partial_history.py` (provenance block), `galactico/validation/partial_history.py::_permutation_maps` (SHA-256-derived placebo seeds; pattern only, not imported), `galactico/profiles/uncertainty.py::shared_match_weights` (one multinomial matrix shared by all measurements; pattern only: E-12's unit is the club) |

Not reused, on purpose: `experiments/run_external_replication.evaluate` (unfiltered
StatsBomb reader, per-league surfaces, league-wide parity halves), `spec.evaluate` (hard-codes
`player_id` and the unfiltered adapter), `bootstrap_players` (resamples matches; E-12's
estimand is across players and its dependence is by club).

Engineering: `from __future__ import annotations`; frozen dataclasses; full type hints;
`__all__`; numpy and pandas only (no scipy; the normal quantile is
`statistics.NormalDist().inv_cdf`); ruff clean (line length 100); paths anchored at
`Path(__file__).resolve().parents[n]`; module docstring states claim and non-claim. JSON keys
never come from `results_key_denylist`. No double-quoted provider schema key followed by a
colon in any committed file (build provider-shaped test payloads with `dict(...)`).

## 1. Data flow

```
E-11 committed results.json + local results.local.json        (read_dependency)
        | admission per construct, link verdict for [A], Wilson upper bounds, surface hashes, crosswalk digest
        v
PUBLIC STAGE (no StatsBomb path is opened)
  wyscout season inputs (5 leagues, wyscout_reference) -> public_cohorts -> unit_values
  -> normal_scores (league x position x side) -> panel P -> same_club_split, evaluate_contrast(public_winter)
LICENSED STAGE
  E-11 double-coded folders -> crosswalk_matches -> team_sheet_crosswalk -> verified pairs (memory)
  StatsBomb 2015/16 people x Wyscout people -> name_nationality_link(tiers=["A"]) (memory)
  combine_links -> club_keys / assert_club_crosswalk
  statsbomb season inputs (4 leagues, statsbomb_reference) + wyscout season inputs
  -> season_summary -> cross_corpus_cohorts (per floor pair) -> unit_values -> normal_scores
  -> club_levels -> build_panel -> evaluate_contrast x {within_league, league_change, bundesliga_destination}
  -> sensitivities, attrition
assemble -> results.local.json (LOCAL) + results.json (tokens; public block) + report_tables.md
```

## 2. Structure functions (`transport_movers.py`; no outcome is touched)

```python
VERSION = "transport-movers-v1"

def club_keys(team_names: pd.Series, league: pd.Series,
              aliases: Mapping[str, Sequence[str]]) -> pd.Series
def assert_club_crosswalk(origin_keys: Iterable[str], destination_keys: Iterable[str],
                          config: Mapping[str, object]) -> dict[str, int]
def combine_links(verified: pd.DataFrame, wide: pd.DataFrame | None
                  ) -> tuple[pd.DataFrame, dict[str, int]]
def broad_position(position_names: pd.Series, rule: Sequence[Sequence[str]]) -> pd.Series
def season_summary(inputs: pd.DataFrame) -> pd.DataFrame
def cross_corpus_cohorts(links: pd.DataFrame, origin: pd.DataFrame, destination: pd.DataFrame,
                         shared_clubs: Collection[str], config: Mapping[str, object],
                         *, origin_floor: int, destination_floor: int) -> pd.DataFrame
def public_cohorts(inputs: pd.DataFrame, position: pd.Series, config: Mapping[str, object],
                   *, side_floor: int) -> pd.DataFrame
def false_link_bound(*, origin_floor_players: int, verified: int, wide_only: int,
                     false_link_upper: float, absent_partner_upper: float) -> float
def sample_gate(*, stayers: int, movers: int, stayer_clubs: int, mover_clubs: int,
                config: Mapping[str, object]) -> Gate
```

| Function | Exact behaviour |
|---|---|
| `club_keys` | `key = normalise_name(name)`; if `key` is one of the spellings in `aliases`, replace by the canonical; return `key + "\|" + league`. No provider team id enters |
| `assert_club_crosswalk` | shared = intersection. Raises `StructureError` (runner exit 3) unless shared per league equals `club_crosswalk_expected_shared`, origin-only count equals `club_crosswalk_expected_origin_only`, destination-only count in the overlap leagues and in `destination_only_league` equal their expected values, and every key occurs once per corpus. Returns the counts |
| `combine_links` | `verified`: `origin_id`, `destination_id` (E-11 pairs with status `dependency_verified_pair_status`). `wide`: `origin_id`, `destination_id` for outcome `LINKED`, or `None` in `verified_only` mode. Result: `origin_id`, `destination_id`, `tier` (`V`, else `A`). Tier V wins. An `origin_id` whose two tiers name different partners, and every link into a `destination_id` claimed by two `origin_id`s, is dropped; counts `tier_v`, `tier_a`, `tier_conflict`, `claimed_twice` |
| `broad_position` | lower-case name; first matching substring of `statsbomb_broad_position_rule` in order; no match gives missing |
| `season_summary` | input: one corpus, columns `player_id`, `club`, `league`, `game_id`, `date`, `minutes_regulation`. Output index `player_id`: `main_club`, `main_league`, `main_minutes` (minutes for the main club only), `clubs` (count with at least one minute), `tie` (two clubs share the maximum). Rows with `tie` are excluded downstream and counted |
| `cross_corpus_cohorts` | one row per link with both summaries present, outfield on both sides, no tie, `main_minutes >= floor` on each side: `cohort` by the protocol table (`S`, `M_w`, `M_x`, `M_b`, `EXCLUDED_SAME_MAIN_SECOND_CLUB`), `tier`, `role_same`, `second_club`, `origin_club_shared`, `destination_club_shared`, `second_tier_stayer`, `age_band`, `minutes_band`. Also returns, in `attrs["attrition"]`, the count of links lost at each step by reason |
| `public_cohorts` | from the five-league inputs: per player the clubs with minutes and their first and last appearance dates. `P_M` and `P_S` by the protocol table. Output per unit: `cohort`, `before_club`, `after_club`, `before_league`, `after_league`, `before_games`, `after_games` (tuples of `game_id`, memory only), `minutes_before`, `minutes_after`. `attrs["attrition"]`: two-club players, by window, interleaved, goalkeepers, below each side floor |
| `false_link_bound` | `F = false_link_upper * wide_only + absent_partner_upper * max(0.0, origin_floor_players - verified - wide_only * (1.0 - false_link_upper))`. The caller forms `min(F / movers, false_link_share_cap)` |
| `sample_gate` | failed codes in the order `MIN_STAYERS`, `MIN_MOVERS`, `INVERSE_N_SUM` (evaluated only when both counts exceed 3), `MIN_STAYER_CLUBS`, `MIN_MOVER_CLUBS`; `passed = not failed` |

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
```

## 3. Measurement functions

```python
def unit_values(inputs: pd.DataFrame, games: pd.DataFrame,
                construct: Mapping[str, object]) -> pd.DataFrame
def normal_scores(values: pd.Series, cells: pd.Series, *, minimum_cell: int,
                  offset: float) -> pd.DataFrame
def club_levels(z: pd.Series, minutes: pd.Series, club: pd.Series, *, leave_one_out: bool,
                minimum_others: int) -> pd.Series
def build_panel(cohorts: pd.DataFrame, origin_scores: pd.DataFrame,
                destination_scores: pd.DataFrame, levels: pd.DataFrame,
                config: Mapping[str, object]) -> tuple[pd.DataFrame, pd.DataFrame]
```

3.1 **Season inputs** (built by the runner, section 6): one frame per corpus-league with
`input_columns` plus `league` and `club` (club key). One row per player-match with at least
one regulation minute; `0.0` where the player has no qualifying event.

3.2 **`unit_values`**. `games`: `unit_key`, `game_id` (which matches count for the unit:
main-club matches; in the public arm the matches of one side). Sort a unit's games by
`(date, game_id)`; index parity gives half A (even) and B (odd). Output per `unit_key`:
`minutes`, `value`, `minutes_a`, `value_a`, `minutes_b`, `value_b`, each value
`scale * sum(numerator) / sum(denominator)`; a zero denominator gives NaN.

3.3 **`normal_scores`**. Within each cell, over finite values only: average ranks `r`
(ties averaged), `u = (r - offset) / n`, `z = NormalDist().inv_cdf(u)`. Cells with fewer
than `minimum_cell` finite values give NaN for every member and are counted. Output
columns `z`, `u`, `cell_units`. The function receives the whole reference population of the
corpus-league (every outfield player at the floor), not only linked players. Half values
are scored by a separate call over units whose half minutes are at least
`half_floor_fraction_of_floor * floor`.

3.4 **`club_levels`**. Minutes-weighted mean of `z` over the club's rows; with
`leave_one_out` the row's own contribution is removed from numerator and denominator.
NaN when fewer than `minimum_others` other finite rows remain (or, without leave-one-out,
fewer than `minimum_others` rows).

3.5 **Cells.** Origin: (`origin_league`, StatsBomb broad position). Destination:
(`destination_league`, Wyscout role with `wyscout_position_map`). Public arm:
(league of the side, Wyscout role, side).

3.6 **Panel schema** (the boundary between structure and statistics; one frame per
construct and floor pair; canonical order = sort by `cohort`, `cluster`, then the
provider ids, after which the ids are dropped):

| Column | dtype | Meaning |
|---|---|---|
| `unit` | int32 | running index in canonical order; never a provider id |
| `cohort` | str | `S`, `M_w`, `M_x`, `M_b`; public arm `P_S`, `P_M` |
| `tier` | str | `V`, `A`; `D` (provider-declared id) in the public arm |
| `cluster` | str | origin club key (public arm: before-side club key) |
| `origin_league`, `destination_league`, `position` | str | `position` is the Wyscout role |
| `role_same`, `second_club`, `origin_club_shared`, `destination_club_shared`, `second_tier_stayer` | bool | protocol flags (public arm: all False except `second_club` for `P_M`) |
| `age_band`, `minutes_band` | int8 | 0, 1, 2 by `age_band_edges_years`, `destination_minutes_band_edges` |
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
    namespace: str                 # sha256 of version, seed, B and the cluster keys, first 16 hex

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
    rho_stayers: Estimate
    rho_movers: Estimate
    ratio: Estimate
    fisher_difference: Estimate
    fisher_analytic_half_width: float
    spearman_stayers: float | None
    spearman_movers: float | None
    reliability: Mapping[str, Estimate]      # stayers_pre, stayers_post, movers_pre, movers_post
    rho_star_stayers: Estimate
    rho_star_movers: Estimate
    ratio_star: Estimate
    standing_shift: Estimate
    matched_dropped_movers: int

def cluster_worlds(clusters: Iterable[str], *, replicates: int, seed: int) -> Worlds
def weighted_correlation(weights: np.ndarray, x: np.ndarray, y: np.ndarray,
                         *, minimum_weight: float) -> np.ndarray
def contrast_statistics(panel: pd.DataFrame, stayers: np.ndarray, movers: np.ndarray,
                        worlds: Worlds, config: Mapping[str, object],
                        *, stayer_weights: np.ndarray | None = None) -> ContrastStatistics
def identity_placebos(panel: pd.DataFrame, mask: np.ndarray, config: Mapping[str, object]
                      ) -> dict[str, object]
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
| `cluster_worlds` | `clusters` = every club key of the origin corpus (public arm: every before-side club), sorted. `rng = np.random.default_rng(np.random.SeedSequence([seed, 1]))`; `weights = rng.multinomial(C, [1/C]*C, size=B)`. Created once per arm by the runner and passed to every construct, contrast and sensitivity (R12) |
| `weighted_correlation` | rows of `weights` are `(B, n)` unit weights (`worlds.weights[:, cluster_index]`). `sw = sum w`; means, `cxy`, `vx`, `vy` with `1/sw` moments; `r = cxy / sqrt(vx * vy)`. NaN where `sw < minimum_weight`, a variance is not positive, or the result is not finite. Pairs with a NaN in `x` or `y` are removed before the call |
| point estimates | unit weights (one row of ones) through the same code path |
| `contrast_statistics` | `rho_g` on (`z_pre`, `z_post`); `ratio = rho_M / rho_S`; `fisher_difference = atanh(rho_S) - atanh(rho_M)`; `fisher_analytic_half_width = 1.6449 * sqrt(1/(n_S - 3) + 1/(n_M - 3))`. Reliability per arm and side: `r` of (`z_*_a`, `z_*_b`) over units with both halves finite, stepped up `2r / (1 + r)` inside each world. `rho_star_g = rho_g / sqrt(rel_pre * rel_post)`, NaN unless the root exceeds `attenuation_minimum`; `ratio_star = rho_star_M / rho_star_S`. `Estimate.decision` and `.reported` = `np.quantile` (linear) over finite worlds, `None` when the finite share is below `minimum_valid_replicate_share`. `stayer_weights` multiplies stayer unit weights (composition match) |
| standing shift | `d = z_post - z_pre`; cell = `position` x bin of `u_pre` by `prior_percentile_bin_edges` (right-open, last bin closed). Per world: for each cell with positive stayer weight, mover mass `m_c`, weighted stayer mean `s_c`; `D = (sum over those cells of [sum of w*d over movers in c] - m_c * s_c) / sum m_c`. `matched_dropped_movers` = movers in cells with no stayer (point sample) |
| `identity_placebos` | for each seed in `identity_placebo_seeds`: inside each pool of `identity_placebo_pool` restricted to `mask`, sort by `unit`, permute the destination columns (`z_post`, `z_post_a`, `z_post_b`) with `default_rng(int.from_bytes(sha256(f"{seed}\|{placebo}\|{pool key}".encode()).digest()[:8], "big"))`. Return sorted correlations, `point`, `strictly_above_all` (ties fail), `singleton_units`, mean `unchanged_units` |
| `contamination_curve` | for each fraction `f`: `round(f * n_M)` movers chosen without replacement; each gets the destination columns of a uniformly drawn row of `reference_post` in his (`destination_league`, `position`); `contamination_draws` draws from `default_rng(SeedSequence([contamination_seed, index of f]))`; report mean and 0.05 / 0.95 quantiles of the point `ratio` and the algebraic `(1 - f) * ratio` |
| `pseudo_movers` | `pseudo_mover_draws` draws: `movers` stayers relabelled at random (`default_rng(SeedSequence([pseudo_mover_seed, draw]))`), point `ratio` of relabelled against the rest; report mean and 0.05 / 0.95 quantiles |
| `rule_comparison` | rows: stayers with finite `z_pre`, `z_post`, `level_origin`; movers with those and finite `level_destination_prior`. `None` when movers on those rows are below `transport_rule_minimum_movers`. Per world: weighted least squares of stayers' `z_post` on `[1, z_pre - level_origin, level_origin]` (normal equations; a singular world is invalid). Forecasts for movers by `transport_rules`; loss = weighted mean squared error; differences `R1 - R0`, `R1_raw - R0`, `R2 - R1`, `R3 - R1`, `R3 - R2` as `Estimate`s. Coefficients are a function of stayer rows only |
| `composition_weights` | stayer weight = (movers' share of the cell) / (stayers' share of the cell), cell = `position` x `age_band` x `minutes_band`; 0 where no mover; movers in cells without stayers are counted |
| `attrition_contrast` | weighted mean `z_pre` of units that cleared the destination floor minus those that did not, as an `Estimate` |

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
    token: str
    reason: str

def decide(*, arm: str, admitted: bool, admission_reason: str, gate: Gate,
           statistics: ContrastStatistics | None, false_link_share: float,
           placebos_passed: bool | None, config: Mapping[str, object]) -> Verdict
def decide_rules(comparison: RuleComparison | None, compared: bool,
                 config: Mapping[str, object]) -> str
def evaluate_contrast(panel: pd.DataFrame, reference_post: pd.DataFrame, *, arm: str,
                      contrast: str, stayer_cohort: str, mover_cohorts: Sequence[str],
                      admitted: bool, admission_reason: str, false_link_share: float,
                      worlds: Worlds, config: Mapping[str, object]) -> dict[str, object]
def same_club_split(panel: pd.DataFrame, worlds: Worlds, config: Mapping[str, object]
                    ) -> dict[str, object]
```

`decide` is the protocol's decision table, rows 1 to 12 in order, written as one
`if` ladder with no other entry point. Comparisons: `>=` for lower bounds against the
margin, `<` for upper bounds, inclusive for the standing-shift margin. Any `None` or NaN
bound fails the row that needs it (rows 3 and 5 exist to name those cases). `arm ==
"public_winter"` skips row 1 and uses `false_link_share = 0.0`.

`evaluate_contrast` enforces the order that makes `INCONCLUSIVE` true to its definition:

1. not admitted: return `{verdict: NOT_ADMITTED, ...}`; **no panel column is read**.
2. `sample_gate` from cohort counts and distinct `cluster` counts; failed: return
   `{verdict: INCONCLUSIVE, gate: ...}`; **`contrast_statistics` is not called** (a test
   replaces it with a function that raises).
3. statistics, placebos (both arms), `decide`, then `rule_comparison` and `decide_rules`,
   then (cross-corpus only) the contamination curve and pseudo-movers.

Contrasts: `within_league` = `S` against `M_w`; `league_change` = `S` against `M_x`;
`bundesliga_destination` = `S` against `M_b`; `public_winter` = `P_S` against `P_M`.

`same_club_split`: `P_S` rows only; status `REPORTED` iff units reach
`same_club_split_minimum_units` and clusters reach `minimum_clubs_per_arm`; then `rho`,
its reliabilities and `rho_star` as `Estimate`s.

Sensitivities (primary contrast only, each skipped below `sensitivity_minimum_movers`):
a list of `(label, stayer mask, mover mask, stayer_weights)` passed to
`contrast_statistics`; `player_bootstrap` replaces `worlds` by unit-level multinomial
weights within arm x position (`player_bootstrap_sensitivity_seed`); `floors_450`,
`floors_1350` rebuild cohorts, cells and the panel at those floors. No sensitivity reaches
`decide`.

## 6. Runner `experiments/run_transport_movers.py`

```python
def read_dependency(config: Mapping[str, object]) -> Dependency
def verified_pairs(e11_config: Mapping[str, object]) -> tuple[pd.DataFrame, frozenset[int], str]
def statsbomb_season(folder: str, surface, e11_config, config) -> tuple[pd.DataFrame, pd.DataFrame]
def wyscout_season(competition: str, surface, e11_config, config) -> tuple[pd.DataFrame, pd.DataFrame]
def outcome_inputs(protocol_hash: str, stamp: Mapping[str, object], *, stage: str) -> dict
def public_stage(config, dependency, stamp, protocol_hash) -> dict
def licensed_stage(config, dependency, stamp, protocol_hash) -> tuple[dict, dict]
def calibrate(config, *, out: Path | None = None) -> dict
def execute(config, *, verify: bool = False) -> int
def main(argv: Sequence[str] | None = None) -> int
```

| Piece | Rule |
|---|---|
| `Dependency` | frozen dataclass: `admission: Mapping[str, tuple[str, str]]` (status, reason per construct key), `link_usable: bool` (E-11 `link_verdicts` entry with `tiers == ["A"]`), `false_link_upper`, `absent_partner_upper` (floats from the pooled `[A]` block of E-11's local `identity` list; `None` in `verified_only` mode), `surface_hashes`, `crosswalk_player_digest`, `committed_hash`, `local_sha256`, `protocol_hash`. Raises unless the local file's sha256 equals `local_results_sha256` in the committed file |
| `verified_pairs` | reruns E-11's `read_matches` / `read_team_sheets` / `read_wyscout_*` / `crosswalk_matches` / `team_sheet_crosswalk` on the two double-coded folders; keeps status `dependency_verified_pair_status`; returns the pairs (memory), the Wyscout game ids of the linked La Liga matches, and `crosswalk_digest`, which must equal E-11's recorded digest (else exit 3) |
| surfaces | `statsbomb_reference_surface(root, e11_config, variant="open_play")` and `wyscout_reference_surface(spain_actions, excluded_game_ids, e11_config)`; `sha256(xt.values.tobytes())` must equal E-11's recorded hashes (else exit 3) |
| `statsbomb_season` | E-11's reader has no season entry point, so the runner feeds it identity links: `match_links` with `match_key` = running index, `subset` = folder, `wy_game_id` = `sb_game_id`, `swapped` False, `wy_team_for_sb_home` / `_away` = the StatsBomb team ids; `pairs` with `wy_player_id` = `sb_player_id`, status verified, `is_goalkeeper` from the sheets. Then, in chunks of `season_reader_chunk_matches` matches: `harmonise_statsbomb(read_events(...), links, pairs, e11_config, variant="open_play")`, `sheet_minutes(...)`, `player_match_inputs(frame, minutes, surface, e11_config)`; keep `input_columns` only; add `date`, `league`, `club`. Asserts `origin_expected_matches`. People frame: `sb_player_id`, `player_name`, `player_nickname`, `country`, modal position name by regulation spell minutes. Peak memory stays under 1.5 GB |
| `wyscout_season` | same with `harmonise_wyscout` on `actions.parquet` (column list; `provider == {"pappalardo"}` asserted), identity links on Wyscout ids, `read_wyscout_team_sheets` for minutes. Asserts `destination_expected_matches`. People from `read_wyscout_people` plus birth date from the raw players file |
| wide link | `name_nationality_link(left, right, e11_config, tiers=["A"])` with `left` and `right` built exactly as E-11's `evaluate_wide_link` builds them (`left_id`, `full_name`, `known_as`, `country`; `right_id`, `full_name`, `countries`), over every StatsBomb 2015/16 player with a position spell and every Wyscout record. The measured rates apply to that construction only |
| `outcome_inputs` | the only function that opens an event or action file of a real season. Raises `RuntimeError` unless `protocol_hash` equals `lf_sha256` of the committed protocol and `stamp` is a passed calibration stamp for the current config and source hashes. `stage="public"` never touches `statsbomb_root` |
| writing | `Path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8", newline="\n")`. Never shell redirection. No timestamp in any payload |

CLI.

| Command | Reads | Writes (all under `local_output_root`) | Real outcome data |
|---|---|---|---|
| `calibrate [--out PATH]` | config only | `calibration.json` | no (synthetic) |
| `execute` | everything | `results.local.json`, `results.json`, `report_tables.md` | **yes; root only, once** |
| `execute --verify` | everything | `determinism.json` | yes; root only, once |

`execute` refuses (exit 2, message naming the failed condition) unless all hold:

1. git is available and the work tree is clean for the protocol, the config and every
   file in `source_hashes`.
2. `protocol_commit = git log --diff-filter=A --format=%H -- <dir>/preregistration.md` is
   non-empty, and the protocol and config blobs at `HEAD` equal the ones in that commit
   (LF-normalised). The commit is derived, never typed.
3. `calibration.json` exists, `passed` is true, and its `config_hash` and `source_hashes`
   equal the current ones.
4. E-11's committed `results.json` and local `results.local.json` exist and agree
   (`read_dependency`); E-11's protocol commit is an ancestor of `HEAD`.
5. `local_output_root` resolves under `data/licensed/`.
6. Without `--verify`: `results.local.json` does not exist (one execution). With
   `--verify`: it exists.

Exit codes: `exit_codes` in config. `--verify` recomputes both payloads, compares bytes
with the files on disk, writes `determinism.json` (`equal`, the four sha256 values) and
exits 4 on any difference.

**The single command the root runs for the real execution** (after the protocol commit,
after E-11's execution, after `calibrate`):

```powershell
.venv\Scripts\python.exe -X utf8 experiments/run_transport_movers.py execute
```

then once `... execute --verify`, then copy `results.json` (and `calibration.json`) into
`experiments/preregistered/E-12-transport-movers/`. Expected wall time: about ten minutes,
dominated by reading 1,517 StatsBomb event files once.

## 7. Synthetic generator and calibration

```python
def synthetic_panel(rng: np.random.Generator, scenario: Mapping[str, object],
                    config: Mapping[str, object]) -> tuple[pd.DataFrame, pd.DataFrame]
def run_calibration(config: Mapping[str, object], *, panels: int | None = None,
                    replicates: int | None = None) -> dict[str, object]
```

Generator (reference implementation: `design/E-12/_work/prototype.py::gen`; port it, do not
import it). Parameters default to `calibration_defaults`, overridden per scenario.

1. Reference population: `clubs` x `players_per_club` origin players. Team effect
   `T_c ~ N(0, g)`, own part `o_i ~ N(0, 1 - g)`, `g = team_variance_share`; `t_pre = T + o`.
2. Draw `stayers + movers` linked players without replacement. A mover's destination club
   is a different club chosen uniformly.
3. True destination value, with `s = stability`: stayers `s * t_pre + sqrt(1 - s^2) * e`.
   Movers by `mode`: `scale` gives `s * ratio * t_pre + sqrt(1 - (s * ratio)^2) * e`;
   `team_stays_behind` gives `s * o + sqrt(1 - s^2) * e`; `destination` gives
   `s * (o + T_dest) + sqrt(1 - s^2) * e`. Add `standing_shift` to movers.
4. Observation with full-value reliability `rel` (per arm): half reliability
   `q = rel / (2 - rel)`; each half `sqrt(q) * t + sqrt(1 - q) * noise`; full = mean of halves.
5. `false_link_share` of movers receive the destination values of a random other player.
6. Normal scores over the whole population per side and half; `level_origin` leave-one-out
   over the origin club; `level_destination_prior` over the destination club's origin values.
7. Positions are assigned uniformly from three labels and used as cells, so the generator
   exercises the same code path as real panels. `assumed_false_link_share` is passed to
   `decide` as `false_link_share`.

`run_calibration`: for each scenario, `calibration_panels` panels (or the scenario's own
`panels`), `calibration_bootstrap_replicates` worlds, seed
`SeedSequence([calibration_seed, scenario index])`; each panel goes through
`evaluate_contrast` exactly as a real one. Output per scenario: shares by verdict token, by
reason, by rule verdict; mean point `ratio` and `ratio_star`; each requirement with
`required`, `observed`, `passed`. `passed` overall iff every requirement of every scenario
holds. `calibration.json` = that dict plus `config_hash`, `source_hashes` and `version`.

Requirements (frozen in `calibration_scenarios`; measured on the design prototype at 400
panels and 400 worlds, shown so a failing port can be told from a failing design):

| Scenario | Plants | Requirement | Prototype |
|---|---|---|---|
| `planted_equivalence` | ratio 1.0 | `TRANSPORTS_WITHIN_MARGIN` >= 0.85; `REDUCED_BEYOND_MARGIN` <= 0.01; mean ratio within 0.03 of 1.0 | 0.96; 0.00; 1.004 |
| `planted_null_at_margin` | ratio 0.80 (the boundary of the equivalence claim) | each directional verdict <= 0.10; mean ratio within 0.03 of 0.80 | 0.045 and 0.047; 0.796 |
| `planted_loss` | ratio 0.5 | `REDUCED_BEYOND_MARGIN` >= 0.90; `TRANSPORTS_WITHIN_MARGIN` <= 0.01; mean ratio within 0.03 of 0.5 | 0.98; 0.00; 0.496 |
| `reliability_artefact` | ratio 1.0, reliability 0.89 stayers, 0.80 movers | `REDUCED_BEYOND_MARGIN` <= 0.02; mean raw ratio in [0.86, 0.94]; mean disattenuated ratio in [0.95, 1.05] | 0.00; 0.902; 1.005 |
| `false_links_adjusted` | ratio 1.0, 25% false mover links, bound 0.25 | `REDUCED_BEYOND_MARGIN` <= 0.02 | 0.00 |
| `false_links_unadjusted` | same, bound 0 | `REDUCED_BEYOND_MARGIN` >= 0.04 (non-vacuity: the guard acts) | 0.10 |
| `no_stayer_persistence` | stability 0.1 | reason `STAYER_PERSISTENCE_BELOW_FLOOR` >= 0.95; each directional verdict <= 0.01 | 1.00; 0.00 |
| `planted_gate_failure` | 1,097 stayers, 29 movers | `INCONCLUSIVE` = 1.0 and `contrast_statistics` never called | 1.00 |
| `planted_standing_shift` | ratio 1.0, movers shifted by -0.5 | reason `STANDING_SHIFT_OUTSIDE_MARGIN` >= 0.85; `TRANSPORTS_WITHIN_MARGIN` <= 0.02 | 0.96; 0.00 |
| `rules_team_level_stays` | movers keep own deviation only | `OWN_DEVIATION_PREFERRED` >= 0.75 | 0.90 |
| `rules_everything_travels` | movers keep everything | `NO_RULE_PREFERRED_OVER_CARRY_FORWARD` >= 0.90 | 1.00 |
| `rules_destination_level` | movers take the destination level | `DESTINATION_LEVEL_PREFERRED` >= 0.80 | 0.91 |

`tests/test_transport_movers_rule.py` runs the same scenarios at `calibration_test_panels`
panels with each bound relaxed by `calibration_test_tolerance` (it must stay under a minute
in the data-free CI job); the full run is the `calibrate` command.

## 8. Result shapes

All files are aggregate only: no player, club or match identifier, no name, no row per
player. `null`, never NaN. Each under `maximum_results_bytes`.

**`results.local.json`** (LOCAL; never committed).

| Key | Content |
|---|---|
| `experiment`, `version`, `tier` | `E-12`, config `version`, `LOCAL_LICENSED` |
| `provenance` | section 9 in full |
| `dependency` | per construct `status`, `reason`; `link_usable`; `identity_mode`; the two Wilson upper bounds; `surface_hashes_equal`, `crosswalk_digest_equal` |
| `structure` | club crosswalk counts; link counts by tier and by loss reason; per floor pair: cohort counts, flags' counts, position mix, distinct clubs per cohort, cells (count, smallest, excluded) |
| `attrition` | the protocol's attrition table, with the per-construct floor-clearing contrasts |
| `identity` | `expected_false_links` per floor pair; `false_link_share` per contrast |
| `contrasts` | list; one object per construct x contrast: `construct`, `contrast`, `role`, `verdict`, `reason`, `gate`, `statistics` (every field of `ContrastStatistics`, `null` when not compared), `placebos` (per arm: sorted values, `point`, `strictly_above_all`, `singleton_units`), `contamination`, `pseudo_movers`, `rule_comparison`, `rule_verdict` |
| `sensitivities` | list; `label`, `construct`, `stayers`, `movers`, `rho_stayers`, `rho_movers`, `ratio` with both intervals, `ratio_star`. No verdict |
| `uncertainty_limit`, `product_effect` | fixed strings from the protocol |

**`results.json`** (committed).

| Key | Content |
|---|---|
| `experiment`, `version`, `tier`, `tiers` | `E-12`; config `version`; `LOCAL_LICENSED` (the stricter of the two); `{cross_corpus: LOCAL_LICENSED, public_winter: PUBLIC}` |
| `provenance` | as local, minus data digests, surface hashes and crosswalk digests; with `providers`, `local_results_sha256`, `calibration_hash`, `dependency` (hashes only) and the verbatim config |
| `admission` | per construct `{status, reason}` |
| `cross_corpus` | `identity_mode`; `gates` per subject `{passed, failed}` (booleans and codes); `rule_verdicts` per subject; `statistics` = the string `withheld: LOCAL_LICENSED aggregate, see analysis.md` |
| `public_winter` | `providers` (`["pappalardo"]`); `cohort` and `attrition` counts; `same_club_split` per construct (`status`, `units`, `clubs`, `floor_minutes`, `correlation`, `disattenuated`, `reliability_before`, `reliability_after`, each with point and both intervals); `movers` per construct (`gate` with counts and `required_movers`, `statistics` or `null`) |
| `verdicts` | `{"<contrast>:<construct>": {"token", "reason"}}` for the four contrasts x five constructs |
| `attribution`, `uncertainty_limit`, `product_effect` | fixed strings |

Outside `provenance.config` and `public_winter`, `results.json` holds no `int` and no
`float` (`bool` is allowed); a test walks the payload. `report_tables.md` is generated
from `results.local.json` so no number in `analysis.md` is retyped; it prints counts below
`small_count_suppression_below` as `<5`.

Figures a hosted page may print (PUBLIC record `public_winter:<construct>` only, with
RFC 6901 pointers into `results.json`): `same_club_split_correlation`
(`/public_winter/same_club_split/<construct>/correlation/point`, only when `REPORTED`),
`winter_movers_at_floor` (`/public_winter/movers/<construct>/gate/movers`),
`winter_movers_required` (`.../gate/required_movers`). E-12 supplies no figure named or
usable as a reference value for the break-even carry-over fraction.

## 9. Hash discipline

| Object | Hash |
|---|---|
| `preregistration.md`, `config.json` | `lf_sha256` (CRLF to LF, then sha256). The checkout has `core.autocrlf=true`; a raw-byte hash does not reproduce |
| source files | `lf_sha256`, keys as posix paths relative to the repository root: `galactico/validation/transport_movers.py`, `experiments/run_transport_movers.py`, every file in `dependency_source_files`, `galactico/validation/digests.py`, `galactico/models/xt/grid.py`, `galactico/models/xt/__init__.py`, `galactico/identity/resolver.py`, `galactico/providers/base.py` |
| E-11 | `lf_sha256` of its committed `results.json` and protocol; sha256 of its `results.local.json` bytes |
| StatsBomb raw JSON | E-11 `folder_manifest` digest per folder used (four leagues and the two double-coded folders): byte-exact; these files never pass through git |
| Pappalardo raw JSON | byte-exact sha256 of `players.json`, `teams.json` and the five `matches_<League>.json`, checked against the fetch `MANIFEST.json` |
| Pappalardo Parquet | content hash, never file bytes (the footer embeds the pandas version): sort by `["game_id", "period", "seconds", "event_id"]`, then `sha256(pd.util.hash_pandas_object(frame, index=False).values.tobytes())` |
| season input frames | the same content hash after sorting by `["game_id", "player_id"]`, per corpus-league; local file only |
| surfaces | `sha256(xt.values.tobytes())`, asserted equal to E-11's |
| crosswalk | E-11's `crosswalk_digest` of the verified pairs, asserted equal to E-11's; the combined link table gets a digest and counts in the local file only |
| panels | content hash per construct and floor pair, local file only |
| `protocol_commit` | derived from git by the runner |
| determinism | sha256 of the bytes of both result files, first run and verify run |

## 10. Synthetic test suite (data-free unless marked)

| File | Tests |
|---|---|
| `test_transport_movers_structure.py` | `club_keys` on the 12 aliases, on accents and on a name that is a substring of another; `assert_club_crosswalk` passes on a synthetic 66 / 14 / 14 / 18 layout and raises on a missing alias, a duplicate and a miscount; `combine_links` precedence, conflict, twice-claimed, `verified_only`; `broad_position` on every StatsBomb position name, "Right Wing Back" is DF; `season_summary` tie, second club, minutes at the main club only; every cohort of the protocol table from hand-built lineups, including same main club with a second club, a Bundesliga destination, a mover whose origin club is absent; floors per construct (900 / 1,800); `public_cohorts` winter rule, summer mover rejected, interleaved rejected, split-date boundary (a match on the split date is "after"), goalkeeper rejected; `unit_values` halves by own match order, zero denominator is NaN not zero, row-order invariance; `normal_scores` ties, minimum cell, NaN in and out, symmetric around zero, `u` in (0, 1); `club_levels` excludes the unit's own value (changing it leaves his level unchanged) and respects the minimum; `false_link_bound` against a hand calculation; `sample_gate` every code and the boundary `0.0179` |
| `test_transport_movers_statistics.py` | `weighted_correlation` equals `np.corrcoef` on rows repeated by integer weights (oracle uses repetition, not weights); point estimate equals the unit-weight world; standing shift equals an explicit double loop written from the protocol sentence; Spearman-Brown inside the world, not after; disattenuated value missing below `attenuation_minimum`; `rule_comparison` coefficients equal `np.linalg.lstsq` on repeated stayer rows and are unchanged when every mover's `z_post` is replaced (stayer-only fitting); all rules scored on identical rows; `cluster_worlds` deterministic, sorted, shared: two constructs given the same `Worlds` see identical weights and world `b` has the same club counts in both; row-order invariance of every statistic; placebos: pools respected, counts preserved, seed derivation fixed (a pinned vector), singletons unchanged and counted, permuted correlation near zero on a planted strong panel; contamination curve close to `(1 - f)` times the clean ratio on a planted panel; invalid worlds counted and an interval withheld below the valid share; non-vacuity: at least one test panel yields each of a finite and a missing interval |
| `test_transport_movers_rule.py` | the decision table as a truth table written by hand from the protocol (it imports only `decide`): every row, every boundary (`L == m` passes row 7, `U == m` fails row 6, `D` bound equal to the margin passes), NaN in each position, `false_link_share` moving a case from row 6 to row 10, public arm skipping row 1; exhaustiveness: a grid over the bounds returns exactly one token from the vocabulary each time and every token and every reason is produced at least once; `decide_rules` every branch; `evaluate_contrast` computes nothing for a construct that is not admitted and nothing behind a failed gate (statistics function patched to raise); the reduced calibration (section 7) |
| `test_transport_movers_runner.py` | `execute` refuses: without git, on a dirty tree, with a protocol differing from its commit, without or with a stale or failed calibration stamp, without E-11 results, with a local file whose sha256 differs from E-11's committed record, with an output root outside `data/licensed/`, on a second execution; end to end on a synthetic corpus written to `tmp_path` (provider-shaped files built with `dict(...)`): planted full transport returns `TRANSPORTS_WITHIN_MARGIN` for the primary subject and the public arm returns `INCONCLUSIVE` with statistics `null`; two runs byte-identical; `allow_nan=False`; size ceiling; denylist walk on both files; `scripts/check_licensing.check` passes on `results.json`; no `int` or `float` in `results.json` outside the config echo and `public_winter`; the public stage completes with `statsbomb_root` pointing at a missing directory and its block is byte-identical to the block from a full run; no file is created outside `local_output_root` (directory snapshot before and after); no payload string equals any synthetic player or club name; `import galactico.api` leaves `galactico.validation.transport_movers` out of `sys.modules`; `@pytest.mark.slow` structure check on the real caches (skips cleanly when absent): the club crosswalk assertion holds and the public structural counts equal `public_structural_counts`. It reads lineups and match lists only |

Oracles are written from the protocol text with plain loops, `itertools` and
`np.corrcoef` / `np.linalg.lstsq`, and import no helper from the module under test.

## 11. Pre-outcome code review checklist

Run by a reviewer who did not write the code, on synthetic data, before `execute`.

1. The protocol and config in the experiment directory are byte-equal (LF) to this folder's.
2. Every numeric literal in `transport_movers.py` and the runner is `0`, `1`, `2`, `3`
   (the `n - 3` of the gate), `0.5` or `1.6449`, or comes from config. Grep for others.
3. Every key of `config.json` is read by code or echoed in provenance; none is unused.
4. E-11 functions are imported, not copied; their source hashes are in provenance; the
   runner contains no pass-type, shot-type or channel literal.
5. The two surface hashes and the crosswalk digest are asserted against E-11's before any
   season is read.
6. `outcome_inputs` is the only call site that opens a season's events or actions; it is
   reached only after the refusals of section 6.
7. Links and pairs never reach `to_parquet`, `to_csv`, `to_json`, `pickle`, `print` or a
   log call. Grep the runner for those names.
8. Provider ids are dropped in `build_panel`; no function after it has an id column.
9. Cells use the whole reference population; cohort membership never changes a `z`.
10. Halves alternate by the unit's own match order, not by league-wide parity.
11. `level_origin` is leave-one-out; `level_destination_prior` uses origin-season values only.
12. Stayer coefficients are computed from stayer rows only, inside each world.
13. One `Worlds` object per arm; no function draws its own resampling weights except the
    declared sensitivity.
14. `decide` matches the protocol table row for row; no other code assigns a verdict token.
15. A failed gate or a non-admitted construct returns before any outcome column is read.
16. `false_link_share` enters row 6 only; it never touches row 7.
17. Disattenuated values are reported beside raw values everywhere; nothing prints one
    without the other.
18. `results.json`: no number outside the config echo and `public_winter`; no denylisted
    key; under the size ceiling; the public block was produced with no StatsBomb path.
19. `calibration.json` passed with the committed config and the reviewed sources.
20. Protocol and config are committed; `git log` shows that commit before any results file.
21. The attribution strings and the logo path are present in `analysis.md`'s template and
    in the protocol.

## 12. StatsBomb attribution requirement

Clause 1.4 applies to every publication of analysis formed from StatsBomb data, nulls and
verdict labels included.

| Where | Requirement |
|---|---|
| `preregistration.md` (it prints structural counts formed from StatsBomb lineups) | the logo image line and the attribution text are already at its foot (relative path to `statsbomb_logo_path`); the root adds the asset in the same commit |
| `analysis.md`, `report_tables.md` | the logo image and both attribution strings above the first table; the sentence that the conclusions are not StatsBomb's |
| `results.json` | `attribution` block with both strings |
| any hosted label derived from a `cross_corpus` verdict | `product_copy.attribution_line` beside it, linking to `research_note_path`; no number |
| `results.local.json` | both strings; never leaves the machine |
| tests | `test_transport_movers_runner.py` asserts the strings in both payloads and in the report template; a docs test asserts the logo path exists once the root has added the asset |

The logo file is not created by this package; E-11 names the same path.

## 13. Shared-file requests to the root

| File | Edit |
|---|---|
| research firewall tuple (`tests/test_research_firewall.py`, H1) | append `galactico.validation.transport_movers` |
| `galactico/domain/verdicts.py` | 20 records `E-12` / `<contrast>:<construct>`: tier from `record_tiers`; `claim_token` from config; `vocabulary` = `verdict_vocabulary`; outcomes = `product_outcomes` with `limits` for `product_outcomes_with_limits` and statements = `product_copy.banner`; `non_claim` from config; `not_run_statement` = `product_copy.banner.PENDING`; public records carry the figures of section 8 after the run |
| `experiments/preregistered/README.md` | one row for E-12 |
| `docs/assets/statsbomb/statsbomb-logo.png` | add (shared with E-11) |
| `VALIDATION.md` Phase 5 | replace "rank successful fits above failed ones better than market value does" by a pointer to E-12's claim; that test is not runnable on this corpus |
| CI | none: every non-slow test is data-free |

## ASSUMED INTERFACES

1. **E-11 modules and frames** as in `design/E-11/PIPELINE.md` sections 2 to 4 and 8:
   function names and signatures in the reuse table; `match_links` and `pairs` column
   schemas (the runner builds identity links in those schemas to read whole seasons);
   committed `results.json` keys `admission` (per quantity `{status, reason}`),
   `link_verdicts` (list of `{tiers, verdict}`), `local_results_sha256`; local
   `results.local.json` keys `identity` (pooled block for tiers `["A"]` with Wilson
   intervals for the false-link and absent-partner false-link rates), `provenance.xt`
   (surface hashes), `provenance.crosswalk_digests.players`. If E-11 prefers to expose a
   season entry point (`player_match_inputs` for a whole folder or competition), the
   identity-link adapter in section 6 is deleted and nothing else changes.
2. **E-11 tier A as graded.** Its pipeline lets a StatsBomb nickname form match the Wyscout
   full name inside tier A. E-12 calls the function exactly as E-11's evaluation does, so
   the measured rates apply. The assignment's wording ("exact full-name token set") is met
   only if E-11 passes no nickname; the reconciler fixes one reading for both.
3. **E-11 protocol, "E-12 uses the widest tier set graded LINK_USABLE".** E-12 uses `[A]`
   only and never tier B. One of the two sentences has to change before the commit.
4. **E-11 protocol, `ADMITTED_ORDER_ONLY`: "no level-shift estimand".** E-12's `D` is a
   difference of within-cell normal scores, not a raw level shift, and enters the verdict
   under both admissions. If the reconciler reads E-11's sentence as covering `D`, the
   survival row loses its regression-to-the-mean guard for order-only constructs; say so
   in the protocol rather than dropping it silently.
5. **Surfaces.** E-11's assumed-interface note has E-12 value "each league on a surface
   fitted by that same rule". E-12 uses E-11's two reference surfaces for every league
   (the only graded pair). Either reading works with E-11's functions; the protocol states
   which.
6. **`galactico/validation/digests.py`** (H1): `lf_sha256(path)`, `lf_sha256_text(text)`.
7. **ARCH-SPEC.** Module name (`club_change` there); results contract 3.2 (met, with `tier`
   set to the stricter tier and a `tiers` map for the two arms; `protocol_commit` derived
   from git); `VerdictRecord` fields and rule V7 (no digit in a LOCAL record's sentences:
   the copy in config complies); `statsbomb_cache.py` is not used directly, only through
   whatever E-11's reader reads.
8. **PRODUCT-PLANNING 1.9.** It draws a reference tick on the carry-over strip when a
   hostable `figures["retention_reference"]` exists. E-12 never supplies one: no E-12
   estimand is the fraction of a rate. It also renders the cross-corpus arm as a ledger row
   only, which is inside what this protocol allows ("a page may show less").
9. **Transfer Lab** reads the governing contrast by candidate origin league as in
   `product_governing_contrast`.

## DISSENT

1. **The cross-corpus arm is unlikely to settle its question.** Synthetic simulation of the
   frozen rule at the planning sizes: a true ratio of 0.9, the only published figure,
   returns `NOT_ESTABLISHED` in about 55% of panels at an observed stayer correlation of
   0.75 and about 74% at 0.62; with the false-link bound at 0.15 a 40% loss is called in
   24% of panels. The design satisfies the root decision and says this in the protocol.
   The evidence argues for registering it as what it is: a test that can detect near-full
   transport or large loss, with `NOT_ESTABLISHED` the modal outcome.
2. **ROOT 2.2 counts 31 public movers at 450 minutes on each side.** Under rules that can be
   frozen (outfield, winter window, non-interleaved spells) the count is 29 (one goalkeeper
   and one non-winter case fall out). The gate needs 62. The protocol uses 29.
3. **O1 read strictly also covers this protocol's own planning tables.** The structural
   counts in `preregistration.md` are formed from StatsBomb lineups; they are printed in
   Markdown with attribution, and the config holds only rounded planning sizes, public club
   spellings and league-membership counts. If the root reads O1 as barring those too, the
   counts move to `analysis.md` and the crosswalk expectations to a local file.
