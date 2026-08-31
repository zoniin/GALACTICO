# E-02 — Metronome Fit, confirmatory

**Committed before any E-02 analysis was run. Nothing below may change once the
first result is observed.**

E-01 found strong evidence that Metronome Fit is a touch-volume confound, but
reached its kill verdict on criteria selected after seeing results, while its own
pre-registered decisive test passed. That makes E-01 exploratory. This is the
confirmatory replication.

---

## 1. Hypothesis

**H0 (the construct exists):** after removing touch volume and team identity,
Metronome Fit retains a reliable, distinct ordering of players that a football
observer would recognise as deep circulation control.

**H1 (the construct is a confound):** what remains after adjustment is not
recognisable as circulation control, and the ordering does not survive.

---

## 2. Dataset

Pappalardo/Wyscout 2017/18 — a **different provider and a different season** from
E-01, which used StatsBomb 2015/16. Same-provider replication is not replication.

Primary: **Italy (Serie A)**, 380 matches. Not used in any Galáctico analysis to
date, and deliberately not La Liga, which the Stage 1 report has already explored.

Secondary, reported separately and not pooled: England, Germany, France.

## 3. Inclusion and exclusion

- Players with **≥ 900 minutes** in the competition-season.
- Outfield players only; goalkeepers excluded.
- Open-play actions only. Set pieces excluded.
- No exclusion on team, position, age or club strength.

The 900-minute floor conditions on playing time, which is itself an outcome of
ability. This is a known uncontrolled selection and is not corrected for; it is
recorded so it is not later presented as a discovery.

## 4. Metric definition — frozen

Metronome index = the mean of z-scores, standardised within the analysis pool, of:

1. Pass volume per 90
2. Share of team possessions the player touches
3. Pass completion percentage
4. Share of completed passes that are backward or square
5. Switch frequency per 90 (completed passes with lateral displacement > 0.35)
6. Reception count per 90
7. Share of actions in the middle third
8. Inverse of dangerous-loss rate

No component may be added, dropped or reweighted after the first result.

## 5. Confounds — frozen

- **Touch volume** (count of on-ball actions), classified **NUISANCE**. The
  construct claims rhythm control, not involvement, so shared variance is
  damaging.
- **Team identity** (one-hot, one level dropped), classified **CONTEXT**.
  Reported both adjusted and unadjusted; team dominance is part of the
  environment, and removing it entirely is itself a choice.

Adjustment is OLS residualisation on `[log(touches), team one-hot]`, in that
single specification. Per-possession denominators are **not** used: E-01's own
data showed they leave team η² unchanged or slightly worse (0.466 → 0.473).

## 6. Tests and thresholds — frozen

| Test | Threshold | Fails if |
|---|---|---|
| T1 Reliability of adjusted index | split-half Spearman-Brown, lower bound of 90% CI | < 0.70 |
| T2 Variance explained by confounds | R² of `[log(touches), team]` on the raw index | > 0.60 |
| T3 Ordering stability | Spearman ρ between raw and adjusted ordering | < 0.50 |
| T4 Leaderboard survival | top-12 overlap, raw vs adjusted | < 6 of 12 |
| T5 Incremental information | \|r\| with the closest single simple baseline | > 0.85 |

Baselines for T5, fixed: touches/90, passes/90, pass completion %, mean x,
mean y, mean pass length, minutes.

**Parallel analysis on the residual factor matrix is not a test.** E-01 proposed
it and it fires on raw unadjusted data in every league and subset checked, giving
it a false-positive rate near 100%.

## 7. Decision rule — frozen

- **REJECT** the construct if **T2 fails and at least one of T3 or T4 fails.**
- **SHIP_WITH_BAND** if T2 passes but T5 fails — reliable and real, but not
  adding enough over a simpler statistic to justify the name.
- **SHIP** only if all five pass.
- Any other combination is **RESEARCH_ONLY** and is reported without a verdict.

## 8. Interpretation language — frozen

If rejected, the finding is stated as: *"the proposed index is substantially
explained by touch volume and team identity, and the ordering that remains does
not correspond to the claimed construct."*

It is **not** stated as "metronomes do not exist" or "tempo control is not real."
The experiment tests one operationalisation on two corpora. It does not test the
football concept.

## 9. What would make this wrong

- Serie A 2017/18 may be unrepresentative.
- The eight components are one of many defensible operationalisations; a different
  one might survive.
- Residualising on team may remove genuine player influence on team style, since a
  circulation hub partly *creates* the possession dominance being adjusted away.
  This is the strongest objection to the whole design and is not resolved.

---

*Committed before running. Results in `results.json`, interpretation in
`analysis.md`. If either contradicts this document, this document wins.*
