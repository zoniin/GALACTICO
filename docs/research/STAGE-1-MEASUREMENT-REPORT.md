# Stage 1 — which football concepts survive measurement

**Corpus:** Pappalardo/Wyscout, La Liga 2017/18 (CC BY 4.0).
380 matches · 20 teams · 628,659 actions · 10,555 appearances · 345 players over
900 minutes.
**Status: exploratory.** Thresholds were fixed before the run; the confound
variables were not chosen after seeing results. But this is one league, one
season, one provider, and nothing here is confirmatory.

---

## The corpus audit, first

No metric research begins on an unaudited corpus.

| Check | Result |
|---|---|
| Coordinates outside the unit square | 0 |
| Matches with anomalous action volume | 0 |
| Impossible minute totals | 0 |
| End coordinate absent | 0.4% |
| Outcome not judged by the provider | 12.6% |

Action mix: 50.7% pass, 27.4% duel, 7.7% touch, 6.1% set piece, 1.3% shot. The
12.6% unjudged figure is almost entirely duels and touches, which Wyscout does not
score for accuracy. That is a provider fact, not missing data, and it is why
`success` is nullable in the neutral schema rather than defaulting to `False`.

---

## Expected threat, and a bug real data exposed

The first fit produced a nearly flat surface — the own box and the centre circle
within 0.0001 of each other. The cause was structural: with `p_move + p_shot = 1`
in every cell the Markov chain has no absorbing state except a shot, so every
possession eventually produces one and the fixed point is uniform. A flat surface
means no pass has value, which would have silently zeroed every progression
number downstream.

Supplying turnovers as an absorbing state fixes it. The surface now rises
monotonically:

| Own third | Middle third | Final third | Opposition box |
|---:|---:|---:|---:|
| 0.0071 | 0.0152 | 0.0619 | 0.1216 |

A ~9× gradient, converging in 46 iterations. Synthetic tests had passed the broken
version, because the synthetic generator also had no turnovers. That is worth
recording: the test suite was self-consistent and wrong, and only real data caught
it.

---

## The gauntlet

Seven candidate axes. Reliability is odd/even split-half, Spearman-Brown
corrected, over players with 900+ minutes. Confound R² is against touch volume
plus team identity. "Closest baseline" is the strongest correlation with any of
eight deliberately stupid statistics: touches, passes, completion %, mean x, mean
y, mean pass length, shots, minutes.

| Axis | r | 90% CI | Confound R² | ρ after | Top-12 kept | Closest baseline | \|r\| | Status |
|---|---:|---|---:|---:|---:|---|---:|---|
| `progression` | 0.89 | 0.87–0.91 | 0.30 | 0.79 | 9/12 | touches/90 | 0.59 | **SHIP** |
| `progression_per_action` | 0.86 | 0.84–0.88 | 0.06 | 0.95 | 12/12 | completion % | 0.53 | **SHIP** |
| `half_space_share` | 0.96 | 0.96–0.97 | 0.04 | 0.97 | 9/12 | completion % | 0.47 | **SHIP** (style) |
| `width` | 0.99 | 0.98–0.99 | 0.05 | 0.97 | 5/12 | mean x | 0.52 | **SHIP** (style) |
| `verticality` | 0.97 | 0.97–0.98 | 0.05 | 0.96 | 11/12 | mean x | **0.90** | **BAND** |
| `chance_creation` | 0.60 | 0.54–0.65 | 0.15 | 0.87 | 9/12 | mean x | 0.48 | **BAND** |
| `ball_retention` | 0.90 | 0.88–0.91 | 0.27 | 0.84 | 4/12 | completion % | **0.95** | **REJECT** |

### `ball_retention` is rejected, and the machinery caught it

Reliability 0.90. Excellent by every standard this project had before E-01. And
its **pre-declared negative control was "must not be a near-copy of raw pass
completion percentage."** It correlates with pass completion at **0.95**.

The whole justification for the axis was threat-weighting: losing the ball in your
own box should count for more than losing it on the touchline. Threat-weighting
moves the number by about 5% of its variance. Only 4 of the top 12 survive
confound adjustment.

So it measures pass completion, and pass completion already exists and is simpler.
Ship that instead, under its own name. This is the second confirmed instance of
the E-01 pattern — high reliability, plausible leaderboard, no incremental
information — and it was caught by a control written down before the number
existed rather than by intuition afterwards.

### `verticality` is flagged rather than rejected

Its declared negative control was mean *pass length*, and it passes that. But it
correlates 0.90 with mean *x* — where the player operates on the pitch. That
confound was not pre-declared, so rejecting on it now would be exactly the
post-hoc reasoning E-01 was criticised for. It ships as a band with the
correlation stated, and the pre-declared control for the next run is mean x.

### Why `progression` ships at confound R² = 0.30 and `progression_per_action` at 0.06

Because the claims differ. `progression` declares touch volume as a **context**
variable — opportunities on the ball are partly constitutive of realised
progression, so a moderate correlation is expected and is not evidence against.
`progression_per_action` declares it as a **nuisance**: the rate exists precisely
to remove opportunity, so *any* substantial correlation would be a failure. It
shows 0.06, keeps 12 of its top 12 through adjustment, and is the strongest result
in the table.

Same statistic, opposite readings, decided by the claim rather than the threshold.
There is deliberately no `if confound_r2 > t: reject` rule in the codebase.

---

## Face validity

Never used to fit or tune anything. A check, and a weak one — E-01 exists because
a perfect-looking leaderboard was wrong.

**`progression`, per 90:** Marcelo, Isco, Juncà, Lucas Vázquez, Messi, Iniesta,
Carvajal, Asensio. Attacking full-backs and creators, which is what a volume
progression measure should surface in 2017/18.

**`progression_per_action`:** Iván Alejo, Portu, Juncà, Lucas Vázquez, Marcelo,
Andreas Pereira, Messi, El Zhar. Less famous, and that is the expected behaviour
of a rate rather than a fault — a player with 50 touches per 90 who gains threat
on a high share of them ranks above one with 116 touches who does not. Both axes
ship, labelled differently, because they answer different questions.

---

## What ships

Four axes as numbers, two as bands, one rejected. The original specification had
eleven named traits; after two gates and a baseline battery, five survive as
usable and two of those are style descriptors that are never ranked.

`ball_retention` is removed from the metric registry. Its rejection is a result,
and `docs/research/` is where results live.

---

## Limits of this report

One provider, one league, one season. Four StatsBomb leagues from 2015/16 are not
four replications of this and neither would five Wyscout leagues be — same
provider, same annotation regime.

Split-half over odd/even matches within a season measures consistency, not
season-to-season stability, and the two differ substantially for football metrics.

The 900-minute floor is an uncontrolled selection: it conditions on playing time,
which is itself an outcome of the quality being measured.

And the confound set is touch volume plus team. Position was not included, because
position is constitutive for the style axes and would have removed the construct;
that decision is defensible and is also the one most worth attacking.
