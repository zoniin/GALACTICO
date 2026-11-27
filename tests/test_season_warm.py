"""The warming plan (PLAN D4-A, ``season/warm.py``), on football-data.org's invented world.

Each test targets one way a scheduled run could overspend or warm the wrong thing:

- more than four requests at priority 2 in a run, or more than one at priority 3;
- a request at a reader's priority, or one that spends the reserve readers keep;
- a request for a resource a cache already holds fresh;
- a resource read under other parameters or another version than the catalogue's own, so a
  page still meets it cold after the run;
- the steps out of the contract's order, or the round robin stuck on one player;
- a request with no key, or after the key is refused;
- a reply that carries anything but counts.

football-data.org is ``season_v4``'s world behind ``httpx.MockTransport``; Wikipedia answers
404 (the day view reads Real Madrid's cup ties there, and goes on without them). Nothing reads
a recorded reply or the network.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, date, datetime, timedelta

import httpx
import pytest
import season_v4 as v4

from galactico.domain.labels import scan_labels
from galactico.domain.thesis import BANNED_KEY_PARTS, banned_key_paths
from galactico.match_centre.openfootball import OpenFootball
from galactico.match_centre.season import warm
from galactico.match_centre.season.budget import Budget, RequestBudget
from galactico.match_centre.season.catalog import Catalog
from galactico.match_centre.season.competitions import COMPETITIONS
from galactico.match_centre.season.football_data import FootballData
from galactico.match_centre.season.keys import MADRID_KEY
from galactico.match_centre.season.wiki_season import MadridSeason

NOW = datetime(2026, 11, 27, 18, 0, tzinfo=UTC)
"""Friday 27 November 2026, 19:00 in Madrid: the sample world's today."""
TODAY = date(2026, 11, 27)


def run(coroutine):
    return asyncio.run(coroutine)


class Clock:
    def __init__(self) -> None:
        self.now = NOW

    def __call__(self) -> datetime:
        return self.now


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    reached: list[str] = []

    async def refuse(self, request):
        reached.append(request.url.host)
        raise httpx.ConnectError("no network in tests")

    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", refuse)
    yield
    assert reached == [], "no request left the process"


def build(*, world: v4.World | None = None, key: str | None = "test-only",
          budget: Budget | None = None, available: int = 1000
          ) -> tuple[Catalog, v4.World, Clock]:
    """The catalogue over the invented world. ``available`` is what every reply says is left
    of the key's minute (``X-Requests-Available-Minute``)."""
    world = world or v4.sample_world()
    world.available = available
    clock = Clock()
    football = None
    if key is not None:
        football = FootballData(key, transport=world.transport(), now=clock,
                                budget=budget or Budget(per_minute=1000, reserve=0))
    wikipedia = httpx.MockTransport(lambda request: httpx.Response(404))
    catalog = Catalog(football=football, openfootball=OpenFootball(),
                      madrid=MadridSeason(transport=wikipedia, clock=clock), clock=clock)
    return catalog, world, clock


def finish_today(world: v4.World, code: str, match_id: int, result=(1, 0)) -> None:
    """Make one of ``world``'s matches of today finished."""
    listed = world.matches[code]
    clubs = {c.id: c for c in world.clubs[code]}
    for n, m in enumerate(listed):
        if m["id"] == match_id:
            listed[n] = v4.match(match_id, m["utcDate"], clubs[m["homeTeam"]["id"]],
                                 clubs[m["awayTeam"]["id"]], code=code, status="FINISHED",
                                 result=result, half_time=result, matchday=m["matchday"],
                                 stage=m["stage"], last_updated="2026-11-27T17:55:00Z")
            return
    raise KeyError(match_id)


def described(calls: list[warm.Call]) -> list[tuple]:
    return [(c.step, c.resource, c.competition, c.season, c.priority) for c in calls]


# ------------------------------------------------------------------ the plan


def test_the_plan_lists_the_contracts_steps_in_order_and_makes_no_request():
    catalog, world, _ = build()
    calls = run(warm.plan(NOW, catalog))
    assert world.calls == []
    assert [c.step for c in calls] == sorted(c.step for c in calls)
    pd, cl = "la-liga", "champions-league"
    others = [c.slug for c in COMPETITIONS
              if c.fd_code and c.gate is None and c.slug not in (pd, cl)]
    assert described(calls) == [
        (1, "day", None, None, 2),
        (2, "season_matches", pd, None, 2), (2, "standings", pd, None, 2),
        (2, "season_matches", cl, None, 2), (2, "standings", cl, None, 2),
        (3, "teams", pd, None, 2), (3, "teams", cl, None, 2),
        # No finish seen yet (step 4), no squad held yet (step 5).
        (6, "season_matches", pd, 2025, 2), (6, "season_matches", pd, 2024, 2),
        (6, "season_matches", pd, 2023, 2), (6, "season_matches", cl, 2025, 2),
        (6, "season_matches", cl, 2024, 2), (6, "season_matches", cl, 2023, 2),
        *[(7, "teams", slug, None, 3) for slug in others],
    ]
    assert "copa-libertadores" not in others, "a competition gated by P-D9 is not warmed"
    assert run(warm.plan(NOW, build(key=None)[0])) == []


def test_a_fresh_catalogue_reads_each_competition_at_the_days_first_version():
    # warm._moved reads a moved version as one that is not the date's alone.
    catalog, _, _ = build()
    assert {catalog.version(c.slug) for c in COMPETITIONS} == {TODAY.toordinal() * 1000}


def test_step_five_takes_the_squad_round_robin_a_new_player_first_each_slot():
    catalog, world, clock = build()
    run(catalog.football.teams("PD", 2026))
    madrid = [p.fd_id for p in world.squads[86]]
    firsts = []
    for slot in range(3):
        now = NOW + slot * warm.SLOT
        clock.now = now
        persons = [c.person for c in run(warm.plan(now, catalog)) if c.step == 5]
        assert sorted(persons) == sorted(madrid) and len(persons) == len(set(persons))
        turn = madrid.index(persons[0])
        assert persons == madrid[turn:] + madrid[:turn], "the squad's order, rotated"
        firsts.append(persons[0])
    assert len(set(firsts)) == 3


# ------------------------------------------------------------------ the run


def test_a_cold_run_spends_four_requests_at_priority_2_then_one_for_search():
    catalog, world, _ = build()
    report = run(warm.run(NOW, catalog))
    assert report.enabled and report.requests == 5 == len(world.calls)
    assert [call.split("?")[0] for call in world.calls] == [
        "/v4/matches", "/v4/competitions/PD/matches", "/v4/competitions/PD/standings",
        "/v4/competitions/CL/matches", "/v4/competitions/PL/teams"]
    steps = {s.step: s for s in report.steps}
    assert (steps[1].read, steps[2].read, steps[2].deferred) == (1, 3, 1)
    assert steps[7].read == 1 and steps[7].read + steps[7].deferred + steps[7].failed == (
        steps[7].planned)


def test_each_run_reads_only_what_no_cache_holds_and_never_more_than_five():
    catalog, world, clock = build()
    seen: list[str] = []
    for slot in range(8):
        clock.now = NOW + slot * warm.SLOT
        before = len(world.calls)
        report = run(warm.run(clock.now, catalog))
        made = world.calls[before:]
        assert report.requests == len(made) <= warm.WARM_REQUESTS + warm.SEARCH_REQUESTS
        # The day is the only resource that is due again a slot later (a match is in play).
        again = [call for call in made if call in seen and not call.startswith("/v4/matches?")]
        assert again == [], again
        seen += made
    paths = {call.split("?")[0] for call in seen}
    assert {"/v4/competitions/PD/teams", "/v4/competitions/CL/teams"} <= paths
    assert any(path.startswith("/v4/persons/") for path in paths), "step 5 was reached"
    assert any("season=2023" in call for call in seen), "step 6 was reached"


def test_what_a_run_keeps_is_what_the_pages_ask_for():
    # After the plan has run through, the catalogue's own views of those resources are
    # answered from the caches: under a cap of no request, none is deferred.
    catalog, world, clock = build()
    for slot in range(12):
        clock.now = NOW + timedelta(seconds=30) + slot * timedelta(seconds=1)
        run(warm.run(clock.now, catalog))
    assert run(warm.run(clock.now, catalog)).requests == 0
    before = len(world.calls)
    player = f"{v4.SQUAD[16].fd_id}-kai-delantero"
    with RequestBudget(0) as cap:
        views = [run(catalog.day(TODAY)), run(catalog.season_matches("la-liga")),
                 run(catalog.table("la-liga")), run(catalog.season_matches("champions-league")),
                 run(catalog.table("champions-league")), run(catalog.teams("la-liga")),
                 run(catalog.named(player))]
    assert len(world.calls) == before and cap.deferred == 0
    assert all(not view.freshness.partial for view in views)
    assert views[-1].value, "the named list the run kept is the one the player page reads"


def test_a_finish_seen_today_moves_its_competition_into_step_four():
    world = v4.sample_world()
    finish_today(world, "PL", 300003, (2, 0))
    finish_today(world, "PD", 100007, (1, 0))
    catalog, world, _ = build(world=world)
    report = run(warm.run(NOW, catalog))
    assert report.requests == 5
    calls = run(warm.plan(NOW, catalog))
    step4 = [(c.resource, c.competition) for c in calls if c.step == 4]
    # La Liga's season matches and standings are step 2's already; its scorers are new.
    assert step4 == [("scorers", "la-liga"), ("season_matches", "premier-league"),
                     ("standings", "premier-league"), ("scorers", "premier-league")]
    assert catalog.version("premier-league") == TODAY.toordinal() * 1000 + 1


def test_the_run_keeps_the_reserve_readers_spend_and_stops_when_the_minute_is_down_to_it():
    # Seven of the key's minute left, two kept back by the client: priority 2 spends while
    # more than four are left, so a run makes two requests; a reader (priority 1) still can.
    catalog, world, _ = build(available=7, budget=Budget(per_minute=10, reserve=2))
    report = run(warm.run(NOW, catalog))
    assert report.requests == 2 == len(world.calls)
    assert sum(s.deferred for s in report.steps) >= 1
    run(catalog.table("champions-league"))
    assert len(world.calls) == 3, "the reader's cold resource was read"


def test_no_key_no_request_and_a_refused_key_stops_the_run():
    catalog, world, _ = build(key=None)
    report = run(warm.run(NOW, catalog))
    assert not report.enabled and report.requests == 0 and report.to_json()["planned"] == 0
    catalog, world, _ = build(key="not-the-world's-token")
    report = run(warm.run(NOW, catalog))
    assert len(world.calls) == 1 and report.requests == 1
    assert report.to_json()["failed"] == 1
    assert run(warm.run(NOW, catalog)).enabled is False, "the client is off for the hour"
    assert len(world.calls) == 1


def test_the_reply_is_counts_only_with_safe_keys():
    catalog, world, _ = build()
    payload = run(warm.run(NOW, catalog)).to_json()
    assert banned_key_paths(payload, parts=BANNED_KEY_PARTS) == []
    text = json.dumps(payload)
    for club in ("Real Madrid", "Norte", "Test Roma", "Kai"):
        assert club not in text
    assert all(isinstance(v, (bool, int)) for k, v in payload.items() if k != "steps")
    assert [step["step"] for step in payload["steps"]] == list(warm.STEPS)
    assert scan_labels([warm.__doc__.splitlines()[0]]) == []
    assert MADRID_KEY.startswith("86-")
