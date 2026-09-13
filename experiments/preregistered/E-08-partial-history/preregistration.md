# E-08 — partially observed histories, aggregate forecasts only

Commit this plan before evaluating any E-08 forecast errors. E-07's overlapping
holdout comparator errors and coverage failure have already been seen. This is a
prospective follow-up analysis plan on **reused evaluation periods**, not an
untouched confirmatory study or independent replication. Freeze `config.json`;
record any implementation correction rather than changing rules after outcomes.

## Claim and unchanged boundaries

Do regularized histories of the ten actual outfield starters add opening-30-minute
positive completed-pass xT forecast information beyond team context, broad-position
composition and the amount of individual history available?

Use public Pappalardo Spain/England 2017/18 only. Reuse E-07's exact `[0,1800)` first-
half target, two-sided stable-opening quality exclusions, raw dismissal clocks,
strict prior-calendar-date histories and Spain xT surface fitted before November.
The surface is shared by every league, feature, outcome and placebo. E-07's
protocol defines those inherited measurements; fingerprint the reused code.
Quality conditioning uses events after kickoff: this is not a deployable forecast
for arbitrary fixtures. Actual lineups are observed, not counterfactually assigned.

Development remains Spain November–February; evaluation is Spain and England
March–season end. England histories can update but never fit or select models.
No coefficients, player estimates or requirements enter Player Lab or XI Lab.
Individual evidence gates remain unchanged in the products. This experiment
cannot certify sparse individuals, unseen XIs, tactical roles, or causal replacements.

## Aggregate cohort and missing information

Require ten identified outfield starters in a valid opening and at least five
prior valid openings for both own team and opponent. Require a finite prior league
reference for each starter's broad position. Do **not** require 900 prior minutes
or three individual openings for this aggregate experiment. These are different
cohort semantics, not relaxed individual measurement certification.

Historical opening observations enter history even if their own lineups fail
evaluation gates. Player histories use only the current team. A valid opening
with no recorded positive pass value is zero; an unseen player's individual mean
is unavailable. The latter gets an explicit reference prediction, never observed
zero performance. Provider broad positions are static metadata, not timestamped
tactical roles. Reject inconsistent broad labels within a player's input panel.

Full-match xT and nominal minutes cannot exclude a primary row. Report the old
operational comparator only on its common-available subset: every starter needs
positive finite prior nominal exposure and finite accounting. Report all other
comparators on that same subset too; never compare unequal-cohort errors as models.

## Regularized histories and identity-link stress test

Let n be prior valid current-team openings, m their mean and r the strictly prior
league appearance-weighted broad-position mean. For finite k define:

`D_k = sum_over_starters [ n/(n+k) * (m-r) ]`.

At n=0 the summand is exactly zero for all k, including k=0. For k=0 and n>0
the weight is one. The corresponding unfitted forecast is `role_sum + D_k`.
`context_only` has no individual-history column; it is an explicit boundary
candidate, not a rank-deficient all-zero column.

These are **regularized histories**, not posterior ability estimates or calibrated
uncertainty. With a freely fitted residual coefficient, uniform residual scaling
can be undone algebraically; relative evidence counts, not shrinkage scale alone,
distinguish candidates. Test this invariance rather than interpreting selected k
as discovered player reliability.

For each of 20 fixed seeds, permute historical individual means within strictly
prior team × static-broad-position donor pools. Include all known players in those
pools, not only current starters; exclude n=0 donors. Preserve real starter IDs,
their counts, unseen flags, position references and context. Use sorted IDs and a
SHA256-derived seed keyed by configured seed, placebo seed, decision date, team
and position; the map is fixed within a date and invariant to input row ordering.
Publish support diagnostics, including singleton pools/no-change cases.

This deliberately breaks mean-to-player linkage but not roster/evidence structure.
Donor means have different precision while recipient counts stay fixed: it is an
**identity-link stress test, not an exchangeable permutation test**, p-value or
causal experiment. Repeat the complete development selection/refitting for each
seed; no placebo may be selected using holdout results.

## Models and frozen selection procedure

Primary strong baseline, in fixed column order:

`intercept, team_mean, team_recent, opponent_mean, home, role_sum,
mean_log1p_count, unseen_fraction`.

The augmented model adds only D_k. This prevents the new feature from winning
merely by exposing broad-position composition or history coverage omitted from
the baseline. The original E-07 four-column context is a secondary bridge only.
Fit ordinary least squares with NumPy. Remove only baseline columns whose
training max-minus-min is <=1e-12 (never the intercept); record them and keep the
same remaining base columns for augmented fitting. Never remove a remaining
dependent column by search: insufficient rank invalidates the fit. A residual
column dependent on the retained baseline invalidates that finite candidate.
Holdout variation cannot restore a dropped column or refit coefficients.

Two expanding Spain development folds: November–December training / January
validation, then November–January training / February validation. Require >=50
training and >=30 validation rows in each fold. Each candidate uses identical
rows. A candidate invalid in either fold is ineligible. If the baseline or a fold
sample gate fails, return INCONCLUSIVE and preserve reportable diagnostics.

Select the smallest pooled validation squared error: sum squared errors across
both folds divided by their total validation rows (not an equal-fold mean).
Clip fitted negative forecasts to zero consistently before scoring; report counts.
Candidates within absolute 1e-12 MSE of the minimum tie: prefer context_only,
then greater finite k. The grid order cannot decide a tie. Refit the chosen model
and baseline once on all Spain development rows. If that fit fails, report
INCONCLUSIVE; do not try another candidate after inspecting evaluation outcomes.
Publish all candidate fold errors, exclusion reasons, dropped columns and final
coefficients. Candidate tuning itself is subject to finite-sample overfitting
([Cawley & Talbot, 2010](https://www.jmlr.org/papers/v11/cawley10a.html)).

## Evaluation, reporting and outcome rule

Report unfitted own-team mean, recent-five mean, opponent conceded mean, broad-role
sum and every finite regularized sum even when model fitting is gated. Report MSE,
RMSE, MAE, mean prediction/observation, clipping, row/match/week/club counts,
maximum club share, exclusion reasons, unseen-player fraction and history coverage.
Preserve the operational subset report separately. Empty metrics are null, not zero.

Primary paired loss is chosen-model minus strong-baseline squared error on common
evaluation rows. Reuse E-07's 2,000 shared calendar-week draws and percentile
2.5–97.5% intervals with the new frozen seed, keeping both fixture sides together.
Intervals condition on selected k, coefficients, xT and this post-kickoff-selected
cohort; they omit fitted-model and longer-range dependence uncertainty.

Require >=50 rows and >=8 weeks in **each** league. Missing training/test support
or an unavailable required placebo fit is INCONCLUSIVE. A limited FOLLOWUP_SIGNAL
requires a finite selected k, upper paired interval below zero in both leagues,
and its paired MSE difference strictly smaller than **all 20** placebo differences
in each league. Ties fail this stress criterion. Report discrete rank and every
placebo result; this conservative diagnostic rule is not statistical significance.
Otherwise the incremental signal is NOT_ESTABLISHED. A context-only selection
means the procedure selected no incremental player-history information.

Even FOLLOWUP_SIGNAL needs fresh validation; repeated holdout use can overfit
([Dwork et al., 2015](https://arxiv.org/abs/1506.02629)). No product promotion follows
from any verdict. Publish failure and coverage without changing dates or floors.

## Reproducibility and tests

Artifact: protocol/config/code hashes, dataset manifests, frozen xT/training hashes,
package versions, feature schema version, seeds, selection details and aggregate
diagnostics. No raw or player-match panels in Git. Reuse legal provider checks.

Test future/same-day poisoning, input order, absent versus observed-zero history,
current-team-only transfer histories, unused full-match fields, fixed base columns,
context-only equality, OLS rescaling invariance, training-only model selection,
tie ordering, permutation strata/counts, finite/null reporting and gate behavior.
