# Datasets

Verified against primary sources. Prices and terms checked August 2026.

## LAB — event level

| Corpus | Size | Licence | Tier |
|---|---|---|---|
| Pappalardo/Wyscout 2017/18 | ~1,826 matches, all five big-five leagues complete, plus WC2018 and Euro2016 | CC BY 4.0 | PUBLIC |
| StatsBomb open 2015/16 | 1,517 matches: La Liga 380, Premier League 380, Serie A 380, Ligue 1 377 | Restrictive EULA | LOCAL |
| StatsBomb 360 tournaments | Euro 2024 (51) and WC 2022 (64), full freeze-frame coverage | Restrictive EULA | LOCAL |

Pappalardo contains a complete 38-match Real Madrid 2017/18 season with the full
19-club competitor universe. StatsBomb's four 2015/16 seasons are the only
complete-population event corpus with position spells and timestamps, which makes
them the only viable source for role-transition work.

Note what StatsBomb open data is *not*: eighteen La Liga seasons are listed but
sixteen are Barcelona-only subsets, and most listed Champions League seasons are a
single match, the final.

## LIVE — aggregate level

| Source | Cost | What it gives | Coordinates |
|---|---|---|---|
| API-Football Pro | $19/mo | ~30 aggregate fields per player-season, lineups, injuries, transfers | none |
| Sportmonks Starter + xG | EUR 29 + 15-29/mo | richer aggregates, xG per match/player | none |
| UEFA open API | free | official physical metrics: distance, top speed, sprints, Champions League | n/a |
| FPL API | free | 109 fields per player per match including xG and xA, Opta-derived | Premier League only |
| football-data.co.uk | free | team-level match xG from 2026/27 | n/a |
| ClubElo | free | club Elo, complete history, current | n/a |

`fixtures/events` on API-Football returns goals, cards and substitutions. It is not
event data. Nothing under $50/month returns per-action pitch coordinates; that
requires Sportradar or the Hudl Wyscout Data API, both quote-only.

## VISION

| Corpus | Content | Licence |
|---|---|---|
| SoccerTrack v2 | 10 full-length panoramic 4K matches with per-frame game-state annotations | code MIT, data CC BY 4.0 |
| Alfheim | panoramic video with 20 Hz ZXY ground-truth positions | free |
| SkillCorner open | 10 A-League matches, broadcast tracking at 10 fps | MIT |
| DFL/Sportec | 7 Bundesliga matches, TRACAB Gen5 at 25 Hz, real names | CC BY 4.0 |

Alfheim matters most: ground-truth positions are the only way to report a median
positional error rather than an opinion about whether the animation looks right.

## The Bridge calibration corpus

Five complete women's league seasons sit inside both StatsBomb open data and
API-Football's free 2022-2024 window: Liga F 2023/24 (240 matches, 30 per team),
FA WSL 2023/24, Frauen-Bundesliga 2023/24, NWSL 2023 and one further season. Full
round-robin, full population, real provider pairing, zero cost.

This works where the men's equivalent does not: every StatsBomb men's club season
in that window is a single-team slice.

