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
(CC BY 4.0).

**REFERENCE ONLY** — reachable and free, and not ours to use. Consulted by hand,
never ingested, no adapter. UEFA: clause 6.2 of its terms bars systematic
collection, scripted access and model use. The Premier League Fantasy API: the
Premier League terms reserve database rights and bar building a database from the
site without written approval. football-data.co.uk: the owner states that use is
for private individuals and excludes automated and AI use. ClubElo publishes no
licence at all, and unknown terms are not permission. FPL and ClubElo were listed
PUBLIC and hostable here until 9 October 2026, when the terms were read again;
no code ever used either. Until the second audit this tier existed here and in the
names and notes of four entries whose type was `LOCAL_LICENSED`, which means
downloadable at runtime. It is now a tier of the type, `DataTier.REFERENCE_ONLY`:
an entry at it cannot be written with a permission on, `assert_may_ingest`,
`assert_may_host` and `assert_may_commit` refuse it by the tier, and an adapter
class that names one fails where it is defined.

**LOCAL_LICENSED** — runtime download into a gitignored cache, readable locally,
never served to a third party. StatsBomb open data and any paid API feed.
API-Football is the one paid feed with an entry. That entry said a hosted instance
may serve numbers derived from it. No terms of use are recorded for it, so since the
second audit it may not; no adapter exists and nothing outside the tests reads the
entry. The hostable
set is the three PUBLIC sources, and a test asserts that it is exactly those.

**TRIAL** — time-boxed vendor trial data. Usable for calibration; never a
dependency of anything that must keep working after expiry. Currently empty, and a
test asserts it stays empty.

## StatsBomb specifically

The Public Data User Agreement is not an open licence. Clause 1.2.1 bars the user
from providing the data to any third party. Clause 1.2.2 bars commercial
exploitation of the data **or any analysis derived from it** — the restriction
follows through to derived scores. Clause 1.4 requires the StatsBomb brand logo on
published analysis.

Consequence: no vendored events, no cached Parquet in git, no machine-readable
table derived from it in the tree, and a hosted instance may never serve a
StatsBomb-derived number. `assert_may_host("statsbomb")` raises.

Published analysis formed from StatsBomb data names the source and carries the
logo. The documents that print such analysis are the README, METRICS.md,
[E-01](docs/research/E-01-metronome-fit.md),
[Stage 1C](docs/research/STAGE-1C-EXTERNAL-REPLICATION.md), the erratum
[M-07](docs/research/M-07-rank-ties.md) and the draft protocols E-09, E-11 and
E-12. The logo is the file the provider ships with the data, kept at
`docs/assets/statsbomb/`. This paragraph stated the requirement for 39 days, from
31 August to 9 October 2026, while E-01 and Stage 1C carried no logo. The logo came in commit `b7bc919`; a branch that does not hold that commit shows the
two reports without it.

What `tests/test_licensing.py` checks. It keeps three lists, and every Markdown
file that git tracks or would track and that mentions StatsBomb must be on exactly
one. A file on the first prints a figure formed from StatsBomb data: it must draw
the logo by a path that resolves from where the file is, name the data source and
say that its analysis is formed from StatsBomb data. A file on the second mentions
the provider and prints no such figure. Whether a file prints one is a reading by
a person, recorded in the list; the test cannot see a figure. The third list holds
one file: the preregistration of E-02, which quotes two figures of E-01 and can
never be edited, since nothing under `experiments/preregistered/` is. It is held
to the sha256 of the bytes that were read and to naming E-01, which carries the
credit.

One served view prints such analysis, and it carries the same credit. Player Lab's
"Why only five?" view prints the external-replication label of each construct and
the Metronome Fit conclusion, with the logo, the data-source sentence and a link
from each to its research note. Each link leads to the note on the default branch: while that
branch lacks commit `b7bc919`, the link leads to a copy with no logo. The logo the view draws is a second,
identical copy of the logo file, kept under `web/assets/` because the server
serves that folder and not `docs/`. No number derived from StatsBomb data may be
served. `tests/test_served_credit.py` holds the two logo files identical and finds
no such number in the four replies it reads: the construct catalogue, the bundle's
meta and two profiles.

A sha256 digest of a provider's files is not data and not a table derived from
data, so a preregistered protocol may pin its inputs by digest.

One constant in the code was chosen from StatsBomb-side analysis. The StatsBomb
estimator of chance creation in `galactico/domain/constructs.py` has a minutes
floor of 450, and the note beside it quotes the curve the floor was read from.
Both sit in a hashed registry entry, so they are recorded here and not edited.
They are not served: Player Lab serves the estimator of its bundle's own regime.
Two docstrings quote such figures as comments: `galactico/reliability/confound.py`
(figures of E-01, with their source named) and `galactico/domain/roles.py` (a
share measured on the four-league corpus).

One derived table was in the repository. `experiments/external_replication.json`
carried the StatsBomb half of Stage 1C, four blocks of aggregate figures, beside
the public half, from the commit that published the report until 9 October 2026.
The guard reads paths, extensions and the content of tracked text files, for
provider schema keys, credentials and bulk record dumps; none of its patterns
matches a block of aggregate figures. The blocks are out of every tree from commit
`d3d3ff5` on and remain in the history before it; a branch that does not yet hold that
commit still has them in its tree. Per-league reliability, confound share and closest baseline as
ranges, and the La Liga means and standard deviations are in the report as
published analysis. The other fields of the removed blocks, the ordering figures
among them, are only in the history and in a local record. The runner writes that
half under the gitignored cache. A test reads the key names of every JSON file
under `experiments/` and fails on one that names the provider. It reads names, not
values, so the control is the writer: the same test holds the tracked record to
its four public blocks and the runner to their prefix.

## Attribution

Pappalardo requires citing the constituent figshare articles individually plus the
2019 Scientific Data paper. SkillCorner requires the MIT copyright line.
DFL/Sportec requires CC BY 4.0 attribution.
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

`scripts/check_licensing.py` blocks files over 512 KB, data file extensions,
anything under a restricted tier directory, committed environment files,
credential-shaped strings, and provider schema keys or a bulk record dump in
tracked text. The two content checks read a file whose suffix is one of fourteen
text suffixes and whose size is within the ceiling, and no other file. It lists
paths NUL-separated (`git ls-files -z`): git prints any other listing of a name
that is not plain ASCII in quotes, and the guard used to count such a file as
checked without opening it. A listed file that cannot be opened is now exit 2,
which is not a pass. Three exemptions remain. `tests/fixtures/` is exempt from the
size and extension checks and from the check for schema keys and record dumps. An
image under `docs/screenshots/` is exempt from the size ceiling and from nothing
else; until the second audit the whole directory had the exemptions of the
fixtures. The script itself is exempt from the two content checks, because it
holds their patterns. It runs before lint and before tests, because a licence
mistake is the only failure here that a later commit cannot fix.

