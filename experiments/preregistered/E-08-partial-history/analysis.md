# E-08 — greater coverage did not earn incremental player-history prediction

**NOT_ESTABLISHED.** Development-only selection chose `context_only` over every
finite pooling strength. This experiment reached its sample gates, unlike E-07;
it did not establish an incremental forecast signal from these player histories.
It does not establish that players, lineup selection or all other models lack value.

Protocol/config were committed and pushed at `68454bf` before E-08 error evaluation.
The history builder is `b5b1fe9`; the evaluator and CLI are `61fe186`. An independent
pre-outcome review found and verified repair of an empty-cohort reporting bug.
No statistical rules were changed. The complete aggregate artifact is
[results.json](results.json); no player-match panels are committed.

## What was built and evaluated

The new pipeline keeps E-07's fixed first-30-minute positive completed-pass xT
target, pre-November Spain xT reference, stable-opening exclusions and strict
prior-calendar histories. Only the aggregate study admits sparse individual
histories. Unknown individual means get the prior broad-position reference;
actual observed zeros remain observed zeros. Player Lab's evidence gates and XI
eligibility have not changed.

| Cohort | Candidate team observations | Accepted observations | Matches | Weeks |
|---|---:|---:|---:|---:|
| Spain development, November–February | 314 | 272 | 136 | 16 |
| Spain evaluation, March–season end | 246 | 216 | 108 | 11 |
| England evaluation, March–season end | 202 | 174 | 87 | 10 |

All 20 clubs appear in each cohort. Mean unseen-starter fractions are 3.75%,
1.11% and 1.32%, respectively. E-07's 900-minute/three-opening individual gates
produced only 3 development rows; the changed **aggregate** estimand now has 272.
Those are different cohorts, not a before/after model-error comparison.

## The development decision

The baseline already contains own-team mean/recent threat, opponent conceded
threat, home/away, broad-position reference sum and history-coverage summaries.
Each candidate adds only its regularized individual-history residual sum.

First fold: 122 training and 68 validation observations. Second fold: 190 training
and 82 validation observations. The following MSEs pool the 150 validation rows,
not equally weighted fold means. All six candidates were eligible; no baseline
columns were dropped. These are development selection scores, not fresh test errors.

| Candidate | Pooled development-validation MSE |
|---|---:|
| Context only — selected | 0.071181 |
| Individual history, k=0 | 0.071975 |
| Regularized history, k=1 | 0.071840 |
| Regularized history, k=3 | 0.071671 |
| Regularized history, k=10 | 0.071759 |
| Regularized history, k=30 | 0.072069 |

The best finite candidate was k=3, still worse than the baseline by 0.000490 MSE.
No held-out result was used to rescue another candidate or choose a new model.

## Evaluation and identity-link controls

| Forecast | Spain MSE | England MSE |
|---|---:|---:|
| Selected / strong context baseline | 0.082657 | 0.071578 |
| Original weaker E-07-style context | 0.083265 | 0.069227 |
| Unfitted prior team mean | 0.087631 | 0.088730 |
| Unfitted player-history sum with unseen-player references | 0.092637 | 0.094215 |

Selected and strong-baseline predictions are **the same function**. Their paired
MSE difference and week-resampling interval are therefore exactly zero and [0, 0].
That is an algebraic identity after context-only selection, **not** a tight interval
proving that player effects are absent. The weaker context comparator performs
better in England; “strong” describes the controls included, not guaranteed accuracy.

All 20 fixed identity-link controls completed their own forward selection/refit.
They shuffle prior player means inside team/position groups while preserving
recipient evidence counts. The actual procedure ranks 18th/16th of 21 in the
conservative tie-counting diagnostic, and does not strictly beat every control.
These ranks are neither p-values nor causal tests. “Changed players” in support
diagnostics means a changed assigned historical mean, not merely a different
donor with an identical mean. All candidate folds, final coefficients and control
errors are retained in the artifact.

Operational full-match accounting is available for 209/216 Spain and 168/174 England
evaluation rows. Its errors are reported only alongside comparators evaluated on
those **same subsets**; missing full-match accounting cannot exclude a primary row.

## Interpretation and product consequence

Partial evidence solved this design's coverage obstruction, not its incremental
prediction problem. This specified additive-history procedure preferred context
without the individual residual. The null is narrower than a general rejection
of lineup information, but it does not justify learned player weights, a predicted
XI rating, or transfer-value claims.

Evaluation periods overlap previously inspected E-07 outcomes. The protocol
disciplines the follow-up but does not make those periods untouched. Week intervals
condition on fitted models, pooling selection, the fixed xT surface and post-kickoff
stable-window exclusions; they omit broader uncertainty and dependence.

Keep the product's explicit-requirement decision claim. Do not repeatedly retune
this corpus until individual utility appears. The prudent next product increment
is transparent alternatives under declared requirements; any renewed predictive
claim needs a separate rationale and fresh permitted evaluation evidence.

## Reproduction

```powershell
.venv\Scripts\python.exe -X utf8 experiments/run_partial_history.py
.venv\Scripts\python.exe -m pytest -q tests/test_partial_history.py tests/test_partial_evaluation.py tests/test_partial_experiment.py
```

The complete run was repeated unchanged because the first pretty-printed tool
response was truncated; compact capture preserved the full second artifact.
The intact first-run provenance, coverage, selection and actual-model evaluation
sections exactly matched the repeat. Source hashes normalize checkout CRLF to LF;
dataset file hashes remain byte-exact. Both runs used the same frozen configuration.
