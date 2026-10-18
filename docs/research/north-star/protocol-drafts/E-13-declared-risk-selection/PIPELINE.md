# E-13 pipeline specification

Companion to `preregistration.md` and `config.json` in this folder, registered with them and
pinned by `pipeline_spec_sha256`. The protocol says what is decided; this file says what is
built. Where they disagree the protocol wins and the disagreement is a defect to report. Every
shipped name below was read in the code on 18 October 2026 (section 1); nothing is assumed.

## 0. Files, ownership, order

One implementation agent owns the new files (one module, one runner); no shared file is edited
by it.

| File | Kind | Notes |
|---|---|---|
| `galactico/validation/risk_selection.py` | new | engine, simulator, real split, decisions, planted arms. Research only; nothing under `galactico/api`, `galactico/optimization`, `galactico/profiles`, `galactico/match_lab`, `galactico/domain` may import it |
| `experiments/run_risk_selection.py` | new | CLI, provenance, oracle gate, writer |
| `tests/test_risk_selection.py` | new | the module: engine oracle, synthetic, split, decisions, planted gate (sections 6.1 to 6.4, 6.6) |
| `tests/test_risk_selection_experiment.py` | new | the runner: config contract, registry records, writer, hashes, rehearsal (6.5) |
| `experiments/preregistered/E-13-declared-risk-selection/{preregistration.md,config.json,PIPELINE.md}` | root commits | registered from this folder (section 11). `config.json` and `PIPELINE.md` byte for byte; `preregistration.md` after one edit, the DRAFT banner replaced by one line pointing at ROOT-DECISIONS and the north-star README. The implementer reads them and never edits them |
| `experiments/preregistered/E-13-declared-risk-selection/acceptance.json` | root commits, after the pipeline commit and before the run | the planted gate's stamp (section 9). Not a protocol file |

Not touched: `experiments/run_optimizer_curse.py` (called by the bridge, bytes pinned), every
frozen file of ROOT-DECISIONS 3b, `galactico/optimization/squad/kernel.py` (ROOT 2.7 X9),
`galactico/optimization/xi/risk.py`, the verdict registry, the router and every other shared
file (section 11 lists what the root changes, and when).

**Order** (the house order, north-star README "How a draft becomes a protocol"): the audit;
the registration commit (three protocol files, six `PENDING` records, the shared-file edits of
section 11); the pipeline commit (the four files above); the pre-outcome code review
(section 7); the planted gate, stamped in a commit of its own (`acceptance.json`); one run and
one determinism re-run (section 8). Nothing of this file is built or run before registration.
A rule the planted gate shows to be unsound is not repaired: E-13 is superseded by a new
experiment id with its own preregistration. Code may be corrected where it departs from the
frozen text, after which the code review is repeated for the changed files and the stamp is
regenerated.

Build order inside the pipeline commit: 2.1 and 2.2 with their oracle first; then 2.3 to 2.5
(synthetic: no data, no solver); then 2.6 (real split; the solver import is lazy and only
inside `solver_audit`). Decisions (2.7) are pure and can be written first; planted arms (2.8)
last.

**Outcome hygiene for the implementer.** Develop only with `rehearsal_seed`, `planted_seed` or
test-local seeds, on `rehearsal_design` cells, planted cells and the synthetic corpora of 2.6.
Never call `run(config, rehearsal=False)`, never pass the frozen `seed` to a generator, never
evaluate a half-split of a real snapshot. A planted run on the frozen geometries evaluates
BALANCE, the reference arms and the pseudo-rules only (`rules=("BALANCE",)`), never a
declared-risk rule. The rehearsal evaluates every rule, on `rehearsal_design` cells only,
which share no (latent SD, noise, minimum) with a frozen cell; its artifact therefore holds no
risk-rule table for a frozen cell. The `slow` parity tests compare half-free quantities
(full-sample values and shipped worlds) with `build_snapshot`; that is structure, and it is the
only real-data contact allowed before the run.

## 1. Shipped interfaces (verified against the code on 18 October 2026)

| Need | Shipped object | How |
|---|---|---|
| Quantisation constant | `galactico.optimization.xi.QUANTIZATION` (re-exported from `solver.py`) | must equal `config["quantization"]`, asserted at start |
| Rounding policy | `solver._q(value, normalizer, scale) = int(round(value / normalizer * scale))`, Python's half-even | re-expressed as `np.rint(values / normalizer * quantization)` (half-even), divide then multiply then round; parity test against `_q` |
| Frames | the four files of `data_paths`, read whole by `pandas.read_parquet` (`data_read_rule`, as `historical.load_snapshot` reads them) | once per run; peak memory printed to stderr |
| Snapshot, candidates, minima, provenance | `historical.build_snapshot(actions=, matches=, lineups=, players=, match_id=, worlds=0, team_id=)`; `api.decision_lab.decision_inputs(snap, formation, minimums=None)` | unchanged; `decision_inputs` returns the three measured requirements in force (the opt-in state of XI Lab, OR-XI-SPEC 1.3) and three inactive `unavailable` rows |
| Prior frames | `optimization.snapshots.prior_frames(actions=, matches=, lineups=, cutoff_day=)` | the frames `historical.py` hashes, in its order |
| xT surface | `historical.fit_prior_xt(prior_actions)` (ROOT 2.5 O2) | same prior rows as the snapshot |
| Per-match components | `optimization.snapshots.rate_components(actions=team_actions, by_match=by_match, xt=xt, metrics=...)` with the three `SnapshotMetric`s of `snapshots.snapshot_metrics()` whose `metric_id` is in `expected_active_requirements`; `by_match` = the team's prior lineups grouped by `(player_id, game_id)`, minutes summed (`historical.py:136`) | the product's own implementation of the published rule (ROOT 4, Z3: one object); `snapshots.py` is pinned in `source_paths`; a slow test ties its sums to `build_snapshot`'s values |
| Shipped world weights (parity only) | `profiles.uncertainty.shared_match_weights(game_ids, replicates, seed)` with `historical.SEED` | parity test of world values |
| Eligibility semantics | `solver._eligible(player, slot)`: `player.minutes > 0 and player.position in slot.allowed_positions and (player.eligible_slots is None or slot.slot_id in player.eligible_slots)`; `solver._applies(requirement, slot_id)`; a key with a `None` value for a requirement in force at that slot is inadmissible | re-implemented in `enumerate_selections` (not imported), checked by the solver audit |
| Discard rule | `risk._discard` (OR-XI-SPEC 1.4; `solver.py:549-564`): a world is discarded when a non-excluded candidate eligible at a slot where a requirement in force applies has no value in it for that requirement | re-implemented in `world_valid` (2.2) and `weighted_rates` (2.6); a test ties the Part B used and discarded world ids to `risk.world_losses` on a synthetic corpus |
| BALANCE solver (audit only) | `galactico.optimization.xi.solve_xi(candidates, requirements, formation, *, seed=, time_limit=, quantization=, analyze_ties=False)` returning `XIResult` (`solution_status`, `assignments`, `objective_vector` = `(M / Q, T / Q)`) | certified when `solution_status == "OPTIMAL"`; objective compared as `round(v * Q)` |
| Risk solver (audit only) | `galactico.optimization.xi.risk.declared_risk_selection(candidates, requirements, formation, *, rule, tail_count, worlds, world_count, world_seed, bootstrap_version, locked=(), excluded=(), seed, quantization, analyze_ties, deadline, provenance=None)` returning `RiskSelection` (`status` in `CERTIFIED`, `UNFIELDABLE`, `NOT_EVALUABLE`, `UNKNOWN`, `MODEL_INVALID`; `lineup` as `((slot_id, player_id), ...)`; `world_losses` of `WorldLoss(world_id, selected=LossPair(maximum_shortfall, total_shortfall), world_least)`; `tail_sum` = `TailSums(summed_maximum_shortfall, summed_total_shortfall)`; `certificate` with `used_world_ids`, `discarded_worlds`, `completeness`) | lazy import inside `solver_audit` through two adapters (2.6); `rule="WORST_WORLD"` takes `tail_count` 1, `"TAIL"` the tier's `k`, `"MINIMAX_REGRET"` none; `deadline` is a `time.monotonic()` value |
| Risk oracle | `tests/test_xi_risk_oracle.py` (nine tests, seven of which need POSIX resource limits and skip on Windows) and `tests/xi_exact_oracle.py` (the brute-force logic, no test function) | both are `risk_solver_oracle_tests`; both hashed; pytest runs both paths and collects tests from the first |
| LF hashing | `galactico.validation.digests.lf_sha256(path) -> str`, `lf_sha256_text(text) -> str` | text files only |
| M-05 | `experiments.run_optimizer_curse.run(seed, trials)` | bridge reference, called live |
| Registry and copy guard | `galactico.domain.verdicts` (`VerdictRecord`, `Outcome`, `Tier`, `VerdictStatus`, `derive`, `all_payloads`, `PENDING`); `galactico.api.runtime.finalize`, `HOSTED_PROVIDERS`, `BoundaryViolation`; `galactico.domain.labels.scan_labels`; `galactico.domain.thesis.banned_key_paths(payload, *, banned, parts, allow)` with `BANNED_KEY_PARTS` | the runner's tests (6.5); the writer's key walk |
| Corpus fixtures | `tests/conftest.py`: `corpus_root`, `spain_frames` (skip cleanly without data) | the three `slow` tests |
| Provider guard | `galactico.providers.base.assert_may_host("pappalardo")` | in the loader |

## 2. `galactico/validation/risk_selection.py`

Module docstring (verbatim first paragraph): "E-13: declared-risk selection rules compared
by exhaustive enumeration. Claims what each rule selects and reports inside a declared
additive requirement model, on synthetic matches with known values and on coherent halves
of historical matches. Claims nothing about football: a rule is a declared preference over
resamples, never a way to pick a team that plays differently."

`__all__` lists every public name below. `VERSION = config["version"]`, asserted equal at
import of the config. All dataclasses `frozen=True`. Arrays are NumPy; "int" arrays are
`int64`; coefficient arrays are `float64` holding exact integers. Index letters: `B` batch
(trials or split directions), `W` worlds, `N` candidates, `R` requirements (sorted by
requirement id), `S` selections, `G` matches. No function takes a default for a value that is
in config.

### 2.1 Integer model

```python
def quantize(values: np.ndarray, normalizer: np.ndarray | float, quantization: int) -> np.ndarray
    # np.rint(values / normalizer * quantization); divide, then multiply, then round (solver._q order)
def selection_sums(coefficients: np.ndarray, incidence: np.ndarray) -> np.ndarray
    # (..., N, R), (S, N) -> (..., S, R) via np.einsum("...nr,sn->...sr", ...); assert abs < 2**50
def shortfalls(sums: np.ndarray, targets: np.ndarray) -> tuple[np.ndarray, np.ndarray]
    # (..., S, R), (R,) -> M (..., S), T (..., S), int64; d = maximum(0, targets - sums)
def encoding_base(total_bound: int, worlds: int) -> int
    # encoding_base_rule: max(2, 2 * worlds * total_bound + 1), total_bound = max(sum of targets,
    # largest T of the batch over point, world and reference values). Raises OverflowError unless
    # (M_max * BIG + total_bound) * worlds < 2**62 at the call site (checked by encode)
def encode(m: np.ndarray, t: np.ndarray, base: int) -> np.ndarray      # base * m + t, int64; private use only
def level_of(objective: np.ndarray) -> np.ndarray                      # (B, S) -> bool (B, S): objective == row minimum
def level_mean(level: np.ndarray, values: np.ndarray) -> np.ndarray
    # bool (B, S), (B, S) or (B, S, R) -> (B,) or (B, R): mean over the level set; NaN where it is empty
```

`BIG` is recomputed per call from the batch's own bound. Any value above that bound gives the
same order; a test doubles it and requires identical outputs. No function returns, logs or
stores an encoding; only decoded `M`, `T` and level sets leave.

### 2.2 Rules

```python
RULES = ("BALANCE", "WORST_WORLD", "TAIL_10", "TAIL_25", "TAIL_50", "MINIMAX_REGRET")
MODES = RULES[1:]

@dataclass(frozen=True)
class RuleOutcome:
    rule: str
    level: np.ndarray               # bool (B, S)
    usable: np.ndarray              # bool (B,): W_used >= max(1, tail_count); always True for BALANCE
    tail_count: int | None          # k; 1 for WORST_WORLD; None for BALANCE and MINIMAX_REGRET
    own_m_sum: np.ndarray | None    # int64 (B,): sum of M over the k tail worlds at the optimum (BALANCE: point M);
                                    # None for MINIMAX_REGRET
    own_t_sum: np.ndarray | None    # int64 (B,): the same for T (the audit compares both with TailSums)
    own_divisor: int | None         # k (1 for BALANCE and WORST_WORLD); None for MINIMAX_REGRET
    world_least: np.ndarray | None  # MINIMAX_REGRET: int64 (B, W, 2), each world's least (M, T); else None

def world_valid(denominators: np.ndarray, needed: np.ndarray) -> np.ndarray
    # (B, W, N) world denominators, bool (N,) candidates eligible at a slot where a requirement in force
    # applies -> bool (B, W): every needed candidate has a positive denominator (the discard rule, T2)

def apply_rules(
    point_m: np.ndarray, point_t: np.ndarray,        # int64 (B, S)
    world_m: np.ndarray, world_t: np.ndarray,        # int64 (B, W, S)
    world_valid: np.ndarray,                         # bool (B, W)
    *, tail_counts: Mapping[str, int], base: int,    # {"WORST_WORLD": 1, "TAIL_10": k, ...} for this W
    rules: Sequence[str] = RULES,
) -> dict[str, RuleOutcome]
```

Masked reductions, with `e = encode(world_m, world_t, base)` and invalid worlds set to `-1`
(every valid encoding is `>= 0`, so a discarded world never enters a tail):

| Rule | Objective `(B, S)` | Decoding |
|---|---|---|
| `BALANCE` | `encode(point_m, point_t, base)` | `own_m_sum = point M` at the optimum |
| `WORST_WORLD`, `TAIL_*` | `sort(e, axis=1)[:, ::-1][:, :k].sum(axis=1)` | `own_m_sum = objective.min(axis=1) // base`, `own_t_sum = objective.min(axis=1) % base` (exact because `base > sum of T`) |
| `MINIMAX_REGRET` | `e_star = where(valid, e.min(axis=2), 0)`; `where(valid[..., None], e - e_star[..., None], 0).max(axis=1)` | `world_least` decoded from `e_star` |

`k` is fixed by the tier (ROOT 2.5: `TAIL(k of B)`); it is not recomputed on `W_used`. Rows
with `W_used < max(1, k)`: `usable=False`, empty level set, excluded and counted by callers
(`unusable_trial_rule`). `rules` lets a planted run evaluate BALANCE alone.

```python
@dataclass(frozen=True)
class Evaluation:
    rule: str
    level: np.ndarray                 # bool (B, S)
    level_size: np.ndarray            # int64 (B,)
    usable: np.ndarray                # bool (B,)
    informative: np.ndarray           # bool (B,): level differs from BALANCE's level; False for BALANCE
    reported_point_m: np.ndarray      # float64 (B,), normalised units, level mean
    reported_point_t: np.ndarray
    reported_own_m: np.ndarray | None # own_m_sum / (own_divisor * Q)
    own_nonzero: np.ndarray | None    # bool (B,): some selection of the level has a non-zero own statistic
    reference_m: np.ndarray           # level mean of the reference M / Q (truth in A1; held-out in A2, B)
    reference_t: np.ndarray
    reference_nonzero: np.ndarray     # bool (B,): some selection of the level has a non-zero reference M
    disappointment_point: np.ndarray  # level mean of 1[reference M > point M], integer comparison per selection
    disappointment_own: np.ndarray | None  # level mean of 1[reference M * own_divisor > own_m_sum]
    reference_regret_m: np.ndarray    # reference_m - (smallest reference M over selections) / Q
    reference_optimal: np.ndarray     # level mean of 1[selection attains the lexicographic reference optimum]
    point_sums: np.ndarray            # float64 (B, R): level mean of the selection's coefficient sums / Q at the point values
    reference_sums: np.ndarray        # float64 (B, R): the same at the reference values

def evaluate_rules(
    point_coef: np.ndarray,       # (B, N, R)
    world_coef: np.ndarray,       # (B, Wmax, N, R)
    world_valid: np.ndarray,      # bool (B, Wmax)
    reference_coef: np.ndarray,   # (B, N, R)
    targets: np.ndarray,          # int64 (R,)
    incidence: np.ndarray,        # (S, N)
    *, tiers: Sequence[int], tail_counts: Mapping[int, Mapping[str, int]], quantization: int,
    rules: Sequence[str] = RULES,
    extra_levels: Mapping[str, np.ndarray] | None = None,   # reference / planted arms: name -> bool (B, S)
) -> dict[int, dict[str, Evaluation]]
```

Tier `W` uses `world_coef[:, :W]` and `world_valid[:, :W]`; world sums are computed once at
`Wmax`. `extra_levels` arms get an `Evaluation` with `reported_own_m=None`. Batch so that no
array exceeds about 250 MB (`B * Wmax * S * R * 8` bytes).

### 2.3 Synthetic matches

```python
@dataclass(frozen=True)
class Geometry:
    geometry_id: str
    groups: tuple[tuple[int, int], ...]   # (group size, picks)
    requirements: int
    trials: int
    normalizer: float
    minimum_levels: tuple[tuple[str, float], ...]
    exposure_counts: Mapping[str, tuple[int, ...]]

def geometries(config: Mapping, *, design: str) -> tuple[Geometry, ...]
    # design "FROZEN": config["geometries"]; "REHEARSAL": the same geometries with rehearsal_design's
    # minimum levels and trials // rehearsal_design["trial_divisor"]. Raises ValueError on a null count vector
def geometry_incidence(geometry: Geometry) -> np.ndarray
    # (S, N); rows in itertools.product order of itertools.combinations per group, candidates numbered group by group

@dataclass(frozen=True)
class SyntheticDraws:
    latent: np.ndarray            # (trials, N, R) = latent_mean + latent_sd * standard normal
    match_uniforms: np.ndarray    # (trials, N, G) uniform [0, 1)
    count_order: np.ndarray       # int64 (trials, N): a permutation of 0..N-1 per trial
    shared: np.ndarray            # (trials, G, R) standard normal
    idiosyncratic: np.ndarray     # (trials, G, N, R) standard normal
    world_counts: np.ndarray      # int64 (trials, Wmax, G): multinomial(G, np.full(G, 1 / G))
    half_order: np.ndarray        # int64 (trials, G): permutation; half A = the G // 2 matches listed first
    half_world_counts: np.ndarray # int64 (trials, 2, Wmax, G // 2): multinomial(h, np.full(h, 1 / h)) per direction, h = G // 2

def draw_synthetic(geometry: Geometry, *, geometry_index: int, seed: int, config: Mapping,
                   latent_sd: float, trials: int, worlds: int) -> SyntheticDraws
```

Streams: `np.random.default_rng([seed, geometry_index, stream])` with `stream` =
`config["stream_*"]` (latent 0, match uniforms 1, count permutation 2, shared effect 3,
idiosyncratic 4, world counts 5, split halves 6, half-A worlds 7, half-B worlds 8, planted
coins 9, planted noise 10). One call per stream, in the shapes above, so no stream depends on
another. Probabilities are always arrays (`np.full(h, 1 / h)`): numpy 2.5 refuses a scalar.

```python
def exposure(draws: SyntheticDraws, counts: Sequence[int], profile: str) -> np.ndarray
    # bool (trials, G, N). Candidate i gets sorted(counts)[count_order[t, i]] matches
    # (WIDE_ALIGNED: the position of i in a stable ascending argsort of latent[t].mean(axis=-1) replaces count_order);
    # he plays the matches whose match_uniforms[t, i] are the n_i smallest (stable argsort)
def observations(draws: SyntheticDraws, *, noise_sd: float, shared_fraction: float) -> np.ndarray
    # (trials, G, N, R): latent + noise_sd * sqrt(G) * (sqrt(rho) * shared[:, :, None, :] + sqrt(1 - rho) * idiosyncratic)
def weighted_values(obs: np.ndarray, plays: np.ndarray, weights: np.ndarray) -> tuple[np.ndarray, np.ndarray]
    # obs (B, G, N, R), plays (B, G, N), weights (B, K, G) >= 0
    # -> values (B, K, N, R) = sum_g w*plays*obs / sum_g w*plays ; valid bool (B, K) by world_valid with every
    #    candidate needed (in Part A every candidate is eligible for a pick at which every requirement applies)
def oracle_shrinkage(values: np.ndarray, plays_count: np.ndarray, *, noise_sd: float, latent_mean: float,
                     latent_sd: float, matches: int) -> np.ndarray
    # latent_mean + a_i * (values - latent_mean), a_i = latent_sd^2 / (latent_sd^2 + noise_sd^2 * matches / n_i)
def m05_bridge(config: Mapping) -> dict
    # rng = default_rng(bridge_seed); latent = rng.normal(1.8, 0.3, (bridge_trials, 8, 2)); for noise in bridge_noise_sd:
    # measured = latent + rng.normal(0, noise, latent.shape)   -- M-05's exact draw order (the three literals are M-05's).
    # BALANCE_FIRST: the first index of BALANCE's level set in combinations order, on the measured values;
    # ORACLE_SHRINKAGE_FIRST: the first index of BALANCE's level set on oracle_shrinkage(measured) with every n_i = G
    # (so a = 0.3^2 / (0.3^2 + noise^2), M-05's factor); each of the six columns from the arm bridge_columns names,
    # against run_optimizer_curse.run(); returns {"rows": [...], "maximum_absolute_difference": float, "passed": bool}
```

### 2.4 Cells and Part A1 / A2

```python
@dataclass(frozen=True)
class Cell:
    cell: int                 # position in expand_cells(config)
    block: str                # "PRIMARY" | "BEYOND_MENU" | "SENSITIVITY" | "STRESS" | "SPLIT"
    variant: str              # "BASE" or a sensitivity variant id
    geometry_id: str
    noise_sd: float
    minimum_level: str
    minimum: float
    exposure_profile: str
    shared_fraction: float
    worlds: int

def expand_cells(config: Mapping, *, design: str) -> tuple[Cell, ...]
```

Order: PRIMARY (tier in `decision_tiers`, geometry, noise, level, exposure), BEYOND_MENU
(tiers of `world_tiers` not in `decision_tiers`; same inner order), SENSITIVITY (variant,
exposure, geometry, noise, level; at `sensitivity_worlds`), STRESS (geometry, noise, level,
exposure; at `stress_worlds`, primary exposure profiles), SPLIT (tier in `decision_tiers`,
geometry, noise, level; at `split_exposure_profile`). With `design="FROZEN"` the counts must equal
`expected_primary_cells_per_tier` per tier (PRIMARY and BEYOND_MENU),
`expected_sensitivity_cells`, `expected_stress_cells`, `expected_split_cells_per_tier` per
decision tier; assert. With the frozen config: 72 + 36 + 90 + 12 + 36 = 246 cells. With
`design="REHEARSAL"`, PRIMARY and SPLIT only, over `rehearsal_design`'s noise and levels at the
primary profiles and `rehearsal_design["latent_sd"]`; no count is asserted.

```python
@dataclass(frozen=True)
class ArmRow:           # one per (cell, arm); BALANCE and reference arms are emitted for the first decision tier only
    cell: int; arm: str; trials_used: int; discarded_world_trial_share: float
    level_size_mean: float; tied_share: float; identical_share: float | None
    reported_point_m: float; reported_own_m: float | None
    true_m: float; true_t: float
    optimism_point: float; optimism_own: float | None
    disappointment_point: float; disappointment_own: float | None
    regret_m: float; optimal_frequency: float

@dataclass(frozen=True)
class PairedRow:        # one per (cell, rule in MODES)
    cell: int; rule: str; valid: bool; usable_trials: int; informative_trials: int; compared: bool
    reporting_nonzero_trials: int; reporting_compared: bool
    delta_true_mean: float; delta_true_low: float; delta_true_high: float; delta_true_se: float
    delta_rep_mean: float; delta_rep_zero_informative_share: float | None
    delta_optimism_mean: float; delta_optimism_low: float; delta_optimism_high: float
    optimism_own_mean: float | None; optimism_own_low: float | None; optimism_own_high: float | None
    true_shortfall_lower: bool      # delta_true_high < 0; recorded, carries no token

@dataclass(frozen=True)
class SplitRuleRow:     # A2, one per (cell, rule)
    cell: int; rule: str; trials_used: int; informative_trials: int
    true_optimism_half: float; heldout_gap: float; heldout_excess: float

@dataclass(frozen=True)
class DiagnosticRow:    # A2, one per (cell, rule in MODES)
    cell: int; rule: str; usable_trials: int; informative_trials: int                     # reported only
    delta_optimism_mean: float; delta_optimism_low: float; delta_optimism_high: float   # truth
    delta_gap_mean: float; delta_gap_low: float; delta_gap_high: float                  # held-out
    delta_true_mean: float; delta_true_low: float; delta_true_high: float               # truth
    delta_out_mean: float; delta_out_low: float; delta_out_high: float                  # held-out
    tracking_mean: float; tracking_low: float; tracking_high: float                     # delta_out - delta_true
    agreement: str                                                                       # "AGREES" | "CONTRADICTS" | "UNRESOLVED"
    tracking: str                                                                        # "TRACKS" | "DIVERGES" | "UNRESOLVED"

@dataclass(frozen=True)
class SumGapRow:        # A2, BALANCE, one per SPLIT cell of the first decision tier
    cell: int; trials_used: int
    sum_gap_true_mean: float; sum_gap_true_low: float; sum_gap_true_high: float
    sum_gap_heldout_mean: float
    recovery_ratio: float | None; recovery_low: float | None; recovery_high: float | None   # None when unresolved
    denominators_positive: bool | None                                                       # every replicate's
    resolved: bool                                                                           # sum_gap_true_low > 0
    recovers: bool | None                                                                    # protocol's rule; None when unresolved
    shortfall_excess_mean: float                                                             # BALANCE heldout_excess

def trial_bootstrap_counts(trials: int, *, replicates: int, seed: int, geometry_index: int) -> np.ndarray
    # int64 (replicates, trials): default_rng([seed, geometry_index]).multinomial(trials, np.full(trials, 1 / trials),
    # size=replicates)
def paired_interval(differences: np.ndarray, usable: np.ndarray, counts: np.ndarray, *,
                    quantiles: Sequence[float], method: str) -> tuple[float, float, float, float]
    # differences (trials,), finite where usable; usable bool (trials,). Restricted to usable columns:
    # replicate means = (counts[:, usable] @ differences[usable]) / counts[:, usable].sum(axis=1);
    # returns (mean over usable trials, low, high, se) with np.quantile(..., method=method) and
    # se = std(replicate means, ddof=1) (standard_error_rule). A replicate with zero weight raises
    # (the cell is then invalid, unusable_trial_rule)
def ratio_interval(numerator: np.ndarray, denominator: np.ndarray, usable: np.ndarray, counts: np.ndarray, *,
                   quantiles: Sequence[float], method: str) -> tuple[float, float, float, bool]
    # mean(numerator) / mean(denominator), the percentile interval of the replicate ratios, and whether every
    # replicate denominator is positive (if not, the interval is None and the cell does not recover)
def cost_bound(row: PairedRow, subject_cells: int, config: Mapping) -> float
    # delta_true_mean - z * delta_true_se, z = NormalDist().inv_cdf(1 - cost_family_alpha / subject_cells)
def run_part_a1(config: Mapping, *, seed: int, design: str, rules: Sequence[str] = RULES,
                planted: Sequence[str] = (), reporting_shift: str | None = None,
                cells: Sequence[Cell] | None = None, trials: int | None = None) -> tuple[list[ArmRow], list[PairedRow]]
def run_part_a2(config: Mapping, *, seed: int, design: str, rules: Sequence[str] = RULES,
                planted: Sequence[str] = (), leak_fraction: float = 0.0, heldout_shift: float = 0.0,
                cells: Sequence[Cell] | None = None, trials: int | None = None
                ) -> tuple[list[SplitRuleRow], list[DiagnosticRow], list[SumGapRow]]
def planted_level(kind: str, balance_level: np.ndarray, reference_best: np.ndarray,
                  reference_worst: np.ndarray, coins: np.ndarray) -> np.ndarray
    # "TRUTH_MIX": reference_best (the lexicographic reference-optimal level) where coins, else balance_level
    # "REFERENCE_WORST_MIX": reference_worst (the selections with the largest reference (M, T)) where coins, else balance_level
    # "RANDOM_MIX": all-True where coins, else balance_level;  "IDENTICAL": balance_level
    # coins = default_rng([seed, geometry_index, stream_planted_coins]).random(trials) < planted_probability
```

A1 per trial: point = `weighted_values(obs, plays, ones)`; worlds = `weighted_values(obs,
plays, world_counts)`; reference = latent. Coefficients = `quantize(values, normalizer, Q)`;
targets = `quantize(minimum, normalizer, Q)`. Reference arms through `extra_levels`:
`BALANCE_FIRST` (first True of BALANCE's level), `ORACLE_SHRINKAGE` (BALANCE level on shrunk
values; its `reported_own_m` is the shrunk-scale `M`, filled by the caller), `RANDOM_SET`
(all True). Paired differences use every usable trial, with zeros where the level sets are
identical; `delta_rep = reported_point_m(rule) - reported_point_m(BALANCE)`.
`valid = discarded_world_trial_share <= maximum_discarded_world_trial_share`;
`compared = valid and informative_trials >= minimum_informative_trials`;
`reporting_compared = valid and reporting_nonzero_trials >= reporting_minimum_nonzero_trials`,
a trial counting when the rule's `own_nonzero` or `reference_nonzero` is true.
`reporting_shift` (planted tests only) gives `TRUTH_MIX` an own statistic so that the
reporting rule can be planted: `"PLUS"` and `"MINUS"` set it to its true `M` plus or minus
`planted_reporting_shift_margin_multiple * true_shortfall_margin`, plus a `planted_array_sd`
normal draw from `stream_planted_noise`; `"ZERO"` sets it to 0 and is run on cells whose minima
are 0, where every true shortfall is 0 too.

A2 per trial and direction `d in {0, 1}`: selecting half `H_d`, other half `H_{1-d}`; point
weights = indicator of `H_d`; world weights = `half_world_counts[t, d]` scattered onto the
ascending match indices of `H_d`; held-out values from the indicator of `H_{1-d}`; truth =
latent. Two `evaluate_rules` calls per direction (reference = held-out, reference = truth)
sharing the same levels. A trial is usable for a rule when both directions are; its value is
the mean of the two directions; it is informative when either direction is.
`heldout_excess = heldout_gap - true_optimism_half`; `tracking = delta_out - delta_true` per
trial. Sum gaps (BALANCE): `sum_gap_true = mean_r(point_sums - true reference_sums)`,
`sum_gap_heldout = mean_r(point_sums - held-out reference_sums)`. `leak_fraction > 0` (tests
only) moves that fraction of the other half's matches into the selecting half's weights without
removing them from the other half: a deliberately broken check for the planted-failure test.
`heldout_shift > 0` (tests only) adds that many normalised units to every held-out `M` of the
planted pseudo-rule's selections and of no other arm's: a held-out cost that the truth does not
have.

### 2.5 Memory and cost (estimates, UNVERIFIED until the rehearsal reports them)

| Block | Largest array | Estimate |
|---|---|---|
| A1 `GROUPED_14C10`, 200 worlds | batch 100 trials × 200 × 200 × 3 × 8 B = 96 MB | 20–40 s per (noise, exposure, level) at 4,000 trials |
| A1 `M05_8C3`, 200 worlds | batch 500 × 200 × 56 × 2 × 8 B = 90 MB | 3–6 s |
| A1 + A2 total | | under 60 min, one process, under 1.5 GB |
| Part B enumeration, 40 worlds | batch 100 directions × 40 × S × 3 × 8 B, S = `expected_selection_count` (at most the player-set count) | under 10 min |
| Structure planted check, both snapshots | as Part B, three pseudo-rules and BALANCE, no worlds read except for the used gate | under 10 min |
| Solver audit, `solver_audit_expected_items` solves at 12 worlds | | 5–30 min; `solver_time_limit` each |

No process pool. The rehearsal prints measured times to stderr; the implementer reports them.

### 2.6 Real split (Part B)

```python
@dataclass(frozen=True)
class SelectionSpace:
    incidence: np.ndarray          # float64 (S, N) over candidates sorted by player_id, requirement-bearing slots only
    assignment_count: int          # ordered feasible assignments (snapshots[i].expected_feasible_assignments)
    player_set_count: int          # distinct full player sets (expected_player_sets)
    selection_count: int           # S (expected_selection_count)
    reference_level: np.ndarray    # bool (S,): selections with the largest sum of prior minutes

def enumerate_selections(candidates: Sequence[Candidate], requirements: Sequence[TacticalRequirement],
                         formation: Formation) -> SelectionSpace
    # depth-first over formation.slots in order; eligibility as in section 1; one player per slot.
    # Raises NotImplementedError unless every requirement in force applies to the same slot set.

@dataclass(frozen=True)
class SplitInputs:
    scenario_id: str
    source: str                    # "CORPUS" | "SYNTHETIC" | "SYNTHETIC_ON_STRUCTURE"
    protocol_hash: str | None      # set by load_split_inputs for CORPUS; None otherwise
    game_ids: np.ndarray           # int64 (G,), ascending (the order shared_match_weights uses)
    date_order: np.ndarray         # int64 (G,): positions of game_ids sorted by (date, game_id)
    home: np.ndarray               # bool (G,): the team was the home side (matches.home_team_id); structure only
    numerators: np.ndarray         # float64 (N, R, G); 0.0 where the player had no row
    minutes: np.ndarray            # float64 (N, G) reconstructed minutes; every metric's denominator, asserted
    needed: np.ndarray             # bool (N,): eligible at a slot where a requirement in force applies (False for GK)
    minima: np.ndarray             # float64 (R,): snapshot requirement minima
    normalizers: np.ndarray        # float64 (R,): the same minima (shipped policy)
    requirement_ids: tuple[str, ...]
    space: SelectionSpace
    structure: dict                # counts only: prior_team_matches, candidates, omitted, assignments, player_sets,
                                   # selections, min/max outfield appearances (positive minutes); plus dataset_hash,
                                   # xt_version, feature_fingerprints

def read_frames(config: Mapping) -> dict[str, pd.DataFrame]
    # assert_may_host(provider); the four files of data_paths, read whole (data_read_rule)
def load_split_inputs(snapshot_spec: Mapping, config: Mapping, *, frames: Mapping[str, pd.DataFrame],
                      protocol_hash: str) -> SplitInputs
    # THE loader of real numerators. Raises PermissionError unless protocol_hash == lf_sha256(EXPERIMENT /
    # "preregistration.md") of the registered file. build_snapshot(**frames, match_id=, worlds=0, team_id=);
    # decision_inputs(snap, formation); prior_frames; fit_prior_xt; rate_components; source="CORPUS";
    # stops (ValueError) if any expected_* count of snapshot_spec differs, or a key is null
def synthetic_split_inputs(*, seed: int, noise_sd: float, drift: float = 0.0, matches: int,
                           groups: Sequence[tuple[int, int]], counts: Sequence[int]) -> tuple[SplitInputs, np.ndarray]
    # test and rehearsal corpus with known latent rates (second value, (N, R)); sentinel player ids >= 9_000_001
    # never leave the function; minutes per appearance drawn as starts and substitute spells
def synthetic_on_structure(inputs: SplitInputs, *, seed: Sequence[int], noise_sd: float, config: Mapping
                           ) -> tuple[SplitInputs, np.ndarray]
    # keeps game_ids, date_order, home, minutes, needed, space, minima, normalizers; REPLACES numerators with
    # minutes / 90 * rate, rate[i, r, g] = latent[i, r] * (1 + (noise_sd / latent_mean) * sqrt(G) * z[g, i, r]);
    # latent[i, r] ~ Normal(mu_r, (latent_sd / latent_mean) * mu_r), mu_r = minima[r] / (requirement-bearing slots);
    # z = sqrt(rho) * shared + sqrt(1 - rho) * idiosyncratic standard normals, rho = base_shared_fraction;
    # never reads inputs.numerators (a test sets them to NaN); source="SYNTHETIC_ON_STRUCTURE", protocol_hash=None
def weighted_rates(inputs: SplitInputs, weights: np.ndarray) -> tuple[np.ndarray, np.ndarray]
    # weights (K, G) -> values (K, N, R) = numerators @ w / minutes @ w * 90 (NaN where a candidate's
    # denominator is zero, and for candidates not needed); valid bool (K,) = world_valid over the needed candidates
def split_masks(inputs: SplitInputs, config: Mapping, *, seed: int, snapshot_index: int,
                random_splits: int) -> list[tuple[str, int, np.ndarray]]
    # (family, split_index, bool mask of half A over game_ids), families in split_families order.
    # RANDOM r: perm = default_rng([seed, real_split_stream_offset + snapshot_index, r]).permutation(G); A = perm[: G // 2]
    # ALTERNATING: A = date_order[0::2]; CHRONOLOGICAL: A = date_order[: G // 2]
def half_world_counts(mask: np.ndarray, *, worlds: int, config: Mapping, seed: int, snapshot_index: int,
                      split_index: int, direction: int) -> np.ndarray
    # int64 (worlds, G): default_rng([seed, real_world_stream_offset + snapshot_index, split_index, direction])
    # .multinomial(h, np.full(h, 1 / h), size=worlds) scattered onto the ascending positions of the selecting half

@dataclass(frozen=True)
class DirectionRow:     # in memory only; never serialised
    family: str; split_index: int; direction: int; multiplier: float; tier: int; rule: str
    exposure_used: bool; used: bool; informative: bool; level_size: int
    reported_point_m: float; reported_own_m: float | None; heldout_m: float
    delta_gap: float | None; delta_out: float | None            # 0.0 where the level equals BALANCE's
    sums_in: tuple[float, ...]; sums_out: tuple[float, ...]     # normalised requirement sums, level mean, per requirement
    home_in_half: int                                           # home matches in the selecting half

def evaluate_snapshot(inputs: SplitInputs, config: Mapping, *, seed: int, snapshot_index: int,
                      random_splits: int, rules: Sequence[str] = RULES,
                      extra: Sequence[str] = ()) -> list[DirectionRow]
    # THE accessor to half-split outcomes. For source "CORPUS" it raises PermissionError unless
    # inputs.protocol_hash == lf_sha256(EXPERIMENT / "preregistration.md"). Tiers: decision_tiers only.

@dataclass(frozen=True)
class SplitBlock:       # one per (snapshot, family, multiplier, tier, rule)
    scenario_id: str; family: str; multiplier: float; tier: int; rule: str
    directions: int; used: int; informative: int; level_size_mean: float
    reported_point_mean: float; reported_own_mean: float | None; heldout_mean: float
    gap_mean: float; gap_quantiles: tuple[float, ...]
    delta_gap_mean: float | None; delta_gap_negative_share: float | None; delta_gap_positive_share: float | None
    delta_out_mean: float | None; delta_out_negative_share: float | None; delta_out_positive_share: float | None
    sums_in_mean: tuple[float, ...]; sums_out_mean: tuple[float, ...]
def summarize_directions(rows: Sequence[DirectionRow], config: Mapping, *, scenario_id: str) -> list[SplitBlock]
    # split_mean_denominator: delta_*_mean over every used direction, zeros where identical; shares over
    # informative used directions; delta_* are None for BALANCE and REFERENCE_PRIOR_MINUTES
def structure_planted_check(inputs: Sequence[SplitInputs], config: Mapping, *, seed: int) -> dict
    # both snapshots together. For snapshot i: synthetic_on_structure(inputs[i], seed=[seed,
    # structure_check_stream_offset + i]) at planted_split_noise_sd; evaluate_snapshot with rules=("BALANCE",),
    # extra = the keys of planted_split_arms, planted_split_random_splits splits, the RANDOM family, the frozen gates.
    # For each pseudo-rule: decide_split(its eight blocks, diagnostic_valid=True, config,
    # expected_blocks=split_expected_blocks). Returns {"tokens": {arm: token}, "reference_gap_sum": float,
    # "passed": bool}; passed iff every token equals planted_split_arms[arm] and the REFERENCE_PRIOR_MINUTES gap
    # sums to exactly 0 over the splits whose two directions are both used. diagnostic_valid=True because the
    # check tests the split rule, not A2
def solver_audit(inputs: SplitInputs, snapshot, config: Mapping, *, seed: int, snapshot_index: int) -> dict
    # {"items": int, "audited": int, "unused_direction": int, "certified": int, "status": "ALL_CERTIFIED_MATCH"}
    # raises PermissionError for CORPUS inputs without the committed hash (as evaluate_snapshot);
    # SolverAuditMismatch (RuntimeError) on the first certified item that disagrees;
    # SolverAuditIncomplete (RuntimeError) when audited is 0 or certified / audited < solver_audit_minimum_certified_share
```

Rules for `evaluate_snapshot`: for each split and direction, half values and world values by
`weighted_rates`; `exposure_used` = every needed candidate has positive minutes in both
halves; `used = exposure_used and W_used(tier) >= ceil(minimum_used_world_share * tier)` for an
arm that reads worlds and `used = exposure_used` for an arm that reads none (BALANCE,
`REFERENCE_PRIOR_MINUTES`, the pseudo-rules); a rule's paired row with BALANCE uses the rule's
flag; coefficients by
`quantize(values, normalizers, Q)` with the columns of candidates not needed set to 0 (they sit
in no requirement-bearing slot; assert `incidence[:, ~needed].sum() == 0`); targets by
`quantize(multiplier * minima, normalizers, Q)`; `evaluate_rules` with reference = held-out
half and `extra_levels={"REFERENCE_PRIOR_MINUTES": reference_level, ...}`. Sums are computed
once per direction; only the targets change with the multiplier. Coverage (structure only):
home matches in half A for the two deterministic splits, and their distribution over the
random splits.

**`solver_audit` items.** The splits in `solver_audit_random_splits` plus the alternating split
when `solver_audit_include_alternating`, both directions, `solver_audit_multipliers`,
`solver_audit_worlds`, the six rules: `solver_audit_expected_items` items over both snapshots
when every audited direction is used. A direction that is not used (exposure) is not audited
and is counted (`unused_direction`). For each audited item:

- Candidates: `decision_inputs(snap, formation, minimums={r: multiplier * minimum_r})` (the
  normalisers stay the snapshot minima), each with
  `dataclasses.replace(c, values={**c.values, **selecting_half_values})`; goalkeepers keep
  `None`.
- Worlds: `{world_id: {player_id: {metric: value or None}}}` for every candidate and the three
  requirements in force, world ids `0..W-1` from `half_world_counts`, `None` where the
  candidate has no minutes in that world.
- `_risk_call(rule, k, candidates, requirements, worlds, config, *, seed)` calls
  `risk.declared_risk_selection(candidates, requirements, config["formation"],
  rule=solver_rule_map[rule], tail_count=(1 if rule == "WORST_WORLD" else k if
  solver_rule_map[rule] == "TAIL" else None), worlds=worlds, world_count=len(worlds),
  world_seed=seed, bootstrap_version=solver_audit_bootstrap_version, seed=solver_seed,
  quantization=quantization, analyze_ties=solver_audit_analyze_ties,
  deadline=time.monotonic() + solver_time_limit)`. BALANCE calls `solve_xi(candidates,
  requirements, formation, seed=solver_seed, time_limit=solver_time_limit,
  quantization=quantization, analyze_ties=False)`.
- `_risk_world_pairs(result) -> dict[int, tuple[int, int]]` =
  `{w.world_id: (w.selected.maximum_shortfall, w.selected.total_shortfall) for w in
  result.world_losses}`.
- Certified: `result.status == "CERTIFIED" and result.certificate.completeness == "EXACT"`
  (BALANCE: `solution_status == "OPTIMAL"`).
- A certified item passes iff (a) the player ids at the requirement-bearing slots of
  `result.lineup` (BALANCE: `assignments`) form a selection of the enumerated level set;
  (b) `_risk_world_pairs(result)` equals the enumerated pairs of that selection in every used
  world; (c) `certificate.used_world_ids` and the ids of `certificate.discarded_worlds` equal
  the enumeration's used and discarded worlds; (d) for a tail rule `result.tail_sum` equals the
  enumerated optimum `(own_m_sum, own_t_sum)`, and for the regret each `world_least` equals the
  enumerated least pair of its world; (e) `result.tail_count` is the `k` passed (1 for
  `WORST_WORLD`, `None` for the regret). BALANCE passes iff (a) and
  `tuple(round(v * Q) for v in objective_vector)` equals the enumerated point pair at the
  optimum. A world discarded by the one discard rule is compared through (c), never skipped.

`analyze_ties` stays false: the membership solves would add one solve per candidate to every
item, and (a) already ties the returned XI to the enumerated level set.

### 2.7 Decisions (pure functions; inputs are plain rows, outputs are tokens)

```python
COMPONENT_SELECTION = ("COSTS_TRUE_SHORTFALL", "INCONCLUSIVE", "LESS_OPTIMISTIC_COST_BOUNDED", "NOT_ESTABLISHED")
COMPONENT_REPORTING = ("NOT_APPLICABLE", "INCONCLUSIVE", "OWN_STATISTIC_NOT_OPTIMISTIC", "NOT_ESTABLISHED")
COMPONENT_SPLIT = ("INCONCLUSIVE", "DIAGNOSTIC_UNVALIDATED", "HELD_OUT_SHORTFALL_LARGER", "HELD_OUT_GAP_SMALLER", "NOT_ESTABLISHED")
# each equal to config["component_vocabulary"]; subject and experiment vocabularies are read from config

def minimum_count(fraction: Sequence[int], cells: int) -> int      # ceil(numerator * cells / denominator), integer arithmetic
def shows_cost(row: PairedRow, subject_cells: int, config: Mapping) -> bool   # row.valid and cost_bound(...) > margin
def decide_selection(rows: Sequence[PairedRow], config: Mapping, *, subject_cells: int) -> str
def decide_reporting(rows: Sequence[PairedRow], rule: str, config: Mapping) -> str   # NOT_APPLICABLE for MINIMAX_REGRET
def interval_sign(low: float, high: float) -> int                  # +1 if low > 0, -1 if high < 0, else 0
def cell_agreement(row: DiagnosticRow) -> str
def cell_tracking(row: DiagnosticRow, config: Mapping) -> str      # closed [-tol, tol]: TRACKS, wholly outside: DIVERGES
def decide_diagnostic(rows: Sequence[DiagnosticRow], config: Mapping) -> bool
def decide_split(blocks: Sequence[SplitBlock], diagnostic_valid: bool, config: Mapping, *,
                 expected_blocks: int, minimum_used: int | None = None, minimum_informative: int | None = None) -> str
    # the gates default to minimum_used_directions and minimum_informative_directions; the rehearsal passes its own
def aggregate_selection(tokens: Sequence[str]) -> str              # cost first: COSTS | INCONCLUSIVE | POSITIVE | NOT_ESTABLISHED
def aggregate_split(tokens: Sequence[str]) -> str                  # cost first: LARGER | INCONCLUSIVE | UNVALIDATED | SMALLER | NOT_ESTABLISHED
def decide_risk_rule(selection: str, split: str) -> str            # the protocol's six-row table
def decide_risk_report(tokens: Sequence[str]) -> str
def decide_split_sample_diagnostic(rows: Sequence[SumGapRow], config: Mapping) -> str
def decide_experiment(risk_rule_tokens: Mapping[str, str]) -> str
def decide_all(paired: Sequence[PairedRow], diagnostic: Sequence[DiagnosticRow], sum_gaps: Sequence[SumGapRow],
               blocks: Sequence[SplitBlock], cells: Sequence[Cell], config: Mapping) -> dict
    # {"components": {rule: {str(tier): {"selection", "reporting", "diagnostic_valid", "split_sample",
    #                                    "compared_cells", "cost_cells", "subject_cells",
    #                                    "true_shortfall_lower_in_all_compared_cells"}}},
    #  "sensitivity": {rule: {"cost_cells": int, "valid_cells": int}},   # SENSITIVITY + STRESS, reported, changes no token
    #  "verdicts": {claim_id: {"token": str, "reason": str}},          # claim_id = "E-13/" + subject, six of them
    #  "verdict": str}
```

Each function implements exactly the protocol table of the same name, rows in order.
`decide_selection` and `decide_reporting` receive one component's PRIMARY rows;
`subject_cells` is the number of valid PRIMARY rows over all components of the subject (TAIL:
three rules × two tiers). `decide_split` receives the component's `RANDOM`-family blocks for
both snapshots and every multiplier and returns `INCONCLUSIVE` if it receives fewer than
`expected_blocks`. `cost_cells` in `sensitivity` counts the rule's valid SENSITIVITY and STRESS
cells that show a cost with `subject_cells` = the number of those valid cells
(`cost_multiplicity_rule`). `reason` is one sentence built from a fixed template per token
(counts only, no player).

### 2.8 Planted arms (used only when `planted` / `extra` is passed; never in the frozen A1, A2 or Part B tables)

`run_part_a1(config, seed=s, design="FROZEN", rules=("BALANCE",), planted=("TRUTH_MIX",
"RANDOM_MIX", "IDENTICAL"), cells=PRIMARY cells of planted_geometries at planted_tiers,
trials=planted_trials)` yields `PairedRow`s for the three pseudo-rules exactly as for a rule.
The planted target of `TRUTH_MIX` is an identity: on a coined trial its level is the true
lexicographic optimum, whose true `M` is the smallest, so its `delta_true` is minus BALANCE's
true regret there and zero elsewhere; the test checks the identity to
`planted_identity_tolerance` and calls it that. `evaluate_snapshot(..., rules=("BALANCE",),
extra=(...))` does the same on a split, the reference being the held-out half
(`REFERENCE_WORST_MIX` takes the held-out-pessimal level), with one coin per direction from
`default_rng([seed, structure_check_stream_offset + snapshot_index,
stream_planted_coins]).random(directions) < planted_probability` (in `split_masks` order, both
directions of a split in turn).

## 3. `experiments/run_risk_selection.py`

Docstring: "Execute E-13's frozen plan; writes an aggregate research artifact only."

```python
EXPERIMENT = ROOT / "experiments/preregistered/E-13-declared-risk-selection"
def protocol_commit() -> str
    # read-only git: `git log --diff-filter=A --format=%H -- <EXPERIMENT>/preregistration.md` (last line = first add).
    # Raises if empty, or if `git diff --quiet HEAD -- <path>` is non-zero for any of protocol_files or any
    # source_paths entry (the committed blobs are what runs). Never a literal.
def provenance(config: Mapping, *, rehearsal: bool) -> dict
def run_oracle_gate(config: Mapping) -> dict
    # refuses unless os.name == "posix" (risk_solver_oracle_platform); subprocess:
    # [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--junitxml", <tmp>, *risk_solver_oracle_tests];
    # reads tests, skipped, failures and errors from the JUnit file (passed = tests - skipped - failures - errors)
    # and raises unless they equal risk_solver_oracle_expected exactly. Returns {"tests": [...], "lf_sha256": {path: digest}, "counts": {...}}:
    # no elapsed time and no stdout line
def run(config: Mapping, *, rehearsal: bool) -> dict
def encode_result(result: Mapping, *, decimals: int) -> str
    # deterministic JSON: indent 2 for mappings and for lists of containers; a list of scalars on ONE line;
    # floats rounded to `decimals`; allow_nan=False (NaN anywhere raises); LF line endings; trailing newline
def verify_against(result: Mapping, reference_path: Path, excluded: Sequence[str]) -> list[str]
def main(argv: Sequence[str] | None = None) -> int
```

| Flag | Meaning |
|---|---|
| `--execute-frozen` | frozen config, frozen seeds; requires `--out`; calls `protocol_commit()` and `run_oracle_gate()` |
| `--rehearsal` | `seed := rehearsal_seed`, `design="REHEARSAL"` (`rehearsal_design`: its latent SD, noise grid, minimum levels and trial divisor), Part B on two `synthetic_split_inputs` "snapshots" at `rehearsal_design["synthetic_corpus_noise_sd"]` with `rehearsal_design["random_splits"]` and its own gates, the structure check on them, oracle gate and solver audit skipped, result carries `"rehearsal": true`; refuses an `--out` inside the repository |
| `--out PATH` | written by the runner with `Path.write_bytes(text.encode("utf-8"))` (never shell redirection); refuses to overwrite an existing file |
| `--verify-against PATH` | after the run, compare with an earlier artifact ignoring `determinism_excluded_keys`; exit 1 and list differing key paths if any |

Exactly one of `--execute-frozen` / `--rehearsal` is required. `run` follows the protocol's
"Frozen procedure" order: hashes, bridge, A1, A2, `read_frames` and `load_split_inputs` for
both snapshots (with the protocol hash), the oracle gate, `structure_planted_check`,
`solver_audit` for each snapshot, `evaluate_snapshot` for each snapshot, decisions, write.
Nothing is written unless every step succeeded, the key walk of section 4 is clean, and
`len(encode_result(...).encode()) <= results_maximum_bytes`.

Config keys whose reader is not named elsewhere in this file (the no-dead-key test covers all):

| Key | Read by | For |
|---|---|---|
| `experiment_id`, `registry_experiment_id`, `tier`, `experiment_directory`, `protocol_files`, `draft_dir` | runner and registry tests | the contract fields; `EXPERIMENT` must equal `ROOT / experiment_directory` |
| `pipeline_spec_sha256` | runner | must equal `lf_sha256(EXPERIMENT / "PIPELINE.md")`, asserted before the bridge |
| `verified_by_root_before_registration`, `counted_by_root_before_registration`, `counted_by_root_rule`, `root_rulings_applied`, `root_rulings_rule` | `test_config_contract` | no `null` remains in a counted key; every T1 to T7 listed |
| `rules`, `modes`, `reference_arms`, `bridge_arms`, `pseudo_rules` | module import check | must equal `RULES`, `MODES` and the arm names of 2.3, 2.4, 2.8 |
| `exposure_unit`, `exposure_subset_rule`, `minimum_level_rule`, `encoding_base_rule`, `standard_error_rule`, `unusable_trial_rule`, `cost_multiplicity_rule`, `split_mean_denominator`, `data_read_rule`, `diagnostic_recovery_interval` | `test_config_contract` | each rule sentence is asserted, and the value is implemented (a rule is read by assertion, not by a branch); the derived counts and levels equal the rules (exposure subsets, spanning profiles, minimum levels to two decimals) |
| `precision_target_sd`, `precision_target_half_width_fraction` | `test_config_contract`, writer | `1.96 * precision_target_sd / sqrt(trials) <= fraction * true_shortfall_margin` for every geometry; realised half-widths written |
| `provider`, `league_list`, `team_id`, `formation` | `read_frames`, `load_split_inputs` | `assert_may_host(provider)`; exactly one league, the `competition=<league>` directory; `build_snapshot(team_id=...)`; `decision_inputs(snap, formation)` |
| `snapshots[*]`, `expected_active_requirements` | `load_split_inputs` | structural stops, per snapshot |
| `split_families` | `split_masks` | the families produced, in this order |
| `alternating_split_index`, `chronological_split_index` | `split_masks`, `half_world_counts` | the `split_index` of the two deterministic splits (seeds of their worlds) |
| `token_scope` | registry tests | the scope sentence of every `risk_rule` record names each condition; its key references resolve to config keys |
| `solver_audit_*`, `solver_rule_map`, `solver_seed`, `solver_time_limit` | `solver_audit` | item list, adapters, certification share |
| `risk_solver_module`, `risk_solver_oracle_tests`, `risk_solver_oracle_expected`, `risk_solver_oracle_platform` | `run_oracle_gate`, `solver_audit` | the lazy import's module name; the gate |
| `bridge_columns` | `m05_bridge` | which arm produces each column |
| `planted_*` | the planted gate (section 9) | every planted requirement and seed |
| `rehearsal_design` | runner, rehearsal only | the rehearsal's cells, trials, splits and gates |
| `float_decimals` | `encode_result` | rounding of every float in the artifact |
| `results_allowed_identifiers` | writer | the only corpus identifiers allowed in the artifact |
| `stream_*`, `real_*_stream_offset`, `structure_check_stream_offset` | generators | third (or second) element of each seed sequence |
| `component_vocabulary`, `verdict_vocabulary`, `experiment_verdict_vocabulary`, `subject_arms`, `registry_*` | `decide_all` (vocabularies and subject map), registry tests (the rest) | tokens must come from the vocabulary; the records built from config are section 10's |
| `risk_report_after_run`, `split_sample_after_run` | registry tests | asserted text; read by the root's results commit |

## 4. `results.json` shape (aggregate only)

Tables are `{"columns": [...], "rows": [[...], ...]}`; categorical columns are small
integers indexing `vocabularies`; one row per line.

| Key | Content |
|---|---|
| `experiment`, `version`, `tier` | `"E-13"`, `config["version"]`, `"PUBLIC"` |
| `provenance` | `protocol_commit`, `protocol_hashes{file: sha}` for the three protocol files, `config_hash`, `source_hashes{posix path: sha}`, `source_hash_policy: "lf-sha256"`, `manifest_digests` (the raw-JSON digests of `manifest_path`: the data pin), `parquet_hashes{posix path: sha}` (recorded, not a pin: they depend on the writer version), `packages{numpy, pandas, pyarrow, ortools}`, `python`, `platform`, `config` (verbatim), `snapshots[{scenario_id, dataset_hash, xt_version, feature_fingerprints, structure}]`, `oracle_gate` (counts and file hashes), `providers: ["pappalardo"]`, `data_license`, `reuse_disclosure` |
| `verdicts` | `{claim_id: {"token", "reason"}}` for the six claims |
| `verdict`, `interpretation`, `uncertainty_limit`, `product_effect` | strings; `product_effect` = "Labels only: no default, coefficient, gate or solver output changes" |
| `decisions` | `components` and `sensitivity` from `decide_all` |
| `vocabularies` | `arms`, `rules`, `blocks`, `variants`, `geometries`, `minimum_levels`, `exposure_profiles`, `families`, `agreements`, `trackings`, `scenarios` |
| `bridge_m05` | `rows` (noise, column, arm, engine value, M-05 value), `maximum_absolute_difference`, `tolerance`, `passed` |
| `part_a1.cells` | table of `Cell` fields |
| `part_a1.arms` | table of `ArmRow`; PRIMARY, BEYOND_MENU and STRESS cells |
| `part_a1.paired` | table of `PairedRow`; all A1 cells, with each cell's realised half-widths |
| `part_a2.rules`, `part_a2.diagnostic`, `part_a2.sum_gap` | tables of `SplitRuleRow`, `DiagnosticRow`, `SumGapRow` |
| `part_b.coverage` | per snapshot: `structure`, used / unused direction counts per family and tier, minimum and mean `W_used`, home matches per half of each deterministic split and their quantiles over the random splits |
| `part_b.structure_planted_check` | the tokens of the three pseudo-rules, `reference_gap_sum`, `passed` |
| `part_b.blocks` | table of `SplitBlock` for the `RANDOM` family (without the two sum tuples) |
| `part_b.deterministic_blocks` | table for `ALTERNATING`, `CHRONOLOGICAL`: `scenario, family, multiplier, tier, rule, used, reported_point_mean, heldout_mean, gap_mean` |
| `part_b.requirement_sums` | table: `scenario, multiplier, rule, requirement, sums_in_mean, sums_out_mean` (`RANDOM` family, first decision tier) |
| `part_b.solver_audit` | `items`, `audited`, `unused_direction`, `certified`, `status` per snapshot |

Forbidden in the artifact: any key or column named `player_id`, `name`, `players`,
`assignments`; any per-player value; any selected XI; any encoding `E` or `BIG`; any
identifier from the corpus other than those of `results_allowed_identifiers` inside `config`
(`scenario_id`, the two public `match_id`s and `team_id`, which names the club the protocol
names); any wall-clock field. Before writing, the runner walks every key with
`banned_key_paths(result, parts=BANNED_KEY_PARTS)` and the forbidden names, and refuses on a
hit. Size: at most `results_maximum_bytes` (480,000; the repository limit is 512 KB). Estimate
from the row counts: 320–420 KB.

## 5. Hash discipline

| Object | Function | Why |
|---|---|---|
| the three `protocol_files` | `digests.lf_sha256(path)` (CRLF → LF, then SHA-256) | `core.autocrlf=true` on Windows checkouts; the recorded hash must verify on any platform (lifecycle T1). `pipeline_spec_sha256` pins `PIPELINE.md` inside `config.json` |
| every `source_paths` entry | `lf_sha256` | same; keys are POSIX paths relative to the repo root |
| data pin | the per-file digests inside `manifest_path` (raw provider JSON), copied verbatim | Parquet digests depend on the pandas version and the cache was re-ingested during reconnaissance (critique H40) |
| every `data_paths` entry (Parquet) | byte-exact `hashlib.file_digest(f, "sha256")` | binary; never normalised; recorded, not a pin |
| protocol commit | `protocol_commit()` | derived from git; the working protocol files and sources are the committed blobs |
| snapshot data | `snapshot.provenance["dataset_hash"]`, `["xt_version"]`, `["feature_fingerprints"]` | the shipped content hashes of the prior rows, reproduced because the files are read whole (`data_read_rule`) |
| oracle | `lf_sha256` of each `risk_solver_oracle_tests` file | which oracle vouched for the solver: the brute-force file and the test file |
| accessor | `load_split_inputs(..., protocol_hash=...)`, checked again by `evaluate_snapshot` and `solver_audit` | real numerators are unreachable without the committed protocol's hash |

A missing `source_paths` file is an execution failure, not a skipped entry.

## 6. Test suite (all synthetic unless marked `slow`)

Oracle rule: the reference in `tests/test_risk_selection.py` is written from the protocol
with `itertools`, `fractions.Fraction` and Python `int`. It compares world losses as tuples
`(M, T)` and sums them componentwise; it never forms an encoding and imports nothing from
`risk_selection` except the function under test. Every row below is a required test function.

### 6.1 Engine

| Test | Asserts |
|---|---|
| `test_rounding_matches_shipped_policy` | `quantize` equals `solver._q` on 10,000 seeded values plus exact `.5` cases built from dyadic rationals |
| `test_rules_equal_independent_oracle` | 60 seeded tiny instances (N ≤ 6, S ≤ 20, W ≤ 7, R ≤ 3, integer coefficients, some negative): level sets, `tail_count`, `own_m_sum`, `own_t_sum`, `world_least` of all six rules equal the tuple oracle |
| `test_oracle_instances_are_not_vacuous` | across the 60: some level set has size > 1 and some size 1; some rule's level differs from BALANCE's and some equals it; some instance where the tail is decided by `T` at equal `M`; some where summed `T` over a tail exceeds the largest single-world `T` (the case a too-small `BIG` gets wrong); some regret instance where a world's regret has `M` above the least and `T` below it |
| `test_encoding_base_is_only_a_device` | doubling `BIG` changes no level set and no decoded value; a `BIG` equal to the largest single total (too small) does change an oracle instance, proving the test can see the defect; `encoding_base` is at least 2 when every target is 0 |
| `test_no_encoding_leaves_the_engine` | no field of `RuleOutcome`, `Evaluation` or any row dataclass holds a value `>= BIG` of its instance; `asdict` of every row has no key containing `encod`, `big` or `base` |
| `test_single_world_equals_balance` | `W = 1` with the world equal to the point values: every rule's level set equals BALANCE's (ROOT 2.5 invariant), including a batch whose point `T` exceeds every world `T` |
| `test_worst_world_is_tail_one` | `WORST_WORLD` equals a `TAIL` with `k = 1`; `k == W_used` equals the sum over all used worlds |
| `test_regret_is_never_negative_and_zero_at_per_world_optimum` | |
| `test_discard_rule_is_the_shipped_one` | a candidate not needed (a goalkeeper, or one eligible only where no requirement applies) with no minutes in a world does not discard it; a needed candidate with none does; the values of a discarded world do not matter; `W_used < k` gives `usable=False` and an empty level |
| `test_world_order_candidate_order_selection_order_invariance` | permutations permute outputs only |
| `test_tiers_are_prefixes` | `evaluate_rules(tiers=(3, 5))[3]` equals a direct call with the first three worlds |
| `test_disappointment_is_integer_exact` | hand-built ties at `reference == reported` are not counted |

### 6.2 Synthetic generator, bridge, intervals

| Test | Asserts |
|---|---|
| `test_geometry_incidence_counts` | 56 and 200 selections; each row has 3 and 10 picks; group quotas hold |
| `test_draws_are_seed_deterministic_and_stream_independent` | same seed → identical arrays; changing `worlds` does not change `latent` or `idiosyncratic` |
| `test_exposure_counts_and_alignment` | every candidate plays exactly his count; `WIDE_ALIGNED` gives the largest count to the largest latent mean; `FULL` plays all |
| `test_noise_scale_matches_declaration` | 20,000 trials, `rho in {0, 0.5}`: the SD of (point value − latent) for an `n`-match candidate is `noise_sd * sqrt(G / n)` within 3 % |
| `test_shared_effect_is_shared` | with `rho = 1` two candidates with identical exposure have identical (value − latent) in every world; with `rho = 0` they do not |
| `test_worlds_are_coherent` | one count vector per world feeds every candidate and requirement (poisoning one candidate's counts fails the test) |
| `test_zero_noise_has_zero_optimism_and_identical_rules` | `noise_sd = 0`: every rule's level set equals the true-optimal level set; optimism and regret are exactly 0 |
| `test_m05_bridge_within_tolerance` | `m05_bridge(config)["passed"]`: each of the six columns of `bridge_columns`, from its arm, at the three noise levels, within `bridge_tolerance` of `run_optimizer_curse.run()` |
| `test_unusable_trials_are_excluded_from_the_pair` | a trial unusable for a rule leaves the rule's and its BALANCE pair's means, intervals and SE as if the trial were absent; the counts matrix is restricted, not refilled; a zero-weight replicate raises |
| `test_random_set_shows_optimism_is_cheap` | `RANDOM_SET` has mean `optimism_point <= 0` and a larger `true_m` than BALANCE in the `HIGH` cells: the reference arm behaves as the protocol says |
| `test_a2_halves_partition_matches` | halves are disjoint, exhaustive, equal-sized; worlds of direction `d` put zero weight outside half `d` |
| `test_a2_zero_noise_has_zero_gap` | `noise_sd = 0`: held-out gap, true optimism, excess, tracking and both sum gaps are exactly 0 |
| `test_a2_usable_and_informative_trials` | a trial with one unusable direction is excluded for that rule; a trial with one informative direction is informative; the informative count changes no token |
| `test_rehearsal_cells_are_disjoint_from_frozen_cells` | no rehearsal cell has the (latent SD, noise, minimum) of a frozen cell |

### 6.3 Split machinery

| Test | Asserts |
|---|---|
| `test_enumeration_equals_bruteforce_permutations` | tiny formations (≤ 5 slots, ≤ 7 candidates, random eligibility, a `None` value, a zero-minute player): assignment count and distinct selections equal an `itertools.permutations` reference |
| `test_enumeration_rejects_mixed_requirement_slots` | `NotImplementedError` |
| `test_reference_level_ignores_requirement_values` | changing every value leaves `reference_level` unchanged |
| `test_fixed_selection_gap_is_antisymmetric` | on the synthetic corpus the `REFERENCE_PRIOR_MINUTES` gap in direction 0 equals minus direction 1 exactly (integers) on every split; its used flag is the same for both directions: the planted null of the split statistic |
| `test_selected_gap_is_positive_under_planted_noise` | `planted_split_corpora` synthetic corpora at `planted_split_noise_sd`, largest multiplier, `planted_split_random_splits` splits: BALANCE's mean gap `> 0` in at least `planted_split_minimum_correct` corpora; at `noise_sd = 0` it is exactly 0 |
| `test_planted_drift_separates_families` | synthetic corpus with a linear time trend: the `CHRONOLOGICAL` fixed-selection one-direction gap is non-zero while its `RANDOM` sum over both directions stays 0 |
| `test_split_means_count_identical_directions_as_zero` | a block of used directions with a known share informative: `delta_*_mean` equals the informative mean times that share, and the shares are over informative directions only |
| `test_structure_planted_check_passes_and_reads_no_numerator` | on two synthetic corpora: `structure_planted_check` passes with eight blocks; setting `inputs.numerators` to NaN changes nothing |
| `test_split_masks_are_seeded_balanced_and_order_free` | `G // 2` matches in A; same seed → same masks; shuffling input rows changes nothing |
| `test_half_worlds_resample_only_the_selecting_half` | zero counts outside the half; row sums equal the half size |
| `test_part_b_discard_equals_world_losses` | on a synthetic corpus built as `Candidate`s with a goalkeeper who has a no-minute world: the used and discarded world ids of `weighted_rates` equal those `risk.world_losses` reports, and the pairs of a fixed lineup equal its pairs |
| `test_corpus_outcomes_need_the_protocol_hash` | `load_split_inputs` without, or with a wrong, `protocol_hash` raises `PermissionError` before any numerator is read; `evaluate_snapshot` and `solver_audit` on inputs relabelled `CORPUS` with a wrong hash raise |
| `test_no_identifier_leaves_the_split` | sentinel ids of the synthetic corpus appear nowhere in `summarize_directions` output or in the encoded rehearsal result |
| `test_solver_audit_detects_a_wrong_answer` | stubs of `declared_risk_selection` with the built result types: an XI outside the level set, a per-world pair off by one unit, a wrong used-world id, a wrong `tail_sum` or a wrong `world_least` → `SolverAuditMismatch`; a correct stub passes; `UNKNOWN`, `NOT_EVALUABLE` or a non-`EXACT` completeness counts as uncertified, and a certified share below the minimum, or no audited item, raises `SolverAuditIncomplete`; an item with a discarded world is compared |
| `test_solver_audit_calls_the_built_signature` | on a synthetic corpus, the real `declared_risk_selection` is called through `_risk_call` for every rule (keywords exactly those of section 1, `tail_count` 1 for `WORST_WORLD`) and every certified item passes |
| `test_snapshot_parity_full_sample` (`slow`) | both shipped snapshots: `weighted_rates(inputs, ones)` equals `snapshot.candidates[*].values` within 1e-12 relative, and their quantised coefficients are identical integers |
| `test_snapshot_parity_shipped_worlds` (`slow`) | `weighted_rates(inputs, shared_match_weights(...)[1])` reproduces `build_snapshot(worlds=40).worlds` within 1e-12 relative with identical quantised coefficients, and the same `None`s |
| `test_snapshot_structure_matches_config` (`slow`) | per snapshot: prior team matches, candidates, feasible assignments, player sets and selections equal its `expected_*` keys; three requirements in force on one common slot set; `dataset_hash` equals `build_snapshot`'s |

### 6.4 Decisions

| Test | Asserts |
|---|---|
| `test_selection_truth_table` | every combination of (valid?, compared count vs gate, cost bound vs margin, `delta_true_high` vs margin, `delta_optimism_high` vs 0) maps to exactly one token, equal to the protocol table; boundary values (`== margin`, `== 0`) included; a valid cell with a cost and fewer informative trials than the gate gives `COSTS_TRUE_SHORTFALL` (the cost row reads every valid cell) |
| `test_cost_bound_uses_the_subject_count` | the same row shows a cost at `subject_cells = 1` and not at 216 when its bound lies between the two |
| `test_reporting_truth_table` | same; `MINIMAX_REGRET` → `NOT_APPLICABLE` before any other row; an identically zero cell is not reporting-compared |
| `test_diagnostic_truth_table` | all 81 sign combinations of the four intervals map to one of `AGREES` / `CONTRADICTS` / `UNRESOLVED`; tracking intervals inside, straddling and wholly outside `[-tol, tol]`, bounds equal to `tol` inside; the two reviewers' cases (a resolved true cost with a held-out pair near zero; a held-out cost with no true cost) are invalid |
| `test_split_truth_table` | gate, diagnostic, larger, smaller, otherwise; rows 3 and 4 cannot both hold; fewer than `split_expected_blocks` blocks → `INCONCLUSIVE`; a block where the mean over used directions and the mean over informative directions fall on two sides of `margin_B` decides by the first |
| `test_aggregation_and_risk_rule_are_total` | every tuple of component tokens aggregates to one value; all 4 × 5 pairs of `(S, P)` map to one token of the vocabulary, equal to the six-row table; exhaustively over two-component subjects, no combination with a component cost gives a `LESS_OPTIMISTIC_*` token or `INCONCLUSIVE` (the four combinations of the first review included) |
| `test_risk_report_and_diagnostic_tokens_are_total` | including unresolved-cell gate, ratio bounds exactly at `1 ± tolerance` (inside), and a resolved cell with a non-positive replicate denominator (does not recover) |
| `test_identity_interval_is_not_evidence` | all-zero differences with zero informative trials → `INCONCLUSIVE`, never a pass on a `[0, 0]` interval (the E-08 lesson), for the selection and the reporting rule |

### 6.5 Runner (`tests/test_risk_selection_experiment.py`)

| Test | Asserts |
|---|---|
| `test_config_contract` | every key the code reads exists and every config key is read (no dead key); no `null` in the keys of `counted_by_root_before_registration`; an AST scan of `risk_selection.py` and the runner finds no numeric constant equal to the configured `seed`, `bootstrap_seed`, `rehearsal_seed`, `planted_seed`, `true_shortfall_margin`, `heldout_shortfall_margin`, `bridge_tolerance`, `minimum_used_directions` or `results_maximum_bytes`; cell counts equal the `expected_*` keys; exposure count vectors have length N and lie in `[2, G]` and follow `exposure_subset_rule`; minimum levels follow `minimum_level_rule`; `quantization` equals the shipped `QUANTIZATION`; `tail_counts` equal the ceilings of 0.10, 0.25, 0.50 of each tier; the structure check's gates are reachable (`2 * planted_split_random_splits >= minimum_used_directions`, `split_expected_blocks == 2 * len(requirement_multipliers)`) |
| `test_pipeline_hash_is_pinned` | `pipeline_spec_sha256 == lf_sha256(EXPERIMENT / "PIPELINE.md")`; a planted one-byte change is detected; a CRLF copy hashes equal |
| `test_protocol_names_only_config_keys` | every backticked token of `preregistration.md` matching `^[a-z][a-z0-9_]*$` is a key at any depth of `config.json` or a member of `PROTOCOL_TERMS`, kept in the test: the shipped names `build_snapshot`, `dataset_hash`, `decision_inputs`, `declared_risk_selection`, `fit_prior_xt`, `load_snapshot`, `may_gate`, `solve_xi`, `world_losses`, `tail_count`, `test_madrid_worlds_are_the_main_solve_s`, `itertools`, `null`, `true`; this file's `expand_cells`; the protocol's quantities `delta_gap`, `delta_out`, `delta_rep`, `margin`, `optimism_own`, `reported_own`, `reported_point`, `sum_gap_true`, `z_m`; and the symbols `c`, `e`, `i`, `k`, `m`, `n`, `n_i`, `rho`, `v`, `w`, `x`, `y` |
| `test_protocol_prints_the_registry_sentences` | every sentence of every `registry_outcomes` statement, `registry_common.not_run_statement` and every family's `scope`, `non_claim` and `claim_token` (split after a full stop followed by a space) occurs verbatim, after whitespace normalisation, in `preregistration.md`; the numbers inside the statements equal `true_shortfall_margin`, `heldout_shortfall_margin`, `diagnostic_recovery_tolerance` (as a percentage) and `decision_tiers`; in the `risk_rule` scope the world counts equal `decision_tiers`, the multipliers `requirement_multipliers` and the formation `formation`, and every other number is a date, a season or the citation's year |
| `test_registry_records_pass_the_boundary_under_every_token` | for each family, every subject of `registry_subjects` built as a `VerdictRecord` from config (section 10) under `PENDING` and under every token of its vocabulary, with a placeholder commit and hashes for executed tokens, constructs (rules V1 to V7) and passes `runtime.finalize({"verdicts": all_payloads(), "provenance": {"providers": HOSTED_PROVIDERS}})`; a planted badge word "LESS OPTIMISTIC, NOT WORSE" is refused under every token, `PENDING` included |
| `test_served_texts_pass_the_copy_guard` | `scan_labels(..., keys=False)` finds nothing in any registry statement, scope, non-claim, claim token, not-run statement or reason template, and `banned_key_paths(config, parts=BANNED_KEY_PARTS)` is empty; a planted "tends to" in a statement is found |
| `test_encode_result_roundtrip_and_layout` | `json.loads(encode_result(x)) == x` after rounding; scalar lists on one line; NaN raises; LF only |
| `test_full_shape_artifact_fits` | a dummy result with the frozen table shapes filled with `-0.123456` encodes to at most `results_maximum_bytes` |
| `test_results_contract` | rehearsal result has `experiment`, `version`, `tier`, `provenance`, `verdicts` with exactly the six claim ids, each token inside its vocabulary; `providers == ["pappalardo"]`; `banned_key_paths(result, parts=BANNED_KEY_PARTS)` is empty; no forbidden key or column |
| `test_hashes_are_lf_normalised` | CRLF and LF copies of a text file hash equal; a binary file is hashed byte-exact |
| `test_oracle_gate_reads_counts_and_refuses_skips` | with a monkeypatched subprocess writing a JUnit file: the expected counts pass; one skipped test, one failure or a missing count raises; two gate records of the same run are byte-equal and hold no elapsed time; a non-POSIX `os.name` is refused |
| `test_frozen_run_requires_out_and_a_committed_protocol` | `main(["--execute-frozen"])` exits non-zero; with a monkeypatched `git` reporting a dirty protocol file (any of the three) it raises before any computation; `--rehearsal` refuses an `--out` under the repo root |
| `test_rehearsal_runs_end_to_end` | `run(config, rehearsal=True)` with a divisor large enough to finish in under 60 s returns every top-level key and `"rehearsal": true`; its Part B reaches split rows beyond the gate on its own gates |
| `test_rehearsal_is_deterministic` | two rehearsal runs encode to identical bytes |
| `test_research_firewall` | no file under `galactico/api`, `galactico/optimization`, `galactico/profiles`, `galactico/match_lab`, `galactico/domain` contains `risk_selection` |
| `test_frozen_seed_is_not_used_in_tests` | neither test file contains the literal `seed` value of `config.json` |

### 6.6 Planted gate (`tests/test_risk_selection.py`, marked `planted`; section 9 runs it for the stamp)

| Test | Asserts |
|---|---|
| `test_planted_effect_classified` | `a1_truth_mix`: for each of `planted_seeds` seeds, PRIMARY cells of `planted_geometries` at `planted_tiers`, `planted_trials` trials, `rules=("BALANCE",)`: `decide_selection` returns `LESS_OPTIMISTIC_COST_BOUNDED` for both components, in at least `planted_minimum_correct` seeds |
| `test_planted_target_is_an_identity` | `a1_identity_of_the_truth_mix_target`: per cell, mean `delta_true(TRUTH_MIX)` equals minus the coin share times BALANCE's true regret on the coined trials within `planted_identity_tolerance` (an implementation identity, not a recovery) |
| `test_planted_cost_classified` | `a1_random_mix`: same seeds; precondition asserted (a planted target `> planted_cost_margin_multiple * margin` in at least one valid cell); `decide_selection(RANDOM_MIX)` is `COSTS_TRUE_SHORTFALL` in at least `planted_minimum_correct` seeds |
| `test_planted_identity_is_inconclusive` | `a1_identical`: zero informative trials in every cell and `decide_selection` is `INCONCLUSIVE` for every seed |
| `test_planted_reporting_classified` | `a1_reporting_shift`: `reporting_shift="PLUS"` gives `decide_reporting` `OWN_STATISTIC_NOT_OPTIMISTIC`, `"MINUS"` gives `NOT_ESTABLISHED`, and `"ZERO"` (cells with minima 0, every own and true shortfall 0) gives `INCONCLUSIVE`, each in at least `planted_minimum_correct` seeds |
| `test_planted_sum_gap_is_recovered` | `a2_sum_gap`: `planted_seeds` seeds, the SPLIT cells of the first decision tier (all three noise levels): `decide_split_sample_diagnostic` returns `RECOVERS_SUM_GAP` in at least `planted_minimum_correct` seeds |
| `test_leaky_halves_are_not_established` | `a2_leaky_halves`: `run_part_a2(..., leak_fraction=0.5)`: the token is `NOT_ESTABLISHED` in at least `planted_minimum_correct` seeds |
| `test_planted_heldout_shift_invalidates_the_diagnostic` | `a2_heldout_shift`: `heldout_shift = planted_heldout_shift_margin_multiple * margin` for `TRUTH_MIX` on the SPLIT cells of one decision tier: `decide_diagnostic` is false in at least `planted_minimum_correct` seeds |
| `test_split_planted_rules_classified` | `split_on_synthetic_corpora`: on `planted_split_corpora` pairs of synthetic snapshots (34 and 30 nested matches, GATED structure), `planted_split_random_splits` splits, eight blocks: each arm of `planted_split_arms` gets its token, in at least `planted_split_minimum_correct` corpora |
| `test_planted_arrays_at_the_frozen_shape` | `array_*`: `planted_array_seeds` seeds of independent cells at each shape of `planted_array_subject_cells` (per-trial normal differences with SD `planted_array_sd`, `planted_array_trials` trials, effect `planted_array_effect_standard_errors` × SD / sqrt(trials)), intervals from `paired_interval` with `bootstrap_replicates`, tokens from `decide_selection` with `subject_cells` = the array's cells: each entry of `planted_arrays` within its `at_most` / `at_least` count |
| `test_paired_interval_coverage` | `array_interval_coverage`: `planted_array_seeds` seeds of one cell with a planted mean: the percentile interval covers it in at least `planted_coverage_minimum` seeds |

Commands the implementer runs and reports (POSIX):

```sh
.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_risk_selection.py tests/test_risk_selection_experiment.py -m "not planted"
.venv/bin/python -m ruff check galactico/validation/risk_selection.py experiments/run_risk_selection.py tests/test_risk_selection.py tests/test_risk_selection_experiment.py
.venv/bin/python -X utf8 experiments/run_risk_selection.py --rehearsal --out <scratchpad>/e13-rehearsal.json
```

## 7. Pre-outcome code review (an independent reviewer signs each line after the pipeline commit and before the stamp)

1. The three protocol files in `experiments/preregistered/E-13-declared-risk-selection/`
   are byte-equal (after LF normalisation, and with the one banner edit of section 0) to the
   audited draft, were committed in the registration commit, and precede the pipeline commit;
   `pipeline_spec_sha256` matches; no `results.json` or `acceptance.json` exists in either
   commit.
2. Every test of section 6 exists under its name; every test outside 6.6 passes; the planted
   gate is run only for the stamp, after this review, and no constant was touched after
   registration.
3. No code path computes a real half-split or uses the frozen `seed` outside
   `run(..., rehearsal=False)`; the accessor guard tests pass; planted runs pass
   `rules=("BALANCE",)`; the rehearsal reads `rehearsal_design` only; the scratchpad and
   `git log -p` show no frozen-seed output and no risk-rule table for a frozen cell.
4. The oracle compares tuples, forms no encoding and imports nothing from the module except
   the function under test. No encoding reaches a dataclass, a log line or the artifact.
5. Level sets, not representatives, feed every reported quantity; the only uses of a first
   index are the two bridge arms.
6. The discard rule is the shipped one, applied to needed candidates only; a discarded world
   is discarded for every rule and counted; no value is imputed; `k` is the tier's declared
   integer; a candidate not needed cannot reach a requirement-bearing slot (assertion present).
7. Rounding is `np.rint(v / n * Q)` in that order; targets use the same function;
   normalisers never move with the multiplier or the minimum level; `BIG` follows
   `encoding_base_rule`.
8. Common random numbers: one draw set per geometry; tiers are world prefixes; the
   bootstrap matrix is shared across cells and rules of a geometry and restricted to usable
   trials; SE is the bootstrap SD.
9. Part B holds fixed the xT surface (`fit_prior_xt`), candidate set, eligibility, minima
   and normalisers; halves partition the team's prior matches; worlds resample the selecting
   half only; the loader demands the protocol hash; `structure_planted_check` runs after the
   oracle gate and before the solver audit and Part B, on both snapshots together, and never
   reads a numerator; "evaluated" means entering a selection or a gap.
10. `RANDOM`, `ALTERNATING` and `CHRONOLOGICAL` are never pooled; decisions read `RANDOM`
    blocks at every multiplier, both snapshots, decision tiers only; block means are over used
    directions with zeros where identical.
11. Decision functions take rows and return tokens; none reads a file, a seed or the clock;
    each matches its protocol table row for row, a cost first; BEYOND_MENU, SENSITIVITY and
    STRESS rows reach no decision function except the sensitivity count.
12. The solver is imported lazily, only in `solver_audit`, only after `run_oracle_gate`
    returned with the frozen counts on POSIX; the adapters use the built signature; a mismatch
    or a certified share below the minimum raises before anything is written.
13. The writer emits no identifier outside `results_allowed_identifiers`, no wall-clock field
    and no NaN; the key walk runs; the full-shape size test passes; `--verify-against` ignores
    only `determinism_excluded_keys`.
14. Hashes: text LF-normalised; data pinned by manifest digests; every `source_paths` file
    present; `protocol_commit` derived, never typed.
15. `ruff` clean; module docstrings state claim and non-claim; the copy-guard and boundary
    tests pass.
16. The firewall test passes; the registry holds six `PENDING` E-13 records whose fields
    equal section 10's records built from `config.json`.

## 8. Real execution (root only, once, after the stamp; POSIX)

```sh
.venv/bin/python -X utf8 experiments/run_risk_selection.py --execute-frozen --out experiments/preregistered/E-13-declared-risk-selection/results.json
```

Determinism re-run (same machine, same environment; writes outside the repository):

```sh
.venv/bin/python -X utf8 experiments/run_risk_selection.py --execute-frozen --out <scratchpad>/e13-rerun.json --verify-against experiments/preregistered/E-13-declared-risk-selection/results.json
```

Exit 0 on both, then `analysis.md` in the house format (bold experiment token first; the
six claim tokens; the component table; the reference arms; the beyond-menu tier; the
tie-break cells; the audit status; "what this establishes / does not"; product consequence
quoting the frozen sentences; reproduction commands). Determinism is claimed for one machine:
`weights @ values` may differ in the last bit across BLAS builds. On Windows the oracle gate
refuses to run (seven of its nine tests need POSIX resource limits).

## 9. Planted gate (`acceptance.json`)

`run_planted_gate(config)` runs the tests of 6.6 through their functions (not through pytest)
and writes `acceptance.json` beside the protocol: per entry of `planted_tests`, its seeds,
counts, requirement and pass flag; the bridge; the rehearsal's encoded hash; the source hashes;
`passed`, the conjunction. It holds no risk-rule quantity for a frozen cell. The gate runs only
after registration, so a failed requirement blocks the run and nothing is retuned. The code may
be corrected where it departs from the frozen text, after which the review of section 7 is
repeated for the changed files and the stamp is regenerated; no constant, arm, requirement,
threshold or rule may change. A rule the gate shows to be unsound is not repaired: E-13 is
superseded by a new experiment id with its own preregistration.

**What the reviser's simulation shows** (18 October 2026; synthetic only; scratch scripts not
committed; REVIEW-RECORD). Independent NumPy implementations of the decision rules, of
BALANCE and the pseudo-rules, and of the structure check, never of a declared-risk rule:

| Check | Result |
|---|---|
| Arrays at 216 independent cells, 4,000 trials, SD 0.05, normal bound (4,000 seeds; 40 seeds with the percentile bootstrap at 2,000 replicates) | `COST_BOUNDARY`: cost token 191 of 4,000 (bootstrap 1 of 40); `POSITIVE_BOUNDARY`: positive token 116 of 4,000 (2 of 40); `POSITIVE_EFFECT` at 6 SE: positive 3,969 of 4,000 (40 of 40); `COST_EFFECT` at margin + 6 SE: cost 3,981 of 4,000 (40 of 40) |
| The same at 72 cells (`WORST_WORLD`, `MINIMAX_REGRET`) | `COST_BOUNDARY` 199 of 4,000 (bootstrap 2 of 40); `POSITIVE_BOUNDARY` 101 of 4,000 (1 of 40); `POSITIVE_EFFECT` 3,989 of 4,000 (40 of 40); `COST_EFFECT` 3,990 of 4,000 (39 of 40) |
| The same at 216 cells with the draft's 2,000 trials for `GROUPED_14C10` | `POSITIVE_EFFECT` 2,041 of 4,000: the margin is then 4.5 standard errors in those cells, so both geometries now have 4,000 trials |
| A1 planted arms, both geometries, the frozen noise and levels, `WIDE` and a stand-in for `GATED_MINUTES` (0.72 × appearances), 2,000 trials, 10 seeds | `TRUTH_MIX` `LESS_OPTIMISTIC_COST_BOUNDED`, `RANDOM_MIX` `COSTS_TRUE_SHORTFALL`, `IDENTICAL` `INCONCLUSIVE` in 10 of 10 seeds; 36 of 36 cells compared for the first two |
| Structure check on an invented Madrid-like structure (14 outfield candidates, 23–29 appearances with starts and substitute spells, 34 and 30 nested matches, `GROUPED_14C10` incidence), 250 splits, noise 0.6, 3 corpora | `TRUTH_MIX` `HELD_OUT_GAP_SMALLER`, `REFERENCE_WORST_MIX` `HELD_OUT_SHORTFALL_LARGER`, `IDENTICAL` `INCONCLUSIVE` in 3 of 3; every block 500 used and at least 222 informative directions; the largest chance that a candidate has no minutes in a world of a half, 0.0023 |

The `at_most` and `at_least` counts of `planted_arrays` are set at least three binomial
standard deviations of 400 seeds away from the simulated rates, and `planted_coverage_minimum`
at more than three from the nominal 95%. Each array runs at both shapes of
`planted_array_subject_cells`. The array tests draw independent cells, the least favourable
case; the run's cells share common random numbers.

## 10. Registry records, copy guard

The registration commit adds, for each family `f` of `registry_subjects` and each of its
subjects:

```python
VerdictRecord(
    experiment_id=config["registry_experiment_id"], subject_id=subject,
    scope=config[f"registry_{f}"]["scope"], tier=Tier[config["tier"]],
    directory=config["experiment_directory"],
    claim_token=config[f"registry_{f}"]["claim_token"],
    non_claim=config[f"registry_{f}"]["non_claim"],
    not_run_statement=config["registry_common"]["not_run_statement"],
    vocabulary=tuple(config["verdict_vocabulary"][f]),
    outcomes={token: Outcome(VerdictStatus[o["status"]], o["limits"], o["statement"])
              for token, o in config["registry_outcomes"][f].items()},
    protocol_hash=lf_sha256(<registered preregistration.md>),
    config_hash=lf_sha256(<registered config.json>),
)
```

with token `PENDING`. `outcomes` covers the vocabulary exactly and holds no `PENDING` (rule
V2). Every text of the six records passes `runtime.finalize` under `PENDING` and under every
token, and `scan_labels`; the reviser checked this on the revised config with a scratch script
of the E-09 draft guard's form (REVIEW-RECORD). The router reads `risk_rule:*` only;
`verdicts.risk_report` stays `null` (`risk_report_after_run`); no surface reads
`split_sample_diagnostic` (`split_sample_after_run`).

## 11. Shared-file requests to the root

One order: the audit, registration, the pipeline, the stamp, the run.

**Before registration** (nothing below is an outcome):

| Step | Detail |
|---|---|
| Structure counts | the root fills every key of `counted_by_root_before_registration` by `counted_by_root_rule` (structure only) and states each value, and each difference from the draft, in the registration commit and REVIEW-RECORD |
| Oracle counts | a POSIX run of `risk_solver_oracle_tests`; the counts equal `risk_solver_oracle_expected` |
| Timing | `scripts/time_xi_risk.py` at 12 worlds with the opt-in on both scenarios: every rule `CERTIFIED`, `EXACT`, inside `solver_time_limit` (`verified_by_root_before_registration`); its printed fields stated in the registration commit |
| Prior exposure | the root states in the registration commit whether `test_madrid_worlds_are_the_main_solve_s`, the timing script or a risk panel on Madrid ran, and confirms that no lineup, tail value, regret or selection frequency of a risk rule on Madrid was seen |
| Pipeline hash | `pipeline_spec_sha256` is `lf_sha256` of this file as it stands. An edit to this file before registration means recomputing it; after registration neither changes |

**The registration commit** changes hosted output, and says so:

| File | Change |
|---|---|
| `experiments/preregistered/E-13-declared-risk-selection/` | the three registered files (section 0); in the same commit the draft folder's three files become one-line pointers to the registered directory, and REVIEW-RECORD stays |
| `experiments/preregistered/README.md` | a row `E-13 declared-risk selection`, `preregistered, not run` |
| `galactico/domain/verdicts.py` | the six `PENDING` records of section 10; the docstring sentence that names the E-13 document a draft |
| `galactico/api/xi_extensions.py` | `E13_SCOPE` gains the declared-minima condition (`requirement_multipliers`, compared in integer targets) and empty locks and exclusions, and `_in_e13_scope` tests them (`token_scope`); the comment on `risk_report` names `risk_report_after_run`. A root product decision: before the run it changes which suffix a request with locks, exclusions or edited minima carries (`RISK_OUTSIDE_E13` in place of `RISK_UNTESTED`) |
| `tests/test_xi_extensions_api.py`, `tests/test_xi_risk.py` | `E13_CONFIG` points at the registered config; `test_e13_scope_equals_the_draft_config` checks the new scope keys; `test_risk_claim_suffix_and_payload_follow_e13s_scope` expects the registered `PENDING` payload (badge "E-13 · RECORD ONLY · NOT RUN", the not-run statement of `registry_common`) where it now expects `NOT_REGISTERED` |
| `tests/test_protocol_drafts.py` | the E-13 guard, as W9 added E-09's: the pipeline hash, every record under every token through `finalize`, the served texts through the copy guard, and the key walks over the config echo and the section 4 keys, each with a planted failure. Until registration it reads this draft folder; the registration commit points it at the registered directory |
| tests and specs that assert no E-13 record | search for `verdict_for("E-13"`, `E-13` and `NOT_REGISTERED` in `tests/` and `e2e/`; at least the two above |
| prose that calls E-13 a draft or the solver missing | `KNOWN_LIMITATIONS.md` (the risk-mode paragraph and the drafts paragraph), the north-star README table row ("a risk solver that does not exist yet"), ROOT-DECISIONS 2.6's registry sentence |
| `tests/test_preregistration_order.py` | unchanged: `PROTOCOL` already holds `PIPELINE.md` |
| `tests/test_licensing.py` | unchanged: no E-13 file names the local-tier provider |

**After registration, before the run:**

| Step | Detail |
|---|---|
| The pipeline commit | the four files of section 0. In that commit, and not before, `tests/test_research_firewall.py` gains `risk_selection` in `RESEARCH_PIPELINES` (`test_the_lists_name_modules_that_exist` requires the file) |
| Code review | section 7, by an independent reviewer |
| The stamp | `acceptance.json`, in a commit of its own (section 9) |

**After the run:** the results commit (`results.json`, `analysis.md`, the six records' tokens,
commit and hashes). If the root chooses it, the same commit adds the `risk_report` figure of
`risk_report_after_run` under an ADR naming the edit, as W8. No product split-sample tool is
part of it (`split_sample_after_run`).

## Interfaces resolved

The draft's ten assumed interfaces, each settled against the code (section 1) or by a root
ruling:

| # | Was | Now |
|---|---|---|
| 1 | one risk function returning `solution_status`, `assignments`, a `time_limit` argument | `declared_risk_selection` as built, through `_risk_call` and `_risk_world_pairs` (T1) |
| 2 | `BIG` above the largest sum of `T`; the discard rule | met by `risk.py` (X3); the shipped discard rule adopted everywhere (T2) |
| 3 | oracle file and menu | both oracle files pinned (T3); the menu is `tail_counts` (T6) |
| 4 | `digests`, `thesis.banned_key_paths` | exist with the signatures of section 1 |
| 5 | registry schema | `domain.verdicts.VerdictRecord` as built; records of section 10 |
| 6 | the `risk_report` sentence as a figure note | conditional on the results commit (T4) |
| 7 | a product split-sample tool | none; research code only (T7) |
| 8 | per-match components re-derived | `snapshots.rate_components`, one object (ROOT 4, Z3) |
| 9 | results writer | `encode_result` (scalar lists on one line), kept |
| 10 | a corpus fixture of unknown name | `corpus_root`, `spain_frames` |

## DISSENT

1. **Engine of Part B (assignment wording, not a ROOT rule).** ROOT 2.2's "on the Madrid
   snapshots" could be read as calling the risk solver for every Part B number; this design
   computes every Part B number by exhaustive enumeration and calls the solver on a frozen
   audit subset only. Evidence: the frozen design is 2 snapshots × 500 directions × 4 levels
   × 2 tiers × 6 rules = 48,000 solves at about a second each, against minutes for enumeration.
   Enumeration also returns the level set, which a solver's single representative cannot (at
   the default minima the full-prior BALANCE optimum is `(0, 0)` and BALANCE is indifferent
   among covered XIs: comparing a rule with an arbitrary representative would credit the rule
   with the tie-break). It follows M-05's own rule: "Exhaustive sets avoid reliance on the
   solver being audited." The solver must already have passed its oracle and must reproduce
   the enumeration on every audited item or the run stops.
2. **ROOT 2.2 wording, "does worst-world / CVaR selection reduce the gap".** Under one
   common point report a rule that does not minimise the report narrows the gap unless its
   true shortfall rises as much (`delta_rep` is never negative). The delivered rule lets the
   optimism criterion be necessary and puts the weight on the cost bound, says so in the frozen
   statement, and carries `RANDOM_SET` as the visible reference. The badge word is
   "LESS OPTIMISTIC, COST BOUNDED": the draft's "NOT WORSE" was refused by the copy guard, and
   "COST BOUNDED" is what the criterion tests (a cost of at most the margin, not none).
3. **A lower synthetic true shortfall earns no token.** If a rule's true shortfall is
   strictly lower than BALANCE's in every compared cell, that is recorded as a boolean and
   reported in `analysis.md` only. The alternative is a statement that will be read as "this
   rule picks the team that plays differently" on the strength of a Gaussian simulation. In
   tie-break cells the optimism criterion itself requires a strictly lower true shortfall; that
   is recorded per cell and is the reason this dissent is stated.
4. **A cost first (reverses the draft's DISSENT 6).** The draft let a failed gate in one
   component make the subject inconclusive even when another component showed a cost, and its
   split aggregation let a held-out cost sit under a positive synthetic token. The revision reads
   a cost first in the selection verdict, in both aggregations and in the token table: a
   measured cost is evidence about the rule whatever a gate did elsewhere (the split verdict's
   cost is a statement about every block, so its own gate is still read first), and `INCONCLUSIVE` keeps the constitution's meaning
   (a gate failed and the criterion was not evaluated, here because nothing measured a cost).
   The cost side is Bonferroni-adjusted over the subject's cells, so reading it first does not
   let a union of 216 tests decide.
5. **The `split_sample_diagnostic` positive token is nearly a theorem.** Held-out sums are
   unbiased for a fixed selection under exchangeable matches, so `RECOVERS_SUM_GAP` mostly
   certifies the implementation (and the leaky-halves test shows the rule can fail). The
   informative part is the statement it licenses about the shortfall line, which is biased,
   and Part B's split-to-split spread. With no product tool (T7) the record labels research
   only. If the root prefers no badge for a near-theorem, drop the claim before registration
   and keep the statement as research-note text.

## OPEN QUESTIONS

1. Whether the risk surface will offer 200 worlds later; the tier is computed and reported
   here but enters no token.
2. The router change of section 11 (minima, locks and exclusions in `E13_SCOPE`) is a root
   product decision for the registration commit. If the root declines it, the protocol's token
   scope still binds the research note, and the scope sentence of every record says what was
   run; the request is then recorded as declined.
3. Whether `split_sample_diagnostic` stays a registry claim (DISSENT 5).
4. Runtime and artifact-size estimates in 2.5 and 4 are arithmetic, not measurements.
