# E-07 result: joint lineup evidence is too sparse

**INCONCLUSIVE — no forecast coefficients were fitted and no held-out forecast
errors were evaluated.** The frozen development minimum was 50 team observations;
only 3 qualified. Neither the nominal-minute floor nor the dates were relaxed.

The protocol was committed at `1de6939` before forecast evaluation. The implementation
was committed at `8f6f65a`; subsequent repairs corrected a provenance file path and
completed the specified coverage fields, not the sample rules or scoring target.
The complete aggregate artifact is `results.json`; raw panels are not committed.

| Cohort | Candidate team observations | Clean opening matches | Eligible team observations |
|---|---:|---:|---:|
| Spain development, Nov–Feb | 314 | 136 | 3 |
| Spain holdout, Mar–May | 246 | 108 | 41 |
| England holdout, Mar–May | 202 | 87 | 32 |

The 900-minute floor excludes 311 of 314 development rows. An independent calculation
directly from normalized appearances—cumulative minutes before the decision day,
then the minimum across the ten actual outfield starters—also finds only 3 complete
development lineups above that floor. The median least-observed starter has 216
prior nominal minutes; the upper quartile is 367. These are measurements of this
cohort, not general football thresholds.

First-30-minute quality gates matter independently. Nominal substitution minute 30
is conservatively excluded. Exact event clocks catch a dismissal at 1798.98 seconds
whose rounded lineup metadata says minute 31. Unattributed completed passes are
not assigned to a guessed player. All valid early histories inform later estimates,
even when their own lineups fail the evaluation exposure floor.

## What this establishes

A per-player evidence rule can leave very few complete observed lineups available
for temporal validation. The combination of a short within-season history and
ten simultaneous individual gates is a serious coverage limit of this design.

It does **not** establish that lineup information lacks predictive value, that the
team-context baseline wins, or that the current solver chooses poor footballers.
The experiment did not reach its model-fitting gate. The Spain/England xT surface
was frozen from 100 Spain matches ending 30 October 2017, and is fully fingerprinted.

## Consequence for the product

Keep XI Lab's current conditional requirement claim. Do not convert summed player
rates into a validated forecast or quietly lower individual evidence gates. Nothing
from E-07 changes solver coefficients, eligibility or requirement thresholds.

The next defensible study is **aggregate prediction with explicitly partial player
evidence**, separately preregistered: compare team context against partially pooled
opening histories, with sparse-player uncertainty admitted. That would test an
aggregate forecast, not certify each player's individual ability. Another option
is genuinely longer permitted historical coverage. Neither is an amendment that
can be smuggled into E-07 after this failure.
