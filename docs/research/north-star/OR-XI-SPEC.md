# OR-XI specification: ceilings, minimal conflict, frontier, declared-risk modes

Build contract for the four exact XI tools of ROOT-DECISIONS 2.1, the router that serves
them and the XI Lab page parts of 2.3. The binding rules are ROOT-DECISIONS sections 1
(R1-R13), 2.1, 2.3, 2.4, 2.5 (O7, O8, O12, O13, H10), 2.6, 2.7 (the rulings on this file,
X1 to X14), 3b and 4, ADR-0018 to ADR-0029 and KNOWN_LIMITATIONS. Where this file and those
rules or the shipped code disagree, the rules and the code win and the disagreement is a
defect to report (ROOT 2.6). Points where this file departed from the wording of a ruling,
why, and the root's ruling on each, are under DISSENT.

**Status.** Draft by the OR-XI designer, 14 October 2026, written after the council was cut
short. Revised the same day after three adversarial reviews (exactness, constitution,
product); every finding and its disposition is in the Review record at the end. Its DISSENT,
gates and open questions were ruled by the root the same day (ROOT-DECISIONS 2.7, X1 to X11),
and this file specifies the ruled state. Audited twice, each time in five scopes (the CEILING
model, CONFLICT, FRONTIER, RISK and its oracle, and the API, page and tests). The first audit
(14 October 2026): 14 blockers survived independent refuters and are applied, with the
refuters' corrections where they gave one; the 64 majors and minors were checked against the
code and each is applied, five with a correction (Review record, "Audit of 14 October 2026");
its three points for the root were ruled on 16 October (X12 to X14, below). The second audit
(16 October 2026) found 79: 11 blockers, all surviving independent refuters and all applied
with the refuters' corrections (three duplicate another blocker and are applied with it), and
22 majors and 46 minors, each checked against the code; every major is applied, and every minor
but one optional part of one, which is rejected (Review record, "Second audit, 16 October
2026"). Its blockers were of three kinds: a served sentence that stated more than its state
proved (the CEILING claim on every state but a fully bracketed one, the FRONTIER claim on every
cut list, the CONFLICT claim on a refused filter test, `CONFLICT_NO_MINIMUM`'s reason on an
explanation of floors, and the frontier ledger's "0 points" on an undecided list), a reply the
shipped code could not build (the pending E-13 form, `dataclasses.replace` against rule V3), and
test fixtures that could not hold (the 4.1 and 3.3 instances). The claims are now chosen by state
(CEILING) or worded to be true on every status (FRONTIER), a refused filter test keeps its member
(CONFLICT), and the frontier's limit check, the RISK overflow guard's place, the RISK claim's
suffix and E-13's scope are fixed. No point needs a root ruling; the E-13 draft's owner has
the open items of section 13 (the `risk_report` statistic, the requirement set of E-13's token
scope, and the interface details). Nothing built. Every claim about the shipped code below was
read from the tree at `25128e8`, and the claims either audit touched were checked again at
`fda88c2` and `1556fa2`; line numbers refer to `25128e8`, which differs from `1556fa2` in none
of the cited files except `KNOWN_LIMITATIONS.md`, whose lines are cited at `fda88c2`.

**Rulings in force (ROOT-DECISIONS 2.7).** Both conflict variants are built and routed:
`explain_solve` in the half-even arithmetic of XI Lab's Satisfy solve and `explain_floors` in the
conservative arithmetic of a hard-floor query (X2); the page explains the main solve with
`explain_solve`. The five additive edits to `web/xi.html` are granted on X4's condition (every
shipped XI test and browser spec passes unchanged, and the new panels send nothing until their
own button is pressed); the stand-alone page once specified in 8.4 is not built. X12: that
condition forbids a solve or any request that reads the corpus, and allows the one corpus-free
`GET /api/xi/extensions` on load. X13: edits (3) and (4) go just before the inline script.
X14: the tracked XI Lab screenshots are regenerated and inspected only where the corpus is
present, and a commit made without it restores them (`git restore docs/screenshots`) and never
commits a capture it could not look at (section 9, e2e; section 12). `xi.risk.tail` is in
`runtime.LONG_ROUTES` (X5). The risk menu offers 12 worlds until the 40-world solves are timed
on the corpus (X5; section 11, item 15).

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
`galactico/models/xt/grid.py` (ROOT 3b). Their bytes are hashed in several places, each file
in its own: `tradeoffs.py` and `domain.py` into every hard-floor input fingerprint
(`tradeoffs._source_fingerprints`, tradeoffs.py:69-75); `solver.py`, `tradeoffs.py` and
`domain.py`, with `kernel.py`, into the kernel's input contract (`_SOURCES`, kernel.py:79,
pinned by `tests/test_squad_kernel.py`); `historical.py` into E-08's published `results.json`;
and `historical.py` and `grid.py` into the results of the experiment runners that list them
(for example `experiments/run_partial_history.py:77-79`), as ROOT 3b says of published results.

**Not edited either, although not frozen:** `galactico/optimization/squad/kernel.py`. Its
source fingerprint is in the input contract of every Squad Lab and Transfer Lab certificate
(kernel.py:425-427); an edit would change those served hashes (R13). The new modules use its
private members, as `squad/brief.py` already does (brief.py:47-57, 299-414), and a test pins
the members they use (X9, section 9).

**Owned by the root, changed only by request (section 12):** `galactico/api/player_lab.py`
(router registration), `web/xi.html` (five additive edits, granted: X4),
`galactico/api/runtime.py` and `tests/test_lab_runtime.py` (one long route, granted: X5),
every top-level `*.md`, `galactico/optimization/xi/__init__.py` (no change requested),
`ROOT-DECISIONS.md`, `docs/research/north-star/README.md`. `web/labs-shared.js` is not changed:
the optional id prefix for `Shell.ledger` was declined as not needed (X11).

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
| `verdict_for`, `record`, `derive`, `PENDING`, `as_payload` | `domain/verdicts.py` | the E-13 payloads, and their pending form for a request outside E-13's scope (5.7) |
| `_outward`, `corpus_token`, `FLAGSHIP`, `_built_once`, `INTEGER_ONLY`, `_APPROXIMATE`, `_DERIVED_PLACES` | `api/planning.py` | outward printing at four decimals, the cheap corpus identity of a cache key, the ADR-0024 build gate, the integer-only `Literal` validator, and the printed form of a minimum read off the record (`planning._minimum_text`, planning.py:897-909). The API tests pin the call signatures of the private ones, as X9 pins the kernel's (section 9) |
| `window.Shell` | `web/labs-shared.js` | badges, ledger, error, infeasible and not-certified markup |

**Engineering (ROOT section 4).** `from __future__ import annotations`; frozen dataclasses;
full type hints; `__all__`; ruff clean at line length 100 (E, F, I, UP, B, SIM); a module
docstring whose first paragraph states the claim and the non-claim. No tool imports
`solve_xi`, `maximize_requirement`, `bootstrap_selection`, `removal_sensitivity` or
`candidate_injection`: the kernel does what they would do in a loop (ROOT 2.6 D5, D6). No tool
reads a data file or an environment variable, or a clock other than `time.monotonic`; the only
files a tool reads are its own source and the kernel's sources, to fingerprint them
(`kernel.source_fingerprints`, kernel.py:225-238), and the installed OR-Tools distribution's
metadata, which `kernel.input_contract` reads for its version (`importlib.metadata.version`,
kernel.py:428). Tests skip cleanly without the corpus.

## 1. The declared model, the three shipped integer policies, worlds and time

### 1.1 Notation

A request declares: a formation with slots `S` in formation order, each with allowed
positions; a candidate set `C` (the gated players of the snapshot, sorted by `player_id`),
each with a position, minutes, an optional `eligible_slots` tuple and a value table
`v_p[metric]` (a finite float or `None`); locks `L ⊆ C`; exclusions `X ⊆ C`; the requirements
in force `R` (section 1.3), each with a metric `μ_r`, a minimum `m_r`, a normaliser `n_r > 0`
and an applicability set `A_r` (empty means every slot); optionally hard floors `φ_r` for some
`r ∈ R`; the quantisation `q` (always `QUANTIZATION = 100000` from the API); and, for the risk
modes, a world count `B`.

| Symbol | Exact definition |
|---|---|
| `Eligible(p, s)` | `solver._eligible`: `minutes_p > 0`, position in the slot's allowed positions, and `eligible_slots` is `None` or holds `s` |
| `applies(r, s)` | `solver._applies`: `A_r` empty or `s ∈ A_r` |
| admissible key `(p, s)` under a value table `V` | `Eligible(p, s)` and no `r ∈ R` with `applies(r, s)` has `V_p.get(μ_r) is None` (a metric absent from the table counts as `None`). A missing measurement forbids the assignment; nothing is imputed (solver.py:202-215, kernel.py:506-508). Exclusions are not part of this definition; every tool but CONFLICT (3.1) builds its keys through `kernel._background`, which also leaves out every `p ∈ X` (kernel.py:502) |
| XI, `x` | a map `S → C` whose every pair is an admissible key, injective, with `L ⊆ x(S)` and `x(S) ∩ X = ∅` |
| assignment | a partial injective map from `S` to `C` whose every pair is an admissible key: slots may be empty and nothing is said about `L` or `X`. An XI is an assignment that fills every slot, holds every locked player and no excluded one. CONFLICT tests sets of declarations by assignments (section 3); every other tool speaks of XIs only |
| `𝒳(D)` | the set of XIs under the declarations `D` |
| `a_r` | the number of slots `s ∈ S` with `applies(r, s)` |
| `S_r(x)` | `Σ_{s : applies(r, s)} Fraction(v_{x(s)}[μ_r])`, exact |

### 1.2 Three shipped integer policies, and which quantity uses which

ROOT 2.4 says new solvers reuse the shipped policies, name which applies to which quantity,
and invent no third. The shipped code has three named rules, not two (DISSENT 1), and X1
(ROOT-DECISIONS 2.7) amends 2.4 to these three, each named; a new tool never mixes two inside
one quantity. None is new.

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
| every hard floor the reader declares | CEILING, FRONTIER, CONFLICT (`explain_floors`) | `HARD_POLICY` | ROOT 2.4 and X2: hard floors a reader declares are conservative; a returned XI meets the raw floor exactly |
| the minima of a Satisfy solve, in that solve's own arithmetic | CONFLICT (`explain_solve`, X2) | `SHORTFALL_POLICY` | the arithmetic of the solve it explains: `solve_xi` enforces Satisfy minima as `Σ _q(...) ≥ _q(m)` (solver.py:274-275), not conservatively (the principle of ROOT 2.6 D2, applied to CONFLICT by X2) |
| per-world shortfalls `d_r^w`, `M^w`, `T^w` | RISK | `SHORTFALL_POLICY` | ROOT 2.6 D8 and the single-world invariant: with one world a risk mode returns BALANCE's pair, and BALANCE rounds with `_q`. Shortfalls are an objective, not a hard constraint |

Half-even infeasibility implies conservative infeasibility, not the converse: a conservative
coefficient `floor(v / n · q)` (exact) is never above `_q(v, n, q)` and a conservative target
`ceil(m / n · q)` is never below `_q(m, n, q)`, because for every coefficient and target within
`MAX_MAGNITUDE = 10**12` the float error of `_q` is below `10**-3` (two roundings of relative
size `2**-53` each). The bound is enforced, not assumed: `kernel._tables` raises `ValueError` on
a coefficient or a target above `MAX_MAGNITUDE` under either policy (kernel.py:602-612), every
new tool builds its tables through it or with the same check (3.4), and `solve_xi` itself
checks coefficients only (solver.py:267). So an XI meeting a set of minima conservatively meets it half-even, and a Satisfy solve
that is INFEASIBLE is INFEASIBLE in the conservative model too. The converse fails: a set
`explain_floors` certifies in the conservative model may hold together under the solve's
half-even comparison. That is why the page explains XI Lab's solve with `explain_solve`, in
the solve's own arithmetic (X2), and `explain_floors` answers hard-floor queries. Each
response names its arithmetic.

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
main solve had the side requirements in force, which is always (DISSENT 5, OPEN QUESTION 1;
ruled by X6). The router enforces the second: `explains: "solve"` is refused without the
opt-in with its own sentence (`CONFLICT_SOLVE_NEEDS_OPT_IN`), because without it the tool would
explain a model in which the side requirements are inactive, which is not the solve the reader
saw. A test asserts that `explain_solve`'s `requirements_in_force` (3.4) equal `solve_xi`'s
active set on the same declarations.

Without the opt-in, the ceilings and risk panels answer on a model that holds progression
alone while the main solve above them holds three requirements. Each such reply carries the
sentence `MODEL_DIFFERS` (7.7), naming both sets, whenever they differ. The page never sends
a side minimum without the opt-in; it filters the main solve's minima by the server's list of
requirements (8.2), and says that the side minima are not part of the question.

### 1.4 Worlds

Used by the risk modes only.

| Item | Exact definition |
|---|---|
| source | the router's gated loader `_match_snapshot(scenario_id, B)` (7.3) with `B ∈ runtime.WORLD_MENU = (12, 40)`: `historical.load_snapshot(match_id, worlds=B, seed=historical.SEED)`, the call `decision_lab.snapshot` makes, behind the ADR-0024 build gate. It is not the object `/api/xi/solve` holds; it is built by the same function from the same files and seed. The risk routes accept `B = 12` only until the 40-world solves are timed on the corpus (X5, 7.1). 200 worlds are not offered (`PRECOMPUTED_WORLDS` is a result-store tier, not a computation) |
| world ids | `0 .. B − 1`, the keys of `snap.worlds`, kept as integers |
| world vector | whole-vector replacement, never a merge (solver.py:550): `V^w_p = dict(worlds[w].get(p, {}))` for **every** candidate. `kernel._background` keeps a player's own vector when he is absent from `values` (kernel.py:468-482), so `risk.py` always passes a complete mapping, in which absence means every metric `None`, as `bootstrap_selection` reads it |
| discard rule | world `w` is discarded iff some `p ∉ X`, some slot `s` with `Eligible(p, s)` and some `r ∈ R` with `applies(r, s)` have `V^w_p[μ_r] is None` (solver.py:549-564). Locks and the point-estimate measurement rule play no part. Recorded as `{"world_id": w, "reason": "missing shared-world exposure"}`, the shipped string |
| used worlds `U` | the others, ascending. `k` and `B` are never recomputed on `|U|` |
| lemma | for every `w ∈ U` the keys `(p, s)` with `p ∉ X` that are admissible under `V^w` are exactly those with `Eligible(p, s)` (the discard rule leaves no such key unmeasured), so `β_w.variables`, and hence `𝒳`, are the same in every used world. `risk.py` checks it (5.6 step 2; a `RuntimeError` if not) |
| world fingerprint | `solver._fingerprint(snap.worlds)` over all `B` worlds, discarded ones included: the function and input of `bootstrap_world_fingerprint` (solver.py:609). For `B = 12`, when both snapshots are built from the same files, it equals the fingerprint the main solve on the same scenario carries: a fact of construction, tested on the corpus (slow test), never checked per request. Equal fingerprints say the worlds were drawn alike; they do not say which worlds the main solve's selection frequencies use: those are only the worlds it certified under its own decision rule and requirements (`bootstrap_used_worlds`, solver.py:566-568) |
| prefix property | `shared_match_weights` draws all replicates from one generator with `multinomial(..., size=B)` (profiles/uncertainty.py:139-141), which draws rows in sequence: the first 12 of the 40 worlds are the 12 worlds, row for row (checked under numpy 2.5.3 and under 2.5.4, the version in the project's `.venv`). The world vectors are then computed from those weights by float matrix products (historical.py:203-212), whose rows could in principle depend on the row count under another BLAS, so equal weights are not enough: a structure test checks the property itself under the installed numpy, on the weights and on the world vectors built from them by the same expression on synthetic frames (`solver._fingerprint` of worlds 0 to 11 of the 40 equals that of the 12), and records `numpy.__version__` as information only; no test asserts a version string. While that test passes, the 40-world certificate may say that the main solve's 12 worlds are its worlds 0 to 11 (`RISK_PREFIX`, 7.7) |
| seeds | the world seed is `snap.provenance["seed"]` (`historical.SEED`); the solver seed is `historical.SEED` too, as `decision_lab` passes it. The router passes the world seed and `snap.provenance["bootstrap_version"]` to every risk function as the keyword arguments `world_seed` and `bootstrap_version` (5.7) |

### 1.5 Deadlines, deterministic time, statuses, completeness

Every tool takes `deadline: float`, a `time.monotonic()` value, as the kernel does. The router
passes `time.monotonic() + budget.remaining()`. Every CP-SAT call is made through
`kernel._Run(deadline, seed)` (one worker, the seed, `max_deterministic_time =
PER_SOLVE_DETERMINISTIC_LIMIT = 10.0`, `max_time_in_seconds = max(0.001, deadline − now)`),
except the two risk solve kinds of section 5.6, which use `risk._solver` with the same worker,
seed and wall-clock settings and the deterministic limit `SELECTION_DETERMINISTIC_LIMIT = 40.0`.
Every RISK certificate carries both limits; every other certificate carries its one limit.
`_Run.solve` returns `("UNKNOWN", None)` without a call when the deadline has passed, including
when it passes between a tool's own deadline check and the call; every tool records that call
as `NOT_RUN`, never as `UNKNOWN`.

| Rule | Text |
|---|---|
| statuses | `OPTIMAL`, `FEASIBLE`, `INFEASIBLE`, `UNKNOWN`, `MODEL_INVALID`, `NOT_RUN`, one per call, in call order |
| undecided | `UNKNOWN` and `NOT_RUN` are never evidence of absence: no tool turns them into "no XI", "no further point", "not needed" or a value |
| incumbents | a `FEASIBLE` incumbent of an optimisation is not an optimum. FRONTIER and RISK never report one. CEILING reports it as `FEASIBLE_NOT_PROVEN` with the solver's bound, which still brackets every sum (section 2.4), as the shipped maximiser does (tradeoffs.py:417-421) |
| integers from the solver | CP-SAT's float `objective_value` and `best_objective_bound` are not exact integers: with ortools 9.15.6755 an `OPTIMAL` integer objective can be reported one or two ulp off (`1524.9999999999995` for 1525, `-14.000000000000002` for −14). Every integer a tool reports, compares or reuses (an objective value, a lexicographic stage value `v_i`, `Φ*`, `ρ*`) is `solver.value` of the expression the solve optimised, an exact Python int, or is recomputed in Python from the witness. `objective_value` is never compared, stored as an integer or served; `best_objective_bound` is used only rounded outward as in 2.3 step 7 |
| completeness | `EXACT` (every statement proved), `COMPLETE` (an enumeration proved complete), `LIMIT_REACHED`, `DEADLINE`, `MODEL_INVALID`; no other token, in any block, except `NOT_REQUESTED` on a RISK membership block computed with `analyze_ties=False`, which the router never sends (5.7). `runtime.is_complete` caches a reply only when every `completeness` value in it is `EXACT` or `COMPLETE` |
| proved terminal outcomes | an outcome proved without a solve or by an INFEASIBLE proof is complete: `UNFIELDABLE` and `NOT_SATISFIABLE` (CEILING, FRONTIER, RISK), `NOT_EVALUABLE` (RISK) and `MODEL_FEASIBLE` (CONFLICT) carry `EXACT` (the frontier's empty set `COMPLETE`); a membership block that is vacuous because no selection exists is `EXACT` with no rows. Each is cached like any exact reply, and a test calls `is_complete` on each. `FLOORS_UNMET` (CEILING, FRONTIER: no XI meets the declared floors, proved; whether an XI exists without them, not decided) is not one of them: its completeness is that of the undecided solve, so it is not stored |
| a proof supersedes earlier calls | a proof that the feasible set is empty supersedes every call made before it that was undecided or refused: those calls asked about a set now proved empty, and the reply states nothing that rests on them. `UNFIELDABLE` and `NOT_SATISFIABLE` are then `EXACT` (`COMPLETE` for FRONTIER) with `stopped_by` `None`, and `FLOORS_UNMET` takes its completeness and `stopped_by` from its cause solve alone. The earlier statuses stay in `statuses`. It arises in CEILING (an end undecided, a later end `INFEASIBLE`, 2.3 step 6) and in REGRET (a world's least `UNKNOWN` or `MODEL_INVALID`, another's `UNFIELDABLE`, 5.3); in FRONTIER, CONFLICT and TAIL no undecided or refused call can precede such a proof |
| which limit stopped a call | for every CP-SAT call a tool makes itself, the solver's `deterministic_time` and `wall_time` (from the response) are recorded in the tool's provenance under two keys: `<tool>_solve_deterministic_times`, a list in call order of `{"status", "deterministic_time"}`, which is reproducible, and `<tool>_solve_wall_times`, a list in call order of `wall_time` floats, which depends on load and is diagnostic only; `<tool>` is `ceiling`, `conflict`, `frontier` or `risk`. A `NOT_RUN` call has no entry in either list. Neither list is a certificate field, and neither enters `input_contract` or `input_fingerprint`; times are not encodings. An undecided call (`UNKNOWN`, or `FEASIBLE` where an optimum was asked) is `LIMIT_REACHED` with `DETERMINISTIC_LIMIT` when its `deterministic_time` is at least its limit and `time.monotonic() < deadline` right after it returns; that stop is load-independent. Every other undecided call is `DEADLINE` with `WALL_CLOCK`: one the wall clock stopped, a call not made (`NOT_RUN`), a call inside `kernel.value` (which exposes no solver), and an `UNKNOWN` that reached neither limit |
| one certificate, one token | a certificate has one `completeness` and one `stopped_by`, read over the calls no proof has superseded (the row "a proof supersedes earlier calls"). Completeness: `MODEL_INVALID` if any call was `MODEL_INVALID`; otherwise `DEADLINE` if any undecided call is `DEADLINE`; otherwise `LIMIT_REACHED` if any undecided call is `LIMIT_REACHED` or, for FRONTIER, the point limit stopped the list; otherwise `EXACT` (`COMPLETE` for an enumeration). `stopped_by` is read from the undecided calls alone: `WALL_CLOCK` if any is `DEADLINE`, else `DETERMINISTIC_LIMIT` if any is `LIMIT_REACHED`, else `POINT_LIMIT` for a FRONTIER list cut at its limit, else `None`. A load-dependent stop therefore always wins, and a reply is never called load-independent while one of its calls was not |
| wall clock | the wall-clock budget can stop a solve before its deterministic limit. Such a status is load-dependent; it is reported as `DEADLINE`. Neither `DEADLINE` nor `LIMIT_REACHED` is cached, so a load-dependent answer is never stored |
| solver faults | an exception raised by CP-SAT (`MemoryError` from `std::bad_alloc`, or any other) is not a status: it is an internal fault and the API answers 500 (7.8). The risk models are written so that none is expected (5.1, split encoding); a test runs every seeded oracle instance's risk solves in a subprocess capped in memory and time, so a regression fails the test instead of exhausting the machine (section 9) |

### 1.6 Prior exposure (ROOT 2.5, 4.4)

Two exact computations on the default Madrid model were seen before this design: the
three-dimensional frontier has 12 nondominated points over 480 feasible player sets, and the
removal table. They are disclosed here. No constant, grid, limit, floor, tolerance or test
expectation in this file is derived from them: `MAX_FRONTIER_POINTS = 64` mirrors
`brief.MAX_BRIEF_ROWS`, the tail menu is the E-13 draft's, and the slow tests compare with a
brute-force enumeration on the real snapshot rather than pinning a count.

## 2. CEILING: `galactico/optimization/xi/ceilings.py`

Design claim (a note for the builder, never served; the served `claim` is the 7.7 constant the
reply's state selects (2.2, "Claim by state") and the served `non_claim` is
`CEILING_NON_CLAIM`, each defined in `ceilings.py`, restated by the router (7.7) and served word
for word; the same rule holds for every tool): for each requirement in force, the least and
the largest sum any XI reaches under the eligibility rules, the measurement rule, locks,
exclusions and declared hard floors (compared conservatively, 2.1), each bracketed exactly
where the search settles it: one end is the sum of one XI, the other a proved bound no XI
passes. When the end is `QUANTIZED_OPTIMAL`, that XI has the extreme rounded sum `I±_r`; it need
not have the extreme sum `R±_r` (2.1), and another XI can sum to more (or less). Each range is
over the XIs of `𝒳_F` (with floors, the conservative inner set, 2.1) for one requirement alone;
a sum is arithmetic on prior rates, not a forecast, and neither end is a target.

### 2.1 Definition

`𝒳_F = { x ∈ 𝒳(D) : Σ_{s : applies(r, s)} floor_H(v_{x(s)}[μ_r]) ≥ ceil_H(φ_r) for every floored r }`
(HARD_POLICY). For each `r ∈ R`, with `O_r(x) = Σ_{s : applies(r, s)} round(Fraction(v_{x(s)}[μ_r]) / Fraction(n_r) · q)`
(OBJECTIVE_POLICY) and `e_r = a_r · n_r / (2q)`:

| Quantity | Definition |
|---|---|
| `I⁺_r`, `x⁺_r` | `max_{x ∈ 𝒳_F} O_r(x)` and one XI attaining it |
| `I⁻_r`, `x⁻_r` | `min_{x ∈ 𝒳_F} O_r(x)` and one XI attaining it |
| largest raw sum `R⁺_r = max_{x ∈ 𝒳_F} S_r(x)` | lies in `[S_r(x⁺_r), (n_r / q) · I⁺_r + e_r]`: the left end is the sum of `x⁺_r`; the right end bounds every `S_r(x)` because `S_r(x) ≤ (n_r / q) · O_r(x) + e_r ≤ (n_r / q) · I⁺_r + e_r`. `R⁺_r` itself need not be reached by `x⁺_r`: XIs tied at `I⁺_r` can differ in `S_r` (the top-tie instance of section 9), and which of them the solver returns is its choice |
| least raw sum `R⁻_r` | lies in `[(n_r / q) · I⁻_r − e_r, S_r(x⁻_r)]`, symmetrically |
| bracket | every `x ∈ 𝒳_F` has `(n_r / q) · I⁻_r − e_r ≤ S_r(x) ≤ (n_r / q) · I⁺_r + e_r` |

Two facts are reported against the declared minimum `m_r` (the main solve's minimum, compared
exactly in `Fraction`; a floor is a different declaration). `m_r` is read from the
`requirements` argument as passed, never from the floored copy `requirements′` of 2.3 step 1,
whose `minimum` is `φ_r`; a test with `φ_r ≠ m_r` asserts it:

| Field | True | False | None |
|---|---|---|---|
| `minimum_reached_by_some_xi` | `S_r(x) ≥ m_r` for a returned witness `x`, read in the order `x⁺_r`, then `x⁻_r`; `minimum_reached_witness` names the end whose witness decided (`LARGEST` or `LEAST`) | `(n_r / q) · J⁺_r + e_r < m_r` with `J⁺_r` the proved integer upper bound of the LARGEST end | neither |
| `minimum_missed_by_some_xi` | `S_r(x) < m_r` for a returned witness `x`, read in the order `x⁻_r`, then `x⁺_r`; `minimum_missed_witness` names that end | `(n_r / q) · J⁻_r − e_r ≥ m_r`, `J⁻_r` the proved integer lower bound of the LEAST end | neither |

Both witnesses are XIs of `𝒳_F`, so each can decide either True fact: with floors, or when `O_r`
ties at an end, `x⁻_r` can reach a minimum `x⁺_r` misses, and when one end is `NO_SOLUTION` the
other end's witness can still decide. The sentence a True fact serves prints the deciding
witness's exact sum (7.5). A proved bound decides False whatever the end's certification. A
`FEASIBLE_NOT_PROVEN` end with a finite bound has both a witness and a bound; one whose bound is
not finite (2.3 step 7) decides only through its witness; a `NO_SOLUTION` end decides nothing.
A fact is `None` only when no returned witness and no bound decides it. `None` has two causes,
each with its own sentence (`reason` beside the fact, 7.7), read from the end whose bound would
decide False (LARGEST for reached, LEAST for missed):

- `ALLOWANCE`: that end is `QUANTIZED_OPTIMAL`. Then `m_r` lies between its witness's sum and its
  raw bound, a band at most `2e_r` wide, because `I± = O_r(x±)` and
  `|S_r − (n_r / q) · O_r| ≤ e_r`; "it lies inside the rounding allowance of the search" is true.
- `NOT_CERTIFIED`: that end is not `QUANTIZED_OPTIMAL`: `FEASIBLE_NOT_PROVEN` with a finite bound,
  `FEASIBLE_NOT_PROVEN` without one, or `NO_SOLUTION`. "The largest (least) end was not certified
  within the search limits" is true in each case. The `ALLOWANCE` sentence is never served for an
  unproved end: its undecided band holds CP-SAT's optimality gap, which no rounding allowance
  bounds (with `n = 1`, `q = 100000`, `a = 10`, an incumbent at 2.9 and a bound at 4.00005 leave a
  minimum of 3.5 undecided, 0.6 away from the incumbent while `e_r = 0.00005`).

The facts compare exact sums in `Fraction`. XI Lab's Satisfy solve above compares half-even
integers (`SHORTFALL_POLICY`): each of the `a_r` coefficients and the target moves by at most
half a unit, so within `(a_r + 1) · n_r / (2q)` of a minimum (that is `e_r + n_r / (2q)`, not
`e_r`) the two can disagree. With ten applicable slots, `q = 100000`, `n = 1` and every player
at 0.0000051, each `_q` is 1 and the sum 10, a minimum of 0.0001049 has `_q` 10 and no
shortfall, while the exact sum 0.000051 lies 5.39 units of `n / q` below it, beyond `e_r` (5 units).
With `n = 1`,
`q = 100000`, two slots and two players at 0.500004, a minimum of 1.000006 is reached by an XI
here (it sums to 1.000008) while `solve_xi(mode="SATISFY")` is INFEASIBLE (50000 + 50000 <
100001). Every reply that serves a minimum statement therefore also serves
`CEILING_EXACT_FACTS` (7.7), which names both comparisons (ADR-0020: every tool says which
policy a statement uses).

With declared floors, `𝒳_F` is the conservative inner set: an XI that meets a raw floor with less
than `(a_r + 1) · n_r / q` to spare can lie outside it (tradeoffs.py:215-230). Two players at
0.15 on one requirement meet a floor of 0.3 exactly, yet `14999 + 14999 < 30000`, so their XI is
outside `𝒳_F`, and a bound read off `𝒳_F` ("none sums to more than 5.0001") can be passed by
that XI (it sums to 10 on another requirement). Every statement read off a bound (the False
facts, the outer ends of the intervals, the ledger's "no XI above" and "no XI below") is
therefore about `𝒳_F`: whenever `floors` is non-empty, those sentences are served with the scope
`{xi}` of 7.7 and the reply carries `FLOORS_SCOPE`. The True facts and the attained sums need no
scope: a witness meets each raw floor exactly (2.3).

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
    integer_value: int | None      # O_r of the witness recomputed in Python, OBJECTIVE_POLICY units of n_r / q
    integer_bound: int | None      # I± when QUANTIZED_OPTIMAL; the solver's bound when FEASIBLE_NOT_PROVEN,
                                   # None when that bound is not finite (2.3 step 7)
    attained: float | None         # S_r(witness), the float nearest the exact sum (never printed: 7.5)
    raw_bound: float | None        # (n_r / q)·integer_bound ± e_r, rounded outward with math.nextafter; None with integer_bound
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
    minimum_reached_witness: str | None   # LARGEST | LEAST: the end whose witness decided True; else None
    minimum_reached_reason: str | None    # None | ALLOWANCE (LARGEST end QUANTIZED_OPTIMAL) | NOT_CERTIFIED (any other LARGEST end), 2.1
    minimum_missed_by_some_xi: bool | None
    minimum_missed_witness: str | None
    minimum_missed_reason: str | None     # as above, read from the LEAST end

@dataclass(frozen=True)
class CeilingCertificate:
    # FIELDABLE | UNFIELDABLE | NOT_SATISFIABLE | FLOORS_UNMET | UNKNOWN | MODEL_INVALID (2.3 step 6)
    feasible_set: str
    solves: int                    # CP-SAT calls actually made
    # one entry per end or cause solve the tool reached, in call order: the call's status, or
    # NOT_RUN for one the deadline skipped (2|R| NOT_RUN for a deadline passed at entry); ends
    # after a proof that ends the tool (2.3 step 6) are not reached and have no entry; () for
    # UNFIELDABLE by construction
    statuses: tuple[str, ...]
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
    # requirement_id ascending; () when the tool ended at step 2 (UNFIELDABLE by construction)
    # or at step 6
    ranges: tuple[RequirementRange, ...]
    floors: tuple[tuple[str, float], ...]     # (requirement_id, φ_r) ascending; () when none
    locked: tuple[int, ...]
    excluded: tuple[int, ...]
    certificate: CeilingCertificate
    claim: str                                # the 7.7 constant its state selects (below), word for word
    non_claim: str                            # CEILING_NON_CLAIM, word for word
    # served reasons, printed by the page (8.2): the kernel's reasons by construction, or
    # UNFIELDABLE_PROVED (defined here, 7.7) on a proved-empty model whose kernel recorded none
    reasons: tuple[str, ...]
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
most `MAX_MAGNITUDE`. At least one requirement must be in force: with `R` empty there is
nothing to range and no solve would show that an XI exists, so it is a `ValueError` (the
router always holds progression). A requirement in force with `hard=True` is a `ValueError`,
as `kernel.value` refuses one (kernel.py:670-674): a hard minimum is declared to this tool as a
floor, and a field that would be ignored is refused (the rule of 7.2). Each of these sentences
names no value. Every other input is validated by `ShortfallKernel.__init__`, `_background`
and `_tables` (unknown ids, duplicates, non-finite values, unknown slots, a coefficient, minimum
or expression above its magnitude limit).

Claim by state. The state selects the reply's `claim`, as 3.4 does for CONFLICT; `non_claim` is
always `CEILING_NON_CLAIM`. Each constant is defined in `ceilings.py` (7.7):

| State | `claim` | Why it is true there |
|---|---|---|
| `feasible_set = FIELDABLE`, and every end of every range is `QUANTIZED_OPTIMAL`, or `FEASIBLE_NOT_PROVEN` with `integer_bound` not `None` | `CEILING_CLAIM` | every end has a witness and a proved finite bound (2.3 step 7) |
| `FIELDABLE`, and some end is `NO_SOLUTION` or has `integer_bound` `None` | `CEILING_PARTIAL_CLAIM` | it speaks per cell: a printed sum is a witness's, a printed bound is proved, a cell marked not certified implies nothing |
| `UNKNOWN` (every end `NO_SOLUTION`, a deadline passed at entry included) | `CEILING_NOT_DECIDED` | no XI was found and no proof was made |
| `UNFIELDABLE` (by construction or by proof), `NOT_SATISFIABLE`, `FLOORS_UNMET` | `CEILING_EMPTY` | `𝒳_F` is empty, by construction or by the first `INFEASIBLE` solve (2.3 step 6) |
| `MODEL_INVALID` (a range solve or the cause solve refused) | `CEILING_REFUSED` | a refusal proves nothing, so this claim states no emptiness; it is not repeated in `statements` (7.5) |

### 2.3 Formulation

1. `kernel = ShortfallKernel(candidates, requirements′, formation, quantization=q, seed=seed)`
   with `requirements′` the requirements in which each floored `r` has `minimum = φ_r`
   (`dataclasses.replace`; only the floored tables enter the model, though `_tables` still
   validates every active requirement's minimum and raises `ValueError` on one above
   `MAX_MAGNITUDE`; the minimum facts read `m_r` from the unmodified `requirements`).
   `β = kernel._background(excluded, locked, None, (), None)`. Then, before step 2, the tables
   `H` of step 3 and the objective coefficients of step 4 are computed with their checks, so a
   `ValueError` never depends on load or on the background: `_background` builds `β.variables`
   even when `β.model` is `None` (kernel.py:496-529: the reasons only decide whether a model is returned, :549-551), and neither computation solves anything.
2. If the deadline has passed: every end `NOT_RUN` (`2·|R|` `NOT_RUN` statuses, no call),
   `feasible_set = UNKNOWN`, completeness `DEADLINE`. If `β.model is None`:
   `feasible_set = UNFIELDABLE` with `β.reasons`, no solve, no range, completeness `EXACT`.
3. `H = kernel._tables(β, conservative=True)` (computed in step 1); region `= β.model.clone()` plus
   `_at_least(region, kernel._expression(β, H[r][0]), H[r][1])` for each floored `r`, in
   ascending requirement id, so that a reordered `floors` mapping builds the same model.
4. Objective coefficients (computed in step 1), mirroring tradeoffs.py:299-312: for each key `(p, s)` of
   `β.variables` with `applies(r, s)`, `c = round(_scaled(β.vectors[p][μ_r], n_r, q))`;
   `|c| > MAX_MAGNITUDE` or `Σ|c| ≥ MAX_EXPRESSION_MAGNITUDE` is a `ValueError` naming no value.
5. For `r` in requirement-id order: one clone maximising `Σ c·x`, then one minimising it.
   At most `2·|R|` solves, plus one (step 6).
6. The first solve that is `INFEASIBLE` proves `𝒳_F` empty and ends the tool; no range is
   reported. With no floor, `feasible_set = UNFIELDABLE`, with the reason `UNFIELDABLE_PROVED`
   (7.7) when the kernel recorded none, as the maximiser and `kernel.value` add one
   (tradeoffs.py:453-457, kernel.py:739-743). With floors, one solve of `β.model` decides the
   cause: `INFEASIBLE` gives `UNFIELDABLE` (with that reason), a witness gives
   `NOT_SATISFIABLE`, `MODEL_INVALID` gives `MODEL_INVALID`, and `UNKNOWN` or `NOT_RUN` gives
   `FLOORS_UNMET`: no XI meets the floors (proved by the first solve), and whether one exists
   without them is not decided; its completeness is that of the undecided solve (1.5), so the
   reply is not stored. `UNFIELDABLE` and `NOT_SATISFIABLE` are proved: completeness `EXACT`.
   The proof supersedes any end left undecided before it (1.5, "a proof supersedes earlier
   calls"): an `UNKNOWN` LARGEST end followed by an `INFEASIBLE` LEAST end gives `UNFIELDABLE`,
   `EXACT`, `stopped_by` `None`, with the `UNKNOWN` kept in `statuses`. The first solve that
   is `MODEL_INVALID` also ends the tool, and so does a cause solve that is `MODEL_INVALID`:
   `feasible_set = MODEL_INVALID`, no range reported, completeness `MODEL_INVALID`, and the
   claim `CEILING_REFUSED` (7.7) in place of a cell that would blame the search limits.
   Otherwise, after the last solve, `feasible_set = FIELDABLE` when some solve returned a
   witness, and `UNKNOWN` when none did (every end undecided or `NOT_RUN`). The claim follows
   the state (2.2, "Claim by state").
7. `OPTIMAL`: `QUANTIZED_OPTIMAL`, `integer_bound = integer_value`. `FEASIBLE`:
   `FEASIBLE_NOT_PROVEN`, `integer_bound = max(value, ceil(best_objective_bound))` (LARGEST)
   or `min(value, floor(best_objective_bound))` (LEAST), the shipped formula
   (tradeoffs.py:421). The rounding is sound: the solver's true bound on an integer objective is
   an integer, and its float errs by far less than one unit for any expression within
   `MAX_EXPRESSION_MAGNITUDE`, so the rounded bound is at most one unit loose and never on the
   wrong side; a loose bound only makes a False fact of 2.1 harder to decide. A `FEASIBLE` end
   whose bound is not finite keeps its witness, `integer_value` and `attained`, with
   `integer_bound = None` and `raw_bound = None`; its fact is decided by the witness or is
   `None` with reason `NOT_CERTIFIED`. Otherwise `NO_SOLUTION` with every number `None`.

Witness check, without the solver, on every returned XI (a `RuntimeError` on failure, never a
silent answer): `kernel._admissible(β, lineup)`; each floor holds in integers and
`S_r(x) ≥ φ_r` in `Fraction` (tradeoffs.py:383-385); `O_r(lineup)` recomputed in Python
(OBJECTIVE_POLICY, from the lineup's values) equals `solver.value(Σ c·x)`, an exact Python int,
where `Σ c·x` is the same expression object the solve maximised or minimised. `integer_value`
is that recomputed `O_r` (tradeoffs.py:413-415). `solver.objective_value` is never compared,
stored as an integer or served (1.5): on an `OPTIMAL` solve it can be one or two ulp off the
integer. No `|objective_value − O_r| < 1/2` check is made either: with `Σ|c|` near
`MAX_EXPRESSION_MAGNITUDE = 2**50` one ulp is 1/4, so such a check could itself fail on a
correct optimum and serve a 500.

### 2.4 Certificate and time

| Situation | Reported |
|---|---|
| every end `QUANTIZED_OPTIMAL` | completeness `EXACT`; both facts decided wherever the minimum is outside the allowance |
| an end `FEASIBLE_NOT_PROVEN` | the attained sum and the bound are reported; the bracket still contains every feasible sum because the bound is CP-SAT's proved bound; a fact this end leaves undecided has reason `NOT_CERTIFIED`, never `ALLOWANCE` (2.1); a bound that is not finite is reported as no bound (`CEILING_NOT_CERTIFIED` in its cell); completeness `LIMIT_REACHED` or `DEADLINE` by the rule of 1.5 |
| an end `NOT_RUN`, `UNKNOWN` | `NO_SOLUTION`, no number, the sentence `CEILING_NOT_CERTIFIED`; completeness `LIMIT_REACHED` or `DEADLINE` (1.5; `NOT_RUN` is always `DEADLINE`) |
| `MODEL_INVALID` anywhere | the tool ends (2.3 step 6): no range, the claim `CEILING_REFUSED`, completeness `MODEL_INVALID` |
| `FLOORS_UNMET` | no range; `FLOORS_CONSERVATIVE` and `FLOORS_CAUSE_UNDECIDED`; completeness of the undecided solve (1.5) |

Relation to shipped code. `maximize_requirement` makes every active minimum a floor, has no
minimiser, no deterministic limit, and warnings that fail the copy guard (tradeoffs.py:233-244:
"quality", "soft", "fit"). CEILING is not built on it but mirrors its objective and floors, and
a test ties them on instances whose oracle feasible set is not empty (on an empty one CEILING
reports no range while the maximiser reports `NO_SOLUTION`, so there is nothing to compare):
with `floors` equal to every active minimum, the LARGEST end of each requirement has the
`integer_value`, `integer_upper_bound` and certification of
`maximize_requirement(target_requirement_id=r)` on the same inputs. The witnesses are not
compared: the kernel background adds symmetry breaking the maximiser lacks (kernel.py:530-548),
so two exact solvers can return different XIs with the same integer value, whose exact sums can
differ (2.1). Instead, on instances where both are `QUANTIZED_OPTIMAL`, each witness's exact sum
is asserted to lie in `[(n_r / q) · I⁺_r − e_r, (n_r / q) · I⁺_r + e_r]`, the band every XI with
integer value `I⁺_r` lies in (1.2), with `I⁺_r` the integer value both report. "The other's
bracket" read as `[witness sum, bound]` is not used: two correct witnesses tied at `I⁺_r` need
not lie in each other's.

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
an XI (yes, no, or not decided). It is one such set; the filter does not show whether another
exists, and it does not choose the set to be the smallest by count; eligibility, the minutes
gate, the evidence gate and missing measurements are part of the model and are never offered
for removal; nothing was relaxed in the solve it explains. Only a `MINIMAL_CERTIFIED` reply
carries this claim; every other status carries its own (3.4).

### 3.1 Declarations and background

| Family (deletion order) | One constraint per | Id | Holds for `x` when | Deleted means |
|---|---|---|---|---|
| `SLOT_COVERAGE` | slot, formation order | `slot:<slot_id>` | the slot is filled | the slot may stay empty |
| `EXCLUSION` | excluded player, ascending id | `exclusion:<player_id>` | he is in no slot | he is available |
| `REQUIREMENT_FLOOR` | floored requirement, ascending id | `floor:<requirement_id>` | `Σ_{s : applies(r, s)} c(v_{x(s)}[μ_r]) ≥ t(φ_r)` in the named arithmetic, `φ_r` the floor below (`m_r` for `explain_solve` and for `explain_floors` with `floors=None`) | no floor on `r` |
| `LOCK` | locked player, ascending id | `lock:<player_id>` | he is in some slot | he is not required |

The background is never deleted: the admissible keys (eligibility, minutes, the measurement
rule over `R`; exclusions are **not** applied to keys here, they are constraints), at most one
player per slot, at most one slot per player. With every declaration deleted, the empty
assignment satisfies the background, so a model with no XI always has a non-empty conflicting
set.

Arithmetic, named by the public function:

| Function | Floors | Arithmetic | Mirrors |
|---|---|---|---|
| `explain_floors(..., floors)` | `floors` given: those `r` at `φ_r` (`{}`: no floor, and the reply's arithmetic sentence says so, `CONFLICT_NO_FLOOR`, 7.7), keys and values validated as CEILING's (2.2); `floors=None`: every `r ∈ R` at `m_r`. A requirement in force with `hard=True` is a `ValueError` with CEILING's sentence (2.2): floors are the only hard declarations here, and a flag that would be ignored is refused | `HARD_POLICY` | `kernel.satisfiable` and `maximize_requirement`. It explains a hard-floor query; the API accepts it (`explains: "floors"`) and no page part sends it in this release (X10) |
| `explain_solve(..., mode)` (X2) | every `r ∈ R` with `r.hard or mode == "SATISFY"`, at `m_r`; `mode` other than `"BALANCE"` or `"SATISFY"` is a `ValueError`, as `solve_xi` refuses one | `SHORTFALL_POLICY` (`_q` coefficients and target) | `solve_xi`'s feasibility, solver.py:198-246, 274-275. The page explains the main solve with it, in the main solve's mode (8.2). In `BALANCE` mode with no hard requirement it declares no floor, and the reply's arithmetic sentence says so (`CONFLICT_NO_MINIMUM`, 7.7) |

A floor at a minimum the reader did not enter (the snapshot's default, which
`decision_inputs` takes for every requirement missing from `minimums`, decision_lab.py:293) is
still a declaration of the problem, and is labelled as the default it is (7.5); the module does
not know which minima were entered, the router does.

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
                                  # (only s0 gives the status MODEL_INVALID)
current = all
for c in order:
    if deadline passed: c and every later one -> NOT_RUN, kept; stop
    s = test(current − {c})       # a test whose solver is None (the deadline passed between the
                                  # check above and the call, 1.5) is NOT_RUN as in the line above
    INFEASIBLE      -> current = current − {c}            DROPPED
    witness w       -> check w against current − {c}       KEPT_WITNESS (w stored)
    UNKNOWN         -> kept                                KEPT_UNDECIDED
    MODEL_INVALID   -> kept; the filter continues          KEPT_REFUSED
conflict = current, in deletion order
for c in conflict, in deletion order:              # restore tests, after the filter
    SLOT_COVERAGE   -> NOT_APPLICABLE, no solve     # an XI fills every slot
    deadline passed -> NOT_RUN                      # also a test whose solver is None
    s = test(all − {c})
    INFEASIBLE      -> restores_alone = False      # another conflict remains
    witness w       -> check w against all − {c}; it is an XI; restores_alone = True
    UNKNOWN         -> restores_alone = None
    MODEL_INVALID   -> restores_alone = None; completeness MODEL_INVALID; the set's status
                       stands (the filter proved it) and the later restore tests still run
```

| Statement | Proof |
|---|---|
| `current` is never satisfiable | true after `s0`; it changes only to a set a solve just proved INFEASIBLE |
| the final set's infeasibility is certified by one recorded solve on exactly that set | the last `DROPPED` test was on the final set (later tests only keep, a `KEPT_REFUSED` one included), or `s0` if nothing was dropped. Its position in `statuses` is `final_set_proof_solve` |
| a refused filter test leaves the set certified | a `KEPT_REFUSED` member never leaves `current`, so the final set holds it and is still the set the last `DROPPED` test (or `s0`) proved; the status is `NOT_PROVEN_MINIMAL`, because that member's necessity was not checked, and the completeness `MODEL_INVALID` (1.5), so the reply is not stored |
| each `KEPT_WITNESS` member `c` is necessary to the set | its witness satisfies `current_t − {c} ⊇ final − {c}`, and a satisfiable set stays satisfiable when declarations are removed. The witness is checked again, without the solver, against exactly `final − {c}`. It is an assignment, not an XI: declarations outside `final − {c}` were not imposed on it |
| every proper subset of the final set is satisfiable | each proper subset is contained in `final − {c}` for some member `c` |
| what this does not prove | that `all − {c}` is satisfiable. Instance, with non-negative rates: slots, then `exclusion:A`, a progression floor above the largest sum any assignment reaches (for example above the sum, over the applicable slots, of each slot's largest admissible coefficient; "above every XI's sum" is vacuous here, because no XI exists (`lock:A` with `exclusion:A`), and with `exclusion:A` dropped an assignment may use `A`), `lock:A`, where `A` has an admissible key; every slot and the exclusion are dropped because the floor conflict persists, the floor is kept with a witness that leaves slots empty, and the final set is `{floor:progression}`; dropping the floor from everything declared still leaves `lock:A` with `exclusion:A`. The restore test reports `restores_alone = False` for it |
| `restores_alone = True` | the witness meets every declaration but `c`, slot coverage included, so it is an XI of the model without `c`; checked without the solver against `all − {c}` |
| solves | at most `1 + |order|` for the filter (with 11 slots, 11 locks, 30 exclusions and 3 floors, 56 small feasibility solves) plus one restore test per member of the final set that is not slot coverage |

Deletion order is a declared device: declarations tested early are dropped whenever possible,
so the set leans on locks and floors, the declarations a reader made, rather than on slot
coverage. When the model holds more than one minimal conflicting set, another order can return
another; the response says so conditionally and prints the order. When the set is the only
one, or a one-member set (the smallest any conflict can be, because the empty assignment
meets the background), an unconditional "another order can return another" or "it is not the
smallest by count" would be false, so the copy never says either (7.7). QuickXplain is not used: it needs fewer solves for small sets and its certificate is
harder to read; the deletion filter's certificate is one line per declaration.

### 3.4 Interface

```python
CONFLICT_VERSION = "deletion-filter-conflict-v1"
FAMILIES = ("SLOT_COVERAGE", "EXCLUSION", "REQUIREMENT_FLOOR", "LOCK")   # the deletion order
ARITHMETICS = ("SOLVE_HALF_EVEN", "HARD_FLOOR_CONSERVATIVE")   # explain_solve, explain_floors
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
    # DROPPED | KEPT_WITNESS | KEPT_UNDECIDED | KEPT_REFUSED (status MODEL_INVALID) | NOT_RUN
    outcome: str
    # KEPT_WITNESS only: an assignment meeting final − {c}; () otherwise (the two lists below
    # too). Not an XI: slots may be empty and a player whose exclusion lies outside
    # final − {c} may appear
    witness: ConflictLineup
    witness_excluded_players: tuple[int, ...]   # excluded players the witness uses; () when none
    witness_missing_locked_players: tuple[int, ...]   # locked players the witness leaves out; () when none

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
    initial_status: str            # the test of every declaration (s0)
    final_set_proof_solve: int | None   # index in statuses of the solve proving the final set (0: s0)
    # members_with_witness + members_undecided + members_refused == len(conflict)
    members_with_witness: int      # KEPT_WITNESS
    members_undecided: int         # KEPT_UNDECIDED and NOT_RUN
    members_refused: int           # KEPT_REFUSED
    witnesses_verified: bool
    solves: int                    # CP-SAT calls actually made
    # s0, then one per filter test in deletion order, then one per restore test that is not
    # NOT_APPLICABLE, in call order; NOT_RUN for a test the deadline skipped
    statuses: tuple[str, ...]
    per_solve_deterministic_limit: float
    deletion_order: str
    completeness: str              # EXACT | LIMIT_REACHED | DEADLINE | MODEL_INVALID (1.5)
    stopped_by: str | None

@dataclass(frozen=True)
class MinimalConflict:
    # MINIMAL_CERTIFIED | NOT_PROVEN_MINIMAL | MODEL_FEASIBLE | UNDECIDED | MODEL_INVALID
    status: str
    requirements_in_force: tuple[str, ...]  # R, requirement_id ascending (1.3: equal to solve_xi's active set)
    declarations: tuple[Declaration, ...]   # all of them, deletion order
    conflict: tuple[str, ...]               # constraint ids of the set, deletion order; () unless the final set is certified
    tests: tuple[DeletionTest, ...]         # filter rows, deletion order; () for MODEL_FEASIBLE and UNDECIDED (status rules)
    restore_tests: tuple[RestoreTest, ...]  # one per member of the set, deletion order; () when conflict is ()
    feasible_witness: Lineup                # MODEL_FEASIBLE: an XI meeting every declaration
    certificate: ConflictCertificate
    locked: tuple[int, ...]
    excluded: tuple[int, ...]
    claim: str                              # the 7.7 constant its status selects, word for word
    non_claim: str                          # CONFLICT_NON_CLAIM, word for word
    provenance: dict

def explain_floors(candidates, requirements, formation="4-3-3", *,
                   floors: Mapping[str, float] | None = None,
                   locked=(), excluded=(), seed=20260906, quantization=QUANTIZATION,
                   deadline: float, provenance=None) -> MinimalConflict
# X2: the arithmetic of the Satisfy solve it explains (SHORTFALL_POLICY, 1.2)
def explain_solve(candidates, requirements, formation="4-3-3", *, mode: str,
                  locked=(), excluded=(), seed=20260906, quantization=QUANTIZATION,
                  deadline: float, provenance=None) -> MinimalConflict
```

Status rules. The status selects the reply's `claim` (7.7), and `non_claim` is always
`CONFLICT_NON_CLAIM`:

| Status | When | `claim` | `tests`, `restore_tests`, `conflict` |
|---|---|---|---|
| `MINIMAL_CERTIFIED` | the initial test is INFEASIBLE and every member of the final set is `KEPT_WITNESS` | `CONFLICT_CLAIM` | every filter row; one restore row per member; the set |
| `NOT_PROVEN_MINIMAL` | the final set is certified infeasible and at least one member is `KEPT_UNDECIDED`, `KEPT_REFUSED` or `NOT_RUN`; each `KEPT_UNDECIDED` or `NOT_RUN` member carries `CONFLICT_MEMBER_UNDECIDED` and each `KEPT_REFUSED` member `CONFLICT_MEMBER_REFUSED`, never "needed"; completeness `MODEL_INVALID` when any filter or restore test was `MODEL_INVALID` (1.5) | `CONFLICT_NOT_PROVEN_CLAIM` | as above |
| `MODEL_FEASIBLE` | the initial test found an XI, which is checked and returned (completeness `EXACT`) | `CONFLICT_FEASIBLE` | `()`, `()`, `()`; no filter test runs, so no `NOT_RUN` row turns the reply into `DEADLINE` |
| `UNDECIDED` | the initial test was not decided (`UNKNOWN`, or `NOT_RUN` for a deadline already passed at entry) | `CONFLICT_NOT_DECIDED` | `()`, `()`, `()`; completeness by 1.5, nothing stored |
| `MODEL_INVALID` | the initial test was `MODEL_INVALID` (a filter test that is refused keeps its member, `KEPT_REFUSED`, above) | `CONFLICT_MODEL_INVALID` | `()`, `()`, `()`; `final_set_proof_solve = None`; completeness `MODEL_INVALID` |

Completeness is `EXACT` only when every filter test and every applicable restore test is
decided; otherwise `LIMIT_REACHED`, `DEADLINE` or `MODEL_INVALID` by the rule of 1.5. An
undecided restore test never changes the status of the set: it only leaves that member's
`restores_alone` at `None`. A restore test that is `MODEL_INVALID` does not either: the filter
proved the set, so its status and its `claim` stand, that member's `restores_alone` is `None`,
the later restore tests still run, and the completeness is `MODEL_INVALID`.

Validation. `conflict.py` builds a `ShortfallKernel` on the declared candidates, requirements,
formation, seed and quantisation, for its validation (`__init__`) and its input contract
(section 10), and passes locks and exclusions through `_player_ids`; it does not solve the
kernel's background model, in which coverage and exclusions are fixed. Coefficient tables are
computed here with the shipped functions (`_q`, or `floor`/`ceil` of `_scaled`), with the
`MAX_MAGNITUDE` and `MAX_EXPRESSION_MAGNITUDE` checks of `kernel._tables` on every coefficient,
target and expression, over keys that include excluded players (exclusions are declarations
here, 3.1), and a test asserts they equal `kernel._tables` on the keys both hold. So the
"mirrors `solve_xi`" parity of 3.1 holds within those limits: an excluded player's coefficient
above them, which `solve_xi` never reads (solver.py:200-201, 267), is a `ValueError` in
`explain_solve`; no request the router builds reaches that case. Witness checks verify
admissibility, injectivity, every declaration of the tested set in integers and, for
`HARD_FLOOR_CONSERVATIVE`, every floor of the tested set in `Fraction`; a restore witness is also checked to be an XI of the model without `c` (every
slot filled, every lock but `c` in, every exclusion but `c` out). A filter witness records the
excluded players it uses and the locked players it leaves out: either can happen when that
declaration lies outside `final − {c}`, and the page names both (7.5).

## 4. FRONTIER: `galactico/optimization/xi/frontier.py`

Design claim (never served; the served sentences are the 7.7 constants `FRONTIER_CLAIM` and
`FRONTIER_NON_CLAIM`, defined in `frontier.py`; `FRONTIER_CLAIM` speaks of each listed point
and states no completeness, so it is true on every status, and completeness is stated by
`status_text`, 7.5): every combination of 2 or 3 declared
requirement sums **in the shipped rounding** (OBJECTIVE_POLICY integers) that some XI reaches
and that no XI's rounded sums match or exceed on all of them while exceeding it on one, each
with one XI that reaches it, with a proof that none is missing. The certified object is the
integer vector, and that is what the page prints as the point (exactly, 7.5); the witness's
unrounded sums are printed beside it, in the same unit, as a secondary column and are not the
point. Not a ranking, no point is preferred, nothing is said about a requirement that was not
declared, and a sum is not a forecast. O7 forbids "best/optimal trade-off/knee". Because that
can be read as three phrases ("best", "optimal trade-off", "knee") or with "best" and
"optimal" each qualifying "trade-off", the words never served on the frontier are the union:
"best", "optimal", "trade-off" (also "tradeoff" and "trade off") and "knee". A test checks
every served frontier string outside provenance and the rendered frontier panel for them. The
one exception is the solver status token `OPTIMAL` in a status field of the certificate
(`stage_statuses`, `statuses`, `final_region_status`): a certified solver status under R11, not
the forbidden phrase.

### 4.1 Definition

Dimensions `D = (r_1, …, r_d)`, `d ∈ {2, 3}`, distinct members of `R`, declared by the
reader in an order; no default exists. The feasible set is `𝒳_F` of section 2.1 (eligibility,
locks, exclusions, and hard floors only if declared, compared conservatively; ROOT 2.4), so
with floors the completeness sentence is scoped to it as CEILING's bound sentences are (2.1,
`{xi}` and `FLOORS_SCOPE` of 7.7): an XI that meets a raw floor exactly can be outside `𝒳_F` and
above every listed point. For `x ∈ 𝒳_F`,
`V(x) = (O_{r_1}(x), …, O_{r_d}(x))` in OBJECTIVE_POLICY integers. `u` dominates `v` iff
`u ≥ v` componentwise and `u ≠ v`. The frontier `P` is the set of vectors `V(x)` that no
`V(y)` dominates. The claim is "nondominated among the declared descriptors at the shipped
quantisation" (O7): two XIs with different raw sums can share a vector, and an XI whose raw
vector is nondominated can be dominated after rounding, within `a_r · n_r / q` per dimension.
Each point reports beside it, in club medians (the unit of the point `V_i / q`), the witness's
sums divided by `n_r` and the allowance `a_r / (2q) = e_r / n_r`: for every XI,
`|S_r(x) / n_r − O_r(x) / q| ≤ a_r / (2q)` exactly (1.2). Raw sums in per-90 units beside a point
in club medians would differ from it by a factor near `n_r`, which is not 1 for any shipped
requirement (decision_lab.py:302); the three columns therefore share one unit (7.5).

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
region R_0 = background β + declared floors, in ascending id, and the objective coefficients
             of each dimension (section 2.3 steps 1 to 4, with their ValueErrors, raised before
             any deadline or emptiness check as in 2.3 step 1)
loop k = 0, 1, …
    if |points| = max: the limit check, one solve of R_k with no objective (a feasibility solve,
    as CONFLICT's tests, 3.2), dispatched as:
        a witness (OPTIMAL or FEASIBLE: no optimum was asked, so 1.5 does not count it undecided)
                                         -> LIMIT_REACHED, stopped_by POINT_LIMIT, final_region_status
                                            that status (an XI of R_k proves a further point)
        INFEASIBLE                       -> COMPLETE (final_region_status INFEASIBLE)
        anything else (UNKNOWN, NOT_RUN, MODEL_INVALID)
                                         -> stop: completeness and stopped_by by 1.5,
                                            final_region_status this status
    otherwise, for stage i = 1..d (stage i > 1 first fixes V_j = v_j for j < i), maximise V_i
    over R_k; dispatch its status in this order, the same for every stage:
        INFEASIBLE, i = 1, no point yet  -> P is proved empty; status and completeness by the cause (below)
        INFEASIBLE, i = 1                -> COMPLETE (final_region_status INFEASIBLE)
        INFEASIBLE, i > 1                -> RuntimeError (a lexicographic level was lost)
        not OPTIMAL (FEASIBLE, UNKNOWN, NOT_RUN, MODEL_INVALID)
                                         -> stop: completeness and stopped_by by 1.5,
                                            final_region_status this stage's status; this iteration
                                            records nothing
        OPTIMAL                          -> v_i = solver.value(V_i), an exact int (1.5); next stage
    record v = (v_1, …, v_d) and the stage-d witness, checked without the solver
    R_{k+1} = R_k ∧ OR_i (V_i ≥ v_i + 1)      # Booleans b_i, b_i ⇒ V_i ≥ v_i + 1, add_bool_or(b)
```

The cause of an empty `P`, as CEILING's (2.3 steps 2 and 6): `β.model is None` gives
`UNFIELDABLE` by construction (`final_region_status = INFEASIBLE_BY_CONSTRUCTION`, the kernel's
reasons, no solve), `COMPLETE`. Otherwise, with no floor, `UNFIELDABLE` (reason
`UNFIELDABLE_PROVED` when the kernel recorded none), `COMPLETE`; with floors, one solve of
`β.model`: `INFEASIBLE` gives `UNFIELDABLE` and a witness `NOT_SATISFIABLE`, each `COMPLETE`, `MODEL_INVALID` gives `MODEL_INVALID`, and `UNKNOWN` or `NOT_RUN` gives
`FLOORS_UNMET`, whose completeness is that solve's (1.5): the empty frontier is proved, its cause
is not, and the reply is not stored. A point recorded before any stop, a `MODEL_INVALID`
included, is kept.

| Statement | Proof |
|---|---|
| each recorded `v` is nondominated in `𝒳_F` | suppose `V(y) ≥ v`, `V(y) ≠ v`. If `y ∉ R_k`, some earlier point `w` has `V(y) ≤ w`, so `v ≤ w`; but the witness of `v` lies in `R_k`, so for each earlier point `w` some `v_i ≥ w_i + 1`, and `v` is not weakly below `w`. So `y ∈ R_k`, and `V(y)` is lexicographically above `v`, contradicting the lexicographic maximum |
| points are distinct | a new point is not weakly below any earlier one |
| complete when `R_k` is INFEASIBLE (its stage-1 solve, or the limit check) | every `x ∈ 𝒳_F` has `V(x)` weakly below some point; a nondominated vector weakly below a point equals it |
| when complete, every feasible vector is weakly below a point | the same sentence |
| a witness of the limit check proves a further point | an XI `x ∈ R_k` has `V(x)` not weakly below any listed point; some point `p` of `P` has `V(x) ≤ p`, and `p` is not listed, since `p ≤ w` for a listed `w` would give `V(x) ≤ w` |
| termination and solve count | each iteration adds a distinct vector of the finite set `{V(x)}`. A complete non-empty run makes exactly `d · |P| + 1` solves (the last stage-1 solve or limit check is INFEASIBLE); a run cut by `POINT_LIMIT` makes `d · max_points + 1`; an empty `P` makes one solve without floors and two with them (the stage-1 solve and the cause solve, below), and none by construction |
| partial lists stay true | every point recorded before a limit or a deadline was proved nondominated when it was recorded; only completeness is lost |
| a cut list is a prefix | the `k`-th recorded point is the `k`-th point of `P` in lexicographic-descending order of the declared dimensions (each iteration takes the lexicographic maximum over `R_k`, which holds every point not yet listed), so a list cut by `POINT_LIMIT` or a deadline is the lexicographic-largest prefix of `P` in the declared order |

The dimension order decides the order in which the points are found and which XI is shown for
each (the stage-`d` witness depends on which sums were fixed first). The complete set `P` does
not depend on it. A list cut by `POINT_LIMIT` or a deadline does: it is a prefix in the declared
order, so with `d = 2` the reversed declaration lists the other end of the frontier, not the same
points reversed (one slot, players `(6 − i, i)` for `i = 1..5`, `max_points = 2`: `[(5,1),(4,2)]`
both ways, each in its own coordinates). No summed or weighted objective exists anywhere
(ADR-0020 rejected it).

### 4.3 Interface

```python
FRONTIER_VERSION = "lexicographic-cut-frontier-v1"
MAX_FRONTIER_POINTS = 64
DIMENSION_COUNTS = (2, 3)
POINT_ORDER = ("lexicographic, descending, in the order in which the requirements were "
               "declared; when the list is complete, reversing a two-requirement declaration "
               "reverses it; when it is not complete, the points listed are the first ones in "
               "that order, and declaring the requirements in another order may list other "
               "points")   # one constant, true in every state (4.2, a cut list is a prefix); "may":
                           # a list stopped by a deadline can hold all of P

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
    # OPTIMAL or FEASIBLE with stopped_by POINT_LIMIT: the limit check found an XI, so another
    # point exists. Otherwise the status of the solve that stopped the search (a stage i, or
    # the limit check: FEASIBLE, UNKNOWN, NOT_RUN, MODEL_INVALID): no proof.
    final_region_status: str
    solves: int                         # CP-SAT calls actually made (4.2, solve count)
    statuses: tuple[str, ...]           # every call in call order, NOT_RUN for one the deadline skipped
    # COMPLETE (also for a proved empty set) | LIMIT_REACHED | DEADLINE | MODEL_INVALID (1.5);
    # FLOORS_UNMET takes that of its undecided cause solve
    completeness: str
    stopped_by: str | None              # POINT_LIMIT | DETERMINISTIC_LIMIT | WALL_CLOCK; None when no call is undecided and no limit cut the list (1.5)
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
    status: str                         # FRONTIER | UNFIELDABLE | NOT_SATISFIABLE | FLOORS_UNMET | INCOMPLETE | MODEL_INVALID
    points: tuple[FrontierPoint, ...]   # POINT_ORDER
    point_order: str
    floors: tuple[tuple[str, float], ...]
    locked: tuple[int, ...]
    excluded: tuple[int, ...]
    certificate: FrontierCertificate
    claim: str                          # FRONTIER_CLAIM, word for word, on every status; it states no completeness
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

`ValueError` (a 422 at the API), each with a sentence that names no value, when
`len(dimensions) ∉ DIMENSION_COUNTS`, a dimension repeats or is not an active requirement,
`max_points` is not an `int` in `1..64` (`type(max_points) is int`, so `True` is refused), a floor
key or value fails CEILING's checks (2.2), a dimension's objective coefficients fail the
magnitude checks of 2.3 step 4, or a requirement in force has `hard=True` (floors are the only
hard constraints, and a hard flag would otherwise be ignored silently; CEILING refuses it too).
Status `FRONTIER` with completeness `COMPLETE`; `UNFIELDABLE` and `NOT_SATISFIABLE` with
`COMPLETE` (the empty set is proved); `FLOORS_UNMET` with the completeness of its undecided
cause solve (4.2); `INCOMPLETE` with `LIMIT_REACHED` or `DEADLINE` and every listed point
certified; `MODEL_INVALID` with the points recorded before the refusal. A point limit reached
exactly is not a stop: a frontier of exactly `max_points` points is `COMPLETE` when the limit
check is INFEASIBLE.
Witness check per point: admissible, floors in integers and `Fraction`, `V(lineup)` recomputed
in Python equals the point, whose coordinates are `solver.value` of each stage's expression
(1.5). `pairwise_nondominated` is recomputed on the returned list without a solver; false is a
`RuntimeError`.

## 5. DECLARED-RISK: `galactico/optimization/xi/risk.py`

Design claim (never served; the served sentences are the 7.7 constants, defined in `risk.py`
with `RISK_HARD`, `RISK_OVERFLOW`, `RISK_NOT_EVALUABLE` and `RISK_GROWTH`, which `risk.py` raises
or returns, and restated by the router where it serves them by name, 7.1): on the shared resampled worlds of the snapshot, an XI that a
declared rule over the per-world loss selects, its optimum, which players every and some XI
of the rule's level set hold, and, **for the XI shown**, the worlds that decide its value.
Another XI the rule selects has the same optimum and can have other tail or binding worlds;
the page says so. Non-claim (E-13's, verbatim): "Stability against resampling of the
historical matches; not robustness to opponents, absences or form, and not a forecast." No
chance figure, share or average over worlds is computed or printed, with one possible
exception left to section 13: if E-13's owner keeps its tail statistic, the product serves
`Σ M / k` as an exact text labelled as the mean largest shortfall over the `k` tail worlds,
never a share or a chance.

### 5.1 Per-world loss and its encoding

For `w ∈ U` and `x ∈ 𝒳` (section 1.4; the same set in every used world), with `_q`
coefficients `c^w_r(p) = _q(V^w_p[μ_r], n_r, q)` and targets `t_r = _q(m_r, n_r, q)`:
`d^w_r(x) = max(0, t_r − Σ_{s : applies(r, s)} c^w_r(x(s)))`, `M^w(x) = max_r d^w_r(x)`,
`T^w(x) = Σ_r d^w_r(x)`. The loss of `x` in `w` is the pair `(M^w, T^w)`, compared
lexicographically (O8).

Bounds, from the instance and never from an outcome: `L^w_r = Σ` over the keys `(p, s)` of
`β_w.variables` (5.6 step 2: `Eligible(p, s)`, `p ∉ X`, measured under `V^w`) with
`applies(r, s)` of `min(0, c^w_r(p))`, which is solver.py's `lower` (solver.py:258-270, over
`variables`, which leave out excluded players, solver.py:200-201); `U^w_r = max(0, t_r − L^w_r)`
(the deficit bound of solver.py:270, 276); `T_bound = max_{w ∈ U} Σ_r U^w_r`;
`M_bound = max_{w ∈ U} max_r U^w_r`. They are computed only when `|U| ≥ 1`, after step 1's
`NOT_EVALUABLE` test (5.6), so the maxima are never over an empty set. When `R` is empty,
`M^w = T^w = 0` and `T_bound = M_bound = 0`, so `BIG = 1` (as `solve_xi` reads `deficits or [0]`
and the kernel `default=0`).

`E^w(x) = BIG · M^w(x) + T^w(x)` with

    BIG = 2 · |U| · T_bound + 1

| Requirement on BIG | Holds because |
|---|---|
| O8: strictly larger than the largest possible total | `BIG > T_bound ≥ T^w(x)` |
| TAIL: a sum of `k ≤ |U|` encodings orders as the pair (sum of `M`, sum of `T`) | `BIG > |U| · T_bound ≥ Σ_{w ∈ K} T^w` for every set `K` of used worlds (E-13 DISSENT 3) |
| REGRET: `E^w − E*^w` orders as the pair `(M^w − M*^w, T^w − T*^w)` | the `T` part lies in `[−T_bound, T_bound]` and `BIG > 2 · T_bound` |
| a device, not a parameter | any larger value gives the same order; a test doubles it and requires identical rule-invariant outputs (status, optimum, tail sums or regret optimum, membership). The XI shown and its tail worlds may change: CP-SAT's representative of a tied level set depends on the objective coefficients |

`E` and `BIG` exist only inside `_encoding_base`, the overflow guard (5.6 step 2), the model
builders and the one Python equality check of 5.6. They are never a field, a provenance value, a log record, an exception
message or a served number; a test asserts each (section 9). O8 permits this encoding for the
risk modes; ADR-0020 rejected a weighted sum of the two stages as a search device for the
kernel, and the kernel keeps its three-solve form. The request for ADR-0030 (section 12)
records that O8 overrides that rejection for the risk modes only, and why: BIG is exact by
5.1, never serialised, and tested.

Split variables. No integer variable of a risk model has a domain of size `E_max =
BIG · M_bound + T_bound`. A variable that holds an encoding (`η`, `u_w`, `ρ` of 5.6) is written
`BIG · a + b` with `a ∈ [0, M_bound]` and `b ∈ [0, BIG − 1]`. Over those domains `BIG · a + b`
takes every integer of `[0, E_cap − 1]`, `E_cap = BIG · (M_bound + 1)`, which contains
`[0, E_max]` because `T_bound ≤ BIG − 1`; so the optimum, the level set and the Python check of
5.6 are exactly those of the unsplit model, and `E^w ≤ E_cap − 1` for every `w` and `x`.
Measured on ortools 9.15.6755, the project's version: the unsplit TAIL model of the previous
draft (`η, u_w ∈ [0, E_max]`) ignored its wall-clock limit and raised `MemoryError`
(`std::bad_alloc`) during search on 2 of 144 seeded TAIL selections of oracle-sized instances
(3 slots, 7 candidates, `q = 1000`, `k = 2`), its memory growing about 110 MB/s and
`max_memory_in_mb` not stopping it; the split model matched the brute-force oracle (optimum,
level set, membership) on all 144, with no crash and no overrun. Solver parameters are not the
fix: `linearization_level=2` clears those two instances and fails a third.

Overflow guard. A request is refused with `ValueError(RISK_OVERFLOW)`, a sentence holding no
number, when `(k + |U| + 2) · E_cap ≥ 2**53` (TAIL) or `3 · E_cap ≥ 2**53` (REGRET), at the
place in the algorithm 5.6 step 2 fixes (after `NOT_EVALUABLE` and the tables, before the
deadline rule, the `UNFIELDABLE`-by-construction test and any solve). Each bounds
the absolute value every linear expression of the model can take over its variables' domains
(the objective, the epigraph constraints and the level-set constraint of 5.6), so CP-SAT works
far inside int64 and every integer the tool reads with `solver.value` is exact. The float
`objective_value` and `best_objective_bound` are never read as integers (1.5); an incumbent can
reach `(k + |U|) · (E_cap − 1)`, so no claim of float exactness is made about it. At the shipped
default minima `t_r = q` exactly (the normaliser is the default minimum), so with non-negative
rates `T_bound = |R| · q` and `M_bound = q`; a minimum `μ` times the club median makes
`E_cap ≈ 2 · |U| · |R| · μ² · q²`, and with `|U| = B` the TAIL guard admits `μ` up to about
`(2**53 / (2 · (k + B + 2) · B · |R| · q²))^½`: about 7.8 at `B = 40`, `k = 20`, `|R| = 3`, and
about 25 at `B = 12`, `k = 6`; REGRET admits about `(2**53 / (6 · B · |R| · q²))^½`, about 35 at
`B = 40`. This is arithmetic on the definitions, not a measurement.

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
worlds grows with their number (O8): `RiskCertificate.growth`, `RISK_GROWTH` formatted by
`risk.py`, which says the same of a tail sum and so is carried by every TAIL certificate too,
and which the page prints in the certificate block (5.7, 8.2). With `|U| < k` the rule is
`NOT_EVALUABLE`; `k` is not lowered.

Reported for the XI shown (another XI of the level set can have other tail worlds; the page
labels these tables "for the XI shown"): every used world's pair; the tail, the `k` worlds
sorted by the key (`M^w` descending, `T^w` descending, `world_id` ascending) and cut at `k`;
the boundary ties, the worlds outside the tail with the same pair as its last member, in
ascending world id; the
tail sums `(Σ M, Σ T)`, which are the rule's optimum and so the same for every XI it
selects.

### 5.3 MINIMAX_REGRET

`E*^w = BIG · M*^w + T*^w`, where `(M*^w, T*^w)` is the certified least pair in world `w`:
`kernel.value(excluded=X, locked=L, values=V^w, deadline=…)` with status `CERTIFIED` (BALANCE
on that world, ADR-0020; `_q` rounding). Objective: minimise `max_{w ∈ U} (E^w(x) − E*^w)`;
every term is at least 0 (O8). Reported: for every used world, both pairs, the XI shown's
and the world's least; the binding worlds of the XI shown, in ascending world id, every `w`
whose pair of differences `(M^w − M*^w, T^w − T*^w)` is the lexicographic maximum, found by
comparing those
tuples in local Python variables that are never stored, logged or served (E stays inside 5.1's
limits); the ledger and the page print each binding world with its two pairs and never a
difference (O8). Another XI the rule selects has the same optimum and
can have other binding worlds; the page says so. If a used world's least is `UNFIELDABLE`,
the rule is `UNFIELDABLE` (by the lemma of 1.4 every used world shares `𝒳`, so all are), with
completeness `EXACT` (the proof supersedes any other world's undecided or refused least, 1.5),
no XI and never `UNKNOWN`. Its reasons are the kernel's construction reasons, and when the
least is `UNFIELDABLE` by solver proof, `UNFIELDABLE_PROVED` (7.7) in place of the sentence
`kernel.value` adds (kernel.py:739-743, which names "pins", a declaration XI Lab does not have),
so the three rules serve one reason for one proved fact (5.6 step 6). Otherwise, if any used
world's least is `MODEL_INVALID` (`kernel.value` returns it with a reason, kernel.py:703-706),
the rule is `MODEL_INVALID`, completeness `MODEL_INVALID`, no XI, no selection solve. Otherwise,
if any used world's least pair is not `CERTIFIED` (`UNKNOWN`), the rule returns `UNKNOWN` with
those worlds in `undecided_world_ids` and no XI: unlike the shipped bootstrap, a world is not
set aside for a wall-clock reason, because that would make the rule's objective depend on load.

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
   `w ∈ U`, `β_w = kernel._background(X, L, None, (), V^w)`, and `β_w.variables.keys() ==
   β.variables.keys()` is checked with an explicit `RuntimeError` on failure (the lemma of 1.4;
   not an `assert`, which `python -O` removes); `G^w = kernel._tables(β_w, conservative=False)`
   (its `ValueError`s). Only `β`'s model and variables are solved; each `β_w` serves its keys and
   tables. Then, in this order, none of it a solve: the overflow guard of 5.1 (`L^w_r`, `U^w_r`,
   `T_bound`, `M_bound`, `BIG` and `E_cap` from the keys and tables just built, which exist even
   when `β.model` is `None`; `ValueError(RISK_OVERFLOW)`), so a refusal depends neither on load nor
   on the background and comes, for REGRET, before any per-world optimum is spent; the deadline
   rule (a passed deadline gives `UNKNOWN`, no solve, as the kernel); and `β.model is None`:
   `UNFIELDABLE` by construction, completeness `EXACT`.
3. Per world and requirement, over `β`'s variables with world `w`'s coefficients
   (`kernel._expression(β, G^w[r][0])`, target `G^w[r][1] = t_r`): `d^w_r ∈ [0, U^w_r]` with
   `d^w_r + Σ c·x ≥ t_r`; `M^w ∈ [0, M_bound]` with `M^w ≥ d^w_r`; `T^w = Σ_r d^w_r`;
   `E^w = BIG · M^w + T^w`, an expression, never a variable. A linear epigraph, no
   `add_max_equality` (ADR-0020). The objectives below are non-decreasing in every `M^w` and
   `T^w`, so at the optimum the epigraph values can be taken exact.
4. TAIL, with the split variables of 5.1: `η = BIG · η_M + η_T` and, per used world,
   `u_w = BIG · u^M_w + u^T_w`, with `η_M, u^M_w ∈ [0, M_bound]` and `η_T, u^T_w ∈ [0, BIG − 1]`;
   `BIG · u^M_w + u^T_w ≥ BIG · (M^w − η_M) + (T^w − η_T)`; minimise
   `Φ = k · (BIG · η_M + η_T) + Σ_w (BIG · u^M_w + u^T_w)`. For fixed `x` the minimum over `η` is
   the sum of the `k` largest `E^w(x)`, reached at the `k`-th largest value, which the split
   domain holds (5.1).
5. REGRET: per-world optima first (`|U|` calls of `kernel.value`, three bounded solves each);
   then `ρ = BIG · ρ_M + ρ_T` with `ρ_M ∈ [0, M_bound]`, `ρ_T ∈ [0, BIG − 1]`,
   `ρ ≥ E^w − E*^w` for every `w`; minimise `ρ`. REGRET did not fail in the measured runs, but its
   `ρ` had the same domain of size `E_max`, so it is split too.
6. The selection solve uses `risk._solver` (deterministic limit `SELECTION_DETERMINISTIC_LIMIT =
   40.0`, recorded). Only `OPTIMAL` is a selection. `INFEASIBLE` is a proof that no XI exists
   (for example two locked goalkeepers: each lock has an admissible key, so the kernel records
   no reason, kernel.py:518-529, and CP-SAT proves the model empty): status `UNFIELDABLE`,
   completeness `EXACT`, no lineup, the solve recorded, the reason `UNFIELDABLE_PROVED` (7.7).
   `UNKNOWN` / `FEASIBLE`: `UNKNOWN`, no lineup, completeness by 1.5. `MODEL_INVALID`: status
   `MODEL_INVALID`, no lineup, completeness `MODEL_INVALID`. A solver exception is not a status
   (1.5): it propagates and the API answers 500. The witness is checked without the solver:
   admissible; `(M^w, T^w)` recomputed per world with `kernel._shortfalls(G^w, lineup)`; the
   objective recomputed from those integers in Python (the sum of the `k` largest `E^w`, or the
   largest `E^w − E*^w`) equals `solver.value` of the objective expression, an exact int (1.5).
   `Φ*` and `ρ*` are those Python-recomputed integers, never `objective_value`.
   The tail, the boundary ties and the binding worlds are then computed from pairs alone.
7. Ties (R11). The rule's level set is the base model plus `Φ ≤ Φ*` (TAIL, the split expression
   of step 4) or `ρ ≤ ρ*` (REGRET); with the split variables free this admits exactly the XIs
   whose objective equals the optimum. For each candidate in id order, the opposite solve of
   `kernel.membership` (kernel.py:876-912): in the selected XI, add `Σ_s x_{p,s} = 0`;
   otherwise add `= 1`. INFEASIBLE is the only source of `necessary = True` and of
   `possible = False`; an undecided solve leaves `None`. Excluded players and players with no
   admissible key are `(False, False)` by construction; locked players `(True, True)`. The
   membership block has its own `completeness`. When no selection exists because none can
   (`UNFIELDABLE`, `NOT_EVALUABLE`) it is `EXACT` with no rows, since nothing is undecided. When
   the selection itself is undecided (`UNKNOWN`) or refused (`MODEL_INVALID`) it has no rows and
   the selection's completeness (1.5), so the reply is not stored. With `analyze_ties=False` no
   membership solve is made: no rows, completeness `NOT_REQUESTED`, which `runtime.is_complete`
   does not treat as complete; the router always passes `True`. These solves use
   `SELECTION_DETERMINISTIC_LIMIT` too and stop at the deadline. No CORE / FAVORED / CONTESTED /
   FRINGE label is formed here: those stay on the main solve (H10).

The point-estimate requirement ledger is reported for every rule (E-13's "What no outcome
changes"): `point_loss`, the selected XI's pair at the point values (`_q` tables of the 0-world
point vectors; `None` if the lineup uses a key the point vectors forbid), and `point_sums`, for
each requirement in force its exact raw sum `S_r` at the point values as the float nearest it,
or `None` for a requirement whose metric is `None` at a key the lineup uses, as `point_loss` is.
The snapshot never holds a world value where the point value is `None` (historical.py:210-215),
but the module does not assume it, and the oracle instances draw holes independently.

### 5.7 Interface

```python
RISK_VERSION = "declared-risk-lexicographic-v1"
RULES = ("WORST_WORLD", "TAIL", "MINIMAX_REGRET")      # the fixed order of the page
TAIL_MENU = MappingProxyType({12: (2, 3, 6), 40: (4, 10, 20)})   # TAIL only; WORST_WORLD is k = 1
SELECTION_DETERMINISTIC_LIMIT = 40.0
EXACT_OBJECTIVE_LIMIT = 2**53
RISK_HARD = "..."; RISK_OVERFLOW = "..."; RISK_NOT_EVALUABLE = "..."   # the 7.7 texts, defined here
RISK_WORST = "..."; RISK_TAIL = "..."; RISK_REGRET = "..."; RISK_NON_CLAIM = "..."
RISK_GROWTH = "..."                                    # formatted into the certificate (O8)
UNFIELDABLE_PROVED = ceilings.UNFIELDABLE_PROVED       # one text, defined in ceilings.py

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
    # WORLD_LEAST: one record per kernel stage kernel.value ran for that world, from its
    # stage_statuses (Z, S1, S2 as run), and one NOT_RUN record for a call that ran no solve
    # (a deadline passed, stage_statuses ()); never the value status CERTIFIED
    purpose: str                   # WORLD_LEAST | SELECTION | MEMBERSHIP
    world_id: int | None
    player_id: int | None
    status: str                    # a 1.5 status; no objective value and no bound: those are encodings

@dataclass(frozen=True)
class MembershipRow:
    player_id: int
    possible: bool | None          # in some XI of the rule's level set
    necessary: bool | None         # in every XI of it

@dataclass(frozen=True)
class MembershipBlock:
    rows: tuple[MembershipRow, ...]     # player_id ascending; () when no selection exists
    # EXACT (also when vacuous) | LIMIT_REACHED | DEADLINE | MODEL_INVALID (1.5);
    # NOT_REQUESTED with analyze_ties=False (never served, 5.6 step 7)
    completeness: str

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
    solves: int                         # every CP-SAT call, kernel.value's stages included
    records: tuple[SolveRecord, ...]    # in call order; their statuses are the page's "statuses" (8.2)
    # WORST_WORLD and TAIL: RISK_GROWTH formatted with B and |U| (O8: the certificate says that
    # a worst case grows with B and records B); None for MINIMAX_REGRET
    growth: str | None
    completeness: str                   # EXACT | LIMIT_REACHED | DEADLINE | MODEL_INVALID (1.5)
    stopped_by: str | None

@dataclass(frozen=True)
class RiskSelection:
    rule: str                           # WORST_WORLD | TAIL | MINIMAX_REGRET
    tail_count: int | None              # k; 1 for WORST_WORLD; None for MINIMAX_REGRET
    status: str                         # CERTIFIED | UNFIELDABLE | NOT_EVALUABLE | UNKNOWN | MODEL_INVALID
    lineup: Lineup                      # the XI shown; () unless CERTIFIED
    world_losses: tuple[WorldLoss, ...] # every used world, ascending id, for the XI shown; () unless CERTIFIED
    tail_world_ids: tuple[int, ...]     # for the XI shown, in the key order of 5.2
    tail_boundary_ties: tuple[int, ...] # for the XI shown, ascending world id
    tail_sum: TailSums | None           # the rule's optimum (TAIL, WORST_WORLD)
    binding_world_ids: tuple[int, ...]  # for the XI shown (MINIMAX_REGRET), ascending world id
    point_loss: LossPair | None
    point_sums: tuple[tuple[str, float | None], ...]   # requirement_id ascending; None as 5.6; never printed as floats: the router adds exact texts (7.5)
    membership: MembershipBlock
    certificate: RiskCertificate
    # the rule's bare 7.7 label formatted by risk.py with B and k (RISK_TAIL.format(B=…, k=…)); no
    # "{" left. risk.py cannot know E-13's verdict or scope: the router adds the suffix (below)
    claim: str
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
                            # WORST_WORLD accepts tail_count None or 1; MINIMAX_REGRET only None
def world_losses(lineup: Lineup, candidates, requirements, formation, *, worlds,
                 locked=(), excluded=(), quantization=QUANTIZATION) -> tuple[WorldLoss, ...]
```

`world_count` must equal `len(worlds)` and, in the module, any positive integer is accepted so
that the oracle tests can use one to five worlds and the single-world invariant can be tested;
`tail_count` must lie in `1..world_count`. The menu (`TAIL_MENU` for the world counts the API
offers, `B = 12` until the 40-world timing of X5 (7.1), and `WORST_WORLD` for `k = 1`) is
enforced by the API. `world_seed` and `bootstrap_version` are
required keyword arguments with no default; the oracle tests pass constants of their own and
a test asserts both reach the certificate unchanged. `world_losses` is pure Python, an
independent re-evaluation helper (the oracle tests use it; E-13's audit reads its pairs from
the result through its own adapter, section 13). It applies the discard rule of 1.4 to
`worlds` and returns one `WorldLoss` per used world, ascending, with `world_least` `None`; the
`lineup` must be an XI of the used worlds under `locked` and `excluded` (every slot filled once,
every pair an admissible key, every locked player in, no excluded player), and anything else is
a `ValueError` with a fixed sentence that names no value. With `|U| = 0` it returns `()` after
checking that `lineup` is an XI under the candidates' own vectors. Every integer pair is also served in
normalised units by the router as text, exactly: `M / q` with `q = 100000` has at most five
decimals.

Labels until E-13 runs. The rule's label says what it computes (`RISK_WORST`, `RISK_TAIL`,
`RISK_REGRET`, section 7.7); `RiskSelection.claim` is that label alone, because `risk.py` is
given neither the verdict registry nor the scenario. The router serves as the envelope `claim`
`result.claim`, one space and exactly one suffix, and leaves `result.claim` as the tool
returned it (7.5): `RISK_OUTSIDE_E13` for a request outside `E13_SCOPE` (below), whatever the
registry says; otherwise `RISK_UNTESTED` ("E-13 has not tested this rule.") while
`verdicts.verdict_for("E-13", subject).basis` is not `EXECUTED`; otherwise no suffix, and the
envelope `claim` equals `result.claim`. Subjects are the E-13
draft's: `risk_rule:WORST_WORLD`, `risk_rule:TAIL`, `risk_rule:MINIMAX_REGRET`, and
`risk_report:WORST_WORLD`, `risk_report:TAIL` for the tail figures. Today each answers
`NOT_REGISTERED` and its badge reads RECORD ONLY · NOT TESTED with "No registered protocol tests
this claim." The subject of a reply is fixed by its rule (5.2): a `WORST_WORLD` reply carries
`risk_rule:WORST_WORLD`, a `TAIL` reply `risk_rule:TAIL`. Rules are never ordered or
preselected by token.

Scope of E-13's tokens. E-13 limits every token to its menu: "A request outside it (another
world count, another tail count, another formation or club) carries the pending sentence,
whatever the tokens say" (E-13 preregistration, Product consequence). Its config fixes formation
`4-3-3`, `decision_tiers` 12 and 40, the `tail_counts` per tier, the two Madrid snapshots
(config.json:116-119) and the requirement set in force, `expected_active_requirements`, the
three measured requirements (config.json:124), and its preregistration says it shows nothing
about "a requirement set ... that was not run". The risk requests accept `4-3-1-2` (7.2) and,
without the opt-in, progression alone (1.3). The router holds those values as constants,
`E13_SCOPE` (formation, world counts, tail counts, scenarios and the requirement set, so the
opt-in must be true), kept equal to the draft's config by a test, and a request outside them
(today: formation `4-3-1-2`, or no opt-in) is served, whatever the registry says: in
`verdicts.risk_rule` the subject's pending form when the subject is registered,

    verdicts.as_payload(verdicts.derive(dataclasses.replace(
        verdicts.record("E-13", subject), token=verdicts.PENDING,
        protocol_commit=None, results_hash=None)))

and the `verdict_for` payload while it is not (already an untested form); the envelope claim
ends with `RISK_OUTSIDE_E13` in place of `RISK_UNTESTED`. `dataclasses.replace` re-runs
`VerdictRecord.__post_init__`, and rule V3 requires a `PENDING` record to hold neither
`protocol_commit` nor `results_hash` (verdicts.py:193-199), so both are cleared with the token;
on a record that is still `PENDING` this is the same payload, and on an executed one it is
basis `REGISTERED_NOT_RUN`, badge "E-13 · RECORD ONLY · NOT RUN", E-13's `not_run_statement` as
its sentence, `protocol_verdict` null, `report` the preregistration, `figures` empty (`derive`
drops figures for a `PENDING` record) and `may_gate` false. Whether E-13's tokens may also hold
for a progression-only request is a reconciliation item for E-13's owner (section 13); until
it is settled, such a request is outside the scope.

`risk_report`. E-13's own statistic for `risk_report:*` is the largest shortfall `M` of the
worst world (WORST_WORLD) and the mean `M` over the `k` tail worlds (TAIL), in normalised units
(E-13 preregistration, Fixed definitions; PIPELINE.md:96-101, `own_m_sum / own_divisor`). This
file serves the tail sums `Σ M`, `k` times that mean, and no panel prints a figure note under
them. Until section 13's reconciliation item is settled, `verdicts.risk_report` is `null` on
every reply and no figure carries a `risk_report` payload, so E-13's sentence about its tail
value is never set beside a number it did not test.

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
| `t_bound(instance, worlds, *, excluded)` | B | `T_bound` of 5.1 written from its text (`L^w_r` over the keys with `Eligible(p, s)`, `p ∉ X` and every needed metric measured under `V^w`; `max` over used worlds of `Σ_r U^w_r`; 0 when `R` is empty; defined only when `|U| ≥ 1`), so the non-vacuity condition "some summed `T` over a tail exceeds `T_bound`" can be checked |
| `world_pairs(x, vectors)`, `tail_optimum(k)`, `regret_optimum()`, `tail_of(x, k)`, `binding_of(x)` | B | `(M^w, T^w)` over `used_worlds`; the lexicographic minimum over XIs of (sum of the `k` largest `M`, sum of `T` over the `k` lexicographically largest worlds); the per-world least pairs and the lexicographic minimum over XIs of the lexicographic maximum over worlds of `(M − M*, T − T*)`, each returning the optimum and every XI attaining it; and, for a given XI, its tail and boundary ties by the key of 5.2 and its binding worlds, so the tool's per-world reports are compared for the lineup the tool returned, never with a witness of the oracle's choosing |

Instances (`tests/xi_exact_oracle.instances(seed)`): 3 to 5 slots with mixed allowed
positions, 5 to 8 candidates, some with `eligible_slots`, some with zero minutes, 1 to 3
requirements with mixed `slot_ids`, some `None` values, 1 to 5 worlds with holes, locks and
exclusions, `q ∈ {100, 1000, 100000}`. CEILING and FRONTIER instances draw decimal values of
either sign. RISK and the `explain_solve` instances draw dyadic values and dyadic minima
(multiples of 1/64 in `[−2, 4]`, minima in `[0, 4]`) with normalisers in `{0.5, 1, 2, 4}`, for
which `int(round(v / n * q))` (written out in the test, not imported) equals the exact half-even
integer; the generator asserts it on every coefficient and on every target. A decimal minimum
can round differently (`1.344465 / 1.0` at 100000 is 134446 by `_q`, 134447 exactly) and would
make the oracle and the tool disagree for no defect. A separate test identifies the policy on a
non-dyadic value (section 9).

FRONTIER instances draw three requirements, so that `d = 2` and `d = 3` both exist on every
seed, and the dimensions are a seeded ordered sample of `R` of size `d`. The FRONTIER
oracle-equality tests assert, across the 120 seeds, that they are not vacuous: some `d = 3`
frontier with at least two points; some frontier with at least three points; some point reached
by XIs with different raw sums; some instance whose raw-nondominated set differs from its
integer-nondominated set; some point whose witness uses a negative coefficient; some floor that
binds; some `UNFIELDABLE` and some `NOT_SATISFIABLE`.

## 7. API: `galactico/api/xi_extensions.py`

### 7.1 Routes

| Method | Path | Budget route | Seconds | Long | Request | Tool |
|---|---|---|---|---|---|---|
| GET | `/api/xi/extensions` | none | | no | none | the menus (7.5), corpus-free |
| POST | `/api/xi/ceilings` | `xi.ceilings` | 10 | no | `CeilingsRequest` | `ceilings.requirement_ranges` |
| POST | `/api/xi/conflict` | `xi.conflict` | 15 | no | `ConflictRequest` | `explains: "solve"`: `conflict.explain_solve`; `explains: "floors"`: `conflict.explain_floors` (X2) |
| POST | `/api/xi/frontier` | `xi.frontier` | 30 | no | `FrontierRequest` | `frontier.nondominated_sums` |
| POST | `/api/xi/risk/tail` | `xi.risk.tail` | 60 | yes (X5, section 12) | `RiskTailRequest` | `rule: "WORST_WORLD"`: `risk.worst_world_selection`; `rule: "TAIL"`: `risk.tail_selection` |
| POST | `/api/xi/risk/regret` | `xi.risk.regret` | 150 | yes | `RiskRegretRequest` | `risk.minimax_regret_selection` |

The budgets are the ones `runtime.BUDGETS` already holds (runtime.py:133-148, pinned by
`tests/test_lab_runtime.py:116-125`); `xi.risk.regret` is already in `LONG_ROUTES`. No new
budget. `xi.split-sample` stays unused here (OPEN QUESTION 2; deferred to E-13 by X8). No path collides with
`decision_lab`'s five `/api/xi/*` routes. The router is
`APIRouter(route_class=decision_lab.DecisionRoute)`: a pydantic validation error never echoes
an input value, and the refusals of 7.2 are fixed sentences that name no id (the kernel's own
"unknown locked player IDs: [...]" never reaches a client, because `declare` checks ids
first).

Imports. Like the shipped lab routers, the router reads no data and imports no solver when it
is imported (player_lab.py:55-56): `ceilings`, `conflict`, `frontier`, `risk`, `squad.kernel`
and `optimization.snapshots` are imported only inside the functions that use them (handlers,
validators, the `GET`), never at module level. The router restates `EXPERIMENTAL_OPT_IN_ERROR`
as `planning` does (planning.py:175-176), `TAIL_MENU`, and every tool sentence of 7.7 it serves
by name, each kept equal to the tool module's object by a test (the pattern of
`tests/test_planning_api.py:149`); every other tool sentence reaches the reply as a field of the
tool's result. A subprocess test imports `galactico.api.xi_extensions` and asserts that no
`ortools` module, no `squad.kernel`, no `optimization.snapshots` and no tool module is loaded,
and that `_match_snapshot.cache_info().currsize == 0` (the pattern of
`tests/test_planning_api.py:136`).

`xi.risk.tail` enumerates every candidate for membership (5.6 step 7), which is what
`LONG_ROUTES` names ("every candidate"), so it joins that set and the pinned set of
`tests/test_lab_runtime.py:123` (X5). Both are shared files and the root makes the change
(section 12); a tail request then holds a long-job place, as a regret request does. The
`B = 40` option ships only after the TAIL and REGRET selection and membership solves are timed
at `q = 100000` on the Madrid worlds (X5; section 11, item 15; OPEN QUESTION 5): until then
the risk routes accept, and the `GET` reply offers, 12 worlds only (7.2, 7.5), and 40 joins the
menu in the change that records the times in ADR-0030. The measurement records wall time,
deterministic time and status per solve, and the peak memory (RSS) of the process, and nothing
else: no lineup, pair or selection is printed or kept, so it adds no prior exposure for E-13
(1.6).

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
    explains: Literal["solve", "floors"]              # required: which arithmetic (3.1, X2)
    mode: Literal["BALANCE", "SATISFY"] | None = None # required iff explains == "solve": the main solve's mode
    minimums: dict[RequirementId, Minimum] = {}       # the minima in force, as decision_inputs reads them;
                                                      # non-empty refused when explains == "floors" with a floors dict
    floors: dict[RequirementId, Minimum] | None = None  # explains == "floors" only. None: every requirement
                                                        # in force is a floor at its minimum; {}: no floor;
                                                        # refused when explains == "solve"

class FrontierRequest(XIDeclarations):
    dimensions: list[RequirementId] = Field(min_length=2, max_length=3)   # required, ordered
    floors: dict[RequirementId, Minimum] = {}
    max_points: int = Field(default=64, ge=1, le=64, strict=True)

class RiskTailRequest(XIDeclarations):
    # required: no default world count; Literal[12, 40] once the 40-world solves are timed (X5,
    # 7.1). INTEGER_ONLY because a Literal compares by equality and would read 12.0 as 12, and
    # Field(strict=True) cannot be applied to a Literal (pydantic 2.14 raises)
    bootstrap_worlds: Annotated[Literal[12], planning.INTEGER_ONLY]
    rule: Literal["WORST_WORLD", "TAIL"]            # required: no default rule
    tail_count: StrictInt | None = None             # TAIL: required, in TAIL_MENU[bootstrap_worlds]; WORST_WORLD: refused
    minimums: dict[RequirementId, Minimum] = {}

class RiskRegretRequest(XIDeclarations):
    bootstrap_worlds: Annotated[Literal[12], planning.INTEGER_ONLY]   # as RiskTailRequest (X5)
    minimums: dict[RequirementId, Minimum] = {}
```

A `model_validator(mode="after")` refuses, with its own sentence, a field that belongs to the
other branch (`floors` with `explains: "solve"`, `mode` with `explains: "floors"`, a
`tail_count` with `WORST_WORLD`, and a non-empty `minimums` with `explains: "floors"` and a
`floors` dict, because `explain_floors` then reads only the floors and the minima would change
nothing: sent and not used would be ignored silently), `explains: "solve"` without `mode`,
repeated dimensions, `TAIL` without a `tail_count`, and a `tail_count` outside the menu (1 is
not on the `TAIL` menu: that rule is `WORST_WORLD`). `minimums` with `explains: "solve"` and
`mode: "BALANCE"` are accepted, although a BALANCE explanation declares no floor: the page sends
the main solve's minima unchanged (8.2), they are declared rows of the reply (7.6), and the
served `CONFLICT_NO_MINIMUM` says that no minimum is a constraint under that rule. Then, at
declaration time, `ValueError` (422), each with a fixed sentence that names no value: a side
requirement named in `minimums`, `floors` or `dimensions` without the opt-in
(`EXPERIMENTAL_OPT_IN_ERROR`), so with the shipped requirement set every frontier request
without the opt-in is a 422; `explains: "solve"` without the opt-in
(`CONFLICT_SOLVE_NEEDS_OPT_IN`, 1.3); a lock or exclusion id that is not a gated candidate of
the scenario (`UNKNOWN_PLAYER`: "A locked or excluded player is not a candidate of this
decision point."). The risk overflow guard is a tool refusal, not a declaration-time one:
`risk.py` raises it (5.6 step 2) and `runtime.lab_errors` maps it to 422 with its sentence. Locks and exclusions are sorted and de-duplicated,
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
`planning.corpus_token(planning.FLAGSHIP)`: the names, sizes and modification times of the five
public tables `planning._corpus_files` lists for Spain (`actions`, `matches`, `lineups`, and the
provider-wide `players` and `teams`, storage/public.py:49), opened by nobody (ADR-0024); it
raises `FileNotFoundError` (a 503) when one is absent, and the API tests patch it as
`tests/test_squad_api.py` does. It is not exactly the set `load_snapshot` reads, and both
differences are accepted, as planning accepts them: `load_snapshot` does not read
`teams.parquet` (historical.py:281-287), so an absent teams file answers 503 on the new routes
while `/api/xi/solve` still answers; and it reads `data/public/pappalardo/MANIFEST.json` into
provenance (historical.py:229-233), which the token does not cover, so a manifest rewritten
alone leaves a stored reply's manifest in provenance stale until a frame file changes.

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
vectors only, historical.py:198-214). A consequence of keeping `decision_lab.snapshot` as it
is: after a corpus rewrite in a running server, the main solve above can still run on that
cache's older snapshot while these routes build a new one, so the conflict panel can explain a
model built from other files than the solve it sits under (it can even find that model
feasible). No served sentence can tell, because the router does not see the main reply; the
KNOWN_LIMITATIONS request of section 12 states it.

### 7.4 Declaring the problem

`declare(snap, request)`: first, every lock and exclusion id must be a gated candidate of the
snapshot (`UNKNOWN_PLAYER`, 7.2); then `decision_inputs(snap, formation, "BALANCE" |
request.mode, minimums)` (the shipped function, unchanged), then the opt-in rule of 1.3. Risk,
ceilings, frontier and `explains: "floors"` use `"BALANCE"` (no requirement is hard; floors
are separate declarations); conflict uses `request.mode` for `explains="solve"`.
For `explains: "floors"` with `floors` absent, the floors are `{r: r.minimum}` for every
`r ∈ R`, read from the requirements `decision_inputs` built from `minimums`. `declare` also
records each minimum's origin: entered (its id is in the request's `minimums`) or the snapshot's
default (`snap.requirement_minima`, which `decision_inputs` takes for a missing id,
decision_lab.py:293). The origin decides how a minimum, or a floor implied at it (`floors`
absent, or `explains: "solve"`), is printed (7.5) and whether it is a declared or a computed
ledger row (7.6). A floor taken from the request's own `floors` dict (CEILING, FRONTIER, or
`explains: "floors"` with a dict) has no such origin: it is the reader's floor, printed as
entered, whatever the `minimums`. The candidates are
the snapshot's gated players; the 900-minute gate and the omitted players are the snapshot's,
and the response names the omitted players beside the result (`snap.omitted`, the full
records, as `/api/xi/solve` serves them, decision_lab.py:429).

### 7.5 Response envelope

Every POST reply has every one of these keys, `null` where a key does not apply to the tool;
`result` is `dataclasses.asdict` of the tool's dataclass with the router's text fields added
beside the numbers.

| Key | Content |
|---|---|
| `tool` | `"xi.ceilings"`, `"xi.conflict"`, `"xi.frontier"`, `"xi.risk.tail"`, `"xi.risk.regret"` |
| `scenario_id`, `scenario` | the `SCENARIOS` entry |
| `formation`, `slots` | formation id; `[{slot_id, label}]` in formation order |
| `players` | `[{player_id, name, position}]` of the gated candidates; no rate is served here |
| `omitted_candidates` | `snap.omitted`, as `/api/xi/solve` serves it |
| `requirements_in_force` | `[{requirement_id, label, evidence_class, experimental}]`, `evidence_class` the domain name (O13) |
| `model_note` | on every reply: `MODEL_DIFFERS` formatted with the labels in force here and the labels the main XI Lab model holds (always the three of `decision_inputs`) whenever they differ, `null` when they are equal. It differs for CEILING and RISK without the opt-in, and for a CONFLICT reply with `explains: "floors"` and no opt-in; `explains: "solve"` requires the opt-in (1.3), and with the shipped requirement set every frontier request without it is a 422 (7.2), so it never differs on those |
| `declared` | the declared rows (7.6) |
| `result` | the tool's dataclass, plus text fields (below) |
| `ledger` | the computed rows (7.6) |
| `evidence` | `shell.evidence_payload` of the whole result |
| `verdicts` | on every reply: `{"risk_rule": …, "risk_report": null}` for RISK (5.7: the in-scope or pending payload of the rule's subject; `risk_report` stays `null` until section 13 settles it), `null` for CEILING, CONFLICT and FRONTIER |
| `claim`, `non_claim` | the result's `claim` and `non_claim` (the constants the tool's state selects: CEILING by the 2.2 table, CONFLICT by the 3.4 table, FRONTIER its one constant, 7.7; for RISK the formatted label); for RISK the envelope `claim` is `result.claim`, one space and the suffix 5.7 chooses (`RISK_OUTSIDE_E13`, `RISK_UNTESTED`, or none), and `result.claim` itself is left as the tool returned it. The router never substitutes a constant by name |
| `statements` | the reply-level sentences of 7.7, formatted by the router, in the order of the table below |
| `budget` | `budget.report(result completeness)` |
| `provenance` | `{"providers": ["pappalardo"], "snapshot": scrub_lineage(snap.provenance), "tool": result.provenance}`; `tool` holds the version, `input_contract` (`kernel.input_contract` plus the declarations), `input_fingerprint`, `source_fingerprints`, and keys under the reserved prefixes `ceiling_`, `conflict_`, `frontier_`, `risk_` (kernel.py:115-127), the solve-time lists of 1.5 among them |

`statements`, per tool and state (a constant whose condition fails is absent; none is
repeated):

| Tool | Statements, in order |
|---|---|
| CEILING | `FLOORS_SCOPE` when `floors` is non-empty; `CEILING_EXACT_FACTS` when any range is reported; `NOT_SATISFIABLE`: `FLOORS_CONSERVATIVE`; `FLOORS_UNMET`: `FLOORS_CONSERVATIVE`, `FLOORS_CAUSE_UNDECIDED`. `MODEL_INVALID` adds none: its claim is `CEILING_REFUSED` (2.2) |
| CONFLICT | one arithmetic sentence, chosen by `explains` and by whether `result.declarations` (every declaration, never `result.conflict`) holds a `REQUIREMENT_FLOOR`: `explains: "solve"` with one (every SATISFY explanation): `CONFLICT_HALF_EVEN`; `explains: "solve"` without one (a BALANCE explanation): `CONFLICT_NO_MINIMUM`; `explains: "floors"` with one (`floors` absent, or non-empty): `CONFLICT_CONSERVATIVE`; `explains: "floors"` without one (`floors: {}`): `CONFLICT_NO_FLOOR`. `CONFLICT_NO_MINIMUM` is never served on `explains: "floors"`, which carries no main-solve mode, and `CONFLICT_NO_FLOOR` never on `explains: "solve"` |
| FRONTIER | `FLOORS_SCOPE` when `floors` is non-empty; the status sentence `status_text` (below; on `MODEL_INVALID` it is `SOLVER_REFUSED`, served once); `FRONTIER_WITNESS` when at least one point is listed; `NOT_SATISFIABLE`: `FLOORS_CONSERVATIVE`; `FLOORS_UNMET`: `FLOORS_CONSERVATIVE`, `FLOORS_CAUSE_UNDECIDED` |
| RISK | `RISK_BALANCE`; `RISK_WITNESS` when `CERTIFIED`; `RISK_DISCARDED` when a world was discarded; `RISK_SAME_DRAW` (`B = 12`) or `RISK_PREFIX` (`B = 40`, while the prefix test passes); `RISK_NOT_EVALUABLE` when `NOT_EVALUABLE`; `SOLVER_REFUSED` when `MODEL_INVALID`. `RISK_GROWTH` is not a statement: it is the certificate's `growth` field (5.2, 5.7), printed in the certificate block |

Text fields the router adds (the page prints them and computes nothing; every number the page
shows is one of these or a number field on the allow-list of 8.3 printed as is). Every table the
page prints is a row list the router serves in print order, so the page never picks entries out
of other lists by id (8.3). The builders of these texts are pure functions of the declared
candidates, requirements, formation and the tool's result, so a case no route can pose (every
requirement the router builds applies to the ten outfield slots, decision_lab.py:290-303) is
tested on them directly (section 9).

- Printed minima, one rule for every tool: a minimum the reader entered is printed as entered
  (`domain.precision.format_plain`); a minimum read off the record (the snapshot's default) is
  printed as `planning._minimum_text` prints one, `_APPROXIMATE` (`"≈ "`) then
  `_DERIVED_PLACES` (four) decimals. The origin is the one `declare` records (7.4).
- CEILING, per range: `largest.attained_text` (the witness's exact sum rounded down,
  `planning._outward`, four decimals), `largest.bound_text` (rounded up), `least.attained_text`
  (up), `least.bound_text` (down); a bound that is `None` (2.3 step 7) has `bound_text` `null`.
  A bound text is computed from the exact `Fraction`, never from the float `raw_bound` (several
  float operations and one `nextafter` step, which need not land on the outward side of a
  four-decimal grid point): `_outward(Fraction(n_r) · (2 · integer_bound + a_r) / (2q), up=True)`
  for LARGEST and `_outward(Fraction(n_r) · (2 · integer_bound − a_r) / (2q), up=False)` for
  LEAST.
  `minimum_text` by the rule above; the two minimum statements, a True fact printing the
  deciding witness's sum (`minimum_reached_witness`: rounded down; `minimum_missed_witness`:
  rounded up), and the bound-based sentences formatted with `{xi}` (7.7); and `evidence` (7.6).
  The router recomputes `S_r(lineup)` in `Fraction` from the declared candidates' values before
  calling `_outward`; it never floors the float `attained`, which can lie on the other side of a
  four-decimal boundary.
- CONFLICT: per declaration `label_text` ("Slot coverage: Left back", "Exclusion: {name}",
  "Lock: {name}", and for a floor: "Floor on {label}: {φ}" for a floor from the request's
  `floors` dict, printed as entered (`format_plain`), whatever the `minimums`; for a floor
  implied at a minimum, "Floor on {label}: {minimum}" with the minimum printed by the rule
  above when it was entered, or "Floor on {label}: its default minimum, the median prior
  starting-XI sum ({minimum})" for a default, 7.4). `member_rows`, in deletion order, one per
  member of `conflict`: `{constraint_id, family, label_text, member_text, restore_text,
  assignment_rows, missing_locked_text, restore_rows}`, where `member_text` is
  `CONFLICT_MEMBER_WITNESS` for `KEPT_WITNESS`, `CONFLICT_MEMBER_REFUSED` for `KEPT_REFUSED` and
  `CONFLICT_MEMBER_UNDECIDED` for `KEPT_UNDECIDED` and `NOT_RUN`; `restore_text` is the restore
  test's sentence (7.7): `CONFLICT_RESTORES_YES`, `_NO`, `_SLOT` (`NOT_APPLICABLE`),
  `_REFUSED` (status `MODEL_INVALID`) or `_UNDECIDED` (`UNKNOWN`, `NOT_RUN`); a member that is
  not `KEPT_WITNESS` has `assignment_rows = []` and `missing_locked_text = null`;
  `assignment_rows` is `[{slot_label, player_text, note_text}]` in formation
  order, `player_text` the name or "empty", `note_text` "Excluded by you; that exclusion is set
  aside in this check" for an excluded player the witness uses, else `null`;
  `missing_locked_text` is `CONFLICT_LOCK_SET_ASIDE` with the names of the locked players the
  witness leaves out, or `null`; `restore_rows` is the restore XI as `[{slot_label,
  player_text}]`, or `[]`. Also the arithmetic sentence (in `statements`) and the deletion order.
- FRONTIER, per point, three columns in one unit, club medians (the requirement's normaliser,
  the club's median prior starting-XI sum): `point_texts`, the certified coordinates, each
  `V_i / q` printed exactly with five decimals (`q = 100000`), labelled "rounded sum, in club
  medians"; two distinct points never print the same texts. `raw_sum_texts`, for each dimension
  `S_{r_i}(witness) / n_i`, computed in `Fraction` from the declared candidates' values and
  `Fraction(n_i)` of the same float normaliser the tool used (never from the float `raw_sums`),
  printed at five decimals rounded down, labelled "one XI reaching it sums to, before rounding,
  in club medians". `allowance_texts`, `a_{r_i} / (2q)` computed in `Fraction` from `a_r` and `q`
  and printed at five decimals rounded up (0.00005 for the ten outfield slots every formation of
  `decision_inputs` has), labelled "allowance, in club medians"; never derived from the float
  `raw_rounding_error_bounds`, which keep their per-90 meaning and are not printed, as
  `quantized_sums` and `raw_sums` are not. On the printed texts, `|raw − point| ≤ allowance`
  holds exactly: the point and the rounded-up allowance lie on the five-decimal grid, and
  rounding down never crosses a grid point below the true value. `lineup_rows`,
  `[{slot_label, player_text}]` in formation order. When `d = 2`: `plot_x = (V_1 − min V_1) /
  (max V_1 − min V_1)` and `plot_y = 1 − (V_2 − min V_2) / (max V_2 − min V_2)` over the listed
  points in `Fraction`, served as decimal strings with six places, rounded half-even from the
  exact `Fraction`, `0.5` when a range is zero; `plot_y` is already in SVG orientation (larger
  sums higher on screen), for a fixed `viewBox="-0.05 -0.05 1.1 1.1"`. Per reply, `status_text`:
  `FRONTIER_COMPLETE` iff the status is `FRONTIER` and the completeness `COMPLETE`;
  `FRONTIER_LIMIT` iff `stopped_by` is `POINT_LIMIT`, with `{n}` = `max_points`;
  `FRONTIER_STOPPED` for `INCOMPLETE` otherwise (a deterministic limit or the wall clock), with
  `{n}` = the number of points listed when it is at least 1, and `FRONTIER_STOPPED_NONE`, never
  `FRONTIER_STOPPED` with `{n}` = 0, when no point is listed; `SOLVER_REFUSED` for
  `MODEL_INVALID`; `null` for
  `UNFIELDABLE`, `NOT_SATISFIABLE` and `FLOORS_UNMET`. A `LIMIT_REACHED` from the deterministic
  limit never serves `FRONTIER_LIMIT`, which would claim a point limit was reached and another
  point proved.
- RISK: every pair as `maximum_shortfall_text`, `total_shortfall_text` (exact decimals of
  `M / q`, `T / q`); the tail sums as `summed_maximum_shortfall_text`,
  `summed_total_shortfall_text`; `boundary_ties_text` ("Worlds outside the tail with the same
  pair as its last world: 3, 7." or "None."); `point_sum_texts` (exact sums rounded down at four
  decimals, `null` for a `None` sum) and the point pair's texts; the rule label;
  `world_count_text` ("12 worlds, 11 used"). Row lists: `lineup_rows` `[{slot_label,
  player_text}]` in formation order; `tail_rows` `[{world_id, maximum_shortfall_text,
  total_shortfall_text}]` in the tail's key order; `boundary_rows`, the same shape, ascending
  world id; `binding_rows` `[{world_id, selected_texts, least_texts}]`, ascending world id, each
  holding both pairs and never a difference (O8); `world_rows`, every used world in ascending id
  with its pair and, for REGRET, the world's least pair. The membership block as
  `membership.groups`, a list in the fixed order below, each
  `{heading, rows}` with the rows in `player_id` order and every `(possible, necessary)`
  combination that can occur in exactly one group: `(True, True)` "In every XI this rule
  selects"; `(True, False)` "In some XIs this rule selects, not in all"; `(True, None)` "In some
  XIs this rule selects; whether in all was not decided"; `(None, False)` "Not in every XI this
  rule selects; whether in some was not decided"; `(False, False)` "In no XI this rule
  selects". The two undecided headings name no cause, because a membership solve that is
  `MODEL_INVALID` leaves `None` as an undecided one does (5.6 step 7), and the block's
  completeness says which. A player in the XI shown is possible, and one
  outside it is not necessary (that XI is a selection without him), so no other combination
  occurs; a test asserts it.

No key is `total`, `index`, `score`, `rank` or holds a part of `thesis.BANNED_KEY_PARTS`;
`finalize` refuses otherwise.

`GET /api/xi/extensions` returns, through `finalize`: `world_counts` `[12]`; `tail_counts`
`{"12": [2, 3, 6]}` (40 and its counts `[4, 10, 20]` join both only once the 40-world solves are
timed, X5, 7.1); `rule_options` per world count, in the
fixed order of `RULES`, each `{rule, tail_count, text}` with server text: one `WORST_WORLD`
entry with `tail_count` 1 ("Worst world of 12: the extreme of the tail rule"), one `TAIL` entry
per menu count ("Tail: 3 highest-loss worlds of 12"), one `MINIMAX_REGRET` entry ("Least
largest regret over 12 worlds"); no `TAIL` entry has `tail_count` 1. `requirements`
`[{requirement_id, label, experimental}]` for the three measured requirements, the source of
every requirement select and of the page's minima filter. No shared constant holds them: the
labels are a dict local to `decision_inputs` and its evidence class is chosen inline
(decision_lab.py:282-286, 304), and `decision_lab.py` is root-owned and unchanged, while a
corpus-free `GET` cannot call `decision_inputs`. The router therefore holds its own copy of the
three requirements, each with its id, label, metric and experimental flag, kept equal to
`decision_inputs` by a test on a synthetic snapshot that compares id, label and metric field by
field and the flag with `evidence_class == "RESEARCH"`; the `GET` serves id, label and flag.
`experimental_requirements` `["left_pass_origins", "right_pass_origins"]` (a test asserts these
are exactly the `RESEARCH` requirements of `decision_inputs`); `dimension_counts` `[2, 3]`;
`max_frontier_points` 64; `opt_in_label` (`OPT_IN_LABEL`); `frontier_opt_in_text`
(`FRONTIER_OPT_IN`, which the page prints before any POST); `side_minima_text`
(`SIDE_MINIMA_SET_ASIDE`); `provenance.providers`.

### 7.6 The ledger (O12) and evidence (O13)

Declared rows, `shell.declared_row`, are a function of the resolved request (the
`model_dump` the cache key hashes), never of which fields were sent, so one key always has one
ledger (the rule of `planning.declared_rows`, planning.py:1249-1263): always the decision
point and the role-slot template; then each lock and exclusion (by name); each minimum and
floor in the request's dicts, as entered (`domain.precision.format_plain`); the dimensions in
order and the point limit ("Point limit: 64", always, because `max_points` changes the answer
and is in the cache key); for CONFLICT, the arithmetic ("Arithmetic: half-even, as the solve
above" for `explains: "solve"`, whatever its mode, with the certificate token
`SOLVE_HALF_EVEN`; "Arithmetic: conservative, as a hard-floor query" for `explains: "floors"`),
for `explains: "solve"` the decision rule explained ("Decision rule explained: Satisfy all
minima" or "…: Balance shortfalls", from `mode`, which decides whether the minima are floors),
and for `explains: "floors"` the floors declared ("Floors: every requirement in force at its
minimum" when `floors` is absent, "Floors: none" when it is `{}`, and a non-empty dict as its
floor rows above), so a request with floors implied at every minimum and one with none never
share a declared ledger; the experimental opt-in only when true; the world count and the risk
rule ("Tail 3 of 12 worlds", "Worst world of 12"). A default minimum that is not in the
request's `minimums` is not a declared row: it appears as a computed row.

Computed rows, `shell.ledger_row`, each conditional on the declared rows. `ledger_row` raises
`TypeError` on an empty `row_id` or `sample` (shell.py:256-306), which `lab_errors` does not map,
so every field is fixed here for every terminal state; `value_text` is `None` wherever no number
exists, and the row then stays and is never drawn as zero. `POINT_SAMPLE` is the router's fixed
sentence "Prior per-90 rates of the gated squad before the cutoff; one value per player." and
`world_count_text` is the RISK text of 7.5.

| Tool | `row_id` | `quantity` | `value_text` | `sample` | `verdict` |
|---|---|---|---|---|---|
| all | `default-minimum-{r}`, per requirement in force whose minimum was not entered | "Default minimum of {label}"; on FRONTIER, which compares no minimum, "Club median of {label}, the unit of these sums" | the minimum printed by the 7.5 rule ("≈ " and four decimals) | "Median of the club's prior starting-XI sums of this requirement." | `None` (class `HEURISTIC`) |
| CEILING | `ceiling-{r}-largest` and `ceiling-{r}-least`, per range | "Largest sum of {label}", "Least sum of {label}" | "at least {attained}; no {xi} above {bound}" and "at most {attained}; no {xi} below {bound}"; with no finite bound, "at least {attained}" or "at most {attained}"; `None` for a `NO_SOLUTION` end. No row when no range is reported (`UNFIELDABLE`, `NOT_SATISFIABLE`, `FLOORS_UNMET`, `MODEL_INVALID`): the panel prints the state's sentence | `POINT_SAMPLE` | `None` |
| CONFLICT | `conflict-set` | "Declarations that cannot hold together" | "{n} declarations" for `MINIMAL_CERTIFIED` and `NOT_PROVEN_MINIMAL`; "0 declarations" for `MODEL_FEASIBLE`; `None` for `UNDECIDED` and `MODEL_INVALID`, never 0 | `POINT_SAMPLE` | `None` |
| FRONTIER | `frontier-points` | "Nondominated rounded sums of {labels}" | by status and the number `n` of listed points: `FRONTIER` (always `COMPLETE`): "{n} points", "1 point" when `n = 1`; `INCOMPLETE` or `MODEL_INVALID` with `n ≥ 1`: "{n} points listed; the list is not complete", "1 point listed; the list is not complete" when `n = 1`; "0 points" for `UNFIELDABLE` and `NOT_SATISFIABLE` only, whose empty set is proved; `None` for `FLOORS_UNMET` and for `INCOMPLETE` or `MODEL_INVALID` with `n = 0`, never 0: "0 points" is served only where the empty set is proved | `POINT_SAMPLE` | `None` |
| RISK, TAIL and WORST_WORLD | `risk-tail-sums` | "Tail sums" | "summed largest shortfall {ΣM}; summed shortfall {ΣT}" when `CERTIFIED`, else `None` | `world_count_text` | the payload of `verdicts.risk_rule` (5.7) |
| RISK, MINIMAX_REGRET | `risk-binding-worlds` | "Binding worlds of the XI shown" | "world {id}: this XI ({M}, {T}); least any XI reaches there ({M*}, {T*})" per binding world, both pairs and never a difference (O8), when `CERTIFIED`, else `None` | `world_count_text` | the payload of `verdicts.risk_rule` |
| RISK, every rule | `risk-worlds` | "Resampled worlds" | `world_count_text` | `RISK_SAME_DRAW` or `RISK_PREFIX` as served, else "Drawn from the prior matches with the snapshot's seed." | the payload of `verdicts.risk_rule` |
| RISK, every rule | `risk-discarded` | "Worlds set aside" | "{d} of {B}" | `RISK_DISCARDED` when `d > 0`, else "No world was set aside." | the payload of `verdicts.risk_rule` |

Row ids use hyphens, never colons: the kit prints `data-ledger` only for a plain word
(`[A-Za-z0-9_-]+`, labs-shared.js:55, 191), as the shipped ids (`minimum-progression`,
`reference-progression`, `audit-depth`) do; a requirement id keeps its underscores.

`solver` is `"{status} · {certification or completeness} · 1/100000"` on every computed row but
the default-minimum row, whose `solver` is `None` (a record). `verdict` is `None` for CEILING,
CONFLICT and FRONTIER (exact computation, no empirical claim: the kit prints "Exact
computation · no empirical claim"). An API test builds every terminal state of every tool and
passes each row through `shell.ledger_row`.

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
or raises are defined in that tool's module, because an optimisation module does not import
the API layer: every `claim` and `non_claim` (`CEILING_CLAIM`, `CEILING_PARTIAL_CLAIM`,
`CEILING_NOT_DECIDED`, `CEILING_EMPTY`, `CEILING_REFUSED`, `CEILING_NON_CLAIM`, the CONFLICT
claims and `CONFLICT_NON_CLAIM`, `FRONTIER_CLAIM`, `FRONTIER_NON_CLAIM`, the RISK labels and
`RISK_NON_CLAIM`), `UNFIELDABLE_PROVED`, `FLOORS_CONSERVATIVE`, `RISK_HARD`, `RISK_OVERFLOW`,
`RISK_NOT_EVALUABLE` and `RISK_GROWTH`. `UNFIELDABLE_PROVED` and `FLOORS_CONSERVATIVE` are
defined once, in `ceilings.py`, and re-exported by `frontier.py` (and `UNFIELDABLE_PROVED` by
`risk.py`); a test asserts the copies are the same text. The router restates the ones it serves
by name, with an equality test, and defines the rest (7.1, "Imports"). A tool's `claim` and
`non_claim` fields hold the constant of this table that its state selects (CEILING: the 2.2
table; CONFLICT: the 3.4 table; FRONTIER: its one constant, true on every status), word for
word, formatted only where the constant has placeholders (the RISK labels, by `risk.py`, 5.7;
the router adds the RISK suffix to the envelope claim, 7.5); the design notes in sections
2 to 5 are never served (two of them name words the copy guard refuses, by design). A unit test
per tool asserts `scan_labels(asdict(result))` is empty. No shipped warning of `solve_xi` or
`maximize_requirement` is served outside provenance: several fail the guard.

| Constant | Text |
|---|---|
| `CEILING_CLAIM` (`FIELDABLE`, every end with a witness and a finite bound, 2.2) | For each requirement in force, two intervals over the XIs that the eligibility rules, missing measurements, locks, exclusions and declared hard floors allow, each floor compared conservatively: the largest sum any of these XIs reaches lies in the first, the least in the second. One end of each interval is the exact sum of one XI the search found, printed rounded outward to four decimals; that XI need not reach the largest or the least sum itself. The other end is a bound no such XI passes: the search adds each prior per-90 rate rounded half-even to 1/100000 of the club median, and the bound is the limit the search proved on that rounded sum, widened by its rounding allowance and printed rounded outward. |
| `CEILING_PARTIAL_CLAIM` (`FIELDABLE`, some end without a witness or without a finite bound) | For each requirement in force, the largest and the least sum over the XIs that the eligibility rules, missing measurements, locks, exclusions and declared hard floors allow, each floor compared conservatively, are bracketed only on the sides the search settled. Where a cell shows a sum, it is the exact sum of one XI the search found, printed rounded outward to four decimals; that XI need not reach the largest or the least sum itself. Where a cell shows a bound, no such XI passes it: the search adds each prior per-90 rate rounded half-even to 1/100000 of the club median, and the bound is the limit the search proved on that rounded sum, widened by its rounding allowance and printed rounded outward. A cell marked not certified implies nothing. |
| `CEILING_NOT_DECIDED` (`UNKNOWN`) | Whether any XI that the eligibility rules, missing measurements, locks, exclusions and declared hard floors allow exists was not decided within the search limits. No range is implied. |
| `CEILING_EMPTY` (`UNFIELDABLE`, `NOT_SATISFIABLE`, `FLOORS_UNMET`) | No XI that the eligibility rules, missing measurements, locks, exclusions and declared hard floors allow exists, each floor compared conservatively, so there is no range to report. |
| `CEILING_NON_CLAIM` | Each range is taken for one requirement alone, over the XIs the eligibility rules, missing measurements, locks, exclusions and declared hard floors allow, each floor compared conservatively: reaching two minima at once is a different question. A sum is arithmetic on prior rates, not a forecast of what an XI would produce. |
| `CEILING_REACHED` / `_UNREACHABLE` | One XI reaches the minimum of {label} ({minimum}): it sums to at least {attained}, its sum rounded down to four decimals. / No {xi} reaches the minimum of {label} ({minimum}): none sums to more than {bound}, a bound rounded up to four decimals. |
| `CEILING_MISSED` / `_EVERY` | One XI stays below the minimum of {label} ({minimum}): it sums to at most {attained}, its sum rounded up to four decimals. / Every {xi} reaches the minimum of {label} ({minimum}): none sums to less than {bound}, a bound rounded down to four decimals. |
| `{xi}` (a format argument of `_UNREACHABLE`, `_EVERY`, `FRONTIER_COMPLETE` and the CEILING ledger rows, 7.6) | "XI" when `floors` is empty; "XI that meets your floors in the conservative comparison" when it is not (2.1) |
| `CEILING_EXACT_FACTS` | These minimum statements compare exact sums with each minimum. The solve above first rounds each rate and each minimum half-even to 1/100000 of the club median, so when a sum and a minimum differ by no more than half of that unit for each place counted plus half of it for the minimum, the solve above can find a shortfall where these statements find none, or none where they find one. |
| `CEILING_REACHED_ALLOWANCE` (the LARGEST end `QUANTIZED_OPTIMAL` only, 2.1) / `_NOT_CERTIFIED` (any other LARGEST end) | Whether an XI reaches the minimum of {label} ({minimum}) is not settled: it lies inside the rounding allowance of the search. / Whether an XI reaches the minimum of {label} ({minimum}) is not settled: the largest end was not certified within the search limits. |
| `CEILING_MISSED_ALLOWANCE` (the LEAST end `QUANTIZED_OPTIMAL` only) / `_NOT_CERTIFIED` (any other LEAST end) | Whether every XI reaches the minimum of {label} ({minimum}) is not settled: it lies inside the rounding allowance of the search. / Whether every XI reaches the minimum of {label} ({minimum}) is not settled: the least end was not certified within the search limits. |
| `CEILING_NOT_CERTIFIED` | This end of the range was not certified within the search limits. No value is implied. |
| `CEILING_REFUSED` (`MODEL_INVALID`, as the claim) | The solver refused the model, so no range is reported. No value is implied. |
| `UNFIELDABLE_PROVED` (a reason, CEILING, FRONTIER, RISK; defined in `ceilings.py`) | No XI satisfies the combined eligibility rules, missing measurements, locks and exclusions. |
| `FLOORS_CONSERVATIVE` | No XI meets the declared floors in the conservative comparison: each rate rounded down and each floor rounded up to 1/100000 of the club median, so an XI that meets a floor with less than that unit times one more than the number of places counted to spare can be excluded. |
| `FLOORS_SCOPE` | Your floors are compared conservatively: each rate rounded down and each floor rounded up to 1/100000 of the club median, so an XI that meets a floor with less than that unit times one more than the number of places counted to spare can be left out of every range and point here. |
| `FLOORS_CAUSE_UNDECIDED` | Whether any XI exists without the floors was not decided within the search limits. |
| `CONFLICT_CLAIM` (`MINIMAL_CERTIFIED`) | These declarations cannot all hold together. Leave out any one of them and the others in this set can hold together, with every declaration outside the set also set aside. That check leaves out the other declarations: dropping one of these alone may still leave no XI, and each one says whether it does. This is one such set: when more than one exists, checking in another order can return another, and this one was not chosen to be the smallest by count. |
| `CONFLICT_NOT_PROVEN_CLAIM` (`NOT_PROVEN_MINIMAL`) | These declarations cannot all hold together. For a member shown with an assignment, leaving it out lets the others in this set hold together, with every declaration outside the set also set aside; for at least one member that was not decided within the search limits, or the solver refused the check, so this set may not be minimal. Dropping one of these alone, with the other declarations kept, may still leave no XI, and each one says whether it does. |
| `CONFLICT_NOT_DECIDED` (`UNDECIDED`) | Whether these declarations can all hold together was not decided within the search limits. No set is implied. |
| `CONFLICT_MODEL_INVALID` (`MODEL_INVALID`: the initial test only, 3.4) | The solver refused the model of these declarations, so whether they can all hold together was not decided. No set is implied. |
| `CONFLICT_NON_CLAIM` | Eligibility rules, the minutes gate and missing measurements are part of the model and are never offered for removal. Nothing was relaxed in the solve this explains. |
| `CONFLICT_HALF_EVEN` | Minima are compared as the Satisfy rule compares them: each rate and each minimum rounded half-even to 1/100000 of the club median. |
| `CONFLICT_CONSERVATIVE` | Floors are compared conservatively: each rate rounded down and each floor rounded up to 1/100000 of the club median, so an XI that meets a floor with less than that unit times one more than the number of places counted to spare can be excluded. |
| `CONFLICT_NO_MINIMUM` (`explains: "solve"` only) | No minimum is part of this question: under the decision rule of the solve above no minimum is a constraint, so only places, exclusions and locks are checked. |
| `CONFLICT_NO_FLOOR` (`explains: "floors"` only) | No floor is part of this question, so only places, exclusions and locks are checked. |
| `CONFLICT_MEMBER_WITNESS` | Leave this declaration out, set aside every declaration outside this set, and the others in this set can hold together. One assignment is shown; it is only required to meet those, so a place can be empty, a player you excluded can appear, a player you locked can be missing, and a floor outside this set can be unmet. |
| `CONFLICT_LOCK_SET_ASIDE` | Locked by you and not in this assignment: {names}. That lock is set aside in this check. |
| `CONFLICT_MEMBER_UNDECIDED` (`KEPT_UNDECIDED`, `NOT_RUN`) | Leaving this declaration out was not decided within the search limits. The set still cannot hold together, but it may not be minimal. |
| `CONFLICT_MEMBER_REFUSED` (`KEPT_REFUSED`) | The solver refused the check of leaving this declaration out. The set still cannot hold together, but it may not be minimal. |
| `CONFLICT_RESTORES_YES` / `_NO` | Dropping only this declaration, with all the other declarations kept, leaves at least one XI. One is shown. / Dropping only this declaration, with all the other declarations kept, still leaves no XI: another conflict remains. |
| `CONFLICT_RESTORES_UNDECIDED` / `_SLOT` | Whether dropping only this declaration leaves an XI was not decided within the search limits. / An XI fills every place, so leaving this one empty is not a way to field one. |
| `CONFLICT_RESTORES_REFUSED` (restore status `MODEL_INVALID`) | Whether dropping only this declaration leaves an XI was not decided: the solver refused that check. |
| `CONFLICT_FEASIBLE` (`MODEL_FEASIBLE`, as the claim) | Every declaration holds in at least one XI, so there is nothing to explain; one such XI is shown. |
| `CONFLICT_SOLVE_NEEDS_OPT_IN` | The solve above holds the two EXPERIMENTAL side pass-origin requirements; explaining it needs the experimental opt-in. |
| `FRONTIER_CLAIM` (every status; it states no completeness, which `status_text` states) | Each point listed is a combination of rounded sums of the declared requirements that some XI reaches and that no XI's rounded sums match or exceed on all of them while exceeding it on one, shown with one XI that reaches it. Whether the list holds every such combination is stated with it. The XIs are those the eligibility rules, missing measurements of any requirement in force, locks, exclusions and declared hard floors allow, each floor compared conservatively. A rounded sum adds each prior per-90 rate as a multiple of the club median, rounded half-even to 1/100000, and is printed exactly. Beside each point, the sums of one XI reaching it before rounding, in the same unit and rounded down; they differ from the point by no more than the allowance shown. |
| `FRONTIER_NON_CLAIM` | Not a ranking: no point is preferred, and the list follows the order in which you declared the requirements. A point says nothing about requirements you did not declare, and a sum is arithmetic on prior rates, not a forecast. |
| `FRONTIER_COMPLETE` | Complete: a final solve proved that the rounded sums of every {xi} are no more than one of these points on every declared requirement. |
| `FRONTIER_LIMIT` / `_STOPPED` | The limit of {n} points was reached and another point exists. The list is not complete. The points listed come first in the declared order; another order can list others. / The search stopped after {n} points. Each listed point is certified; other points may exist. The points listed come first in the declared order; another order may list others. |
| `FRONTIER_STOPPED_NONE` (`INCOMPLETE` with no point) | The search stopped before any point was certified, so no point is listed; which points there are was not decided within the search limits. |
| `FRONTIER_WITNESS` (when a point is listed) | Another XI can reach the same point with other sums before rounding; which XI is shown is the search's choice and can change with the declared order. |
| `SOLVER_REFUSED` (FRONTIER, RISK) | The solver refused the model at one step, so this answer is not complete. Anything shown was certified before that step; nothing else is implied. |
| `FRONTIER_OPT_IN` | With the requirements this XI Lab model holds, two or more declared sums need the two EXPERIMENTAL side pass-origin requirements, which enter only through the experimental opt-in. |
| `RISK_WORST` | Worst world of {B}, the extreme of the tail rule for these {B} worlds (a tail of one world): an XI whose single highest-loss resampled world is least, comparing the largest shortfall first and then the summed shortfall. |
| `RISK_TAIL` | Tail {k} of {B}: an XI whose {k} highest-loss resampled worlds have the least summed loss, comparing summed largest shortfalls first and then summed shortfalls. |
| `RISK_REGRET` | Least largest regret over {B} worlds: in each resampled world an XI's largest and summed shortfalls are set against the least pair any XI reaches there, and an XI whose largest gap is least is chosen. |
| `RISK_WITNESS` | The worlds listed are those of the XI shown. Another XI this rule selects reaches the same value and can have other highest-loss or binding worlds. |
| `RISK_BALANCE` | This rule compares shortfalls whatever the decision rule of the solve above: a Satisfy minimum is not a constraint here. |
| `RISK_UNTESTED` | E-13 has not tested this rule. |
| `RISK_OUTSIDE_E13` | E-13 does not test this rule on this request: its formation, requirement set, world count, tail count or match lies outside what E-13 tests. |
| `RISK_GROWTH` (the certificate's `growth`, WORST_WORLD and TAIL; defined in `risk.py`) | A worst case or a tail sum over resampled worlds can only grow as worlds are added. This request draws {B} worlds, of which {U} could be used. |
| `RISK_NON_CLAIM` | Stability against resampling of the historical matches; not robustness to opponents, absences or form, and not a forecast. |
| `RISK_DISCARDED` | {d} of {B} worlds were set aside: in each, a player who can be selected has no value in that world for a requirement in force here ({labels}) at a place he is eligible for: he has no recorded minutes in that world's resampled matches, or no value at all. The main solve's resampling sets worlds aside by this rule over its own requirements. |
| `RISK_SAME_DRAW` (`B = 12`) | These are drawn by the main solve's rule for its {B} resampled worlds: the same seed and the same match-resampling procedure, from the corpus files as they are now. Its selection frequencies use only the worlds it certified under its own decision rule and requirements, which can be fewer. |
| `RISK_PREFIX` (`B = 40`, while the prefix test holds) | The main solve's 12 resampled worlds are worlds 0 to 11 of these 40. Its selection frequencies use only the worlds it certified under its own decision rule and requirements. |
| `RISK_HARD` | Declared-risk rules compare shortfalls; a hard minimum is a Satisfy question. |
| `RISK_OVERFLOW` | The declared minima are too large for the exact integer model of this rule. |
| `RISK_NOT_EVALUABLE` | No world, or fewer worlds than the tail count, could be used, so this rule was not evaluated. |
| `MODEL_DIFFERS` | This answer's model holds {labels_here}; the solve above holds {labels_main}. Differences from the solve above can come from that alone. |
| `SIDE_MINIMA_SET_ASIDE` | Without the experimental opt-in, the side pass-origin minima of the solve above are not part of this question. |
| `UNKNOWN_PLAYER` | A locked or excluded player is not a candidate of this decision point. |
| `OPT_IN_LABEL` | Include the two EXPERIMENTAL side pass-origin requirements |

`RISK_SAME_DRAW` and `RISK_PREFIX` state how the worlds are built, which the router knows
without seeing the main reply; neither says that the main solve used these worlds, and the
certificate prints the world fingerprint so a reader can compare it with the main solve's.
`RISK_SAME_DRAW` names the procedure and the files as they are now, not "the same matches":
after a corpus rewrite in a running server the main solve keeps worlds drawn from the files as
they were (`decision_lab.snapshot`'s cache, KNOWN_LIMITATIONS.md:79-82), while the gated loader
of 7.3 draws again from the new files, and the fingerprints then differ.
The earlier sentence that the worlds "are the worlds the main solve's selection frequencies
use" is withdrawn: the main solve sets aside, besides discarded worlds, every world it could
not certify (solver.py:566-568), under its own mode and requirements. The sentence
`CONFLICT_CONSERVATIVE_FOR_SOLVE`, which the page was to print while the half-even variant
waited for a ruling, is withdrawn: under X2 no reply explains the main solve conservatively.

### 7.8 Caching, budgets, failures

A reply is stored when `runtime.is_complete` holds: every `completeness` in it `EXACT` or
`COMPLETE`, the membership block included. Proved terminal outcomes are `EXACT` or `COMPLETE`
(1.5) and are stored: `UNFIELDABLE`, `NOT_SATISFIABLE`, `NOT_EVALUABLE` (with an `EXACT`, empty
membership block) and `MODEL_FEASIBLE`. `DEADLINE`, `LIMIT_REACHED` and `MODEL_INVALID`
replies are returned and computed again next time; a reply whose membership is undecided is
one of them, and so is a `FLOORS_UNMET` reply (its cause undecided) and a membership block
`NOT_REQUESTED`; an identical request in flight is still computed once
(`RESULTS.get_or_compute`). Status codes are the runtime's: 404 unknown
scenario, 422 refusal (with the tool's sentence), 429 busy, 503 corpus absent, 500 for a
`BoundaryViolation` or an internal fault (`KeyError`, `RuntimeError` from a witness check, or an
exception raised by CP-SAT, such as `MemoryError`, which is never turned into a status, 1.5).

### 7.9 What does not change (R13)

`decision_lab.py`, `runtime.py` (except the one long route the root adds, X5, section 12),
`shell.py`, `planning.py`, `squad_lab.py`, `transfer_lab.py`, `labs-shared.js` and every
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
after `#tradeoff-panel`, two script tags immediately before the inline script
(`labs-shared.js`, then `xi-extensions.js`), one call
`XiExtensions.mount(document.getElementById('xi-extensions'))` in a script tag after them and
still before the inline script, and three event dispatches: two inside `solve()`,
`new Event('xi:invalidated')` when a solve starts and `new CustomEvent('xi:solved', …)` after
`render()` with `detail = {input: solvedInput, status: d.solution_status}`, and one more
`xi:invalidated` in the `#minimum-inputs` input listener, when a main minimum is edited
(section 12, edit 5). The root granted these edits (X4, ROOT-DECISIONS 2.7) on one condition:
every shipped XI test and browser spec passes unchanged, and the new panels send nothing until
their own button is pressed (8.2), which X12 reads as no solve and no request that reads the
corpus, the one corpus-free `GET` on load allowed.

The scripts and the mount precede the inline script so that the controller listens before the
page's first solve can finish (X13 accepted this placement). Placed after it, as the granted
text of X4 had them, they race the inline script's async start-up (xi.html:81:
`await api('/api/xi/scenarios')`, then `await solve()`): the parser fetches the two external
files while that chain runs, and an `xi:solved` dispatched before `mount` is lost, leaving every
panel disabled until the next solve. Before the inline script nothing is lost: neither
`labs-shared.js` nor `xi-extensions.js` declares a script-scope name or reads a page name when
evaluated (labs-shared.js:13-15), the mount `<div>` (edit 2) is already parsed, and `mount` only
builds markup inside it, registers its two listeners and sends the corpus-free `GET`.

`xi-extensions.js` reads the page only through these events; it never reads `result`, `locks`
or any page-scope name, and it declares nothing in script scope (one global,
`window.XiExtensions`), so it precedes the page's `$`, `esc`, `num`, `pct` and `api`, which the
inline script declares after it (X13), without colliding with them, as `labs-shared.js` does
(labs-shared.js:13-15). Evaluating the file touches no `document`: the
render test harness, whose `document` throws on any access (test_shell_render.py:44), loads it
and never calls `mount`.

The file has two parts. `window.XiExtensions.render`: pure functions, payload to markup string,
every server string through `Shell.esc`, no element touched, the discipline of the shared kit.
`window.XiExtensions.mount(root)`: the controller that builds the four panels, fetches
`GET /api/xi/extensions` once, listens to the two events, sends requests through `Shell.api`,
and discards a response whose request version is not the latest (the page's own
`requestVersion` rule). It is called only by the page.

Ledger ids. `Shell.ledger` emits the fixed ids `ledger-declared` and `evidence-ledger`
(labs-shared.js:185-198), each in one of two forms, and this section shows up to four ledgers
on one page. `XiExtensions.render.ledger(prefix, declared, rows)` calls `Shell.ledger` and
replaces whole attribute runs, never adds an attribute (an element with two `class` attributes
keeps only the first, so an added class would be dropped by the parser):
`class="ledger" id="ledger-declared"` becomes
`class="ledger xi-ledger-declared" id="{prefix}-ledger-declared"`;
`class="unavailable" id="ledger-declared"` becomes
`class="unavailable xi-ledger-declared" id="{prefix}-ledger-declared"`;
`class="ledger evidence-ledger" id="evidence-ledger"` becomes
`class="ledger evidence-ledger" id="{prefix}-evidence-ledger"`; and
`class="unavailable" id="evidence-ledger"` becomes
`class="unavailable" id="{prefix}-evidence-ledger"`. Exactly one form of each must occur, once;
otherwise the function throws, so a change to the kit fails a test instead of producing
duplicate ids or a lost class. `xi-extensions.css` repeats the `#ledger-declared` rules of
labs-shared.css:40-41 (among them `td{overflow-wrap:anywhere}`, which the 320 and 390 px checks
need) for `.xi-ledger-declared`, scoped under `#xi-extensions` (8.3).
The root declined an optional prefix argument to `Shell.ledger` as not needed (X11): this
rewrite is the specification, and `labs-shared.js` is not edited.

### 8.2 The panels

One section, four panels in a fixed order. One checkbox above them, `#xi-experimental-opt-in`,
unchecked on every load, labelled `OPT_IN_LABEL`; ticking it sends `experimental_opt_in: true`
on the next request of every panel and prints the composed class beside every number. Before
`xi:solved` every button is disabled and each panel reads "Re-solve the main XI first.";
`xi:invalidated` disables them again and clears every panel, and a panel reply whose request
version is no longer the latest (a new main solve, or a main minimum edited, while it was in
flight) is discarded, never rendered (8.1). **No panel sends a POST on its own**: every POST
follows a press of that panel's button, so a shipped flow that presses no new button sends no
new POST. The only new request on load is the corpus-free `GET /api/xi/extensions`, sent once
by `mount` through `finalize`: the frontier and risk selects need its `requirements` and
`rule_options` before their buttons can be enabled. X12 rules that this `GET` meets X4's
condition, which forbids a solve or any request that reads the corpus. The e2e spec asserts
that this `GET` is the only new request on load. If the `GET` fails, the section prints the
error through `Shell.errorText` and every panel stays disabled; nothing is retried on its own.

Request body, every panel, built from `event.detail.input` (the main solve's `scenario_id`,
`formation`, `mode`, `locks`, `excludes`, `minimums`) and the `GET` reply's `requirements`:
`scenario_id`, `formation`, `locks` and `excludes` copied from the main solve, so a panel
never fields a player the main solve excluded; `experimental_opt_in` from the checkbox;
`minimums` (ceilings, risk) the main solve's minima restricted to the requirement ids
whose `experimental` flag is false when the opt-in is unticked, and all of them when it is
ticked; the conflict panel, whose request always carries the opt-in, sends the main solve's
`minimums` unfiltered, which is `{}` until the reader applies minima (xi.html:79), so default
minima stay defaults in its labels and declared rows. Restricting keys by a server flag is the
one selection the page makes; it decides nothing about what is in force (the server does, and
refuses a side minimum without the opt-in). When a key was left out the panel prints
`SIDE_MINIMA_SET_ASIDE`. Integers are sent as the `GET` served them (`world_counts[i]`,
`rule_options[B][j].tail_count`), never as an option's string value, because
`bootstrap_worlds` and `tail_count` are strict integers and a string is a 422.

| Panel | Shown when | Request | Renders (server field) | States |
|---|---|---|---|---|
| `#conflict-panel` "Which declarations cannot hold together" | the last main solve is `INFEASIBLE` | button `#explain-conflict`, "Explain, including the two EXPERIMENTAL requirements the solve above used"; `POST /api/xi/conflict` with the common body, the opt-in sent as true whatever the checkbox (the main solve had them in force), the main solve's `minimums` unfiltered (`{}` when it sent none), `explains: "solve"` and the main solve's `mode`; no `floors` key (X2) | status badge; the served `claim` (the constant the status selects, 3.4; never `CONFLICT_CLAIM` by name); the served arithmetic sentence (`statements`: `CONFLICT_HALF_EVEN` for a Satisfy solve, even when the set holds no floor, or `CONFLICT_NO_MINIMUM` for a `BALANCE` solve, which declares no floor; the condition is on the declarations, 7.5, not on the set); one row per entry of `result.member_rows` in server order: family, `label_text`, `member_text`, `restore_text`; a `<details>` per member with its `assignment_rows` (slot label, `player_text`, `note_text`), its `missing_locked_text` when not `null`, and, when the restore test found one, its `restore_rows`; certificate (solves, statuses, `final_set_proof_solve`, completeness, deletion order); ledger, prefix `conflict` | `NOT_PROVEN_MINIMAL`: the status badge, the served claim, the member rows as normal, each undecided or `NOT_RUN` member with `CONFLICT_MEMBER_UNDECIDED` and each refused member with `CONFLICT_MEMBER_REFUSED` (their `member_text`), completeness in the certificate; `MODEL_FEASIBLE`: the served claim (`CONFLICT_FEASIBLE`) and the XI; `UNDECIDED`, and `MODEL_INVALID` (a refused initial test only): `Shell.notCertified` and the served claim; 422, 503 through `Shell.errorText` |
| `#ceilings-panel` "Attainable range of each requirement sum" | after `xi:solved` | button `#solve-ceilings`; `POST /api/xi/ceilings` with the common body; no floors from the page | the served `claim` in every state (the constant the state selects, 2.2; never `CEILING_CLAIM` by name), non-claim, `model_note` and the served `statements` (`CEILING_EXACT_FACTS`, and `FLOORS_SCOPE` for an API reply with floors); a table, one row per range in server order: label and evidence badge (`evidence`, the domain class); least `attained_text`/`bound_text`; largest `attained_text`/`bound_text`; the two minimum statements; certificate details; ledger, prefix `ceilings` | an end not certified: `CEILING_NOT_CERTIFIED` in its cell, no number; an end with a witness and no bound (`bound_text` `null`): its `attained_text` in its own cell and `CEILING_NOT_CERTIFIED` in the bound cell only; `UNKNOWN`: `Shell.notCertified` and the served claim (`CEILING_NOT_DECIDED`), each cell `CEILING_NOT_CERTIFIED`; `UNFIELDABLE`: the served claim (`CEILING_EMPTY`) and `Shell.infeasible(reasons)`; `MODEL_INVALID`: `Shell.notCertified` and the served claim (`CEILING_REFUSED`). `NOT_SATISFIABLE` and `FLOORS_UNMET` need floors, which the page never sends; an API reply in those states renders the served claim and `Shell.infeasible` of its served statements |
| `#frontier-panel` "Nondominated requirement sums" | after `xi:solved` | selects `#frontier-dim-1..3`, each starting empty with the placeholder "Choose a requirement", options the `GET` reply's `requirements` (only those with `experimental` false while the opt-in is unticked, labels as served); the button `#solve-frontier` is enabled only with two or three distinct choices; `POST /api/xi/frontier` with `scenario_id`, `formation`, `locks`, `excludes`, the opt-in and `dimensions` in the chosen order; no minima (sums, not shortfalls) and no floors | the served `claim` (never `FRONTIER_CLAIM` by name) and non-claim; the served `status_text` above the table; the served evidence badge beside the table (`evidence`, `EXPERIMENTAL` whenever the side requirements are in force, which every frontier needs with the shipped requirement set); a table, one row per point in server order, one column per declared dimension (`point_texts`, header "rounded sum, in club medians"), a column `raw_sum_texts` (header "one XI reaching it sums to, before rounding, in club medians"), a column `allowance_texts` (header "allowance, in club medians"), a "One XI" toggle showing the point's `lineup_rows`; `FRONTIER_WITNESS` under the table; for `d = 2` an SVG with `viewBox="-0.05 -0.05 1.1 1.1"` and one circle per point at (`plot_x`, `plot_y`), every circle the same size, colour and stroke; the `point_order` sentence; certificate (points, solves, completeness, `stopped_by`, final region status); ledger, prefix `frontier` | without the opt-in, `GET`'s `frontier_opt_in_text` and the button disabled; `LIMIT_REACHED`, `DEADLINE`, `MODEL_INVALID` with at least one point: the served `status_text` above the table; `INCOMPLETE` or `MODEL_INVALID` with no point: `Shell.notCertified` and the served `status_text` (`FRONTIER_STOPPED_NONE` or `SOLVER_REFUSED`), no table and no SVG, as the conflict panel's `UNDECIDED`; `UNFIELDABLE`: `Shell.infeasible(reasons)`; `NOT_SATISFIABLE` and `FLOORS_UNMET` (API replies with floors only): `Shell.infeasible` of the served statements and reasons; one point: the same table with one row |
| `#risk-panel` "Declared risk preference over resampled matches" | after `xi:solved` | `#risk-worlds` (the `GET` reply's `world_counts`: 12 alone until the 40-world timing, X5) and `#risk-rule` (the `GET` reply's `rule_options[B]` texts, fixed order), both starting on an empty placeholder; the button `#solve-risk` is enabled only when both are chosen; `POST /api/xi/risk/tail` with the common body, `bootstrap_worlds`, `rule` and, for `TAIL`, `tail_count`; or `POST /api/xi/risk/regret` with the common body and `bootstrap_worlds`; both integers as the `GET` served them | the served envelope `claim` (the rule label, ending with `RISK_OUTSIDE_E13` for a request outside E-13's scope, a request without the opt-in included, or `RISK_UNTESTED` while not executed, 5.7); `Shell.verdictBadge` and `verdictLines` of `verdicts.risk_rule`; no `risk_report` line (it is `null` until section 13 settles it); the non-claim, `model_note` and the served `statements`; roster of `result.lineup_rows`; TAIL and WORST_WORLD: the tail sums' texts, a table "For the XI shown" of `tail_rows`, `boundary_ties_text`; REGRET: a table "For the XI shown" of `binding_rows` with both pairs, and `world_rows` in `<details>`; `RISK_WITNESS` under each such table; the point-estimate pair's texts and `point_sum_texts`; the membership groups (server headings, server order); certificate: B, used, discarded count and list, world seed, fingerprint, `RISK_SAME_DRAW` or `RISK_PREFIX` when served, the certificate's `growth` sentence (WORST_WORLD and TAIL, O8), solves, the statuses of `records` in call order, completeness, both deterministic limits; ledger, prefix `risk` | `NOT_EVALUABLE`: `RISK_NOT_EVALUABLE`; `UNKNOWN`: `Shell.notCertified`, no XI; `MODEL_INVALID`: `Shell.notCertified` and `SOLVER_REFUSED`, no XI; `UNFIELDABLE`: `Shell.infeasible(reasons)`; 422 overflow sentence as sent |

### 8.3 Rules of the page

- R10: JS computes no eligibility, coverage, objective, uncertainty, bound, count or plot
  position. Every number printed is a server string (`*_text`, `*_texts`, `value_text`,
  server-formatted counts) or a server number field on this allow-list, printed as is: the
  integer fields (world ids, `solves`, `final_set_proof_solve`, point counts, `world_count`,
  `world_seed`) and the certificates' deterministic limits (`per_solve_deterministic_limit`,
  `selection_deterministic_limit`, `world_least_deterministic_limit`); `plot_x` and `plot_y` are server strings placed as
  SVG coordinates in the fixed `viewBox`, never transformed. JS never sorts, filters or groups
  rows, and never looks an entry up in one list by an id from another: every table is a served
  row list (`ranges`, `member_rows`, `assignment_rows`, `restore_rows`, `lineup_rows`,
  `tail_rows`, `boundary_rows`, `binding_rows`, `world_rows`, `membership.groups`, 7.5) printed
  in the order received. The one selection it makes is by the server's `experimental` flag
  (8.2).
- No ranking or highlighting of a frontier point: every row and every circle has the same
  classes and computed style; nothing is selected on arrival; the detail area reads "Choose a
  point to see one XI that reaches it." A point the reader opens gets the outline every opened
  row gets, and nothing else changes. None of the words O7 forbids ("best", "optimal",
  "trade-off" in any spelling, "knee", section 4; the solver status token `OPTIMAL` in a status
  field excepted), nor "dominant" or "recommended", appears; the page prints the server's
  `point_order` sentence under the table.
- No rule is preselected, and the order of rules never depends on a verdict token (E-13).
- No `%` sign and no word of chance appears in the risk panel.
- Every per-world table of the risk panel is titled "For the XI shown" and followed by
  `RISK_WITNESS`.
- Ids are unique on the page (8.1).
- Mobile: the kit's `cell` helper is private (it is not on `window.Shell`) and its stacking rule
  applies to `.evidence-ledger` only, at 650 px (labs-shared.css:44), so `xi-extensions.js`
  writes its own `data-label` attribute on every cell of its tables, and `xi-extensions.css`
  stacks those tables at 600 px and below by the same pattern (`td::before{content:
  attr(data-label)}`). The SVG has its fixed `viewBox` and `width: 100%`; at 390 and 320 px
  `#xi-extensions` itself has `scrollWidth ≤ clientWidth` (the shipped parts of `/xi` are not
  measured at 320 px by this work).
- Stylesheet scope (X4, R13): `xi-extensions.css` is linked after `labs-shared.css` on `/xi`, so
  an unscoped rule would restyle shipped elements no shipped spec measures (`.panel h2`, `.ledger
  td` on the tradeoff and alternatives panels). Every selector in it starts with
  `#xi-extensions` or names only `xi-`-prefixed classes or ids; no element-only selector and no
  kit class (`.panel`, `.ledger`, `.badge`, `.evidence-ledger`) appears outside that scope. A
  unit test parses the sheet and asserts it (section 9).
- Names the shipped specs select without a scope are never used by the page parts, so a
  shipped locator never matches a new element: no `data-requirement`, `data-floor` or
  `data-alternative` attribute, no `alternative-xi` class, no text "Adjust requirement minima",
  and no text "lock/exclusion" anywhere in the new panels (alternatives.spec.js:15, 34, 37;
  labs.spec.js:179-180; repairs.spec.js:204, 211-212, 256; tradeoff.spec.js:18, 66).
- Colour: gold (`rgb(201, 162, 39)`) is not used on any number of the new panels, as the
  tradeoff test already checks on its own panel.

### 8.4 Fallback page: not needed

The stand-alone page this section specified, for the case in which the root refused the
`xi.html` edits, is not needed and is not built: X4 (ROOT-DECISIONS 2.7) granted the five
edits, so there is no `web/xi-extensions.html` and no `/xi/extensions` route, `/xi` is the only
page that mounts the panels, and the e2e spec targets `/xi`.

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
every proved terminal outcome. Each tool file also pins, by name and call signature, the private
`kernel.py` members its module uses (X9).

Comparing two results. A result's provenance holds the wall times of its solves (1.5), which
differ on every run. Every comparison of two results by `asdict` (determinism, shuffled inputs,
WORST_WORLD against TAIL(1)) is of `stable(asdict(result))`: `asdict(result)` with
`provenance["<tool>_solve_wall_times"]` deleted from both sides, and nothing else compared less
strictly; the `<tool>_solve_deterministic_times` lists stay in the comparison and must be equal.
Each tool file also asserts that the wall-time list holds one finite float `≥ 0` per call that
is not `NOT_RUN`. Wall times are not moved to `budget.report`, whose keys
`tests/test_lab_runtime.py:147` pins.

Integers from the solver. Each tool file wraps the solver, as `tests/test_xi_tradeoffs.py:156`
does, so that `objective_value` and `best_objective_bound` return the exact value minus `2**-20`
on an `OPTIMAL` solve, and asserts that no `RuntimeError` is raised, that `stable(asdict(...))`
equals the unwrapped run's, and that a tampered witness still raises (1.5, 2.3). The test does
not rely on a seeded instance on which one OR-Tools version happens to report a non-integral
optimum; such an instance may be added beside it, with the OR-Tools version recorded.

Classification of stops (1.5). The CEILING, CONFLICT and RISK files each plant a mixed
sequence: one call stopped at its deterministic limit and a later call `NOT_RUN` gives
`DEADLINE` and `WALL_CLOCK`; deterministic stops alone give `LIMIT_REACHED` and
`DETERMINISTIC_LIMIT`; a monkeypatched `UNKNOWN` that reached neither limit gives `DEADLINE` and
`WALL_CLOCK`. FRONTIER cannot produce a mixed sequence: it stops at its first undecided call, and
the only call that can follow another is the cause solve, after a decided `INFEASIBLE` (4.2). Its
single stopping call decides the tokens, and the frontier file plants each single stop: a
deterministic stop (`LIMIT_REACHED`, `DETERMINISTIC_LIMIT`), a monkeypatched `UNKNOWN` that
reached neither limit (`DEADLINE`, `WALL_CLOCK`), and a floors cause solve stopped at its
deterministic limit (`FLOORS_UNMET`, `LIMIT_REACHED`, `DETERMINISTIC_LIMIT`).

Claims by state (checklist item 18). Each tool file asserts that the served claim is the
constant its state selects, and that on every reply no served sentence states what only a
proved or complete one would: the CEILING claim per state of 2.2, the CONFLICT claim per status
of 3.4, the one FRONTIER claim on every status with no served sentence of a cut or empty
undecided list stating completeness, and the RISK label.

| File | Tests |
|---|---|
| `test_xi_ceilings.py` | integer ends equal the oracle's `min`/`max` of `O_r` over `𝒳_F`, with and without floors, locks, exclusions, `None` values, zero minutes and negative rates; every feasible oracle `S_r` lies in the bracket, in `Fraction`; witnesses admissible, floors met in integers and `Fraction`, `O_r` recomputed equal; the two minimum facts equal the oracle's truth over `𝒳_F` whenever not `None`, and `None` occurs only when no returned witness and no bound decides it, with reason `ALLOWANCE` only on a `QUANTIZED_OPTIMAL` end (and there `raw_bound − attained ≤ 2e_r`, up to the outward `nextafter` steps) and `NOT_CERTIFIED` on any other (a planted case of each of the four decided outcomes and of each reason); both witnesses decide: on the planted instance `q = 1`, `n = 1`, slots `a`, `b`, players A1 (`a`; r 0.6, f 1, g 1), A2 (`a`; r 1.4, f 2, g 0), B1 (`b`; r 0.6, f 1, g 0), B2 (`b`; r 0.4, f 0, g 1), floors f ≥ 2 and g ≥ 1, `m_r = 1.5`, reached is True by the LEAST witness (1.8) and missed True by the LARGEST witness (1.2), and a case with one end `NO_SOLUTION` (monkeypatched) is decided by the other end's witness; a monkeypatched `FEASIBLE` LARGEST end with `m_r` strictly between the witness's sum and a finite bound more than `2e_r` above it gives `None` with `NOT_CERTIFIED`, never `ALLOWANCE`, and the router serves `CEILING_REACHED_NOT_CERTIFIED` (and the LEAST mirror `CEILING_MISSED_NOT_CERTIFIED`); a monkeypatched `FEASIBLE` end whose `best_objective_bound` is `inf` or `-inf` keeps its witness and `attained_text`, with `integer_bound`, `raw_bound` and `bound_text` `None`, and its fact decided by the witness or `None` with `NOT_CERTIFIED`; a `QUANTIZED_OPTIMAL` end with `m_r` inside its band gives `ALLOWANCE`; a `FEASIBLE_NOT_PROVEN` end decides a fact by its witness or its finite bound; the top-tie instance (`q = 10`, `n = 1`, every slot applicable; slots s0 {A,B}, s1 {A,B}, s2 {A}; seven A players with rates 0.85, 0.63, 1.67, 0.2, 0.76, 1.26, 0.22, where {1,3,6} and {3,5,6} tie at `O = 38` with sums 3.78 and 3.69): the oracle's `R⁺` and `R⁻` each lie in the served interval (`[attained_text, bound_text]` for LARGEST, `[bound_text, attained_text]` for LEAST, compared as `Fraction`), the witness's `O_r` equals `I⁺`, and its sum is not asserted to equal `R⁺`; the same containment at `q = 100000` on the pinned instance one applicable slot, player 1 at 0.0000155 and player 2 at 0.000015, both coefficient 2, run in both id orders (the values swapped between the ids), with containment asserted on both runs and at least one of the two asserted to return a witness that misses `R⁺` (the OR-Tools version recorded); claim per state (2.2): an all-`QUANTIZED_OPTIMAL` instance and one with a monkeypatched `FEASIBLE` end and a finite bound give `CEILING_CLAIM`; a monkeypatched `UNKNOWN` LEAST solve beside a proved LARGEST end (`FIELDABLE`) and a monkeypatched `FEASIBLE` end whose `best_objective_bound` is `±inf` give `CEILING_PARTIAL_CLAIM`; a deadline passed at entry and an all-`UNKNOWN` run give `CEILING_NOT_DECIDED`; one slot `a` {A} with players 1 and 2 (A) both locked (the first solve `INFEASIBLE`, `UNFIELDABLE`, `ranges == ()`), `UNFIELDABLE` by construction, `NOT_SATISFIABLE` and `FLOORS_UNMET` give `CEILING_EMPTY`; a `MODEL_INVALID` range solve and a `MODEL_INVALID` cause solve give `CEILING_REFUSED`, with `CEILING_REFUSED` absent from `statements`; `scan_labels` of each is empty; declared floors (instance A: `q = 100000`, slots `a`, `b`, p1 (`a`) and p2 (`b`) with r1 0.15 and r2 5.0, p3 (`a`) and p4 (`b`) with r1 1.0 and r2 0, `m_r2 = 8`, floor r1 ≥ 0.3): the served r2 statement is `CEILING_UNREACHABLE` with the floor scope of `{xi}` and the reply carries `FLOORS_SCOPE`, while the oracle confirms that (p1, p2) meets the raw floor and sums to 10; with `m_r1 = 1.0` the same instance serves `CEILING_EVERY` and a least-end ledger row, both scoped; without floors neither the scope nor `FLOORS_SCOPE` appears; instance B (`q = 100000`, `n = 1`, slots `a`, `b`, p1 and p2 at 0.500004, minimum 1.000006): reached is True here while `solve_xi(mode="SATISFY")` is INFEASIBLE, and the API reply carries `CEILING_EXACT_FACTS`; a monkeypatched run in which every solve is `UNKNOWN` gives `feasible_set = UNKNOWN`; a proof after an undecided end (1.5, "a proof supersedes earlier calls"; R = {r1, r2}, no floors, r1's LARGEST solve monkeypatched `UNKNOWN` with a deterministic time at its limit and the deadline not passed, r1's LEAST solve `INFEASIBLE`) gives `UNFIELDABLE`, `EXACT`, `stopped_by` `None`, the `UNKNOWN` kept in `statuses`, stored; with floors and the cause solve returning a witness, the same sequence gives `NOT_SATISFIABLE`, `EXACT`; an empty `R` and a requirement with `hard=True` are each a `ValueError`; a reordered `floors` mapping gives an identical `stable(asdict)`; with `φ_r ≠ m_r` the facts use `m_r`; `UNFIELDABLE` by construction and by proof (the proved one with the reason `UNFIELDABLE_PROVED`), `NOT_SATISFIABLE` with floors, each `EXACT`; with floors and an `UNKNOWN` (monkeypatched) cause solve, `FLOORS_UNMET`, not stored; with floors and a `NOT_RUN` cause solve (the deadline passing between the `INFEASIBLE` solve and the cause solve), `FLOORS_UNMET`, `DEADLINE`, `WALL_CLOCK`, not stored; a `MODEL_INVALID` solve (monkeypatched), a range solve or the cause solve, ends the tool with `feasible_set = MODEL_INVALID`, no range, the claim `CEILING_REFUSED` and completeness `MODEL_INVALID`; a deadline passing after the first requirement's two solves gives `FIELDABLE`, every later end `NO_SOLUTION` with `CEILING_NOT_CERTIFIED`, their facts `None` with `NOT_CERTIFIED`, `DEADLINE`, and the claim `CEILING_PARTIAL_CLAIM`; parity, on instances whose oracle feasible set is not empty: with floors equal to every active minimum the LARGEST end equals `maximize_requirement`'s `integer_value`, `integer_upper_bound` and certification, and each witness's exact sum lies in `[(n_r / q) · I⁺_r − e_r, (n_r / q) · I⁺_r + e_r]` (2.4; witnesses are not compared); a passed deadline gives `NOT_RUN` everywhere (`2·|R|` `NOT_RUN` statuses, `solves == 0`), no number, `DEADLINE`; a coefficient above `MAX_MAGNITUDE` is a `ValueError` with the deadline already passed and with `β.model` `None` alike (2.3 step 1); `UNFIELDABLE` by construction has `statuses == ()` and `solves == 0`; `ceilings.UNFIELDABLE_PROVED`, `frontier.UNFIELDABLE_PROVED` and `risk.UNFIELDABLE_PROVED` are the same text, as `FLOORS_CONSERVATIVE` in `ceilings` and `frontier`; the implication of 1.2 (half-even infeasibility implies conservative infeasibility), as a property test on random `v`, `n` and `m` within `MAX_MAGNITUDE`, values near `10**12` and the 0.005 and 0.015 cases of `tests/test_squad_kernel.py:639` included: `floor(_scaled(v, n, q)) ≤ _q(v, n, q)` and `ceil(_scaled(m, n, q)) ≥ _q(m, n, q)`; a monkeypatched `FEASIBLE` status gives `FEASIBLE_NOT_PROVEN` with a bracket that still contains every oracle sum; a monkeypatched response whose deterministic time reached the limit gives `LIMIT_REACHED` and `stopped_by = DETERMINISTIC_LIMIT`, one whose wall time ran out `DEADLINE` and `WALL_CLOCK`; a tampered witness raises `RuntimeError`; the objective coefficients equal `round(_scaled(...))` and differ from `_q` on `1.344465 / 1.0` at 100000; determinism; shuffled candidates and requirements give an identical `stable(asdict)` |
| `test_xi_conflict.py` | `explain_floors`: the returned set equals the oracle's deletion filter in the declared order (equality, not just minimality); the oracle finds the set not satisfiable and every set with one member removed satisfiable; each restore test equals the oracle's `restores_alone` (`NOT_APPLICABLE` for slot coverage); `MODEL_FEASIBLE` iff the oracle finds an XI, `EXACT`; parity, on instances with no hard requirement: `explain_floors()` is `MODEL_FEASIBLE` iff `kernel.satisfiable` is `SATISFIABLE`; the instance of 3.3 (`exclusion:A`, a floor above every assignment's sum, `lock:A` with an admissible key) returns `{floor:progression}` with a witness that is checked against `{lock:A}` (which XI or assignment comes back is the solver's choice and is not asserted), and its restore test is `False`; that instance, pinned as slots `a`, `b` {DF}, players 1, 2, 3 DF each with progression 1.0, `exclusion:1`, a progression floor above 2 and `lock:1`, is `MINIMAL_CERTIFIED` with `claim` equal to the 7.7 `CONFLICT_CLAIM`, whose wording is conditional; enumerating every subset of its declarations with the oracle's `satisfiable` finds exactly two minimal conflicting sets, `{floor:progression}` and `{exclusion:1, lock:1}`, and the oracle's `deletion_filter` run with the floor tested first returns `{exclusion:1, lock:1}`, so the clause "checking in another order can return another" is true there; on the three-slot instance below, run unpatched (a progression floor no XI reaches, for example 3.5), the reply is `MINIMAL_CERTIFIED` with conflict `(floor:progression)`, its restore test is `True`, `claim == CONFLICT_CLAIM`, and the same enumeration finds `{floor:progression}` to be the only minimal conflicting set; two planted independent conflicts give one set whose members all have `restores_alone = False`, and no served sentence of the reply states that dropping a member leaves an XI; a witness that uses an excluded player lists him in `witness_excluded_players`; a locked-and-excluded player `p` with an admissible key, in an instance with no other conflict, gives exactly `{exclusion:p, lock:p}`; a witness that leaves out a locked player lists him in `witness_missing_locked_players`; a slot no admissible player can fill, in an instance with no other conflict, gives `{slot:s}`; a monkeypatched `UNKNOWN` on one filter test gives `NOT_PROVEN_MINIMAL`, that member `KEPT_UNDECIDED`, never `MINIMAL_CERTIFIED`; the claim per status, on the instance slots s1 {DF}, s2 {DF, MF}, s3 {MF}, players 1 and 2 DF and 3 and 4 MF each with progression 1.0, a progression floor no XI reaches and `exclusion:2`: a monkeypatched `UNKNOWN` on the filter test of `{floor:progression}` gives `NOT_PROVEN_MINIMAL`, conflict `(exclusion:2, floor:progression)`, `exclusion:2` `KEPT_UNDECIDED` and `claim == CONFLICT_NOT_PROVEN_CLAIM`, with the oracle finding `{floor:progression}` unsatisfiable (so `CONFLICT_CLAIM` would be false); a deadline that passes after the three slot tests gives the same set, both members `NOT_RUN`, the same claim, `DEADLINE`; `MODEL_FEASIBLE` has `claim == CONFLICT_FEASIBLE` and `tests == restore_tests == conflict == ()`, completeness `EXACT`; a deadline passed at entry gives `s0` `NOT_RUN`, `UNDECIDED`, `claim == CONFLICT_NOT_DECIDED`, `tests == ()`, `DEADLINE`, nothing stored; a deadline passing mid-filter keeps the `NOT_RUN` members, gives `NOT_PROVEN_MINIMAL` with `CONFLICT_MEMBER_UNDECIDED` on each and its restore tests `NOT_RUN`; `MODEL_INVALID` (monkeypatched) at `s0` (`MODEL_INVALID`, `claim == CONFLICT_MODEL_INVALID`, `tests == restore_tests == conflict == ()`, not stored); mid-filter, on the three-slot instance with floor 3.5 and `MODEL_INVALID` on the test of the set `{floor:progression}` (the filter test of `exclusion:2`): `NOT_PROVEN_MINIMAL`, conflict `(exclusion:2, floor:progression)`, `exclusion:2` `KEPT_REFUSED` with status `MODEL_INVALID` and empty witness fields, `floor:progression` `KEPT_WITNESS`, no `NOT_RUN` row, `final_set_proof_solve == 3` (`statuses[0]` and `statuses[3]` both INFEASIBLE), `members_refused == 1`, `claim == CONFLICT_NOT_PROVEN_CLAIM`, completeness `MODEL_INVALID`, `stopped_by` `None`, the restore tests run, and the oracle finds the returned set and `{floor:progression}` each unsatisfiable; and in a restore test (the set and its claim stand, that member `None`, the later restore tests run, completeness `MODEL_INVALID`); `LIMIT_REACHED` with `DETERMINISTIC_LIMIT`, and `DEADLINE` with `WALL_CLOCK`, each planted (1.5); one on a restore test leaves the status and gives that member `None` and completeness `DEADLINE`; `final_set_proof_solve` points at an INFEASIBLE status of a test of exactly the final set, `statuses[0]` is `s0`, `statuses` holds one entry per filter test (`NOT_RUN` included) and per restore test that is not `NOT_APPLICABLE`, `solves` counts only the calls made, and `members_with_witness + members_undecided + members_refused == len(conflict)`; a test whose `_Run.solve` returns no solver (the deadline monkeypatched to pass between the loop's check and the call) is `NOT_RUN`, never `KEPT_UNDECIDED` or `UNKNOWN`, with every later declaration `NOT_RUN`; tables equal `kernel._tables` on shared keys; a tampered filter witness and a tampered restore witness each raise; reordered inputs give the same set; `explain_solve` with a `mode` other than `BALANCE` or `SATISFY`, and `explain_floors` with an unknown floor key, a non-finite floor or a requirement with `hard=True` (with explicit floors that leave it out, too), are each a `ValueError`. A planted boundary instance feasible under half-even and not conservatively returns a set holding the floor from `explain_floors`. `explain_floors` with explicit floors where `φ ≠ m`, and with `floors={}`, against the oracle. `explain_solve`: against the oracle in half-even, `MODEL_FEASIBLE` iff `solve_xi(mode="SATISFY")` is `OPTIMAL` or `FEASIBLE`; `explain_solve(mode="BALANCE")` is `MODEL_FEASIBLE` iff `solve_xi(mode="BALANCE")` is `OPTIMAL` or `FEASIBLE`, on instances with and without a hard requirement, a locked-and-excluded player and two locked goalkeepers, and a `BALANCE` explanation with no hard requirement declares no floor; `requirements_in_force` equals `solve_xi`'s active set; and the boundary instance gives `MODEL_FEASIBLE` |
| `test_xi_frontier.py` | the set of `integer_sums` equals the oracle's nondominated set, `d = 2` and `d = 3`, with floors, locks and exclusions; every oracle feasible vector is weakly below a point; points pairwise nondominated; witnesses verified; the planted instance of 4.1 (`q = 1`, `n = 1`, two slots, declared `(r1, r2)`) gives exactly the points `[(1,1), (0,2)]`, `COMPLETE`, each listed once although XIs with different raw sums reach it ((1,1) by {a,c} and {b,c} with raw (1.1, 1.5) and by {c,d} with (0.9, 1.5); (0,2) by {a,b} with (1.0, 2.0) and by {a,d} and {b,d} with (0.8, 2.0)); at each point the oracle's XI with the componentwise larger raw sums has `V` equal to the point, and whichever witness the tool returns, `V(lineup)` equals `integer_sums`; the same instance with `exclusion:c` gives the single point (0,2), reached by three XIs whose raw sums are not all equal (the served texts of a one-point instance are asserted in the API tests); `max_points=1` on an instance with at least two points gives the lexicographic-maximum oracle point, `LIMIT_REACHED`, `stopped_by = POINT_LIMIT`, `final_region_status = OPTIMAL` from the limit check, a solve with no objective (4.2); a frontier of exactly `max_points` points is `COMPLETE`, its limit check `INFEASIBLE`; a monkeypatched `UNKNOWN` at the limit check gives `max_points` points, `INCOMPLETE`, `DEADLINE`, `WALL_CLOCK` and `FRONTIER_STOPPED`, never `FRONTIER_LIMIT`, and a monkeypatched `FEASIBLE` there gives `POINT_LIMIT` with `final_region_status = FEASIBLE`; the limit check is recorded in `statuses` and counted in `solves`; on seeded complete instances `solves == d · |points| + 1` with `statuses` ending in `INFEASIBLE`, on a `POINT_LIMIT` cut `solves == d · max_points + 1`, on an empty floored region `solves == 2`, without floors 1, and by construction 0; on an instance with at least three points, a monkeypatched `UNKNOWN` at stage 2 of the third iteration gives exactly the two earlier points, `INCOMPLETE`, `DEADLINE`, `WALL_CLOCK`, `final_region_status = UNKNOWN`; for `d = 2` and `d = 3`, with `max_points < |P|` and with that monkeypatched stop, the listed points are the first points of the oracle frontier sorted lexicographic-descending in the declared order; on a `COMPLETE` instance, reversing a two-dimension declaration reverses the list and swaps every pair; on the instance one slot, players `(6 − i, i)` for `i = 1..5`, `max_points = 2`, both declarations list `[(5,1),(4,2)]` in their own coordinates, which is not the reversed forward list, and `point_order` is the one 4.3 constant; a deadline passed before any solve gives `INCOMPLETE`, no point, `final_region_status = NOT_RUN`, `DEADLINE`; `UNFIELDABLE` by proof (`final_region_status = INFEASIBLE`, two locked players whose only admissible slot is the same one, so the kernel records no reason; the reason `UNFIELDABLE_PROVED`) and by construction (`INFEASIBLE_BY_CONSTRUCTION`, the kernel's reasons); with floors and a monkeypatched `UNKNOWN` cause solve, `FLOORS_UNMET`, no point, not stored; with floors and a cause solve stopped at its deterministic limit, `FLOORS_UNMET`, `LIMIT_REACHED`, `DETERMINISTIC_LIMIT`; with floors and a monkeypatched `MODEL_INVALID` cause solve, status `MODEL_INVALID`, no point, completeness `MODEL_INVALID`, `stopped_by` `None`, `final_region_status = INFEASIBLE`, not stored; `LIMIT_REACHED` with `DETERMINISTIC_LIMIT`, and `MODEL_INVALID` with the earlier points kept, each planted; a tampered witness, a list that is not pairwise nondominated and an `INFEASIBLE` stage `i > 1` (each monkeypatched) each raise `RuntimeError`; the objective coefficient is `round(_scaled(...))` and not `_q` (`1.344465 / 1.0` at 100000 gives 134447); declared floors (instance A of the ceilings tests, dimensions (r1, r2), floor r1 ≥ 0.3): the reply carries `FLOORS_SCOPE` and its completeness sentence is scoped, and the oracle confirms that (p1, p2), vector (30000, 1000000), meets the raw floor and is absent from the list; the list follows `POINT_ORDER`; no default dimension (calling without `dimensions` is a `TypeError`), `d ∉ {2, 3}`, a repeat, an inactive requirement, `max_points` 0, 65 or `True`, a bad floor key or value, and a requirement with `hard=True` are each a `ValueError`; empty feasible set as `UNFIELDABLE` and `NOT_SATISFIABLE`, each `COMPLETE`; `claim` is `FRONTIER_CLAIM` and `non_claim` `FRONTIER_NON_CLAIM` on every status, and on each cut or undecided reply (the 4.2 instance with `max_points=2`, `INCOMPLETE`, `POINT_LIMIT`, `[(5,1),(4,2)]`; the planted stage-2 `UNKNOWN` stop after two points; the deadline-at-entry reply with no point; `MODEL_INVALID` with earlier points kept; `MODEL_INVALID` from the floored cause solve with no point) no served sentence states that the list is complete (none begins "Every combination", none holds "Complete"), and where the list is cut the oracle's nondominated set strictly contains the listed points; no served frontier string outside provenance holds a word O7 forbids (section 4: "best", "optimal", "trade-off" in any spelling, "knee"; the status token `OPTIMAL` in a status field excepted); determinism; shuffled inputs give an identical `stable(asdict)` |
| `test_xi_risk_oracle.py` | (the E-13-pinned file) on every seeded instance, with `U` from the oracle's `used_worlds`, and every `k ∈ 1..B`: the status equals the oracle's, in the order of 5.6 (`NOT_EVALUABLE` iff `|U| = 0`, or `|U| < k` for TAIL, REGRET with `|U| = 0` included; otherwise `UNFIELDABLE` iff the oracle's `𝒳` under the vectors of any used world is empty), each terminal outcome has completeness `EXACT` and an `EXACT` empty membership block, and `certificate.used_world_ids` and the discarded world ids equal the oracle's `used_worlds`; where `CERTIFIED`: TAIL's `tail_sum` equals the oracle's optimum and the selected player set is in the oracle's level set; the tail ids and boundary ties equal the oracle's `tail_of(lineup, k)` for the returned lineup; REGRET's per-world least pairs and optimum equal the oracle's, the selected set is in its level set, and the binding worlds equal `binding_of(lineup)`; `world_losses` equals the oracle's pairs, and raises `ValueError` on a lineup that is not an XI of the used worlds; membership equals the oracle's level-set membership; `point_loss` equals the oracle's pair for the returned lineup under the candidates' own vectors (half-even tables) and `point_sums` the exact `Fraction` sums, with a planted `None` case for each field; every seeded instance's TAIL, WORST_WORLD and REGRET selection and membership calls finish within their wall-clock limit, run in a subprocess capped in memory and time (1.5, 5.1), so a regression fails the test instead of exhausting the machine; the instances are not vacuous: across the 120, some level set has more than one XI and some exactly one, some TAIL level set differs from the level set of the point-value BALANCE optimum (the oracle's XIs that minimise `(M, T)` at the candidates' own vectors, compared as sets of player sets, the comparison of E-13's own non-vacuity test, PIPELINE.md:598) and some equals it, some tail is decided by `T` at equal `M`, some instance discards a world, and some summed `T` over a tail exceeds `T_bound` (the oracle's `t_bound`) |
| `test_xi_risk.py` | single-world invariant: TAIL(1) and REGRET equal `kernel.value(values=…)` in integers, `solve_xi` on world-replaced candidates by `round(v * q)` of its `objective_vector`, and the oracle; WORST_WORLD equals TAIL(1) in `stable(asdict)` (section 9) except `rule`, `certificate.rule`, `claim`, `provenance.input_contract.rule` and the provenance fingerprints (`input_fingerprint` among them); TAIL(`|U|`) is the lexicographic minimum of (`Σ M`, `Σ T`); the discarded list equals `bootstrap_selection`'s `bootstrap_discarded_worlds` and the fingerprint its `bootstrap_world_fingerprint` on the same inputs, calling `bootstrap_selection` directly with a base `XIResult`, because `solve_xi(worlds=...)` returns before the bootstrap when its point-estimate solve is infeasible (solver.py:321-351) and its provenance then holds no bootstrap key (called directly, the discard loop runs on every seed, solver.py:545-564); a world dict missing a non-excluded player who is eligible at a slot where a requirement in force applies discards the world, as the bootstrap does, while one missing only a goalkeeper (eligible at no such slot) or only an excluded player discards nothing; doubling BIG (monkeypatched `_encoding_base`) leaves status, optimum (`tail_sum` or the regret optimum) and membership unchanged; two planted deterministic instances, one TAIL with `k = 2` and one REGRET, on which `BIG = T_bound + 1` provably selects a different set (the carry of 5.1), give the oracle's selection with the shipped BIG and another with the monkeypatched small one; no encoding leaves: the test recomputes BIG (when `T_bound ≥ 1`), the selection optimum `Φ*` (when the tail's `Σ M ≥ 1`) or `ρ*` (when its largest-shortfall difference is at least 1), every `E^w` of the returned lineup with `M^w ≥ 1` and every `E*^w` with `M*^w ≥ 1` (an encoding with a zero `M` part is a small sum or difference that equals a served field or a whole token of a served string by accident, and the API test's difference check covers it), and asserts that none appears in `asdict(result)` as an integer or as a whole digit token (`\b...\b`) of a string, except where it equals a value served under an allow-listed path (ids, counts, seeds, `quantization`, `LossPair` and `TailSums` fields); no key contains `encod`, `big`, `base` or `objective`; none of those integers appears as a token in `caplog`; the overflow guard refuses at `(k + |U| + 2) · E_cap ≥ 2**53` (TAIL) and `3 · E_cap ≥ 2**53` (REGRET) with a sentence holding no digit, in the order of 5.6: `|U| = 0` gives `NOT_EVALUABLE` (never a `max()` error); a slot no candidate can fill (`β.model` `None`) with a minimum of 1000, a normaliser of 0.001 and `q = 100000` raises `ValueError(RISK_OVERFLOW)`, not `UNFIELDABLE`, and so does the same request with the deadline already passed; for REGRET the refusal comes before any `kernel.value` call (a monkeypatched counter stays at 0); the split encoding (5.1): no integer variable of a built model has a domain wider than `BIG`, and every seeded oracle instance's TAIL, WORST_WORLD and REGRET solves run in the capped subprocess of `test_xi_risk_oracle.py`, which is the regression guard for the crash of 5.1 (the instances of the first audit's private generator are not in the repository and are not reproduced); a hard requirement is a `ValueError`; `|U| < k` gives `NOT_EVALUABLE` with no solve, `EXACT`, an `EXACT` empty membership block; two locked goalkeepers give `UNFIELDABLE` (not `UNKNOWN`) for TAIL, WORST_WORLD and REGRET, `EXACT`, no lineup, and the same `reasons` for all three (`UNFIELDABLE_PROVED`, never the kernel's sentence naming pins); a world's least `UNKNOWN` beside another's `UNFIELDABLE` gives `UNFIELDABLE`, `EXACT` (1.5); a passed deadline gives `UNKNOWN`, no lineup; one per-world optimum `UNKNOWN` gives `UNKNOWN` with that world in `undecided_world_ids`; one per-world optimum `MODEL_INVALID` (monkeypatched) gives `MODEL_INVALID`, completeness `MODEL_INVALID`; an `UNKNOWN` or `MODEL_INVALID` selection (monkeypatched) carries a membership block with no rows and that completeness; `analyze_ties=False` gives a block with no rows and `NOT_REQUESTED`, for which `runtime.is_complete` is false; `claim` is the rule's bare label formatted with `B` and `k` (`RISK_TAIL.format(B=…, k=…)`), with no suffix, and no served string holds `{`; `certificate.growth` is `RISK_GROWTH` formatted with `B` and `|U|` for TAIL and WORST_WORLD and `None` for REGRET; the `WORLD_LEAST` records are one per stage of `kernel.value`'s `stage_statuses`, one `NOT_RUN` record for a call that ran no solve, and `solves` counts every CP-SAT call, `kernel.value`'s included; `tail_boundary_ties` and `binding_world_ids` are ascending; shortfalls use `_q`: a planted `1.344465 / 1.0` coefficient at 100000 gives `_q`'s integer; `world_seed` and `bootstrap_version` reach the certificate unchanged; `TAIL_MENU` plus `WORST_WORLD` at 1 equals the E-13 draft config's `tail_counts` for `B ∈ WORLD_MENU`; the prefix property of 1.4 (`shared_match_weights(games, 12, SEED)` equals the first 12 rows at 40, and the world vectors built from both by the expression of historical.py:203-212 on synthetic frames give `solver._fingerprint` of worlds 0 to 11 equal to that of the 12), checked under the installed numpy, whose version the test records as information and does not assert; determinism; shuffled candidates, requirements and world order give an identical `stable(asdict)` |
| `test_xi_extensions_api.py` | with a synthetic snapshot patched into the router's loader: each route answers 200 with the envelope of 7.5 and passes `runtime.finalize` (providers, `banned_key_paths` with `BANNED_KEY_PARTS`, `scan_labels`); every constant of 7.7 passes `scan_labels` under the format arguments the router uses; an extra field, a non-strict integer (`bootstrap_worlds` 12.0, "12" and `true` included), a branch field of the other `explains`, `explains: "solve"` without `mode`, a non-empty `minimums` with `explains: "floors"` and a `floors` dict, `explains: "solve"` without the opt-in (`CONFLICT_SOLVE_NEEDS_OPT_IN`), a repeated dimension, `TAIL` without a `tail_count`, `tail_count` 1 or an off-menu count with `TAIL`, any `tail_count` with `WORST_WORLD`, `bootstrap_worlds` 0, 40 (until the 40-world timing, X5) or 80, a side requirement without the opt-in (every frontier request without the opt-in among them), an unknown player id are each 422 with a body holding no input value; unknown scenario 404; a missing corpus file 503; the risk overflow is 422; identical requests are one computation (cache `hit`); reordered and repeated locks are one key; a request that sends a default and one that omits it share one key and receive identical declared rows, which hold the decision point and template rows and the opt-in row only when true; a `DEADLINE` reply is not stored; proved terminal replies are stored; `budget` holds the route's seconds; every reply carries every key of 7.5, `model_note` non-null exactly when the in-force set differs from the main model's (a CONFLICT reply with `explains: "floors"` and no opt-in included) and `verdicts` `null` except for RISK; `claim` equals `result.claim` for CEILING, CONFLICT and FRONTIER on every status, and `result.claim` plus one space and the 5.7 suffix for RISK (both suffixes and the no-suffix case tested, `result.claim` left as the tool returned it); `claim` is the state's constant of the 2.2 table for every CEILING state (`CEILING_CLAIM`, `_PARTIAL_CLAIM`, `_NOT_DECIDED`, `_EMPTY`, `CEILING_REFUSED`), never `CEILING_CLAIM` when an end is `NO_SOLUTION`, a `bound_text` is null or no range is reported; no FRONTIER reply whose `status_text` is `FRONTIER_LIMIT`, `FRONTIER_STOPPED`, `FRONTIER_STOPPED_NONE` or `SOLVER_REFUSED` serves a sentence stating completeness; `statements` holds exactly the 7.5 table's constants for the state; CONFLICT's arithmetic sentence: `explains: "floors"` with `floors: {}` and one candidate both locked and excluded is `MINIMAL_CERTIFIED` with members `exclusion:p` and `lock:p`, `statements == [CONFLICT_NO_FLOOR]` and the declared row "Arithmetic: conservative, as a hard-floor query"; `explains: "floors"` with `floors` absent serves `[CONFLICT_CONSERVATIVE]`; `explains: "solve"` in `BALANCE` serves `[CONFLICT_NO_MINIMUM]`; `explains: "solve"` in `SATISFY` made infeasible by locks alone (a player both locked and excluded, reachable minima), whose final set holds no floor, serves `[CONFLICT_HALF_EVEN]`; `CONFLICT_NO_MINIMUM` never on `explains: "floors"`, `CONFLICT_NO_FLOOR` never on `explains: "solve"`; a NOT_PROVEN_MINIMAL reply with a refused member (monkeypatched) serves `CONFLICT_MEMBER_REFUSED` as that member's `member_text`, and a refused restore test `CONFLICT_RESTORES_REFUSED` as its `restore_text`; a RISK membership solve refused (monkeypatched) puts that player under a heading that names no cause; CONFLICT and RISK replies with a refused call are not stored; the default minima are computed rows, not declared rows, and the declared rows hold the point limit, the conflict arithmetic ("half-even, as the solve above" for `explains: "solve"` in either mode) and the decision rule explained; `{"explains": "floors"}` and `{"explains": "floors", "floors": {}}`, no minimum entered, differ in their declared rows ("Floors: every requirement in force at its minimum" against "Floors: none"); every computed `row_id` is a plain word (`[A-Za-z0-9_-]+`); every terminal state of every tool (each status, `FLOORS_UNMET`, `MODEL_INVALID`, a `NO_SOLUTION` end, a bound that is not finite) builds its computed rows through `shell.ledger_row` without a `TypeError`, and the CONFLICT row's `value_text` is `None` on `UNDECIDED` and `MODEL_INVALID`; the FRONTIER row's `value_text` is "1 point" for `FRONTIER` with one point and "{n} points" with several, "{n} points listed; the list is not complete" for `INCOMPLETE`/`POINT_LIMIT` (`max_points = 1` gives "1 point listed; the list is not complete"), for `INCOMPLETE`/`DEADLINE` with points (the monkeypatched stage-2 `UNKNOWN`) and for `MODEL_INVALID` with earlier points kept, `None` with `FRONTIER_STOPPED_NONE` for `INCOMPLETE`/`DEADLINE` with no point (deadline passed at entry) and for `INCOMPLETE`/`LIMIT_REACHED` with no point (a deterministic limit on the first stage-1 solve), `None` for `MODEL_INVALID` at the first solve and for `FLOORS_UNMET`, and "0 points" for `UNFIELDABLE` and `NOT_SATISFIABLE` and in no other state; on FRONTIER the default-minimum rows read "Club median of {label}, the unit of these sums"; printed minima: with `minimums={}` in Satisfy mode, a conflict holding a default floor labels it "Floor on {label}: its default minimum, the median prior starting-XI sum (≈ …)" and a CEILING `minimum_text` of a default is "≈ " and four decimals, while an entered minimum prints as entered; with `explains: "floors"`, `floors: {"progression": 0.25}` and `minimums: {}`, a conflict holding that floor labels it "Floor on {label}: 0.25", never as a default minimum; evidence composes to `HEURISTIC` without the opt-in on CEILING, CONFLICT (`explains: "floors"`) and RISK, and to `EXPERIMENTAL` with it on every tool, the progression range included; an in-scope RISK request (opt-in, `4-3-3`) carries the E-13 `NOT_REGISTERED` payload of its rule's subject and the suffix `RISK_UNTESTED`, a request without the opt-in or in `4-3-1-2` the same payload and `RISK_OUTSIDE_E13`, and `verdicts.risk_report` is `null`; with an executed E-13 stub registered in `verdicts.VERDICTS` (`monkeypatch.setitem`, a `PUBLIC` record with a vocabulary token, a 40-hex lower-case `protocol_commit`, a 64-hex lower-case `results_hash` and a figure; a patched `verdict_for` alone would make `record()` raise `KeyError`, a 500), a `4-3-1-2` request answers 200 (no 422 and no 500) with `verdicts.risk_rule.basis == "REGISTERED_NOT_RUN"`, badge "E-13 · RECORD ONLY · NOT RUN" with E-13's `not_run_statement`, `figures == []`, `protocol_verdict` null and the claim ending with `RISK_OUTSIDE_E13`, while an in-scope `4-3-3` request on the same stub carries the executed payload and no suffix; `E13_SCOPE` equals the E-13 draft config's formation, `decision_tiers`, `tail_counts`, scenarios and `expected_active_requirements`; a REGRET reply's ledger row holds two pairs per binding world, and no served number equals a component of `(M − M*, T − T*)` for any world unless it also equals a served pair component or sits under a path of the same allow-list as the encoding check (ids, counts, seeds, `quantization`, `LossPair` and `TailSums` fields), so a small difference that coincides with a world id or a count does not fail the test; the encoding check of `test_xi_risk.py` repeated on the served reply; `GET /api/xi/extensions` is corpus-free and finalized, the router's copy of the requirements equals `decision_inputs`'s measured requirements field by field (id, label, metric, and the flag against `evidence_class == "RESEARCH"`), it carries `frontier_opt_in_text`, and no `TAIL` option has `tail_count` 1; FRONTIER texts, on a 1-point and a 3-point `d = 2` reply: `point_texts` equal `V_i / q` exactly, `plot_x` and `plot_y` equal their definition recomputed in `Fraction` and rounded half-even at six places (`0.5` on a zero range); on the router's pure text builders (7.5), which take cases no route can pose, in club medians on an instance with `n_r ≠ 1` (`n = (20, 18)`, two slots, players a (9.1, 8.2), b (10.3, 7.7), c (8.0, 9.9)): for {a, b} `raw_sum_texts` are `0.97000` and `0.88333`, not `19.4000` and `15.8999`, `allowance_texts` equal `a_r / (2q)` rounded up at five decimals, and on every served point and dimension `|S_r / n_r − V_r / q| ≤ a_r / (2q)` in `Fraction` and `|Decimal(raw_text) − Decimal(point_text)| ≤ Decimal(allowance_text)` on the texts; a case with `a_r = 1`, on the same builders, pins rounding down against outward rounding; through the route at `q = 100000`, a one-point instance whose point texts differ from every witness's raw texts: a synthetic snapshot with `requirement_minima` 1.0 for the three measured requirements (so `n = 1`), the opt-in and dimensions (progression, left_pass_origins); players a, b, c eligible for exactly the two central-midfield slots, with (progression, left, right) values a (0.299996, 0.199997, 0.0), b (0.299997, 0.199998, 0.0), c (0.299998, 0.199996, 0.0), and nine fillers each the only candidate eligible for one of the other slots, 0.0 on all three metrics; every XI has `V = (60000, 40000)`, so one point, `COMPLETE`, `FRONTIER_COMPLETE`, `plot_x = plot_y = 0.500000`; whichever XI is the witness, `point_texts` are `0.60000` and `0.40000` while `raw_sum_texts` are `0.59999` and `0.39999`, so the point prints `V / q` and not the witness's raw sums, `allowance_texts` are `0.00005` (`a_r = 10`), and the inequality holds on the texts and in `Fraction`; `status_text` per branch: `FRONTIER_COMPLETE`, `FRONTIER_LIMIT` with `{n} = max_points` for `POINT_LIMIT`, `FRONTIER_STOPPED` with `{n}` the listed count for a `DETERMINISTIC_LIMIT` and for a `WALL_CLOCK` stop with at least one point, `FRONTIER_STOPPED_NONE` with none, `SOLVER_REFUSED` for `MODEL_INVALID` (and `SOLVER_REFUSED` once in `statements`), `null` for the empty states; `FRONTIER_WITNESS` in `statements` exactly when a point is listed; the call signatures of `planning._built_once`, `planning._outward` and `planning._minimum_text` and the values of `planning._APPROXIMATE` and `planning._DERIVED_PLACES` are pinned, as X9 pins the kernel's; importing `galactico.api.xi_extensions` in a subprocess loads no `ortools` module, no `squad.kernel`, no `optimization.snapshots` and no tool module, and leaves `_match_snapshot.cache_info().currsize == 0` (7.1, "Imports"); the router's restated `EXPERIMENTAL_OPT_IN_ERROR`, `TAIL_MENU` and tool sentences equal the objects they restate; snapshot immutability: the router loader's snapshot, and a snapshot patched into `decision_lab.snapshot`, deep-copied before and compared after each new route, are unchanged; with all sixteen in-flight places held each new POST answers 429 with `Retry-After`, and REGRET holds a long-job place; two concurrent requests of different routes on one `(scenario, worlds)` build the snapshot once (the gate); `corpus_token()` equals `planning.corpus_token(planning.FLAGSHIP)`, with the tmp-corpus pattern of `tests/test_planning_api.py:437`; R13: the five shipped `/api/xi/*` paths, their methods and their replies on the synthetic snapshot are byte-identical in an app with and without this router; no path is served twice |
| `test_xi_extensions_render.py` | under node, the harness of `test_shell_render.py` (the page-scope names first, then `labs-shared.js`, then `xi-extensions.js`, which loads without touching `document`; `mount` is never called), the render functions on replies built by the real router on the synthetic snapshot: no `undefined`, `NaN` or `[object`; hostile strings escaped; every digit run in the visible text (`shell.visible_text`) lies inside a server string printed at that place (so the "90" of a label is covered) or is the decimal form of a server number field on the 8.3 allow-list at the path the renderer reads (the integer fields and the three deterministic-limit fields), after removing the `aria-label` and `title` the kit's `Shell.evidenceBadge` and `verdictBadge` write ("rung 6 of 7; 1 is observed, 7 is experimental": `LADDER.length` and the literal 1 of the kit's ladder sentence are kit constants, not reply numbers) and any other fixed kit text, an exemption the test states; rows in reply order, every table built from a served row list (7.5) and none by looking an entry up by id; membership groups printed in server order under server headings; two distinct frontier points never print identical coordinate texts; every frontier row and circle has the same class list and `plot_x`/`plot_y` appear unchanged as coordinates; no element is marked selected on arrival; the markup of all four panels together, each with its ledger (prefixes `conflict`, `ceilings`, `frontier`, `risk`), has unique ids, and the ledger rewrite throws when either kit id is absent or appears in a form it does not know; the declared table, in both kit forms, has a single `class` attribute that contains `xi-ledger-declared`; every selector of `xi-extensions.css` starts with `#xi-extensions` or names only `xi-` classes or ids (a Python parse of the sheet); `scan_labels` of the visible text is empty; no `%` in the risk markup; empty, `DEADLINE`, `LIMIT_REACHED`, `NOT_EVALUABLE`, `UNDECIDED`, `NOT_PROVEN_MINIMAL` (with an undecided and a refused member, printing `CONFLICT_MEMBER_UNDECIDED` and `CONFLICT_MEMBER_REFUSED`), `MODEL_FEASIBLE`, `MODEL_INVALID`, `UNFIELDABLE`, `NOT_SATISFIABLE` and `FLOORS_UNMET` (with `FLOORS_CONSERVATIVE`), a CEILING end with no bound, and opt-in-missing states each render their sentence; the conflict panel prints the served `claim` and never `CONFLICT_CLAIM` by name, the ceilings panel the served `claim` in each state (`FIELDABLE` complete and partial, `UNKNOWN`, `UNFIELDABLE`, `MODEL_INVALID`, and the API-only `NOT_SATISFIABLE` and `FLOORS_UNMET`) and never `CEILING_CLAIM` by name, and the frontier panel the served claim, with no completeness sentence in its visible text on `LIMIT_REACHED`, `DEADLINE` and `MODEL_INVALID`, `FRONTIER_WITNESS` under its table, its ledger and its evidence badge, and, on an `INCOMPLETE` or `MODEL_INVALID` reply with no point, `Shell.notCertified` and the status sentence with no table and no circle; the risk certificate block prints `certificate.growth` for TAIL and WORST_WORLD; `xi-extensions.js` declares nothing in script scope. A unit test (Python) asserts that `web/xi.html` with the five insertions of section 12 removed has the LF-normalised sha256 of the shipped file (section 10), and that the two script tags and the mount call stand before the inline script (8.1) |
| `e2e/xi-extensions.spec.js` | `/xi` solves and the panels mount with every button disabled until `xi:solved`; after the page's first solve `#solve-ceilings` is enabled, `#solve-frontier` and `#solve-risk` are enabled only once their selects hold a valid choice (8.2), and the conflict panel is shown only when the main solve is `INFEASIBLE`; the corpus-free `GET` is the only new request on load; no `pageerror` and no console error anywhere in this spec; the shipped flows (apply minima, a lock, a preset, a mode change, as `repairs.spec.js` drives them) with the panels mounted send no new POST and log no console error; after applying minima with the opt-in unticked, pressing `#solve-ceilings` sends only the progression minimum, answers 200 and shows `SIDE_MINIMA_SET_ASIDE`; ceilings: the request carries the main locks and exclusions, and each cell's text equals the reply's `*_text` exactly; frontier: the selects start empty, the opt-in starts unchecked and the opt-in sentence shows; after ticking it and choosing two dimensions the request carries them in order with the opt-in, the main locks and exclusions and no minima; rows equal the reply's points in order and print `point_texts`; the frontier ledger's rows equal the reply's declared and computed rows and the evidence badge reads the served class, `EXPERIMENTAL`; every row and circle has equal computed style; after opening a point only that row's outline changes; risk: the selects start empty and the button is disabled; options equal the server's `rule_options` in order; a TAIL request carries the main locks, exclusions and filtered minima, `rule`, and `bootstrap_worlds` and `tail_count` as JSON integers, and the tail world ids equal the reply's; a REGRET request at `B = 12` renders the binding worlds with two pairs each; the certificate shows B, seed, fingerprint and discarded count; the panel text holds no `%`; the badge's text equals the reply's `verdicts.risk_rule.badge` (never a literal, which would fail once E-13 is registered); conflict: with mode Satisfy and the progression minimum at 1000 the main solve is INFEASIBLE, the conflict panel appears, the explain request carries the opt-in, `explains: "solve"`, `mode: "SATISFY"` and no `floors` key, the panel prints the served claim and the served arithmetic sentence (`CONFLICT_HALF_EVEN`), and the rows equal the reply's `member_rows` in order, holding `floor:progression`, each with its restore sentence; a frontier reply fulfilled from a recorded `DEADLINE` body renders the deadline sentence, and one fulfilled from a deadline-at-entry body (no point) shows `FRONTIER_STOPPED_NONE` with no table and no circle; stale replies (8.1, 8.2): with a `/api/xi/ceilings` reply held and then a `#lock-player` click, and again with a held `/api/xi/risk/tail` reply and an input event on `#minimum-inputs`, the held reply released after the change is not rendered, the panel is cleared, its button stays disabled until the next `xi:solved`, and no console error is logged; the page has no duplicate id; the computed `overflow-wrap` of a declared-ledger cell in the new panels is `anywhere`; at 390 and 320 px `#xi-extensions` has `scrollWidth ≤ clientWidth`; the shipped panels behave as before (the tradeoff, alternatives and repairs specs are unchanged and still pass). Screenshots (X14): the shipped `labs.spec.js` rewrites the tracked `docs/screenshots/11-xi-lab.png` and `12-xi-mobile.png` on `/xi`; they are regenerated and inspected only where the corpus is present, and a run or a commit made without it restores them with `git restore docs/screenshots` and never commits a capture nobody looked at |

**Slow tests** (`@pytest.mark.slow`, skip without the corpus), one per tool file, on the
6 May Madrid snapshot: CEILING ends equal a brute-force enumeration of the real snapshot's XIs;
the three-dimensional FRONTIER under the opt-in equals the brute-force nondominated set (the
count is compared with the brute force, not with a pinned number, section 1.6), and if the brute
force finds more than `max_points` points the test asserts `LIMIT_REACHED` and the
lexicographic-descending prefix instead; CONFLICT
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
parity of section 13 calls CEILING with no floors (equivalently floors at 0, which bind nothing
on non-negative rates, as `attained` sets every active minimum to 0, planning.py:1160) and
compares integer value, integer bound and certification, and each
witness's exact sum inside the band `[(n_r / q) · I⁺_r − e_r, (n_r / q) · I⁺_r + e_r]` (2.4).

**Not changed:** every existing test file. `test_xi_solver.py`, `test_xi_tradeoffs.py`,
`test_xi_alternatives.py`, `test_tradeoff_oracle.py`, `test_decision_api.py`,
`test_squad_kernel.py`, `test_absence_stress.py`, `test_candidate_injection.py`,
`test_role_brief.py`, `test_planning_api.py`, `test_transfer_api.py`, `test_team_snapshot.py`,
`test_evidence_mapping.py`, `test_lab_runtime.py` (except the pinned `LONG_ROUTES` set, to
which the root adds `xi.risk.tail`, X5), `test_web_shell.py`, `test_shell_render.py`, `test_conftest.py` and the
e2e specs pass unchanged; a failure in any of them is a defect of this work, not a reason to
edit it.

## 10. Hashes, fingerprints and provenance

| Object | Rule |
|---|---|
| source fingerprints | `kernel.source_fingerprints(*paths)` (LF-normalised sha256, keys relative to the repository root, returned as a dict sorted by key, kernel.py:225-238, so the order of the paths means nothing). Every tool: its own module plus `squad/kernel.py`, `xi/solver.py`, `xi/tradeoffs.py` and `xi/domain.py`. `optimization/historical.py` is not listed: no tool imports it, and the snapshot's own provenance carries its lineage |
| input contract | `kernel.input_contract` (canonical model, seed, both kernel policies, the deterministic limit, sources, OR-Tools version) plus the tool's declarations: floors, the compared minima `{requirement_id: m_r}` (CEILING: for a floored requirement the kernel model holds `φ_r`, so `m_r` would otherwise be in no hashed input), dimensions, `max_points`, rule, `k`, `B`, `world_seed`, `bootstrap_version`, the world fingerprint, the arithmetic, and for CONFLICT `mode` and the floor set it implies (two `explain_solve` calls that differ only in `mode`, with `hard=False` requirements, floor different sets); never the deadline, and never a solve time (1.5) |
| input fingerprint | `kernel.fingerprint({"version": TOOL_VERSION, "contract": input_contract})`; order-free because the kernel canonicalises its inputs |
| lineage | `scrub_lineage(snap.provenance)`: a new result never inherits a prior certification; the tools' own keys use the prefixes the kernel already reserves |
| frozen files | unchanged bytes; existing tests already pin `historical.py` (E-08), and the four kernel sources |
| line endings | every hash LF-normalised (`core.autocrlf=true` on Windows checkouts) |

## 11. Pre-merge review checklist

The reviewer signs each line before the root registers the router.

1. No frozen file and no root-owned file is in the diff; `kernel.py` is byte-identical, and a
   test pins the private members of it the new modules use (X9).
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
13. **DISSENT 2, ruled X2.** `conflict.py` exports `explain_solve` (`SHORTFALL_POLICY`) and
    `explain_floors` (`HARD_POLICY`), each with its tests against the oracle;
    `ConflictRequest.explains` is `Literal["solve", "floors"]` and routes to them;
    `explains: "solve"` without the opt-in is refused with `CONFLICT_SOLVE_NEEDS_OPT_IN`; the page
    explains the main solve with `explains: "solve"` and the main solve's mode and prints
    `CONFLICT_HALF_EVEN`; every reply names its arithmetic.
14. **DISSENT 4 and R13, ruled X4, X12, X13 and X14.** The five `xi.html` edits of section 12
    and nothing else, edits (3) and (4) just before the inline script (X13); every shipped XI
    test and browser spec passes unchanged; no POST until the panel's own button is pressed and
    no request that reads the corpus, the one corpus-free `GET /api/xi/extensions` on load
    allowed (X12); the tracked XI screenshots regenerated and inspected only where the corpus is
    present, and restored with `git restore docs/screenshots` otherwise, never a capture nobody
    looked at committed (X14). No `web/xi-extensions.html` and no `/xi/extensions` route exist
    (8.4); the e2e spec targets `/xi`.
15. **Long route and run time, ruled X5.** `xi.risk.tail` is in `runtime.LONG_ROUTES` and in the
    pinned set of `tests/test_lab_runtime.py` (the root's edit, section 12). The risk routes
    accept, and the `GET` reply offers, 12 worlds only until the TAIL and REGRET selection and
    membership solves have been timed at `q = 100000` on the Madrid worlds at `B = 12` and
    `B = 40` (times, statuses and peak memory only, 7.1), with the numbers in ADR-0030; 40 joins the menu only
    in that change.
16. The snapshot is loaded only through the gated loader of 7.3; `decision_lab.snapshot` and
    `runtime.match_snapshot` are not called by the new router.
17. No `objective_value` is compared, stored or served as an integer; every integer comes from
    `solver.value` or a Python recomputation (1.5). No risk variable has a domain wider than
    `BIG` (5.1, split encoding).
18. Every served claim is the constant its state selects (CEILING 2.2, CONFLICT 3.4, FRONTIER
    its one constant, true on every status, 7.7); no sentence served on an unproved end, an
    undecided or refused set, a cut list or an undecided empty list states what only a proved
    one would, and no ledger row draws an undecided count as zero.
19. Every selector of `xi-extensions.css` is scoped to `#xi-extensions` or an `xi-` name (8.3);
    the ledger rewrite replaces whole attribute runs (8.1).

## 12. Requests to the root

| File | Change |
|---|---|
| `galactico/api/player_lab.py` | after `app.include_router(transfer_router)` (player_lab.py:59): `from .xi_extensions import router as xi_extensions_router` with the other router imports, and `app.include_router(xi_extensions_router)`. The module imports no solver and reads no data at import, like the others: the tool modules are imported inside its functions only, and a subprocess test asserts it (7.1, "Imports") |
| `web/xi.html` (granted, X4, X13; item 14) | five additive edits, nothing else: (1) in `<head>`, after the `labs-shared.css` link: `<link rel="stylesheet" href="/static/xi-extensions.css">`; (2) between the closing `</section>` of `#tradeoff-panel` and the `<details>` that holds `#provenance`: `<div id="xi-extensions"></div>`; (3) immediately before the inline `<script>` (X13; it was "after the inline `</script>`" in the text X4 granted): `<script src="/static/labs-shared.js"></script><script src="/static/xi-extensions.js"></script>`; (4) after those, still before the inline `<script>`: `<script>XiExtensions.mount(document.getElementById('xi-extensions'))</script>`; (5) in `solve()`, `document.dispatchEvent(new Event('xi:invalidated'))` as its first statement after `busy=true`, and `document.dispatchEvent(new CustomEvent('xi:solved',{detail:{input:solvedInput,status:d.solution_status}}))` immediately after `render();`; in the `#minimum-inputs` input listener, the same `xi:invalidated` dispatch. `tests/test_web_shell.py` (nav and shared stylesheet) and `tests/test_shell_render.py` (page-scope names) are unaffected. Running the shipped `e2e/labs.spec.js` after these edits rewrites the tracked `docs/screenshots/11-xi-lab.png` and `12-xi-mobile.png` (labs.spec.js:148, 153) full-page, now showing the new panels, and `README.md:26` embeds the first. X14: they are regenerated and inspected only where the corpus is present; a commit made without it restores them (`git restore docs/screenshots`) and never commits a capture it could not look at |
| `galactico/api/runtime.py`, `tests/test_lab_runtime.py:123` (granted, X5; item 15) | add `"xi.risk.tail"` to `LONG_ROUTES` (it enumerates every candidate for membership, the case the set's docstring names) and to the pinned set in the test |
| `web/labs-shared.js` | no change: the optional `prefix` argument to `Shell.ledger` was declined as not needed (X11); 8.1 rewrites the ids |
| `KNOWN_LIMITATIONS.md` | Line numbers at `fda88c2`. The `decision_lab.snapshot` limitation this row once asked to add now is already in the file (:79-82, commit `1e200f4`), so nothing is added now. When the tools ship: replace the minimal-conflict bullet (:77-78, "Infeasibility diagnostics do not yet certify a minimal conflicting constraint set. No constraint is silently relaxed.") by what CONFLICT certifies and in which arithmetic; in the hard-floor bullet (:90-93) replace "A maximum is not a Pareto-frontier certificate" by "a maximum is not a frontier; the frontier explorer lists the nondominated sums of declared requirements at the shipped quantisation, never a ranking"; in the selection-bias bullet (:124-128) replace "no football-calibrated correction, robust/CVaR objective or minimax-regret mode ships" by the declared-risk modes, their claim, and that E-13 has not tested them; to the reached/ceiling bullet (:194-206) add that XI Lab's CEILING brackets the largest sum and Transfer Lab's numbers are unchanged; the scope paragraph (:397-401) drops "certified Pareto frontiers, declared-risk XI modes, minimal conflict sets". Add: the experimental opt-in is needed for any frontier with the shipped requirements; with declared floors, XI Lab's ranges and frontier are taken over the conservative integer model, and an XI that meets a raw floor with less than `(a_r + 1)/100000` of the club median to spare (one unit for each place counted and one more) can be left out; the risk overflow refusal; WORST_WORLD grows with B; the risk menu offers 12 worlds until the 40-world solves are timed (X5); after a corpus rewrite in a running server, the XI Lab conflict panel can explain a model built from the files as they are now while the main solve above it still runs on `decision_lab.snapshot`'s older copy (:79-82), so the explanation can differ from that solve's model, and can even find it feasible (7.3) |
| `README.md`, `ARCHITECTURE.md` | the four modules, the router and the two web files in the module tables; the XI Lab section names the three additions and the opt-in |
| `DECISIONS.md` | ADR-0030 "XI exact additions: ranges, minimal conflict, frontier, declared-risk modes": Problem (the four limitations), Decision (sections 1.2, 3.3, 4.2, 5.1 of this file), Evidence (the oracle and parity tests, filled in by the builders), Numerical boundary (the three policies, the allowance, the split encoding and the overflow guard of 5.1, integers read with `solver.value` and never from `objective_value`, 1.5), Alternatives rejected (calling `maximize_requirement` per requirement; QuickXplain; a weighted sum for the frontier; a probability for a tail; a default dimension; editing `kernel.py`; the literal O8 BIG, which a sum of `k` encodings can carry past; encoding variables with a domain of size `E_max`, which crashed CP-SAT on 2 of 144 seeded TAIL selections (5.1); CP-SAT parameters as that fix; a stand-alone page beside `/xi`, X4), Relation to ADR-0020 (its rejection of a weighted sum of the two stages as a search device stands for the kernel; O8 overrides it for the risk modes only, because BIG is exact by construction, never serialised, and tested for both the carry and the leak), Relation to ADR-0024 (the router's snapshot loader is behind the build gate; `xi.risk.tail` is a long route, X5), the run times and peak memory of item 15 (recorded in the change that adds 40 worlds to the menu), Confidence, Reversal (E-13's verdict relabels the risk modes) |
| `ROOT-DECISIONS.md` | no change requested: section 2.7 rules this file's DISSENT, gates and open questions (X1 to X11) and the three points of the first audit (X12 to X14, 16 October 2026), and the 2.6 opening paragraph records that an OR-XI spec exists. The second audit raised no point for the root |
| `docs/research/north-star/README.md` | its row for this file should read: draft, attacked once by three lenses, gates ruled in ROOT-DECISIONS 2.7 (X1 to X14), audited twice in five scopes with every confirmed blocker applied, nothing awaiting a root ruling, open items with E-13's owner, nothing built |
| `galactico/optimization/xi/__init__.py` | no change: the router imports the four modules by path |
| `pyproject.toml`, `playwright.config.js`, `.github/` | no change: `e2e/` is discovered as it is |

Rulings received on the three points the audit of 14 October 2026 raised under X4 (ROOT-DECISIONS
2.7, 16 October 2026); this file specifies the ruled state:

- **R-A, the `GET` on mount** (S5-api-page-tests-4). **Ruled: X12.** X4's "send nothing until
  their own button is pressed" forbids a solve or any request that reads the corpus; one
  corpus-free `GET /api/xi/extensions` on load, for the panels' fixed sentences and menus, is
  allowed (8.2).
- **R-B, where edits (3) and (4) go** (S5-api-page-tests-22). **Accepted: X13.** They go just
  before the inline script, so the panels are mounted before the first `xi:solved` can fire;
  they remain additive and X4's condition stands (8.1).
- **R-C, the committed screenshots** (S5-api-page-tests-26). **Ruled: X14.** The tracked XI Lab
  screenshots are regenerated and inspected only where the corpus is present; a commit made
  without it restores them (`git restore docs/screenshots`) and never commits a capture it could
  not look at (section 9, e2e; item 14).

The second audit (16 October 2026) raised no point for the root.

## 13. Reconciliation

**With the E-13 draft** (`protocol-drafts/E-13-declared-risk-selection/PIPELINE.md`,
ASSUMED INTERFACES 1 to 3). Interface 1 assumes one function returning `solution_status`
(`"OPTIMAL"`), `assignments` and per-world pairs. This file provides
`declared_risk_selection(..., rule, tail_count)` returning `status` (`"CERTIFIED"`), `lineup`
and `world_losses`; E-13's two adapters `_risk_call` and `_risk_world_pairs` map them, which
its table allows. `_risk_call` must also fill the arguments interface 1 lacks and
`declared_risk_selection` requires: `world_count = len(worlds)`, a world seed and a version
string of E-13's own (its audit builds its own split-half worlds, with no snapshot seed and no
`bootstrap_version`), and `deadline = time.monotonic() + ` its solver time limit in place of
`time_limit`; `rule="WORST_WORLD"` accepts `tail_count` `None` or 1 (5.7), so the `k = 1` that
E-13's config gives `WORST_WORLD` (config.json:13-16) passes. `_risk_world_pairs` reads the
pairs from the result's `world_losses`; `risk.world_losses` is an independent re-evaluation
helper, not that adapter (5.7). Interface 2 (BIG above the largest sum of `T` over the used worlds, `_q`
coefficients, the discard rule, `k` not recomputed) is met, with BIG also above twice the
largest total for the regret. One difference to resolve before E-13 is frozen: the draft's
protocol discards a world "in which any candidate has zero exposure", the product discards one
in which a non-excluded player lacks a needed metric at a slot he is eligible for (ROOT 2.4,
"exactly as the shipped bootstrap does"). The two differ for a candidate with no exposure in
a world who is eligible at no slot a requirement in force applies to: the requirements apply to
outfield slots only, so a goalkeeper with no minutes in a world discards it under the draft's
rule and not under the shipped one. They also differ for an excluded candidate with no
exposure in a world: the shipped rule ignores him, because his set of needed metrics is empty
(solver.py:551-559), while the draft's discards the world (E-13 preregistration.md:81). The
reconciler checks by structure whether either case occurs in the Madrid worlds, and E-13 adopts
the shipped rule or records both differences. Interface 3
(file name, menu) is met for `B = 12` now, and for 40 once the timing of X5 adds it to the
menu (7.1), with six reconciliation items for the E-13 draft's owner: its
`risk_solver_oracle_tests` (and so the `lf_sha256` list of PIPELINE.md:580, "which oracle
vouched for the solver") must hold `tests/xi_exact_oracle.py` beside
`tests/test_xi_risk_oracle.py`, because the brute-force logic lives in the first and could
change without moving the second's hash; by the same reasoning its `source_paths`
(config.json:239-253) must also list `galactico/optimization/squad/kernel.py` and
`galactico/optimization/xi/tradeoffs.py`, because `risk.py`'s behaviour runs through
`kernel._background`, `_tables`, `_expression` and `value` and through `tradeoffs._scaled` and
`_finite`, and `kernel.py` is not frozen; the product's menu is the draft's `tail_counts` exactly
(config.json:13-16): `WORST_WORLD` at 1 and `TAIL` at 2, 3, 6 and 4, 10, 20, so
`risk_rule:WORST_WORLD` and `risk_rule:TAIL` never name the same computation; and the
`risk_report` statistic (5.7). E-13's own statistic is `M` of the worst world and the mean `M`
over the `k` tail worlds, in normalised units, and interface 6 expects its sentence "printed as a
figure note under the objective lines"; this file serves the tail sums `Σ M`, `k` times the
mean, and prints no figure note. Either the product serves E-13's statistic (`Σ M / k` as an
exact server text, labelled as the mean largest shortfall over the `k` tail worlds) with the
`risk_report` payload attached to that figure and a figure note on the risk panel, or E-13
changes its own statistic to the sum before commit P. Until one is chosen,
`verdicts.risk_report` is `null` and no figure carries it (5.7); option (a) is the one
exception to section 5's rule that no average over worlds is printed. Fifth, the requirement set
of E-13's token scope: its Madrid part runs with the three measured requirements in force
(`expected_active_requirements`, config.json:124), and its preregistration says it shows
nothing about a requirement set it did not run, while the product's default risk request,
without the opt-in, holds progression alone (1.3). The router treats such a request as outside
`E13_SCOPE` (5.7) until E-13 either lists the requirement set in its token scope, as this file
now reads it, or states that its `risk_rule` tokens hold for any requirement set. Sixth, the
interface-1 details above (`world_count`, world seed, version string, deadline, and
`WORST_WORLD` at `tail_count` 1). The token scope of E-13 (its formation, tiers, tail counts,
snapshots and requirement set) is honoured by the router as 5.7 states. The split-sample tool of row 7 is not in this file (OPEN
QUESTION 2; deferred to E-13 by X8).

**With `planning.attained`.** Transfer Lab's reached and ceiling numbers come from the shipped
maximiser with minima set to zero (planning.py:1119-1208) and are pinned by
`test_planning_api.py` and `test_transfer_api.py`. They are not rewired to CEILING: that would
move served text (R13). A slow test asserts that on the planning problem `attained` solves,
with non-negative rates, CEILING on `problem.candidates`, `problem.requirements`,
`problem.formation`, the locks and the exclusions with no floors (equivalently floors at 0,
which bind nothing on non-negative rates; `attained` replaces every active minimum by 0,
planning.py:1160, so 2.4's recipe of floors at every active minimum would bind on the club
medians and shrink `𝒳_F`) has, at its LARGEST end, the integer value, the integer bound and the
certification of the `maximize_requirement` call `attained` makes, and that each witness's
exact sum lies in the band `[(n_r / q) · I⁺_r − e_r, (n_r / q) · I⁺_r + e_r]` of 2.4, so the two
cannot drift silently. The witnesses
themselves are not compared: two exact solvers with different models (the kernel's symmetry
breaking, different limits) can return different XIs with one integer value (4.1).

**With KNOWN_LIMITATIONS and the frozen solver's diagnostic.** `solve_xi` keeps saying
"Diagnostic reasons; not a minimal conflicting set" in its provenance; that remains true of
`solve_xi`. CONFLICT is the separate, certified answer, and the page prints it beside the
shipped diagnostic, never in its place.

## 14. As built (18 October 2026)

The four tools, the router and the page parts were built from this file (commits `b744512`,
`a23c5c0`, `5ae2402`) and reviewed against section 11 by three reviewers, whose findings were
fixed and verified (`e24e67f`). Where the code departs from the text above, the code is the
record and the departure is accepted by the root:

| Section | As built |
|---|---|
| 0, 6 | The oracle was written whole by one author who built none of the four tools, from sections 1 to 5 alone, not in four parts by the tool builders. This is the stricter form of the same independence (ROOT 4). Its records are `collections.namedtuple` subclasses and its generator a hand-written SplitMix64 stream, because it may import only `itertools`, `math`, `fractions` and `collections`; it carries `from __future__ import annotations`, a compiler directive its AST test allows |
| 6 | The oracle functions the table abbreviates take the instance, the worlds and the declarations as keywords (`world_pairs(instance, x, *, worlds, excluded)`, `tail_optimum(instance, k, *, worlds, locked, excluded)` and the like) |
| 1.5, 10 | Deterministic times are recorded at ten significant digits by all four tools through one helper in `ceilings.py`; times are diagnostic and enter no input contract, so `frontier.py` and `risk.py` do not list `ceilings.py` among their source fingerprints |
| 5.7 | A risk stage that was not run after a decided stage has its own `NOT_RUN` record; the risk input contract names its search `selection_search` |
| 7.5 | Empty membership groups are omitted from a risk reply; the menu reply carries `world_count_texts`, the labels of the world menu; text fields the page prints and the table did not name (`attained_note`, `bound_note`, `minimum_reached_text`, `minimum_missed_text`, `dimension_labels`) are served so the page never picks an entry out of a list |
| 7.6 | Declared rows follow `planning.declared_rows` order; a one-member conflict set reads "1 declaration" |
| 8 | The section's lead sentence names the model each panel answers on; the page's listeners write any fault into the section's status line instead of raising into a shipped flow |
| 11 item 15 | The 40-world risk option is not offered (`OFFERED_WORLDS = (12,)`) until its solves are timed on the corpus |

## DISSENT

The root ruled every item on 14 October 2026 (ROOT-DECISIONS 2.7). Each item keeps its
argument and is followed by its ruling; the sections above specify the ruled state.

1. **ROOT 2.4, "two policies".** The shipped code has three named integer rules, not two:
   `_q` (float division, then half-even), the conservative floor/ceil, and the exact half-even
   objective of the hard-floor query (tradeoffs.py:37, 307). The last two are both "exact
   Fraction"; the first and last are both "half-even" and disagree on about one coefficient in a
   thousand. The design satisfies the ruling's intent (reuse, name each, invent none) by naming
   all three in 1.2 and assigning each quantity to one; the wording needed amending so that a
   later builder does not merge `_q` and the objective rule.
   **Ruled: X1, ROOT-DECISIONS 2.7.** Accepted: 2.4 names the three policies the shipped code
   has, `SHORTFALL_POLICY`, `HARD_POLICY` and `OBJECTIVE_POLICY`; a new tool names which applies
   to each quantity and never mixes two inside one quantity (1.2).
2. **ROOT 2.4, "hard constraints use the conservative policy", against the shipped Satisfy
   rule.** XI Lab's Satisfy solve, pinned by R13, enforces its minima in `_q` half-even integers
   (solver.py:274-275), not conservatively. A minimal conflicting set computed in the
   conservative arithmetic can be a set the half-even solve does not find infeasible, and the
   reverse holds for minimality. Following the principle the root accepted for the role brief
   (ROOT 2.6 D2: the arithmetic of the solve it explains), `explain_solve` uses `_q` and says
   so; every hard floor a reader declares to a new tool is conservative, as 2.4 says. The two
   variants are separate functions with separate names so neither can be mistaken for the
   other.
   **Ruled: X2, ROOT-DECISIONS 2.7.** Accepted: a minimal conflicting set is computed in the
   arithmetic of the solve it explains. `explain_solve` (half-even `_q`, explaining XI Lab's
   Satisfy solve) and `explain_floors` (conservative, explaining a hard-floor query) are both
   built and routed (`explains: "solve" | "floors"`), each reply names its arithmetic, and the
   page explains the main solve with `explain_solve` (3.1, 7.1, 7.2, 8.2; section 11, item 13).
   Every hard floor a reader declares to a new tool stays conservative.
3. **ROOT 2.5 O8, the size of BIG.** "Strictly larger than the largest possible total"
   preserves the lexicographic order for one world but not for a sum of `k > 1` encodings
   (summed totals can carry into the `M` digit) nor for a regret (the `T` difference ranges over
   twice the total). E-13's DISSENT 3 says the same about TAIL. The design takes `BIG = 2 · |U| ·
   T_bound + 1`, which meets O8's literal requirement and both sharpenings; with the literal
   minimum, TAIL and REGRET would be different rules from the ones described to the reader, and a
   test shows an instance where they are. The price is the overflow refusal of 5.1 for very
   large declared minima.
   **Ruled: X3, ROOT-DECISIONS 2.7.** Accepted: BIG is `2 · |U| · T_bound + 1` (5.1); a declared
   problem whose encoding would overflow is refused with its own sentence (`RISK_OVERFLOW`); BIG
   is never serialised.
4. **R13 against ROOT 2.3, where the page parts live.** 2.3 asks for XI Lab additions; R13 asks
   for new pages and leaves shared files to the root. A separate page would have to repeat the
   scenario, template, lock and minimum controls and would explain a solve the reader cannot see.
   The design keeps every new line in new files and asks the root for five additive edits to
   `xi.html` (section 12) that change no shipped element but do change the page's bytes and its
   script graph.
   **Ruled: X4, ROOT-DECISIONS 2.7.** The five additive edits are granted: they add page parts
   2.3 asks for and change no shipped element. Condition: every shipped XI test and browser spec
   passes unchanged, and the new panels send nothing until their own button is pressed (8.1,
   8.2; section 11, item 14). The fallback page of 8.4 is not built.
5. **ADR-0001 / ADR-0019 opt-in on the new XI parts, against XI Lab's own default.** XI Lab's
   main solve has the two side requirements in force without an opt-in (legacy, kept by
   ADR-0019). The new parts follow ADR-0001 and O7 instead: progression alone unless the reader
   opts in. Two consequences follow, both accepted by the ruling: with the shipped
   requirement set a frontier needs the opt-in every time (only one requirement is not
   experimental), and the minimal-conflict display of the main solve must ask the reader to opt
   in before it can explain that solve. The alternative, new parts that mirror the main solve's
   three requirements by default, would render `EXPERIMENTAL` numbers on a new surface without an
   opt-in.
   **Ruled: X6, ROOT-DECISIONS 2.7.** Accepted: the new XI parts default to progression alone;
   the two side requirements enter only with the explicit opt-in, and a conflict that explains
   the main solve asks for it (1.3, 8.2); `MODEL_DIFFERS` says so whenever the two models differ.
6. **Deviation reported, not a dissent: CEILING does not call the shipped maximiser.** 2.1 says
   "generalise the existing hard-floor maximiser". Calling it per requirement and direction would
   make every active minimum a floor (it has no other mode), would lack the minimiser, would run
   without a deterministic limit, and would bring warnings that fail the copy guard into the
   reply. CEILING reproduces its objective and floor arithmetic exactly and a parity test ties
   the two.
   **Ruled: X7, ROOT-DECISIONS 2.7.** Accepted: CEILING reproduces the shipped maximiser's
   arithmetic and does not call it; the parity test of 2.4 and section 9 ties the two.

## OPEN QUESTIONS

Every question below is ruled or settled (ROOT-DECISIONS 2.7); 2 and 3 are deferred to E-13 by
ruling.

1. Whether the new XI parts default to progression alone (this file) or mirror the main solve's
   three requirements (DISSENT 5). **Ruled: X6, ROOT-DECISIONS 2.7.** Progression alone, as this
   file specifies; the side requirements enter only with the explicit opt-in.
2. The HONEST EVALUATION split-sample tool (`xi.split-sample` budget; E-13 draft, interface 7,
   "owner OR-XI") is not specified here. Its definition is E-13's `product_split_rule`, and the
   route stays withheld until E-13's `split_sample_diagnostic` is executed; a separate spec should
   follow E-13's freezing, not precede it. **Ruled: X8, ROOT-DECISIONS 2.7.** Deferred to E-13:
   the split-sample tool is specified after E-13 is frozen.
3. The tail menu is the E-13 draft's (`ceil` of a tenth, a quarter and a half of `B`, plus 1);
   whether 200 precomputed worlds are ever offered is E-13's open question 3. **Ruled: X8,
   ROOT-DECISIONS 2.7.** Deferred to E-13: the tail menu is the E-13 draft's until E-13 is
   frozen.
4. Settled, no longer open: the 12 worlds are the first 12 of the 40 (1.4, prefix property),
   because `Generator.multinomial(..., size=B)` draws rows in sequence; checked under numpy
   2.5.3 and 2.5.4, and checked again by a structure test under whatever numpy is installed. While it holds, the 40-world certificate prints
   `RISK_PREFIX`; `RISK_GROWTH` stays the general statement and no comparison of the two menus'
   values is printed.
5. Run time of the TAIL and REGRET selection and membership solves at `q = 100000` with 40
   worlds is unmeasured. **Ruled: X5, ROOT-DECISIONS 2.7.** `xi.risk.tail` joins
   `runtime.LONG_ROUTES`; the 40-world option ships only after these solves are timed on the
   corpus, and until then the menu offers 12 worlds (7.1; section 11, item 15). If the
   deterministic limit of 40 is often reached, the honest answers are `LIMIT_REACHED`, a larger
   budget, or precomputed results; never a coarser quantisation (ROOT 3b).
6. The new modules use private members of `kernel.py`, as `brief.py` does. Exporting public
   names would edit `kernel.py` and move a hash served in every Squad and Transfer certificate.
   **Ruled: X9, ROOT-DECISIONS 2.7.** No edit to `kernel.py`: the new modules use its private
   members, as `squad/brief.py` does, and a test pins the members they use (section 9).
7. Whether the conflict tool should also be offered for an infeasible hard-floor query in the
   shipped tradeoff panel. **Ruled: X10, ROOT-DECISIONS 2.7.** Not in this release: the API
   accepts `explains: "floors"`; no page part in the shipped tradeoff panel.

## Review record

Three adversarial reviews of the first draft (exactness, constitution, product), 14 October
2026. Each finding was checked against this file and the tree at `25128e8` before its
disposition. 73 findings: 12 blockers, 30 majors, 31 minors. All 73 hold and are applied; none
is rejected. Two are applied with a correction to the reviewer's proposal (C18, E10), noted in
their lines. Three needed a root ruling and were first applied as gates with a compliant
fallback (section 11, items 13 to 15): E10, E25 and P11. The root ruled them the same day
(ROOT-DECISIONS 2.7: X2, X4, X5), and this file now specifies the ruled state. Code checks made for this record: the
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
| E3 | blocker | `explains: "solve"` accepted without the opt-in explains a model with inactive side requirements | applied: refused with `CONFLICT_SOLVE_NEEDS_OPT_IN` (1.3, 7.2); parity test of in-force sets |
| E4 | blocker | RISK ledger row serves the "largest regret pair", a difference O8 forbids | applied: 7.6 row prints binding worlds with both pairs; API test |
| E5 | major | Leak test "no integer ≥ BIG anywhere" cannot pass (seeds, match id, quantisation) | applied: test recomputes BIG, Φ*, ρ*, E^w with M ≥ 1 and checks them, with an allow-list |
| E6 | major | INFEASIBLE selection unmapped; world-least UNFIELDABLE reported as UNKNOWN | applied: 5.3, 5.6 step 6, UNFIELDABLE EXACT; two-locked-goalkeeper tests |
| E7 | major | After "Apply minima" the panels send side minima without the opt-in and get 422 | applied: 8.2 request-body rule, minima filtered by the server's `experimental` flag, `SIDE_MINIMA_SET_ASIDE`; e2e |
| E8 | major | Cache key includes defaults while declared rows use `model_fields_set` | applied: declared rows a function of the resolved request (7.6, 7.3); API test |
| E9 | major | `RISK_SAME_WORLDS` not supported by a fingerprint match; check tautological | applied: sentence withdrawn; `RISK_SAME_DRAW`/`RISK_PREFIX` state construction only; slow discard-parity test with opt-in and main exclusions |
| E10 | major | `explain_solve` uses half-even, breaching ROOT 2.4 while the page depends on it | applied with correction (the fallback sentence says the set may hold together under half-even, not only "may not be minimal"): half-even variant gated (item 13), page explains with `explain_floors`, `CONFLICT_CONSERVATIVE_FOR_SOLVE`. **Ruled: X2, ROOT-DECISIONS 2.7**: both variants built and routed, the page explains with `explain_solve`, `CONFLICT_CONSERVATIVE_FOR_SOLVE` withdrawn |
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
| E25 | minor | `xi.html` edits depend on a root ruling under R13 | applied: checklist item 14, fallback page fully specified (8.4). **Ruled: X4, ROOT-DECISIONS 2.7**: the edits granted, the fallback page not built |
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
| C16 | major | Four `Shell.ledger` calls produce duplicate ids | applied: per-panel id rewrite that throws if the kit changes; unique-id tests. The optional root kit change was declined (X11) |
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
| P11 | major | TAIL enumerates candidates outside the long-route limit; snapshot builds not gated | applied: snapshot as C11; long route requested of the root, `B = 40` gated on timing (item 15). **Ruled: X5, ROOT-DECISIONS 2.7**: `xi.risk.tail` in `LONG_ROUTES`; 12 worlds only until the 40-world solves are timed |
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

### Audit of 14 October 2026

One audit in five scopes: S1 the CEILING model and the shared rules of section 1, S2
CONFLICT, S3 FRONTIER, S4 RISK and its oracle, S5 the API, the page parts and the tests. 78
findings: 14 blockers, 26 majors, 38 minors. Every blocker survived an independent refuter,
none was refuted, and each is applied, with the refuter's corrected proposal where it gave one.
Four blockers duplicate another scope's and are applied once (S3-frontier-3 as
S1-model-ceiling-5, S5-api-page-tests-1 as S3-frontier-1, S5-api-page-tests-2 as
S1-model-ceiling-4, S5-api-page-tests-3 as S1-model-ceiling-2); where two refuters proposed
different fixes for one defect, the line says which was taken and why. Each major and minor was
checked against this file and the code at `fda88c2` before its disposition; every one holds and
is applied, five with a correction (S1-model-ceiling-13, S2-conflict-6, S3-frontier-4,
S3-frontier-12, S5-api-page-tests-22). None is rejected. Three points need a root ruling under
X4 and are listed in section 12 (R-A, R-B, R-C); one needs the E-13 draft's owner
(S4-risk-oracle-6, section 13). The root ruled the three on 16 October 2026 (X12 to X14), and
the second audit's record below carries them into the file.

| # | Severity | Finding | Disposition |
|---|---|---|---|
| S1-model-ceiling-1 | blocker | Witness check compared `O_r` with CP-SAT's float `objective_value`, which ortools 9.15.6755 reports one or two ulp off an `OPTIMAL` integer: a correct optimum raised `RuntimeError` and served a 500 | applied with the refuter's correction: compare with `solver.value(Σ c·x)`; no `|objective_value − O_r| < 1/2` check (it can fail at `2**50`); bound rounding stated sound (2.3); "integers from the solver" row (1.5); the 5.1 exactness sentence removed; 4.2 stage values and 5.6 `Φ*`, `ρ*` from `solver.value` or recomputation; wrapped-solver test (9) |
| S1-model-ceiling-2 | blocker | `CEILING_CLAIM` said one XI reaches the least and largest sum; it reaches only the extreme rounded sum, and XIs tied at `I⁺` differ in `S` | applied with the refuter's correction, merged with S5-api-page-tests-3: `CEILING_CLAIM` makes no reach claim, holds for `FEASIBLE_NOT_PROVEN` ends and names no XI shown (the panel shows none); section 2 design note and 2.1 row; top-tie and `q = 100000` tests |
| S1-model-ceiling-3 | blocker | With declared floors, bound-based sentences spoke of every XI while `𝒳_F` is the conservative inner set; a CEILING `NOT_SATISFIABLE` reply had no outcome sentence | applied, the refuter's option (b), extended to FRONTIER: `{xi}` scope argument, `FLOORS_SCOPE`, `FLOORS_CONSERVATIVE` defined once in `ceilings.py` and served for CEILING `NOT_SATISFIABLE`; KNOWN_LIMITATIONS request; instance-A tests for both tools |
| S1-model-ceiling-4 | blocker | Reason `ALLOWANCE` was served on `FEASIBLE_NOT_PROVEN` ends, where the undecided band holds the optimality gap; an end with a witness and no finite bound was undefined | applied with the refuter's correction: `ALLOWANCE` only on a `QUANTIZED_OPTIMAL` end, `NOT_CERTIFIED` on any other (its sentences are true there); the non-finite bound defined in 2.3 step 7, 7.5 and 8.2; planted tests |
| S1-model-ceiling-5 | blocker | Wall times in the tool's provenance made every "identical `asdict`" determinism test fail | applied with the refuter's correction: two keys per tool (`<tool>_solve_deterministic_times`, `<tool>_solve_wall_times`), `stable(asdict)` deletes only the wall-time key (9); `budget.report` untouched, its keys being pinned |
| S2-conflict-1 | blocker | `CONFLICT_CLAIM` was served whatever the status: false on `NOT_PROVEN_MINIMAL` and `MODEL_FEASIBLE`, uncertified on `UNDECIDED` and `MODEL_INVALID` | applied with the refuter's correction: the claim chosen by status (3.4 table), `CONFLICT_NOT_PROVEN_CLAIM`, `CONFLICT_NOT_DECIDED`, and `CONFLICT_MODEL_INVALID` for `MODEL_INVALID` (the refuter's `CONFLICT_NOT_DECIDED` says "within the search limits", which misstates a refusal); ledger value `None`; 8.2 states; tests |
| S2-conflict-2 | blocker | "Another order can return another, and it is not the smallest by count" is false for a unique or one-member set, the usual case and the e2e one | applied, the refuter's conditional wording in `CONFLICT_CLAIM`, the section 3 design note and 3.3; tests on unique-set instances |
| S3-frontier-1 | blocker | The point was printed in club medians, the raw sums and the allowance in per-90 units, so the claim about them was false | applied, merged with S5-api-page-tests-1, with that refuter's correction: three columns in club medians, `S / n` rounded down and `a_r / (2q)` rounded up at five decimals, the text-level inequality proved (7.5); this refuter's toward-the-point rounding with a six-decimal allowance is also exact and was not taken, so the column rounds one way as the rest of the page does |
| S3-frontier-2 | blocker | `POINT_ORDER`'s reversal clause is false under every cut list | applied, the refuter's single constant; 4.2 "a cut list is a prefix" row and order paragraph; the optional sentence added to `FRONTIER_LIMIT` and `_STOPPED`; prefix tests |
| S3-frontier-3 | blocker | Same wall-time defect for FRONTIER | applied as S1-model-ceiling-5; the two-key form was taken over this refuter's single key with a per-entry deletion, because deleting one key is simpler to state and test |
| S4-risk-oracle-1 | blocker | The TAIL model as written ignored its wall-clock limit and crashed CP-SAT (`MemoryError`) on 2 of 144 oracle-sized instances | applied with the refuter's correction: split variables for `η`, `u_w` and `ρ` with the equivalence proof (5.1, 5.6); guard rechecked to `(k + |U| + 2) · E_cap` and `3 · E_cap` and the example recomputed (7.8 at `B = 40`, `k = 20`); solver exceptions are a 500, not a status (1.5, 7.8); capped-subprocess tests and three planted regression instances; peak memory in the X5 timing; ADR-0030 alternatives |
| S5-api-page-tests-1 | blocker | Same mixed units, seen from the API | applied as S3-frontier-1, with this refuter's rounding |
| S5-api-page-tests-2 | blocker | Same `ALLOWANCE` defect | applied as S1-model-ceiling-4; this refuter's two `SEARCH_GAP` sentences were not added: the `NOT_CERTIFIED` sentences are true in that case and the interval is printed beside them |
| S5-api-page-tests-3 | blocker | Same `CEILING_CLAIM` reach claim | applied as S1-model-ceiling-2; this refuter's "the XI shown … by up to the width of its interval" was not taken: no XI is shown, and an unproved end's width is not rounding |
| S1-model-ceiling-6 | major | Each fact consulted one witness; the other end's witness can decide it | applied: both witnesses, `minimum_*_witness` fields, the sentence prints the deciding sum (2.1, 2.2, 7.5); planted tests |
| S1-model-ceiling-7 | major | Exact-sum facts beside the half-even main solve, unsaid | applied: `CEILING_EXACT_FACTS` and instance B (2.1, 7.7, 9) |
| S1-model-ceiling-8 | major | `FIELDABLE` undefined; `R` empty unhandled | applied: rule in 2.3 step 6; `R` empty is a `ValueError` (2.2); tests |
| S1-model-ceiling-9 | major | No aggregation of per-call stops into one `completeness` and `stopped_by` | applied: per-call rule with `time.monotonic() < deadline` and the "one certificate, one token" row (1.5); planted mixed test |
| S1-model-ceiling-10 | minor | Prefix property "checked under numpy 2.5.3"; `.venv` has 2.5.4 | applied: the test checks the property and records the version only (1.4, OPEN QUESTION 4, 9); checked here under 2.5.4 for 8, 19, 30 and 37 games |
| S1-model-ceiling-11 | minor | `_q`'s float error bound needs a magnitude limit | applied: within `MAX_MAGNITUDE`, enforced by `kernel._tables` (1.2) |
| S1-model-ceiling-12 | minor | Minima still validated; floor order; `hard=True` | applied: 2.3 step 1, ascending floor order, `hard=True` refused (2.2) |
| S1-model-ceiling-13 | minor | Parity "the other's bracket" undefined | applied with correction: each witness's sum in the band `[(n/q)·I⁺ − e, (n/q)·I⁺ + e]` of every XI at `I⁺` (2.4, 9, 13), tighter than the proposed bracket and bound check and true for both witnesses |
| S1-model-ceiling-14 | minor | Proved `UNFIELDABLE` had no reason; a `MODEL_INVALID` end blamed the search limits | applied: `UNFIELDABLE_PROVED`; a `MODEL_INVALID` solve ends the tool with `CEILING_REFUSED` (2.3, 2.4) |
| S2-conflict-3 | major | Same aggregation gap for CONFLICT | applied as S1-model-ceiling-9 |
| S2-conflict-4 | major | Untested CONFLICT branches (a) to (h) | applied: each in section 9; `requirements_in_force` added (3.4) |
| S2-conflict-5 | major | `tests`, `restore_tests`, `conflict` undefined per status; restore-time `MODEL_INVALID` contradicted | applied: the 3.4 status table; a restore-time `MODEL_INVALID` keeps the set's status (3.3) |
| S2-conflict-6 | major | A floor at a default minimum had no text and was called "of yours" | applied with correction: the router prints it as a default (7.4 origin, 7.5 rule) instead of a `Declaration.default` field, which the module cannot fill; "of yours" dropped |
| S2-conflict-7 | minor | `explain_solve` minima not dyadic | applied: dyadic minima, asserted on targets (6) |
| S2-conflict-8 | minor | `minimums` silently unused with explicit floors | applied: refused (7.2) |
| S2-conflict-9 | minor | "It meets only those" literally false; a missing locked player unflagged | applied: `CONFLICT_MEMBER_WITNESS` reworded, `witness_missing_locked_players`, `CONFLICT_LOCK_SET_ASIDE` |
| S2-conflict-10 | minor | Planted instances under-specified | applied (3.3, 9) |
| S2-conflict-11 | minor | `mode`, floors unvalidated; `mode` not in the contract; BALANCE labelled Satisfy | applied: 3.1, section 10, `CONFLICT_NO_MINIMUM` |
| S3-frontier-4 | major | Empty floored region with an undecided cause solve had no status | applied with correction: `FLOORS_UNMET`, whose completeness is the undecided solve's so the reply is not stored, rather than `COMPLETE`, which would cache "not decided"; CEILING given the same `feasible_set` |
| S3-frontier-5 | major | No rule for which status sentence a frontier reply carries | applied: `status_text` (7.5); a stage-1 `FEASIBLE` at the limit is `POINT_LIMIT` |
| S3-frontier-6 | major | Frontier branches and served computations untested | applied: (a) to (h) and the API text tests (9) |
| S3-frontier-7 | major | Seeded frontier oracle tests could be vacuous | applied: three requirements per instance, seeded ordered dimensions, a non-vacuity list (6) |
| S3-frontier-8 | major | Expected `DEADLINE` underivable; `final_region_status` undefined | applied: any other undecided call is `DEADLINE`/`WALL_CLOCK` (1.5); a three-point instance; the failing stage's status (4.3) |
| S3-frontier-9 | major | O7's three words never named | applied: the union "best", "optimal", "trade-off" in any spelling and "knee", the status token `OPTIMAL` excepted (4, 8.3, 9) |
| S3-frontier-10 | minor | Pseudocode dispatch loose | applied: one dispatch per stage, points kept under every stop, `d · |P| + 2` solves (4.2) |
| S3-frontier-11 | minor | Claim's first sentence and the order sentence | applied (4, 4.2, `FRONTIER_CLAIM`) |
| S3-frontier-12 | minor | Validation list incomplete; `True` accepted as `max_points` | applied with correction: a `hard=True` requirement is refused, not ignored, as CEILING refuses it and 7.2 refuses silently ignored fields (4.3) |
| S3-frontier-13 | minor | Small test and ledger gaps | applied: served-text check moved to the API tests, lexicographic-maximum point, slow-test prefix branch, point-limit declared row, half-even plot rounding |
| S4-risk-oracle-2 | major | The risk oracle test compared only `CERTIFIED` outcomes | applied: statuses, `k ∈ 1..B`, used and discarded ids, `EXACT` terminal blocks (9) |
| S4-risk-oracle-3 | major | `point_loss`, `point_sums` untested; `point_sums` with `None` undefined | applied (5.6, 5.7, 9) |
| S4-risk-oracle-4 | major | `analyze_ties=False`, an undecided selection's block, a world-least `MODEL_INVALID` | applied: `NOT_REQUESTED` (1.5), blocks per state (5.6), the `MODEL_INVALID` rule (5.3); tests |
| S4-risk-oracle-5 | major | E-13's token scope excludes `4-3-1-2`, which the risk routes accept | applied: `E13_SCOPE`, the pending payload, `RISK_OUTSIDE_E13` (5.7); API test with a registry stub |
| S4-risk-oracle-6 | major | `risk_report` attached to `Σ M` while E-13 tests the mean | applied as a reconciliation item for E-13's owner (13); until it is settled `verdicts.risk_report` is `null` (5.7) |
| S4-risk-oracle-7 | minor | Discard parity vacuous on point-infeasible instances | applied: `bootstrap_selection` called directly (9) |
| S4-risk-oracle-8 | minor | Targets not dyadic in RISK instances | applied (6) |
| S4-risk-oracle-9 | minor | Loose definitions (empty `R`, `w ∈ U`, expressions, `assert`, exactness) | applied (5.1, 5.6) |
| S4-risk-oracle-10 | minor | Discard-rule difference with E-13 incomplete | applied: the excluded-candidate case added (13) |
| S4-risk-oracle-11 | minor | E-13's `source_paths` omit `kernel.py` and `tradeoffs.py` | applied (13) |
| S4-risk-oracle-12 | minor | `world_losses` on a non-XI, tie order, `t_bound` | applied (5.2, 5.3, 5.7, 6) |
| S5-api-page-tests-4 | major | The `GET` on mount against X4's words | applied: 8.2 reworded, ruling R-A requested (12); e2e asserts it is the only new request |
| S5-api-page-tests-5 | major | The ledger rewrite produced two `class` attributes | applied: whole attribute runs in both kit forms (8.1); render and e2e tests |
| S5-api-page-tests-6 | major | Rows had to be assembled in JS by id | applied: served row lists (7.5, 8.2, 8.3) |
| S5-api-page-tests-7 | major | No text for a minimum the reader did not enter | applied: one printing rule (7.5); conflict copy reworded |
| S5-api-page-tests-8 | major | Computed ledger rows undefined; `ledger_row` raises on them | applied: the 7.6 table; every terminal state through `ledger_row` (9) |
| S5-api-page-tests-9 | major | Digit-run render test fails on kit badges | applied: kit `aria-label`, `title` and constants exempted, stated in the test |
| S5-api-page-tests-10 | major | Nothing scoped `xi-extensions.css` | applied: 8.3 rule, unit test, checklist item 19 |
| S5-api-page-tests-11 | minor | The "same constants" do not exist | applied: the router's copy and a field-by-field test (7.5) |
| S5-api-page-tests-12 | minor | `Literal[12]` accepts 12.0 | applied: `planning.INTEGER_ONLY` (7.2); 422 test |
| S5-api-page-tests-13 | minor | Claim placeholders in a "word for word" field | applied: `risk.py` formats; no `{` served (5.7, 9) |
| S5-api-page-tests-14 | minor | KNOWN_LIMITATIONS request stale | applied: lines at `fda88c2`, the add-now item dropped, sentences quoted (12) |
| S5-api-page-tests-15 | minor | `RISK_SAME_DRAW` false after a corpus rewrite | applied: reworded, with the reason (7.7) |
| S5-api-page-tests-16 | minor | Conservative floors understated | applied: `FLOORS_CONSERVATIVE`, `CONFLICT_CONSERVATIVE`, `FLOORS_SCOPE` |
| S5-api-page-tests-17 | minor | `corpus_token` covers teams, not the manifest | applied: stated and accepted (7.3) |
| S5-api-page-tests-18 | minor | Envelope keys inconsistent | applied: every key on every reply, the `statements` table, GET field names (7.5) |
| S5-api-page-tests-19 | minor | The kit's `data-label` cells are private | applied: own cells and stacking (8.3) |
| S5-api-page-tests-20 | minor | Same as S2-conflict-8 | applied as S2-conflict-8 |
| S5-api-page-tests-21 | minor | No declared row for `mode`, `explains`, `max_points` | applied (7.6) |
| S5-api-page-tests-22 | minor | An `xi:solved` before `mount` is lost | applied with correction: scripts and mount placed before the inline script, adding no page state (8.1); ruling R-B requested |
| S5-api-page-tests-23 | minor | Same as S1-model-ceiling-10 | applied as S1-model-ceiling-10 |
| S5-api-page-tests-24 | minor | REGRET difference check has no allow-list | applied (9) |
| S5-api-page-tests-25 | minor | Private `planning` members unpinned | applied (0, 9) |
| S5-api-page-tests-26 | minor | Shipped specs rewrite committed screenshots | applied: stated (12); ruling R-C requested |
| S5-api-page-tests-27 | minor | `CONFLICT_HALF_EVEN` printed for a BALANCE explanation | applied as S2-conflict-11 |
| S5-api-page-tests-28 | minor | Two fingerprint rows say one thing | applied: one rule (10) |

Code checks made for this record, at `fda88c2`: `kernel._tables` bounds coefficients and targets
by `MAX_MAGNITUDE` (kernel.py:602-612) and validates every active minimum; `kernel.value`
refuses a hard requirement (kernel.py:670-674) and adds a reason on a proved-empty model
(kernel.py:739-743), as the maximiser does (tradeoffs.py:453-457); the conservative slack bound
(tradeoffs.py:215-230); `kernel.source_fingerprints` returns a sorted dict; `_Run.solve` returns
a solver object, so `deterministic_time` and `wall_time` can be read; `decision_inputs` keeps its
labels in a local dict and takes the default minimum at decision_lab.py:293 with the normaliser
at :302; `shell.ledger_row` raises `TypeError` on an empty `row_id` or `sample`; the kit's
ledger markup, its private `cell`, its badge `aria-label` and its 650 px stacking rule
(labs-shared.js:105-109, 179-198; labs-shared.css:40-44); `planning.INTEGER_ONLY`,
`_minimum_text`, `_corpus_files` over the five public tables, and `_outward` at four places;
`load_snapshot`'s four frames and the manifest it reads; `solve_xi` returns before the bootstrap
on an infeasible point solve and the discard rule ignores excluded players (solver.py:321-351,
545-564); the snapshot sets a world value to `None` wherever the point value is
(historical.py:210-215); the E-13 draft's formation, scenarios, `source_paths`, own statistics
and token scope; `verdicts.record`, `derive` and `PENDING`; the screenshots `labs.spec.js`
writes and `README.md:26`; numpy 2.5.4, ortools 9.15.6755 and pydantic 2.14.1 in `.venv`; the
prefix property under numpy 2.5.4; the frontier example of 7.5 in `Fraction` (0.97000 and
0.88333 against the point 0.97000 and 0.88334); the overflow-guard examples by arithmetic; and
every 7.7 constant, new or changed, together with the new labels, ledger texts and `{xi}`
scope, through `labels.scan_labels` (none flagged), and the frontier constants against O7's
words (none present).

### Second audit, 16 October 2026

A second audit in the same five scopes (S1 the CEILING model and section 1, S2 CONFLICT, S3
FRONTIER, S4 RISK and its oracle, S5 the API, the page parts and the tests), prefixed `A2-`. 79
findings: 11 blockers, 22 majors, 46 minors. Every blocker survived an independent refuter;
none was refuted, and each is applied with the refuter's corrected proposal. Three blockers
duplicate another (A2-S5-api-page-tests-1 as A2-S4-risk-oracle-1, A2-S5-api-page-tests-2 as
A2-S1-model-ceiling-1 and A2-S3-frontier-1, A2-S5-api-page-tests-4 as A2-S2-conflict-3) and are
applied with it; where two refuters proposed different fixes for one defect, the line says which
was taken and why. Each major and minor was checked against this file and the code at `1556fa2`
before its disposition: every major is applied, and every minor too, except the optional part
(b) of A2-S1-model-ceiling-17, which is rejected with its reason. Several are applied with a
correction or a choice between the auditor's options, noted in their lines. No point needs a
root ruling. The E-13 draft's owner now has three open items in section 13: the `risk_report`
statistic (from the first audit), the requirement set of its token scope (A2-S5-api-page-tests-12)
and the interface-1 details (A2-S4-risk-oracle-12). The root's rulings on the first audit's
three points (X12 to X14, ROOT-DECISIONS 2.7) are carried into the preamble, 8.1, 8.2, section
9, item 14 and section 12 (A2-S1-model-ceiling-5, A2-S5-api-page-tests-5).

| # | Severity | Finding | Disposition |
|---|---|---|---|
| A2-S1-model-ceiling-1 | blocker | `CEILING_CLAIM` was served on every reply, though it states found XIs and proved bounds that UNKNOWN, empty, refused and partly undecided replies do not have | applied with the refuter's correction: the claim chosen by state (2.2 table): `CEILING_CLAIM`, `CEILING_PARTIAL_CLAIM`, `CEILING_NOT_DECIDED`, `CEILING_EMPTY` (proved empty only), and `CEILING_REFUSED` as the `MODEL_INVALID` claim, dropped from `statements` (the refuter's cleaner option); 2.3 step 6, 7.5, 7.7, 8.2; claim-per-state tests (a) to (e) in the tool, API and render tests |
| A2-S2-conflict-1 | blocker | A refused filter test served `CONFLICT_MODEL_INVALID` ("not decided") although `s0` had proved the set, and threw away a certified set | applied with the refuter's correction: `KEPT_REFUSED` keeps the member and the filter continues; only `s0` gives status `MODEL_INVALID`; `members_refused`; `CONFLICT_MEMBER_REFUSED`; `CONFLICT_NOT_PROVEN_CLAIM` names a refusal; 3.3 proof row, 3.4 table, 7.5, 7.7, 8.2; the three-slot test with `final_set_proof_solve == 3` |
| A2-S2-conflict-2 | blocker | The test asserted a unique minimal set on the 3.3 instance, which has two, and cited a "one-slot instance" that does not exist | applied with the refuter's correction: the 3.3 instance pinned (slots `a`, `b`, players 1 to 3, floor above 2), exactly two minimal sets and the floor-first filter returning `{exclusion:1, lock:1}`; the unpatched three-slot instance as the unique-set case; the phantom reference deleted. Rechecked here by brute force |
| A2-S2-conflict-3 | blocker | `explains: "floors"` with `floors: {}` served `CONFLICT_NO_MINIMUM`, whose reason (the decision rule of the solve above) the router cannot know and which is false under Satisfy | applied with the refuter's correction: `CONFLICT_NO_FLOOR`; the 7.5 rule written as four cases on `result.declarations`; 3.1 and 8.2 aligned; API tests for all four cases |
| A2-S3-frontier-1 | blocker | `FRONTIER_CLAIM` stated completeness on every status, false on every cut list and on an undecided empty one | applied, the refuter's option (a): one constant that speaks of each listed point and leaves completeness to `status_text`, true on every status (4, 4.3, 7.7); the per-status option of A2-S5-api-page-tests-2 was not taken, as one true constant is simpler, as S3-frontier-2 chose for `POINT_ORDER`; tests on every cut and undecided reply |
| A2-S3-frontier-2 | blocker | The 4.1 instance was used as a one-point fixture but has two points, and the router cannot pose it | applied with the refuter's correction: the unit test asserts both points and the single point under `exclusion:c`; the API test uses the refuter's `q = 100000` instance, whose raw texts differ from its point texts (the auditor's instance was not, as its raw texts equal the point's). Rechecked here in `Fraction` |
| A2-S4-risk-oracle-1 | blocker | The pending E-13 form, `dataclasses.replace(..., token=PENDING)`, raises V3 on an executed record, the only case it exists for | applied: `protocol_commit=None, results_hash=None` cleared with the token, the resulting payload stated (5.7); the API test registers an executed stub in `verdicts.VERDICTS` (A2-S5-api-page-tests-1's addition) and asserts 200 and `REGISTERED_NOT_RUN` |
| A2-S5-api-page-tests-1 | blocker | Same defect as A2-S4-risk-oracle-1 | applied as A2-S4-risk-oracle-1, with this refuter's note that the stub must be a record in `verdicts.VERDICTS` |
| A2-S5-api-page-tests-2 | blocker | Same defects as A2-S1-model-ceiling-1 and A2-S3-frontier-1 | applied as those two; this refuter's `CEILING_NO_RANGE` for all four empty or refused states was not taken, because the A2-S1 refuter's split states emptiness where it is proved and nothing on a refusal |
| A2-S5-api-page-tests-3 | blocker | The frontier ledger served "0 points" for an undecided empty list; `MODEL_INVALID` with points had no value | applied with the refuter's correction: values by status and count, "0 points" only where the empty set is proved, `None` otherwise, `FRONTIER_STOPPED_NONE`, the page's no-table state; A2-S3-frontier-4's "{n} listed" wording not taken |
| A2-S5-api-page-tests-4 | blocker | Same defect as A2-S2-conflict-3, with 8.2's condition read on the set | applied as A2-S2-conflict-3; 8.2 now says the condition is on the declarations |
| A2-S1-model-ceiling-2 | major | A proof of emptiness after an undecided end got two different completeness tokens from two rules | applied: 1.5 row "a proof supersedes earlier calls" (also REGRET's case of 5.3); 2.3 step 6; planted test |
| A2-S1-model-ceiling-3 | major | Cause solve `MODEL_INVALID`, cause solve `NOT_RUN` and a mid-run deadline untested | applied: three planted tests (9) |
| A2-S1-model-ceiling-4 | major | `CEILING_NON_CLAIM` said every range is over all XIs, while with floors it is over the inner set | applied: the non-claim and the design note name the set; `scan_labels` rerun |
| A2-S1-model-ceiling-5 | minor | The spec still cited X1 to X11 and asked for rulings X12 to X14 already gave | applied with A2-S5-api-page-tests-5 |
| A2-S1-model-ceiling-6 | minor | The `planning.attained` parity named no floors; 2.4's recipe would bind | applied: no floors, equivalently floors at 0 (13, slow tests); checked at planning.py:1160 |
| A2-S1-model-ceiling-7 | minor | `ranges` comment missed step 2; `statuses` and `solves` undefined for ends not called | applied (2.2, 2.3 step 2) |
| A2-S1-model-ceiling-8 | minor | `reasons` called diagnostic though printed; `UNFIELDABLE_PROVED` had no home | applied: served reasons; defined in `ceilings.py`, re-exported by `frontier.py` and `risk.py`, identity test |
| A2-S1-model-ceiling-9 | minor | Three bands understated (exact facts against half-even; the conservative floor allowance; 2.1) | applied: 2.1 says `(a_r + 1) · n_r / (2q)`; `CEILING_EXACT_FACTS`, `FLOORS_CONSERVATIVE`, `FLOORS_SCOPE`, `CONFLICT_CONSERVATIVE` and the KNOWN_LIMITATIONS request name the bands in words; both examples rechecked |
| A2-S1-model-ceiling-10 | minor | Wrong cross-reference; `V_p[μ_r]` against the kernel's `.get` | applied (1.1) |
| A2-S1-model-ceiling-11 | minor | The 1.4 lemma was false as worded under 1.1's definition | applied: the lemma speaks of keys of players outside `X` and of `β_w.variables` (1.4), with A2-S4-risk-oracle-3 |
| A2-S1-model-ceiling-12 | minor | "Both limits are in every certificate" false outside RISK; "four settings" miscounted | applied (1.5) |
| A2-S1-model-ceiling-13 | minor | Which file is hashed where was inexact; the OR-Tools metadata read was omitted | applied (0) |
| A2-S1-model-ceiling-14 | minor | A refusal depended on load and on the background | applied: tables and coefficients computed before step 2 (2.3 step 1); `_background` builds its variables when the model is `None` (kernel.py:496-551); test |
| A2-S1-model-ceiling-15 | minor | The `q = 100000` containment instance depended on the id order | applied: pinned, both orders run |
| A2-S1-model-ceiling-16 | minor | The prefix test checked weights only | applied: the world vectors' fingerprint too (1.4, 9) |
| A2-S1-model-ceiling-17 | minor | (a) oracle truth set unnamed; (b) a floor at or above the minimum could decide "missed" False; (c) 1.2's implication untested | (a) and (c) applied (9); (b) rejected: optional, and the `None` it leaves serves a true sentence (read over all XIs, whether every XI reaches the minimum is not settled by the search), while the reader already declared the floor |
| A2-S2-conflict-4 | major | After a filter refusal, `NOT_RUN` rows made `stopped_by` `WALL_CLOCK`; the refused row had no token | applied as A2-S2-conflict-1: no `NOT_RUN` follows a refusal; `KEPT_REFUSED` added |
| A2-S2-conflict-5 | major | A refused restore test had no sentence; "within the search limits" misstated it | applied: `CONFLICT_RESTORES_REFUSED` (7.5, 7.7); API test |
| A2-S2-conflict-6 | major | A floor from an explicit `floors` dict was labelled a default minimum | applied: printed as entered (7.4, 7.5); API test with `floors: {progression: 0.25}` |
| A2-S2-conflict-7 | minor | `statuses` indexing, `solves` and `members_undecided` undefined | applied (3.4); test |
| A2-S2-conflict-8 | minor | `_Run.solve` returning no solver mid-loop was unhandled | applied: `NOT_RUN` in the pseudocode, filter and restore (3.3); checked at kernel.py:197-204 |
| A2-S2-conflict-9 | minor | The `Fraction` floor check read literally covered floors outside the tested set | applied (3.4) |
| A2-S2-conflict-10 | minor | `{slot:s}` holds only with no other conflict | applied (9); rechecked |
| A2-S2-conflict-11 | minor | A BALANCE explanation was labelled "as the Satisfy solve" | applied, the first option: "half-even, as the solve above" and the token `SOLVE_HALF_EVEN` (3.4, 7.6) |
| A2-S2-conflict-12 | minor | `explain_floors` ignored `hard=True` silently | applied: refused with CEILING's sentence (3.1); the `kernel.satisfiable` parity runs on instances with no hard requirement |
| A2-S2-conflict-13 | minor | No validation path; magnitude checks over excluded players' keys | applied: a `ShortfallKernel` for validation and the contract, `_player_ids`, the parity stated within the limits (3.4) |
| A2-S2-conflict-14 | minor | Wrong parenthetical; `t(m)` where `explain_floors` uses `φ` | applied (3.1, 3.3) |
| A2-S2-conflict-15 | minor | "All three minima" contradicted the common body and would turn defaults into entered minima | applied: the main solve's `minimums` unfiltered (8.2); checked at xi.html:79 |
| A2-S2-conflict-16 | minor | After a corpus rewrite the conflict panel can explain another model than the solve above | applied, the first option: stated in 7.3 and added to the KNOWN_LIMITATIONS request (12); no served sentence, as the router does not see the main reply |
| A2-S3-frontier-3 | major | A `FEASIBLE` stage-1 solve at the point limit was `POINT_LIMIT` by 4.2 and undecided by 1.5 | applied, the auditor's first option: the limit check is a solve with no objective, whose witness is decided (4.2, 4.3); the first audit's S3-frontier-5 disposition ("a stage-1 `FEASIBLE` at the limit is `POINT_LIMIT`") is superseded; checked that CP-SAT returns `OPTIMAL` on a feasibility solve (ortools 9.15.6755); planted tests |
| A2-S3-frontier-4 | major | Frontier ledger: "0 points" on an undecided list, no value for `MODEL_INVALID` with points | applied as A2-S5-api-page-tests-3 |
| A2-S3-frontier-5 | major | The mixed-stop test cannot be built for FRONTIER | applied: restricted to CEILING, CONFLICT and RISK; FRONTIER's single stops, the cause solve's deterministic stop added (9) |
| A2-S3-frontier-6 | major | Cause solve `MODEL_INVALID` and the solve count untested; the count was misstated | applied: exact counts in the 4.2 table (`d · |P| + 1`, `d · max_points + 1`, 2, 1, 0); tests |
| A2-S3-frontier-7 | minor | "Another order can list others" false for a stopped list that holds all of `P` | applied: "may" in `FRONTIER_STOPPED` and `POINT_ORDER`; "can" kept in `FRONTIER_LIMIT`, where it is proved |
| A2-S3-frontier-8 | minor | The claims omitted the measurement rule over every requirement in force | applied to `FRONTIER_CLAIM`, and to the CEILING claims for parity; `scan_labels` rerun |
| A2-S3-frontier-9 | minor | FRONTIER named in a no-opt-in case that cannot occur | applied (7.2, 7.5, 9); 422 test |
| A2-S3-frontier-10 | minor | Proof-table notation, an unconditional row, `SOLVER_REFUSED` twice | applied (4.2, 7.5) |
| A2-S3-frontier-11 | minor | Nothing said that another XI can reach a point with other raw sums | applied: `FRONTIER_WITNESS`, under the table |
| A2-S4-risk-oracle-2 | major | Who appends the RISK suffix was contradictory | applied in A2-S5-api-page-tests-6's form: the envelope `claim` is `result.claim` plus the suffix, `result.claim` left as the tool returned it; this auditor's "write the same text to `result.claim`" was not taken, because the router never alters a tool field (5.7, 7.5, 9) |
| A2-S4-risk-oracle-3 | major | `L^w_r` over keys that include excluded players changed BIG; `T_bound` undefined at `|U| = 0` | applied: over `β_w.variables` (solver.py:258-270 checked); computed only when `|U| ≥ 1`; oracle `t_bound` takes `excluded`; `world_losses` at `|U| = 0` |
| A2-S4-risk-oracle-4 | major | The overflow guard had no place in the algorithm | applied with a correction: a fixed place in 5.6 step 2, after `NOT_EVALUABLE` and the tables but before the deadline rule and the `UNFIELDABLE`-by-construction test (the auditor placed it after the latter), so a refusal depends neither on load nor on the background, as A2-S1-model-ceiling-14 makes CEILING's; removed from 7.2's declaration-time list; precedence tests |
| A2-S4-risk-oracle-5 | major | The three planted regression instances cannot be built from the repository | applied, the second option: dropped, the capped-subprocess run of every seeded instance and the domain-width test are the guard; wording fixed |
| A2-S4-risk-oracle-6 | minor | The oracle status rule had no precedence; two other test phrases were loose | applied (9) |
| A2-S4-risk-oracle-7 | minor | The WORST against TAIL(1) comparison missed `provenance.input_contract.rule` | applied (9) |
| A2-S4-risk-oracle-8 | minor | The leak test could flag a small `ρ*` or `Φ*` or `BIG = 1` | applied: each conditioned (9) |
| A2-S4-risk-oracle-9 | minor | O8's growth sentence was in no certificate field; it called a tail sum a worst case | applied, the first option, because O8 says the certificate says so: `RiskCertificate.growth`, printed in the certificate block, `RISK_GROWTH` reworded for tails and moved from `statements` (5.2, 5.7, 7.5, 7.7, 8.2) |
| A2-S4-risk-oracle-10 | minor | Section 13's option (a) printed an average section 5 forbids | applied: section 5 names that one exception (5, 13) |
| A2-S4-risk-oracle-11 | minor | `WORLD_LEAST` records and `solves` undefined | applied (5.7); checked at kernel.py:708-709 |
| A2-S4-risk-oracle-12 | minor | E-13's interface-1 arguments, `WORST_WORLD` at 1, the 40-world menu and `world_losses`' role were unreconciled | applied: reconciliation items (13), `declared_risk_selection` accepts `tail_count` 1 for `WORST_WORLD` (5.7) |
| A2-S4-risk-oracle-13 | minor | REGRET's proved-empty reason named pins | applied: `UNFIELDABLE_PROVED` in its place (5.3); equal-reasons test |
| A2-S5-api-page-tests-5 | major | X12 to X14 not absorbed | applied: preamble, 8.1, 8.2, section 9 e2e (X14's restore rule), item 14, section 12 rows and the rulings list |
| A2-S5-api-page-tests-6 | major | Same as A2-S4-risk-oracle-2 | applied as A2-S4-risk-oracle-2, in this finding's form |
| A2-S5-api-page-tests-7 | major | Re-exporting the tools' constants would load the solver at Player Lab's start-up | applied: lazy imports and restated constants with equality tests, planning's pattern (7.1 "Imports", 7.7, 12); subprocess import test; checked that importing `player_lab` loads neither `ortools` nor the kernel today |
| A2-S5-api-page-tests-8 | major | The frontier panel had no ledger and no evidence badge | applied (8.2); render and e2e tests |
| A2-S5-api-page-tests-9 | major | Refused restore tests and membership solves had only "within the limits" sentences | applied: `CONFLICT_RESTORES_REFUSED` as A2-S2-conflict-5; the membership headings name no cause (7.5) |
| A2-S5-api-page-tests-10 | major | Floors implied at every minimum and no floor gave one declared ledger | applied: "Floors: every requirement in force at its minimum" and "Floors: none" (7.6); test |
| A2-S5-api-page-tests-11 | major | No test of the stale-reply rule | applied: e2e with held ceilings and risk replies (9); 8.2 states the rule |
| A2-S5-api-page-tests-12 | major | `E13_SCOPE` left out the requirement set E-13 ran | applied, both options: the requirement set (so the opt-in) joins `E13_SCOPE` now, `RISK_OUTSIDE_E13` names it, and a reconciliation item asks E-13's owner (5.7, 13); "needs no change" removed |
| A2-S5-api-page-tests-13 | minor | `SOLVER_REFUSED` twice on a frontier `MODEL_INVALID` | applied as A2-S3-frontier-10 |
| A2-S5-api-page-tests-14 | minor | Colon row ids render as `data-ledger=""` | applied: hyphens (7.6); checked at labs-shared.js:55, 191 |
| A2-S5-api-page-tests-15 | minor | `bound_text` source undefined | applied: from the exact `Fraction` (7.5) |
| A2-S5-api-page-tests-16 | minor | The digit-run rule could not hold, and float limits are printed | applied, the allow-list option (8.3, 9) |
| A2-S5-api-page-tests-17 | minor | `_minimum_text` and two constants unpinned; the router's copy lacked metric and evidence | applied (7.5, 9) |
| A2-S5-api-page-tests-18 | minor | (a) `RISK_GROWTH` on tails and empty states; (b) `MODEL_DIFFERS` spoke of two XIs; (c) FRONTIER in `model_note`; (d) default-minimum rows on FRONTIER; (e) outward texts beside the minimum | (a) as A2-S4-risk-oracle-9; (b) applied; (c) as A2-S3-frontier-9; (d) applied: on FRONTIER the row reads "Club median of {label}, the unit of these sums"; (e) applied, the second option: the four CEILING sentences say how their figure is rounded |
| A2-S5-api-page-tests-19 | minor | (a) string option values; (b) no `GET` failure state; (c) e2e enablement sentence; (d) literal badge; (e) shipped unscoped selectors | applied: (a) and (b) in 8.2, (c) and (d) in the e2e, (e) in 8.3; checked against the shipped specs |
| A2-S5-api-page-tests-20 | minor | Two FRONTIER text cases cannot be posed through a route | applied: the text builders are pure functions tested directly (7.5, 9) |
| A2-S5-api-page-tests-21 | minor | Overflow guard listed at declaration time; TAIL without `tail_count` implicit; BALANCE minima unused | applied: (a) as A2-S4-risk-oracle-4, (b) stated with a 422 test, (c) stated (7.2) |
| A2-S5-api-page-tests-22 | minor | 8.1 out of date with section 12 and X13; byte test without the LF rule; stale conflict model | applied: (a) and (b) in 8.1, (c) in the render test, (d) as A2-S2-conflict-16 |

Code checks made for this record, at `1556fa2`: `kernel._background` builds its variables when it
returns no model (kernel.py:496-551) and leaves excluded players out (:502), and reads a measurement
with `.get` (:507); `kernel.input_contract` reads the OR-Tools version through
`importlib.metadata` (:428); `_Run.solve` returns `("UNKNOWN", None)` without recording a status
(:197-204); `kernel.value` returns no stage status for a passed deadline (:708-709) and names
pins in its proved-empty sentence (:742); `tradeoffs._source_fingerprints` hashes `tradeoffs.py`
and `domain.py` only (:69-75), and `experiments/run_partial_history.py:77-79` hashes
`historical.py` and `grid.py`; `solve_xi`'s `lower` runs over variables that leave excluded
players out (solver.py:200, 258-276); `planning.attained` sets every active minimum to 0
(planning.py:1160); `planning` restates `EXPERIMENTAL_OPT_IN_ERROR` (:175-176) and tests its
import (test_planning_api.py:136-166); importing `galactico.api.player_lab` loads no `ortools`
module and no kernel; `planning._outward`, `_built_once`, `_minimum_text`, `_APPROXIMATE`,
`_DERIVED_PLACES`; the kit's `word` (labs-shared.js:55, 191); `xi.html` sends `minimums: {}`
until minima are applied (:79); verdict rule V3 (verdicts.py:193-199), `derive`'s pending branch
(:452-470) and the NOT RUN badge (:503); E-13's `expected_active_requirements`
(config.json:124), its "requirement set" non-claim (preregistration.md:413) and interfaces 1
and 3 (PIPELINE.md:754-756); the world vectors' matrix products (historical.py:203-212);
`decision_inputs` applies every requirement to the ten outfield slots and maps the role `cm` to
the two central-midfield slots (decision_lab.py:241-333); the shipped specs' unscoped
selectors; CP-SAT returns `OPTIMAL` on a feasibility solve (ortools 9.15.6755); by brute force,
the minimal conflicting sets of the pinned 3.3 instance and of the three-slot instance, and the
frontier API instance's vectors and texts in `Fraction`; the two band examples of
A2-S1-model-ceiling-9 by arithmetic; and every 7.7 constant, new or changed, with the new
declared-row, ledger and membership texts and `POINT_ORDER`, through `labels.scan_labels` (61
constants and 10 texts, none flagged), and the frontier texts against O7's words (none present).
