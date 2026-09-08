# Decision Engine checkpoint

## CURRENT COMMIT

Release code: `f86e520` — connected historical Match/XI UI, APIs and browser tests.
`6392598` — exact XI/shared-world core. `95b9904` — Match Lab/scalar null.
Earlier milestones: `470907a` decision/falsification plan; `c28ebfc` shared-match
uncertainty and Player Lab gates; `b9652c6` baseline lint repair.
Entry was clean `f0ed51a`. Commits are local; no push has been performed.

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

## CURRENT STATE MAP

- VERIFIED COMPLETE: frozen Player Lab; historical Match Lab implementation;
  conditional XI engine/UI; exactness/temporal/browser checks; licensing guard.
- PARTIALLY COMPLETE: decision usefulness; opponent/transfer foundations.
- STALE DOCUMENTATION: no known release-state discrepancy after the final audit.
- UNVERIFIED: external human acceptance, historical fitness, learned utility.
- BROKEN: no unresolved release defect known.
- NOT STARTED: full Opponent/Transfer, Pareto/robust, LIVE/Bridge/VISION products.

## IN PROGRESS

No unfinished implementation within this milestone. Final evidence: **220 Python
tests passed**, Ruff clean (including all new experiment/preparation scripts),
**11 Playwright tests passed** against freshly prepared data in 55.5 seconds.
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

## OPEN BLOCKERS

None requiring user authority. External human sign-off is not claimed.
Creation, rest defense and keeper quality are unmeasured in XI Lab: an explicit
limit on the decision claim, not missing implementation disguised as a result.

## EXACT NEXT COMMANDS

To run the committed product from the prepared workspace:

```powershell
uv run ruff check galactico tests
uv run pytest -q
npx playwright test e2e/smoke.spec.js e2e/labs.spec.js
uv run python scripts/check_licensing.py
git diff --check
git status --short
uv run uvicorn galactico.api.player_lab:app --host 127.0.0.1 --port 8090
```

Open `/`, `/match?id=2565907` or `/xi` on that server. The final session starts a
local server on port 8090; check it before starting another. For a fresh checkout,
follow README's fetch/prepare steps. Do not redownload/rebuild merely to resume.

Next research reproductions (not unfinished release work):

```powershell
uv run python experiments/run_xi_backtest.py --since 2018-03-01
uv run python experiments/run_match_score.py --competition Spain
uv run python experiments/run_match_score.py --competition England
uv run python experiments/run_optimizer_curse.py
```

England requires its public corpus. New learned utility or role-transition models
need a protocol before confirmatory evaluation; do not tune to the 12-match window.

## EXACT NEXT FILES

`docs/research/STAGE-3-QUESTIONS.md`, `docs/research/E-06-lineup-requirements.md`,
`experiments/run_xi_backtest.py`: decide/preregister the next temporal role/value
baseline experiment. The current requirement model loses to prior minutes.
`galactico/optimization/historical.py`: deployment transport, sample/availability
limits and fixed-xT uncertainty require research, not undocumented coefficients.
`galactico/optimization/xi/solver.py`: candidate injection and removal foundations
are available; future alternatives/robust policies need explicit preferences.
`galactico/match_lab/model.py`: team descriptors can feed an opponent requirement
experiment only after a reliability/meaning audit. No automatic opponent adjustment.

## AGENT RESULTS NOT YET INTEGRATED

None. All earlier council and fresh review findings are integrated. Completed or
errored agents hold no exclusive work requiring recovery.
