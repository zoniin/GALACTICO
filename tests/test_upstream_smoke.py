"""The upstream probe reports each source and fails only on a failed or empty one.

Corpus-free and offline: the feeds are stubbed here; the probe itself is what asks the real
sources, on its own schedule (.github/workflows/upstream-smoke.yml). football-data.org is
``season_v4``'s invented world behind ``httpx.MockTransport`` (PLAN D4-A): three requests at
most, counts only, the field-names contract, and nothing at all without the key.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import re
import sys
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
import season_v4 as v4

from galactico.match_centre.feed import FeedError, Snapshot
from galactico.match_centre.openfootball import OpenFootball
from galactico.match_centre.openligadb import OpenLigaDB
from galactico.match_centre.season.budget import Budget
from galactico.match_centre.studio import Studio

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("upstream_smoke", ROOT / "scripts/upstream_smoke.py")
smoke = importlib.util.module_from_spec(spec)
sys.modules.setdefault("upstream_smoke", smoke)  # its dataclass looks its module up
spec.loader.exec_module(smoke)

SCHEDULE = [dict(round="Matchday 1", date="2026-08-28", team1="A", team2="B", score=[1, 0]),
            dict(round="Matchday 2", date="2026-12-05", team1="B", team2="A")]
LIGADB = [{"matchID": 1, "matchDateTimeUTC": "2026-08-28T18:30:00Z", "group": {"groupOrderID": 1},
           "team1": {"teamId": 1, "teamName": "A"}, "team2": {"teamId": 2, "teamName": "B"},
           "matchIsFinished": True,
           "matchResults": [{"resultTypeID": 2, "pointsTeam1": 1, "pointsTeam2": 0}],
           "goals": [{"scoreTeam1": 1, "scoreTeam2": 0, "matchMinute": 3,
                      "goalGetterName": "A. One", "scoringTeamId": 1}]}]


@pytest.fixture
def feeds(monkeypatch):
    broken: set[str] = set()

    async def season(self, code, year):
        if code in broken:
            raise FeedError("Season file unavailable.")
        return Snapshot(SCHEDULE, "now")

    async def ligadb(self, shortcut, year):
        return Snapshot([] if shortcut in broken else LIGADB, "now")

    async def roster(self, day):
        return {"players": [{"apps": 3}, {"apps": None}], "source": "https://en.wikipedia.org/x"}

    monkeypatch.setattr(OpenFootball, "season", season)
    monkeypatch.setattr(OpenLigaDB, "season", ligadb)
    monkeypatch.setattr(Studio, "roster", roster)
    return broken


def test_every_upstream_is_reported_with_rows_and_latest_result(feeds, capsys):
    assert smoke.main([]) == 0
    out = capsys.readouterr().out
    for name in ("OpenFootball es.1 (La Liga)", "OpenFootball fr.1 (Ligue 1)", "OpenLigaDB bl1",
                 "OpenLigaDB pl", "OpenLigaDB ucl", "Wikipedia Real Madrid season"):
        assert name in out
    assert "| OpenFootball es.1 (La Liga) | ok | 2 | 2026-08-28 | 1 with a result |" in out
    assert "1 finished; 1 of 1 goals named; 1 of 1 matched to OpenFootball de.1" in out
    assert "1 players with appearances" in out


def test_a_failed_upstream_fails_the_run_and_a_late_one_only_when_asked(feeds, capsys):
    assert smoke.main(["--max-age", "100000"]) == 0
    assert smoke.main(["--max-age", "1"]) == 1
    assert "late (over 1 days)" in capsys.readouterr().out
    feeds.add("it.1")
    assert smoke.main(["--json"]) == 1
    assert '"ok": false' in capsys.readouterr().out


def test_an_emptied_goal_feed_fails_the_run(feeds, capsys):
    # F11: a season OpenLigaDB empties is the failure the probe exists to catch.
    feeds.add("ucl")
    assert smoke.main([]) == 1
    out = capsys.readouterr().out
    assert "| OpenLigaDB ucl | FAILED |" in out


# ------------------------------------------------------------------ football-data.org (D4-A)


def _client(world, *, mutate=None):
    """The probe's client over ``season_v4``'s invented world; ``mutate`` rewrites a reply's
    JSON body (a field renamed upstream)."""
    import httpx

    def reply(request):
        response = world.reply(request)
        if mutate is None:
            return response
        body = mutate(request.url.path, json.loads(response.content))
        return httpx.Response(response.status_code, headers=dict(response.headers),
                              content=json.dumps(body).encode(), request=request)

    return smoke._Kept("test-only", transport=httpx.MockTransport(reply),
                       budget=Budget(per_minute=100, reserve=2))


def test_without_the_key_football_data_is_skipped_and_fails_nothing(feeds, capsys):
    assert smoke.main([]) == 0
    out = capsys.readouterr().out
    assert "| football-data.org | skipped | 0 | - | skipped: FOOTBALL_DATA_KEY is not set |" in out


def test_football_data_is_asked_three_times_and_reported_in_counts_only(feeds, monkeypatch,
                                                                        capsys):
    world = v4.sample_world()
    monkeypatch.setattr(smoke._Kept, "from_env", classmethod(lambda cls: _client(world)))
    assert smoke.main(["--json"]) == 0
    results = [row for row in json.loads(capsys.readouterr().out)
               if row["upstream"].startswith("football-data.org")]
    assert [call.split("?")[0] for call in world.calls] == [
        "/v4/competitions", "/v4/competitions/PD/standings", "/v4/matches"]
    assert len(world.calls) == smoke.FD_REQUESTS
    by_name = {row["upstream"]: row for row in results}
    listed = v4.competitions(winners=world.winners)
    assert by_name["football-data.org competitions"]["rows"] == listed["count"]
    assert by_name["football-data.org standings PD"]["rows"] == len(world.clubs["PD"])
    today = datetime.now(UTC).date().isoformat()
    assert by_name[f"football-data.org day {today}"]["ok"]
    for row in results:
        assert row["ok"] and not row["skipped"], row
        assert re.search(r"fields: 0 of the contract's \d+ missing, 0 not in it", row["note"])
    text = json.dumps(results)
    for word in ("Real Madrid", "A FC", "Norte", "Test Roma", "Kai", "test-only"):
        assert word not in text, word


def test_a_field_gone_from_a_reply_fails_the_run_and_a_new_one_is_counted():
    def rename(path, body):
        if path == "/v4/matches":
            for match in body["matches"]:
                match["area"]["countryCode"] = match["area"].pop("code")
        return body

    world = v4.sample_world()
    results = asyncio.run(smoke._football_data(date(2026, 11, 27), _client(world,
                                                                           mutate=rename)))
    day = results[-1]
    assert not day.ok and "fields: 1 of the contract's" in day.note and "1 not in it" in day.note
    assert all(row.ok for row in results[:-1])


def test_an_object_the_reply_leaves_out_is_not_a_missing_field():
    contract = ["a", "a.x", "b", "b.c", "b.d", "l", "l[].x", "m", "m[].y"]
    body = json.dumps({"a": None, "b": {"c": 1}, "l": [], "m": [{"y": 1}, {"z": 2}]}).encode()
    assert smoke.contract_gaps(body, contract) == (1, 1)  # b.d gone; m[].z new


def test_a_refused_key_fails_the_rows_without_a_second_request_or_the_key():
    world = v4.sample_world()
    world.token = "another-token"
    results = asyncio.run(smoke._football_data(date(2026, 11, 27), _client(world)))
    assert len(world.calls) == 1 and not any(row.ok for row in results)
    assert all("test-only" not in row.note for row in results)
    assert smoke.table(results, date(2026, 11, 27), None).count("FAILED") == 3
