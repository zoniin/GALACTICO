# E-03 — Ball retention: a reliable metric with nothing to add

**Status: construct formally closed.** Rejected in 5 of 5 leagues.

## The claim under test

Threat-weighted ball retention. The idea was that losing possession in your own
box should count for more than losing it near the touchline, so weighting losses
by the expected threat at stake ought to separate players that raw pass completion
cannot.

Stage 1 rejected it on La Liga. This tested whether that rejection was a La Liga
accident.

## Result

| League | Reliability | Confound R² | \|r\| with pass completion | Top-12 kept |
|---|---:|---:|---:|---:|
| Spain | 0.90 | 0.27 | **0.95** | 4/12 |
| England | 0.87 | 0.31 | **0.93** | 5/12 |
| Italy | 0.89 | 0.22 | **0.93** | 4/12 |
| Germany | 0.87 | 0.19 | **0.95** | 4/12 |
| France | 0.87 | 0.21 | **0.93** | 6/12 |

Reliability between 0.87 and 0.90 in every league — this is a *good measurement*.
And in every league it correlates with plain pass completion percentage between
0.93 and 0.95, against a pre-declared ceiling of 0.85.

The threat-weighting moves 5–13% of the variance. The other 87–95% is a statistic
that any spreadsheet already contains.

## Why this failure is different from E-01's

They fail at different stages, and the distinction is worth keeping.

**Metronome Fit failed the confound audit.** It was measuring something other than
what it claimed — touch volume dressed as rhythm control. The number was about the
wrong thing.

**Ball retention fails incremental information.** It measures exactly what it
claims. It is reliable, it is not badly confounded, its ordering is stable. It is
simply *redundant*: a sophisticated transformation that contributes almost nothing
beyond a trivial baseline.

> A metric can be honest, reliable and about the right thing, and still not earn
> its place, because a simpler statistic already carries the information.

This is the failure mode that sophistication actively hides. A complicated formula
feels like it must be adding something, and reliability testing will not tell you
otherwise — ball retention passes reliability more comfortably than progression
does. Only a deliberately stupid baseline exposes it.

## What ships instead

Pass completion percentage, under its own name, as a `DERIVED` quantity with no
pretence of being more.

## Closing the construct

Five independent leagues, one frozen threshold, the same verdict everywhere. The
construct is closed. Reopening it requires a new operationalisation and a
preregistration, not a rerun.

