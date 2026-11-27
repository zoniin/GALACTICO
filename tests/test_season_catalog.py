"""The catalogue (PLAN D3-A, ``season/catalog.py``): source chains, overlay, versions, credits,
budgets, the Madrid joins and the goal reports, on invented sources.

Each test targets one way the one API the pages read could mislead or overspend:

- a chain that asks football-data.org with no key (a request that must never be made), or
  that does not fall back when the key is refused;
- a today row and a season row of one match where the older one is shown;
- a finish that does not move a competition's version, so a stale table or list is served;
- a credit for a source the value did not use, or none for one it did;
- a page view that spends more football-data.org requests cold than PLAN 3.6 allows, or any
  warm (the ``RequestLedger`` below counts them);
- a Madrid player given another's facts, or a goal given a scorer the source does not name;
- a served sentence with a banned word (R3) or a reply key with a banned part (B5).

football-data.org is ``season_v4``'s invented world behind ``httpx.MockTransport``;
OpenFootball and OpenLigaDB are stubbed at their season reads with rows built here from the
same world; Wikipedia and Wikidata are ``season_wiki``'s builders behind one MockTransport.
Nothing reads a recorded reply or the network.
"""

from __future__ import annotations

import ast
import asyncio
import importlib.util
import sys
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import httpx
import pytest
import season_v4 as v4
import season_wiki as wiki

from galactico.domain.labels import scan_labels
from galactico.domain.thesis import BANNED_KEY_PARTS, banned_key_paths
from galactico.match_centre.feed import FeedError, Snapshot
from galactico.match_centre.kickoff import from_utc
from galactico.match_centre.openfootball import OpenFootball
from galactico.match_centre.openligadb import OpenLigaDB
from galactico.match_centre.season import catalog as cat
from galactico.match_centre.season import derive
from galactico.match_centre.season import goals as goal_rules
from galactico.match_centre.season.budget import Budget, RequestBudget
from galactico.match_centre.season.catalog import Catalog, NotListed, Unknown
from galactico.match_centre.season.football_data import FootballData, NotCovered
from galactico.match_centre.season.infobox import Infoboxes
from galactico.match_centre.season.keys import MADRID_KEY
from galactico.match_centre.season.model import to_json
from galactico.match_centre.season.wiki_season import MadridSeason
from galactico.match_centre.season.wikidata import Wikidata

ROOT = Path(__file__).resolve().parents[1]
SEASON = ROOT / "galactico" / "match_centre" / "season"
NOW = datetime(2026, 11, 27, 18, 0, tzinfo=UTC)
"""Friday 27 November 2026, 19:00 in Madrid: the sample world's today."""
TODAY = date(2026, 11, 27)
FD_HOST = "api.football-data.org"


def run(coroutine):
    return asyncio.run(coroutine)


class Clock:
    """The wall clock every client and the catalogue read, moved by hand."""

    def __init__(self) -> None:
        self.now = NOW

    def __call__(self) -> datetime:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += timedelta(seconds=seconds)


# ------------------------------------------------------------------ the free feeds, invented

OF_NAMES = {86: "Real Madrid CF", 90001: "A FC", 90002: "Norte CF",
            90003: "Ribera Unión Deportiva"}
"""OpenFootball's names for the La Liga clubs: its own forms, not football-data.org's."""
OF_RESULTS_THROUGH = "2026-09-20"
"""The free file's results stop here (a lagging volunteer file)."""


def of_rows(matches: list[dict], *, through: str = OF_RESULTS_THROUGH) -> list[dict]:
    """football-data.org's invented matches as OpenFootball writes them: local Central
    European date and time, its club names, a result only up to ``through``."""
    rows = []
    for m in matches:
        if m["homeTeam"]["id"] not in OF_NAMES or m["awayTeam"]["id"] not in OF_NAMES:
            continue
        local = from_utc(datetime.fromisoformat(m["utcDate"].replace("Z", "+00:00")), "CET")
        row = {"round": f"Matchday {m['matchday']}", "date": local.date().isoformat(),
               "time": f"{local:%H:%M}", "team1": OF_NAMES[m["homeTeam"]["id"]],
               "team2": OF_NAMES[m["awayTeam"]["id"]]}
        full = m["score"]["fullTime"]
        if m["status"] == "FINISHED" and row["date"] <= through:
            row["score"] = {"ft": [full["home"], full["away"]]}
        rows.append(row)
    return rows


OLD_MEETING = {"round": "Matchday 9", "date": "2015-10-17", "time": "20:00",
               "team1": "Real Madrid CF", "team2": "Norte CF", "score": {"ft": [2, 1]}}
"""An invented meeting from an earlier season's file, for the head-to-head."""

OL_IDS = {"Real Madrid": 1, "Test Roma": 2, "Test Porto": 3, "Nord Kickers 1904": 4}


def ol_goal(goal_id, home, away, minute, name, *, own=False, pen=False):
    return {"goalID": goal_id, "scoreTeam1": home, "scoreTeam2": away, "matchMinute": minute,
            "goalGetterID": goal_id + 100, "goalGetterName": name, "isPenalty": pen,
            "isOwnGoal": own, "isOvertime": False}


def ol_record(match_id, utc, home, away, matchday, result=None, goals=()):
    return {"matchID": match_id, "matchDateTimeUTC": utc,
            "group": {"groupName": f"{matchday}. Spieltag", "groupOrderID": matchday,
                      "groupID": matchday},
            "team1": {"teamId": OL_IDS[home], "teamName": home},
            "team2": {"teamId": OL_IDS[away], "teamName": away},
            "matchIsFinished": result is not None,
            "matchResults": ([{"resultTypeID": 2, "pointsTeam1": result[0],
                               "pointsTeam2": result[1]}] if result else []),
            "goals": list(goals)}


UCL = [
    ol_record(11, "2026-09-16T19:00:00Z", "Real Madrid", "Test Roma", 1, (2, 0), [
        ol_goal(1, 1, 0, 8, "K. Delantero"), ol_goal(2, 2, 0, 77, "N. Enlace")]),
    ol_record(12, "2026-09-16T19:00:00Z", "Test Porto", "Nord Kickers 1904", 1, (1, 1), [
        ol_goal(3, 1, 0, 10, "P. Uno"), ol_goal(4, 1, 1, 80, "")]),
    ol_record(13, "2026-11-24T20:00:00Z", "Test Roma", "Real Madrid", 2, (1, 3), [
        ol_goal(5, 1, 0, 20, "R. Uno"), ol_goal(6, 1, 1, 25, "K. Delantero"),
        ol_goal(7, 1, 2, 51, "N. Enlace"), ol_goal(8, 1, 3, 88, "R. Dos", own=True)]),
    ol_record(14, "2026-11-27T17:45:00Z", "Test Porto", "Test Roma", 2, None, [
        ol_goal(9, 0, 1, 30, "R. Uno"), ol_goal(10, 0, 2, 44, "R. Dos")]),
]
"""OpenLigaDB's invented Champions League: the world's matches, with goals; the paused match
lists one goal more than football-data.org's result."""


@pytest.fixture(autouse=True)
def free_feeds(monkeypatch):
    """OpenFootball and OpenLigaDB read from the invented rows, never the network."""
    world = v4.sample_world()

    async def of_season(self, code, year):
        if code == "es.1" and year == 2026:
            return Snapshot(of_rows(world.matches["PD"]), NOW.isoformat())
        if code == "es.1" and year == 2015:
            return Snapshot([OLD_MEETING], NOW.isoformat())
        return Snapshot([], NOW.isoformat())

    async def ol_season(self, shortcut, year):
        return Snapshot(UCL if (shortcut, year) == ("ucl", 2026) else [], NOW.isoformat())

    monkeypatch.setattr(OpenFootball, "season", of_season)
    monkeypatch.setattr(OpenLigaDB, "season", ol_season)


# ------------------------------------------------------------------ Wikipedia and Wikidata


@dataclass
class Wiki:
    """MediaWiki and Wikidata over ``season_wiki``'s builders, recording every request.
    ``unborn`` are players whose infobox states no birth date."""

    unborn: tuple[str, ...] = ("Hugo Central",)
    requests: list[httpx.Request] = field(default_factory=list)

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        params = request.url.params
        if request.url.host == "www.wikidata.org":
            if params.get("props") == "claims":
                ids = params["ids"].split("|")
                return httpx.Response(200, json=wiki.entities_claims({
                    q: {"P2048": [wiki.height("+183")], "P19": [wiki.birthplace("Q900001")]}
                    if q == "Q870017" else {} for q in ids}))
            return httpx.Response(200, json=wiki.entities_labels({"Q900001": "Villa Prueba"}))
        if params.get("action") == "parse":
            return httpx.Response(200, json=wiki.parse_reply(wiki.sample_article(),
                                                             wiki.squad_html()))
        if params.get("prop") == "pageprops":
            titles = params["titles"].split("|")
            return httpx.Response(200, json=wiki.pageprops_reply({
                t: f"Q8{_fd(t) % 100000:05}" if _fd(t) else None for t in titles}))
        if params.get("rvprop") in ("timestamp|ids", "ids"):
            return httpx.Response(200, json=wiki.revision_stamp(1000020,
                                                                "2026-11-25T22:52:44Z"))
        if params.get("rvprop") == "content":
            titles = params["titles"].split("|")
            return httpx.Response(200, json=wiki.articles_reply({
                t: self._infobox(t) for t in titles}))
        return httpx.Response(404)

    def _infobox(self, title: str) -> str | None:
        player = _player(title)
        if player is None:
            return None
        born = None if player.name in self.unborn else tuple(
            int(n) for n in player.born.split("-"))
        return wiki.infobox(name=player.wp_name, position="[[Forward (association football)|"
                            "Forward]]", born=born)


def _player(title: str) -> v4.Player | None:
    return next((p for p in v4.SQUAD if p.wp_title and p.wp_title.replace("_", " ") == title),
                None)


def _fd(title: str) -> int:
    player = _player(title)
    return player.fd_id if player else 0


# ------------------------------------------------------------------ the catalogue under test


@dataclass
class Setup:
    catalog: Catalog
    world: v4.World
    clock: Clock
    wiki: Wiki
    football: FootballData | None

    def fd_calls(self) -> int:
        return len(self.world.calls)


def build(*, key: str | None = "test-only", world: v4.World | None = None,
          wiki_stub: Wiki | None = None, gates=()) -> Setup:
    world = world or v4.sample_world()
    world.available = 1000
    clock = Clock()
    football = None
    if key is not None:
        football = FootballData(key, transport=world.transport(), now=clock, recheck=0,
                                budget=Budget(per_minute=1000, reserve=0))
    stub = wiki_stub or Wiki()
    transport = httpx.MockTransport(stub)
    catalog = Catalog(football=football, openfootball=OpenFootball(),
                      madrid=MadridSeason(transport=transport, clock=clock),
                      wikidata=Wikidata(transport=transport, clock=clock),
                      infoboxes=Infoboxes(transport=transport), gates=gates, clock=clock)
    return Setup(catalog, world, clock, stub, football)


def set_match(world: v4.World, code: str, match_id: int, **changes) -> None:
    """Replace one invented match of ``world`` by a copy with ``changes`` (``v4.match``)."""
    listed = world.matches[code]
    for n, m in enumerate(listed):
        if m["id"] == match_id:
            homes = {c.id: c for c in world.clubs[code]}
            args = dict(status=m["status"], code=code, matchday=m["matchday"],
                        stage=m["stage"], last_updated=m["lastUpdated"])
            result = (m["score"]["fullTime"]["home"], m["score"]["fullTime"]["away"])
            if result[0] is not None:
                args["result"] = result
            args.update(changes)
            listed[n] = v4.match(match_id, m["utcDate"], homes[m["homeTeam"]["id"]],
                                 homes[m["awayTeam"]["id"]], **args)
            return
    raise KeyError(match_id)


# ------------------------------------------------------------------ the chain


def test_with_a_key_the_day_is_one_request_in_the_declared_order():
    s = build()
    view = run(s.catalog.day(TODAY))
    assert s.fd_calls() == 1
    assert s.world.calls[0].startswith("/v4/matches?dateFrom=2026-11-26&dateTo=2026-11-28")
    assert [m.fd_id for m in view.value] == [100007, 200004, 300003]
    assert [m.competition for m in view.value] == ["la-liga", "champions-league",
                                                   "premier-league"]
    assert view.credits == ("football_data_org",), "no cup tie today: Wikipedia not shown"
    assert not view.freshness.partial


def test_with_no_key_no_request_reaches_football_data_and_the_free_feeds_answer(monkeypatch):
    reached: list[str] = []

    async def no_network(self, request):
        reached.append(request.url.host)
        raise httpx.ConnectError("no network in tests")

    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", no_network)
    assert FootballData.from_env({}, transport=httpx.MockTransport(lambda r: 1 / 0)) is None
    s = build(key=None)
    c = s.catalog
    day = run(c.day(date(2026, 8, 22)))
    assert [(m.home.name, m.away.name, m.result.home, m.result.away) for m in day.value] == [
        ("Norte CF", "Ribera Unión Deportiva", 0, 0), ("Real Madrid", "A FC", 3, 1)]
    madrid_game = day.value[1]
    assert madrid_game.home.key == MADRID_KEY and madrid_game.fd_id is None
    assert madrid_game.legacy_keys[0].startswith("es.1-2026-")
    assert day.credits == ("openfootball",), "OpenLigaDB was read, but no row of it is shown"
    views = [
        day, run(c.competitions()), run(c.season_matches("la-liga")), run(c.table("la-liga")),
        run(c.scorers("champions-league")), run(c.scorers("la-liga")), run(c.teams("la-liga")),
        run(c.team(MADRID_KEY)), run(c.team_matches(MADRID_KEY)),
        run(c.person("kai-delantero")), run(c.named("kai-delantero")), run(c.madrid()),
        run(c.match(madrid_game.legacy_keys[0])), run(c.goals(madrid_game.key)),
        run(c.search_entries()), run(c.h2h(MADRID_KEY, "norte-cf", NOW)),
    ]
    assert reached == [], "no request left the process"
    assert all("football_data_org" not in v.credits for v in views)
    competitions = [x.slug for x in views[1].value]
    assert competitions == ["la-liga", "champions-league", "copa-del-rey", "supercopa",
                            "premier-league", "bundesliga", "serie-a", "ligue-1"]
    assert views[3].value.derived and views[3].value.order == derive.DERIVED_ORDER
    assert views[5].value == [] and cat.NO_SCORERS in views[5].missing
    assert cat.NO_SQUADS in views[6].missing
    assert cat.NO_NAMED in views[10].missing
    lag = [line for line in day.freshness.lines if "results stop at" in line]
    assert lag, "the free file's lag is said"


def test_a_refused_key_falls_back_to_the_free_feeds_and_stops_asking():
    s = build(key="not-the-world's-token")
    view = run(s.catalog.day(date(2026, 8, 22)))
    assert s.fd_calls() == 1, "one request, answered 400"
    assert "football_data_org" not in view.credits and "openfootball" in view.credits
    assert [m.fd_id for m in view.value] == [None, None]
    for call in (s.catalog.season_matches("la-liga"), s.catalog.table("la-liga"),
                 s.catalog.match(view.value[1].key), s.catalog.team(MADRID_KEY)):
        found = run(call)
        assert "football_data_org" not in found.credits
    assert s.fd_calls() == 1, "the client is off for the hour: no second request"


def test_a_competition_football_data_does_not_reach_and_a_gated_one_are_unknown():
    s = build()
    s.world.fail = {"/competitions/PD/": "restricted"}
    found = run(s.catalog.season_matches("la-liga"))
    assert {m.fd_id for m in found.value} == {None}, "403: the free feeds carry La Liga"
    with pytest.raises(Unknown):
        run(s.catalog.season_matches("eredivisie"))
    for slug in ("copa-libertadores", "europa-league", "no-such-league"):
        with pytest.raises(NotCovered):
            run(s.catalog.season_matches(slug))
    assert "copa-libertadores" not in [c.slug for c in run(s.catalog.competitions()).value]
    gated = build(gates={"P-D9", "P5-B"})
    slugs = [c.slug for c in run(gated.catalog.competitions()).value]
    assert "copa-libertadores" in slugs and "europa-league" in slugs
    with pytest.raises(NotCovered):
        run(s.catalog.table("copa-del-rey"))


def test_an_unknown_key_is_unknown():
    s = build()
    for key in ("Not A Key", "999999-real-madrid-v-norte-2026-11-28", "real-madrid-v-x-2026-13-40",
                "es.1-2026-0000000000000000"):
        with pytest.raises(Unknown):
            run(s.catalog.match(key))
    with pytest.raises(Unknown):
        run(s.catalog.person("no-such-player"))
    assert issubclass(NotListed, Unknown) and issubclass(Unknown, FeedError)


# ------------------------------------------------------------------ overlay and versions


def test_the_today_overlay_shows_the_row_with_the_later_source_updated():
    s = build()
    before = run(s.catalog.season_matches("la-liga"))
    live = next(m for m in before.value if m.fd_id == 100007)
    assert (live.result.home, live.result.away) == (1, 0)
    set_match(s.world, "PD", 100007, result=(2, 0), last_updated="2026-11-27T20:41:00Z")
    s.clock.advance(61)
    run(s.catalog.day(TODAY))
    calls = s.fd_calls()
    after = run(s.catalog.season_matches("la-liga"))
    assert s.fd_calls() == calls, "the season resource is still fresh: overlaid, not refetched"
    live = next(m for m in after.value if m.fd_id == 100007)
    assert (live.result.home, live.result.away) == (2, 0)
    assert live.source_updated == "2026-11-27T20:41:00Z"

    s = build()
    set_match(s.world, "PD", 100007, last_updated="2026-11-27T10:00:00Z")
    run(s.catalog.day(TODAY))
    set_match(s.world, "PD", 100007, result=(3, 0), last_updated="2026-11-27T19:00:00Z")
    later = run(s.catalog.season_matches("la-liga"))
    live = next(m for m in later.value if m.fd_id == 100007)
    assert (live.result.home, live.result.away) == (3, 0), "the season row is the later"


def test_a_new_finish_in_the_day_resource_moves_its_competitions_version():
    s = build()
    run(s.catalog.day(TODAY))
    start, europe = s.catalog.version("la-liga"), s.catalog.version("champions-league")
    run(s.catalog.season_matches("la-liga"))
    run(s.catalog.table("la-liga"))
    calls = s.fd_calls()
    set_match(s.world, "PD", 100007, status="FINISHED", result=(1, 0),
              last_updated="2026-11-27T21:55:00Z")
    s.clock.advance(61)
    run(s.catalog.day(TODAY))
    assert s.catalog.version("la-liga") == start + 1
    assert s.catalog.version("champions-league") == europe
    calls += 1
    finished = run(s.catalog.season_matches("la-liga"))
    assert s.fd_calls() == calls + 1, "the new version is read once"
    assert next(m for m in finished.value if m.fd_id == 100007).status == "FINISHED"
    run(s.catalog.season_matches("la-liga"))
    run(s.catalog.table("la-liga"))
    assert s.fd_calls() == calls + 1, "standings wait ten minutes after the finish"
    s.clock.advance(cat.STANDINGS_DEBOUNCE.total_seconds())
    run(s.catalog.table("la-liga"))
    assert s.fd_calls() == calls + 2
    assert s.catalog.version("la-liga") // 1000 == TODAY.toordinal()


# ------------------------------------------------------------------ credits


def test_credits_list_only_the_sources_the_value_used():
    s = build()
    assert run(s.catalog.season_matches("premier-league")).credits == ("football_data_org",)
    assert run(s.catalog.competitions()).credits == ("football_data_org",)
    goals = run(s.catalog.goals("200003-test-roma-v-real-madrid-2026-11-24"))
    assert goals.credits == ("football_data_org", "wikipedia", "openligadb"), \
        "Wikipedia writes Madrid's names and fills the ground; Wikidata is not shown"
    keyless = build(key=None)
    assert run(keyless.catalog.competitions()).credits == ()
    assert run(keyless.catalog.season_matches("champions-league")).credits == ("openligadb",)
    assert run(keyless.catalog.season_matches("copa-del-rey")).credits == ("wikipedia",)


# ------------------------------------------------------------------ the request ledger


class RequestLedger:
    """football-data.org requests per catalogue call, counted at the transport, on a cold
    catalogue and then warm (PLAN 3.6, PL 7.1)."""

    def __init__(self, setup: Setup) -> None:
        self.setup = setup

    def spend(self, *calls) -> int:
        before = self.setup.fd_calls()
        for call in calls:
            run(call())
        return self.setup.fd_calls() - before


CAPS = {
    "matches": (1, lambda c: [lambda: c.day(TODAY)]),
    "leagues": (1, lambda c: [c.competitions]),
    "competition": (2, lambda c: [lambda: c.season_matches("la-liga"),
                                  lambda: c.table("la-liga")]),
    "competition, a lazy tab": (1, lambda c: [lambda: c.scorers("la-liga")]),
    "match": (1, lambda c: [lambda: c.match("100001-real-madrid-v-a-fc-2026-08-22"),
                            lambda: c.goals("100001-real-madrid-v-a-fc-2026-08-22")]),
    "team": (2, lambda c: [lambda: c.team(MADRID_KEY), lambda: c.team_matches(MADRID_KEY)]),
    "another team": (2, lambda c: [lambda: c.team("90002-norte", competition="la-liga"),
                                   lambda: c.team_matches("90002-norte")]),
    "player": (2, lambda c: [lambda: c.person("70017-kai-delantero")]),
    "another player": (2, lambda c: [lambda: c.person("71021-bruno-brisa")]),
    "a non-Madrid player's matches tab": (1, lambda c: [lambda: c.named("71021-bruno-brisa")]),
    "search": (0, lambda c: [c.search_entries]),
    "builder": (0, lambda c: [c.madrid]),
}


@pytest.fixture
def ledger() -> RequestLedger:
    """A ``RequestLedger`` over a cold catalogue with the key."""
    return RequestLedger(build())


@pytest.mark.parametrize("view", list(CAPS))
def test_a_cold_view_stays_within_its_cap_and_a_warm_one_makes_no_request(view, ledger):
    cap, calls = CAPS[view]
    assert ledger.spend(*calls(ledger.setup.catalog)) <= cap
    assert ledger.spend(*calls(ledger.setup.catalog)) == 0


def test_the_head_to_head_reads_one_season_cold_and_says_it_is_partial():
    s = build()
    s.world.past[("PD", 2025)] = [
        v4.match(150001, "2026-03-01T20:00:00Z", v4.NORTE, v4.MADRID, status="FINISHED",
                 result=(0, 1), matchday=26),
        # R9 poison: a result dated after the head-to-head's day must change nothing.
        v4.match(150002, "2026-12-01T20:00:00Z", v4.MADRID, v4.NORTE, status="FINISHED",
                 result=(0, 5), matchday=27)]
    run(s.catalog.season_matches("la-liga"))
    ledger = RequestLedger(s)
    with RequestBudget(3) as budget:
        spent = ledger.spend(lambda: s.catalog.h2h(MADRID_KEY, "90002-norte", NOW))
    assert spent == 1 and budget.spent == 1
    view = run(s.catalog.h2h(MADRID_KEY, "90002-norte", NOW))
    assert view.freshness.partial, "2024 and 2023 are not held"
    h2h = view.value
    assert (h2h.meetings, h2h.wins, h2h.draws, h2h.losses) == (2, 2, 0, 0)
    assert [m.season for m in h2h.matches] == ["2025/26", "2015/16"]
    assert "OpenFootball" in h2h.span and "football-data.org" in h2h.span
    assert all(m.fd_id != 150002 for m in h2h.matches), "R9: the later result is not read"
    poisoned = run(s.catalog.h2h(MADRID_KEY, "90002-norte", datetime(2026, 3, 1, tzinfo=UTC)))
    assert poisoned.value.meetings == 1, "R9: a meeting on the day itself is not before it"


def test_a_view_over_its_budget_is_served_partial_not_failed():
    s = build()
    with RequestBudget(1):
        run(s.catalog.team(MADRID_KEY))
        view = run(s.catalog.team_matches(MADRID_KEY))
    assert view.freshness.partial and cat.DEFERRED_LINE in view.freshness.lines
    assert s.fd_calls() == 1
    with RequestBudget(0):
        for call in (s.catalog.day(TODAY), s.catalog.season_matches("premier-league"),
                     s.catalog.scorers("la-liga"), s.catalog.teams("champions-league")):
            listed = run(call)
            assert listed.value == [] and listed.freshness.partial
    assert s.fd_calls() == 1, "a deferred request is never made"


# ------------------------------------------------------------------ the Madrid joins


def test_madrids_squad_is_the_lists_order_joined_to_football_data_by_birth_and_surname():
    s = build()
    team = run(s.catalog.team(MADRID_KEY)).value
    keys = [e.person.key for e in team.squad]
    listed = [p for p in v4.SQUAD if p.group is not None]
    wp_order = [e.person.name for e in run(build(key=None).catalog.team(MADRID_KEY)).value.squad]
    assert [e.person.name for e in team.squad[:len(listed)]] == wp_order, "the list's order"
    assert sorted(wp_order) == sorted(p.wp_name for p in listed)
    by_name = {e.person.name: e for e in team.squad}
    kai = by_name["Kai Delantero"]
    assert (kai.person.key, kai.shirt, kai.born, kai.nationality) == (
        "70017-kai-delantero", 9, "1998-02-28", "Germany")
    assert by_name["Iñaki Portero"].person.key == "70001-inaki-portero", "accents set aside"
    assert by_name["Rui Banda"].person.key == "rui-banda", "shared birth and surname: unjoined"
    assert by_name["Rúben Banda"].person.key == "ruben-banda"
    assert by_name["Hugo Central"].person.key == "hugo-central", "no birth date: unjoined"
    assert len(keys) == len(set(keys)), "one key per player"
    tail = [e.person.key for e in team.squad[len(listed):]]
    assert tail == ["70021-oleh-nuevo", "70022-marco-reserva"], \
        "FD's players the list does not hold, in its order; an unjoined one is not listed twice"
    person = run(s.catalog.person("70017-kai-delantero"))
    p = person.value
    assert (p.shirt, p.born, p.wp_title, p.qid, p.height_cm, p.birthplace) == (
        9, "1998-02-28", "Kai Delantero", "Q870017", 183, "Villa Prueba")
    assert p.positions == ("Forward",)
    assert person.credits == ("football_data_org", "wikipedia", "wikidata")
    same = run(s.catalog.person("kai-delantero")).value
    assert same.ref.key == "70017-kai-delantero", "the Wikipedia key finds the joined player"
    alone = run(s.catalog.person("rui-banda"))
    assert alone.value.fd_id is None and cat.NOT_JOINED in alone.missing


def test_a_matchs_madrid_fill_takes_only_what_football_data_does_not_state():
    s = build()
    view = run(s.catalog.match("100001-real-madrid-v-a-fc-2026-08-22"))
    m = view.value
    assert (m.fd_id, m.referee, m.ground, m.attendance) == (
        100001, "Iván Silbato (Spain)", "Estadio Invento", 70123)
    assert m.report_url == "https://league.example.invalid/match/100001"
    assert [r.provider for r in m.sources] == ["football_data_org", "wikipedia"]


def test_a_legacy_board_id_resolves_to_the_football_data_match():
    keyless = build(key=None)
    old = next(m for m in run(keyless.catalog.day(date(2026, 8, 22))).value
               if m.home.key == MADRID_KEY)
    s = build()
    view = run(s.catalog.match(old.legacy_keys[0]))
    assert view.value.fd_id == 100001 and old.legacy_keys[0] in view.value.legacy_keys
    assert s.fd_calls() == 1
    slug = run(s.catalog.match("real-madrid-v-a-fc-2026-08-22")).value
    assert slug.fd_id == 100001, "a keyless slug key finds the keyed match"
    cup = run(s.catalog.match("atletico-prueba-v-real-madrid-2026-10-28")).value
    assert cup.competition == "copa-del-rey" and cup.fd_id is None


def test_madrids_season_facts_are_keyed_as_the_catalogue_keys_matches_and_players():
    s = build()
    run(s.catalog.season_matches("la-liga"))
    run(s.catalog.season_matches("champions-league"))
    run(s.catalog.teams("la-liga"))
    calls = s.fd_calls()
    view = run(s.catalog.madrid())
    assert s.fd_calls() == calls, "the season facts spend no football-data.org request"
    facts = view.value
    keys = {m.key for m in facts.article.matches}
    assert "100001-real-madrid-v-a-fc-2026-08-22" in keys
    assert "atletico-prueba-v-real-madrid-2026-10-28" in keys, "a cup tie keeps its own key"
    kai = [line for line in facts.article.lines if line.person.name == "Kai Delantero"]
    assert kai and {line.person.key for line in kai} == {"70017-kai-delantero"}
    assert cat.NO_APPEARANCES in view.missing
    assert [e.person.key for e in facts.squad] == [p.ref.key for p in facts.people]


# ------------------------------------------------------------------ goals through the catalogue


def test_a_champions_league_matchs_goals_come_from_openligadb_with_madrids_names():
    s = build()
    key = "200003-test-roma-v-real-madrid-2026-11-24"
    view = run(s.catalog.goals(key))
    assert [(e.minute, e.side, e.scorer, e.scorer_key) for e in view.value] == [
        (20, "home", "R. Uno", None), (25, "away", "Kai Delantero", "kai-delantero"),
        (51, "away", "Nico Enlace", "nico-enlace"), (88, "away", "R. Dos", None)]
    assert [c.line for c in view.coverage] == ["The source names the scorers of all 4 goals."]
    assert {e.match for e in view.value} == {key}
    run(s.catalog.teams("la-liga"))
    joined = run(s.catalog.goals(key)).value
    assert [e.scorer_key for e in joined if e.scorer_key] == [
        "70017-kai-delantero", "70011-nico-enlace"], "with FD's squad held, FD's keys"


def test_a_la_liga_madrid_matchs_goals_come_from_wikipedia_keyed_to_the_catalogue():
    s = build()
    run(s.catalog.teams("la-liga"))
    view = run(s.catalog.goals("100001-real-madrid-v-a-fc-2026-08-22"))
    assert [(e.minute, e.added, e.scorer, e.penalty) for e in view.value] == [
        (12, None, "Kai Delantero", True), (55, None, "Kai Delantero", False),
        (70, None, "A FC Striker", False), (90, 2, "Vinício Ala", False)]
    assert {e.match for e in view.value} == {"100001-real-madrid-v-a-fc-2026-08-22"}
    assert view.value[0].scorer_key == "70017-kai-delantero"
    assert view.coverage[0].line == "The source names the scorers of all 4 goals."
    assert "openligadb" not in view.credits


def test_a_paused_matchs_disagreement_keeps_both_and_a_match_without_a_source_says_so():
    s = build()
    view = run(s.catalog.goals("200004-test-porto-v-test-roma-2026-11-27"))
    assert len(view.value) == 2
    assert [c.line for c in view.coverage][-1] == (
        "The goal reports list 2 goals; the result feed shows 0–1. Both are shown as "
        "reported.")
    partial = run(s.catalog.goals("200002-test-porto-v-nord-kickers-2026-09-16"))
    assert partial.coverage[0].line == "The source names the scorers of 1 of 2 goals."
    none = run(s.catalog.goals("300002-test-albion-v-test-city-2026-11-26"))
    assert none.value == [] and none.coverage[0].line == goal_rules.NO_SOURCE
    ahead = run(s.catalog.goals("100008-real-madrid-v-norte-2026-11-28"))
    assert ahead.value == [] and ahead.coverage == ()


def test_scorers_without_a_key_are_counted_from_openligadbs_finished_matches():
    s = build(key=None)
    view = run(s.catalog.scorers("champions-league"))
    assert [(x.person.name, x.team.name, x.goals) for x in view.value] == [
        ("Kai Delantero", "Real Madrid", 2), ("Nico Enlace", "Real Madrid", 2),
        ("P. Uno", "Test Porto", 1), ("R. Uno", "Test Roma", 1)]
    assert view.value[0].person.key == "kai-delantero" and view.value[0].assists is None
    assert view.coverage[0].line == "The source names the scorers of 7 of 8 goals."
    keyed = run(build().catalog.scorers("la-liga"))
    assert [c.line for c in keyed.coverage] == [cat.listed_line(4)]


def test_the_search_makes_no_request_and_says_when_it_is_partial():
    s = build()
    cold = run(s.catalog.search_entries())
    assert s.fd_calls() == 0
    assert cold.freshness.partial and cat.SEARCH_PARTIAL in cold.freshness.lines
    assert [e.kind for e in cold.value[:2]] == ["competition", "competition"]
    run(s.catalog.teams("la-liga"))
    warm = run(s.catalog.search_entries()).value
    clubs = [e for e in warm if e.kind == "club"]
    assert clubs[0].key == MADRID_KEY and {e.name for e in clubs} >= {"Norte CF", "A FC"}
    players = [e for e in warm if e.kind == "player"]
    assert players[0].madrid and any(e.key == "71021-bruno-brisa" for e in players)


# ------------------------------------------------------------------ keys and copy (B5, R3)


def _views(s: Setup) -> list:
    c = s.catalog
    return [run(c.day(TODAY)), run(c.competitions()), run(c.season_matches("la-liga")),
            run(c.table("la-liga")), run(c.table("la-liga", "home")),
            run(c.scorers("la-liga")), run(c.teams("la-liga")), run(c.team(MADRID_KEY)),
            run(c.team_matches(MADRID_KEY)), run(c.person("70017-kai-delantero")),
            run(c.named("70017-kai-delantero")),
            run(c.match("200003-test-roma-v-real-madrid-2026-11-24")),
            run(c.goals("200003-test-roma-v-real-madrid-2026-11-24")),
            run(c.search_entries()), run(c.madrid()),
            run(c.h2h(MADRID_KEY, "90002-norte" if s.football else "norte-cf", NOW))]


@pytest.mark.parametrize("key", ["test-only", None])
def test_every_view_has_safe_keys_and_every_served_line_passes_the_copy_guard(key):
    for view in _views(build(key=key)):
        data = to_json(view)
        assert banned_key_paths(data, parts=BANNED_KEY_PARTS) == []
        lines = [*view.freshness.lines, *view.missing, *(c.line for c in view.coverage)]
        assert [line for line in lines if scan_labels(line)] == []


def test_every_fixed_line_and_line_shape_passes_the_copy_guard():
    from galactico.match_centre.season.competitions import COMPETITIONS

    shapes = [*cat.LINES, cat.listed_line(1), cat.listed_line(500), cat.cut_line(100)]
    for config in COMPETITIONS:
        shapes += [f"{config.name} can’t be read right now.",
                   f"{config.name}: the last schedule read is shown."]
    assert [line for line in shapes if scan_labels(line)] == []


# ------------------------------------------------------------------ hygiene


ALLOWED = {(2, "feed"), (2, "freshness"), (2, "names"), (2, "openfootball"), (2, "openligadb"),
           (2, "studio"), (2, "kickoff"), (1, None), (1, "adapters"), (1, "budget"),
           (1, "competitions"), (1, "crosswalk"), (1, "football_data"), (1, "infobox"),
           (1, "keys"), (1, "model"), (1, "revisions"), (1, "wiki_season"), (1, "wikidata"),
           (1, "derive")}


@pytest.mark.parametrize("name", ["catalog.py", "adapters.py"])
def test_the_modules_import_only_what_plan_3_1_allows(name):
    tree = ast.parse((SEASON / name).read_text(encoding="utf-8"))
    stdlib = set(sys.stdlib_module_names) | {"__future__"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(a.name.split(".")[0] in stdlib for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0:
                assert node.module.split(".")[0] in stdlib, node.module
            else:
                assert (node.level, node.module) in ALLOWED, node.module
    text = (SEASON / name).read_text(encoding="utf-8")
    assert "galactico.domain" not in text and "ortools" not in text.casefold()
    assert "recommend" not in text.casefold()


def test_no_crest_link_and_no_dropped_field_reaches_a_view():
    blob = repr([to_json(v) for v in _views(build())])
    for word in ("crests.football-data.org", "assets.example.invalid", "playedMatches",
                 "shirtNumber", "emblem", "odds"):
        assert word not in blob, word


def test_the_licence_guard_passes_the_catalogue_files():
    spec = importlib.util.spec_from_file_location("check_licensing",
                                                  ROOT / "scripts" / "check_licensing.py")
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    paths = [SEASON / n for n in ("catalog.py", "adapters.py", "crosswalk.py", "goals.py")]
    paths += [ROOT / "tests" / n for n in ("test_season_catalog.py", "test_crosswalk.py",
                                           "test_season_goals.py")]
    assert guard.check(paths) == []


def test_without_a_key_madrids_squad_is_the_lists_own_keyed_by_article_title():
    s = build(key=None)
    team = run(s.catalog.team(MADRID_KEY)).value
    assert team.squad[0].person.key == "inaki-portero", "an accent never changes a key"
    assert all(e.born is not None or e.person.name == "Hugo Central" for e in team.squad), \
        "the infobox's birth date where Wikipedia states one"


def test_a_cup_day_shows_madrids_tie_from_wikipedia_and_credits_only_it():
    s = build()
    view = run(s.catalog.day(date(2026, 10, 28)))
    assert [(m.competition, m.home.name, m.result.home, m.result.away) for m in view.value] == [
        ("copa-del-rey", "Atlético Prueba", 0, 4)]
    assert view.credits == ("wikipedia",)
    assert s.fd_calls() == 1, "the day resource was still read, and listed nothing"


def test_a_table_after_a_day_counts_only_results_up_to_it():
    s = build(key=None)
    after = run(s.catalog.table("la-liga", "after", date(2026, 8, 23))).value
    madrid = next(r for r in after.rows if r.team.key == MADRID_KEY)
    assert (after.view, after.after, madrid.played, madrid.points) == ("after", "2026-08-23",
                                                                       1, 3)
    full = run(s.catalog.table("la-liga")).value
    assert next(r for r in full.rows if r.team.key == MADRID_KEY).points == 6


class FakeRevisions:
    """The revision reader's grid, given: one appearance per finished match of the article,
    keyed as Wikipedia keys them (match and player)."""

    def __init__(self) -> None:
        self.asked: list = []

    async def grid(self, title, matches, *, since, upcoming=None, refs=None):
        from galactico.match_centre.season.model import Appearance
        from galactico.match_centre.season.revisions import Grid

        self.asked.append((title, since, upcoming, dict(refs or {})))
        kai = (refs or {})["Kai Delantero"]
        rows = tuple(Appearance(person=kai, match=m.key, state="appeared", sources=())
                     for m in matches if m.status == "FINISHED")
        return Grid(appearances=rows, checks=(), unattributed=(), first={}), []


def test_appearances_are_keyed_as_the_catalogue_keys_matches_and_players():
    s = build()
    s.catalog.revisions = FakeRevisions()
    run(s.catalog.season_matches("la-liga"))
    run(s.catalog.teams("la-liga"))
    view = run(s.catalog.madrid())
    asked = s.catalog.revisions.asked[0]
    assert asked[0] == wiki.TITLE and asked[1] == "2026-07-01T00:00:00Z"
    assert asked[2] == "2026-11-28T20:00:00Z", "the next match bounds the last snapshot"
    keys = {a.match for a in view.value.appearances}
    assert "100001-real-madrid-v-a-fc-2026-08-22" in keys
    assert "atletico-prueba-v-real-madrid-2026-10-28" in keys
    assert {a.person.key for a in view.value.appearances} == {"70017-kai-delantero"}
    assert cat.NO_APPEARANCES not in view.missing

