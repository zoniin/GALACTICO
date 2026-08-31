# Research questions

Each has a benchmark, a baseline and a failure condition. An answer of "no" is
publishable, and is expected in several cases.

## Open

1. **Does the Bridge work?** Can LIVE aggregates reconstruct xT-derived axes?
   Baseline: the position-and-minutes mean. Success: out-of-sample R^2 approaching
   the Box Plus/Minus analogue at ~0.79 offensive. Expect ~0.19 on defensive axes,
   i.e. failure, and do not ship those.
2. **Does role fit exist?** Replicate the 9% interaction-variance finding, then
   ship only dimensions where a role-transition model beats persistence.
   Final-third touches beat it by ~32% MSE; shots and xG go negative.
3. **Is Metronome Fit a real construct**, or does it collapse into generic
   involvement once residualised on touch volume and team possession share?
4. **Does lineup optimisation beat manager persistence?** Baselines in ascending
   difficulty: random feasible XI, top-11 by prior minutes, top-11 by rating, and
   the same XI as last match.
5. **Do system-level ratings predict match xG** better than a sum of individual
   ratings, and better than Elo alone?
6. **Can broadcast video measure compactness?** Individual position error is
   1.7-16.4 m. Does averaging over eleven players suppress it enough for team width
   to be usable? Measured against ground truth, not eyeballed.
7. **Does marginal system fit outperform player rating** at ranking historical
   transfers by realised success?
8. **Is complementarity predictive?** Log structural complementarity scores now;
   test them against lineup outcomes once enough have accumulated.

## Settled

- **Which value primitive?** xT. Split-half 0.89 against VAEP's 0.25.
- **Is finishing measurable?** No.
- **Is pairwise chemistry estimable?** No.
- **Is a single optimal XI identified?** No.

