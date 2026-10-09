# Decisions

An ADR log. Every entry records what was decided, the evidence behind it, what was
rejected, how confident the decision is, and — the field that matters most — what
would reverse it.

A decision with no reversal condition is a belief, not a decision.

---

## ADR-0001 — Every number carries its evidence class, and composition degrades it

**Problem.** A player's pass count, his estimated progression score, and an
optimiser's objective delta are three different kinds of object. Rendering them
identically is the failure mode most likely to make this project dishonest, and
it happens silently.

**Decision.** `MetricResult` carries value, evidence class, uncertainty, sample
size, reliability and a provenance DAG. Arithmetic propagates all of them.
Composition takes the *weakest* evidence class of its inputs, so no sequence of
operations can turn a prediction into an observation.

**Alternatives rejected.** Convention and code review (does not survive contact
with a deadline). A `float` subclass (loses provenance under most operations).
Tagging at the display layer only (too late — by then the mixing has happened).

**Evidence.** The ordering `OBSERVED < DERIVED < ESTIMATED < PREDICTIVE <
OPTIMIZED < HEURISTIC < EXPERIMENTAL` is a conservative total order over what is
really a partial order. Taking the maximum can only understate confidence, which
is the safe direction.

**Confidence.** High on the principle; medium on the specific ordering.

**Reversal.** If `OPTIMIZED` versus `HEURISTIC` ordering produces absurd results
in practice, replace the total order with an explicit lattice.

---

## ADR-0002 — The reliability gate runs before axes are designed, and is enforced in code

**Problem.** A metric invented first and reliability-tested second acquires
defenders. The honest answer then becomes expensive to accept.

**Decision.** Split-half reliability is computed per candidate axis before the
axis ships. The gate is a code path, not a guideline: `r ≥ 0.70` renders a
number, `0.50 ≤ r < 0.70` renders a band only, `r < 0.50` renders "insufficient
signal" and carries **zero** optimiser weight.

**Evidence.** Expected threat reaches player-season split-half `ρ = 0.89` while
VAEP reaches `0.25` on identical Premier League data. Empirical-Bayes-adjusted
goals-minus-xG has approximately zero year-over-year correlation even at a
hundred-shot floor. Defensive volume counts sit below `r = 0.50`.

**Confidence.** High.

**Reversal.** If measured reliabilities cluster tightly around 0.6–0.7, the
thresholds are doing no work and should be re-derived from the distribution.

---

## ADR-0003 — Implement expected threat in-repo; take no dependency on socceraction

**Problem.** `socceraction` is the obvious import for xT and VAEP. Its last
release pins `numpy < 2` and `python < 3.13`. OR-Tools, which the entire
optimisation layer rests on, requires `numpy >= 2.0.2`. This machine runs Python
3.13.14 with numpy 2.4.2. They cannot share an environment.

**Decision.** Implement the xT grid model in `galactico/models/xt/`. Do not
implement VAEP at all.

**Alternatives rejected.** A permanent two-environment split — taxes every future
change, for one dependency. Vendoring socceraction — inherits its maintenance
burden without its maintainer.

**Evidence.** xT is a Markov chain on a grid and fits in a page; it is
implemented and tested against a synthetic pitch with a known-correct surface.
VAEP is not needed regardless of packaging: its split-half reliability of 0.25
disqualifies it as a player-rating primitive, which is the only thing it would
have been used for here.

**Confidence.** High.

**Reversal.** If VAEP's action-level decomposition later proves necessary for
something other than player rating, revisit — and expect the two-environment
split to come with it.

---

## ADR-0004 — Provider definitions are preserved, never silently harmonised

**Problem.** SPADL-style harmonisation aligns action *types* across providers. It
does not align what was *observed*. Pooling those is a correctness bug that never
raises.

**Decision.** `MetricDefinition.comparable_across` declares which providers may be
pooled for a given metric. `assert_comparable` raises otherwise. Provider wording
is kept verbatim in `source_definitions`.

**Evidence.** StatsBomb records carries for ball movement under three metres;
other providers only record separation beyond it. Carries are 12–15% of all
events — the single largest source of harmonisation failure. StatsBomb and
Wyscout on identical matches agree on only ~0.53 normalised similarity of the
action-type sequence under standard harmonisation.

**Confidence.** High.

**Reversal.** A published, validated cross-provider harmonisation with per-player
(not per-match-half) agreement figures would justify widening
`comparable_across` for specific metrics.

---

## ADR-0005 — Three data tiers, separated at the architecture level

**Decision.** `PUBLIC` (redistributable, hostable — the demo runs on these and
nothing else), `LOCAL_LICENSED` (runtime download into a gitignored cache, never
served), `TRIAL` (time-boxed, never a dependency). Enforced by
`assert_may_host` / `assert_may_commit` and by a CI licensing guard.

**Evidence.** The StatsBomb Public Data User Agreement bars providing data to
third parties (1.2.1) and bars commercial exploitation of the data *or any
derived analysis* (1.2.2). The Pappalardo/Wyscout corpus is CC BY 4.0 and
commercially usable. These cannot live in the same tier.

**Confidence.** High.

**Reversal.** None foreseeable. Licence terms changing in our favour would
loosen individual entries, not the tier structure.

---

## ADR-0006 — Real Madrid 2017/18 is the laboratory; 2026/27 is the subject

**Problem.** There is no free, licence-clean source of current-season event data.

**Decision.** LAB runs on Pappalardo 2017/18 (public tier) and StatsBomb 2015/16
(local only). LIVE runs on paid aggregates plus free official feeds. They are
never rendered on the same scale.

**Evidence.** StatsBomb open data's most recent Real Madrid match is 2021-04-10.
Carreras, Huijsen and Mastantuono have zero event records in any open corpus.
Verified against the competition manifest directly. Meanwhile 2017/18 gives a
complete 38-match Madrid season with the full 19-club competitor universe, and
its central selection question — the BBC front three against an Isco-led shape —
is both contested and retrospectively evaluable, which a 2026/27 optimal XI is
not.

**Confidence.** High.

**Reversal.** An affordable current-season event feed appearing. Sportradar and
Hudl Wyscout both sell one; neither publishes a hobbyist price.

---

## ADR-0007 — Stable core and contested slots replace the single optimal XI

**Historical scope.** The rating-noise simulation below motivated the original
plan; its three-to-five core players and percentage inflation are not results from
the shipped requirement solver. ADR-0012 supersedes the original frequency-only
labeling with shared-world, equally-optimal necessity/possibility bounds.

**Problem.** Presenting one XI as the answer overstates what the data supports.

**Decision.** Bootstrap player estimates, re-solve, and report per-player
selection frequency: locked above 0.9, contested between 0.1 and 0.9 with the
competing candidates and the size of the gap, out below 0.1.

**Evidence.** At an optimistic one-rating-point standard error, every enumerated
near-optimal XI fell inside one standard error of the optimum, and a
200-replicate bootstrap left only three to five of eleven players above 90%
selection frequency. The optimiser's curse separately inflates the reported
objective by 3.5% at four-point noise and 9.9% at eight-point noise.

**Confidence.** High. This is also the product's most interesting output, which
is a happy coincidence rather than the reason.

**Reversal.** None. Better ratings shrink the contested set; they do not make a
single XI identified.

---

## ADR-0008 — No learned pairwise chemistry

**Decision.** Complementarity is a *computed structural score* from profile
overlap — spatial, progression-source, creative, defensive. Predictions are
logged so they can be tested against outcomes later. No pair effects are
estimated.

**Evidence.** Of 2,689 distinct starting XIs in the four-league corpus, 2,461
appear exactly once and only ten recur five times or more, so lineup-level
identification is impossible. At pair level, one club-season presents roughly 300
candidate parameters against ~118 goal events, and the published chemistry model
beat a constant-mean baseline by 0.19% on defensive chemistry.

**Confidence.** High.

**Reversal.** A corpus with tens of seasons of consistent lineups, which does not
exist for club football.

---

## ADR-0009 — Computer vision targets team shape, never player ratings

**Decision.** VISION produces line height, width, compactness, block type and
phase classification, feeding Opponent Lab. It never contributes to a numeric
player profile.

**Evidence.** Broadcast-derived coordinates from three commercial providers
measured 1.7–16.4 m positional RMSE against a calibrated optical reference at
0.08 m. But shape metrics average over eleven players, and averaging is exactly
what suppresses per-player error — a claim that must be *measured*, not assumed,
which is what the VISION benchmark exists to do. Calibration itself is not the
obstacle: on main-camera frames completeness is 97.8% with sub-metre pitch
registration.

**Confidence.** Medium-high on the reframe; the aggregation claim is untested
here and is a named research question.

**Reversal.** If measured team-width error exceeds roughly half a metre, the
aggregation argument fails and VISION stays a visualisation.

---

## ADR-0010 — MIT licence, code only, no data in the repository

**Decision.** MIT. The repository ships code, schemas, tests, tiny fixtures and
download scripts. It ships no football data of any kind.

**Evidence.** AGPL would permanently exclude the GPL-2.0 calibration models the
VISION track may want, and the project's substance is the models and the
optimiser rather than the source. The best pitch-calibration repositories
(PnLCalib, No-Bells-Just-Whistles) are GPL-2.0-only; Ultralytics YOLO is AGPL-3.0
and the vendor reads it as covering model weights.

**Confidence.** High.

**Reversal.** None expected.

---

## ADR-0011 — Freeze Player Lab after repairing shared-world inference

**Problem.** Individually plausible player bootstrap intervals were being paired
as though independently sampled teammates represented coherent historical worlds.
Some comparison/scatter paths also bypassed estimator gates.

**Decision.** Use one match-count resample across every player and construct;
preserve world identities and zero-exposure holes. Require matching world
namespaces for paired differences and invalidate artifacts when semantics change.
Apply gates on every public path. A difference interval excluding zero is a
directional inference, not established practical materiality. Freeze the Player
Lab implementation after these repairs; do not claim external human acceptance.

**Evidence.** Independent covariance, world-order and missing-exposure regression
tests, API gate tests and rendered-browser checks. See
[M-04](docs/research/M-04-shared-match-worlds.md).

**Alternatives rejected.** Independent teammate bootstraps, subtracting interval
endpoints, and frontend-only suppression of inadmissible estimates.

**Confidence.** High on the repair; conditional on exchangeability of historical
matches and the fixed estimator. Shared resampling does not cover every uncertainty.

**Reversal.** A validated temporal/dependence-aware resampling design can replace
the multinomial worlds while retaining their joint identity contract.

---

## ADR-0012 — Optimize explicit structural requirements, not universal XI quality

**Decision.** XI Lab identifies eligible assignments with the least declared
structural shortfall. BALANCE minimizes the largest normalized deficit, then total
deficit. SATISFY makes active minima hard. Normalizers and priority order are
inspectable tactical policy, not learned football utility. There is no weighted
quality sum, chemistry uplift or continuity bonus.

CP-SAT solves a discretized model and reports status, bounds and quantization.
Only certified optima are called optimal. An independent exhaustive oracle checks
tiny instances. Equal optima remain equal: opposite-membership solves identify
necessary and possible players, including otherwise indistinguishable keepers.
Shared-world frequency bands preserve that ambiguity. The browser defaults to 12
worlds; CORE/FAVORED/CONTESTED/FRINGE are descriptive policy labels, not universal
scientific boundaries or probabilities of being the better footballer.

**Evidence.** [E-06](docs/research/E-06-lineup-requirements.md) records formulation,
oracle checks and a temporal development diagnostic: 6.00/11 actual-starter overlap
versus 6.83 for prior minutes. [M-05](docs/research/M-05-optimizer-selection-bias.md)
shows that deficit minimization still selects estimation noise. No calibrated
optimism correction, Pareto frontier or robust risk mode is claimed.

**Alternatives rejected.** Treating measurement validity as utility, arbitrary
quality weights, independent player worlds and stable-core claims based solely on
the solver's administrative representative of tied optima.

**Confidence.** High on the conditional decision claim and exactness contract;
low on predictive or causal football usefulness, which is not established.

**Reversal.** Preregistered temporal and external validation against strong simple
baselines could justify a separately named predictive utility model. It would not
retroactively make the current requirements causal.

---

## ADR-0013 — Match Lab ships a contribution vector, not an overall rating

**Decision.** Describe recorded match events and expose exact component filters,
units, availability and provenance. Positive completed-pass xT is named as such;
it is not momentum or conserved possession contribution. Missing Wyscout xG is
unavailable, and pass recipients reconstructed by adjacency are labeled inferred.
No commercial rating collection or imitation is used.

**Evidence.** The scalar audit covers 9,722 Spain and 9,579 England outfield
player-matches. Accounting is exactly the existing pass-xT baseline; role-relative
standardization correlates .988 and .982 with it. This earns neither a new
construct nor an overall contribution claim. See
[E-05](docs/research/E-05-match-score.md).

**Alternatives rejected.** Renaming xT as a rating, adding its key-pass subset a
second time, arbitrary weights over incomparable components and transferring
season reliability to confidence in an individual match performance.

**Confidence.** High that these candidates do not identify an overall rating.
This does not prove every possible scalar is useless.

**Reversal.** A declared utility or legally available target, discriminant and
temporal/external validation, baseline improvements and a mathematically faithful
decomposition could support a narrowly named contribution index.

---

## ADR-0014 — Historical selection uses strict decision-day cutoffs and declared eligibility

**Decision.** Build Madrid candidates from prior appearances, not current-team
metadata. Exclude the entire decision day from events, xT training and historical
rates. Use versioned manual broad-slot rules and a 900-minute outfield floor.
Eligibility is separate from value: the formation changes assignment, not a
player's estimated rate. Historical rates are carried forward additively as an
explicit, deployment-dependent assumption.

Default minima and normalizers are median prior starting-XI sums of pre-cutoff
player rates. Editing a minimum does not change its original normalizer. Side
pass-origin rates are experimental descriptors, not validated team width. The
May 6 snapshot contains 16 eligible players; chance creation, rest defense and
goalkeeping quality are unmeasured, and injury/suspension/fitness is unverified.

**Evidence.** Tests poison future and same-day rows and verify unchanged inputs.
Isco and Modrić have 1,638 and 1,733 prior league minutes respectively, below the
Wyscout creation floor. Hiding that limitation would predetermine the flagship
BBC-versus-Isco comparison without measuring its crucial creative dimension.

**Alternatives rejected.** Full-season Player Lab inputs in historical backtests,
same-day matches assumed complete, current squad metadata as historical truth,
and mechanically inferred romantic role labels.

**Confidence.** High on leakage prevention; manual roles and thresholds remain
heuristics. This is not a complete historical availability reconstruction.

**Reversal.** Licensed historical availability, validated formation evidence and
temporally validated role-transition estimates can replace individual assumptions
with separately versioned evidence.

---

## ADR-0015 — Aggregate partial evidence does not certify individuals or XI utility

**Decision.** Keep the conditional-requirement engine separate from predictive
research. E-08 admits sparse player histories only inside an aggregate forecast;
it does not lower Player Lab or historical XI eligibility gates. Unknown histories
receive declared prior broad-position references, not invented observed zeros.
Development-only tuning includes a context-only boundary, and compares against
team context, broad-position composition and evidence-coverage controls.

**Evidence.** E-07's joint individual floor left only three development observations.
E-08's distinct aggregate cohort provides 272, but the frozen forward selection
prefers context only over every finite pooling strength. Its incremental signal is
NOT_ESTABLISHED. Spain/England evaluation periods were reused, and identity-link
stress controls are not exchangeable permutation tests. See
[E-08](experiments/preregistered/E-08-partial-history/analysis.md).

**Alternatives rejected.** Lowering product evidence gates to rescue a validation
sample, interpreting pooled sparse histories as posterior player quality, tuning
the chosen model against evaluation outcomes, and treating a zero loss-difference
interval between identical models as proof of no player effects.

**Confidence.** High on implementation and the frozen selection outcome; limited
on generality. This rejects neither all lineup forecasting nor causal player value.

**Reversal.** A separately specified model with a credible new rationale and fresh
permitted evaluation evidence may establish predictive information. Turning that
into decision utility still needs its own claim and validation. Meanwhile, useful
product development can expose alternative XIs under explicit requirements.

---

## ADR-0016 — Explore diverse witnesses without inventing another objective

**Decision.** Show different personnel sets inside a certified optimum region.
Fix both lexicographic shortfalls and sequentially require at least two replaced
players versus the comparison XI and each prior witness. Keep search status,
raw requirements and exact constraint provenance visible. The diversity cuts live
in a clone, never in stable-core/tie analysis or bootstrap worlds.

**Evidence.** Exhaustive tiny-instance oracles check membership and both objectives.
The real default Madrid snapshot returns three distinct personnel alternatives
with the same [0, 0] objective. This is a property of declared requirements, not
evidence that those teams are equally good at football. See the
[search contract](docs/research/XI-EQUIVALENT-ALTERNATIVES.md).

**Alternatives rejected.** Returning slot permutations as new teams, labeling
greedy exhaustion as all optima enumerated, adding a new arbitrary diversity or
quality utility, relaxing locks/minima to fill cards, or reusing stale results
after the decision inputs change.

**Confidence.** High on the conditional search contract; no predictive or causal
claim. Pairwise distance is an explicit presentation policy, not tactical value.

**Reversal.** A separately specified epsilon/Pareto or robust exploration policy
can expand the frontier later. It must not silently replace objective equality.

---

## ADR-0017 — Explicit progression specialization is not universal XI utility

**Decision.** Add a separate maximum-historical-pass-xT query under three explicit
hard floors. The HTTP product maximizes progression only; side-specific pass-origin
rates remain research/style constraints, not merit. Preserve BALANCE, SATISFY and
equivalent witnesses unchanged. Return a response-owned XI and a distinct typed
maximizing certificate, never the main solve's bootstrap frequencies.

**Evidence.** Independent formulation and adversarial reviews agreed that covered
shortfall ties and progression surplus answer different questions. A development
diagnostic can omit Ronaldo, Benzema and Casemiro when progression alone is
maximized. That is evidence of a narrow objective, not football superiority. See
the [contract and verification](docs/research/XI-PROGRESSION-UNDER-FLOORS.md).

**Numerical boundary.** Conservative floor coefficients and upward-rounded targets
prevent raw-floor violations. This can exclude boundary-feasible raw assignments;
INFEASIBLE applies only to that conservative integer model. Objective rounding,
incumbents, maximizing bounds and requirement-specific allowances are separate.

**Alternatives rejected.** Rewarding surplus inside BALANCE without a policy change,
maximizing style as universal quality, silently promoting soft minima to hard
constraints, calling one primary optimum Pareto-optimal, mixing numerical and
sampling uncertainty, or weakening floors after infeasibility.

**Confidence.** The claim is conditional numerical optimization, not prediction or
causal football value. Passing capacity is an additive historical-rate assumption.

**Reversal.** A genuinely supported broader utility would require fresh evidence
and a separately reviewed decision claim. E-08's null is not reopened by this tool.

---

## ADR-0018 — Local-tier evidence may label a hosted quantity; it never gates or parameterises one

**Problem.** The written rule was "a hosted instance may never serve a
StatsBomb-derived number". The shipped product already serves StatsBomb-derived
labels: `external_replication` (`ROBUST`, `ROBUST_WITH_SHIFT`) was assigned from
the 2015/16 comparison and is printed in Player Lab. Nothing said whether a label
may unlock a panel, or whether a coefficient fitted on the local corpus may sit
inside a hosted computation. Transfer and opponent research would both have
reached for one.

**Decision.** Labels yes, numbers no, coefficients no. A verdict token from a
LOCAL-tier experiment may be shown on a hosted page as a label that links to its
research note. It may never be the gate that unlocks a number-bearing panel, never
parameterise a served computation, and no LOCAL-derived number, interval,
coefficient or identifier is served or committed in machine-readable form. Hosted
panels are gated on PUBLIC-tier verdicts only. `galactico/domain/verdicts.py`
enforces it in the type: a LOCAL record cannot carry a figure, `may_gate` is false
for it under every token, and no digit may ride inside its sentences. Every new
response passes `runtime.finalize`, which requires the provider set at any depth
of the payload to be exactly the hosted one.

The registry ships **empty**. No protocol has been frozen, so every subject
answers "RECORD ONLY · NOT TESTED". Five protocols are drafted under
`docs/research/north-star/protocol-drafts/`; a draft is not a registration.

**Evidence.** Clauses 1.2.1, 1.2.2 and 1.4 of the StatsBomb Public Data User
Agreement, re-read on 9 October 2026 and unchanged. The agreement's preamble
permits sharing analysis and conclusions; a per-player derived table served on
demand is hard to distinguish from providing the data.

**Alternatives rejected.** Banning the existing replication labels (they are
conclusions, which the agreement permits). Letting a replicated verdict unlock a
hosted panel (the panel's numbers would then depend on local data). Publishing a
fitted carry-over coefficient as "just two numbers".

**Confidence.** High on the rule. One known gap is not closed by it: the two
published notes formed from StatsBomb data carry no StatsBomb logo, which clause
1.4 requires. See KNOWN_LIMITATIONS.

**Reversal.** A written permission from the provider, or a licensed feed whose
terms allow hosted derived values.

---

## ADR-0019 — One evidence mapping; planning surfaces default to progression only

**Problem.** ADR-0001's ladder had no production caller. Profiles carried the
literal "Estimated", XI Lab carried `MEASURED / HEURISTIC / RESEARCH /
UNAVAILABLE`, Match Lab carried `DIRECT / DERIVABLE / REJECTED / UNAVAILABLE`,
and "composition takes the weakest" was hand-labelled per requirement. A page that
joins labs could not compute its own evidence class.

**Decision.** `galactico/domain/evidence.py` is the one place a shipped vocabulary
becomes an `EvidenceClass`, and the one place classes are composed. XI's
`MEASURED` is `ESTIMATED`; `RESEARCH` is `EXPERIMENTAL`; `UNAVAILABLE` and
`REJECTED` are the absence of a number, not a class. A declared input (minima,
locks, exclusions, the slot, an absence) is not evidence and is never coerced into
a class: computed numbers are labelled conditional on the declarations, which are
listed beside them.

Stated consequence. The two side pass-origin requirements that drive the shipped
XI solve are `RESEARCH`, so every result that uses them composes to
`EXPERIMENTAL`, which ADR-0001 says never renders without an opt-in. The shipped
XI Lab is not changed. The planning tools default to the progression requirement
alone and admit the two side requirements only through an explicit
`experimental_opt_in`; the composed class and the inputs that bind it are always
printed.

**Evidence.** `tests/test_evidence_mapping.py`: the tables are total over the
vocabularies the shipped code emits; composition equals `provenance.weakest` under
hypothesis; a default three-requirement problem composes to `EXPERIMENTAL` with
exactly the two side requirements binding, a progression-only problem to
`HEURISTIC` (its minimum is a declared policy).

**Alternatives rejected.** Relabelling the side descriptors as measured. Hiding
the composed class. Changing what XI Lab serves.

**Confidence.** High on the mapping. The ordering of `OPTIMIZED` against
`HEURISTIC` remains the medium-confidence part ADR-0001 already names.

**Reversal.** A side descriptor that survives its own experiment moves to
`ESTIMATED` and the opt-in disappears for it.

---

## ADR-0020 — The squad and transfer tools share one exact kernel whose integers equal the XI solver's

**Problem.** Stress, brief and injection each need hundreds of shortfall solves.
The shipped model takes 0.13 to 3 seconds per solve, and six tools written
separately would be six definitions of the same shortfall.

**Decision.** `galactico/optimization/squad/kernel.py` computes the declared
lexicographic shortfall as a linear epigraph in at most three bounded solves: a
zero-shortfall feasibility check, the least maximum, then the least total on that
level. The frozen solver is not edited; its rounding function is imported, so a
shortfall here is the same integer XI Lab reports for the same squad. Hard
statements ("the minima are reachable", "meets the brief") use the conservative
floor/ceil policy of the hard-floor query. No third policy exists. A certified
level records the model and declarations it was computed under and is refused
anywhere else. Solver limits are deterministic time, not wall clock, so a status
does not depend on machine load.

**Evidence.** On the shipped Madrid scenario the kernel equals `solve_xi` on the
baseline and all sixteen single removals in both formations, and on all 120
absence pairs, at 9-25 ms per value. An independent oracle (itertools, exact
Fractions, no import from the kernel or the solver) agrees on seeded instances and
on Madrid. Review found `membership` answering about a level computed with a
different lock; the level now carries a hash of its declarations.

**Numerical boundary.** A squad can show shortfall `(0, 0)` under half-even
rounding and still be not satisfiable under the conservative policy, within
`(slots + 1) / quantization` normalised units per requirement. Every tool says
which policy a statement uses.

**Alternatives rejected.** Calling `solve_xi` in a loop. Coarsening the
quantisation to make it faster. A weighted sum of the two stages as a search
device (one serialisation away from a scalar). Editing the frozen solver.

**Confidence.** High. The cost of `add_max_equality`, not the integer scale, was
the bottleneck, and the equality with the shipped solver is tested on real data.

**Reversal.** If XI Lab is ever re-versioned, it can adopt the kernel; until then
the two must agree and a test says so.

---

## ADR-0021 — Snapshots for any club and cutoff carry a named eligibility rule set

**Problem.** The only snapshot builder is frozen, reads Spain, defaults to team
675 and applies a 24-player manual table. Any other team returned zero candidates
under the Madrid version string. Squad and transfer questions need other clubs, a
cutoff that is a date rather than a match, and worlds an external player can share.

**Decision.** `galactico/optimization/snapshots.py` stands beside the frozen
`historical.py`. A snapshot is built for a (competition, team, decision match or
bare cutoff date) under a registered `EligibilityRuleSet`. Two exist: the Madrid
manual rules, wrapped unchanged under their shipped version and marked reviewed,
and `provider-position-broad-v1`, marked unreviewed, in which the provider's
four-class position decides. A manual rule set applied to another team is an
error. Worlds have a named scheme: `TEAM_MATCHES` (the shipped draw) and
`LEAGUE_MATCHES` (one weight per league match per world, shared by every player of
that league); leagues are resampled independently and the snapshot says so. A
cutoff is spelled `YYYY-MM-DD` and nothing else. League reference distributions of
starting-XI rate sums are a separate, descriptive object.

**Evidence.** Byte equality with `historical.build_snapshot` for Madrid on
candidates, omitted players, worlds, minima, `dataset_hash` and `xt_version`. The
future-and-same-day poison test passes against a bare date. All twenty La Liga
clubs field a 4-3-3 under the provider rule. Review found that a day-first date
string was parsed month-first, which would have admitted a month of later matches
without a word.

**Numerical boundary.** `LEAGUE_MATCHES` worlds are a different resampling scheme
from the shipped one, with their own namespace; frequencies from the two are not
comparable.

**Alternatives rejected.** Editing `historical.py` (its hash is pinned by E-07 and
E-08). Inferring slot roles from event locations (an unvalidated construct that
would inherit the solver's credibility). Lowering the 900-minute gate to thicken
squads. Pooling a player's minutes across clubs. Pretending worlds couple leagues.
A winter planning scenario: Madrid has nine gated outfield players on 1 January
2018, fewer than the ten the template needs.

**Confidence.** High for parity and temporal integrity. Provider-position
eligibility is a heuristic, too permissive (it does not tell left from right) and
sometimes wrong; depth under it mostly restates the provider's position code, and
every surface that uses it says so.

**Reversal.** A reviewed rule set for another club replaces the broad rule by
registration. A role-inference construct that survives its own experiment would
enter as a third kind, with its verdict attached.

---

## ADR-0022 — Absence stress and the role brief are exact statements about the gated model

**Problem.** The shipped removal table excludes one player from one representative
XI and reports swaps that can be tie noise. Nothing said what a pair of absences
does, which absences leave no XI at all, or what a newcomer at a slot would have
to supply.

**Decision.** Three exact tools on the shared kernel. Slot depth is a chain of
named sets that separates eligibility-, gate-, measurement- and requirement-induced
thinness and prints the omitted players beside every count. Absence stress
enumerates every set of `k` unavailable players (`k = 1, 2`; `3` on explicit
confirmation), certifies each set's least declared shortfall or that it leaves no
fieldable XI, returns all worst sets with ties, and lists every inclusion-minimal
unfieldable set with the slot group that is short. No absence likelihood exists
anywhere. The role brief for a slot is the complete set of minimal requirement
vectors an addition at that slot must supply, in the conservative arithmetic of
the solve it explains; a candidate meets it only through the exact solve with him
placed there. Locked players are not removable in a stress test.

**Evidence.** On the shipped scenario, 17 of 120 pairs and 212 of 560 triples
leave no XI: exactly the pairs predicted by three tight slot groups with one spare
player each. With the seven gated-out players counted, the back four would have
four spare. Under the planning default (progression only) no single absence raises
the shortfall. The brief at left back has eight minimal rows although the squad
already reaches its minima, because the only two players eligible there are
eligible nowhere else.

**Numerical boundary.** As ADR-0020.

**Alternatives rejected.** Absence probabilities, including literature injury
rates. A single "most important player" label. A bilevel interdiction model as the
product path (its certificate is harder to read than a table of solved sets).
Building the brief from half-even sums (it could disagree with the solve that
defines "meets"). Reporting one displaced player from two representative XIs.

**Confidence.** High that the numbers are exact for the declared model. None is
claimed that the model's thinness is the squad's: most of it is the evidence gate,
and the result says so.

**Reversal.** If licensed availability data ever exists, a likelihood-weighted
view is a new, separately claimed tool. Stress over resampled worlds waits for a
verdict on the risk modes.

---

## ADR-0023 — Candidate injection and the break-even carry-over fraction are transport-agnostic statements

**Problem.** The shipped injection helper is untested, re-solves the baseline per
candidate and reports representative-XI entry that can be a tie artifact. Whether
a rate measured at one club repeats at another is untested here: seven players in
the corpus have 900 minutes at each of two clubs. No coefficient fitted on the
local corpus may reach a hosted page (ADR-0018).

**Decision.** The transfer tools state only what follows from arithmetic. The
universe is the gated outfield players of the declared leagues at the cutoff,
valued on one declared xT surface, same league by default; other leagues are an
explicit opt-in and flagged as not adjusted for league strength. The user declares
the slot; admissibility is the provider's broad position; lane shares, foot and
age are shown for a person to judge and no role is inferred. Each candidate gets
an exact forced-inclusion solve, which yields the injected optimum and his
possible and necessary membership. Rows are grouped by a categorical outcome of
that solve, then ordered inside a group by one declared key, with equal keys as
tie groups; no key combines requirements and no ordinal exists. The response
states how many candidates were screened and shows a pool-median reference
injection beside them. The break-even carry-over fraction scales his additive
rates on a fixed grid and reports the smallest value at which a declared
conclusion still holds, with the exact solves that bracket it. No carry-over
function is fitted or applied.

**Evidence.** The injected optimum is the smaller of the baseline and the
forced-inclusion value, and membership follows from comparing the two; both are
oracle-tested. Adding a candidate can never raise the largest shortfall; the total
at the lexicographic optimum can move either way, and both directions are tested.
The shipped scenario's baseline is `(0, 0)`: no candidate can lower it, and the
tool says so instead of listing tie artifacts. One hand-built instance has the
total-only conclusion holding at fractions 0.40-0.70 and 0.90-1.00 and failing
between, which is why the default conclusion is the lexicographic one (monotone by
theorem) and the total-only one scans the whole grid.

**Alternatives rejected.** A learned carry-over or league-strength coefficient
(not identified in the public corpus; the cross-provider one is licence-barred).
Shrinking candidate rates toward a positional mean with an unregistered constant.
A shortlist ordered by modelled change, tiers named by merit, similarity
percentages, or any per-player scalar. A "displaced player": under ties none
exists.

**Confidence.** High for the arithmetic. None is claimed for what a player would
do after a move; the composed evidence class is no stronger than `HEURISTIC`.

**Reversal.** If a public-tier experiment ever supports a carry-over statement for
a construct, the page may show the tested range beside the break-even, never
substituted into the solve. An ordering by a solver output would need an ADR that
overturns the no-rating rule.
