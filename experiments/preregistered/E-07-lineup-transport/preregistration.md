# E-07 — does lineup history add forecast information beyond team context?

This plan must be committed before evaluating forecast errors. Both historical
corpora have been inspected in earlier research; this is a prospective analysis
plan on reused historical data, not a claim of untouched data collection. Structural
quality counts and clock/schema checks have been inspected, not this experiment's
forecast associations. All thresholds live in `config.json` and must not change
after results are seen. Deviations are reported, not silently adopted.

## Claim and estimand

For the lineup that actually started, predict its **attributed positive completed-pass
xT in the first 30 minutes**, summed over the ten actual outfield starters. The
primary question is whether player history adds predictive information beyond
own-team history, opponent conceded history and home/away.

This does not estimate causal player contributions, performance of an unplayed XI,
general football utility, goals/wins or the tactical effects of changing deployment.
It tests an important prerequisite for predictive interpretation of lineup inputs.
The existing requirement solver is not changed by this experiment.

## Target and availability

Use the public Pappalardo Spain/England 2017/18 corpora only. The target window is
`period == 1H` and `0 <= seconds < 1800`; it has fixed exposure, not reconstructed
lineup minutes. Both sides must have eleven unique recorded starters, exactly one
identified goalkeeper and known broad positions. The first-half event stream must
extend to 1800 seconds. Reject a whole match if either side has a substitution at
nominal minute <=30, a tagged dismissal (`1701`/`1703`) before 1800 first-half seconds,
an unattributed completed pass, an invalid completed-pass coordinate, or a named
nonstarter acting in the opening window. Raw substitution time is coarse; this
conservative boundary is intentional. Dismissals use exact event clocks, not the
rounded match metadata minute.

This selects on events observed after kickoff. Report exclusion reasons and
coverage; conclusions apply only to stable, recorded opening lineups. Nonstarter
and invalid-window exposure is missing, not zero. A valid starter with no recorded
passes contributes zero. Do not infer hidden coordinates or exact full-match minutes.

## Fixed measurement and time split

Fit one 16x12 xT surface on **Spain matches dated strictly before 1 November 2017**,
using the current XI fitting definition (completed passes, open-play shots,
unsuccessful passes as turnovers). Hold it fixed for both leagues and every
feature/target. This deliberately tests transport of the same reference construct;
no English refit is substituted after observing results. Record its full hash.

Development/calibration: Spain, 1 November 2017 through 28 February 2018.
Temporal evaluation: Spain, March through season end. External evaluation: England,
March through season end. These are new forecast-error evaluations on previously
used corpora. All descriptive histories use strictly earlier **calendar dates**,
so simultaneous matches cannot leak. English histories may update chronologically;
English outcomes cannot tune fitted coefficients or any policy.

## Common mature cohort

Every evaluated outfield starter needs >=900 prior nominal league minutes (the
shipped XI sample rule) and >=3 prior valid opening starts. Own team and opponent
need >=5 prior valid opening windows. Use the same target rows for every comparator.
Report rejected rows rather than lowering floors after seeing coverage. A player
changing teams uses only history at the current team, matching the present XI
carry-forward definition. Broad-role history is league-wide and prior-only;
provider MD is normalized to MF. No tactical role inference is claimed.
Clean historical windows are built independently of these evaluation eligibility
gates, so early-season evidence is not recursively discarded. Nominal minutes
are inherited eligibility, not corrected actual exposure. Report unique clubs,
maximum club share and calendar weeks as well as row/match counts.

## Forecasts

Unfitted comparators, all in xT per 30 minutes:

1. Own-team mean of all prior valid openings.
2. Own-team mean of its last five prior valid openings.
3. Opponent's mean previously conceded opening xT.
4. Sum of prior league broad-position opening means for the ten starters.
5. Sum of each starter's own prior valid-opening mean (**lineup opening history**).
6. Current operational carry-forward: sum of each starter's prior full-match xT
   divided by prior nominal minutes, multiplied by 30.

Comparator 6 deliberately retains the current pipeline's imperfect full-match
exposure. Its error cannot isolate additivity from horizon or minutes-reconstruction
error. Comparator 5 avoids that mismatch and is the primary lineup feature.

Fit ordinary least squares on the common Spain development cohort only:

- Context: intercept + own-team opening mean + opponent conceded opening mean + home.
- Context + lineup: those same columns plus (lineup opening history − own-team mean).

The subtraction names a lineup deviation from team history. Since team history
is already a regressor, this is algebraically equivalent to adding the raw lineup
sum; it does not isolate a within-team or causal effect. No hyperparameter search,
shrinkage grid, role interaction, player identity coefficient or feature selection.
Use NumPy least squares; insufficient rank or <50 development rows is INCONCLUSIVE.
Freeze coefficients before evaluating either test period. Clip negative predicted
xT to zero consistently for both fitted forecasts and report the clipping count.

## Scoring, dependence and decision rule

Primary: paired mean **squared-error difference**, augmented minus context, on
identical held-out rows. OLS targets a conditional mean, so squared-error scoring
matches that directive ([Gneiting, 2011](https://arxiv.org/abs/0912.0902)). MAE, RMSE,
mean prediction/observation and raw comparator errors are secondary diagnostics.
No single-match or team ranking is produced.

Resample calendar-week clusters 2,000 times with seed 20260908, keeping both team
observations of a fixture together. Percentile 2.5–97.5% intervals describe this
limited one-season resampling analysis; they omit fitted-parameter/xT-surface
uncertainty and longer-range dependence. Do not call them universal confidence.

Require >=50 held-out team rows and >=8 calendar weeks in **each** league. Otherwise
INCONCLUSIVE. Evidence of incremental prediction requires the upper interval bound
for augmented-minus-context MSE to be below zero in **both** Spain and England.
Otherwise incremental prediction is NOT_ESTABLISHED. Passing is not permission to
turn these coefficients into XI utility weights; that needs a separate decision claim.

## Implementation checks and output

Test clock boundaries, missing coordinates/exposure, two-sided early incidents,
unique players, zero-action starters, ordering, prior-date exclusion, future-poisoning
invariance, baseline/augmented column identity and shared-week resampling. Freeze
the scoring rule in tests. Publish all aggregate errors and coverage even on failure.
Artifact provenance includes protocol/config hashes, code fingerprints, dataset file
hashes, xT hash, package versions, sample filters and seed. Only aggregate results
may enter Git; raw and per-player/per-match panels remain in ignored runtime data.
