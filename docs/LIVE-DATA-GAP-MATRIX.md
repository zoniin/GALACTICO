# LIVE data gap matrix

**The finding that reframes this document: money does not buy constructs. Money
buys recency and league breadth.**

Every construct Galáctico has validated is already coverable at **$0** on
historical corpora. Only about nine are coverable at $0 for the *current* season,
and most of those are Premier League only. So the matrix below is really
two-dimensional — construct × recency — and a sixth cell state is needed that the
original five could not express.

| State | Meaning |
|---|---|
| `DIRECT` | The source supplies it as a field |
| `DERIVABLE` | Computable from what the source supplies |
| `MODELLED` | Only via a bridge model, with error |
| `HISTORICAL_ONLY` | Direct and free, but not for the current season |
| `VALIDATION_ONLY` | Too small or too time-boxed to build on; use to check |
| `UNAVAILABLE` | Not present |
| `LICENSE_BLOCKED` | Present, and we may not use it |

## The matrix

| Construct | API-Football $19 | UEFA free | FPL free | FotMob | Sportradar trial | LAB free | VISION | Bridge |
|---|---|---|---|---|---|---|---|---|
| minutes | DIRECT | DIRECT | DIRECT | LICENSE_BLOCKED | DIRECT | HISTORICAL_ONLY | — | — |
| lineups | DIRECT | DIRECT | DIRECT | LICENSE_BLOCKED | DIRECT | HISTORICAL_ONLY | — | — |
| goals / assists | DIRECT | DIRECT | DIRECT | LICENSE_BLOCKED | DIRECT | HISTORICAL_ONLY | — | — |
| passes | DIRECT | UNAVAILABLE | UNAVAILABLE | LICENSE_BLOCKED | DIRECT | HISTORICAL_ONLY | — | — |
| **progression** | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | **UNAVAILABLE** | DIRECT | **HISTORICAL_ONLY** | — | **MODELLED** |
| **chance creation** | UNAVAILABLE | UNAVAILABLE | DERIVABLE | LICENSE_BLOCKED | DIRECT | HISTORICAL_ONLY | — | MODELLED |
| xG / xA | UNAVAILABLE | UNAVAILABLE | **DIRECT** | LICENSE_BLOCKED | DIRECT | DERIVABLE | — | MODELLED |
| shot location | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | **LICENSE_BLOCKED** | DIRECT | HISTORICAL_ONLY | DERIVABLE | — |
| touch location | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | LICENSE_BLOCKED | DIRECT | HISTORICAL_ONLY | DERIVABLE | — |
| heatmaps | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | LICENSE_BLOCKED | UNAVAILABLE | DERIVABLE | DERIVABLE | — |
| event XY | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | **DIRECT** | **HISTORICAL_ONLY** | MODELLED | — |
| physical distance | UNAVAILABLE | **DIRECT?** | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | HISTORICAL_ONLY | MODELLED | — |
| top speed / sprints | UNAVAILABLE | **DIRECT?** | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | HISTORICAL_ONLY | MODELLED | — |
| **width / half-space** | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | LICENSE_BLOCKED | DIRECT | HISTORICAL_ONLY | DERIVABLE | MODELLED |
| role | DERIVABLE | DERIVABLE | DERIVABLE | LICENSE_BLOCKED | DERIVABLE | HISTORICAL_ONLY | DERIVABLE | — |
| team shape | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | DERIVABLE | HISTORICAL_ONLY | **DERIVABLE** | — |
| pressing / press resistance | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | DERIVABLE | HISTORICAL_ONLY | UNAVAILABLE | UNAVAILABLE |

`DIRECT?` marks UEFA's physical metrics: the most load-bearing unverified claim in
the whole analysis. It matters because it is the only free route to a physical
axis for current Real Madrid players, and it is unresolved whether the numbers are
reachable as JSON or only inside per-match PDF reports. **Settle this before
committing to any spend plan.** If it is PDF-only the data is still usable, but a
PDF-extraction workstream has to be costed in.

## The free corpus is larger than previously stated

Four free, licence-clean sources supply real event XY, and two supply tracking XY:

- **StatsBomb open** — 80 competition-seasons with 360 freeze frames (local-only licence)
- **Pappalardo/Wyscout** — CC BY 4.0, 1,826 matches, five leagues, the current LAB
- **Sportec / DFL open** — 7 matches with **synchronised event *and* tracking x/y/z plus speed**
- **SkillCorner open** — 10 matches of broadcast tracking at 10fps, plus season physical aggregates

The last two were missing from earlier analysis and are the **only free route to
physical distance, top speed and sprints**. Sportec matters disproportionately:
it is the sole free source carrying both modalities for the same matches, which
makes it the natural validation set for any event-to-physical or event-to-shape
inference.

## What to buy

**$19/month. API-Football Pro. That is the whole recommendation.**

Free layer: StatsBomb + Pappalardo + Sportec + SkillCorner as the spatial training
corpus; FPL for current-season Opta xG/xA per gameweek (Premier League); UEFA for
Champions League minutes and lineups, and physical metrics if they resolve; ClubElo
as the opponent-strength covariate; football-data.co.uk for team-xG validation.

Paid layer: current-season minutes, lineups, passes, injuries and transfers across
~1,100 competitions.

**$19 is the point of diminishing returns, and it is worth naming explicitly.**
Moving to Sportmonks at roughly €53 buys per-player xG across five leagues — but
the Premier League is already free through FPL, so the true increment is four
leagues plus a team-level Pressure Index of undocumented granularity. Its
`ballCoordinates` carry no `player_id` and are not a substitute for event data.

**No amount under $100/month unlocks:** current-season event XY, progressive
passes, or press resistance. Those are historical-only, permanently, until someone
writes a much larger cheque.

## How to spend the trials

**Sportradar's 30-day / 1,000-request trial: validation, not collection.** A
thousand requests is a few dozen matches — far too small to train on, exactly right
for measuring how far a free-corpus bridge model drifts on current-season data.
Score it `VALIDATION_ONLY` and plan it as a calibration exercise.

**Sportmonks' 14-day trial: field discovery only.** Their documentation exposes no
statistic field names publicly and routes discovery through a token-gated endpoint,
so the trial is the only legitimate way to settle whether the xG add-on includes
per-player xA.

## Consequence for the roadmap

The bridge model is not a workaround for being poor. It is the permanent
architecture, because the constructs that survived Stage 1B — progression,
progression per action, and the two spatial style axes — are precisely the ones
that no current-season source under $100/month supplies directly.

Build the bridge on Pappalardo and StatsBomb XY, then calibrate it against
Sportec's synchronised pairs.

