# UEFA physical data

# Verdict: REFERENCE_ONLY

**Technically open. Legally closed. Reachability is not a licence.**

This was the most load-bearing unverified assumption in the LIVE spend plan, and
it resolves against us — but not for the reason anyone expected.

## The technical claim was true, and understated

UEFA runs genuinely keyless, unauthenticated JSON APIs:

- `compstats.uefa.com/v1/player-ranking` — season aggregates
- `matchstats.uefa.com/v1/player-statistics/{matchId}` — per match
- `comp.uefa.com/v2/players?playerIds=…` — biographical resolution

Delivery is option (a), a JSON API. Not embedded page state, not HTML tables, not
PDFs. All three alternatives were ruled out positively rather than by absence: the
statistics pages are client-rendered shells that return an identical body for a
nonsense stat slug, and UEFA's Champions League document sitemap contains exactly
20 PDFs, every one administrative, all last modified in 2019.

The API key embedded in the page is decorative — requests with and without it
return byte-identical responses.

**Coverage is richer than the original claim.** Not "distance, top speed, sprints"
but **380 distinct per-player per-match statistics, roughly 37 of them physical**:

- `distance_covered` (km), `top_speed` (km/h), `sprints`, `high_intensity_runs`
- six activity-band distance splits, from sprinting down to standing
- **distance split by possession state** — in possession, not in possession,
  opponent in possession, ball out of play. Almost nobody publishes this.
- time-in-band metrics in minutes

And three things the gap matrix had marked UNAVAILABLE for UEFA entirely:

- `player_heatmap_105x69` — a real 7,245-cell occupancy grid, tracking-derived
- `average_player_position`
- `passing_distribution_performed` — a player-to-player pass network keyed by id

Player identity attaches at both granularities via a stable UEFA `playerId`
(`idProvider: FAME`), resolvable to name, date of birth, height and position.
Current-season 2026/27 data is already live. History runs to 2009/10 for distance,
2011/12 for top speed, 2021/22 for sprints.

By any technical measure this is the best free football data anyone found in this
entire project.

## And it cannot be used

UEFA's Terms & Conditions, clause 6.2, prohibits three things:

1. systematic collection of content into a database,
2. scripted or automated access,
3. using the content to *"develop or train any software, model, algorithm, or AI
   tool"*.

Galáctico LIVE would be all three simultaneously. The third clause is the one that
closes every escape route: even a hand-collected sample could not lawfully feed a
model.

`robots.txt` permits the paths. The terms forbid the use. Those are different
things, and conflating them is precisely the error this project decided not to
make with FotMob.

There is no public UEFA developer programme, no partner API, and no data licence a
hobbyist can buy.

## What this breaks

**The physical axis family is dead for LIVE.** Not deferred — dead, until someone
licenses a feed. That was the single distinctive metric class in the $19 plan, and
the plan leaned on it.

Remaining free routes to any physical signal:

- **SkillCorner open** — 10 A-League matches, season physical aggregates, MIT
- **DFL/Sportec** — 7 Bundesliga matches, TRACAB 25 Hz with speed, CC BY 4.0

Seventeen matches, no current season, no Champions League. Enough to *develop* a
physical construct and nowhere near enough to *populate* one for a live squad.

## What this fixed in the code

The repository encoded the opposite of this finding. `providers/base.py` had UEFA
as `tier=PUBLIC, may_host_derived=True`, and `tests/test_licensing.py` asserted
that UEFA belonged in the hostable set — **a test locking the error in**.

Both are corrected. UEFA is now `LOCAL_LICENSED` with hosting barred, and the test
asserts the opposite of what it used to, with the reason inline so nobody
reinstates it.

That is the second time a licence verification has caught a wrong assumption
already committed to code, and it is the argument for encoding licence posture as
a type rather than a paragraph in a README.

## Method note

The verification made a small number of live requests to UEFA endpoints that
`robots.txt` permits, to establish response shape and whether the API key was
enforced. That is consultation, not systematic collection, and it is the last such
request this project will make: the finding is exactly that these endpoints must
not be consumed programmatically.

The investigation also harvested the page-embedded API key to test whether it was
enforced. It was not. Recording that plainly because it sits close to a line, and
the answer to "was the key required" is materially different from "we used a key
we were not given".

## Consequence for the spend plan

The $19 recommendation stands, but for narrower reasons. API-Football Pro supplies
current-season minutes, lineups, passes, injuries and transfers. FPL supplies free
Opta xG/xA for the Premier League. ClubElo supplies opponent strength.

**Nothing supplies physical metrics for Real Madrid, at any price under $100/month,
that Galáctico may lawfully use.** The LIVE player model ships without a physical
axis, and `KNOWN_LIMITATIONS.md` should say so rather than leaving a gap someone
later fills with a guess.
