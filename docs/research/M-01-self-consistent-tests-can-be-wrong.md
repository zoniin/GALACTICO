# M-01 — A test suite can be consistent with the code and wrong about reality

**Methodology note. This one is permanent.**

## What happened

The first expected-threat fit on real La Liga data produced a surface where the
own penalty area and the centre circle differed by less than 0.0001. Every cell
was worth roughly the same, which means no pass has value, which means every
progression number downstream would have been noise around zero.

The test suite was green. It had been green through the entire implementation.

## Why the model was wrong

The value iteration was

    xT[z] = s[z]·g[z] + m[z]·Σ T[z,z']·xT[z']

with `m` and `s` estimated as move-count and shot-count over their sum. That
forces `m[z] + s[z] = 1` in every cell: the ball always either moves or is shot,
and possession never simply ends.

A Markov chain with no absorbing state other than a shot has one destination.
Every possession eventually produces a shot from somewhere, so the expected value
of holding the ball anywhere converges to the same number — the league's overall
scoring rate per possession. The fixed point is flat *by construction*, and no
amount of data changes it.

Supplying turnovers as an absorbing state makes `1 - m[z] - s[z]` the per-cell
probability of losing the ball. Value then decays with the number of transitions
required to reach a shot, which is what makes distance from goal cost something.

## Why the tests did not catch it

Because the generator and the implementation shared the same false assumption.

`synthetic_pitch()` produced successful moves and shots. It produced no
turnovers, because the author was thinking about the same model the code
implemented. The tests then asserted things that were true of *that* world:
values rise toward goal, forward passes beat backward ones. Both held, weakly,
because shot probability still varies by cell. The synthetic surface had a
coefficient of variation of 0.30 — enough to satisfy an ordering assertion,
nowhere near enough to be a usable model. With turnovers the same generator
produces 1.25.

The suite verified that the code agreed with the author's mental model. Both were
wrong about football, and agreement between them proved nothing.

> A test suite can establish consistency between code and synthetic assumptions
> while both are wrong about reality.

## What exposed it

Not a test. Printing the fitted surface's column means and reading them:

| Own third | Middle | Final third | Opposition box |
|---:|---:|---:|---:|
| 0.1258 | 0.1257 | — | 0.1756 |

Nine significant figures of agreement between the own box and the centre circle
is not a subtle numerical issue, it is a football impossibility. It took about
four seconds to see once the numbers were on screen.

## What changed

**The generator now models turnovers**, because a generator that shares the
implementation's assumptions cannot test them.

**Three invariants stated in football terms rather than equation terms:**

- Moving from your own penalty area to the top of the opponent's box must be
  worth more than a quarter of the surface's total range. Expressed as a fraction
  of the range so it holds at any scale, and derived from what football requires
  rather than from what the formula computes.
- Value must be monotone along the central corridor toward goal.
- A fit with no turnovers must collapse to near-uniform, and adding them must
  restore the gradient by at least 3×. This asserts the failure *directly*, so
  the day someone changes the parameterisation the guarantee has to be re-derived
  rather than silently lost.

## The general lesson

Two rules came out of this and apply beyond xT.

**Prefer invariants derived from the domain over invariants derived from the
implementation.** "Forward passes are worth more than backward ones" restates the
equation. "Your own box is worth materially less than the opponent's box" is a
claim about football that the equation has to earn.

**Look at the output on real data before trusting the suite.** The audit step in
`ingestion/pipeline.py` exists for the same reason, and the four-second read that
caught this is now a required step rather than a lucky one.

