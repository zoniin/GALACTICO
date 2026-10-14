# OR-XI specification: ceilings, minimal conflict, frontier, declared-risk modes

Build contract for the four exact XI tools of ROOT-DECISIONS 2.1, the router that serves
them and the XI Lab page parts of 2.3. The binding rules are ROOT-DECISIONS sections 1
(R1-R13), 2.1, 2.3, 2.4, 2.5 (O7, O8, O12, O13, H10), 3b and 4, ADR-0018 to ADR-0029 and
KNOWN_LIMITATIONS. Where this file and those rules or the shipped code disagree, the rules
and the code win and the disagreement is a defect to report (ROOT 2.6). Points where this
file departs from the wording of a ruling, and why, are under DISSENT.

**Status.** Draft by the OR-XI designer, 14 October 2026, written after the council was cut
short. Revised the same day after three adversarial reviews (exactness, constitution,
product); every finding and its disposition is in the Review record at the end. Not audited,
nothing built. Every claim about the shipped code below was read from the tree at `25128e8`;
line numbers refer to it.

**Gates before building.** Three parts wait for a root ruling, and each has a specified path
that satisfies the rules as they stand (section 11, items 13 to 15): the half-even conflict
variant `explain_solve` (DISSENT 2; until the ruling only the conservative `explain_floors` is
built and the page explains with it), the five additive edits to `web/xi.html` (DISSENT 4; if
refused, the stand-alone page of 8.4), and `xi.risk.tail` as a long route (section 12;
`runtime.py` and the test that pins `LONG_ROUTES` are shared files; whatever the answer, the
40-world option ships only after its solves are timed).

**What the four tools are.** Exact computation on a declared model, the first of the three
kinds of deliverable ROOT section 0 allows. Each has a written decision claim, a certificate,
and an independent brute-force oracle. None makes an empirical claim, and none changes what
`solve_xi`, `maximize_requirement`, `bootstrap_selection` or any shipped endpoint returns
(R13).

## 0. Files and ownership

| File | New | Owner | Content |
|---|---|---|---|
| `galactico/optimization/xi/ceilings.py` | yes | OR-XI A | least and largest sum of each requirement in force over the declared XIs (section 2) |
| `galactico/optimization/xi/conflict.py` | yes | OR-XI A | certified minimal conflicting set of declarations (section 3) |
| `galactico/optimization/xi/frontier.py` | yes | OR-XI B | complete nondominated requirement-sum vectors with one witness each (section 4) |
| `galactico/optimization/xi/risk.py` | yes | OR-XI C | TAIL(k of B), WORST_WORLD, MINIMAX_REGRET over shared worlds (section 5) |
| `galactico/api/xi_extensions.py` | yes | OR-XI D | the router, request models, the gated snapshot loader, envelope, ledger, copy (section 7) |
| `web/xi-extensions.js`, `web/xi-extensions.css` | yes | OR-XI D | the XI Lab page parts (section 8) |
| `web/xi-extensions.html` | only on the fallback | OR-XI D | the stand-alone page of 8.4, built only if the root refuses the `xi.html` edits |
| `tests/xi_exact_oracle.py` | yes | by part (section 6) | the brute-force oracle shared by the four tool test files; not collected by pytest. Each part is written by a builder who does not implement the tool it checks: the shared core by D, the CEILING and CONFLICT parts by C, the FRONTIER part by A, the RISK part by B (ROOT 4: an oracle independent of the code it checks) |
| `tests/test_xi_ceilings.py`, `tests/test_xi_conflict.py` | yes | OR-XI A | section 9 |
| `tests/test_xi_frontier.py` | yes | OR-XI B | section 9 |
| `tests/test_xi_risk.py`, `tests/test_xi_risk_oracle.py` | yes | OR-XI C | section 9. The second name is the one the E-13 draft pins in `risk_solver_oracle_tests`; the oracle file it imports must be pinned beside it (section 13) |
| `tests/test_xi_extensions_api.py`, `tests/test_xi_extensions_render.py`, `e2e/xi-extensions.spec.js` | yes | OR-XI D | section 9 |
| `docs/research/north-star/OR-XI-SPEC.md` | yes | this designer | this file |

Four builders (A to D) can work in parallel against the dataclasses fixed in sections 2 to 5.
D builds against those dataclasses with stub tools until A to C land.

**Frozen, never edited, never re-imported for a new purpose that changes their bytes:**
`galactico/optimization/historical.py`, `galactico/optimization/xi/domain.py`,
`galactico/optimization/xi/solver.py`, `galactico/optimization/xi/tradeoffs.py`,
`galactico/models/xt/grid.py` (ROOT 3b). Their bytes are hashed into every hard-floor input
fingerprint (`tradeoffs._source_fingerprints`, tradeoffs.py:69-75), into the kernel's input
contract (kernel.py:79, pinned by `tests/test_squad_kernel.py`), and, for `historical.py`,
into E-08's published `results.json`.

**Not edited either, although not frozen:** `galactico/optimization/squad/kernel.py`. Its
source fingerprint is in the input contract of every Squad Lab and Transfer Lab certificate
(kernel.py:425-427); an edit would change those served hashes (R13). The new modules use its
private members, as `squad/brief.py` already does (brief.py:47-57, 299-414).

**Owned by the root, changed only by request (section 12):** `galactico/api/player_lab.py`
(router registration), `web/xi.html` (five additive edits), `galactico/api/runtime.py` and
`tests/test_lab_runtime.py` (one long route), `web/labs-shared.js` (an optional id prefix for
`Shell.ledger`, not required), every top-level `*.md`, `galactico/optimization/xi/__init__.py`
(no change requested), `ROOT-DECISIONS.md`, `docs/research/north-star/README.md`.

**Reused, unchanged:**

| Reuse | From | How |
|---|---|---|
| `Candidate`, `TacticalRequirement`, `Formation`, `Slot`, `FORMATIONS` | `xi/domain.py` | the input types of every tool |
| `_eligible`, `_applies`, `_q`, `_fingerprint`, `QUANTIZATION` | `xi/solver.py` | eligibility, applicability, the shortfall rounding, the world fingerprint, the scale |
| `_scaled`, `_finite`, `FLOOR_POLICY`, `OBJECTIVE_POLICY`, `MAX_MAGNITUDE`, `MAX_EXPRESSION_MAGNITUDE` | `xi/tradeoffs.py` | exact scaling, input checks, the two exact policies and their limits |
| `ShortfallKernel` and its `_background`, `_tables`, `_expression`, `_witness`, `_admissible`, `_shortfalls`; `_Run`, `_at_least`, `value`, `fingerprint`, `source_fingerprints`, `scrub_lineage`, `Membership`, `Lineup`, `SHORTFALL_POLICY`, `HARD_POLICY`, `PER_SOLVE_DETERMINISTIC_LIMIT` | `squad/kernel.py` | the background model, coefficient tables, witnesses, the deterministic per-solve limit and the per-world BALANCE optima |
| `EXPERIMENTAL_OPT_IN_ERROR` | `optimization/snapshots.py:110` | the one refusal sentence for a side requirement without the opt-in |
| `runtime.budget_for`, `lab_errors`, `cache_key`, `RESULTS`, `long_job`, `finalize`, `respond`, `is_complete`, `match_scenario`, `WORLD_MENU`, `HOSTED_PROVIDERS` | `api/runtime.py` | every rule of a new route (ADR-0024). `runtime.match_snapshot` is not used: it reaches `decision_lab.snapshot`, an `lru_cache` outside the build gate (7.3) |
| `SCENARIOS`, `decision_inputs`, `DecisionRoute` | `api/decision_lab.py` | the scenario table, the shipped XI model, 422 bodies without input values |
| `load_snapshot`, `SEED` | `optimization/historical.py` (imported, never edited) | the build of a match snapshot, called by the gated loader of 7.3 exactly as `decision_lab.snapshot` calls it |
| `declared_row`, `ledger_row`, `evidence_payload`, `verdict_payload` | `api/shell.py` | the O12 ledger and the O13 badges |
| `_outward`, `corpus_token`, `FLAGSHIP`, `_built_once` | `api/planning.py` | outward printing at four decimals, the cheap corpus identity of a cache key, and the ADR-0024 build gate |
| `window.Shell` | `web/labs-shared.js` | badges, ledger, error, infeasible and not-certified markup |

**Engineering (ROOT section 4).** `from __future__ import annotations`; frozen dataclasses;
full type hints; `__all__`; ruff clean at line length 100 (E, F, I, UP, B, SIM); a module
docstring whose first paragraph states the claim and the non-claim. No tool imports
`solve_xi`, `maximize_requirement`, `bootstrap_selection`, `removal_sensitivity` or
`candidate_injection`: the kernel does what they would do in a loop (ROOT 2.6 D5, D6). No tool
reads a data file or an environment variable, or a clock other than `time.monotonic`; the only
files a tool reads are its own source and the kernel's sources, to fingerprint them
(`kernel.source_fingerprints`, kernel.py:225-238). Tests skip cleanly without the corpus.

## 1. The declared model, the three shipped integer policies, worlds and time

### 1.1 Notation

A request declares: a formation with slots `S` in formation order, each with allowed
positions; a candidate set `C` (the gated players of the snapshot, sorted by `player_id`),
each with a position, minutes, an optional `eligible_slots` tuple and a value table
`v_p[metric]` (a finite float or `None`); locks `L ⊆ C`; exclusions `X ⊆ C`; the requirements
in force `R` (section 1.5), each with a metric `μ_r`, a minimum `m_r`, a normaliser `n_r > 0`
and an applicability set `A_r` (empty means every slot); optionally hard floors `φ_r` for some
`r ∈ R`; the quantisation `q` (always `QUANTIZATION = 100000` from the API); and, for the risk
modes, a world count `B`.

| Symbol | Exact definition |
|---|---|
| `Eligible(p, s)` | `solver._eligible`: `minutes_p > 0`, position in the slot's allowed positions, and `eligible_slots` is `None` or holds `s` |
| `applies(r, s)` | `solver._applies`: `A_r` empty or `s ∈ A_r` |
| admissible key `(p, s)` under a value table `V` | `Eligible(p, s)` and no `r ∈ R` with `applies(r, s)` has `V_p[μ_r] is None`. A missing measurement forbids the assignment; nothing is imputed (solver.py:202-215, kernel.py:506-508) |
| XI, `x` | a map `S → C` whose every pair is an admissible key, injective, with `L ⊆ x(S)` and `x(S) ∩ X = ∅` |
| assignment | a partial injective map from `S` to `C` whose every pair is an admissible key: slots may be empty and nothing is said about `L` or `X`. An XI is an assignment that fills every slot, holds every locked player and no excluded one. CONFLICT tests sets of declarations by assignments (section 3); every other tool speaks of XIs only |
| `𝒳(D)` | the set of XIs under the declarations `D` |
| `a_r` | the number of slots `s ∈ S` with `applies(r, s)` |
| `S_r(x)` | `Σ_{s : applies(r, s)} Fraction(v_{x(s)}[μ_r])`, exact |

### 1.2 Three shipped integer policies, and which quantity uses which

ROOT 2.4 says new solvers reuse the shipped policies, name which applies to which quantity,
and invent no third. The shipped code has three named rules, not two (DISSENT 1). None is new.

| Policy | Shipped at | Coefficient of a value `v` | Target of a minimum `m` | Exactness |
|---|---|---|---|---|
| `SHORTFALL_POLICY` (`kernel.SHORTFALL_POLICY`; `solve_xi`'s `rounding`) | `solver._q`, solver.py:52-54, used at 264-271 | `int(round(v / n * q))`: float division, then Python's half-even | `int(round(m / n * q))` | `d_r(x) = max(0, t_r − f_r(x))`, `M = max_r d_r`, `T = Σ_r d_r` are BALANCE's two stages exactly |
| `HARD_POLICY = tradeoffs.FLOOR_POLICY` | tradeoffs.py:302, 308; `kernel._tables(conservative=True)` | `floor(Fraction(v) / Fraction(n) · q)` | `ceil(Fraction(m) / Fraction(n) · q)` | `f ≥ t ⇒ S_r(x) ≥ m` exactly; an XI within `(a_r + 1) · n_r / q` of the floor can be excluded (tradeoffs.py:215-230) |
| `OBJECTIVE_POLICY = tradeoffs.OBJECTIVE_POLICY` | tradeoffs.py:307 | `round(Fraction(v) / Fraction(n) · q)`: exact, half-even | none | `|S_r(x) − (n_r / q) · f_r(x)| ≤ a_r · n_r / (2q)` for every XI |

`_q` and `OBJECTIVE_POLICY` are both half-even and differ only in when the rounding happens
(after a float division, or on the exact fraction). They disagree on about 185 of 200,000
random coefficients; for example `1.344465 / 1.0` at `q = 100000` is 134446 by `_q` and 134447
exactly. `tests/test_squad_kernel.py:639` pins that they differ in general; its slow K9 test
pins that they coincide on the Madrid data and worlds. The new tools never mix them inside
one quantity:

| Quantity | Tool | Policy | Why this one |
|---|---|---|---|
| sums maximised and minimised | CEILING | `OBJECTIVE_POLICY` | the shipped maximiser's objective (tradeoffs.py:307); O7's "shipped quantisation with exact Fraction arithmetic"; the same rounding `planning.attained` already serves |
| sums of the nondominated vectors | FRONTIER | `OBJECTIVE_POLICY` | O7, word for word |
| every hard floor the reader declares, and the minima of a Satisfy solve the page explains | CEILING, FRONTIER, CONFLICT (`explain_floors`) | `HARD_POLICY` | ROOT 2.4: hard constraints are conservative; a returned XI meets the raw floor exactly |
| the minima of a Satisfy solve, in that solve's own arithmetic | CONFLICT (`explain_solve`), **gated**: specified here, built and routed only after the root amends 2.4 (DISSENT 2; section 11, item 13) | `SHORTFALL_POLICY` | the arithmetic of the solve it explains: `solve_xi` enforces Satisfy minima as `Σ _q(...) ≥ _q(m)` (solver.py:274-275), not conservatively (the principle of ROOT 2.6 D2) |
| per-world shortfalls `d_r^w`, `M^w`, `T^w` | RISK | `SHORTFALL_POLICY` | ROOT 2.6 D8 and the single-world invariant: with one world a risk mode returns BALANCE's pair, and BALANCE rounds with `_q`. Shortfalls are an objective, not a hard constraint |

Half-even infeasibility implies conservative infeasibility, not the converse: a conservative
coefficient `floor(v / n · q)` (exact) is never above `_q(v, n, q)` and a conservative target
`ceil(m / n · q)` is never below `_q(m, n, q)`, because the float error of `_q` is far below one
half. So an XI meeting a set of minima conservatively meets it half-even, and a Satisfy solve
that is INFEASIBLE is INFEASIBLE in the conservative model too: `explain_floors` on the same
declarations always finds a conflict to show. That conflict is certified in the conservative
model only; under the solve's half-even comparison the same set may hold together, and the
page says so (`CONFLICT_CONSERVATIVE_FOR_SOLVE`, 7.7). Each response names its arithmetic.

### 1.3 Requirements in force and the experimental opt-in

XI Lab's shipped model (`decision_lab.decision_inputs`, decision_lab.py:241-333) makes three
requirements active: `progression` (legacy `HEURISTIC`, domain `HEURISTIC`) and the two side
pass-origin rates (legacy `RESEARCH`, domain `EXPERIMENTAL`), with normaliser equal to the
snapshot's default minimum. ADR-0001 says an `EXPERIMENTAL` number never renders without an
explicit opt-in; ADR-0019 kept the shipped XI Lab as it is and put new planning surfaces on
progression alone; O7 puts the side rates behind an opt-in for the frontier. Every new XI
request therefore carries `experimental_opt_in` (default false):

- without it, the router takes `decision_inputs(...)` and replaces each of
  `left_pass_origins` and `right_pass_origins` by `dataclasses.replace(r, status="research",
  hard=False)`: present, named, inactive in every solve (the rule of
  `snapshots.snapshot_inputs`, snapshots.py:857-964). A minimum, a floor or a dimension naming
  either is refused with `EXPERIMENTAL_OPT_IN_ERROR`, never ignored;
- with it, both side requirements are in force together, as in planning ("One cannot be
  declared without the other", KNOWN_LIMITATIONS).

`R` is the set of requirements with `active` true after this step. The unavailable
requirements (`chance_creation`, `rest_defense`, `goalkeeping`) stay `UNMEASURED` as shipped.
Consequence, stated on the page: with the shipped requirement set a frontier of two or more
dimensions needs the opt-in, and a conflict that explains the main solve needs it whenever the
main solve had the side requirements in force, which is always (DISSENT 5, OPEN QUESTION 1).
The router enforces the second: `explains: "solve"` (once routed) is refused without the
opt-in with its own sentence (`CONFLICT_SOLVE_NEEDS_OPT_IN`), because without it the tool would
explain a model in which the side requirements are inactive, which is not the solve the reader
saw. A test asserts that `explain_solve`'s requirements in force equal `solve_xi`'s active set
on the same declarations.

Without the opt-in, the ceilings and risk panels answer on a model that holds progression
alone while the main solve above them holds three requirements. Each such reply carries the
sentence `MODEL_DIFFERS` (7.7), naming both sets, whenever they differ. The page never sends
a side minimum without the opt-in; it filters the main solve's minima by the server's list of
requirements (8.2), and says that the side minima are not part of the question.

### 1.4 Worlds

Used by the risk modes only.

| Item | Exact definition |
|---|---|
| source | the router's gated loader `_match_snapshot(scenario_id, B)` (7.3) with `B ∈ runtime.WORLD_MENU = (12, 40)`: `historical.load_snapshot(match_id, worlds=B, seed=historical.SEED)`, the call `decision_lab.snapshot` makes, behind the ADR-0024 build gate. It is not the object `/api/xi/solve` holds; it is built by the same function from the same files and seed. 200 worlds are not offered (`PRECOMPUTED_WORLDS` is a result-store tier, not a computation) |
| world ids | `0 .. B − 1`, the keys of `snap.worlds`, kept as integers |
| world vector | whole-vector replacement, never a merge (solver.py:550): `V^w_p = dict(worlds[w].get(p, {}))` for **every** candidate. `kernel._background` keeps a player's own vector when he is absent from `values` (kernel.py:468-482), so `risk.py` always passes a complete mapping, in which absence means every metric `None`, as `bootstrap_selection` reads it |
| discard rule | world `w` is discarded iff some `p ∉ X`, some slot `s` with `Eligible(p, s)` and some `r ∈ R` with `applies(r, s)` have `V^w_p[μ_r] is None` (solver.py:549-564). Locks and the point-estimate measurement rule play no part. Recorded as `{"world_id": w, "reason": "missing shared-world exposure"}`, the shipped string |
| used worlds `U` | the others, ascending. `k` and `B` are never recomputed on `|U|` |
| lemma | for every `w ∈ U` the admissible keys under `V^w` are exactly the keys with `Eligible(p, s)` and `p ∉ X`, so `𝒳` is the same set in every used world. `risk.py` asserts it (a `RuntimeError` if not) |
| world fingerprint | `solver._fingerprint(snap.worlds)` over all `B` worlds, discarded ones included: the function and input of `bootstrap_world_fingerprint` (solver.py:609). For `B = 12`, when both snapshots are built from the same files, it equals the fingerprint the main solve on the same scenario carries: a fact of construction, tested on the corpus (slow test), never checked per request. Equal fingerprints say the worlds were drawn alike; they do not say which worlds the main solve's selection frequencies use: those are only the worlds it certified under its own decision rule and requirements (`bootstrap_used_worlds`, solver.py:566-568) |
| prefix property | `shared_match_weights` draws all replicates from one generator with `multinomial(..., size=B)` (profiles/uncertainty.py:139-141), which draws rows in sequence: the first 12 of the 40 worlds are the 12 worlds, row for row (checked under numpy 2.5.3). A structure test pins it to the installed numpy version; while it holds, the 40-world certificate may say that the main solve's 12 worlds are its worlds 0 to 11 (`RISK_PREFIX`, 7.7) |
| seeds | the world seed is `snap.provenance["seed"]` (`historical.SEED`); the solver seed is `historical.SEED` too, as `decision_lab` passes it. The router passes the world seed and `snap.provenance["bootstrap_version"]` to every risk function as the keyword arguments `world_seed` and `bootstrap_version` (5.7) |

### 1.5 Deadlines, deterministic time, statuses, completeness

Every tool takes `deadline: float`, a `time.monotonic()` value, as the kernel does. The router
passes `time.monotonic() + budget.remaining()`. Every CP-SAT call is made through
`kernel._Run(deadline, seed)` (one worker, the seed, `max_deterministic_time =
PER_SOLVE_DETERMINISTIC_LIMIT = 10.0`, `max_time_in_seconds = max(0.001, deadline − now)`),
except the two risk solve kinds of section 5.6, which use `risk._solver` with the same four
settings and the deterministic limit `SELECTION_DETERMINISTIC_LIMIT = 40.0`. Both limits are in
every certificate. `_Run.solve` returns `("UNKNOWN", None)` without a call when the deadline
has passed; every tool records that call as `NOT_RUN`, never as `UNKNOWN`.

| Rule | Text |
|---|---|
| statuses | `OPTIMAL`, `FEASIBLE`, `INFEASIBLE`, `UNKNOWN`, `MODEL_INVALID`, `NOT_RUN`, one per call, in call order |
| undecided | `UNKNOWN` and `NOT_RUN` are never evidence of absence: no tool turns them into "no XI", "no further point", "not needed" or a value |
| incumbents | a `FEASIBLE` incumbent of an optimisation is not an optimum. FRONTIER and RISK never report one. CEILING reports it as `FEASIBLE_NOT_PROVEN` with the solver's bound, which still brackets every sum (section 2.4), as the shipped maximiser does (tradeoffs.py:417-421) |
| completeness | `EXACT` (every statement proved), `COMPLETE` (an enumeration proved complete), `LIMIT_REACHED`, `DEADLINE`, `MODEL_INVALID`; no other token, in any block. `runtime.is_complete` caches a reply only when every `completeness` value in it is `EXACT` or `COMPLETE` |
| proved terminal outcomes | an outcome proved without a solve or by an INFEASIBLE proof is complete: `UNFIELDABLE` and `NOT_SATISFIABLE` (CEILING, FRONTIER, RISK), `NOT_EVALUABLE` (RISK) and `MODEL_FEASIBLE` (CONFLICT) carry `EXACT` (the frontier's empty set `COMPLETE`); a membership block that is vacuous because no selection exists is `EXACT` with no rows. Each is cached like any exact reply, and a test calls `is_complete` on each |
| which limit stopped a call | for every CP-SAT call a tool makes itself, the solver's `wall_time` and `deterministic_time` (from the response) are recorded in the tool's provenance (`*_solve_times`; times are not encodings). An undecided call stopped at its deterministic limit (`deterministic_time ≥` the limit, wall clock not exhausted) is load-independent and gives `LIMIT_REACHED`; one the wall clock stopped, or a call not made (`NOT_RUN`), gives `DEADLINE`. Calls made inside `kernel.value` expose no solver and count as `DEADLINE`. A certificate with an undecided call names which stopped it in `stopped_by` (`DETERMINISTIC_LIMIT`, `WALL_CLOCK`, or for FRONTIER also `POINT_LIMIT`) |
| wall clock | the wall-clock budget can stop a solve before its deterministic limit. Such a status is load-dependent; it is reported as `DEADLINE`. Neither `DEADLINE` nor `LIMIT_REACHED` is cached, so a load-dependent answer is never stored |

### 1.6 Prior exposure (ROOT 2.5, 4.4)

Two exact computations on the default Madrid model were seen before this design: the
three-dimensional frontier has 12 nondominated points over 480 feasible player sets, and the
removal table. They are disclosed here. No constant, grid, limit, floor, tolerance or test
expectation in this file is derived from them: `MAX_FRONTIER_POINTS = 64` mirrors
`brief.MAX_BRIEF_ROWS`, the tail menu is the E-13 draft's, and the slow tests compare with a
brute-force enumeration on the real snapshot rather than pinning a count.

## 2. CEILING: `galactico/optimization/xi/ceilings.py`

Design claim (a note for the builder, never served; the served `claim` and `non_claim` fields
are the 7.7 constants `CEILING_CLAIM` and `CEILING_NON_CLAIM`, defined in `ceilings.py` and
re-exported by the router, word for word; the same rule holds for every tool): for each
requirement in force, the least and the largest sum any XI reaches under the eligibility
rules, locks, exclusions and declared hard floors, each with one XI that reaches it,
bracketed exactly. Each range is over all XIs for one requirement alone; a sum is arithmetic
on prior rates, not a forecast, and neither end is a target.

### 2.1 Definition

`𝒳_F = { x ∈ 𝒳(D) : Σ_{s : applies(r, s)} floor_H(v_{x(s)}[μ_r]) ≥ ceil_H(φ_r) for every floored r }`
(HARD_POLICY). For each `r ∈ R`, with `O_r(x) = Σ_{s : applies(r, s)} round(Fraction(v_{x(s)}[μ_r]) / Fraction(n_r) · q)`
(OBJECTIVE_POLICY) and `e_r = a_r · n_r / (2q)`:

| Quantity | Definition |
|---|---|
| `I⁺_r`, `x⁺_r` | `max_{x ∈ 𝒳_F} O_r(x)` and one XI attaining it |
| `I⁻_r`, `x⁻_r` | `min_{x ∈ 𝒳_F} O_r(x)` and one XI attaining it |
| largest raw sum `R⁺_r = max_{x ∈ 𝒳_F} S_r(x)` | lies in `[S_r(x⁺_r), (n_r / q) · I⁺_r + e_r]`: the left end is attained by `x⁺_r`; the right end bounds every `S_r(x)` because `S_r(x) ≤ (n_r / q) · O_r(x) + e_r ≤ (n_r / q) · I⁺_r + e_r` |
| least raw sum `R⁻_r` | lies in `[(n_r / q) · I⁻_r − e_r, S_r(x⁻_r)]`, symmetrically |
| bracket | every `x ∈ 𝒳_F` has `(n_r / q) · I⁻_r − e_r ≤ S_r(x) ≤ (n_r / q) · I⁺_r + e_r` |

Two facts are reported against the declared minimum `m_r` (the main solve's minimum, compared
exactly in `Fraction`; a floor is a different declaration). `m_r` is read from the
`requirements` argument as passed, never from the floored copy `requirements′` of 2.3 step 1,
whose `minimum` is `φ_r`; a test with `φ_r ≠ m_r` asserts it:

| Field | True | False | None |
|---|---|---|---|
| `minimum_reached_by_some_xi` | `S_r(x⁺_r) ≥ m_r` (witness `x⁺_r`) | `(n_r / q) · J⁺_r + e_r < m_r` with `J⁺_r` the proved integer upper bound of the LARGEST end | neither |
| `minimum_missed_by_some_xi` | `S_r(x⁻_r) < m_r` (witness `x⁻_r`) | `(n_r / q) · J⁻_r − e_r ≥ m_r`, `J⁻_r` the proved integer lower bound of the LEAST end | neither |

A witness decides True and a proved bound decides False whatever the end's certification: a
`FEASIBLE_NOT_PROVEN` end has both (its incumbent is an XI and CP-SAT's bound is proved), so it
decides a fact whenever either does. A `NO_SOLUTION` end decides nothing. `None` has two
causes, and the router serves a different sentence for each (`reason` beside the fact:
`ALLOWANCE` when the end has a witness and a bound and `m_r` lies between them, `NOT_CERTIFIED`
when the end is `NO_SOLUTION`); 7.7 has the four sentences.

They are per requirement and marginal. Two minima reachable one at a time say nothing about
reaching both; the page says so.

### 2.2 Interface

```python
CEILING_VERSION = "requirement-sum-range-v1"
DIRECTIONS = ("LARGEST", "LEAST")

@dataclass(frozen=True)
class SumEnd:
    direction: str                 # LARGEST | LEAST
    solver_status: str             # status of the one solve of this end, or NOT_RUN
    certification: str             # QUANTIZED_OPTIMAL | FEASIBLE_NOT_PROVEN | NO_SOLUTION
    integer_value: int | None      # O_r of the witness, OBJECTIVE_POLICY units of n_r / q
    integer_bound: int | None      # I± when QUANTIZED_OPTIMAL; the solver's bound when FEASIBLE_NOT_PROVEN
    attained: float | None         # S_r(witness), the float nearest the exact sum (never printed: 7.5)
    raw_bound: float | None        # (n_r / q)·integer_bound ± e_r, rounded outward with math.nextafter
    lineup: Lineup                 # the witness, (slot_id, player_id) in formation order; () when none

@dataclass(frozen=True)
class RequirementRange:
    requirement_id: str
    label: str
    metric: str
    # no evidence field: the router adds the composed domain class per range (7.6); the legacy
    # XI string ("HEURISTIC", "RESEARCH") is never served outside provenance (ROOT 3b, O13)
    applicable_slots: int          # a_r
    normalizer: float
    minimum: float                 # m_r from the unmodified requirements, compared only
    raw_rounding_error_bound: float   # e_r, math.nextafter outward (tradeoffs.py:145-148)
    largest: SumEnd
    least: SumEnd
    minimum_reached_by_some_xi: bool | None
    minimum_reached_reason: str | None    # None | ALLOWANCE | NOT_CERTIFIED (2.1)
    minimum_missed_by_some_xi: bool | None
    minimum_missed_reason: str | None

@dataclass(frozen=True)
class CeilingCertificate:
    feasible_set: str              # FIELDABLE | UNFIELDABLE | NOT_SATISFIABLE | UNKNOWN | MODEL_INVALID
    solves: int
    statuses: tuple[str, ...]      # every call, in call order
    completeness: str              # EXACT | LIMIT_REACHED | DEADLINE | MODEL_INVALID (1.5)
    stopped_by: str | None         # DETERMINISTIC_LIMIT | WALL_CLOCK; None when nothing is undecided
    quantization: int
    objective_policy: str          # tradeoffs.OBJECTIVE_POLICY
    hard_policy: str               # kernel.HARD_POLICY
    per_solve_deterministic_limit: float
    witnesses_verified: bool       # every witness re-evaluated without the solver

@dataclass(frozen=True)
class CeilingResult:
    formation: str
    ranges: tuple[RequirementRange, ...]      # requirement_id ascending
    floors: tuple[tuple[str, float], ...]     # (requirement_id, φ_r) ascending; () when none
    locked: tuple[int, ...]
    excluded: tuple[int, ...]
    certificate: CeilingCertificate
    claim: str                                # CEILING_CLAIM, word for word
    non_claim: str                            # CEILING_NON_CLAIM, word for word
    reasons: tuple[str, ...]                  # kernel reasons by construction; diagnostic only
    provenance: dict

def requirement_ranges(
    candidates: Sequence[Candidate],
    requirements: Sequence[TacticalRequirement],
    formation: str | Formation = "4-3-3",
    *,
    floors: Mapping[str, float] | None = None,
    locked: Collection[int] = (),
    excluded: Collection[int] = (),
    seed: int = 20260906,
    quantization: int = QUANTIZATION,
    deadline: float,
    provenance: Mapping | None = None,
) -> CeilingResult
```

`floors` keys must be active requirement ids (`ValueError` otherwise), values finite and at
most `MAX_MAGNITUDE`. Every other input is validated by `ShortfallKernel.__init__` and
`_background` (unknown ids, duplicates, non-finite values, unknown slots).

### 2.3 Formulation

1. `kernel = ShortfallKernel(candidates, requirements′, formation, quantization=q, seed=seed)`
   with `requirements′` the requirements in which each floored `r` has `minimum = φ_r`
   (`dataclasses.replace`; only the floored tables are read, so the other minima do not
   matter; the minimum facts read `m_r` from the unmodified `requirements`).
   `β = kernel._background(excluded, locked, None, (), None)`.
2. If the deadline has passed: every end `NOT_RUN`, `feasible_set = UNKNOWN`, completeness
   `DEADLINE`. If `β.model is None`: `feasible_set = UNFIELDABLE` with `β.reasons`, no
   solve, completeness `EXACT`.
3. `H = kernel._tables(β, conservative=True)`; region `= β.model.clone()` plus
   `_at_least(region, kernel._expression(β, H[r][0]), H[r][1])` for each floored `r`.
4. Objective coefficients, mirroring tradeoffs.py:299-312: for each key `(p, s)` of
   `β.variables` with `applies(r, s)`, `c = round(_scaled(β.vectors[p][μ_r], n_r, q))`;
   `|c| > MAX_MAGNITUDE` or `Σ|c| ≥ MAX_EXPRESSION_MAGNITUDE` is a `ValueError` naming no value.
5. For `r` in requirement-id order: one clone maximising `Σ c·x`, then one minimising it.
   At most `2·|R|` solves, plus one (step 6).
6. The first solve that is `INFEASIBLE` ends the tool: with no floor, `feasible_set =
   UNFIELDABLE`; with floors, one solve of `β.model` decides `UNFIELDABLE` (INFEASIBLE) or
   `NOT_SATISFIABLE` (a witness), else `UNKNOWN` / `MODEL_INVALID`. No range is reported.
   `UNFIELDABLE` and `NOT_SATISFIABLE` are proved: completeness `EXACT` (1.5).
7. `OPTIMAL`: `QUANTIZED_OPTIMAL`, `integer_bound = integer_value`. `FEASIBLE`:
   `FEASIBLE_NOT_PROVEN`, `integer_bound = max(value, ceil(best_objective_bound))` (LARGEST)
   or `min(value, floor(best_objective_bound))` (LEAST), `None` if the bound is not finite.
   Otherwise `NO_SOLUTION` with every number `None`.

Witness check, without the solver, on every returned XI (a `RuntimeError` on failure, never a
silent answer): `kernel._admissible(β, lineup)`; each floor holds in integers and
`S_r(x) ≥ φ_r` in `Fraction` (tradeoffs.py:383-385); `O_r(lineup)` recomputed in Python equals
the solver's objective value.

### 2.4 Certificate and time

| Situation | Reported |
|---|---|
| every end `QUANTIZED_OPTIMAL` | completeness `EXACT`; both facts decided wherever the minimum is outside the allowance |
| an end `FEASIBLE_NOT_PROVEN` | the attained sum and the bound are reported; the bracket still contains every feasible sum because the bound is CP-SAT's proved bound; completeness `LIMIT_REACHED` or `DEADLINE` by the rule of 1.5 |
| an end `NOT_RUN`, `UNKNOWN` | `NO_SOLUTION`, no number, the sentence `CEILING_NOT_CERTIFIED`; completeness `LIMIT_REACHED` or `DEADLINE` (1.5; `NOT_RUN` is always `DEADLINE`) |
| `MODEL_INVALID` anywhere | completeness `MODEL_INVALID` |

Relation to shipped code. `maximize_requirement` makes every active minimum a floor, has no
minimiser, no deterministic limit, and warnings that fail the copy guard (tradeoffs.py:233-244:
"quality", "soft", "fit"). CEILING is not built on it but mirrors its objective and floors, and
a test ties them on instances whose oracle feasible set is not empty (on an empty one CEILING
reports no range while the maximiser reports `NO_SOLUTION`, so there is nothing to compare):
with `floors` equal to every active minimum, the LARGEST end of each requirement has the
`integer_value`, `integer_upper_bound` and certification of
`maximize_requirement(target_requirement_id=r)` on the same inputs. The witnesses are not
compared: the kernel background adds symmetry breaking the maximiser lacks (kernel.py:530-548),
so two exact solvers can return different XIs with the same integer value. Each witness's raw
sum is asserted to lie in the other's bracket instead.

## 3. CONFLICT: `galactico/optimization/xi/conflict.py`

Design claim (never served; the served sentences are the 7.7 constants): when the declared
model has no XI, a set of the reader's declarations that cannot all hold together, such that
leaving out any one member lets the other members hold together **when every declaration
outside the set is also set aside**. That is what the deletion filter certifies, and nothing
more. It does not say that dropping one member from everything the reader declared leaves an
XI: the model can hold another, independent conflict, and the assignment that shows a member
is needed can leave slots empty and use a player the reader excluded, when those declarations
lie outside the set. A separate solve per member answers the reader's question directly
(3.3, "restore test"): with every other declaration kept, does dropping this one alone leave
an XI (yes, no, or not decided). It is one such set, not the only one and not the smallest by
count; eligibility, the minutes gate, the evidence gate and missing measurements are part of
the model and are never offered for removal; nothing was relaxed in the solve it explains.

### 3.1 Declarations and background

| Family (deletion order) | One constraint per | Id | Holds for `x` when | Deleted means |
|---|---|---|---|---|
| `SLOT_COVERAGE` | slot, formation order | `slot:<slot_id>` | the slot is filled | the slot may stay empty |
| `EXCLUSION` | excluded player, ascending id | `exclusion:<player_id>` | he is in no slot | he is available |
| `REQUIREMENT_FLOOR` | floored requirement, ascending id | `floor:<requirement_id>` | `Σ_{s : applies(r, s)} c(v_{x(s)}[μ_r]) ≥ t(m)` in the named arithmetic | no floor on `r` |
| `LOCK` | locked player, ascending id | `lock:<player_id>` | he is in some slot | he is not required |

The background is never deleted: the admissible keys (eligibility, minutes, the measurement
rule over `R`; exclusions are **not** applied to keys here, they are constraints), at most one
player per slot, at most one slot per player. With every declaration deleted, the empty
assignment satisfies the background, so a model with no XI always has a non-empty conflicting
set.

Arithmetic, named by the public function:

| Function | Floors | Arithmetic | Mirrors |
|---|---|---|---|
| `explain_floors(..., floors)` | `floors` given: those `r` at `φ_r` (`{}`: no floor); `floors=None`: every `r ∈ R` at `m_r` | `HARD_POLICY` | `kernel.satisfiable` and `maximize_requirement`. The page uses it to explain the main solve until the ruling of item 13: `floors=None` for a Satisfy solve, `floors={}` for a Balance one (whose minima are not constraints) |
| `explain_solve(..., mode)`, **gated** (1.2) | every `r ∈ R` with `r.hard or mode == "SATISFY"`, at `m_r` | `SHORTFALL_POLICY` (`_q` coefficients and target) | `solve_xi`'s feasibility, solver.py:198-246, 274-275. Built, tested and routed only after the root amends 2.4 (section 11, item 13); until then `conflict.py` exports `explain_floors` alone |

### 3.2 Model

One CP-SAT model per call. A Boolean `x_{p,s}` per admissible key; a Boolean `a_c` per
declaration. Background: `Σ_p x_{p,s} ≤ 1` per slot, `Σ_s x_{p,s} ≤ 1` per player.
Declarations, each enforced only if `a_c` (`only_enforce_if`): `Σ_p x_{p,s} ≥ 1`;
`Σ_s x_{p,s} == 0`; `Σ c·x ≥ t`; `Σ_s x_{p,s} ≥ 1`. A declaration whose expression is a
constant is decided in Python: a constant that holds adds nothing, one that fails adds
`add_bool_or([a_c.Not()])` (the rule of `kernel._at_least`). No symmetry breaking: it does not
change feasibility and the witness check stays simple. A test of a set `T` of declarations is
a clone with `a_c == 1` for `c ∈ T` and `a_c == 0` otherwise, solved with no objective
(`OPTIMAL` or `FEASIBLE` means a witness).

### 3.3 Algorithm: deletion filter, and its proof

A set `T` of declarations is **satisfiable** when some assignment (1.1) meets the background
and every declaration in `T`; declarations outside `T` are not imposed. The whole model
(every declaration) is satisfiable exactly when an XI exists. A proper subset can be
satisfiable by an assignment with empty slots or an excluded player in it, when the
slot-coverage or exclusion declaration is outside the subset.

```
order = declarations in the deletion order of 3.1
s0 = test(all)                    # a witness: MODEL_FEASIBLE (an XI); not INFEASIBLE: UNDECIDED / MODEL_INVALID
current = all
for c in order:
    if deadline passed: c and every later one -> NOT_RUN, kept; stop
    s = test(current − {c})
    INFEASIBLE      -> current = current − {c}            DROPPED
    witness w       -> check w against current − {c}       KEPT_WITNESS (w stored)
    UNKNOWN         -> kept                                KEPT_UNDECIDED
    MODEL_INVALID   -> kept; the tool ends MODEL_INVALID
conflict = current, in deletion order
for c in conflict, in deletion order:              # restore tests, after the filter
    SLOT_COVERAGE   -> NOT_APPLICABLE, no solve     # an XI fills every slot
    deadline passed -> NOT_RUN
    s = test(all − {c})
    INFEASIBLE      -> restores_alone = False      # another conflict remains
    witness w       -> check w against all − {c}; it is an XI; restores_alone = True
    UNKNOWN         -> restores_alone = None
    MODEL_INVALID   -> restores_alone = None; the tool ends MODEL_INVALID
```

| Statement | Proof |
|---|---|
| `current` is never satisfiable | true after `s0`; it changes only to a set a solve just proved INFEASIBLE |
| the final set's infeasibility is certified by one recorded solve on exactly that set | the last `DROPPED` test was on the final set (later tests only keep), or `s0` if nothing was dropped. Its position in `statuses` is `final_set_proof_solve` |
| each `KEPT_WITNESS` member `c` is necessary to the set | its witness satisfies `current_t − {c} ⊇ final − {c}`, and a satisfiable set stays satisfiable when declarations are removed. The witness is checked again, without the solver, against exactly `final − {c}`. It is an assignment, not an XI: declarations outside `final − {c}` were not imposed on it |
| every proper subset of the final set is satisfiable | each proper subset is contained in `final − {c}` for some member `c` |
| what this does not prove | that `all − {c}` is satisfiable. Instance, with non-negative rates: slots, then `exclusion:A`, a progression floor above every sum the squad can reach, `lock:A`; every slot and the exclusion are dropped because the floor conflict persists, the floor is kept with a witness that leaves slots empty, and the final set is `{floor:progression}`; dropping the floor from everything declared still leaves `lock:A` with `exclusion:A`. The restore test reports `restores_alone = False` for it |
| `restores_alone = True` | the witness meets every declaration but `c`, slot coverage included, so it is an XI of the model without `c`; checked without the solver against `all − {c}` |
| solves | at most `1 + |order|` for the filter (with 11 slots, 11 locks, 30 exclusions and 3 floors, 56 small feasibility solves) plus one restore test per member of the final set that is not slot coverage |

Deletion order is a declared device: declarations tested early are dropped whenever possible,
so the set leans on locks and floors, the declarations a reader made, rather than on slot
coverage. Another order can return another minimal set; the response says so and prints the
order. QuickXplain is not used: it needs fewer solves for small sets and its certificate is
harder to read; the deletion filter's certificate is one line per declaration.

### 3.4 Interface

```python
CONFLICT_VERSION = "deletion-filter-conflict-v1"
FAMILIES = ("SLOT_COVERAGE", "EXCLUSION", "REQUIREMENT_FLOOR", "LOCK")   # the deletion order
ARITHMETICS = ("SATISFY_HALF_EVEN", "HARD_FLOOR_CONSERVATIVE")
DELETION_ORDER = ("slot coverage in formation order, then exclusions, requirement floors "
                  "and locks, each by ascending id")
ConflictLineup = tuple[tuple[str, int | None], ...]   # None: the slot is empty

@dataclass(frozen=True)
class Declaration:
    constraint_id: str             # slot:lb | exclusion:3322 | floor:progression | lock:3563
    family: str
    subject: str                   # slot_id, player_id as text, or requirement_id
    raw_floor: float | None        # floors only: the floor as declared
    integer_target: int | None     # floors only: t in the named arithmetic

@dataclass(frozen=True)
class DeletionTest:
    constraint_id: str
    status: str                    # status of the test, or NOT_RUN
    outcome: str                   # DROPPED | KEPT_WITNESS | KEPT_UNDECIDED | NOT_RUN
    # KEPT_WITNESS only: an assignment meeting final − {c}; () otherwise. Not an XI: slots may
    # be empty and a player whose exclusion lies outside final − {c} may appear
    witness: ConflictLineup
    witness_excluded_players: tuple[int, ...]   # excluded players the witness uses; () when none

@dataclass(frozen=True)
class RestoreTest:
    constraint_id: str             # a member of the final set
    status: str                    # status of the test of all − {c}; NOT_RUN; or NOT_APPLICABLE (slot coverage)
    restores_alone: bool | None    # True: an XI meets every other declaration; False: none does; None: not decided / not applicable
    witness: Lineup                # True only: that XI; () otherwise

@dataclass(frozen=True)
class ConflictCertificate:
    arithmetic: str
    rounding_policy: str           # kernel.SHORTFALL_POLICY or kernel.HARD_POLICY
    quantization: int
    initial_status: str            # the test of every declaration
    final_set_proof_solve: int | None   # position in statuses of the solve proving the final set
    members_with_witness: int
    members_undecided: int
    witnesses_verified: bool
    solves: int
    statuses: tuple[str, ...]      # filter tests, then restore tests, in call order
    per_solve_deterministic_limit: float
    deletion_order: str
    completeness: str              # EXACT | LIMIT_REACHED | DEADLINE | MODEL_INVALID (1.5)
    stopped_by: str | None

@dataclass(frozen=True)
class MinimalConflict:
    # MINIMAL_CERTIFIED | NOT_PROVEN_MINIMAL | MODEL_FEASIBLE | UNDECIDED | MODEL_INVALID
    status: str
    declarations: tuple[Declaration, ...]   # all of them, deletion order
    conflict: tuple[str, ...]               # constraint ids of the set, deletion order; () unless infeasible
    tests: tuple[DeletionTest, ...]         # one per declaration, deletion order
    restore_tests: tuple[RestoreTest, ...]  # one per member of the set, deletion order
    feasible_witness: Lineup                # MODEL_FEASIBLE: an XI meeting every declaration
    certificate: ConflictCertificate
    locked: tuple[int, ...]
    excluded: tuple[int, ...]
    claim: str                              # CONFLICT_CLAIM, word for word
    non_claim: str                          # CONFLICT_NON_CLAIM, word for word
    provenance: dict

def explain_floors(candidates, requirements, formation="4-3-3", *,
                   floors: Mapping[str, float] | None = None,
                   locked=(), excluded=(), seed=20260906, quantization=QUANTIZATION,
                   deadline: float, provenance=None) -> MinimalConflict
# gated (1.2, item 13): built only after the root's ruling on DISSENT 2
def explain_solve(candidates, requirements, formation="4-3-3", *, mode: str,
                  locked=(), excluded=(), seed=20260906, quantization=QUANTIZATION,
                  deadline: float, provenance=None) -> MinimalConflict
```

Status rules: `MINIMAL_CERTIFIED` iff the initial test is INFEASIBLE and every member of the
final set is `KEPT_WITNESS`. `NOT_PROVEN_MINIMAL`: the final set is certified infeasible and at
least one member is `KEPT_UNDECIDED` or `NOT_RUN`; each such member carries the sentence
`CONFLICT_MEMBER_UNDECIDED`, never "needed". `MODEL_FEASIBLE`: the initial test found an XI,
which is checked and returned (completeness `EXACT`). `UNDECIDED`: the initial test was not
decided; nothing is said. Completeness is `EXACT` only when every filter test and every
applicable restore test is decided; otherwise `LIMIT_REACHED` or `DEADLINE` by 1.5. An
undecided restore test never changes the status of the set: it only leaves that member's
`restores_alone` at `None`. Coefficient tables are computed here with the shipped functions
(`_q`, or `floor`/`ceil` of `_scaled`) and a test asserts they equal `kernel._tables` on the
keys both hold. Witness checks verify admissibility, injectivity, every declaration of the
tested set in integers and, for `HARD_FLOOR_CONSERVATIVE`, every floor in `Fraction`; a restore
witness is also checked to be an XI of the model without `c` (every slot filled, every lock
but `c` in, every exclusion but `c` out).

## 4. FRONTIER: `galactico/optimization/xi/frontier.py`

Design claim (never served; the served sentences are the 7.7 constants `FRONTIER_CLAIM` and
`FRONTIER_NON_CLAIM`, defined in `frontier.py`): every combination of 2 or 3 declared
requirement sums **in the shipped rounding** (OBJECTIVE_POLICY integers) that no XI's rounded
sums match or exceed on all of them while exceeding it on one, each with one XI that reaches
it, with a proof that none is missing. The certified object is the integer vector, and that
is what the page prints as the point (exactly, 7.5); the witness's unrounded sums are printed
beside it as a secondary column and are not the point. Not a ranking, no point is preferred,
nothing is said about a requirement that was not declared, and a sum is not a forecast. O7
lists three words that are never served; a test checks them.

### 4.1 Definition

Dimensions `D = (r_1, …, r_d)`, `d ∈ {2, 3}`, distinct members of `R`, declared by the
reader in an order; no default exists. The feasible set is `𝒳_F` of section 2.1 (eligibility,
locks, exclusions, and hard floors only if declared; ROOT 2.4). For `x ∈ 𝒳_F`,
`V(x) = (O_{r_1}(x), …, O_{r_d}(x))` in OBJECTIVE_POLICY integers. `u` dominates `v` iff
`u ≥ v` componentwise and `u ≠ v`. The frontier `P` is the set of vectors `V(x)` that no
`V(y)` dominates. The claim is "nondominated among the declared descriptors at the shipped
quantisation" (O7): two XIs with different raw sums can share a vector, and an XI whose raw
vector is nondominated can be dominated after rounding, within `a_r · n_r / q` per dimension.
Each point reports the allowance `e_r` beside it.

Why the printed point is the integer vector and not the witness's raw sums (exact
counterexample, `q = 1`, `n = 1`, two slots, half-even): players `a(0.5, 1.0)`, `b(0.5, 1.0)`,
`c(0.6, 0.5)`, `d(0.3, 1.0)`. The integer frontier is `{(0, 2), (1, 1)}`. With witnesses
`{a, b}`, raw `(1.0, 2.0)`, and `{c, d}`, raw `(0.9, 1.5)`, the first printed raw row would
dominate the second, and the XI `{a, c}`, raw `(1.1, 1.5)`, would exceed every printed raw
point on the first requirement. A completeness sentence about raw sums would be false. In the
integers it is true. Distinct integer vectors also print as distinct texts, which raw sums at
four decimals do not guarantee (on Madrid one integer unit of progression is about `3.0e-5`).

### 4.2 Algorithm and proof

```
region R_0 = background β + declared floors (section 2.3 steps 1 to 3)
loop k = 0, 1, …
    stage 1: maximise V_1 over R_k
        INFEASIBLE and no point yet -> empty feasible set (UNFIELDABLE / NOT_SATISFIABLE, as 2.3 step 6), COMPLETE
        INFEASIBLE                  -> COMPLETE (final_region_status INFEASIBLE)
        OPTIMAL and |points| = max  -> LIMIT_REACHED, stopped_by POINT_LIMIT (final_region_status OPTIMAL: a point exists)
    stage i = 2..d: fix V_j = v_j for j < i, maximise V_i
        any stage not OPTIMAL       -> LIMIT_REACHED / DEADLINE (1.5) / MODEL_INVALID; this iteration records nothing
        INFEASIBLE at stage i > 1   -> RuntimeError (a lexicographic level was lost)
    record v = (v_1, …, v_d) and the stage-d witness, checked without the solver
    R_{k+1} = R_k ∧ OR_i (V_i ≥ v_i + 1)      # Booleans b_i, b_i ⇒ V_i ≥ v_i + 1, add_bool_or(b)
```

| Statement | Proof |
|---|---|
| each recorded `v` is nondominated in `𝒳_F` | suppose `V(y) ≥ v`, `V(y) ≠ v`. If `y ∉ R_k`, some earlier point `w` has `V(y) ≤ w`, so `v ≤ w`, but `v ∈ R_k` means `v` is not weakly below `w`. So `y ∈ R_k`, and `V(y)` is lexicographically above `v`, contradicting the lexicographic maximum |
| points are distinct | a new point is not weakly below any earlier one |
| complete when `R_k` is INFEASIBLE | every `x ∈ 𝒳_F` has `V(x)` weakly below some point; a nondominated vector weakly below a point equals it |
| every feasible vector is weakly below a point | the same sentence |
| termination | each iteration adds a distinct vector of the finite set `{V(x)}`; at most `|P| + 1` iterations of at most `d` solves |
| partial lists stay true | every point recorded before a limit or a deadline was proved nondominated when it was recorded; only completeness is lost |

The dimension order decides which point is found first and nothing else: the set `P` does not
depend on it. No summed or weighted objective exists anywhere (ADR-0020 rejected it).

### 4.3 Interface

```python
FRONTIER_VERSION = "lexicographic-cut-frontier-v1"
MAX_FRONTIER_POINTS = 64
DIMENSION_COUNTS = (2, 3)
POINT_ORDER = ("lexicographic, descending, in the order in which the requirements were "
               "declared; reversing a two-requirement declaration reverses the list")

@dataclass(frozen=True)
class FrontierPoint:
    integer_sums: tuple[int, ...]       # V(witness), aligned with dimensions: THE POINT
    quantized_sums: tuple[float, ...]   # integer_sums[i] · n_i / q, nearest float (never printed)
    raw_sums: tuple[float, ...]         # S_{r_i}(witness), nearest float of the exact sum (never printed)
    lineup: Lineup                      # one XI reaching the point; not the only one
    stage_statuses: tuple[str, ...]     # the d stage statuses, all OPTIMAL

@dataclass(frozen=True)
class FrontierCertificate:
    points: int
    pairwise_nondominated: bool         # checked without a solver
    witnesses_verified: bool
    # INFEASIBLE: proof that no point is missing. INFEASIBLE_BY_CONSTRUCTION: a kernel reason.
    # OPTIMAL: another point exists (limit). NOT_RUN, UNKNOWN, FEASIBLE, MODEL_INVALID: no proof.
    final_region_status: str
    solves: int
    statuses: tuple[str, ...]
    completeness: str                   # COMPLETE (also for a proved empty set) | LIMIT_REACHED | DEADLINE | MODEL_INVALID
    stopped_by: str | None              # POINT_LIMIT | DETERMINISTIC_LIMIT | WALL_CLOCK; None when complete
    quantization: int
    objective_policy: str
    hard_policy: str
    per_solve_deterministic_limit: float
    raw_rounding_error_bounds: tuple[float, ...]   # e_{r_i}, outward
    max_points: int

@dataclass(frozen=True)
class Frontier:
    formation: str
    dimensions: tuple[str, ...]         # as declared
    status: str                         # FRONTIER | UNFIELDABLE | NOT_SATISFIABLE | INCOMPLETE | MODEL_INVALID
    points: tuple[FrontierPoint, ...]   # POINT_ORDER
    point_order: str
    floors: tuple[tuple[str, float], ...]
    locked: tuple[int, ...]
    excluded: tuple[int, ...]
    certificate: FrontierCertificate
    claim: str                          # FRONTIER_CLAIM, word for word
    non_claim: str                      # FRONTIER_NON_CLAIM, word for word
    reasons: tuple[str, ...]
    provenance: dict

def nondominated_sums(
    candidates, requirements, formation="4-3-3", *,
    dimensions: Sequence[str],                     # required: no default dimension (O7)
    floors: Mapping[str, float] | None = None,
    locked=(), excluded=(), seed=20260906, quantization=QUANTIZATION,
    max_points: int = MAX_FRONTIER_POINTS,
    deadline: float, provenance=None,
) -> Frontier
```

`ValueError` (a 422 at the API) when `len(dimensions) ∉ DIMENSION_COUNTS`, a dimension repeats
or is not an active requirement, or `max_points ∉ 1..64`. Status `FRONTIER` with completeness
`COMPLETE`; `UNFIELDABLE` and `NOT_SATISFIABLE` with `COMPLETE` (the empty set is proved);
`INCOMPLETE` with `LIMIT_REACHED` or `DEADLINE` and every listed point certified.
Witness check per point: admissible, floors in integers and `Fraction`, `V(lineup)` recomputed
in Python equals the point. `pairwise_nondominated` is recomputed on the returned list without
a solver; false is a `RuntimeError`.

## 5. DECLARED-RISK: `galactico/optimization/xi/risk.py`

Design claim (never served; the served sentences are the 7.7 constants, defined in `risk.py`
with `RISK_HARD`, `RISK_OVERFLOW` and `RISK_NOT_EVALUABLE`, which `risk.py` raises or returns,
and re-exported by the router): on the shared resampled worlds of the snapshot, an XI that a
declared rule over the per-world loss selects, its optimum, which players every and some XI
of the rule's level set hold, and, **for the XI shown**, the worlds that decide its value.
Another XI the rule selects has the same optimum and can have other tail or binding worlds;
the page says so. Non-claim (E-13's, verbatim): "Stability against resampling of the
historical matches; not robustness to opponents, absences or form, and not a forecast." No
chance figure, share or average over worlds is computed or printed.

### 5.1 Per-world loss and its encoding

For `w ∈ U` and `x ∈ 𝒳` (section 1.4; the same set in every used world), with `_q`
coefficients `c^w_r(p) = _q(V^w_p[μ_r], n_r, q)` and targets `t_r = _q(m_r, n_r, q)`:
`d^w_r(x) = max(0, t_r − Σ_{s : applies(r, s)} c^w_r(x(s)))`, `M^w(x) = max_r d^w_r(x)`,
`T^w(x) = Σ_r d^w_r(x)`. The loss of `x` in `w` is the pair `(M^w, T^w)`, compared
lexicographically (O8).

Bounds, from the instance and never from an outcome: `L^w_r = Σ` over admissible keys `(p, s)`
with `applies(r, s)` of `min(0, c^w_r(p))`; `U^w_r = max(0, t_r − L^w_r)` (the deficit bound of
solver.py:270, 276); `T_bound = max_w Σ_r U^w_r`; `M_bound = max_w max_r U^w_r`.

`E^w(x) = BIG · M^w(x) + T^w(x)` with

    BIG = 2 · |U| · T_bound + 1

| Requirement on BIG | Holds because |
|---|---|
| O8: strictly larger than the largest possible total | `BIG > T_bound ≥ T^w(x)` |
| TAIL: a sum of `k ≤ |U|` encodings orders as the pair (sum of `M`, sum of `T`) | `BIG > |U| · T_bound ≥ Σ_{w ∈ K} T^w` for every set `K` of used worlds (E-13 DISSENT 3) |
| REGRET: `E^w − E*^w` orders as the pair `(M^w − M*^w, T^w − T*^w)` | the `T` part lies in `[−T_bound, T_bound]` and `BIG > 2 · T_bound` |
| a device, not a parameter | any larger value gives the same order; a test doubles it and requires identical rule-invariant outputs (status, optimum, tail sums or regret optimum, membership). The XI shown and its tail worlds may change: CP-SAT's representative of a tied level set depends on the objective coefficients |

`E` and `BIG` exist only inside `_encoding_base` and the model builders and in the one Python
equality check of 5.6. They are never a field, a provenance value, a log record, an exception
message or a served number; a test asserts each (section 9). O8 permits this encoding for the
risk modes; ADR-0020 rejected a weighted sum of the two stages as a search device for the
kernel, and the kernel keeps its three-solve form. The request for ADR-0030 (section 12)
records that O8 overrides that rejection for the risk modes only, and why: BIG is exact by
5.1, never serialised, and tested. Overflow guard: with
`E_max = BIG · M_bound + T_bound`, a request with `k · E_max ≥ 2**53` (TAIL) or
`E_max ≥ 2**53` (REGRET) is refused with `ValueError(RISK_OVERFLOW)`, a sentence holding no
number. Below `2**53` every objective value and bound CP-SAT reports is an exact float. At the
shipped default minima `t_r = q` exactly (the normaliser is the default minimum), so with
non-negative rates `T_bound = |R| · q`, and the guard admits a minimum up to about
`(2**53 / (2 · k · B · |R| · q²))^½` times the club median: about 13.7 times at `B = 40`,
`k = 20`, `|R| = 3`. This is arithmetic on the definitions, not a measurement.

### 5.2 TAIL(k of B) and WORST_WORLD

For the rule `TAIL`, `k` is an integer from the fixed menu `TAIL_MENU[B]`; `WORST_WORLD` is
the rule with `k = 1` and is offered only under its own name:

| B | `TAIL` menu of `k` | `WORST_WORLD` | how it was fixed |
|---|---|---|---|
| 12 | 2, 3, 6 | `k = 1` | `ceil(B/10)`, `ceil(B/4)`, `ceil(B/2)`: the E-13 draft's `TAIL_10`, `TAIL_25`, `TAIL_50` counts, with its `WORST_WORLD` at 1 (config.json:13-16), written as integers. No fraction or percentage is served |
| 40 | 4, 10, 20 | `k = 1` | the same |

So no request can name the same rule twice, and the E-13 subject of a reply is fixed by its
rule: `risk_rule:WORST_WORLD` for `WORST_WORLD`, `risk_rule:TAIL` for `TAIL`.

Objective: minimise over `x ∈ 𝒳` the sum of the `k` largest `E^w(x)`, `w ∈ U`; equivalently
the lexicographic minimum of (sum of the `k` largest `M^w`, sum of `T^w` over the `k`
lexicographically largest worlds). `WORST_WORLD` is `TAIL` with `k = 1` and is labelled as the
extreme of that family for the fixed `B` (its label names the tail family and `B`,
`RISK_WORST`); its certificate records `B` and the sentence that a worst case over resampled
worlds grows with their number (O8). With `|U| < k` the rule is `NOT_EVALUABLE`; `k` is not
lowered.

Reported for the XI shown (another XI of the level set can have other tail worlds; the page
labels these tables "for the XI shown"): every used world's pair; the tail, the `k` worlds
sorted by the key (`M^w` descending, `T^w` descending, `world_id` ascending) and cut at `k`;
the boundary ties, the worlds outside the tail with the same pair as its last member; the
tail sums `(Σ M, Σ T)`, which are the rule's optimum and so the same for every XI it
selects.

### 5.3 MINIMAX_REGRET

`E*^w = BIG · M*^w + T*^w`, where `(M*^w, T*^w)` is the certified least pair in world `w`:
`kernel.value(excluded=X, locked=L, values=V^w, deadline=…)` with status `CERTIFIED` (BALANCE
on that world, ADR-0020; `_q` rounding). Objective: minimise `max_{w ∈ U} (E^w(x) − E*^w)`;
every term is at least 0 (O8). Reported: for every used world, both pairs, the XI shown's
and the world's least; the binding worlds of the XI shown, every `w` whose pair of
differences `(M^w − M*^w, T^w − T*^w)` is the lexicographic maximum, found by comparing those
tuples in local Python variables that are never stored, logged or served (E stays inside 5.1's
limits); the ledger and the page print each binding world with its two pairs and never a
difference (O8). Another XI the rule selects has the same optimum and
can have other binding worlds; the page says so. If a used world's least is `UNFIELDABLE`,
the rule is `UNFIELDABLE` (by the lemma of 1.4 every used world shares `𝒳`, so all are), with
completeness `EXACT`, no XI and the kernel's reasons; never `UNKNOWN`. If any other used
world's least pair is not `CERTIFIED`, the rule returns `UNKNOWN` with those worlds in
`undecided_world_ids` and no XI: unlike the shipped bootstrap, a world is not set aside for a
wall-clock reason, because that would make the rule's objective depend on load.

### 5.4 The single-world invariant

**Theorem.** With `|U| = 1`, TAIL(1) and MINIMAX_REGRET return an XI whose `(M, T)` in that
world is the BALANCE optimum there. TAIL(1) minimises `E^w`, which orders as the pair. REGRET
minimises `E^w − E*^w ≥ 0`, which is 0 exactly at the BALANCE optima. Tested against the
oracle, against `kernel.value(values=…)` (its integers) and against `solve_xi` on the
world-replaced candidates, comparing `round(v * q)` for each `v` of its float
`objective_vector` (a product such as `7 / 100000 * 100000` is `6.999999999999999` in floating
point), on every seeded single-world instance.

### 5.5 Rules for hard minima and Satisfy

The risk rules compare shortfalls. A requirement in force with `hard=True` is a `ValueError`
(`RISK_HARD`), as `kernel.value` refuses it (kernel.py:670-674); the router builds the model
with `mode="BALANCE"`, so the XI Lab decision rule above does not change the risk panel, and
the page says so (`RISK_BALANCE`); without the opt-in it also holds fewer requirements than
the solve above, and the reply says that too (`MODEL_DIFFERS`, 1.3).

### 5.6 Formulation

1. Worlds: discard rule; `U`; `V^w` complete mappings. `|U| = 0` or `|U| < k`: `NOT_EVALUABLE`,
   no solve, completeness `EXACT`.
2. Background `β = kernel._background(X, L, None, (), V^{u_0})` with `u_0 = min U`; for every
   `w ∈ U`, `β_w = kernel._background(X, L, None, (), V^w)` and `assert β_w.variables.keys() ==
   β.variables.keys()` (the lemma of 1.4); `G^w = kernel._tables(β_w, conservative=False)`.
   `β.model is None`: `UNFIELDABLE` by construction (the deadline rule first, as the kernel),
   completeness `EXACT`.
3. Per world and requirement: `d^w_r ∈ [0, U^w_r]` with `d^w_r + Σ c·x ≥ t_r`; `M^w ∈ [0,
   M_bound]` with `M^w ≥ d^w_r`; `T^w = Σ_r d^w_r`; `E^w = BIG · M^w + T^w`. A linear epigraph,
   no `add_max_equality` (ADR-0020). The objectives below are non-decreasing in every `M^w` and
   `T^w`, so at the optimum the epigraph values can be taken exact.
4. TAIL: `η ∈ [0, E_max]`, `u_w ∈ [0, E_max]`, `u_w ≥ E^w − η`; minimise `k · η + Σ_w u_w`.
   For fixed `x` the minimum over integer `η` is the sum of the `k` largest `E^w(x)`, reached at
   the `k`-th largest value.
5. REGRET: per-world optima first (`|U|` calls of `kernel.value`, three bounded solves each);
   then `ρ ∈ [0, E_max]`, `ρ ≥ E^w − E*^w` for every `w`; minimise `ρ`.
6. The selection solve uses `risk._solver` (deterministic limit `SELECTION_DETERMINISTIC_LIMIT =
   40.0`, recorded). Only `OPTIMAL` is a selection. `INFEASIBLE` is a proof that no XI exists
   (for example two locked goalkeepers: each lock has an admissible key, so the kernel records
   no reason, kernel.py:518-529, and CP-SAT proves the model empty): status `UNFIELDABLE`,
   completeness `EXACT`, no lineup, the solve recorded. `UNKNOWN` / `FEASIBLE`: `UNKNOWN`, no
   lineup, completeness by 1.5. The witness is checked without the solver:
   admissible; `(M^w, T^w)` recomputed per world with `kernel._shortfalls(G^w, lineup)`; the
   objective recomputed from those integers in Python equals the solver's objective value.
   The tail, the boundary ties and the binding worlds are then computed from pairs alone.
7. Ties (R11). The rule's level set is the base model plus `k · η + Σ u_w ≤ Φ*` (TAIL) or
   `ρ ≤ ρ*` (REGRET); with `η`, `u`, `ρ` free this admits exactly the XIs whose objective
   equals the optimum. For each candidate in id order, the opposite solve of
   `kernel.membership` (kernel.py:876-912): in the selected XI, add `Σ_s x_{p,s} = 0`;
   otherwise add `= 1`. INFEASIBLE is the only source of `necessary = True` and of
   `possible = False`; an undecided solve leaves `None`. Excluded players and players with no
   admissible key are `(False, False)` by construction; locked players `(True, True)`. The
   membership block has its own `completeness`; when no selection exists (`UNFIELDABLE`,
   `NOT_EVALUABLE`) it is `EXACT` with no rows, since nothing is undecided. These solves use
   `SELECTION_DETERMINISTIC_LIMIT` too and stop at the deadline. No CORE / FAVORED / CONTESTED /
   FRINGE label is formed here: those stay on the main solve (H10).

The point-estimate requirement ledger is reported for every rule (E-13's "What no outcome
changes"): the selected XI's pair at the point values (`_q` tables of the 0-world point
vectors; `None` if the lineup uses a key the point vectors forbid) and its exact raw sums.

### 5.7 Interface

```python
RISK_VERSION = "declared-risk-lexicographic-v1"
RULES = ("WORST_WORLD", "TAIL", "MINIMAX_REGRET")      # the fixed order of the page
TAIL_MENU = MappingProxyType({12: (2, 3, 6), 40: (4, 10, 20)})   # TAIL only; WORST_WORLD is k = 1
SELECTION_DETERMINISTIC_LIMIT = 40.0
EXACT_OBJECTIVE_LIMIT = 2**53
RISK_HARD = "..."; RISK_OVERFLOW = "..."; RISK_NOT_EVALUABLE = "..."   # the 7.7 texts, defined here
RISK_WORST = "..."; RISK_TAIL = "..."; RISK_REGRET = "..."; RISK_NON_CLAIM = "..."

@dataclass(frozen=True)
class LossPair:
    maximum_shortfall: int         # M, integer units of 1 / quantization (normalised)
    total_shortfall: int           # T

@dataclass(frozen=True)
class TailSums:                    # the tail rule's optimum; not a LossPair: a sum of maxima is not a maximum
    summed_maximum_shortfall: int  # Σ M over the tail
    summed_total_shortfall: int    # Σ T over the tail

@dataclass(frozen=True)
class WorldLoss:
    world_id: int
    selected: LossPair             # the XI shown, in this world
    world_least: LossPair | None   # MINIMAX_REGRET: the certified least pair of this world

@dataclass(frozen=True)
class DiscardedWorld:
    world_id: int
    reason: str                    # "missing shared-world exposure"

@dataclass(frozen=True)
class SolveRecord:
    purpose: str                   # WORLD_LEAST | SELECTION | MEMBERSHIP
    world_id: int | None
    player_id: int | None
    status: str                    # no objective value and no bound: those are encodings

@dataclass(frozen=True)
class MembershipRow:
    player_id: int
    possible: bool | None          # in some XI of the rule's level set
    necessary: bool | None         # in every XI of it

@dataclass(frozen=True)
class MembershipBlock:
    rows: tuple[MembershipRow, ...]     # player_id ascending; () when no selection exists
    completeness: str                   # EXACT (also when vacuous) | LIMIT_REACHED | DEADLINE (1.5)

@dataclass(frozen=True)
class RiskCertificate:
    rule: str
    tail_count: int | None
    world_count: int                    # B, as requested
    used_world_ids: tuple[int, ...]
    discarded_worlds: tuple[DiscardedWorld, ...]
    discarded_world_count: int
    undecided_world_ids: tuple[int, ...]   # REGRET only
    world_fingerprint: str
    world_seed: int
    solver_seed: int
    bootstrap_version: str
    quantization: int
    shortfall_policy: str               # kernel.SHORTFALL_POLICY
    comparison: str                     # "largest shortfall first, then summed shortfall"
    selection_deterministic_limit: float
    world_least_deterministic_limit: float   # kernel.PER_SOLVE_DETERMINISTIC_LIMIT
    solves: int
    records: tuple[SolveRecord, ...]
    completeness: str                   # EXACT | LIMIT_REACHED | DEADLINE | MODEL_INVALID (1.5)
    stopped_by: str | None

@dataclass(frozen=True)
class RiskSelection:
    rule: str                           # WORST_WORLD | TAIL | MINIMAX_REGRET
    tail_count: int | None              # k; 1 for WORST_WORLD; None for MINIMAX_REGRET
    status: str                         # CERTIFIED | UNFIELDABLE | NOT_EVALUABLE | UNKNOWN | MODEL_INVALID
    lineup: Lineup                      # the XI shown; () unless CERTIFIED
    world_losses: tuple[WorldLoss, ...] # every used world, ascending id, for the XI shown; () unless CERTIFIED
    tail_world_ids: tuple[int, ...]     # for the XI shown
    tail_boundary_ties: tuple[int, ...] # for the XI shown
    tail_sum: TailSums | None           # the rule's optimum (TAIL, WORST_WORLD)
    binding_world_ids: tuple[int, ...]  # for the XI shown (MINIMAX_REGRET)
    point_loss: LossPair | None
    point_sums: tuple[tuple[str, float], ...]   # never printed as floats: the router adds exact texts (7.5)
    membership: MembershipBlock
    certificate: RiskCertificate
    claim: str                          # the rule's 7.7 label, word for word
    non_claim: str                      # RISK_NON_CLAIM, word for word
    reasons: tuple[str, ...]
    provenance: dict

def tail_selection(candidates, requirements, formation="4-3-3", *,
                   worlds: Mapping[int, Mapping[int, Mapping[str, float | None]]],
                   world_count: int, tail_count: int,
                   world_seed: int, bootstrap_version: str,      # required; copied into the certificate
                   locked=(), excluded=(), seed=20260906, quantization=QUANTIZATION,
                   analyze_ties: bool = True, deadline: float, provenance=None) -> RiskSelection
def worst_world_selection(...same, without tail_count...) -> RiskSelection   # tail_selection(k=1), rule WORST_WORLD
def minimax_regret_selection(candidates, requirements, formation="4-3-3", *, worlds,
                             world_count: int, world_seed: int, bootstrap_version: str,
                             locked=(), excluded=(), seed=20260906,
                             quantization=QUANTIZATION, analyze_ties: bool = True,
                             deadline: float, provenance=None) -> RiskSelection
def declared_risk_selection(candidates, requirements, formation="4-3-3", *, rule: str,
                            tail_count: int | None = None, **options) -> RiskSelection
def world_losses(lineup: Lineup, candidates, requirements, formation, *, worlds,
                 locked=(), excluded=(), quantization=QUANTIZATION) -> tuple[WorldLoss, ...]
```

`world_count` must equal `len(worlds)` and, in the module, any positive integer is accepted so
that the oracle tests can use one to five worlds and the single-world invariant can be tested;
`tail_count` must lie in `1..world_count`. The menu (`TAIL_MENU`, `B ∈ {12, 40}`, and
`WORST_WORLD` for `k = 1`) is enforced by the API. `world_seed` and `bootstrap_version` are
required keyword arguments with no default; the oracle tests pass constants of their own and
a test asserts both reach the certificate unchanged. `world_losses` is pure Python and is the adapter the E-13 solver audit needs
(section 13). Every integer pair is also served in normalised units by the router as text,
exactly: `M / q` with `q = 100000` has at most five decimals.

Labels until E-13 runs. The rule's label says what it computes (`RISK_WORST`, `RISK_TAIL`,
`RISK_REGRET`, section 7.7), and while `verdicts.verdict_for("E-13", subject).basis` is not
`EXECUTED` it ends with `RISK_UNTESTED`: "E-13 has not tested this rule." Subjects are the E-13
draft's: `risk_rule:WORST_WORLD`, `risk_rule:TAIL`, `risk_rule:MINIMAX_REGRET`, and
`risk_report:WORST_WORLD`, `risk_report:TAIL` for the tail figures. Today each answers
`NOT_REGISTERED` and its badge reads RECORD ONLY · NOT TESTED with "No registered protocol tests
this claim." The subject of a reply is fixed by its rule (5.2): a `WORST_WORLD` reply carries
`risk_rule:WORST_WORLD`, a `TAIL` reply `risk_rule:TAIL`. Rules are never ordered or
preselected by token.

## 6. The oracle: `tests/xi_exact_oracle.py`

Written from sections 1 to 5 alone. It imports `itertools`, `math`, `fractions` and
`collections` and nothing from `galactico` (an AST test asserts it); candidates and
requirements are read by attribute. It forms no encoding: losses are compared as tuples.
Each part is written by a builder who does not implement the tool it checks (section 0): the
shared core (first four rows and the two world rows) by D, CEILING and CONFLICT by C,
FRONTIER by A, RISK by B. A builder never edits another's part; a disagreement between a tool
and its oracle part is settled from the text of this file, not from the other's code.

| Function | Part | Definition |
|---|---|---|
| `options(instance, *, vectors, excluded, keys_ignore_exclusions=False)` | core | per slot, the admissible players in id order (section 1.1); for CONFLICT, exclusions are not applied here |
| `xis(instance, *, locked, excluded, vectors)` | core | every XI by `itertools.product` over the options, injective, locks included, exclusions absent |
| `objective(v, n, q)`, `floor_coef`, `ceil_target`, `half_even(v, n, q)` | core | `round(Fraction(v)/Fraction(n)*q)`; `floor`; `ceil`; and the shortfall rule as exact `Fraction` half-even (ROOT 2.6 D8), used only on instances where it equals `_q` |
| `exact_sum(x, r, vectors)` | core | `S_r(x)` in `Fraction` |
| `world_vector(instance, world, p)` | core | `dict(world.get(p, {}))`: whole-vector replacement; a player absent from a world has every metric `None` (1.4) |
| `used_worlds(instance, worlds, *, excluded)` | core | the discard rule of 1.4 written from its text: world `w` is discarded iff some `p ∉ X`, some slot `s` with `Eligible(p, s)` and some `r ∈ R` with `applies(r, s)` have `world_vector(...)[μ_r] is None`; returns `(U ascending, discarded ascending)` |
| `ceilings(...)` | C | per requirement, `min` and `max` of `O_r` over `𝒳_F` and every `S_r` |
| `satisfiable(declarations, ...)`, `deletion_filter(order, ...)`, `restores_alone(c, ...)` | C | whether some assignment (1.1) meets the background and every declaration of the set, by depth-first backtracking over slots in formation order (each slot: an admissible unused player, or empty when its coverage declaration is absent), pruning when the slots left cannot hold the locked players still missing (counted by their admissible slots among those left) and when a floor cannot be met even if every applicable slot left takes the largest coefficient among its admissible players (and 0 when it may stay empty), a bound that ignores injectivity and so never prunes a witness; it stops at the first witness and counts nodes. The deletion filter of 3.3 run on it; the restore test of 3.3 on `all − {c}` |
| `frontier(...)` | A | the vectors `V(x)` over `𝒳_F` and their nondominated subset |
| `world_pairs(x, vectors)`, `tail_optimum(k)`, `regret_optimum()`, `tail_of(x, k)`, `binding_of(x)` | B | `(M^w, T^w)` over `used_worlds`; the lexicographic minimum over XIs of (sum of the `k` largest `M`, sum of `T` over the `k` lexicographically largest worlds); the per-world least pairs and the lexicographic minimum over XIs of the lexicographic maximum over worlds of `(M − M*, T − T*)`, each returning the optimum and every XI attaining it; and, for a given XI, its tail and boundary ties by the key of 5.2 and its binding worlds, so the tool's per-world reports are compared for the lineup the tool returned, never with a witness of the oracle's choosing |

Instances (`tests/xi_exact_oracle.instances(seed)`): 3 to 5 slots with mixed allowed
positions, 5 to 8 candidates, some with `eligible_slots`, some with zero minutes, 1 to 3
requirements with mixed `slot_ids`, some `None` values, 1 to 5 worlds with holes, locks and
exclusions, `q ∈ {100, 1000, 100000}`. CEILING and FRONTIER instances draw decimal values of
either sign. RISK and the `explain_solve` instances draw dyadic values (multiples of 1/64 in
`[−2, 4]`) with normalisers in `{0.5, 1, 2, 4}`, for which `int(round(v / n * q))` (written out
in the test, not imported) equals the exact half-even integer; the generator asserts it on every
coefficient. A separate test identifies the policy on a non-dyadic value (section 9).

## 7. API: `galactico/api/xi_extensions.py`

### 7.1 Routes

| Method | Path | Budget route | Seconds | Long | Request | Tool |
|---|---|---|---|---|---|---|
| GET | `/api/xi/extensions` | none | | no | none | the menus (7.5), corpus-free |
| POST | `/api/xi/ceilings` | `xi.ceilings` | 10 | no | `CeilingsRequest` | `ceilings.requirement_ranges` |
| POST | `/api/xi/conflict` | `xi.conflict` | 15 | no | `ConflictRequest` | `conflict.explain_floors`; `explain_solve` too after the ruling of item 13 |
| POST | `/api/xi/frontier` | `xi.frontier` | 30 | no | `FrontierRequest` | `frontier.nondominated_sums` |
| POST | `/api/xi/risk/tail` | `xi.risk.tail` | 60 | no (requested, section 12) | `RiskTailRequest` | `rule: "WORST_WORLD"`: `risk.worst_world_selection`; `rule: "TAIL"`: `risk.tail_selection` |
| POST | `/api/xi/risk/regret` | `xi.risk.regret` | 150 | yes | `RiskRegretRequest` | `risk.minimax_regret_selection` |
| GET | `/xi/extensions` | none | | no | none | fallback page only (8.4): `FileResponse(web/xi-extensions.html)`; registered only if the root refuses the `xi.html` edits |

The budgets are the ones `runtime.BUDGETS` already holds (runtime.py:133-148, pinned by
`tests/test_lab_runtime.py:116-125`); `xi.risk.regret` is already in `LONG_ROUTES`. No new
budget. `xi.split-sample` stays unused here (OPEN QUESTION 2). No path collides with
`decision_lab`'s five `/api/xi/*` routes. The router is
`APIRouter(route_class=decision_lab.DecisionRoute)`: a pydantic validation error never echoes
an input value, and the refusals of 7.2 are fixed sentences that name no id (the kernel's own
"unknown locked player IDs: [...]" never reaches a client, because `declare` checks ids
first).

`xi.risk.tail` enumerates every candidate for membership (5.6 step 7), which is what
`LONG_ROUTES` names ("every candidate"), but it is not in that set, and both `runtime.py` and
the test that pins the set (`tests/test_lab_runtime.py:123`) are shared files. Section 12 asks
the root to add it. Until then a tail request holds no long-job place and is bounded only by
its 60-second budget and the sixteen in-flight places; this is stated in ADR-0030, and the
`B = 40` option is not shipped until the TAIL and REGRET selection and membership solves are
measured at `q = 100000` on the Madrid worlds (section 11, item 15; OPEN QUESTION 5). The
measurement records wall time, deterministic time and status per solve and nothing else: no
lineup, pair or selection is printed or kept, so it adds no prior exposure for E-13 (1.6).

### 7.2 Request models

All `ConfigDict(extra="forbid")`; integers, floats and booleans strict; floats
`allow_inf_nan=False`. `RequirementId = Literal["progression", "left_pass_origins",
"right_pass_origins"]`.

```python
class XIDeclarations(BaseModel):
    scenario_id: str = "madrid-2018-05-06"
    formation: Literal["4-3-3", "4-3-1-2"] = "4-3-3"
    locks: list[StrictInt] = Field(default_factory=list, max_length=11)
    excludes: list[StrictInt] = Field(default_factory=list, max_length=30)
    experimental_opt_in: StrictBool = False

Minimum = Annotated[float, Field(strict=True, ge=0, le=1000, allow_inf_nan=False)]

class CeilingsRequest(XIDeclarations):
    minimums: dict[RequirementId, Minimum] = {}     # compared only (2.1)
    floors: dict[RequirementId, Minimum] = {}       # hard, conservative

class ConflictRequest(XIDeclarations):
    # Until the ruling of item 13: Literal["floors"]. After it: Literal["solve", "floors"].
    explains: Literal["floors"]                       # required: which arithmetic (3.1)
    minimums: dict[RequirementId, Minimum] = {}       # the minima in force, as decision_inputs reads them
    floors: dict[RequirementId, Minimum] | None = None  # None: every requirement in force is a floor
                                                        # at its minimum; {}: no floor
    # after the ruling only: mode: Literal["BALANCE", "SATISFY"] | None = None, required iff
    # explains == "solve"; floors refused when explains == "solve"

class FrontierRequest(XIDeclarations):
    dimensions: list[RequirementId] = Field(min_length=2, max_length=3)   # required, ordered
    floors: dict[RequirementId, Minimum] = {}
    max_points: int = Field(default=64, ge=1, le=64, strict=True)

class RiskTailRequest(XIDeclarations):
    bootstrap_worlds: Literal[12, 40]               # required: no default world count
    rule: Literal["WORST_WORLD", "TAIL"]            # required: no default rule
    tail_count: StrictInt | None = None             # TAIL: required, in TAIL_MENU[bootstrap_worlds]; WORST_WORLD: refused
    minimums: dict[RequirementId, Minimum] = {}

class RiskRegretRequest(XIDeclarations):
    bootstrap_worlds: Literal[12, 40]
    minimums: dict[RequirementId, Minimum] = {}
```

A `model_validator(mode="after")` refuses, with its own sentence, a field that belongs to the
other branch (`floors` with `explains: "solve"`, `mode` with `explains: "floors"`, a
`tail_count` with `WORST_WORLD`: sent and not used would be ignored silently), repeated
dimensions, and a `tail_count` outside the menu (1 is not on the `TAIL` menu: that rule is
`WORST_WORLD`). Then, at declaration time, `ValueError` (422), each with a fixed sentence that
names no value: a side requirement named in `minimums`, `floors` or `dimensions` without the
opt-in (`EXPERIMENTAL_OPT_IN_ERROR`); `explains: "solve"` without the opt-in
(`CONFLICT_SOLVE_NEEDS_OPT_IN`, 1.3); a lock or exclusion id that is not a gated candidate of
the scenario (`UNKNOWN_PLAYER`: "A locked or excluded player is not a candidate of this
decision point."); the risk overflow guard. Locks and exclusions are sorted and de-duplicated,
as `solve_xi` reads them (solver.py:108); a player both locked and excluded is not refused: it
is a declaration the conflict tool explains and the other tools answer as `UNFIELDABLE` with
the kernel's reason.

### 7.3 Handler skeleton

The ADR-0024 shape, as `squad_lab._answer` (squad_lab.py:256-280) and
`tests/test_lab_runtime.py:816`:

```
budget = runtime.budget_for(route)                       # at handler entry
if request.scenario_id not in decision_lab.SCENARIOS: 404 "unknown historical scenario"
with runtime.lab_errors():
    key = runtime.cache_key(route, canonical(request), corpus_token())
    def compute():
        with runtime.long_job(route):
            snap = _match_snapshot(request.scenario_id, worlds)   # 0, or B for risk; gated (below)
            problem = declare(snap, request)                      # 7.4
            result = tool(..., deadline=time.monotonic() + budget.remaining())
            return runtime.finalize(envelope(route, snap, request, problem, result, budget))
    data, hit = runtime.RESULTS.get_or_compute(key, compute, store=runtime.is_complete)
    return runtime.respond(data, cache_hit=hit)
```

`canonical(request)` is `request.model_dump(mode="json")` with locks and exclusions sorted and
de-duplicated and every dict key-sorted; dimensions keep their declared order (it is part of
the answer). It includes every default, so a request that sends a default and one that omits
it are one key; that is safe because nothing in a reply depends on which fields were sent
(the declared rows of 7.6 are a function of the resolved request). `corpus_token()` is
`planning.corpus_token(planning.FLAGSHIP)`: the names, sizes and modification times of Spain's
public frames and the provider-wide `players` and `teams` files, the files `load_snapshot`
reads, opened by nobody (ADR-0024); it raises `FileNotFoundError` (a 503) when one is absent,
and the API tests patch it as `tests/test_squad_api.py` does.

The snapshot loader is the router's own, behind the ADR-0024 build gate:

```python
@planning._built_once(maxsize=4, reads=lambda scenario_id, worlds: ("Spain",))
def _match_snapshot(scenario_id: str, worlds: int):
    if worlds != 0 and worlds not in runtime.WORLD_MENU: raise ValueError(...)
    return historical.load_snapshot(runtime.match_scenario(scenario_id)["match_id"],
                                    worlds=worlds, seed=historical.SEED)
```

One build per key, later callers handed the first caller's object, two builds at once in the
process (shared with planning's loaders), 429 after the documented wait for a place, and the
corpus identity in the key, so a snapshot built from files that have since changed is
dropped and built again. `decision_lab.snapshot` (an `lru_cache` keyed on `(match_id, worlds)`
only, decision_lab.py:208-210) is not used and not touched: it serves the five shipped routes as
before, including its known staleness after a corpus rewrite, which is now in
KNOWN_LIMITATIONS (section 12). Cost, stated: the first request of each route kind after start
builds its snapshot (the actions frame and the prior xT fit) inside its own budget, which on a
cold process can leave a 10-second CEILING request little time and return `DEADLINE`; the next
request finds it built. The world-free tools (CEILING, CONFLICT, FRONTIER) load `worlds = 0`,
whose point candidates and default minima are those of every world count (worlds add sampled
vectors only, historical.py:198-214).

### 7.4 Declaring the problem

`declare(snap, request)`: first, every lock and exclusion id must be a gated candidate of the
snapshot (`UNKNOWN_PLAYER`, 7.2); then `decision_inputs(snap, formation, "BALANCE" |
request.mode, minimums)` (the shipped function, unchanged), then the opt-in rule of 1.3. Risk,
ceilings, frontier and `explains: "floors"` use `"BALANCE"` (no requirement is hard; floors
are separate declarations); conflict uses `request.mode` for `explains="solve"` once routed.
For `explains: "floors"` with `floors` absent, the floors are `{r: r.minimum}` for every
`r ∈ R`, read from the requirements `decision_inputs` built from `minimums`. The candidates are
the snapshot's gated players; the 900-minute gate and the omitted players are the snapshot's,
and the response names the omitted players beside the result (`snap.omitted`, the full
records, as `/api/xi/solve` serves them, decision_lab.py:429).

### 7.5 Response envelope

Every POST reply has these keys; `result` is `dataclasses.asdict` of the tool's dataclass with
the router's text fields added beside the numbers.

| Key | Content |
|---|---|
| `tool` | `"xi.ceilings"`, `"xi.conflict"`, `"xi.frontier"`, `"xi.risk.tail"`, `"xi.risk.regret"` |
| `scenario_id`, `scenario` | the `SCENARIOS` entry |
| `formation`, `slots` | formation id; `[{slot_id, label}]` in formation order |
| `players` | `[{player_id, name, position}]` of the gated candidates; no rate is served here |
| `omitted_candidates` | `snap.omitted`, as `/api/xi/solve` serves it |
| `requirements_in_force` | `[{requirement_id, label, evidence_class, experimental}]`, `evidence_class` the domain name (O13) |
| `model_note` | `MODEL_DIFFERS` formatted with the labels in force here and the labels the main XI Lab model holds (always the three of `decision_inputs`), or `null` when they are equal; CEILING and RISK replies (1.3) |
| `declared` | the declared rows (7.6) |
| `result` | the tool's dataclass, plus text fields (below) |
| `ledger` | the computed rows (7.6) |
| `evidence` | `shell.evidence_payload` of the whole result |
| `verdicts` | risk only: `{"risk_rule": verdict_payload(...), "risk_report": verdict_payload(...) or null}` |
| `claim`, `non_claim`, `statements` | fixed sentences of 7.7, formatted by the router |
| `budget` | `budget.report(result completeness)` |
| `provenance` | `{"providers": ["pappalardo"], "snapshot": scrub_lineage(snap.provenance), "tool": result.provenance}`; `tool` holds the version, `input_contract` (`kernel.input_contract` plus the declarations), `input_fingerprint`, `source_fingerprints`, and keys under the reserved prefixes `ceiling_`, `conflict_`, `frontier_`, `risk_` (kernel.py:115-127) |

Text fields the router adds (the page prints them and computes nothing; every number the page
shows is one of these or an integer field printed as is):

- CEILING, per range: `largest.attained_text` (the witness's exact sum rounded down,
  `planning._outward`, four decimals), `largest.bound_text` (rounded up), `least.attained_text`
  (up), `least.bound_text` (down), `minimum_text`, the two minimum statements, and `evidence`
  (7.6). The router recomputes `S_r(lineup)` in `Fraction` from the declared candidates' values
  before calling `_outward`; it never floors the float `attained`, which can lie on the other
  side of a four-decimal boundary.
- CONFLICT: per declaration `label_text` ("Slot coverage: Left back", "Exclusion: {name}",
  "Floor on {label}: {value as entered}", "Lock: {name}"); per member the member sentence and,
  for a witness, per slot `player_text` (the name, or "empty") and `note_text` for an excluded
  player the witness uses ("Excluded by you; that exclusion is set aside in this check"); per
  restore test its sentence (7.7); the arithmetic sentence; the deletion order.
- FRONTIER, per point: `point_texts`, the certified coordinates, each `V_i / q` printed exactly
  with five decimals (`q = 100000`), labelled "rounded sum, in club medians" (the unit is the
  requirement's normaliser, the club's median prior starting-XI sum); two distinct points
  never print the same texts. `raw_sum_texts`, the witness's exact sums at four decimals
  rounded down, labelled "one XI reaching it sums to"; `allowance_texts`, `e_r` rounded up.
  When `d = 2`: `plot_x = (V_1 − min V_1) / (max V_1 − min V_1)` and `plot_y = 1 − (V_2 − min
  V_2) / (max V_2 − min V_2)` over the listed points in `Fraction`, served as decimal strings
  with six places, `0.5` when a range is zero; `plot_y` is already in SVG orientation (larger
  sums higher on screen), for a fixed `viewBox="-0.05 -0.05 1.1 1.1"`.
- RISK: every pair as `maximum_shortfall_text`, `total_shortfall_text` (exact decimals of
  `M / q`, `T / q`); the tail sums as `summed_maximum_shortfall_text`,
  `summed_total_shortfall_text`; `boundary_ties_text` ("Worlds outside the tail with the same
  pair as its last world: 3, 7." or "None."); `point_sum_texts` (exact sums rounded down at four
  decimals) and the point pair's texts; the rule label; `world_count_text` ("12 worlds, 11
  used"); the membership block as `membership.groups`, a list in the fixed order below, each
  `{heading, rows}` with the rows in `player_id` order and every `(possible, necessary)`
  combination that can occur in exactly one group: `(True, True)` "In every XI this rule
  selects"; `(True, False)` "In some XIs this rule selects, not in all"; `(True, None)` "In some
  XIs this rule selects; whether in all was not decided within the time limit"; `(None, False)`
  "Not in every XI this rule selects; whether in some was not decided within the time limit";
  `(False, False)` "In no XI this rule selects". A player in the XI shown is possible, and one
  outside it is not necessary (that XI is a selection without him), so no other combination
  occurs; a test asserts it.

No key is `total`, `index`, `score`, `rank` or holds a part of `thesis.BANNED_KEY_PARTS`;
`finalize` refuses otherwise.

`GET /api/xi/extensions` returns, through `finalize`: `world_counts` `[12, 40]`;
`tail_counts` `{"12": [2, 3, 6], "40": [4, 10, 20]}`; `rule_options` per world count, in the
fixed order of `RULES`, each `{rule, tail_count, text}` with server text: one `WORST_WORLD`
entry with `tail_count` 1 ("Worst world of 12: the extreme of the tail rule"), one `TAIL` entry
per menu count ("Tail: 3 highest-loss worlds of 12"), one `MINIMAX_REGRET` entry ("Least
largest regret over 12 worlds"); no `TAIL` entry has `tail_count` 1. `requirements`
`[{requirement_id, label, experimental}]` for the three measured requirements, taken from the
same constants `decision_inputs` uses (a test asserts equality with `decision_inputs` on a
synthetic snapshot), the source of every requirement select and of the page's minima filter;
`experimental_requirements` `["left_pass_origins", "right_pass_origins"]` (a test asserts these
are exactly the `RESEARCH` requirements of `decision_inputs`); `dimension_counts` `[2, 3]`;
`max_frontier_points` 64; the opt-in label and sentence; `SIDE_MINIMA_SET_ASIDE` (7.7);
`provenance.providers`.

### 7.6 The ledger (O12) and evidence (O13)

Declared rows, `shell.declared_row`, are a function of the resolved request (the
`model_dump` the cache key hashes), never of which fields were sent, so one key always has one
ledger (the rule of `planning.declared_rows`, planning.py:1249-1263): always the decision
point and the role-slot template; then each lock and exclusion (by name); each minimum and
floor in the request's dicts, as entered (`domain.precision.format_plain`); the dimensions in
order; the experimental opt-in only when true; the world count and the risk rule ("Tail 3 of
12 worlds", "Worst world of 12"). A default minimum that is not in the request's `minimums` is
not a declared row: it appears as a computed row ("Default minimum of {label}: median prior
starting-XI sum", `HEURISTIC`).

Computed rows, `shell.ledger_row`, each conditional on the declared rows: CEILING two rows per
requirement (largest, least: value text "at least {attained}; no XI above {bound}" and "at most
{attained}; no XI below {bound}"); CONFLICT one row ("Declarations that cannot hold together",
"{n} declarations"); FRONTIER one row ("Nondominated rounded sums of {labels}", "{n} points");
RISK three rows: for TAIL and WORST_WORLD the rule's optimum ("Tail sums", value text "summed
largest shortfall {ΣM}; summed shortfall {ΣT}"), for MINIMAX_REGRET the binding worlds of the
XI shown ("Binding worlds of the XI shown", value text "world {id}: this XI ({M}, {T}); least
any XI reaches there ({M*}, {T*})" per binding world, both pairs and never a difference, O8);
then the world count and the discarded count. `solver` is
`"{status} · {certification or completeness} · 1/100000"`. `verdict` is `None` for CEILING,
CONFLICT and FRONTIER (exact computation, no empirical claim: the kit prints "Exact
computation · no empirical claim") and the E-13 payload for RISK.

Evidence: `shell.evidence_payload` of `[(label, evidence.from_xi(r.evidence_class)) for each
requirement the quantity uses] + [("Eligibility rules declared by hand", HEURISTIC), ("Exact
solve on the declared model", evidence.SOLVER_CLASS)]`, composed by `weakest()`; for RISK also
`("Shared resampled prior matches", ESTIMATED)`. Every quantity of every tool uses **every
requirement in force**, because the measurement rule over `R` decides which keys are
admissible (1.1) and so which XIs exist, plus its floors: a progression range with the opt-in
is conditional on the side rates and is `EXPERIMENTAL`. The composed class is `HEURISTIC` on
progression alone and `EXPERIMENTAL` with the opt-in, with the side requirements binding
(ADR-0019). `DECLARED` is never a class (O12). The legacy XI strings stay in provenance only.

### 7.7 Copy

Every sentence below is a module constant, served outside provenance, and passes
`labels.scan_labels` under every format argument a test supplies. The sentences a tool returns
or raises (`claim`, `non_claim`, `RISK_HARD`, `RISK_OVERFLOW`, `RISK_NOT_EVALUABLE`,
`FLOORS_CONSERVATIVE`) are defined in that tool's module, because an optimisation module does
not import the API layer; the router re-exports them and defines the rest. A tool's `claim` and
`non_claim` fields hold the constants of this table word for word; the design notes in sections
2 to 5 are never served (two of them name words the copy guard refuses, by design). A unit test
per tool asserts `scan_labels(asdict(result))` is empty. No shipped warning of `solve_xi` or
`maximize_requirement` is served outside provenance: several fail the guard.

| Constant | Text |
|---|---|
| `CEILING_CLAIM` | For each requirement in force, the least and the largest sum any XI reaches under the eligibility rules, locks, exclusions and declared hard floors, each with one XI that reaches it. The search adds each prior per-90 rate rounded half-even to 1/100000 of the club median; each printed interval contains the exact least or largest sum. |
| `CEILING_NON_CLAIM` | Each range is taken over all XIs for one requirement alone: reaching two minima at once is a different question. A sum is arithmetic on prior rates, not a forecast of what an XI would produce. |
| `CEILING_REACHED` / `_UNREACHABLE` | One XI reaches the minimum of {label} ({minimum}): it sums to at least {attained}. / No XI reaches the minimum of {label} ({minimum}): none sums to more than {bound}. |
| `CEILING_MISSED` / `_EVERY` | One XI stays below the minimum of {label} ({minimum}): it sums to at most {attained}. / Every XI reaches the minimum of {label} ({minimum}): none sums to less than {bound}. |
| `CEILING_REACHED_ALLOWANCE` / `_NOT_CERTIFIED` | Whether an XI reaches the minimum of {label} ({minimum}) is not settled: it lies inside the rounding allowance of the search. / Whether an XI reaches the minimum of {label} ({minimum}) is not settled: the largest end was not certified within the search limits. |
| `CEILING_MISSED_ALLOWANCE` / `_NOT_CERTIFIED` | Whether every XI reaches the minimum of {label} ({minimum}) is not settled: it lies inside the rounding allowance of the search. / Whether every XI reaches the minimum of {label} ({minimum}) is not settled: the least end was not certified within the search limits. |
| `CEILING_NOT_CERTIFIED` | This end of the range was not certified within the search limits. No value is implied. |
| `FLOORS_CONSERVATIVE` | No XI meets the declared floors in the conservative comparison: each rate rounded down and each floor rounded up to 1/100000 of the club median, so an XI that meets a floor exactly on its boundary can be excluded. |
| `CONFLICT_CLAIM` | These declarations of yours cannot all hold together. Leave out any one of them and the others in this set can hold together, with every declaration outside the set also set aside. That check leaves out your other declarations: dropping one of these alone may still leave no XI, and each one says whether it does. This is one such set: checking in another order can return another, and it is not the smallest by count. |
| `CONFLICT_NON_CLAIM` | Eligibility rules, the minutes gate and missing measurements are part of the model and are never offered for removal. Nothing was relaxed in the solve this explains. |
| `CONFLICT_HALF_EVEN` (gated, item 13) | Minima are compared as the Satisfy rule compares them: each rate and each minimum rounded half-even to 1/100000 of the club median. |
| `CONFLICT_CONSERVATIVE` | Floors are compared conservatively: each rate rounded down and each floor rounded up to 1/100000 of the club median, so an XI that meets a floor exactly on its boundary can be excluded. |
| `CONFLICT_CONSERVATIVE_FOR_SOLVE` | The solve above compares minima half-even; this explanation compares them conservatively, which is stricter. These declarations cannot all hold together in the conservative comparison; under the solve's own comparison this set alone may hold together. Whatever the solve above could not hold, the conservative comparison cannot hold either, so an explanation always exists. |
| `CONFLICT_MEMBER_WITNESS` | Leave this declaration out, set aside every declaration outside this set, and the others in this set can hold together. One assignment is shown; it meets only those, so a place can be empty and a player you excluded can appear. |
| `CONFLICT_MEMBER_UNDECIDED` | Leaving this declaration out was not decided within the search limits. The set still cannot hold together, but it may not be minimal. |
| `CONFLICT_RESTORES_YES` / `_NO` | Dropping only this declaration, with all your others kept, leaves at least one XI. One is shown. / Dropping only this declaration, with all your others kept, still leaves no XI: another conflict remains. |
| `CONFLICT_RESTORES_UNDECIDED` / `_SLOT` | Whether dropping only this declaration leaves an XI was not decided within the search limits. / An XI fills every place, so leaving this one empty is not a way to field one. |
| `CONFLICT_FEASIBLE` | Every declaration holds in at least one XI, so there is nothing to explain; one such XI is shown. |
| `CONFLICT_SOLVE_NEEDS_OPT_IN` (gated) | The solve above holds the two EXPERIMENTAL side pass-origin requirements; explaining it needs the experimental opt-in. |
| `FRONTIER_CLAIM` | Every combination of rounded sums of the declared requirements that no XI's rounded sums match or exceed on all of them while exceeding it on one, each with one XI that reaches it. A rounded sum adds each prior per-90 rate as a multiple of the club median, rounded half-even to 1/100000, and is printed exactly. Beside each point, the sums of one XI reaching it before rounding; they can differ from the point by the allowance shown. |
| `FRONTIER_NON_CLAIM` | Not a ranking: no point is preferred, and the list follows the order in which you declared the requirements. A point says nothing about requirements you did not declare, and a sum is arithmetic on prior rates, not a forecast. |
| `FRONTIER_COMPLETE` | Complete: a final solve proved that every XI's rounded sums are no more than one of these points on every declared requirement. |
| `FRONTIER_LIMIT` / `_STOPPED` | The limit of {n} points was reached and another point exists. The list is not complete. / The search stopped after {n} points. Each listed point is certified; other points may exist. |
| `FRONTIER_OPT_IN` | With the requirements this XI Lab model holds, two or more declared sums need the two EXPERIMENTAL side pass-origin requirements, which enter only through the experimental opt-in. |
| `RISK_WORST` | Worst world of {B}, the extreme of the tail rule for these {B} worlds (a tail of one world): an XI whose single highest-loss resampled world is least, comparing the largest shortfall first and then the summed shortfall. |
| `RISK_TAIL` | Tail {k} of {B}: an XI whose {k} highest-loss resampled worlds have the least summed loss, comparing summed largest shortfalls first and then summed shortfalls. |
| `RISK_REGRET` | Least largest regret over {B} worlds: in each resampled world an XI's largest and summed shortfalls are set against the least pair any XI reaches there, and an XI whose largest gap is least is chosen. |
| `RISK_WITNESS` | The worlds listed are those of the XI shown. Another XI this rule selects reaches the same value and can have other highest-loss or binding worlds. |
| `RISK_BALANCE` | This rule compares shortfalls whatever the decision rule of the solve above: a Satisfy minimum is not a constraint here. |
| `RISK_UNTESTED` | E-13 has not tested this rule. |
| `RISK_GROWTH` | A worst case over resampled worlds grows with their number. This one is over {B} worlds, of which {U} were used. |
| `RISK_NON_CLAIM` | Stability against resampling of the historical matches; not robustness to opponents, absences or form, and not a forecast. |
| `RISK_DISCARDED` | {d} of {B} worlds were set aside: in each, a player who can be selected has no value in that world for a requirement in force here ({labels}) at a place he is eligible for: he has no recorded minutes in that world's resampled matches, or no value at all. The main solve's resampling sets worlds aside by this rule over its own requirements. |
| `RISK_SAME_DRAW` (`B = 12`) | These are drawn as the main solve draws its {B} resampled worlds: the same seed and the same matches. Its selection frequencies use only the worlds it certified under its own decision rule and requirements, which can be fewer. |
| `RISK_PREFIX` (`B = 40`, while the prefix test holds) | The main solve's 12 resampled worlds are worlds 0 to 11 of these 40. Its selection frequencies use only the worlds it certified under its own decision rule and requirements. |
| `RISK_HARD` | Declared-risk rules compare shortfalls; a hard minimum is a Satisfy question. |
| `RISK_OVERFLOW` | The declared minima are too large for the exact integer model of this rule. |
| `RISK_NOT_EVALUABLE` | No world, or fewer worlds than the tail count, could be used, so this rule was not evaluated. |
| `MODEL_DIFFERS` | This answer's model holds {labels_here}; the solve above holds {labels_main}. Differences between the two XIs can come from that alone. |
| `SIDE_MINIMA_SET_ASIDE` | Without the experimental opt-in, the side pass-origin minima of the solve above are not part of this question. |
| `UNKNOWN_PLAYER` | A locked or excluded player is not a candidate of this decision point. |
| `OPT_IN_LABEL` | Include the two EXPERIMENTAL side pass-origin requirements |

`RISK_SAME_DRAW` and `RISK_PREFIX` state how the worlds are built, which the router knows
without seeing the main reply; neither says that the main solve used these worlds, and the
certificate prints the world fingerprint so a reader can compare it with the main solve's.
The earlier sentence that the worlds "are the worlds the main solve's selection frequencies
use" is withdrawn: the main solve sets aside, besides discarded worlds, every world it could
not certify (solver.py:566-568), under its own mode and requirements.

### 7.8 Caching, budgets, failures

A reply is stored when `runtime.is_complete` holds: every `completeness` in it `EXACT` or
`COMPLETE`, the membership block included. Proved terminal outcomes are `EXACT` or `COMPLETE`
(1.5) and are stored: `UNFIELDABLE`, `NOT_SATISFIABLE`, `NOT_EVALUABLE` (with an `EXACT`, empty
membership block) and `MODEL_FEASIBLE`. `DEADLINE`, `LIMIT_REACHED` and `MODEL_INVALID`
replies are returned and computed again next time; a reply whose membership is undecided is
one of them, and an identical request in flight is still computed once
(`RESULTS.get_or_compute`). Status codes are the runtime's: 404 unknown
scenario, 422 refusal (with the tool's sentence), 429 busy, 503 corpus absent, 500 for a
`BoundaryViolation` or an internal fault (`KeyError`, `RuntimeError` from a witness check).

### 7.9 What does not change (R13)

`decision_lab.py`, `runtime.py` (unless the root grants the long-route request of section
12), `shell.py`, `planning.py`, `squad_lab.py`, `transfer_lab.py`, `labs-shared.js` and every
frozen file are untouched; `decision_lab.snapshot` is neither called nor cleared by the new
routes, and the snapshot objects the shipped routes hold are never handed to a new tool; the
five shipped `/api/xi/*` routes answer byte for byte as before; `runtime.router` still serves only `/api/evidence/verdicts`
(`tests/test_lab_runtime.py:798`); runtime, squad and transfer still serve exactly 14 API
routes (`tests/test_planning_api.py:1643-1647`). `runtime.source_fingerprint()` changes because
new files exist under `optimization/` and `api/`; that is intended (no result store ships).

## 8. XI Lab page parts: `web/xi-extensions.js`, `web/xi-extensions.css`

### 8.1 Placement and wiring

ROOT 2.3 puts the three additions on the XI page; R13 asks for new capability in new files and
leaves shared files to the root. The page parts therefore live entirely in two new files and
reach `web/xi.html` through five additive root edits (section 12), which change no existing
element, id, text or handler: a stylesheet link, one mount `<div id="xi-extensions"></div>`
after `#tradeoff-panel`, two script tags after the inline script (`labs-shared.js`, then
`xi-extensions.js`), one call `XiExtensions.mount(document.getElementById('xi-extensions'))`
in a script tag after them, and two `CustomEvent` dispatches inside `solve()`:
`xi:invalidated` when a solve starts and when a main minimum is edited, `xi:solved` after
`render()` with `detail = {input: solvedInput, status: d.solution_status}`. Whether the root
makes these edits is a ruling (DISSENT 4, section 11 item 14); if it refuses, the same two
files serve the stand-alone page of 8.4 and nothing else changes.

`xi-extensions.js` reads the page only through these events; it never reads `result`, `locks`
or any page-scope name, and it declares nothing in script scope (one global,
`window.XiExtensions`), so it can follow the page's `$`, `esc`, `num`, `pct` and `api` as
`labs-shared.js` does (labs-shared.js:13-15). Evaluating the file touches no `document`: the
render test harness, whose `document` throws on any access (test_shell_render.py:44), loads it
and never calls `mount`.

The file has two parts. `window.XiExtensions.render`: pure functions, payload to markup string,
every server string through `Shell.esc`, no element touched, the discipline of the shared kit.
`window.XiExtensions.mount(root)`: the controller that builds the four panels, fetches
`GET /api/xi/extensions` once, listens to the two events, sends requests through `Shell.api`,
and discards a response whose request version is not the latest (the page's own
`requestVersion` rule). It is called only by the page.

Ledger ids. `Shell.ledger` emits the fixed ids `ledger-declared` and `evidence-ledger`
(labs-shared.js:185-198), and this section shows up to four ledgers on one page.
`XiExtensions.render.ledger(prefix, declared, rows)` calls `Shell.ledger` and replaces exactly
those two attributes, each of which must occur once in its output, with
`id="{prefix}-ledger-declared" class="xi-ledger-declared"` (on the declared table) and
`id="{prefix}-evidence-ledger"`; `xi-extensions.css` repeats the `#ledger-declared` rules of
labs-shared.css:40-41 for `.xi-ledger-declared`. If either id is not found exactly once the
function throws, so a change to the kit fails a test instead of producing duplicate ids.
Section 12 offers the root the cleaner fix, an optional prefix argument to `Shell.ledger`
whose default leaves every shipped page's bytes unchanged; if granted, the rewrite goes.

### 8.2 The panels

One section, four panels in a fixed order. One checkbox above them, `#xi-experimental-opt-in`,
unchecked on every load, labelled `OPT_IN_LABEL`; ticking it sends `experimental_opt_in: true`
on the next request of every panel and prints the composed class beside every number. Before
`xi:solved` every button is disabled and each panel reads "Re-solve the main XI first.";
`xi:invalidated` disables them again and clears every panel. **No panel sends a request on its
own**: every POST follows a press of that panel's button, so a shipped flow that presses no
new button sends no new POST, and the only new request on load is the corpus-free `GET`.

Request body, every panel, built from `event.detail.input` (the main solve's `scenario_id`,
`formation`, `mode`, `locks`, `excludes`, `minimums`) and the `GET` reply's `requirements`:
`scenario_id`, `formation`, `locks` and `excludes` copied from the main solve, so a panel
never fields a player the main solve excluded; `experimental_opt_in` from the checkbox;
`minimums` (ceilings, conflict, risk) the main solve's minima restricted to the requirement ids
whose `experimental` flag is false when the opt-in is unticked, and all of them when it is
ticked. Restricting keys by a server flag is the one selection the page makes; it decides
nothing about what is in force (the server does, and refuses a side minimum without the
opt-in). When a key was left out the panel prints `SIDE_MINIMA_SET_ASIDE`.

| Panel | Shown when | Request | Renders (server field) | States |
|---|---|---|---|---|
| `#conflict-panel` "Which declarations cannot hold together" | the last main solve is `INFEASIBLE` | button `#explain-conflict`, "Explain, including the two EXPERIMENTAL requirements the solve above used"; `POST /api/xi/conflict` with the common body, the opt-in sent as true whatever the checkbox (the main solve had them in force), all three minima, `explains: "floors"`, and `floors` omitted when the main mode was `SATISFY` (every requirement in force a floor at its minimum) or `{}` when it was `BALANCE` (its minima were not constraints). After the ruling of item 13: `explains: "solve"` and the main `mode` instead | status badge; `CONFLICT_CLAIM`; the arithmetic sentence (`CONFLICT_CONSERVATIVE_FOR_SOLVE` for a Satisfy solve explained conservatively; `CONFLICT_HALF_EVEN` after item 13); one row per member of `result.conflict` in server order: family, `label_text`, the member sentence, the restore sentence; a `<details>` per member with its assignment (slot label, `player_text`, `note_text`) and, when the restore test found one, the XI without that member; certificate (solves, statuses, `final_set_proof_solve`, completeness, deletion order); ledger, prefix `conflict` | `MODEL_FEASIBLE`: `CONFLICT_FEASIBLE` and the XI; `UNDECIDED`: `Shell.notCertified`; 422, 503 through `Shell.errorText` |
| `#ceilings-panel` "Attainable range of each requirement sum" | after `xi:solved` | button `#solve-ceilings`; `POST /api/xi/ceilings` with the common body; no floors from the page | claim, non-claim and `model_note`; a table, one row per range in server order: label and evidence badge (`evidence`, the domain class); least `attained_text`/`bound_text`; largest `attained_text`/`bound_text`; the two minimum statements; certificate details; ledger, prefix `ceilings` | an end not certified: `CEILING_NOT_CERTIFIED` in its cell, no number; `UNFIELDABLE`: `Shell.infeasible(reasons)` |
| `#frontier-panel` "Nondominated requirement sums" | after `xi:solved` | selects `#frontier-dim-1..3`, each starting empty with the placeholder "Choose a requirement", options the `GET` reply's `requirements` (only those with `experimental` false while the opt-in is unticked, labels as served); the button `#solve-frontier` is enabled only with two or three distinct choices; `POST /api/xi/frontier` with `scenario_id`, `formation`, `locks`, `excludes`, the opt-in and `dimensions` in the chosen order; no minima (sums, not shortfalls) and no floors | the claim and non-claim; a table, one row per point in server order, one column per declared dimension (`point_texts`), a column "one XI reaching it sums to" (`raw_sum_texts`), the allowances (`allowance_texts`), a "One XI" toggle showing the lineup; for `d = 2` an SVG with `viewBox="-0.05 -0.05 1.1 1.1"` and one circle per point at (`plot_x`, `plot_y`), every circle the same size, colour and stroke; the `point_order` sentence; certificate (points, solves, completeness, `stopped_by`, final region status) | without the opt-in, `FRONTIER_OPT_IN` and the button disabled; `LIMIT_REACHED`, `DEADLINE`: the sentence above the table; `UNFIELDABLE`: `Shell.infeasible(reasons)`; `NOT_SATISFIABLE`: `Shell.infeasible([FLOORS_CONSERVATIVE, ...reasons])`; one point: the same table with one row |
| `#risk-panel` "Declared risk preference over resampled matches" | after `xi:solved` | `#risk-worlds` (12 or 40) and `#risk-rule` (the `GET` reply's `rule_options[B]` texts, fixed order), both starting on an empty placeholder; the button `#solve-risk` is enabled only when both are chosen; `POST /api/xi/risk/tail` with the common body, `bootstrap_worlds`, `rule` and, for `TAIL`, `tail_count`; or `POST /api/xi/risk/regret` with the common body and `bootstrap_worlds` | the rule label and `RISK_UNTESTED` while not executed; `Shell.verdictBadge` and `verdictLines` of `verdicts.risk_rule`; the non-claim, `model_note` and `RISK_BALANCE`; roster (slot, player) of `result.lineup`; TAIL and WORST_WORLD: the tail sums' texts, a table "For the XI shown" of the tail worlds (world id, `maximum_shortfall_text`, `total_shortfall_text`), `boundary_ties_text`, `RISK_GROWTH`; REGRET: a table "For the XI shown" of the binding worlds with both pairs, and every world's two pairs in `<details>`; `RISK_WITNESS` under each such table; the point-estimate pair's texts and `point_sum_texts`; the membership groups (server headings, server order); certificate: B, used, discarded count and list, world seed, fingerprint, `RISK_SAME_DRAW` or `RISK_PREFIX` when served, solves, statuses, completeness, both deterministic limits; ledger, prefix `risk` | `NOT_EVALUABLE`: `RISK_NOT_EVALUABLE`; `UNKNOWN`: `Shell.notCertified`, no XI; `UNFIELDABLE`: `Shell.infeasible(reasons)`; 422 overflow sentence as sent |

### 8.3 Rules of the page

- R10: JS computes no eligibility, coverage, objective, uncertainty, bound, count or plot
  position. Every number printed is a server string (`*_text`, `*_texts`, `value_text`,
  server-formatted counts) or a server integer field printed as is (world ids, `solves`,
  `final_set_proof_solve`, point counts); `plot_x` and `plot_y` are server strings placed as
  SVG coordinates in the fixed `viewBox`, never transformed. JS never sorts, filters or groups
  rows; it prints them in the order received, and the membership groups arrive grouped. The
  one selection it makes is by the server's `experimental` flag (8.2).
- No ranking or highlighting of a frontier point: every row and every circle has the same
  classes and computed style; nothing is selected on arrival; the detail area reads "Choose a
  point to see one XI that reaches it." A point the reader opens gets the outline every opened
  row gets, and nothing else changes. None of the words O7 forbids, nor "dominant" or
  "recommended", appears; the page prints the server's `point_order` sentence under the table.
- No rule is preselected, and the order of rules never depends on a verdict token (E-13).
- No `%` sign and no word of chance appears in the risk panel.
- Every per-world table of the risk panel is titled "For the XI shown" and followed by
  `RISK_WITNESS`.
- Ids are unique on the page (8.1).
- Mobile: the tables use the kit's `data-label` cells and stack at 600 px and below; the SVG has
  its fixed `viewBox` and `width: 100%`; at 390 and 320 px `#xi-extensions` itself has
  `scrollWidth ≤ clientWidth` (the shipped parts of `/xi` are not measured at 320 px by this
  work).
- Colour: gold (`rgb(201, 162, 39)`) is not used on any number of the new panels, as the
  tradeoff test already checks on its own panel.

### 8.4 Fallback page, if the root refuses the `xi.html` edits

`web/xi-extensions.html`, served at `GET /xi/extensions` by the new router, is a complete page
of its own; `/xi` is then not touched at all. Head: `labs.css`, `labs-shared.css`,
`xi-extensions.css`. Body, in order: `Shell.nav` markup; a header "XI exact tools" and one
sentence, "These panels explain the XI Lab solve made on this page; the XI Lab page itself is
unchanged."; the controls `#fb-scenario` and `#fb-formation` (options from
`GET /api/xi/scenarios`), `#fb-mode` ("Balance shortfalls", "Satisfy all minima"),
`#fb-minimums` (one number input per measured requirement, filled from the last solve reply's
`requirements[].minimum`, `min=0 max=1000`), `#fb-players` (one row per candidate of the last
solve reply with a lock and an exclude checkbox), and `#fb-solve` "Solve the XI"; `#fb-status`;
`#fb-roster` (slot and player of the reply's assignments); then `<div id="xi-extensions">`.
`#fb-solve` sends `POST /api/xi/solve` with `{scenario_id, formation, mode, locks, excludes,
minimums, bootstrap_worlds: 12}`, the body XI Lab sends; it dispatches `xi:invalidated` when it
starts and whenever a control changes, and `xi:solved` with `{input, status}` after the
roster is printed. The page's inline script, after the two script tags, calls
`XiExtensions.mount(document.getElementById('xi-extensions'))` and solves once on load with
the default scenario. Its own e2e spec repeats the panel tests of section 9 on this page.

## 9. Tests

Oracles import nothing from the module under test; differential references (`solve_xi`,
`maximize_requirement`, `kernel.satisfiable`, `kernel.value`, `bootstrap_selection`) are named
as such and are never the oracle. Each rule test set contains the interesting outcome and its
opposite. Seeded instances: seeds `0..119` per oracle-equality test unless stated. Where a
level set can hold several XIs, a test compares optima, level-set membership, and the tool's
per-world reports recomputed by the oracle **for the lineup the tool returned**; it never
compares the tool's witness with an oracle witness. Every tool file asserts
`scan_labels(asdict(result))` is empty on every instance, and that each completeness token is
one of 1.5 and `runtime.is_complete` holds exactly on `EXACT` / `COMPLETE` replies, including
every proved terminal outcome.

| File | Tests |
|---|---|
| `test_xi_ceilings.py` | integer ends equal the oracle's `min`/`max` of `O_r` over `𝒳_F`, with and without floors, locks, exclusions, `None` values, zero minutes and negative rates; every feasible oracle `S_r` lies in the bracket, in `Fraction`; witnesses admissible, floors met in integers and `Fraction`, `O_r` recomputed equal; the two minimum facts equal the oracle's truth whenever not `None`, and `None` occurs only with reason `ALLOWANCE` (the minimum between witness and bound) or `NOT_CERTIFIED` (a planted case of each of the four decided outcomes and of each reason); a `FEASIBLE_NOT_PROVEN` end decides a fact by its witness or its bound; with `φ_r ≠ m_r` the facts use `m_r`; `UNFIELDABLE` by construction and by proof, `NOT_SATISFIABLE` with floors, each `EXACT`; parity, on instances whose oracle feasible set is not empty: with floors equal to every active minimum the LARGEST end equals `maximize_requirement`'s `integer_value`, `integer_upper_bound` and certification, and each witness's raw sum lies in the other's bracket (witnesses are not compared); a passed deadline gives `NOT_RUN` everywhere, no number, `DEADLINE`; a monkeypatched `FEASIBLE` status gives `FEASIBLE_NOT_PROVEN` with a bracket that still contains every oracle sum; a monkeypatched response whose deterministic time reached the limit gives `LIMIT_REACHED` and `stopped_by = DETERMINISTIC_LIMIT`, one whose wall time ran out `DEADLINE` and `WALL_CLOCK`; a tampered witness raises `RuntimeError`; the objective coefficients equal `round(_scaled(...))` and differ from `_q` on `1.344465 / 1.0` at 100000; determinism; shuffled candidates and requirements give an identical `asdict` |
| `test_xi_conflict.py` | `explain_floors`: the returned set equals the oracle's deletion filter in the declared order (equality, not just minimality); the oracle finds the set not satisfiable and every set with one member removed satisfiable; each restore test equals the oracle's `restores_alone` (`NOT_APPLICABLE` for slot coverage); `MODEL_FEASIBLE` iff the oracle finds an XI, `EXACT`; parity: `explain_floors()` is `MODEL_FEASIBLE` iff `kernel.satisfiable` is `SATISFIABLE`; the instance of 3.3 (`exclusion:A`, an unreachable floor, `lock:A`) returns `{floor:progression}` with a witness that has empty slots, and its restore test is `False`; two planted independent conflicts give one set whose members all have `restores_alone = False`, and no served sentence of the reply states that dropping a member leaves an XI; a witness that uses an excluded player lists him in `witness_excluded_players`; a locked-and-excluded player gives exactly `{exclusion:p, lock:p}`; a slot no admissible player can fill gives `{slot:s}`; a monkeypatched `UNKNOWN` on one filter test gives `NOT_PROVEN_MINIMAL`, that member `KEPT_UNDECIDED`, never `MINIMAL_CERTIFIED`; one on a restore test leaves the status and gives that member `None` and completeness `DEADLINE`; `final_set_proof_solve` points at an INFEASIBLE status of a test of exactly the final set; tables equal `kernel._tables` on shared keys; a tampered witness raises; reordered inputs give the same set. A planted boundary instance feasible under half-even and not conservatively returns a set holding the floor from `explain_floors`. After the ruling of item 13 only: `explain_solve` against the oracle in half-even, `MODEL_FEASIBLE` iff `solve_xi(mode="SATISFY")` is `OPTIMAL` or `FEASIBLE`, its requirements in force equal `solve_xi`'s active set, and the boundary instance gives `MODEL_FEASIBLE` |
| `test_xi_frontier.py` | the set of `integer_sums` equals the oracle's nondominated set, `d = 2` and `d = 3`, with floors, locks and exclusions; every oracle feasible vector is weakly below a point; points pairwise nondominated; witnesses verified; the planted instance of 4.1 (two XIs sharing an integer vector with different raw sums) gives one point whose served texts are the integer coordinates, and the oracle's XI with larger raw sums is weakly below it in the integers; `max_points=1` on an instance with at least two points gives one point of the oracle set, `LIMIT_REACHED`, `stopped_by = POINT_LIMIT`, `final_region_status = OPTIMAL`; a monkeypatched `UNKNOWN` at stage 2 of the third iteration gives exactly the two earlier points, `DEADLINE`; reversing a two-dimension declaration reverses the list and swaps every pair; the list follows `POINT_ORDER`; no default dimension (calling without `dimensions` is a `TypeError`), `d ∉ {2, 3}`, a repeat or an inactive requirement is a `ValueError`; empty feasible set as `UNFIELDABLE` and `NOT_SATISFIABLE`, each `COMPLETE`; claim and non-claim equal the 7.7 constants and hold none of the words O7 forbids; determinism; shuffled inputs give an identical `asdict` |
| `test_xi_risk_oracle.py` | (the E-13-pinned file) on every seeded instance, with `U` from the oracle's `used_worlds`, and every `k ∈ 1..|U|`: TAIL's `tail_sum` equals the oracle's optimum and the selected player set is in the oracle's level set; the tail ids and boundary ties equal the oracle's `tail_of(lineup, k)` for the returned lineup; REGRET's per-world least pairs and optimum equal the oracle's, the selected set is in its level set, and the binding worlds equal `binding_of(lineup)`; `world_losses` equals the oracle's pairs; membership equals the oracle's level-set membership; the instances are not vacuous: across the 120, some level set has more than one XI and some exactly one, some TAIL selection differs from BALANCE's and some equals it, some tail is decided by `T` at equal `M`, some instance discards a world, and some summed `T` over a tail exceeds `T_bound` |
| `test_xi_risk.py` | single-world invariant: TAIL(1) and REGRET equal `kernel.value(values=…)` in integers, `solve_xi` on world-replaced candidates by `round(v * q)` of its `objective_vector`, and the oracle; WORST_WORLD equals TAIL(1) in everything but `rule`, `certificate.rule`, `claim` and the provenance fingerprints; TAIL(`|U|`) is the lexicographic minimum of (`Σ M`, `Σ T`); the discarded list equals `bootstrap_selection`'s `bootstrap_discarded_worlds` and the fingerprint its `bootstrap_world_fingerprint` on the same inputs; a world dict missing a player discards the world, as the bootstrap does; doubling BIG (monkeypatched `_encoding_base`) leaves status, optimum (`tail_sum` or the regret optimum) and membership unchanged; two planted deterministic instances, one TAIL with `k = 2` and one REGRET, on which `BIG = T_bound + 1` provably selects a different set (the carry of 5.1), give the oracle's selection with the shipped BIG and another with the monkeypatched small one; no encoding leaves: the test recomputes BIG, the selection optimum `Φ*` or `ρ*`, every `E^w` of the returned lineup with `M^w ≥ 1` and every `E*^w` with `M*^w ≥ 1`, and asserts that none appears in `asdict(result)` as an integer or as a whole digit token (`\b...\b`) of a string, except where it equals a value served under an allow-listed path (ids, counts, seeds, `quantization`, `LossPair` and `TailSums` fields); no key contains `encod`, `big`, `base` or `objective`; none of those integers appears as a token in `caplog`; the overflow guard refuses above `2**53` with a sentence holding no digit; a hard requirement is a `ValueError`; `|U| < k` gives `NOT_EVALUABLE` with no solve, `EXACT`, an `EXACT` empty membership block; two locked goalkeepers give `UNFIELDABLE` (not `UNKNOWN`) for TAIL, WORST_WORLD and REGRET, `EXACT`, no lineup; a passed deadline gives `UNKNOWN`, no lineup; one per-world optimum `UNKNOWN` gives `UNKNOWN` with that world in `undecided_world_ids`; shortfalls use `_q`: a planted `1.344465 / 1.0` coefficient at 100000 gives `_q`'s integer; `world_seed` and `bootstrap_version` reach the certificate unchanged; `TAIL_MENU` plus `WORST_WORLD` at 1 equals the E-13 draft config's `tail_counts` for `B ∈ WORLD_MENU`; the prefix property of 1.4 (`shared_match_weights(games, 12, SEED)` equals the first 12 rows at 40), with the numpy version it was checked on recorded in the test; determinism; shuffled candidates, requirements and world order give an identical `asdict` |
| `test_xi_extensions_api.py` | with a synthetic snapshot patched into the router's loader: each route answers 200 with the envelope of 7.5 and passes `runtime.finalize` (providers, `banned_key_paths` with `BANNED_KEY_PARTS`, `scan_labels`); every constant of 7.7 passes `scan_labels` under the format arguments the router uses; an extra field, a non-strict integer, a branch field of the other `explains`, a repeated dimension, `tail_count` 1 or an off-menu count with `TAIL`, any `tail_count` with `WORST_WORLD`, `bootstrap_worlds` 0 or 80, a side requirement without the opt-in, an unknown player id are each 422 with a body holding no input value; unknown scenario 404; a missing corpus file 503; the risk overflow is 422; identical requests are one computation (cache `hit`); reordered and repeated locks are one key; a request that sends a default and one that omits it share one key and receive identical declared rows, which hold the decision point and template rows and the opt-in row only when true; a `DEADLINE` reply is not stored; proved terminal replies are stored; `budget` holds the route's seconds; `model_note` is present exactly when the in-force set differs from the main model's; the default minima are computed rows, not declared rows; evidence composes to `HEURISTIC` without the opt-in and `EXPERIMENTAL` with it on every tool, the progression range included; RISK carries the E-13 `NOT_REGISTERED` payloads, `RISK_UNTESTED`, and the subject of its rule; a REGRET reply's ledger row holds two pairs per binding world, and no served number equals a component of `(M − M*, T − T*)` for any world unless it also equals a served pair component; the encoding check of `test_xi_risk.py` repeated on the served reply; `GET /api/xi/extensions` is corpus-free and finalized, its `requirements` equal `decision_inputs`'s measured requirements and no `TAIL` option has `tail_count` 1; snapshot immutability: the router loader's snapshot, and a snapshot patched into `decision_lab.snapshot`, deep-copied before and compared after each new route, are unchanged; with all sixteen in-flight places held each new POST answers 429 with `Retry-After`, and REGRET holds a long-job place; two concurrent requests of different routes on one `(scenario, worlds)` build the snapshot once (the gate); `corpus_token()` equals `planning.corpus_token(planning.FLAGSHIP)`, with the tmp-corpus pattern of `tests/test_planning_api.py:437`; R13: the five shipped `/api/xi/*` paths, their methods and their replies on the synthetic snapshot are byte-identical in an app with and without this router; no path is served twice |
| `test_xi_extensions_render.py` | under node, the harness of `test_shell_render.py` (the page-scope names first, then `labs-shared.js`, then `xi-extensions.js`, which loads without touching `document`; `mount` is never called), the render functions on replies built by the real router on the synthetic snapshot: no `undefined`, `NaN` or `[object`; hostile strings escaped; every digit run in the visible text (`shell.visible_text`) equals a server string of the reply or the decimal form of a server integer at the path the renderer reads; rows in reply order; membership groups printed in server order under server headings; two distinct frontier points never print identical coordinate texts; every frontier row and circle has the same class list and `plot_x`/`plot_y` appear unchanged as coordinates; no element is marked selected on arrival; the markup of all four panels together has unique ids, and the ledger rewrite throws when either kit id is absent; `scan_labels` of the visible text is empty; no `%` in the risk markup; empty, `DEADLINE`, `LIMIT_REACHED`, `NOT_EVALUABLE`, `UNDECIDED`, `MODEL_FEASIBLE`, `UNFIELDABLE`, `NOT_SATISFIABLE` (with `FLOORS_CONSERVATIVE`) and opt-in-missing states each render their sentence; `xi-extensions.js` declares nothing in script scope. A unit test (Python) asserts that `web/xi.html` with the five insertions of section 12 removed has the sha256 of the shipped file |
| `e2e/xi-extensions.spec.js` | `/xi` solves and the four panels mount with buttons disabled until `xi:solved`; no `pageerror` and no console error anywhere in this spec; the shipped flows (apply minima, a lock, a preset, a mode change, as `repairs.spec.js` drives them) with the panels mounted send no new POST and log no console error; after applying minima with the opt-in unticked, pressing `#solve-ceilings` sends only the progression minimum, answers 200 and shows `SIDE_MINIMA_SET_ASIDE`; ceilings: the request carries the main locks and exclusions, and each cell's text equals the reply's `*_text` exactly; frontier: the selects start empty, the opt-in starts unchecked and the opt-in sentence shows; after ticking it and choosing two dimensions the request carries them in order with the opt-in, the main locks and exclusions and no minima; rows equal the reply's points in order and print `point_texts`; every row and circle has equal computed style; after opening a point only that row's outline changes; risk: the selects start empty and the button is disabled; options equal the server's `rule_options` in order; a TAIL request carries the main locks, exclusions and filtered minima, `rule` and `tail_count`, and the tail world ids equal the reply's; a REGRET request at `B = 12` renders the binding worlds with two pairs each; the certificate shows B, seed, fingerprint and discarded count; the panel text holds no `%`; the badge reads RECORD ONLY · NOT TESTED; conflict: with mode Satisfy and the progression minimum at 1000 the main solve is INFEASIBLE, the conflict panel appears, the explain request carries the opt-in, `explains: "floors"` and no `floors` key, and the rows equal the reply's `conflict` in order, holding `floor:progression`, each with its restore sentence; a frontier reply fulfilled from a recorded `DEADLINE` body renders the deadline sentence; the page has no duplicate id; at 390 and 320 px `#xi-extensions` has `scrollWidth ≤ clientWidth`; the shipped panels behave as before (the tradeoff, alternatives and repairs specs are unchanged and still pass) |

**Slow tests** (`@pytest.mark.slow`, skip without the corpus), one per tool file, on the
6 May Madrid snapshot: CEILING ends equal a brute-force enumeration of the real snapshot's XIs;
the three-dimensional FRONTIER under the opt-in equals the brute-force nondominated set (the
count is compared with the brute force, not with a pinned number, section 1.6); CONFLICT
(`explain_floors`, opt-in) with the BBC preset's locks and a raised progression floor equals
the oracle's deletion filter and restore tests; the oracle's backtracking records its node
count per test, and the test fails, rather than skips, above `10^7` nodes in one test, a guard
on run time and not an expectation about the data; RISK at `B = 12`: the fingerprint equals
`/api/xi/solve`'s `bootstrap_world_fingerprint` for the same scenario; the discarded list equals
the main solve's `bootstrap_discarded_worlds` when the risk request carries the opt-in and the
main solve's exclusions, because the discard rule reads the requirements in force and the
exclusions (1.4) and only then are they the main solve's; on world 0 alone the single-world
invariant holds against `solve_xi`; without the opt-in, the router's requirements equal
`snapshots.snapshot_inputs` on the parity-tested Madrid match snapshot. The `planning.attained`
parity of section 13 compares integer value, integer bound and certification, and each
witness's raw sum inside the other's bracket.

**Not changed:** every existing test file. `test_xi_solver.py`, `test_xi_tradeoffs.py`,
`test_xi_alternatives.py`, `test_tradeoff_oracle.py`, `test_decision_api.py`,
`test_squad_kernel.py`, `test_absence_stress.py`, `test_candidate_injection.py`,
`test_role_brief.py`, `test_planning_api.py`, `test_transfer_api.py`, `test_team_snapshot.py`,
`test_evidence_mapping.py`, `test_lab_runtime.py` (unless the root grants the long-route
request and edits it), `test_web_shell.py`, `test_shell_render.py`, `test_conftest.py` and the
e2e specs pass unchanged; a failure in any of them is a defect of this work, not a reason to
edit it.

## 10. Hashes, fingerprints and provenance

| Object | Rule |
|---|---|
| source fingerprints | `kernel.source_fingerprints(*paths)` (LF-normalised sha256, keys relative to the repository root). CEILING and FRONTIER: their module, `squad/kernel.py`, `xi/solver.py`, `xi/tradeoffs.py`, `xi/domain.py`; CONFLICT and RISK: the same five, with their own module first. `optimization/historical.py` is not listed: no tool imports it, and the snapshot's own provenance carries its lineage |
| input contract | `kernel.input_contract` (canonical model, seed, both kernel policies, the deterministic limit, sources, OR-Tools version) plus the tool's declarations: floors, the compared minima `{requirement_id: m_r}` (CEILING: for a floored requirement the kernel model holds `φ_r`, so `m_r` would otherwise be in no hashed input), dimensions, `max_points`, rule, `k`, `B`, `world_seed`, `bootstrap_version`, the world fingerprint, the arithmetic; never the deadline |
| input fingerprint | `kernel.fingerprint({"version": TOOL_VERSION, "contract": input_contract})`; order-free because the kernel canonicalises its inputs |
| lineage | `scrub_lineage(snap.provenance)`: a new result never inherits a prior certification; the tools' own keys use the prefixes the kernel already reserves |
| frozen files | unchanged bytes; existing tests already pin `historical.py` (E-08), and the four kernel sources |
| line endings | every hash LF-normalised (`core.autocrlf=true` on Windows checkouts) |

## 11. Pre-merge review checklist

The reviewer signs each line before the root registers the router.

1. No frozen file and no root-owned file is in the diff; `kernel.py` is byte-identical.
2. No new module imports `solve_xi`, `maximize_requirement`, `bootstrap_selection`,
   `removal_sensitivity` or `candidate_injection`.
3. Each quantity uses the policy of section 1.2 and no other; no float `≥` comparison decides a
   raw floor (only `Fraction`).
4. Every CP-SAT call goes through `kernel._Run` or `risk._solver`: one worker, the seed, a
   deterministic limit, the remaining wall clock; every status recorded; `NOT_RUN` for a call not
   made.
5. No `UNKNOWN`, `NOT_RUN` or `FEASIBLE` incumbent is reported as an optimum, a proof of
   absence or a necessity.
6. Every witness is re-evaluated without the solver; a failed check raises.
7. `E` and `BIG` appear in no dataclass, provenance value, log call or exception message.
8. The frontier has no default dimension; nothing orders, marks or preselects a point or a rule.
9. Every served string outside provenance passes `scan_labels`; no shipped solver warning is
   served outside provenance.
10. Every reply passes `finalize`; `providers` is exactly `["pappalardo"]`.
11. `xi-extensions.js` computes no number and sorts nothing; `xi.html` edits are the five of
    section 12 and nothing else (the unit test of section 9 passes).
12. The oracle file imports nothing from `galactico`, and no builder wrote the oracle part of
    a tool he implements (section 0).
13. **Gate, DISSENT 2.** The root has ruled on the amendment of ROOT 2.4 (section 12). Until it
    accepts, `conflict.py` exports only `explain_floors`, `ConflictRequest.explains` is
    `Literal["floors"]`, and the page explains a Satisfy solve conservatively with
    `CONFLICT_CONSERVATIVE_FOR_SOLVE`. If it accepts, `explain_solve`, its tests, the
    `"solve"` branch with `CONFLICT_SOLVE_NEEDS_OPT_IN` and the page's switch to it are built in
    one change. If it refuses, they are never built.
14. **Gate, DISSENT 4 and R13.** The root has ruled on the five `xi.html` edits. If it refuses,
    the fallback page of 8.4 is built and registered instead, `/xi` is untouched, and the e2e
    spec targets `/xi/extensions`.
15. **Gate, long route and run time.** The root has answered the `LONG_ROUTES` request for
    `xi.risk.tail` (section 12), and the TAIL and REGRET selection and membership solves have
    been timed at `q = 100000` on the Madrid worlds at `B = 12` and `B = 40` (times and statuses
    only, 7.1), with the numbers in ADR-0030. The `B = 40` option ships only after that timing.
16. The snapshot is loaded only through the gated loader of 7.3; `decision_lab.snapshot` and
    `runtime.match_snapshot` are not called by the new router.

## 12. Requests to the root

| File | Change |
|---|---|
| `galactico/api/player_lab.py` | after `app.include_router(transfer_router)` (player_lab.py:59): `from .xi_extensions import router as xi_extensions_router` with the other router imports, and `app.include_router(xi_extensions_router)`. The module imports no solver and reads no data at import, like the others |
| `web/xi.html` (ruling, item 14) | five additive edits, nothing else: (1) in `<head>`, after the `labs-shared.css` link: `<link rel="stylesheet" href="/static/xi-extensions.css">`; (2) between the closing `</section>` of `#tradeoff-panel` and the `<details>` that holds `#provenance`: `<div id="xi-extensions"></div>`; (3) after the inline `</script>`: `<script src="/static/labs-shared.js"></script><script src="/static/xi-extensions.js"></script>`; (4) after those: `<script>XiExtensions.mount(document.getElementById('xi-extensions'))</script>`; (5) in `solve()`, `document.dispatchEvent(new Event('xi:invalidated'))` as its first statement after `busy=true`, and `document.dispatchEvent(new CustomEvent('xi:solved',{detail:{input:solvedInput,status:d.solution_status}}))` immediately after `render();`; in the `#minimum-inputs` input listener, the same `xi:invalidated` dispatch. `tests/test_web_shell.py` (nav and shared stylesheet) and `tests/test_shell_render.py` (page-scope names) are unaffected |
| `galactico/api/runtime.py`, `tests/test_lab_runtime.py:123` (item 15) | add `"xi.risk.tail"` to `LONG_ROUTES` (it enumerates every candidate for membership, the case the set's docstring names) and to the pinned set in the test. Until granted, a tail request holds no long-job place (7.1) |
| `web/labs-shared.js` (optional) | an optional third argument `prefix` to `Shell.ledger`, prefixing its two ids, default unchanged so every shipped page keeps its bytes. Not required: 8.1 rewrites the ids until then |
| `KNOWN_LIMITATIONS.md` | add now: `decision_lab.snapshot` is an `lru_cache` keyed on `(match_id, worlds)` only, so the shipped XI routes keep a snapshot built before a corpus rewrite until the process restarts (the new routes use the gated loader and do not). When the tools ship: replace the minimal-conflict line (:77-78) by what CONFLICT certifies and in which arithmetic; the Pareto line (:86-89) by "a maximum is not a frontier; the frontier explorer lists the nondominated sums of declared requirements at the shipped quantisation, never a ranking"; the risk line (:120-124) by the declared-risk modes, their claim, and that E-13 has not tested them; to the reached/ceiling paragraph (:190-200) add that XI Lab's CEILING brackets the largest sum and Transfer Lab's numbers are unchanged; the scope list (:393-397) drops the three items. Add: the experimental opt-in is needed for any frontier with the shipped requirements; the risk overflow refusal; WORST_WORLD grows with B |
| `README.md`, `ARCHITECTURE.md` | the four modules, the router and the two web files in the module tables; the XI Lab section names the three additions and the opt-in |
| `DECISIONS.md` | ADR-0030 "XI exact additions: ranges, minimal conflict, frontier, declared-risk modes": Problem (the four limitations), Decision (sections 1.2, 3.3, 4.2, 5.1 of this file), Evidence (the oracle and parity tests, filled in by the builders), Numerical boundary (the three policies, the allowance, the overflow guard), Alternatives rejected (calling `maximize_requirement` per requirement; QuickXplain; a weighted sum for the frontier; a probability for a tail; a default dimension; editing `kernel.py`; the literal O8 BIG, which a sum of `k` encodings can carry past), Relation to ADR-0020 (its rejection of a weighted sum of the two stages as a search device stands for the kernel; O8 overrides it for the risk modes only, because BIG is exact by construction, never serialised, and tested for both the carry and the leak), Relation to ADR-0024 (the router's snapshot loader is behind the build gate; `xi.risk.tail` is or is not a long route, per the root's answer), the run times of item 15, Confidence, Reversal (E-13's verdict relabels the risk modes) |
| `ROOT-DECISIONS.md` | rulings requested: 2.4, "two policies" becomes the three of 1.2, each named, and (item 13) whether the hard-constraint sentence admits a conflict explained in the half-even arithmetic of the shipped Satisfy solve it explains (until then CONFLICT explains conservatively); O8: BIG as in 5.1; 2.3 and R13 (item 14): the page-parts ruling of 8.1, or the fallback page of 8.4; 2.6 opening paragraph: an OR-XI draft now exists |
| `docs/research/north-star/README.md` | a row for this file: draft, reviewed once by three lenses, not audited |
| `galactico/optimization/xi/__init__.py` | no change: the router imports the four modules by path |
| `pyproject.toml`, `playwright.config.js`, `.github/` | no change: `e2e/` is discovered as it is |

## 13. Reconciliation

**With the E-13 draft** (`protocol-drafts/E-13-declared-risk-selection/PIPELINE.md`,
ASSUMED INTERFACES 1 to 3). Interface 1 assumes one function returning `solution_status`
(`"OPTIMAL"`), `assignments` and per-world pairs. This file provides
`declared_risk_selection(..., rule, tail_count)` returning `status` (`"CERTIFIED"`), `lineup`
and `world_losses`; E-13's two adapters `_risk_call` and `_risk_world_pairs` map them, which
its table allows. Interface 2 (BIG above the largest sum of `T` over the used worlds, `_q`
coefficients, the discard rule, `k` not recomputed) is met, with BIG also above twice the
largest total for the regret. One difference to resolve before E-13 is frozen: the draft's
protocol discards a world "in which any candidate has zero exposure", the product discards one
in which a non-excluded player lacks a needed metric at a slot he is eligible for (ROOT 2.4,
"exactly as the shipped bootstrap does"). The two differ for a candidate with no exposure in
a world who is eligible at no slot a requirement in force applies to: the requirements apply to
outfield slots only, so a goalkeeper with no minutes in a world discards it under the draft's
rule and not under the shipped one. The reconciler checks by structure whether that case occurs
in the Madrid worlds, and E-13 adopts the shipped rule or records the difference. Interface 3
(file name, menu) is met, with two reconciliation items for the E-13 draft's owner: its
`risk_solver_oracle_tests` (and so the `lf_sha256` list of PIPELINE.md:580, "which oracle
vouched for the solver") must hold `tests/xi_exact_oracle.py` beside
`tests/test_xi_risk_oracle.py`, because the brute-force logic lives in the first and could
change without moving the second's hash; and the product's menu is the draft's
`tail_counts` exactly (config.json:13-16): `WORST_WORLD` at 1 and `TAIL` at 2, 3, 6 and 4, 10,
20, so `risk_rule:WORST_WORLD` and `risk_rule:TAIL` never name the same computation. The
split-sample tool of row 7 is not in this file (OPEN QUESTION 2).

**With `planning.attained`.** Transfer Lab's reached and ceiling numbers come from the shipped
maximiser with minima set to zero (planning.py:1119-1208) and are pinned by
`test_planning_api.py` and `test_transfer_api.py`. They are not rewired to CEILING: that would
move served text (R13). A slow test asserts that on the planning problem `attained` solves,
with non-negative rates, CEILING's LARGEST end has the integer value, the integer bound and the
certification of the `maximize_requirement` call `attained` makes, and that each witness's
exact raw sum lies in the other's bracket, so the two cannot drift silently. The witnesses
themselves are not compared: two exact solvers with different models (the kernel's symmetry
breaking, different limits) can return different XIs with one integer value (4.1).

**With KNOWN_LIMITATIONS and the frozen solver's diagnostic.** `solve_xi` keeps saying
"Diagnostic reasons; not a minimal conflicting set" in its provenance; that remains true of
`solve_xi`. CONFLICT is the separate, certified answer, and the page prints it beside the
shipped diagnostic, never in its place.

## DISSENT

1. **ROOT 2.4, "two policies".** The shipped code has three named integer rules, not two:
   `_q` (float division, then half-even), the conservative floor/ceil, and the exact half-even
   objective of the hard-floor query (tradeoffs.py:37, 307). The last two are both "exact
   Fraction"; the first and last are both "half-even" and disagree on about one coefficient in a
   thousand. The design satisfies the ruling's intent (reuse, name each, invent none) by naming
   all three in 1.2 and assigning each quantity to one; the wording should be amended (section
   12) so that a later builder does not merge `_q` and the objective rule.
2. **ROOT 2.4, "hard constraints use the conservative policy", against the shipped Satisfy
   rule.** XI Lab's Satisfy solve, pinned by R13, enforces its minima in `_q` half-even integers
   (solver.py:274-275), not conservatively. A minimal conflicting set computed in the
   conservative arithmetic can be a set the half-even solve does not find infeasible, and the
   reverse holds for minimality. Following the principle the root accepted for the role brief
   (ROOT 2.6 D2: the arithmetic of the solve it explains), `explain_solve` would use `_q` and
   say so; every hard floor a reader declares to a new tool is conservative, as 2.4 says. The
   two variants are separate functions with separate names so neither can be mistaken for the
   other. Because the root's preamble requires a design that satisfies a ruling even under
   dissent, the half-even variant is gated (section 11, item 13): until the root amends 2.4,
   only `explain_floors` is built, and the page explains a Satisfy solve conservatively, which
   is sound (1.2: the conservative model of an INFEASIBLE Satisfy solve is INFEASIBLE too) and
   says that the set is certified in the stricter comparison only.
3. **ROOT 2.5 O8, the size of BIG.** "Strictly larger than the largest possible total"
   preserves the lexicographic order for one world but not for a sum of `k > 1` encodings
   (summed totals can carry into the `M` digit) nor for a regret (the `T` difference ranges over
   twice the total). E-13's DISSENT 3 says the same about TAIL. The design takes `BIG = 2 · |U| ·
   T_bound + 1`, which meets O8's literal requirement and both sharpenings; with the literal
   minimum, TAIL and REGRET would be different rules from the ones described to the reader, and a
   test shows an instance where they are. The price is the overflow refusal of 5.1 for very
   large declared minima.
4. **R13 against ROOT 2.3, where the page parts live.** 2.3 asks for XI Lab additions; R13 asks
   for new pages and leaves shared files to the root. A separate page would have to repeat the
   scenario, template, lock and minimum controls and would explain a solve the reader cannot see.
   The design keeps every new line in new files and asks the root for five additive edits to
   `xi.html` (section 12) that change no shipped element but do change the page's bytes and its
   script graph. The build depends on that ruling (section 11, item 14). If the root reads R13
   as forbidding even those, the fallback is the page `/xi/extensions` of 8.4, fully specified,
   with its own controls; the four panels and the API are unchanged by that choice.
5. **ADR-0001 / ADR-0019 opt-in on the new XI parts, against XI Lab's own default.** XI Lab's
   main solve has the two side requirements in force without an opt-in (legacy, kept by
   ADR-0019). The new parts follow ADR-0001 and O7 instead: progression alone unless the reader
   opts in. Two consequences the root should accept or overrule explicitly: with the shipped
   requirement set a frontier needs the opt-in every time (only one requirement is not
   experimental), and the minimal-conflict display of the main solve must ask the reader to opt
   in before it can explain that solve. The alternative, new parts that mirror the main solve's
   three requirements by default, would render `EXPERIMENTAL` numbers on a new surface without an
   opt-in.
6. **Deviation reported, not a dissent: CEILING does not call the shipped maximiser.** 2.1 says
   "generalise the existing hard-floor maximiser". Calling it per requirement and direction would
   make every active minimum a floor (it has no other mode), would lack the minimiser, would run
   without a deterministic limit, and would bring warnings that fail the copy guard into the
   reply. CEILING reproduces its objective and floor arithmetic exactly and a parity test ties
   the two.

## OPEN QUESTIONS

1. Whether the new XI parts default to progression alone (this file) or mirror the main solve's
   three requirements (DISSENT 5).
2. The HONEST EVALUATION split-sample tool (`xi.split-sample` budget; E-13 draft, interface 7,
   "owner OR-XI") is not specified here. Its definition is E-13's `product_split_rule`, and the
   route stays withheld until E-13's `split_sample_diagnostic` is executed; a separate spec should
   follow E-13's freezing, not precede it.
3. The tail menu is the E-13 draft's (`ceil` of a tenth, a quarter and a half of `B`, plus 1).
   The root confirms it or replaces it before E-13 is frozen; whether 200 precomputed worlds are
   ever offered is E-13's open question 3.
4. Settled, no longer open: the 12 worlds are the first 12 of the 40 (1.4, prefix property),
   because `Generator.multinomial(..., size=B)` draws rows in sequence; checked under numpy
   2.5.3 and pinned by a structure test. While it holds, the 40-world certificate prints
   `RISK_PREFIX`; `RISK_GROWTH` stays the general statement and no comparison of the two menus'
   values is printed.
5. Run time of the TAIL and REGRET selection and membership solves at `q = 100000` with 40
   worlds is unmeasured, and is now a gate (section 11, item 15). If the deterministic limit of
   40 is often reached, the honest answers are `LIMIT_REACHED`, a larger budget, or precomputed
   results; never a coarser quantisation (ROOT 3b).
6. The new modules use private members of `kernel.py`, as `brief.py` does. Exporting public
   names would edit `kernel.py` and move a hash served in every Squad and Transfer certificate;
   the root decides whether that is worth an ADR.
7. Whether the conflict tool should also be offered for an infeasible hard-floor query in the
   shipped tradeoff panel. The API supports it (`explains: "floors"`); the page part is not
   specified, because it would sit inside a shipped panel.

## Review record

Three adversarial reviews of the first draft (exactness, constitution, product), 14 October
2026. Each finding was checked against this file and the tree at `25128e8` before its
disposition. 73 findings: 12 blockers, 30 majors, 31 minors. All 73 hold and are applied; none
is rejected. Two are applied with a correction to the reviewer's proposal (C18, E10), noted in
their lines. Three need a root ruling and are applied as gates with a compliant fallback built
first (section 11, items 13 to 15): E10, E25 and P11. Code checks made for this record: the
conflict and frontier counterexamples by hand from the definitions; `historical.SEED =
20260906` and `match_id = 2565907` against BIG at defaults; `kernel.value` returns
`UNFIELDABLE` on a proved-empty model (kernel.py:739-743); `xi.html`'s `#apply-minima` sends all
three minima and `repairs.spec.js` fails on any console error; `scan_labels` refuses the old
section 4 and 5 prose ("best", "probability") and the draft `RISK_DISCARDED` ("because", fixed);
`Shell.ledger`'s fixed ids (labs-shared.js:185-198); the render harness's throwing `document`
(test_shell_render.py:44); `planning._corpus_files` returns `(present, absent)`; the
multinomial prefix property under numpy 2.5.3; E-13 `config.json` `tail_counts` and
`PIPELINE.md:580`; `LONG_ROUTES` pinned at `tests/test_lab_runtime.py:123`.

### Exactness lens

| # | Severity | Finding | Disposition |
|---|---|---|---|
| E1 | blocker | Conflict copy claims more than the deletion filter certifies; witness called an XI though it can leave slots empty and field an excluded player | applied: 1.1 "assignment", 3 design claim, 3.3 proof table with counterexample, restore test per member, `CONFLICT_CLAIM`, `CONFLICT_MEMBER_WITNESS`, `CONFLICT_RESTORES_*`, tests |
| E2 | blocker | Frontier certified on integer vectors but prints raw witness sums; completeness sentence false on printed numbers | applied: 4.1 counterexample, `point_texts` = `V/q` exact, raw sums secondary, reworded `FRONTIER_CLAIM`/`_COMPLETE`, render test |
| E3 | blocker | `explains: "solve"` accepted without the opt-in explains a model with inactive side requirements | applied: refused with `CONFLICT_SOLVE_NEEDS_OPT_IN` (1.3, 7.2) once routed; parity test of in-force sets |
| E4 | blocker | RISK ledger row serves the "largest regret pair", a difference O8 forbids | applied: 7.6 row prints binding worlds with both pairs; API test |
| E5 | major | Leak test "no integer ≥ BIG anywhere" cannot pass (seeds, match id, quantisation) | applied: test recomputes BIG, Φ*, ρ*, E^w with M ≥ 1 and checks them, with an allow-list |
| E6 | major | INFEASIBLE selection unmapped; world-least UNFIELDABLE reported as UNKNOWN | applied: 5.3, 5.6 step 6, UNFIELDABLE EXACT; two-locked-goalkeeper tests |
| E7 | major | After "Apply minima" the panels send side minima without the opt-in and get 422 | applied: 8.2 request-body rule, minima filtered by the server's `experimental` flag, `SIDE_MINIMA_SET_ASIDE`; e2e |
| E8 | major | Cache key includes defaults while declared rows use `model_fields_set` | applied: declared rows a function of the resolved request (7.6, 7.3); API test |
| E9 | major | `RISK_SAME_WORLDS` not supported by a fingerprint match; check tautological | applied: sentence withdrawn; `RISK_SAME_DRAW`/`RISK_PREFIX` state construction only; slow discard-parity test with opt-in and main exclusions |
| E10 | major | `explain_solve` uses half-even, breaching ROOT 2.4 while the page depends on it | applied with correction (the fallback sentence says the set may hold together under half-even, not only "may not be minimal"): half-even variant gated (item 13), page explains with `explain_floors`, `CONFLICT_CONSERVATIVE_FOR_SOLVE`. **Root ruling** |
| E11 | major | Frontier selects need requirement labels with no server source | applied: `GET /api/xi/extensions` `requirements` list, tested equal to `decision_inputs` |
| E12 | major | Oracle has no discard rule or world vector; builder A writes oracle and the code it checks | applied: `used_worlds`, `world_vector`; oracle parts reassigned (section 0, 6) |
| E13 | minor | "A page that has solved the main XI has already built it" is false; LRU not keyed on corpus | applied: sentence deleted, gated loader, cold-build cost stated, LRU staleness to KNOWN_LIMITATIONS |
| E14 | minor | `objective_vector · q` compared as integers fails in floating point | applied: `round(v * q)` (5.4, 9) |
| E15 | minor | Completeness undefined for proved terminal outcomes; `NOT_RUN` outside the vocabulary | applied: 1.5 row, EXACT/COMPLETE for proved outcomes, membership EXACT when vacuous |
| E16 | minor | `TAIL_MENU` holds k = 1, duplicating WORST_WORLD | applied: menu without 1; `rule` field; subject fixed by rule |
| E17 | minor | `tail_sum` reuses `LossPair` for sums of maxima | applied: `TailSums` dataclass and texts |
| E18 | minor | Legacy evidence string served on a new surface | applied: field removed; router serves the composed domain class |
| E19 | minor | "No tool reads a file" is false (source fingerprints) | applied: section 0 reworded |
| E20 | minor | `Shell.infeasible` loses the conservative caveat for NOT_SATISFIABLE | applied: `FLOORS_CONSERVATIVE` passed as the first reason |
| E21 | minor | `planning.attained` parity compares witnesses' raw sums | applied: integer value, bound, certification, and bracket containment (2.4, 13) |
| E22 | minor | Too-small BIG detection relies on seeds containing a carry case | applied: two planted deterministic instances (TAIL k = 2, REGRET) |
| E23 | minor | Slow CONFLICT oracle enumeration may not finish | applied: backtracking with lock and floor-bound pruning, node counts recorded, a run-time guard (not an expected count, 1.6) |
| E24 | minor | OPEN QUESTION 4 is answerable from the code | applied: prefix property verified (numpy 2.5.3), structure test, `RISK_PREFIX` |
| E25 | minor | `xi.html` edits depend on a root ruling under R13 | applied: checklist item 14, fallback page fully specified (8.4). **Root ruling** |
| E26 | minor | Deterministic-limit stops reported as DEADLINE | applied: times recorded, `LIMIT_REACHED` vs `DEADLINE`, `stopped_by` (1.5) |

### Constitution lens

| # | Severity | Finding | Disposition |
|---|---|---|---|
| C1 | blocker | Conflict sentences state a model-level fact the filter does not prove | applied: as E1 |
| C2 | blocker | Frontier claim not scoped to the shipped quantisation; printed sums are raw | applied: as E2 |
| C3 | blocker | REGRET ledger row serves a difference | applied: as E4 |
| C4 | blocker | Ceilings panel 422s after applied minima; shipped e2e console-error check would fail | applied: explicit button `#solve-ceilings`, no automatic POST, minima filter; e2e of shipped flows with panels mounted |
| C5 | major | `RISK_SAME_WORLDS` claims more than fingerprint equality | applied: as E9 |
| C6 | major | Tail and binding worlds belong to one witness; tests compare witnesses | applied: "for the XI shown", `RISK_WITNESS`, oracle `tail_of`/`binding_of` for the returned lineup, BIG-doubling compares invariants |
| C7 | major | No status for INFEASIBLE selection; UNFIELDABLE world-least reported undecided | applied: as E6 |
| C8 | major | Leak test cannot pass; caplog substring test | applied: as E5, whole-token matching |
| C9 | major | Section prose for claim fields holds banned tokens | applied: claim fields bound to 7.7 constants word for word; prose marked "never served"; `scan_labels(asdict(result))` per tool |
| C10 | major | Frontier values at four decimals cannot separate points | applied: as E2, render test of distinct texts |
| C11 | major | Snapshot via `decision_lab.snapshot` bypasses the ADR-0024 gate | applied: gated loader with `planning._built_once` (7.3); single-build test |
| C12 | major | Declared rows from `model_fields_set` vs cache key | applied: as E8 |
| C13 | major | Frontier and risk request contents undefined; no server list for options | applied: 8.2 common body; `GET` `requirements` |
| C14 | major | Panels without opt-in solve a different model, unstated | applied: `MODEL_DIFFERS` / `model_note`, `RISK_BALANCE`; API test |
| C15 | major | WORST_WORLD not labelled as the extreme of the tail family; k = 1 duplicate | applied: `RISK_WORST` reworded; k = 1 only as WORST_WORLD |
| C16 | major | Four `Shell.ledger` calls produce duplicate ids | applied: per-panel id rewrite that throws if the kit changes; optional root kit change (section 12); unique-id tests |
| C17 | minor | Float `objective_vector · q` comparison | applied: as E14 |
| C18 | minor | One WITHIN sentence serves two facts and two causes | applied with correction (a FEASIBLE_NOT_PROVEN end's incumbent decides True as a witness, so not "never True"): four sentences, `reason` fields |
| C19 | minor | `m_r` vs `φ_r` read unspecified | applied: 2.1, 2.3 step 1, test with `φ_r ≠ m_r` |
| C20 | minor | Risk refusal sentences defined in the API layer but raised in `risk.py` | applied: defined in the tool modules, re-exported (5.7, 7.7) |
| C21 | minor | NOT_EVALUABLE and DISCARDED wording wrong | applied: both reworded to the rule's exact condition |
| C22 | minor | `corpus_token` cannot raise; omitted form inconsistent | applied: `planning.corpus_token(planning.FLAGSHIP)`; full omitted records |
| C23 | minor | Membership grouping in JS, plot_y orientation, digit-run test | applied: `membership.groups` from the server, plot_y in SVG orientation, test accepts served integers |
| C24 | minor | Encoding vs ADR-0020's rejected weighted sum unrecorded | applied: 5.1 note; ADR-0030 request cites ADR-0020 |
| C25 | minor | No inputs for `world_seed`, `bootstrap_version`; WORST = TAIL(1) test ignores fingerprints | applied: required keyword arguments; comparison excludes rule, claim and fingerprints |
| C26 | minor | Exact non-selection replies never cached | applied: as E15 |

### Product lens

| # | Severity | Finding | Disposition |
|---|---|---|---|
| P1 | blocker | `RISK_SAME_WORLDS` often false; guard compares the snapshot with itself | applied: as E9; `RISK_DISCARDED` names its requirements |
| P2 | blocker | Panels 422 after applied minima; shipped e2e would fail | applied: as C4 and E7 |
| P3 | blocker | Conflict claim "dropping any one leaves an XI" not certified | applied: as E1 |
| P4 | blocker | REGRET ledger row is a difference | applied: as E4 |
| P5 | major | Cache key and declared rows disagree | applied: as E8 |
| P6 | major | Leak tests unrunnable; BIG-doubling fails on ties | applied: as E5 and C6 |
| P7 | major | CEILING/FRONTIER evidence ignores the measurement rule; legacy token served | applied: every quantity composes all requirements in force (7.6); as E18 |
| P8 | major | Nothing calls `mount` | applied: fifth `xi.html` edit; file loads without touching `document` |
| P9 | major | Page parts lack server text fields | applied: `requirements`, `label_text`, `membership.groups`, `boundary_ties_text`, `point_sum_texts`, `allowance_texts`, plot orientation and `viewBox` (7.5) |
| P10 | major | Duplicate ledger ids | applied: as C16 |
| P11 | major | TAIL enumerates candidates outside the long-route limit; snapshot builds not gated | applied: snapshot as C11; long route requested of the root, `B = 40` gated on timing (item 15). **Root ruling** |
| P12 | major | Risk functions cannot fill `world_seed`, `bootstrap_version` | applied: as C25 |
| P13 | major | E-13 pins the test file but not the oracle it imports | applied: reconciliation item for the E-13 draft's owner (section 13) |
| P14 | major | Test plan misses integration risks | applied: snapshot immutability, shipped flows without console errors, REGRET e2e, 429 and long-job tests, `xi.html` byte test, overflow on `#xi-extensions` |
| P15 | minor | `corpus_token` formula cannot raise | applied: as C22, tmp-corpus parity test |
| P16 | minor | `attained_text` floors a float | applied: router recomputes in `Fraction` (7.5) |
| P17 | minor | Compared minima absent from the input contract | applied: section 10 |
| P18 | minor | UNFIELDABLE / NOT_EVALUABLE replies never cached | applied: as E15 |
| P19 | minor | Digit-run render test contradicts 8.3 | applied: as C23 |
| P20 | minor | 422 bodies can echo ids; omitted shape inconsistent | applied: `UNKNOWN_PLAYER` checked in `declare`; one omitted shape |
| P21 | minor | Ceiling parity on empty instances; float invariant | applied: parity restricted to non-empty feasible sets; as E14 |
