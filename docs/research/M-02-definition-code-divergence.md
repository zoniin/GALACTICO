# M-02 — A metric can be validated, stable, and describe a different quantity

**Methodology note. Permanent.**

## What happened

The construct registry declared `progression_per_action` as *per completed pass*.
The implementation divided by *every on-ball action* — passes, touches, shots and
duels. The registry also declared `half_space_share` and `width` as shares of
on-ball actions while the shipped estimator used completed passes.

Three of five constructs had a public definition that described a different
quantity from the one being computed.

## Why it survived everything

This is the uncomfortable part. The affected metrics had passed:

- split-half reliability, 0.83–0.99 across five leagues
- a confound audit against touch volume and team
- a baseline battery against eight deliberately stupid statistics
- external replication under a provider **and** season shift

None of that could catch it. Every one of those procedures asks *is this number
stable, and is it measuring something distinct?* The number was stable. It was
measuring something distinct. It simply was not the thing the definition claimed.

> A metric's implementation can be numerically stable and scientifically validated
> while its public definition describes a different quantity.

Reliability testing compares a metric to itself. Nothing in the measurement
lifecycle compared the metric to its own description.

## Why it mattered more than it looked

Wyscout duels are **27% of all actions**; StatsBomb decomposes contested
situations differently and has far fewer. So "on-ball actions" is not a stable
denominator across providers — it is a different population in each ontology.

A cross-provider replication computed with that denominator would have been
comparing two different quantities and reporting the difference as a finding about
football. Stage 1C caught this by harmonising to completed passes, but by
reasoning about the ontologies rather than by any mechanism.

## Why ordinary tests missed it

Because there was nothing to test *against*. The declaration lived in a
dataclass field as a string, the computation lived in a function body, and no
artefact connected them. A test could only have asserted that a hand-written
string matched a hand-written implementation — two independent restatements of an
intention, which is exactly the pair that drifted.

## What now prevents it

**The definition became executable.** `galactico/features/spec.py` holds one
`ConstructSpec` per construct, declaring numerator, denominator, eligibility
filters and scaling as data. Both the number and the English sentence are derived
from it:

    SPECS["progression_per_action"].describe()
    'sum of positive xT gain over completed passes, per completed passes'

There is no second definition to drift from, because the implementation *is* the
specification, evaluated. The spec evaluator was checked against the previous
inline implementation across all 345 players and five constructs: maximum absolute
difference **0.0** everywhere.

**A per-action spec cannot omit its denominator.** Constructing one raises, with
the failure named in the message. Leaving it implicit is precisely how the bug
happened.

**Contract tests use adversarial fixtures.** The motivating one: one completed
progressive pass, one failed pass, four duels. The denominator must be 1. Adding
duels must not move the number. That fixture fails against the old implementation
and passes against the new.

**Semantic changes invalidate versions.** Each spec has a fingerprint hashing its
structure, and the fingerprints participate in the profile artifact's version key.
Widening a denominator changes the hash whether or not anyone bumps a version
number — which was demonstrated when the artifact key moved from `fe9d6a56add9`
to `fdbfab4d9a42` the moment fingerprints were included.

## The general lesson

The measurement lifecycle had six stages and none of them asked whether the metric
matched its own description. Validity against *the world* and validity against
*the claim* are different audits, and the second one is cheaper, easier to
automate, and was entirely absent.

Prefer generating documentation from semantics over maintaining both.

