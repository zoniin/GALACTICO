# Roadmap

Implementation status, checked against code, executable experiments and rendered
product. A working surface does not establish the validity of every decision claim.

## Verified complete: foundations and measurement laboratory

- Typed evidence/provenance, construct and estimator registry, comparability guards.
- Pappalardo ingestion and five-league replication; StatsBomb local-only ingestion
  and external replication. Provider and season change together in that comparison.
- Internal derivation lineage, identity-resolution foundation, reliability gates,
  executable feature specifications, xT implementation and independent invariants.
- Licensing guard in CI and pre-commit. UEFA model use is prohibited, not pending.

The surviving player constructs and their qualifications are recorded in the
[registry](galactico/domain/constructs.py) and the Stage 1 research reports.
Rejected constructs remain rejected; replication is not decision-utility validation.

## Player Lab: implementation frozen

The historical API and browser expose quality/style separately, estimator-specific
sample gates, uncertainty, comparison and scatter. The Stage 2 blocking statistical
defect was repaired: all players and constructs now use shared match-resampling
worlds, with identity checks and explicit missing exposure. Comparison and scatter
respect the same gates. See [M-04](docs/research/M-04-shared-match-worlds.md).

Automated and rendered-browser checks cover the release behavior. This freeze does
not claim an independent human football-review sign-off. Further cosmetic work is
not a prerequisite for the decision laboratory.

## Match Lab: historical v1 implemented

`/match` opens public Pappalardo matches: actual lineups, KEY/TACTICAL/ALL timeline,
shots, period-aware positive pass-xT flow, inferred passing network, team
pass-origin descriptors and player-match contribution vectors. Madrid's 38 league
matches are the default collection. Data availability and provenance are explicit.

No Wyscout xG is invented. Threat flow is not momentum. Recipients are inferred,
not directly observed. StatsBomb Match Lab and LIVE Match Lab are not shipped.

The first scalar candidates failed the incremental-meaning audit in Spain and
England: role standardization mostly renames positive pass xT. No overall match
rating ships. See [E-05](docs/research/E-05-match-score.md) and the
[capability matrix](docs/research/MATCH-INTELLIGENCE-CAPABILITY-MATRIX.md).

## XI Lab: experimental requirement model implemented

`/xi` offers pre-match Madrid snapshots before 8 April and 6 May 2018, with 4-3-3
and 4-3-1-2 slot templates. It finds assignments with the least declared structural
shortfall, not a universally best XI.

- Exact CP-SAT assignment, eligibility, locks/exclusions, BALANCE and SATISFY.
- Lexicographic worst then total normalized deficit; actual status, bounds,
  quantization and complete requirement inputs recorded.
- Editable minima, requirement ledger, server-derived change explanations and
  removal-sensitivity endpoint; candidate-injection primitive for future transfers.
- Strict prior-calendar-date events, xT fit, rates and threshold construction.
- Shared team-match worlds and equally optimal necessity/possibility checks.
  The browser's 12-world bands are exploratory, not calibrated selection chances.
- Independent exhaustive tiny-instance oracle, synthetic failure cases,
  temporal leakage checks and real browser coverage.
- Personnel-diverse equivalent-XI witnesses inside the certified shortfall optimum.
- Separate progression-under-explicit-hard-floors query, with conservative floor
  quantization and its own maximizing certificate. No inherited bootstrap/core or
  Pareto claim. [Contract](docs/research/XI-PROGRESSION-UNDER-FLOORS.md).

The May 6 snapshot has 16 eligible players under manual football rules and sample
gates. Fitness/suspension availability is unknown. Only progression and experimental
side-specific pass-origin rates enter; chance creation, rest defense and keeper
quality remain unmeasured. Historical rates need not survive changed deployment.

The 12-match development diagnostic averages **6.00/11** actual starters, losing
to the same-eligibility prior-minutes baseline at **6.83/11**. This is a thinking
aid, not evidence of superior selection. See [E-06](docs/research/E-06-lineup-requirements.md).

## Squad Lab and Transfer Lab: exact tools implemented, nothing validated

`/squad` and `/transfer` open a planning snapshot: Real Madrid at the end of the
2017/18 league season by default, any league club under the provider-position
rule. They state what follows from arithmetic on a declared, gated model and
nothing else. See [ADR-0020 to ADR-0023](DECISIONS.md).

- One exact kernel for the declared shortfall, equal to the XI solver's integers
  on real data at 9-25 ms per value against 130-3,000 ms. Snapshots for any club
  and cutoff date with byte parity for Madrid. League reference distributions of
  starting-XI sums.
- Slot depth with every drop attributed to the gate, the eligibility rule or a
  requirement, and the omitted players named.
- Absence stress for sets of one, two or (on confirmation) three players: worst
  sets with ties, sets that leave no fieldable XI and their minimal cores.
- The role brief: what an addition at a declared slot would have to supply.
- A gated candidate universe, exact forced-inclusion re-solves with possible and
  necessary membership, and the break-even carry-over fraction.
- Planning defaults to the progression requirement only; the side pass-origin
  requirements are an explicit experimental opt-in. Evidence classes are composed
  from the domain ladder and shown.
- Independent exhaustive oracles for every tool, pinned real-data regressions,
  corpus-free API tests, a copy guard on every served label and browser tests.

Not established by any of it: that the declared minima are the right identity,
that a requirement sum says anything about results, or that a recorded rate
repeats after a move. The transfer tools carry rates over unchanged and say so.

## Partially complete / research-only

- Optimizer's curse quantified in a synthetic requirement model; oracle shrinkage
  reduces but does not eliminate it. No football-calibrated correction ships
  ([M-05](docs/research/M-05-optimizer-selection-bias.md)).
- Opponent foundation: descriptive match/team aggregates exist; no validated
  opponent-to-requirement mapping or conditioned solver is implemented.
- Five protocols are **drafted, not frozen and not run**
  ([drafts](docs/research/north-star/README.md)): E-09 shot and defensive-location
  candidates, E-10 conceded-territory persistence, E-11 provider agreement on the
  100 double-coded matches, E-12 rates across a club change, E-13 declared-risk
  selection. Each needs adversarial review and an audit before it is registered.
  The verdict registry is empty.

## Not started or not validated

- Attainable ranges per requirement (what this squad can reach, which Transfer
  Lab needs before it can suggest a minimum worth declaring), certified
  Pareto-frontier enumeration, declared-risk (tail, minimax-regret) modes,
  certified minimal conflict sets, continuity utility, role-transition value models
  and automatic formation identification. No specification exists for the XI-level
  tools yet; the squad kernel is the place to build them.
- External lineup-utility validation, team-outcome association and forced-change
  quasi-experiments. No backtest observes the unplayed counterfactual XI.
- E-07's first observed-opening forecast protocol was executed but remained
  inconclusive at its development sample gate (3 qualifying observations versus
  50 required). E-08's separately preregistered partial-history study reached 272
  development rows but selected context only; incremental prediction was not
  established. No learned XI utility is promoted. Inspectable personnel-diverse
  equivalent XIs are now implemented; renewed prediction claims need fresh evidence.
- LIVE ingestion and its licensed availability contract; no event coordinates or
  physical metrics may be fabricated from aggregate inputs.
- Bridge estimation and paired-corpus validation; candidate sources require a
  fresh coverage/licensing check before use.
- Opponent Lab, a Director's desk that chains the labs, learned embeddings and
  VISION. A tag sidecar for the Wyscout detail the neutral schema drops (body
  part, duel outcome, cards, own goals) is specified and not built; the shot and
  opponent experiments need it.

The next research gates are identification and out-of-sample decision validation,
not adding more tactical labels: freeze and run E-11 before E-12, and E-09 and
E-10 before any shot or opponent quantity reaches a page. Exact continuation state
lives in [ASTRA-CHECKPOINT](docs/ASTRA-CHECKPOINT.md).
