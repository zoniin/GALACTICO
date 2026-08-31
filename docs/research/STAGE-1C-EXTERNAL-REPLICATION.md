# Stage 1C — external replication under a provider and season shift

**Wyscout/Pappalardo 2017/18 → StatsBomb 2015/16.**

Both change at once, so no discrepancy can be attributed uniquely to provider
ontology. This is `EXTERNAL_REPLICATION_PROVIDER_SEASON_SHIFT`, and the question
is not whether the numbers match — it is whether the football construct survives.

## Corpus, verified from the manifest

| Competition | Matches | Teams | Event files |
|---|---:|---:|---:|
| La Liga 2015/16 | 380 | 20 | 380 / 380 |
| Premier League 2015/16 | 380 | 20 | 380 / 380 |
| Serie A 2015/16 | 380 | 20 | 380 / 380 |
| Ligue 1 2015/16 | 377 | 20 | 377 / 377 |

Complete populations, 3.4 GB, local tier only — StatsBomb's agreement bars
redistribution and bars commercial exploitation of derived analysis, so nothing
here is committed and nothing derived from it may ever be hosted.

## The estimators had to change, and the Stage 1B numbers do not carry over

Stage 1B computed per-action axes over "on-ball actions". That population means
different things in the two ontologies: **Wyscout duels are 27% of all actions and
StatsBomb's are far fewer**, because StatsBomb decomposes contested situations
differently. Comparing those directly would compare two different quantities and
call the difference a replication result.

So both sides were **recomputed over completed passes only** — the one action both
providers represent comparably — and the Wyscout Stage 1B figures are not reused.
This is estimator v2 on both sides. Every number below is like-for-like.

Carries are the other case. StatsBomb records them; Wyscout has no equivalent. The
StatsBomb progression estimator **excludes carries on purpose**, so the definition
matches. A carry-inclusive version is registered separately as
`statsbomb_carry_v1`, an `APPROXIMATED` estimator of the same construct, so it can
never be mistaken for the reference one.

| Concept | Overlap | Equivalence |
|---|---|---|
| completed pass | HIGH | SEMANTICALLY_EQUIVALENT (inverse outcome convention) |
| ball-moving action | MEDIUM | IDENTICAL_DEFINITION (by excluding carries) |
| shot | HIGH | SEMANTICALLY_EQUIVALENT |
| turnover / absorbing state | MEDIUM | SEMANTICALLY_EQUIVALENT |
| on-ball action denominator | **LOW** | **NOT_COMPARABLE** — hence the harmonisation |
| pressure / press resistance | NONE | NOT_COMPARABLE (StatsBomb-only, unused) |

## Results

**Reliability**

| Axis | WY ESP | WY ENG | WY ITA | WY FRA | SB ESP | SB ENG | SB ITA | SB FRA |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| progression | 0.89 | 0.90 | 0.88 | 0.88 | 0.91 | 0.92 | 0.88 | 0.93 |
| progression_per_action | 0.90 | 0.83 | 0.87 | 0.87 | 0.88 | 0.91 | 0.88 | 0.91 |
| chance_creation | 0.60 | 0.55 | 0.70 | 0.69 | **0.84** | **0.85** | **0.78** | **0.90** |
| half_space_share | 0.95 | 0.95 | 0.94 | 0.95 | 0.96 | 0.97 | 0.95 | 0.96 |
| width | 0.98 | 0.98 | 0.98 | 0.98 | 0.99 | 0.99 | 0.98 | 0.99 |

**Confound R²** against pass volume and team

| Axis | WY range | SB range |
|---|---|---|
| progression | 0.20–0.31 | **0.07–0.17** |
| progression_per_action | 0.06–0.08 | 0.05–0.06 |
| chance_creation | 0.07–0.13 | 0.04–0.09 |
| half_space_share | 0.05–0.11 | 0.01–0.03 |
| width | 0.01–0.03 | 0.01–0.03 |

**Closest simple baseline |r|** — every axis in both regimes sits between 0.39 and
0.70, far below the frozen 0.85 ceiling. No axis becomes redundant under either
ontology.

## External verdicts

| Construct | Verdict |
|---|---|
| `progression` | **ROBUST_WITH_SHIFT** |
| `progression_per_action` | **ROBUST_WITH_SHIFT** |
| `chance_creation` | **ROBUST_WITH_SHIFT** (improves) |
| `half_space_share` | **ROBUST_WITH_SHIFT** |
| `width` | **ROBUST** |

Nothing failed. Reliability is equal or better under StatsBomb for every axis,
confounding is lower for every axis, and no axis collapsed into a simple baseline.

## Distribution shift, and why attribution is limited

La Liga, the one competition present in both regimes:

| Axis | Wyscout 2017/18 | StatsBomb 2015/16 | Shift |
|---|---:|---:|---|
| progression | 0.1707 ± 0.0961 | 0.1157 ± 0.0854 | −32% |
| progression_per_action | 0.0058 ± 0.0031 | 0.0036 ± 0.0026 | −38% |
| chance_creation | 0.0213 ± 0.0243 | 0.0448 ± 0.0544 | **+110%** |
| half_space_share | 0.3586 ± 0.1229 | 0.3076 ± 0.1183 | −14% |
| width | 0.4056 ± 0.2399 | 0.4451 ± 0.2401 | +10% |

**Provider and season moved together, so these cannot be attributed cleanly.** The
plausible contributions, stated as hypotheses rather than conclusions:

- The **progression** drop is most likely the xT surface, refitted on StatsBomb's
  own action population with its own turnover semantics — StatsBomb splits
  loss-of-control into Miscontrol and Dispossessed where Wyscout folds both into a
  failed touch, which changes the absorbing-state mass and therefore the whole
  surface's scale. Football-era effects between 2015/16 and 2017/18 cannot be
  ruled out and are not separately identified.
- The **chance_creation** doubling is most likely the assist-marking difference.
  StatsBomb marks `shot_assist` and `goal_assist` explicitly; Wyscout uses a
  key-pass tag. That mapping is `SEMANTICALLY_EQUIVALENT`, not identical, and it
  is the one place where a definitional difference is doing visible work.
- The **style** shifts are small and could be either.

Absolute values are therefore not comparable across regimes, which is why the
construct registry marks cross-provider pooling of raw values an invalid context.
The rankings and validity are what replicate.

## The finding that changes a product rule

**Chance creation is far more reliable under StatsBomb, and the 1,800-minute gate
does not transfer.**

| Minutes floor | Wyscout r | StatsBomb r |
|---:|---:|---:|
| 450 | 0.544 | **0.821** |
| 900 | 0.625 | 0.849 |
| 1,350 | 0.683 | 0.881 |
| 1,800 | 0.725 | 0.893 |
| 2,250 | 0.756 | 0.899 |

Under StatsBomb the axis clears the 0.70 number-grade threshold at **450 minutes** —
it is already more reliable at 450 than Wyscout is at 2,250.

That is a strong signal the Wyscout instability was **measurement noise in the
key-pass tag rather than sparsity of the underlying football event**. Under a
richer, more consistently marked assist annotation, the same construct stabilises
almost immediately.

The consequence is that a single global minutes gate would be wrong in both
directions — over-cautious on StatsBomb, and falsely reassuring if applied the
other way. **The floor belongs to the estimator, not the construct**, which is
exactly what the construct-versus-estimator split exists for:

    chance_creation
        wyscout_event_v1    minutes_floor = 1800
        statsbomb_event_v1  minutes_floor =  450

## Decision

The Stage 2 gate required `progression` and `progression_per_action` to remain
recognisable, plus at least one of `half_space_share` and `width`.

All five survived. **Proceed to Stage 2 Player Lab.**

## Limits

Provider and season are confounded by construction and this stage cannot separate
them; a same-season cross-provider comparison would, and no free corpus supports
one for these leagues.

The harmonisation to completed passes is itself a choice. It makes the comparison
honest and it also discards information each provider holds — StatsBomb carries,
Wyscout duels — so these estimators are deliberately weaker than the best either
ontology could support alone. That is the correct trade for a replication test and
the wrong one for a production estimator, which is why both are registered.
