# Root decisions for the north-star build (binding on every agent)

Written by the root integrator after reading the whole constitution (README, VISION,
ROADMAP, DECISIONS ADR-0001..0017, VALIDATION, KNOWN_LIMITATIONS, ARCHITECTURE,
METRICS, DATASETS, LICENSING, docs/ASTRA-CHECKPOINT, the research notes) and the XI
solver core. Refine these; do not relitigate them. If you believe one is wrong, say so
explicitly in your output under "DISSENT" with the evidence, and still deliver a
design that satisfies it.

## 0. What "going further" means here

The owner's north star: a sporting director asks "We want to play a more aggressive,
possession-dominant 4-3-3 next season. Which players should we retain, which roles
are structurally deficient, and which potential signings would improve those
deficiencies most reliably within our constraints?" and the system helps answer it,
quantifies its uncertainty and shows its evidence.

The repository's own warning governs how we get there (docs/research/STAGE-3-QUESTIONS.md):
"Every arbitrary constant introduced at this stage would inherit the credibility of the
measurement work without having earned any of it." So the build has exactly three
kinds of deliverable, and nothing else is allowed:

1. EXACT COMPUTATION on a declared model (no new empirical claim). Certified, checked
   against an independent brute-force oracle, with a written decision claim.
2. PREREGISTERED RESEARCH that tests whether a number means what its name implies,
   with the product consequence of each possible verdict fixed in advance. Nulls ship.
3. PRODUCT SURFACES that render (1) and the verdicts of (2), and say what is unmeasured.

## 1. Non-negotiables (the constitution, restated as rules)

- R1 No overall rating of anything, ever. No per-player scalar that orders players by
  merit. Per-player outputs are vectors keyed by declared requirement, or categorical
  facts with an exact definition. Candidate lists are ordered by an explicit,
  user-visible, declared key and say so; ties stay ties.
- R2 Every number carries an evidence class and provenance. Composition takes the weakest.
- R3 Names describe the numerator. "Conceded final-third entries, left share", never
  "weak left side". "Vulnerability", "weakness", "dominance", "momentum", "fit score",
  "quality", "best" do not appear as labels on unvalidated quantities.
- R4 Reliability is not validity is not decision utility. New constructs go through the
  lifecycle; passing it earns a descriptor, not an optimiser weight with football meaning.
- R5 Preregistration discipline: protocol + frozen config committed BEFORE any outcome
  is computed; pipelines are developed and unit-tested on SYNTHETIC data only; root
  executes the real run once (plus one determinism re-run) after the protocol commit;
  no rescue tuning; verdict vocabulary is fixed in the protocol.
  Structure-only inspection (schemas, counts, coverage, sample sizes) is allowed during
  design; computing any outcome statistic is not.
- R6 Closed stays closed: E-07 and E-08 are not reopened or re-tuned. No product evidence
  gate is lowered (900-minute outfield floor; 1800-minute Wyscout chance-creation floor).
- R7 Licensing: no football data in git; nothing over 512 KB; no data extensions outside
  tests/fixtures. Pappalardo = PUBLIC. StatsBomb = LOCAL_LICENSED: never read by any API
  or web path, no StatsBomb-derived number or coefficient may reach a hosted surface or a
  committed machine-readable table; aggregate findings appear only in research reports
  with the required attribution. No scraping. No new provider without a licence check.
- R8 Nothing is invented: no market values, wages, contracts, injuries, fitness. Missing
  stays missing and is rendered as UNAVAILABLE/UNMEASURED.
- R9 Temporal integrity: a decision at date D uses only matches on calendar dates before D,
  including the xT fit.
- R10 The frontend renders server decisions. JS never computes eligibility, coverage,
  objectives or uncertainty. No LLM-written numbers or tactical explanations at runtime.
- R11 Exactness: report solver status, bounds, quantisation; only certified optima are
  called optimal; unknown is never evidence of absence; ties remain visible.
- R12 Shared worlds: every resample is one coherent match-weight vector shared by all
  players and constructs it touches; world ids are preserved; zero-exposure holes stay holes.
- R13 Existing behaviour is pinned: the shipped Player/Match/XI Lab outputs, endpoints,
  hashes and tests must not change. New capability arrives in NEW modules, NEW endpoints
  and NEW pages. Shared files are touched only by the root integrator.

## 2. The release, as one chain

    declared identity -> explicit requirements -> squad audit -> role brief
        -> candidate search -> evidence ledger
    (and, per match)   opponent record -> optional requirement proposal -> XI solve

### 2.1 Exact decision tools (new modules under galactico/optimization/)

All operate on the existing typed domain (Candidate, TacticalRequirement, Formation) and
the existing integer quantisation policy. None changes solve_xi's behaviour.

- CEILING: generalise the existing hard-floor maximiser to any active requirement, and add
  the matching minimiser, giving the attainable range of each requirement sum for a squad.
- CONFLICT: when SATISFY is infeasible, a certified MINIMAL conflicting set of declared
  constraints (requirement floors, locks, exclusions, slot coverage) - the limitation
  KNOWN_LIMITATIONS.md names ("do not yet certify a minimal conflicting constraint set").
- FRONTIER: complete, certified enumeration of the nondominated requirement-sum vectors
  over 2-3 declared requirement dimensions, with one witness XI per vector and an explicit
  completeness certificate. Never a ranking of the frontier points.
- DECLARED-RISK selection over shared worlds: WORST_WORLD, CVAR(alpha) and MINIMAX_REGRET,
  where the user declares the risk preference. Claim: stability against resampling of the
  historical matches, NOT robustness to states of football nature.
- HONEST EVALUATION: split-sample (select on one half of the matches, evaluate on the
  other) as a football-calibrated diagnostic of selection optimism (M-05 follow-up).
- ABSENCE STRESS: exact worst-case declared shortfall when any k players are unavailable
  (k = 1, 2), by certified enumeration. No absence probabilities are invented.
- ROLE BRIEF (inverse problem): for a chosen slot, the minimal requirement-value vectors a
  hypothetical addition restricted to that slot must supply for the declared minima to
  become satisfiable (the Pareto-minimal "needs" of the residual squad), plus the exact
  count of gated candidates in the declared universe that meet it.
- BREAK-EVEN RETENTION: for an injected candidate, the smallest fraction lambda in [0,1] of
  his historical rates at which the conclusion (enters a certified optimum / removes the
  declared shortfall) still holds. This is the transport-agnostic robustness statement:
  no learned transport function is applied in the product.

### 2.2 Preregistered research (experiments/preregistered/E-09 .. E-13)

- E-09 NEW PLAYER CANDIDATES through the lifecycle: `shot_volume` (non-penalty shots per
  90), `shot_location_value` (location-only conversion-model-weighted non-penalty shots per
  90; must show incremental information over shot_volume or be rejected as redundant, by the
  ball_retention precedent), and one defensive-location candidate. Includes a transparent
  in-repo location-only shot conversion model, named as a MODEL (PREDICTIVE), evaluated
  leave-one-league-out. "Finishing" (goals minus expectation) stays out of scope.
- E-10 CONCEDED-TERRITORY PERSISTENCE (opponent): are team-level concession descriptors
  (where opponents' final-third entries and shots arrive, defensive action height, a
  PPDA-style rate) repeatable, are they more than team strength or schedule, and does the
  defender-specific term add out-of-sample predictive skill beyond the attacker's own
  tendency? Verdict per descriptor decides whether Opponent Lab may show it as a tested
  persistent tendency or only as a historical record. "Concedes there" is never called
  "weak there": funnelling and weakness are observationally confounded and the lab says so.
- E-11 PROVIDER AGREEMENT ON DOUBLE-CODED MATCHES: 100 matches exist in both corpora
  (World Cup 2018, 64; Barcelona's La Liga 2017/18 matches, 36, including both Clasicos).
  Compute each surviving construct's per-player-match and per-team-match inputs from each
  provider independently and grade cross-provider comparability per construct. This is the
  only way to separate a provider effect from a time effect, it yields a verified identity
  crosswalk (same match, same team sheet), and it must be registered and run BEFORE E-12,
  because E-12 may only use constructs E-11 grades comparable. LOCAL tier: aggregate report only.
- E-12 TRANSPORT ACROSS A CLUB CHANGE: persistence of the comparable constructs for movers
  versus stayers (StatsBomb 2015/16 -> Pappalardo 2017/18, where both groups cross the same
  provider+season shift, so stayers are the control), plus the public-only within-2017/18
  winter-window movers (31 players with >= 450 minutes at both clubs; almost certainly
  INCONCLUSIVE by its own sample gate, and reported as such). Product consequence fixed in
  advance; only the public-only arm may ever surface a number in a hosted page. Identity is a
  declared, stress-tested research link (the resolver cannot link the providers: StatsBomb
  lineups carry no birth date), never a persisted crosswalk in the repository.
- E-13 DECLARED-RISK SELECTION AND SELECTION OPTIMISM: on the M-05 synthetic harness with
  known latent values, does worst-world / CVaR selection reduce the gap between reported
  and true shortfall, and at what cost in true shortfall? Plus the split-sample diagnostic
  (M-05's stated "next experiment": shrinkage/selection estimated out of sample, selection
  and reporting evaluated separately) on the Madrid snapshots. Decides how the risk modes
  are labelled.

Existing `UNTESTED` placeholders `shot_profile` and `defensive_action_profile` are what E-09
finally tests: the specific candidates replace the placeholders in the proposed count;
`carrying_value` stays untested (Wyscout has no carry event).

### 2.3 Surfaces

- XI Lab additions: frontier explorer, declared-risk mode, minimal-conflict display.
- Squad Lab (/squad): depth by slot, attainable ranges versus declared minima, removal
  ledger for every squad player, absence stress test, role brief per slot. Any club under
  "broad-position eligibility (unreviewed)" with an explicit banner; Madrid keeps its
  manual versioned rules.
- Transfer Lab (/transfer): the user declares the slot being recruited; candidates are the
  gated players of the declared universe whose provider broad position is admissible for
  that slot (no mechanical role inference; lane evidence is shown for a human to judge);
  each candidate gets an exact injected re-solve, the requirement-keyed change vector, the
  displaced player, break-even retention, and shared-world stability. Default universe is
  the same league; cross-league candidates are opt-in and labelled "not strength-adjusted".
- Opponent Lab (/opponent): the prior-date record of what a team did and what was done
  against it, each descriptor badged with its E-10 verdict; an optional, explicitly
  HEURISTIC requirement proposal that the user must accept before it changes an XI solve.
- Director's desk (/desk): the chain end to end, with an evidence ledger and an explicit
  "not measured here" panel (finishing skill, defending quality, goalkeeping, physical
  profile, character, price, wages, contracts, availability).

### 2.4 Fixed definitions (so separate designs agree)

Notation. Worlds w = 1..W each give every candidate a value vector. For an assignment x and
active requirement r: S_r^w(x) is the sum of applicable values in world w; the normalised
shortfall is d_r^w(x) = max(0, m_r - S_r^w(x)) / n_r, quantised exactly as the shipped
solver does. M^w(x) = max_r d_r^w(x) and T^w(x) = sum_r d_r^w(x) are BALANCE's two stages.

- RISK MODES: see the O8 ruling in section 2.5 (TAIL(k of B), WORST_WORLD = TAIL(1),
  MINIMAX_REGRET, all on the lexicographically encoded per-world loss). The componentwise
  two-stage definitions an earlier draft of this file gave are WITHDRAWN: a second-stage
  "regret in totals" can be negative and is not a regret.
- INVARIANT, to be tested against the oracle: with a single world every risk mode returns
  the same certified objective vector as BALANCE on that world.
- A world with missing joint exposure is discarded and recorded, exactly as the shipped
  bootstrap does; risk modes condition on the certified-feasible worlds and say so.
- Hard constraints use the conservative Fraction floor/ceil policy of
  galactico/optimization/xi/tradeoffs.py (returned assignments satisfy raw floors exactly;
  boundary-feasible raw assignments may be excluded; INFEASIBLE refers to the integer model).
  Objectives use the shipped half-even policy. New solvers reuse these two policies and
  name which one applies to which quantity; they do not invent a third.
- FRONTIER objectives are requirement SUMS (maximise each), not shortfalls. Eligibility,
  locks and exclusions are the only constraints unless the user adds explicit hard floors.
- ROLE BRIEF for slot s = the set of Pareto-minimal vectors ( max(0, m_r - f_r) )_r where f
  ranges over the nondominated requirement-sum vectors of the residual problem (formation
  without slot s, squad without the hypothetical addition). A candidate "meets the brief at
  s" iff the exact injected SATISFY solve with him restricted to s is feasible; the brief is
  the explanation of that solve, never a substitute for it.
- BREAK-EVEN RETENTION lambda* for candidate c and a declared conclusion C (default: "the
  declared total shortfall with c available is strictly smaller than without him"): scale
  every additive rate of c by lambda and report the smallest grid value of lambda in
  {0.00, 0.05, ..., 1.00} at which C holds, with the exact solves that bracket it. Style
  shares are not scaled; which metrics are scaled is declared in the response.

### 2.5 Root rulings on the critic's open items (research/_critic.md; these supersede 2.4 where they differ)

- O1 / R11 LOCAL-TIER EVIDENCE ON HOSTED SURFACES (root ADR, numbered after the council's):
  labels yes, numbers no, coefficients no. A verdict token from a LOCAL-tier experiment may be
  shown on a hosted page as a label that links to the research note (precedent: the shipped
  `external_replication` labels). It may never be the gate that unlocks a number-bearing hosted
  panel, never parameterise a served computation, and no LOCAL-derived number, coefficient,
  interval or identifier is ever served or committed in machine-readable form. Hosted panels
  are gated on PUBLIC-tier (Pappalardo) verdicts only; a second-provider replication status
  sits beside them as a label. Every served artifact's provenance carries its `providers` set
  and a test asserts it equals {"pappalardo"}. Clause 1.4 applies to published analysis:
  every research note formed from StatsBomb data carries the StatsBomb logo and attribution
  (the two existing notes are repaired in the documentation package).
- O2 xT RECIPES: no new recipe and no unification tonight (unifying would move shipped
  numbers). Decision-surface code (snapshots, opponent record, universe) uses
  `historical.fit_prior_xt` (failed pass only), strictly prior dates. Research on the shipped
  Player Lab constructs (E-11, E-12) uses the shipped Player Lab recipe
  (`experiments/run_external_replication.fit_xt`). Each protocol names its recipe; the
  three-recipe divergence is recorded as a known limitation.
- O3 REGISTRIES: candidates in `galactico/features/candidates.py`; team descriptors in their
  own registry under `galactico/features/team/`; neither touches `CONSTRUCTS` or `SPECS`.
- O5 / C10 INTERVALS AT SMALL n: any protocol with fewer than 100 units computes the interval
  on the half-sample correlation and transforms it (the conservative order), and writes the
  critical value itself (1.6449, i.e. a one-sided 95% lower bound). This is a declared
  departure for team-level units, not a change to the player-level house method.
- O6 POSSESSION SEGMENTATION: none exists; every sequence metric (directness, tempo, regain
  height, set-piece phase, rebounds) is out of scope tonight or explicitly exploratory.
- O7 FRONTIER: dimensions are user-declared with no default; the declared direction is
  "more of this declared descriptor"; the claim is "nondominated among the declared
  descriptors at the shipped quantisation", never best/optimal trade-off/knee. EXPERIMENTAL
  descriptors (the two side pass-origin rates) are offered only behind an explicit opt-in.
  The grid is the shipped quantisation with exact Fraction arithmetic; no grid, floor or
  tolerance may be derived from the frontier or removal tables already seen on real data.
- O8 / C12 / K6-K8 DECLARED-RISK MODES (replaces the three bullets in 2.4):
  per-world loss is the lexicographic pair (M^w, T^w). Internally it is compared through an
  exact integer encoding E^w = BIG * M^w + T^w with BIG strictly larger than the largest
  possible total, so the encoding preserves lexicographic order; E is a search device and is
  NEVER serialised, logged in provenance or displayed (a test asserts it).
    TAIL(k of B): minimise the sum of the k largest E^w(x), k an integer the user declares from
      a small menu fixed in the API; report the tail world ids and each tail world's (M, T).
    WORST_WORLD is TAIL(k = 1) and is labelled as the extreme of that family for the fixed B
      (a worst case over B resamples grows with B: the certificate says so and records B).
    MINIMAX_REGRET: minimise max_w ( E^w(x) - E*^w ), E*^w the certified per-world optimum
      (never negative); report both pairs per world and the binding worlds, never a difference.
    INVARIANT: with one world every mode returns the BALANCE optimum's (M, T).
  B, seed, world fingerprint and dropped-world count are part of every certificate. No
  probability is printed. Solver limits use deterministic time, recorded in the certificate.
- O12 DECLARED INPUTS: `DECLARED` is not an evidence class. A ledger has two parts: the
  declared inputs (identity, minima, locks, exclusions, absences, slot, risk preference) and
  the computed quantities with their classes; every computed quantity is labelled conditional
  on the declared inputs.
- O13 ONE MAPPING to `EvidenceClass`: Match Lab DIRECT -> OBSERVED; DERIVABLE count ratios ->
  DERIVED; DERIVABLE xT quantities and the profile literal "Estimated" -> ESTIMATED; XI
  MEASURED -> ESTIMATED; HEURISTIC -> HEURISTIC; RESEARCH -> EXPERIMENTAL; UNAVAILABLE and
  REJECTED are absence states, not classes. A fitted shot model is PREDICTIVE.
- O14 / R10 ELIGIBILITY OUTSIDE MADRID: `PROVIDER_POSITION` only, banner "unreviewed". Depth
  under that rule mostly reflects the provider's four-way position code and the page says so.
- K15 TRANSFER ENDPOINT: E-12's primary endpoint is the quantity Transfer Lab injects,
  `progression` per 90; per-action and the shares are secondary.
- R9 / K18: no winter scenario (the 900-minute floor leaves Madrid nine outfield candidates on
  1 January 2018). The planning snapshot is end of season.
- H8 / H35 ORDERING OF CANDIDATES (refines R1): candidates are first grouped by an exact
  categorical outcome of the injected solve (for example: removes the declared shortfall /
  reduces it / leaves it unchanged / not evaluable), then ordered inside a group by ONE
  requirement-keyed quantity the user chose, named in the response as `order_key`; equal keys
  are returned as tie groups; no key combines requirements; the response states how many
  candidates were screened and carries the selection-optimism warning; a reference injection
  (the league median gated player at that broad position) is shown beside the list.
- H10: CORE / FAVORED / CONTESTED / FRINGE stay on the XI page. Planning pages show counts
  ("in k of B worlds") and name which requirements the model contains.
- H14-H21 NAMES: "share of final-third entries conceded, by lateral third" (never weakness,
  vulnerability, weak flank); "defensive action distance" (never line height); the Wyscout
  PPDA analogue is "opponent passes per recorded high-zone defensive action"; tag 403 is
  "head or body"; "location-only conversion value" (never shot quality, never provider xG);
  "break-even carry-over fraction" for retention (it predicts nothing).
- 4.4 PRIOR KNOWLEDGE: every protocol carries a prior-knowledge paragraph built from section
  4.4 of the critique. Exact computations on the declared model already seen (the 12-point
  frontier, the k-removal table) are not experimental outcomes; they are disclosed in E-13 and
  no constant is derived from them.

### 2.6 Root rulings on the OR-SQUAD draft's DISSENT and OPEN QUESTIONS (07:10; binding on its builders)

The design council was cut short: OR-SQUAD-SPEC.md, ARCH-SPEC.md, PRODUCT-MATCHDAY.md and the
E-09..E-13 drafts are complete but were never attacked, revised or reconciled; PRODUCT-PLANNING is
in two parts (`_pp_part1.md`, `_pp_part2.md`; its desk section is unfinished); no OR-XI spec
exists. Builders therefore treat a spec as a strong draft: where it contradicts the shipped code,
a measured fact or this file, this file and the code win, and the deviation is reported.

- D1 ACCEPTED. The default break-even conclusion is the lexicographic one
  (`SHORTFALL_VECTOR_LOWER`): the declared shortfall vector with the candidate available is
  lexicographically smaller than without him. It is monotone in the carry-over fraction by
  theorem. `TOTAL_SHORTFALL_LOWER` stays available as a declared alternative and keeps its
  full-grid scan and non-monotonicity warning.
- D2 ACCEPTED. The role brief is computed in the hard-constraint (conservative floor/ceil)
  arithmetic of the solve it explains. Section 2.4's "half-even frontier" wording does not apply
  to the brief.
- D3 ACCEPTED. No "displaced player". The page element is "players no longer in any
  least-shortfall XI" (`no_longer_possible_ids`), possibly empty, with its sentence.
- D4 RULED. Planning surfaces (Squad, Transfer, desk) default to the progression requirement
  only. The two side pass-origin requirements are EXPERIMENTAL and enter only through an explicit
  `experimental_opt_in` declared by the user; the composed class and its binding inputs are
  always printed.
- D5, D6 ACCEPTED. `galactico/optimization/squad/kernel.py` is the single exact kernel of the
  squad and transfer tools; the linear epigraph replaces `add_max_equality`; no tool calls
  `solve_xi` in a loop.
- D7 ACCEPTED. Pure scaling, no shrinkage, no destination-slot mean.
- D8 RULED. Shortfall integers come from `xi.solver._q`, so Squad and Transfer numbers equal XI
  Lab numbers for the same squad; oracles use exact Fraction half-even; invariant K9 guards the gap.
- Q3 The planning cutoff for Spain is 2018-05-21. The flagship scenario id is
  `madrid-planning-2018-05-21` (the id ARCH-SPEC and PRODUCT-PLANNING use; OR-SQUAD's
  `madrid-2017-18-season-end` is not used).
- Q4 Squad Lab shows no world statistics in this release. Transfer detail may show counts over
  `LEAGUE_MATCHES` worlds with the namespace note.
- Q5 A membership filter is allowed as an explicit opt-in filter, default off, never an order.
- Q6 Stress across worlds stays out.
- Q7 `RELEASE_LOCK` is dropped: locked players are not removable in a stress test.
- Q8 The universe states, on the page and in provenance, that a player whose latest club is
  outside the five leagues is not visible to it.
- Q9, Q10 Out of scope.
- Q11 Ordering follows section 2.5 (H8/H35): outcome group first, then one declared key.
- ARCH D1: a candidate construct that survives E-09 is NOT promoted and is not shown beside
  players in this release; `product_admissible` stays false until a later, separate promotion.
- The verdict registry ships EMPTY: nothing is registered until a protocol is frozen by commit.
  The five protocol drafts are committed as DRAFT documents, not as registered protocols, so
  `verdict_for` answers `NOT_REGISTERED` ("RECORD ONLY · NOT TESTED") for every subject.

## 3. Scenario decisions

- Real Madrid stays the laboratory subject. Add a third snapshot kind: a PLANNING snapshot
  whose cutoff is a date rather than a decision match (end of the 2017/18 league season),
  for squad and transfer questions. The two existing match snapshots are untouched.
- Identity presets are named after what they set ("progression minimum at the 75th
  percentile of league starting-XI sums"), never after an adjective. Any mapping from an
  adjective to a number is a declared, editable policy with evidence class HEURISTIC.
- Requirement minima may be declared relative to a REFERENCE DISTRIBUTION computed from the
  public corpus (league-wide prior starting-XI sums). The reference is descriptive.

## 3b. Frozen files and the module layout (from the subsystem maps)

FROZEN - do not edit, their bytes are hashed into published experiment results or into
every hard-floor query fingerprint: `galactico/optimization/historical.py`,
`galactico/optimization/xi/domain.py`, `galactico/optimization/xi/tradeoffs.py`,
`galactico/optimization/xi/solver.py`, `galactico/models/xt/grid.py`. Also never add a key to
`galactico/features/spec.py::SPECS` or to `CONSTRUCTS` before a construct survives (a sixth
SPECS key makes the Player Lab bundle stale, breaks Match Lab labels and changes XI
provenance), and never add a column or a file inside `data/public/parquet/pappalardo/
competition=*/` (content hashes of those directories are provenance).
New dataclasses live in the new module that uses them. New data columns live in a SIDECAR
keyed by `event_id`, written outside the `competition=*` directories.

New modules (existing empty stub packages are used where the architecture already names them):

    galactico/optimization/xi/        ceilings.py  conflict.py  frontier.py  risk.py
    galactico/optimization/squad/     depth.py  stress.py  brief.py
    galactico/optimization/transfers/ universe.py  injection.py  retention.py
    galactico/optimization/snapshots.py     any club / cutoff date / eligibility rule set;
                                            league-coherent worlds; parity-tested against
                                            historical.build_snapshot for Madrid
    galactico/optimization/reference.py     league reference distributions of starting-XI sums
    galactico/ingestion/sidecar.py          Wyscout tags the neutral schema drops (body part,
                                            duel won/lost/neutral, cards, own goal, shot placement)
    galactico/features/candidates.py        candidate ConstructSpecs, outside SPECS
    galactico/features/team/                match_table.py (team-match for/against), descriptors.py
    galactico/models/shots/                 location-only shot conversion model
    galactico/models/opponent/              prior-date opponent record
    galactico/validation/                   research pipelines only (firewalled from product code)
    galactico/domain/verdicts.py            machine-readable experiment verdicts; the ONLY thing
                                            product code may read from research
    galactico/api/                          xi_extensions.py squad_lab.py transfer_lab.py
                                            opponent_lab.py desk.py  (root registers the routers)
    web/                                    squad.html transfer.html opponent.html desk.html

Evidence vocabulary on new surfaces is the domain ladder (`galactico.domain.provenance.
EvidenceClass`, composed with `weakest()`), which today is on no production path. XI's legacy
strings map as MEASURED -> ESTIMATED, HEURISTIC -> HEURISTIC, RESEARCH -> EXPERIMENTAL;
UNAVAILABLE is not a class, it is the absence of a number.

Measured facts that shape the design (default Madrid scenario, 16 gated candidates):
- BALANCE optimum is (0, 0): under the default minima no injection can "improve" anything.
  Transfer and squad questions need a declared deficiency first (a departure, an absence, a
  raised declared minimum) and must report possible/necessary membership, not "enters the XI".
- The three-dimensional frontier has 12 nondominated points (480 feasible player sets).
- 17 of 120 pairs and 212 of 560 triples of absences leave NO fieldable XI. That thinness is
  produced by the 900-minute evidence gate (seven squad players omitted), not by the squad.
  Squad Lab reports gate-induced, eligibility-induced and shortfall fragility SEPARATELY and
  names the omitted players beside every depth number.
- A min-max solve costs ~0.7 s at quantisation 100000 and ~15 ms at 100; a linear maximise
  costs ~12 ms. Never coarsen quantisation silently; choose formulations accordingly.
- Hashes must be computed on LF-normalised bytes (`core.autocrlf=true` on Windows checkouts).

## 4. Engineering rules for parallel work

- Root owns: git (all commits), galactico/api/player_lab.py, galactico/api/decision_lab.py,
  galactico/optimization/xi/__init__.py, galactico/domain/constructs.py, README.md and every
  top-level *.md, docs/ASTRA-CHECKPOINT.md, pyproject.toml, .github/, playwright.config.js.
  Agents propose changes to these as a patch description in their final report.
- Each agent owns an explicit list of NEW files. Never edit a file you do not own.
- No agent runs a state-changing git command. No agent starts a server on port 8090 or 8111;
  use the port you are given.
- The machine has 15.6 GB RAM and many agents. Read Parquet with a column list; never load
  raw provider JSON unless you own that task; no process over ~1.5 GB; no pools over 4.
- Python: `from __future__ import annotations`, frozen dataclasses, type hints, ruff clean
  (line length 100; E, F, I, UP, B, SIM), module docstrings that state the claim and the
  non-claim in the project's voice. Tests must skip cleanly when the corpus is absent
  (the CI check job has no data).
- Verification placement (M-01..M-05): an oracle must be independent of the code it checks;
  a definition and its implementation must be one object; a 200 response is not a working
  page - look at it; teammates share worlds; an optimiser selects noise.
