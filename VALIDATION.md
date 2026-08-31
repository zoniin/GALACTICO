# Validation

Pre-registered. Written before running, so a disappointing result cannot be
quietly reframed as a different experiment.

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

The fourth is the one this literature almost never reports, and it is brutal:
managers change one to three players a game, so persistence scores eight or nine
out of eleven. The only published external validation to calibrate against reached
35% exact and 60% near-miss agreement on *formation alone* across 760 matches.

If Galactico cannot beat persistence, the README says so and the tool is described
as a thinking aid.

## Phase 2 — The falsifiable claim

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

Forced absences are the only quasi-exogenous variation in lineup composition
available. The manager's hand is forced, so the change is far less confounded with
his private read on form. Restricted to absences with causes unrelated to
performance.

## Phase 4 — The Bridge

Calibrated on four complete women's league seasons, plus NWSL 2023 that sit in both StatsBomb open
data and API-Football's free 2022-2024 window. Per target axis, report: naive
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

