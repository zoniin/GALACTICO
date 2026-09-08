# Validation

Protocols and results have different statuses. A protocol written before a run
does not make every subsequent development diagnostic preregistered. The records
below distinguish correctness, measurement validity and decision usefulness.

## Current release evidence

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
| Product | Playwright interactions and manually inspected desktop/mobile screenshots | Football usefulness from HTTP success alone |

Player Lab's implementation is frozen after the shared-world and gate repairs
([M-04](docs/research/M-04-shared-match-worlds.md)); no independent human football
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

