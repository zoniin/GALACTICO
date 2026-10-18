# North-star build: decisions and protocol drafts

Working record of the October 2026 build that added Squad Lab and Transfer Lab.
Two things live here, and neither is a result.

| File | What it is | Status |
|---|---|---|
| [ROOT-DECISIONS.md](ROOT-DECISIONS.md) | The binding decisions the build ran under: the constitution restated as rules R1-R13, the tool definitions, the frozen files, and the rulings on what the reconnaissance and the designers disputed (sections 2.5 and 2.6) | Followed for everything shipped, with one rule overridden by decision. R13 pins the shipped Player, Match and XI Lab outputs; ADR-0025 and ADR-0027 override it for the corrections they name, in Player Lab and on Match Lab's player rows. Sections on tools that were not built (frontier, risk modes, minimal conflict, Opponent Lab, the desk) are plans, not descriptions. So is section 2.2: its heading names `experiments/preregistered/E-09 .. E-13`; of the five only E-11 is registered (14 October 2026), and the other four are drafts under `protocol-drafts/` |
| [OR-XI-SPEC.md](OR-XI-SPEC.md) | The build contract of the four exact XI tools of ROOT 2.1 (ceilings, minimal conflict, frontier, declared-risk modes), their router and the XI Lab page parts | Attacked once by three lenses, gates ruled in ROOT-DECISIONS 2.7 (X1 to X14), audited twice in five scopes with every confirmed blocker applied, nothing awaiting a root ruling; open items with E-13's owner. Built (ADR-0030); its checklist review is under way |
| [protocol-drafts/](protocol-drafts/) | Four experiment protocols with their configs and pipeline specifications, and a pointer where E-11's draft was | **Drafts. Not frozen, not registered, not run** |

## The five protocols

| Protocol | Question | Tier | Depends on | Reviewed |
|---|---|---|---|---|
| [E-09](protocol-drafts/E-09-player-candidates/preregistration.md) | Do shot-volume, location-weighted shot and defensive-location candidates survive the measurement lifecycle? Includes a location-only shot conversion model, named as a model | PUBLIC | the tag sidecar (built; the draft names functions it does not have) | no |
| [E-10](protocol-drafts/E-10-conceded-shape/preregistration.md) | Is where a team concedes a property of the defending team, beyond the attacker's own tendencies? | PUBLIC, replicated on LOCAL | the tag sidecar (built; the draft names functions it does not have) | no |
| [E-11](../../../experiments/preregistered/E-11-provider-agreement/preregistration.md) | Do the two providers' estimators agree on the 100 matches both coded (World Cup 2018; Barcelona's 36 La Liga 2017/18 matches)? | LOCAL | nothing; must run before E-12 | ten audits; the tenth, partitioned across nine auditors, READY on the eleventh revision; two later revisions verified; **registered 14 October 2026, not run** |
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
- E-11's pipeline is built and tested on synthetic data and its acceptance stamp is
  committed; no other draft has a pipeline. No outcome named in any of the five has been
  computed. The designers' own simulations of their decision rules ran on synthetic data
  only.
- E-11 alone is registered (14 October 2026, [ADR-0029](../../../DECISIONS.md)).
  `galactico/domain/verdicts.py` holds its sixteen records, token `PENDING`, each
  reading E-11 · RECORD ONLY · NOT RUN; every other badge on a planning page reads
  RECORD ONLY · NOT TESTED.

## E-11 after thirteen revisions: READY, registered, not run

On 9 October 2026 the E-11 draft went through three rounds of review, revision and
independent audit. On 13 October a fourth revision applied the third audit's
blockers, a fourth independent audit found one blocker that revision introduced, a
fifth revision applied it, a fifth audit found one more that no earlier audit had
raised, a sixth revision applied it, a sixth audit found two more, a seventh revision
applied them, a seventh audit found two more, an eighth revision applied those, an
eighth audit split across nine auditors found three more, a ninth revision applied
them, six reviewers verified those fixes and found fourteen consistency items, a tenth
revision applied them, a ninth audit in the same partitioned way found one more blocker
and eight of its nine scopes ready, an eleventh revision applied it, and a tenth audit in
the same way returned READY: all nine scopes, no blocker. A twelfth revision applies its
fifteen consistency items, which change no token. Each audit was made by a reviewer who had written none of the
draft and walked the branches of its verdict rules on synthetic numbers.

| Round | What was reviewed | Revision | Independent audit |
|---|---|---|---|
| 1 | the draft, by three adversarial reviewers: a statistician, a reader of the football data, a reader for the constitution | 44 changes applied, 12 proposals rejected with reasons | NOT_READY, 9 blockers |
| 2 | the first audit's findings | 29 changes applied, 8 rejected | NOT_READY, 5 blockers |
| 3 | the second audit's findings, and seven rulings by the root on what the first two rounds left open | 29 changes applied, 7 rejected | NOT_READY, 3 blockers |
| 4 | the third audit's three blockers (13 October) | 3 applied, none rejected; the third audit's consistency items are not in this repository, were not available to this round, and none was applied | NOT_READY, 1 blocker and 5 consistency items |
| 5 | the fourth audit's findings (13 October) | the blocker and consistency items 2 to 5 applied; item 1 by a rerun of the simulation | NOT_READY, 1 blocker and 8 consistency items |
| 6 | the fifth audit's findings (13 October) | the blocker and all 8 consistency items applied | NOT_READY, 2 blockers and 12 consistency items |
| 7 | the sixth audit's findings (13 October) | both blockers and all 12 consistency items applied | NOT_READY, 2 blockers and 11 consistency items |
| 8 | the seventh audit's findings (13 October) | both blockers and consistency items 1 to 10 applied; item 11, a simulated figure a third implementation did not reproduce exactly, is descriptive and unchanged | NOT_READY: 3 blockers, each confirmed by three of three skeptics; 29 of 35 consistency candidates confirmed |
| 9 | the eighth audit's findings (13 October) | all 3 blockers and the 29 confirmed consistency items applied, with two optional notes for E-12 | verified by five reviewers by finding and one over the whole diff: 3 blockers and 27 items resolved, 2 items partly; no new blocker; 14 new consistency items, most in sentences the revision added |
| 10 | the verification's follow-ups (13 October) | the 2 partial items completed and the 14 consistency items applied | NOT_READY, partitioned like the eighth: 8 of 9 scopes READY; 1 blocker, confirmed by three of three skeptics; 26 of 29 consistency candidates confirmed |
| 11 | the ninth audit's findings (14 October) | the blocker and the 26 confirmed consistency items applied | **READY**: all 9 scopes READY, no blocker candidate; 15 of 18 consistency candidates confirmed |
| 12 | the tenth audit's consistency items (14 October) | all 15 applied, with one optional wording; none changes a token | verified by three reviewers by item group and one over the whole diff: no blocker; 17 consistency items on the output of stopped and partly failed runs |
| 13 | the verification's items (14 October) | applied; one turned into a root ruling (below) | verified by two reviewers by item group and one over the whole diff: no blocker, every item resolved; one wording of the protocol corrected, which leaves the pipeline hash unchanged |

What the third audit confirmed applied: all five blockers of the second audit, its
consistency items 4 to 16 and the seven rulings. The hash of the pipeline
specification equals the one the config pins. Within the four verdict rules (cell,
link, admission, registry) every case it walked returns exactly one verdict.

Its verdict was NOT_READY, with three blockers. The fourth revision applies each:

1. The sentence frozen for an INCONCLUSIVE registry token held the word
   "control", which the copy guard bans, so the verdicts endpoint would have
   refused that record after a run. It now reads "a check the pipeline runs on
   itself failed". Every sentence of every token of every subject is served
   through the real response boundary by `tests/test_protocol_drafts.py`.
2. The permuted-link control bore on verdicts and its computation was not
   defined: four readings the text allowed gave different results on synthetic
   corpora. It is now one computation, on fixed aggregates: the units of each
   quantity's headline cell keep the two aggregates of its point estimate, the
   Wyscout aggregates are reassigned inside cluster × role by a cyclic shift of a
   shuffled order whose generator, stratum order and draws are fixed, and nothing
   is gated, aggregated or weighted again; a headline cell that is INCONCLUSIVE has
   no control (protocol, "Models and baselines"; PIPELINE sections 3 and 5). A
   simulation on the acceptance generator, synthetic only, is in the protocol: the
   control held in all 4,500 corpora at true agreement 0.60 to 0.95, and in 172 of
   900 with a link drawn uniformly inside team × role. It is a stress test, not a
   test that the link is right. `permuted_link_acceptance` makes the first result a
   requirement of the acceptance run.
3. The config said no key held a provider's full name; three of its keys and
   four keys of the local result file did. They are renamed (`wy_parquet_root`,
   `wy_raw_root`, `wy_competition`; `mean_sb`, `mean_wy`, `sd_sb`, `sd_wy`), the
   rule names the three words it means and covers all four result files at every
   depth. The fourth revision also required a value per provider to sit under `sb`
   or `wy` and a provider key to take the prefix `sb_` or `wy_`; frozen keys such as
   `penalty_area_sb` and `mean_sb` break both, so the frozen runner test could not
   be met. That was the fourth audit's blocker. The fifth revision states the
   convention every key meets (`sb` or `wy` as one `_`-separated part) and tests
   only the three names.

The fourth revision also says that the fetch script was committed with the draft,
before registration, and recomputes `pipeline_spec_sha256`. A test now ties the
pinned hash to the file, so an edit that forgets it fails.

The script that fetches the two double-coded folders exists under `scripts/`. Its
check mode opens no connection and passes on the three local folders the config
pins: every listed match file is present and each folder's digest equals the pinned
one. In all the rounds nothing was computed across the two providers, and no outcome
of the protocol has been computed at all: no agreement value, no event pairing, no team-
sheet pairing and no false-link rate. Before the rounds the two rosters were linked by
name and nationality for structure counts, and a count of such links on the double-coded
players is in the working notes, so the draft declares the recall criterion of its link
verdict not blind (its prior-exposure table).

The fourth audit's consistency items, applied in the fifth revision: the simulation
overstated what the control shows (item 2 above; rerun); `scope` holds the competition years, and
the digit rule is now said to be V7's, which does not read it; a planted cell names
its reader and valuation; the cluster has one definition in the config and PIPELINE;
and a helper, `control_holds`, decides the control, so its tests reach a NaN value.

The fifth audit confirmed every blocker and consistency item above applied, walked the
four verdict rules by brute force (each returns exactly one outcome), checked the
simulation script against PIPELINE section 6 and every figure the protocol prints
from it, and found one blocker no earlier audit had raised. Purpose (b) did not say
whether a player's sheets are the Wyscout rows as read or after the zero-minute filter
of the player crosswalk. For an unpaired player whom the licensed provider credits with
a minute and Wyscout with none, a link to his own record was `FALSE` on one reading and
`UNVERIFIABLE` on the other, and the false-link criterion passes with one false link
in six hundred and fails with two. His sheets are now the rows as read, zero-minute
rows included, and a frozen test pins that case. Its eight consistency items are
applied too: an example key that exists, the convention said to be one; the strings
`results.json` may hold; the absent-partner rerun is one evaluation per paired player;
the simulation sentence; the registration commit's edits of the licence test;
`teams.parquet` hashed; the end-to-end test's config and its planted dismissal; the
control's point and recomputation are one call.

The sixth audit was pointed at what earlier audits had read least: the match and
team-sheet crosswalks, the wide link, the minutes rules, the inputs, the bootstrap
schemes and the gates. It confirmed the sixth revision and found two blockers. The
wide link needs one row per licensed-side player and nothing built it from the per-match
sheet rows, so a player whose nickname is null in one folder and present in the other
linked at tier N on one reading and not on the other; he now takes the values of his
row in the linked match of largest match key (the World Cup subset is keyed first, so a
player of both subsets takes his La Liga row), and such players are counted. And the pitch cuts were
"exact fractions": a licensed-side x of 80/120 equals 2/3 in float64 and lies below it as
a rational, so a pass ending there was a final-third entry on one reading and not on
the other; every fractional cut is now the float64 quotient. Its twelve consistency
items are applied: the end-to-end test's entry point and config, match uniqueness in
both directions as the protocol says and the rejection reason of each case, matches
absent from the per-competition Wyscout files, the four name strings unescaped alike,
the coverage numerator, the absent-partner rerun against full-run candidates, unused
substitutes, the teams frame's provenance key, the Wyscout starter minutes of the
shipped adapter, the xT recipe on harmonised rows, and four generator and quantile
numbers moved from prose to config.

The seventh audit read the parts no audit had: the xT surfaces, the three bootstrap
schemes, the aggregated gates, the runner's refusal checks against git and
`tests/test_preregistration_order.py`, the result shapes, and the acceptance run, which
it implemented again from section 6 alone. On 200 synthetic corpora per entry every
acceptance requirement was met, every population value fell within 0.007 of its
target, and the permuted-link control held in 1,200 of 1,200 agreeing corpora. It
found two blockers. The seventh revision named the row of a player's names two ways:
"the last linked match" in the protocol and "largest `match_key`" in the pipeline,
which disagree for a Barcelona player who also played the later World Cup; the protocol
now names the pipeline's ordering. And the local results file was to pass the whole
licence check, which refuses every path under `data/licensed/` and every file above
its ceiling; only the committed files are held to the whole check now, and the local
file to its fingerprint patterns. Of its eleven consistency items, ten are applied:
the acceptance run's weight arrays and population seeds, the generator's minutes from
the cap, the scenario `count_family` switch, the Wyscout turnover as a pass whose
success is False, the team weights over every team of a linked match, every surface
failure mapped to its gate, the result strings, a slot for the disagreeing players,
the divergence intervals on the shared match weights, and a failure while writing
that leaves no local results behind.

The eighth audit changed method, because one auditor at a time found one or two
blockers per round. Nine auditors each held one part of the draft (data and gates; the
sheet crosswalk and the wide link; measurements; statistics; decision rules; the
acceptance run; runner, results and registration; fitness for purpose against E-12 and
the registry; a mechanical cross-file sweep), a triage merged their 44 findings, and
every blocker candidate went to three skeptics, one asking whether the text already
decides it, one whether the case can arise, one whether the fix is right. All three
candidates were confirmed three to zero. A Pappalardo file missing at run time could
end the one execution as `DATA_MISSING`, as `MATCH_CROSSWALK` or as a retryable failure,
depending on the reading; it is now a refusal before the run, and `DATA_MISSING` tests
licensed-side files only. The player crosswalk and the wide link never named their
tokenizer, and `name_tokens` drops particles and one-letter tokens where a plain split
keeps them, so a tier A link could hold on one reading and fail on the other; every
name comparison is now on `name_tokens`. And the acceptance run's population check sat
about one standard deviation inside its tolerance for one entry, so roughly one
faithful implementation in seventy would fail the frozen stamp by chance; the population
check now uses four times the corpora, which puts every entry about four standard
deviations inside. Twenty-nine of thirty-five consistency candidates were confirmed and
applied; among them, an E-11 label served on a hosted page would have carried no logo,
no credit and no link, which ADR-0027 requires, and the results commit now must add
them. The fitness auditor found E-11's outputs serve E-12 once the hashes and calls E-12
pins are named, which section 14 now does; the mismatches it found on E-12's side belong
to the unreviewed E-12 draft.

The ninth audit ran the eighth's method on the tenth revision. Eight of its nine scopes
returned READY. The measurements scope found the one blocker: Wyscout puts the
interception tag on the intercepting player's next event, which can be a clearance, and
the protocol both counted every row carrying the flag in the defensive unions and said
clearances are in neither union, so defensive quantities differed by reading. A flagged
clearance is now an interception in the unions and stays a clearance for the descriptive
tables, which is also what E-09 and E-10 define. Of its twenty-six consistency items the
notable ones: the sheet readers now receive every config value they read; how the two
minute rules differ is stated in full; a failed run never records an exception message,
which could carry a count or an identifier into the committed analysis; every exclusion,
not one, forbids descriptive use; the acceptance cap on admissions at the boundary under
the team-match structure gets the margin the protocol promises; and section 14 tells
E-12 where to read the link bounds and what it must check on its own folders.

The tenth audit ran the same method on the eleventh revision, each auditor first checking
that revision's edits in its scope for regressions. All nine scopes returned READY and no
blocker candidate was raised. Its fifteen consistency items change no token: among them a
stray word the eleventh revision left in a frozen sentence, what a stopped run writes in
each block, what `CLAIMED_TWICE` rows carry, the count ratio's direction and interval,
the machine as well as the BLAS in the provenance E-12 must match, and the Wyscout role
E-12 must name beside its own position labels. The twelfth revision applies them, so
that the text registered is the text found ready, corrected only where no token moves.

The verification of the twelfth revision found no blocker, so the tenth audit's READY
holds for the text as revised. Its items, applied in the thirteenth revision, fix what a
stopped or partly failed run writes, which descriptive rows have which keys, and when the
planning sentence that nothing was tested may change: when an E-11 badge reads TESTED,
not merely when results are committed, since a run stopped by a gate leaves every token
`INCONCLUSIVE`. One item is a question for the root, not wording: E-11 grades ordering
within the Wyscout role code, and the E-12 draft forms its origin cells within a
position label from the licensed provider; whether an admission covers that design must
be ruled before E-12 is frozen, and section 14 now says so.

The verification of the thirteenth revision found no blocker and every item resolved. Its
one finding, a protocol sentence that said E-11 reads a position label it never forms, is
corrected; PIPELINE.md did not change, so its pinned hash stands.

The owner decided to register, and E-11 was registered on 14 October 2026 in one commit
that holds the three files and the edits PIPELINE section 13 lists, and nothing else
([ADR-0029](../../../DECISIONS.md)). The draft folder holds one-line pointers. What is left
is the order section 13 gives: the pipeline, built and tested on synthetic data; the
acceptance stamp in a commit of its own; then the run. The first two are done: the six
modules and their tests (`c9ec004`, `5935816`), a review of the pre-outcome checklist of
section 11 by four reviewers whose 29 findings were applied and verified (`3733721`), and
the stamp (`f6f9184`), whose seventeen scenarios all passed. The run waits on the public
corpus, which the build environment cannot reach. The root ruled on the role named
above on 16 October 2026 (ROOT-DECISIONS 2.8): an admission covers an E-12 origin cell
only for a linked unit whose two position labels agree. The third audit's own consistency items are not in this
repository and were never applied.

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
