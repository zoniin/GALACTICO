# Stage 1B — were the La Liga results football results?

**Corpus:** Pappalardo/Wyscout 2017/18, all five big-five leagues. 1,826 matches ·
98 teams · ~3.07M actions · 1,628 players over 900 minutes. CC BY 4.0.

The Stage 1 gauntlet was rerun without modification. Thresholds are the Stage 1
thresholds. Metric definitions are frozen. Negative controls were declared before
any league beyond Spain was computed. Nothing was retuned because a leaderboard
looked strange.

## Corpus audits

| | ESP | ENG | ITA | GER | FRA |
|---|---:|---:|---:|---:|---:|
| Matches | 380 | 380 | 380 | 306 | 380 |
| Actions | 628,659 | 643,150 | 647,372 | 519,407 | 632,807 |
| Players ≥ 900′ | 345 | 333 | 330 | 290 | 330 |
| Coordinates out of range | 0 | 0 | 1 | 2 | 0 |
| Anomalous match volumes | 0 | 0 | 0 | 0 | 0 |
| Impossible minutes | 0 | 0 | 0 | 0 | 0 |
| Outcome unjudged | 12.6% | 12.3% | 12.7% | 12.6% | 12.9% |

Three out-of-range coordinates across 3.07M actions. The unjudged share is stable
at 12.3–12.9%, consistent with it being a Wyscout annotation policy about duels
and touches rather than data loss.

## The replication matrix

| Axis | ESP | ENG | ITA | GER | FRA | r range | Replication |
|---|---|---|---|---|---|---|---|
| `progression` | SHIP | SHIP | SHIP | SHIP | SHIP | 0.82–0.90 | **REPLICATED** |
| `progression_per_action` | SHIP | SHIP | SHIP | SHIP | SHIP | 0.80–0.86 | **REPLICATED** |
| `half_space_share` | SHIP | SHIP | SHIP | SHIP | SHIP | 0.96 | **REPLICATED** |
| `width` | SHIP | SHIP | SHIP | SHIP | SHIP | 0.99 | **REPLICATED** |
| `chance_creation` | BAND | REJ | BAND | REJ | BAND | 0.55–0.70 | PARTIAL |
| `ball_retention` | REJ | REJ | REJ | REJ | REJ | 0.87–0.90 | **FAILED** |
| `verticality` | REJ | REJ | REJ | REJ | REJ | 0.97–0.98 | **FAILED** |

**Answer to the question this stage existed to ask: four of seven were football
results.** Two were artefacts that happened to be reliable. One is genuinely
context-dependent.

`progression_per_action` is the strongest axis in the project: reliability
0.80–0.86, confound R² 0.04–0.08 against touch volume and team, and 9–12 of its
top 12 surviving adjustment in every league.

## The two failures

**`ball_retention`** correlates 0.93–0.95 with plain pass completion in all five
leagues. Reliable, honest, and redundant. Written up separately as
[E-03](E-03-ball-retention-incremental-value.md) because it fails at a different
lifecycle stage than Metronome Fit did — incremental information rather than
confound audit — and that distinction is worth preserving.

**`verticality`** was BAND in Stage 1, flagged rather than rejected because its
0.90 correlation with mean pitch position was not a pre-declared control.
Replication settles it: |r| with mean x is 0.90–0.92 in every league, past the
frozen 0.85 ceiling, so it is rejected by a threshold that already existed rather
than one invented for it.

The follow-up diagnostic asked whether it is anything beyond geometry:

| | ESP | ENG | ITA | GER | FRA |
|---|---:|---:|---:|---:|---:|
| Raw \|r\| with mean x | 0.90 | 0.92 | 0.91 | 0.91 | 0.91 |
| Within field-position decile | 0.23 | 0.27 | 0.26 | 0.28 | 0.23 |
| Residual variance retained | 0.20 | 0.16 | 0.18 | 0.17 | 0.17 |

So roughly **83% of verticality is where the player receives the ball**, and
within a field-position stratum the relationship largely disappears. About 17%
survives, and it is stable across leagues, which means there is a real residual
behaviour in there.

That residual is **not** rescued now. Doing so would be exactly the post-hoc
reasoning E-01 was criticised for. A field-position-conditioned verticality is a
legitimate candidate for a future preregistration, with mean x as a declared
control from the start.

## Chance creation: the instability is sample size

Reliability was investigated rather than smoothed. Pooled across all five leagues,
varying only the minutes floor:

| Minutes floor | n | r | Lower bound |
|---:|---:|---:|---:|
| 450 | 1,903 | 0.544 | 0.517 |
| 900 | 1,551 | 0.625 | 0.599 |
| 1,350 | 1,204 | 0.683 | 0.657 |
| 1,800 | 870 | 0.725 | 0.697 |
| 2,250 | 572 | 0.756 | 0.725 |

Clean and monotone. The instability is not definitional, not role heterogeneity,
and not grid discretisation — it is that chance creation is a sparse action and
900 minutes is not enough of them.

This converts directly into product behaviour:

> **Chance creation needs roughly 1,800 minutes before Galáctico will show it as a
> number.** Below that it renders as a band, and below 900 minutes it does not
> render at all.

That is more useful than a metric that pretends to be stable at 400 minutes, and
it is the kind of statement only a reliability-versus-minutes curve can support.

## Why the xT surface is fitted per league

Leagues genuinely play differently, and a pooled surface would impose Serie A's
shot geography on the Bundesliga. The cost is that absolute xT values are not
comparable across leagues — which is why replication is judged on reliability,
confounding and ordering rather than on distributional agreement. Making the
distributions align would have meant normalising away a real football difference
to make a chart look tidy.

## What ships after Stage 1B

**Four axes as numbers:** `progression`, `progression_per_action`,
`half_space_share`, `width`. Two of the four are style descriptors and are never
ranked.

**One as a band, conditional on minutes:** `chance_creation`.

**Two closed:** `ball_retention`, `verticality`.

The original specification named eleven traits. Seven were tested seriously. Four
survived five leagues.

## Limits

Same provider and same season across all five leagues. Five Wyscout 2017/18
leagues are better evidence than one, and they are still not five independent
replications — a shared annotation regime is a shared assumption. Cross-provider
replication against StatsBomb 2015/16 is the honest next test, and it is not done.

Split-half over odd/even matches measures within-season consistency, not
season-to-season stability. The 900-minute floor remains an uncontrolled selection
on playing time.
'''
