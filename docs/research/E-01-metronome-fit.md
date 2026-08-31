# E-01 — Is "Metronome Fit" a real construct?

**Status: does not ship as a scored metric.**
**Corpus:** StatsBomb 2015/16, La Liga (380) + Premier League (380), 21,018
player-match rows.

---

## Why this one matters more than the result

Metronome Fit passed every check Galáctico had.

Split-half reliability, Spearman-Brown corrected: **0.94–0.95**. That is higher
than expected threat's 0.89 — the most reliable thing measured on this corpus.

Face validity: the La Liga leaderboard read Kroos, Mascherano, Iniesta, Piqué,
Modrić, Busquets. The Premier League leaderboard read Cazorla, Fàbregas,
Schweinsteiger, Yaya Touré, Carrick.

If you had asked a football person to name the metronomes of that era, they would
have produced approximately that list. Reliability said the measurement was
repeatable. Face validity said it matched expert intuition. Both were true.

It was measuring touch volume.

Among deep players (CB, DM, CM) the index correlated **r = 0.927** with raw touch
count in both leagues, and touch volume plus team fixed effects explained **89.5%**
(La Liga) and **90.3%** (Premier League) of its variance. The three components
carrying the actual circulation-hub meaning — involvement across possession
phases, pass volume, reception availability — were 79–87% explained by log touch
volume alone. Team identity by itself explained 43–47% of reception availability.

After removing touch volume and team, **three of the top twelve survived** in La
Liga and four in the Premier League, and rank correlation with the original
leaderboard fell to **ρ = 0.28 / 0.33**.

The metric was more reliable than anything else available and had better face
validity than anything else available, and it was a confound wearing a football
name. That is the lesson: **reliability tells you a measurement is repeatable, not
what is being repeated.**

This result is why `galactico/reliability/confound.py` exists. The reliability gate
is now the first of two.

---

## What survives, and it is not a metronome

Something does remain after residualising, and it is reliable. It is a
deep-distribution and long-range-passing axis, and its leaderboard is centre-backs.
That is a legitimate style axis. It is not the construct the name promised, and
naming it "metronome" would be the same error one layer down.

---

## Component-level answers

**Tempo modulation is not a player-level construct.** Every published measure of
tempo, directness or pace of play is defined at team or sequence level. A
player-level signal is measurable and highly reliable, but inspection shows it is
85% StatsBomb carry duration plus an integer-second gap whose median is exactly
zero. It measures positional pressure and available space, not rhythm control —
and being carry-derived makes it provider-definitional in exactly the way carries
already are.

**Switch frequency is stable** (0.865 at player level) but the flag is a
deterministic provider threshold, so it is not comparable across providers. Same
category as carries; same treatment.

**No published decomposition finds a metronome factor.** Every dimensionality
reduction of passing and possession features in the literature returns *location*
and *direction* components — spatial structure, not circulation control. Our own
decomposition agrees: a metronome-looking factor emerges, and it is the general
involvement axis.

---

## Where this writeup is weaker than it looks

Recorded because the project claims to publish failures, and a failure that hides
its own methodological problems is not much of a publication.

**The pre-registered decisive test passed.** The adjusted index retained
split-half 0.854–0.871. The kill verdict was then argued on criteria selected
after seeing the results. That is HARKing, and it happened inside a report whose
own flagship recommendation was a pre-registered kill gate.

**One proposed kill rule has a ~100% false-positive rate.** "Fail if parallel
analysis retains two or more factors" fires on raw unresidualised data in every
league and subset tested. It cannot serve as an intake gate.

**The recommended fix does not work.** Per-possession denominators were proposed
to remove team dominance. On the same data they do not: team η² on reception
availability goes 0.466 → 0.473 in La Liga, marginally *worse*, and 0.428 → 0.397
in the Premier League. The "0.47 → 0.09" figure quoted in support came from a
different procedure entirely — residualising on log touch volume.

**The headline r = 0.927 is inflated by roughly 0.03** because the index was
z-scored against a pool it was not evaluated on.

**Four StatsBomb 2015/16 leagues are not four replications.** Same provider, same
season, same annotation regime. Two leagues agreeing is weaker evidence than it
appears.

---

## Verdict

The confound is real, large, and replicated across two leagues. That part stands.

The *kill* was reached post-hoc, so the honest status is: **not shipped, on strong
but partly post-hoc grounds, pending a pre-registered replication on a different
provider and season.** The construct is not in the metric registry, and it is not
in the optimiser.

If someone wants to rescue it, the bar is a pre-registered test on the Pappalardo
2017/18 corpus with thresholds fixed in advance, showing that something survives
removal of touch volume and team identity, and that whatever survives has a
leaderboard a football person recognises as metronomes rather than centre-backs.
