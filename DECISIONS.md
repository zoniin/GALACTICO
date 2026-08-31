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
