# Known limitations

This is the release boundary, not a list of caveats attached to a stronger claim.
When a limitation changes, preserve the experiment in `docs/research/`.

## Data and licensing

- The hosted laboratory uses the public Pappalardo 2017/18 corpus, not a current
  event feed. No licensed current-season event source is integrated.
- StatsBomb remains local-only under the repository's enforced provider posture.
  Its data is not served, and no number derived from it may be. Player Lab serves
  two things formed from it, as words: the external-replication label of each
  construct and the Metronome Fit conclusion. They stand in the "Why only five?"
  view with the provider's logo, the data-source credit and a link to each research
  note. The links lead to the notes on the default branch, which show the logo only
  once that branch holds commit `b7bc919`. The check that no served string holds a figure
  formed from it reads four replies, not every route.
- No FotMob, SofaScore, WhoScored or unlicensed Opta-proxy ingestion exists.
- UEFA is reference-only: systematic collection and model use are prohibited.
  LIVE is not implemented and has no physical axis without a lawful licensed feed.
- Historical vendor/current-squad reconnaissance is a dated research result, not
  evidence that no new lawful source can ever exist. Recheck terms and coverage
  before any new provider is implemented; do not weaken the typed guard.

## Match Lab describes events, not total performance

- Pappalardo supplies shot locations but not xG/xA. Those fields are unavailable,
  not backfilled. Some body-part tags mean head **or body**, not necessarily header.
- Threat flow is positive completed-pass xT in period-aware five-minute bins.
  It is not momentum, net possession value, calibrated match control or chance
  quality. Repeated advances can accumulate positive gain.
- Match xT uses a retrospective full-season surface. It must not be reused as a
  pre-match predictor; XI Lab independently refits using strictly prior dates.
- Pass recipients are inferred from adjacent same-team on-ball events, elapsed
  time and endpoint proximity. Missing/ambiguous links are not observed passes to
  a known receiver. Node locations are pass origins, not average tracked positions.
- Event action counts are not tracking touches. Pass-origin shares are not
  off-ball occupation, heatmaps of all movement or intrinsic tactical preference.
- Season reliability does not become confidence in an individual match. Player
  cards report component observations/estimates, not persistent ability.
- A registry construct is served on a player row only inside the context its
  registry entry declares ([ADR-0025](DECISIONS.md)). In the 38 listed matches that
  withholds five quantities on each of the 76 goalkeeper rows: the card prints the
  reason and no number. Recorded counts and team rows are not gated. The
  estimator's minutes floor is not applied either: these are match totals, and a
  player-match of any length carries them.
- Match minutes are nominal reconstructed exposure, not exact on-field duration.
  Recorded red/second-yellow dismissals suppress the unresolved minutes value;
  the original nominal value remains provenance only. Event totals are unaffected.
- No overall match rating was identified. Accounting is the existing xT baseline;
  broad-role standardization remains highly correlated with it in Spain and
  England. This rejects those candidates, not every imaginable scalar
  ([E-05](docs/research/E-05-match-score.md)).

## XI Lab is a conditional requirement model

- The default objective minimizes declared structural shortfalls. It does not maximize
  wins, forecast the counterfactual result or identify universal football quality.
- Madrid slot eligibility is a versioned manual rule. No player-by-role uplift,
  learned formation inference, pair chemistry or continuity value enters the solve.
- Only positive pass-xT rate and experimental left/right wide-channel pass-origin
  rates enter the current scenario. Side rates are not validated team width.
  Chance creation, rest defense and goalkeeping quality remain unmeasured.
- The 6 May snapshot has 16 eligible players. Isco/Modrić fall below the Wyscout
  creation floor; a player below the 900-minute outfield sample gate cannot enter
  merely because a football observer expects him to play. Keeper quality does not
  distinguish eligible keepers, so tied selection must remain visible.
- Availability means observed prior squad plus sample/eligibility rules. Injuries,
  suspensions, fitness, training and the manager's private information are unknown.
- Additive historical per-90 rates assume players repeat deployment-dependent
  behavior together. That assumption is not a forecast or causal transport model.
- Default minima and fixed normalizers are heuristic historical starting-XI
  medians. Their choice affects the answer; editable requirements expose policy
  rather than remove it.
- Optimality applies to the recorded integer-quantized problem. Raw values may
  differ at rounding tolerance; unproven feasible solutions are not optimal.
- The shipped solve's infeasibility diagnostics are not a minimal conflicting set.
  XI Lab's conflict panel is the separate, certified answer: a deletion filter over
  the declared floors, locks, exclusions and slot coverage, each removal proved by an
  INFEASIBLE solve, in the arithmetic of the solve it explains (half-even for the
  Satisfy rule, conservative for a hard-floor query; ROOT 2.7 X2). A test that times
  out or is refused keeps its declaration and marks the set as not proved minimal;
  it is never read as absence. No constraint is silently relaxed.
- After the corpus files are rewritten in a running server, the conflict panel can
  explain a model built from the files as they are now while the main solve above it
  still runs on `decision_lab.snapshot`'s older copy (the next item), so the two can
  differ, and the panel can even find the declarations feasible.
- XI Lab's snapshot (`decision_lab.snapshot`) is cached per process on the match id
  and world count only, so after the corpus files are rewritten the shipped XI routes
  keep serving the snapshot built before, until the server restarts. The planning
  routes key their builds on the identity of the files they read and do not.
- The development backtest loses to prior minutes: 6.00 versus 6.83 actual starters
  out of 11. Manager agreement is not correctness, and tied representative choice
  can change overlap. See [E-06](docs/research/E-06-lineup-requirements.md).
- Equivalent alternatives share the certified quantized objective, not necessarily
  identical raw requirement values or football value. Sequential diversity cuts
  do not enumerate all optima or find the largest possible diverse set. Search
  timeouts are incomplete, not evidence that no more alternatives exist.
- The separate hard-floor query maximizes historical positive-pass xT only, not
  football quality or team output. It can omit famous finishers or defensive players
  because those functions are absent from its objective. A maximum is not a
  frontier; the frontier explorer lists the nondominated sums of declared
  requirements at the shipped quantisation, never a ranking. Larger side-origin
  counts are not merit. Any frontier with the shipped requirements needs the
  experimental opt-in, because only progression is not experimental.
- With declared floors, XI Lab's ranges and frontier are taken over the conservative
  integer model: an XI that meets a raw floor with less than `(a_r + 1)/100000` of the
  club median to spare (one unit for each place counted and one more) can be left out
  of every range and point.
- Its conservative floor rounding guarantees raw-floor satisfaction for returned
  assignments but can reject raw-feasible boundary XIs. INFEASIBLE and OPTIMAL
  concern that integer model, not the full unquantized problem. The numerical
  rounding allowance is not statistical uncertainty; no stability bands transfer
  from the main pitch to this separate response.
- Joint evidence availability is restrictive: E-07's temporal forecast study had
  only 3 eligible development lineups when all ten outfield starters had to meet
  the 900-minute floor. No forecast model could be fitted under the frozen rules.
  This is a coverage failure, not proof that lineup information is useless.
- E-08's aggregate partial-history follow-up solved the coverage problem, but
  development-only selection preferred context without individual-history residuals.
  This specified model did not establish incremental prediction. It does not show
  that players have no effect; reused evaluation periods are not fresh validation.
  No sparse-player certification or learned XI weights follow from aggregate coverage.

## Uncertainty and selection bias

- Shared match worlds preserve teammate/construct covariance from that resample;
  they do not model every dependence, tactical change, availability state or xT
  surface uncertainty. Historical worlds hold the pre-cutoff xT surface fixed.
- The browser uses only 12 worlds, an explicitly coarse exploratory summary.
  Necessary-to-possible frequencies include equally optimal XI ambiguity. They
  are not confidence intervals or probabilities that a player is better.
- Frequencies condition on fully certified feasible worlds. Missing joint exposure
  discards a whole world; incomplete solves and discarded worlds are recorded. In
  Transfer Lab a world in which it is proved that no XI exists without the
  candidate, or with him, is counted on its own: it is neither compared nor set
  aside.
- CORE/FAVORED/CONTESTED/FRINGE cutoffs are product conventions, not universal
  scientific boundaries. A user lock is a constraint, not statistical evidence.
- The old three-to-five stable-core result and 3.5%/9.9% inflation figures were
  illustrative rating-noise experiments, **not current XI Lab results**. The current
  requirement-model simulation confirms selection optimism, and no football-calibrated
  correction ships ([M-05](docs/research/M-05-optimizer-selection-bias.md)). XI Lab's
  declared-risk modes (the tail of k of B resampled worlds, the worst world, minimax
  regret) select for stability against resampling of the historical matches, not
  robustness to states of football; E-13, which would test whether they reduce
  selection optimism, is a draft and has not run. The worst world grows with B, and a
  declared problem whose encoding would overflow is refused. The risk menu offers 12 and
  40 worlds. The 40-world option was added after its solves were timed on the corpus
  ([ADR-0030](DECISIONS.md)): on the two Madrid scenarios, in both formations, with and
  without the opt-in, at the default minima, every call was certified and exact, a warm
  request took at most 0.48 s, a cold first request at most 1.02 s with its snapshot
  build, and the timing process, which held one router snapshot at a time, peaked at
  653 MB. The router keeps up to four, and a server's footprint with 40 worlds on offer
  was not measured. Four slots no longer hold every scenario and world count, so moving
  between them can evict a snapshot and build it again (0.76 to 0.90 s in that run).
  Other declarations were not timed; a solve that runs past its route's budget is
  reported as not certified.
- You never observe the unplayed XI. Observational associations or manager
  agreement cannot establish that a proposed lineup would have won.

## Reliability is not validity or utility

Metronome Fit was more reliable on split halves than expected threat and still
measured touch volume. A repeatable number can repeat the wrong thing. Every new
construct must survive discriminant and baseline checks; passing those still does
not establish decision utility. The figures are in
[E-01](docs/research/E-01-metronome-fit.md), which names their source.

Defensive quality, finishing skill and goalkeeper quality have no validated
shipped estimator here. This is a limitation of the current evidence/model, not a
proof that all possible data regimes can never measure them. Cross-provider
pooling remains guarded; the Bridge remains unvalidated.

## Squad Lab and Transfer Lab describe a gated model, not a squad

- Every number is exact arithmetic on declared inputs: a role-slot template,
  requirement minima, an eligibility rule set and the evidence gate. None says
  whom to keep, sell or sign. Both lists are grouped first by the categorical
  outcome of the exact computation, in a fixed sequence; inside a group the order
  is the name, or one declared recorded quantity the user chooses. That grouping is
  as near to an ordering by a solver output as these pages come. With a single
  requirement in force, which is the default, Transfer Lab's outcome groups are a
  threshold on that one recorded rate, its break-even carry-over fraction restates
  the same rate, and that key lists a group in the order of the modelled change.
  The page says so above the list.
- Planning surfaces use the **progression requirement only** by default. The two
  side pass-origin requirements are EXPERIMENTAL and enter through an explicit
  opt-in. Finishing, defending, goalkeeping, physical profile, character, fee,
  wages, contracts and availability are not in the data. A player who mainly
  finishes, defends or keeps goal contributes little to a passing requirement by
  construction: removing Cristiano Ronaldo leaves the declared shortfall where it
  was. That is a statement about what the model contains.
- Depth, tight slot groups and "leaves no fieldable XI" are properties of the
  gated candidate set. Most of Madrid's thinness is produced by the 900-minute
  gate and the manual eligibility rules: at the end of 2017/18 it takes three
  absences inside one slot group before no XI can be fielded, and two after the
  gate. Of the 171 pairs of absences, 6 leave no XI, and every one of the six is
  attributed to the gate. Omitted players are named beside every count. Goalkeepers are exempt from the gate by the shipped rule, so a keeper
  with 90 minutes counts as depth.
- Outside Real Madrid, eligibility is the provider's four-class position code,
  labelled unreviewed. It does not tell a left back from a right back. Depth under
  it mostly restates the position code.
- There are no absence likelihoods. Stress is a scenario table over sets of
  players, not a risk estimate. Stress over resampled worlds is not implemented.
- A role brief lists what an addition at a slot would have to supply for the
  declared minima to become reachable. It is the explanation of an exact solve,
  in conservative integer arithmetic; a raw-boundary case can read as not met.
- **Whether a recorded rate repeats after a club change has not been tested.**
  Candidate values are rates recorded at another club, carried over unchanged.
  The break-even carry-over fraction is the smallest share of those rates that
  must carry over for a declared conclusion to hold; it predicts nothing. Seven players in the five-league
  corpus have 900 minutes at each of two clubs, none involving Real Madrid.
- Candidates from another league are valued on the destination league's surface
  and are not adjusted for league strength. Nothing in one season of five
  separate leagues identifies such an adjustment.
- A player whose latest club is outside the five leagues is invisible to the
  universe, and anyone with a prior appearance for the destination club is left
  out of it, including the few who had already moved on.
- Screening hundreds of candidates and reading off the most favourable result
  selects estimation noise ([M-05](docs/research/M-05-optimizer-selection-bias.md)).
  The response states how many were screened and shows a pool-median reference;
  no correction is applied.
- On the flagship the squad meets the default minimum with or without Cristiano
  Ronaldo, and the league's 75th and 90th percentiles of starting-XI progression
  (1.953, 2.378) lie below Madrid's own median (3.006). So no candidate can lower
  anything until a minimum is raised by hand. Transfer Lab then states, for each
  requirement in force, the sum of one XI the solver found (3.8140 here, with or
  without him) and a ceiling no XI exceeds (3.8143), so the minimum is not a
  guess. The largest sum lies between the two and is not computed. The shortfall
  model rounds each rate and the minimum to 1/100000 of the club median, so a
  minimum entered between the two numbers, or just under the first, can be
  answered with a shortfall or with none: with him excluded, 3.8141 is answered
  as reachable and 3.8143 with a shortfall of 0.00006. Each requirement is
  maximised on its own: the two numbers do not say several can be reached
  together, neither is a target, and Squad Lab does not show them yet.
- With the experimental opt-in, both side requirements are in force together.
  One cannot be declared without the other.
- Whether a set of absences that leaves no XI is attributed to the gate, to the
  user's own exclusion or to the eligibility rules is decided by counting the
  players each of them removed from the short slot group, not by an exact cover. It agreed with an exact
  assignment check wherever the two were compared (160 cases in review, 1,154
  across all 98 clubs in the final audit), and could be wrong on a contrived
  squad. Neither comparison is a committed test.
- Transfer Lab fills the break-even column one candidate at a time. A pool of
  several hundred (another league included) takes tens of seconds. Superseded
  requests are dropped by the page, not cancelled on the server.
- Squad Lab's single-absence rows print the change in the least declared
  shortfall without each player, under a first group of rows that raise it.
  That is the question the tool answers; it is conditional on the declarations
  and says nothing about the player. The stress claim also names the absence set
  with the largest rise, which for sets of one is one player. The same pattern was
  removed from Transfer Lab's list and left here.
- Some text is written in the two pages and not sent by the server: headings, keys and
figure notes; fixed labels in front of a served value; fixed words chosen by a served
token, a missing value or an empty list (for example, in Transfer Lab holds, fails or
not determined for a cell of the carry-over grid, "foot not recorded" and the deficiency
state printed from its token; in Squad Lab the two names of a requirement that is not in
force, "No available player." and "Nobody."); and descriptions of figures for assistive
technology, which put fixed words around served values. Transfer Lab's two
  buttons and its status lines carry a served count inside words written in the
  page. Every other sentence that depends on a reply is the server's, printed as
  sent, and the header of each page lists what the page assembles.
- This is a single-user laboratory, not a service. Two corpus builds and two
  enumerating computations run at a time; a request that has waited five seconds
  for a place is answered 429. At most sixteen planning requests are past the
  result-cache lookup at once, and the seventeenth is answered 429 at once, with
  `Retry-After: 5`. Ten different clubs requested cold at the same moment got six
  replies and four refusals. A budget does not interrupt a corpus read, so a
  request can last its budget plus one build. A request identical to one in
  flight, or one that needs a build in flight, waits for it with no time limit of
  its own and holds one of the sixteen places and a worker thread until it ends.
- A failure raised inside pandas or numpy as a plain `ValueError` is still
  answered as a 422 carrying the library's sentence. Only file errors and Arrow's
  own are told apart and answered 503.
- The 404, 422 and 503 states of the two pages are tested at the API and not
  in the browser. The 429 state is tested in both, with a fulfilled reply. A real deadline was never reached on the shipped
  scenarios; those states are tested by rewriting replies.

## The tag sidecar holds facts, and nothing has read it yet

- No column of the sidecar is a construct. A tag is the provider's judgement,
  recorded as the provider recorded it.
- No experiment and no page reads it yet. E-10, registered and not run, will read its
  cards, own goals and goals and the sheet's dismissals through functions not yet built;
  the E-09 draft will too. Before E-10's registration the root's structure-only counts
  read its cards and the sheet's red-card minutes on the corpus and computed no outcome
  ([ADR-0031](DECISIONS.md)).
- Its match table leaves out extra-time and shootout scores: for a cup match that
  went past ninety minutes the two scores are the ninety-minute score.
- `verify` shows the tables are the ones the manifest records. It does not show
  that the module as it stands built them; the manifest's `builder_source_hash`
  does.
- CI builds Spain only, so the corpus tests of the other six competitions skip
  there.

## Registered or drafted, not run

Five protocols are written: new shot and defensive-location candidates (E-09),
whether where a team concedes is a property of the defender (E-10), provider agreement
on the 100 double-coded matches (E-11), whether rates survive a club change (E-12),
and declared-risk selection against selection optimism (E-13). E-11 and E-10 are
registered under `experiments/preregistered/`; the other three are drafts under
[`docs/research/north-star/protocol-drafts/`](docs/research/north-star/README.md). E-11 went through three
rounds of review, revision and independent audit on 9 October 2026; the third audit
returned NOT_READY with three blockers. A fourth revision of 13 October applied
them, and five more audits that day found one, one, two, two and three blockers; a
ninth revision applied the last three, a verification found them resolved, a tenth
revision applied its follow-ups, and a ninth audit found eight of nine scopes ready and
one blocker, which an eleventh revision applied. A tenth audit returned READY on the
eleventh revision; a twelfth and a thirteenth applied consistency items that change no
token, each verified to add no blocker. E-11 was registered on 14 October 2026
([ADR-0029](DECISIONS.md)); its pipeline is built on synthetic data and its acceptance
stamp committed, and it has not run. E-10 was attacked by three reviewers and audited
three times; the third audit confirmed no blocker, and verifications of its fourth
revision and of its alignment with the root's rulings for Opponent Lab found none. It was
registered on 19 October 2026 ([ADR-0031](DECISIONS.md)); its pipeline is not built,
and its results commit waits for E-09's registration, since the record it would show for
three subjects stays withheld until an E-09 record exists. E-11's sixteen records read
E-11 · RECORD ONLY · NOT RUN, E-10's seven read E-10 · RECORD ONLY · NOT RUN, and every
other badge on a planning page reads RECORD ONLY · NOT TESTED. The other three are drafts
with no pipeline. No outcome of any of the five has been computed.

## Found by the October reconnaissance and not repaired

Four were then decided and repaired on 9 October, and a second audit found each
repair incomplete; [ADR-0027](DECISIONS.md) records what was done. A construct is
published only inside the context it declares, in Player Lab and on Match Lab's
player rows ([ADR-0025](DECISIONS.md)). Rank correlations use average ranks, with an
erratum for the published figures ([M-07](docs/research/M-07-rank-ties.md),
[ADR-0026](DECISIONS.md)): no verdict or gate changed. Two licence findings are
recorded in [LICENSING](LICENSING.md): a document that prints analysis formed from
StatsBomb data names the source and carries its logo, as clause 1.4 of its
agreement requires, and so does the one served view that does, with one frozen
exception recorded there; and FPL, ClubElo and football-data.co.uk are reference
only, since the terms read that day do not support the hostable posture two of
them were given. The rest was not changed.

- StatsBomb delisted 272 of 306 Bundesliga 2015/16 matches on 26 May 2026. The
  files still download. The four-league posture here is unaffected; a fetch that
  enumerated the events directory instead of the match index would ingest them.

- The legacy `REGISTRY` in `galactico/domain/metrics.py` still states the
  superseded on-ball-action denominators and names providers that match no
  adapter. Nothing in production reads it.
- The Wyscout columns of the published Stage 1C table do not reproduce from the
  corpus as it is: three of the four were computed with one xT turnover recipe and
  the fourth with another. On a rerun 72 of the 220 values of that half differ, in
  nine cells (the three xT-weighted constructs in Spain, England and France), by up
  to 0.00098; the nine ordering figures among them move by up to 0.000444. Two
  printed cells of the report would read differently at its own precision, both
  on the Wyscout side: the La Liga progression mean (0.1707 to 0.1709) and the top
  of the chance-creation confound R² range (0.13 to 0.12). The runner lists the
  differences and no longer writes over the record. Found while correcting the
  rank ties ([M-07](docs/research/M-07-rank-ties.md)); not corrected.
- Three approximate figures of the August decision log have no source in the
  repository: two in ADR-0004 (the share of events that are carries, and a
  similarity of the two providers on identical matches) and one in ADR-0008 (a count
  of goal events). They read as published literature and were left as they stood.
  If any was computed here from local-only data, DECISIONS.md prints it without the
  credit that would need.
- E-01's two rank correlations predate the audit code. No script in the
  repository produces them, so the tie correction says nothing about them.
- `experiments/external_replication.json` carried the StatsBomb half of Stage 1C
  as machine-readable aggregate figures from the day it was published until
  9 October 2026. It is out of the tree and remains in the history.

- The evidence ladder of ADR-0001 is composed on the planning surfaces only.
  Player, Match and XI Lab still carry their own strings.
- Three xT turnover recipes are live (Stage 1B, Player Lab, XI Lab). Surfaces
  differ by up to 0.004 per cell. They were not unified: doing so moves shipped
  numbers.
- Lineup minutes are nominal on a flat 90-minute clock; about 250 starters
  sent off before the 90th minute across the five leagues are credited 90 minutes
  or more (256 or 258 depending on the clock convention; no committed script
  produces the count).
- The `ROBUST` versus `ROBUST_WITH_SHIFT` boundary is written nowhere: `width` and
  `half_space_share` received different labels, and no rule says what size of shift
  separates them. The two La Liga shifts and the labels are in
  [Stage 1C](docs/research/STAGE-1C-EXTERNAL-REPLICATION.md), which names their source.

## Found while repairing the second audit and not repaired

- **Open owner decision: the chance-creation floor.** The Wyscout estimator shows
  chance creation as a number from 1,800 minutes, and the registry note beside that
  floor says the construct clears the number grade only near 1,800 minutes. Both
  were chosen on the published pool, which included goalkeepers. On the declared
  population the reliability at the floor is 0.699, under the 0.70 number
  threshold. It is 0.723 at 2,250 minutes, and the lower bound Stage 1B graded on
  is 0.668 and 0.686 at those two floors. So 53 point estimates are served with
  the estimator signal "limited". The floor and the note sit in a hashed registry
  entry and were not changed, and the API still serves the note as text on the
  construct and on its 319 outfield rows; the page does not print it. Whether the
  floor should rise, and to where, has not been decided
  ([M-08](docs/research/M-08-reliability-pool.md)).
- Some rows under "Declared by you" were declared by nobody. Transfer Lab lists
  the leagues searched and the long-list filters there when the reader chose no
  other league and no filter, and Squad Lab the absence-set size its page sends by
  default. A request sent straight to the API that names no scenario and no
  formation is answered for the flagship and 4-3-3, and those two rows are listed
  as declared too. The shipped default minimum is no longer among them: it is a
  row of the computed ledger, marked as the shipped default.
- Identical requests behind one that is refused for a long-computation place are
  refused in turn, each after its own five seconds. With both places held for 26
  seconds, four identical requests were refused after 5, 10, 15 and 20 seconds;
  with the places held for 9.5 seconds the first was refused after 5 and the other
  three were answered.
- Player Lab prints the interval under a quality value to three decimals, whatever
  the size of the value. 14 chance-creation cards read "0.000–0.000": on 13 the
  value and both ends are exactly zero, and on one the ends differ below the third
  decimal. 14 progression-per-action cards print two ends alike that differ, and on
  93 of the 319 the two printed ends are the same or 0.001 apart, under a value
  shown to four or five decimals.
- The Player Lab page still writes sentences from served values: the hero line of three
counts, the footer (player count, minutes floor, artifact key, build time), the line
under INSUFFICIENT SIGNAL (the floor and the minutes played), the share sentence of a
style row and its two reference lines, the titles of the channel bar, the line under a
withheld channel bar (page words before the served reason), and the leader's name joined
to the server's sentence in a comparison. For the
  comparable-position reference it subtracts the median from the value itself.
  Player Lab replies do not pass `runtime.finalize`, and they serve words the copy guard
  bans in a planning reply: the family value "quality" on every quality row, "grade" in
  the note of the chance-creation estimator, "ranking as quality" in the declared
  contexts of the two style constructs, "no better direction" in a style comparison, the
  labels "robust" and "robust with shift", and "fit" in Metronome fit.
- The declared-context rule gates Match Lab's player rows and nothing below
  them. The timeline and the passing network still carry the xT gain of passes a
  goalkeeper made: in the 38 listed matches, 739 of 2,797 timeline events by a
  goalkeeper have a positive gain, 26 of them at the TACTICAL level, and 306 of
  the 378 network edges from a goalkeeper do. A match total withheld on a
  goalkeeper's row can also be had by subtraction: in all 76 team rows the
  completed passes equal the sum of the player rows, and a team row is not gated.

## Pages that moved or were removed (ADR-0033)

- Player Lab moved from `/` to `/player`. On the local app an old link to `/` with `?player=`
  or `?view=` answers 308 (permanent) to `/player` with the same query; a bare `/` now opens the match
  board. Since ADR-0034 the page keeps the view and the player in its URL.
- The hosted site's `/` was the lineup studio; it is now the match board, as on the local app.
  The studio is at `/lineup`. The hosted site serves no archive page, so an old link to `/`
  with `?player=` opens the match board there rather than a 404.
- The scouting demo (`/match-centre/demo`, `web/matchroom-demo.html`) is removed: it printed
  invented figures beside real players' names. Its address answers 308 (permanent) to `/match-centre`, and
  `/static/matchroom-demo.html` is a 404. Nothing replaces its transfer shortlist on the
  current-season side.
- The labs kept their layout under ADR-0033's look; ADR-0034 replaced it, answer first, with
  the research tools, the evidence ledger, absence stress and the provenance record closed on
  arrival. The e2e suite checks that the answer comes before the primary visual and above the
  fold; it has no gate on a page's total height.
- A label drawn in an SVG is kept at 12 px on screen by `web/site.js`, which enlarges it in the
  drawing's units. At 12 px some labels that sat apart at their old size touch on a phone: the
  percentile labels of a reference strip when two percentiles are close. Two drawings leave a
  label to the text beside them on a phone instead: the depth pitch leaves slot names to the
  depth list, and Match Lab's threat flow labels every half hour. The XI page's pitch labels its
  places in HTML since ADR-0034.
- The depth pitch's marks are smaller than 24 px on a phone (about 13 px apart) and have no
  wider pointer area, which would cover the next mark. The depth list beside the pitch selects
  the same players with full-size buttons.
- The navigation lists a page only where the serving app answers its route. The hosted site
  therefore shows no Squad & signings destination and links Players to the scouting page and
  Lineup to the studio; the archive pages appear only on a local install with the corpus. On
  both apps a destination opens its current-season page first (ADR-0035).

## This season's pages, answer first (ADR-0034)

- La Liga has no free fill. OpenFootball's La Liga file lags behind play and OpenLigaDB has no
  current La Liga season, so the La Liga table says where its results stop ("Table after
  matchday N of M", with the count of later fixtures without a result), its match reports name
  no scorers, and goals by opponent does not offer La Liga. Nothing missing is estimated.
- A fixture without a result may not have been played: a postponement looks the same in the
  free files, so the pages say "without a result", never "not yet played".
- The Champions League comes from OpenLigaDB alone. Its table is the league phase, ordered by
  points, goal difference and goals scored, as the other tables are; the competition's own
  tie-breakers are not applied. The knockout rounds are mapped from OpenLigaDB's stage names and
  have not been checked against real knockout data, which the feed has not published yet.
- A Bundesliga or Premier League result filled from OpenLigaDB depends on the club matching of
  the goal explorer (`goal_scout.verify_fixtures`); a fixture whose clubs or matchday do not
  match keeps no result.
- A scorer listed under two names is joined only by the declared rule (`merge_scorers`: the same
  name, or the same surname with a matching first name, initial or a nickname from a short map);
  different initials are never joined, and a short form that could be two players stays apart
  with a note.
- Lineup places a player within his position by the first position in his Wikipedia infobox
  (side, and attacking or defensive for a midfielder). Where the batched MediaWiki request is
  refused (it answered 429 from the build environment), each article's source is read, a few at
  a time; a player whose article does not load stands by shirt number, and the key line says so.
- The proposed XI's key (most 2026/27 appearances in each position) counts appearances in every
  competition as Wikipedia lists them; it says nothing of form or fitness.
- The Lineup's next-match card links to the opponent's goals only where the free goal feed
  covers the competition, so a La Liga fixture has no such link.
- Goals by opponent no longer offers the teammate side-by-side comparison or the "Opponent
  strength" control (cut with La Liga in ADR-0034).
- Match reports link to Check against targets only for the matches an XI scenario is prepared
  for (two of the season's Madrid matches); the others have no link rather than a link to
  another match's scenario.
- Signings no longer carries the full targets editor. Targets arrive by the menu, the link from
  Squad depth, the "Compare them against a gap" leads, or Squad depth's editor (its link carries
  them over); the two wide-channel experimental targets reach Signings only through a link with
  `optin=1`. On a wide screen its candidate panel scrolls inside itself.
- The archive pages are still served only on a local install with the corpus; the hosted site
  says so on their addresses.

## The second pass (ADR-0035)

- Kick-off times are turned into one instant by the European summer-time rule written out in
  `match_centre/kickoff.py` (UK time for OpenFootball's Premier League, Central European time
  for its other leagues), not by a time-zone database. A source that changed the zone it writes
  in would be shown an hour out until the table of zones is changed; a time whose zone is not
  known is shown as published, and the page says so. Server sentences keep Madrid's dates.
- A Real Madrid scorer takes the squad list's name only where the feed's name matches one squad
  player by surname and first initial (or exactly, once accents and case are set aside). Two
  squad players with one surname and initial both keep the feed's names; a player missing from
  the squad list keeps the feed's name. Other clubs' scorers are named as the feed names them.
- When the shared OpenLigaDB download serves a season from its cache, the feed's warning for a
  stale snapshot no longer reaches the Goals notes; the data is still dated by "Results
  through".
- On a phone the Matches report (goals and two form tables) comes before the board of the day,
  which then starts about 1,000 px down the page.
- "Analyst tools" (importing your own event file on Lineup) is offered only on a local install.
- Under Advanced on the XI page, the ranges and frontier tables still print the lab's
  four-decimal texts: the kit prints only digits the server sent, and `/api/xi/*` is frozen.
  A few of the lab's own sentences remain inside the opened Advanced answers of Squad depth
  (the brief and the absences), and Signings' closed "Advanced: resampled seasons" still says
  "Left midfield" in its world statement.
- Signings opens its pool for the default La Liga set at start-up; another combination of
  leagues builds its pool on its first request (about 2 s once the league frames are loaded).
- Where nothing makes a gap at a position, Signings' candidate panel waits for a row to be
  chosen: opening the first row by minutes would put one candidate first.
- At 390 px the native match select of Match reports cuts the result letter of the served phone
  label.
- Squad depth and Signings answer for Real Madrid's 2017/18 squad, on a local install only:
  nothing on either app says where the 2026/27 squad is thin. "Who could cover a position?" is
  answered inside the squad by Squad depth's "Who can play where" row and outside it by
  Signings' list of every eligible player in one declared factual order; where the targets
  leave no gap there, that list has nothing to compare against and says so.
- The Table's La Liga sentence is in the past tense and dated by its matchday, because the free
  La Liga file stops weeks behind play; Madrid's current La Liga place is not known to the site.

## Wikipedia through the MediaWiki API only (Phase D)

- The Lineup reads its squad list through the MediaWiki API (`action=parse`, sent with
  `maxlag=5`), no longer from the rendered article. The list exists only as rendered HTML, so
  there is no second route to it: where the API turns the request away (a 429, or `maxlag` while
  Wikipedia's databases lag), the Lineup serves the last list it read, dated, or answers "The
  current squad list is unavailable." The infobox positions keep their fallback to each
  article's source.
- Real Madrid's season article has a second route: where `api.php` turns the `action=parse`
  request away, its facts come from `index.php?action=raw`. That route holds the statistics,
  cards, clean sheets, matches, goals and transfers, but not the squad list, which exists only as
  rendered HTML; the facts then say "The squad list couldn’t be read just now; the squad is left
  out." Wikidata has no second route: a batch that cannot be read leaves those players' height
  and place of birth missing.
- Wikipedia's API may turn this site's requests away; per-match appearances then wait for the
  next successful read. From the probe's environment `api.php` refused 21 of 29 requests and
  `index.php?action=raw` 13 of 77 (D4-B). The revision list has no second route, and a refusal on
  any of its pages loses the pages read before it, so the next read starts again from the
  season's first day; keeping the pages read and resuming is carried to the Real Madrid page's
  wave.
- A player's infobox is read under either spelling of each parameter (`nationalteam1` or
  `national_team1`, `club-update` or `club_update`), and an update stamp written as a signature
  ("22:03, 21 November 2026 (UTC)") is read as its UTC day. A stamp in any other form is no date
  (shown "—"), and a count is never shown without its stamp (B14).

## The season data layer (ADR-0036)

- No page reads it yet. Both apps build the season catalogue (football-data.org where
  `FOOTBALL_DATA_KEY` is set; OpenFootball, OpenLigaDB, Wikipedia and Wikidata) and every page
  still renders from the free feeds exactly as before; the season pages are its first readers.
  Without the key, or once football-data.org refuses it, no request leaves for it, and the
  catalogue serves the six competitions the free feeds carry, with OpenFootball's La Liga file
  as stale as it is.
- football-data.org's free plan delays its scores by an amount it does not publish, and gives no
  match minute. The delay is not measured yet: nothing was in play during the probe window.
  Until it is, a match in play is shown "In play" with the time the source was read, "Paused"
  never reads "Half-time", and the pages say that results may take an hour or more to appear.
- `playedMatches` counts the matches a player was named for, not the matches he played: it equals
  football-data.org's matchday-squad count for 19 of 19 Real Madrid scorers and Wikipedia's
  appearances for 13 of 19 (D4-B). It is never read (B1). Appearances come from Wikipedia, for
  Real Madrid only, and no leaderboard has an appearances column.
- A scorers list is asked for at 500 lines and says how many players the source lists with at
  least one goal; where the source lists exactly 500, one more line says that a player with fewer
  goals may be missing (B2). Nothing claims the list is complete. An assist the source does not
  record is missing (shown "—"), never 0.
- The key's ten requests a minute are shared with every other user of the key. A cold view past
  its cap (PLAN 3.6) is shown in part, with "Part of this page is still loading. Reload in a
  minute to see the rest." The shared cache tier (Vercel Runtime Cache) is off: its package is
  not deployed, and whether it works under the legacy `builds` key is unverified, so each
  instance starts cold.
- A match key carries its Europe/Madrid day. If the match moves to another day, its old key
  resolves only while a season resource that holds it is in the cache; otherwise it is a 404.
- Keys differ by mode. With no key, a match's key is built from the free feed's club names; with
  the key, from football-data.org's short names. `match(key)` resolves either form by the club
  rule, and a board id resolves too (with the key it lands on the football-data.org match).
- Joins are declared rules, and an ambiguous join is not made. A Real Madrid player whom the
  crosswalk cannot join uniquely (a shared date of birth and surname, or no infobox birth date)
  keeps his Wikipedia facts only, with "football-data.org’s record of this player couldn’t be
  joined to Wikipedia’s, so its facts are left out." A football-data.org name of one word is
  joined by date of birth and the Wikipedia name's first word, uniquely. A box of Real Madrid's
  season article that the club-name rule cannot join (the article writes an opponent as its own
  article is titled) is joined by competition, Real Madrid's side and the Europe/Madrid day
  (18 of 18 finished Madrid matches, against 14 of 18 by the club-name rule, D4-B).
- With no key, Champions League and Bundesliga scorers are counted from OpenLigaDB's named goals
  in finished matches, with no assists; the coverage line says how many goals are named. Premier
  League, Serie A and Ligue 1 goals get "The free sources this site reads don’t name the scorers
  of this match." In play, goal reports that disagree with the result are both kept, with a line;
  once the match is finished, disagreeing goal reports are not shown.
- A derived table (no key, or a date in the past) orders by points, goal difference, goals scored
  and name. A competition's official tiebreaks (head-to-head, fair play) and points deductions can
  differ. A match decided on penalties counts as a draw at its level result; where a source's
  result includes the shoot-out kicks (not level), the match is left out of every derived figure.
  Position by matchday is the table on the day of each matchday's last counted result, so a
  rescheduled match moves its matchday's point to the day it was played. Goal periods are drawn
  only where minutes are known for at least 80 % of the goals, and a goal report listing more
  goals for a side than the result is not used.
- A competition with several tables (a group stage) names each table's group; until the
  Competition page shows every group, the catalogue gives the first table with "This competition
  has more than one table; the first is shown."
- A club squad from football-data.org can be partial (one Champions League club lists a single
  player). A squad of fewer than 11 players is treated as "the source lists no squad for this
  club", never shown as the squad.
- The Copa Libertadores is a calendar season: the 2026 edition ends with the final on 28
  November, and the source lists no 2027 edition yet.
- A file at its plain address (the type, or a sheet a page links without a version) can be up
  to ten minutes old in a reader's browser after a deployment; the shell's sheets and scripts
  change address with their content and are never stale. A hosted page can be up to ten minutes
  old on the CDN, and up to an hour more while the CDN fetches it again.
- Unverified on Vercel, for the user to check on a deployment: whether `regions: ["fra1"]` is
  honoured with the legacy `builds` key; whether a Schedule sends its secret to the warm route;
  and whether the Runtime Cache works from Python.

## Product scope

No LLM invents a number or post-hoc tactical explanation. The frontend renders
server-computed assignments, constraints, deficits and uncertainty. Opponent Lab,
a Director's desk, learned embeddings, LIVE and VISION are not implemented. VISION's
intended target remains team shape, not player ratings.
