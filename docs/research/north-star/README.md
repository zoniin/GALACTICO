# North-star build: decisions and protocol drafts

Working record of the October 2026 build that added Squad Lab and Transfer Lab.
Two things live here, and neither is a result.

| File | What it is | Status |
|---|---|---|
| [ROOT-DECISIONS.md](ROOT-DECISIONS.md) | The binding decisions the build ran under: the constitution restated as rules R1-R13, the tool definitions, the frozen files, and the rulings on what the reconnaissance and the designers disputed (sections 2.5 and 2.6) | Followed for everything shipped. Sections on tools that were not built (frontier, risk modes, minimal conflict, Opponent Lab, the desk) are plans, not descriptions |
| [protocol-drafts/](protocol-drafts/) | Five experiment protocols with their configs and pipeline specifications | **Drafts. Not frozen, not registered, not run** |

## The five drafts

| Draft | Question | Tier | Depends on |
|---|---|---|---|
| [E-09](protocol-drafts/E-09-player-candidates/preregistration.md) | Do shot-volume, location-weighted shot and defensive-location candidates survive the measurement lifecycle? Includes a location-only shot conversion model, named as a model | PUBLIC | the tag sidecar |
| [E-10](protocol-drafts/E-10-conceded-shape/preregistration.md) | Is where a team concedes a property of the defending team, beyond the attacker's own tendencies? | PUBLIC, replicated on LOCAL | the tag sidecar |
| [E-11](protocol-drafts/E-11-provider-agreement/preregistration.md) | Do the two providers' estimators agree on the 100 matches both coded (World Cup 2018; Barcelona's 36 La Liga 2017/18 matches)? | LOCAL | nothing; must run before E-12 |
| [E-12](protocol-drafts/E-12-transport-movers/preregistration.md) | Do player rates survive a club change? Movers against stayers across the two corpora, plus the small within-season arm | LOCAL and PUBLIC arms | E-11's comparability grades |
| [E-13](protocol-drafts/E-13-declared-risk-selection/preregistration.md) | Do declared-risk selection rules reduce selection optimism, and what does held-out evaluation say about the Madrid snapshots? | PUBLIC | a risk solver that does not exist yet |

Each was written by one designer in one pass. The design council that produced
them was meant to attack every draft with three adversarial reviewers, revise,
reconcile the five against each other and have each audited before any commit. It
was cut short after the drafting stage. So:

- No draft has been reviewed. Expect defects: a threshold that lives only in
  prose, a branch of a verdict rule left undefined, a sample gate miscounted.
- No pipeline exists for any of them, and no outcome named in any of them has
  been computed. The designers' own simulations of their decision rules ran on
  synthetic data only.
- Nothing is registered. `galactico/domain/verdicts.py` ships an empty registry,
  so every badge on a planning page reads RECORD ONLY · NOT TESTED.

## How a draft becomes a protocol

1. Adversarial review (a statistician, a football reader, the constitution) and an
   independent audit that walks every branch of the verdict rule.
2. One commit that adds the reviewed `preregistration.md` and `config.json` under
   `experiments/preregistered/E-NN-slug/`. That commit is the registration:
   `tests/test_preregistration_order.py` requires it to precede the commit that
   adds `results.json`, and nothing may touch the protocol afterwards.
3. A record in the verdict registry with the protocol's hashes, token `PENDING`.
4. The pipeline, built and tested on synthetic data only, including the planted
   effect and planted null the decision rule must classify correctly.
5. One real run, one determinism re-run, the results, the analysis.

E-11 before E-12. Nothing from E-11 or the cross-corpus arm of E-12 may reach a
hosted page as a number ([ADR-0018](../../../DECISIONS.md)).

## What the drafts cite that is not in this repository

References such as "critic R6", "maps/lifecycle.md T17" or
"research/mover-census.md" point to working notes of the build: eight subsystem
maps, six method reports, two structure-only corpus audits and an independent
critique. They are long, partly raw, and include counts derived from the
local-only corpus, so they were kept out of the repository. The facts the drafts
lean on most are restated where they are used; the ones that changed a design
decision are in ROOT-DECISIONS sections 2.5 and 3b and in
[KNOWN_LIMITATIONS](../../../KNOWN_LIMITATIONS.md).
