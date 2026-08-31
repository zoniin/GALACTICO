# Known limitations

Written before the code and kept current as evidence arrives. If something here
stops being true, that is a research result and belongs in `/research`.

## Data

- **No free, licence-clean source of current-season event data exists.** Verified
  at field level across every vendor under $50/month. LIVE is aggregate-only.
- **The current Real Madrid squad has no open event data.** Carreras, Huijsen and
  Mastantuono have zero records anywhere. StatsBomb's most recent Real Madrid
  match is 2021-04-10.
- **FBref's advanced statistics were deleted on 2026-01-20**, retroactively across
  all seasons, when Stats Perform terminated the licence.
- **StatsBomb open data may not be hosted or commercially exploited**, derived
  analysis included. Local-only, permanently.

## Statistics

- **The player x role interaction is at most 9% of variance** and indistinguishable
  from zero for shooting metrics. Role fit is real but small, and mostly mechanical
  rather than tactical.
- **Pairwise chemistry is unidentifiable.** Not merely noisy. 2,461 of 2,689
  distinct starting XIs in the corpus appear exactly once.
- **The single optimal XI is not identified.** Bootstrap leaves three to five of
  eleven players above 90% selection frequency.
- **The optimiser's curse inflates reported objectives** by ~3.5% at four-point
  rating noise and ~9.9% at eight-point noise. Shrinkage corrects the reported
  number, not the decision.
- **You never observe the counterfactual XI.** No backtest can show the engine's
  team would have beaten the manager's, because only one was played.
- **A one-player-swap effect is out of statistical reach.** Detecting a 0.05 xGD
  effect needs roughly 14,700 team-matches; the corpus supplies about 3,650.

## Modelling

- Defensive quality is not measurable at the event tier.
- Finishing skill is not measurable at all.
- Cross-provider pooling is unsafe for several metrics and is blocked in code.
- The Bridge is unvalidated. Until it passes, LIVE ships a reduced axis set.

## Scope

- No LLM invents any number. If one is added it may parse intent and narrate
  engine state; all numeric truth comes from the deterministic layer.
- VISION contributes team shape only, never player ratings.

