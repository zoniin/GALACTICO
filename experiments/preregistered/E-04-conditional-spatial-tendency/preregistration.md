# E-04 — Conditional spatial tendency

**PLACEHOLDER. Not run, not designed in full, and deliberately not part of
Stage 2.** This exists so the stronger claim has somewhere honest to go.

## Why it exists

`half_space_share` and `width` ship as *descriptive* constructs: the observed
share of completed passes originating in a channel. That is exactly what the
estimator computes, and the shipped language now says so.

They do **not** establish a preference. Position is CONSTITUTIVE for them —
deployment is part of the measurement, not a confound removed from it. A player
with a 46% half-space origin share may seek those channels, or may simply have
been played there.

Verticality was rejected because its behavioural reading mostly vanished after
conditioning on field position. The spatial constructs avoid that fate only
because their claim is now narrow enough to be true. Widening the claim without
this experiment would reproduce the verticality error with a different name.

## The question

> Does a stable player-level spatial tendency survive after accounting for
> deployment and opportunity?

## Sketch, not a design

For each eligible completed pass, model the probability that it originated in the
half-space, conditional on context:

    logit P(half_space origin) = context effects + player effect

with context covering at least broad role, longitudinal pitch zone, team, and side
of pitch. The player effect is what "preference" would need to mean.

Open questions the council must settle before this is a preregistration:

- Is the player effect identified, or absorbed by team and role?
- Deployment is chosen by the manager partly *because* of the player's tendency.
  Is anything here identified at all, or is this the role-fit positivity problem
  again in spatial clothes?
- What is the null? Stage 1C measured player × role interaction at ≤9% of
  variance; is there any reason to expect more here?
- What would falsify it?

## Status

Not scheduled. Do not run during Stage 2.

