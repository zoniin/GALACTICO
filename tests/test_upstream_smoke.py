"""The upstream probe reports each source and fails only on a failed or empty one.

Corpus-free and offline: the feeds are stubbed here; the probe itself is what asks the real
sources, on its own schedule (.github/workflows/upstream-smoke.yml).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from galactico.match_centre.feed import FeedError, Snapshot
from galactico.match_centre.openfootball import OpenFootball
from galactico.match_centre.openligadb import OpenLigaDB
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
