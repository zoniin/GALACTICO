# E-02 — Metronome Fit, confirmatory: results

**Serie A 2017/18 · 306 outfield players over 900 minutes · 293 in the reliability
sample.** Run exactly as preregistered. Thresholds were not touched.

## Results against the frozen tests

| Test | Value | Threshold | Verdict |
|---|---:|---|---|
| T1 adjusted reliability, lower bound | **0.810** | ≥ 0.70 | PASS |
| T2 confound R² | **0.628** | ≤ 0.60 | FAIL |
| T3 ordering ρ, raw vs adjusted | **0.595** | ≥ 0.50 | PASS |
| T4 top-12 overlap | **6 / 12** | ≥ 6 | PASS |
| T5 closest simple baseline \|r\| | **0.867** (passes/90) | ≤ 0.85 | FAIL |

## Decision, by the frozen rule

The rule was: REJECT if T2 fails **and** at least one of T3 or T4 fails.

T2 failed. T3 and T4 both passed.

**DECISION: RESEARCH_ONLY.**

**E-02 does not reject Metronome Fit.**

## What this means, and what it does not

E-01 killed the construct. It did so on criteria selected after seeing results,
while its own pre-registered decisive test passed. E-02 was written to settle that
properly, on a different provider and a different season.

Run properly, the construct survives rejection. It is confounded — 62.8% of its
variance is touch volume and team, just past the ceiling — and it duplicates
passes per 90 at 0.867, just past that ceiling too. But the ordering holds at
ρ = 0.60, half the leaderboard survives adjustment, and the adjusted index is
still reliable at 0.81.

That is a genuinely mixed result, and the preregistration was written to be able
to say so instead of forcing a verdict.

**Three of the five tests land within a whisker of their boundary**: 0.628 against
0.60, exactly 6 against a floor of 6, 0.867 against 0.85. A slightly different
switch threshold or minutes floor would flip at least one. That fragility is
itself the finding, and it is exactly what E-01's post-hoc reasoning obscured by
reaching a clean-looking kill.

## The leaderboards

**Raw:** Jorginho, Hamšík, Albiol, Brozović, Koulibaly, Pjanić, Biglia, Barzagli,
Borja Valero, Insigne, Mário Rui, Lucas Leiva.

**Adjusted for touch volume and team:** Brozović, Jorginho, Sagna, Biglia,
Hamšík, Cigarini, Viviani, Barzagli, Magnanelli, De Rossi, Borja Valero, Sensi.

The adjusted list is the more interesting one. Two centre-backs drop out; Cigarini,
Magnanelli, Viviani and Sensi come in — deep midfielders at unfashionable clubs,
exactly the players a touch-volume-driven index would bury. Jorginho and Brozović
survive both. That is not what a pure confound looks like.

Face validity is a weak check and E-01 is the reason we say so. It is recorded,
not relied on.

## Project status

**Metronome Fit remains RESEARCH_ONLY.** It is not in the metric registry, it is
not in the optimiser, and it does not render.

It is **not** marked REJECTED_CONSTRUCT, because the preregistered rule did not
reject it, and overriding that now would reproduce E-01's error with more
ceremony.

The sequence stays permanent: E-01's exploratory failure, its HARKing disclosure,
this preregistration, and this outcome. A project that only preserves the
experiments confirming its priors is not doing this.

## What would settle it

A third experiment with a wider margin: more leagues, a pre-declared switch
threshold sensitivity analysis, and — the real question neither experiment
addresses — whether residualising on team removes genuine player influence, since
a circulation hub partly *creates* the possession dominance being adjusted away.

