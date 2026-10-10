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

**Since ADR-0027.** The type holds a fourth tier, `REFERENCE_ONLY`: sources that are
reachable and not ours to use. `assert_may_ingest`, `assert_may_host` and
`assert_may_commit` refuse an entry at that tier whatever its flags say.

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

**Evidence.** In the four-league local corpus most distinct starting XIs appear
exactly once and very few recur five times or more, so lineup-level identification
is impossible. The three counts that stood here until October 2026 were taken out:
they are counts of StatsBomb lineups, and this file carries no credit for analysis
formed from that data (ADR-0027). At pair level, one club-season presents roughly 300
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

**Since ADR-0025 and ADR-0027.** The freeze was overridden twice in October 2026 to
correct defects. ADR-0025 names its corrections. ADR-0027 names the curve, the channel
bar, the bundle check and the credit; the same repairs also made the explore route order
a style listing by distance from its pitch-area reference before it cuts the list, and
moved four sentences from the page to the server: the order of a listing, the note above
a comparison's observed-location rows, the sentence beside an estimator signal and the
percentile sentence. Player Lab is frozen except for
those corrections.

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
200 reply passes `runtime.finalize`, which requires the provider set at any depth
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

**Confidence.** High on the rule. The gap named when this was written, that the two
published notes formed from StatsBomb data carried no logo, was closed on 9 October
2026 (LICENSING). The second audit then found the rule itself broken in the product:
the "Why only five?" view served a figure of E-01 inside a sentence and printed the
five labels with no credit, no logo and no link to a note. ADR-0027 records the
repair.

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
anywhere else. The per-solve limit is deterministic time; a
wall-clock request budget also applies, and a solve it cuts off is reported as
undecided, never as a value.

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
manual rules, wrapped unchanged under their shipped version and marked as declared by
hand (no external football review of them is recorded),
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

**Reversal.** A hand-declared rule set for another club replaces the broad rule by
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
already reaches its minima, because Marcelo, one of the two players eligible
there, is eligible nowhere else.

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
injection beside them. A list row shows a candidate's recorded facts, his certified
forced value and his membership; the signed change against the squad's own value is
printed only for a candidate the user opens, beside its certificate. The break-even carry-over fraction scales his additive
rates on a fixed grid and reports the smallest value at which a declared
conclusion still holds, with the exact solves that bracket it. No carry-over
function is fitted or applied.

Stated consequence. With one requirement in force, which is the planning default,
the forced value of a row is a function of the one recorded rate printed in it: a
higher rate gives a lower declared shortfall or the same one. The outcome groups are
then a threshold on that rate, and the rate key lists a group in the order of the
modelled change. That is as near to an ordering by a solver output as this tool
comes. The reply says so in a sentence the page prints above the groups: they
restate one recorded rate under a declared minimum and are not a second piece of
evidence about a player. The default order is the name. The final audit found the
page printing the signed change beside every name and the documents saying nothing
orders players by merit; the row lost the number and the documents the sentence.

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

---

## ADR-0024 — A new route's builds are inside its budget and behind one gate; the copy guard runs at the boundary

**Problem.** The runtime states what every new request does: a server-owned budget
for the whole request, an identical request in flight computed once, two long
computations at a time, a copy guard on every served label. An audit that attacked
the routes on the real corpus found none of the four true at the boundary. Every
Squad Lab request declared its problem under one process-wide lock, before the
result cache was asked and before a budget existed; every Transfer Lab request built
its snapshot and candidate universe the same way. Ten first requests for ten clubs
made an already cached request wait 21.7 seconds, 45 made the page and the static
files wait 30, and a five-league request that took 8.5 seconds reported 0.032 elapsed.
The copy guard ran only in tests, on the replies those tests asked for.

**Decision.**

1. One build gate in `api/planning.py` behind the snapshot, reference and universe
   loaders. One build per key, with later callers handed the first caller's object;
   two builds at once in the process; 429 after the documented wait for a place. A
   key that is already built is returned under the gate's guard and waits behind no
   other build.
2. Every POST starts its budget at handler entry, asks the result cache before
   anything is built, and declares its problem inside the computed function. The
   key is the request as resolved (`canonical_request`: reordered or repeated
   exclusions and locks, reordered presets and declarations, and the club spelling
   of a scenario are one key) and a cheap identity of the corpus files it reads
   (`corpus_token`: names, sizes and modification times; no file is opened). Since
   the second audit the same identity is in the build gate's key: a squad, a league
   reference or a pool built from files that have since changed is dropped and built
   again. The squad and the reference answer to their own league, the pool to all
   five. The dataset hash stays in provenance.
3. The copy guard lives in `domain/labels.py`, beside the key walker, and
   `runtime.finalize` runs it over the string values of every new 200 reply outside
   its provenance blocks. It reads no key, no string under provenance and no error
   body. Keys stay with the key walker and its path-scoped exemptions, so one key
   answers to one rule: thirteen whole keys and, since the second audit, any key one
   of whose parts is one of eight words (rating, ratings, rank, ranks, ranking,
   ranked, merit, overall). Since the second audit a reply read from the result
   store passes `finalize` like a computed one. The refusal names the path and the
   word, never the sentence.
4. Added after the second audit (ADR-0027). At most sixteen planning requests are
   past the result-cache lookup at once, and the seventeenth is answered 429 at once,
   with `Retry-After`. A reply held in memory takes no place.

**Evidence.** Replayed on the real corpus after the change: the ten-club burst
returns six replies and four 429s in six seconds while the cached request answers in
0.01; each reply's elapsed time is within 0.03 seconds of its wall time; two
simultaneous first requests build once. The guard took 2,264 ms on the largest real
reply (1.56 MB, 64,071 strings) and takes 85: one combined pattern asks first whether
a text holds any banned token, which is sound because an allowed phrase is matched
only between non-word characters and removing one cannot create a token. Its answers
equal the plain definition on 300,000 generated strings, of which a seeded 20,000 are
a test. No real reply trips it: 147 replies of 14 routes for six clubs, and every
player and team name in the corpus. The gate, key and budget tests use events,
counters and a patched clock; none sleeps for an outcome.

The second audit then sent 45 identical cold requests at one key, and a stored
reply waited with them. The same probe on the runtime as it was: all 45 answered
after 12.9 seconds, and a stored reply, the page and a static file asked for two
seconds in each waited 10.9 seconds for a worker thread. With the sixteen places:
16 answered when the computation ended, 29 were refused within 0.25 seconds, and
the stored reply, the page and the static file answered within 0.08 seconds.

**Numerical boundary.** A budget does not interrupt a corpus read, so a request can
last its budget plus one build. Each distinct request on the two enumerating routes
still holds one of the two long-computation places, and one problem can be two
requests: a preset sent together with what it sets by hand is one problem, with one
input fingerprint, under two keys, and `confirm_k3` sent with `k` below 3 is a
second key for the same computation. A request identical to one in flight, or one
that needs a build in flight, waits for it with no time limit of its own and holds
one of the sixteen places meanwhile. Identical requests behind one that is refused
for a long-computation place are refused in their own turn, five seconds apart:
with both places held for 26 seconds, four were refused after 5, 10, 15 and 20
seconds. The cache key contains file modification times, so a result store filled
on one machine could not be read on another; nothing ships in one. A failure raised
inside pandas or numpy as a plain `ValueError` is still answered 422 with the
library's sentence, and no error body passes the copy guard.

**Alternatives rejected.** A lock per club with no bound (four concurrent universe
builds took the server from 380 MB to 1,257 MB). Keying the cache on the dataset
hash (it needs the build the lookup exists to avoid). Folding a repeated preset or
league into the key (a refusal would be answered from the stored reply of the
accepted request). Scanning labels in tests only (M-06). Scanning keys with the copy
guard at the boundary as well (a scoreline key exempted by the key walker would be
refused by the other rule). After the second audit: a five-second limit on the wait
for an identical request (it would refuse the second of two ordinary requests behind
an eight-second pool build), and reading provenance with the copy guard (a banned
word in lineage inherited from the frozen solver would be a 500 that cannot be
reworded).

**Confidence.** High for the mechanics. The label guard can refuse a response for a
legitimate name that is a banned word; none exists in this corpus, and a new corpus
would show it as a 500 on the first request that serves the name.

**Reversal.** A hosted, multi-user deployment needs a job queue and precomputed
results. The gate and the sixteen places are single-user devices. Past them a
request is answered 429: at once for a place past the cache lookup, after five
seconds for a build or a long-computation place. A request that waits for an
identical one in flight is not refused for waiting.

---

## ADR-0025 — A construct is published only inside the context it declares

**Problem.** All five shipped constructs declare outfield players as their valid
context. The builder read only the list of excluded contexts, which the two
pass-origin constructs do not repeat, so 26 goalkeepers shipped with both as point
estimates and percentiles among goalkeepers: K. Navas at the 57.7th percentile for
half-space share. The explore route counted 345 players under each style construct
and returned 24 goalkeepers for half-space share; profile and compare served their
estimates and percentiles. The pooled reliability served on outfield rows was taken
over the 333 of the 345 players who have 300 minutes in each half of the match
split, 23 goalkeepers among them.

**Decision.** The registry answers the question and the builder asks it:
`ConstructDefinition.context_excluding(position)` reads the declared valid context
first. The builder's gate names no construct and no position. Outside the
context a profile carries the construct as a withheld row (`out_of_context`) with the
reason and with no value, percentile, interval or reference population. An
unrecorded position withholds. The channel breakdown under a profile bins the same
passes as the two pass-origin constructs, so it is not shipped where they are
withheld. Pooled split-half reliability is taken over the players a construct is
defined for. A bundle records the builder rules it was built under; the artifact key
covers them and the API refuses a bundle built under others. This overrides
ADR-0011's freeze of the Player Lab implementation, and rule R13 of ROOT-DECISIONS
on its outputs, for the corrections named here. The rule is product-wide: it
reached Match Lab's player rows with ADR-0027.

**Evidence.** The rebuilt bundle against the previous one, value by value: 26
profiles differ in what they publish and all are goalkeepers, each with five
withheld rows and no channel breakdown. On the 319 outfield profiles only the
reliability of four constructs moved (progression 0.892 to 0.879, progression per
action 0.898 to 0.894, width 0.983 to 0.979, half-space share 0.9532 to 0.9525) and
no render state changed. The explore route counts 319 players under each style
construct, not 345. Construct version hashes are unchanged: no registry entry was
edited.

**Numerical boundary.** The four pooled reliabilities served on outfield rows stay
above the 0.70 number threshold, so none crossed it. Chance creation's served
reliability comes from a minutes curve and did not move in this change. That curve
was still the published one, taken over a pool with goalkeepers in it; ADR-0027
replaced it.

**Corrected after the second audit.** This record said three things that were not
so. That 20 of the 40 rows the Explore view listed under wide-channel share were
goalkeepers: the route returned the 300 highest values, the goalkeepers held the 26
lowest, and the page drew none. The commit message of `7753b45` repeats that
sentence and cannot be changed. That the reliability had been taken over all 345
players: it was 333. That the channel breakdown restates the pass-origin
constructs: it binned the same passes with other edges, and on 289 of the 319
outfield profiles its half-space shares differed from the printed share by more
than half a point (220 for the wide channels). ADR-0027 binned it with the
constructs' own predicate, and it restates them since that rebuild.

**Alternatives rejected.** Adding goalkeepers to the two constructs' excluded
contexts: a registry edit that changes two published definition hashes to say what
each entry already says. Dropping the rows, as the quality rows were dropped: an
absence with no reason reads as a gap in the data. Keeping the channel bar for
goalkeepers as raw observation: it is the withheld number under the withheld row.
A goalkeeper construct: none has been through the lifecycle.

**Confidence.** High. The gate is a property of the registry and is tested without
data; the bundle test covers every profile.

**Reversal.** A construct whose declared context includes goalkeepers is published
for them by its declaration and a rebuild, with no change to the builder. Since
ADR-0027 the API refuses a bundle whose recorded registry hashes are not those of
the registry in force, so the old bundle is not served in the meantime.

---

## ADR-0026 — Rank correlations use average ranks; published figures are corrected by erratum

**Problem.** The confound audit reported how much of a construct's ordering survives
adjustment as a rank correlation, ranking with an argsort of an argsort. Tied values
then take distinct ranks in whatever order the rows arrive. Sixty to sixty-five
players in each league sit at exactly zero chance creation. Over 1,000 orders of the
same rows the published Stage 1B figure for Spain ranges from 0.8626 to 0.8741.

**Decision.** Average ranks are the definition and the default. The sort-order
ranking stays available under its own name, only to reproduce the record, and warns
when the data are tied. Published reports and result files are records and are not
rewritten: [M-07](docs/research/M-07-rank-ties.md) is the erratum, with every figure
recomputed under both policies by `experiments/run_rank_tie_erratum.py`. The two
runners that produced the records name the sort-order policy explicitly. A rerun of
the Stage 1B runner reproduces all 35 ordering figures of its record; a rerun of
the Stage 1C runner reproduces 11 of the 20 on the public corpus (see Found on the
way). Since ADR-0027 neither runner writes over a record it does not reproduce
unless `--overwrite-record` is given, and under average ranks the top-k survivor
count is undefined where the k-th value is tied with the next, raw or adjusted: the
leaderboard check then fails by name and says how many rows share the value.

**Evidence.** On the public corpus 61 distinct figures were recomputed: the 35 of
Stage 1B, 20 in the Wyscout columns of Stage 1C, 5 of the Stage 1 grid sensitivity
and E-02's T3. 17 move: 8 in Stage 1B and 9 in Stage 1C. The largest change is
0.004369 (Stage 1B, chance creation, Germany). The lowest of the 55 audit figures
is 0.7761 (Stage 1B, England, progression). E-02's T3, the one frozen gate that
reads an ordering figure, is 0.5948. Both are judged against a floor of 0.50, and
T3 clears it by 0.0948, which is 21.7 times the largest correction. Rerun with
average ranks, the 35 Stage 1B statuses and the seven replication labels are
unchanged, and the audit's pass or fail is the same in all 55 cells. E-02's frozen
runner now executes the corrected default; its test T3 has no tied value among 306
players and is identical to the last bit. The other half of Stage 1C was recomputed
in the same way. Its totals are in M-07, which carries the credit they need and prints
none of the twenty figures themselves; none is printed here. The commit message of `d3d3ff5` calls 0.7761 the lowest
figure; it is the lowest of those 55, and the message cannot be changed.

**Numerical boundary.** Reproducing a sort-order figure bit for bit is a statement
about one machine: an unstable sort does not promise the same ranks for ties
elsewhere. The slow test asserts the corrected figures and compares the published
ones with the committed files. On the machine the erratum was run on, a rerun of
the Stage 1B runner differs from its record in 4 of 420 values, none an ordering
figure and none by more than 1.1e-16. By the exact comparison that is still not the
record, and the runner exits 1. No published cell on the public corpus has a tied
twelfth place (0 of 55), so the count rule changed no published count or verdict.

**Alternatives rejected.** Rewriting the published tables. Keeping the sort-order
ranking as the default with a warning: the wrong number by default. Deleting it: the
record could no longer be reproduced.

**Found on the way.** The Wyscout columns of the Stage 1C table mix two xT turnover
recipes and do not reproduce from the corpus as it is: a rerun differs from the
record in 72 of the 220 values of that half, in nine cells. The tracked result file
carried the StatsBomb half of that table in machine-readable form; it is out of the
tree (see LICENSING). E-01's two rank correlations have no script and are not
covered.

**Confidence.** High. The corrected statistic is checked against the definition
written out in the test, against pandas, and against scipy where it is installed.

**Reversal.** None expected. A statistic of the data must not move when the rows do.

---

## ADR-0027 — The second audit: where the declared-context rule reaches, and what a credit, a bound and a tie must say

**Problem.** A second read-only audit confirmed 67 findings in five lenses, each
reproduced by a second reviewer. Rules written in ADR-0018, ADR-0024, ADR-0025 and
ADR-0026 held where each was first applied and not in the next place. Match Lab
served all five registry constructs as numbers for every goalkeeper. The
reliability served on chance-creation rows was the published curve of a pool with
goalkeepers in it. The channel bar was said to restate the two pass-origin
constructs and did not. The "Why only five?" view and seven documents printed
analysis formed from StatsBomb data with no credit: three the audit named
(METRICS.md, KNOWN_LIMITATIONS.md, the E-11 draft) and four found while repairing
(this file, VALIDATION.md, the E-09 draft and the frozen E-02 preregistration).
Forty-five requests on one key held every worker thread. The top-k survivor count still moved with the order of
tied rows. Reference only was a tier of LICENSING and not of the type.

**Decision.**

1. The declared-context rule is product-wide. On a Match Lab player row a registry
   construct outside its declared context is served with no value, the status
   `UNAVAILABLE` and the reason (`match-intelligence-v3`). Team rows, recorded
   counts, the timeline and the passing network are not gated; the last two are
   listed, not repaired.
2. The reliability served on chance-creation rows is the curve of the declared
   population, from `experiments/run_chance_creation_curve.py`
   ([M-08](docs/research/M-08-reliability-pool.md)). The estimator's floor of 1,800
   minutes and the note beside it sit in a hashed registry entry and were not
   changed. Whether the floor should rise is an open owner decision.
3. The channel bar is binned with the two constructs' own predicate. A bundle names
   the five builder rules it was built under (`BUILD_RULES` in
   `galactico/profiles/build.py`), and the API refuses one built under other rules
   or under another registry. The explore route orders a style listing by distance
   from its pitch-area reference before it cuts the list, and the page sorts
   nothing; ADR-0011 lists the four sentences that moved from the page to the server.
4. Analysis formed from StatsBomb data carries the logo and the credit wherever it
   is printed, the served view included; each label there links to its research
   note, and no served string may hold a figure formed from that data. The credit
   block of the README, METRICS.md, E-01, Stage 1C, M-07 and the E-09 draft ends by
   saying what is true of the tree; the blocks of the E-11 and E-12 drafts do not
   yet. This file and VALIDATION are to print no such figure: ADR-0026 gives the erratum's public totals, and the lineup
   counts of ADR-0008 were taken out. The frozen E-02 preregistration quotes two
   figures of E-01 and cannot be edited; it is listed on its own, pinned by its
   sha256. A digest of a provider's files is not data, and a preregistered protocol
   may pin its inputs by one. The StatsBomb estimator's floor in the registry is
   recorded in LICENSING as a known constant.
5. At most sixteen planning requests are past the result-cache lookup at once
   (ADR-0024). A request identical to one in flight still waits for it.
6. Under average ranks a tied boundary of the top k leaves the survivor count
   undefined and the check fails by name. Both record runners name the sort-order
   policy and refuse to write over a record they do not reproduce (ADR-0026).
7. Reference only is a tier of the type, `DataTier.REFERENCE_ONLY`.
8. What was found and left is listed in KNOWN_LIMITATIONS under its own heading.

This overrides ADR-0011's freeze and rule R13 of ROOT-DECISIONS for the corrections
of this record to Player Lab and to Match Lab's player rows.

**Evidence.** Each figure is a builder's, recomputed for this record. In the 38
listed matches 76 goalkeeper rows hold 380 entries with the reason and no value.
On the declared population r is 0.519, 0.601, 0.659, 0.699 and 0.723 at floors of
450 to 2,250 minutes, against 0.544 to 0.756 as published with 134 to 82
goalkeepers in the pool; the script reproduces the published table to its printed
digits first. In the shipped bundle the reliability moved on all 319 outfield
chance-creation rows, 53 of them went from "strong" to "limited", and no value,
percentile or render state moved. The bar moved on 315 of the 319 outfield
profiles and now equals the two constructs to 1.1e-16 on every one; before, 289
half-space and 220 wide sums were off by more than half a point. In the count
example of the tests 45 rows share the twelfth value: the sorted count came out
between 8 and 11 by row order, and there is now no count in any order. The
hostable sources are the three `PUBLIC` ones.

**Numerical boundary.** At the estimator's floor the declared-population
reliability is 0.69925 against a threshold of 0.70, and the lower bound Stage 1B
graded on is 0.668 there and 0.686 at 2,250 minutes. The sixteen places bound
worker threads, not time. The check that no served string holds a figure formed
from StatsBomb data reads four replies; it does not read every route.

**Alternatives rejected.** Scoping ADR-0025 to season profiles: the documents
stated the rule without qualification. Leaving the published curve and saying so.
Editing the floor in the registry: it moves the hash of a published entry, and the
decision is the owner's. A numeric erratum to Stage 1B: its table is true of the
pool it used. Rewording "restates" and keeping the bins. A credit block on this
file. A cap on waiters per in-flight key: two keys under it can still take every
thread. Typing reference-only sources as local with every permission off.

**Confidence.** High where a test holds the behaviour: the corpus test over the 38
matches, the test that the script reproduces both curves, the bundle test of the
bar, the sixteen-places tests on the cache and on all nine planning routes, the
row-order test of the audit. Lower for the process: where a first, interrupted
attempt had left work in the tree, no test was seen failing before its fix, and the
repairs have not been audited (VALIDATION).

**Reversal.** The owner's ruling on the chance-creation floor: raising it edits a
registry entry, and the API then refuses the built bundle until it is rebuilt. A
construct that declares goalkeepers in its context is served for them on Match
Lab's rows by that declaration. A hosted deployment replaces the sixteen places
with a queue (ADR-0024).
