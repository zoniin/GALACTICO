# North-star build: decisions and protocol drafts

Working record of the October 2026 build that added Squad Lab and Transfer Lab.
Two things live here, and neither is a result.

| File | What it is | Status |
|---|---|---|
| [ROOT-DECISIONS.md](ROOT-DECISIONS.md) | The binding decisions the build ran under: the constitution restated as rules R1-R13, the tool definitions, the frozen files, and the rulings on what the reconnaissance and the designers disputed (sections 2.5 and 2.6) | Followed for everything shipped, with one rule overridden by decision. R13 pins the shipped Player, Match and XI Lab outputs; ADR-0025 and ADR-0027 override it for the corrections they name, in Player Lab and on Match Lab's player rows. Sections on tools that were not built (frontier, risk modes, minimal conflict, Opponent Lab, the desk) are plans, not descriptions. So is section 2.2: its heading names `experiments/preregistered/E-09 .. E-13`, and no such protocol is registered; the five are drafts under `protocol-drafts/` |
| [protocol-drafts/](protocol-drafts/) | Five experiment protocols with their configs and pipeline specifications | **Drafts. Not frozen, not registered, not run** |

## The five drafts

| Draft | Question | Tier | Depends on | Reviewed |
|---|---|---|---|---|
| [E-09](protocol-drafts/E-09-player-candidates/preregistration.md) | Do shot-volume, location-weighted shot and defensive-location candidates survive the measurement lifecycle? Includes a location-only shot conversion model, named as a model | PUBLIC | the tag sidecar | no |
| [E-10](protocol-drafts/E-10-conceded-shape/preregistration.md) | Is where a team concedes a property of the defending team, beyond the attacker's own tendencies? | PUBLIC, replicated on LOCAL | the tag sidecar | no |
| [E-11](protocol-drafts/E-11-provider-agreement/preregistration.md) | Do the two providers' estimators agree on the 100 matches both coded (World Cup 2018; Barcelona's 36 La Liga 2017/18 matches)? | LOCAL | nothing; must run before E-12 | three rounds on 9 October 2026; the third audit returned NOT_READY |
| [E-12](protocol-drafts/E-12-transport-movers/preregistration.md) | Do player rates survive a club change? Movers against stayers across the two corpora, plus the small within-season arm | LOCAL and PUBLIC arms | E-11's comparability grades | no |
| [E-13](protocol-drafts/E-13-declared-risk-selection/preregistration.md) | Do declared-risk selection rules reduce selection optimism, and what does held-out evaluation say about the Madrid snapshots? | PUBLIC | a risk solver that does not exist yet | no |

Each was written by one designer in one pass. The design council that produced
them was meant to attack every draft with three adversarial reviewers, revise,
reconcile the five against each other and have each audited before any commit. It
was cut short after the drafting stage. E-11 alone has been reviewed since; its
state is the next section. So:

- E-09, E-10, E-12 and E-13 have not been reviewed. Expect defects: a threshold
  that lives only in prose, a branch of a verdict rule left undefined, a sample
  gate miscounted.
- No pipeline is built for any of the five (E-11 has its fetch script and nothing else),
and no outcome named in any of them has been computed. The designers' own simulations of their decision rules ran on
  synthetic data only.
- Nothing is registered. `galactico/domain/verdicts.py` ships an empty registry,
  so every badge on a planning page reads RECORD ONLY · NOT TESTED.

## E-11 after three rounds: a draft, not ready, not registered

On 9 October 2026 the E-11 draft went through three rounds of review, revision and
independent audit. Each audit was made by a reviewer who had written none of the
draft and walked the branches of its verdict rules on synthetic numbers.

| Round | What was reviewed | Revision | Independent audit |
|---|---|---|---|
| 1 | the draft, by three adversarial reviewers: a statistician, a reader of the football data, a reader for the constitution | 44 changes applied, 12 proposals rejected with reasons | NOT_READY, 9 blockers |
| 2 | the first audit's findings | 29 changes applied, 8 rejected | NOT_READY, 5 blockers |
| 3 | the second audit's findings, and seven rulings by the root on what the first two rounds left open | 29 changes applied, 7 rejected | NOT_READY, 3 blockers |

What the third audit confirmed applied: all five blockers of the second audit, its
consistency items 4 to 16 and the seven rulings. The hash of the pipeline
specification equals the one the config pins. Within the four verdict rules (cell,
link, admission, registry) every case it walked returns exactly one verdict.

Its verdict is NOT_READY, with three blockers. None of the three is applied yet.

1. The sentence frozen for an INCONCLUSIVE registry token holds the word
   "control", which the copy guard bans, so the verdicts endpoint would refuse
   that record after a run.
2. The permuted-link control bears on verdicts and its computation is not
   defined: four readings the text allows gave different results on synthetic
   corpora.
3. The config says no key holds a provider's full name; three of its keys and
   four keys of the local result file do, so the frozen test list could not be
   met by the frozen files.

The script that fetches the two double-coded folders exists under `scripts/`. Its
check mode opens no connection and passes on the three local folders the config
pins: every listed match file is present and each folder's digest equals the pinned
one. In the three rounds nothing was computed across the two providers, and no outcome
of the protocol has been computed at all: no agreement value, no event pairing, no team-
sheet pairing and no false-link rate. Before the rounds the two rosters were linked by
name and nationality for structure counts, and a count of such links on the double-coded
players is in the working notes, so the draft declares the recall criterion of its link
verdict not blind (its prior-exposure table).

A fourth round consists of applying the three blockers and the remaining
consistency items of the third audit, recomputing the pipeline hash, and a fresh
independent audit. Registration follows a READY verdict only, in one commit that
holds nothing else. Two notes for whoever runs that round. The draft's PIPELINE
says the fetch script is committed with the registration; it is committed now,
before registration, as part of the draft, and the next revision must say so. The
draft's own banner says its third revision has not been audited; it has.

## Three things to settle before another draft is registered

- E-09's config pins the digest of `experiments/run_replication.py`, and its
  pipeline refuses to run when the file differs. The pin is the file as it was
  before the rank-tie correction. The file has changed twice since, and the
  function the draft imports from it, `decide`, has not. Pin again before
  registration, or pin the function. E-09 also sends count-valued candidates
  through the confound audit, where a tied twelfth place now leaves the survivor
  count undefined; the draft does not say how it reports that.
- A test refuses a JSON file under `experiments/` that has a key naming the
  local-tier provider. Two keys of the E-10 config, one of its test-vector file
  and five of the E-12 config are such names. None holds data. They are renamed
  before registration, or the test's rule is changed first; a registered file is
  never edited.
- A credited draft draws the provider's logo by a path that resolves from the
  draft folder. Under `experiments/preregistered/` that path is another, so it is
  changed in the registration commit. E-12's pipeline specification still says
  the logo file is added in that commit; it has been in the tree since 9 October.

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
