# E-09 pipeline specification

Companion to `preregistration.md` and `config.json` (same folder). The protocol
says what is decided; this file says what to build. Where the two disagree the
protocol wins and this file is the defect.

Every number an implementer needs is in `config.json`. Code reads thresholds from
the loaded config; a numeric literal for a threshold in code is a review failure
(section 9).

---

## 0. Work packages

Five packages, buildable in parallel against the interfaces below. Each owns only
the files listed. All are developed and tested on **synthetic data only**.

| WP | Owns (all new) | Depends on |
|---|---|---|
| A | `galactico/features/candidates.py`, `tests/test_candidates.py` | `features/spec.py` (`Scaling`, `ConstructSpec`), `features/axes.py` (`AxisSpec`), `domain/provenance.py` (`EvidenceClass`) |
| B | `galactico/models/shots/{__init__,geometry,logistic,model}.py`, `tests/test_shot_model.py` | numpy, pandas |
| C | `galactico/validation/shot_model_evaluation.py`, `tests/test_shot_model_evaluation.py` | B |
| D | `galactico/validation/candidate_gauntlet.py`, `tests/test_candidate_gauntlet.py` | A, C (types only), `reliability/`, `validation/{lifecycle,replication}.py`, `features/axes.py::compute_baselines` |
| E | `galactico/validation/candidate_synthetic.py`, `experiments/run_candidate_gauntlet.py`, `tests/test_candidate_planted.py`, `tests/test_candidate_runner.py`, `tests/test_candidate_pins.py` | A to D |
| F (conditional, lowest priority) | `galactico/validation/candidate_external.py`, `tests/test_candidate_external.py` | A to D; LOCAL tier |

Root owns: the protocol commit, the real run, `results.json`, `analysis.md`,
`MODEL-CARD.md`, `experiments/preregistered/README.md`, every registry edit of
section 11.

SHARED-FILE REQUESTS (root): append `galactico.validation.shot_model_evaluation`,
`galactico.validation.candidate_gauntlet`, `galactico.validation.candidate_synthetic`,
`galactico.validation.candidate_external` to the research-pipeline tuple of
`tests/test_research_firewall.py`; add the E-09 row to
`experiments/preregistered/README.md`.

## 1. ASSUMED INTERFACES

| # | Provider | Assumed | E-09 use | If absent |
|---|---|---|---|---|
| I1 | `galactico/ingestion/sidecar.py` | `read_sidecar(competition: str, columns: Sequence[str] \| None = None) -> pd.DataFrame`; column `event_id` int64, unique, one row per neutral action row that carries any restored tag; column `body_part` in `{"left_foot", "right_foot", "head_or_body"}` or null; file outside `competition=*/` | `body_part` on every `type == "shot"` row | preflight stops; E-09 contains no tag parsing of its own |
| I2 | `galactico/validation/digests.py` (H1 D3) | `lf_sha256(path: Path) -> str`, `lf_sha256_text(text: str) -> str` | every protocol, config and source hash | the runner defines the identical two-line function privately and says so in `provenance.source_hash_policy` |
| I3 | `galactico/domain/verdicts.py` | a frozen record per (experiment, subject) with at least `experiment`, `subject`, `verdict`, `closure`, `scope`, `protocol_hash`, `results_hash` | root writes five records after the run: `shot_location_v1` and the four candidates | consequences of section 11 are applied by hand |
| I4 | `galactico/domain/thesis.py` (H1 A2) | a pure walker returning the paths of banned keys in a JSON-like payload | `tests/test_candidate_runner.py` checks `results.json` keys | the test carries a local walk over the same banned set |
| I5 | `tests/conftest.py` | a corpus fixture that skips cleanly without data | `tests/test_candidate_pins.py` only | inline `pytest.skip` |
| I6 | E-10, E-11, E-12, Transfer and Squad designs | they read candidates only through `galactico.features.candidates` (`CANDIDATES`, `evaluate_candidate`) and the instrument only through `galactico.models.shots`; they gate any use on the I3 verdict | none inside E-09 | — |
| I7 | H2 | no E-09 code relies on the repaired `describe()`, `_spearman`, or `AxisReliability.lower_bound` | — | E-09 never calls `lower_bound`, `grade`, `ConfoundVerdict.passed` or `ActionFilter.describe` |

E-09 computes no team-level quantity. If E-10 wants a conceded location value it
depends on the E-09 instrument verdict and must say so.

## 2. Reuse

| Reused unchanged | From | For |
|---|---|---|
| `decide(reliability_low, confound_r2, baseline_r, kind_is_nuisance)` | `experiments/run_replication.py` (LF sha256 pinned in config; injected, never copied) | league status |
| `_safe_abs_corr` | same module | battery correlations, after the degenerate guard |
| `split_half_reliability(first, second, correct=...)`, `spearman_brown`, `AxisReliability(...).interval` | `galactico/reliability/core.py` | r_half, r_sb, house interval |
| `discriminant_validity`, `residualise` | `galactico/reliability/confound.py` | nuisance R-squared; reported joint audit |
| `compute_baselines(actions, minutes)` | `galactico/features/axes.py` | eight house battery columns and `minutes` |
| `Status`, `LeagueResult`, `classify_replication` | `galactico/validation/{lifecycle,replication}.py` | status enum; the house replication label, reported only |
| `Scaling`, `ConstructSpec`, `Measure`, `ActionFilter`, `evaluate` | `galactico/features/spec.py` | scaling enum; the plain-spec parity form of `shot_volume` |
| `AxisSpec` | `galactico/features/axes.py` | the claim record of each candidate |
| `EvidenceClass` | `galactico/domain/provenance.py` | evidence class on each spec |
| `assert_may_host` | `galactico/providers/base.py` | licence posture check in the runner |

Not reused, deliberately: `fit_league_xt` / `fit_xt` (no candidate uses xT);
`run_league` (v1 estimator, GK-inclusive, joint R-squared); `ConfoundVerdict.passed`
(a different rule); `AxisReliability.lower_bound` (falls back to the point estimate).

`experiments/` is a namespace package. The runner and the tests put the repository
root on `sys.path` (anchored to `Path(__file__)`), then
`from experiments.run_replication import decide, _safe_abs_corr`. Library modules
never import `experiments`: the rule is a parameter.

## 3. `galactico/features/candidates.py` (WP-A)

Module docstring states: candidates are definitions under test, held outside
`spec.SPECS` because a sixth key there breaks five shipped things; nothing here
is a validated construct; the dict is named `CANDIDATES`, never `SPECS`.

```python
class CandidateMeasure(Enum):
    COUNT = "count"
    SUM_MODEL_PROBABILITY = "sum of location-only conversion-model probability"

@dataclass(frozen=True)
class Zone:
    name: str
    min_start_x_exclusive: float | None = None
    min_start_x_inclusive: float | None = None
    min_start_y_inclusive: float | None = None
    max_start_y_inclusive: float | None = None
    phrase: str = ""                       # "starting in the opponent half"
    def mask(self, actions: pd.DataFrame) -> pd.Series      # False on sentinel starts
    @property
    def fingerprint(self) -> str           # "opponent_half[x>0.5]"

ZONES: dict[str, Zone]                     # exactly the two zones of config["zones"]
SENTINEL_STARTS: tuple[tuple[float, float], ...] = ((0.0, 0.0), (1.0, 1.0))

@dataclass(frozen=True)
class Clause:
    types: frozenset[str] = frozenset()
    subtypes: frozenset[str] = frozenset()
    flags: frozenset[str] = frozenset()    # boolean columns, all must be true
    zone: str | None = None
    def mask(self, actions: pd.DataFrame) -> pd.Series
    def describe(self) -> str
    @property
    def fingerprint(self) -> str

@dataclass(frozen=True)
class CandidateSpec:
    candidate_id: str
    family: str                            # "volume" | "style"; never the word the enum uses
    measure: CandidateMeasure
    numerator: tuple[Clause, ...]          # union of clauses, each row counted once
    scaling: Scaling
    denominator: tuple[Clause, ...] = ()
    instrument: str | None = None
    evidence_class: EvidenceClass = EvidenceClass.DERIVED
    def describe(self) -> str
    @property
    def denominator_label(self) -> str
    @property
    def fingerprint(self) -> str

CANDIDATES: dict[str, CandidateSpec]       # 4 keys, order as in config
CLAIMS: dict[str, AxisSpec]                # same 4 keys; text of preregistration section 5
SHOT_VOLUME_AS_CONSTRUCT_SPEC: ConstructSpec   # COUNT over ActionFilter({"shot"}), PER_90

def rows(clauses: tuple[Clause, ...], actions: pd.DataFrame) -> pd.DataFrame
def evaluate_candidate(spec: CandidateSpec, actions: pd.DataFrame, minutes: pd.Series, *,
                       shot_values: pd.Series | None = None) -> pd.Series
__all__ = [...]
```

| Element | Exact behaviour |
|---|---|
| `Clause.mask` | AND of: `type in types` if `types`; `subtype in subtypes` if `subtypes`; each flag column truthy after `fillna(False)`; `ZONES[zone].mask` if `zone`. An empty clause raises `ValueError` |
| `Zone.mask` | the declared comparisons on `start_x`, `start_y`, AND NOT (start equals a sentinel pair). `opponent_half` is `start_x > 0.50` strictly; `penalty_area` is `start_x >= 0.84` and `0.19 <= start_y <= 0.81` |
| `rows` | rows matching any clause; `actions[mask_1 \| mask_2 \| ...]`; each row once |
| `Clause.fingerprint` | `"\|".join([",".join(sorted(types)), ",".join(sorted(subtypes)), ",".join(sorted(flags)), ZONES[zone].fingerprint if zone else "-"])` |
| union fingerprint | `"+".join(sorted(clause fingerprints))`; `"-"` for an empty tuple |
| `CandidateSpec.fingerprint` | `sha256("\x1f".join([candidate_id, measure.value, numerator_fp, scaling.value, denominator_fp, instrument or "-"]).encode()).hexdigest()[:12]` |
| `__post_init__` | `PER_SELECTED_ACTION` without denominator raises; `PER_90` with one raises; `SUM_MODEL_PROBABILITY` without `instrument` raises; `COUNT` with one raises; empty numerator raises |
| `evaluate_candidate`, COUNT | `numerator = rows(...).groupby("player_id").size().reindex(minutes.index).fillna(0.0)` |
| `evaluate_candidate`, SUM | `shot_values` required (Series indexed by `event_id`); every numerator row's `event_id` must be present or `KeyError` naming the count missing; sum per `player_id`, reindexed, `fillna(0.0)` |
| scaling | `PER_90`: `numerator * 90.0 / minutes.replace(0, nan)`. `PER_SELECTED_ACTION`: `numerator / rows(denominator).groupby("player_id").size().reindex(index).replace(0, nan)`; no denominator rows gives NaN, never 0 |
| unit | output index is `minutes.index`; a `player_id` of 0 is never in it |

Pinned payloads (the fingerprints in `config.json` were computed from exactly
these; `<US>` is `\x1f`):

| id | payload | sha256[:12] | `describe()` |
|---|---|---|---|
| `shot_volume` | `shot_volume<US>count<US>shot\|\|\|-<US>per 90 minutes<US>-<US>-` | `1c6517c2be31` | `count over shots, per 90 minutes` |
| `shot_location_value` | `shot_location_value<US>sum of location-only conversion-model probability<US>shot\|\|\|opponent_half[x>0.5]<US>per 90 minutes<US>-<US>shot_location_v1` | `9998c7120f99` | `sum of location-only conversion-model probability over shots starting in the opponent half, per 90 minutes` |
| `box_shot_share` | `box_shot_share<US>count<US>shot\|\|\|penalty_area[x>=0.84;0.19<=y<=0.81]<US>per action in the denominator set<US>shot\|\|\|-<US>-` | `af2b2b118e73` | `count over shots starting in the penalty area, per shot` |
| `opp_half_defensive_actions` | `opp_half_defensive_actions<US>count<US>duel\|Ground defending duel\|\|opponent_half[x>0.5]+\|\|interception\|opponent_half[x>0.5]<US>per 90 minutes<US>-<US>-` | `72619cd8130b` | `count over ground defending duel records or interception-flagged events, starting in the opponent half, per 90 minutes` |

If an implementation yields another fingerprint the implementation is wrong.

`tests/test_candidates.py` (hand-computable, in the style of `tests/test_spec_contract.py`):
fingerprints and sentences equal `config.json`; zone edges at 0.50 / 0.51 and
0.83 / 0.84, 0.18 / 0.19, 0.81 / 0.82; sentinel starts excluded from zone clauses
and kept in zone-free clauses; a row matching both clauses of the union counted
once; a penalty and a direct free-kick shot (`type == "set_piece"`) never counted;
`player_id` 0 never credited; per-90 scales with minutes and the share does not;
a player with no shots has share NaN and volume 0.0; `shot_volume` equals
`spec.evaluate(SHOT_VOLUME_AS_CONSTRUCT_SPEC, ...)` and
`compute_baselines(...)["shots_per_90"]` on the same frame; a missing `event_id`
in `shot_values` raises; `CANDIDATES.keys()` is disjoint from `spec.SPECS`,
`CONSTRUCTS`, `REJECTED`, `RESEARCH_ONLY`; `spec.SPECS` has exactly its five
shipped keys; no clause can read `success` or `clearance` (`Clause` has no such
field, and a flag of either name raises); no key or family string is in the
banned set.

## 4. `galactico/models/shots/` (WP-B)

Product-side package: pure functions, no threshold, no verdict, no file access.
Package docstring: "A location-only shot conversion model. It is a model
(PREDICTIVE). It is not xG supplied by the provider; the provider supplies none.
It sees where a shot started and whether the provider classed it head-or-body. It
does not see defenders, the goalkeeper, pressure, shot type, the shooter or the
team. It says nothing about finishing."

```python
# geometry.py
PITCH_LENGTH_M = 105.0; PITCH_WIDTH_M = 68.0; GOAL_WIDTH_M = 7.32
def shot_geometry(start_x: np.ndarray, start_y: np.ndarray) -> tuple[np.ndarray, np.ndarray]
    # (distance_m, angle_rad) by the formulas of preregistration 4.1; atan2, no branch

# logistic.py
@dataclass(frozen=True)
class LogisticFit:
    coefficients: np.ndarray
    standard_errors: np.ndarray
    log_likelihood: float
    iterations: int
    converged: bool
def fit_logistic(design: np.ndarray, outcome: np.ndarray, *, offset: np.ndarray | None = None,
                 max_iterations: int, tolerance: float) -> LogisticFit
def predict_probability(coefficients: np.ndarray, design: np.ndarray, *,
                        offset: np.ndarray | None = None) -> np.ndarray

# model.py
@dataclass(frozen=True)
class ShotModelSpec:
    model_id: str                          # "M0" | "MD" | "M1" | "MFLEX"
    terms: tuple[str, ...]                 # exactly config["model_terms"][model_id]
SHOT_MODELS: dict[str, ShotModelSpec]
SHOT_COLUMNS = ("event_id", "game_id", "team_id", "player_id", "start_x", "start_y",
                "distance_m", "angle_rad", "head_or_body", "counter_attack", "goal")
def shot_frame(actions: pd.DataFrame, body_part: pd.Series, *,
               min_start_x_exclusive: float) -> pd.DataFrame      # SHOT_COLUMNS, sorted by event_id
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
                   tolerance: float) -> FittedShotModel
def predict(model: FittedShotModel, shots: pd.DataFrame) -> np.ndarray
```

| Element | Exact behaviour |
|---|---|
| `shot_frame` | rows with `type == "shot"` and `start_x > min_start_x_exclusive`; `head_or_body = (body_part.reindex(event_id) == "head_or_body")` as int; a shot with null body part raises `ValueError` with the count (coverage is a pinned 1.0); includes `player_id` 0 rows (location and label are valid); `goal` as int |
| terms | `intercept` 1; `distance_m`; `angle_rad`; `head_or_body`; `a*b` product; `hinge(v,k)` is `max(v - k, 0)` |
| `fit_logistic` | Newton / IRLS from zero coefficients on internally standardised non-constant columns, back-transformed; step halving while the log-likelihood falls (at most 30 halvings); stop when the largest absolute coefficient change on the standardised scale is below `tolerance`; `converged=False` at `max_iterations` or on a singular information matrix, never an exception; `standard_errors = sqrt(diag(inv(X'WX)))`; no penalty |
| `M0` | one intercept; `predict` returns `base_rate` for every row |
| `predict` | probabilities in the open unit interval, unclipped |

`tests/test_shot_model.py`: geometry at hand-computed points (penalty spot
(0.895, 0.5): d 11.025 m; goal-line centre: theta pi; goal-line outside the post:
theta 0; symmetry in `start_y` about 0.5); design matrices term by term; recovery
of planted coefficients within four standard errors at 40,000 synthetic shots;
log-likelihood gradient at the fit below 1e-6 in absolute value; `M0` equals the mean;
permutation of rows changes nothing; a separable toy sample returns
`converged=False`; offset fit recovers a known intercept; no symbol named after
the banned words; no `xg` identifier (`grep`-style source test).

## 5. `galactico/validation/shot_model_evaluation.py` (WP-C)

```python
def brier(p: np.ndarray, y: np.ndarray) -> float
def log_loss(p: np.ndarray, y: np.ndarray, *, clip: float) -> float
def skill(loss: float, reference_loss: float) -> float | None           # 1 - loss/reference; None if reference <= 0
def observed_over_expected(p: np.ndarray, y: np.ndarray) -> float | None
def calibration_slope(p: np.ndarray, y: np.ndarray, *, clip: float, max_iterations: int,
                      tolerance: float) -> float | None                 # logit(y) ~ a + b*logit(p)
def calibration_intercept(p, y, *, clip, max_iterations, tolerance) -> float | None   # offset logit(p)
def calibration_bins(p, y, event_id, *, n_bins: int) -> list[dict]      # keys: n, mean_probability, observed_rate
def calibration_error(bins: list[dict]) -> tuple[float, float]          # (ece, mce)
def auroc(p: np.ndarray, y: np.ndarray) -> float | None                 # average ranks for ties

@dataclass(frozen=True)
class LoloResult:
    predictions: Mapping[str, pd.DataFrame]   # league -> SHOT_COLUMNS + p_M0, p_MD, p_M1, p_MFLEX
    fits: Mapping[str, Mapping[str, FittedShotModel]]   # held-out league -> model_id -> fit without it
    sample_gate: Mapping[str, object]         # counts per fold, passed: bool, reasons
def leave_one_league_out(shots: Mapping[str, pd.DataFrame], config: Mapping) -> LoloResult
def select_instrument(lolo: LoloResult, config: Mapping) -> dict        # {"instrument", "pooled_gain", "fold_gains", "folds_meeting"}
def match_resample_weights(n_matches: int, *, replicates: int, seed: int, league_position: int) -> np.ndarray
def instrument_report(lolo: LoloResult, instrument: str, config: Mapping) -> dict   # section 7 "instrument" block
def instrument_verdict(report: dict, config: Mapping) -> tuple[str, tuple[str, ...]]   # verdict, failed gate ids
def shot_values(lolo: LoloResult, instrument: str) -> dict[str, pd.Series]   # league -> Series indexed by event_id
```

| Element | Exact behaviour |
|---|---|
| fold f | fit all four models on the concatenation of the other leagues' shot frames; predict league f; `p_M0` is the training goal rate |
| sample gate S | evaluated from counts before any fit; on failure return a `LoloResult` with empty `predictions` and `passed=False` |
| resampling | `np.random.default_rng([config["seed"], league_position]).multinomial(n, [1/n]*n, size=replicates)` over the league's sorted `game_id`s; statistics recomputed from per-match sums (`sum (p-y)^2`, `sum (p0-y)^2`, log-loss sums); pooled statistics resample each league independently and add the sums |
| intervals | percentiles `config["interval_quantiles"]` of the replicate statistic, `np.percentile` default interpolation |
| bins | stable sort by `(p, event_id)`; `np.array_split` into `ece_bins` |
| subgroups (R4) | pooled over the five held-out leagues: `head_or_body == 0`, `== 1`, `distance_m < 10`, `10 <= distance_m < 20`, `distance_m >= 20` |
| null calibration error | `ece_null_draws` draws of `y ~ Bernoulli(p)` per league with `default_rng([ece_null_seed, league_position])`; report the 50th, 95th, 99th percentile of ECE and MCE; reported, not a gate |
| verdict | preregistration 4.5, first failing class wins; `failed` lists every failed gate id |
| undefined statistic | any `None` in a gated statistic fails that gate and is listed |

`tests/test_shot_model_evaluation.py`: each metric against a hand-computed
six-row case; AUROC with ties; ECE of a two-bin toy; skill is `None` on a zero
reference; **leakage** (flipping every label of the held-out league leaves its
predictions byte-identical and changes the other four leagues' predictions);
training base rate, not test rate, is the reference; resample weights depend only
on seed and league position; every gate R1 to R5, L1 to L3 and S reachable in
both directions from a hand-built report dict; verdict mapping exhaustive over the
2^9 pass/fail combinations with exactly one token each; the selection rule at
both edges (0.0099 / 0.0100 pooled; 3 / 4 folds).

## 6. `galactico/validation/candidate_gauntlet.py` (WP-D)

```python
@dataclass(frozen=True)
class LeagueFrames:
    league: str
    actions: pd.DataFrame      # game_id, team_id, player_id, type, subtype, period, start_x, start_y,
                               # end_x, end_y, success, goal, interception, counter_attack, event_id
    lineups: pd.DataFrame      # game_id, team_id, player_id, minutes
    players: pd.DataFrame      # player_id, position
    body_part: pd.Series       # index event_id

@dataclass(frozen=True)
class GateCount:
    league: str; candidate: str
    eligible: int; audit_units: int | None; reliability_units: int
    position_groups: Mapping[str, int]; dropped_position_groups: tuple[str, ...]
    unattributed_share: float | None
    passed: bool; reasons: tuple[str, ...]

@dataclass(frozen=True)
class ReliabilityEstimate:
    n: int; r_half: float | None; r_sb: float | None
    house_low: float | None; house_high: float | None; half_low: float | None
    reliability_low: float | None

@dataclass(frozen=True)
class LeagueEvaluation:
    league: str; candidate: str; gate: GateCount
    status: str                       # "INCONCLUSIVE" | "SHIP" | "SHIP_WITH_BAND" | "REJECT"
    reject_reason: str | None         # "REDUNDANT" | "CONFOUNDED" | "UNRELIABLE"
    inconclusive_reason: str | None
    centred: ReliabilityEstimate | None           # gating
    raw_pooled: ReliabilityEstimate | None        # reported
    within_position: Mapping[str, ReliabilityEstimate | None]   # reported
    team_and_position_centred: ReliabilityEstimate | None       # reported
    baseline_correlations: Mapping[str, float | None]
    dropped_battery_columns: tuple[str, ...]
    closest_baseline: str | None; baseline_r: float | None
    nuisance_r2: float | None
    joint_r2: float | None; joint_r2_adjusted: float | None; joint_regressors: int | None
    joint_noise_floor: float | None; ordering_rho: float | None; top_k_kept: int | None
    house_joint_r2: float | None; house_joint_r2_exceeds_ceiling: bool | None
    mean: float | None; sd: float | None; zero_share: float | None
    half_minutes_share_p05_p95: tuple[float, float] | None
    rule_reasons: tuple[str, ...]

@dataclass(frozen=True)
class CandidateVerdict:
    candidate: str; verdict: str; closure: str | None; rule_row: int
    evaluable: int; surviving: int; ship: int; rejected: int
    statuses: Mapping[str, str]; reject_reasons: Mapping[str, str]
    house_replication_label: str | None

Rule = Callable[[float, float, float, bool], tuple[Status, tuple[str, ...]]]

def half_of_game(actions: pd.DataFrame) -> pd.Series                      # index game_id, values 0/1
def eligible_minutes(lineups: pd.DataFrame, players: pd.DataFrame, config: Mapping) -> pd.Series
def player_team(lineups: pd.DataFrame) -> pd.Series
def unattributed_duel_share(actions: pd.DataFrame, lineups: pd.DataFrame, index: pd.Index) -> pd.Series
def baseline_battery(frames: LeagueFrames, minutes: pd.Series, shot_volume: pd.Series) -> pd.DataFrame
def count_gates(spec: CandidateSpec, frames: LeagueFrames, config: Mapping) -> GateCount
def centre(values: pd.Series, groups: pd.Series) -> pd.Series
def reliability_estimate(first: pd.Series, second: pd.Series, *, groups: pd.Series | None,
                         config: Mapping, label: str) -> ReliabilityEstimate
def reject_reason(rule: Rule, reliability_low: float, nuisance_r2: float, baseline_r: float,
                  kind_is_nuisance: bool) -> str | None
def evaluate_league(spec: CandidateSpec, frames: LeagueFrames, gate: GateCount,
                    shot_values: pd.Series | None, rule: Rule, config: Mapping) -> LeagueEvaluation
def candidate_verdict(spec: CandidateSpec, evaluations: Sequence[LeagueEvaluation],
                      instrument_verdict: str, config: Mapping) -> CandidateVerdict
def run_gauntlet(frames: Mapping[str, LeagueFrames], shot_values: Mapping[str, pd.Series] | None,
                 instrument_verdict: str, rule: Rule, config: Mapping) -> dict
```

| Element | Exact behaviour |
|---|---|
| `half_of_game` | `games = sorted(actions["game_id"].unique())`; half = position in `games` modulo 2. Identical to `run_replication.py:110-116` |
| `eligible_minutes` | `lineups.groupby("player_id").minutes.sum()`; keep `>= minutes_floor`, position in `outfield_positions`, id != 0 |
| `player_team` | team with the most lineup minutes; ties to the smallest `team_id` |
| `baseline_battery` columns | from `compute_baselines(actions[player in index], minutes)`: `minutes, touches, touches_per_90, passes_per_90, pass_completion, mean_x, mean_y, mean_pass_length`; `shot_volume` = the candidate value (asserted equal to `shots_per_90` to 1e-12); `opp_half_on_ball_per_90` = rows of type pass, touch or shot in zone `opponent_half`, per 90; `defensive_actions_per_90` = candidate-4 clauses with the zone removed, per 90; `unattributed_duel_share`. All coerced to float64 (`pass_completion` is object dtype upstream) |
| `unattributed_duel_share` | for team t in match m, `u = (ground defending duel rows with player_id 0) / (ground defending duel rows)` (0.0 if none); per player the lineup-minutes-weighted mean of `u` over his rows of `lineups` |
| `count_gates` | structure only. A: eligible with a finite full-season value (share floor applied when `share_floor`); R: A with both half floors (and half share floors); position groups in R below `minimum_position_group` are dropped from R and listed; `unattributed_share` for candidate 4 = share of pitch-wide union rows with `player_id` 0 in the league; reasons from config gate names |
| half values | `evaluate_candidate(spec, actions of half h for players in R, half-h minutes, shot_values=...)` |
| `centre` | value minus the mean over the same group among the units passed in |
| `reliability_estimate` | `r_half, n = split_half_reliability(a, b, correct=False)`; `r_sb = spearman_brown(r_half)`; `house = AxisReliability(label, r_sb, n, minutes_floor, period).interval` (None stays None); `half_low = spearman_brown(tanh(atanh(r_half) - z / sqrt(n - 3)))`; `reliability_low = min(house_low, half_low)`; any non-finite gives `None` fields |
| baseline | drop battery columns with sd below `degenerate_sd` (recorded); `baseline_r = max _safe_abs_corr(value, column)` over A; ties to the earlier column in config order |
| nuisance | `discriminant_validity(value, columns, key=id, top_k=top_k).variance_explained_by_confounds` on `nuisance_columns`; `None` if there are none |
| joint audit (reported) | `discriminant_validity` on `[touches, team one-hot drop-first, position one-hot drop-first]`; adjusted `1 - (1 - R2)(n - 1)/(n - k - 1)`; floor `k/(n - 1)`; `house_joint_r2` on `[touches, team one-hot]` and its comparison with `nuisance_r2_ceiling`, for candidates with a nuisance column only |
| degenerate guard | value sd below `degenerate_sd`, or zero share above `maximum_zero_share`, or any non-finite rule input: status `INCONCLUSIVE`, reason named, rule not called |
| rule call | `rule(reliability_low, nuisance_r2 if not None else 0.0, baseline_r, bool(nuisance_columns))` |
| `reject_reason` | `REDUNDANT` if `rule(1.0, 0.0, baseline_r, False)` rejects; else `CONFOUNDED` if `rule(1.0, nuisance_r2, 0.0, kind_is_nuisance)` rejects; else `UNRELIABLE` if `rule(reliability_low, 0.0, 0.0, False)` rejects; else `None`. Thresholds therefore live only in the frozen rule |
| `candidate_verdict` | the seven rows of preregistration section 9, in order; `rule_row` records which fired; `house_replication_label = classify_replication(...)` over evaluable leagues, reported |
| order in `run_gauntlet` | all `count_gates` for all candidates and leagues first; a candidate with fewer than `minimum_evaluable_leagues` passing gets no statistic computed |

`tests/test_candidate_gauntlet.py`: truth table for `decide` written from the
protocol (edges 0.85 / 0.8501, 0.60 / 0.6001 with and without nuisance,
0.70 / 0.6999, 0.50 / 0.4999; NaN baseline documented as passing the raw rule and
caught by the guard); `reject_reason` for each of the three reasons and for none;
verdict rows 1 to 7 each reached, plus exhaustiveness over every multiset of five
league statuses with reasons (one verdict each, no exception); `half_of_game`
equals the house expression on a shuffled frame; centring removes a planted
position effect and leaves a planted player effect; `reliability_low <= house_low`
always and equals the half-r bound when that is smaller; centred r no greater than
raw r on data with a pure position effect; the nuisance-only R-squared is flagged
(`house_joint_r2_exceeds_ceiling`) on a planted team effect; a constant vector and
an all-NaN battery give `INCONCLUSIVE`, never `SHIP`; goalkeepers and `player_id`
0 absent from every set; gate counts computed before any value (a spy on
`evaluate_candidate` shows zero calls when gates fail); row-order invariance of
the whole league evaluation; every returned field `None` rather than NaN.

## 7. Runner, results, hashes

`experiments/run_candidate_gauntlet.py` (WP-E). Paths anchored to
`ROOT = Path(__file__).resolve().parents[1]`. Reads Parquet with a column list,
one league at a time for the gauntlet; the five shot frames are held together
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
| 1 | provenance | the LF sha256 of `frozen_rule_path` differs from config; any candidate fingerprint differs from config; `--protocol-commit` is not the commit that last changed `preregistration.md` and `config.json` (read-only `git log -1 --format=%H -- <path>`), or the working-tree LF hash differs from the LF hash of `git show <commit>:<path>`; the output file already exists (unless `--determinism-rerun` to another path) |
| 2 | structural pins | any `expected_*` of config differs; the period filter drops a row; a shot has no body part |
| 3 | self-check | section 8 rates not met |
| 4 | count gates | never stops; gates are recorded |
| 5 | instrument | — |
| 6 | candidates | — |
| 7 | write | the serialised artifact exceeds `results_maximum_bytes`, or contains a banned key, or `json.dumps(..., allow_nan=False)` raises |

Written as `Path.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8", newline="\n")`. Never stdout redirection.

### 7.1 `results.json` shape (aggregate only)

```
{
  "version": "player-candidates-v1",
  "provenance": {
    "experiment": "E-09", "protocol_commit": "...", "protocol_hash": "...", "config_hash": "...",
    "source_hash_policy": "sha256 of LF-normalised bytes",
    "source_hashes": {"<posix path>": "..."},
    "frozen_rule": {"path": "...", "lf_sha256": "...", "function": "decide"},
    "candidate_fingerprints": {"shot_volume": "1c6517c2be31", ...},
    "frame_hashes": {"<league>": {"actions": "...", "lineups": "...", "players": "...", "body_part": "..."}},
    "raw_manifest_sha256": "...", "packages": {"numpy": "...", "pandas": "...", "pyarrow": "..."},
    "data_license": "...", "reuse_disclosure": "...", "config": { ...verbatim... }
  },
  "selfcheck": {"passed": true, "replicates": 12,
                "worlds": {"EFFECT": {"<subject>": {"<verdict token>": count}}, "NULL": {...}, "NUISANCE": {...}},
                "instrument_scenarios": {"PLANTED": {"<verdict token>": count}, ...}},
  "structure": {"<league>": {"matches", "shot_rows", "in_domain_shot_rows", "out_of_domain_shot_rows",
                             "goal_rows_on_shots", "eligible_players", "eligible_by_position": {...},
                             "union_rows", "union_rows_unattributed"}},
  "instrument": {
    "sample_gate": {"passed", "reasons", "folds": {"<held-out league>": {"train_shots", "train_goals",
                    "heldout_shots", "heldout_goals", "training_rate"}}},
    "fits": {"<held-out league>": {"<model>": {"terms": [...], "coefficients": [...],
             "standard_errors": [...], "converged", "iterations", "log_likelihood"}}},
    "selection": {"instrument", "pooled_gain", "fold_gains": {...}, "folds_meeting"},
    "leagues": {"<held-out league>": {"<model>": {"brier", "log_loss", "brier_skill", "log_loss_skill",
                "observed_over_expected", "calibration_slope", "calibration_intercept", "ece", "mce",
                "auroc"}, "brier_skill_interval": [lo, hi], "calibration_bins": [{"n",
                "mean_probability", "observed_rate"} x10], "null_calibration_error": {...}}},
    "pooled": {"<model>": {...same metrics...}, "brier_skill_interval": [lo, hi],
               "log_loss_gain_over_comparator": x, "log_loss_gain_interval": [lo, hi],
               "subgroups": {"<name>": {"n", "goals", "observed_over_expected"}},
               "descriptive_subgroups": {"counter_attack": {...}}},
    "gates": {"S": {"passed", "detail"}, "R1": ..., "R5": ..., "L1": ..., "L3": ...},
    "verdict": "...", "failed_gates": [...]
  },
  "candidates": {
    "<candidate>": {
      "definition": "...", "fingerprint": "...", "evidence_class": "...",
      "leagues": {"<league>": { ...every LeagueEvaluation field, GateCount nested... }},
      "verdict": "...", "closure": null | "...", "rule_row": n,
      "evaluable": n, "surviving": n, "ship": n, "rejected": n,
      "house_replication_label": "..."
    }
  },
  "predictions": { ...preregistration section 12, verbatim, with "matched": bool per subject... },
  "product_effect": {"<subject>": "...the registry consequence token of section 11..."},
  "interpretation_limits": "..."
}
```

Rules: no player, team or match identifier anywhere (the only ids are league
names); no key named `id`, `player_id`, or any member of the banned set; a missing
value is `null`; counts are ints; under 512 KB (expected about 60 KB).

### 7.2 Hash discipline

| Hash | Of | How |
|---|---|---|
| `protocol_hash`, `config_hash` | the two committed files | `lf_sha256(path)` |
| `source_hashes` | `experiments/run_candidate_gauntlet.py`, `experiments/run_replication.py`, `galactico/features/{candidates,spec,axes}.py`, `galactico/models/shots/*.py`, `galactico/validation/{candidate_gauntlet,shot_model_evaluation,candidate_synthetic,lifecycle,replication,digests}.py`, `galactico/reliability/{core,confound}.py`, `galactico/ingestion/sidecar.py` | `lf_sha256`; keys `.as_posix()` relative to the root |
| `frame_hashes` | the frames actually used | `frame_digest`: select the listed columns in the listed order, cast `success` to nullable boolean and ids to int64, sort by the key (`event_id`; lineups by `game_id, player_id`; players by `player_id`), `reset_index(drop=True)`, `sha256(pd.util.hash_pandas_object(frame, index=False).values.tobytes())`. Parquet file bytes are **not** hashed: the footer embeds the pandas version |
| `raw_manifest_sha256`, `raw_file_sha256` | `data/public/pappalardo/MANIFEST.json` | `lf_sha256` of the manifest; plus the manifest's own SHA-256 entries for the five leagues' events and matches files and for `players.json`, echoed verbatim. Raw digests are the stable pin; the frame hashes say what the run actually read |
| `protocol_commit` | git | verified in phase 1; never a literal in source |
| results | `results.json` | root records `lf_sha256` of it in the I3 verdict records |

### 7.3 The commands

Preflight, any number of times, before or after the protocol commit (structure and
synthetic only; prints the gate counts and the self-check table; writes nothing in
the repository):

    .venv/Scripts/python.exe -B experiments/run_candidate_gauntlet.py --preflight

**The single command the root runs for the real execution, once:**

    .venv/Scripts/python.exe -B experiments/run_candidate_gauntlet.py --protocol-commit <sha> --out experiments/preregistered/E-09-player-candidates/results.json

Determinism re-run (must be byte-identical; exit code 1 otherwise):

    .venv/Scripts/python.exe -B experiments/run_candidate_gauntlet.py --protocol-commit <sha> --determinism-rerun --out <scratchpad>/E-09-rerun.json

Model card, generated from the committed results, never typed:

    .venv/Scripts/python.exe -B experiments/run_candidate_gauntlet.py --render-card experiments/preregistered/E-09-player-candidates/results.json

## 8. Synthetic suite and the planted checks

`galactico/validation/candidate_synthetic.py`. **Independent of what it checks**:
it imports numpy and pandas only, plus `LeagueFrames` as a container. It writes its
own geometry from the formulas in the protocol and builds neutral-schema rows
directly. An `ast` test asserts it imports nothing from `features.candidates`,
`models.shots`, `shot_model_evaluation` or the gauntlet's functions.

```python
def synthetic_league(world: Mapping, *, league_position: int, replicate: int, config: Mapping) -> LeagueFrames
def synthetic_corpus(world: Mapping, *, replicate: int, config: Mapping) -> dict[str, LeagueFrames]
def synthetic_shots(scenario: Mapping, *, replicate: int, config: Mapping) -> dict[str, pd.DataFrame]
def run_selfcheck(rule: Rule, config: Mapping) -> dict          # the "selfcheck" block of results.json
```

Seed for every draw: `np.random.default_rng([selfcheck_seed, world_position, replicate, league_position])`.

### 8.1 Generator (per league; parameters are the `synthetic_*` keys)

| Step | Rule |
|---|---|
| squad | 20 teams; per team 5 DF, 5 MD, 5 FW, 1 GK; the last DF and last MD are fringe players |
| fixtures | double round-robin, 38 rounds, 380 matches; `game_id` increases with the round |
| appearances | a regular plays a match with probability 0.75, a fringe player with 0.20; 90 minutes when he plays; the goalkeeper always plays |
| passes | 5 per player-match; `type "pass"`, start and end uniform on the pitch, `success` true with probability 0.8 |
| shots | per player-match Poisson(rate); rate = position mean x lognormal(0, log sd) with unit mean, drawn once per player; distance ~ Gamma(shape 6, scale s/6) x (0.6 if head-or-body), clipped to [1, 45] m, with s the player's distance scale; lateral offset = min(abs(Normal(0, 7)), distance); head-or-body with probability 0.16; coordinates rounded to two decimals; goal ~ Bernoulli(logistic(truth coefficients . features of the rounded coordinates)) |
| ground defending duels | opponent-half and own-half counts per player-match are independent Poissons with the player's two rates (position mean x unit-mean lognormal); opponent-half `start_x` uniform on {0.51..0.95}, own-half on {0.05..0.50}; each record's `player_id` set to 0 with the team's unattributed probability (linear from `low` to `high` across teams) |
| interceptions | per player-match Poisson(ratio x duel rate) in each half region; a `touch` row with `interception` true; never unattributed |
| goalkeeper | pass rows only |
| planted traps in every league | one penalty and one direct free-kick shot per team (`type "set_piece"`), two shots with `start_x <= 0.50`, one duel row and one shot row at a sentinel start, one shot by `player_id` 0 |

### 8.2 Planted worlds (candidates; five synthetic leagues each; 12 replicates)

| World | What is planted | Must be classified | Rate |
|---|---|---|---|
| `EFFECT` | within-position spread in shot rate (log sd 0.45, position means 1.2 / 1.5 / 1.8), player-specific shot distance scale uniform 8 to 28 m independent of rate, within-position spread in both duel rates, flat 10% unattributed | instrument `ACCEPTED` or `ACCEPTED_WITHIN_LEAGUE`; all four candidates `ESTABLISHED_NUMBER` or `ESTABLISHED_BAND` | every subject in at least 11 of 12 |
| `NULL` | no within-position spread in anything; position means 0.5 / 1.2 / 2.5; one distance scale | `shot_volume` and `box_shot_share` `NOT_ESTABLISHED` / `UNRELIABLE`; `shot_location_value` `NOT_ESTABLISHED` / `REDUNDANT`; `opp_half_defensive_actions` `NOT_ESTABLISHED` (any closure) | 12 of 12; an `ESTABLISHED_*` anywhere fails the self-check |
| `NUISANCE` | opponent-half duel rate 6.0 for everyone; own-half rate widely spread; unattributed probability 0 to 0.45 across teams | `opp_half_defensive_actions` `NOT_ESTABLISHED` / `CONFOUNDED` | at least 11 of 12; never `ESTABLISHED_*` |

`NULL` carries a second assertion that documents why the gate is position-centred:
the **uncentred** pooled reliability of `shot_volume` exceeds 0.70 in every
replicate league while its verdict is `UNRELIABLE`.

Generator sanity assertions (about the data, not the pipeline, computed from the
generator's own latent values): in `EFFECT` the population correlation between
latent shot rate and latent value rate is below 0.75; in `NUISANCE` the latent
share of variance carried by team attribution exceeds 0.65.

### 8.3 Planted instrument scenarios (five leagues x 8,000 shots; 12 replicates)

| Scenario | What is planted | Must be classified | Rate |
|---|---|---|---|
| `PLANTED` | every league follows the truth coefficients | `ACCEPTED`; never `NOT_ESTABLISHED` | at least 10 of 12 `ACCEPTED`, the rest `ACCEPTED_WITHIN_LEAGUE` |
| `NO_SIGNAL` | goal probability 0.105 for every shot | `NOT_ESTABLISHED` | 12 of 12 |
| `TOO_SHARP` | logit multiplied by 4 around its median, shifted by -3 | `NOT_ESTABLISHED`, with R5 among the failed gates | 12 of 12 |
| `LEVEL_SHIFT` | one league's odds multiplied by 0.80 | `ACCEPTED_WITHIN_LEAGUE`; never `ACCEPTED` | at least 11 of 12 |
| `SLOPE_SHIFT` | one league's centred logit halved | `NOT_ESTABLISHED`, with R3 among the failed gates | 12 of 12 |

Feasibility of these rates was checked on synthetic data at aggregate level before
this file was written (`_work/synth_feasibility*.py`, `_work/synth_worlds.py`,
`_work/synth_model*.py` beside this file; no real row was read): every stated
classification was met in 19 or 20 of 20 replicates. Those scripts drew true
probabilities rather than fitting per event, and the `NUISANCE` world and the
defensive candidate were checked by algebra only, so the event-level generator may
need a parameter moved.

**What may be adjusted, and until when.** `synthetic_*` parameters may be edited
until the protocol commit if a stated rate is not met, with the reason recorded in
the implementer's report. Thresholds, gates, the decision rule and the rates
themselves may not be edited to make a check pass. After the protocol commit
nothing in `config.json` changes.

### 8.4 Test files

| File | Content | Marker |
|---|---|---|
| `tests/test_candidate_planted.py` | 8.2 and 8.3 at `selfcheck_replicates`; the generator sanity assertions; the independence `ast` test; the planted traps never credited | `slow` for the full replicate count; a 2-replicate deterministic smoke variant always runs |
| `tests/test_candidate_runner.py` | phase order (a spy shows no value computed before phase 4 ends); each phase-1 and phase-2 stop; refusal to overwrite; determinism (two runs on a synthetic corpus byte-identical); `results.json` schema, size, `allow_nan`, banned-key walk, no identifier; config read from the frozen file and only `selfcheck_replicates` overridden; every threshold in code traced to a config key (source scan of `shot_model_evaluation.py`, `candidate_gauntlet.py` and the runner for the literals 0.85, 0.70, 0.60, 0.82 finds none outside docstrings) | — |
| `tests/test_candidate_pins.py` | on the real corpus, **structure only**: the `expected_*` pins, period filter, body-part coverage, clause overlap, fingerprints | `slow`; skips without data |

No test computes a candidate statistic or a model fit on real rows.

## 9. Pre-outcome code-review checklist

Signed off by a reviewer who did not write the package, before the protocol commit.

1. `git status` shows no `results.json` under the E-09 folder and no cached real-data output of this pipeline anywhere.
2. No agent report lists a real-data execution beyond `--preflight` and `tests/test_candidate_pins.py`.
3. Fingerprints computed by the code equal `config.json` (four of four).
4. `lf_sha256("experiments/run_replication.py")` equals `frozen_rule_lf_sha256`; `decide` is imported, not copied; no threshold literal in WP-C, D, E code.
5. `candidate_gauntlet.py`, `shot_model_evaluation.py`, `candidate_synthetic.py` are in the firewall tuple; nothing under `galactico/api`, `galactico/optimization`, `galactico/profiles`, `galactico/match_lab` imports them; `galactico/models/shots` imports nothing from `galactico/validation` or `experiments`.
6. `spec.SPECS` has five keys; `CONSTRUCTS` has five; the shipped fingerprints are unchanged; the full suite is green without the corpus.
7. The model sees only `distance_m`, `angle_rad`, `head_or_body`: `design_matrix` reads no other column; the strings `opportunity`, `success`, `blocked`, `zone` do not occur in `galactico/models/shots/`.
8. Leave-one-league-out leakage test present and passing; the reference rate is the training rate.
9. No goals-minus-model quantity anywhere (`grep` for a subtraction of a probability sum from a goal count in WP files).
10. The share floor, half floor, minutes floor and GK exclusion are applied before any value is computed; gate counts precede statistics (spy test).
11. Every departure of preregistration 6.1 has its named test; the T23 flag is emitted.
12. Self-check passes at the stated rates from a clean checkout, and `--preflight` on the real corpus prints all pins matching and the count gates (expected planning values: eligible 319 / 306 / 306 / 270 / 306; share sets about 80 / 84 / 88 / 66 / 80).
13. `results.json` writer: UTF-8, LF, `allow_nan=False`, sorted keys, size check, banned-key walk, no identifiers.
14. Phase 1 refuses a wrong commit, a dirty protocol, an existing output.
15. Protocol, config, this file and the code agree on every name in section 7.1; `preregistration.md` section 9 has seven rows and the code has seven branches.
16. Ruff clean; `from __future__ import annotations`; frozen dataclasses; `__all__`; docstrings state claim and non-claim.

## 10. External leg (WP-F, conditional)

`galactico/validation/candidate_external.py`; run through
`experiments/run_candidate_gauntlet.py --external --protocol-commit <sha>`; only
after `results.json` is committed and only for candidates at `ESTABLISHED_*`.

```python
def statsbomb_shot_detail(root: Path, competition: str) -> pd.DataFrame     # event_id:str, shot_type:str, body_part:str
def statsbomb_frames(competition: str, provider: StatsBombProvider, config: Mapping) -> LeagueFrames
def external_verdict(candidate: str, evaluations: Sequence[LeagueEvaluation], wyscout_mean: float,
                     statsbomb_mean: float, instrument_verdict: str | None, config: Mapping) -> str
def run_external(results: Mapping, config: Mapping) -> dict
```

| Rule | Detail |
|---|---|
| shot rows | neutral `type == "shot"` joined to `shot_type == external_shot_type`; `body_part` mapped to `head_or_body` for `external_head_or_body_parts`, else a foot class |
| reading raw events | keys reached through variables (`event.get(kind_key)`), never a double-quoted provider key followed by a colon; no freeze frame and no provider xG field is read, at all |
| instrument | the selected specification of the Wyscout run, refitted leave-one-league-out over the four StatsBomb leagues with the `external_minimum_training_*` gates; the same R and L gates |
| gauntlet | the same functions, same rule, `minimum_evaluable_leagues = 3` |
| verdict | preregistration section 11 |
| output | `external_output` under `data/licensed/` (gitignored). **Never committed.** The research report `docs/research/E-09-EXTERNAL-LEG.md` carries aggregate findings in prose and tables with the StatsBomb attribution; no coefficient table |
| firewall | nothing under `galactico/api` may import this module; add it to the firewall tuple |

`opp_half_defensive_actions` is never passed to this leg; its external verdict is
`NOT_COMPARABLE` by declaration.

## 11. Registry consequences

### 11.1 Applied by the root after the run (tonight)

| Verdict | Edit |
|---|---|
| any | remove `shot_profile` and `defensive_action_profile` from `UNTESTED` (one tuple after H1 B1; otherwise both `galactico/api/player_lab.py:40` and `scripts/generate_docs.py:67`); regenerate README / METRICS blocks; add the E-09 row to `experiments/preregistered/README.md`; write the five I3 verdict records |
| `INCONCLUSIVE` | add the candidate id to `UNTESTED` |
| `NOT_ESTABLISHED` / `REDUNDANT`, `CONFOUNDED`, `UNRELIABLE` | `REJECTED[id] = (headline, detail)` in `galactico/profiles/build.py` with the frozen headline of preregistration section 10; detail = the league range of the deciding statistic; add `test_<id>_stays_rejected` asserting absence from `CONSTRUCTS` and `spec.SPECS` |
| `NOT_ESTABLISHED` / `INSTRUMENT`, `MIXED`; `ESTABLISHED_*` awaiting the external leg | `RESEARCH_ONLY[id] = (headline, detail)` |
| `ESTABLISHED_*` for `opp_half_defensive_actions` | `RESEARCH_ONLY` tonight with headline "Passed the five-league lifecycle; not comparable in the second provider"; eligible for 11.2 |
| instrument, any verdict | `MODEL-CARD.md` rendered; `docs/LIVE-DATA-GAP-MATRIX.md:32` corrected from `DERIVABLE` to `MODELLED` for xG on the free corpus |

Counts after any outcome: 13 proposed; tested = 13 minus the candidates left in
`UNTESTED` minus `carrying_value`.

### 11.2 Full registration (`CONSTRUCTS` plus `SPECS`) — every hardcoded list

Needed before a survivor renders in Player Lab. Not executable tonight under R13
(see DISSENT 1). The complete list, so that it is one deliberate release:

| # | Where | Change |
|---|---|---|
| 1 | `galactico/domain/constructs.py` | `_register(ConstructDefinition(id, claim, family, estimators={"wyscout_event_v1": Estimator(key="wyscout_event_v1", regime="wyscout_event", inputs=..., denominator=..., minutes_floor=900)}, reference_estimator="wyscout_event_v1", display_name=<config display_name>, known_confounds=..., invalid_contexts=(... "goalkeeper" ..., "cross-league comparison", "any provider other than Wyscout v2 event data" where NOT_COMPARABLE), external_replication=<verdict, never UNTESTED>))` |
| 2 | `galactico/features/spec.py::SPECS` | `shot_volume` is expressible today (`Measure.COUNT`, `ActionFilter({"shot"})`, `PER_90`) and equals `SHOT_VOLUME_AS_CONSTRUCT_SPEC`. The other three are **not**: they need a subtype filter, an OR of clauses, a zone on `start_x`, and a model-weighted measure. New `ActionFilter` fields must enter `fingerprint` only when non-default or all five shipped fingerprints change |
| 3 | the three `Measure` switch sites | `features/spec.py:188-196`, `profiles/uncertainty.py:94-125`, `match_lab/model.py:120-135` |
| 4 | `galactico/features/estimators.py` | `ESTIMATOR_DENOMINATORS` labels every per-action spec "completed passes" (wrong for `box_shot_share`, whose denominator is shots); `CHANNEL_GEOMETRY` / `describe_style` assume a 0.5 reference for any style share |
| 5 | `galactico/match_lab/model.py:113-119` | hardcoded five-label dict; a sixth key raises `KeyError` |
| 6 | `tests/test_player_lab.py:53-54` (and `tests/test_registry_contract.py` after H1) | exact shipped set |
| 7 | `galactico/profiles/build.py` | `REJECTED` / `RESEARCH_ONLY` / `UNTESTED`; `RELIABILITY_CURVE` if a floor above 900 is wanted; `_render_state` has no band path, so an `ESTABLISHED_BAND` construct renders as insufficient signal today |
| 8 | `scripts/build_profiles.py`, `data/public/profiles/Spain_2017-18.json` | rebuild; until then `/api/*` returns 503 (stale `semantic_versions`) |
| 9 | `galactico/optimization/historical.py:247` | `feature_fingerprints` is built from `SPECS`: every XI snapshot's provenance changes although the frozen file is not edited |
| 10 | `galactico/profiles/uncertainty.py:164` | every `SPECS` key is bootstrapped for every player |
| 11 | `scripts/generate_docs.py`, README.md, METRICS.md | regenerate `constructs`, `claims`, `rejected`, `counts`, `fingerprints` |
| 12 | `galactico/providers/statsbomb.py::MAPPING_AUDIT` | add "shot, no penalties or direct free kicks" (SEMANTICALLY_EQUIVALENT with shot type) and "defensive action" (NOT_COMPARABLE); correct the existing "shot" row, which says no surviving construct uses shots |
| 13 | `galactico/domain/metrics.py` | the stale legacy `REGISTRY` seeds `defensive_action_profile`; `tests/test_domain.py:74-76` asserts it. Leave or retire deliberately; E-09 does not touch it |
| 14 | `galactico/domain/metrics.py::Family` | a per-90 count has no member other than the one named with a word this build does not put on an unvalidated label; see DISSENT 3 |
| 15 | `galactico/api/decision_lab.py:241-245` | **not changed.** The shipped requirement dict stays three keys |

### 11.3 May a surviving construct become an XI or Squad requirement dimension?

| Construct, state | Requirement dimension | Name on the surface | Evidence class |
|---|---|---|---|
| `shot_volume`, `ESTABLISHED_NUMBER`, external `ROBUST` or `ROBUST_WITH_SHIFT` | yes, user-declared, new endpoints only | id `shot_volume`; "Shots per 90, no penalties or direct free kicks (sum of selected players' historical rates)" | HEURISTIC on the domain ladder (DERIVED rate, additive historical per-90 assumption, declared minimum; weakest wins). Legacy XI string `HEURISTIC` |
| `opp_half_defensive_actions`, `ESTABLISHED_NUMBER`, external `NOT_COMPARABLE` | yes, same conditions; same-league universe only | id `opp_half_defensive_actions`; "Opponent-half defensive actions per 90 (ground defending duel records and interception-flagged events; sum of historical rates)". Never "pressing" | HEURISTIC |
| `shot_location_value`, any verdict, tonight | no | — | UNAVAILABLE in every dated snapshot until an instrument fitted strictly before the decision date exists (R9) and passes its 6,000-shot gate |
| `shot_location_value`, after that follow-up | yes, same conditions | "Location-model value of shots per 90 (location-only conversion model; not provider xG)" | HEURISTIC (PREDICTIVE input) |
| `box_shot_share`, any verdict | **never** | descriptor only: Player, Transfer and desk evidence ledgers | DERIVED; not summed, not scaled by break-even retention |
| any construct at `ESTABLISHED_BAND` | inactive research dimension, user opt-in, never default | same names | EXPERIMENTAL on the ladder; legacy `RESEARCH`, `status="research"` |
| anything else | no; listed in the "not measured here" panel | — | — |

Tonight only `opp_half_defensive_actions` can meet a row above (its external
verdict is declared, not derived), and then only as an opt-in dimension that is
inactive by default; every other survivor waits for the external leg. A row that
depends on a `ROBUST` label depends on a StatsBomb-derived label reaching a hosted
surface: precedent exists for labels (`/api/constructs` already returns them), no
number is involved, and the owner's pending decision on that precedent governs.
If it goes against, those rows read "no".

A requirement sum of shot rates is not team shots: who shoots depends on who else
plays. The surface carries the same additive-assumption sentence the progression
requirement carries. No verdict produces an objective weight.

## 12. Model card — frozen template

`render_model_card(results)` emits exactly these sections; every number is read
from `results.json`, none is typed. `{...}` marks a field.

1. **Model details.** `shot_location_v1`; instrument `{selection.instrument}`; unpenalised logistic regression, IRLS, NumPy `{packages.numpy}`; formula of preregistration 4.1; pitch convention 105 x 68 m, goal 7.32 m; coefficients and standard errors for each of the five leave-one-league-out fits (table); protocol commit `{...}`; training-frame hashes.
2. **Intended use.** Valuing the origin of shots (no penalties, no direct free kicks) in aggregate over a player-season, within one league, for men's top-division club football of 2017/18, as input to a construct that passes its own lifecycle.
3. **Out of scope, as prohibitions.** A verdict on a single shot. Finishing skill. Goalkeeper evaluation. Comparison with any provider's xG as if on one scale. Any season, tier, sex or provider not evaluated. Any dated decision, until a strictly-prior fit exists.
4. **What enters and what does not.** In: shot origin, provider head-or-body class. Not in: defender and goalkeeper positions, pressure, shot type, ball height, assist type, shooter, team, league, game state. Excluded as outcome-informed, with audit counts: opportunity tag (on 4,250 of 4,271 goals), accuracy tags, blocked tag, goal-mouth zone tags.
5. **Training data.** Pappalardo et al. 2019, CC BY 4.0; provider `Shot` events, periods 1H and 2H, origin in the opponent half; exclusions with counts `{structure}`; label = goal flag on the shot row; base rate by league `{...}`.
6. **Evaluation.** Leave one league out, five folds; match-level resampling, `{bootstrap_replicates}` replicates, coefficients fixed.
7. **Metrics**, per held-out league and pooled, for `M0`, `MD`, `M1`, `MFLEX`: Brier, log loss, both skills against the training rate, observed over expected, calibration slope and intercept, ECE and MCE with the simulated null percentiles, AUROC (for comparability only). Table from `{instrument.leagues}`, `{instrument.pooled}`.
8. **By factor.** Observed over expected for footed, head-or-body, three distance bands (gated); counter-attack flag (descriptive). Calibration bins per league.
9. **Uncertainty not in any number here.** (a) coefficient uncertainty: omitted from intervals; (b) omitted information: published Brier gaps put the per-shot disagreement with a richer model at 0.05 to 0.08 RMS, the same order as the mean shot value; its between-player part cannot be estimated from this corpus; (c) location error: integer-percent coordinates, unpublished operator accuracy; (d) outcome variance is not uncertainty about the model sum.
10. **Evidence class.** PREDICTIVE. Every construct built on it inherits it.
11. **Verdict and scope.** `{instrument.verdict}`; failed gates `{...}`. Under `ACCEPTED_WITHIN_LEAGUE`: values carry no goal unit and are not compared across leagues.
12. **Caveats.** Metres are a convention on percent coordinates; the provider's pitch drawing is not metric; head-or-body is not header; one season; national-team matches not evaluated; in-sample valuation is forbidden (a league is always valued by the fit that excluded it).
13. **Temporal validity.** Full-season out-of-league fits are measurement instruments for research only.
14. **Change policy.** Formula and thresholds frozen at the protocol commit. A refit is a new model id with a new card.

## 13. DISSENT

1. **"CONSTRUCTS plus SPECS" cannot be the tonight consequence of a positive verdict.** Evidence: `ConstructSpec` cannot express three of the four candidates (section 11.2 row 2) and `features/spec.py` is frozen for implementers; a sixth `SPECS` key changes `feature_fingerprints` in every XI snapshot (`historical.py:247`), stales the Player Lab bundle (503) and raises in Match Lab, all of which R13 pins. The design satisfies the root decision by specifying the full registration list (11.2) and satisfies R13 by making tonight's consequence a verdict record plus `RESEARCH_ONLY` copy (11.1). Recommended: full registration as its own versioned release with an ADR.
2. **Candidates are `CandidateSpec`, not `ConstructSpec`.** The root layout says "candidate ConstructSpecs". Same evidence as above. `shot_volume` is additionally provided in plain `ConstructSpec` form and tested equal.
3. **The registry's only family for a per-90 magnitude is named with a banned word.** `Family` has QUALITY, STYLE, PHYSICAL, TEAM; shipped per-90 constructs use the first, and `orderable_as_ranking` and the compare "leader" key off it. Candidates carry `family="volume"` here. Before any registration the root should add a neutral member or accept the enum name as internal.
4. **The frozen `decide()` is reused unchanged, but not with Stage 1B's inputs.** Evidence: its battery contains shots per 90 (the candidate itself); `decide(0.9, 0.0, float("nan"), False)` returns `SHIP`; the house R-squared is joint with team although the rule's docstring thresholds nuisance variance. The rule body and thresholds are untouched; the three input guards are tabled in preregistration 6.1, and the one that can favour survival is flagged per league.
5. **Two-tier instrument acceptance.** The root asked for frozen acceptance thresholds; this design freezes them and adds a scope tier (`ACCEPTED_WITHIN_LEAGUE`). A single tier would most likely reject the instrument on Italy's level (planning figure 0.897), a property no within-league candidate uses. If the council prefers one tier, delete the L/R distinction and treat every gate as R; the expected result is then `NOT_ESTABLISHED` for the instrument and closure `INSTRUMENT` for `shot_location_value`.

## 14. Open questions

1. Does the sidecar (I1) land tonight with `body_part` on every shot? Without it E-09 cannot leave preflight.
2. Thresholds R1 (0.08 pooled, 0.03 per-league lower bound) differ from the reconnaissance proposal (0.08 point and 0.05 lower bound in every league). By derived sampling error (about 0.012 per league) the proposal fails a model whose true skill is 0.10 in about one run in five; the council should confirm before the commit.
3. A per-shot mean of the instrument was left out in favour of `box_shot_share`. If the council wants it, it is a fifth candidate and needs its own protocol.
4. Within-position reliabilities are reported and written into `invalid_contexts`, but nothing in the product gates a render on position. Is text enough?
5. Should Euro 2016 and World Cup 2018 be an external transport test of the instrument? Not in this protocol; they are not in the neutral Parquet cache used here.
6. Whether E-10 uses `shot_location_v1` for conceded shot value; if so its protocol must cite the instrument verdict.
7. The reconnaissance critic asks for the interval method to be fixed as a house decision before any protocol (its O5). E-09 fixes its own, stricter, inside the protocol. If the council adopts a house rule tonight, E-09 takes it before the commit provided it is no more lenient than `min(house, half-r)`.
8. The external leg needs raw StatsBomb shot type and body part, which the neutral adapter drops. WP-F reads them in a LOCAL helper; E-11 will need the same fields and the two should share one reader.
