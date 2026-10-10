# Metrics

Generated blocks below come from the construct registry. Interpretation around
them is hand-written. Documentation drifted from the code three times before this
file was made to derive its state; see
[M-02](docs/research/M-02-definition-code-divergence.md).

Regenerate with `python scripts/generate_docs.py`.

<!-- generated:counts -->
**11 proposed. 8 tested. 5 survive.**

2 rejected, 1 research-only, 3 proposed but not yet through the lifecycle.
<!-- /generated:counts -->

## What ships

<!-- generated:claims -->
- **Progression** — Realised possession value added through territorial advancement.
- **Progression per action** — Efficiency of territorial advancement, independent of ball-touching opportunity.
- **Chance creation** — Creating shooting opportunities for team-mates, weighted by threat added.
- **Half-space pass-origin share** — Share of completed passes originating in the defined half-space channels.
- **Wide-channel pass-origin share** — Share of completed passes originating in the defined wide channels.
<!-- /generated:claims -->

<!-- generated:constructs -->
| Construct | Family | Denominator | Minutes floor | External replication |
|---|---|---|---:|---|
| `progression` — Progression | quality | per 90 minutes | — | robust with shift |
| `progression_per_action` — Progression per action | quality | completed passes | — | robust with shift |
| `chance_creation` — Chance creation | quality | per 90 minutes | 1800 | robust with shift |
| `half_space_share` — Half-space pass-origin share | style | completed passes | — | robust with shift |
| `width` — Wide-channel pass-origin share | style | completed passes | — | robust |
<!-- /generated:constructs -->

<img src="docs/assets/statsbomb/statsbomb-logo.png" alt="StatsBomb" width="170">

Data source: **StatsBomb** open data, read locally under the StatsBomb Public Data
User Agreement. Three things on this page are analysis formed from StatsBomb data and
carry the StatsBomb logo as clause 1.4 of that agreement requires: the
external-replication column of the table above, and the StatsBomb row and the
comparison of the two published curves under "Chance creation is estimator-gated",
all from [Stage 1C](docs/research/STAGE-1C-EXTERNAL-REPLICATION.md); and the Metronome Fit
conclusion under "What does not ship", from
[E-01](docs/research/E-01-metronome-fit.md). No StatsBomb data is in this repository,
and no machine-readable table derived from it is in the tree. The StatsBomb-side
figures printed here are published analysis.

Quality and style are separate families rendered in separate panels. A player
whose passes originated wide is not thereby better than one whose did not, and a
UI that sorts on a style axis makes a claim the data does not support.

### The spatial constructs are descriptive

`half_space_share` and `width` measure where completed passes **originated**.
Position is CONSTITUTIVE for them: deployment is part of the measurement, not a
confound removed from it. They are named after what enters the numerator for that
reason.

Three different spatial questions, only the first of which is shipped:

| Question | Shipped |
|---|---|
| Where did the player's actions occur? | yes — these constructs |
| Where, relative to comparable roles? | partly — the role-population reference |
| Given deployment and opportunity, does he occupy the zone unusually often? | **no** |

The third is what "preference" would have to mean, and it is
[E-04](experiments/preregistered/E-04-conditional-spatial-tendency/preregistration.md),
unrun. Verticality was rejected because its behavioural reading vanished under
conditioning; these survive only because their claim is narrow enough to be true.

The interface shows two references and calls neither an expected value:

- **Pitch-area reference** — what share of the pitch's width the channel occupies.
  Wide is 42%, the half-spaces 32%, the centre 26%. A 42% wide-origin share is no
  departure at all.
- **Comparable-role median** — what players in the same broad position actually did.

## Executable definitions

Both the number and the sentence are derived from one specification object, so a
declaration cannot disagree with its implementation. The fingerprint hashes the
structure: change what is computed and stored artifacts invalidate whether or not
anyone bumps a version.

<!-- generated:fingerprints -->
| Construct | Definition | Fingerprint |
|---|---|---|
| `progression` | sum of positive xT gain over completed passes, per 90 minutes | `582eb5f10997` |
| `progression_per_action` | sum of positive xT gain over completed passes, per completed passes | `954dfa834164` |
| `chance_creation` | sum of xT delta over completed passes flagged key pass, per 90 minutes | `4ba70c496930` |
| `half_space_share` | count over completed passes starting in the half-space channels, per completed passes | `434485dcd76e` |
| `width` | count over completed passes starting in the wide channels, per completed passes | `a40c90db10d5` |
<!-- /generated:fingerprints -->

## What does not ship

<!-- generated:rejected -->
| Construct | Status | Why |
|---|---|---|
| `ball_retention` | rejected | Too similar to ordinary pass completion |
| `verticality` | rejected | Mostly explained by starting field position |
| `metronome_fit` | research only | Construct validity unresolved after preregistered replication |
<!-- /generated:rejected -->

Three different failure classes, and the differences matter more than the
failures:

- **Metronome Fit** failed the confound audit — measuring something other than it
  claimed.
- **Ball retention** failed incremental information — measuring the right thing,
  redundantly.
- **Verticality** failed construct interpretation — mostly geometry wearing a
  behavioural name.

Also absent, from earlier stages: **finishing** (approximately zero year-over-year
correlation even at a hundred-shot floor), **pressing** and **press resistance**
(depend on a provider-specific pressure flag that exists only in StatsBomb), and
**defensive coverage** as a quality axis (defensive volume counts have
year-over-year r below 0.50).

A test asserts none of these can reach a profile.

## Chance creation is estimator-gated

Reliability rises with minutes, so the floor belongs to the estimator rather than
the construct. A reliability belongs to the pool it was taken over, and each
figure below is given with its pool:

| Estimator | Minutes floor | Reliability at floor | Pool |
|---|---:|---:|---|
| `wyscout_event_v1` | 1,800 | 0.725 | as published in Stage 1B: every player with the minutes, goalkeepers included |
| `wyscout_event_v1` | 1,800 | 0.699 | the declared population, outfield players ([M-08](docs/research/M-08-reliability-pool.md)) |
| `statsbomb_event_v1` | 450 | 0.821 | as published in Stage 1C: every player with the minutes, goalkeepers included |

Player Lab serves the curve of the second row. On it the reliability at the floor
is under the 0.70 number threshold, and whether the floor should rise is an open
owner decision. The two published curves were taken over pools of the same kind.
On them the axis is more reliable under StatsBomb at 450 minutes than under
Wyscout at 2,250, which Stage 1C read as key-pass tag noise rather than event
sparsity. The StatsBomb curve has not been recomputed on the declared population,
so no figure of it stands beside the second row. Below the floor the interface
renders INSUFFICIENT SIGNAL and the explorer withholds the value — the same number
cannot be both unavailable and published.
