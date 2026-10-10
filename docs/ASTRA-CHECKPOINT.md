# Decision Engine checkpoint

## CURRENT COMMIT

10 October: the Squad Lab / Transfer Lab build, the repairs of the first audit, the
decisions the owner delegated on 9 October and the repairs of the second audit are
committed on the branch `north-star`, above `feb9f8b`.
`git log --oneline feb9f8b..north-star` lists the commits. The branch was pushed on
9 October, and CI passed both jobs on `b7bc919` (run [37944962165](https://github.com/zoniin/GALACTICO/actions/runs/37944962165))
and on `7899c76` (run [37953254713](https://github.com/zoniin/GALACTICO/actions/runs/37953254713)).
The commits after `7899c76` had not been pushed when this was written. Whether `main`
holds the branch is a fact about `main`, not about this file:
`git branch --contains b7bc919` answers it.

On 10 October, on the tree of the second-audit repairs: 1,476 Python tests passed and 1
skipped (the tag sidecar is not built), with the local StatsBomb cache present (without
it one more skips); 52 browser tests and the two screenshot captures passed; Ruff and
the licence guard clean; the regenerated profile and "Why only five?" screenshots
read. The CI workflow was changed on this branch (the browser job ingests five
leagues, runs the Python suite with the corpus and runs three more specs); run
37944962165 was its first on GitHub Actions.

Commits, oldest first: `d7e9acc` e2e port from the environment · `f581c56` guards
that could not fail · `9a7da06` measurement gates that failed open · `c79a3ef`
Match Lab and XI Lab defects · `850cba1` guarded public loader, one evidence
mapping, the verdict registry · `cfb36be` the exact kernel, any-club snapshots,
league references · `ac1d43a` depth, absence stress, role brief · `1d6f7f1`
candidate universe, exact injection, break-even carry-over · `4668b2a` lab
runtime and page shell · `e96b81c` ADR-0018 to 0023, M-06, protocol drafts ·
`36150fb` tool sentences by label · `a8ffe3d` planning API and browser kit ·
`d9bf28f` Squad Lab and Transfer Lab · `9b8c105` documentation and screenshots ·
`5991c23` the attained sum in Transfer Lab. Then the repairs the final audit asked
for: `b91f466` six false statements in the documents · `e55d824` the Madrid rule
set is declared by hand, not reviewed · `1853ad2` tool sentences · `d9ba681` builds
inside the budget and behind a gate, cache keys on the request as resolved (never
two problems under one key) · `8b13d52` the copy
guard at the response boundary · `55b3b7b` server fields for the pages · `2736f08` the pages print them · `4faa22a` the audit record. Then the decisions the
owner delegated on 9 October: `b7bc919` StatsBomb credit and logo, three sources
reference only · `7753b45` a construct is published only inside its declared
context · `d3d3ff5` average ranks, the erratum M-07 and the StatsBomb-side table
out of the tree · `7899c76` the documents for those decisions · `f4d0410` the
erratum compares the StatsBomb half with the local record · then the repairs of
the second audit.

At least eight commit messages are wrong in part and cannot be corrected without
rewriting history: the five below, and three whose own words the second audit
contradicts. `d9ba681` says one problem, one cache key; a preset sent together with what
it sets by hand is one problem under two keys (ADR-0024). `8b13d52` says the copy guard
runs on every response; it reads the string values of a 200 reply outside provenance and
no error body. `5991c23` says the attained number is the largest sum any XI of the
declared squad reaches; it is the sum of one XI the solver found. `ac1d43a` says the role brief matched a slot search on 88 slot and
scenario combinations; the committed test covers 22. `4faa22a` says four of the
first audit's findings were high and that all were repaired from failing tests;
five were high, and one was a sentence corrected in a commit of documents only.
`b7bc919` says LICENSING stated the credit requirement for months; it was 39 days.
`7753b45` says 20 of the 40 rows the Explore view listed under wide-channel share
were goalkeepers, and that the channel bar restates the pass-origin shares; the
page drew no goalkeeper, and the bar did not restate them until the second
audit's rebuild. `d3d3ff5` calls 0.7761 the lowest figure and says a rerun of the
runners reproduces what was published; 0.7761 is the lowest of the 55 audit
figures on the public corpus, E-02's T3 is 0.5948, and a rerun of the Stage 1C
runner does not reproduce its record.

This build ran in a fresh clone on a second Windows machine with no `uv` and no
`gh`: `py -3.12 -m venv .venv`, then `pip install -e ".[dev,api]"`. The commands
below still read `uv run`; substitute `.venv\Scripts\python.exe -m`.

Earlier state, 20 September: progression-under-hard-floors core/API is committed as `d99892b`;
browser/docs release is HEAD after this update. All implementation is integrated:
374 Python tests and 13 Playwright tests passed, Ruff/licensing clean, final
desktop/mobile screenshots inspected. Verify final push/CI using commands below.
Entry was clean, pushed `47ff5ae`, whose CI `35297823998` passed. E-08 stays closed.

Recovery history: disk filled on 18 September and truncated API/domain/XI HTML
before any new commit. All three were restored exactly from HEAD via apply_patch
before reapplying edits; no files were deleted. More than 14 GB was free at the
final verification. Disk interruption and agent usage boundaries left no missing
implementation. Root independently verified and integrated all recovered work.

Earlier entry: clean `946bf4a`, verified on 13 September; resumed 17 September.
E-08 protocol `68454bf` was committed/pushed before errors were evaluated.
History implementation `b5b1fe9` and evaluator/CLI `61fe186` are pushed to main.
Do not amend E-07 or promote aggregate findings into individual/decision gates.
E-08 completed: NOT_ESTABLISHED, context-only selected; published/pushed `4ce4d5d`.
Code CI `35263719118` passed both jobs. Equivalent-XI core/API is `abe548c`;
browser/docs release `9207731` and screenshot refresh `47ff5ae` passed CI.

Follow-through: `8f6f65a` implements E-07's research pipeline; protocol `1de6939`
was pushed before evaluation. Linux mobile repair `b4c60cb` is also pushed, and
GitHub Actions runs `34244854096` and `34278076355` passed both core and browser
jobs (the latter for E-07 result commit `8158f6b`). Final E-07 report correction
`946bf4a` also passed CI `34278961603` before the E-08 continuation.

Release code: `f86e520` — connected historical Match/XI UI, APIs and browser tests.
`6392598` — exact XI/shared-world core. `95b9904` — Match Lab/scalar null.
Earlier milestones: `470907a` decision/falsification plan; `c28ebfc` shared-match
uncertainty and Player Lab gates; `b9652c6` baseline lint repair.
Entry was clean `f0ed51a`. The original release through `05e7d9f` was pushed to
main at the user's request. Follow-through work is being committed/pushed as well;
use `git log origin/main..HEAD` to verify the exact remaining local commits.

Workspace: `C:/Users/Owner/galactico`; PowerShell; use the local `.venv`.
Permissions are unrestricted with approval disabled; omit sandbox_permissions.
No credentials or proprietary data are needed or committed.

## COMPLETED

- Specialized OR/statistical, match-data/score, historical, football/product and
  fresh adversarial agent findings integrated. The council led to implementation.
- Player Lab frozen after genuine covariance, world-identity and API-gate repairs.
- Historical Match Lab: 38 Madrid league matches, actual lineups, timeline levels,
  shots, positive pass-xT flow, inferred networks, contribution vectors/team descriptors.
  Missing xG stays unavailable. Stoppage substitutions are not labeled extra time.
  Dismissal-affected minutes are withheld; other exposure is explicitly nominal.
- Typed XI domain and exact CP-SAT: 4-3-3/4-3-1-2, eligibility, locks/exclusions,
  BALANCE/SATISFY, deficits, quantization/status/bounds, equally optimal membership,
  shared-world stability, removal sensitivity and candidate-injection foundation.
- Pre-match Madrid snapshots for 8 April / 6 May 2018; prior-calendar-date events
  and xT fitting. Heuristic minima/normalizers and manual eligibility are inspectable.
- Working API and browser surfaces. BBC inclusion and diamond-plus-Isco inclusion
  are explicit constraints, not learned role prescriptions or superiority claims.
- Independent exhaustive solver oracle, covariance and future-poisoning tests,
  synthetic failure cases, actual corpus tests and browser interactions.
- Fresh-start prepare command executed: 628,659 Spain actions, 380 matches and
  345 profiles rebuilt. Runtime data remains ignored.
- Executed scalar baseline audit Spain/England, optimizer-noise simulation,
  and 12-match temporal manager-selection diagnostic. Sources/nulls preserved.
- Sensitivity provenance repaired: baseline lineage retained, each removal returns
  fresh certification/hash/bounds, no stale bootstrap metadata.
- README/roadmap/decisions/validation/limitations rewritten from actual state;
  all linked research files exist.
- Fixed Linux-only native-select overflow by constraining the grid/control's
  intrinsic width, not hiding overflow. Added font-fallback regression. Repaired
  a vacuous comparison E2E assertion to check actual API interpretation/leader.
- E-07 prospectively committed analysis plan, clean first-30 panel, prior-date
  histories, fixed-reference xT, paired calendar-week evaluation and 27 tests.
  Both public leagues executed; INCONCLUSIVE at the frozen development sample gate.
  Aggregate results/code/data/config hashes are preserved beside the protocol.
- Fresh review repaired an early-return reporting omission: all six unfitted
  holdout comparators now report descriptive errors even when fitting is gated.
  No protocol, evidence floor, cohort or fitted-model decision changed. CI now
  explicitly reports that no registered research tests is not a validation pass.
- E-08 executed twice unchanged; full aggregate artifact saved and independently
  audited (source/data/config/protocol/xT hashes and all 21 selection procedures).
  272 development rows, 216 Spain /174 England evaluation rows. Context-only won
  development selection; NOT_ESTABLISHED. No product evidence gates changed.
- Equivalent-XI search: typed witnesses with both certified objective values fixed,
  pairwise personnel-distance cuts, explicit incomplete/exhausted statuses and
  parent/constraint fingerprints. Cuts never enter tie analysis or bootstrap worlds.
- `/api/xi/alternatives` and actual browser ledger ship. Default Madrid returns
  three witnesses, each replacing two players, under original nonzero minima.
  Delayed-response/lock invalidation, dirty-minima guard and mobile layout tested.
  Screenshots 13/14 manually inspected. No alternative receives a quality rank.
- Distinct `/api/xi/tradeoff` maximizes historical pass-xT under three explicit
  hard floors. Exact-input Fraction floor/ceil constraints guarantee raw floors;
  boundary-feasible raw XIs can be excluded. Independent objective coefficients,
  integer bounds, numerical allowances, source hashes and typed certificates.
- Independent oracle covers 36 randomized instances, exact-number boundaries,
  monotonicity, eligibility/locks/missingness and actual Madrid tightening floors.
  Fresh review independently ran 37 core/oracle tests. Prior-solve certificates
  are stripped from active provenance, retained only as source input.
- Separate browser XI/floor ledger, readable rounded summaries with exact
  certificates, no inherited main-pitch frequencies. Default/impossible query,
  stale floor-edit and lock replies, dirty minima, 390px and gold checks passed.
  Screenshots 15/16 and refreshed 11/12 manually inspected. Numeric-overflow
  request validation now returns 422, not a serialization failure.

- 9 October, guards. The test behind "no overall rating" had never run in CI,
  and six more guards failed open. Each was repaired from a failing test
  ([M-06](research/M-06-a-guard-that-never-runs.md)). The Player Lab bundle
  (385,145 values) and 864 recomputed reliability and confound figures are
  bit-identical after the measurement repairs.
- 9 October, engine. One exact kernel equal to the XI solver's integers; snapshots
  for any club and cutoff date with byte parity for Madrid; league references;
  slot depth; absence stress; the role brief; a gated candidate universe; exact
  forced-inclusion injection; the break-even carry-over fraction. Independent
  oracles for each. The frozen files were not edited.
- 9 October, product. `/squad` and `/transfer` with their routers, a shared
  runtime (budgets, cache, boundary check) and shell (navigation, evidence and
  verdict payloads, copy guard). Planning surfaces default to progression only;
  the side pass-origin requirements are an explicit experimental opt-in. Each
  page was reviewed in a browser by an agent that did not build it; fourteen
  defects were repaired.
- 9 October, final audit. Three read-only reviewers that had written none of the
  branch: documentation claims against code and data, the HTTP boundary on the
  real corpus, the constitution on the rendered pages. 36 findings, five high.
  The code findings were repaired from failing tests in six commits, and a README
  sentence in a seventh, of documents only. What was not repaired is in
  KNOWN_LIMITATIONS. The findings and the three repair reports are with the
  owner's working notes.
- 9 October, owner decisions. Four findings left for the owner were decided and
  repaired: the StatsBomb credit and logo, three provider postures, constructs
  inside their declared context (ADR-0025), average ranks with the erratum M-07
  (ADR-0026).
- 9 October, second audit. Five lenses over the branch up to `f4d0410`, the first
  audit's repairs included; 67 findings, each reproduced by a second reviewer.
  Six builders repaired the code from the rulings of ADR-0027. The declared-context
  rule reached Match Lab's player rows; the chance-creation curve was recomputed
  on the declared population (M-08); the served view and the documents that print
  analysis formed from StatsBomb data carry the credit, with one frozen exception
  recorded in LICENSING; sixteen planning requests may be past the cache lookup at
  once. What was found and left is in KNOWN_LIMITATIONS. These repairs have not
  been audited.
- 9 October, E-11. The draft went through three rounds of review, revision and
  independent audit. The third audit returned NOT_READY with three blockers. It is
  not registered ([status](research/north-star/README.md)).
- 9 October, record. ADR-0018 to ADR-0027, M-06 to M-08. Five protocol **drafts**
  (E-09 to E-13) under `docs/research/north-star/protocol-drafts/`.

## CURRENT STATE MAP

- VERIFIED COMPLETE: Player Lab, frozen since ADR-0011 except the corrections of
  ADR-0025 and ADR-0027 (October 2026); historical Match Lab implementation;
  conditional XI engine/UI; exactness/temporal/browser checks; licensing guard;
  the exact squad and transfer tools and their two pages, as arithmetic.
- PARTIALLY COMPLETE: decision usefulness; the opponent foundation.
- DRAFTED, NOT REGISTERED, NOT RUN: E-09 to E-13. The design council that wrote
  them was cut short before adversarial review, reconciliation and audit. E-11 has
  since had three rounds and its third audit returned NOT_READY; the other four
  are unreviewed. The verdict registry is empty.
- SPECIFIED, NOT BUILT: the tag sidecar (body part, duel outcome, cards, own
  goals), which E-09 and E-10 need; Opponent Lab; a Director's desk.
- NOT SPECIFIED: certified XI frontier, declared-risk modes, minimal conflict
  sets. The XI-level design was lost when the council stopped; the squad kernel
  is where to build them.
- UNVERIFIED: external human acceptance, historical fitness, learned utility,
  whether a rate repeats after a club change, and the repairs of the second audit,
  which have not been audited.
- BROKEN: nothing known beyond what KNOWN_LIMITATIONS lists as found and not
  repaired.
- OWNER DECISIONS OPEN: see OPEN BLOCKERS.
- NOT STARTED: LIVE/Bridge/VISION products.

## IN PROGRESS

No unfinished implementation on `north-star`. **1,476 local Python tests, 52 browser
tests and two screenshot captures** passed on 10 October, plus Ruff/licensing. The E-11
protocol draft is in review and is not registered. Do not reopen E-07 or E-08.

The 20 September release: **374 local Python tests and 13 Playwright tests**
passed, plus Ruff/licensing. All recovery/council/adversarial results
are integrated. Final push/CI is the only remaining handoff check if resuming
before it completes; do not rebuild the feature or reopen E-08.

The PREVIOUS equivalent-XI milestone completed. Full local verification passed
**308 Python tests** and **12 Playwright tests**; Ruff clean. The additional oracle
checks both lexicographic stages, pairwise diversity and conditional exhaustion.
One initial test sat on an integer-rounding boundary; its eligibility fixture was
corrected, not the solver's hard constraints. Core/API/UI agent work is integrated.
Final release push/CI is the only handoff check if resuming before its completion.

Previous release evidence: **247 Python
tests passed**, Ruff clean (including all new experiment/preparation scripts),
**11 Playwright tests passed** after the mobile repair; Linux CI independently passed.
Screenshots 10/11/12 were inspected, including actual dismissed-player exposure,
BBC/Isco inclusion, selected-player gold and 390px layout. Licensing guard is clean.
One upstream TestClient/httpx deprecation warning remains; it is not a test failure.

## FAILED EXPERIMENTS

- Match accounting scalar is algebraically pass-xT; role standardization correlates
  .988/.982 with it in Spain/England. No overall contribution scalar identified.
- Requirement XI overlap: 6.00/11 versus prior-minutes 6.83/11 across 12 late-season
  fixtures. Development diagnostic, not causal/external validation.
- Exact deficit minimization selects noise. Oracle Gaussian shrinkage helps in
  simulation but is not calibrated for Madrid; no correction ships.
- E-07: only 3/314 development team observations passed the joint per-player
  evidence gates (50 required); holdouts had 41 Spain /32 England observations.
  Independent cumulative-minutes calculation confirmed the 3 complete development
  XIs above 900 prior nominal minutes. No OLS coefficients or fitted-model error
  comparison were evaluated. Six unfitted comparators have descriptive errors;
  do not label this a failure of predictive lineup information.
- E-08: coverage increased to 272 development observations, but forward tuning
  selected context only (MSE .071181 vs .071671 for best finite k=3). Incremental
  prediction NOT_ESTABLISHED. The zero loss-difference interval compares identical
  predictions, not proof of absent player effects. No rescue tuning is authorized.

## OPEN BLOCKERS

External human sign-off is not claimed.
Creation, rest defense and keeper quality are unmeasured in XI Lab: an explicit
limit on the decision claim, not missing implementation disguised as a result.

Owner decisions and open work. Items 2 to 5 were left open by the 9 October
reconnaissance, decided that day and corrected again after the second audit
(ADR-0027). Items 1, 6, 7 and 8 are open:

1. The branch was pushed on 9 October and CI passed on it twice. Merging into `main`
   is a fast-forward of a tip whose CI run is green: commit order is how this
   repository shows that a protocol preceded its results, so the branch is never
   squashed or rebased. This file cannot say whether the merge has happened;
   `git branch --contains b7bc919` does. While the default branch lacks that commit,
   the note links of the "Why only five?" view lead to copies of the two reports
   with no logo and no credit.
2. Decided: a document that prints analysis formed from StatsBomb data names the
   source and carries its logo (clause 1.4), and so does the served "Why only
   five?" view. A test lists every document that mentions the provider.
3. Decided: FPL, ClubElo and football-data.co.uk are reference only, which is now
   a tier of the type in `providers/base.py`. The terms read that day do not
   support more.
4. Decided: a construct is published only inside the context it declares
   (ADR-0025). Goalkeepers carry all five as withheld rows with the reason, in
   Player Lab and on Match Lab's player rows.
5. Decided: average ranks are the default; the published figures are corrected by
   erratum, not rewritten (M-07, ADR-0026). No verdict or gate changed.
6. Which of the remaining drafts to review, freeze and run, and in what order.
   E-11 gates E-12. E-09 and E-10 need the tag sidecar first.
7. E-11 is not ready. Its third audit returned NOT_READY with three blockers,
   which are not yet applied; a fourth round applies them and audits again
   ([status](research/north-star/README.md)).
8. The chance-creation floor. The Wyscout estimator shows chance creation as a
   number from 1,800 minutes. On the declared population the reliability there is
   0.699, under the 0.70 number threshold, and 0.723 at 2,250 minutes; 53 point
   estimates are served with the signal "limited". The floor sits in a hashed
   registry entry and was not changed. Whether it should rise is the owner's
   decision (M-08).

## EXACT NEXT COMMANDS

To run the committed product from the prepared workspace:

```powershell
uv run ruff check galactico tests
uv run pytest -q
npx playwright test e2e/smoke.spec.js e2e/labs.spec.js e2e/alternatives.spec.js e2e/tradeoff.spec.js e2e/repairs.spec.js e2e/squad.spec.js e2e/transfer.spec.js
uv run python scripts/check_licensing.py
git diff --check
git status --short
git log --oneline origin/main..north-star
gh run list --branch main --limit 3
uv run uvicorn galactico.api.player_lab:app --host 127.0.0.1 --port 8090
```

Open `/`, `/match?id=2565907`, `/xi`, `/squad` or `/transfer` on that server. Check
whether a local server already listens on port 8090 before starting another. For a
fresh checkout, follow README's fetch/prepare steps; Transfer Lab needs
`scripts/prepare_planning.py` as well. Do not redownload/rebuild merely to resume.
Set `GALACTICO_E2E_PORT` to run a browser spec on a private port. Running
`e2e/labs.spec.js` or `e2e/screenshots.spec.js` rewrites tracked screenshots:
`git restore docs/screenshots` unless the change is intended and inspected.

Next research reproductions (not unfinished release work):

```powershell
uv run python experiments/run_xi_backtest.py --since 2018-03-01
uv run python experiments/run_match_score.py --competition Spain
uv run python experiments/run_match_score.py --competition England
uv run python experiments/run_optimizer_curse.py
uv run python experiments/run_lineup_transport.py
uv run python experiments/run_partial_history.py
```

England requires its public corpus. New learned utility or role-transition models
need a protocol before confirmatory evaluation; do not tune to the 12-match window.

## EXACT NEXT FILES

For the planning work, in the order to read them:
`docs/research/north-star/ROOT-DECISIONS.md` (the rules the build ran under; its
sections on tools that were not built are plans), `DECISIONS.md` ADR-0018 to 0027,
`galactico/optimization/squad/kernel.py` (every new exact tool goes through it),
`galactico/api/runtime.py` and `shell.py` (every new route and page goes through
them), `galactico/api/planning.py`, then the two routers and pages.
`docs/research/north-star/protocol-drafts/`: five drafts and how a draft becomes a
protocol. Nothing there may be cited as a result or wired to a page.
`galactico/domain/verdicts.py`: ships empty. Registering a protocol adds a record
with its hashes; a LOCAL-tier record can label and can never gate.

`experiments/preregistered/E-08-partial-history/analysis.md` and results.json:
completed and independently reviewed; do not rerun to resume or tune after the null.
Implemented
pure interfaces: partial_history.partial_rows(panel, config) -> (rows, audit);
partial_evaluation.evaluate_study({league: rows}, config) -> aggregate diagnostics.
Future predictive claims require a new rationale and fresh permitted evidence;
these coefficients/estimates do not enter Player Lab or XI Lab.

`experiments/preregistered/E-07-lineup-transport/analysis.md` and `results.json`:
retain the coverage failure and unchanged thresholds. E-08 is already executed;
do not repeat its design stage or bypass individual Player Lab evidence gates.
`galactico/validation/transport.py`, `transport_forecast.py`, `forecast_evaluation.py`:
reuse pure tested windows/scoring; new evidence pooling needs a new implementation
and protocol. Existing opening histories intentionally include early observations
that did not themselves pass the later evaluation floor.
`galactico/optimization/historical.py`: deployment transport, sample/availability
limits and fixed-xT uncertainty require research, not undocumented coefficients.
`docs/research/XI-EQUIVALENT-ALTERNATIVES.md`, `galactico/optimization/xi/solver.py`,
`web/xi.html`: exact diverse-equivalence exploration is complete.
`docs/research/XI-PROGRESSION-UNDER-FLOORS.md`, `galactico/optimization/xi/tradeoffs.py`,
`tests/test_tradeoff_oracle.py`, `e2e/tradeoff.spec.js`: the separate epsilon-constraint
point query is now complete too. Neither feature certifies a full Pareto frontier,
robustness or general football utility. Future policy comparisons/frontier work
must declare their additional decision claim, not silently change these solvers.
`galactico/match_lab/model.py`: team descriptors can feed an opponent requirement
experiment only after a reliability/meaning audit. No automatic opponent adjustment.

## AGENT RESULTS NOT YET INTEGRATED

From the 9 October build, held by the owner outside the repository because they
are long, partly raw and include counts derived from the local-only corpus: eight
subsystem maps, six method reports, two structure-only corpus audits, an
independent critique, and full specifications for the squad and transfer tools
(built), the data and API layers (built except the tag sidecar), and the matchday
pages (the shell is built; Opponent Lab and the XI additions are not). The
decisions those documents led to are in `docs/research/north-star/` and
`DECISIONS.md`; the specifications themselves are not needed to work on what
shipped.

Before that: none. E-08, equivalent-XI and hard-floor query council/core/API/UI/oracle work is
integrated. Recovery agents' work and fresh release review are complete. Root owns
the final push/CI check; no agent retains an exclusive unfinished implementation.
