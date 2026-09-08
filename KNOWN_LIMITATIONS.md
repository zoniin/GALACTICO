# Known limitations

This is the release boundary, not a list of caveats attached to a stronger claim.
When a limitation changes, preserve the experiment in `docs/research/`.

## Data and licensing

- The hosted laboratory uses the public Pappalardo 2017/18 corpus, not a current
  event feed. No licensed current-season event source is integrated.
- StatsBomb remains local-only under the repository's enforced provider posture;
  neither its data nor derived results enter the hosted Match/XI surfaces.
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
- Match minutes are nominal reconstructed exposure, not exact on-field duration.
  Recorded red/second-yellow dismissals suppress the unresolved minutes value;
  the original nominal value remains provenance only. Event totals are unaffected.
- No overall match rating was identified. Accounting is the existing xT baseline;
  broad-role standardization remains highly correlated with it in Spain and
  England. This rejects those candidates, not every imaginable scalar
  ([E-05](docs/research/E-05-match-score.md)).

## XI Lab is a conditional requirement model

- The objective minimizes declared structural shortfalls. It does not maximize
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
- Infeasibility diagnostics do not yet certify a minimal conflicting constraint
  set. No constraint is silently relaxed.
- The development backtest loses to prior minutes: 6.00 versus 6.83 actual starters
  out of 11. Manager agreement is not correctness, and tied representative choice
  can change overlap. See [E-06](docs/research/E-06-lineup-requirements.md).
- Joint evidence availability is restrictive: E-07's temporal forecast study had
  only 3 eligible development lineups when all ten outfield starters had to meet
  the 900-minute floor. No forecast model could be fitted under the frozen rules.
  This is a coverage failure, not proof that lineup information is useless.

## Uncertainty and selection bias

- Shared match worlds preserve teammate/construct covariance from that resample;
  they do not model every dependence, tactical change, availability state or xT
  surface uncertainty. Historical worlds hold the pre-cutoff xT surface fixed.
- The browser uses only 12 worlds, an explicitly coarse exploratory summary.
  Necessary-to-possible frequencies include equally optimal XI ambiguity. They
  are not confidence intervals or probabilities that a player is better.
- Frequencies condition on fully certified feasible worlds. Missing joint exposure
  discards a whole world; incomplete solves and discarded worlds are recorded.
- CORE/FAVORED/CONTESTED/FRINGE cutoffs are product conventions, not universal
  scientific boundaries. A user lock is a constraint, not statistical evidence.
- The old three-to-five stable-core result and 3.5%/9.9% inflation figures were
  illustrative rating-noise experiments, **not current XI Lab results**. The current
  requirement-model simulation confirms selection optimism, but no football-calibrated
  correction, robust/CVaR objective or minimax-regret mode ships
  ([M-05](docs/research/M-05-optimizer-selection-bias.md)).
- You never observe the unplayed XI. Observational associations or manager
  agreement cannot establish that a proposed lineup would have won.

## Reliability is not validity or utility

Metronome Fit reached split-half .94–.95 and still measured touch volume. A
repeatable number can repeat the wrong thing. Every new construct must survive
discriminant and baseline checks; passing those still does not establish decision
utility. See [E-01](docs/research/E-01-metronome-fit.md).

Defensive quality, finishing skill and goalkeeper quality have no validated
shipped estimator here. This is a limitation of the current evidence/model, not a
proof that all possible data regimes can never measure them. Cross-provider
pooling remains guarded; the Bridge remains unvalidated.

## Product scope

No LLM invents a number or post-hoc tactical explanation. The frontend renders
server-computed assignments, constraints, deficits and uncertainty. Full Opponent
and Transfer Labs, Pareto alternatives, learned embeddings, LIVE and VISION are
not implemented. VISION's intended target remains team shape, not player ratings.
