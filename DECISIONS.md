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

**Since ADR-0033, ADR-0034 and ADR-0035.** The freeze was overridden three more times in
November 2026, for `web/index.html` alone: the site shell (ADR-0033), the answer-first page
(ADR-0034) and its second pass (ADR-0035), each for exactly the edits it names. Player Lab's
API returns the same bytes.

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

The registry shipped **empty** until 14 October 2026, when E-11 was registered and
its sixteen LOCAL records added, token `PENDING` (ADR-0029). On 19 October 2026 E-10 was
registered and its seven PUBLIC records added, token `PENDING` (ADR-0031). Every other
subject answers "RECORD ONLY · NOT TESTED". Three protocols remain drafts under
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

---

## ADR-0028 — Provider detail the neutral frames drop lives in a sidecar, as facts

**Problem.** The neutral action schema keeps what every provider can supply. The
public Wyscout data says more: fifty-seven tags in use (body part, duel outcome,
cards, goal zone, own goals and others) and match-sheet fields (bench,
substitutions, card minutes, coaches, half-time scores). Two drafted experiments
need them. New columns in the neutral frames would change files whose hash the
profile bundle records.

**Decision.** `galactico/ingestion/sidecar.py` writes three tables for a
competition beside the neutral frames and never inside them: `events` (one row for
each event that has a position, the event ids of `actions.parquet`), `matches` and
`squads`, with a manifest written last. Every tag id on an event survives in
`tags`. A named column says what one tag, or one family of tags, says, with the
provider's meaning. No column is a construct, and `success`, `goal` and
`clearance` of the neutral frames are not reinterpreted. Raw events are decoded one
at a time. `attach` is the one join: one to one, or it raises. The sidecar is
PUBLIC tier, gitignored like every data file, and built by
`scripts/build_sidecar.py`.

**Evidence.** Built on 10 October 2026 for the seven competitions of the release.
In each the event ids equal those of the neutral frame, the tables verify against
their manifest, and no event carries two tags of one counted family or a tag
outside the provider's dictionary. Spain holds 628,659 events, 380 matches and
13,673 squad rows. A league builds in about ten seconds. An independent reviewer,
with code of its own, recomputed every tag-derived column from the stored tags for
three competitions, rebuilt the squad rows from the raw sheets for two, and
counted the manifest's anomalies from the raw files for all seven; the slow tests
hold the tables to the structure counts of an audit that had counted the raw
files earlier.

**Numerical boundary.** The match table leaves out extra-time and shootout scores,
so for a cup match that went past ninety minutes its two scores are the
ninety-minute score and the winner field says what followed. `verify` shows that
the tables are the ones the manifest records, not that the module as it stands
built them: `builder_source_hash` is in the manifest for a caller that needs to
know. CI builds Spain only.

**Alternatives rejected.** New columns in the neutral frames. A second, wider
adapter. Reading the raw files in each experiment.

**Confidence.** High for what the tables hold. No experiment has read the sidecar
yet, and the two drafts that will were written against other function names
(north-star README).

**Reversal.** A change of schema is a new version directory; `load` refuses a
manifest of another schema version.


---

## ADR-0029 — E-11 is registered; what a page says while it is not run

**Problem.** The E-11 provider-agreement protocol was found READY by a tenth
independent audit, partitioned across nine auditors, and two later revisions were each
verified to add no blocker. Registering it puts sixteen records in the verdict registry,
which the planning pages print. Three sentences the pages served were true only while
the registry was empty: the research block said no protocol was registered, an
unregistered subject said "No protocol covers this quantity." (false for E-11's
`progression`, whose E-12 row printed it), and the shots entry said no protocol covered
shots.

**Decision.** The three files are registered under
`experiments/preregistered/E-11-provider-agreement/` as found ready. `config.json` and
`PIPELINE.md` are byte for byte the draft; `preregistration.md` differs in two lines
only, the draft banner, replaced by a pointer to the documents it cites, and the logo
path, which resolves from the new folder. The draft files become one-line pointers.
`galactico/domain/verdicts.py` holds sixteen LOCAL records, token `PENDING`, built from
the config's own sentences and hashes: thirteen quantity cells and three link tier sets.
Each reads "E-11 · RECORD ONLY · NOT RUN"; none gates, none carries a figure.

The page wording follows the evidence, not the commit. An unregistered subject now
reads "No registered protocol tests this claim." While no E-11 badge reads TESTED, the
research block lists the records and says "The registered protocols are listed with
their state. No quantity shown here has been tested: each is a record, or an exact
computation on what you declared." Once one does, that sentence names what E-11 tested
(agreement between two providers on the same matches), which is not validity or
decision use. The shots entry says that E-11, registered and not run, compares only
whether two providers agree on shot counts.

**Evidence.** The tenth audit's report (all nine scopes READY, no blocker), the
verifications of the twelfth and thirteenth revisions, the three folder digests
recomputed by `scripts/fetch_statsbomb_double_coded.py --check` on the day of
registration, and `tests/test_verdict_registry.py`, which ties every record to the
committed files and the config's sentences.

**Alternatives rejected.** Keeping the registry empty until the run (the records would
then be written after the outcome is known, and the page would keep a false sentence
about E-11's subjects). Serving E-11 records on the local server only (ADR-0018 already
permits a LOCAL label on a hosted page; the records carry no digit and claim nothing).

**Ruled since.** E-11 grades ordering within the Wyscout role code; the E-12 draft forms
its origin cells within the licensed provider's position label. On 16 October 2026 the root
ruled (ROOT-DECISIONS 2.8) that an admission covers an origin cell only for a linked unit
whose two labels agree, so E-12's confirmatory contrasts that rely on one are computed on
those units and the others are reported beside them, outside any verdict.

**Confidence.** High that the registered text is the text found ready. The pipeline is
not built; a defect found while building it is reported in the analysis, never repaired
by editing a registered file.

**Reversal.** None for the files. A protocol found unsound before its run is superseded
by a new experiment id, and this one is recorded as not run.


---

## ADR-0030 — XI exact additions: ranges, minimal conflict, frontier, declared-risk modes

**Problem.** Four limitations of XI Lab were written down and not repaired: infeasibility
diagnostics did not certify a minimal conflicting set; a single maximum was not a frontier;
no robust or regret selection mode existed; and the attainable range of a requirement was
known only through one maximiser. ROOT 2.1 asked for all four as exact computation on the
declared model, each with a written claim, a certificate and an independent oracle. No
OR-XI specification existed when the council stopped.

**Decision.** [OR-XI-SPEC.md](docs/research/north-star/OR-XI-SPEC.md), attacked by three
lenses, ruled by the root (ROOT-DECISIONS 2.7, X1 to X14) and audited twice in five scopes,
is the contract. Four modules under `galactico/optimization/xi/`:

- `ceilings.py`: the least and largest sum of each requirement in force over the declared
  XIs, with the objective rounding for sums and the conservative rounding for any declared
  floor; either end's witness may decide whether a minimum is reached.
- `conflict.py`: a deletion filter over floors, locks, exclusions and slot coverage, each
  removal proved by an INFEASIBLE solve, in the arithmetic of the solve it explains:
  `explain_solve` in the half-even integers of XI Lab's Satisfy rule, `explain_floors` in
  the conservative integers of a hard-floor query (X2). A per-member restore test says
  whether dropping that declaration alone leaves an XI.
- `frontier.py`: the complete set of nondominated requirement-sum vectors over two or three
  declared dimensions, one witness each, with a completeness certificate; no default
  dimension and no ranking, knee or best point (O7).
- `risk.py`: TAIL(k of B), WORST_WORLD as TAIL(1) and MINIMAX_REGRET over the shared worlds,
  on the lexicographic per-world loss in the solver's own integers, searched through the
  exact encoding `BIG = 2·|U|·T_bound + 1` (X3), which preserves the order for a sum of `k`
  encodings and for a regret and is never serialised, logged or displayed (O8).

`galactico/api/xi_extensions.py` serves them; `web/xi-extensions.js` draws them under the
main solve, each panel sending nothing until its button is pressed (X4, X12). The new parts
use progression alone unless the reader opts in to the two experimental side requirements
(X6). No frozen file and not `squad/kernel.py` is edited; the shipped XI routes return the
same bytes with the router present.

**Evidence.** A brute-force oracle (`tests/xi_exact_oracle.py`), written from the spec alone
by an author who built none of the four modules, imports nothing from `galactico`. Each tool
equals it over 120 seeded instances with non-vacuity checks (a three-point frontier, a binding
floor, a summed tail above the bound, a set holding a lock, a floor and an exclusion), and
the risk modes return BALANCE's pair with one world. CEILING's largest end matches the
shipped maximiser's arithmetic (X7). A three-way review against the spec's checklist
follows the build.

**Numerical boundary.** Three named policies (X1): the shortfall rounding of `solver._q`,
the conservative floor and ceiling of hard statements, and the exact half-even objective.
A floor is met in the conservative model, so an XI within `(a_r + 1)/q` of the club median of
a raw floor can be left out. Integers are read from the solver's values, never from its
objective value. A declared problem whose encoding would overflow is refused.

**Alternatives rejected.** Calling `maximize_requirement` per requirement (no minimiser, every
minimum a floor, warnings that fail the copy guard); QuickXplain; a weighted sum for the
frontier; a probability for a tail; a default dimension; editing `kernel.py`; the literal O8
BIG, which a sum of `k` encodings can carry past; a stand-alone page beside `/xi`.

**Relation to ADR-0020 and ADR-0024.** ADR-0020's rejection of a weighted sum of the two
stages as a search device stands for the kernel; O8 overrides it for the risk modes only,
because the encoding is exact by construction and never leaves the solve. The router's
snapshot loader is behind ADR-0024's build gate, and `xi.risk.tail` is a long route (X5).

**Run times and peak memory (X5; OR-XI-SPEC 11 item 15).** The root ran
`scripts/time_xi_risk.py` in the dispatch-only `root-checks` job on the corpus (run
39163120253, `main` at `6c6529d`, 18 October 2026): 84 calls, both Madrid scenarios × B in
{12, 40} × formations 4-3-3 and 4-3-1-2 × the opt-in off and on × every menu entry, with the
default minima and no lock or exclusion, the first call of each scenario and B made cold.
Every call was `CERTIFIED` and `EXACT`; `finalize` refused none, none raised, and no world was
set aside. At B = 40 the warm routes took 0.11 to 0.37 s for TAIL and WORST_WORLD and 0.20 to
0.48 s for MINIMAX_REGRET, against budgets of 60 and 150 s; the largest single selection solve
took 0.17 s of wall time, and no solve reached its deterministic limit. A cold first request
at B = 40 took 0.94 to 1.02 s, of which the snapshot build was 0.76 to 0.86 s (at B = 12, 0.87
to 0.99 s, build 0.78 to 0.90 s). The peak RSS of the timing process was 653 MB, the largest
per-call peak (483 to 533 MB on warm calls). That process held one router snapshot at a time
(the harness clears the loader before each cold call); the router keeps up to four, so a
server's footprint with 40 worlds on offer was not measured. With 40 worlds offered, the
loader (`_match_snapshot`, `maxsize=4`) no longer holds every (scenario, worlds) pair: the two
scenarios at 0 worlds (ceilings, conflict, frontier), 12 and 40 are six keys, so a reader who
moves between them can evict a snapshot and pay its build again, 0.76 to 0.90 s in this run.
The size stays four; raising it would first need the peak measured with all six built. X5 is
met: 40 worlds joins the risk menu in the change that records these figures
(`OFFERED_WORLDS = (12, 40)`, with the tail counts 4, 10 and 20), and a 40-world reply states
`RISK_PREFIX` while the prefix test of `tests/test_xi_risk.py` passes.

**Confidence.** High that each tool computes what its claim says on the declared model, by
the oracle. The 40-world risk option is offered since its solves were timed on the corpus
(above); those times are of the two Madrid scenarios with the default declarations, and a
solve that runs past its route's budget is reported as not certified.

**Reversal.** E-13's verdict relabels the risk modes. A change of policy is a new version of
the affected module and of its served constants.


---

## ADR-0031 — E-10 is registered; its record waits for its run

**Problem.** The E-10 conceded-shape protocol was found READY: a third independent audit
confirmed no blocker in its third revision, three verifiers found that the fourth revision's
edits added none, and an independent check of its alignment with ROOT-DECISIONS 2.12 (N2,
N6) claimed none and reported four minor findings, A12-1 to A12-4 (the draft's
`REVIEW-RECORD.md`). Registering it puts seven PUBLIC records in the verdict registry, which
the planning pages print, and makes one served sentence false: planning's `shots` entry said
"No registered protocol tests one", and E-10 registers `conceded_shots_inside_box_share`.

**Decision.** The four files are registered under
`experiments/preregistered/E-10-conceded-shape/` as found ready, in one commit, as the
draft's `PIPELINE.md` section 13 lists. `config.json`, `PIPELINE.md` and
`descriptor_test_vectors.json` are byte for byte the draft; `preregistration.md` differs in
one line, the DRAFT banner, replaced by the line `PIPELINE.md` section 0 gives. It draws no
logo: it prints no figure formed from StatsBomb data, and the only E-10 document that will
draw one is `analysis.md` (section 12.4). The draft's four files become one-line pointers;
its `REVIEW-RECORD.md` stays as the record of review. `galactico/domain/verdicts.py` holds
seven PUBLIC records, token `PENDING`, built from the config's own sentences and the hashes
of the registered files: the six descriptors (claim token "TENDENCY, ONE SEASON") and the
level (claim token "VOLUME, ONE SEASON"). Each reads "E-10 · RECORD ONLY · NOT RUN"; none
gates, since `may_gate` needs an executed ESTABLISHED record, and none carries a figure until
the results commit (section 12.2).

The page wording follows the evidence, not the commit. Every record is `PENDING`, so the
research block lists E-10's records beside E-11's and keeps "The registered protocols are
listed with their state. No quantity shown here has been tested: ...". The `shots` entry
keeps its id, term and status and now reads: "No shot construct is shown. E-11, registered
and not run, compares only whether two providers agree on shot counts; E-10, registered,
tests a team-level conceded shot share that no planning page shows, and its badge says
whether it has run." (ROOT 2.12 N6; A12-2 added the last clause, without which "registered"
beside E-11's "registered and not run" implied that E-10 had run.) It stays true at E-10's
results commit, which leaves it.

The prior-date record of Opponent Lab, not yet built, is withheld until E-10's results
commit, when all seven records are `EXECUTED` (ROOT 2.12 N1, N2; the protocol's Product
consequence). The frozen table shows it from then for every subject, while ROOT 2.12 N4 holds
S3, S4 and S5 back until a registry record under `"E-09"` exists (A12-1). The two agree only
if E-09 is registered by then, so **E-10's results commit follows E-09's registration**
(route (a) of A12-1). The other route, carrying N4's condition in the frozen table, was an
edit to a READY draft needing its own audit, and is not taken.

**Before registration** (section 13; each a check the root repeats).

- Audit: the third audit, the verification of the fourth revision and the verification of
  the ROOT 2.12 alignment, none with a confirmed blocker. A12-2 and A12-4 were applied, A12-1
  by the order above; A12-3 is a fix to `OPPONENT-DESK-SPEC.md`, passed to that file's own
  audit, and the E-10 files need none.
- Pipeline hash: `pipeline_spec_sha256` is `lf_sha256` of the registered `PIPELINE.md`,
  `3aa89efb8931973a5089d5ba0f661a5db4d2763da7e8b20090c5cac5c34a1353`, recomputed after A12-2.
- Fingerprints: recomputed from the payloads of `descriptor_test_vectors.json`; all six and
  all four equal `descriptor_fingerprints` and `descriptor_fingerprints_sb`.
- Structure-only counts (`verified_by_root_before_registration` items 3 to 5; ROOT 2.9 Z2,
  Z6): run by the root in the dispatch-only `root-checks` job (check `e10-counts`, run
  39163118449, job 117780407620, `main` at `6c6529d`, 18 October 2026) with
  `scripts/e10_root_counts.py` (`lf_sha256`
  `52595dc72b7c6240c8921bad40b7bc2a35891bd7a194b3a871453b89c0116e6c`) on the draft config
  (`lf_sha256` `e3a56391c320e3cf8cd1699da51d91630373c0d1fee54e9783912c459fb80c39`), from the
  tag sidecar `wyscout-tag-sidecar-v1` with tag mapping `wyscout-v2-tags2name-57live-v1` in
  all five leagues. The registered config differs from that one in `pipeline_spec_sha256`
  only, which no count reads. They are counts; no outcome was computed.

  The dismissal assumption, per league: the players whose event record carries a
  `second_yellow` card in `regulation_periods`, those among them whose sheet `red_minute` in
  that match is not null, and the share, against `dismissal_assumption_minimum_share` (0.5).

  | League | `second_yellow` players | `red_minute` not null | Share | Holds |
  |---|---|---|---|---|
  | Spain | 42 | 42 | 1.0000 | yes |
  | England | 19 | 17 | 0.8947 | yes |
  | Italy | 45 | 45 | 1.0000 | yes |
  | Germany | 22 | 22 | 1.0000 | yes |
  | France | 33 | 33 | 1.0000 | yes |

  No pair was left out in any league (none credited to player 0, none of a player not on that
  match's sheet, none with every `second_yellow` event outside `regulation_periods`). The
  assumption holds in every league, the lowest share being England's 17/19, so
  `dismissal_check` stands and `dismissal_check_fallback` is not used.

  The residuals, which `dismissals_mismatch` is built to invalidate and only G1 bounds. Event
  record to sheet (players with a regulation dismissal card and a null sheet `red_minute`):
  Spain 0 of 71, England 2 of 41 (both `second_yellow`), Italy 0 of 91, Germany 0 of 43,
  France 0 of 86; none is off the sheet, none is player 0, none is listed under another team.
  Sheet to event record (sheet players whose `red_minute` is not null and who carry no
  regulation dismissal card): Spain 0 of 71, England 0 of 39, Italy 0 of 91, Germany 0 of 43,
  France 1 of 87, a player with no dismissal card outside `regulation_periods` either.
- E-11 order: E-11 was registered on 14 October 2026 (ADR-0029) and its pipeline built and
  stamped on synthetic data; it has not run. Its directory holds no `results.json` and no
  `analysis.md`, so no E-11 analysis exists and none was read. The case `reuse_disclosure`
  names (E-11 ran first) does not arise.
- Split calendar count (`reliability_split`, third audit 2-1): per league and half, the teams,
  each team's meetings in the half, and the distribution over teams of the share of those
  meetings dated before `evaluation_start` (2018-01-01) and of the share at home, written
  share: number of teams. Every meeting is counted (the match table's validity is not built),
  and no team lacks a meeting in either half. It changes nothing in the rule.

  | League | Half | Teams | Meetings | Before `evaluation_start` | At home |
  |---|---|---|---|---|---|
  | Spain | A | 20 | 19 | 8/19: 2, 9/19: 18 | 9/19: 11, 10/19: 8, 11/19: 1 |
  | Spain | B | 20 | 19 | 8/19: 20 | 8/19: 1, 9/19: 8, 10/19: 11 |
  | England | A | 20 | 19 | 11/19: 20 | 9/19: 11, 10/19: 8, 11/19: 1 |
  | England | B | 20 | 19 | 9/19: 2, 10/19: 18 | 8/19: 1, 9/19: 8, 10/19: 11 |
  | Italy | A | 20 | 19 | 10/19: 20 | 8/19: 3, 9/19: 7, 10/19: 7, 11/19: 3 |
  | Italy | B | 20 | 19 | 8/19: 4, 9/19: 16 | 8/19: 3, 9/19: 7, 10/19: 7, 11/19: 3 |
  | Germany | A | 18 | 17 | 9/17: 18 | 7/17: 4, 8/17: 5, 9/17: 5, 10/17: 4 |
  | Germany | B | 18 | 17 | 8/17: 18 | 7/17: 4, 8/17: 5, 9/17: 5, 10/17: 4 |
  | France | A | 20 | 19 | 10/19: 20 | 6/19: 1, 7/19: 1, 8/19: 2, 9/19: 5, 10/19: 7, 11/19: 4 |
  | France | B | 20 | 19 | 9/19: 20 | 8/19: 4, 9/19: 7, 10/19: 5, 11/19: 2, 12/19: 1, 13/19: 1 |
- Replication label: nothing open (ROOT 2.9 Z5); E-10 creates no record for its LOCAL arm.

**Evidence.** The draft's `REVIEW-RECORD.md` (every round of review, the audits'
dispositions and the alignment's verification), the counts' job log, and two tests:
`tests/test_verdict_registry.py` ties every record to the committed files and the config's
sentences, and `tests/test_protocol_drafts.py` checks the registered files' pipeline hash,
serves every registry and figure sentence through `finalize` under `PENDING` and every
token, and walks every key of the config and the vectors for a provider's name or the `SB_`
prefix, each with a planted defect it must find.

**Alternatives rejected.** Keeping the registry empty until the run (the records would then
be written after the outcome is known, and the `shots` entry would keep a false sentence).
Showing the prior-date record from registration (ROOT 2.12 N1: the registry cannot tell the
code-review window, in which no WP A file may run on `data/`, from the time after the gate
stamp). The `shots` wording "E-10, registered and not run" (a second rewording at the results
commit, which section 13 does not schedule). Carrying N4's condition in the frozen table
(route (b) of A12-1, above).

**Number.** `OPPONENT-DESK-SPEC.md` and ROOT-DECISIONS 2.12 (N5, N7) had named the Opponent
Lab and desk ADR "ADR-0031". This registration takes that number; that ADR is ADR-0032, and
both files were renumbered in this change.

**Confidence.** High that the registered text is the text found ready and verified. The
pipeline is not built; a defect found while building it is reported in the analysis, never
repaired by editing a registered file.

**Reversal.** None for the files. A protocol found unsound before its run is superseded by a
new experiment id, and this one is recorded as not run.

---

## ADR-0033 — One app: unified shell, navigation and design system

**Problem.** The product was two products that did not know about each other. The labs
(Player, Match, XI, Squad and Transfer Lab, 2017/18) carried a dark monospace look, a
"Laboratories" nav of five links written by `galactico/api/shell.py` and copied by hand into
four pages, and a fourth nav of Player Lab's own. The current-season pages (Lineup studio, Match
centre, Leagues, Scouting) carried a light look, a "Workspaces" nav of four links, and a demo
page (`/match-centre/demo`) that printed invented key-pass and interception counts beside the
names of real players, linked from three footers. `/` was Player Lab on the local app and the
Lineup studio on the hosted one. Nothing linked the two halves except one line of Player Lab's
copy; five wordmarks, four header designs, 150 colours and labels of 8 to 11 px made every page
harder to read than it had to be (the UX audit of 26 November 2026). R13 pins the shipped
pages' bytes, and ADR-0011 freezes Player Lab; both had to give way for exactly the edits below.

**Decision.** One shell, one navigation and one design system for every page of both apps.

- *Design system.* `web/tokens.css` is the only sheet with colour literals: primitives
  (`--c-*`) and roles named by job (`--bg`, `--surface-1/2/3`, `--text`, `--text-muted`,
  `--border`, `--border-control`, `--accent`, `--selected`, `--live`, `--danger`, `--warning`,
  the pitch, chart, studio and heat roles), each role with a light and a dark value. Light is
  the default; dark follows `prefers-color-scheme` and a reader's choice (`[data-theme]`,
  `web/theme.js`). Pitch and chart surfaces are dark in both themes. `web/base.css` (fonts,
  reset, type scale, links, a two-tone focus ring that is never gold) and `web/components.css`
  (the shell and `ui-*` components) follow. `tokens.css`, `base.css` and `components.css`
  declare the order `@layer tokens, base, legacy, components, page;`; every older sheet and
  every page's own `<style>` is wrapped in `@layer legacy`, and `about.html`'s in `@layer page`.
  Gold (`#c9a227`, `--selected`) marks the selected subject and nothing else; on a light
  surface it is a fill with its dark edge (`--selected-edge`), never a bare line, and focus is
  no longer gold. No sheet or page style sets text under 12 px or a colour literal. Two kinds
  of drawing are held to the same rule another way: a label an SVG draws in its viewBox's units
  is kept at 12 px on screen by `web/site.js` (it raises the label's size in drawing units to
  12 px over the drawing's scale, on load, on a redraw and on a change of width), and a canvas
  reads its colours and its 12 px type from the tokens when it draws (Player Lab's scatter,
  the studio's activity map). Labels are sentence case, and one eyebrow style is the only
  uppercase text. Monospace is for ids and raw records only. Type is DM Sans, with Barlow
  Condensed for display.
- *The labs, restyled with no change of markup.* `web/labs.css` re-points the names the lab
  sheets read (`--line`, `--chalk`, `--muted`, `--surface`, `--ink`, `--gold`, `--serif`,
  `--mono`, `--ui`) at the roles; `labs-shared.css`, `planning.css` and `xi-extensions.css`
  keep their pinned variable sets and selectors and lose only their 9 to 11 px monospace
  uppercase labels. A pitch and a chart re-point the same names for what they hold. Player
  Lab's inline palette (`--ink-*`, `--bone-*`) and the inline styles of Squad and Transfer Lab
  are re-pointed the same way. Match Lab draws its two teams in `--chart-team-1/2` and its
  tabs read "Key", "Tactical", "All", "Volume" and "xT value".
- *The current-season pages, on the same tokens.* `web/match-centre.css` is the one sheet of
  Matches, Table and Scouting; `web/centre-theme.css`, which repainted a dark theme no page
  showed, is deleted with it. `web/studio-shell.css` keeps the frame only (its private
  `--navy`, `--violet`, `--muted`, `--rule` and `--cream` are gone), and `web/studio.css` and
  `web/goal-scout.css` read roles (`--card`, `--line`, `--faint` and `--mint` are gone). The
  Match centre's "Data source" select is shown only where a second source exists.
- *Shell.* `galactico/site_nav.py` (standard library only, shipped to Vercel through
  `vercel.json` `includeFiles`) writes the skip link, the header (the lime G wordmark, the
  navigation, the season chip "2026/27" or "2017/18 archive · La Liga", the theme switch), the
  phone tab bar (44 px targets, 12 px labels), the sub-navigation (below) and the footer
  ("About the numbers", the page's data credits, the type credit). It writes each page's
  `<title>`, preloads the three type files above the fold (DM Sans, upright Barlow Condensed for
  the headings, the italic of the wordmark), gives `<main id="main">` `tabindex="-1"` so the skip
  link moves focus, labels the theme switch with a tooltip, and loads `web/site.js`, the one
  script every page shares (the SVG label floor, the archive-missing state, the focus ring and
  pointer area of a mark on a pitch). Every page file holds `<!--shell:head-->`,
  `<!--shell:header-->` and `<!--shell:footer-->`, one `<main id="main">` and no `<title>`;
  both apps serve every page through `site_nav.page()`. `/about` ("About the numbers") is on
  both apps; its opening sentence and its list of contents are built from the sections the
  app serves (the hosted page, with one section, has no list).
- *Sub-navigation.* A destination with two or more pages the app serves gets a second row under
  the header, `<nav class="site-subnav" aria-label="… pages">`: each page by name with its
  season, the page shown marked `aria-current="page"`. Matches: "Matches 2026/27" and "Match
  reports 2017/18 archive" (`/match-centre`, `/match`); Players: "Goals by opponent 2026/27" and
  "Player profiles 2017/18 archive"; Lineup: "Lineup 2026/27" and "Check against targets
  2017/18 archive" (`/lineup`, `/xi`); Squad & signings: "Squad depth" and "Signings" (`/squad`,
  `/transfer`). Without it Match Lab and XI Lab linked only each other on the local app. The
  hosted app serves one page per destination and shows no second row.
- *Navigation.* Five destinations in one order everywhere, `<nav class="site-nav"
  aria-label="Main">`: Matches (`/match-centre`, else `/`), Table (`/match-centre/leagues`),
  Players (`/player`, else `/match-centre/scouting`), Lineup (`/lineup`, else `/xi`), Squad &
  signings (`/squad`, else `/transfer`). Each link is `<a href="…" data-nav="key">` with an icon
  and a label. A destination is listed only when the serving app answers a GET for one of its
  routes, and links to the first it answers. Exactly one link carries `aria-current`: `"page"`
  when it opens the page shown, `"true"` when the page shown is another page of that
  destination. `shell.nav_markup`, `shell.DESTINATIONS`, the two `nav-sep` separators, the
  "Laboratories" and "Workspaces" navs, the `.brand` and `lab-tag` mastheads and the kit's
  `Shell.nav` and `Shell.header` are removed.
- *Routes.* `/` is Matches on both apps (`make_router`'s route). Player Lab moves to `/player`;
  on the local app `/?player=` and `/?view=` answer 308 (permanent) to `/player?…`, and on the hosted app
  the same link opens Matches. Old `/?day=`, `/?match=` and `/?source=` links still open the
  board. `/match-centre/demo` answers 308 (permanent) to `/match-centre`; `web/matchroom-demo.html` and its
  three footer links are deleted (R8: no evidence class describes an invented number). Every
  other existing URL still answers 200: `/match-centre`, `/match-centre/leagues`,
  `/match-centre/scouting`, `/lineup`, `/match`, `/xi`, `/squad`, `/transfer`.
- *Titles and headings.* The shell writes every title in one pattern, "<page> · <destination>
  · Galáctico", or "<destination> · Galáctico" where the page bears its destination's name:
  "Matches", "Table", "Goals by opponent · Players", "Player profiles · Players", "Match
  reports · Matches", "Lineup", "Check against targets · Lineup", "Squad depth · Squad &
  signings", "Signings · Squad & signings", "About the numbers". The H1 of a page names its
  object or its question: "Matches", "League tables", "Goals by opponent", "Lineup.", "Where is
  cover thin?" (Squad) and "Who could fill this position?" (Transfer), the audit's glossary.
  One h1 per view: Match Lab's two team names are h2 of its scoreboard, and Player Lab's
  player and comparison names are h2 (each of its five views keeps one h1). The league table's
  "Rank" column is "Pos". The H1s of Player Lab's views and XI Lab are the page groups' to
  rewrite, answer first.
- *States a reader can act on.* A missing archive reads "The 2017/18 archive isn't installed
  on this server." on every archive page, with the setup steps linked only on a loopback
  address: any 503 in the kit's `errorText` (Squad, Transfer, XI's panels) and on a page's first
  request (Match, XI and Player Lab, whose boot no longer fails silently), and the server's
  corpus-absent detail on a later one. The server's own detail ("run the Pappalardo
  fetch/ingest") is not shown; a later failure of one match or one solve still prints the
  server's words.
  The scouting page says "Player comparison needs a licensed data key and runs only on a local
  install." where it told visitors to set `API_FOOTBALL_KEY`; the key's setup is in the README
  only.

**The R13 and ADR-0011 override (in the form of W8).** This change overrides R13, and ADR-0011
for `web/index.html`, for exactly these edits, and for nothing else of the pages' behaviour:

- the nav bytes of `web/index.html`, `match.html`, `xi.html`, `squad.html` and `transfer.html`
  (the hand-written header replaced by the three placeholders), of `studio.html`,
  `match-centre.html`, `leagues.html` and `scouting.html` (the "Workspaces" nav), and Player
  Lab's view switch, which moved from its header into a bar inside `<main>`, without the
  one-way "→ Match centre" line;
- the `<title>` of every page, `<main id="main">`, and the head placeholder before every sheet;
- the routes above, and the demo's removal;
- the page chrome and the look: every sheet listed above, the inline `<style>` of
  `index.html`, `squad.html` and `transfer.html` (re-pointed tokens, 12 px sentence-case labels;
  Squad Lab's style comment now says the focus ring is not gold), Player Lab's bootstrap-dots
  box, the colours Match Lab's script draws its teams and passing edges in, its five tab labels,
  the key swatches of Transfer Lab's carry legend, and the Match centre's source select;
- the files and handlers the shell needed: `galactico/api/player_lab.py` (root-owned: its `/`
  route removed, `/player` added, `app.state.about_sections`), the page handlers of
  `galactico/api/decision_lab.py`, `squad_lab.py` and `transfer_lab.py` (each `FileResponse`
  replaced by `site_nav.page`; `/match` and `/xi` stay in the OpenAPI schema, now with a
  `text/html` response type), and the new `galactico/api/about.py`, `web/about.html`,
  `web/assets/favicon.svg` and `web/site.js`;
- the review round's page edits: Player Lab's selected-player marks (the percentile tick and
  the channel-share dot in an overlay, gold with its edge; the bootstrap dots round, edged and at
  full strength), its scatter (token colours, 12 px DM Sans), its "external replication" line
  (12 px, not monospace), its removed in-page tier chip and its boot's error state; Match Lab's
  `api()` (it keeps the HTTP status), its flow chart's axis labels (every half hour on a phone)
  and the focus ring and pointer area of its shot and passing-network marks; XI Lab's `api()`,
  its 503 state, and its pitch marks' focus ring and pointer area; the depth pitch's focus ring
  (Squad), its slot labels left to the list on a phone, and the "not measured" panel of Squad
  and Transfer behind a disclosure closed on arrival; Transfer's row-fill status, which now
  prints the kit's markup; the edge on Transfer's selected carry notch; the studio's activity
  map, which reads its colours from the tokens and carries its own "2017/18 archive" chip; the
  league table's columns on a phone; and the scouting page's setup note;
- the pinned tests, re-pinned in the same change: `tests/test_web_shell.py` (rewritten: every
  page is a page of the shell, every old sheet sits in `legacy`, every inline style in a
  layer), `tests/test_shell_payloads.py` (the navigation is the site shell's; the kit draws
  none), `tests/test_shell_render.py` (no `nav` in the kit's markup or sheet;
  `nav[data-nav=v2]` no longer required), `tests/test_squad_api.py` and
  `tests/test_transfer_api.py` (the new nav link and titles), `tests/test_lineup_studio.py` and
  `tests/test_match_centre.py` (`/` is Matches; the demo redirects, 308, and its file is a 404),
  `tests/test_xi_extensions_render.py` (`SHIPPED_XI_HTML` re-pinned once, for the shell and the
  three script edits above; the five additive edits are unchanged; the old pin is in its
  docstring; its `selectors()` helper now steps into `@layer` blocks),
  `tests/test_planning_render.py` and `tests/test_shell_render.py` (the kit's archive-missing
  sentence), `tests/test_web_render.py` (the bootstrap dots); the e2e specs `e2e/smoke.spec.js`
  (Player Lab at `/player`; its player and comparison names are h2), `e2e/labs.spec.js` (the
  sentence-case tab names), `e2e/transfer.spec.js` (the current mark is `data-nav="squad"`,
  `aria-current="true"`), `e2e/squad.spec.js` (a comment, and the H1),
  `e2e/match-centre.spec.js` (the demo is gone; the shell on every page at 1440, 390 and 320 px;
  the scouting page's unavailable state; and four new gates: every served page reached from `/`
  by the pages' own links, the sub-navigation, no visible text under 12 px at 390 and 1440 px
  measured on screen, SVG labels included, and keyboard focus never under the phone tab bar),
  and `e2e/screenshots.spec.js` (Player Lab at `/player`); and the new tests
  `tests/test_site_nav.py` and `tests/test_design_tokens.py`.

No API reply changes: the `/api/*` routes, the frozen files and the planning and XI payloads
return the same bytes, and no server sentence is written in the browser.

**Evidence.** The UX audit of 26 November 2026 (the six jobs, the twelve problems, the
constraint map) and the redesign brief. `tests/test_site_nav.py`: the module imports nothing
from `galactico` and ships with the hosted function; each app's nav links only routes it
serves; exactly one `aria-current`; the season chip, the studio's archive chip included; one
title pattern; the sub-navigation; a crawl from `/` over the served pages' links reaches every
page on both apps; the credits equal the provider registry's; `/` and every old link on both
apps. `tests/test_design_tokens.py`: no colour literal in any sheet, page style or script but
`tokens.css`; every role has both themes; text 4.5:1 and control borders (the studio board's
included), the focus ring, the pitch lines, chart marks and both team colours 3:1 on every
surface they appear on; gold is `--selected` only, never focus, and wherever a page or a script
paints it on a light surface it has its edge; no sheet, page style, inline style or canvas sets
text under 12 px; one archive-missing sentence and no command in any page. The e2e suite on the
local corpus, with the gold, ordering and 390 and 320 px overflow checks unchanged, and the four
new gates above.

**Alternatives rejected.** Two navs, one per season (the audit's first problem). A nav listing
every route on every app (a link to a page the app does not serve is a 404, `shell.py`'s old
rule). Keeping `/` per deployment. Keeping the demo with a louder disclaimer (R8). Rewriting
the lab markup now (the page groups that follow own their pages; this change keeps markup).
Re-styling the labs by editing every rule of every sheet (the pinned variable sets of
`labs-shared.css` and `planning.css` exist so that one sheet can re-point them). Gold for focus
(two meanings for one colour).

**Opponent Lab and the desk (ADR-0032, reserved).** `OPPONENT-DESK-SPEC.md` section 11 asked
for two more links in the old lab nav. That request is amended in this change: Opponent Lab,
when built, joins the site navigation (`site_nav.NAV` and `site_nav.PAGES`) as a sixth item or
under Matches, decided in ADR-0032, and its page carries the three placeholders like every
other.

**Confidence.** High that every page is served inside the shell, that each app links only what
it serves, and that the colour, size and contrast rules hold for every sheet (the tests above).
Medium on the look itself: the labs keep their old layout, which the page groups that follow
replace one page at a time, answer first.

**Reversal.** A reader study showing that the job-based nav hides a lab people looked for; a
host that serves pages without the shell (the placeholders would then need a static fill).

---

## ADR-0034 — Answer-first pages

**Problem.** ADR-0033 gave every page one shell and one design system, and kept every page's
markup. The pages still opened on controls, caveats and research vocabulary: Squad Lab was about
22,000 px tall on a phone, the XI page opened on a goalkeeper and a form, the Transfer page made
a reader press "Set the problem" and "Re-solve" before any answer and then grouped its list by
the outcome of the re-solve, Player Lab kept no state in its address, a match report linked
every match to an XI scenario it did not have, and the current-season side was stale or empty
where its sources lagged (La Liga goals were a 503 everywhere; the Bundesliga and Premier League
tables stopped weeks back; the board opened on an empty day; the Champions League was missing).
The UX audit of 26 November 2026 (sections 3.3, 3.4, 4.7, 4.8, the gaps F1 to F20) and the
redesign brief's decision 4 asked for one template on every page, answer first. R13 pins the
shipped pages' bytes and several shipped replies, and ADR-0011 freezes Player Lab; both give way
for exactly the edits below.

**Decision.** Every page follows one template: the season chip (the shell's), an H1 that names
the object or the question, one answer sentence the server writes, then the primary visual,
then detail in tabs or disclosures closed by default, then "About these numbers", closed. Words
follow the audit's glossary (section 4.7). Loading, empty, unavailable, error and withheld
states are designed, and no developer text reaches a reader. Every page works at 1440, 390 and
320 px with no horizontal overflow and 44 px targets on a phone.

- *The answer sentences, on the server (R10).* No football sentence is assembled in a browser.
  The full app's sentences are written in three new modules beside the frozen lab APIs, each
  asking the lab route itself so a sentence is about the reply the page holds and a refusal
  there is the same refusal here, and each passing `api.runtime.finalize`:
  `galactico/api/player_answers.py` (`GET /api/answers/player/{id}`, `/api/answers/compare`,
  `/api/answers/explore/{construct}`, `/api/answers/matches`, `/api/answers/match/{id}`),
  `galactico/api/xi_answers.py` (`GET /api/answers/xi/scenarios`, `POST /api/answers/xi`) and
  `galactico/api/planning_answers.py` (`GET /api/planning/targets`, `POST /api/squad/answer`,
  `POST /api/transfer/answer`). The hosted app's sentences are written in
  `galactico/match_centre/answers.py` (Matches and Table), `goal_scout.py` (Players),
  `scouting.py` (Real Madrid against La Liga) and `studio.py` (Lineup). The hosted function
  cannot import `galactico.domain`, so `tests/test_matches_table.py`, `test_goal_scout.py`,
  `test_season_scouting.py` and `test_lineup_studio.py` run every sentence shape through
  `scan_labels`. Every number in a sentence is one the reply carries (R8); a list is in the
  order of a declared, visible key (R1); a percentile sentence follows the registry's order,
  never the player's highest first.
- *Matches and Table* (F2, F3, F7, F8, F10, F16, F19). `galactico/match_centre/openligadb.py`
  fills a result OpenFootball's Bundesliga and Premier League files have not reported from
  OpenLigaDB (`bl1`, `pl`), once `goal_scout.verify_fixtures`' club matching confirms both
  clubs and the matchday; a result OpenFootball has is never replaced, and a filled result
  takes the feed's date (the old one kept as `scheduled_date`). The Champions League comes
  from OpenLigaDB `ucl` alone, written in OpenFootball's row shape, its clubs named as
  OpenFootball names them, else in English (`CLUB_NAMES`). `freshness.py` says how current
  each competition is from its own rows ("Results through Sun 20 Sep", "Table after matchday 7
  of 38", the count of later fixtures without a result), shown in place of a "last checked"
  time. The board opens on the nearest day with fixtures (the server picks it when `day` is
  left out), filters by competition, polls only while a match is in play, and lists saved
  matches across dates (`GET /api/match-centre/saved`). `GET /api/match-centre/summary` is the
  page's answer: Madrid's last result with its scorers where the feed names every goal, and the
  next match. A table's answer says Madrid's place in the declared order (points, goal
  difference, goals scored), in the past tense where results stop early. Public replies carry
  `Vercel-CDN-Cache-Control` with stale-while-revalidate, never on a reply with a warning and
  never when the private feed is mounted.
- *Players, this season* (F1, F20). La Liga is not offered: OpenLigaDB has no current `la1`
  season, so `goal_scout.LEAGUES` is the Champions League (Real Madrid, read from OpenLigaDB
  without the OpenFootball check), the Premier League and the Bundesliga, and
  `/api/match-centre/goal-scout/es` and `/la1` are 404s that say why. The first view
  (`GET /api/match-centre/goal-scout`) is Madrid's next opponent where the feed carries its
  competition, else Madrid in the Champions League, with one line saying which; in a league the
  preferred club is Madrid's next, else last, Champions League opponent from it, else the first
  club by name. The group of matches against a club in places 1 to 6 is keyed `places_1_6`
  (`top` was a banned token as a served value, R3; old links still work). A scorer listed under
  two names is joined only by a declared rule (`merge_scorers`); a group with no match is not
  offered; the unclassified count is said beside the split. The page opens on a "Real Madrid
  scorers" card (`GET /api/studio/scorers`, Wikipedia's counts, by goals then name). Cut: the
  teammate side-by-side comparison, the "Opponent strength" control and La Liga in the explorer.
- *Lineup* (F9, F12, F15). The server proposes the default XI by a declared key (most 2026/27
  appearances in each position), stated on the board; within a position a player stands where
  the first position of his Wikipedia infobox puts him (side, and attacking or defensive for a
  midfielder), else by shirt number, and the key line says which rule applied. The lineup and
  formation are in the address (copy-link, a toast, a broken-link notice;
  `GET /api/studio/lineup` answers a link with its sentence, 422 with a plain refusal), and the
  local save is a convenience. Madrid's next fixture comes from the Matches page's schedule
  (`GET /api/studio/next`). An archive sample is labelled as the 2017/18 match it is (its
  competition and date) and sits in a closed "Archive: where he played in 2017/18"; the drawn
  role area says it is drawn, not measured. A bench player is placed by tapping him, then the
  position he takes. The page loads one page-layer sheet, `web/lineup.css`.
- *Player profiles* (F6). The player's name is the H1 and his facts line sits under it; the
  percentile is each measure's headline; the view and the player are in the address (back,
  forward and a shared link open the same screen); Explore rows and scatter dots open their
  player; an unknown player says so under the H1 and offers a profile. "View provenance" and
  the evidence detail are one closed "About these numbers". List and comparison marks are
  plain (`plain-mark`), so gold stays the selected player's.
- *Match reports* (F7 for the archive, F18). The H1 names the match, the sentence restates the
  recorded result and the scorers read from the goal events, in the order scored, and only where
  they add up to the recorded score; lineups and key moments come first, the measures a reader
  sees first are plain counts in the server's words, and the rest sits under "More measures". A
  link to Check against targets is served only for a match with a prepared scenario; the silent
  fallback to the prepared XI scenarios is gone. A link to a match the archive does not hold
  opens the season's last match and says so. A Madrid league match of 2017/18 on the Matches
  page links to its archive report where the app serves it.
- *Check against targets* (the XI page). The H1 is the question ("Can an XI meet your
  targets?"), the sentence says how many measured targets the XI meets, and "No XI meets all of
  them" only where the lab proves it. The choices are "Before the match", "Formation" and "Aim"
  ("Meet every target", "Get as close as possible to every target"); the XI is drawn on a dark
  portrait pitch as on Lineup; the targets are listed in plain words with "Set targets" closed
  under them. The research tools (other XIs, the hard-limit question, how often each player is
  picked, the ranges, the frontier, the risk rule) are closed disclosures under "Advanced", each
  with one line saying what it does; the clash panel stays an open section, shown only when the
  solve is infeasible, and says "a set of your choices that cannot all hold together", not the
  smallest (the conflict method certifies a minimal set). The declarations are in the address.
- *Squad depth and Signings* (F13, F14). Squad depth answers which positions are thinnest,
  draws them on the pitch, and gives every recruitable position a "Find cover" link to Signings
  that carries the scenario, formation, departures, targets (`target=requirement:SOURCE[:value]`),
  the experimental opt-in and the slot in the address (`planning_answers.handoff_query`);
  Signings reads the link, solves on arrival and keeps nothing in browser storage. Its list is
  one server reply in the order of one declared factual key (minutes, age or name; ties by
  player id), with the sentence that says which key is in force; changing the key asks the
  server. The outcome of a re-solve is a sentence in the candidate's row, never a place in the
  list: no outcome band and no grouping by outcome (ADR-0023). The pool is "eligible" at a
  position, never said to "play" it, because the data records a broad position only. The
  per-row break-even strips, the row fill and the full targets editor are gone from the list;
  one candidate's break-even carry-over fraction is under "Advanced: how much of his output
  must carry over" in his panel, and targets arrive by the link, the menu or Squad depth's
  editor.
- *Shell additions.* A browser asking either app for an address it does not serve gets the
  site's own page (`galactico/match_centre/errors.py`, `web/missing.html`,
  `site_nav.not_found`: one heading, one sentence, the ways on; installed by
  `galactico/api/player_lab.py` and `galactico/match_centre/public.py`); an archive page asked of the
  hosted app says the archive runs only on a local install. API paths, static files and
  clients that do not ask for HTML keep the JSON 404. "About the numbers" gains "This season's
  results, tables and goals" (`galactico/match_centre/methods.py`) on both apps. Matches and
  Table credit OpenLigaDB beside OpenFootball, and Players credits Wikipedia.
  `web/components.css` documents the page-header slot order (`.page-scope`, H1, `.page-answer`,
  `.page-actions` with at most one primary, `.page-controls`), adds the scrolling strip with
  edge fades (`.ui-strip`), raises `.ui-btn` to 44 px at 640 px and below, and makes the
  wordmark a 44 px target on a phone. `web/tokens.css` adds `--kit-keeper`. Each page has its
  own sheet in `@layer page`: `matches.css`, `goals.css`, `lineup.css`, `player-lab.css`,
  `match-lab.css`, `xi.css`, `planning-pages.css`. `web/match-centre.css`, `goal-scout.css`,
  `studio.css` and `studio-shell.css` are deleted, and no page loads them.
- *A scheduled upstream probe* (F11). Every test stubs the current-season upstreams.
  `scripts/upstream_smoke.py` asks each real source once through the project's own feed code and
  reports its status, row count, latest result date and, for the two fill leagues, how many
  matches the club matching confirmed; a failed or empty upstream fails it, a late one is
  reported (and fails only with `--max-age`). `.github/workflows/upstream-smoke.yml` runs it
  once a day and on demand, apart from the test job: a source being down is not a broken
  commit. The CI lint step and `make lint` also lint `scripts/`, and `make e2e` runs
  `e2e/xi-extensions.spec.js` as CI does.

**The R13 and ADR-0011 override (in the form of W8).** This change overrides R13, and ADR-0011
for `web/index.html`, for exactly these edits, and for nothing else of the pages' behaviour.
The frozen lab APIs (`/api/players*`, `/api/compare`, `/api/explore/*`, `/api/scatter`,
`/api/matches*`, `/api/xi/*`, the runtime, squad and transfer routes) return the same bytes;
the frozen files (`optimization/historical.py`, `xi/domain.py`, `xi/solver.py`,
`xi/tradeoffs.py`, `models/xt/grid.py`, `squad/kernel.py`) are untouched. Each override names
the pin, old → new, and why.

- *Pages.* The markup, copy, scripts and sheets of every page file (`match-centre.html`,
  `leagues.html`, `scouting.html`, `studio.html`, `index.html`, `match.html`, `xi.html`,
  `squad.html`, `transfer.html`), with the scripts they load (`match-centre.js`, `leagues.js`,
  `scouting.js`, `goal-scout.js`, `goal-links.js`, `studio.js`, `studio-formation.js`,
  `planning.js`, `xi-extensions.js`), rewritten to the template above. The ADR-0011 freeze is
  lifted for exactly `index.html`'s markup, copy and the re-pins below; `index.html` still
  defines `strip`, `geoBar`, `quantileDots`, `showPlayer`, `META`, `CONSTRUCTS`, `loadExplore`,
  `runCompare`, `cmpA` and `cmpB` and writes `#profile`, `#why`, `#why-credit`, `#explore-body`
  and `#cmp`; `geoBar` gains a third argument for the mark class (default `selected-mark`, so
  the profile is unchanged). `match.html` still defines `selectedPlayer`, `renderPlayers`,
  `match` and `metricRows`, and its rows still show the status tokens.
- *`tests/test_xi_extensions_render.py`.* `SHIPPED_XI_HTML` re-pinned twice under this ADR, from
  `4d9cd94b…` to `18f108a2…` (answer first: the question H1, the server's sentence, the three
  choices in the glossary's words, the XI beside "Your targets", the research tools under
  "Advanced", the record in "About these numbers", the menu from `/api/answers/xi/scenarios`,
  the declarations in the address) and from `18f108a2…` to `9200a696…` (the review fixes: the
  portrait pitch with 44 px places, the first outfield player selected on arrival, a target's
  field at three significant figures with the exact target sent unless edited, `data-exact`,
  the aim as two radios on a narrow phone, "Technical record (JSON)"). The five additive edits
  are unchanged. The frame test: "Re-solve the main XI first." (four times) → "Waiting for the
  XI above." (four times), the ranges, frontier and risk panels are closed `<details>` with a
  title and one line, the lead says "Where an answer holds other targets than the XI above, it
  says so.", and the opt-in reads "Explain the clash, with the two experimental channel targets
  the XI above used". New: the clash line claims a minimal set, never the smallest, and the
  kit's copy holds no "EXPERIMENTAL". Why: the template and the glossary; the conflict method
  certifies minimality, not the smallest count.
- *`tests/test_planning_render.py`.* The Transfer lede "The list is grouped first by the outcome
  of the re-solve, in a fixed sequence; inside a group it is in the order of a key you choose."
  → the script uses `order.statement` and `outcome_sentence`, contains no `.sort(` and no
  `GP.ordered(`, and "grouped first by the outcome" appears nowhere. Why: F14 and ADR-0023;
  grouping by outcome put the candidates who close the gap first, a shortlist ordered by
  modelled change. `squad.html`'s list of the labels it assembles keeps its count of 7 with the
  glossary's words: "Below the gate:" → "Under 900 minutes:", "Excluded by you:" → "Left out
  by you:", "Raises the least declared shortfall when used here:" → "Widens the gap to your
  targets here:", "Available here and at no other slot:" → "Can play only here:", "No
  measurement this slot needs:" → "Missing a measurement this position needs:", "Declared for
  other slots only:" → "Declared for other positions only:", "Admitted by position, no
  eligibility rule:" → "Listed position only, no declared role:"; in the player panel "Why he
  is in no solve" → "Why he is in no count", "Recorded on the declared requirements" → "His
  recorded rates", "Absence stress" → "When he is missing", "nominal minutes" → "minutes",
  "shortfalls in units of" → "gaps in units of".
- *`tests/test_web_render.py`.* "WITHHELD · OUTSIDE DECLARED CONTEXT" → "Withheld"; "INSUFFICIENT
  SIGNAL" → "Not enough minutes to judge"; "estimator signal: limited" → "Reliability: limited";
  "This estimator needs 1,800 minutes" → "This measure needs 1,800 minutes"; "Minutes 1,340",
  read from `#profile`, → "1,340 minutes", read from the header's `#player-facts`; the
  comparison's "Observed location" → "Where their passes start". The percentile sentence, the
  status line, the share lines and the comparison captions are the server's, and the page
  composes none when they are missing. The count per measure is unchanged.
- *`tests/test_match_lab.py`.* New pins only: the page prints the server's title, sentence,
  scoreboard and XI link and writes none of its own; the sections read in match order with
  "About these numbers" last; the script writes no result word; the first table holds the plain
  counts under the server's names.
- *`tests/test_site_nav.py`.* "About the numbers": hosted sections `["sources"]` →
  `["this-season", "sources"]`; hosted answer "Where every number comes from." → "How this
  season's results, tables and goals are gathered and where every number comes from."; local
  sections gain "this-season" before "sources" and the local answer gains the clause. New: both
  apps answer a missing page with the designed 404 and keep the JSON 404 for an API path, a
  static file or a client that does not ask for HTML. Matches and Table credit `("openfootball",
  "openligadb")` (was `("openfootball",)`), Players adds "wikipedia", and OpenLigaDB's
  `used_for` "Goal reports, 2026/27" → "Champions League fixtures and results, missing
  Bundesliga and Premier League results, and goal reports, 2026/27".
- *`tests/test_web_shell.py` and `tests/test_design_tokens.py`.* Every `web/*.html` is a page of
  `PAGES` → `PAGES` plus `site_nav.MISSING`; `LEGACY_SHEETS` drops `match-centre.css`,
  `studio-shell.css`, `studio.css` and `goal-scout.css`, and a new test asserts each is gone and
  loaded by no page. The required sheets `{labs, match-centre, studio, index, squad}` →
  `{labs, matches, goals, lineup, index, squad}`. The SVG-text set no longer requires
  "xi.html <script>": the XI page labels its pitch in HTML (12 px floor, as every sheet). The
  colour, contrast, gold and 12 px rules apply to every new sheet unchanged.
- *`tests/test_goal_scout.py` and `tests/test_season_scouting.py`.* `/goal-scout/es` 503 → 404
  ("La Liga goals aren't in the free goal feed: OpenLigaDB has no current La Liga season."),
  and the unavailable-feed test asks for `en` with the plain detail "The free goal feed,
  OpenLigaDB, can't be reached right now."; `LEAGUES` `{es, en, de}` → `{ucl, en, de}`; the
  preferred club of `en` and `de` from fixed ids (Crystal Palace 2489, Bayern 40) → the declared
  rule above, stated in `opening`; the group key `top` → `places_1_6` in `goal_scout`,
  `scouting.opponent_groups`, `goal-scout.js` and the comparison select (`top` still accepted);
  an answer with no classified match drops the split clause ("…, all in matches not yet
  classified by the opponent's place." → "…"); a feed that names fewer goals than were scored
  says "the feed names the scorers of N of them"; the La Liga lead-in → "La Liga goals aren't in
  the free goal feed, so this shows Real Madrid in the Champions League."; server cache 6 h →
  1 h, and the CDN header `s-maxage=21600` → `1800` (900 for the first view). Additions to the
  reply (`code`, `leagues`, `club_name`, `club_list`, `answer`, `opening`, `bands`,
  `band_note`, `scorers`, `order`, `opponents`, `opponent`, `notes`, `classified`,
  `split_note`, `through`; per match `day_label`, `split_label`, `result`, `note`; per event
  `scorer`), an `opponent` query parameter, and `parse_matches` rows' `group`; every existing
  key is kept, `clubs` included. `scouting.opponent_groups` takes an optional `counts` (default
  unchanged). `/api/match-centre/scouting/madrid` adds the lines the page prints (`club`,
  `competition`, `line`, `note`, `stale`, `schedule`, `credits`). Why: F1, F20 and R3.
- *`tests/test_lineup_studio.py`.* A roster row `{id, name, number, group, nation, archive, apps,
  goals}` in parse order → the same plus `short`, in the declared order (GK, DF, MF, FW, then
  shirt number), and players in a proposal carry `position`, `side` and `depth`; `SAMPLES`
  4-tuples with "Deportivo v Villarreal" and "Lyon v Nice" → `Sample(match_id, player, match,
  competition, day)` with "Deportivo La Coruña v Villarreal" and "Olympique Lyonnais v Nice", as
  the public data names them, and the activity reply adds `competition` and `label`;
  `/api/studio/squad` from the roster only → the roster plus `season_label`, `order`, `key`,
  `rule`, `formations`, `default`, `sides`, `revised`, `revised_label` and `proposals` (per
  formation `xi`, `ties`, `answer`, `names`); the hand-picked `preferred` map of
  `web/studio-formation.js` → the server's proposal. Why: F9, F12, F15, R1 and R10.
- *`tests/test_match_centre.py`.* An autouse fixture answers OpenLigaDB with an empty season,
  so no test reaches an upstream; no assertion changed.
- *Current-season replies.* `/api/match-centre/fixtures`: `day` optional (the server picks the
  nearest day with fixtures); adds `code`, `through` and `order`; Champions League matches; the
  server's order. `/api/match-centre/leagues/{code}`: accepts `ucl`, `day` optional; adds `gd`,
  `answer`, `freshness`, `order`, `credits`, `madrid`, `stage`, `outcomes`, `club_answer`. A
  report key accepts `ucl-…` ids and adds `goals`, `goals_note`, `clubs`, `through`, `credits`
  and `archive`. `/api/match-centre` adds `competitions`. New routes: `/api/match-centre/summary`,
  `/api/match-centre/saved`, `/api/match-centre/goal-scout`, `/api/studio/scorers`,
  `/api/studio/lineup`, `/api/studio/next`. Every existing field is kept.
- *e2e specs.* `e2e/match-centre.spec.js` rewritten for the new Matches and Table: the report
  score "0 – 0" as page text → "0–0" in the scoreboard; "Recent form" a button → a heading (the
  private feed's sections are real tabs); the search box and "No fixtures match these filters on
  this date." → the competition filter and "No Premier League matches on this day."; the inline
  "2 fixtures through that date have no reported result" → the server's banner "Table after
  matchday N of M" and its note, which still counts them; the always-visible footer links
  "OpenFootball coverage · API-Football coverage" → "About these numbers" with the OpenFootball
  and OpenLigaDB credits (API-Football's only where its data appears). `e2e/players.spec.js`:
  `places_1_6`; the chips `['All opponents2', 'Places 1–61', 'Places 7–360', 'Not
  classified1']` → `['All opponents2', 'Places 1–61', 'Not classified1']`; the teammate test is
  removed with the comparison. `e2e/studio.spec.js` rewritten: the La Liga goal links, the
  `#match-prep` panel and the "Compare Mbappé with a teammate" and "Scout Example opponent"
  links are gone with the La Liga goal source; "Save lineup" → "Save on this device"; "Event
  heatmap" / "Role zone" → "Archive sample" / "Role area"; `#sample` "ST · Planned position" →
  "Drawn area for the ST role, not measured", and "<match> · <date>" → the server's archive
  label; a player without a sample has no map panel; a bench tap waits for a position; the
  default slot is the ST; `.slot` → `.ln-slot`. `e2e/smoke.spec.js`: the player's name
  `#profile .phead h2` → `#player-title` (the h1), his team `#profile` → `#player-facts`;
  "WITHHELD" → "Withheld"; "estimator signal: X" → "Reliability: X" (its title still equals
  `signal_note` word for word); `.pctsub` equal to player_lab's `percentile_note` → the server's
  `percentile_line` ("94th percentile among La Liga midfielders with 900+ minutes in 2017/18 (127
  players)"), the ordinal still checked against `round(percentile)`; "This estimator needs …
  before a point estimate is shown" → "This measure needs … before a number is shown", with
  "Not enough minutes to judge (under 1,800)"; `#cmp h2` "Observed location" → "Where their
  passes start", `#cmp .phead h2` → `#compare-title`; the second keeper's wait narrowed to
  `/api/compare?`. `e2e/labs.spec.js`: `#score-note` "NOT_IDENTIFIED" → "One-number match
  summary: not identified."; the XI H1 and sentence; the quick picks named in plain words
  ("Ronaldo, Benzema and Bale together", "Isco at the tip of a diamond"); "Not checked" for the
  lab's NOT_EVALUATED. `e2e/repairs.spec.js`: "Building match intelligence" → "Loading the
  match"; a picker option `date.slice(0,10) + ' · ' + label` ("2017-08-20 · Deportivo La
  Coruña - Real Madrid, 0 - 3") → the server's line ("Sun 20 Aug 2017 · Deportivo La Coruña
  0–3 Real Madrid"), with the date order checked; the coverage line is the server's sentence;
  "Find the XI again" and "Set targets". `e2e/alternatives.spec.js`, `e2e/tradeoff.spec.js` and
  `e2e/xi-extensions.spec.js`: each tool is opened from its closed disclosure; "Adjust
  requirement minima" → "Set targets", the solve button → "Find the XI again", a lock is
  "Locked in"; the requests on load add `GET /api/answers/xi/scenarios` and
  `POST /api/answers/xi`. `e2e/squad.spec.js`: `#eyebrow` the browser-built "team · season ·
  matches before" → the server's scope line; `#constraints button` ("EXCLUDE name ×") →
  `#departures` chips ("Without <name> ×"); `#presets` → the `#targets` select and a departures
  chip; the `#audit` button removed (any change runs the audit); "Apply the edited minima and
  re-audit before asking this." → "Apply the edited targets before asking this."; "Squad audit
  unavailable:" → "Squad depth unavailable:"; "Absence stress unavailable:" → "Absences
  unavailable:"; the address is the server's share link; the page's own season chip is gone.
  `e2e/transfer.spec.js` rewritten: the "Set the problem" (`#apply`) and "Re-solve with each
  listed candidate" (`#search`) buttons, the row fill (`#fill-status`, `#fill-stop`, the
  21-cell strips), the outcome bands and the client-side reorder (the old pins at
  `transfer.spec.js:88-360`) → an answer on arrival, rows equal to the server's in the server's
  order, one request per order change, and the gold, late-reply, superseded-answer, 429,
  not-certified, no-XI-world, comma-locale and 320 px checks re-expressed on the new markup.
  `e2e/shell.spec.js` gains the 404 page (on both apps), the 44 px wordmark and the strip
  fades. `e2e/screenshots.spec.js` captures the new pages: Squad depth and Signings open from
  the hand-off link (`?exclude=3322&target=progression:EXPLICIT:4`, and `4.2` with `slot=st`)
  and are captured at the top, answer first. The tracked images `01`, `03`, `04`, `06`, `07`,
  `09`, `10`, `11`, `12`, `17` and `18` under `docs/screenshots/` were regenerated on the local
  corpus and inspected (each shows Pappalardo/Wyscout data only); `08-why.png`, which shows the
  labels formed from StatsBomb data, stays as committed.

No assertion about a number, an order, gold, the copy guard, overflow or a credit was weakened;
each was re-expressed on the new markup or made stronger.

**Evidence.** The UX audit and the redesign brief. `tests/test_player_answers.py`,
`test_xi_answers.py` and `test_planning_answers.py`: every branch of every sentence over
synthetic replies, the routes end to end, and the real archive where it is built; each passes
the copy guard, every number in it is one the reply carries, a list of candidates is in the
order of the declared key and never of a modelled change, and the hand-off link reads back in
the browser kit as the problem it was written from. `tests/test_matches_table.py`: the fill
never replaces a reported result, the freshness lines from the rows, every answer shape through
`scan_labels` with its numbers checked, no German Champions League name. The e2e suite on the
local corpus: answer before the primary visual and above the fold at 1440 px, the detail
closed, gold the selected subject only, no overflow at 390 and 320 px, 44 px targets, the
late-reply and superseded-reply checks, and the designed states.

**Alternatives rejected.** Keeping the lab layouts and adding a sentence on top (the controls
would still come first). Writing the sentences in the browser from the replies (R10). Ordering
Signings by the outcome of the re-solve, even within a declared key (ADR-0023). Keeping La Liga
in the goal explorer with an empty state (every link to it was a dead end, F1). Estimating a
missing La Liga result or scorer (R8). Precomputing an XI scenario for every match (F18's large
option; hiding the link is exact and small). Polling the board every minute on any day (F16).

**Open.** The brief lists `/player` first under Players; the review asked for the current-season
page first. That is a root decision and is unchanged here.

**Confidence.** High that every page leads with a server sentence that passes the copy guard and
carries only numbers its reply carries, that the frozen APIs and files are unchanged, and that
the order, gold, overflow and credit checks hold (the tests above). Medium on the Wikipedia
placement rule and on the Champions League knockout stages, which OpenLigaDB has not yet
published.

**Reversal.** A reader study showing that the answer sentence is read as a recommendation; a
source that carries current La Liga goals under a licence the site may use (La Liga then
returns to the explorer); a test showing a recorded rate carries over after a move (Signings
could then say more than eligibility).

**Since ADR-0035.** The open item above is resolved: every destination opens its current-season
page first where one exists, on both apps, so Players opens `/match-centre/scouting` before
`/player` (ADR-0035, D1). ADR-0035 is this decision's second pass: the third review's findings,
fixed in the same template, with the R13 overrides it names.

---

## ADR-0035 — Answer-first pages, second pass

**Problem.** ADR-0034 put every page answer first. The third review (an adversarial walk of
every page of both apps at 1440, 390 and 320 px, 27 November 2026) found that the answers were
there and the pages still made a reader work: the Players destination opened the 2017/18
archive on the local app although a current-season page exists; kick-off times were the
source's local time with no zone; one Real Madrid scorer could be named two ways on one page
("F. Valverde" from OpenLigaDB, "Federico Valverde" from the squad list); Signings, opened from
Squad depth's "Find cover" where the targets leave no gap, opened on a list with nothing to
close; measures were named three ways (the registry's "Progression", the chips', the map's);
research words ("HEURISTIC", "EXPERIMENTAL", certificates, ledgers) sat in the default view of
the archive pages; Goals by opponent printed split columns of zeros when no match was
classified; the Table dropped Pos on a phone; the XI page could open on the goalkeeper and
printed a target at sixteen digits; and Matches spent six chips and a repeating sentence on how
current each feed is, with a native US-format date field. The review's further findings are
H1–H36 (this season's pages), PL-, MR-, XI-, SQ-, TR- and AR- (the archive pages), and the
cross-cutting R1-, R3-, R7-, R8-, R10-, A11Y-, SPD-, COPY-, UI- and FN- items. R13 pins the
shipped pages' bytes and several shipped replies, and ADR-0011 freezes Player Lab; both give
way for exactly the edits below.

**Decision.** Ten root decisions, applied on both apps, and the review's findings fixed in the
template of ADR-0034. Every new string passes `scan_labels` (the hosted modules' tests run each
shape through it) or `runtime.finalize`; every number is one a reply carries (R8); every list
is in a declared, visible order (R1), and no shortlist is ordered by a modelled change
(ADR-0023).

- *D1, the current season first.* Every destination opens its current-season page first where
  one exists, on both apps: Players opens `/match-centre/scouting`, then `/player`
  (`site_nav.NAV`). ADR-0034's open item is resolved by this.
- *D2, kick-off as one instant.* `galactico/match_centre/kickoff.py` turns each source's
  published local time into UTC: OpenFootball's Premier League in UK time, its other leagues
  in Central European time, by the European summer-time rule written out in the module (no
  time-zone database on the hosted function); OpenLigaDB's own `matchDateTimeUTC`. Every
  fixture carries `kickoff_utc`; a Premier League result filled from OpenLigaDB is written in
  UK time. The pages show the reader's local time (`Site.kickoff`, with the weekday where the
  reader's date differs) and say once "Times in your time zone"; a time whose zone is unknown
  is shown as published, and the line says so. Server sentences keep their dates in
  Europe/Madrid.
- *D3, one name per player.* `galactico/match_centre/names.py` writes a Real Madrid scorer as
  the Wikipedia squad list writes him where the two names are the same once accents and case
  are set aside, or where the surname and first initial match one squad player and no other;
  a name that matches none, or more than one, stays as the feed gives it. It applies on the
  server to the summary answer, the match report's goals and the Goals explorer's events and
  scorers.
- *D4, Signings answers on arrival from Squad depth.* Where the hand-off's targets leave no gap
  at the position, Signings opens on the scenario Squad depth's answer named for that position
  (the absences there that leave no XI, with the existing exclusions), states it in the answer
  and shows each absence as a removable chip (`open_gap`); where no scenario makes a gap, one
  line says so, the pool is said once after it ("118 La Liga midfielders with 900 or more
  minutes are eligible at left central midfield.", not a second "none of them has a gap to
  close"), and the candidate panel still shows the XI with him. The list's order is unchanged:
  one declared factual key.
- *D5, plain measure names from one map.* `GET /api/answers/measures` serves the names, units,
  axis names and position words every Player profiles view prints: chips, compare rows, the
  Explore heading and rows, the map's legend ("Progression" reads "Ball progression"), and the
  list of the five on "About the numbers", where the registry's label, which the research notes
  use, follows the plain name ("Ball progression. “Progression” in the research notes.").
  Values are at the precision the shipped formatting uses, with units; raw decimals and
  intervals sit in a closed "How sure is this?".
- *D6, research words out of the default view.* Match reports' key moments in plain event
  names and the pass-linking rule in words (`network_rule`); Compare's captions; the XI page's
  footnotes and the "EXPERIMENTAL" labels; the Signings candidate panel (plain facts and the XI
  with him first). Method sentences, claims, certificates, ledgers and integer-model notes sit
  under a closed "Technical record: how this was worked out".
- *D7, Goals by opponent when nothing is classified.* When no match's opponent is classified,
  the split columns are hidden (one column, "Goals"), the server's line says why, and the page
  leads with the scorers.
- *D8, Pos on a phone.* The Table keeps its Pos column at every width; at 360 px and below
  W, D and L are hidden and Pts stays in view.
- *D9, the XI page and the slot names.* Check against targets opens on a field player, never
  the goalkeeper; a target's field shows the display precision (the exact target in
  `data-exact`, sent unless edited); LCM and RCM read "Left central midfield" and "Right central
  midfield" wherever a slot is named in words, from served labels (`xi_answers` `slot_labels`,
  Lineup's `ROLE_NAMES`; `xi/domain.py` stays frozen).
- *D10, freshness in one line.* Matches says how current the feeds are in one compact line,
  the stale leagues flagged, with the server's sentence; dates are in the house format, and the
  date field stays hidden, opened from a button, bounded by the season.

*This season's pages* (H1–H36). Matches: a day step waits for the board and the report, then
scrolls to the report and focuses it (H1); at 960 px and below the report comes before the
board (H2); long names wrap clear of the star (H3); each club's goals sit under its name on a
phone, and a form row takes two lines under 360 px (H5); days, the filter and the tabs are
history entries, restored on Back (H8, H9); a season no feed holds is a 404 with "The free
feeds have no fixtures for 2027/28 yet." and a designed state with "Back to today", and the
board's reply adds `first` and `last` (H10); focus is restored after a redraw and the day
buttons use `aria-disabled` (H19); the printed order line and a status line that reads out the
server's day summary (R1-1, A11Y-3); the form caption is the server's, with the true count
(R8-3). Table: capped at 52rem (H17); "Choose a date", the chosen date shown, "Latest table" to
clear it, and no date control in a club's schedule (H16); dates no longer wrap, a scheduled
fixture shows its kick-off or nothing, and the schedule stacks on a phone (H34); the shorter
column stays in view (H35); `GET /api/match-centre/standings` opens the Table on the
competition of Madrid's latest result with one sentence for both competitions (H36). Goals by
opponent: the answer follows the opponent filter and each group has its own tile labels and
line (H11); the page answer is the all-competitions scorer sentence and the Champions League
sentence sits in the explorer card (H12); "Credited to a player" only where it differs from
Goals (H14); the credit links to www.openligadb.de (H15); the squad and La Liga cards sit beside
the explorer from 1100 px (H17); the saved-match, per-scorer and goal-side lines and the
archive sample's counts are the server's (R10-1). Lineup: a formation change on the proposal
shows the server's proposal for it, and an edited lineup is reshaped from the formation it was
edited in, by each player's own position, whatever shapes were tried on the way (H6); new 3-5-2
coordinates, every slot inside the pitch (H7); the goalkeeper's shirt is teal, since gold is
the selected subject's (H18); a link without a formation means 4-3-3, and a link with only a
formation opens its proposal (H20, FN-1); the sentence names moved players (H21); "Analyst
tools" is a server slot filled only on the local app, so the hosted page carries no import
(H28); every disclosure fits a 320 px screen (UI-1).

*The shell.* Every page has a meta description and Open Graph tags, and a `?xi=` or `?match=`
link uses the server's sentence (H22); the 404 page offers the navigation the app serves, the
first as the primary action (H23); server strings use curly apostrophes and en dashes (H24); a
non-breaking space joins an initial to its surname (H26); `Site.season` sets the header chip
when a page shows another season (H27); the competition switcher is one tab strip on Matches,
Table and Goals, one "Copy link" sits in the page actions of every page that keeps its view in
the address, and there is one date control (H29); the phone tab bar reads "Squad" (the link
keeps its full name) and the sub-navigation is one line that scrolls sideways (H30). Under
`/static` both apps serve no page template (`galactico/match_centre/assets.Assets`, mounted by
`public.py` and, in this change, `galactico/api/player_lab.py`), and the hosted app serves only
the files its own pages load (`assets.HOSTED`; H32, R7-1). `vercel.json` `includeFiles` ships
the hosted package, the hosted pages' templates and exactly `assets.HOSTED`, so no archive page,
archive script or the StatsBomb logo is in the hosted bundle (R7-1). Concurrent fetches and one
shared OpenLigaDB download per season (SPD-4).

*Player profiles* (D5, PL-1 to PL-6, R8-4, R8-5, R8-7, R3-2, A11Y-2, A11Y-4, A11Y-5). The player
opened is appended under Explore's forty, gold, where the rows served do not hold him (PL-1);
Find a player lists players under the minutes floor, greyed, with their minutes
(`GET /api/answers/players/under-floor`, by name; PL-2); a reliability r is printed at the
fewest places that keep it on its grade's side of the threshold, so 0.699 never reads "0.70"
(PL-3); the "Why only five?" view is drawn from `GET /api/answers/why`, its counts the
registry's, its replication verdicts in allowed words and its note links named by the note,
never by a title that holds a copy-guard word (PL-4, R3-2, R8-5); every channel of the bar is
named, in a row under it (A11Y-4); a goalkeeper's reason is said in plain words
(`zones_withheld_line`, `location_note`, R8-7); Explore's order note is served (`order_note`)
and names no player as first (R1).

*Match reports* (MR-1 to MR-5, R8-2, R3-1, A11Y-1, SPD-2, D6). The result is said winner's score
first ("lost 1–0 at home", MR-5); the pass-linking rule is served in words (`network_rule`);
the page went from 146 keyboard stops to 62 (A11Y-1); a background warm-up loads the corpus
after start-up, skipped under pytest (SPD-2).

*Check against targets* (XI-1 to XI-8, SPD-1, D9, R3-3, R10-2). The main solve asks for no
resampled season and "How often each player is picked" asks `POST /api/answers/xi/frequency`
only when opened (XI-1); solves are cached per declarations and snapshot (XI-2, SPD-1); the
preset reads "Isco in a 4-3-1-2 diamond" and the answer says where he was placed, since a lock
keeps a player in the XI, not at one place (XI-3); a second stage finds the equally close XI
with the fewest changes, so leaving Ronaldo out changes one player (XI-4); an infeasible "Meet
every target" names the target no XI reaches and the most any XI reaches, badged "No XI reaches
this", with the clash panel under the pitch (XI-5); the channel opt-in is ticked on arrival and
the frontier offers plain names (XI-6); the research answers under Advanced keep their method,
claims, certificates and ledgers under "Technical record: how this was worked out" (XI-7); one
precision per target (XI-8); the wait shows its seconds and a Cancel; the technical records
leave out the provenance and tier keys (R3-3); the other XIs' claim is one fixed sentence with
no count worked out in the page (R10-2).

*Squad depth and Signings* (SQ-1 to SQ-5, R8-6, R8-1, COPY-1, A11Y-6, D4, D6, TR-1 to TR-3,
SPD-3). With no target stated the answer names the starting target ("the club's median XI"),
never "every target you set" (R8-6); a candidate is "added to the squad with the rates he
recorded at his club", and "placed at X it widens by N" only where his forced inclusion changes
the gap (R8-1); a player with no declared role reads "Listed position only, no declared role:"
(SQ-2); the editor's field shows two places with the exact value in `data-exact` (SQ-4); the
Squad pitch is one keyboard stop (A11Y-6); the candidate and "Show all" are in the address and
restored on reload (TR-1); a lane filter lists the players at least half of whose completed
passes started in that lane, a filter and never an order (TR-2); the default La Liga pool warms
at start-up (SPD-3).

*Across the archive* (AR-1 to AR-3). The XI player panel links his season profile (AR-1); no
target under 44 px at 390 or 320 px (AR-2); a reader's change on an archive page is a history
entry (AR-3).

*Interface feedback is not football copy (R10).* The Lineup board narrates what a reader just
did, in the browser: "X replaces Y.", "Now choose the position X takes.", the picked and bench
hints, "Imported N actions for <name>." and "N actions in your file". Matches' order line ends
with "Times in your time zone." or "Times as each source publishes them.", and the Table's date
button reads "Table after <date>". These are interface feedback about the page itself, not
sentences about football, and stay in the browser; every sentence about a match, a player, a
table or a lineup is the server's.

**The R13 and ADR-0011 override (in the form of W8).** This change overrides R13, and ADR-0011
for `web/index.html`, for exactly these edits, and for nothing else of the pages' behaviour.
The frozen lab APIs (`/api/players*`, `/api/compare`, `/api/explore/*`, `/api/scatter`,
`/api/matches*`, `/api/xi/*`, the runtime, squad and transfer routes) return the same bytes;
the frozen files (`optimization/historical.py`, `xi/domain.py`, `xi/solver.py`,
`xi/tradeoffs.py`, `models/xt/grid.py`, `squad/kernel.py`) are untouched. Each override names
the pin, old → new, and why.

- *Pages.* The markup, copy, scripts and sheets of every page file and the scripts they load
  (`match-centre.html`/`.js`, `matches.css`, `leagues.html`/`.js`, `scouting.html`/`.js`,
  `goal-scout.js`, `goals.css`, `studio.html`/`.js`, `studio-formation.js`, `lineup.css`,
  `about.html`, `index.html`, `player-lab.css`, `match.html`, `match-lab.css`, `xi.html`,
  `xi.css`, `xi-extensions.js`, `squad.html`, `transfer.html`, `planning.js`,
  `planning-pages.css`), with `components.css` (`.page-copy`, the short tab label, the
  sub-navigation strip), `site.js` (`Site.season`, `toast`, `copyLink`, `kickoff`) and the
  measure list `galactico/api/about.py` writes for "About the numbers", per D1–D10
  and the findings above. `web/about.html`'s own `<meta name="description">` is removed: the
  shell writes one description per page, with Open Graph tags (H22). `index.html` still defines
  every name ADR-0034 lists and writes the same element ids.
- *`web/tokens.css`.* `--kit-keeper` `var(--c-amber-300)` → `var(--c-teal-300)`, a new primitive
  `#6fd0d6`. Why: H18; gold is reserved for the selected subject.
- *`tests/test_xi_extensions_render.py`.* `SHIPPED_XI_HTML` re-pinned under this ADR from
  `9200a696…` to `240e1e5e2b9b…` (through two intermediate pins of this round, `ba4d28e1…` and
  `34b54247…`), for XI-1, XI-2, SPD-1, XI-3 to XI-7, R1-2, R3-3, R10-2, AR-1 and AR-3 as above;
  the old pin and its reasons are in the constant's docstring. The five additive edits, every
  id and event and the gold rule are kept. The frame and kit: "Explain the clash, with the two
  experimental channel targets the XI above used" → "Explain the clash"; the opt-in "Also check
  the two wide-channel targets (experimental)" → "Also check the two channel targets, as the XI
  above does", and no "experimental)" in the kit's copy. Why: D6, XI-6.
- *`tests/test_planning_render.py`.* The editor field's pin gains `data-exact="8.25"
  data-shown="8.25"` (SQ-4), and its `aria-label` "Explicit minimum:" → "Your number:" (D6); the
  printed record equals the reply less each `tier` key, and holds no `"tier"` (R3-3); the lines
  under a slot that the page lists go from 7 to 8 ("Goalkeepers count whatever their minutes:",
  SQ-4).
- *`tests/test_served_credit.py`.* The "Why only five?" view is drawn from `/api/answers/why`:
  the note links "Research note: the second-provider test" and "Research note E-01" (were the
  note titles, which hold "fit"); "external replication:" → "Second data provider:";
  "Progression" → "Ball progression", "Metronome fit" → "Metronome (research name)"; the view
  passes `scan_labels`. Why: PL-4, R3-2, R8-5.
- *`tests/test_player_answers.py`.* A goalkeeper's answer "No measure is shown for K. Navas:
  defined for outfield players; this player is recorded as GK." → "These measures cover
  outfield players; K. Navas is a goalkeeper.", each measure's line in the same words, and a
  pair with a goalkeeper "First and Keeper cannot be compared on these measures: withheld for
  Keeper. Defined …" → "Keeper is a goalkeeper; these measures cover outfield players." (R8-7);
  Explore "…highest first; Marcelo is first, at 0.63." → "…highest first. One measure of one
  season: not an order of merit." (R1); a match "lost 0–1 at home to Real Betis" → "lost 1–0 at
  home", and over the real archive the scoreline check "ours–theirs" → the winner's score first
  together with the result word ("won", "lost", "drew"), so the direction is still checked
  (MR-5); the reliability r at the fewest places that keep it on its grade's side (PL-3). The
  compare row pin keeps its three keys and gains `name` and `detail` (D5). New fields:
  `zones_withheld_line`, `location_note`, `order_note`, `network_rule`.
- *`tests/test_planning_answers.py`.* With no target stated, "At least one XI meets every target
  you set." → "At least one XI meets the starting target (the club's median XI)." and "already
  meet every target you set" → "already meet the starting target (the club's median XI)" (R8-6);
  Signings "placed there with the rates each recorded at his club" → "each added to the squad
  with the rates he recorded at his club", and rows "Placed at right back, …" → "Added to the
  squad, …", with "placed at X it widens by N" where `forced_inclusion_change` > 0 (R8-1); "Listed
  position only, no declared role: …" (SQ-2). New: D4's arrival on a position where nothing makes
  a gap is the server's one line, then the pool once ("… are eligible at right back."), and an
  opened gap keeps the full sentence after its line.
- *`tests/test_xi_answers.py`.* The preset "Isco at the tip of a diamond" → "Isco in a 4-3-1-2
  diamond" (XI-3); an infeasible "Meet every target" answer equal to "…no XI from the N players
  in the pool meets every target." → starts with it and appends the unreachable target and the
  most any XI reaches (XI-5); the changes count of the lab's XI → of the equally close XI with
  the fewest changes, never more than the lab's (XI-4); the page's request
  `api('/api/answers/xi',input)` → `api('/api/answers/xi',input,signal)` (the Cancel).
- *`tests/test_site_nav.py`.* Players hrefs `("/player", "/match-centre/scouting")` →
  `("/match-centre/scouting", "/player")`, and the full app's Players link `/player` →
  `/match-centre/scouting` (D1); the 404 page's ways on, hosted `[/match-centre,
  /match-centre/leagues, /lineup]` → the navigation the app serves (adds
  `/match-centre/scouting`; the local app adds `/squad`), one primary (H23); "That page isn't
  here", "The 2017/18 archive isn't on this site" and the About answer's "this season's" now
  use ’ (H24); the sub-navigation strip gains `ui-strip`. New: "About the numbers" lists the
  five measures by their plain names, the registry's label after each that differs (D5); page
  descriptions and Open Graph
  tags (H22), the hosted `/static` allowlist, no page template under `/static` on the local app,
  the hosted bundle (`vercel.json`) ships what the hosted app reads and no archive file (H32,
  R7-1), and the label markup `<span class="site-nav-label"[ data-short="Squad"]>` (H30).
- *`tests/test_matches_table.py`.* The scorer clause "K. Forward" → "K. Forward" with a
  non-breaking space (H26); `/api/match-centre/saved` adds `missing_note` (R10-1); the
  goals-note, lag and unavailable sentences and "The free La Liga feed doesn’t name scorers."
  use ’ (H24). The OpenLigaDB stub's `matchDateTimeUTC`, always `T20:00:00Z` whatever its German
  time, is now the real Central European instant: test data, not an assertion (D2 reads UTC
  first).
- *`tests/test_goal_scout.py`.* `test_an_opponent_narrows_the_counts_and_the_matches_but_not_the_answer`
  → `…_the_matches_and_the_answer`: `narrow["answer"] == whole["answer"]` → "Against Club Seven,
  Real Madrid CF have scored 2 goals in 1 Champions League match; Jude Bellingham and Kylian
  Mbappé scored 1 each." (H11); the league `<option value>` list → the served tab buttons (H29);
  the feed-down, "La Liga goals aren’t…" and opening lines use ’ (H24).
- *`tests/test_lineup_studio.py`.* "…with 2 of them in other places." → "…in other places:
  Name25 plays LW and Name7 RW." (H21); the next card's `when` "Sun 29 Nov · 21:00" → "Sun 29
  Nov", with `kickoff` and `kickoff_utc` (D2); the Analyst tools disclosure leaves `studio.html`
  for a server slot filled only on the local app, and the page order no longer lists `tools`
  (H28); the 3-5-2 slots LWB (12,43)→(11,52), LCM (32,39)→(33,35), DM (50,54)→(50,55), RCM
  (68,39)→(67,35), RWB (88,43)→(89,52), LCB (25,71)→(25,72), CB (50,73)→(50,74), RCB
  (75,71)→(75,72), the proposals unchanged (H7); "Drawn area for the ST role" → "…for the
  striker role" (D9); the refusals use ’ (H24).
- *`tests/test_season_scouting.py`.* "Real Madrid CF's", "Real Madrid's midfielders" and
  "OpenFootball's La Liga file can't" use ’ (H24). `test_match_centre.py`, `test_season_scouting.py`
  and `test_lineup_studio.py` gain an autouse fixture that answers the squad list with no
  names, so no test reaches Wikipedia; no assertion changed.
- *`tests/test_web_render.py`.* The page harness gains `removeAttribute` and `querySelector`; no
  assertion changed.
- *Shipped replies* (every existing key kept). Fixtures add `kickoff_utc` (D2) and `first`,
  `last`, `season`, `status` (H10, A11Y-3, H27); a season no feed holds 503 → 404 with "The free
  feeds have no fixtures for YYYY/YY[ yet]." on fixtures and leagues (H10); the fixture report
  adds `form_note` and `line` (R8-3, H22); Real Madrid's scorer names → the squad list's in the
  summary answer, the report's goals and the Goals events and scorers (D3); new
  `GET /api/match-centre/standings` (H36); Goals: the answer narrowed by the opponent, bands add
  `matches_label`, `goals_label` and `line`, scorers add `filter_line` and `empty_line`, events
  add `side_label`, and `provider_url` (H11, R10-1, H15); `/api/studio/next` `when` no longer
  holds the time, and adds `kickoff` and `kickoff_utc`; `/api/studio/lineup` takes `formation`
  and `xi` as optional (H20, FN-1); the studio formations' slots add `name` (D9), the activity
  reply adds `filters` (R10-1, H28), and `/api/studio/scorers` reads the squad list alone (same
  fields). New archive answer routes: `GET /api/answers/measures` (D5), `GET
  /api/answers/players/under-floor` (PL-2), `GET /api/answers/why` (PL-4) and `POST
  /api/answers/xi/frequency` (XI-1); the archive answers add the fields named above and the
  Signings request takes `lane` and `open_gap` (TR-2, D4).
- *Static files and the bundle.* The hosted `/static` serves `assets.HOSTED` only, and neither
  app serves a page template there (was every file of `web/` on both apps); `vercel.json`
  `includeFiles` `{…,web/**}` → the hosted pages' six templates and `assets.HOSTED` (R7-1, H32).
- *e2e specs*, each re-pin listed in its spec's header and re-expressed on the server's words,
  none deleted. `match-centre.spec.js`: the freshness chips → one line; the competition select →
  tabs; `filter=saved` survives a reload; the date control; the Table's landing standings.
  `players.spec.js`: the page answer is the squad's; the title, meta and tabs; a single "Goals"
  column; "Copy link". `studio.spec.js`: a formation change shows the proposal; `when` and
  `kickoff`; the sample counts and "Show"; the striker zone wording. `shell.spec.js`: the 404
  heading uses ’, and its ways on. `smoke.spec.js`: names from `/api/answers/measures`; the
  reliability check reads the server's sentence and checks both r figures; the goalkeeper
  reasons and location notes in plain words; the channel labels row; the opened player under
  the forty; the Why links from `/api/answers/why`. `labs.spec.js`: `#solver-status`
  `data-status` with the status line; the frequency on opening, by name; the Isco preset and
  where he was placed; "No XI reaches this". `repairs.spec.js`: 1.50 shown with `data-exact`
  1.5; the server's changes line. `alternatives.spec.js`: the served status words, the fixed
  claim, "Players replaced: N", measured rows only. `tradeoff.spec.js`: display precision with
  `data-exact`; served words; 1,000.00; "Not checked". `xi-extensions.spec.js`: the opt-in
  ticked on arrival, the unticked path still tested; `data-status`. `squad.spec.js`: the player
  panel from the server's view; nested records revealed; the D4 back link carries the opened
  exclusions. `transfer.spec.js`: the `lane` and `open_gap` request keys; the R8-1 and R8-6
  sentences; the attained text.
- *README images.* `docs/screenshots/` regenerated on the local corpus and inspected; an image is
  kept only where it shows Pappalardo/Wyscout data alone, and `08-why.png` stays as committed.

No assertion about a number, an order, gold, the copy guard, overflow or a credit was weakened;
each was re-expressed on the new markup or made stronger.

**Evidence.** The third review's findings and the root decisions D1–D10. The hosted tests
(`test_matches_table.py`, `test_goal_scout.py`, `test_lineup_studio.py`, `test_season_scouting.py`,
`test_match_centre.py`, `test_site_nav.py`): summer time and its change-over days in both zones,
UTC rows and filled rows in UK time; the board's `first` and `last`, its season and status line;
the 404 for a season no feed holds; the standings answer with its numbers checked against the
tables; the name rule (an ambiguous initial stays as the feed gives it, an own goal in each
direction, the explorer); the served words for groups, scorers and goal sides; the role names
and the 3-5-2 spacing; the moved-players clause; links with no formation or only one; every
page's description and card; the `/static` rules on both apps and the bundle; the nav order.
The archive tests (`test_player_answers.py`, `test_xi_answers.py`, `test_planning_answers.py`,
`test_planning_render.py`, `test_served_credit.py`, `test_xi_extensions_render.py`,
`test_web_render.py`): the Why view's copy guard and counts, the goalkeeper notes, the
reliability figure, one precision per target, the fewest-changes XI, the unreachable target,
the cache, the listed-position wording, the D4 scenario. The e2e suite on the local corpus at
1440, 390 and 320 px, light and dark: no horizontal overflow, no text under 12 px, no target
under 44 px on a phone, gold the selected subject only, and a copy-guard scan of twenty archive
states with every disclosure closed and opened.

**Alternatives rejected.** A time-zone database for D2 (the rule is two lines per zone, and the
hosted function would need `tzdata` it is not guaranteed to have). Showing the source's local
time with its zone named (a reader in another zone still converts). Merging scorer records
across feeds (D3 joins names, never goals). Opening Signings' candidate panel on the first row by
minutes when nothing makes a gap (it would put one candidate first). Rounding the XI kit's
ranges and frontier tables in the page (the kit's digit rule forbids it, and `/api/xi/*` is
frozen). Folding Matches' form tables behind a disclosure on a phone (kept open, per H2; see
Open). Removing `08-why.png` (kept as committed by root decision; see Open).

**Open.** Under Advanced, the XI ranges and frontier tables still print the lab's four-decimal
texts; a fix would add display texts to `galactico/api/xi_extensions.py` or an answers route
under its own ADR (XI-7, in part). A few of the lab's own sentences remain inside the opened
Advanced brief and absence answers (SQ-5), and Signings' closed "Advanced: resampled seasons"
still says "Left midfield" in its world statement (COPY-1). A combination of leagues other than
the default still builds its pool on first request, about 2 s (SPD-3). At 390 px the native
match select cuts the result letter of the served phone label (MR-5). On a phone the Matches
report (goals and two form tables) comes before the board, which then starts about 1,000 px
down. When the shared OpenLigaDB download serves a season from cache, its stale-snapshot warning
no longer reaches the Goals notes (the data stays dated by "Results through"). `08-why.png`
under `docs/screenshots/`, referenced by no document, shows the "Why only five?" view whose
labels are formed from StatsBomb data; it stays as committed by root decision, and the review's
R7-2 asks for it to be removed or regenerated with the StatsBomb credit.

**Confidence.** High that the nav opens the current season first on both apps, that every
kick-off with a known zone is one instant shown in the reader's zone, that a Madrid scorer has
one name on a page, that the frozen APIs and files are unchanged and that the order, gold,
overflow, copy-guard and credit checks hold (the tests above). Medium on the summer-time rule for
a fixture inside the hour of a change-over (tested at both edges), and on the name rule for a
squad that later holds two players with one surname and initial (both then keep the feed's
names, by the rule).

**Reversal.** A source that publishes kick-offs in UTC for every competition (D2's rule then goes
away); a reader study showing that the current season first hides the archive from the people
who look for it (D1); a squad list that stops matching the feed's names often enough that the
rule leaves most of them as the feed gives them (D3 then needs a declared alias table).
