# Roadmap

Running status, updated as stages land.

## Stage 0 - Foundations - COMPLETE

- [x] Research council reports, provider matrix, licensing map
- [x] Evidence algebra with provenance DAG (`domain/provenance.py`)
- [x] Metric registry, content-addressed versions, comparability guard
- [x] Role taxonomy with fuzzy membership
- [x] Reliability gate and empirical-Bayes shrinkage
- [x] Expected threat, validated against a synthetic pitch
- [x] Licence posture enforced in code plus a CI guard
- [x] Repository skeleton, tooling, 67 tests passing
- [x] Ten foundation documents

## Stage 1 - Historical event laboratory - MOSTLY COMPLETE

- [x] Pappalardo ingestion, reproducible via `scripts/fetch_pappalardo.py`
- [x] Provider-neutral action schema; Wyscout quirks terminate at the adapter
- [x] Corpus audit: La Liga 2017/18 clean on every structural check
- [x] xT fitted on real data, turnover absorbing state added, grid sensitivity run
- [x] Seven candidate axes through reliability, confound audit and a baseline battery
- [x] Metric lifecycle and confound taxonomy in code
- [x] Precision policy centralised
- [x] Stage 1 measurement report published, including the rejection
- [ ] StatsBomb 2015/16 ingestion (local tier) - not started
- [ ] Internal derivation lineage (RAW_OBSERVATION -> ... -> COMPOSITE) - not started
- [ ] Remaining four Pappalardo leagues ingested - not started

Exit criteria: 15 of 15 met.

## Stage 1B - Replication and reconnaissance - COMPLETE

- [x] All five domestic leagues ingested; audits pass
- [x] Gauntlet run independently per league, thresholds frozen
- [x] Replication status per metric (REPLICATED / PARTIAL / FAILED)
- [x] Ball-retention rejection independently confirmed 5/5 (E-03)
- [x] Verticality field-position issue resolved: 83% is geometry, rejected
- [x] Chance-creation instability diagnosed as sample size; curve published
- [x] E-02 executed exactly as preregistered - did NOT reject; RESEARCH_ONLY
- [x] Internal derivation taxonomy implemented
- [x] xT failure postmortem preserved (M-01) with independent invariants
- [x] FotMob reconnaissance complete; no endpoint touched, no adapter built
- [x] LIVE data gap matrix and spend analysis

Outstanding: cross-provider replication against StatsBomb 2015/16, and the
entity-resolution layer (specified, not yet built).

## Stage 1C - External replication - COMPLETE (11 of 12)

Wyscout 2017/18 -> StatsBomb 2015/16. Provider and season shift together.

- [x] StatsBomb populations audited from the manifest: 380/380/380/377, 20 teams each
- [x] xT refit under StatsBomb; turnover semantics re-checked
- [x] Provider semantic mapping audit (6 concepts, one NOT_COMPARABLE)
- [x] All five surviving constructs externally evaluated
- [x] External verdicts recorded on every construct
- [x] chance_creation minutes curve independently estimated under StatsBomb
- [x] Construct vs estimator represented in code
- [x] Entity resolution foundation with regression tests
- [ ] UEFA physical-data status - verification still running
- [x] 129 tests pass
- [x] Licence guard passes, now as a pre-commit hook
- [x] Working tree clean

Result: nothing failed. Reliability equal or better under StatsBomb on every
axis, confounding lower on every axis. Stage 2 gate passed.

## Stage 2 - Player Lab - NEXT

Four axes as numbers, one gated by an estimator-specific minutes floor. The
surface should represent what is actually known, including the rejections -
2 rejected, 1 research-only - rather than filling five radar slots.

## Stage 2 - Player Lab v0
Quality and style panels, intervals, shrinkage, role-normalised percentiles.

## Stage 3 - XI optimiser
CP-SAT, role slots, soft constraints with deficit variables, primary structural
weakness as the largest penalised deficit, sensitivity by re-solve.

## Stage 4 - Uncertainty
Bootstrap, stable core, contested slots, objective distributions.

## Stage 5 - LIVE
Real Madrid 2026/27 on a paid aggregate feed plus UEFA physical metrics.

## Stage 6 - The Bridge
Calibrated on the four complete women's league seasons, plus NWSL 2023 present in both StatsBomb
open data and API-Football's free window. Promote only what passes.

## Stages 7-10
Opponent Lab, Transfer Lab, Role Fit research, embeddings and functional
similarity.

## Stages 11-12 - VISION
Benchmark first, product second. Measure calibration, tracking, positional error
and team-shape error before anything renders.

## Stage 13+
Metronome Fit, transfer retrospectives, tactical presets, squad construction,
robust optimisation, time machine, command layer.

