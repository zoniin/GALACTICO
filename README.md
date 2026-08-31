# Galáctico

Football analytics is good at describing players and surprisingly weak at
answering decisions.

Who should start? Which role should a player occupy? What does this team lack?
Which signing actually fixes it? How should any of those answers change against a
particular opponent?

Galáctico is an attempt to turn football data into explicit, testable decision
models — and to publish the cases where those models fail.

That second part is not modesty. It is the design.

---

## The constraint everything else follows from

**Every number knows what kind of number it is.**

A pass count, an estimated progression score, and an optimiser's objective delta
are three different kinds of object. Most analytics tools render them identically,
which is how a model output ends up being read as a measurement.

Here, evidence class is a property of the value and it survives arithmetic:

```python
>>> passes = MetricResult.observed(64, source="statsbomb", definition="passes")
>>> projected = role_model.project(player, Role.DEEP_CONTROLLER)   # PREDICTIVE
>>> (passes + projected).evidence
<EvidenceClass.PREDICTIVE: 3>
```

Composition takes the *weakest* input. There is no operation in this codebase
that can launder a prediction into an observation.

Seven classes: `OBSERVED`, `DERIVED`, `ESTIMATED`, `PREDICTIVE`, `OPTIMIZED`,
`HEURISTIC`, `EXPERIMENTAL`. Uncertainty propagates alongside — element-wise when
two values come from the same bootstrap replicate set, by quadrature otherwise,
and the fallback records that it assumed independence, because for metrics derived
from the same events that assumption is usually false.

And precision follows the uncertainty rather than the float:

```python
>>> progression.render()
'78 ± 6'          # not 78.4327
>>> finishing.render()
'insufficient signal'
```

---

## Three worlds

**LIVE** — current football, centred on Real Madrid 2026/27. Aggregate player
data from a paid feed, plus free official sources including UEFA's physical
metrics. It sacrifices granularity where it must and never manufactures what it
does not have.

**LAB** — the scientific core. Event-level corpora where metric development,
reliability testing, backtesting and validation actually happen. Real Madrid
2017/18 is the flagship, because its central selection question — the BBC front
three against an Isco-led shape — is both genuinely contested and retrospectively
evaluable. A 2026/27 optimal XI is neither.

**VISION** — team geometry recovered from broadcast video. Not a replacement for
event data. Line height, width, compactness, block type — the things that survive
averaging over eleven players, feeding opponent characterisation.

Between LIVE and LAB sits **the Bridge**: can lower-granularity aggregates
reconstruct the richer profile? That is a research question with a measurable
answer, not an assumption. Where the answer is no, LIVE does not show the metric.

---

## What is built

Stage 0 is complete and tested.

| Component | State |
|---|---|
| Evidence algebra and provenance DAG | done, 24 tests |
| Metric registry with content-addressed versions | done |
| Cross-provider comparability enforcement | done |
| Role taxonomy with fuzzy membership | done |
| Reliability gate and empirical-Bayes shrinkage | done |
| Expected threat, fitted and validated | done |
| Licence posture enforced in code + CI guard | done |
| Ingestion, optimiser, bridge, vision | not started |

```bash
make install
make check      # licence guard, lint, 67 tests
```

---

## Findings so far

These came out of the research that preceded the code, and they shaped it.

- **Expected threat reaches split-half `ρ = 0.89`; VAEP reaches `0.25`.** xT is
  the value primitive. VAEP is not implemented.
- **The player × role interaction is at most 9% of variance**, and
  indistinguishable from zero for anything shooting-related, measured across 1,517
  matches and 486 role-movers. Persistence beats a role-mean baseline on all ten
  per-90 metrics tested. Role fit is real, small, and mostly mechanical.
- **The single optimal XI is not statistically identified.** A 200-replicate
  bootstrap leaves three to five of eleven players above 90% selection frequency.
  So the output is a stable core and a set of contested slots.
- **Pairwise chemistry is unidentifiable.** 2,461 of 2,689 distinct starting XIs
  in the corpus appear exactly once.
- **Finishing, pressing and defensive coverage are absent from the metric
  registry**, and a test asserts they stay absent.

See [`DECISIONS.md`](DECISIONS.md) for what was decided and what would reverse it,
and [`KNOWN_LIMITATIONS.md`](KNOWN_LIMITATIONS.md) for what this cannot do.

---

## Documents

[VISION](VISION.md) · [ARCHITECTURE](ARCHITECTURE.md) ·
[METRICS](METRICS.md) · [VALIDATION](VALIDATION.md) ·
[DATASETS](DATASETS.md) · [LICENSING](LICENSING.md) ·
[RESEARCH QUESTIONS](RESEARCH_QUESTIONS.md) · [ROADMAP](ROADMAP.md) ·
[DECISIONS](DECISIONS.md) · [KNOWN LIMITATIONS](KNOWN_LIMITATIONS.md)

---

## Licence

MIT, for the code. The repository contains no football data and never will —
corpora are downloaded at runtime into a gitignored cache under the terms each
provider sets. See [LICENSING.md](LICENSING.md); a CI guard enforces it.
