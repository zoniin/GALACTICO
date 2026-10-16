# E-09 pipeline specification

Companion to `preregistration.md` and `config.json` (same folder). The protocol says what is
decided; this file says what to build. **It is frozen with them:** it is committed in the
registration commit byte for byte as it stands here, its `lf_sha256` is
`pipeline_spec_sha256` in the config, and phase 1 of the runner refuses a mismatch. Where
this file and the protocol disagree, the protocol wins and this file is the defect.

Every number an implementer needs is in `config.json`. Code reads thresholds, seeds, lists
and sentences from the loaded config; a numeric literal for a threshold in code is a review
failure (section 9), and no function takes a default for a value that is in the config.
Config keys that restate a rule as a sentence (`minutes_rule`, `split_rule`, `ece_binning_rule`
and the like) are read by assertions, not by branches: the pipeline asserts the frozen value
and implements only that value.

---

## 0. Files, ownership, order

Packages, buildable in parallel against the interfaces below. Each owns only the files
listed. All are developed and tested on **synthetic data only**.

| WP | Owns (all new) | Depends on |
|---|---|---|
| A | `galactico/features/candidates.py`, `tests/test_candidates.py` | `features/spec.py` (`Scaling`), `features/axes.py` (`AxisSpec`), `domain/provenance.py` (`EvidenceClass`) |
| B | `galactico/models/shots/{__init__,geometry,logistic,model}.py`, `tests/test_shot_model.py` | numpy, pandas |
| C | `galactico/validation/shot_model_evaluation.py`, `tests/test_shot_model_evaluation.py` | B |
| D | `galactico/validation/candidate_gauntlet.py`, `tests/test_candidate_gauntlet.py` | A, C (types only), `reliability/`, `validation/{lifecycle,replication}.py`, `features/axes.py::compute_baselines` |
| E | `galactico/validation/candidate_synthetic.py`, `experiments/run_candidate_gauntlet.py`, `tests/test_candidate_planted.py`, `tests/test_candidate_runner.py`, `tests/test_candidate_pins.py` | A to D |
| F (conditional, lowest priority, LOCAL) | `galactico/validation/candidate_sb.py`, `tests/test_candidate_sb.py` | A to D; `validation/sb_reader.py` unchanged |

Root owns: the registration commit and every shared-file edit of section 13, the real run,
`results.json`, `analysis.md`, `MODEL-CARD.md`, every registry edit of section 11.

**Registration-time edits** (section 13). `config.json` and `PIPELINE.md` are registered byte
for byte. `preregistration.md` is registered after two edits and no other: the DRAFT banner
(the one-line block quote under the title, which holds the only relative links but one) is
replaced by the one line
`> References such as ROOT 2.5 or R12 point to [ROOT-DECISIONS.md](../../../docs/research/north-star/ROOT-DECISIONS.md); the working notes they cite are described in the [README](../../../docs/research/north-star/README.md) beside it.`,
and the logo path `../../../../assets/statsbomb/statsbomb-logo.png`, which resolves from the
draft folder, becomes `../../../docs/assets/statsbomb/statsbomb-logo.png`, which resolves
from `committed_experiment_dir`. `REVIEW-RECORD.md` stays in the draft folder as the record
of review; the three protocol files there become one-line pointers to the registered
directory.

**Key names.** No key, at any depth, of `config.json`, `results.json` or the LOCAL file of
the external leg contains `statsbomb`, `pappalardo` or `wyscout` in any letter case, or
starts with `SB_`. A key that concerns the local-tier provider has `sb` as one of its
`_`-separated parts (`sb_root`, `penalty_area_sb`, `sb_verdict_vocabulary`); one that names
the public provider's side beside it has `wy` (`wy_league_of_sb_folder`); `key_naming`.
Values may name a provider. `tests/test_licensing.py` enforces the first name and the `SB_`
prefix on every JSON file under `experiments/`; the runner test of section 8.4 enforces all
three names at every depth. The LOCAL module is `candidate_sb.py` for the same reason: its
path is a key of `source_hashes`.

**Licence-guard traps.** Never write, in any committed file, a double-quoted
`possession_team`, `freeze_frame`, `obv_total_net` or `shot_statsbomb_xg`; never a
double-quoted `eventId`, `subEventId`, `matchPeriod` or `tagsList` followed by a colon. No
provider xG field and no freeze frame is read, at all.

**Engineering.** `from __future__ import annotations`; frozen dataclasses; full type hints;
`__all__`; numpy and pandas only (no scipy); ruff clean (line length 100); paths anchored at
`Path(__file__).resolve().parents[n]`; module docstrings state claim and non-claim.

## 1. Shipped interfaces (verified against the code on 14 October 2026)

| # | Provider | Interface | E-09 use | Failure |
|---|---|---|---|---|
| I1 | `galactico/ingestion/sidecar.py` (ADR-0028) | `verify(league)`; `manifest(league)` (`sidecar_schema_version`, `tag_mapping_version`, `actions_event_ids_equal`); `load(league, "events", columns=sidecar_columns)` (one row per raw event that has a position: the `event_id` set of `actions.parquet`); `attach(actions, events, ["body_part", "shot_family"])`, the only sanctioned join; `provenance(league)`. `body_part` is `left_foot`, `right_foot`, `head_or_body`, or null for none or several; `shot_family` is `open_play`, `free_kick`, `penalty` or null | body part on every shot row; the shot-family pins | `SidecarMissing`, `SidecarStale`, `SidecarMismatch`, a manifest whose versions differ from `sidecar_schema_version` / `sidecar_tag_mapping_version`, or `actions_event_ids_equal` not true (`sidecar_requires_actions_event_ids_equal`): phase 2 stops. E-09 contains no tag parsing of its own |
| I2 | `galactico/validation/digests.py` | `lf_sha256(path)`, `lf_sha256_text(text)` | every protocol, config, pipeline and source hash, and the hash of `decide`'s source | — |
| I3 | `galactico/domain/verdicts.py` | `VerdictRecord(experiment_id, subject_id, scope, tier, directory, claim_token, non_claim, not_run_statement, vocabulary, outcomes, protocol_hash, config_hash, token, protocol_commit, results_hash, figures)`; `Outcome(status, limits, statement, registry_move)`; rules V1 to V7; `product_admissible` | five PUBLIC records, `PENDING` at registration (section 11.1) | — |
| I4 | `galactico/domain/thesis.py` | `banned_key_paths(payload, parts=BANNED_KEY_PARTS)` | `tests/test_candidate_runner.py` checks `results.json` keys | — |
| I5 | `tests/conftest.py` | `league_available(competition)` (skips cleanly without the league's frames); no per-league sidecar fixture exists | `tests/test_candidate_pins.py` only, plus an inline skip when `sidecar.manifest(league)` raises `SidecarMissing` | — |
| I6 | `galactico/storage/public.py` | `load_public(league, tables=public_tables, action_columns=action_columns)`: the hosting guard and `provider == "pappalardo"` on every action row | every neutral frame | `LicenseViolation`, `FileNotFoundError`: phase 2 stops |
| I7 | E-11 (registered) | `aggregated_player_quantities` of its config (`e11_config_sha256`); its own `provider_inputs` defines its inputs and does not read `galactico.features.candidates` | the two imported definitions (protocol section 1) | the root recomputes `lf_sha256` of E-11's config before registration (`verified_by_root_before_registration`) |
| I8 | H2 repairs | none relied on | — | E-09 never calls `AxisReliability.lower_bound` (it now returns NaN without an interval), `grade`, `ConfoundVerdict.passed` or `ActionFilter.describe` |

E-09 computes no team-level quantity. If E-10 wants a conceded location value it depends on
the E-09 instrument token and must say so.

## 2. Reuse

| Reused unchanged | From | For |
|---|---|---|
| `decide(reliability_low, confound_r2, baseline_r, kind_is_nuisance)` | `experiments/run_replication.py`, pinned by `frozen_rule_decide_source_sha256` and `frozen_rule_constants` (injected, never copied) | league status |
| `_safe_abs_corr` | same module | battery correlations, after the guard |
| `split_half_reliability(first, second, correct=False)`, `spearman_brown`, `AxisReliability(...).interval` | `galactico/reliability/core.py` | `r_half`, `r_sb`, the reported house interval. `split_half_reliability` takes **mappings keyed by player id**: it is called with `series.to_dict()` on the index of R, as `run_replication.py` does; a `pd.Series` passed directly is iterated by value and returns `(nan, 0)` |
| `discriminant_validity(..., ties=rank_ties)`, `residualise` | `galactico/reliability/confound.py` | the reported joint audit. Under `ties="average"` a tied k-th place gives `top_k_survivors=None` with `top_k_tied_raw` and `top_k_tied_adjusted` |
| `compute_baselines(actions, minutes)` | `galactico/features/axes.py` | eight house battery columns and `minutes`, called with the minutes of `minutes_rule` |
| `Status`, `LeagueResult`, `classify_replication`, `ConfoundFinding`, `ConfoundKind` | `galactico/validation/{lifecycle,replication}.py` | status enum; reported labels |
| `Scaling` | `galactico/features/spec.py` | scaling enum of a `CandidateSpec` |
| `AxisSpec` | `galactico/features/axes.py` | the claim record of each candidate |
| `EvidenceClass` | `galactico/domain/provenance.py` | evidence class on each spec |
| `load_public`, `assert_may_host` | `galactico/storage/public.py`, `galactico/providers/base.py` | licence posture in the runner |

Not reused, deliberately: `fit_league_xt` / `fit_xt` (no candidate uses xT); `run_league`
(v1 estimator, goalkeeper-inclusive, joint R-squared); `ConfoundVerdict.passed` (a different
rule); `AxisReliability.lower_bound`; the `ConstructSpec` machinery of `spec.py` (ROOT 4: a
definition and its implementation are one object, so `shot_volume` exists once, as a
`CandidateSpec`; section 11.2 generates any `ConstructSpec` form from it at promotion).

`experiments/` is a namespace package. The runner and the tests put the repository root on
`sys.path` (anchored to `Path(__file__)`), then `from experiments.run_replication import
decide, _safe_abs_corr`. Library modules never import `experiments`: the rule is a parameter.

## 3. `galactico/features/candidates.py` (WP-A)

Module docstring states: candidates are definitions under test, held outside `spec.SPECS`
because a sixth key there breaks five shipped things; nothing here is a validated construct;
the dict is named `CANDIDATES`, never `SPECS`.

```python
class CandidateMeasure(Enum):
    COUNT = "count"
    SUM_CONVERSION_VALUE = "sum of location-only conversion value"

@dataclass(frozen=True)
class Zone:
    name: str
    min_start_x_exclusive: float | None = None
    min_start_x_inclusive: float | None = None
    min_start_y_inclusive: float | None = None
    max_start_y_inclusive: float | None = None
    phrase: str = ""                       # config zones[*].phrase
    def mask(self, actions: pd.DataFrame) -> pd.Series      # False on sentinel starts
    @property
    def fingerprint(self) -> str           # "opponent_half[x>0.5]"

ZONES: dict[str, Zone]                     # exactly the two zones of config["zones"]
SENTINEL_STARTS: tuple[tuple[float, float], ...]   # config["location_sentinels"]

@dataclass(frozen=True)
class Clause:
    types: frozenset[str] = frozenset()
    subtypes: frozenset[str] = frozenset()
    flags: frozenset[str] = frozenset()    # boolean columns, all must be true
    zone: str | None = None
    def mask(self, actions: pd.DataFrame) -> pd.Series
    def noun(self) -> str
    @property
    def fingerprint(self) -> str

@dataclass(frozen=True)
class CandidateSpec:
    candidate_id: str
    family: str                            # "volume" | "style"
    measure: CandidateMeasure
    numerator: tuple[Clause, ...]          # union of clauses, each row counted once
    scaling: Scaling
    denominator: tuple[Clause, ...] = ()
    instrument: str | None = None
    evidence_class: EvidenceClass = EvidenceClass.DERIVED
    def describe(self) -> str
    @property
    def fingerprint(self) -> str

CANDIDATES: dict[str, CandidateSpec]       # 4 keys, order as in config
CLAIMS: dict[str, AxisSpec]                # same 4 keys; text of preregistration section 5

def rows(clauses: tuple[Clause, ...], actions: pd.DataFrame) -> pd.DataFrame
def capped_minutes(lineups: pd.DataFrame, *, cap: int) -> pd.Series     # minutes_rule
def evaluate_candidate(spec: CandidateSpec, actions: pd.DataFrame, minutes: pd.Series, *,
                       shot_values: pd.Series | None = None) -> pd.Series
__all__ = [...]
```

| Element | Exact behaviour |
|---|---|
| `Clause.mask` | AND of: `type in types` if `types`; `subtype in subtypes` if `subtypes`; each flag column truthy after `fillna(False)`; `ZONES[zone].mask` if `zone`. An empty clause raises `ValueError`; a flag named `success` or `clearance` raises |
| `Zone.mask` | the declared comparisons on `start_x`, `start_y`, AND NOT (start equals a sentinel pair). `opponent_half` is `start_x > 0.50` strictly; `penalty_area` is `start_x >= 0.84` and `0.19 <= start_y <= 0.81` |
| `rows` | rows matching any clause; `actions[mask_1 \| mask_2 \| ...]`; each row once |
| `capped_minutes` | `lineups.minutes.clip(upper=cap)` per row, summed by `player_id`; `cap` is `regulation_minutes_cap` |
| `Clause.fingerprint` | `"\|".join([",".join(sorted(types)), ",".join(sorted(subtypes)), ",".join(sorted(flags)), ZONES[zone].fingerprint if zone else "-"])` |
| union fingerprint | `"+".join(sorted(clause fingerprints))`; `"-"` for an empty tuple |
| `CandidateSpec.fingerprint` | `sha256("\x1f".join([candidate_id, measure.value, numerator_fp, scaling.value, denominator_fp, instrument or "-"]).encode()).hexdigest()[:12]` |
| `Clause.noun` | from `describe_nouns`: the subtype noun if `subtypes` (one subtype); else the flag noun if `flags` and no `types`; else the plural type noun |
| `CandidateSpec.describe` | `"{measure phrase} over {numerator phrase}, {scaling phrase}"`. Numerator phrase: one clause gives `noun + " " + zone phrase` (zone phrase omitted when there is no zone); several clauses that share one zone give their nouns joined by `" or "`, then `", "`, then the zone phrase. Scaling phrase: `per 90 minutes`, or `per ` + the singular noun of the one denominator clause's type (`types_singular`) |
| `__post_init__` | `PER_SELECTED_ACTION` without denominator raises; `PER_90` with one raises; `SUM_CONVERSION_VALUE` without `instrument` raises; `COUNT` with one raises; empty numerator raises; several numerator clauses with different zones raise (`describe` has no rule for them) |
| `evaluate_candidate`, COUNT | `numerator = rows(...).groupby("player_id").size().reindex(minutes.index).fillna(0.0)` |
| `evaluate_candidate`, SUM | `shot_values` required (Series indexed by `event_id`); every numerator row's `event_id` must be present or `KeyError` naming the count missing; sum per `player_id`, reindexed, `fillna(0.0)` |
| scaling | `PER_90`: `numerator * 90.0 / minutes.replace(0, nan)`. `PER_SELECTED_ACTION`: `numerator / rows(denominator).groupby("player_id").size().reindex(index).replace(0, nan)`; no denominator rows gives NaN, never 0 |
| unit | output index is `minutes.index`; a `player_id` of 0 is never in it |

Pinned payloads (the fingerprints in `config.json` were computed from exactly these; `<US>`
is `\x1f`):

| id | payload | sha256[:12] | `describe()` |
|---|---|---|---|
| `shot_volume` | `shot_volume<US>count<US>shot\|\|\|-<US>per 90 minutes<US>-<US>-` | `1c6517c2be31` | `count over shots, per 90 minutes` |
| `shot_location_value` | `shot_location_value<US>sum of location-only conversion value<US>shot\|\|\|opponent_half[x>0.5]<US>per 90 minutes<US>-<US>shot_location_v1` | `537cef62eb4e` | `sum of location-only conversion value over shots starting in the opponent half, per 90 minutes` |
| `box_shot_share` | `box_shot_share<US>count<US>shot\|\|\|penalty_area[x>=0.84;0.19<=y<=0.81]<US>per action in the denominator set<US>shot\|\|\|-<US>-` | `af2b2b118e73` | `count over shots starting in the penalty area, per shot` |
| `opp_half_defensive_actions` | `opp_half_defensive_actions<US>count<US>duel\|Ground defending duel\|\|opponent_half[x>0.5]+\|\|interception\|opponent_half[x>0.5]<US>per 90 minutes<US>-<US>-` | `72619cd8130b` | `count over ground defending duel records or interception-flagged events, starting in the opponent half, per 90 minutes` |

If an implementation yields another fingerprint the implementation is wrong. A verdict
attaches to these fingerprints. The house `ConstructSpec.describe` grammar differs (it would
read "..., per shots"); a later `SPECS` registration carries a cross-reference to the
`CandidateSpec` fingerprint it was generated from (section 11.2).

`tests/test_candidates.py` (hand-computable, in the style of `tests/test_spec_contract.py`):
fingerprints, display names and sentences equal `config.json`; `describe` follows its rule on
two invented specs beyond the four; zone edges at 0.50 / 0.51 and 0.83 / 0.84, 0.18 / 0.19,
0.81 / 0.82; sentinel starts excluded from zone clauses and kept in zone-free clauses; a row
matching both clauses of the union counted once; a flagged clearance counted once, as an
interception; a penalty and a direct free-kick shot (`type == "set_piece"`) never counted;
`player_id` 0 never credited; `capped_minutes` caps a starter substituted at minute 93 at 90;
per-90 scales with minutes and the share does not; a player with no shots has share NaN and
volume 0.0; `shot_volume` equals `compute_baselines(...)["shots_per_90"]` on the same frame
with the same minutes; a missing `event_id` in `shot_values` raises; `CANDIDATES.keys()` is
disjoint from `spec.SPECS`, `CONSTRUCTS`, `REJECTED`, `RESEARCH_ONLY`; `spec.SPECS` has
exactly its five shipped keys; no clause can read `success` or `clearance`; every display
name, sentence and claim text passes `labels.scan_labels`; no key or family string is in the
banned set.

## 4. `galactico/models/shots/` (WP-B)

Product-side package: pure functions, no threshold, no verdict, no file access. Package
docstring: "A location-only shot conversion model. It is a model (PREDICTIVE). It is not xG
supplied by the provider; the provider supplies none. It sees where a shot started and
whether the provider classed it head-or-body. It does not see defenders, the goalkeeper,
pressure, shot type, the shooter or the team. It says nothing about finishing."

```python
# geometry.py
def shot_geometry(start_x: np.ndarray, start_y: np.ndarray, *, pitch_length_m: float,
                  pitch_width_m: float, goal_width_m: float) -> tuple[np.ndarray, np.ndarray]
    # (distance_m, angle_rad) by the formulas of preregistration 4.1; atan2, no branch

# logistic.py
@dataclass(frozen=True)
class LogisticFit:
    coefficients: np.ndarray
    standard_errors: np.ndarray
    log_likelihood: float
    iterations: int
    converged: bool
def fit_logistic(design: np.ndarray, outcome: np.ndarray, *, offset: np.ndarray | None,
                 max_iterations: int, tolerance: float, max_halvings: int) -> LogisticFit
def predict_probability(coefficients: np.ndarray, design: np.ndarray, *,
                        offset: np.ndarray | None) -> np.ndarray

# model.py
@dataclass(frozen=True)
class ShotModelSpec:
    model_id: str                          # "M0" | "MD" | "M1" | "MFLEX"
    terms: tuple[str, ...]                 # exactly config["model_terms"][model_id]
def shot_models(config: Mapping) -> dict[str, ShotModelSpec]
SHOT_COLUMNS = ("event_id", "game_id", "team_id", "player_id", "start_x", "start_y",
                "distance_m", "angle_rad", "head_or_body", "counter_attack", "goal")
def shot_frame(actions: pd.DataFrame, *, in_domain: pd.Series, geometry: Mapping) -> pd.DataFrame
    # actions carries body_part (sidecar.attach); SHOT_COLUMNS, sorted by event_id
def design_matrix(spec: ShotModelSpec, shots: pd.DataFrame) -> np.ndarray
@dataclass(frozen=True)
class FittedShotModel:
    spec: ShotModelSpec
    coefficients: tuple[float, ...]
    standard_errors: tuple[float, ...]
    n_shots: int
    n_goals: int
    base_rate: float
    log_likelihood: float
    iterations: int
    converged: bool
def fit_shot_model(spec: ShotModelSpec, shots: pd.DataFrame, *, max_iterations: int,
                   tolerance: float, max_halvings: int) -> FittedShotModel
def predict(model: FittedShotModel, shots: pd.DataFrame) -> np.ndarray
```

| Element | Exact behaviour |
|---|---|
| `shot_frame` | rows with `type == "shot"` where `in_domain` is true; the caller passes `ZONES["opponent_half"].mask(actions)`, so the model domain and the numerator of `shot_location_value` are one predicate (no sentinel start, `start_x > 0.50`); `head_or_body = (body_part == head_or_body_value)` as int; a shot row with null `body_part` raises `ValueError` with the count (coverage is pinned); includes `player_id` 0 rows (location and label are valid); `goal` as int |
| terms | `intercept` 1; `distance_m`; `angle_rad`; `head_or_body`; `a*b` product; `hinge(v,k)` is `max(v - k, 0)` |
| `fit_logistic` | Newton / IRLS from zero coefficients on internally standardised non-constant columns, back-transformed; step halving while the log-likelihood falls (at most `max_halvings` halvings); stop when the largest absolute coefficient change on the standardised scale is below `tolerance`; `converged=False` at `max_iterations` or on a singular information matrix, never an exception; `standard_errors = sqrt(diag(inv(X'WX)))`; no penalty |
| `M0` | not fitted: `predict` returns the training goal rate for every row, `converged=True` by definition |
| `predict` | probabilities in the open unit interval, unclipped |

`tests/test_shot_model.py`: geometry at hand-computed points (penalty spot (0.895, 0.5):
d 11.025 m; goal-line centre: theta pi; goal-line outside the post: theta 0; symmetry in
`start_y` about 0.5); a (1,1) and a (0,0) shot are outside `shot_frame` and a (0.51, 0.5) shot
is inside; design matrices term by term; recovery of planted coefficients within four
standard errors at 40,000 synthetic shots; log-likelihood gradient at the fit below 1e-6 in
absolute value; `M0` equals the training mean; permutation of rows changes nothing; a
separable toy sample returns `converged=False`; offset fit recovers a known intercept; no
symbol named after the banned words; no `xg` identifier (`grep`-style source test).

## 5. `galactico/validation/shot_model_evaluation.py` (WP-C)

```python
def brier(p: np.ndarray, y: np.ndarray) -> float
def log_loss(p: np.ndarray, y: np.ndarray, *, clip: float) -> float
def skill(loss: float, reference_loss: float) -> float | None           # 1 - loss/reference; None if reference <= 0
def observed_over_expected(p: np.ndarray, y: np.ndarray) -> float | None
def calibration_slope(p, y, *, clip, max_iterations, tolerance, max_halvings) -> float | None
def calibration_intercept(p, y, *, clip, max_iterations, tolerance, max_halvings) -> float | None
def calibration_bins(p: np.ndarray, y: np.ndarray, *, n_bins: int) -> list[dict]   # n, mean_probability, observed_rate
def calibration_error(bins: list[dict]) -> tuple[float, float]          # (ece, mce)
def auroc(p: np.ndarray, y: np.ndarray) -> float | None                 # average ranks for ties

@dataclass(frozen=True)
class LoloResult:
    predictions: Mapping[str, pd.DataFrame]   # league -> SHOT_COLUMNS + p_M0, p_MD, p_M1, p_MFLEX
    fits: Mapping[str, Mapping[str, FittedShotModel]]   # held-out league -> model_id -> fit without it
    sample_gate: Mapping[str, object]         # counts per fold; s_count_passed, s_fit_passed: bool | None; reasons
def leave_one_league_out(shots: Mapping[str, pd.DataFrame], config: Mapping) -> LoloResult
def select_instrument(lolo: LoloResult, config: Mapping) -> dict        # {"instrument", "pooled_gain", "fold_gains", "folds_meeting", "challenger_converged"}
def match_resample_weights(n_matches: int, *, replicates: int, seed: int, league_position: int) -> np.ndarray
def instrument_report(lolo: LoloResult, instrument: str, config: Mapping) -> dict   # section 7 "instrument" block
def instrument_verdict(report: dict, config: Mapping) -> tuple[str, tuple[str, ...]]   # token, failed gate ids
def shot_values(lolo: LoloResult, instrument: str) -> dict[str, pd.Series]   # league -> Series indexed by event_id
```

| Element | Exact behaviour |
|---|---|
| fold f | fit `MD`, `M1`, `MFLEX` on the concatenation of the other leagues' shot frames; predict league f; `p_M0` is the training goal rate |
| gate S-count | evaluated from counts before any fit (`gate_s_count`); on failure return a `LoloResult` with empty `predictions`, `s_count_passed=False`, `s_fit_passed=None` |
| gate S-fit | after the fits: every model of `gate_s_fit_models` converged in every fold (`gate_s_fit_rule`); on failure the predictions are kept for the report and the token is `INCONCLUSIVE`. A challenger that did not converge in every fold is recorded and is not selectable |
| selection | 4.3 of the protocol; `MFLEX` only when `challenger_converged` is true in every fold |
| resampling | `bootstrap_rule`: `np.random.default_rng([config["seed"], league_position]).multinomial(n, [1/n]*n, size=bootstrap_replicates)` over the league's sorted `game_id`s; statistics recomputed from per-match sums (`sum (p-y)^2`, `sum (p0-y)^2`, log-loss sums of the instrument and of `MD`); pooled statistics add the five leagues' replicate sums |
| intervals | `np.quantile(..., method=interval_quantile_method)` at `interval_quantiles` of the replicate statistic |
| R2 | `gate_r2_gain`: relative gain `(LL_MD - LL_inst) / LL_MD` of the pooled sums, per replicate |
| bins | `ece_binning_rule`: sort by probability; for k = 1 .. `ece_bins` - 1 the cut is the first index at or after `k * n / ece_bins` at which the probability value changes; equal cuts merge; a bin never holds part of a run of tied values. No event id enters |
| `calibration_error` | ECE `sum(n_b / n * abs(mean_probability_b - observed_rate_b))` (`ece_weighting`); MCE the largest of those absolute gaps (`mce_rule`) |
| calibration fits | slope: logistic regression of y on `a + b * logit(p)`; intercept: of y on `a` with offset `logit(p)`; `p` clipped at `probability_clip` for the logit; a fit that does not converge returns `None`, which fails its gate in that league (`calibration_fit_failure`) |
| subgroups (R4) | pooled over the five held-out leagues, by the predicates of `gate_r4_subgroups` |
| AUROC | `auroc_rule`: on the concatenated out-of-league predictions; average ranks |
| null calibration error | `ece_null_draws` draws of `y ~ Bernoulli(p)` per league with `default_rng([ece_null_seed, league_position])`; report the 50th, 95th, 99th percentile of ECE and MCE; reported, not a gate |
| verdict | preregistration 4.5, first failing class wins; `failed` lists every failed gate id |
| undefined statistic | any `None` in a gated statistic fails that gate and is listed |

`tests/test_shot_model_evaluation.py`: each metric against a hand-computed six-row case;
AUROC with ties; bins of a toy with a tied run straddling a cut: the run stays in one bin and
the result is invariant to row order; ECE of a two-bin toy; skill is `None` on a zero
reference; **leakage** (flipping every label of the held-out league leaves its predictions
byte-identical and changes the other four leagues' predictions); training base rate, not test
rate, is the reference; resample weights depend only on seed and league position; every gate
R1 to R5, L1 to L3, S-count and S-fit reachable in both directions from a hand-built report
dict; a non-converged challenger leaves the instrument at `M1` and S passes; a non-converged
`M1` in one fold gives `INCONCLUSIVE`; a non-converged calibration fit fails its gate;
verdict mapping exhaustive over the 2^10 pass/fail combinations with exactly one token each;
the selection rule at both edges (0.0099 / 0.0100 pooled; 3 / 4 folds).

## 6. `galactico/validation/candidate_gauntlet.py` (WP-D)

```python
@dataclass(frozen=True)
class LeagueFrames:
    league: str
    actions: pd.DataFrame      # action_columns minus provider, plus body_part, shot_family (sidecar.attach)
    lineups: pd.DataFrame      # game_id, team_id, player_id, minutes
    players: pd.DataFrame      # player_id, position

@dataclass(frozen=True)
class GateCount:
    league: str; candidate: str
    eligible: int; audit_units: int | None; reliability_units: int
    position_groups: Mapping[str, int]; dropped_position_groups: tuple[str, ...]
    unattributed_share: float | None
    passed: bool; reasons: tuple[str, ...]

@dataclass(frozen=True)
class ReliabilityEstimate:
    n: int; groups: int; r_half: float | None; r_sb: float | None
    house_low: float | None; house_high: float | None; half_low: float | None

@dataclass(frozen=True)
class LeagueEvaluation:
    league: str; candidate: str; gate: GateCount
    status: str                       # "INCONCLUSIVE" | "SHIP" | "SHIP_WITH_BAND" | "REJECT"
    reject_reason: str | None         # "REDUNDANT" | "CONFOUNDED" | "UNRELIABLE"
    inconclusive_reason: str | None   # gate reason, or "DEGENERATE:<vector>", or "NON_FINITE:<input>"
    centred: ReliabilityEstimate | None           # gating
    raw_pooled: ReliabilityEstimate | None        # reported
    within_position: Mapping[str, ReliabilityEstimate | None]   # reported
    team_and_position_centred: ReliabilityEstimate | None       # reported
    baseline_correlations: Mapping[str, Mapping[str, float | None]]   # column -> {"raw", "centred", "gating"}
    dropped_battery_columns: tuple[str, ...]
    closest_baselines: tuple[str, ...]; baseline_r: float | None
    nuisance_r2: float | None; nuisance_r2_raw: float | None; nuisance_r2_centred: float | None
    joint_r2: float | None; joint_r2_adjusted: float | None; joint_regressors: int | None
    joint_noise_floor: float | None; ordering_rho: float | None
    top_k_kept: int | None; top_k_tied_raw: int | None; top_k_tied_adjusted: int | None
    house_joint_r2: float | None; house_joint_r2_exceeds_ceiling: bool | None
    damaging_confounds: tuple[str, ...]
    departures_active: tuple[str, ...]            # the lenient departures of preregistration 6.1 in force
    mean: float | None; sd: float | None; zero_share: float | None
    match_set_minutes_share_p05_p95: tuple[float, float] | None
    rule_reasons: tuple[str, ...]

@dataclass(frozen=True)
class CandidateVerdict:
    candidate: str; token: str; rule_row: int
    evaluable: int; surviving: int; ship: int; rejected: int
    statuses: Mapping[str, str]; reject_reasons: Mapping[str, str]
    context_limits: tuple[str, ...]
    house_replication_label: str | None

Rule = Callable[[float, float, float, bool], tuple[Status, tuple[str, ...]]]

def match_set_of_game(actions: pd.DataFrame) -> pd.Series                 # index game_id, values 0/1
def eligible_minutes(lineups: pd.DataFrame, players: pd.DataFrame, config: Mapping) -> pd.Series
def player_team(lineups: pd.DataFrame, config: Mapping) -> pd.Series
def unattributed_duel_share(actions: pd.DataFrame, lineups: pd.DataFrame, index: pd.Index) -> pd.Series
def baseline_battery(frames: LeagueFrames, minutes: pd.Series, shot_volume: pd.Series,
                     config: Mapping) -> pd.DataFrame
def count_gates(spec: CandidateSpec, frames: LeagueFrames, config: Mapping) -> GateCount
def centre(values: pd.Series, groups: pd.Series) -> pd.Series
def reliability_estimate(first: pd.Series, second: pd.Series, *, groups: pd.Series | None,
                         config: Mapping, label: str) -> ReliabilityEstimate
def reject_reason(rule: Rule, reliability_low: float, nuisance_r2: float, baseline_r: float,
                  kind_is_nuisance: bool) -> str | None
def evaluate_league(spec: CandidateSpec, frames: LeagueFrames, gate: GateCount,
                    shot_values: pd.Series | None, rule: Rule, config: Mapping) -> LeagueEvaluation
def candidate_verdict(spec: CandidateSpec, evaluations: Sequence[LeagueEvaluation],
                      instrument_token: str, config: Mapping) -> CandidateVerdict
def run_gauntlet(frames: Mapping[str, LeagueFrames], shot_values: Mapping[str, pd.Series] | None,
                 instrument_token: str, rule: Rule, config: Mapping) -> dict
```

| Element | Exact behaviour |
|---|---|
| `match_set_of_game` | `games = sorted(actions["game_id"].unique())`; set = position in `games` modulo 2 (`split_rule`). Identical to `run_replication.py` lines 219 to 223 |
| `eligible_minutes` | `capped_minutes(lineups, cap=regulation_minutes_cap)`; keep `>= minutes_floor`, position in `outfield_positions`, id != 0 |
| `player_team` | team with the most capped minutes; ties to the smallest `team_id` (`player_team_rule`) |
| `baseline_battery` columns | from `compute_baselines(actions[player in index], minutes)`: `minutes, touches, touches_per_90, passes_per_90, pass_completion, mean_x, mean_y, mean_pass_length`; `shot_volume` = the candidate value (asserted equal to `shots_per_90` to 1e-12, same minutes); `opp_half_on_ball_per_90` by `opp_half_on_ball_rule` (types pass or touch, interception flag false, zone `opponent_half`, per 90); `duel_or_interception_per_90` by `duel_or_interception_rule`; `unattributed_duel_share`. All coerced to float64 (`pass_completion` is object dtype upstream) |
| `unattributed_duel_share` | for team t in match m, `u = (ground defending duel rows with player_id 0) / (ground defending duel rows)` (0.0 if none); per player the capped-minutes-weighted mean of `u` over his rows of `lineups` |
| `count_gates` | structure only. A: eligible with a finite full-season value (share floor applied when `share_floor`, counting denominator rows, `share_floor_counts`); R: A with both match-set floors (and match-set share floors); position groups in R below `minimum_position_group` are dropped from R and listed; `unattributed_share` for `opp_half_defensive_actions` = share of pitch-wide union rows with `player_id` 0 in the league; reasons from config gate names |
| match-set values | `evaluate_candidate(spec, actions of match set h for players in R, match-set-h capped minutes, shot_values=...)` |
| `centre` | value minus the mean over the same group among the units passed in |
| `reliability_estimate` | `r_half, n = split_half_reliability(a.to_dict(), b.to_dict(), correct=False)` on the centred values keyed by player id; `g` = groups passed (1 when `groups` is None); `r_sb = spearman_brown(r_half)`; `house = AxisReliability(label, r_sb, n, minutes_floor, period).interval` (None stays None, reported); `half_low = spearman_brown(tanh(atanh(r_half) - interval_z / sqrt(n - 2 - g)))` when `r_half` is finite, `abs(r_half) < 1` and `n - 2 - g >= 1`, else None (`half_low_rule`). The gating value is `half_low` (`reliability_low_rule`) |
| baseline | for each battery column with sd over A at least `degenerate_sd` (others dropped and recorded): `raw = _safe_abs_corr(value, column)` over A; `centred = _safe_abs_corr(centre(value, position), centre(column, position))` over A; `gating = max(raw, centred)` with NaN propagating (`baseline_centring`); `baseline_r = max(gating)`; `closest_baselines` = every column whose `gating` equals it, in battery order (`baseline_tie_rule`) |
| nuisance | `nuisance_r2 = max(R2 raw, R2 centred)` of the value on `nuisance_columns` over A (`nuisance_centring`), by `residualise`; `None` if there are none |
| joint audit (reported) | `discriminant_validity(value, [touches, team one-hot drop-first, position one-hot drop-first], key=id, top_k=top_k, ties=rank_ties)`; adjusted `1 - (1 - R2)(n - 1)/(n - k - 1)`; floor `k/(n - 1)`; `top_k_kept = top_k_survivors` (None on a tie, with the two tied counts and `top_k_tied_statement` in the report); `house_joint_r2` on `[touches, team one-hot]` and its comparison with `nuisance_r2_ceiling`, for candidates with a nuisance column only |
| guard | each vector of `degenerate_vectors` tested on its own: sd below `degenerate_sd`, or zero share above `maximum_zero_share`; then any non-finite rule input or a None `half_low`: status `INCONCLUSIVE`, `inconclusive_reason` names the vector or input, rule not called |
| rule call | `rule(half_low, nuisance_r2 if not None else 0.0, baseline_r, bool(nuisance_columns))` |
| `reject_reason` | `REDUNDANT` if `rule(1.0, 0.0, baseline_r, False)` rejects; else `CONFOUNDED` if `rule(1.0, nuisance_r2, 0.0, kind_is_nuisance)` rejects; else `UNRELIABLE` if `rule(reliability_low, 0.0, 0.0, False)` rejects; else `None`. Thresholds therefore live only in the frozen rule |
| `departures_active` | the lenient departures of preregistration 6.1 in force for this league and candidate: `identity_column` (`shot_volume`), `presence_column_without_candidate_rows`, `nuisance_only_r2` (candidates with a nuisance column), `goalkeepers_excluded` |
| within position, context limits | `reliability_estimate` on one position's players in R, uncentred, `g = 1` (`within_position_rule`), when that position has at least `within_position_report_minimum` players; `context_limits` by `context_limit_rule` over the five leagues |
| `candidate_verdict` | the eight rows of preregistration 9.1, in order; E is the leagues whose status is in `evaluable_statuses`; `rule_row` records which fired; `house_replication_label = classify_replication(...)` over evaluable leagues, reported |
| order in `run_gauntlet` | all `count_gates` for all candidates and leagues first; a candidate with fewer than `minimum_evaluable_leagues` passing gets no statistic computed; `shot_location_value` gets none unless the instrument token is `ACCEPTED` or `ACCEPTED_WITHIN_LEAGUE` |

`tests/test_candidate_gauntlet.py`: `decide` pinned: `lf_sha256_text(inspect.getsource(decide))`
equals `frozen_rule_decide_source_sha256`, the three module constants equal
`frozen_rule_constants` and equal `baseline_ceiling`, `reliability_number`,
`reliability_band`, and a truth table written from the protocol (edges 0.85 / 0.8501,
0.60 / 0.6001 with and without nuisance, which ties the literal to `nuisance_r2_ceiling` and
`frozen_rule_nuisance_literal`, 0.70 / 0.6999, 0.50 / 0.4999; NaN baseline documented as
passing the raw rule and caught by the guard); `reject_reason` for each of the three reasons
and for none; token rows 1 to 8 each reached, including every case listed in preregistration
9.1, plus exhaustiveness over every multiset of five league statuses with reasons and both
instrument states (one token each, no exception); `r_half = -0.4` at n = 66 gives `REJECT`
with reason `UNRELIABLE`, and `r_half = -1/3` the same; `match_set_of_game` equals the house
expression on a shuffled frame; centring removes a planted position effect and leaves a
planted player effect; `half_low` on hand numbers with g = 3 and the house interval on the
same; `half_low <= house_low` on a grid wherever both exist; a within-position near-copy of a
battery column is caught by the centred correlation while its raw correlation is below the
ceiling; a pure position effect is caught by the raw correlation; the nuisance R-squared takes
the larger centring; each departure of preregistration 6.1 shown in its stated direction on a
planted frame, each lenient one listed in `departures_active`; a constant vector, a match-set
vector with 0.5001 zeros (and not with 0.50) and an all-NaN battery give `INCONCLUSIVE` naming
the vector, never `SHIP`; goalkeepers and `player_id` 0 absent from every set; gate counts
computed before any value (a spy on `evaluate_candidate` shows zero calls when gates fail);
row-order invariance of the whole league evaluation, including a planted tie at the twelfth
place giving `top_k_kept` None with the tied counts; every returned field `None` rather than
NaN.

## 7. Runner, results, hashes

`experiments/run_candidate_gauntlet.py` (WP-E). Paths anchored to
`ROOT = Path(__file__).resolve().parents[1]`. Reads Parquet with a column list through
`load_public`, one league at a time for the gauntlet; the five shot frames are held together
(about 40,000 rows).

```python
def load_config() -> dict
def load_league(league: str, config: Mapping) -> LeagueFrames
def frame_digest(frame: pd.DataFrame, *, sort_by: Sequence[str], columns: Sequence[str]) -> str
def preflight(config: Mapping, *, protocol_commit: str | None) -> dict     # structure only
def run(config: Mapping, *, protocol_commit: str) -> dict
def render_model_card(results: Mapping) -> str
def main(argv: Sequence[str] | None = None) -> int
```

Phases of `run`, in order. Nothing in phases 1 to 4 reads an outcome.

| # | Phase | Stops the run with nothing written if |
|---|---|---|
| 1 | provenance | `lf_sha256_text(inspect.getsource(decide))` differs from `frozen_rule_decide_source_sha256`, or a constant of `frozen_rule_constants` differs from the module's; `lf_sha256(PIPELINE.md)` differs from `pipeline_spec_sha256`; any candidate fingerprint differs from config; `--protocol-commit` is not the commit that first added `preregistration.md` under `committed_experiment_dir` (read-only `git log --diff-filter=A --format=%H -- <path>`), a later commit touched one of the three protocol files, or a working-tree LF hash differs from the LF hash of `git show <commit>:<path>`; the output file already exists (unless `--determinism-rerun` to another path). The LF hash of `frozen_rule_path` is recorded in provenance and does not stop the run (`frozen_rule_file_hash_role`) |
| 2 | structural pins | any `expected_*` of config differs or is null; the period filter drops a row; a shot has no body part; a shot-family disagreement (`shot_family_pins`); the sidecar of I1 fails |
| 3 | self-check | section 8 predicate not met |
| 4 | count gates | never stops; gates are recorded |
| 5 | instrument | — |
| 6 | candidates | — |
| 7 | write | the serialised artifact exceeds `results_maximum_bytes`, contains a banned key or a key of `results_identifier_key_denylist`, or `json.dumps(..., allow_nan=False)` raises |

Written as `Path.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8", newline="\n")`. Never stdout redirection.

### 7.1 `results.json` shape (aggregate only)

```
{
  "experiment": "E-09", "version": "player-candidates-v2", "tier": "PUBLIC",
  "verdicts": {"<subject>": {"token": "...", "reason": null | "<rule_row and closure>"}},
  "provenance": {
    "experiment": "E-09", "protocol_commit": "...", "protocol_hash": "...", "config_hash": "...",
    "pipeline_hash": "...", "providers": ["pappalardo"],
    "source_hash_policy": "sha256 of LF-normalised bytes",
    "source_hashes": {"<posix path>": "..."},
    "frozen_rule": {"path": "...", "function": "decide", "source_sha256": "...", "constants": {...},
                    "file_lf_sha256": "..."},
    "candidate_fingerprints": {"shot_volume": "1c6517c2be31", ...},
    "frame_hashes": {"<league>": {"actions": "...", "lineups": "...", "players": "...", "sidecar_events": "..."}},
    "sidecar": {"<league>": { ...sidecar.provenance(league)... }},
    "raw_manifest_sha256": "...", "packages": {"numpy": "...", "pandas": "...", "pyarrow": "..."},
    "data_license": "...", "reuse_disclosure": "...", "config": { ...verbatim... }
  },
  "selfcheck": {"passed": true, "replicates": 12,
                "worlds": {"EFFECT": {"<subject>": {"<token>": count}}, ...},
                "league_assertions": {"NULL": {...}, "NUISANCE": {...}},
                "generator_sanity": {...},
                "instrument_scenarios": {"PLANTED": {"<token>": count}, ...}},
  "structure": {"<league>": {"matches", "shot_rows", "in_domain_shot_rows", "behind_halfway_shot_rows",
                             "sentinel_start_shot_rows", "goal_rows_on_shots", "eligible_players",
                             "eligible_by_position": {...}, "union_rows", "union_rows_unattributed"}},
  "instrument": {
    "sample_gate": {"s_count_passed", "s_fit_passed", "reasons", "folds": {"<held-out league>": {"train_shots",
                    "train_goals", "heldout_shots", "heldout_goals", "training_rate", "converged": {...}}}},
    "fits": {"<held-out league>": {"<model>": {"terms": [...], "coefficients": [...],
             "standard_errors": [...], "converged", "iterations", "log_likelihood"}}},
    "selection": {"instrument", "specification", "pooled_gain", "fold_gains": {...}, "folds_meeting",
                  "challenger_converged"},
    "leagues": {"<held-out league>": {"<model>": {"brier", "log_loss", "brier_skill", "log_loss_skill",
                "observed_over_expected", "calibration_slope", "calibration_intercept", "ece", "mce",
                "auroc"}, "brier_skill_interval": [lo, hi], "calibration_bins": [{"n",
                "mean_probability", "observed_rate"}], "null_calibration_error": {...}}},
    "pooled": {"<model>": {...same metrics...}, "brier_skill_interval": [lo, hi],
               "log_loss_gain_over_comparator": x, "log_loss_gain_interval": [lo, hi],
               "subgroups": {"<name>": {"n", "goals", "observed_over_expected"}},
               "descriptive_subgroups": {"counter_attack": {...}}},
    "gates": {"S_count": {"passed", "detail"}, "S_fit": ..., "R1": ..., "R5": ..., "L1": ..., "L3": ...},
    "token": "...", "failed_gates": [...]
  },
  "candidates": {
    "<candidate>": {
      "definition": "...", "fingerprint": "...", "evidence_class": "...",
      "leagues": {"<league>": { ...every LeagueEvaluation field, GateCount nested... }},
      "token": "...", "rule_row": n,
      "evaluable": n, "surviving": n, "ship": n, "rejected": n,
      "context_limits": [...], "house_replication_label": "..."
    }
  },
  "registry_effect": {"<subject>": {"registry_move": "...", "player_lab_headline": "..." | null}},
  "predictions": { ...preregistration section 12, verbatim, with "matched": bool per subject... },
  "interpretation_limits": "..."
}
```

Rules: no player, team or match identifier anywhere (the only ids are league names); no key
in `results_identifier_key_denylist` or refused by `banned_key_paths(..., parts=BANNED_KEY_PARTS)`
(no key named `rank`, `ranking`, `score`, `total`, `index` and the like); a missing value is
`null`; counts are ints; under `results_maximum_bytes` (expected about 70 KB). The top-level
`experiment`, `tier` and `verdicts` are the contract `tests/test_verdict_registry.py` reads.

### 7.2 Hash discipline

| Hash | Of | How |
|---|---|---|
| `protocol_hash`, `config_hash`, `pipeline_hash` | the three registered files | `lf_sha256(path)` |
| `source_hashes` | `experiments/run_candidate_gauntlet.py`, `experiments/run_replication.py`, `galactico/features/{candidates,spec,axes}.py`, `galactico/models/shots/*.py`, `galactico/validation/{candidate_gauntlet,shot_model_evaluation,candidate_synthetic,lifecycle,replication,digests}.py`, `galactico/reliability/{core,confound}.py`, `galactico/ingestion/sidecar.py`, `galactico/providers/pappalardo.py` (it sets type, subtype, the flags and the coordinates of every neutral column read), `galactico/storage/public.py` | `lf_sha256`; keys `.as_posix()` relative to the root |
| `frozen_rule` | `decide` and its module | `source_sha256` = `lf_sha256_text(inspect.getsource(decide))` (gating, phase 1); `file_lf_sha256` = `lf_sha256(frozen_rule_path)` (recorded only) |
| `frame_hashes` | the frames actually used | `frame_digest`: select the listed columns in the listed order, cast `success` to nullable boolean and ids to int64, sort by the key (`event_id`; lineups by `game_id, player_id`; players by `player_id`), `reset_index(drop=True)`, `sha256(pd.util.hash_pandas_object(frame, index=False).values.tobytes())`. Parquet file bytes are **not** hashed: the footer embeds the pandas version |
| `sidecar` | each league's sidecar | `sidecar.provenance(league)` verbatim (schema and tag-mapping versions, content hashes, raw digests) |
| `raw_manifest_sha256`, `raw_file_sha256` | `data/public/pappalardo/MANIFEST.json` | `lf_sha256` of the manifest; plus the manifest's own SHA-256 entries for the five leagues' events and matches files and for `players.json`, echoed verbatim |
| `protocol_commit` | git | verified in phase 1; never a literal in source; the commit that first added `preregistration.md`, as `VerdictRecord.protocol_commit` defines it |
| results | `results.json` | root records `lf_sha256` of it in the five records |

### 7.3 The commands

Preflight, any number of times, before or after the protocol commit (structure and
synthetic only; prints the gate counts, the structural pins and the self-check table; writes
nothing in the repository):

    .venv/Scripts/python.exe -B experiments/run_candidate_gauntlet.py --preflight

**The single command the root runs for the real execution, once:**

    .venv/Scripts/python.exe -B experiments/run_candidate_gauntlet.py --protocol-commit <sha> --out experiments/preregistered/E-09-player-candidates/results.json

Determinism re-run (must be byte-identical; exit code 1 otherwise):

    .venv/Scripts/python.exe -B experiments/run_candidate_gauntlet.py --protocol-commit <sha> --determinism-rerun --out <scratchpad>/E-09-rerun.json

Model card, generated from the committed results, never typed:

    .venv/Scripts/python.exe -B experiments/run_candidate_gauntlet.py --render-card experiments/preregistered/E-09-player-candidates/results.json

## 8. Synthetic suite and the planted checks

`galactico/validation/candidate_synthetic.py`. **Independent of what it checks**: it imports
numpy and pandas only, plus `LeagueFrames` as a container. It writes its own geometry from
the formulas in the protocol and builds neutral-schema rows directly, with `body_part` and
`shot_family` columns as the sidecar would attach them. An `ast` test asserts it imports
nothing from `features.candidates`, `models.shots`, `shot_model_evaluation` or the gauntlet's
functions.

```python
def synthetic_league(world: Mapping, *, world_position: int, league_position: int,
                     replicate: int, config: Mapping) -> LeagueFrames
def synthetic_corpus(world: Mapping, *, world_position: int, replicate: int,
                     config: Mapping) -> dict[str, LeagueFrames]
def synthetic_shots(scenario: Mapping, *, scenario_position: int, replicate: int,
                    config: Mapping) -> dict[str, pd.DataFrame]
def generator_sanity(config: Mapping) -> dict
def run_selfcheck(rule: Rule, config: Mapping) -> dict          # the "selfcheck" block of results.json
```

Seeds: `selfcheck_seed_rule` (worlds and scenarios on separate streams; resampling inside the
self-check as in the real run).

### 8.1 Generator (per league; parameters are the `synthetic_*` keys)

| Step | Rule |
|---|---|
| squad | `synthetic_teams` teams; per team `synthetic_position_counts` outfield players and `synthetic_goalkeepers_per_team` goalkeeper; the last DF and the last MD are fringe players (`synthetic_fringe_positions`) |
| fixtures | double round-robin by the circle method, `synthetic_rounds` rounds, 380 matches; `game_id` increases with the round |
| appearances | a regular plays a match with probability `synthetic_regular_appearance_probability`, a fringe player with `synthetic_fringe_appearance_probability`; 90 minutes when he plays; the goalkeeper always plays |
| passes | `synthetic_passes_per_player_match` per player-match; `type "pass"`, start and end uniform on the unit square, rounded to `synthetic_coordinate_decimals`; `success` true with probability `synthetic_pass_success_probability` |
| shots | per player-match Poisson(rate); rate = position mean x lognormal(0, `shot_rate_log_sd`) with unit mean, drawn once per player; distance ~ Gamma(shape `synthetic_distance_gamma_shape`, scale s/shape) x (`synthetic_head_or_body_distance_factor` if head-or-body), clipped to `synthetic_distance_clip_m`, with s the player's distance scale (`distance_scale_m`); lateral offset = min(abs(Normal(0, `synthetic_lateral_sd_m`)), distance), on the attacker's left with probability `synthetic_lateral_left_probability`; head-or-body with probability `synthetic_head_or_body_probability`; coordinates rounded to `synthetic_coordinate_decimals`; goal ~ Bernoulli(logistic(`synthetic_truth_coefficients` . features of the rounded coordinates)); `shot_family` `open_play` |
| ground defending duels | opponent-half and own-half counts per player-match are independent Poissons with the player's two rates: position mean x unit-mean lognormal with `opp_half_duel_rate_log_sd` and `own_half_duel_rate_log_sd`, or, where `shared_duel_rate_log_sd` is set, one shared unit-mean lognormal multiplier on both; `start_x` uniform on the integer percents of `synthetic_duel_start_x_percent`; `start_y` uniform on the unit square, rounded; each record's `player_id` set to 0 with the team's unattributed probability (linear from `low` to `high` across teams) |
| interceptions | per player-match Poisson(`interception_ratio` x duel rate) in each half region; a `touch` row with `interception` true; never unattributed |
| goalkeeper | pass rows only |
| planted traps in every league | one penalty and one direct free-kick shot per team (`type "set_piece"`, `shot_family` `penalty` / `free_kick`), two shots with `start_x <= 0.50`, one duel row and one shot row at the (1,1) sentinel and one shot row at (0,0), one shot by `player_id` 0 |

### 8.2 Planted worlds (candidates; five synthetic leagues each)

| World | What is planted | Must be classified (config `expected`, `never`) |
|---|---|---|
| `EFFECT` | within-position spread in shot rate, player-specific shot distance scale independent of rate, within-position spread in both duel rates, flat unattributed share | instrument `ACCEPTED` or `ACCEPTED_WITHIN_LEAGUE`; all four candidates `ESTABLISHED_NUMBER` or `ESTABLISHED_BAND` |
| `NULL` | no within-position spread in anything; strong position means; one distance scale | every candidate `NOT_ESTABLISHED_*` (`shot_location_value` `NOT_ESTABLISHED_REDUNDANT`); never `ESTABLISHED_*`. League assertions (`league_assertions`): the raw pooled reliability of `shot_volume` above 0.70 and its centred bound below the band in every replicate league, which documents why the gate is position-centred |
| `NUISANCE` | one opponent-half duel rate for everyone; own-half rate widely spread; team-level unattributed probability across a range that keeps the league's union share at or below `maximum_unattributed_share` | `opp_half_defensive_actions` `NOT_ESTABLISHED_CONFOUNDED`; never `ESTABLISHED_*` or `INCONCLUSIVE`. League assertion: union share at most the gate in every replicate league |
| `REDUNDANT_WITHIN_POSITION` | as `EFFECT`, but one shared multiplier on a player's two duel rates, so within a position the candidate is a fixed share of all his defensive activity | `opp_half_defensive_actions` `NOT_ESTABLISHED_REDUNDANT`; never `ESTABLISHED_*` |

Generator sanity assertions (about the data, not the pipeline; `synthetic_generator_sanity`
and `generator_sanity_rules`): in `EFFECT` the population correlation between a player's
latent shot rate and his latent value rate is below its bound; in `NUISANCE` the latent
share of the opponent-half value's variance carried by team attribution is above its bound.

### 8.3 Planted instrument scenarios (five leagues x `synthetic_instrument_shots_per_league`)

Distance scale `synthetic_instrument_distance_scale_m` for every shot; match ids by
`synthetic_instrument_match_rule`; otherwise the shot rule of 8.1.

| Scenario | What is planted | Must be classified |
|---|---|---|
| `PLANTED` | every league follows the truth coefficients | `ACCEPTED` or `ACCEPTED_WITHIN_LEAGUE` always, `ACCEPTED` in at least the stated count |
| `NO_SIGNAL` | goal probability `goal_rate` for every shot | `NOT_ESTABLISHED` |
| `TOO_SHARP` | logit multiplied by `logit_multiplier` around its median, shifted by `logit_shift` | `NOT_ESTABLISHED`, with R5 among the failed gates |
| `LEVEL_SHIFT` | one league's odds multiplied by `odds_multiplier` | `ACCEPTED_WITHIN_LEAGUE`; never `ACCEPTED` |
| `SLOPE_SHIFT` | one league's logit, centred on its median, multiplied by `logit_slope_multiplier` | `NOT_ESTABLISHED`, with R3 among the failed gates |

**Feasibility, checked at event level before this revision was written.** The reviser
implemented this generator, the gauntlet of preregistration 6, the decision rule of 9 and
the instrument gates of 4 (with the bootstrap) in a throwaway script on synthetic numbers
only, and ran each world and scenario for 40 replicates. The counts are in
`selfcheck_feasibility`; every predicate held with the margins recorded there, and the
`minimum_replicates_matching` values were set from them. The script is a working note, not
kept; the pipeline's own self-check is the check that binds.

**What may be adjusted, and until when.** `synthetic_*` parameters may be edited until the
protocol commit if a stated rate is not met, with the reason recorded in the implementer's
report. Thresholds, gates, the decision rule and the rates themselves may not be edited to
make a check pass. After the protocol commit nothing in `config.json` changes; a self-check
that fails after registration stops the run, and the protocol is superseded by a new
experiment id (ADR-0029, Reversal).

### 8.4 Test files

| File | Content | Marker |
|---|---|---|
| `tests/test_candidate_planted.py` | 8.2 and 8.3 at `selfcheck_replicates`; the league assertions; the generator sanity assertions; the independence `ast` test; the planted traps never credited | `slow` for the full replicate count; a 2-replicate deterministic smoke variant always runs |
| `tests/test_candidate_runner.py` | phase order (a spy shows no value computed before phase 4 ends); each phase-1 and phase-2 stop, including a changed `decide` source, a changed constant, a changed `PIPELINE.md` and a null pin; refusal to overwrite; determinism (two runs on a synthetic corpus byte-identical); `results.json` schema, size, `allow_nan`, denylist and banned-key walk, no identifier; no key at any depth of the config or of a `results.json` built by the runner contains `statsbomb`, `pappalardo` or `wyscout` in any letter case; config read from the frozen file and only `selfcheck_replicates` overridden; every threshold in code traced to a config key (source scan of `shot_model_evaluation.py`, `candidate_gauntlet.py` and the runner for the literals 0.85, 0.70, 0.60, 0.82 finds none outside docstrings); a synthetic tree built from a runner `results.json` with the five records of section 11.1 passes every checker of `tests/test_verdict_registry.py` | — |
| `tests/test_candidate_pins.py` | on the real corpus, **structure only**: the `expected_*` pins, period filter, body-part coverage, clause overlap, shot-family pins, fingerprints; skips per league through `league_available` and when the league's sidecar manifest is absent | `slow`; skips without data |

No test computes a candidate statistic or a model fit on real rows.

## 9. Pre-outcome code-review checklist

Signed off by a reviewer who did not write the package, after the pipeline commit and before
the self-check stamp and the run.

1. `git status` shows no `results.json` under the E-09 folder and no cached real-data output of this pipeline anywhere.
2. No agent report lists a real-data execution beyond `--preflight` and `tests/test_candidate_pins.py`.
3. Fingerprints computed by the code equal `config.json` (four of four).
4. `lf_sha256_text(inspect.getsource(decide))` equals `frozen_rule_decide_source_sha256` and the constants equal `frozen_rule_constants`; `decide` is imported, not copied; no threshold literal in WP-C, D, E code.
5. `candidate_gauntlet.py`, `shot_model_evaluation.py`, `candidate_synthetic.py`, `candidate_sb.py` are in the firewall tuple; nothing under `galactico/api`, `galactico/optimization`, `galactico/profiles`, `galactico/match_lab` imports them; `galactico/models/shots` imports nothing from `galactico/validation` or `experiments`.
6. `spec.SPECS` has five keys; `CONSTRUCTS` has five; the shipped fingerprints are unchanged; the full suite is green without the corpus.
7. The model sees only `distance_m`, `angle_rad`, `head_or_body`: `design_matrix` reads no other column; the strings `opportunity`, `success`, `blocked`, `zone` do not occur in `galactico/models/shots/`.
8. Leave-one-league-out leakage test present and passing; the reference rate is the training rate.
9. No goals-minus-model quantity anywhere (`grep` for a subtraction of a value sum from a goal count in WP files).
10. The share floor, match-set floor, minutes floor and goalkeeper exclusion are applied before any value is computed; gate counts precede statistics (spy test).
11. Every departure of preregistration 6.1 has its named test and its direction; lenient ones are listed in `departures_active`.
12. Self-check passes from a clean checkout, and `--preflight` on the real corpus prints all pins matching and the count gates (planning values: eligible 319 / 306 / 306 / 270 / 306 on nominal minutes, which capped minutes can only lower; share sets about 80 / 84 / 88 / 66 / 80).
13. `results.json` writer: UTF-8, LF, `allow_nan=False`, sorted keys, size check, denylist and banned-key walk, no identifiers, the registry contract at the top level.
14. Phase 1 refuses a wrong commit, a dirty protocol, a changed `PIPELINE.md`, a changed `decide`, an existing output.
15. Protocol, config, this file and the code agree on every name in section 7.1; preregistration 9.1 has eight rows and the code has eight branches.
16. Ruff clean; `from __future__ import annotations`; frozen dataclasses; `__all__`; docstrings state claim and non-claim.

## 10. External leg (WP-F, conditional, LOCAL)

`galactico/validation/candidate_sb.py`; run through
`experiments/run_candidate_gauntlet.py --external --protocol-commit <sha>`; only after
`results.json` is committed and only for candidates of `sb_leg_candidates` at
`ESTABLISHED_*`. LOCAL_LICENSED end to end (`sb_leg_tier`): nothing under `galactico/api`,
`galactico/optimization`, `galactico/profiles`, `galactico/match_lab`, `galactico/models` or
`galactico/features` imports it.

```python
def sb_frames(folder: str, config: Mapping) -> LeagueFrames               # positions, minutes, periods, shots
def sb_shot_detail(folder: str, game_ids: Collection[int], config: Mapping) -> pd.DataFrame
    # event_id (str), shot_type, body_part, read from sb_reader.iter_events; keys reached through variables
def sb_verdict(candidate: str, evaluations: Sequence[LeagueEvaluation],
               refit_token: str | None, config: Mapping) -> str
def sb_level_shift(public: Mapping[str, Sequence[float]], local: Mapping[str, Sequence[float]],
                   config: Mapping) -> float | None
def run_external(results: Mapping, config: Mapping) -> dict
```

| Rule | Detail |
|---|---|
| inputs | `sb_root` only; no path under `sb_forbidden_roots` is opened. Before anything is read, `sb_reader.folder_manifest` of each of `sb_folders` equals `sb_folder_digests` (the three null digests are counted by the root before registration) |
| readers | `galactico.validation.sb_reader` (E-11, registered) imported unchanged and pinned in `source_hashes`: `read_matches`, `read_events(scale=sb_location_scale)`, `read_team_sheets` (minutes by `sb_minutes_rule`). Body part and the position names of spells are read by `candidate_sb.py` itself from the raw lists `sb_reader.iter_events` and the lineup files yield; `sb_reader` is not extended, since its hash is in E-11's committed acceptance stamp and an edit before E-11's run would invalidate it |
| vocabulary | a shot type outside `sb_known_shot_types`, a body part outside `sb_head_or_body_parts` + `sb_foot_parts`, or a position name outside `sb_position_groups` stops the leg before any statistic |
| frames | `type == "shot"` only for shots of `sb_open_play_shot_types`, other shots dropped; `head_or_body` for `sb_head_or_body_parts`; periods mapped by `sb_period_labels`; positions by `sb_position_rule`; goalkeepers excluded; `event_id` kept as the provider's string and never cast to an integer (`frame_digest` hashes it as a string on this leg) |
| battery | `sb_battery_rule` |
| instrument | the specification selected on the public run, refitted leave-one-league-out over the four folders, with `sb_gate_s_count`, the R and L gates in `sb_gate_leagues_required` of 4, the pooled gates at the public thresholds, and no reselection |
| gauntlet | the same functions, same rule, `minimum_evaluable_leagues = sb_minimum_evaluable_leagues` |
| token | preregistration section 11, rows in order; `sb_verdict_vocabulary`; the sentence `sb_statements[token]` |
| level shift | `sb_level_shift_rule`; reported only |
| output | `sb_output_root` (gitignored), file `external_results.local.json`. **Never committed.** The research note `sb_report` carries aggregate findings in prose and tables with the StatsBomb logo and attribution; no coefficient table |
| registry | none: the leg writes no `VerdictRecord` and changes no registry (DISSENT 7) |

`opp_half_defensive_actions` is not in this leg; its cross-provider status is E-11's token for
the same subject id.

`tests/test_candidate_sb.py` (synthetic only, invented names and ids): the box edges on the
provider's lattice (x = 101.9/102.0, y = 17.9/18.0/62.0/62.1, divided by 120 and 80, against
`penalty_area_sb`); the position map and its tie rule; the period map; an unknown shot type,
body part or position name stops the leg; every token row reached, row 1 before row 2; a
string `event_id` survives hashing; the module passes `check_licensing.check`; no product
package imports it; `sb_reader` is byte-identical to `HEAD`.

## 11. Registry consequences

### 11.1 At registration, and after the run

**At registration** (root, the registration commit; section 13): five PUBLIC records in
`galactico/domain/verdicts.py`, token `PENDING`: `experiment_id = registry_experiment_id`,
`tier = Tier.PUBLIC`, `directory = committed_experiment_dir`, `not_run_statement` from
`registry_common`; candidate records (`registry_candidate_subjects`) with `scope`,
`claim_token`, `non_claim` from `registry_candidate`, `vocabulary = verdict_vocabulary.candidate`,
`outcomes` from `registry_outcomes.candidate` (status, limits, statement, registry_move); the
instrument record (`registry_instrument_subjects`) likewise from `registry_instrument` and the
`instrument` entries; `protocol_hash`, `config_hash` = `lf_sha256` of the registered files. In
the same commit `product_admissible` gains the promotion-set condition (protocol section 10).

**After the run** (root, the results commit):

| Token | Edit |
|---|---|
| any | each record takes `token` from `results.json` `verdicts`, `protocol_commit` and `results_hash`; remove `shot_profile` and `defensive_action_profile` from `UNTESTED` in `galactico/profiles/build.py` (line 111; one tuple, read by `galactico/api/player_lab.py` and `scripts/generate_docs.py`); regenerate the README and METRICS blocks; add the E-09 row state to `experiments/preregistered/README.md` |
| `INCONCLUSIVE` | add the candidate id to `UNTESTED` (`untested_edit`; a declared hand edit tied to the token by a test, not a `registry_move`) |
| `NOT_ESTABLISHED_REDUNDANT`, `_CONFOUNDED`, `_UNRELIABLE` | `REJECTED[id] = (headline, detail)` from `player_lab_text[token]`, the headline filled by `baseline_fill_rule` through `baseline_prose`, or through `nuisance_prose`; add `test_<id>_stays_rejected` asserting absence from `CONSTRUCTS` and `spec.SPECS` |
| `NOT_ESTABLISHED_INSTRUMENT`, `_MIXED` | `RESEARCH_ONLY[id] = (headline, detail)` from `player_lab_text[token]` |
| `ESTABLISHED_*` | no registry move (rule V6, ARCH D1); the candidate is not in `REJECTED`, `RESEARCH_ONLY` or `UNTESTED`, and is counted as tested and not shipped; `product_admissible` stays false through the empty promotion set |
| instrument, any token | `MODEL-CARD.md` rendered; `docs/LIVE-DATA-GAP-MATRIX.md` corrected from `DERIVABLE` to `MODELLED` for xG on the free corpus |

Counts after any outcome: 13 proposed; tested = 13 minus the candidates left in `UNTESTED`
minus `carrying_value`. These edits change served Player Lab output (`/api/constructs`: the
three registry lists and the hero counts) and its tests (`tests/test_registry_contract.py`,
`tests/test_player_lab.py`); R13 and ADR-0011 pin that output, ROOT 2.2 authorises the
placeholder replacement, and the root records the override in an ADR note in the results
commit. The headlines and details hold no digit and pass the copy guard
(`tests/test_registry_contract.py`).

### 11.2 A later promotion (`CONSTRUCTS` plus `SPECS`) — every hardcoded list

Not in this release (ARCH D1). Listed so that a later promotion is one deliberate release with
its own ADR, gated on the PUBLIC E-09 token only:

| # | Where | Change |
|---|---|---|
| 1 | `galactico/domain/constructs.py` | `_register(ConstructDefinition(id, claim, family, estimators=..., reference_estimator=..., display_name=<config display_name>, known_confounds=..., invalid_contexts=(... "goalkeeper" ..., the context limits of `results.json`, "cross-league comparison" ...), external_replication=<a second-provider label or UNTESTED>))`. A label beside the construct, never its gate (ADR-0018) |
| 2 | `galactico/features/spec.py::SPECS` | generated from the `CandidateSpec` (ROOT 4: one object), with a cross-reference to its fingerprint. `shot_volume` is expressible today (`Measure.COUNT`, `ActionFilter({"shot"})`, `PER_90`); the other three are **not**: they need a subtype filter, an OR of clauses, a zone on `start_x`, and a model-weighted measure. New `ActionFilter` fields must enter `fingerprint` only when non-default or all five shipped fingerprints change |
| 3 | the three `Measure` switch sites | `features/spec.py` (`evaluate`), `profiles/uncertainty.py` (lines 104 to 110), `match_lab/model.py` (lines 184 to 186) |
| 4 | `galactico/features/estimators.py` | `ESTIMATOR_DENOMINATORS` labels every per-action spec "completed passes" (wrong for `box_shot_share`, whose denominator is shots); `CHANNEL_GEOMETRY` / `describe_style` assume a 0.5 reference for any style share |
| 5 | `galactico/match_lab/model.py` | the hardcoded five-label dict (`labels`, line 153); a sixth key raises `KeyError` |
| 6 | `tests/test_player_lab.py`, `tests/test_registry_contract.py` | exact shipped set |
| 7 | `galactico/profiles/build.py` | `REJECTED` / `RESEARCH_ONLY` / `UNTESTED`; `RELIABILITY_CURVE` if a floor above 900 is wanted; `_render_state` has no band path, so an `ESTABLISHED_BAND` construct renders as insufficient signal today |
| 8 | `scripts/build_profiles.py`, the Player Lab bundle | rebuild; until then `/api/*` returns 503 (stale `semantic_versions`) |
| 9 | `galactico/optimization/historical.py` | `feature_fingerprints` is built from `SPECS` (line 247): every XI snapshot's provenance changes although the frozen file is not edited |
| 10 | `galactico/profiles/uncertainty.py` | every `SPECS` key is bootstrapped for every player |
| 11 | `scripts/generate_docs.py`, README.md, METRICS.md | regenerate `constructs`, `claims`, `rejected`, `counts`, `fingerprints` |
| 12 | `galactico/providers/statsbomb.py::MAPPING_AUDIT` | correct the existing "shot" row (it maps eventId 10 plus free-kick shots); add the defensive row with E-11's mapping |
| 13 | `galactico/domain/metrics.py` | the legacy `REGISTRY` seeds `defensive_action_profile`; `tests/test_domain.py` asserts it. Leave or retire deliberately |
| 14 | `galactico/domain/metrics.py::Family` | a per-90 count has no member other than the one named with a word this build does not put on an unvalidated label; see DISSENT 3 |
| 15 | `galactico/domain/verdicts.py` | the promotion set gains the promoted id |
| 16 | `galactico/api/decision_lab.py` | **not changed.** The shipped requirement dict stays three keys |

### 11.3 Requirement dimensions

None in this release. No E-09 construct becomes an XI, Squad or Transfer requirement
dimension, a planning-page number or a value beside a player (ARCH D1). A later promotion that
proposes one decides it in its own ADR on the PUBLIC token alone; `box_shot_share` never
becomes one; `shot_location_value` stays UNAVAILABLE in every dated snapshot until an
instrument fitted strictly before the decision date exists (R9) and passes its
`followup_as_of_minimum_training_shots` gate, and under `ACCEPTED_WITHIN_LEAGUE` it would be
same-league only. A requirement sum of shot rates is not team shots: who shoots depends on
who else plays.

## 12. Model card — frozen template

`render_model_card(results)` emits exactly these sections; every number is read from
`results.json`, none is typed. `{...}` marks a field.

1. **Model details.** `shot_location_v1`; specification `{selection.specification}`; unpenalised logistic regression, IRLS, NumPy `{packages.numpy}`; formula of preregistration 4.1; pitch convention from `{config.pitch_length_m}` x `{config.pitch_width_m}` m, goal `{config.goal_width_m}` m; coefficients and standard errors for each of the five leave-one-league-out fits (table); protocol commit `{...}`; training-frame hashes.
2. **Intended use.** Valuing the origin of open-play shots in aggregate over a player-season, within one league, for men's top-division club football of 2017/18, as input to a candidate that passes its own lifecycle.
3. **Out of scope, as prohibitions.** A verdict on a single shot. Finishing skill. Goalkeeper evaluation. Comparison with any provider's xG as if on one scale. Any season, tier, sex or provider not evaluated. Any dated decision, until a strictly-prior fit exists.
4. **What enters and what does not.** In: shot origin, provider head-or-body class. Not in: defender and goalkeeper positions, pressure, shot type, ball height, assist type, shooter, team, league, game state. Excluded as outcome-informed, with audit counts read from `{structure}`: opportunity tag, accuracy tags, blocked tag, goal-mouth zone tags.
5. **Training data.** Pappalardo et al. 2019, CC BY 4.0; provider `Shot` events, periods `{config.periods}`, origin in the opponent half and not at a location sentinel; exclusions with counts `{structure}`; label = goal flag on the shot row; base rate by league `{...}`.
6. **Evaluation.** Leave one league out, five folds; match-level resampling, `{config.bootstrap_replicates}` replicates, coefficients fixed.
7. **Metrics**, per held-out league and pooled, for `M0`, `MD`, `M1`, `MFLEX`: Brier, log loss, both skills against the training rate, observed over expected, calibration slope and intercept, ECE and MCE with the simulated null percentiles, AUROC (for comparability only). Table from `{instrument.leagues}`, `{instrument.pooled}`.
8. **By factor.** Observed over expected for footed, head-or-body, three distance bands (gated); counter-attack flag (descriptive). Calibration bins per league.
9. **Uncertainty not in any number here.** (a) coefficient uncertainty: omitted from intervals; (b) omitted information: published Brier gaps put the per-shot disagreement with a richer model at 0.05 to 0.08 RMS, the same order as the mean shot value; its between-player part cannot be estimated from this corpus; (c) location error: integer-percent coordinates, unpublished operator accuracy; (d) outcome variance is not uncertainty about the model sum.
10. **Evidence class.** PREDICTIVE. Every construct built on it inherits it.
11. **Verdict and scope.** `{instrument.token}`; failed gates `{...}`. Under `ACCEPTED_WITHIN_LEAGUE`: values carry no goal unit and are not compared across leagues.
12. **Caveats.** Metres are a convention on percent coordinates; the provider's pitch drawing is not metric; head-or-body is not header; one season; national-team matches not evaluated; in-sample valuation is forbidden (a league is always valued by the fit that excluded it).
13. **Temporal validity.** Full-season out-of-league fits are measurement instruments for research only.
14. **Change policy.** Formula and thresholds frozen at the protocol commit. A refit is a new model id with a new card; the specification selected by preregistration 4.3 is named in the id (`shot_location_v1/M1` or `/MFLEX`).

## 13. Order of operations and shared-file requests to the root

One order, the house order (north-star README, E-11 PIPELINE section 13): independent audit
to READY, registration, the pipeline, the self-check stamp, the run.

**Before registration** (nothing below is an outcome):

| Step | Detail |
|---|---|
| Audit | an independent audit of this revision that walks every branch of 4.5, 9.1 and 11 |
| Structure counts | the root runs a committed structure-only script over the five leagues and writes `expected_behind_halfway_shot_rows`, `expected_sentinel_start_shot_rows` and `expected_in_domain_shot_rows` (`counted_by_root_before_registration`); the three `sb_folder_digests` that are null are computed with `sb_reader.folder_manifest` on the local folders |
| Verified values | `verified_by_root_before_registration`: `pipeline_spec_sha256` is `lf_sha256` of this file as it stands (an edit before registration means recomputing it); the `decide` source hash and constants; the two sidecar versions against `galactico.ingestion.sidecar`; `e11_config_sha256` against the registered E-11 config |
| Root ruling | ARCH D1 against `product_admissible` (protocol section 10): the promotion-set change below, or a ruling that replaces it. E-09 is not registered without one |

**The registration commit** changes served output, and says so:

| File | Change |
|---|---|
| `experiments/preregistered/E-09-player-candidates/` | the three registered files (section 0); `experiments/preregistered/README.md` row `E-09 player candidates`, `preregistered, not run` |
| `galactico/domain/verdicts.py` | the five `PENDING` records of section 11.1; `product_admissible(c)` returns `verdict_for("E-09", c).may_gate and c in PROMOTED`, `PROMOTED` an empty frozenset (`promotion_set_in_this_release`); the docstring's paragraph naming E-09 a draft and saying `product_admissible` is false while E-09 is not registered |
| `tests/test_verdict_registry.py` | the shipped-registry test (it lists E-11's sixteen records); the `product_admissible` test gains the promotion set; a test that `product_admissible` is false for every E-09 subject under every token of the config |
| `tests/test_protocol_drafts.py` (or a sibling) | ties the E-09 files: `lf_sha256` of `PIPELINE.md` equals `pipeline_spec_sha256`; every record built from the config under `PENDING` and under every token constructs and its `as_payload` passes `runtime.finalize`; every `player_lab_text`, `baseline_prose`, `nuisance_prose`, display name and sentence passes `labels.scan_labels` and holds no digit where `tests/test_registry_contract.py` requires none; no key of the config names a provider |
| `tests/test_preregistration_order.py` | nothing: `PROTOCOL` already holds `PIPELINE.md` |
| `tests/test_licensing.py` | remove the draft `preregistration.md` and `PIPELINE.md` from their lists (they become one-line pointers) and add the registered pair to `NO_FIGURE_FORMED_FROM_STATSBOMB`; the registered `preregistration.md` draws the logo by the registration-time path |
| `galactico/api/planning.py` | the `shots` entry of `NOT_MEASURED_EXTRA` says no registered protocol tests a shot construct, which is false once E-09 is registered; the root's wording |
| prose that calls E-09 an unreviewed draft or a draft with no review | `docs/research/north-star/README.md`, `KNOWN_LIMITATIONS.md` ("Registered or drafted, not run", the sidecar entry), ROOT-DECISIONS 2.6's registry sentence, ADR-0018's registry paragraph, ADR-0028's "Confidence" sentence |
| `docs/assets/statsbomb/statsbomb-logo.png` | the existing file, unchanged |

**After registration, before the run:**

| Step | Detail |
|---|---|
| The commit that adds the pipeline | the source files and tests of section 0. In that commit, and not before, `tests/test_research_firewall.py` gains `galactico.validation.shot_model_evaluation`, `candidate_gauntlet`, `candidate_synthetic` and `candidate_sb` in `RESEARCH_PIPELINES` (`test_the_lists_name_modules_that_exist` requires each listed file to exist) |
| Review and stamp | the checklist of section 9; then the self-check run on the frozen config, its block committed beside the protocol as `selfcheck.json` in a commit of its own after the pipeline and before the results. A failed stamp stops E-09 before any outcome (section 8.3) |

**After the run:** the results commit (`results.json`, `analysis.md`, `MODEL-CARD.md`, the
record tokens and hashes, the registry edits of 11.1 with the ADR note).

## DISSENT

1. **"CONSTRUCTS plus SPECS" cannot be the consequence of a positive verdict in this release.**
   Evidence: `ConstructSpec` cannot express three of the four candidates (11.2 row 2) and
   `features/spec.py` is frozen for implementers; a sixth `SPECS` key changes
   `feature_fingerprints` in every XI snapshot, stales the Player Lab bundle (503) and raises
   in Match Lab, all of which R13 pins. ARCH D1 has since ruled the same way: no promotion in
   this release. The full registration list (11.2) is kept for the later release.
2. **Candidates are `CandidateSpec`, not `ConstructSpec`.** The root layout says "candidate
   ConstructSpecs". Same evidence. `shot_volume` exists once, as a `CandidateSpec`, and is
   tested equal to the house `shots_per_90` column; a `ConstructSpec` form is generated from
   it at promotion, never written beside it (ROOT 4, ROOT 2.9 Z3).
3. **The registry's only family for a per-90 magnitude is named with a banned word.** `Family`
   has QUALITY, STYLE, PHYSICAL, TEAM; shipped per-90 constructs use the first. Candidates
   carry `family="volume"` here. Before any promotion the root should add a neutral member or
   accept the enum name as internal.
4. **The frozen `decide()` is reused unchanged, but not with Stage 1B's inputs.** Its battery
   contains shots per 90 (the candidate itself); `decide(0.9, 0.0, float("nan"), False)`
   returns `SHIP`; the house R-squared is joint with team although the rule's docstring
   thresholds nuisance variance; the baseline and nuisance statistics here are the larger of
   two centrings, and the reliability bound is the half-r bound. The rule body and thresholds
   are untouched and pinned by source hash; every input departure is tabled with its
   direction in preregistration 6.1.
5. **Two-tier instrument acceptance.** The root asked for frozen acceptance thresholds; this
   design freezes them and adds a scope tier (`ACCEPTED_WITHIN_LEAGUE`). A single tier would
   most likely reject the instrument on Italy's level (planning figure 0.897), a property no
   within-league candidate uses. If the council prefers one tier, delete the L/R distinction
   and treat every gate as R; the expected result is then `NOT_ESTABLISHED` for the
   instrument and `NOT_ESTABLISHED_INSTRUMENT` for `shot_location_value`.
6. **`shot_volume` counts open-play shots, not all non-penalty shots (ROOT 2.2).** Evidence: the
   registered E-11 defines `shot_volume` as open-play shots and `non_penalty_shot_volume`
   separately, and its token applies to an E-09 candidate only if E-09 imports its definition
   unchanged; the house `shots_per_90` baseline counts the neutral `shot` type only, so the
   identity of 5.1 holds; a direct free kick's origin is set by where the foul was given, not
   chosen by the shooter, and its conversion follows another process, which the location-only
   model would value as an open-play shot from that spot. The display name says "open-play"
   and "no direct free kicks". If the root holds to ROOT 2.2, `free_kick_shot` set pieces join
   both shot candidates, the identity with `shots_per_90` is dropped, the subject is renamed
   `non_penalty_shot_volume` to match E-11, and the fingerprints are recomputed.
7. **No registry record for the external leg.** A LOCAL `VerdictRecord` in E-09's directory
   would make `tests/test_verdict_registry.py::local_estimate_failures` read E-09's PUBLIC
   `results.json`, whose aggregate floats it refuses, and would require its `analysis.md` to
   carry the StatsBomb logo. The leg's token is therefore a label in its credited note only,
   and moves nothing. If the root wants it in the registry, it needs a directory of its own
   with its own protocol files, or a registry convention for a LOCAL leg of a PUBLIC
   experiment; the E-10 revision raised the same question.

## OPEN QUESTIONS

1. ARCH D1 against `product_admissible`: is the promotion-set change of section 13 the root's
   chosen form, or does the root rule another (for example, that `product_admissible` may turn
   true while promotion stays separate)? E-09 waits for the ruling.
2. Thresholds R1 (0.08 pooled, 0.03 per-league lower bound) differ from the reconnaissance
   proposal (0.08 point and 0.05 lower bound in every league). By derived sampling error
   (about 0.012 per league) the proposal fails a model whose true skill is 0.10 in about one
   run in five; the council should confirm before the commit.
3. A per-shot mean of the instrument was left out in favour of `box_shot_share`. If the
   council wants it, it is a fifth candidate and needs its own protocol.
4. Should Euro 2016 and World Cup 2018 be an external transport test of the instrument? Not
   in this protocol.
5. Whether E-10 uses `shot_location_v1` for conceded shot value; if so its protocol must cite
   the instrument token.
6. ROOT 2.2 against DISSENT 6: open-play shots, as E-11 registered, or every non-penalty shot?
