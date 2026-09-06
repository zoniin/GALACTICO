# M-04: independent samples were a false assumption

At `f0ed51a`, Player Lab resampled each player and each construct independently.
The comparison API paired those draws while claiming different players were
independent. Teammates share match conditions. The code could not recover their
covariance, despite storing draws rather than marginal quantiles. All 176 existing
tests passed before the repair.

The repair draws one multinomial count vector over sorted historical match IDs
for each world. All player/construct numerators and exposure denominators consume
that same vector. A player absent from a match has zero exposure, not a zero rate.
World identifiers preserve holes when an entire resample contains no exposure.
Differences use the intersection of finite, identified common worlds.

The independent regression example gives two teammates identical, varying match
performances. Both marginal intervals are wide, but their difference is exactly
zero in every shared world. Independent bootstraps fail this test. Additional
tests cover row-order invariance, cross-construct identity, absent exposure and
rejection of unrelated or quantile-only worlds.

The bootstrap method, seed, world namespace and semantic versions enter artifact
identity. The API refuses stale artifacts, and gated quantities are withheld from
compare and scatter as well as profile/explore. Excluding zero is described as
statistical direction; no practical-importance threshold has been identified.

Limits: conditional on a fixed xT surface; exchangeable matches despite changing
roles/form; limited rare-player coverage; no causal uncertainty. XI snapshots
must filter xT training before the decision date independently of this repair.
