"""Per-match appearances from the season article's revision history (REC 1.3), rule by rule.

A synthetic season is built in code: invented players (``season_v4.SQUAD``), invented matches,
and after each match a revision of the statistics table (``season_wiki.snapshot``) whose stamp
names the match just played. Each test then plants one thing the rules must handle:

- a change of 2 (an editor catching up, like Espí's after Elche) or a negative change;
- a missing stamp (two matches updated in one edit), of one competition or of two;
- a match whose changes of 1 fall outside [11, 16], and a later revision that repairs it;
- a match the tables have not caught up with yet;
- a revision saved before kick-off whose stamp already names the match (R9 poisoning);
- a row that appears mid-season, and a row missing before the season's first match;
- a season count the attributed appearances do not add up to, and an appearance in a match
  football-data.org does not name the player for.

The service is then read through an ``httpx.MockTransport``: the paged list, at most 50
contents a request, content kept by revision id, the raw fallback, the agent and ``maxlag``.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import httpx
import season_v4 as v4
import season_wiki as wiki

from galactico.domain.labels import scan_labels
from galactico.domain.thesis import BANNED_KEY_PARTS, banned_key_paths
from galactico.match_centre.season import revisions as rv
from galactico.match_centre.season.model import (
    Match,
    Named,
    PersonRef,
    SeasonLine,
    Side,
    TeamRef,
    to_json,
)
from galactico.match_centre.season.wiki_season import MADRID_REF, person_key, title_key
from galactico.match_centre.studio import AGENT

PLAYERS = [p for p in v4.SQUAD if p.group is not None]          # twenty listed players
COLUMNS = ("la-liga", "copa-del-rey", "champions-league", "supercopa")
CHECKED = "2026-11-26T12:00:00+00:00"


def title(p: v4.Player) -> str:
    return title_key(p.wp_title)


def key(p: v4.Player) -> str:
    return person_key(p.wp_title)


def fixture(n: int, competition: str, day: str, hour: int = 19) -> rv.Fixture:
    return rv.Fixture(f"m{n}-real-madrid-v-club-{day}", competition, day,
                      f"{day}T{hour:02}:00:00Z", f"Real Madrid v Club {n}")


def text(counts: dict[str, dict[str, int | str]], stamp: str, *, drop=()) -> str:
    rows = [wiki.efs_player2(p, [(counts[title(p)][c], 0) for c in COLUMNS])
            for p in PLAYERS if title(p) not in drop]
    return wiki.snapshot(rows, stamp)


class Season:
    """A season of matches with 13 appearances each, a revision after each."""

    def __init__(self, fixtures: list[rv.Fixture], played: list[set[int]] | None = None):
        self.fixtures = fixtures
        self.played = played or [set(range(13)) for _ in fixtures]
        self.counts = {title(p): dict.fromkeys(COLUMNS, 0) for p in PLAYERS}
        self.texts: list[tuple[int, str, str]] = []   # (revid, timestamp, wikitext)
        self.revid = 1000
        self.add("2026-08-20T10:00:00Z", "2026-05-30")

    def add(self, timestamp: str, stamp: str, *, drop=(), counts=None) -> rv.Snap:
        self.revid += 1
        content = text(counts or self.counts, stamp, drop=drop)
        self.texts.append((self.revid, timestamp, content))
        return rv.snapshot_of(self.revid, timestamp, content)

    def play(self, k: int, *, extra: dict[int, int] | None = None, stamp: str | None = None,
             hours: int = 3) -> rv.Snap | None:
        fx = self.fixtures[k]
        for i in self.played[k]:
            self.counts[title(PLAYERS[i])][fx.competition] += 1
        for i, units in (extra or {}).items():
            self.counts[title(PLAYERS[i])][fx.competition] += units
        if stamp == "":
            return None
        when = datetime.fromisoformat(fx.kickoff_utc.replace("Z", "+00:00")) + timedelta(
            hours=hours)
        return self.add(when.strftime("%Y-%m-%dT%H:%M:%SZ"), stamp or fx.day)

    def snaps(self) -> list[rv.Snap]:
        return [rv.snapshot_of(revid, ts, content) for revid, ts, content in self.texts]

    def grid(self) -> rv.Grid:
        return rv.attribute(rv.pair(self.fixtures, self.snaps()), self.snaps(), checked=CHECKED)


def states(grid: rv.Grid, match: str) -> dict[str, str]:
    return {a.person.key: a.state for a in grid.appearances if a.match == match}


LEAGUE = [fixture(1, "la-liga", "2026-08-22"), fixture(2, "la-liga", "2026-08-29"),
          fixture(3, "champions-league", "2026-09-16"), fixture(4, "la-liga", "2026-09-20"),
          fixture(5, "la-liga", "2026-09-27")]


def test_a_change_of_one_is_appeared_and_of_none_did_not_appear():
    season = Season(LEAGUE[:3], [set(range(13)), set(range(2, 15)), set(range(5, 18))])
    for k in range(3):
        season.play(k)
    grid = season.grid()
    spans = rv.pair(season.fixtures, season.snaps())
    assert [len(s.fixtures) for s in spans] == [1, 1, 1]
    assert [s.after.stamp for s in spans] == [fx.day for fx in season.fixtures]
    for k, fx in enumerate(season.fixtures):
        found = states(grid, fx.key)
        assert {p for p, s in found.items() if s == "appeared"} == {
            key(PLAYERS[i]) for i in season.played[k]}
        assert {p for p, s in found.items() if s == "did_not_appear"} == {
            key(PLAYERS[i]) for i in range(20) if i not in season.played[k]}
    assert [c.appeared for c in grid.checks] == [13, 13, 13]
    assert all(c.attributable and c.line is None for c in grid.checks)
    assert grid.unattributed == ()
    # Each appearance names its revision pair.
    row = next(a for a in grid.appearances if a.match == LEAGUE[1].key)
    assert [s.revision for s in row.sources] == [spans[1].before.revid, spans[1].after.revid]
    assert row.sources[1].url == (
        f"https://en.wikipedia.org/wiki/Special:PermanentLink/{spans[1].after.revid}")


def test_a_change_of_two_or_a_negative_change_is_not_attributable_and_kept_as_units():
    """The Espí case: after a match with 16 changes of 1, one more player's count rose by 2.
    Seventeen would break the five-substitute bound; the rule does not guess."""
    fixtures = [LEAGUE[0], LEAGUE[1], LEAGUE[3]]
    season = Season(fixtures, [set(range(13)), set(range(16)), set(range(1, 14))])
    season.play(0)
    season.play(1, extra={18: 2})
    season.play(2, extra={0: -1})   # an editor takes one of player 0's two back
    grid = season.grid()
    second = states(grid, fixtures[1].key)
    assert second[key(PLAYERS[18])] == "not_attributable"
    assert sum(s == "appeared" for s in second.values()) == 16
    assert grid.checks[1].attributable and grid.checks[1].appeared == 16
    third = states(grid, fixtures[2].key)
    assert third[key(PLAYERS[0])] == "not_attributable"
    units = {(u.person.key, u.competition): (u.units, u.matches) for u in grid.unattributed}
    assert units == {(key(PLAYERS[0]), "la-liga"): (-1, (fixtures[2].key,)),
                     (key(PLAYERS[18]), "la-liga"): (2, (fixtures[1].key,))}
    # The units stay in the season count: attributed + units equals the article's count.
    lines = [SeasonLine(PersonRef(key(p), p.wp_name), c, season.counts[title(p)][c], None,
                        None, None, None, None, ()) for p in PLAYERS for c in COLUMNS]
    titles = {key(p): title(p) for p in PLAYERS}
    assert rv.reconcile(grid, lines, season.fixtures, titles) == ()


def test_a_missing_stamp_reads_two_matches_of_one_competition_together():
    season = Season(LEAGUE[3:5], [set(range(13)) | {15}, set(range(13)) | {16}])
    season.play(0, stamp="")          # no revision names the first match's day
    season.play(1)
    spans = rv.pair(season.fixtures, season.snaps())
    assert [len(s.fixtures) for s in spans] == [2]
    grid = season.grid()
    for fx in season.fixtures:
        found = states(grid, fx.key)
        assert all(found[key(PLAYERS[i])] == "appeared" for i in range(13))     # 2: both
        assert found[key(PLAYERS[19])] == "did_not_appear"                      # 0: neither
        assert found[key(PLAYERS[15])] == "not_attributable"                    # 1: both n/a
        assert found[key(PLAYERS[16])] == "not_attributable"
    units = {u.person.key: (u.units, u.matches) for u in grid.unattributed}
    assert units[key(PLAYERS[15])] == (1, tuple(fx.key for fx in season.fixtures))
    assert all(c.attributable and "in one edit" in c.line for c in grid.checks)


def test_a_missing_stamp_over_two_competitions_settles_each_column():
    fixtures = [fixture(1, "la-liga", "2026-09-20"), fixture(2, "champions-league",
                                                             "2026-09-23")]
    season = Season(fixtures, [set(range(13)), set(range(4, 17))])
    season.play(0, stamp="")
    season.play(1)
    grid = season.grid()
    assert states(grid, fixtures[0].key)[key(PLAYERS[0])] == "appeared"
    assert states(grid, fixtures[1].key)[key(PLAYERS[0])] == "did_not_appear"
    assert states(grid, fixtures[1].key)[key(PLAYERS[16])] == "appeared"
    assert [c.appeared for c in grid.checks] == [13, 13] and grid.unattributed == ()


def test_a_match_outside_eleven_to_sixteen_is_given_up_until_a_later_revision_repairs_it():
    season = Season(LEAGUE[:2])
    season.play(0)
    # The editor updated nine players and the stamp, then the other four an hour later.
    fx = season.fixtures[1]
    partial = {t: dict(c) for t, c in season.counts.items()}
    for i in range(9):
        partial[title(PLAYERS[i])][fx.competition] += 1
    season.add("2026-08-29T22:00:00Z", fx.day, counts=partial)
    grid = season.grid()
    check = grid.checks[1]
    assert not check.attributable and check.appeared == 0
    assert "9 players" in check.line and scan_labels([check.line]) == []
    assert set(states(grid, fx.key).values()) == {"not_attributable"}
    assert {u.units for u in grid.unattributed} == {1}
    # A later revision with the same stamp completes the table: the match is attributed.
    season.play(1, hours=4)
    grid = season.grid()
    assert grid.checks[1].attributable and grid.checks[1].appeared == 13
    assert grid.unattributed == ()
    # Too many (seventeen changes of 1) is given up the same way.
    over = Season(LEAGUE[:1], [set(range(17))])
    over.play(0)
    assert not over.grid().checks[0].attributable


def test_a_match_the_tables_have_not_caught_up_with_waits():
    season = Season(LEAGUE[:2])
    season.play(0)
    season.play(1, stamp="")
    grid = season.grid()
    assert grid.checks[1].line == rv.PENDING and not grid.checks[1].attributable
    assert set(states(grid, LEAGUE[1].key).values()) == {"not_attributable"}
    assert grid.checks[0].attributable


def test_a_revision_saved_before_kick_off_never_pairs_with_the_match():
    """R9 poisoning: an editor stamped the day before the match had kicked off, with counts
    that are not the match's. A snapshot after a match is never one saved before it."""
    season = Season(LEAGUE[:2])
    season.play(0)
    poisoned = {t: {c: v + 1 for c, v in row.items()} for t, row in season.counts.items()}
    season.add("2026-08-29T12:00:00Z", LEAGUE[1].day, counts=poisoned)
    season.play(1)
    spans = rv.pair(season.fixtures, season.snaps())
    assert spans[1].after.timestamp > LEAGUE[1].kickoff_utc
    grid = season.grid()
    assert grid.checks[1].attributable and grid.checks[1].appeared == 13


def test_rows_before_the_first_match_count_zero_and_a_row_added_later_is_not_attributed():
    late = PLAYERS[19]
    season = Season(LEAGUE[:2], [set(range(13)), set(range(12)) | {19}])
    # The table before the season's first match lists only some players: the rest count 0.
    season.texts[0] = (season.texts[0][0], season.texts[0][1],
                       text(season.counts, "2026-05-30", drop={title(late), title(PLAYERS[0])}))
    season.play(0)
    first_after = season.texts[-1]
    season.texts[-1] = (first_after[0], first_after[1],
                        text(season.counts, LEAGUE[0].day, drop={title(late)}))
    season.play(1)
    grid = season.grid()
    assert states(grid, LEAGUE[0].key)[key(PLAYERS[0])] == "appeared"
    assert states(grid, LEAGUE[1].key)[key(late)] == "not_attributable"
    assert grid.first[title(PLAYERS[1])]["la-liga"] == 0


def test_a_season_count_that_does_not_add_up_is_named():
    season = Season(LEAGUE[:1])
    season.play(0)
    grid = season.grid()
    p = PLAYERS[0]
    lines = [SeasonLine(PersonRef(key(p), p.wp_name), "la-liga", 3, None, None, None, None,
                        None, ()),
             SeasonLine(PersonRef(key(PLAYERS[1]), PLAYERS[1].wp_name), "la-liga", None, None,
                        None, None, None, None, ())]
    found = rv.reconcile(grid, lines, season.fixtures, {key(p): title(p)})
    assert [(m.person.key, m.attributed, m.unattributed, m.listed) for m in found] == [
        (key(p), 1, 0, 3), (key(PLAYERS[1]), 1, 0, None)]
    assert scan_labels([m.line for m in found]) == []


def test_an_appearance_without_a_matchday_squad_listing_is_a_source_conflict():
    season = Season(LEAGUE[:1])
    season.play(0)
    grid = season.grid()
    match = LEAGUE[0].key
    named = [Named(PersonRef(key(PLAYERS[i]), "x"), match, ()) for i in range(1, 13)]
    found = rv.conflicts(grid.appearances, named, persons={key(p) for p in PLAYERS[:14]},
                         matches={match}, labels={match: "Real Madrid v Club 1"})
    assert [c.person.key for c in found] == [key(PLAYERS[0])]
    assert "Real Madrid v Club 1" in found[0].line and scan_labels([found[0].line]) == []
    # A player whose list was not read, or a match his list does not cover, is no conflict.
    assert rv.conflicts(grid.appearances, named, persons=set(), matches={match}) == ()
    assert rv.conflicts(grid.appearances, named, persons={key(PLAYERS[0])}, matches=set()) == ()


def test_the_grid_passes_the_key_and_copy_guards():
    season = Season(LEAGUE[:3], [set(range(13)), set(range(16)), set(range(9))])
    season.play(0)
    season.play(1, extra={18: 2})
    season.play(2)
    grid = season.grid()
    data = to_json(grid)
    assert banned_key_paths(data, parts=BANNED_KEY_PARTS) == []
    assert scan_labels(data, keys=False) == []
    sentences = [rv.PENDING] + [c.line for c in grid.checks if c.line]
    two = Season(LEAGUE[3:5], [set(range(20)), set(range(20))])
    two.play(0, stamp="")
    two.play(1)
    sentences += [c.line for c in two.grid().checks if c.line]
    assert len(set(sentences)) >= 3 and scan_labels(sentences) == []


def test_the_plan_reads_one_revision_per_match_and_the_baseline():
    stubs = [rv.RevisionStub(n, f"2026-08-{d:02}T{h:02}:00:00Z") for n, (d, h) in enumerate(
        [(20, 10), (21, 9), (22, 22), (23, 8), (29, 9), (29, 23), (30, 1)], start=1)]
    fixtures = LEAGUE[:2]
    assert rv.plan(stubs, fixtures) == [2, 5, 7]
    assert rv.plan(stubs, fixtures, upcoming="2026-08-30T00:00:00Z") == [2, 5, 6]
    assert rv.plan([], fixtures) == [] and rv.plan(stubs, []) == []


# ------------------------------------------------------------------ the service


def match(fx: rv.Fixture) -> Match:
    other = TeamRef(key="club", fd_id=None, name="Club", short="Club", plate="CLU")
    return Match(key=fx.key, fd_id=None, legacy_keys=(), competition=fx.competition,
                 season="2026/27", stage=None, matchday=None, group=None,
                 kickoff_utc=fx.kickoff_utc, kickoff_confirmed=True, status="FINISHED",
                 home=MADRID_REF, away=other, result=Side(1, 0), half_time=Side(None, None),
                 duration="REGULAR", winner="HOME_TEAM", referee=None, ground=None,
                 attendance=None, report_url=None, source_updated=None, sources=())


class Upstream:
    """MediaWiki over a synthetic revision history, with filler edits between matches."""

    def __init__(self, texts: list[tuple[int, str, str]], *, content_status: int = 200):
        self.texts = {revid: (ts, content) for revid, ts, content in texts}
        self.requests: list[httpx.Request] = []
        self.content_status = content_status

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        params = request.url.params
        if request.url.path == "/w/index.php":
            ts, content = self.texts[int(params["oldid"])]
            return httpx.Response(200, text=content)
        if "revids" in params:
            if self.content_status != 200:
                return httpx.Response(self.content_status, text=wiki.RATE_LIMITED)
            wanted = [int(r) for r in params["revids"].split("|")]
            assert len(wanted) <= 50
            return httpx.Response(200, json=wiki.revision_contents(
                [(r, *self.texts[r]) for r in wanted]))
        end = params["rvend"]
        listed = sorted(((r, ts) for r, (ts, _) in self.texts.items() if ts >= end),
                        reverse=True)
        start = int(params.get("rvcontinue", "0"))
        page = listed[start:start + 50]
        more = str(start + 50) if start + 50 < len(listed) else None
        return httpx.Response(200, json=wiki.revision_list(page, more=more))


def busy_season() -> Season:
    fixtures = [fixture(n, "la-liga", f"2026-{8 + (n // 4):02}-{1 + 7 * (n % 4):02}")
                for n in range(8)]
    season = Season(fixtures)
    for k, fx in enumerate(fixtures):
        # Eight filler edits before each match (prose), then the match's table.
        kick = datetime.fromisoformat(fx.kickoff_utc.replace("Z", "+00:00"))
        for n in range(8):
            when = kick - timedelta(hours=40 - n)
            season.add(when.strftime("%Y-%m-%dT%H:%M:%SZ"),
                       fixtures[k - 1].day if k else "2026-05-30")
        season.play(k)
    return season


def test_the_service_lists_in_pages_reads_what_the_plan_needs_and_keeps_it():
    season = busy_season()
    upstream = Upstream(season.texts)
    service = rv.Revisions(transport=httpx.MockTransport(upstream))
    matches = [match(fx) for fx in season.fixtures]
    grid, spans = asyncio.run(service.grid(wiki.TITLE, matches, since="2026-07-01T00:00:00Z"))
    assert len(season.texts) > 50
    lists = [r for r in upstream.requests if "revids" not in r.url.params]
    contents = [r for r in upstream.requests if "revids" in r.url.params]
    assert len(lists) == 2 and len(contents) == 1
    assert len(contents[0].url.params["revids"].split("|")) == len(season.fixtures) + 1
    assert all(c.attributable for c in grid.checks) and len(grid.checks) == 8
    assert all(r.headers["user-agent"] == AGENT["User-Agent"] and r.url.params["maxlag"] == "5"
               for r in upstream.requests)
    assert lists[0].url.params["rvlimit"] == "50"
    # Kept: a refresh lists only what is newer and reads no content it already holds.
    upstream.requests.clear()
    service.cache = type(service.cache)(8)
    asyncio.run(service.grid(wiki.TITLE, matches, since="2026-07-01T00:00:00Z"))
    assert [r.url.params["rvend"] for r in upstream.requests] == [season.texts[-1][1]]
    assert service.content_requests == 1


def test_a_rate_limited_content_request_falls_back_to_each_revisions_raw_text():
    season = busy_season()
    upstream = Upstream(season.texts, content_status=429)
    service = rv.Revisions(transport=httpx.MockTransport(upstream))
    grid, _ = asyncio.run(service.grid(wiki.TITLE, [match(fx) for fx in season.fixtures],
                                       since="2026-07-01T00:00:00Z"))
    raw = [r for r in upstream.requests if r.url.path == "/w/index.php"]
    assert len(raw) == len(season.fixtures) + 1
    assert all(r.url.params["action"] == "raw" and r.headers["user-agent"] == AGENT["User-Agent"]
               for r in raw)
    assert all(c.attributable for c in grid.checks)


def test_the_service_reads_only_finished_matches_in_kick_off_order():
    season = Season(LEAGUE[:2])
    season.play(0)
    season.play(1)
    upstream = Upstream(season.texts)
    service = rv.Revisions(transport=httpx.MockTransport(upstream),
                           clock=lambda: datetime(2026, 11, 26, 12, tzinfo=UTC))
    later = match(fixture(9, "la-liga", "2026-12-01"))
    later = Match(**{**later.__dict__, "status": "TIMED", "result": Side(None, None)})
    grid, spans = asyncio.run(service.grid(
        wiki.TITLE, [match(LEAGUE[1]), later, match(LEAGUE[0])], since="2026-07-01T00:00:00Z"))
    assert [c.match for c in grid.checks] == [LEAGUE[0].key, LEAGUE[1].key]
    assert grid.appearances[0].sources[0].checked == CHECKED
