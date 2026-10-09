# E-13 pipeline specification

Companion to `preregistration.md` and `config.json` in this folder. The protocol says what
is decided; this file says what is built. Where they disagree the protocol wins and the
disagreement is a defect to report. Work package `R-E13` of ARCH-SPEC 8.2.

## 0. Files, ownership, order

One implementation agent owns all of these (one module, one runner: no shared-file edits).

| File | Kind | Notes |
|---|---|---|
| `galactico/validation/risk_selection.py` | new | engine, simulator, real split, decisions. Research only; nothing under `galactico/api`, `galactico/optimization`, `galactico/profiles`, `galactico/match_lab`, `galactico/domain` may import it |
| `experiments/run_risk_selection.py` | new | CLI, provenance, writer |
| `tests/test_risk_selection.py` | new | the module: engine oracle, synthetic, split, decisions (sections 6.1–6.4) |
| `tests/test_risk_selection_experiment.py` | new | the runner: config contract, writer, hashes, rehearsal (6.5). One file more than ARCH-SPEC 8.2 lists; "one test file per module" |
| `experiments/preregistered/E-13-declared-risk-selection/{preregistration.md,config.json}` | root copies them from this folder and commits | implementer reads, never edits |

Not touched: `experiments/run_optimizer_curse.py` (called by the bridge, bytes pinned),
every frozen file of ROOT-DECISIONS 3b, `experiments/preregistered/README.md`, the verdict
registry (root adds six PENDING records from `verdict_vocabulary`, `product_consequences`
and `consequence_sentences`).

Build order: 2.1–2.2 and their oracle first; then 2.3–2.5 (synthetic: no data, no solver);
then 2.6 (real split; the solver import is lazy and only inside `solver_audit`). Decisions
(2.7) are pure and can be written first; planted arms (2.8) last.

**Outcome hygiene for the implementer.** Develop only with `rehearsal_seed` or test-local
seeds and with the synthetic corpus of 2.6. Never call `run(config, rehearsal=False)`, never
pass the frozen `seed` to a generator, never evaluate a half-split of a real snapshot. The
`slow` parity tests compare half-free quantities (full-sample values and shipped worlds)
with `build_snapshot`; that is structure, and it is the only real-data contact allowed.

## 1. Reuse

| Need | Reused object | How |
|---|---|---|
| Quantisation constant | `galactico.optimization.xi.QUANTIZATION` | must equal `config["quantization"]`, asserted at start |
| Rounding policy | `solver._q`: `int(round(value / normalizer * scale))` | re-expressed as `np.rint(values / normalizer * quantization)`; parity test against Python `round` |
| Snapshot, candidates, minima, provenance | `historical.build_snapshot(worlds=0)`, `api.decision_lab.decision_inputs(snap, "4-3-3")` | unchanged; called once per snapshot |
| xT surface | `historical.fit_prior_xt(prior_actions)` (ROOT 2.5 O2) | same prior rows as the snapshot |
| Per-match components | `profiles.uncertainty._per_match_components`, `features.spec.SPECS["progression"]`; side descriptors re-derived by the published rule (completed passes with `start_y < 0.21`, `> 0.79`) | `prior_components` reproduces `historical.py:109-160`; parity-tested |
| Shipped world weights (parity only) | `profiles.uncertainty.shared_match_weights(team_lineups.game_id, 40, SEED)` | parity test of world values |
| Eligibility semantics | `solver._eligible` (not imported): `minutes > 0 and position in slot.allowed_positions and (eligible_slots is None or slot_id in eligible_slots)`, plus "no `None` for an applicable active metric" | re-implemented in `enumerate_selections`, checked by the solver audit |
| BALANCE solver (audit only) | `galactico.optimization.xi.solve_xi(..., analyze_ties=False)` | objective compared as `round(v * Q)` |
| Risk solver (audit only) | see ASSUMED INTERFACES 1–2 | lazy import inside `solver_audit` |
| LF hashing | `galactico.validation.digests.lf_sha256`, `lf_sha256_text` (HARDENING-H1 D3) | text files only |
| M-05 | `experiments.run_optimizer_curse.run()` | bridge reference, called live |

## 2. `galactico/validation/risk_selection.py`

Module docstring (verbatim first paragraph): "E-13: declared-risk selection rules compared
by exhaustive enumeration. Claims what each rule selects and reports inside a declared
additive requirement model, on synthetic matches with known values and on coherent halves
of historical matches. Claims nothing about football: a rule is a declared preference over
resamples, never a better team."

`__all__` lists every public name below. `VERSION = "declared-risk-selection-v1"`.
All dataclasses `frozen=True`. Arrays are NumPy; "int" arrays are `int64`; coefficient
arrays are `float64` holding exact integers. Index letters: `B` batch (trials or split
directions), `W` worlds, `N` candidates, `R` requirements (sorted by requirement id),
`S` selections, `G` matches.

### 2.1 Integer model

```python
def quantize(values: np.ndarray, normalizer: np.ndarray | float, quantization: int) -> np.ndarray
    # np.rint(values / normalizer * quantization); divide, then multiply, then round (solver._q order)
def selection_sums(coefficients: np.ndarray, incidence: np.ndarray) -> np.ndarray
    # (..., N, R), (S, N) -> (..., S, R) via np.einsum("...nr,sn->...sr", ...); assert abs < 2**50
def shortfalls(sums: np.ndarray, targets: np.ndarray) -> tuple[np.ndarray, np.ndarray]
    # (..., S, R), (R,) -> M (..., S), T (..., S), int64; d = maximum(0, targets - sums)
def encoding_base(total_max: int, worlds: int) -> int
    # BIG = worlds * total_max + 1 (>= 2): larger than any sum of T over the worlds. Raises OverflowError
    # unless (M_max * BIG + total_max) * worlds < 2**62 at the call site (checked by encode)
def encode(m: np.ndarray, t: np.ndarray, base: int) -> np.ndarray      # base * m + t, int64; private use only
def level_of(objective: np.ndarray) -> np.ndarray                      # (B, S) -> bool (B, S): objective == row minimum
def level_mean(level: np.ndarray, values: np.ndarray) -> np.ndarray
    # bool (B, S), (B, S) or (B, S, R) -> (B,) or (B, R): mean over the level set; NaN where it is empty
```

`BIG` is recomputed per call from the batch's own largest `T` and world count. Any value
above that bound gives the same order; a test doubles it and requires identical outputs.
No function returns, logs or stores an encoding; only decoded `M`, `T` and level sets leave.

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
    own_divisor: int | None         # k (1 for BALANCE and WORST_WORLD); None for MINIMAX_REGRET

def apply_rules(
    point_m: np.ndarray, point_t: np.ndarray,        # int64 (B, S)
    world_m: np.ndarray, world_t: np.ndarray,        # int64 (B, W, S)
    world_valid: np.ndarray,                         # bool (B, W)
    *, tail_counts: Mapping[str, int],               # {"WORST_WORLD": 1, "TAIL_10": k, ...} for this W
) -> dict[str, RuleOutcome]
```

Masked reductions, with `e = encode(world_m, world_t, base)` and invalid worlds set to `-1`
(every valid encoding is `>= 0`, so a discarded world never enters a tail):

| Rule | Objective `(B, S)` | Decoding |
|---|---|---|
| `BALANCE` | `encode(point_m, point_t, base)` | `own_m_sum = point M` at the optimum |
| `WORST_WORLD`, `TAIL_*` | `sort(e, axis=1)[:, ::-1][:, :k].sum(axis=1)` | `own_m_sum = objective.min(axis=1) // base` (exact because `base > sum of T`) |
| `MINIMAX_REGRET` | `e_star = where(valid, e.min(axis=2), 0)`; `where(valid[..., None], e - e_star[..., None], 0).max(axis=1)` | none |

`k` is fixed by the tier (ROOT 2.5: `TAIL(k of B)`); it is not recomputed on `W_used`. Rows
with `W_used < max(1, k)`: `usable=False`, empty level set, excluded and counted by callers.

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
    reference_m: np.ndarray           # level mean of the reference M / Q (truth in A1; held-out in A2, B)
    reference_t: np.ndarray
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
    extra_levels: Mapping[str, np.ndarray] | None = None,   # reference / planted arms: name -> bool (B, S)
) -> dict[int, dict[str, Evaluation]]
```

Tier `W` uses `world_coef[:, :W]` and `world_valid[:, :W]`; world sums are computed once at
`Wmax`. `extra_levels` arms get an `Evaluation` with `reported_own_m=None`. Batch so that no
array exceeds ~250 MB (`B * Wmax * S * R * 8` bytes).

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

def geometries(config: Mapping) -> tuple[Geometry, ...]
def geometry_incidence(geometry: Geometry) -> np.ndarray
    # (S, N); rows in itertools.product order of itertools.combinations per group, candidates numbered group by group

@dataclass(frozen=True)
class SyntheticDraws:
    latent: np.ndarray            # (trials, N, R) = latent_mean + latent_sd * standard normal
    match_uniforms: np.ndarray    # (trials, N, G) uniform [0, 1)
    count_order: np.ndarray       # int64 (trials, N): a permutation of 0..N-1 per trial
    shared: np.ndarray            # (trials, G, R) standard normal
    idiosyncratic: np.ndarray     # (trials, G, N, R) standard normal
    world_counts: np.ndarray      # int64 (trials, Wmax, G): multinomial(G, 1/G)
    half_order: np.ndarray        # int64 (trials, G): permutation; half A = the G // 2 matches listed first
    half_world_counts: np.ndarray # int64 (trials, 2, Wmax, G // 2): multinomial(G // 2, uniform) per direction

def draw_synthetic(geometry: Geometry, *, geometry_index: int, seed: int, config: Mapping,
                   trials: int | None = None, worlds: int | None = None) -> SyntheticDraws
```

Streams: `np.random.default_rng([seed, geometry_index, stream])` with `stream` =
`config["stream_*"]` (latent 0, match uniforms 1, count permutation 2, shared effect 3,
idiosyncratic 4, world counts 5, split halves 6, half-A worlds 7, half-B worlds 8, planted
coins 9). One call per stream, in the shapes above, so no stream depends on another.

```python
def exposure(draws: SyntheticDraws, counts: Sequence[int], profile: str) -> np.ndarray
    # bool (trials, G, N). Candidate i gets sorted(counts)[count_order[t, i]] matches
    # (WIDE_ALIGNED: the position of i in a stable ascending argsort of latent[t].mean(axis=-1) replaces count_order);
    # he plays the matches whose match_uniforms[t, i] are the n_i smallest (stable argsort)
def observations(draws: SyntheticDraws, *, noise_sd: float, shared_fraction: float) -> np.ndarray
    # (trials, G, N, R): latent + noise_sd * sqrt(G) * (sqrt(rho) * shared[:, :, None, :] + sqrt(1 - rho) * idiosyncratic)
def weighted_values(obs: np.ndarray, plays: np.ndarray, weights: np.ndarray) -> tuple[np.ndarray, np.ndarray]
    # obs (B, G, N, R), plays (B, G, N), weights (B, K, G) >= 0
    # -> values (B, K, N, R) = sum_g w*plays*obs / sum_g w*plays ; valid bool (B, K): every candidate has a positive denominator
def oracle_shrinkage(values: np.ndarray, plays: np.ndarray, *, noise_sd: float, config: Mapping) -> np.ndarray
    # latent_mean + a_i * (values - latent_mean), a_i = latent_sd^2 / (latent_sd^2 + noise_sd^2 * G / n_i)
def m05_bridge(config: Mapping) -> dict
    # rng = default_rng(bridge_seed); latent = rng.normal(1.8, 0.3, (bridge_trials, 8, 2)); for noise in bridge_noise_sd:
    # measured = latent + rng.normal(0, noise, latent.shape)   -- M-05's exact draw order (the three literals are M-05's).
    # Engine BALANCE_FIRST arm (first index of the level set, combinations order) against run_optimizer_curse.run():
    # the six columns per noise level; returns {"rows": [...], "maximum_absolute_difference": float, "passed": bool}
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

def expand_cells(config: Mapping) -> tuple[Cell, ...]
```

Order: PRIMARY (tier in `decision_tiers`, geometry, noise, level, exposure), BEYOND_MENU
(tiers of `world_tiers` not in `decision_tiers`; same inner order), SENSITIVITY (variant,
exposure, geometry, noise, level), STRESS (geometry, noise, level, exposure), SPLIT (tier in
`decision_tiers`, geometry, noise, level). Counts must equal
`expected_primary_cells_per_tier` per tier (PRIMARY and BEYOND_MENU),
`expected_sensitivity_cells`, `expected_stress_cells`, `expected_split_cells_per_tier` per
decision tier; assert. With the frozen config: 72 + 36 + 72 + 12 + 36 = 228 cells.

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
    cell: int; rule: str; valid: bool; informative_trials: int; compared: bool
    delta_true_mean: float; delta_true_low: float; delta_true_high: float
    delta_optimism_mean: float; delta_optimism_low: float; delta_optimism_high: float
    optimism_own_mean: float | None; optimism_own_low: float | None; optimism_own_high: float | None
    true_shortfall_lower: bool      # delta_true_high < 0; recorded, carries no token

@dataclass(frozen=True)
class SplitRuleRow:     # A2, one per (cell, rule)
    cell: int; rule: str; trials_used: int
    true_optimism_half: float; heldout_gap: float; heldout_excess: float

@dataclass(frozen=True)
class DiagnosticRow:    # A2, one per (cell, rule in MODES)
    cell: int; rule: str; informative_trials: int
    delta_optimism_mean: float; delta_optimism_low: float; delta_optimism_high: float   # truth
    delta_gap_mean: float; delta_gap_low: float; delta_gap_high: float                  # held-out
    delta_true_mean: float; delta_true_low: float; delta_true_high: float               # truth
    delta_out_mean: float; delta_out_low: float; delta_out_high: float                  # held-out
    agreement: str                                                                       # "AGREES" | "CONTRADICTS" | "UNRESOLVED"

@dataclass(frozen=True)
class SumGapRow:        # A2, BALANCE, one per SPLIT cell of the first decision tier
    cell: int; trials_used: int
    sum_gap_true_mean: float; sum_gap_true_low: float; sum_gap_true_high: float
    sum_gap_heldout_mean: float
    recovery_ratio: float | None; recovery_low: float | None; recovery_high: float | None   # None when unresolved
    resolved: bool                                                                           # sum_gap_true_low > 0
    shortfall_excess_mean: float                                                             # BALANCE heldout_excess

def trial_bootstrap_counts(trials: int, *, replicates: int, seed: int, geometry_index: int) -> np.ndarray
    # int64 (replicates, trials): default_rng([seed, geometry_index]).multinomial(trials, 1/trials, size=replicates)
def paired_interval(differences: np.ndarray, counts: np.ndarray, quantiles: Sequence[float]) -> tuple[float, float, float]
    # mean, low, high of (counts @ differences) / trials; NaN-free input required
def ratio_interval(numerator: np.ndarray, denominator: np.ndarray, counts: np.ndarray,
                   quantiles: Sequence[float]) -> tuple[float, float, float]
    # mean(numerator) / mean(denominator) and the percentile interval of (counts @ numerator) / (counts @ denominator)
def run_part_a1(config: Mapping, *, seed: int, trial_divisor: int = 1,
                planted: Sequence[str] = ()) -> tuple[list[ArmRow], list[PairedRow]]
def run_part_a2(config: Mapping, *, seed: int, trial_divisor: int = 1,
                leak_fraction: float = 0.0) -> tuple[list[SplitRuleRow], list[DiagnosticRow], list[SumGapRow]]
def planted_level(kind: str, balance_level: np.ndarray, target_level: np.ndarray, coins: np.ndarray) -> np.ndarray
    # kind "TRUTH_MIX": target_level (the reference-optimal level set) where coins, else balance_level
    # kind "RANDOM_MIX": all-True where coins, else balance_level;  kind "IDENTICAL": balance_level
    # coins = default_rng([seed, geometry_index, stream_planted_coins]).random(trials) < planted_probability
```

A1 per trial: point = `weighted_values(obs, plays, ones)`; worlds = `weighted_values(obs,
plays, world_counts)`; reference = latent. Coefficients = `quantize(values, normalizer, Q)`;
targets = `quantize(minimum, normalizer, Q)`. Reference arms through `extra_levels`:
`BALANCE_FIRST` (first True of BALANCE's level), `ORACLE_SHRINKAGE` (BALANCE level on shrunk
values; its `reported_own_m` is the shrunk-scale `M`, filled by the caller), `RANDOM_SET`
(all True). Paired differences use every usable trial (zeros where identical).
`valid = discarded_world_trial_share <= maximum_discarded_world_trial_share`;
`compared = valid and informative_trials >= minimum_informative_trials`.

A2 per trial and direction `d in {0, 1}`: selecting half `H_d`, other half `H_{1-d}`; point
weights = indicator of `H_d`; world weights = `half_world_counts[t, d]` scattered onto the
ascending match indices of `H_d`; held-out values from the indicator of `H_{1-d}`; truth =
latent. Two `evaluate_rules` calls per direction (reference = held-out, reference = truth)
sharing the same levels. Trial value = mean of the two directions.
`heldout_excess = heldout_gap - true_optimism_half`. Sum gaps (BALANCE): `sum_gap_true =
mean_r(point_sums - true reference_sums)`, `sum_gap_heldout = mean_r(point_sums - held-out
reference_sums)`. `leak_fraction > 0` (tests only) moves that fraction of the other half's
matches into the selecting half's weights without removing them from the other half: a
deliberately broken check for the planted-failure test.

### 2.5 Memory and cost (estimates, UNVERIFIED until the rehearsal reports them)

| Block | Largest array | Estimate |
|---|---|---|
| A1 `GROUPED_14C10`, 200 worlds | batch 100 trials × 200 × 200 × 3 × 8 B = 96 MB | 10–20 s per (noise, exposure, level) |
| A1 `M05_8C3`, 200 worlds | batch 500 × 200 × 56 × 2 × 8 B = 90 MB | 3–6 s |
| A1 + A2 total | | under 30 min, one process, under 1.5 GB |
| Part B enumeration, 40 worlds | batch 100 directions × 40 × 480 × 3 × 8 B = 46 MB | under 10 min |
| Solver audit, 192 solves at 12 worlds | | 5–30 min; `solver_time_limit` each |

No process pool. The rehearsal prints measured times to stderr; the implementer reports them.

### 2.6 Real split (Part B)

```python
@dataclass(frozen=True)
class SelectionSpace:
    incidence: np.ndarray          # float64 (S, N) over candidates sorted by player_id, requirement-bearing slots only
    assignment_count: int          # ordered feasible assignments (expected 5200)
    player_set_count: int          # distinct full player sets (expected 480)
    selection_count: int           # S
    reference_level: np.ndarray    # bool (S,): selections with the largest sum of prior minutes

def enumerate_selections(candidates: Sequence[Candidate], requirements: Sequence[TacticalRequirement],
                         formation: Formation) -> SelectionSpace
    # depth-first over formation.slots in order; eligibility as in section 1; one player per slot.
    # Raises NotImplementedError unless every active requirement applies to the same slot set.

@dataclass(frozen=True)
class SplitInputs:
    scenario_id: str
    source: str                    # "CORPUS" | "SYNTHETIC" | "SYNTHETIC_ON_STRUCTURE"
    game_ids: np.ndarray           # int64 (G,), ascending (the order shared_match_weights uses)
    date_order: np.ndarray         # int64 (G,): positions of game_ids sorted by (date, game_id)
    numerators: np.ndarray         # float64 (N, R, G); 0.0 where the player did not appear
    minutes: np.ndarray            # float64 (N, R, G) denominators
    measured: np.ndarray           # bool (N,): candidate carries values for every active requirement (False for GK)
    minima: np.ndarray             # float64 (R,): snapshot requirement minima
    normalizers: np.ndarray        # float64 (R,): the same minima (shipped policy)
    requirement_ids: tuple[str, ...]
    space: SelectionSpace
    structure: dict                # counts only: prior_team_matches, candidates, omitted, assignments, player_sets,
                                   # selections, min/max outfield appearances; plus dataset_hash, xt_version, feature_fingerprints

def prior_components(*, actions, matches, lineups, players, match_id: int, team_id: int) -> dict[str, pd.DataFrame]
    # metric -> frame[player_id, game_id, numerator, denominator] for the three active metrics, by historical.py:109-160
def load_split_inputs(snapshot_spec: Mapping, config: Mapping) -> SplitInputs
    # assert_may_host("pappalardo"); reads the four files in data_paths; build_snapshot(worlds=0);
    # decision_inputs(snap, formation); source="CORPUS"; stops (ValueError) if any expected_* count differs
def synthetic_split_inputs(*, seed: int, noise_sd: float, drift: float = 0.0, matches: int = 34,
                           groups: Sequence[tuple[int, int]] = ((5, 4), (5, 3), (4, 3))) -> tuple[SplitInputs, np.ndarray]
    # test and rehearsal corpus with known latent rates (second value, (N, R)); GATED_SQUAD counts;
    # sentinel player ids >= 9_000_001 never leave the function
def synthetic_on_structure(inputs: SplitInputs, *, seed: int, noise_sd: float, config: Mapping) -> tuple[SplitInputs, np.ndarray]
    # keeps game_ids, date_order, minutes, measured, space, minima, normalizers; REPLACES numerators with
    # minutes / 90 * rate, rate[i, r, g] = latent[i, r] * (1 + (noise_sd / latent_mean) * sqrt(G) * z[g, i, r]);
    # latent[i, r] ~ Normal(mu_r, (latent_sd / latent_mean) * mu_r), mu_r = minima[r] / (requirement-bearing slots);
    # z = sqrt(rho) * shared + sqrt(1 - rho) * idiosyncratic standard normals, rho = base_shared_fraction;
    # never reads inputs.numerators; source="SYNTHETIC_ON_STRUCTURE"
def weighted_rates(inputs: SplitInputs, weights: np.ndarray) -> tuple[np.ndarray, np.ndarray]
    # weights (K, G) -> values (K, N, R) = numerators @ w / minutes @ w * 90 (NaN where not measured); valid bool (K,)
def split_masks(inputs: SplitInputs, config: Mapping, *, snapshot_index: int, random_splits: int) -> list[tuple[str, int, np.ndarray]]
    # (family, split_index, bool mask of half A over game_ids).
    # RANDOM r: perm = default_rng([seed, real_split_stream_offset + snapshot_index, r]).permutation(G); A = perm[: G // 2]
    # ALTERNATING: A = date_order[0::2]; CHRONOLOGICAL: A = date_order[: G // 2]
def half_world_counts(mask: np.ndarray, *, worlds: int, config: Mapping, snapshot_index: int,
                      split_index: int, direction: int) -> np.ndarray
    # int64 (worlds, G): default_rng([seed, real_world_stream_offset + snapshot_index, split_index, direction])
    # .multinomial(h, 1/h, size=worlds) scattered onto the ascending positions of the selecting half; zeros elsewhere

@dataclass(frozen=True)
class DirectionRow:     # in memory only; never serialised
    family: str; split_index: int; direction: int; multiplier: float; tier: int; rule: str
    used: bool; informative: bool; level_size: int
    reported_point_m: float; reported_own_m: float | None; heldout_m: float
    sums_in: tuple[float, ...]; sums_out: tuple[float, ...]     # normalised requirement sums, level mean, per requirement

def evaluate_snapshot(inputs: SplitInputs, config: Mapping, *, snapshot_index: int, random_splits: int,
                      protocol_hash: str | None = None, extra: Sequence[str] = ()) -> list[DirectionRow]
    # THE accessor to half-split outcomes. If inputs.source == "CORPUS" it raises PermissionError unless
    # protocol_hash == lf_sha256(EXPERIMENT / "preregistration.md"). Tiers: decision_tiers only.
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
    # delta_* are None for BALANCE and REFERENCE_PRIOR_MINUTES; shares are over informative used directions
def structure_planted_check(inputs: SplitInputs, config: Mapping, *, snapshot_index: int) -> dict
    # synthetic_on_structure(seed=[seed, structure_check_stream_offset + snapshot_index]) at planted_split_noise_sd,
    # planted_split_random_splits splits; pseudo-rules TRUTH_MIX (target = held-out-optimal level), RANDOM_MIX, IDENTICAL;
    # returns {"truth_mix": token, "random_mix": token, "identical": token, "reference_gap_sum": 0, "passed": bool};
    # passed iff HELD_OUT_GAP_SMALLER, HELD_OUT_SHORTFALL_LARGER, INCONCLUSIVE and the fixed-selection gap sums to 0
def solver_audit(inputs: SplitInputs, snapshot, config: Mapping, *, snapshot_index: int, protocol_hash: str) -> dict
    # {"items": int, "certified": int, "uncertified": int, "skipped_discarded_world": int,
    #  "status": "ALL_CERTIFIED_MATCH" | "PARTIAL_CERTIFIED_MATCH"}
    # raises SolverAuditMismatch (RuntimeError) on the first certified item that disagrees
```

Rules for `evaluate_snapshot`: for each split and direction, half values and world values by
`weighted_rates`; `used = all measured candidates have exposure in both halves and
W_used(tier) >= ceil(minimum_used_world_share * tier)`; coefficients by `quantize(values,
normalizers, Q)` with unmeasured candidates' columns set to 0 (they sit in no
requirement-bearing slot; assert `incidence[:, ~measured].sum() == 0`); targets by
`quantize(multiplier * minima, normalizers, Q)`; `evaluate_rules` with reference = held-out
half and `extra_levels={"REFERENCE_PRIOR_MINUTES": reference_level, ...}`. Sums are computed
once per direction; only the targets change with the multiplier.

`solver_audit` items: the splits in `solver_audit_random_splits` plus the alternating split,
both directions, `solver_audit_multipliers`, `solver_audit_worlds`, six rules. For each item
build `Candidate`s with the selecting half's values (`dataclasses.replace(c, values=...)`;
goalkeepers keep `None`), requirements with the multiplied minima and unchanged normalisers,
and worlds as `{world_id: {player_id: {metric: value}}}`. BALANCE through `solve_xi`, the
others through the risk solver with the tier's `k`. Certified = status `OPTIMAL`. A
certified item passes iff (a) the returned XI's requirement-bearing player set lies in the
enumerated level set and (b) the solver's per-world `(M, T)` pairs for that XI equal the
enumerated pairs in every used world (BALANCE: its objective vector equals the enumerated
point pair). Items in which a world was discarded are skipped and counted.

### 2.7 Decisions (pure functions; inputs are plain rows, outputs are tokens)

```python
COMPONENT_SELECTION = ("INCONCLUSIVE", "COSTS_TRUE_SHORTFALL", "LESS_OPTIMISTIC_NOT_WORSE", "NOT_ESTABLISHED")
COMPONENT_REPORTING = ("NOT_APPLICABLE", "INCONCLUSIVE", "OWN_STATISTIC_NOT_OPTIMISTIC", "NOT_ESTABLISHED")
COMPONENT_SPLIT = ("INCONCLUSIVE", "DIAGNOSTIC_UNVALIDATED", "HELD_OUT_SHORTFALL_LARGER", "HELD_OUT_GAP_SMALLER", "NOT_ESTABLISHED")
EXPERIMENT_VERDICTS = ("INCONCLUSIVE", "LABEL_EARNED", "NOT_ESTABLISHED")
# subject vocabularies are read from config["verdict_vocabulary"]

def minimum_count(fraction: Sequence[int], cells: int) -> int      # ceil(numerator * cells / denominator), integer arithmetic
def decide_selection(rows: Sequence[PairedRow], config: Mapping) -> str
def decide_reporting(rows: Sequence[PairedRow], rule: str, config: Mapping) -> str   # NOT_APPLICABLE for MINIMAX_REGRET
def interval_sign(low: float, high: float) -> int                  # +1 if low > 0, -1 if high < 0, else 0
def cell_agreement(row: DiagnosticRow) -> str
def decide_diagnostic(rows: Sequence[DiagnosticRow], config: Mapping) -> bool
def decide_split(blocks: Sequence[SplitBlock], diagnostic_valid: bool, config: Mapping) -> str
def aggregate_selection(tokens: Sequence[str]) -> str              # "INCONCLUSIVE" | "COSTS" | "POSITIVE" | "NOT_ESTABLISHED"
def aggregate_split(tokens: Sequence[str]) -> str                  # "INCONCLUSIVE" | "UNVALIDATED" | "LARGER" | "SMALLER" | "NOT_ESTABLISHED"
def decide_risk_rule(selection: str, split: str) -> str            # the protocol's five-row table
def decide_risk_report(tokens: Sequence[str]) -> str
def decide_split_sample_diagnostic(rows: Sequence[SumGapRow], config: Mapping) -> str
def decide_experiment(risk_rule_tokens: Mapping[str, str]) -> str
def decide_all(paired: Sequence[PairedRow], diagnostic: Sequence[DiagnosticRow], sum_gaps: Sequence[SumGapRow],
               blocks: Sequence[SplitBlock], cells: Sequence[Cell], config: Mapping) -> dict
    # {"components": {rule: {str(tier): {"selection", "reporting", "diagnostic_valid", "split_sample",
    #                                    "compared_cells", "true_shortfall_lower_in_all_compared_cells"}}},
    #  "sensitivity": {rule: {"cost_cells": int, "cells": int}},     # SENSITIVITY + STRESS, reported, changes no token
    #  "verdicts": {claim_id: {"token": str, "reason": str}},        # claim_id = "E-13/" + subject, six of them
    #  "verdict": str}
```

Each function implements exactly the protocol table of the same name, rows in order.
`decide_selection` and `decide_reporting` receive one component's PRIMARY rows;
`decide_split` receives the component's `RANDOM`-family blocks for both snapshots and every
multiplier (eight blocks) and returns `INCONCLUSIVE` if it receives fewer.
`reason` is one sentence built from a fixed template per token (counts only, no player).

### 2.8 Planted arms (used only when `planted` / `extra` is passed; never in the frozen A1, A2 or Part B tables)

`run_part_a1(config, seed=s, planted=("TRUTH_MIX", "RANDOM_MIX", "IDENTICAL"))` restricted
by a derived config to `planted_geometry`, `planted_worlds`, `planted_trials` yields
`PairedRow`s for the three pseudo-rules exactly as for a rule. Known planted magnitudes:
`delta_true(TRUTH_MIX) = -(share of coins) * regret_m(BALANCE on the coined trials)`,
`delta_true(RANDOM_MIX) = (share of coins) * [true_m(RANDOM_SET) - true_m(BALANCE)]` on the
coined trials; the function also returns these two per-cell targets when `planted` is set.
`evaluate_snapshot(..., extra=(...))` does the same on a split, the "truth" being the
held-out half.

## 3. `experiments/run_risk_selection.py`

Docstring: "Execute E-13's frozen plan; writes an aggregate research artifact only."

```python
EXPERIMENT = ROOT / "experiments/preregistered/E-13-declared-risk-selection"
def protocol_commit() -> str
    # read-only git: `git log --diff-filter=A --format=%H -- <EXPERIMENT>/preregistration.md` (last line = first add).
    # Raises if empty, or if `git diff --quiet HEAD -- <path>` is non-zero for preregistration.md, config.json
    # or any source_paths entry (the committed blobs are what runs). Never a literal.
def provenance(config: Mapping, *, rehearsal: bool) -> dict
def run_oracle_gate(config: Mapping) -> dict
    # subprocess: [sys.executable, "-m", "pytest", "-q", *risk_solver_oracle_tests]; non-zero exit raises.
    # returns {"tests": [...], "lf_sha256": {...}, "summary": last stdout line}
def run(config: Mapping, *, rehearsal: bool) -> dict
def encode_result(result: Mapping, *, decimals: int) -> str
    # deterministic JSON: indent 2 for mappings and for lists of containers; a list of scalars on ONE line;
    # floats rounded to `decimals`; allow_nan=False (NaN anywhere raises); LF line endings; trailing newline
def verify_against(result: Mapping, reference_path: Path, excluded: Sequence[str]) -> list[str]
def main(argv: Sequence[str] | None = None) -> int
```

| Flag | Meaning |
|---|---|
| `--execute-frozen` | frozen config, frozen seeds; requires `--out`; calls `protocol_commit()` |
| `--rehearsal` | `seed := rehearsal_seed`, trials divided by `rehearsal_trial_divisor`, Part B on `synthetic_split_inputs` (two synthetic "snapshots", `rehearsal_random_splits`), oracle gate and solver audit skipped, result carries `"rehearsal": true`; refuses an `--out` inside the repository |
| `--out PATH` | written by the runner with `Path.write_bytes(text.encode("utf-8"))` (never shell redirection); refuses to overwrite an existing file |
| `--verify-against PATH` | after the run, compare with an earlier artifact ignoring `determinism_excluded_keys`; exit 1 and list differing key paths if any |

Exactly one of `--execute-frozen` / `--rehearsal` is required. `run` follows the protocol's
"Frozen procedure" order. Nothing is written unless every step succeeded and
`len(encode_result(...).encode()) <= results_maximum_bytes`.

Config keys whose reader is not named elsewhere in this file (the no-dead-key test covers all):

| Key | Read by | For |
|---|---|---|
| `experiment_id`, `tier`, `experiment_directory` | runner | the three contract fields; `EXPERIMENT` must equal `ROOT / experiment_directory` |
| `rules`, `modes`, `reference_arms` | module import check | must equal `RULES`, `MODES` and the three reference arm names |
| `provider`, `league_list`, `team_id`, `formation` | `load_split_inputs` | `assert_may_host(provider)`; exactly one league, the `competition=<league>` directory; `build_snapshot(team_id=...)`; `decision_inputs(snap, formation)` |
| `expected_candidates`, `expected_feasible_assignments`, `expected_player_sets`, `expected_active_requirements`, `snapshots[*].expected_prior_team_matches` | `load_split_inputs` | structural stops |
| `split_families` | `split_masks` | the families produced, in this order |
| `alternating_split_index`, `chronological_split_index` | `split_masks`, `half_world_counts` | the `split_index` of the two deterministic splits (seeds of their worlds) |
| `solver_audit_include_alternating`, `solver_seed`, `solver_time_limit` | `solver_audit` | audit item list; `seed` and time limit passed to both solvers (in the unit the solver's API declares) |
| `rehearsal_synthetic_corpus_noise_sd` | runner, rehearsal only | noise of the two synthetic "snapshots" |
| `float_decimals` | `encode_result` | rounding of every float in the artifact |
| `stream_*`, `real_*_stream_offset`, `structure_check_stream_offset` | generators | third (or second) element of each seed sequence |
| `display_status`, `claim_tokens`, `non_claims`, `verdict_vocabulary`, `product_consequences`, `consequence_sentences`, `subject_arms` | `decide_all` (vocabulary and subject map), registry and tests (the rest) | tokens must come from the vocabulary; the registry records must equal these maps |

## 4. `results.json` shape (aggregate only; ARCH-SPEC 3.2 contract plus tables)

Tables are `{"columns": [...], "rows": [[...], ...]}`; categorical columns are small
integers indexing `vocabularies`; one row per line.

| Key | Content |
|---|---|
| `experiment`, `version`, `tier` | `"E-13"`, `config["version"]`, `"PUBLIC"` |
| `provenance` | `protocol_commit`, `protocol_hash`, `config_hash`, `source_hashes{posix path: sha}`, `source_hash_policy: "lf-sha256"`, `manifest_digests` (the raw-JSON digests of `manifest_path`: the data pin), `parquet_hashes{posix path: sha}` (recorded, not a pin: they depend on the writer version), `packages{numpy, pandas, pyarrow, ortools}`, `python`, `config` (verbatim), `snapshots[{scenario_id, dataset_hash, xt_version, feature_fingerprints, structure}]`, `oracle_gate`, `providers: ["pappalardo"]`, `data_license`, `reuse_disclosure` |
| `verdicts` | `{claim_id: {"token", "reason"}}` for the six claims |
| `verdict`, `interpretation`, `uncertainty_limit`, `product_effect` | strings; `product_effect` = "Labels only: no default, coefficient, gate or solver output changes" |
| `decisions` | `components` and `sensitivity` from `decide_all` |
| `vocabularies` | `arms`, `rules`, `blocks`, `variants`, `geometries`, `minimum_levels`, `exposure_profiles`, `families`, `agreements`, `scenarios` |
| `bridge_m05` | `rows` (noise, column, engine value, M-05 value), `maximum_absolute_difference`, `tolerance`, `passed` |
| `part_a1.cells` | table of `Cell` fields |
| `part_a1.arms` | table of `ArmRow`; PRIMARY, BEYOND_MENU and STRESS cells |
| `part_a1.paired` | table of `PairedRow`; all A1 cells |
| `part_a2.rules`, `part_a2.diagnostic`, `part_a2.sum_gap` | tables of `SplitRuleRow`, `DiagnosticRow`, `SumGapRow` |
| `part_b.coverage` | per snapshot: `structure`, used / unused direction counts per family and tier, minimum and mean `W_used`, `structure_planted_check` |
| `part_b.blocks` | table of `SplitBlock` for the `RANDOM` family (without the two sum tuples) |
| `part_b.deterministic_blocks` | table for `ALTERNATING`, `CHRONOLOGICAL`: `scenario, family, multiplier, tier, rule, used, reported_point_mean, heldout_mean, gap_mean` |
| `part_b.requirement_sums` | table: `scenario, multiplier, rule, requirement, sums_in_mean, sums_out_mean` (`RANDOM` family, first decision tier) |
| `part_b.solver_audit` | `items`, `certified`, `uncertified`, `skipped_discarded_world`, `status` per snapshot |

Forbidden in the artifact: any key or column named `player_id`, `name`, `players`,
`assignments`; any per-player value; any selected XI; any encoding `E` or `BIG`; any
identifier from the corpus other than `scenario_id` and the two public `match_id`s inside
`config`; any wall-clock field. Size: at most `results_maximum_bytes` (480,000; the
repository limit is 512 KB). Estimate from the row counts: 300–400 KB (about 36,000 values).

## 5. Hash discipline

| Object | Function | Why |
|---|---|---|
| `preregistration.md`, `config.json` | `digests.lf_sha256(path)` (CRLF → LF, then SHA-256) | `core.autocrlf=true` on this checkout; the recorded hash must verify on any platform (lifecycle T1) |
| every `source_paths` entry | `lf_sha256` | same; keys are POSIX paths relative to the repo root |
| data pin | the per-file digests inside `manifest_path` (raw provider JSON), copied verbatim | Parquet digests depend on the pandas version and the cache was re-ingested during reconnaissance (critique H40) |
| every `data_paths` entry (Parquet) | byte-exact `hashlib.file_digest(f, "sha256")` | binary; never normalised; recorded, not a pin |
| protocol commit | `protocol_commit()` | derived from git; the working protocol, config and sources are the committed blobs |
| snapshot data | `snapshot.provenance["dataset_hash"]`, `["xt_version"]`, `["feature_fingerprints"]` | the shipped content hashes of the prior rows |
| oracle tests | `lf_sha256` of each `risk_solver_oracle_tests` file | which oracle vouched for the solver |
| accessor | `evaluate_snapshot(..., protocol_hash=...)` | real half-split outcomes are unreachable without the committed protocol's hash |

A missing `source_paths` file is an execution failure, not a skipped entry.

## 6. Test suite (all synthetic unless marked `slow`)

Oracle rule: the reference in `tests/test_risk_selection.py` is written from the protocol
with `itertools`, `fractions.Fraction` and Python `int`. It compares world losses as tuples
`(M, T)` and sums them componentwise; it never forms an encoding and imports nothing from
`risk_selection` except the function under test. Every row below is a required test function.

### 6.1 Engine

| Test | Asserts |
|---|---|
| `test_rounding_matches_shipped_policy` | `quantize` equals `int(round(v / n * Q))` on 10,000 seeded values plus exact `.5` cases built from dyadic rationals |
| `test_rules_equal_independent_oracle` | 60 seeded tiny instances (N ≤ 6, S ≤ 20, W ≤ 7, R ≤ 3, integer coefficients): level sets, `tail_count`, `own_m_sum` of all six rules equal the tuple oracle |
| `test_oracle_instances_are_not_vacuous` | across the 60: some level set has size > 1 and some size 1; some rule's level differs from BALANCE's and some equals it; some instance where the tail is decided by `T` at equal `M`; some where summed `T` over a tail exceeds the largest single-world `T` (the case a too-small `BIG` gets wrong) |
| `test_encoding_base_is_only_a_device` | doubling `BIG` changes no level set and no decoded value; a `BIG` equal to the largest single total (too small) does change an oracle instance, proving the test can see the defect |
| `test_no_encoding_leaves_the_engine` | no field of `RuleOutcome`, `Evaluation` or any row dataclass holds a value `>= BIG` of its instance; `asdict` of every row has no key containing `encod`, `big` or `base` |
| `test_single_world_equals_balance` | `W = 1` with the world equal to the point values: every rule's level set equals BALANCE's (ROOT 2.5 invariant) |
| `test_worst_world_is_tail_one` | `WORST_WORLD` equals a `TAIL` with `k = 1`; `k == W_used` equals the sum over all used worlds |
| `test_regret_is_never_negative_and_zero_at_per_world_optimum` | |
| `test_discarded_world_is_ignored_and_counted` | values of an invalid world do not matter; `W_used < k` gives `usable=False` and an empty level |
| `test_world_order_candidate_order_selection_order_invariance` | permutations permute outputs only |
| `test_tiers_are_prefixes` | `evaluate_rules(tiers=(3, 5))[3]` equals a direct call with the first three worlds |
| `test_disappointment_is_integer_exact` | hand-built ties at `reference == reported` are not counted |

### 6.2 Synthetic generator, bridge, planted checks

| Test | Asserts |
|---|---|
| `test_geometry_incidence_counts` | 56 and 200 selections; each row has 3 and 10 picks; group quotas hold |
| `test_draws_are_seed_deterministic_and_stream_independent` | same seed → identical arrays; changing `worlds` does not change `latent` or `idiosyncratic` |
| `test_exposure_counts_and_alignment` | every candidate plays exactly his count; `WIDE_ALIGNED` gives the largest count to the largest latent mean; `FULL` plays all |
| `test_noise_scale_matches_declaration` | 20,000 trials, `rho in {0, 0.5}`: the SD of (point value − latent) for an `n`-match candidate is `noise_sd * sqrt(G / n)` within 3 % |
| `test_shared_effect_is_shared` | with `rho = 1` two candidates with identical exposure have identical (value − latent) in every world; with `rho = 0` they do not |
| `test_worlds_are_coherent` | one count vector per world feeds every candidate and requirement (poisoning one candidate's counts fails the test) |
| `test_zero_noise_has_zero_optimism_and_identical_rules` | `noise_sd = 0`: every rule's level set equals the true-optimal level set; optimism and regret are exactly 0 |
| `test_m05_bridge_within_tolerance` | `m05_bridge(config)["passed"]`: six columns × three noise levels within `bridge_tolerance` of `run_optimizer_curse.run()` |
| `test_planted_effect_recovered_and_classified` | for each of `planted_seeds` test seeds: (a) mean `delta_true(TRUTH_MIX)` within `planted_magnitude_standard_errors` SE of its planted target in every cell; (b) `decide_selection` returns `LESS_OPTIMISTIC_NOT_WORSE`; required in at least `planted_minimum_correct` seeds |
| `test_planted_cost_classified` | same seeds: precondition asserted (planted target `> planted_cost_margin_multiple * margin` in at least one compared cell); `decide_selection(RANDOM_MIX)` is `COSTS_TRUE_SHORTFALL` in at least `planted_minimum_correct` seeds |
| `test_planted_identity_is_inconclusive` | `IDENTICAL` has zero informative trials in every cell and `decide_selection` is `INCONCLUSIVE` for every seed |
| `test_random_set_shows_optimism_is_cheap` | `RANDOM_SET` has mean `optimism_point <= 0` and a larger `true_m` than BALANCE in the `HIGH` cells: the reference arm behaves as the protocol says |
| `test_a2_halves_partition_matches` | halves are disjoint, exhaustive, equal-sized; worlds of direction `d` put zero weight outside half `d` |
| `test_a2_zero_noise_has_zero_gap` | `noise_sd = 0`: held-out gap, true optimism, excess and both sum gaps are exactly 0 |
| `test_planted_sum_gap_is_recovered` | `planted_seeds` seeds at the highest primary noise: `decide_split_sample_diagnostic` returns `RECOVERS_SUM_GAP` in at least `planted_minimum_correct` seeds (unbiasedness of held-out sums, checked through the whole pipeline) |
| `test_leaky_halves_are_not_established` | `run_part_a2(..., leak_fraction=0.5)`: the recovery ratio falls outside the tolerance and the token is `NOT_ESTABLISHED` in at least `planted_minimum_correct` seeds: the planted failure the rule must catch |

### 6.3 Split machinery

| Test | Asserts |
|---|---|
| `test_enumeration_equals_bruteforce_permutations` | tiny formations (≤ 5 slots, ≤ 7 candidates, random eligibility, a `None` value, a zero-minute player): assignment count and distinct selections equal an `itertools.permutations` reference |
| `test_enumeration_rejects_mixed_requirement_slots` | `NotImplementedError` |
| `test_reference_level_ignores_requirement_values` | changing every value leaves `reference_level` unchanged |
| `test_fixed_selection_gap_is_antisymmetric` | on the synthetic corpus the `REFERENCE_PRIOR_MINUTES` gap in direction 0 equals minus direction 1 exactly (integers): the planted null of the split statistic |
| `test_selected_gap_is_positive_under_planted_noise` | `planted_split_corpora` synthetic corpora at `planted_split_noise_sd`, largest multiplier, `planted_split_random_splits` splits: BALANCE's mean gap `> 0` in at least `planted_split_minimum_correct` corpora; at `noise_sd = 0` it is exactly 0 |
| `test_planted_drift_separates_families` | synthetic corpus with a linear time trend: the `CHRONOLOGICAL` fixed-selection one-direction gap is non-zero while its `RANDOM` sum over both directions stays 0 |
| `test_split_planted_rules_classified` | `TRUTH_MIX` (target = held-out-optimal level) → `decide_split(..., diagnostic_valid=True)` is `HELD_OUT_GAP_SMALLER`; `RANDOM_MIX` → `HELD_OUT_SHORTFALL_LARGER` (precondition asserted); `IDENTICAL` → `INCONCLUSIVE`; each in at least `planted_split_minimum_correct` corpora |
| `test_structure_planted_check_passes_and_reads_no_numerator` | on a synthetic corpus: `structure_planted_check` passes; setting `inputs.numerators` to NaN changes nothing |
| `test_split_masks_are_seeded_balanced_and_order_free` | `G // 2` matches in A; same seed → same masks; shuffling input rows changes nothing |
| `test_half_worlds_resample_only_the_selecting_half` | zero counts outside the half; row sums equal the half size |
| `test_corpus_outcomes_need_the_protocol_hash` | `evaluate_snapshot` on inputs with `source="CORPUS"` raises `PermissionError` without, or with a wrong, `protocol_hash` (inputs built synthetically and relabelled) |
| `test_no_identifier_leaves_the_split` | sentinel ids of the synthetic corpus appear nowhere in `summarize_directions` output or in the encoded rehearsal result |
| `test_solver_audit_detects_a_wrong_answer` | stub solver returning an XI outside the level set, or a per-world pair off by one unit → `SolverAuditMismatch`; a correct stub passes; `FEASIBLE` is counted as uncertified; an item with a discarded world is skipped |
| `test_snapshot_parity_full_sample` (`slow`) | both shipped snapshots: `weighted_rates(inputs, ones)` equals `snapshot.candidates[*].values` within 1e-12 relative, and their quantised coefficients are identical integers |
| `test_snapshot_parity_shipped_worlds` (`slow`) | `weighted_rates(inputs, shared_match_weights(...)[1])` reproduces `build_snapshot(worlds=40).worlds` within 1e-12 relative with identical quantised coefficients |
| `test_snapshot_structure_matches_config` (`slow`) | 34 and 30 prior team matches, 16 candidates, 5,200 assignments, 480 player sets, three active requirements on one common slot set |

### 6.4 Decisions

| Test | Asserts |
|---|---|
| `test_selection_truth_table` | every combination of (valid?, compared count vs gate, `delta_true_low` vs margin, `delta_true_high` vs margin, `delta_optimism_high` vs 0) maps to exactly one token, equal to the protocol table; boundary values (`== margin`, `== 0`) included |
| `test_reporting_truth_table` | same; `MINIMAX_REGRET` → `NOT_APPLICABLE` before any other row |
| `test_diagnostic_truth_table` | all 81 sign combinations of the four intervals map to one of `AGREES` / `CONTRADICTS` / `UNRESOLVED`; `decide_diagnostic` thresholds |
| `test_split_truth_table` | gate, diagnostic, larger, smaller, otherwise; rows 3 and 4 cannot both hold; fewer than eight blocks → `INCONCLUSIVE` |
| `test_aggregation_and_risk_rule_are_total` | every tuple of component tokens aggregates to one value; all 4 × 5 pairs of `(S, P)` map to one token of the subject's vocabulary, equal to the protocol table |
| `test_risk_report_and_diagnostic_tokens_are_total` | including unresolved-cell gate and ratio bounds exactly at `1 ± tolerance` |
| `test_every_token_has_a_consequence_and_a_status` | for every subject: `verdict_vocabulary` ⊆ keys of its `product_consequences` family; every consequence key except `NOT_RUN` has a sentence in `consequence_sentences`; every token has a `display_status` |
| `test_array_null_false_positive_rate` | `planted_array_seeds` seeds: one valid, informative cell with per-trial `delta_true ~ N(0, planted_array_sd)`, `delta_optimism ~ N(0, planted_array_sd)`, `planted_array_trials` trials, intervals from `paired_interval`; `LESS_OPTIMISTIC_NOT_WORSE` in at most `planted_array_maximum_false_positive` seeds and `COSTS_TRUE_SHORTFALL` in at most the same number |
| `test_array_effect_recovery_rate` | same with `delta_optimism ~ N(planted_array_effect, planted_array_sd)`: `LESS_OPTIMISTIC_NOT_WORSE` in at least `planted_array_minimum_recovered` seeds |
| `test_identity_interval_is_not_evidence` | all-zero differences with zero informative trials → `INCONCLUSIVE`, never a pass on a `[0, 0]` interval (the E-08 lesson) |

### 6.5 Runner (`tests/test_risk_selection_experiment.py`)

| Test | Asserts |
|---|---|
| `test_config_contract` | every key the code reads exists and every config key is read (no dead key); an AST scan of `risk_selection.py` and the runner finds no numeric constant equal to the configured `seed`, `bootstrap_seed`, `rehearsal_seed`, `true_shortfall_margin`, `heldout_shortfall_margin`, `bridge_tolerance`, `minimum_used_directions` or `results_maximum_bytes`; cell counts equal the `expected_*` keys; exposure count vectors have length N and lie in `[2, G]`; `quantization` equals the shipped `QUANTIZATION`; `tail_counts` equal the ceilings of 0.10, 0.25, 0.50 of each tier |
| `test_protocol_names_only_config_keys` | every backticked token of `preregistration.md` matching `^[a-z][a-z0-9_]*$` is a key of `config.json` or a member of the explicit allowlist `PROTOCOL_TERMS` kept in the test |
| `test_protocol_prints_the_config_sentences` | every sentence inside every value of `consequence_sentences` and `non_claims` (split after a full stop followed by a space) occurs verbatim, after whitespace normalisation, in `preregistration.md`; the numbers inside the sentences equal `true_shortfall_margin`, `diagnostic_recovery_tolerance` and `decision_tiers` |
| `test_no_banned_label_words` | none of best, quality, rating, score, rank, weakness, vulnerability, dominance, momentum occurs as a whole word in any token, key, column, sentence or vocabulary of `config.json` and the module's constants |
| `test_encode_result_roundtrip_and_layout` | `json.loads(encode_result(x)) == x` after rounding; scalar lists on one line; NaN raises; LF only |
| `test_full_shape_artifact_fits` | a dummy result with the frozen table shapes filled with `-0.123456` encodes to at most `results_maximum_bytes` |
| `test_results_contract` | rehearsal result has `experiment`, `version`, `tier`, `provenance`, `verdicts` with exactly the six claim ids, each token inside its vocabulary; `providers == ["pappalardo"]`; `banned_key_paths` (HARDENING-H1 A2) is empty when that module exists; no forbidden key or column |
| `test_hashes_are_lf_normalised` | CRLF and LF copies of a text file hash equal; a binary file is hashed byte-exact |
| `test_frozen_run_requires_out_and_a_committed_protocol` | `main(["--execute-frozen"])` exits non-zero; with a monkeypatched `git` reporting a dirty protocol it raises before any computation; `--rehearsal` refuses an `--out` under the repo root |
| `test_rehearsal_runs_end_to_end` | `run(config, rehearsal=True)` with a divisor large enough to finish in under 60 s returns every top-level key and `"rehearsal": true` |
| `test_rehearsal_is_deterministic` | two rehearsal runs encode to identical bytes |
| `test_research_firewall` | no file under `galactico/api`, `galactico/optimization`, `galactico/profiles`, `galactico/match_lab`, `galactico/domain` contains `risk_selection` |
| `test_frozen_seed_is_not_used_in_tests` | neither test file contains the literal `seed` value of `config.json` |

Commands the implementer runs and reports:

```powershell
.venv\Scripts\python.exe -m pytest -q tests/test_risk_selection.py tests/test_risk_selection_experiment.py
.venv\Scripts\python.exe -m ruff check galactico/validation/risk_selection.py experiments/run_risk_selection.py tests/test_risk_selection.py tests/test_risk_selection_experiment.py
.venv\Scripts\python.exe -X utf8 experiments/run_risk_selection.py --rehearsal --out <scratchpad>\e13-rehearsal.json
```

## 7. Pre-outcome code review (an independent reviewer signs each line before the root runs)

1. The protocol and config in `experiments/preregistered/E-13-declared-risk-selection/`
   are byte-equal (after LF normalisation) to the council's reconciled files and are
   committed in commit P; no `results.json` exists in that commit or earlier.
2. Every test of section 6 exists under its name and passes; the planted suite passed
   **before** commit P and no threshold was touched afterwards.
3. No code path computes a real half-split or uses the frozen `seed` outside
   `run(..., rehearsal=False)`; the accessor guard test passes; the scratchpad and
   `git log -p` show no frozen-seed output.
4. The oracle compares tuples, forms no encoding and imports nothing from the module except
   the function under test. No encoding reaches a dataclass, a log line or the artifact.
5. Level sets, not representatives, feed every reported quantity; the only use of a first
   index is `BALANCE_FIRST`.
6. A discarded world is discarded for every rule and counted; no value is imputed; `k` is
   the tier's declared integer; an unmeasured candidate cannot reach a requirement-bearing
   slot (assertion present).
7. Rounding is `np.rint(v / n * Q)` in that order; targets use the same function;
   normalisers never move with the multiplier or the minimum level.
8. Common random numbers: one draw set per geometry; tiers are world prefixes; the
   bootstrap matrix is shared across cells and rules of a geometry.
9. Part B holds fixed the xT surface (`fit_prior_xt`), candidate set, eligibility, minima
   and normalisers; halves partition the team's prior matches; worlds resample the selecting
   half only; `structure_planted_check` runs before the first real numerator is evaluated
   and never reads one.
10. `RANDOM`, `ALTERNATING` and `CHRONOLOGICAL` are never pooled; decisions read `RANDOM`
    blocks at every multiplier, both snapshots, decision tiers only.
11. Decision functions take rows and return tokens; none reads a file, a seed or the clock;
    each matches its protocol table row for row; BEYOND_MENU, SENSITIVITY and STRESS rows
    reach no decision function except the sensitivity count.
12. The solver is imported lazily, only in `solver_audit`, only after `run_oracle_gate`
    returned; a mismatch raises before anything is written.
13. The writer emits no identifier, no wall-clock field and no NaN; the full-shape size
    test passes; `--verify-against` ignores only `determinism_excluded_keys`.
14. Hashes: text LF-normalised; data pinned by manifest digests; every `source_paths` file
    present; `protocol_commit` derived, never typed.
15. `ruff` clean; module docstrings state claim and non-claim; the banned-word test passes.
16. The firewall test passes; the registry holds six PENDING E-13 records whose
    vocabularies, consequence keys and sentences equal `config.json`.

## 8. Real execution (root only, once, after commit P and the review)

```powershell
.venv\Scripts\python.exe -X utf8 experiments/run_risk_selection.py --execute-frozen --out experiments/preregistered/E-13-declared-risk-selection/results.json
```

Determinism re-run (same machine, same environment; writes outside the repository):

```powershell
.venv\Scripts\python.exe -X utf8 experiments/run_risk_selection.py --execute-frozen --out <scratchpad>\e13-rerun.json --verify-against experiments/preregistered/E-13-declared-risk-selection/results.json
```

Exit 0 on both, then `analysis.md` in the house format (bold experiment token first; the
six claim tokens; the component table; the reference arms; the beyond-menu tier; the
audit status; "what this establishes / does not"; product consequence quoting the frozen
sentences; reproduction commands). Determinism is claimed for one machine: `weights @
values` may differ in the last bit across BLAS builds.

## ASSUMED INTERFACES

| # | Depends on | Assumed | Used where | If different |
|---|---|---|---|---|
| 1 | Declared-risk solver (`X-RISK`), `galactico/optimization/xi/risk.py` | one public solve function taking `candidates, requirements, formation, *, worlds, <rule>, <tail count k for TAIL>, locked=(), excluded=(), seed, time_limit, quantization`; a result exposing `solution_status` (`"OPTIMAL"` = certified), `assignments` (tuple of `Assignment`), the chosen XI's per-world `(M, T)` in integer quantised units or as floats that are exact multiples of `1 / Q`, and the used / discarded world ids. `WORST_WORLD` is callable as such or as `TAIL` with `k = 1` | `solver_audit` only, through two private adapters `_risk_call(rule, k, ...)` and `_risk_world_pairs(result) -> dict[int, tuple[int, int]]` | change the two adapters and `risk_solver_module`; nothing else |
| 2 | same | ROOT 2.5 O8 exactly, with one sharpening: the solver's `BIG` exceeds `k` times the largest possible total (or the sum over all used worlds), so that minimising the sum of the `k` largest encodings is minimising the pair (sum of `M`, sum of `T`) over the `k` lexicographically largest worlds. Half-even `_q` coefficients. A world is discarded when a non-excluded candidate lacks a value for an applicable active metric. `k` is the declared integer, not recomputed on the used worlds | enumeration engine | the audit will stop the run; reconcile before commit P |
| 3 | same | oracle test file `tests/test_xi_risk_oracle.py` (ARCH-SPEC 8.2); the product's menu is world counts {12, 40} and tail counts `ceil(0.10 W)`, `ceil(0.25 W)`, `ceil(0.50 W)` (PRODUCT-MATCHDAY 3.7 `tail_counts`) | `risk_solver_oracle_tests`, `decision_tiers`, `tail_counts` | edit the config keys before commit P |
| 4 | HARDENING-H1 D3, A2 | `galactico/validation/digests.py`: `lf_sha256(path) -> str`, `lf_sha256_text(text) -> str`; `galactico.domain.thesis.banned_key_paths(payload, *, allow=())` | provenance; one test | implementer reports the absence; does not write a second helper |
| 5 | Verdict registry (`F-REG`, ARCH-SPEC 3; PRODUCT-MATCHDAY A1) | six records with `experiment_id="E-13"`, subjects = keys of `subject_arms`, `vocabulary`, `consequences` (the family map restricted to the record's vocabulary plus PENDING), sentences from `consequence_sentences`; if the registry carries a display status, a claim token and a non-claim, they come from `display_status`, `claim_tokens`, `non_claims`. ARCH-SPEC 3.3's two E-13 keys are replaced by the ten keys of `consequence_sentences` (the spec allows the owning experiment to rename before commit P) | product copy | root's schema wins; tokens and sentences stay as frozen |
| 6 | XI Lab risk surface (PRODUCT-MATCHDAY 3.5, 3.8) | subject ids `risk_rule:WORST_WORLD`, `risk_rule:TAIL` (the product spec says `risk_rule:CVAR`; ROOT 2.5 O8 renamed the family), `risk_rule:MINIMAX_REGRET`; the badge word is `claim_tokens["risk_rule"]`, not "REDUCES OPTIMISM"; the `statement` is the registry sentence, not the draft sentences of 3.8; the `risk_report:*` sentence is printed as a figure note under the objective lines (none for MINIMAX_REGRET); rules are never ordered or preselected by token | protocol "Product consequence" | copy changes need a protocol amendment before commit P |
| 7 | HONEST EVALUATION tool (PRODUCT-MATCHDAY 3.6, A7; owner OR-XI) | its single split is `product_split_rule`: positions 0, 2, 4, … of the team's prior matches ordered by `(date, game_id)` form half A; half value `90 * sum(numerator) / sum(minutes)`; minima and normalisers from the snapshot; the route stays `WITHHELD` until the `split_sample_diagnostic` record is executed. E-13 does not import it | consistency only | reconciler checks the two definitions agree; a parity test is added if the product function exists before commit P |
| 8 | `galactico/optimization/snapshots.py` (`O-SNAP`) | not used. E-13 re-derives per-match components itself and parity-tests them against the frozen `build_snapshot` | 2.6 | if `O-SNAP` exposes parity-tested per-match components before commit P the reconciler may substitute it; not after |
| 9 | ARCH-SPEC 3.2 results contract | E-13 writes the contract's keys but with `encode_result` (scalar lists on one line) instead of plain `json.dumps(indent=2)`: with one number per line the frozen tables exceed 512 KB | writer | accept the writer, or cut the BEYOND_MENU and SENSITIVITY tables before commit P |
| 10 | `tests/conftest.py` | a shared corpus fixture exists and skips cleanly without data; name unknown | the three `slow` tests | module-level `skipif` on the `data_paths` files until INTERFACES.md names the fixture |

## DISSENT

1. **Engine of Part B (assignment wording, not a ROOT rule).** The assignment says the real
   part calls the risk solver; this design computes every Part B number by exhaustive
   enumeration and calls the solver on a frozen audit subset only. Evidence: the frozen
   design is 2 snapshots × 500 directions × 4 levels × 2 tiers × 6 rules = 48,000 solves;
   the maps measure 0.24–0.70 s for one BALANCE solve at quantisation 100,000 and the OR
   probe 1.1–2.3 s for one risk solve at 25 worlds: a day or more, against minutes for
   enumeration of the 5,200 feasible assignments. Enumeration also returns the level set,
   which a solver's single administrative representative cannot (at the default minima the
   full-prior BALANCE optimum is `(0, 0)` and BALANCE is indifferent among covered XIs:
   comparing a rule with an arbitrary representative would credit the rule with the
   tie-break). It follows M-05's own rule: "Exhaustive sets avoid reliance on the solver
   being audited." The solver still runs, must already have passed its oracle, and must
   reproduce the enumeration on 192 real instances or the run stops.
2. **ROOT 2.2 wording, "does worst-world / CVaR selection reduce the gap".** Under one
   common point report the reduction is mechanical for any rule that does not minimise the
   reported number (a random selection has none). The delivered rule lets the optimism
   criterion be necessary and puts the weight on the cost bound, says so in the frozen
   product sentence, and carries `RANDOM_SET` as the visible reference. For the same reason
   the badge word is "LESS OPTIMISTIC, NOT WORSE" rather than the product draft's "REDUCES
   OPTIMISM": the shorter name describes the cheap half of the numerator.
3. **ROOT 2.5 O8, size of `BIG`.** "Strictly larger than the largest possible total"
   preserves lexicographic order for one world (BALANCE, WORST_WORLD, MINIMAX_REGRET) but
   not for a sum of `k > 1` encodings: summed totals can carry into the `M` digit. E-13
   assumes `BIG` above the largest possible **sum** of totals and its oracle contains an
   instance that a smaller `BIG` gets wrong. If the solver keeps the smaller bound, TAIL is
   a different rule from the one described to the user, and the audit will say so.
4. **ROOT 2.5 O8 versus the product draft.** PRODUCT-MATCHDAY 3.5 still describes the
   withdrawn two-stage rules (separate tails for `M` and `T`, a second-stage gap that can be
   negative) and a `CVAR` alpha menu. E-13 implements O8: one tail, chosen by the pair,
   declared as an integer `k`. The product's tail counts at 12 and 40 worlds coincide with
   `tail_counts`, so only names and rule sentences need reconciling.
5. **A lower synthetic true shortfall earns no token.** If a rule's true shortfall is
   strictly lower than BALANCE's in every compared cell, that is recorded as a boolean and
   reported in `analysis.md` only. The alternative is a product sentence that will be read
   as "this rule picks the better team" on the strength of a Gaussian simulation.
6. **Subject-level `INCONCLUSIVE` comes first.** A failed gate in one component makes the
   subject inconclusive even if another component shows an established cost. This keeps
   `INCONCLUSIVE` meaning what the constitution says; component tokens are published so the
   cost stays visible in the research note. The opposite order is defensible; it was not
   chosen.
7. **The `split_sample_diagnostic` positive token is nearly a theorem.** Held-out sums are
   unbiased for a fixed selection under exchangeable matches, so `RECOVERS_SUM_GAP` mostly
   certifies the implementation (and the leaky-halves test shows the rule can fail). The
   informative part is the sentence it licenses about the shortfall line, which is biased,
   and Part B's split-to-split spread. If the council prefers no badge for a near-theorem,
   drop the claim and keep the sentence as static copy.

## OPEN QUESTIONS

1. Exact public names in `xi/risk.py` (interface 1) and whether its `BIG` meets interface 2.
2. Whether the registry stores a display status and claim token (ARCH-SPEC 3) or derives
   them (PRODUCT-MATCHDAY A1); both are supplied in `config.json`.
3. Whether the risk surface will offer 200 worlds later; the tier is computed and reported
   here but enters no token.
4. The planted suite's rates (`planted_minimum_correct` = all seeds) have not been run by
   the council (no code exists yet). If the implementer finds a planted check failing for a
   reason of design rather than code, that is reported to the root **before** commit P;
   after it no threshold moves.
5. Runtime and artifact-size estimates in 2.5 and 4 are arithmetic, not measurements.
