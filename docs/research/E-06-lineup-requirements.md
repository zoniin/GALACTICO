# E-06: explicit requirements, not identified lineup utility

XI Lab solves a finite assignment model, not expected football wins. The two
templates are 4-3-3 and 4-3-1-2. Madrid eligibility is a versioned manual football
rule, separate from player values. Player-by-role uplifts, chemistry, continuity
bonuses and a universal quality sum are absent.

Three active requirements: positive completed-pass xT per 90 and experimental left
and right wide-channel completed-pass-origin counts per 90. The side-specific
descriptors are research inputs, not validated team width. Rates are summed under
an explicit unchanged-deployment assumption. The default minimum and normalizer
are each the median sum of pre-cutoff player rates in prior actual starting XIs.
Changing the minimum leaves the original normalizer fixed; both are recorded in
the full tactical requirement inputs and their fingerprint.

BALANCE minimizes worst normalized shortfall, then total normalized shortfall.
SATISFY makes active minima hard. CP-SAT quantizes normalized coefficients to
100,000 units, and the result records solver stages, bounds, scale and rounding.
Optimality refers to that discretized problem. Tiny random instances are compared
with all feasible assignments in an independently implemented oracle. Equivalent
slot permutations are pruned only when eligibility and requirement incidence match.

Shared team-match worlds recompute every player's numerators and exposure using
the same count weights. An opposite-membership solve identifies whether a player
is necessary/possible among all equally optimal XIs. The browser defaults to 12
worlds, explicitly an exploratory summary; API callers may request up to 80.
These ranges reflect optimizer ambiguity and resampling, not fitness, model
uncertainty, causal superiority or confidence in a football ranking.

The pre-Clásico snapshot uses only dates before 6 May 2018, including xT training.
Sixteen candidates survive eligibility and sample rules. Isco has 1,638 prior
league minutes and Modrić 1,733, both below Wyscout's 1,800-minute creation floor.
Chance creation is therefore an unmeasured team requirement. Defensive and keeper
quality are also unmeasured. Injury/suspension/fitness are unverified. Do not call
the resulting model a solution to all aspects of the BBC-versus-Isco question.

## Temporal selection diagnostic

Run `python experiments/run_xi_backtest.py --since 2018-03-01`. This late-season
window is a development diagnostic, not a preregistered external validation.
Every match refits inputs strictly before the decision day; all 12 solves certify.

| Mean actual starter overlap, out of 11 | Result |
|---|---:|
| Requirement-model representative | 6.00 |
| Prior-minutes baseline, same eligibility | 6.83 |
| Previous **league** XI, ungated | 5.00 |
| Candidate-set maximum possible overlap | 9.17 |

The model loses to the simpler prior-minutes baseline. No performance-improvement
claim is supported. The previous league XI can be a poor baseline during rotation
and is not the previous match across all competitions. Missing availability and
sample gates constrain achievable agreement. Equal-optimum representative choice
also affects overlap; no tie-break was optimized for manager agreement.

The tool remains a thinking aid for explicit requirements. Team-outcome
association, role-transition benchmarking, forced-change quasi-experiments,
formation inference and external utility validation have not been run. No
observational lineup comparison can reveal the unplayed counterfactual.
