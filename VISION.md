# Vision

Football analytics describes players well and answers decisions badly.

The descriptive layer is mature: expected goals, possession value, radars,
percentile tables. Ask it a decision question and it goes quiet. Who should start
against this opponent? Which role suits this player? What does this squad
structurally lack, and which of the twenty plausible signings actually fixes it?

Those are optimisation questions wearing football clothes. Galactico is an attempt
to state them explicitly, solve them exactly, and — the part most tools skip —
measure whether the answers are worth anything.

## What it is not

Not a ratings website. Not a dashboard. Not a model that claims to have found
football's hidden equation.

Football is contextual, adversarial, noisy, partially observed, endogenous and
strategically adaptive. An optimiser cannot tell you the objectively correct XI.
It can tell you this:

> Given these observations, these estimated player properties, these tactical
> requirements, this objective and this uncertainty, these lineups are favoured.

That sentence is defensible, and it is more interesting than the one it replaces.

## The three commitments

**Ambition.** Data engineering, statistics, machine learning, mathematical
optimisation, operations research, computer vision, representation learning,
uncertainty quantification, and an interface a football person would actually
use. The reaction to opening the repository should be a question about why one
person built all of it.

**Honesty.** Every number knows what kind of number it is. Observed fact, derived
statistic, statistical estimate, model prediction, optimisation output, heuristic
and untested hypothesis are seven different things and are never rendered as one.

**Falsifiability.** Every modelling claim has a benchmark, a baseline and a
failure condition, written down before the experiment runs. Failures are published
in `/research` rather than buried. Most sports analytics products hide
uncertainty; this one is built out of it.

## Real Madrid

The laboratory subject, for two reasons. Squad construction there is genuinely
hard — an expensive squad with real structural questions, not a puzzle with an
obvious answer. And the 2017/18 season poses the sharpest selection question in
modern football, the BBC front three against an Isco-led shape, with a known
outcome to check against.

The engine is not Madrid-specific. Feed it any club with data.

