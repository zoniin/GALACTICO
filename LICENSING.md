# Licensing

The repository is public. The difference between a corpus that may be
redistributed and one that may only be read locally is the difference between a
project and a liability, so it is enforced in code rather than described here and
hoped for.

## The repository ships

Code, schemas, tests, tiny fixtures, and download scripts. No football data of any
kind, ever. `data/licensed/` and `data/trial/` are gitignored and CI fails on any
attempt to commit into them.

## Tiers

**PUBLIC** — redistributable and hostable. The public demo runs on these and
nothing else: Pappalardo/Wyscout (CC BY 4.0), SkillCorner (MIT), DFL/Sportec
(CC BY 4.0), plus UEFA, ClubElo and FPL as hostable-derived-but-not-redistributable.

**LOCAL_LICENSED** — runtime download into a gitignored cache, readable locally,
never served to a third party. StatsBomb open data and any paid API feed.

**TRIAL** — time-boxed vendor trial data. Usable for calibration; never a
dependency of anything that must keep working after expiry. Currently empty, and a
test asserts it stays empty.

## StatsBomb specifically

The Public Data User Agreement is not an open licence. Clause 1.2.1 bars the user
from providing the data to any third party. Clause 1.2.2 bars commercial
exploitation of the data **or any analysis derived from it** — the restriction
follows through to derived scores. Clause 1.4 requires the StatsBomb brand logo on
published analysis.

Consequence: no vendored events, no cached Parquet in git, no derived metric
tables in the repository, and a hosted instance may never serve a StatsBomb-derived
number. `assert_may_host("statsbomb")` raises.

## Attribution

Pappalardo requires citing the constituent figshare articles individually plus the
2019 Scientific Data paper. SkillCorner requires the MIT copyright line.
DFL/Sportec requires CC BY 4.0 attribution. UEFA and ClubElo require credit.
Attribution text lives in `galactico/providers/base.py` next to the posture it
belongs to.

## Sources deliberately not used

FotMob, SofaScore, WhoScored, Transfermarkt, Understat and SoFIFA all prohibit
programmatic access in terms, in robots.txt, or both. Understat's robots.txt is a
blanket `Disallow: /`. FotMob's terms name scraping explicitly and its robots.txt
disallows `/api/*`.

The strategic argument matters more than the legal one. FBref did not lose its
data to a scraper lawsuit — it lost it as a paying licensee when Stats Perform
terminated the feed and demanded deletion. Opta protects the pipe. A public
repository under a real name that is visibly an Opta-derivative scraper is the
thing most likely to draw a letter, and it buys the least: FotMob exposes shots
with coordinates and nothing else, which is roughly what $19 buys legitimately.

## CI

`scripts/check_licensing.py` blocks files over 512 KB, data file extensions
outside `tests/fixtures/`, anything under a restricted tier directory, committed
environment files, and credential-shaped strings. It runs before lint and before
tests, because a licence mistake is the only failure here that a later commit
cannot fix.

