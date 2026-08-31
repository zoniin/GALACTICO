# FotMob reconnaissance

**Method: public source code only. No FotMob endpoint was ever requested.**

FotMob's `robots.txt` carries `Disallow: /api/*` for every agent except four named
search crawlers, and its Terms of Use name scraping explicitly. That is a
machine-readable denial, so this reconnaissance read open-source client libraries,
generated type definitions, committed test fixtures and notebooks on GitHub — and
nothing else. Every field below is **DOCUMENTED in third-party source we read**,
not verified against a live response, and cannot be, without crossing the line
this project chose not to cross.

**Caveat that matters: the adversarial verification pass for this research did not
run** — it died on an account spend limit. These findings have not been
independently checked. Treat the field names as well-sourced and the interpretation
as unreviewed.

## Where the data comes from

Two coexisting API generations. A legacy `/api/{route}` family (matchDetails,
playerData, teams, leagues, playerStats, fixtures, transfers, …) and a newer
`/api/data/{route}` family adding `leagueseasondeepstats`, `playerMatches`,
`heatmap/match/{id}/heatmaps`, `search/suggest` and `dataproviders`. The same
payloads are also embedded server-side in the page's `__NEXT_DATA__` script tag.

**The provider is Opta, and FotMob does not hide it.** Lineup players carry a
`usingOptaId` boolean; `matchDetails.content.lineup` carries a parallel
`optaLineup` node; `content.playerStats[*]` carries an `optaId` beside FotMob's
own. And the entire `leagueseasondeepstats` vocabulary is verbatim Opta
nomenclature — `goal_assist`, `ontarget_scoring_att`, `total_scoring_att`,
`accurate_pass`, `won_contest`, `won_tackle`, `poss_won_att_3rd`,
`big_chance_created`, `effective_clearance`, `outfielder_block`.

That single fact settles the licensing question more firmly than the ToU does.
Scraping FotMob is scraping Opta with a different logo on it, and a paying
licensee being terminated by Stats Perform is exactly how FBref lost everything in
January 2026.

## The two answers that mattered

### Shotmap — a real, player-attributed, coordinate-bearing event table

26 documented fields: `x`, `y` (**metres on a 105×68 pitch**, not normalised),
`expectedGoals`, `expectedGoalsOnTarget`, `shotType` (Header / LeftFoot /
RightFoot), `situation` (RegularPlay / FromCorner / SetPiece / FastBreak),
`eventType` (Goal / AttemptSaved / Miss / Post / Blocked), `min`, `minAdded`,
`period`, `goalCrossedY` and `goalCrossedZ` (a 3-D goalmouth crossing point),
`blockedX`/`blockedY`, a nested `onGoalShot`, and full player attribution.

No assisting-player id.

**And it exists at season scope, not only per match.** `playerStats?playerId=…
&seasonId=…` returns a flat array of every shot a player took in a
competition-season, with the identical field schema. That is a complete
independent shot-profile layer for the current season — the single most valuable
thing behind the site.

### Heatmaps — genuinely spatial, and coarser than they look

Neither raster images nor event samples. The endpoint returns JSON with a
`template` SVG string carrying a `viewBox` (default `0 0 105 68`) and a `players`
map keyed `p{id}` whose values are SVG fragments of discrete `<circle cx cy>`
elements. Parsing the circles yields a per-player point cloud **in pitch metres**.

Quantised, unordered, untimed. Enough for zone-occupancy style features — width
tendency, centrality, left/right bias, average position — and nothing whatsoever
resembling event data. Which is the honest ceiling, and it happens to line up with
the two style axes that survived Stage 1B.

## The decisive negative

There is a **scope asymmetry** that a UI screenshot would never reveal.

The rich metrics — touches, touches in the opposition box, passes into the final
third, recoveries, duels, aerial duels — exist **only at match scope**, inside
`matchDetails`, per player per match. The league-wide season leaderboard
`leagueseasondeepstats` exposes 35 player stats, and touches, recoveries, duels,
aerial duels and passes into the final third are **all absent from it**.

**Progressive passes appear at no scope at all.** No physical metric — distance,
sprints, top speed, high-intensity runs — appears anywhere in any surface.

So a current-season player model would have to be assembled by summing thousands
of match-level rows, not read off a league table. That is a materially larger
undertaking than "call one endpoint", and it is exactly the kind of thing that
gets discovered three weeks into building.

## Value categorisation

| Category | Fields |
|---|---|
| **A — already available legally elsewhere** | minutes, lineups, goals, assists, cards, xG/xA at season scope (FPL free for the PL; API-Football $19 elsewhere), fixtures, standings |
| **B — uniquely valuable** | season-scope per-player shotmap with x/y/xG/xGOT/body-part/situation; per-player heatmap point clouds; match-scope touches, touches in opposition box, passes into final third, recoveries, duels |
| **C — useful for validation only** | FotMob Rating (a proprietary composite over ~300 Opta stats; useful as an external check, never as an input) |
| **D — redundant** | standings, fixtures, transfers, TV listings, live ticker |
| **E — technically inaccessible** | progressive passes (absent at every scope); any physical metric |
| **F — technically observable, licensing blocks production use** | **everything in category B** |

## The question that matters

> If FotMob granted explicit written permission tomorrow, how much of LIVE could
> be built from it?

**A lot, and less than it first appears.**

It would deliver the one thing no legal source under $50/month delivers: a
current-season, player-attributed, coordinate-bearing shot table with xG, body
part and situation. That alone supports a shot-profile layer, a real finishing
diagnostic, and shot-location style axes for the actual 2026/27 Real Madrid squad.
The heatmaps would additionally support coarse spatial style features — which,
after Stage 1B, is precisely the axis family that survived.

It would **not** deliver progression, because progressive passes are absent
everywhere. It would not deliver any physical axis. And the richest counting stats
would require summing match-level rows across a whole season rather than reading a
table.

So even with permission, FotMob does not remove the need for the bridge model. It
would give Galáctico a spatial shot layer it cannot otherwise have, and leave the
core progression axis exactly where it is today.

## Decision

**No production adapter. No `providers/fotmob/`.** The main application does not
depend on this and will not. What was learned is written down here; that was the
point.

The path if it ever matters is a permission request, not a scraper.

