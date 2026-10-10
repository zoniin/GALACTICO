# Validation

Protocols and results have different statuses. A protocol written before a run
does not make every subsequent development diagnostic preregistered. The records
below distinguish correctness, measurement validity and decision usefulness.

## Current release evidence

The Squad Lab and Transfer Lab build, with the repairs of two audits, passed **1,476
local Python tests** on 10 October (one more skips: the tag sidecar it needs is not
built) and **52 browser tests** plus the two screenshot captures. That run had the
five-league public corpus, the built Player Lab bundle and the local StatsBomb cache
present; without that cache one more test skips. Ruff and the licensing guard passed.
It lives on the `north-star` branch. GitHub Actions passed both jobs on `b7bc919`
(run [37944962165](https://github.com/zoniin/GALACTICO/actions/runs/37944962165))
and on `7899c76` (run [37953254713](https://github.com/zoniin/GALACTICO/actions/runs/37953254713)):
the data-free checks, and the browser job that now ingests all five leagues and runs
the suite with the corpus. The commits after `7899c76` had not been pushed when this
was written, so no run of them is cited here; the Actions page holds it.

What the new tests establish, and what they do not:

- **Exactness.** Each tool has an oracle that shares no code with it: exhaustive
  enumeration in exact Fractions over every assignment, absence set, need vector
  or carry-over grid value on seeded instances, with pinned tables on the Madrid
  snapshots for the kernel, absence stress and the role brief. The kernel returns
  the XI solver's integers on the baseline, all sixteen single removals in both
  templates and all 120 pairs of the shipped scenario. This is arithmetic. It
  says nothing about football.
- **Temporal integrity.** A snapshot built for a bare cutoff date is unchanged
  when later and same-day matches are poisoned, and is byte-equal to the frozen
  builder for both shipped Madrid scenarios.
- **The guards run.** The rating-key walker and the provider check run on every
  new 200 reply at the boundary, not only in tests; so does the copy guard, on
  every string value outside a provenance block. A reply read from the result
  store passes the same check. An error body passes none of it. The research
  firewall parses imports; preregistration order is read from git. See
  [M-06](docs/research/M-06-a-guard-that-never-runs.md).
- **The pages.** Browser tests compare what is drawn with what the server sent,
  hold replies to prove a stale one changes nothing, and check gold and 390 px
  overflow. Desktop and 390 px screenshots were read after every change. An
  independent reviewer used each page on the real corpus and found fourteen
  defects that the builders' own tests had passed, among them a deadline printed
  as a finding and a count never taken drawn as zero. Each fix is covered by a
  test; three of the Transfer page's assertions were not seen failing before the
  fix.
- **Not established.** That the declared minima describe a style, that a
  requirement sum relates to results, that provider-position eligibility says
  where anyone can play, or that a recorded rate repeats after a move. No
  experiment was run in this build: the five new protocols are
  [drafts](docs/research/north-star/README.md) and none is registered. Four are
  unreviewed; E-11 was reviewed and audited three times and found not ready.

**The final audit.** Before the branch was handed over, three reviewers that had
written none of it audited it read-only: every claim of the new documents against
code and data, the HTTP boundary attacked on the real corpus, and the two pages
read state by state against the constitution. They reported 36 findings: five
high, 15 medium and 16 low. The README described the break-even fraction
backwards. A cached request waited 21 seconds behind other clubs' builds, outside
any budget. Transfer Lab built its snapshot and candidate pool before its budget
started and outside the gate, so a request that took 8.5 seconds reported 0.032.
Squad Lab labelled a count with the wrong stage. Transfer Lab printed a signed
modelled change beside every name while these documents said nothing orders
players by merit. The code findings were repaired from failing tests. The README
sentence was corrected in a commit of documents only, and no test pins its
wording. The copy guard that the documents said ran on every response was moved
to the boundary. What the audit found and this branch did not change is listed in
[KNOWN_LIMITATIONS](KNOWN_LIMITATIONS.md). The commit message of `4faa22a` says
four findings were high and that all were repaired from failing tests; it cannot
be changed. The repairs were audited with the rest of the branch in the second
audit, below.

**Decisions delegated by the owner, 9 October.** Four findings that had been left
for the owner were decided and repaired, each from a failing test: the StatsBomb
credit and logo on published analysis, three provider postures, goalkeepers
carrying constructs defined for outfield players (ADR-0025), and tie handling in
the published rank correlations (ADR-0026, erratum
[M-07](docs/research/M-07-rank-ties.md)). The erratum recomputed the published ordering
figures of Stage 1, Stage 1B, Stage 1C and E-02 under both tie policies; E-01's two rank
correlations have no script and were not recomputed. On the public corpus that is 61 figures:
35 of Stage 1B, 20 in the Wyscout columns of Stage 1C, 5 of the Stage 1 grid
sensitivity and E-02's T3. 17 move, the largest by 0.0044, and no status, label or
verdict changes; the audit verdict was compared in 55 cells. The other half of
Stage 1C was recomputed the same way and is reported in M-07, which carries the
credit its figures need. On the way the erratum found a machine-readable table of
StatsBomb-side figures tracked in the repository since Stage 1C was published;
it is out of the tree.

**The second audit, 9 October.** A second read-only audit covered the branch up to
`f4d0410`, the first audit's repairs and the owner's four decisions included, in
five lenses: rank ties and licensing, the truth of the documents, goalkeepers and
declared contexts, the HTTP boundary, and the two planning pages. It reported 67
findings, each reproduced by a second reviewer: 6 high, 20 medium and 41 low by
the second reviewer's grading (5, 23 and 39 as filed). Some are one defect seen
through two lenses. The high ones: Match Lab served every registry construct for
goalkeepers; the reliability served on chance-creation rows was the curve of a
pool with goalkeepers in it; analysis formed from StatsBomb data was served, and
printed in documents, with no credit; and the credit sentence that denied it was
false. [ADR-0027](DECISIONS.md) records the rulings.

Six builders, each with its own files, repaired the code from those rulings, and
these documents were then written from the tree. What was found and left is in
[KNOWN_LIMITATIONS](KNOWN_LIMITATIONS.md) under "Found while repairing the second
audit and not repaired". The account's usage limit stopped five of the six
part-way, and they were relaunched on a half-repaired tree. For the work the
first attempt had left there, no test was seen failing before its fix. Each
builder instead ran those tests against the old behaviour, put back in memory or
taken from the last commit in a scratch copy, and saw them fail; each report says
which tests were seen failing first and which were shown to fail that way. The
repairs of the second audit have not themselves been audited. The one exception
is these documents. A second reader checked every changed sentence against the
tree and found seventeen false or unsupported, one of them a claim that nothing
had been computed across the two providers, which the E-11 draft's own
prior-exposure table contradicts. Each was replaced with the reader's sentence.
The sentences written after that reading were not read a second time: the test
counts and CI runs above, the wording about the merge, and a few lines the
reader had listed as stale.

Reviewed by agents only. No football analyst and no statistician outside the
project has looked at these pages or these protocols.

The preceding progression-under-hard-floors release passed **374 local Python
tests** and **13 Playwright tests** on 20 September. Ruff and the licensing guard
passed.
Independent exhaustive enumeration checks 36 randomized assignments plus exact
rounding boundaries, tightening-floor monotonicity, locks and missing measurements.
A fresh agent independently ran 37 core/oracle tests and found no remaining release
blocker. Real Madrid checks recover a lower attainable progression sum at tighter
side floors, then infeasibility; this validates accounting behavior, not football
quality. No E-08 model or utility coefficient is promoted.

The actual browser checks the response-owned XI, exact floor values, impossible
requests, and stale replies after both floor edits and locks. The main pitch stays
unchanged. Desktop and 390px screenshots were manually inspected; displayed
certificate values are rounded, with exact values retained in provenance. Review
repaired stale inherited certificates and JSON-overflow error handling. Numerical
rounding allowances are explicitly not statistical uncertainty. See the
[method and test contract](docs/research/XI-PROGRESSION-UNDER-FLOORS.md).

The preceding equivalent-XI release was verified with **308 local Python tests** and **12
Playwright tests** across all three labs. New independent brute-force cases check
both lexicographic objectives, pairwise personnel diversity, conditional exhaustion,
deadline/status honesty and isolation from bootstrap/tie analysis. API tests retain
locks, exclusions and unavailable dimensions. Real Madrid browser checks compare
the actual response rosters with the rendered ledger and discard delayed responses
after a lock changes. Desktop and 390px screenshots were manually inspected.

E-08 follow-through adds 33 synthetic history/selection/reporting checks. The local
run on 17 September passed **280 Python tests**, including full empty-cohort,
future-poisoning, fixed-fold selection, identity-link and same-subset comparator
checks. Independent pre-outcome code review passed; these prove implementation
properties, not the forecast claim.

Follow-through verification adds 27 opening-window/forecast tests (247 total locally)
and a Linux font-fallback overflow regression. GitHub Actions run
[34244854096](https://github.com/zoniin/GALACTICO/actions/runs/34244854096) passed
both core checks and actual historical browser tests after the mobile repair.

The final local verification run for this milestone passed 220 Python tests and
11 Playwright tests. Ruff and the licensing guard passed. Desktop/mobile product
screenshots were inspected, and fresh adversarial findings were repaired: shared
worlds and gates; substitution chronology; dismissal exposure; infeasible minima
controls; certified-only tie claims; and sensitivity lineage/policy preservation.
This is recorded run evidence, not a promise that future test counts stay fixed.

| Layer | Evidence | What it does not establish |
|---|---|---|
| Player Lab | Shared-match covariance/world-identity tests, complete API gate checks, actual browser interactions | Practical materiality from a nonzero difference; external human acceptance |
| Match Lab | Synthetic clocks, shots, network and value-accounting checks; real Madrid match rendering | Causal contribution, momentum or persistent ability in one match |
| XI correctness | Independent exhaustive oracle on tiny instances; eligibility, uniqueness, ties, locks and infeasibility cases | That the objective measures good football |
| Temporal integrity | Future and same-day data poisoning leaves historical inputs unchanged | Verified historical fitness or suspension availability |
| XI uncertainty | Joint match-world recomputation and necessary/possible membership across tied optima | A probability of being the best XI; risk-robust or optimism-corrected utility |
| Squad tools | Independent enumeration oracles; pinned Madrid tables; tests that a deadline or an undecided solve never becomes a value, a zero or a negative finding | That thin cover in the gated model is thin cover in the squad; any absence likelihood |
| Transfer tools | Oracle-tested forced-inclusion and break-even arithmetic; separate world namespaces per league; ordering-policy tests | That a rate recorded at one club repeats at another; comparability across leagues |
| Product | Playwright interactions and manually inspected desktop/mobile screenshots | Football usefulness from HTTP success alone |

Player Lab's implementation is frozen since ADR-0011, after the shared-world and
gate repairs ([M-04](docs/research/M-04-shared-match-worlds.md)), except the
corrections of ADR-0025 and ADR-0027 (October 2026); no independent human football
acceptance is claimed. Test counts belong to the executable run, not a roadmap.

### Executed research: nulls remain visible

- **Match-score audit:** Spain 9,722 and England 9,579 outfield player-matches.
  Accounting is exactly positive pass xT. Broad-role standardization correlates
  .988/.982 with it, so neither candidate ships as an overall rating. This is an
  incremental-meaning audit, not supervised performance validation
  ([E-05](docs/research/E-05-match-score.md)).
- **Selection development diagnostic:** 12 Madrid league fixtures from March
  2018; mean actual-starter overlap 6.00/11 for the requirement-model representative,
  **6.83/11 for prior minutes**, 5.00/11 for the previous league XI. Candidate
  gates limit maximum achievable overlap to 9.17/11. The engine loses to prior
  minutes. The window is not an external/preregistered test and the previous
  league XI is not necessarily the previous all-competition XI. Agreement measures
  resemblance to manager choices, not their correctness
  ([E-06](docs/research/E-06-lineup-requirements.md)).
- **Optimizer's curse:** a known-latent-value synthetic requirement model shows
  increasing reported-versus-true shortfall optimism as noise rises. Oracle
  shrinkage reduces, but does not eliminate, it. This is not a calibrated Madrid
  correction ([M-05](docs/research/M-05-optimizer-selection-bias.md)).

The current XI model is an explicit-requirement thinking aid. No team-outcome,
causal lineup superiority, role-transition value or external decision-utility
claim has passed a validation gate.

E-07's preregistered incremental-lineup forecast experiment is **INCONCLUSIVE**:
only 3 Spain development team observations survive the joint individual evidence
gates, below the fixed minimum of 50. The 41/32 eligible Spain/England holdout rows
also fall below their minima. No coefficients or fitted context-versus-lineup
comparison were evaluated. Unfitted comparator errors are descriptive only.
The gates were not relaxed; see [the result](experiments/preregistered/E-07-lineup-transport/analysis.md).

E-08 reached its gates with 272 Spain development rows and 216/174 evaluation rows
in Spain/England, but development tuning selected `context_only` over all finite
regularization candidates. **NOT_ESTABLISHED**: no incremental player-history signal.
The selected-minus-baseline [0, 0] interval is identical predictions, not absence of
player effects. Reused periods and nonexchangeable identity-link controls preclude
confirmatory/causal interpretation. See [E-08](experiments/preregistered/E-08-partial-history/analysis.md).

## Original staged validation agenda

The phases below preserve the original research agenda. They are not a claim
that every target is now available or every experiment has run. Any revised target,
coefficient or split needs a new protocol before a confirmatory experiment.

## Phase 0 — Reliability, as a gate

Split-half within season, Spearman-Brown corrected, at a stated minutes floor,
per axis. Enforced in code: `r >= 0.70` renders a number, `0.50 <= r < 0.70`
renders a band, below that renders "insufficient signal" and carries zero
optimiser weight. The table is published, including the rows that fail.

## Phase 1 — Walk-forward selection agreement

For each matchday, fit strictly on prior events, predict the XI, score exact-XI
accuracy and mean players-in-common out of eleven.

Baselines in ascending difficulty:

1. Random feasible XI
2. Top eleven by prior minutes
3. Top eleven by single rating
4. **The same XI as last match**

The prior expectation was that persistence would score eight or nine out of
eleven. That is not a result from this corpus: the current late-season league-only
diagnostic scores 5.00/11. Rotation and missing non-league fixtures matter. The
single-rating baseline also awaits an identified scalar; none is invented to fill
that row. Random-feasible and a full all-competition persistence baseline remain
unrun here.

If Galactico cannot beat persistence, the README says so and the tool is described
as a thinking aid.

## Phase 2 — The falsifiable claim

**Proposed, not implemented.** The original system-rating formulation below is
not the current requirement objective. Pappalardo has no supplied xG, and no
validated universal XI rating ships. A future association study must define an
available target and revised lineup representation before fitting it.

Compute system-level ratings for the XI that was **actually played**, then predict
that match's xG for and against with team, opponent and home random effects,
cross-validated by matchday.

Claim: engine system ratings beat both the sum of individual ratings and an
Elo-only model on out-of-sample error. If they lose, the role machinery is
decoration and that goes in the README.

Power, stated in advance: match xGD has a standard deviation just over one.
Detecting a 0.10 system-level effect needs ~3,700 team-matches and the corpus
supplies ~3,650, so that test sits exactly at the edge. A one-player swap is a
~0.05 effect needing four times as much data. It is out of reach and will not be
run underpowered.

## Phase 3 — Injuries and red cards

**Not run.** Forced absences are candidates for quasi-exogenous variation, not
automatically valid instruments. Injury risk, disciplinary behavior, opponent,
fixture congestion and selection can share causes with performance. The current
historical availability reconstruction does not establish those causes. Restrict
to verified cases and state identification assumptions before estimating effects.

## Phase 4 — The Bridge

**Not run.** The proposed paired sample was four complete women's league seasons
plus NWSL 2023. Reverify API-Football coverage and both providers' licensed uses
before collection; a historical free-window observation is not a durable data
contract. Per target axis, report: naive
baseline, bridge model, held-out error, rank correlation, calibration, interval,
failure modes. Where it fails, LIVE does not show the metric.

## Phase 5 — Transfer retrospect

Freeze the engine before each historical transfer window, compute predicted
marginal system improvement, and test whether it ranks successful fits above
failed ones better than market value does. Heavily confounded; the confounds are
reported in the output rather than in a footnote.

## Phase 6 — VISION

Against ground-truth tracking. Report calibration success rate, median and 90th
percentile position error, ID-switch rate, track completeness, team-classification
accuracy — and then the metrics that actually matter: error in estimated team
width, line height and compactness. A 1.2 m individual error may yield a 0.2 m
team-width error after aggregation. That is the claim, and it is measured rather
than assumed.

## What no experiment can do

You never observe the counterfactual XI. No backtest can demonstrate that the
engine's team would have outperformed the manager's, because only one was played.
Any wording suggesting otherwise is a bug.

