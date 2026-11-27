"""The football-data.org client (PLAN D2-A): normalisers, tiers, budget, errors and the key.

Each test targets one way the client could mislead, overspend or leak:

- a reply normalised into something the source did not say: a dropped field (B1) that reaches
  an object, a crest link, a missing count turned into 0, an undecided club given a name, a
  match put on the wrong Europe/Madrid day (R8, R9);
- a request the tiers or the budget should have saved: concurrent readers, a fresh shared-store
  entry, a deferral, a known 403 or 404, an hour after a rejected key;
- rows served as fresher than they are (``checked``), or stale rows not served when the
  source fails;
- an upstream status mapped to the wrong error, or upstream text repeated;
- the key in anything but the request's own header.

Every reply comes from ``season_v4``'s invented world through ``httpx.MockTransport``; nothing
here reads a recorded reply or calls the API.
"""

from __future__ import annotations

import ast
import asyncio
import importlib.util
import json
import logging
import re
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import httpx
import pytest
import season_v4 as v4

from galactico.domain.labels import scan_labels
from galactico.domain.thesis import BANNED_KEY_PARTS, banned_key_paths
from galactico.match_centre import feed as feed_module
from galactico.match_centre.feed import FeedError, Snapshot
from galactico.match_centre.season import football_data as fdmod
from galactico.match_centre.season.budget import DEFERRED_LINE, Budget, Deferred, RequestBudget
from galactico.match_centre.season.competitions import COMPETITIONS
from galactico.match_centre.season.football_data import (
    DAY_TTL,
    TABLE_ORDER,
    TTL,
    Disabled,
    FootballData,
    KeyRejected,
    NotCovered,
    NotFound,
    Throttled,
    Unknown,
    day_ttl,
    madrid_day,
)
from galactico.match_centre.season.model import (
    Competition,
    Match,
    Named,
    Person,
    ScorerLine,
    Table,
    Team,
    to_json,
)
from galactico.match_centre.season.store import MAX_TTL, MemoryStore, decode
from galactico.providers import LicenseViolation
from galactico.providers import base as providers_base

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "galactico" / "match_centre" / "season" / "football_data.py"

DUMMY = "fd-dummy-credential-Q7x-never-shown"
"""A recognisable invented key: if it turns up anywhere but the request header, it leaked."""
START = datetime(2026, 11, 27, 18, 0, tzinfo=UTC)
"""Friday 27 November 2026, 19:00 in Madrid: the sample world's "today"."""


class Clock:
    """The two clocks a client reads, moved together: wall (``now``) and monotonic."""

    def __init__(self, wall: datetime = START) -> None:
        self.wall = wall
        self.mono = 1000.0

    def now(self) -> datetime:
        return self.wall

    def monotonic(self) -> float:
        return self.mono

    def advance(self, seconds: float) -> None:
        self.wall += timedelta(seconds=seconds)
        self.mono += seconds


@pytest.fixture
def clock(monkeypatch) -> Clock:
    """Both clocks, with ``FeedCache``'s monotonic time moved with them."""
    found = Clock()
    monkeypatch.setattr(feed_module, "monotonic", found.monotonic)
    return found


class Recorder:
    """A transport handler around a world: records each request's headers, and can answer a
    status of its own instead (``override``) or fail as a network would (``broken``)."""

    def __init__(self, world: v4.World) -> None:
        self.world = world
        self.headers: list[dict[str, str]] = []
        self.urls: list[str] = []
        self.override: tuple[int, bytes, dict[str, str]] | None = None
        self.broken: Exception | None = None

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.headers.append(dict(request.headers))
        self.urls.append(str(request.url))
        if self.broken is not None:
            raise self.broken
        if self.override is not None:
            status, content, headers = self.override
            self.world.calls.append(request.url.path)
            return httpx.Response(status, content=content,
                                  headers={**v4.rate_headers(), **headers}, request=request)
        return self.world.reply(request)

    @property
    def calls(self) -> int:
        return len(self.headers)


def world() -> v4.World:
    found = v4.sample_world()
    found.token = DUMMY
    found.available = 99
    return found


def client(recorder: Recorder, clock: Clock, *, store: MemoryStore | None = None,
           budget: Budget | None = None, recheck: float = 0.0, key: str = DUMMY
           ) -> FootballData:
    return FootballData(
        key, transport=httpx.MockTransport(recorder),
        store=store if store is not None else MemoryStore(clock=clock.monotonic),
        budget=budget if budget is not None else Budget(100, 0, clock.monotonic),
        clock=clock.monotonic, now=clock.now, recheck=recheck)


def run(coro):
    return asyncio.run(coro)


async def everything(fd: FootballData) -> dict[str, object]:
    """One read of each of the eight resources."""
    return {
        "competitions": await fd.competitions(),
        "day": await fd.day(date(2026, 11, 27)),
        "season_matches": await fd.season_matches("PD"),
        "standings": await fd.standings("CL"),
        "teams": await fd.teams("PD"),
        "scorers": await fd.scorers("PD"),
        "person": await fd.person(70017),
        "person_matches": await fd.person_matches(70017),
    }


def walk_keys(node: object) -> set[str]:
    found: set[str] = set()
    if isinstance(node, dict):
        for key, value in node.items():
            found.add(key)
            found |= walk_keys(value)
    elif isinstance(node, list):
        for item in node:
            found |= walk_keys(item)
    return found


# ------------------------------------------------------------------ every resource normalises


def test_every_resource_normalises_into_the_model(clock):
    recorder = Recorder(world())
    found = run(everything(client(recorder, clock)))
    kinds = {"competitions": Competition, "day": Match, "season_matches": Match,
             "standings": Table, "teams": Team, "scorers": ScorerLine,
             "person_matches": Named}
    for name, kind in kinds.items():
        assert found[name] and all(isinstance(item, kind) for item in found[name]), name
    assert isinstance(found["person"], Person)
    assert recorder.calls == 8
    assert recorder.world.calls == [
        "/v4/competitions", "/v4/matches?dateFrom=2026-11-26&dateTo=2026-11-28",
        "/v4/competitions/PD/matches?season=2026", "/v4/competitions/CL/standings",
        "/v4/competitions/PD/teams?season=2026", "/v4/competitions/PD/scorers?limit=100",
        "/v4/persons/70017", "/v4/persons/70017/matches?limit=50&competitions=PD%2CCL"]


def test_competitions_are_the_covered_ones_in_pr_2_1_order(clock):
    recorder = Recorder(world())
    listed = run(client(recorder, clock).competitions())
    covered = [c.slug for c in COMPETITIONS if c.fd_code]
    assert [c.slug for c in listed] == covered  # the European Championship is not covered
    by_slug = {c.slug: c for c in listed}
    assert by_slug["la-liga"].season == "2026/27" and by_slug["la-liga"].fd_code == "PD"
    assert by_slug["brasileirao"].season == "2026"  # a calendar season
    assert by_slug["la-liga"].current_matchday == 14
    assert by_slug["la-liga"].matchdays is None  # derived later, never assumed


def test_a_match_says_what_the_source_says_and_nothing_else(clock):
    recorder = Recorder(world())
    matches = {m.fd_id: m for m in run(client(recorder, clock).season_matches("PD"))}
    first = matches[100001]
    assert first.key == "100001-real-madrid-v-a-fc-2026-08-22"
    assert first.home.key == "86-real-madrid" and first.home.plate == "RMA"
    assert first.competition == "la-liga" and first.season == "2026/27"
    assert (first.result.home, first.result.away) == (3, 1)
    assert (first.half_time.home, first.half_time.away) == (1, 0)
    assert first.winner == "HOME_TEAM" and first.duration == "REGULAR"
    assert first.referee == "Iván Silbato (Spain)"
    assert matches[100002].referee == "Pau Arbitro"  # no nationality stated
    assert matches[100004].referee is None  # no referee listed
    assert first.kickoff_utc == "2026-08-22T19:00:00Z" and first.kickoff_confirmed
    assert first.source_updated == v4.STAMP and first.sources[0].revised == v4.STAMP
    assert first.sources[0].provider == "football_data_org" and first.sources[0].url is None
    assert first.legacy_keys == () and first.ground is None and first.attendance is None
    scheduled = matches[100009]
    assert scheduled.status == "SCHEDULED" and not scheduled.kickoff_confirmed
    assert (scheduled.result.home, scheduled.result.away) == (None, None)  # never 0
    assert scheduled.winner is None
    assert matches[100008].status == "TIMED" and matches[100008].kickoff_confirmed
    assert matches[100006].status == "POSTPONED" and not matches[100006].kickoff_confirmed
    assert matches[100005].status == "AWARDED" and matches[100005].winner == "AWAY_TEAM"
    live = matches[100007]
    assert live.status == "IN_PLAY" and (live.result.home, live.result.away) == (1, 0)
    # Kick-off, then the competition's order, then the home club, then the id.
    order = [m.fd_id for m in run(client(recorder, clock).season_matches("PD"))]
    assert order == [100002, 100001, 100004, 100003, 100005, 100006, 100007, 100008, 100009]


def test_the_table_is_the_sources_own(clock):
    recorder = Recorder(world())
    fd = client(recorder, clock)
    (table,) = run(fd.standings("PD"))
    expected = v4.table_rows(recorder.world.matches["PD"], recorder.world.clubs["PD"])
    assert table.competition == "la-liga" and table.view == "all" and table.after is None
    assert table.order == TABLE_ORDER and not table.derived
    assert [(r.position, r.team.fd_id, r.played, r.won, r.drawn, r.lost, r.goals_for,
             r.goals_against, r.goal_difference, r.points) for r in table.rows] == [
        (e["position"], e["team"]["id"], e["playedGames"], e["won"], e["draw"], e["lost"],
         e["goalsFor"], e["goalsAgainst"], e["goalDifference"], e["points"]) for e in expected]
    assert all(not r.shared and r.form == () for r in table.rows)
    (league_phase,) = run(fd.standings("CL"))
    assert league_phase.competition == "champions-league"


def test_a_shared_position_is_marked_shared():
    body = v4.standings("PD", v4.table_rows([], [v4.A_FC, v4.NORTE, v4.RIBERA]))
    body["standings"][0]["table"][1]["position"] = 1
    rows = fdmod.normalise_standings(body, START.isoformat(), config=COMPETITIONS[0])
    assert [r["shared"] for r in rows[0]["rows"]] == [True, True, False]


def test_a_group_stage_gives_one_table_per_group_and_home_and_away_are_not_read():
    rows = v4.table_rows([], [v4.TEST_ALBION, v4.TEST_CITY])
    body = v4.standings("PL", rows, types=("TOTAL", "HOME", "AWAY"))
    body["standings"].append({"stage": "GROUP_STAGE", "type": "TOTAL", "group": "Group B",
                              "table": rows})
    tables = fdmod.normalise_standings(body, START.isoformat(), config=COMPETITIONS[4])
    assert len(tables) == 2 and all(t["view"] == "all" for t in tables)


def test_squads_map_the_four_positions_and_nothing_else(clock):
    recorder = Recorder(world())
    teams = {t.ref.fd_id: t for t in run(client(recorder, clock).teams("PD"))}
    madrid = teams[86]
    assert madrid.ref.key == "86-real-madrid" and madrid.area == "Spain"
    assert madrid.founded == 1900 and madrid.ground == "Estadio Invento"
    assert madrid.coach is not None and madrid.coach.name == v4.COACH[0]
    assert madrid.competitions == ("la-liga",)
    groups = {e.person.name: e.group for e in madrid.squad}
    assert groups["Inaki Portero"] == "GK" and groups["Dario Lateral"] == "DF"
    assert groups["Pablo Medio"] == "MF" and groups["Kai Delantero"] == "FW"
    assert groups["Oleh Nuevo"] is None  # position null
    assert groups["Marco Reserva"] is None  # position the string "null"
    assert all(e.shirt is None for e in madrid.squad)  # never football-data.org's number
    assert [e.person.name for e in madrid.squad] == [p.name for p in v4.SQUAD]  # source order
    entry = madrid.squad[0]
    assert entry.person.key == "70001-inaki-portero" and entry.born == "1996-03-14"
    assert entry.nationality == "Spain"
    assert teams[90003].ground is None  # Ribera's venue is not stated
    assert all(s.revised is None for t in teams.values() for s in t.sources)  # B1


def test_other_position_words_are_not_guessed():
    body = v4.teams("PD", [v4.team(v4.A_FC, ())])
    body["teams"][0]["squad"] = [
        {"id": 1, "name": "Uno Ejemplo", "position": "Centre-Back", "dateOfBirth": "2000-01-01",
         "nationality": "Spain"},
        {"id": 2, "name": "Dos Ejemplo", "position": "Goalkeeper", "dateOfBirth": "not a date",
         "nationality": None}]
    (team,) = fdmod.normalise_teams(body, START.isoformat())
    assert [(m["group"], m["born"]) for m in team["squad"]] == [(None, "2000-01-01"),
                                                                ("GK", None)]


def test_scorers_keep_missing_counts_missing_and_say_when_the_list_is_cut(clock):
    recorder = Recorder(world())
    fd = client(recorder, clock)
    lines = run(fd.scorers("PD"))
    assert [(s.person.name, s.goals, s.assists, s.penalties) for s in lines] == [
        ("Kai Delantero", 3, 1, 1), ("Vinicio Ala", 1, 2, None),
        ("Ciro Arco", 3, None, None), ("Carlos Punta", 1, None, None)]
    assert all(s.listed == 4 and not s.cut and s.competition == "la-liga" for s in lines)
    assert lines[2].team.key == "90001-a-fc"
    cut = run(fd.scorers("PD", limit=3))
    assert [s.listed for s in cut] == [3, 3, 3] and all(s.cut for s in cut)


def test_a_reply_that_states_a_lower_limit_than_asked_is_cut_at_it():
    body = v4.scorers("PD", [v4.scorer(v4.SQUAD[16], v4.MADRID, 2)], limit=1)
    rows = fdmod.normalise_scorers(body, START.isoformat(), config=COMPETITIONS[0], limit=500)
    assert rows[0]["cut"] and rows[0]["listed"] == 1


def test_a_person_has_no_shirt_and_a_coarse_group(clock):
    recorder = Recorder(world())
    person = run(client(recorder, clock).person(70017))
    assert person.ref.key == "70017-kai-delantero" and person.fd_id == 70017
    assert person.group == "FW" and person.shirt is None  # FD's shirtNumber is 99
    assert person.born == "1998-02-28" and person.nationality == "Germany"
    assert person.positions == () and person.height_cm is None and person.wp_title is None
    assert person.sources[0].revised == v4.STAMP


def test_named_lists_join_to_the_season_matches_keys(clock):
    recorder = Recorder(world())
    fd = client(recorder, clock)
    named = run(fd.person_matches(70017))
    season = {m.fd_id: m.key for code in ("PD", "CL") for m in run(fd.season_matches(code))}
    wanted = sorted((m for m in recorder.world.all_matches()
                     if m["id"] in recorder.world.named[70017]), key=lambda m: m["utcDate"])
    assert [n.match for n in named] == [season[m["id"]] for m in wanted]
    assert all(n.person.key == "70017-kai-delantero" for n in named)


def test_undecided_clubs_and_uncovered_competitions_are_left_out(clock):
    recorder = Recorder(world())
    cl = run(client(recorder, clock).season_matches("CL"))
    assert 200005 not in {m.fd_id for m in cl}  # the play-off slot without clubs
    euro = v4.match(900001, "2026-11-27T19:00:00Z", v4.TESTLAND, v4.TEST_CITY, code="EC")
    body = v4.day([euro, v4.match(900002, "2026-11-27T19:00:00Z", v4.A_FC, v4.NORTE)],
                  "2026-11-26", "2026-11-28")
    rows = fdmod.normalise_matches(body, START.isoformat())
    assert [r["fd_id"] for r in rows] == [900002]


def test_statuses_the_model_does_not_hold_are_read_or_refused():
    extra = v4.match(900003, "2026-11-27T19:00:00Z", v4.A_FC, v4.NORTE, status="EXTRA_TIME",
                     result=(1, 1))
    (row,) = fdmod.normalise_matches(v4.day([extra], "2026-11-26", "2026-11-28"), "x")
    assert row["status"] == "IN_PLAY"
    odd = v4.match(900004, "2026-11-27T19:00:00Z", v4.A_FC, v4.NORTE, status="ABANDONED")
    with pytest.raises(ValueError):
        fdmod.normalise_matches(v4.day([odd], "2026-11-26", "2026-11-28"), "x")
    no_time = v4.day([v4.match(900005, "2026-11-27T19:00:00Z", v4.A_FC, v4.NORTE)],
                     "2026-11-26", "2026-11-28")
    no_time["matches"][0]["utcDate"] = None
    with pytest.raises(ValueError):
        fdmod.normalise_matches(no_time, "x")


# ------------------------------------------------------------------ B1 and crests


def test_the_dropped_fields_reach_no_object_and_no_stored_row(clock):
    source = world()
    source.scorer_lines["PD"][0]["playedMatches"] = 777  # a value seen nowhere else
    recorder = Recorder(source)
    store = MemoryStore(clock=clock.monotonic)
    fd = client(recorder, clock, store=store)
    found = run(everything(fd))
    payload = to_json(found)
    stored = [decode(blob).rows for _, _, blob in store._entries.values()]
    for node in (payload, stored):
        keys = walk_keys(node)
        for dropped in ("playedMatches", "shirtNumber", "crest", "emblem", "flag", "odds",
                        "filters", "client", "lastUpdated", "score", "website", "address"):
            assert dropped not in keys, dropped
        text = json.dumps(node, ensure_ascii=False)
        assert "example.invalid" not in text  # every crest, emblem, flag and website
        assert "Odds" not in text and "synthetic" not in text
        assert "777" not in text and "White / Gold" not in text
        assert '"shirt": 99' not in text


def test_no_reply_holds_a_crest_url(clock):
    source = world()
    crest_host = "https://" + "crests." + "football-data.org"

    def crested(request: httpx.Request) -> httpx.Response:
        reply = source.reply(request)
        text = reply.content.decode().replace("https://assets.example.invalid", crest_host)
        return httpx.Response(reply.status_code, content=text.encode(),
                              headers=dict(reply.headers), request=request)

    fd = FootballData(DUMMY, transport=httpx.MockTransport(crested),
                      store=MemoryStore(clock=clock.monotonic),
                      budget=Budget(100, 0, clock.monotonic), clock=clock.monotonic,
                      now=clock.now, recheck=0)
    text = json.dumps(to_json(run(everything(fd))))
    assert "crests" not in text and "://" not in text
    assert "football-data.org" not in text  # the provider is named by its id, never a host


# ------------------------------------------------------------------ the tiers


def test_fifty_concurrent_calls_make_one_request(clock):
    recorder = Recorder(world())
    fd = client(recorder, clock, recheck=60)

    async def crowd():
        tables = await asyncio.gather(*(fd.standings("PD") for _ in range(50)))
        days = await asyncio.gather(*(fd.day(date(2026, 11, 27)) for _ in range(50)))
        return tables, days

    tables, days = run(crowd())
    assert recorder.calls == 2
    assert all(t == tables[0] for t in tables) and all(d == days[0] for d in days)


def test_fresh_rows_held_in_the_process_make_no_request_until_their_lifetime_ends(clock):
    recorder = Recorder(world())
    fd = client(recorder, clock)
    run(fd.standings("PD"))
    clock.advance(TTL["standings"] - 1)
    run(fd.standings("PD"))
    assert recorder.calls == 1
    clock.advance(2)
    run(fd.standings("PD"))
    assert recorder.calls == 2


def test_a_shared_store_hit_makes_no_request_and_an_expired_one_refetches(clock):
    recorder = Recorder(world())
    store = MemoryStore(clock=clock.monotonic)
    first = client(recorder, clock, store=store)
    (table,) = run(first.standings("PD"))
    assert recorder.calls == 1
    assert len(store) == 1 and all(tags == frozenset({"fd"})
                                   for _, tags, _ in store._entries.values())
    clock.advance(600)
    second = client(recorder, clock, store=store)  # another instance: an empty tier three
    (again,) = run(second.standings("PD"))
    assert recorder.calls == 1
    assert again.sources[0].checked == table.sources[0].checked == START.isoformat()
    # The stored rows' own time is judged, not when this instance first saw them.
    clock.advance(TTL["standings"] - 600)
    (fresh,) = run(second.standings("PD"))
    assert recorder.calls == 2
    assert fresh.sources[0].checked == clock.wall.isoformat()


def test_the_shared_store_keeps_rows_a_week_at_most_and_purges_by_tag(clock):
    recorder = Recorder(world())
    store = MemoryStore(clock=clock.monotonic)
    run(client(recorder, clock, store=store).competitions())
    ((expires, _, _),) = store._entries.values()
    assert expires - clock.mono == MAX_TTL == 7 * 86400
    run(store.purge("fd"))
    assert len(store) == 0


def test_a_new_version_reads_once_and_the_old_version_stays_held(clock):
    recorder = Recorder(world())
    fd = client(recorder, clock)
    run(fd.standings("PD", version=0))
    run(fd.standings("PD", version=1))
    run(fd.standings("PD", version=1))
    run(fd.standings("PD", version=0))
    assert recorder.calls == 2


def test_an_earlier_season_lives_thirty_days(clock):
    source = world()
    source.past[("PD", 2025)] = [v4.match(400001, "2026-03-01T20:00:00Z", v4.MADRID, v4.NORTE,
                                          status="FINISHED", result=(2, 0), half_time=(1, 0))]
    recorder = Recorder(source)
    fd = client(recorder, clock)
    (past,) = run(fd.season_matches("PD", 2025))
    assert past.season == "2025/26"
    clock.advance(TTL["season_matches"] + 1)
    run(fd.season_matches("PD", 2025))
    assert recorder.calls == 1
    clock.advance(TTL["past_season"])
    run(fd.season_matches("PD", 2025))
    assert recorder.calls == 2


def test_stale_rows_keep_their_checked_when_the_source_fails(clock):
    recorder = Recorder(world())
    store = MemoryStore(clock=clock.monotonic)
    fd = client(recorder, clock, store=store)
    (table,) = run(fd.standings("PD"))
    clock.advance(TTL["standings"] + 60)
    recorder.override = (503, b"Service Unavailable", {})
    snap = run(fd.resource("/competitions/PD/standings", {}, ttl=TTL["standings"], priority=1,
                           normalise=lambda body, checked: []))
    assert snap.warning == "Feed unavailable." and snap.checked == START.isoformat()
    (stale,) = run(fd.standings("PD"))
    assert stale == table and stale.sources[0].checked == START.isoformat()
    # A cold instance has only the shared store: it serves those rows, with their time.
    cold = client(recorder, clock, store=store)
    (stale,) = run(cold.standings("PD"))
    assert stale == table
    snap = run(cold.resource("/competitions/PD/standings", {}, ttl=TTL["standings"],
                             priority=1, normalise=lambda body, checked: []))
    assert snap.warning == "Feed unavailable." and snap.checked == START.isoformat()


def test_with_nothing_held_a_failure_is_an_error(clock):
    recorder = Recorder(world())
    recorder.override = (502, b"", {})
    with pytest.raises(FeedError) as caught:
        run(client(recorder, clock).standings("PD"))
    assert type(caught.value) is FeedError and str(caught.value) == "Feed unavailable."


# ------------------------------------------------------------------ the status map


def body(message: str, code: int) -> bytes:
    return json.dumps({"message": message, "errorCode": code}).encode()


STATUS_CASES = [
    ("400 bad token", 400, body("Your API token is invalid.", 400), KeyRejected),
    ("400 read as restricted", 400, body("The resource is restricted.", 400), KeyRejected),
    ("401", 401, body("Authentication failed.", 401), KeyRejected),
    ("403 restricted", 403, body("The resource you are looking for is restricted.", 403),
     NotCovered),
    ("403 read as a token", 403, body("Your API token is invalid.", 403), NotCovered),
    ("404", 404, body("The resource you are looking for does not exist.", 404), NotFound),
    ("429", 429, body("You reached your request limit. Wait 4 seconds.", 429), Throttled),
    ("500", 500, b"<html>Internal error</html>", FeedError),
    ("503", 503, b"", FeedError),
    ("301", 301, b"", FeedError),
    ("200 with an error code", 200, body("restricted", 403), NotCovered),
    ("200 unreadable", 200, b"<html>not json</html>", FeedError),
    ("200 another shape", 200, json.dumps({"standings": "none"}).encode(), FeedError),
]


@pytest.mark.parametrize("label,status,content,error", STATUS_CASES,
                         ids=[case[0] for case in STATUS_CASES])
def test_the_status_map(label, status, content, error, clock):
    recorder = Recorder(world())
    recorder.override = (status, content, {"Location": "https://example.invalid/"}
                         if status == 301 else {})
    with pytest.raises(FeedError) as caught:
        run(client(recorder, clock).standings("PD"))
    assert type(caught.value) is error
    assert isinstance(caught.value, FeedError)
    text = str(caught.value)
    # The source's words are never repeated: only the client's own fixed lines.
    assert text in {fdmod.UNAVAILABLE, fdmod.UNREADABLE, fdmod.OFF_LINE,
                    fdmod.NOT_COVERED_LINE, fdmod.NOT_FOUND_LINE, fdmod.THROTTLED_LINE}
    assert "token" not in text.lower() and "restricted" not in text.lower()
    assert caught.value.__cause__ is None
    if error is FeedError:
        assert text == (fdmod.UNREADABLE if status == 200 else fdmod.UNAVAILABLE)
    assert recorder.calls == 1  # no redirect was followed


def test_unknowns_are_the_404_family():
    assert issubclass(NotCovered, Unknown) and issubclass(NotFound, Unknown)
    assert issubclass(Unknown, FeedError) and not issubclass(KeyRejected, Unknown)
    assert issubclass(KeyRejected, Disabled) and issubclass(Throttled, FeedError)


@pytest.mark.parametrize("failure", [httpx.ConnectTimeout("timed out"),
                                     httpx.ReadTimeout("timed out"),
                                     httpx.ConnectError("refused")])
def test_a_timeout_or_a_lost_connection_is_feed_unavailable(failure, clock):
    recorder = Recorder(world())
    recorder.broken = failure
    with pytest.raises(FeedError) as caught:
        run(client(recorder, clock).standings("PD"))
    assert type(caught.value) is FeedError and str(caught.value) == "Feed unavailable."
    assert caught.value.__cause__ is None and caught.value.__context__ is None


def test_concurrent_readers_all_get_the_typed_error_from_one_request(clock):
    recorder = Recorder(world())
    recorder.world.fail = {"/persons/": "not_found"}
    fd = client(recorder, clock, recheck=60)

    async def crowd():
        return await asyncio.gather(*(fd.person(70017) for _ in range(10)),
                                    return_exceptions=True)

    errors = run(crowd())
    assert all(type(e) is NotFound for e in errors) and recorder.calls == 1


def test_a_rejected_key_turns_the_client_off_for_an_hour_and_logs_once(caplog, clock):
    source = world()
    source.token = "another-key"
    recorder = Recorder(source)
    fd = client(recorder, clock)
    caplog.set_level(logging.DEBUG)
    with pytest.raises(KeyRejected):
        run(fd.standings("PD"))
    assert not fd.enabled
    for read in (fd.teams("PD"), fd.day(date(2026, 11, 27)), fd.standings("PD")):
        with pytest.raises(KeyRejected):
            run(read)
    assert recorder.calls == 1  # nothing more was asked
    clock.advance(fdmod.OFF_FOR - 1)
    with pytest.raises(KeyRejected):
        run(fd.competitions())
    assert recorder.calls == 1
    records = [r for r in caplog.records if r.name == fdmod.__name__]
    assert len(records) == 1 and records[0].levelno == logging.WARNING
    assert DUMMY not in records[0].getMessage()
    source.token = DUMMY
    clock.advance(2)
    assert fd.enabled
    run(fd.competitions())
    assert recorder.calls == 2


def test_a_rejected_key_still_held_rows_are_not_served(clock):
    """Once the source refuses the key, the catalogue reads the next source rather than
    showing this one's rows as if they could still be refreshed."""
    recorder = Recorder(world())
    fd = client(recorder, clock)
    run(fd.standings("PD"))
    clock.advance(TTL["standings"] + 1)
    recorder.override = (401, body("Authentication failed.", 401), {})
    with pytest.raises(KeyRejected):
        run(fd.standings("PD"))


@pytest.mark.parametrize("kind,error,hold", [("restricted", NotCovered, fdmod.NOT_COVERED_FOR),
                                             ("not_found", NotFound, fdmod.NOT_FOUND_FOR)])
def test_a_403_or_a_404_is_remembered_for_its_hold(kind, error, hold, clock):
    recorder = Recorder(world())
    recorder.world.fail = {"/competitions/PD/scorers": kind}
    fd = client(recorder, clock)
    for _ in range(3):
        with pytest.raises(error):
            run(fd.scorers("PD"))
    assert recorder.calls == 1
    run(fd.teams("PD"))  # another resource is not affected
    assert recorder.calls == 2
    clock.advance(hold - 1)
    with pytest.raises(error):
        run(fd.scorers("PD"))
    assert recorder.calls == 2
    recorder.world.fail = {}
    clock.advance(2)
    assert run(fd.scorers("PD"))
    assert recorder.calls == 3


def test_an_uncovered_competition_asks_nothing(clock):
    recorder = Recorder(world())
    fd = client(recorder, clock)
    for read in (fd.standings("EC"), fd.season_matches("XYZ"), fd.teams("EC"),
                 fd.scorers("EC"), fd.person_matches(70017, competitions=("EC",))):
        with pytest.raises(NotCovered):
            run(read)
    assert recorder.calls == 0


def test_a_429_blocks_every_request_until_the_reset_plus_one_second(clock):
    source = world()
    source.reset = 30
    source.fail = {"/competitions/PD/standings": "throttled"}
    recorder = Recorder(source)
    fd = client(recorder, clock)
    with pytest.raises(Throttled) as caught:
        run(fd.standings("PD"))
    assert caught.value.retry_after == 31
    assert fd.budget.blocked_until == pytest.approx(clock.mono + 31)
    with pytest.raises(Deferred):
        run(fd.teams("PD"))
    assert recorder.calls == 1
    clock.advance(31)
    source.fail = {}
    run(fd.teams("PD"))
    run(fd.standings("PD"))
    assert recorder.calls == 3


# ------------------------------------------------------------------ the budget


def test_a_view_at_its_cap_makes_no_request(clock):
    recorder = Recorder(world())
    fd = client(recorder, clock)

    async def view():
        with RequestBudget(1, clock=clock.monotonic) as budget:
            await fd.standings("PD")
            with pytest.raises(Deferred):
                await fd.teams("PD")
            return budget

    budget = run(view())
    assert recorder.calls == 1 and budget.spent == 1 and budget.partial


def test_the_minutes_budget_defers_without_a_request_and_serves_what_is_held(clock):
    source = world()
    source.available = 3
    recorder = Recorder(source)
    fd = client(recorder, clock, budget=Budget(10, 2, clock.monotonic))
    run(fd.standings("PD"))  # the reply leaves 3 - 2 = 1 for this process
    with pytest.raises(Deferred) as caught:
        run(fd.teams("PD"))  # a reader's request stops while two are left
    assert caught.value.reason == "minute" and recorder.calls == 1
    clock.advance(TTL["standings"] + 1)
    fd.budget.observe({"X-Requests-Available-Minute": "0"}, 200)  # another consumer spent it
    snap = run(fd.resource("/competitions/PD/standings", {}, ttl=TTL["standings"], priority=1,
                           normalise=lambda body, checked: []))
    assert snap.warning == DEFERRED_LINE and snap.checked == START.isoformat()
    assert snap.rows and recorder.calls == 1


def test_a_day_with_a_match_in_play_is_read_at_priority_zero(clock):
    source = world()
    source.available, source.reset = 1, 600
    recorder = Recorder(source)
    fd = client(recorder, clock, budget=Budget(10, 0, clock.monotonic))
    today = date(2026, 11, 27)
    run(fd.day(today))  # the reply leaves one request: only priority 0 may spend it
    clock.advance(DAY_TTL["live"] + 1)
    with pytest.raises(Deferred):
        run(fd.season_matches("PD"))
    run(fd.day(today))
    assert recorder.calls == 2


def test_no_key_when_a_request_is_due_spends_no_budget(clock):
    recorder = Recorder(world())
    budget = Budget(100, 0, clock.monotonic)
    fd = FootballData(lambda: None, transport=httpx.MockTransport(recorder),
                      store=MemoryStore(clock=clock.monotonic), budget=budget,
                      clock=clock.monotonic, now=clock.now, recheck=0)
    with pytest.raises(Disabled):
        run(fd.standings("PD"))
    assert recorder.calls == 0 and budget.tokens == 100


# ------------------------------------------------------------------ the day and its lifetime


def test_a_day_is_the_europe_madrid_day():
    """Matches either side of Madrid's midnight, winter and summer: a match a minute after
    midnight in Madrid is the next day's, whatever its UTC date."""
    clubs = (v4.A_FC, v4.NORTE)
    winter = [v4.match(910001, "2026-11-26T22:59:00Z", *clubs),   # 23:59 on the 26th
              v4.match(910002, "2026-11-26T23:00:00Z", *clubs),   # 00:00 on the 27th
              v4.match(910003, "2026-11-27T22:59:00Z", *clubs),   # 23:59 on the 27th
              v4.match(910004, "2026-11-27T23:01:00Z", *clubs)]   # 00:01 on the 28th
    rows = fdmod.normalise_matches(v4.day(winter, "2026-11-26", "2026-11-28"), "x",
                                   day=date(2026, 11, 27))
    assert [r["fd_id"] for r in rows] == [910002, 910003]
    assert rows[0]["key"].endswith("-2026-11-27")
    summer = [v4.match(920001, "2026-07-01T21:59:00Z", *clubs),   # 23:59 on 1 July
              v4.match(920002, "2026-07-01T22:00:00Z", *clubs)]   # 00:00 on 2 July
    rows = fdmod.normalise_matches(v4.day(summer, "2026-07-01", "2026-07-02"), "x",
                                   day=date(2026, 7, 2))
    assert [r["fd_id"] for r in rows] == [920002]
    assert madrid_day(datetime(2026, 3, 29, 0, 59, tzinfo=UTC)) == date(2026, 3, 29)


def test_the_day_view_holds_only_its_own_days_matches(clock):
    recorder = Recorder(world())
    found = run(client(recorder, clock).day(date(2026, 11, 28)))
    assert [m.fd_id for m in found] == [100008]  # the 27th's and the 29th's are not listed


def row(status: str, kickoff: datetime) -> dict:
    return {"status": status, "kickoff_utc": kickoff.strftime("%Y-%m-%dT%H:%M:%SZ")}


def test_a_days_lifetime_follows_its_state():
    now = START
    today, past, future = date(2026, 11, 27), date(2026, 11, 20), date(2026, 12, 4)
    later = now + timedelta(hours=3)
    assert day_ttl([row("TIMED", later), row("PAUSED", now)], today, now=now) == 60
    assert day_ttl([row("TIMED", now + timedelta(minutes=25))], today, now=now) == 120
    assert day_ttl([row("FINISHED", now - timedelta(hours=3, minutes=50))], today,
                   now=now) == 120
    assert day_ttl([row("TIMED", now - timedelta(minutes=10))], today, now=now) == 120
    assert day_ttl([row("FINISHED", now - timedelta(hours=4, minutes=10))], today,
                   now=now) == 900
    assert day_ttl([row("POSTPONED", now + timedelta(minutes=5))], today, now=now) == 900
    assert day_ttl([row("TIMED", later)], today, now=now) == 900
    assert day_ttl([], today, now=now) == 900
    assert day_ttl([row("FINISHED", now - timedelta(days=7))], past, now=now) == 86400
    assert day_ttl([row("TIMED", now + timedelta(days=7))], future, now=now) == 21600
    # Madrid's today, not UTC's: 23:30 UTC on the 27th is the 28th in Madrid.
    late = datetime(2026, 11, 27, 23, 30, tzinfo=UTC)
    assert day_ttl([], date(2026, 11, 28), now=late) == 900


def test_a_live_day_is_read_again_after_a_minute(clock):
    recorder = Recorder(world())
    fd = client(recorder, clock)
    run(fd.day(date(2026, 11, 27)))
    clock.advance(59)
    run(fd.day(date(2026, 11, 27)))
    assert recorder.calls == 1
    clock.advance(2)
    run(fd.day(date(2026, 11, 27)))
    assert recorder.calls == 2


# ------------------------------------------------------------------ the key


def test_a_recognisable_dummy_key_appears_nowhere_but_the_request_header(caplog, clock):
    caplog.set_level(logging.DEBUG)
    source = world()
    recorder = Recorder(source)
    store = MemoryStore(clock=clock.monotonic)
    fd = client(recorder, clock, store=store)
    outputs: list[object] = [run(everything(fd))]
    errors: list[BaseException] = []
    for kind in ("not_found", "restricted", "throttled"):
        source.fail = {"/competitions/PD/teams": kind}
        clock.advance(120)
        try:
            run(client(recorder, clock).teams("PD"))
        except FeedError as error:
            errors.append(error)
    for failure in (httpx.ConnectTimeout("timed out"),):
        recorder.broken = failure
        try:
            run(client(recorder, clock).competitions())
        except FeedError as error:
            errors.append(error)
        recorder.broken = None
    source.fail = {}
    source.token = "another-key"
    try:
        run(client(recorder, clock).competitions())
    except FeedError as error:
        errors.append(error)
    assert {type(e) for e in errors} == {NotFound, NotCovered, Throttled, FeedError,
                                         KeyRejected}

    # It was sent, in the one header, on every request.
    assert recorder.headers and all(h["x-auth-token"] == DUMMY for h in recorder.headers)
    assert all(DUMMY not in value for h in recorder.headers
               for name, value in h.items() if name != "x-auth-token")
    assert all(DUMMY not in url for url in recorder.urls)
    # And it is nowhere else.
    texts = [json.dumps(to_json(outputs)), repr(outputs), repr(fd), repr(vars(fd)),
             repr(list(fd.cache._entries)), repr(list(fd._memo._items)),
             *(json.dumps(decode(blob).rows) for _, _, blob in store._entries.values()),
             *(repr(key) for key in store._entries)]
    for error in errors:
        texts += [str(error), repr(error), repr(error.args), repr(vars(error)),
                  repr(error.__cause__), repr(error.__context__)]
    for record in caplog.records:
        texts += [record.getMessage(), repr(record.args), str(record.exc_text)]
    assert caplog.records  # httpx logs each request; the client logs the rejection
    assert all(DUMMY not in text for text in texts)


def test_from_env_is_none_under_pytest_without_a_transport(monkeypatch):
    monkeypatch.setenv(fdmod.KEY_VARIABLE, DUMMY)
    assert FootballData.from_env() is None
    assert FootballData.from_env(environ={fdmod.KEY_VARIABLE: DUMMY,
                                          "PYTEST_CURRENT_TEST": "x"}) is None


def test_from_env_is_none_without_the_key(monkeypatch):
    recorder = Recorder(world())
    monkeypatch.delenv(fdmod.KEY_VARIABLE, raising=False)
    assert FootballData.from_env(transport=httpx.MockTransport(recorder)) is None
    monkeypatch.setenv(fdmod.KEY_VARIABLE, "   ")
    assert FootballData.from_env(transport=httpx.MockTransport(recorder)) is None


def test_from_env_reads_the_key_when_each_request_is_due(monkeypatch, clock):
    recorder = Recorder(world())
    monkeypatch.setenv(fdmod.KEY_VARIABLE, "first-invented-key")
    fd = FootballData.from_env(transport=httpx.MockTransport(recorder),
                               store=MemoryStore(clock=clock.monotonic),
                               budget=Budget(100, 0, clock.monotonic), clock=clock.monotonic,
                               now=clock.now, recheck=0)
    assert fd is not None
    monkeypatch.setenv(fdmod.KEY_VARIABLE, DUMMY)
    run(fd.competitions())
    assert recorder.headers[-1]["x-auth-token"] == DUMMY
    monkeypatch.delenv(fdmod.KEY_VARIABLE)
    clock.advance(TTL["standings"])
    with pytest.raises(Disabled):
        run(fd.standings("PD"))
    # Rows read while the key was set are not served once it is gone: without a key the
    # client reads nothing, as if it were not there.
    clock.advance(TTL["competitions"])
    with pytest.raises(Disabled):
        run(fd.competitions())
    assert recorder.calls == 1


def test_a_client_built_under_pytest_without_a_transport_asks_nothing():
    fd = FootballData(DUMMY, store=MemoryStore())
    assert not fd.enabled
    with pytest.raises(Disabled):
        run(fd.competitions())
    assert fd._client is None and fd.budget.tokens == 10


# ------------------------------------------------------------------ the guards


def test_the_licence_gate_comes_before_anything_else(monkeypatch, clock):
    recorder = Recorder(world())
    posture = providers_base.PROVIDERS["football_data_org"]
    monkeypatch.setitem(providers_base.PROVIDERS, "football_data_org",
                        replace(posture, tier=providers_base.DataTier.LOCAL_LICENSED,
                                may_host_derived=False))
    with pytest.raises(LicenseViolation):
        run(client(recorder, clock).standings("PD"))
    assert recorder.calls == 0


def test_every_reader_line_passes_the_copy_guard_and_names_no_key():
    lines = [fdmod.UNAVAILABLE, fdmod.UNREADABLE, fdmod.OFF_LINE, fdmod.NOT_COVERED_LINE,
             fdmod.NOT_FOUND_LINE, fdmod.THROTTLED_LINE, TABLE_ORDER,
             str(Disabled()), str(KeyRejected()), str(NotCovered()), str(NotFound()),
             str(Throttled(1.0))]
    for line in lines:
        assert scan_labels(line) == [], line
        assert not re.search(r"\b(key|token|plan|quota|subscription)\b", line, re.I), line


def test_every_object_passes_the_key_and_copy_guards(clock):
    recorder = Recorder(world())
    payload = to_json(run(everything(client(recorder, clock))))
    assert banned_key_paths(payload, parts=BANNED_KEY_PARTS) == []
    assert scan_labels(payload) == []


ALLOWED_IMPORTS = {"__future__", "asyncio", "collections", "collections.abc", "copy",
                   "dataclasses", "datetime", "functools", "json", "logging", "os", "time",
                   "typing", "urllib.parse", "httpx"}


def test_the_client_imports_only_what_plan_3_1_allows():
    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name in ALLOWED_IMPORTS, alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0:
                assert node.module in ALLOWED_IMPORTS, node.module
            elif node.level == 1:
                assert node.module in {"budget", "competitions", "keys", "model", "store"}
            elif node.level == 2:
                assert node.module in {"feed", "kickoff"}, node.module
            else:
                assert node.level == 3 and node.module == "providers", node.module


def test_the_licence_guard_passes_the_new_files():
    spec = importlib.util.spec_from_file_location("check_licensing",
                                                  ROOT / "scripts" / "check_licensing.py")
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    assert guard.check([MODULE, Path(__file__).resolve()]) == []


def test_the_client_closes_its_one_http_client(clock):
    recorder = Recorder(world())
    fd = client(recorder, clock)

    async def use():
        await fd.competitions()
        first = fd._client
        await fd.standings("PD")
        assert fd._client is first  # one client for every request
        await fd.aclose()
        assert first.is_closed and fd._client is None
        async with fd:
            await fd.teams("PD")
        assert fd._client is None

    run(use())


def test_a_snapshot_is_what_tier_three_keeps(clock):
    recorder = Recorder(world())
    fd = client(recorder, clock)
    snap = run(fd.resource("/competitions", {}, ttl=TTL["competitions"], priority=1,
                           normalise=fdmod.normalise_competitions))
    assert isinstance(snap, Snapshot) and snap.warning is None
    assert snap.checked == START.isoformat()
    assert all(isinstance(r, dict) for r in snap.rows)
    assert FootballData.key_for("/matches", {"dateTo": "b", "dateFrom": "a"}, 3) == \
        "fd:v1:/matches?dateFrom=a&dateTo=b@3"
